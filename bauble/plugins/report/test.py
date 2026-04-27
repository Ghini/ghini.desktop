#
# Copyright (c) 2005,2006,2007,2008,2009 Brett Adams <brett@belizebotanic.org>
# Copyright (c) 2012-2017 Mario Frasca <mario@anche.no>
# Copyright 2017 Jardín Botánico de Quito
# Copyright (c) 2017 Ross Demuth <rossdemuth123@gmail.com>
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
import logging
import os
from collections.abc import Generator
from typing import Any

import pytest
from bauble.plugins.garden.models import Accession, Contact, Location, Plant, Source
from bauble.plugins.plants import Family, Genus, Species, VernacularName
from bauble.plugins.report import get_pertinent_objects
from bauble.plugins.tag import Tag, tag_objects
from bauble.test import check_dupids
from sqlalchemy import select

logger: Any = logging.getLogger(__name__)


# Modify desktop.open here to avoid cyclic import
def disable_desktop_open():
    try:
        import bauble.utils.desktop as desktop

        desktop.open = lambda x: x
    except ImportError:
        logger.error("Failed to import and disable desktop.open")


disable_desktop_open()


# Centralize delayed imports
def dynamic_import(module_name, class_name):
    module = __import__(module_name, fromlist=[class_name])
    return getattr(module, class_name)


@pytest.fixture
def setup_test_data(session) -> Generator[None, None, None]:
    """
    Fixture to set up test data for all test cases.
    """
    fctr = gctr = sctr = actr = pctr = 0
    for _f in range(2):
        fctr += 1
        family = Family(id=fctr, family=f"fam{fctr}")
        session.add(family)
        for _g in range(2):
            gctr += 1
            genus = Genus(id=gctr, family=family, genus=f"gen{gctr}")
            session.add(genus)
            for _s in range(2):
                sctr += 1
                sp = Species(id=sctr, genus=genus, sp=f"sp{sctr}")
                vn = VernacularName(id=sctr, species=sp, name=f"name{sctr}")
                session.add_all([sp, vn])
                for _a in range(2):
                    actr += 1
                    acc = Accession(id=actr, species=sp, code=str(actr))
                    contact = Contact(id=actr, name=f"contact{actr}")
                    source = Source(id=actr, source_detail=contact, accession=acc)
                    session.add_all([acc, source, contact])
                    for _p in range(2):
                        pctr += 1
                        loc = Location(id=pctr, code=str(pctr), name=f"site{pctr}")
                        plant = Plant(
                            id=pctr,
                            accession=acc,
                            location=loc,
                            code=str(pctr),
                            quantity=1,
                        )
                        session.add_all([loc, plant])
    if session.in_transaction():
        session.commit()
    yield
    # Cleanup after tests
    session.execute(select(Family)).scalars().delete()
    session.execute(select(Tag)).scalars().delete()
    if session.in_transaction():
        session.commit()


def test_duplicate_ids() -> None:
    """
    Test for duplicate IDs for all .glade files in the gardens plugin.
    """
    import glob

    import bauble.plugins.report as mod

    head, _ = os.path.split(mod.__file__)
    files = (
        glob.glob(os.path.join(head, "*.glade"))
        + glob.glob(os.path.join(head, "mako", "*.glade"))
        + glob.glob(os.path.join(head, "xsl", "*.glade"))
    )
    for file in files:
        assert not check_dupids(file)


@pytest.mark.usefixtures("setup_test_data")
class TestReport:
    def test_no_objects_in_family_note(self, session) -> None:
        family = session.execute(select(Family)).scalars().first()
        from bauble.error import BaubleError
        from bauble.plugins.plants.family import FamilyNote

        fn = FamilyNote(family=family, note="empty")
        session.add(fn)
        session.flush()

        with pytest.raises(BaubleError):
            get_pertinent_objects(Species, [fn])
            get_pertinent_objects(Species, fn)

        with pytest.raises(BaubleError):
            get_pertinent_objects(Accession, [fn])
            get_pertinent_objects(Accession, fn)

        with pytest.raises(BaubleError):
            get_pertinent_objects(Plant, [fn])
            get_pertinent_objects(Plant, fn)

        with pytest.raises(BaubleError):
            get_pertinent_objects(Location, [fn])
            get_pertinent_objects(Location, fn)

    def test_get_species_pertinent_objects_sessionless(self, session):
        def get_ids(objs):
            return sorted([o.id for o in objs])

        family = session.get(Family, 1)
        ids = get_ids(get_pertinent_objects(Species, [family]))
        assert ids == list(range(1, 5))

    def test_get_species_pertinent_to_element(self):
        """
        Test getting the species from a family type.
        """

        def get_ids(objs):
            return sorted([o.id for o in objs])

        # Fetch the family object
        Family = dynamic_import("bauble.plugins.plants", "Family")
        Species = dynamic_import("bauble.plugins.plants", "Species")

        family = self.get(Family, 1)

        # Get pertinent species from the family
        ids = get_ids(get_pertinent_objects(Species, family))

        # Assert the IDs are as expected
        assert ids == list(range(1, 5))

    def test_get_species_pertinent_to_lists(self):
        """
        Test getting the species from different types
        """

        def get_ids(objs):
            return sorted([o.id for o in objs])

        # Dynamically import required models
        Family = dynamic_import("bauble.plugins.plants", "Family")
        Genus = dynamic_import("bauble.plugins.plants", "Genus")
        Species = dynamic_import("bauble.plugins.plants", "Species")
        Accession = dynamic_import("bauble.plugins.garden.models", "Accession")
        Contact = dynamic_import("bauble.plugins.garden.models", "Contact")
        Plant = dynamic_import("bauble.plugins.garden.models", "Plant")
        Location = dynamic_import("bauble.plugins.garden.models", "Location")
        VernacularName = dynamic_import("bauble.plugins.plants", "VernacularName")
        Tag = dynamic_import("bauble.plugins.tag", "Tag")

        # Test fetching pertinent objects from a single family
        family = self.get(Family, 1)
        ids = get_ids(get_pertinent_objects(Species, [family]))
        assert ids == list(range(1, 5))

        # Test fetching pertinent objects from multiple families
        family2 = self.get(Family, 2)
        ids = get_ids(get_pertinent_objects(Species, [family, family2]))
        assert ids == list(range(1, 9))

        # Test fetching from a genus
        genus = self.get(Genus, 1)
        ids = get_ids(get_pertinent_objects(Species, [genus]))
        assert ids == [1, 2]

        # Test fetching from a species
        species = self.get(Species, 1)
        ids = get_ids(get_pertinent_objects(Species, [species]))
        assert ids == [1]

        # Test fetching from an accession
        accession = self.get(Accession, 1)
        ids = get_ids(get_pertinent_objects(Species, [accession]))
        assert ids == [1]

        # Test fetching from a contact
        contact = self.get(Contact, 1)
        ids = get_ids(get_pertinent_objects(Species, [contact]))
        assert ids == [1]

        # Test fetching from a plant
        plant = self.get(Plant, 1)
        ids = get_ids(get_pertinent_objects(Species, [plant]))
        assert ids == [1]

        # Test fetching from a location
        location = self.get(Location, 1)
        ids = get_ids(get_pertinent_objects(Species, [location]))
        assert ids == [1]

        # Test fetching from a vernacular name
        vn = self.get(VernacularName, 1)
        ids = get_ids(get_pertinent_objects(Species, [vn]))
        assert ids == [1]

        # Test fetching from a tag
        tag_objects("test", [family, genus])
        tag = self.execute(select(Tag)).scalars().where(Tag.tag == "test").one()
        ids = get_ids(get_pertinent_objects(Species, [tag]))
        assert ids == list(range(1, 5))

        # Test fetching from all the objects
        ids = get_ids(
            get_pertinent_objects(
                Species, [family, genus, species, accession, plant, location]
            )
        )
        assert ids == list(range(1, 5))

    def test_get_accessions_pertinent_objects(self):
        """
        Test getting the accessions from different types
        """

        def get_ids(objs):
            return sorted([o.id for o in objs])

        # Dynamically import required models
        Family = dynamic_import("bauble.plugins.plants", "Family")
        Genus = dynamic_import("bauble.plugins.plants", "Genus")
        Species = dynamic_import("bauble.plugins.plants", "Species")
        Accession = dynamic_import("bauble.plugins.garden", "Accession")
        Contact = dynamic_import("bauble.plugins.garden", "Contact")
        Plant = dynamic_import("bauble.plugins.garden", "Plant")
        Location = dynamic_import("bauble.plugins.garden", "Location")
        VernacularName = dynamic_import("bauble.plugins.plants", "VernacularName")
        Tag = dynamic_import("bauble.plugins.tag", "Tag")

        # Test fetching pertinent objects from a single family
        family = self.get(Family, 1)
        ids = get_ids(get_pertinent_objects(Accession, [family]))
        assert ids == list(range(1, 9))

        # Test fetching pertinent objects from multiple families
        family2 = self.get(Family, 1)
        ids = get_ids(get_pertinent_objects(Accession, [family, family2]))
        assert ids == list(range(1, 9))

        # Test fetching from a genus
        genus = self.get(Genus, 1)
        ids = get_ids(get_pertinent_objects(Accession, genus))
        assert ids == list(range(1, 5))

        # Test fetching from a species
        species = self.get(Species, 1)
        ids = get_ids(get_pertinent_objects(Accession, species))
        assert ids == [1, 2]

        # Test fetching from an accession
        accession = self.get(Accession, 1)
        ids = get_ids(get_pertinent_objects(Accession, [accession]))
        assert ids == [1]

        # Test fetching from a contact
        contact = self.get(Contact, 1)
        ids = get_ids(get_pertinent_objects(Accession, contact))
        assert ids == [1]

        # Test fetching from a plant
        plant = self.get(Plant, 1)
        ids = get_ids(get_pertinent_objects(Accession, [plant]))
        assert ids == [1]

        # Test fetching from a location
        location = self.get(Location, 1)
        ids = get_ids(get_pertinent_objects(Accession, [location]))
        assert ids == [1]

        # Test fetching from a vernacular name
        vn = self.get(VernacularName, 1)
        ids = get_ids(get_pertinent_objects(Accession, [vn]))
        assert ids == [1, 2]

        # Test fetching from a tag
        tag_objects("test", [family, genus])
        tag = self.execute(select(Tag)).scalars().where(Tag.tag == "test").one()
        ids = get_ids(get_pertinent_objects(Accession, [tag]))
        assert ids == list(range(1, 9))

        # Test fetching from all the objects
        ids = get_ids(
            get_pertinent_objects(
                Accession, [family, genus, species, accession, plant, location]
            )
        )
        assert ids == list(range(1, 9))

    def test_get_plants_pertinent_to(self):
        """
        Test getting the plants from different types
        """

        def get_ids(objs):
            return sorted([o.id for o in objs])

        # Dynamically import required models
        Family = dynamic_import("bauble.plugins.plants", "Family")
        Genus = dynamic_import("bauble.plugins.plants", "Genus")
        Species = dynamic_import("bauble.plugins.plants", "Species")
        Accession = dynamic_import("bauble.plugins.garden", "Accession")
        Contact = dynamic_import("bauble.plugins.garden", "Contact")
        Plant = dynamic_import("bauble.plugins.garden", "Plant")
        Location = dynamic_import("bauble.plugins.garden", "Location")
        VernacularName = dynamic_import("bauble.plugins.plants", "VernacularName")
        Tag = dynamic_import("bauble.plugins.tag", "Tag")

        # Test getting plants from one family
        family = self.get(Family, 1)
        ids = get_ids(get_pertinent_objects(Plant, family))
        assert ids == list(range(1, 17))

        # Test getting plants from multiple families
        family2 = self.get(Family, 2)
        ids = get_ids(get_pertinent_objects(Plant, [family, family2]))
        assert ids == list(range(1, 33))

        # Test getting plants from a genus
        genus = self.get(Genus, 1)
        ids = get_ids(get_pertinent_objects(Plant, genus))
        assert ids == list(range(1, 9))

        # Test getting plants from a species
        species = self.get(Species, 1)
        ids = get_ids(get_pertinent_objects(Plant, species))
        assert ids == list(range(1, 5))

        # Test getting plants from an accession
        accession = self.get(Accession, 1)
        ids = get_ids(get_pertinent_objects(Plant, accession))
        assert ids == list(range(1, 3))

        # Test getting plants from a contact
        contact = self.get(Contact, 1)
        ids = get_ids(get_pertinent_objects(Plant, contact))
        assert ids == list(range(1, 3))

        # Test getting plants from a plant object
        plant = self.get(Plant, 1)
        ids = get_ids(get_pertinent_objects(Plant, plant))
        assert ids == [1]

        # Test getting plants from a location
        location = self.get(Location, 1)
        plants = get_pertinent_objects(Plant, [location])
        ids = sorted([p.id for p in plants])
        assert ids == [1]

        # Test getting plants from a vernacular name
        vn = self.get(VernacularName, 1)
        ids = get_ids(get_pertinent_objects(Plant, vn))
        assert ids == list(range(1, 5))

        # Test getting plants from a tag
        tag_objects("test", [family, genus])
        tag = self.execute(select(Tag)).scalars().where(Tag.tag == "test").one()
        ids = get_ids(get_pertinent_objects(Plant, tag))
        assert ids == list(range(1, 17))

        # Test getting plants from multiple object types
        plants = get_pertinent_objects(
            Plant, [family, genus, species, accession, plant, location]
        )
        ids = get_ids(plants)
        assert ids == list(range(1, 17))

    def test_get_locations_pertinent_to(self):
        """
        Test getting the locations from different types
        """

        def get_ids(objs):
            return sorted([o.id for o in objs])

        # Dynamically import required models
        Family = dynamic_import("bauble.plugins.plants", "Family")
        Genus = dynamic_import("bauble.plugins.plants", "Genus")
        Species = dynamic_import("bauble.plugins.plants", "Species")
        Accession = dynamic_import("bauble.plugins.garden", "Accession")
        Contact = dynamic_import("bauble.plugins.garden", "Contact")
        Plant = dynamic_import("bauble.plugins.garden", "Plant")
        Location = dynamic_import("bauble.plugins.garden", "Location")
        VernacularName = dynamic_import("bauble.plugins.plants", "VernacularName")
        Tag = dynamic_import("bauble.plugins.tag", "Tag")

        # Test getting locations from one family
        family = self.get(Family, 1)
        ids = get_ids(get_pertinent_objects(Location, family))
        assert ids == list(range(1, 17))

        # Test getting locations from multiple families
        family2 = self.get(Family, 2)
        ids = get_ids(get_pertinent_objects(Location, [family, family2]))
        assert ids == list(range(1, 33))

        # Test getting locations from a genus
        genus = self.get(Genus, 1)
        ids = get_ids(get_pertinent_objects(Location, genus))
        assert ids == list(range(1, 9))

        # Test getting locations from a species
        species = self.get(Species, 1)
        ids = get_ids(get_pertinent_objects(Location, species))
        assert ids == list(range(1, 5))

        # Test getting locations from a vernacular name
        vn = self.get(VernacularName, 1)
        ids = get_ids(get_pertinent_objects(Location, vn))
        assert ids == list(range(1, 5))

        # Test getting locations from a plant
        plant = self.get(Plant, 1)
        ids = get_ids(get_pertinent_objects(Location, plant))
        assert ids == [1]

        # Test getting locations from an accession
        accession = self.get(Accession, 1)
        ids = get_ids(get_pertinent_objects(Location, accession))
        assert ids == list(range(1, 3))

        # Test getting locations from a contact
        contact = self.get(Contact, 1)
        ids = get_ids(get_pertinent_objects(Location, contact))
        assert ids == list(range(1, 3))

        # Test getting locations from a location object
        location = self.get(Location, 1)
        locations = get_pertinent_objects(Location, [location])
        ids = [l.id for l in locations]
        assert ids == [1]

        # Test getting locations from a tag
        tag_objects("test", [family, genus])
        tag = self.execute(select(Tag)).scalars().where(Tag.tag == "test").one()
        ids = get_ids(get_pertinent_objects(Location, tag))
        assert ids == list(range(1, 17))

        # Test getting locations from multiple object types
        locations = get_pertinent_objects(
            Location, [family, genus, species, accession, plant, location, tag]
        )
        ids = get_ids(locations)
        assert ids == list(range(1, 17))
