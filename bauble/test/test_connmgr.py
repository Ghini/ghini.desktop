#
# Copyright (c) 2015 Mario Frasca <mario@anche.no>
#
# This file is part of ghini.desktop.
#
# ghini.desktop is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ghini.desktop is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ghini.desktop. If not, see <http://www.gnu.org/licenses/>.
# Refactored for Pytest and SQLAlchemy 2.0.36 compatibility
# Refactored for Pytest and SQLAlchemy 2.0.36 compatibility

import copy
import logging
import os
import shutil
import tempfile
import threading
from collections.abc import Generator
from typing import Any

import bauble
import pytest
from bauble.connmgr import ConnMgrPresenter
from bauble.editor import MockDialog, MockView
from bauble.gtkinit import Gtk
from bauble.prefs import prefs
from bauble.test import check_dupids

logger: Any = logging.getLogger("bauble.connmgr")
logger._cache.clear()
logger.setLevel(logging.INFO)

# Create a global thread lock
prefs_lock: Any = threading.Lock()


@pytest.fixture(scope="function")
def mock_prefs() -> Generator[Any, None, None]:
    """
    Create an independent, thread-safe copy of the global `prefs` object for each test.
    """


    with prefs_lock:  # Ensure exclusive access
        # Create a deep copy of the global prefs for the test
        test_prefs = copy.deepcopy(prefs)
        test_prefs.testing = True  # Enable testing mode for the copy

        # Ensure all preferences are cleared before each test
        test_prefs.prefs.clear()
        test_prefs.prefs[bauble.conn_list_pref] = {}
        test_prefs.prefs[bauble.conn_default_pref] = None

        # Add necessary attributes and keys
        object.__setattr__(
            test_prefs, "picture_root_pref", "bauble.picture_root"
        )  # Attribute for the test
        test_prefs.prefs[test_prefs.picture_root_pref] = "/tmp"

    yield test_prefs  # Provide the isolated copy to the test

    # After the test, no need to restore `prefs` as it's untouched.


@pytest.fixture(autouse=True)
def reset_prefs(mock_prefs) -> None:
    """
    Reset preferences state before each test.
    Ensures the reset uses the mock_prefs fixture.
    """
    mock_prefs.prefs.clear()  # Clear all preferences
    mock_prefs.init(prefs=mock_prefs)  # Reinitialize prefs to default state
    mock_prefs.prefs[bauble.conn_list_pref] = {}
    mock_prefs.prefs[bauble.conn_default_pref] = None


@pytest.fixture
def mock_view():
    """
    Provide a mock view for presenter tests.
    """
    return MockView(combos={"name_combo": [], "type_combo": []})


@pytest.fixture
def mock_presenter(mock_view, mock_prefs):
    """
    Provide a presenter initialized with a mock view.
    """
    # Ensure mock_prefs is properly cleared
    mock_prefs.prefs[bauble.conn_list_pref] = {}
    mock_prefs.prefs[bauble.conn_default_pref] = None

    return ConnMgrPresenter(mock_view, prefs=mock_prefs)


def test_duplicate_ids() -> None:
    """
    Test for duplicate ids for all .glade files in the tag plugin.
    """
    import bauble.connmgr as mod

    head, _ = os.path.split(mod.__file__)
    assert not check_dupids(os.path.join(head, "connmgr.glade"))


class TestConnMgrPresenter:
    """
    Tests for the ConnMgrPresenter class.
    """

    def test_can_create_presenter(self, mock_presenter, mock_view) -> None:
        assert mock_presenter.view == mock_view

    def test_no_connections_then_message(self, mock_view, mock_prefs) -> None:
        mock_prefs.prefs[bauble.conn_list_pref] = {}

        # Now create the presenter, which will read the updated prefs
        mock_presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)

        mock_presenter.refresh_view()
        assert not mock_presenter.view.widget_get_visible("expander")
        assert mock_presenter.view.widget_get_visible("noconnectionlabel")

    def test_one_connection_shown_removed_message(self, mock_view, mock_prefs) -> None:
        # Configure the mock_prefs before instantiating the presenter
        mock_prefs.prefs[bauble.conn_list_pref] = {
            "nugkui": {
                "default": True,
                "pictures": "nugkui",
                "type": "SQLite",
                "file": "nugkui.db",
            }
        }

        # Now create the presenter, which will read the updated prefs
        mock_presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)

        # Refresh the presenter view to reflect the new preferences
        # mock_presenter.refresh_view()

        # Assertions before removal
        assert mock_presenter.view.widget_get_visible("expander")
        assert not mock_presenter.view.widget_get_visible("noconnectionlabel")

        # Remove the connection and refresh the view
        mock_presenter.remove_connection("nugkui")
        mock_presenter.refresh_view()

        # Assertions after removal
        assert mock_presenter.view.widget_get_visible("noconnectionlabel")
        assert not mock_presenter.view.widget_get_visible("expander")

    def test_one_connection_on_remove_confirm_negative(
        self, mock_view, mock_prefs
    ) -> None:
        """
        Test that the connection remains when the user confirms "No" on remove.
        """
        # Set up mock preferences with a single connection
        mock_prefs.prefs[bauble.conn_list_pref] = {
            "nugkui": {
                "default": True,
                "pictures": "nugkui",
                "type": "SQLite",
                "file": "nugkui.db",
            }
        }

        # Create the presenter with the mock view
        mock_presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)

        # Simulate user choosing "No" in the confirmation dialog
        mock_presenter.view.reply_yes_no_dialog.append(False)

        # Trigger the remove button action
        mock_presenter.on_remove_button_clicked("button")

        # Ensure that the UI elements remain unchanged
        assert mock_presenter.view.widget_get_visible(
            "expander"
        ), "Expander should remain visible."
        assert not mock_presenter.view.widget_get_visible(
            "noconnectionlabel"
        ), "No connection label should remain hidden."

        # Ensure the connection still exists in prefs
        assert (
            "nugkui" in mock_presenter.connections
        ), "Connection should not have been removed."

    def test_one_connection_on_remove_confirm_positive(
        self, mock_view, mock_prefs
    ) -> None:
        mock_prefs.prefs[bauble.conn_list_pref] = {
            "nugkui": {
                "default": True,
                "pictures": "nugkui",
                "type": "SQLite",
                "file": "nugkui.db",
            }
        }
        mock_presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)
        mock_presenter.view.reply_yes_no_dialog.append(True)
        mock_presenter.on_remove_button_clicked("button")

        # Assert visibility changes
        assert not mock_presenter.view.widget_get_visible("expander")
        assert mock_presenter.view.widget_get_visible("noconnectionlabel")

    def test_two_connection_initialize_default_first(
        self, mock_view, mock_prefs
    ) -> None:
        mock_prefs.prefs[bauble.conn_list_pref] = {
            "nugkui": {
                "default": True,
                "pictures": "nugkui",
                "type": "SQLite",
                "file": "nugkui.db",
            },
            "btuu": {
                "default": False,
                "pictures": "btuu",
                "type": "SQLite",
                "file": "btuu.db",
            },
        }
        mock_prefs.prefs[bauble.conn_default_pref] = "nugkui"
        mock_presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)

        # Assert default connection
        assert mock_presenter.connection_name == "nugkui"
        params = mock_presenter.connections[mock_presenter.connection_name]
        assert params["default"] is True
        assert mock_view.widget_get_value("usedefaults_chkbx")

    def test_two_connection_initialize_default_second(
        self, mock_view, mock_prefs
    ) -> None:
        mock_prefs.prefs[bauble.conn_list_pref] = {
            "nugkui": {
                "default": True,
                "pictures": "nugkui",
                "type": "SQLite",
                "file": "nugkui.db",
            },
            "btuu": {
                "default": False,
                "pictures": "btuu",
                "type": "SQLite",
                "file": "btuu.db",
            },
        }
        mock_prefs.prefs[bauble.conn_default_pref] = "bruu"
        mock_presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)

        # Assert fallback to the first connection in alphabetical order
        assert mock_presenter.connection_name == "btuu"
        params = mock_presenter.connections[mock_presenter.connection_name]
        assert params["default"] is False
        assert not mock_view.widget_get_value("usedefaults_chkbx")

    def test_two_connection_on_remove_confirm_positive(
        self, mock_view, mock_prefs
    ) -> None:
        mock_prefs.prefs[bauble.conn_list_pref] = {
            "nugkui": {
                "default": True,
                "pictures": "nugkui",
                "type": "SQLite",
                "file": "nugkui.db",
            },
            "btuu": {
                "default": True,
                "pictures": "btuu",
                "type": "SQLite",
                "file": "btuu.db",
            },
        }
        mock_presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)
        mock_presenter.view.reply_yes_no_dialog.append(True)
        mock_presenter.on_remove_button_clicked("button")

        # Assert the expander is still visible due to the second connection
        assert mock_presenter.view.widget_get_visible("expander")
        assert not mock_presenter.view.widget_get_visible("noconnectionlabel")
        assert "combobox_set_active" in mock_view.invoked

    def test_one_connection_shown_and_selected_sqlite(
        self, mock_view, mock_prefs
    ) -> None:
        mock_prefs.prefs[bauble.conn_list_pref] = {
            "nugkui": {
                "default": True,
                "pictures": "nugkui",
                "type": "SQLite",
                "file": "nugkui.db",
            }
        }
        mock_prefs.prefs[bauble.conn_default_pref] = "nugkui"
        mock_presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)

        # Assert connection is selected and UI is correct
        assert mock_presenter.connection_name == "nugkui"
        assert mock_presenter.view.widget_get_visible("expander")
        assert not mock_presenter.view.widget_get_visible("noconnectionlabel")

    def test_one_connection_shown_and_selected_postgresql(
        self, mock_view, mock_prefs
    ) -> None:
        mock_prefs.prefs[bauble.conn_list_pref] = {
            "quisquis": {
                "passwd": False,
                "pictures": "",
                "db": "quisquis",
                "host": "localhost",
                "user": "pg",
                "type": "PostgreSQL",
            }
        }
        mock_prefs.prefs[bauble.conn_default_pref] = "quisquis"
        mock_presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)

        # Assert PostgreSQL-specific UI elements
        assert mock_presenter.connection_name == "quisquis"
        assert mock_presenter.view.widget_get_visible("expander")
        assert mock_presenter.view.widget_get_visible("dbms_parambox")
        assert not mock_presenter.view.widget_get_visible("sqlite_parambox")
        assert not mock_presenter.view.widget_get_visible("noconnectionlabel")

    def test_one_connection_shown_and_selected_oracle(
        self, mock_view, mock_prefs
    ) -> None:
        # Set up the mock preferences for the test
        mock_prefs.prefs[bauble.conn_list_pref] = {
            "quisquis": {
                "passwd": False,
                "pictures": "",
                "db": "quisquis",
                "host": "localhost",
                "user": "pg",
                "type": "Oracle",
            }
        }
        mock_prefs.prefs[bauble.conn_default_pref] = "quisquis"

        # Create the presenter
        mock_presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)

        # Assert Oracle-specific behavior
        assert mock_presenter.connection_name == "quisquis"
        assert mock_presenter.view.widget_get_visible("expander")
        assert mock_presenter.view.widget_get_visible("dbms_parambox")
        assert not mock_presenter.view.widget_get_visible("sqlite_parambox")
        assert not mock_presenter.view.widget_get_visible("noconnectionlabel")

    def test_two_connections_wrong_default_use_first_one(
        self, mock_view, mock_prefs
    ) -> None:
        mock_prefs.prefs[bauble.conn_list_pref] = {
            "nugkui": {
                "default": True,
                "pictures": "nugkui",
                "type": "SQLite",
                "file": "nugkui.db",
            },
            "quisquis": {
                "passwd": False,
                "pictures": "",
                "db": "quisquis",
                "host": "localhost",
                "user": "pg",
                "type": "Oracle",
            },
        }
        mock_prefs.prefs[bauble.conn_default_pref] = "nonce"
        mock_presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)

        # Assert fallback to the first connection in alphabetical order
        as_list = mock_presenter.connection_names
        assert mock_presenter.connection_name == as_list[0]

    def test_when_user_selects_different_type(self, mock_view, mock_prefs) -> None:
        # Configure preferences
        mock_prefs.prefs[bauble.conn_default_pref] = "nugkui"
        mock_prefs.prefs[bauble.conn_list_pref] = {
            "nugkui": {
                "type": "SQLite",
                "default": True,
                "pictures": "nugkui",
                "file": "nugkui.db",
            },
            "quisquis": {
                "type": "PostgreSQL",
                "passwd": False,
                "pictures": "",
                "db": "quisquis",
                "host": "localhost",
                "user": "pg",
            },
        }

        # Create the presenter
        presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)

        # Initial state
        assert presenter.connection_name == "nugkui"
        assert presenter.view.widget_get_visible("sqlite_parambox")

        # Simulate user changing the selected connection type
        mock_view.widget_set_value("name_combo", "quisquis")
        presenter.dbtype = "PostgreSQL"
        presenter.on_name_combo_changed("name_combo")

        # Assert the new state
        assert presenter.connection_name == "quisquis"
        presenter.refresh_view()
        assert presenter.dbtype == "PostgreSQL"
        assert presenter.view.widget_get_visible("dbms_parambox")

    def test_set_default_toggles_sensitivity(self, mock_view, mock_prefs) -> None:
        # Configure preferences
        mock_prefs.prefs[bauble.conn_default_pref] = "nugkui"
        mock_prefs.prefs[bauble.conn_list_pref] = {
            "nugkui": {
                "type": "SQLite",
                "default": True,
                "pictures": "nugkui",
                "file": "nugkui.db",
            },
        }

        # Create the presenter
        presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)

        # Simulate toggling 'use defaults' checkbox
        mock_view.widget_set_value("usedefaults_chkbx", True)
        presenter.on_usedefaults_chkbx_toggled("usedefaults_chkbx")

        # Assert that file input sensitivity is toggled correctly
        assert not mock_view.widget_get_sensitive("file_entry")

    def test_check_parameters_valid(self, mock_view, mock_prefs) -> None:
        import copy

        # Configure preferences
        mock_prefs.prefs[bauble.conn_default_pref] = "quisquis"
        mock_prefs.prefs[bauble.conn_list_pref] = {
            "quisquis": {
                "type": "PostgreSQL",
                "passwd": False,
                "pictures": "/tmp/",
                "db": "quisquis",
                "host": "localhost",
                "user": "pg",
            }
        }

        # Create the presenter
        presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)

        # Test valid parameters
        params = presenter.connections["quisquis"]
        valid, message = presenter.check_parameters_valid(params)
        assert valid

        # Test invalid parameters
        invalid_cases = [
            {"user": ""},
            {"db": ""},
            {"host": ""},
        ]
        for case in invalid_cases:
            test_params = copy.copy(params)
            test_params.update(case)
            valid, message = presenter.check_parameters_valid(test_params)
            assert not valid

        # Test SQLite parameters
        sqlite_params = {
            "type": "SQLite",
            "default": False,
            "file": "/tmp/test.db",
            "pictures": "/tmp/",
        }
        valid, message = presenter.check_parameters_valid(sqlite_params)
        assert valid

        sqlite_params["file"] = "/sys"
        valid, message = presenter.check_parameters_valid(sqlite_params)
        assert not valid

    def test_parameters_to_uri_sqlite(self, mock_view, mock_prefs) -> None:
        # Initialize preferences
        mock_prefs.prefs[bauble.conn_default_pref] = None
        mock_prefs.prefs[bauble.conn_list_pref] = {}

        # Create the presenter
        presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)

        # Case 1: SQLite without additional options
        params = {
            "type": "SQLite",
            "default": False,
            "file": "/tmp/test.db",
            "pictures": "/tmp/",
        }
        assert presenter.parameters_to_uri(params) == "sqlite:////tmp/test.db"

        # Case 2: PostgreSQL without password
        params = {
            "type": "PostgreSQL",
            "passwd": False,
            "pictures": "/tmp/",
            "db": "quisquis",
            "host": "localhost",
            "user": "pg",
        }
        assert (
            presenter.parameters_to_uri(params) == "postgresql://pg@localhost/quisquis"
        )

        # Case 3: PostgreSQL with password
        params["passwd"] = True
        mock_view.reply_entry_dialog.append("secret")  # Simulate user entering password
        assert (
            presenter.parameters_to_uri(params)
            == "postgresql://pg:secret@localhost/quisquis"
        )

        # Case 4: PostgreSQL with port specified
        params["passwd"] = False
        params["port"] = "9876"
        assert (
            presenter.parameters_to_uri(params)
            == "postgresql://pg@localhost:9876/quisquis"
        )

        # Case 5: PostgreSQL with password and port specified
        params["passwd"] = True
        mock_view.reply_entry_dialog.append(
            "another_secret"
        )  # Simulate another password entry
        assert (
            presenter.parameters_to_uri(params)
            == "postgresql://pg:another_secret@localhost:9876/quisquis"
        )

        # Case 6: PostgreSQL with additional options
        params["passwd"] = False
        params["options"] = ["is_this_possible=no", "why_do_we_test=because"]
        assert presenter.parameters_to_uri(params) == (
            "postgresql://pg@localhost:9876/quisquis?"
            "is_this_possible=no&why_do_we_test=because"
        )

        # Case 7: PostgreSQL with password, port, and options
        params["passwd"] = True
        mock_view.reply_entry_dialog.append(
            "final_secret"
        )  # Simulate final password entry
        assert presenter.parameters_to_uri(params) == (
            "postgresql://pg:final_secret@localhost:9876/quisquis?"
            "is_this_possible=no&why_do_we_test=because"
        )

    def test_connection_uri_property(self, mock_view, mock_prefs) -> None:
        # Configure preferences
        mock_prefs.prefs[bauble.conn_default_pref] = "quisquis"
        mock_prefs.prefs[bauble.conn_list_pref] = {
            "quisquis": {
                "type": "PostgreSQL",
                "passwd": False,
                "pictures": "/tmp/",
                "db": "quisquis",
                "host": "localhost",
                "user": "pg",
            }
        }

        # Create the presenter
        presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)

        # Ensure connection is properly initialized
        assert presenter.connection_name == "quisquis"
        assert presenter.dbtype == "PostgreSQL"

        # Simulate updates via the view
        connection_params = presenter.connections["quisquis"]
        mock_view.widget_set_value("database_entry", connection_params["db"])
        presenter.on_text_entry_changed("database_entry")
        mock_view.widget_set_value("user_entry", connection_params["user"])
        presenter.on_text_entry_changed("user_entry")
        mock_view.widget_set_value("host_entry", connection_params["host"])
        presenter.on_text_entry_changed("host_entry")

        # Validate generated URI
        assert presenter.connection_uri == "postgresql://pg@localhost/quisquis"


class TestAddConnection:
    def test_no_connection_on_add_confirm_negative(self, mock_view, mock_prefs) -> None:
        # Setup empty connection list
        mock_prefs.prefs[bauble.conn_list_pref] = {}
        presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)

        # Simulate user canceling add connection dialog
        mock_view.reply_entry_dialog.append("")
        presenter.on_add_button_clicked("button")

        # Assert that nothing changes
        assert not presenter.view.widget_get_visible("expander")
        assert not presenter.view.widget_get_sensitive("connect_button")
        assert presenter.view.widget_get_visible("noconnectionlabel")

    def test_no_connection_on_add_confirm_positive(self, mock_view, mock_prefs) -> None:
        # Setup empty connection list
        mock_prefs.prefs[bauble.conn_list_pref] = {}
        presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)

        # Simulate user providing a valid connection name
        mock_view.reply_entry_dialog.append("conn_name")
        presenter.on_add_button_clicked("button")
        presenter.refresh_view()  # GTK would trigger this

        # Assert that the new connection is added, and visibility is updated
        assert presenter.view.widget_get_visible("expander")
        assert presenter.view.widget_get_sensitive("connect_button")
        assert not presenter.view.widget_get_visible("noconnectionlabel")

    def test_one_connection_on_add_confirm_positive(
        self, mock_view, mock_prefs
    ) -> None:
        # Setup initial connection in preferences
        mock_prefs.prefs[bauble.conn_list_pref] = {
            "nugkui": {
                "default": True,
                "pictures": "nugkui",
                "type": "SQLite",
                "file": "nugkui.db",
            }
        }
        mock_prefs.prefs[bauble.conn_default_pref] = "nugkui"
        presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)

        # Simulate user adding a new connection
        mock_view.reply_entry_dialog.append("new_conn")
        presenter.on_add_button_clicked("button")
        presenter.refresh_view()  # GTK would trigger this

        # Assert that the new connection is prepended to the combo box
        assert (
            "combobox_prepend_text",
            ["name_combo", "new_conn"],
        ) in presenter.view.invoked_detailed
        assert (
            "widget_set_value",
            ["name_combo", "new_conn", ()],
        ) in presenter.view.invoked_detailed

        # Simulate unresolved issue (Skipping test)
        pytest.skip("related to issue #194")


@pytest.fixture
def mock_renderer():
    """Provide a mock renderer."""

    class MockRenderer(dict):
        def set_property(self, key, value):
            self[key] = value

    return MockRenderer()


class GlobalFunctionsTests:
    def test_combo_cell_data_func(self, mock_renderer) -> None:
        import bauble.connmgr

        wt, at = bauble.connmgr.working_dbtypes, bauble.connmgr.dbtypes
        bauble.connmgr.working_dbtypes = ["a", "d"]
        bauble.connmgr.dbtypes = ["a", "b", "c", "d"]

        for index, name in enumerate(bauble.connmgr.dbtypes):
            bauble.connmgr.type_combo_cell_data_func(
                None, mock_renderer, bauble.connmgr.dbtypes, index
            )
            assert mock_renderer["sensitive"] == (
                name in bauble.connmgr.working_dbtypes
            )
            assert mock_renderer["text"] == name

        bauble.connmgr.working_dbtypes, bauble.connmgr.dbtypes = wt, at

    def test_is_package_name(self) -> None:
        from bauble.connmgr import is_package_name

        assert is_package_name("sqlite3")
        assert not is_package_name("sqlheavy42")


class ButtonBrowseButtons:
    def test_file_chosen(self, mock_view, mock_prefs) -> None:
        mock_view.reply_file_chooser_dialog.append("chosen")
        presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)
        presenter.on_file_btnbrowse_clicked()
        presenter.on_text_entry_changed("file_entry")
        assert presenter.filename == "chosen"

    def test_file_not_chosen(self, mock_view) -> None:
        mock_view.reply_file_chooser_dialog = []
        presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)
        presenter.filename = "previously"
        presenter.on_file_btnbrowse_clicked()
        assert presenter.filename == "previously"

    def test_pictureroot_not_chosen(self, mock_view) -> None:
        """
        Test that the pictureroot remains unchanged when no selection is made.
        """
        mock_view.reply_file_chooser_dialog = []  # Simulate no selection
        presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)
        presenter.pictureroot = "previously"

        # Simulate clicking the "browse" button for pictureroot
        presenter.on_pictureroot_btnbrowse_clicked()

        # Assert that pictureroot remains the same
        assert presenter.pictureroot == "previously"

    def test_pictureroot2_chosen(self, mock_view) -> None:
        """
        Test that the pictureroot is updated when a valid selection is made.
        """
        mock_view.reply_file_chooser_dialog.append("chosen")  # Simulate a selection
        presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)

        # Simulate clicking the "browse" button and updating the entry
        presenter.on_pictureroot2_btnbrowse_clicked()
        presenter.on_text_entry_changed("pictureroot2_entry")

        # Assert that pictureroot is updated to the chosen value
        assert presenter.pictureroot == "chosen"

    def test_pictureroot2_not_chosen(self, mock_view) -> None:
        """
        Test that the pictureroot remains unchanged when no selection is made.
        """
        mock_view.reply_file_chooser_dialog = []  # Simulate no selection
        presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)
        presenter.pictureroot = "previously"

        # Simulate clicking the "browse" button for pictureroot2
        presenter.on_pictureroot2_btnbrowse_clicked()

        # Assert that pictureroot remains the same
        assert presenter.pictureroot == "previously"


class OnDialogResponseTests:
    def test_on_dialog_response_ok_invalid_params(self, mock_view, mock_prefs) -> None:
        mock_prefs.prefs[bauble.conn_list_pref] = {}
        presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)
        dialog = MockDialog()
        presenter.on_dialog_response(dialog, Gtk.ResponseType.OK)
        assert "run_message_dialog" in mock_view.invoked
        assert dialog.hidden

    def test_on_dialog_response_ok_valid_params(self, mock_view, mock_prefs) -> None:
        mock_prefs.prefs[bauble.conn_list_pref] = {
            "nugkui": {
                "default": False,
                "pictures": "/tmp/nugkui",
                "type": "SQLite",
                "file": "/tmp/nugkui.db",
            }
        }
        mock_prefs.prefs[bauble.conn_default_pref] = "nugkui"
        mock_prefs.prefs[bauble.prefs.picture_root_pref] = "/tmp"
        presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)
        dialog = MockDialog()
        presenter.on_dialog_response(dialog, Gtk.ResponseType.OK)
        assert "run_message_dialog" not in mock_view.invoked
        assert dialog.hidden
        assert mock_prefs.prefs[bauble.prefs.picture_root_pref] == "/tmp/nugkui"


class TestButtonBrowseButtons:
    """
    Tests for file and picture root browse buttons.
    """

    def test_file_chosen(self, mock_view, mock_prefs) -> None:
        """
        Test that the file path is updated when a valid file is chosen.
        """
        mock_view.reply_file_chooser_dialog.append(
            "chosen"
        )  # Simulate a file selection
        presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)

        # Simulate clicking the "browse" button and updating the entry
        presenter.on_file_btnbrowse_clicked()
        presenter.on_text_entry_changed("file_entry")

        # Assert that the filename is updated to the chosen value
        assert presenter.filename == "chosen"

    def test_file_not_chosen(self, mock_view, mock_prefs) -> None:
        """
        Test that the file path remains unchanged when no file is chosen.
        """
        mock_view.reply_file_chooser_dialog = []  # Simulate no selection
        presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)
        presenter.filename = "previously"

        # Simulate clicking the "browse" button
        presenter.on_file_btnbrowse_clicked()

        # Assert that the filename remains the same
        assert presenter.filename == "previously"

    def test_pictureroot_chosen(self, mock_view, mock_prefs) -> None:
        """
        Test that the pictureroot is updated when a valid directory is chosen.
        """
        mock_view.reply_file_chooser_dialog.append(
            "chosen"
        )  # Simulate a directory selection
        presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)

        # Simulate clicking the "browse" button and updating the entry
        presenter.on_pictureroot_btnbrowse_clicked()
        presenter.on_text_entry_changed("pictureroot_entry")

        # Assert that the pictureroot is updated to the chosen value
        assert presenter.pictureroot == "chosen"

    def test_pictureroot_not_chosen(self, mock_view, mock_prefs) -> None:
        """
        Test that the pictureroot remains unchanged when no directory is chosen.
        """
        mock_view.reply_file_chooser_dialog = []  # Simulate no selection
        presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)
        presenter.pictureroot = "previously"

        # Simulate clicking the "browse" button
        presenter.on_pictureroot_btnbrowse_clicked()

        # Assert that the pictureroot remains the same
        assert presenter.pictureroot == "previously"

    def test_pictureroot2_chosen(self, mock_view, mock_prefs) -> None:
        """
        Test that the pictureroot2 is updated when a valid directory is chosen.
        """
        mock_view.reply_file_chooser_dialog.append(
            "chosen"
        )  # Simulate a directory selection
        presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)

        # Simulate clicking the "browse" button and updating the entry
        presenter.on_pictureroot2_btnbrowse_clicked()
        presenter.on_text_entry_changed("pictureroot2_entry")

        # Assert that the pictureroot is updated to the chosen value
        assert presenter.pictureroot == "chosen"

    def test_pictureroot2_not_chosen(self, mock_view, mock_prefs) -> None:
        """
        Test that the pictureroot2 remains unchanged when no directory is chosen.
        """
        mock_view.reply_file_chooser_dialog = []  # Simulate no selection
        presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)
        presenter.pictureroot = "previously"

        # Simulate clicking the "browse" button
        presenter.on_pictureroot2_btnbrowse_clicked()

        # Assert that the pictureroot remains the same
        assert presenter.pictureroot == "previously"


class TestOnDialogResponse:
    """
    Tests for the `on_dialog_response` method in `ConnMgrPresenter`.
    """

    def test_on_dialog_response_ok_invalid_params(self, mock_view, mock_prefs) -> None:
        """
        Test that a message dialog is displayed when invalid parameters are submitted.
        """
        mock_view.reply_file_chooser_dialog = []
        mock_view.invoked = []
        presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)
        dialog = MockDialog()

        presenter.on_dialog_response(dialog, Gtk.ResponseType.OK, prefs=mock_prefs)

        assert "run_message_dialog" in mock_view.invoked
        assert dialog.hidden

    def test_on_dialog_response_ok_valid_params(self, mock_view, mock_prefs) -> None:
        """
        Test that valid parameters are accepted, and preferences are updated.
        """
        mock_prefs.prefs[bauble.conn_list_pref] = {
            "nugkui": {
                "default": False,
                "pictures": "/tmp/nugkui",
                "type": "SQLite",
                "file": "/tmp/nugkui.db",
            }
        }
        mock_prefs.prefs[bauble.conn_default_pref] = "nugkui"
        mock_prefs.prefs[bauble.prefs.picture_root_pref] = "/tmp"
        mock_view.reply_file_chooser_dialog = []
        mock_view.invoked = []
        presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)
        dialog = MockDialog()

        presenter.on_dialog_response(dialog, Gtk.ResponseType.OK, prefs=mock_prefs)

        assert "run_message_dialog" not in mock_view.invoked
        assert dialog.hidden
        assert mock_prefs.prefs[bauble.prefs.picture_root_pref] == "/tmp/nugkui"

    def test_on_dialog_response_cancel(self, mock_view, mock_prefs) -> None:
        """
        Test that canceling the dialog hides it without further action.
        """
        mock_view.reply_file_chooser_dialog = []
        mock_view.reply_yes_no_dialog = [False]
        presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)
        dialog = MockDialog()

        presenter.on_dialog_response(dialog, Gtk.ResponseType.CANCEL, prefs=mock_prefs)

        assert "run_message_dialog" not in mock_view.invoked
        assert dialog.hidden

    def test_on_dialog_response_cancel_params_changed(
        self, mock_view, mock_prefs
    ) -> None:
        """
        Test that canceling the dialog after changes prompts a save confirmation.
        """
        mock_prefs.prefs[bauble.conn_list_pref] = {
            "nugkui": {
                "default": False,
                "pictures": "/tmp/nugkui",
                "type": "SQLite",
                "file": "/tmp/nugkui.db",
            }
        }
        mock_prefs.prefs[bauble.conn_default_pref] = "nugkui"
        mock_view.reply_file_chooser_dialog = []
        mock_view.reply_yes_no_dialog = [True]
        mock_view.invoked = []

        presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)

        # Simulate a parameter change
        mock_view.widget_set_value("usedefaults_chkbx", True)
        presenter.on_usedefaults_chkbx_toggled("usedefaults_chkbx")

        # Simulate canceling the dialog
        dialog = MockDialog()
        presenter.on_dialog_response(dialog, Gtk.ResponseType.CANCEL, prefs=mock_prefs)

        # Ensure a save confirmation dialog was shown
        assert "run_message_dialog" not in mock_view.invoked
        assert "run_yes_no_dialog" in mock_view.invoked
        assert dialog.hidden


@pytest.fixture
def temp_picture_folder() -> Generator[Any, None, None]:
    """
    Fixture to create a temporary directory and clean it up after the test.
    """
    path = tempfile.mkdtemp()  # Create the temporary directory
    yield path
    if os.path.exists(path):
        shutil.rmtree(
            path, ignore_errors=True
        )  # Recursively remove directory and contents


class TestDialogResponseAndFolders:
    def test_on_dialog_close_or_delete(self, mock_view, mock_prefs) -> None:
        """
        Test that closing or deleting the dialog hides the window.
        """
        presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)
        assert not mock_view.get_window().hidden  # Initial state
        presenter.on_dialog_close_or_delete("widget")
        assert mock_view.get_window().hidden  # After closing

    def test_on_dialog_response_ok_creates_picture_folders_exist(
        self, mock_view, mock_prefs, temp_picture_folder
    ) -> None:
        """
        Test that existing pictures and thumbs folders do not trigger redundant actions.
        """
        pictures_path = os.path.join(temp_picture_folder, "pictures")
        thumbs_path = os.path.join(pictures_path, "thumbs")
        os.makedirs(thumbs_path)  # Both folders already exist

        mock_prefs.prefs[bauble.conn_list_pref] = {
            "nugkui": {
                "default": False,
                "pictures": pictures_path,
                "type": "SQLite",
                "file": os.path.join(pictures_path, "nugkui.db"),
            }
        }
        mock_prefs.prefs[bauble.conn_default_pref] = "nugkui"
        presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)
        dialog = MockDialog()

        presenter.on_dialog_response(dialog, Gtk.ResponseType.OK, prefs=mock_prefs)

        assert os.path.isdir(pictures_path)
        assert os.path.isdir(thumbs_path)
        assert dialog.hidden

    def test_on_dialog_response_ok_creates_picture_folders_half_exist(
        self, mock_view, mock_prefs, temp_picture_folder
    ) -> None:
        """
        Test that only missing folders (thumbs) are created when pictures folder exists.
        """
        pictures_path = os.path.join(temp_picture_folder, "pictures")
        os.mkdir(pictures_path)  # Pictures folder exists; thumbs does not.

        mock_prefs.prefs[bauble.conn_list_pref] = {
            "nugkui": {
                "default": False,
                "pictures": pictures_path,
                "type": "SQLite",
                "file": os.path.join(pictures_path, "nugkui.db"),
            }
        }
        mock_prefs.prefs[bauble.conn_default_pref] = "nugkui"
        presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)
        dialog = MockDialog()

        presenter.on_dialog_response(dialog, Gtk.ResponseType.OK, prefs=mock_prefs)

        assert os.path.isdir(pictures_path)
        assert os.path.isdir(
            os.path.join(pictures_path, "thumbs")
        )  # Thumbs folder is created.
        assert dialog.hidden

    def test_on_dialog_response_ok_creates_picture_folders_no_exist(
        self, mock_view, mock_prefs, temp_picture_folder
    ) -> None:
        """
        Test that missing pictures and thumbs folders are created.
        """
        pictures_path = temp_picture_folder

        mock_prefs.prefs[bauble.conn_list_pref] = {
            "nugkui": {
                "default": False,
                "pictures": pictures_path,
                "type": "SQLite",
                "file": os.path.join(pictures_path, "nugkui.db"),
            }
        }
        # Configure picture root and default connection preference
        mock_prefs.prefs[mock_prefs.picture_root_pref] = pictures_path
        mock_prefs.prefs[bauble.conn_default_pref] = "nugkui"
        presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)
        dialog = MockDialog()

        presenter.on_dialog_response(dialog, Gtk.ResponseType.OK, prefs=mock_prefs)

        assert os.path.isdir(pictures_path)  # Pictures folder is created.
        assert os.path.isdir(
            os.path.join(pictures_path, "thumbs")
        )  # Thumbs folder is created.
        assert dialog.hidden

    def test_on_dialog_response_ok_creates_picture_folders_occupied(
        self, mock_view, mock_prefs, temp_picture_folder
    ) -> None:
        """
        Test that no folders are created when thumbnails or pictures are files.
        """
        pictures_path = os.path.join(temp_picture_folder, "pictures")
        thumbs_path = os.path.join(pictures_path, "thumbs")
        os.mkdir(pictures_path)
        with open(thumbs_path, "w") as f:  # Create thumbs as a file
            f.write("")

        mock_prefs.prefs[bauble.conn_list_pref] = {
            "nugkui": {
                "default": False,
                "pictures": pictures_path,
                "type": "SQLite",
                "file": os.path.join(pictures_path, "nugkui.db"),
            }
        }
        mock_prefs.prefs[bauble.conn_default_pref] = "nugkui"
        presenter = ConnMgrPresenter(mock_view, prefs=mock_prefs)
        dialog = MockDialog()

        presenter.on_dialog_response(dialog, Gtk.ResponseType.OK, prefs=mock_prefs)

        assert os.path.isdir(pictures_path)
        assert os.path.isfile(thumbs_path)  # Thumbs file is not replaced.
