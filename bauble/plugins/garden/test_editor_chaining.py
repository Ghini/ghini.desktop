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
from bauble.plugins.plants.family import Family
from bauble.plugins.plants.genus import Genus
from bauble.plugins.plants.species_model import Species

from bauble.plugins.garden.models.accession import Accession
from bauble.plugins.garden.models.plant import Plant
from bauble.plugins.garden.models.location import Location
from bauble.plugins.garden.accession_editor import AccessionEditor
from bauble.plugins.garden.plant_editor import PlantEditor
from bauble.plugins.garden.location_editor import LocationEditor
from sqlalchemy import select


## we are within the garden plugin (depends on plants)
# RESPONSE_NEXT (accession, plant)

def test_accession_editor_next_preserves_species(db_session):
    family = Family(epithet="Amaranthaceae")
    genus = Genus(family=family, epithet="Salsola")
    species = Species(genus=genus, epithet="kali")
    db_session.add(family)
    db_session.add(genus)
    db_session.add(species)
    db_session.commit()

    editor = AccessionEditor(Accession(species=species))
    editor.view.widget_set_value("acc_code_entry", "2026.0101")
    assert editor.presenter.is_dirty()

    with patch("bauble.plugins.garden.accession_editor.AccessionEditor") as next_editor:
        next_editor.return_value.start.return_value = None
        result = editor.handle_response(editor.RESPONSE_NEXT)
        assert result is True
        next_accession = next_editor.call_args.args[0]
        assert next_accession.species.id == species.id


def test_plant_editor_next_preserves_accession(db_session):
    family = Family(epithet="Amaranthaceae")
    genus = Genus(family=family, epithet="Salsola")
    species = Species(genus=genus, epithet="kali")
    accession = Accession(species=species, code="2026.0101")
    location = Location(code="1")
    db_session.add(family)
    db_session.add(genus)
    db_session.add(species)
    db_session.add(accession)
    db_session.add(location)
    db_session.commit()

    editor = PlantEditor(Plant(accession=accession))
    editor.view.widget_set_value("plant_code_entry", "1")
    editor.view.widget_set_value("plant_quantity_entry", "1")
    editor.view.widget_set_value("plant_loc_comboentry", "1")
    assert editor.presenter.is_dirty()

    with patch("bauble.plugins.garden.plant_editor.PlantEditor") as next_editor:
        next_editor.return_value.start.return_value = None
        result = editor.handle_response(editor.RESPONSE_NEXT)
        assert result is True
        next_plant = next_editor.call_args.args[0]
        assert next_plant.accession.id == accession.id


## we are within the garden plugin
# RESPONSE_OK_AND_ADD (accession->plant; location->plant)

def test_accession_editor_ok_and_add_sends_accession_to_plant_editor(db_session):
    family = Family(epithet="Amaranthaceae")
    genus = Genus(family=family, epithet="Salsola")
    species = Species(genus=genus, epithet="kali")
    location = Location(code="1")
    db_session.add(family)
    db_session.add(genus)
    db_session.add(species)
    db_session.add(location)
    db_session.commit()

    editor = AccessionEditor(Accession(species=species))
    editor.view.widget_set_value("acc_code_entry", "2026.0101")
    assert editor.presenter.is_dirty()

    with patch("bauble.plugins.garden.PlantEditor") as next_editor:
        next_editor.return_value.start.return_value = None
        result = editor.handle_response(editor.RESPONSE_OK_AND_ADD)
        assert result is True
        accession = (db_session.execute(select(Accession)
                                        .where(Accession.code == "2026.0101"))
                     .scalars()
                     .first())
        assert accession is not None
        new_plant = next_editor.call_args.args[0]
        assert new_plant.accession.id == accession.id


def test_location_editor_ok_and_add_sends_location_to_plant_editor(db_session):
    family = Family(epithet="Amaranthaceae")
    genus = Genus(family=family, epithet="Salsola")
    species = Species(genus=genus, epithet="kali")
    accession = Accession(species=species, code="2026.0101")
    db_session.add(family)
    db_session.add(genus)
    db_session.add(species)
    db_session.add(accession)
    db_session.commit()

    editor = LocationEditor()
    editor.view.widget_set_value("loc_name_entry", "1")
    editor.view.widget_set_value("loc_code_entry", "1")
    assert editor.presenter.is_dirty()

    with patch("bauble.plugins.garden.PlantEditor") as next_editor:
        next_editor.return_value.start.return_value = None
        result = editor.handle_response(editor.RESPONSE_OK_AND_ADD)
        assert result is True
        location = (db_session.execute(select(Location)
                                       .where(Location.code == "1"))
                    .scalars()
                    .first())
        assert location is not None
        new_plant = next_editor.call_args.args[0]
        assert new_plant.location.id == location.id
