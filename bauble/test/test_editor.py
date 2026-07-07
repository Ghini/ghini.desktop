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
from types import SimpleNamespace

import bauble.paths as paths
import bauble.prefs as prefs
import bauble.utils as utils
import pytest
from bauble.editor import GenericEditorView, NoteBox
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


def test_today_str_uses_local_today(monkeypatch) -> None:
    """Date-button defaults should use the process local calendar date."""
    monkeypatch.setattr(utils, "local_today", lambda: datetime.date(2026, 5, 14))

    assert utils.today_str("%Y-%m-%d") == "2026-05-14"


class _FakeEntry:
    def __init__(self, text="") -> None:
        self.text = text

    def get_text(self):
        return self.text

    def set_text(self, text) -> None:
        self.text = text


class _FakeParent:
    def __init__(self) -> None:
        self.refreshed = False

    def refresh_sensitivity(self) -> None:
        self.refreshed = True


class _FakePresenter:
    PROBLEM_EMPTY = "EMPTY"

    def __init__(self, parent) -> None:
        self._dirty = False
        self.notes = []
        self.parent = parent
        self.problems = []

    def add_problem(self, problem, widget) -> None:
        self.problems.append((problem, widget))

    def remove_problem(self, problem, widget) -> None:
        if (problem, widget) in self.problems:
            self.problems.remove((problem, widget))

    def parent_ref(self):
        return self.parent


def _note_box_with_date_entry(text="25-05-2026"):
    box = NoteBox.__new__(NoteBox)
    parent = _FakeParent()
    box.presenter = _FakePresenter(parent)
    box.model = SimpleNamespace(date=None, user=None, category=None, note=None)
    box.prefs = prefs
    box.widgets = SimpleNamespace(date_entry=_FakeEntry(text))
    box.update_label = lambda: None
    return box, parent


def test_note_box_date_entry_uses_editor_date_validator() -> None:
    box, _parent = _note_box_with_date_entry("25-05-2026")
    entry = _FakeEntry("25-05-2026")

    box.on_date_entry_changed(entry)

    assert box.model.date == datetime.date(2026, 5, 25)
    assert box.presenter.problems == []


def test_note_box_appends_new_note_once_when_date_is_missing() -> None:
    box, parent = _note_box_with_date_entry("25-05-2026")

    box.set_model_attr("note", "Test note")
    box.set_model_attr("category", "guided category")

    assert box.presenter.notes == [box.model]
    assert box.presenter._dirty is True
    assert parent.refreshed is True


def test_note_box_defaults_to_global_preferences() -> None:
    assert NoteBox._resolve_prefs(None) is prefs


def test_editing_persistent_model_does_not_corrupt_other_session(
    db_session,
) -> None:
    """
    GenericModelViewPresenterEditor merges `model` into its own
    (Temp)Session so that editing never dirties the session `model` came
    from -- e.g. the ResultsView's shared session.

    `_purge_phantom_backrefs()` exists to detach a *transient* model
    (freshly constructed as e.g. ``Plant(accession=some_accession)``) from
    the backref collection its own ``__init__`` auto-populated, before that
    orphan reference gets flushed. It must never run against a *persistent*
    model such as an existing Accession row selected in the ResultsView:
    doing so removes the object from its parent's already-loaded
    relationship collection and, because of ``back_populates``, nulls the
    object's own scalar reference to that parent -- corrupting live state
    in a session the editor was never supposed to touch.
    """
    from sqlalchemy.orm import object_session

    from bauble.editor import GenericModelViewPresenterEditor
    from bauble.plugins.garden.models import Accession
    from bauble.plugins.plants.family import Family
    from bauble.plugins.plants.genus import Genus
    from bauble.plugins.plants.species_model import Species

    family = Family(epithet="Cactaceae")
    genus = Genus(family=family, epithet="Echinocactus")
    species = Species(genus=genus, sp="grusonii")
    accession = Accession(species=species, code="1")
    db_session.add_all([family, genus, species, accession])
    db_session.commit()

    # simulate the ResultsView: the species row has been expanded, so its
    # `accessions` collection is loaded and backs the accession's child row.
    assert accession in species.accessions

    # simulate: right-click on the accession row -> "Edit".
    editor = GenericModelViewPresenterEditor(accession)
    try:
        # the object handed to the editor is still the one attached to the
        # ResultsView's own session and must be left untouched.
        assert object_session(accession) is db_session
        assert accession.species is species, (
            "opening the editor must not clear the `species` backref of "
            "the accession still displayed by the ResultsView"
        )
        assert accession in species.accessions, (
            "opening the editor must not remove the accession from its "
            "parent's already-loaded `accessions` collection"
        )
    finally:
        editor.session.close()
