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


# this file contains tests spanning several editor classes, all
# related to the same behaviour: when the user hits RESPONSE_NEXT or
# RESPONSE_OK_AND_ADD, the current object being edited is committed to
# the session, and a new editor is spawned, initialized as needed.


from unittest.mock import patch
import pytest
from bauble.plugins.plants.family import Family, FamilyEditor
from bauble.plugins.plants.genus import Genus, GenusEditor
from bauble.plugins.plants.species_model import Species
from bauble.plugins.plants.species_editor import SpeciesEditor
from sqlalchemy import select


## RESPONSE_NEXT (genus & species)

def test_genus_editor_next_preserves_family(db_session):
    family = Family(epithet="Amaranthaceae")
    db_session.add(family)
    db_session.commit()

    editor = GenusEditor(Genus(family=family))
    editor.view.widget_set_value("gen_genus_entry", "Salsola")
    assert editor.presenter.is_dirty()

    with patch("bauble.plugins.plants.genus.GenusEditor") as next_editor:
        next_editor.return_value.start.return_value = None
        result = editor.handle_response(editor.RESPONSE_NEXT)
        assert result is True
        next_genus = next_editor.call_args.args[0]
        assert next_genus.family.id == family.id


def test_species_editor_next_preserves_genus(db_session):
    family = Family(epithet="Amaranthaceae")
    genus = Genus(family=family, epithet="Salsola")
    db_session.add(family)
    db_session.add(genus)
    db_session.commit()

    editor = SpeciesEditor(Species(genus=genus))
    editor.view.widget_set_value("sp_species_entry", "kali")
    assert editor.presenter.is_dirty()

    with patch("bauble.plugins.plants.species_editor.SpeciesEditor") as next_editor:
        next_editor.return_value.start.return_value = None
        result = editor.handle_response(editor.RESPONSE_NEXT)
        assert result is True
        next_species = next_editor.call_args.args[0]
        assert next_species.genus.id == genus.id


# RESPONSE_OK_AND_ADD (family-> genus-> species-> accession)

def test_family_editor_ok_and_add_uses_family(db_session):
    # no database preparation before creation of editor
    editor = FamilyEditor()
    editor.view.widget_set_value("fam_family_entry", "Amaranthaceae")
    assert editor.presenter.is_dirty()

    with patch("bauble.plugins.plants.genus.GenusEditor") as next_editor:
        next_editor.return_value.start.return_value = None
        result = editor.handle_response(editor.RESPONSE_OK_AND_ADD)
        assert result is True
        family = (db_session.execute(select(Family)
                                     .where(Family.epithet == "Amaranthaceae"))
                  .scalars()
                  .first())
        assert family is not None
        # new genus receives family from editor
        new_genus = next_editor.call_args.args[0]
        assert new_genus.family.id == family.id


def test_genus_editor_ok_and_add_uses_genus(db_session):
    family = Family(epithet="Amaranthaceae")
    db_session.add(family)
    db_session.commit()

    editor = GenusEditor(Genus(family=family))
    editor.view.widget_set_value("gen_genus_entry", "Salsola")
    assert editor.presenter.is_dirty()

    with patch("bauble.plugins.plants.species_editor.SpeciesEditor") as next_editor:
        next_editor.return_value.start.return_value = None
        result = editor.handle_response(editor.RESPONSE_OK_AND_ADD)
        assert result is True
        genus = (db_session.execute(select(Genus)
                                    .where(Genus.epithet == "Salsola"))
                 .scalars()
                 .first())
        assert genus is not None
        # new species receives genus from editor
        new_species = next_editor.call_args.args[0]
        assert new_species.genus.id == genus.id


def test_species_editor_ok_and_add_uses_species(db_session):
    pytest.importorskip("bauble.plugins.garden.accession_editor")
    family = Family(epithet="Amaranthaceae")
    genus = Genus(family=family, epithet="Salsola")
    db_session.add(family)
    db_session.add(genus)
    db_session.commit()

    editor = SpeciesEditor(Species(genus=genus))
    editor.view.widget_set_value("sp_species_entry", "kali")
    assert editor.presenter.is_dirty()

    with patch("bauble.plugins.garden.accession_editor.AccessionEditor") as next_editor:
        next_editor.return_value.start.return_value = None
        result = editor.handle_response(editor.RESPONSE_OK_AND_ADD)
        assert result is True
        species = (db_session.execute(select(Species)
                                      .where(Species.epithet == "kali")
                                      .join(Genus)
                                      .where(Genus.epithet == "Salsola"))
                   .scalars()
                   .first())
        assert species is not None
        new_accession = next_editor.call_args.args[0]
        assert new_accession.species_id == species.id
        
