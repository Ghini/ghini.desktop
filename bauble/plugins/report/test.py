# -*- coding: utf-8 -*-
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

import os

from bauble.test import BaubleTestCase, check_dupids
from bauble.plugins.report import (
    get_species_pertinent_to, get_accessions_pertinent_to,
    get_plants_pertinent_to, get_locations_pertinent_to)
from bauble.plugins.plants import Family, Genus, Species, VernacularName
from bauble.plugins.garden import Accession, Plant, Location, Source, Contact
from bauble.plugins.tag import tag_objects, Tag


def setUp_test_data():
    pass


def tearDown_test_data():
    pass


def test_duplicate_ids():
    """
    Test for duplicate ids for all .glade files in the gardens plugin.
    """
    import bauble.plugins.report as mod
    import glob
    head, tail = os.path.split(mod.__file__)
    files = []
    files.extend(glob.glob(os.path.join(head, '*.glade')))
    files = glob.glob(os.path.join(head, 'mako', '*.glade'))
    files = glob.glob(os.path.join(head, 'xsl', '*.glade'))
    for f in files:
        assert(not check_dupids(f))


class ReportTestCase(BaubleTestCase):

    def __init__(self, *args):
        super().__init__(*args)

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()


class ReportTests(ReportTestCase):

    def setUp(self):
        super().setUp()
        fctr = gctr = sctr = actr = pctr = 0
        for f in range(2):
            fctr += 1
            family = Family(id=fctr, family='fam%s' % fctr)
            self.session.add(family)
            for g in range(2):
                gctr += 1
                genus = Genus(id=gctr, family=family, genus='gen%s' % gctr)
                self.session.add(genus)
                for s in range(2):
                    sctr += 1
                    sp = Species(id=sctr, genus=genus, sp='sp%s' % sctr)
                    vn = VernacularName(id=sctr, species=sp,
                                        name='name%s' % sctr)
                    self.session.add_all([sp, vn])
                    for a in range(2):
                        actr += 1
                        acc = Accession(id=actr, species=sp, code='%s' % actr)
                        contact = Contact(id=actr, name='contact%s' % actr)
                        source = Source(id=actr, source_detail=contact,
                                accession=acc)
                        self.session.add_all([acc, source, contact])
                        for p in range(2):
                            pctr += 1
                            loc = Location(id=pctr, code='%s' % pctr,
                                           name='site%s' % pctr)
                            plant = Plant(id=pctr, accession=acc, location=loc,
                                          code='%s' % pctr, quantity=1)
                            #debug('fctr: %s, gctr: %s, actr: %s, pctr: %s' \
                            #      % (fctr, gctr, actr, pctr))
                            self.session.add_all([loc, plant])
        self.session.commit()

    def tearDown(self):
        super().tearDown()

    def test_no_objects_in_FamilyNote(self):
        family = self.session.query(Family).get(1)
        from bauble.plugins.plants.family import FamilyNote
        fn = FamilyNote(family=family, note='empty')
        self.session.add(fn)
        self.session.flush()

        from bauble.error import BaubleError
        self.assertRaises(BaubleError, get_species_pertinent_to, [fn])
        self.assertRaises(BaubleError, get_species_pertinent_to, fn)
        self.assertRaises(BaubleError, get_accessions_pertinent_to, [fn])
        self.assertRaises(BaubleError, get_accessions_pertinent_to, fn)
        self.assertRaises(BaubleError, get_plants_pertinent_to, [fn])
        self.assertRaises(BaubleError, get_plants_pertinent_to, fn)
        self.assertRaises(BaubleError, get_locations_pertinent_to, [fn])
        self.assertRaises(BaubleError, get_locations_pertinent_to, fn)

    def test_get_species_pertinent_to_sessionless(self):
        get_ids = lambda objs: sorted([o.id for o in objs])

        family = self.session.query(Family).get(1)
        ids = get_ids(get_species_pertinent_to([family]))
        self.assertEqual(ids, list(range(1, 5)))

    def test_get_species_pertinent_to_element(self):
        """
        Test getting the species from different types
        """
        get_ids = lambda objs: sorted([o.id for o in objs])

        family = self.session.query(Family).get(1)
        ids = get_ids(get_species_pertinent_to(family, self.session))
        self.assertEqual(ids, list(range(1, 5)))

    def test_get_species_pertinent_to_lists(self):
        """
        Test getting the species from different types
        """
        get_ids = lambda objs: sorted([o.id for o in objs])

        family = self.session.query(Family).get(1)
        ids = get_ids(get_species_pertinent_to([family], self.session))
        self.assertEqual(ids, list(range(1, 5)))

        family = self.session.query(Family).get(1)
        family2 = self.session.query(Family).get(2)
        ids = get_ids(
            get_species_pertinent_to([family, family2], self.session))
        self.assertEqual(ids, list(range(1, 9)))

        genus = self.session.query(Genus).get(1)
        ids = get_ids(get_species_pertinent_to([genus], self.session))
        self.assertEqual(ids, [1, 2])

        species = self.session.query(Species).get(1)
        ids = get_ids(get_species_pertinent_to([species], self.session))
        self.assertEqual(ids, [1])

        accession = self.session.query(Accession).get(1)
        ids = get_ids(get_species_pertinent_to([accession], self.session))
        self.assertEqual(ids, [1])

        contact = self.session.query(Contact).get(1)
        ids = get_ids(get_species_pertinent_to(contact, self.session))
        self.assertEqual(ids, [1])

        plant = self.session.query(Plant).get(1)
        ids = get_ids(get_species_pertinent_to([plant], self.session))
        self.assertEqual(ids, [1])

        location = self.session.query(Location).get(1)
        ids = get_ids(get_species_pertinent_to([location], self.session))
        self.assertEqual(ids, [1])

        vn = self.session.query(VernacularName).get(1)
        ids = get_ids(get_species_pertinent_to([vn], self.session))
        self.assertEqual(ids, [1])

        tag_objects('test', [family, genus])
        tag = self.session.query(Tag).filter_by(tag='test').one()
        ids = get_ids(get_species_pertinent_to([tag], self.session))
        self.assertEqual(ids, list(range(1, 5)))

        # now test all the objects
        ids = get_ids(get_species_pertinent_to(
            [family, genus, species, accession, plant, location],
            self.session))
        self.assertEqual(ids, list(range(1, 5)))

    def test_get_accessions_pertinent_to(self):
        """
        Test getting the accessions from different types
        """
        get_ids = lambda objs: sorted([o.id for o in objs])

        family = self.session.query(Family).get(1)
        ids = get_ids(get_accessions_pertinent_to([family], self.session))
        self.assertEqual(ids, list(range(1, 9)))

        family = self.session.query(Family).get(1)
        family2 = self.session.query(Family).get(1)
        ids = get_ids(get_accessions_pertinent_to(
            [family, family2], self.session))
        self.assertEqual(ids, list(range(1, 9)))

        genus = self.session.query(Genus).get(1)
        ids = get_ids(get_accessions_pertinent_to(genus, self.session))
        self.assertEqual(ids, list(range(1, 5)))

        species = self.session.query(Species).get(1)
        ids = get_ids(get_accessions_pertinent_to(species, self.session))
        self.assertEqual(ids, [1, 2])

        accession = self.session.query(Accession).get(1)
        ids = get_ids(get_accessions_pertinent_to([accession], self.session))
        self.assertEqual(ids, [1])

        contact = self.session.query(Contact).get(1)
        ids = get_ids(get_accessions_pertinent_to(contact, self.session))
        self.assertTrue(ids == [1], ids)

        plant = self.session.query(Plant).get(1)
        ids = get_ids(get_accessions_pertinent_to([plant], self.session))
        self.assertEqual(ids, [1])

        location = self.session.query(Location).get(1)
        ids = get_ids(get_accessions_pertinent_to([location], self.session))
        self.assertEqual(ids, [1])

        vn = self.session.query(VernacularName).get(1)
        ids = get_ids(get_accessions_pertinent_to([vn], self.session))
        self.assertEqual(ids, [1, 2])

        tag_objects('test', [family, genus])
        tag = self.session.query(Tag).filter_by(tag='test').one()
        ids = get_ids(get_accessions_pertinent_to([tag], self.session))
        self.assertEqual(ids, list(range(1, 9)))

        # now test all the objects
        ids = get_ids(get_accessions_pertinent_to(
            [family, genus, species, accession, plant, location],
            self.session))
        self.assertEqual(ids, list(range(1, 9)))

    def test_get_plants_pertinent_to(self):
        """
        Test getting the plants from different types
        """
        get_ids = lambda objs: sorted([o.id for o in objs])

        # get plants from one family
        family = self.session.query(Family).get(1)
        ids = get_ids(get_plants_pertinent_to(family, self.session))
        self.assertEqual(ids, list(range(1, 17)))

        # get plants from multiple families
        family = self.session.query(Family).get(1)
        family2 = self.session.query(Family).get(2)
        ids = get_ids(get_plants_pertinent_to([family, family2], self.session))
        self.assertEqual(ids, list(range(1, 33)))

        genus = self.session.query(Genus).get(1)
        ids = get_ids(get_plants_pertinent_to(genus, self.session))
        self.assertEqual(ids, list(range(1, 9)))

        species = self.session.query(Species).get(1)
        ids = get_ids(get_plants_pertinent_to(species, self.session))
        self.assertEqual(ids, list(range(1, 5)))

        accession = self.session.query(Accession).get(1)
        ids = get_ids(get_plants_pertinent_to(accession, self.session))
        self.assertEqual(ids, list(range(1, 3)))

        contact = self.session.query(Contact).get(1)
        ids = get_ids(get_plants_pertinent_to(contact, self.session))
        self.assertTrue(ids == list(range(1, 3)), ids)

        plant = self.session.query(Plant).get(1)
        ids = get_ids(get_plants_pertinent_to(plant, self.session))
        self.assertEqual(ids, [1])

        location = self.session.query(Location).get(1)
        plants = get_plants_pertinent_to([location], self.session)
        ids = sorted([p.id for p in plants])
        self.assertEqual(ids, [1])

        vn = self.session.query(VernacularName).get(1)
        ids = get_ids(get_plants_pertinent_to(vn, self.session))
        self.assertEqual(ids, list(range(1, 5)))

        tag_objects('test', [family, genus])
        tag = self.session.query(Tag).filter_by(tag='test').one()
        ids = get_ids(get_plants_pertinent_to(tag, self.session))
        self.assertEqual(ids, list(range(1, 17)))

        # now test all the objects
        plants = get_plants_pertinent_to(
            [family, genus, species, accession, plant, location], self.session)
        ids = get_ids(plants)
        self.assertEqual(ids, list(range(1, 17)))

    def test_get_locations_pertinent_to(self):
        """
        Test getting the locations from different types
        """
        get_ids = lambda objs: sorted([o.id for o in objs])

        # get locations from one family
        family = self.session.query(Family).get(1)
        ids = get_ids(get_locations_pertinent_to(family, self.session))
        self.assertEqual(ids, list(range(1, 17)))

        # get locations from multiple families
        family = self.session.query(Family).get(1)
        family2 = self.session.query(Family).get(2)
        ids = get_ids(get_locations_pertinent_to([family, family2],
            self.session))
        self.assertEqual(ids, list(range(1, 33)))

        genus = self.session.query(Genus).get(1)
        ids = get_ids(get_locations_pertinent_to(genus, self.session))
        self.assertEqual(ids, list(range(1, 9)))

        species = self.session.query(Species).get(1)
        ids = get_ids(get_locations_pertinent_to(species, self.session))
        self.assertEqual(ids, list(range(1, 5)))

        vn = self.session.query(VernacularName).get(1)
        ids = get_ids(get_locations_pertinent_to(vn, self.session))
        self.assertEqual(ids, list(range(1, 5)))

        plant = self.session.query(Plant).get(1)
        ids = get_ids(get_locations_pertinent_to(plant, self.session))
        self.assertEqual(ids, [1])

        accession = self.session.query(Accession).get(1)
        ids = get_ids(get_locations_pertinent_to(accession, self.session))
        self.assertEqual(ids, list(range(1, 3)))

        contact = self.session.query(Contact).get(1)
        ids = get_ids(get_locations_pertinent_to(contact, self.session))
        self.assertTrue(ids == list(range(1, 3)))

        location = self.session.query(Location).get(1)
        locations = get_locations_pertinent_to([location], self.session)
        ids = [l.id for l in locations]
        self.assertEqual(ids, [1])

        tag_objects('test', [family, genus])
        tag = self.session.query(Tag).filter_by(tag='test').one()
        ids = get_ids(get_locations_pertinent_to(tag, self.session))
        self.assertEqual(ids, list(range(1, 17)))

        # now test all the objects
        locations = get_locations_pertinent_to(
            [family, genus, species, accession, plant, location, tag], self.session)
        ids = get_ids(locations)
        self.assertEqual(ids, list(range(1, 17)))
