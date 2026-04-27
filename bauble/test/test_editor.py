#
# Copyright (c) 2005,2006,2007,2008,2009 Brett Adams <brett@belizebotanic.org>
# Copyright (c) 2012-2015 Mario Frasca <mario@anche.no>
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
#
# test_bauble.py
#
# Import necessary modules
import datetime
import os

import bauble.paths as paths
import bauble.prefs as prefs
import bauble.utils as utils
import pytest
from bauble.editor import GenericEditorView
from bauble.utils import parse_date

# Ensure testing environment
prefs.testing = True


@pytest.fixture
def setup_generic_view():
    """
    Fixture to create a GenericEditorView instance.
    """

    def _setup(filename, root_widget_name=None):
        return GenericEditorView(filename, root_widget_name=root_widget_name)

    return _setup


def test_create_generic_view(setup_generic_view) -> None:
    """
    Test creating a GenericEditorView.
    """
    filename = os.path.join(paths.lib_dir(), "bauble.glade")
    view = setup_generic_view(filename)
    assert isinstance(view.widgets, utils.BuilderWidgets)


def test_set_title_ok(setup_generic_view) -> None:
    """
    Test setting the title with a root widget.
    """
    filename = os.path.join(paths.lib_dir(), "bauble.glade")
    view = setup_generic_view(filename, root_widget_name="main_window")
    title = "testing"
    view.set_title(title)
    assert view.get_window().get_title() == title


def test_set_title_no_root(setup_generic_view) -> None:
    """
    Test setting the title without a root widget.
    """
    filename = os.path.join(paths.lib_dir(), "bauble.glade")
    view = setup_generic_view(filename)
    title = "testing"
    with pytest.raises(NotImplementedError):
        view.set_title(title)
    with pytest.raises(NotImplementedError):
        view.get_window()


def test_set_icon_no_root(setup_generic_view) -> None:
    """
    Test setting the icon without a root widget.
    """
    filename = os.path.join(paths.lib_dir(), "bauble.glade")
    view = setup_generic_view(filename)
    title = "testing"
    with pytest.raises(NotImplementedError):
        view.set_icon(title)


def test_add_widget(setup_generic_view) -> None:
    """
    Test adding a widget to the view.
    """

    from bauble.gtkinit import Gtk

    filename = os.path.join(paths.lib_dir(), "bauble.glade")
    view = setup_generic_view(filename)
    label = Gtk.Label(label="testing")
    view.widget_add("statusbar", label)


@pytest.mark.skip(reason="Cannot be tested in a non-windowed environment")
def test_set_sensitive(setup_generic_view) -> None:
    """
    Test setting widget sensitivity.
    """
    filename = os.path.join(paths.lib_dir(), "connmgr.glade")
    view = setup_generic_view(filename, root_widget_name="main_dialog")
    view.widget_set_sensitive("cancel_button", True)
    assert view.widgets.cancel_button.get_sensitive()
    view.widget_set_sensitive("cancel_button", False)
    assert not view.widgets.cancel_button.get_sensitive()


def test_date_parser_generic() -> None:
    """
    Test parsing various date formats.
    """
    target = datetime.datetime(
        2019,
        1,
        18,
        18,
        20,
        tzinfo=datetime.timezone(datetime.timedelta(hours=5)),
    )
    assert parse_date("18 January 2019 18:20 +0500") == target
    assert parse_date("18:20, 18 January 2019 +0500") == target
    assert parse_date("18:20+0500, 18 January 2019") == target
    assert parse_date("18:20+0500, 18 Jan 2019") == target
    assert parse_date("18:20+0500, 2019-01-18") == target
    assert parse_date("18:20+0500, 1/18 2019") == target
    assert parse_date("18:20+0500, 18/1 2019") == target


def test_date_parser_ambiguous() -> None:
    """
    Test parsing ambiguous date formats with different settings.
    """
    assert parse_date("5 1 4") == datetime.datetime(2004, 1, 5, 0, 0)
    assert parse_date("5 1 4", dayfirst=False, yearfirst=False) == datetime.datetime(
        2004, 5, 1, 0, 0
    )
    assert parse_date("5 1 4", dayfirst=True, yearfirst=False) == datetime.datetime(
        2004, 1, 5, 0, 0
    )
    assert parse_date("5 1 4", dayfirst=False, yearfirst=True) == datetime.datetime(
        2005, 1, 4, 0, 0
    )
    assert parse_date("5 1 4", dayfirst=True, yearfirst=True) == datetime.datetime(
        2005, 4, 1, 0, 0
    )


def test_date_parser_365() -> None:
    """
    Test parsing date with fewer components.
    """
    target = datetime.datetime(2014, 1, 1, 20)
    assert parse_date("2014-01-01 20") == target
