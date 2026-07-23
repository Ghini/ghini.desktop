# Copyright 2026 Mario Frasca <mario@anche.no>.
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

from unittest.mock import patch
from bauble.gtkinit import Gtk
from bauble.plugins.garden.institution import InstitutionEditor


def test_institution_editor_ok_writes_and_commits():
    editor = InstitutionEditor()
    editor.view.widget_set_value("inst_name", "Orto Botanico Test")

    with (patch.object(editor.model, "write") as mock_write,
          patch.object(editor.presenter, "commit_changes")
          as mock_commit):
        result = editor.handle_response(Gtk.ResponseType.OK)

    assert result is True
    mock_write.assert_called_once()
    mock_commit.assert_called_once()


def test_institution_editor_cancel_rolls_back():
    editor = InstitutionEditor()

    with (patch.object(editor.presenter.session, "in_transaction", return_value=True),
          patch.object(editor.presenter.session, "rollback")
          as mock_rollback):
        result = editor.handle_response(Gtk.ResponseType.CANCEL)

    assert result is False
    mock_rollback.assert_called_once()
