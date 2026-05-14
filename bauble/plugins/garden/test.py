# Copyright 2008-2010 Brett Adams
# Copyright 2015,2017 Mario Frasca <mario@anche.no>.
# Copyright 2017 Jardín Botánico de Quito
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


import glob
import logging
import os
import sqlite3
import tempfile
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

import pytest
from bauble.meta import BaubleMeta
from bauble.plugins.garden.exporttopocket import ExportToPocketThread, create_pocket
from bauble.plugins.garden.institution import Institution, InstitutionPresenter
from bauble.plugins.garden.models import Accession as Accession
from bauble.plugins.garden.models import AccessionNote as AccessionNote
from bauble.plugins.garden.models import Collection, Contact, Location, Verification
from bauble.plugins.garden.models import Plant as Plant
from bauble.plugins.garden.models import PlantChange as PlantChange
from bauble.plugins.garden.models import PlantNote as PlantNote
from bauble.plugins.garden.models import (
    Propagation,
    PropCutting,
    PropCuttingRooted,
    PropSeed,
    Source,
)
from bauble.plugins.garden.models import Voucher as Voucher
from bauble.plugins.garden.plant_editor import branch_callback, is_code_unique
from bauble.plugins.plants.family import Family
from bauble.plugins.plants.genus import Genus
from bauble.plugins.plants.species_model import Species
from bauble.plugins.plants.species_model import _remove_zws as remove_zws
from bauble.test import check_dupids, update_gui
from bauble.utils import ilike
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

accession_test_data: Any
default_cutting_values: Any
from bauble.gtkinit import Gtk

logger: Any = logging.getLogger(__name__)

prefs_testing: bool = True

# Test data for different models
accession_test_data = (
    {"id": 1, "code": "2001.1", "species_id": 1},
    {"id": 2, "code": "2001.2", "species_id": 2, "source_type": "Collection"},
)

plant_test_data: Any = (
    {"id": 1, "code": "1", "accession_id": 1, "location_id": 1, "quantity": 1},
    {"id": 2, "code": "1", "accession_id": 2, "location_id": 1, "quantity": 1},
    {"id": 3, "code": "2", "accession_id": 2, "location_id": 1, "quantity": 1},
)

location_test_data: Any = (
    {"id": 1, "name": "Somewhere Over The Rainbow", "code": "RBW"},
)

geographic_area_test_data: Any = [{"id": 1, "name": "Somewhere"}]

collection_test_data: Any = (
    {
        "id": 1,
        "accession_id": 2,
        "locale": "Somewhere",
        "geographic_area_id": 1,
    },
)


# Fixtures for test data setup
@pytest.fixture(scope="module")
def test_data_setup(db_session) -> None:
    from bauble.plugins.garden.institution import Institution
    from bauble.plugins.plants.geography import GeographicArea

    # Insert test data
    for cls, data in [
        (Accession, accession_test_data),
        (Plant, plant_test_data),
        (Location, location_test_data),
        (GeographicArea, geographic_area_test_data),
        (Collection, collection_test_data),
    ]:
        db_session.bulk_insert_mappings(cls, data)

    # Add a test institution
    institution = Institution(
        name="TestInstitution",
        technical_contact="TestTechnicalContact Name",
        email="contact@test.com",
        contact="TestContact Name",
        code="TestCode",
    )
    db_session.add(institution)
    if db_session.in_transaction():
        db_session.commit()


# Test for duplicate IDs in Glade files
def test_duplicate_ids() -> None:
    import bauble.plugins.garden as mod

    head, _ = os.path.split(mod.__file__)
    glade_files = glob.glob(os.path.join(head, "*.glade"))
    for file in glade_files:
        assert not check_dupids(file), f"Duplicate IDs found in file: {file}"


@pytest.fixture
def garden_data(db_session):
    """Fixture to set up garden-related data."""
    family = Family(epithet="Cactaceae")
    genus = Genus(family=family, epithet="Echinocactus")
    species = Species(genus=genus, sp="grusonii")
    sp2 = Species(genus=genus, sp="texelensis")
    db_session.add_all([family, genus, species, sp2])
    if db_session.in_transaction():
        db_session.commit()
    return {"family": family, "genus": genus, "species": species, "sp2": sp2}


@pytest.fixture
def plant_data(db_session, garden_data):
    """Fixture to set up plants for tests."""
    species = garden_data["species"]
    accession = Accession(species=species, code="1")
    location = Location(name="site", code="STE")
    plant = Plant(accession=accession, location=location, code="1", quantity=1)
    db_session.add_all([accession, location, plant])
    if db_session.in_transaction():
        db_session.commit()
    return {"accession": accession, "location": location, "plant": plant}


def test_plant_constraints(db_session, plant_data) -> None:
    """Test that duplicate plant codes with the same accession are not allowed."""
    plant = plant_data["plant"]
    accession = plant_data["accession"]
    location = plant_data["location"]

    # Attempt to add a duplicate plant
    duplicate_plant = Plant(
        accession=accession, location=location, code=plant.code, quantity=1
    )
    db_session.add(duplicate_plant)
    with pytest.raises(IntegrityError):
        if db_session.in_transaction():
            db_session.commit()
    if db_session.in_transaction():
        db_session.rollback()


def test_plant_duplicate(db_session, plant_data) -> None:
    """Test duplication of a plant with notes and changes."""
    accession = plant_data["accession"]
    location = plant_data["location"]

    # Create a new plant
    new_plant = Plant(accession=accession, location=location, code="2", quantity=52)
    note = PlantNote(note="some note", date=date.today())
    note.plant = new_plant
    change = PlantChange(from_location=location, to_location=location, quantity=1)
    change.plant = new_plant
    db_session.add(new_plant)
    if db_session.in_transaction():
        db_session.commit()

    # Duplicate the plant
    duplicate = new_plant.duplicate(code="3")
    assert duplicate.notes == []
    assert duplicate.changes == []
    assert new_plant.notes
    assert new_plant.changes
    if db_session.in_transaction():
        db_session.commit()


def test_search_view_markup_pair(db_session, plant_data) -> None:
    """Test the search view markup pair for living and dead plants."""
    accession = plant_data["accession"]
    location = plant_data["location"]

    # Living plant
    living_plant = Plant(accession=accession, location=location, code="2", quantity=52)
    db_session.add(living_plant)
    assert living_plant.search_view_markup_pair() == (
        '1.2 <span foreground="#555555" size="small" weight="light">- 52 alive in (STE) site</span>',
        "<i>Echinocactus</i> <i>grusonii</i>",
    )

    # Dead plant
    dead_plant = Plant(accession=accession, location=location, code="2", quantity=0)
    db_session.add(dead_plant)
    assert dead_plant.search_view_markup_pair() == (
        '<span foreground="#9900ff">1.2</span>',
        "<i>Echinocactus</i> <i>grusonii</i>",
    )


@pytest.mark.skip(reason="opens the interactive Plant Editor split-mode dialog")
def test_branch_callback(db_session, plant_data) -> None:
    """Test the branch callback functionality."""
    plant = plant_data["plant"]
    plant.quantity = 5
    if db_session.in_transaction():
        db_session.commit()

    # Branch plant
    branch_callback([plant])
    branched_plant = (
        db_session.execute(select(Plant).where(Plant.code != "1")).scalars().first()
    )

    db_session.refresh(plant)
    assert plant.quantity == 5 - branched_plant.quantity
    assert branched_plant.changes[0].quantity == branched_plant.quantity


def test_is_code_unique(plant_data) -> None:
    """Test the uniqueness of plant codes."""
    plant = plant_data["plant"]
    assert not is_code_unique(plant, "1")
    assert is_code_unique(plant, "01")
    assert not is_code_unique(plant, "1-2")
    assert not is_code_unique(plant, "01-2")


def test_living_plant_has_no_date_of_death(plant_data) -> None:
    """Test that a living plant has no date of death."""
    plant = plant_data["plant"]
    assert plant.date_of_death is None


def test_setting_quantity_to_zero_defines_date_of_death(db_session, plant_data) -> None:
    """Test that setting quantity to zero defines the date of death."""
    plant = plant_data["plant"]
    change = PlantChange()
    change.plant = plant
    change.from_location = plant.location
    change.quantity = plant.quantity
    db_session.add(change)

    # Set quantity to zero and test date of death
    plant.quantity = 0
    db_session.flush()
    assert plant.date_of_death is not None


def test_deleting_plant_change_does_not_delete_plant(db_session, plant_data) -> None:
    """Plant changes are owned by plants, not the other way around."""
    plant = plant_data["plant"]
    change = PlantChange(plant=plant, from_location=plant.location, quantity=1)
    db_session.add(change)
    if db_session.in_transaction():
        db_session.commit()

    plant_id = plant.id
    change_id = change.id
    db_session.delete(change)
    if db_session.in_transaction():
        db_session.commit()

    assert db_session.get(PlantChange, change_id) is None
    assert db_session.get(Plant, plant_id) is not None


def test_deleting_source_does_not_delete_contact(db_session, setup_accession) -> None:
    """Sources may refer to reusable contacts without owning them."""
    accession = setup_accession["accession"]
    contact = Contact(name="Reusable contact")
    source = Source(accession=accession, source_detail=contact)
    db_session.add(source)
    if db_session.in_transaction():
        db_session.commit()

    contact_id = contact.id
    source_id = source.id
    db_session.delete(source)
    if db_session.in_transaction():
        db_session.commit()

    assert db_session.get(Source, source_id) is None
    assert db_session.get(Contact, contact_id) is not None


def test_deleting_contact_does_not_delete_source(db_session, setup_accession) -> None:
    """Contacts are reusable source details and do not own source rows."""
    accession = setup_accession["accession"]
    contact = Contact(name="Reusable contact")
    source = Source(accession=accession, source_detail=contact)
    db_session.add(source)
    if db_session.in_transaction():
        db_session.commit()

    contact_id = contact.id
    source_id = source.id
    db_session.delete(contact)
    if db_session.in_transaction():
        db_session.commit()

    source = db_session.get(Source, source_id)
    assert db_session.get(Contact, contact_id) is None
    assert source is not None
    assert source.source_detail is None


def test_deleting_propagation_does_not_delete_plant(db_session, setup_plants) -> None:
    """Propagations may be deleted without deleting their source plant."""
    plant = setup_plants[0]
    propagation = Propagation(plants=[plant], prop_type="UnrootedCutting")
    db_session.add(propagation)
    if db_session.in_transaction():
        db_session.commit()

    plant_id = plant.id
    propagation_id = propagation.id
    db_session.delete(propagation)
    if db_session.in_transaction():
        db_session.commit()

    assert db_session.get(Propagation, propagation_id) is None
    assert db_session.get(Plant, plant_id) is not None


def test_propagation_can_reference_multiple_plants(db_session, setup_plants) -> None:
    """A propagation may use material from more than one source plant."""
    plants = setup_plants[:2]
    propagation = Propagation(plants=plants, prop_type="UnrootedCutting")
    db_session.add(propagation)
    if db_session.in_transaction():
        db_session.commit()

    propagation_id = propagation.id
    db_session.expire_all()

    propagation = db_session.get(Propagation, propagation_id)
    assert {plant.id for plant in propagation.plants} == {plant.id for plant in plants}


def test_deleting_source_plant_does_not_delete_shared_propagation(
    db_session, setup_plants
) -> None:
    """Plants do not own shared propagation records through the association table."""
    plants = setup_plants[:2]
    propagation = Propagation(plants=plants, prop_type="UnrootedCutting")
    db_session.add(propagation)
    if db_session.in_transaction():
        db_session.commit()

    propagation_id = propagation.id
    deleted_plant_id = plants[0].id
    remaining_plant_id = plants[1].id
    db_session.delete(plants[0])
    if db_session.in_transaction():
        db_session.commit()

    propagation = db_session.get(Propagation, propagation_id)
    assert db_session.get(Plant, deleted_plant_id) is None
    assert propagation is not None
    assert {plant.id for plant in propagation.plants} == {remaining_plant_id}


def test_source_plant_propagation_is_scalar(db_session, setup_accession, setup_plants):
    """A source references one plant-propagation trial, not a list of trials."""
    accession = setup_accession["accession"]
    propagation = Propagation(plants=[setup_plants[0]], prop_type="UnrootedCutting")
    source = Source(accession=accession, plant_propagation=propagation)
    db_session.add_all([propagation, source])
    if db_session.in_transaction():
        db_session.commit()

    source_id = source.id
    propagation_id = propagation.id
    db_session.expire_all()

    source = db_session.get(Source, source_id)
    propagation = db_session.get(Propagation, propagation_id)
    assert source.plant_propagation is propagation
    assert source in propagation.used_source


# Constants for test data
default_cutting_values = {
    "cutting_type": "Nodal",
    "length": 2,
    "length_unit": "mm",
    "tip": "Intact",
    "leaves": "Intact",
    "leaves_reduced_pct": 0,
    "flower_buds": "None",
    "wound": "Single",
    "fungicide": "Physan",
    "media": "standard mix",
    "container": '4" pot',
    "hormone": "Auxin powder",
    "cover": "Poly cover",
    "location": "Mist frame",
    "bottom_heat_temp": 65,
    "bottom_heat_unit": "F",
    "rooted_pct": 90,
}

default_seed_values: Any = {
    "pretreatment": "Soaked in peroxide solution",
    "nseeds": 24,
    "date_sown": date(2017, 1, 1),
    "container": "tray",
    "media": "standard mix",
    "covered": "lightly",
    "location": "mist tent",
    "moved_from": "mist tent",
    "moved_to": "hardening table",
    "moved_date": date(2017, 1, 15),
    "germ_date": date(2017, 2, 1),
    "germ_pct": 99,
    "nseedlings": 23,
    "date_planted": date(2017, 2, 8),
}


@pytest.fixture
def setup_species(db_session):
    """Fixture to set up species-related data."""
    family = Family(epithet="Cactaceae")
    genus = Genus(family=family, epithet="Echinocactus")
    species = Species(genus=genus, sp="grusonii")
    sp2 = Species(genus=genus, sp="texelensis")
    db_session.add_all([family, genus, species, sp2])
    if db_session.in_transaction():
        db_session.commit()
    return {"family": family, "genus": genus, "species": species, "sp2": sp2}


@pytest.fixture
def setup_accession(db_session, setup_species):
    """Fixture to set up an accession and related data."""
    species = setup_species["species"]
    accession = Accession(species=species, code="1")
    db_session.add(accession)
    if db_session.in_transaction():
        db_session.commit()
    return {"accession": accession, "species": species}


@pytest.fixture
def setup_plants(db_session, setup_accession):
    """Fixture to set up plants for propagation tests."""
    accession = setup_accession["accession"]
    location = Location(name="Propagation Site", code="PROP")
    db_session.add(location)
    plants = [
        Plant(accession=accession, code=str(i), quantity=1, location=location)
        for i in range(1, 4)
    ]
    db_session.add_all(plants)
    if db_session.in_transaction():
        db_session.commit()
    return plants


def test_cutting_property(db_session, setup_plants) -> None:
    """Test cutting property for propagations."""
    plant = setup_plants[0]
    prop = Propagation(plants=[plant], prop_type="UnrootedCutting")
    cutting = PropCutting(**default_cutting_values)
    cutting.propagation = prop

    # Add rooted cutting
    rooted = PropCuttingRooted(quantity=5, date=date.today())
    rooted.cutting = cutting

    db_session.add(rooted)
    if db_session.in_transaction():
        db_session.commit()

    # Verify rooted cutting is associated
    assert rooted in prop._cutting.rooted

    # Delete cutting and associated rooted objects
    rooted_id = rooted.id
    cutting_id = cutting.id
    prop._cutting = None
    if db_session.in_transaction():
        db_session.commit()

    assert (
        not db_session.execute(select(PropCutting).filter_by(id=cutting_id))
        .scalars()
        .first()
    )
    assert (
        not db_session.execute(select(PropCuttingRooted).filter_by(id=rooted_id))
        .scalars()
        .first()
    )


def test_voucher_management(db_session, setup_accession) -> None:
    """Test voucher functionality."""
    accession = setup_accession["accession"]
    voucher = Voucher(herbarium="ABC", code="1234567", accession=accession)
    db_session.add(voucher)
    if db_session.in_transaction():
        db_session.commit()

    # Remove voucher and verify deletion
    voucher_id = voucher.id
    accession.vouchers.remove(voucher)
    if db_session.in_transaction():
        db_session.commit()
    assert (
        not db_session.execute(select(Voucher).filter_by(id=voucher_id))
        .scalars()
        .first()
    )

    # Test voucher deletion when disassociated
    voucher = Voucher(herbarium="ABC", code="1234567", accession=accession)
    db_session.add(voucher)
    if db_session.in_transaction():
        db_session.commit()

    acc_id = voucher.accession.id
    voucher.accession = None
    if db_session.in_transaction():
        db_session.commit()
    assert (
        not db_session.execute(select(Voucher).filter_by(id=voucher_id))
        .scalars()
        .first()
    )
    assert db_session.execute(select(Accession).filter_by(id=acc_id)).scalars().first()


def test_propagation_get_summary_cutting(db_session, setup_plants) -> None:
    """Test summary generation for cutting propagations."""
    plant = setup_plants[0]
    prop = Propagation(plants=[plant], prop_type="UnrootedCutting")
    cutting = PropCutting(**default_cutting_values)
    cutting.propagation = prop
    db_session.add(prop)
    if db_session.in_transaction():
        db_session.commit()

    summary = prop.get_summary()
    expected = (
        "Cutting; Cutting type: Nodal; Length: 2mm; Tip: Intact; Leaves: Intact; "
        "Flower buds: None; Wounded: Singled; Fungal soak: Physan; Hormone treatment: Auxin powder; "
        'Bottom heat: 65°F; Container: 4" pot; Media: standard mix; Location: Mist frame; '
        "Cover: Poly cover; Rooted: 90%"
    )
    assert summary == expected


@pytest.fixture
def setup_accession2(db_session, setup_species):
    """Fixture to create an accession and related entities."""
    species = setup_species["species"]
    accession = Accession(species=species, code="1")
    db_session.add(accession)
    if db_session.in_transaction():
        db_session.commit()
    return {"accession": accession, "species": species}


@pytest.fixture
def setup_location(db_session):
    """Fixture to create a location."""
    location = Location(name="Some Site", code="STE")
    db_session.add(location)
    if db_session.in_transaction():
        db_session.commit()
    return location


def test_source_propagation_cleanup(db_session, setup_accession2) -> None:
    """Test cleanup of propagation when disassociated from a source."""
    accession = setup_accession2["accession"]
    source = Source(accession=accession)
    propagation = Propagation(prop_type="Seed", source=source)
    seed = PropSeed(**default_seed_values, propagation=propagation)
    cutting = PropCutting(**default_cutting_values, propagation=propagation)

    db_session.add_all([source, propagation, seed, cutting])
    if db_session.in_transaction():
        db_session.commit()

    # Validate initial data
    assert propagation.id is not None
    assert seed.id is not None
    assert cutting.id is not None

    # Remove propagation and validate cleanup
    source.propagation = None
    if db_session.in_transaction():
        db_session.commit()
    assert (
        db_session.execute(select(Propagation).filter_by(id=propagation.id)).first()
        is None
    )
    assert db_session.execute(select(PropSeed).filter_by(id=seed.id)).first() is None
    assert (
        db_session.execute(select(PropCutting).filter_by(id=cutting.id)).first() is None
    )


def test_accession_species_str(db_session, setup_accession2) -> None:
    """Test species string generation for accessions."""
    accession = setup_accession2["accession"]
    sp_str = accession.species_str()
    expected = "Echinocactus grusonii"
    assert remove_zws(sp_str) == expected

    accession.id_qual = "cf."
    accession.id_qual_rank = "sp"
    sp_str = accession.species_str(markup=True)
    expected = "<i>Echinocactus</i> cf. <i>grusonii</i>"
    assert remove_zws(sp_str) == expected


def test_accession_delete_cascades(
    db_session, setup_accession2, setup_location
) -> None:
    """Test cascading delete of accession and dependent entities."""
    accession = setup_accession2["accession"]
    location = setup_location
    plant = Plant(accession=accession, location=location, code="1", quantity=1)
    db_session.add(plant)
    if db_session.in_transaction():
        db_session.commit()

    # Ensure plant exists
    plant_id = plant.id
    assert db_session.execute(select(Plant).filter_by(id=plant_id)).first() is not None

    # Delete accession and ensure plant is also deleted
    db_session.delete(accession)
    if db_session.in_transaction():
        db_session.commit()
    assert db_session.execute(select(Plant).filter_by(id=plant_id)).first() is None


def test_accession_unique_constraint(db_session, setup_accession2) -> None:
    """Test unique constraint on accession codes."""
    species = setup_accession2["species"]
    accession = Accession(species=species, code="1")
    db_session.add(accession)
    with pytest.raises(IntegrityError):
        if db_session.in_transaction():
            db_session.commit()


def test_voucher_management2(db_session, setup_accession2):
    """Test addition and removal of vouchers."""
    accession = setup_accession2["accession"]
    voucher = Voucher(herbarium="ABC", code="1234567", accession=accession)
    db_session.add(voucher)
    if db_session.in_transaction():
        db_session.commit()

    # Verify voucher exists
    assert voucher.id is not None

    # Remove voucher and verify deletion
    voucher_id = voucher.id
    accession.vouchers.remove(voucher)
    if db_session.in_transaction():
        db_session.commit()
    assert db_session.execute(select(Voucher).filter_by(id=voucher_id)).first() is None


def test_legacy_nullable_garden_fields(db_session, setup_accession2) -> None:
    """SQLAlchemy 2 annotations should preserve legacy nullable columns."""
    accession = setup_accession2["accession"]
    species = setup_accession2["species"]
    location = Location(code="NULLABLE")
    contact = Contact()
    verification = Verification(
        verifier="tester",
        date=date.today(),
        accession=accession,
        species=species,
        prev_species=species,
        level=0,
    )
    db_session.add_all([location, contact, verification])
    db_session.commit()

    assert location.name is None
    assert contact.name is None
    assert contact.description == ""
    assert verification.reference is None
    assert verification.notes is None


def test_legacy_nullable_propagation_fields(db_session) -> None:
    """Propagation detail records should preserve legacy nullable columns."""
    propagation = Propagation(prop_type="Seed")
    cutting = PropCutting(propagation=propagation)
    seed = PropSeed(
        propagation=propagation,
        nseeds=1,
        date_sown=date.today(),
    )
    db_session.add_all([propagation, cutting, seed])
    db_session.commit()

    assert cutting.id is not None
    assert cutting.tip is None
    assert cutting.fungicide is None
    assert cutting.bottom_heat_temp is None
    assert cutting.rooted_pct is None
    assert seed.id is not None
    assert seed.pretreatment is None
    assert seed.container is None
    assert seed.moved_date is None
    assert seed.nseedlings is None


def test_seed_propagation_clean_tolerates_missing_cutting(db_session) -> None:
    """Seed cleanup should not require an inactive cutting detail row."""
    propagation = Propagation(prop_type="Seed")
    propagation._seed = PropSeed(nseeds=12, date_sown=date.today())
    db_session.add(propagation)

    propagation.clean()

    assert propagation._seed is not None
    assert propagation._cutting is None


def test_propagation_box_tolerates_missing_date() -> None:
    """Propagation tab rows should render even before a date is entered."""
    from bauble.plugins.garden.propagation_editor import PropagationHandler

    propagation = Propagation(prop_type="Seed")
    propagation._seed = PropSeed(nseeds=12, date_sown=date.today())

    box = PropagationHandler().create_propagation_box(propagation)

    assert box is not None


@pytest.mark.skip(reason="opens the interactive Location Editor dialog")
def test_location_editor_interactions(db_session, setup_location) -> None:
    """Test interactions with the location editor."""
    from bauble.plugins.garden.location_editor import LocationEditor

    location = setup_location
    editor = LocationEditor(model=location)
    widgets = editor.presenter.view.widgets

    # Verify initial widget values
    assert widgets.loc_name_entry.get_text() == location.name
    assert widgets.loc_code_entry.get_text() == location.code

    # Modify name and verify buttons are sensitive
    widgets.loc_name_entry.set_text("New Site")
    update_gui()
    assert widgets.loc_ok_button.set_sensitive

    # Clear code and verify buttons are not sensitive
    widgets.loc_code_entry.set_text("")
    update_gui()
    assert not widgets.loc_ok_button.get_sensitive()

    # Cleanup editor
    editor.handle_response(Gtk.ResponseType.OK)
    editor.session.close()


@pytest.fixture
def setup_accession3(db_session, setup_species):
    """Fixture to create an accession with a source."""
    species = setup_species["species"]
    accession = Accession(code="2001.0002", species=species, source=Source())
    db_session.add(accession)
    if db_session.in_transaction():
        db_session.commit()
    return accession


@pytest.fixture
def setup_collection(db_session, setup_accession3):
    """Fixture to create a collection associated with an accession."""
    collection = Collection(locale="some location", source=setup_accession3.source)
    db_session.add(collection)
    if db_session.in_transaction():
        db_session.commit()
    return collection


def test_collection_search_view_markup_pair(db_session, setup_collection) -> None:
    """Test the search view markup pair for collections."""
    collection = setup_collection
    expected = (
        "2001.0002 - <small>Echinocactus grusonii</small>",
        "Collection at some location",
    )
    assert collection.search_view_markup_pair() == expected


@pytest.fixture
def setup_institution():
    """Fixture to create a new institution."""
    institution = Institution()
    institution.name = "Ghini"
    return institution


def test_institution_properties(db_session, setup_institution) -> None:
    """Test that an institution has all required attributes."""
    institution = setup_institution
    attributes = [
        "name",
        "abbreviation",
        "code",
        "contact",
        "technical_contact",
        "email",
        "tel",
        "fax",
        "address",
    ]
    for attr in attributes:
        assert hasattr(institution, attr)


def test_institution_initialization(db_session) -> None:
    """Test initialization of institution fields in metadata."""
    institution = Institution()
    institution.name = "Ghini"
    institution.write()

    fields = (
        db_session.execute(select(BaubleMeta).where(ilike(BaubleMeta.name, "inst_%")))
        .scalars()
        .all()
    )
    assert {field.name for field in fields} == {"inst_name"}


def test_institution_write_none_stays_none(db_session) -> None:
    """Test that writing None values to an institution keeps them as None."""
    institution = Institution()
    institution.name = "Ghini"
    institution.email = "bauble@anche.no"
    institution.write()

    fields = (
        db_session.execute(select(BaubleMeta).where(ilike(BaubleMeta.name, "inst_%")))
        .scalars()
        .all()
    )
    field_values = {f.name[5:]: f.value for f in fields if f.value is not None}
    assert field_values["name"] == "Ghini"
    assert field_values["email"] == "bauble@anche.no"
    assert len(field_values) == 2


def test_institution_presenter_initialization() -> None:
    """Test creation of an InstitutionPresenter."""
    from bauble.editor import MockView

    view = MockView()
    institution = Institution()
    institution.name = "Test Institution"
    presenter = InstitutionPresenter(institution, view)
    assert presenter.view == view


def test_institution_presenter_empty_name_is_a_problem() -> None:
    """Test that an empty institution name is flagged as a problem."""
    from bauble.editor import MockView

    view = MockView()
    institution = Institution()
    institution.name = ""
    InstitutionPresenter(institution, view)
    assert "add_box" in view.invoked
    assert len(view.boxes) == 1


def test_institution_presenter_invalid_email_blocks_registration() -> None:
    """Test that an invalid email prevents registration."""
    from bauble.editor import MockView

    view = MockView(sensitive={"inst_register": None, "inst_ok": None})
    institution = Institution()
    institution.name = "bauble"
    institution.email = "invalid_email"
    InstitutionPresenter(institution, view)
    assert not view.widget_get_sensitive("inst_register")


def test_institution_presenter_valid_email_allows_registration() -> None:
    """Test that a valid email allows registration."""
    from bauble.editor import MockView

    view = MockView(sensitive={"inst_register": None, "inst_ok": None})
    institution = Institution()
    institution.name = "bauble"
    institution.email = "bauble@anche.no"
    InstitutionPresenter(institution, view)
    assert view.widget_get_sensitive("inst_register")


def test_institution_presenter_registration_logs_info() -> None:
    """Test that registration logs information."""
    from functools import partial

    from bauble.editor import MockView
    from bauble.test import mockfunc
    from bauble.utils import desktop

    invoked = []
    desktop.open = partial(mockfunc, name="desktop.open", caller=invoked.append)

    view = MockView(sensitive={"inst_register": None, "inst_ok": None})
    institution = Institution()
    institution.name = "Ghini"
    presenter = InstitutionPresenter(institution, view)
    presenter.on_inst_register_clicked()

    assert not invoked
    assert not view.widget_get_sensitive("inst_register")


@pytest.fixture
def conversion_test_data():
    return (
        # (DMS, DEG_MIN_DEC, DEG_DEC, UTM)
        (
            (("N", 17, 21, Decimal(59)), ("W", 89, 1, 41)),
            (
                (Decimal(17), Decimal("21.98333333")),
                (Decimal(-89), Decimal("1.68333333")),
            ),
            (Decimal("17.366389"), Decimal("-89.028056")),
        ),
    )


@pytest.fixture
def parse_lat_lon_data():
    return [
        (("N", "17 21 59"), Decimal("17.366389")),
        (("N", "17.03656"), Decimal("17.03656")),
    ]


def test_dms_to_decimal(conversion_test_data) -> None:
    """Test converting DMS to decimal degrees."""
    from bauble.plugins.garden.models import dms_to_decimal

    for data in conversion_test_data:
        dms, _, decimal_deg = data[:3]
        lat = dms_to_decimal(*dms[0])
        lon = dms_to_decimal(*dms[1])
        assert round(lat, 6) == round(decimal_deg[0], 6)
        assert round(lon, 6) == round(decimal_deg[1], 6)


def test_decimal_to_dms(conversion_test_data) -> None:
    """Test converting decimal degrees to DMS."""
    from bauble.plugins.garden.models import latitude_to_dms, longitude_to_dms

    for data in conversion_test_data:
        dms, _, decimal_deg = data[:3]
        lat_dms = latitude_to_dms(decimal_deg[0])
        lon_dms = longitude_to_dms(decimal_deg[1])
        assert lat_dms[:3] == dms[0][:3]
        assert lon_dms[:3] == dms[1][:3]


def test_parse_lat_lon(parse_lat_lon_data) -> None:
    """Test parsing latitude and longitude."""
    from bauble.plugins.garden.source import CollectionPresenter

    parse = CollectionPresenter._parse_lat_lon
    for input_data, expected in parse_lat_lon_data:
        assert parse(*input_data) == expected


def test_accession_retrieve_or_create(db_session, setup_species) -> None:
    """Test retrieval or creation of accessions."""
    species = setup_species["species"]
    acc = Accession.retrieve_or_create(
        db_session,
        {
            "code": "010203",
            "rank": "species",
            "taxon": f"{species.genus.epithet} {species.sp}",
        },
    )
    assert acc.species == species


def test_plant_retrieve_or_create(db_session, setup_accession) -> None:
    """Test retrieval or creation of plants."""
    acc = setup_accession["accession"]
    plant = Plant.retrieve_or_create(
        db_session,
        {
            "accession": acc.code,
            "rank": "species",
            "taxon": f"{acc.species.genus.epithet} {acc.species.sp}",
            "code": "1",
            "quantity": 1,
            "location": "TST",
            "name": "Test Site",
        },
    )
    assert plant.accession == acc


def test_accession_note_retrieve_or_create(db_session, setup_accession) -> None:
    """Test retrieval or creation of accession notes."""
    acc = setup_accession["accession"]
    note = AccessionNote.retrieve_or_create(
        db_session,
        {
            "accession": acc.code,
            "category": "factura",
            "date": "2022-01-01",
            "note": "Test note",
        },
    )
    assert note.accession == acc
    assert note.note == "Test note"


def test_plant_search_strategy(db_session, plant_data) -> None:
    """Test searching plants using PlantSearch strategy."""
    from bauble.search import get_strategy

    strategy = get_strategy("PlantSearch")
    results = strategy.search("1.1", db_session)
    assert len(results) > 0
    plant = results[0]
    assert isinstance(plant, Plant)


def test_location_retrieve_or_create_with_timestamps(db_session) -> None:
    """Test retrieving or creating locations with timestamp fields."""
    Location.retrieve_or_create(
        db_session, {"code": "1", "name": "Test Site", "_created": "2001-12-10"}
    )
    location = Location.retrieve_or_create(db_session, {"code": "1"})
    assert location._created == datetime(2001, 12, 10, tzinfo=timezone.utc)


@pytest.fixture
def setup_pocket_data(db_session, setup_species):
    acc = Accession(species=setup_species["species"], code="010203")
    loc = Location(code="123", name="Pocket Site")
    plt1 = Plant(accession=acc, code="1", quantity=1, location=loc)
    plt2 = Plant(accession=acc, code="2", quantity=1, location=loc)
    db_session.add_all([acc, loc, plt1, plt2])
    if db_session.in_transaction():
        db_session.commit()
    return acc, loc, [plt1, plt2]


def test_export_empty_database() -> None:
    with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
        tmpfile.close()
        create_pocket(tmpfile.name)
        t = ExportToPocketThread(tmpfile.name)
        t.run()

        with sqlite3.connect(tmpfile.name) as cn:
            cursor = cn.cursor()
            for table in ["species", "accession", "plant"]:
                cursor.execute(f"SELECT * FROM {table}")
                assert not cursor.fetchall()

        os.unlink(tmpfile.name)


def test_export_two_plants(setup_pocket_data) -> None:
    acc, loc, plants = setup_pocket_data
    with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
        tmpfile.close()
        create_pocket(tmpfile.name)
        t = ExportToPocketThread(tmpfile.name)
        t.run()

        with sqlite3.connect(tmpfile.name) as cn:
            cursor = cn.cursor()
            cursor.execute('SELECT * FROM "species"')
            assert len(cursor.fetchall()) == 1
            cursor.execute('SELECT * FROM "accession"')
            assert len(cursor.fetchall()) == 1
            cursor.execute('SELECT * FROM "plant"')
            assert len(cursor.fetchall()) == 2

        os.unlink(tmpfile.name)
