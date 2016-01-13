# -*- coding: utf-8 -*-
#
# Copyright (c) 2005,2006,2007,2008,2009 Brett Adams <brett@belizebotanic.org>
# Copyright (c) 2012-2015 Mario Frasca <mario@anche.no>
#
# This file is part of bauble.classic.
#
# bauble.classic is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# bauble.classic is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bauble.classic. If not, see <http://www.gnu.org/licenses/>.

import os

from bauble.test import BaubleTestCase, check_dupids
from bauble.plugins.report import (
    get_species_pertinent_to, get_accessions_pertinent_to,
    get_plants_pertinent_to)
from bauble.plugins.plants import Family, Genus, Species, VernacularName
from bauble.plugins.garden import Accession, Plant, Location
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
        super(ReportTestCase, self).__init__(*args)

    def setUp(self):
        super(ReportTestCase, self).setUp()

    def tearDown(self):
        super(ReportTestCase, self).tearDown()


class ReportTests(ReportTestCase):

    def setUp(self):
        super(ReportTests, self).setUp()
        fctr = gctr = sctr = actr = pctr = 0
        for f in xrange(2):
            fctr += 1
            family = Family(id=fctr, family=u'fam%s' % fctr)
            self.session.add(family)
            for g in range(2):
                gctr += 1
                genus = Genus(id=gctr, family=family, genus=u'gen%s' % gctr)
                self.session.add(genus)
                for s in range(2):
                    sctr += 1
                    sp = Species(id=sctr, genus=genus, sp=u'sp%s' % sctr)
                    vn = VernacularName(id=sctr, species=sp,
                                        name=u'name%s' % sctr)
                    self.session.add_all([sp, vn])
                    for a in range(2):
                        actr += 1
                        acc = Accession(id=actr, species=sp, code=u'%s' % actr)
                        self.session.add(acc)
                        for p in range(2):
                            pctr += 1
                            loc = Location(id=pctr, code=u'%s' % pctr,
                                           name=u'site%s' % pctr)
                            plant = Plant(id=pctr, accession=acc, location=loc,
                                          code=u'%s' % pctr, quantity=1)
                            #debug('fctr: %s, gctr: %s, actr: %s, pctr: %s' \
                            #      % (fctr, gctr, actr, pctr))
                            self.session.add_all([loc, plant])
        self.session.commit()

    def tearDown(self):
        super(ReportTests, self).tearDown()

    def test_no_objects_in_FamilyNote(self):
        family = self.session.query(Family).get(1)
        from bauble.plugins.plants.family import FamilyNote
        fn = FamilyNote(family=family, note=u'empty')
        self.session.add(fn)
        self.session.flush()

        from bauble.error import BaubleError
        self.assertRaises(BaubleError, get_species_pertinent_to, [fn])
        self.assertRaises(BaubleError, get_species_pertinent_to, fn)
        self.assertRaises(BaubleError, get_accessions_pertinent_to, [fn])
        self.assertRaises(BaubleError, get_accessions_pertinent_to, fn)
        self.assertRaises(BaubleError, get_plants_pertinent_to, [fn])
        self.assertRaises(BaubleError, get_plants_pertinent_to, fn)

    def test_get_species_pertinent_to_sessionless(self):
        get_ids = lambda objs: sorted([o.id for o in objs])

        family = self.session.query(Family).get(1)
        ids = get_ids(get_species_pertinent_to([family]))
        self.assert_(ids == range(1, 5), ids)

    def test_get_species_pertinent_to_element(self):
        """
        Test getting the species from different types
        """
        get_ids = lambda objs: sorted([o.id for o in objs])

        family = self.session.query(Family).get(1)
        ids = get_ids(get_species_pertinent_to(family, self.session))
        self.assert_(ids == range(1, 5), ids)

    def test_get_species_pertinent_to_lists(self):
        """
        Test getting the species from different types
        """
        get_ids = lambda objs: sorted([o.id for o in objs])

        family = self.session.query(Family).get(1)
        ids = get_ids(get_species_pertinent_to([family], self.session))
        self.assert_(ids == range(1, 5), ids)

        family = self.session.query(Family).get(1)
        family2 = self.session.query(Family).get(2)
        ids = get_ids(
            get_species_pertinent_to([family, family2], self.session))
        self.assert_(ids == range(1, 9), ids)

        genus = self.session.query(Genus).get(1)
        ids = get_ids(get_species_pertinent_to([genus], self.session))
        self.assert_(ids == [1, 2], ids)

        species = self.session.query(Species).get(1)
        ids = get_ids(get_species_pertinent_to([species], self.session))
        self.assert_(ids == [1], ids)

        accession = self.session.query(Accession).get(1)
        ids = get_ids(get_species_pertinent_to([accession], self.session))
        self.assert_(ids == [1], ids)

        plant = self.session.query(Plant).get(1)
        ids = get_ids(get_species_pertinent_to([plant], self.session))
        self.assert_(ids == [1], ids)

        location = self.session.query(Location).get(1)
        ids = get_ids(get_species_pertinent_to([location], self.session))
        self.assert_(ids == [1], ids)

        vn = self.session.query(VernacularName).get(1)
        ids = get_ids(get_species_pertinent_to([vn], self.session))
        self.assert_(ids == [1], ids)

        tag_objects('test', [family, genus])
        tag = self.session.query(Tag).filter_by(tag=u'test').one()
        ids = get_ids(get_species_pertinent_to([tag], self.session))
        self.assert_(ids == range(1, 5), ids)

        # now test all the objects
        ids = get_ids(get_species_pertinent_to(
            [family, genus, species, accession, plant, location],
            self.session))
        self.assert_(ids == range(1, 5), ids)

    def test_get_accessions_pertinent_to(self):
        """
        Test getting the accessions from different types
        """
        get_ids = lambda objs: sorted([o.id for o in objs])

        family = self.session.query(Family).get(1)
        ids = get_ids(get_accessions_pertinent_to([family], self.session))
        self.assert_(ids == range(1, 9), ids)

        family = self.session.query(Family).get(1)
        family2 = self.session.query(Family).get(1)
        ids = get_ids(get_accessions_pertinent_to(
            [family, family2], self.session))
        self.assert_(ids == range(1, 9), ids)

        genus = self.session.query(Genus).get(1)
        ids = get_ids(get_accessions_pertinent_to(genus, self.session))
        self.assert_(ids == range(1, 5), ids)

        species = self.session.query(Species).get(1)
        ids = get_ids(get_accessions_pertinent_to(species, self.session))
        self.assert_(ids == [1, 2], ids)

        accession = self.session.query(Accession).get(1)
        ids = get_ids(get_accessions_pertinent_to([accession], self.session))
        self.assert_(ids == [1], ids)

        plant = self.session.query(Plant).get(1)
        ids = get_ids(get_accessions_pertinent_to([plant], self.session))
        self.assert_(ids == [1], ids)

        location = self.session.query(Location).get(1)
        ids = get_ids(get_accessions_pertinent_to([location], self.session))
        self.assert_(ids == [1], ids)

        vn = self.session.query(VernacularName).get(1)
        ids = get_ids(get_accessions_pertinent_to([vn], self.session))
        self.assert_(ids == [1, 2], ids)

        tag_objects('test', [family, genus])
        tag = self.session.query(Tag).filter_by(tag=u'test').one()
        ids = get_ids(get_accessions_pertinent_to([tag], self.session))
        self.assert_(ids == range(1, 9), ids)

        # now test all the objects
        ids = get_ids(get_accessions_pertinent_to(
            [family, genus, species, accession, plant, location],
            self.session))
        self.assert_(ids == range(1, 9), ids)

    def test_get_plants_pertinent_to(self):
        """
        Test getting the plants from different types
        """
        get_ids = lambda objs: sorted([o.id for o in objs])

        # get plants from one family
        family = self.session.query(Family).get(1)
        ids = get_ids(get_plants_pertinent_to(family, self.session))
        self.assert_(ids == range(1, 17), ids)

        # get plants from multiple families
        family = self.session.query(Family).get(1)
        family2 = self.session.query(Family).get(2)
        ids = get_ids(get_plants_pertinent_to([family, family2], self.session))
        self.assert_(ids == range(1, 33), ids)

        genus = self.session.query(Genus).get(1)
        ids = get_ids(get_plants_pertinent_to(genus, self.session))
        self.assert_(ids == range(1, 9), ids)

        species = self.session.query(Species).get(1)
        ids = get_ids(get_plants_pertinent_to(species, self.session))
        self.assert_(ids == range(1, 5), ids)

        accession = self.session.query(Accession).get(1)
        ids = get_ids(get_plants_pertinent_to(accession, self.session))
        self.assert_(ids == range(1, 3), ids)

        plant = self.session.query(Plant).get(1)
        ids = get_ids(get_plants_pertinent_to(plant, self.session))
        self.assert_(ids == [1], ids)

        location = self.session.query(Location).get(1)
        plants = get_plants_pertinent_to([location], self.session)
        plant_ids = sorted([p.id for p in plants])
        self.assert_(plant_ids == [1], plant_ids)

        vn = self.session.query(VernacularName).get(1)
        ids = get_ids(get_plants_pertinent_to(vn, self.session))
        self.assert_(ids == range(1, 5), ids)

        tag_objects('test', [family, genus])
        tag = self.session.query(Tag).filter_by(tag=u'test').one()
        ids = get_ids(get_plants_pertinent_to(tag, self.session))
        self.assert_(ids == range(1, 17), ids)

        # now test all the objects
        plants = get_plants_pertinent_to(
            [family, genus, species, accession, plant, location], self.session)
        ids = get_ids(plants)
        self.assert_(ids == range(1, 17), ids)
