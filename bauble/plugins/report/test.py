import unittest
from sqlalchemy import *
from sqlalchemy.exceptions import *
from testbase import BaubleTestCase, log
import bauble.utils as utils
#import bauble.plugins.report as report_plugin
from bauble.plugins.report import _get_all_species_ids, get_all_species, \
     _get_all_accession_ids, get_all_accessions, _get_all_plant_ids, \
     get_all_plants
from bauble.plugins.plants import Family, family_table, Genus, genus_table, \
     Species, species_table, VernacularName, vernacular_name_table
from bauble.plugins.garden import Accession, accession_table, Plant, \
     plant_table, Location, location_table
from bauble.plugins.tag import tag_objects, Tag


def setUp_test_data():
    pass

def tearDown_test_data():
    pass


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
        for f in xrange(0, 2):
            fctr+=1
            family_table.insert({'id': fctr, 'family': str(fctr)}).execute()
            for g in xrange(0, 2):
                gctr+=1
                genus_table.insert({'id': gctr, 'genus': str(gctr),
                                    'family_id': fctr}).execute()
                for s in xrange(0, 2):
                    sctr+=1
                    species_table.insert({'id': sctr, 'sp': str(sctr),
                                          'genus_id': gctr}).execute()
                    vernacular_name_table.insert({'id': sctr,
                                                  'name': str(sctr),
                                                'species_id': sctr}).execute()
                    for a in xrange(0, 2):
                        actr+=1
                        accession_table.insert({'id': actr, 'code': str(actr),
                                                'species_id': sctr}).execute()
                        for p in xrange(0, 2):
                            pctr+=1
                            location_table.insert({'id': pctr,
                                                'site': str(pctr)}).execute()
                            plant_table.insert({'id': pctr, 'code': str(pctr),
                                                'accession_id': actr,
                                                'location_id': pctr}).execute()
##                             print 'f: %s, g: %s, s: %s, a: %s, p: %s' \
##                                   % (fctr, gctr, sctr, actr, pctr)


    def tearDown(self):
        super(ReportTests, self).tearDown()
        execute = self.session.bind.execute
        execute(family_table.delete())
        execute(genus_table.delete())
        execute(species_table.delete())
        execute(vernacular_name_table.delete())
        execute(accession_table.delete())
        execute(location_table.delete())
        execute(plant_table.delete())


    def test_get_all_species(self):
        """
        test getting the species from different types
        """
        family = self.session.load(Family, 1)
        species_id = _get_all_species_ids([family])
        self.assert_(species_id == [1, 2, 3, 4], species_id)

        genus = self.session.load(Genus, 1)
        species_id = _get_all_species_ids([genus])
        self.assert_(species_id == [1, 2], species_id)

        species = self.session.load(Species, 1)
        species_id = _get_all_species_ids([species])
        self.assert_(species_id == [1], species_id)

        accession = self.session.load(Accession ,1)
        species_id = _get_all_species_ids([accession])
        self.assert_(species_id == [1], species_id)

        plant = self.session.load(Plant, 1)
        species_id = _get_all_species_ids([plant])
        self.assert_(species_id == [1], species_id)

        location = self.session.load(Location, 1)
        species_id = _get_all_species_ids([location])
        self.assert_(species_id == [1], species_id)

        vn = self.session.load(VernacularName, 1)
        species_id = _get_all_species_ids([vn])
        self.assert_(species_id == [1], species_id)

        tag_objects('test', [family, genus])
        tag = self.session.query(Tag).filter_by(tag='test').one()
        species_id = _get_all_species_ids([tag])
        self.assert_(species_id == [1,2,3,4], species_id)

        # now test all the objects
        species_id = _get_all_species_ids([family, genus, species,
                                           accession, plant, location])
        self.assert_(species_id == [1, 2, 3, 4], species_id)


    def test_get_all_accessions(self):
        """
        test getting the species from different types
        """
        family = self.session.load(Family, 1)
        acc_id = _get_all_accession_ids([family])
        self.assert_(acc_id == [1, 2, 3, 4, 5, 6, 7, 8], acc_id)

        genus = self.session.load(Genus, 1)
        acc_id = _get_all_accession_ids([genus])
        self.assert_(acc_id == [1, 2, 3, 4], acc_id)

        species = self.session.load(Species, 1)
        acc_id = _get_all_accession_ids([species])
        self.assert_(acc_id == [1, 2], acc_id)

        accession = self.session.load(Accession ,1)
        acc_id = _get_all_accession_ids([accession])
        self.assert_(acc_id == [1], acc_id)

        plant = self.session.load(Plant, 1)
        acc_id = _get_all_accession_ids([plant])
        self.assert_(acc_id == [1], acc_id)

        location = self.session.load(Location, 1)
        acc_id = _get_all_accession_ids([location])
        self.assert_(acc_id == [1], acc_id)

        vn = self.session.load(VernacularName, 1)
        acc_id = _get_all_accession_ids([vn])
        self.assert_(acc_id == [1, 2], acc_id)

        tag_objects('test', [family, genus])
        tag = self.session.query(Tag).filter_by(tag='test').one()
        acc_id = _get_all_accession_ids([tag])
        self.assert_(acc_id == [1,2,3,4,5,6,7,8], acc_id)

        # now test all the objects
        acc_id = _get_all_accession_ids([family, genus, species,
                                           accession, plant, location])
        self.assert_(acc_id == [1, 2, 3, 4, 5, 6, 7, 8], acc_id)


    def test_get_all_plants(self):
        """
        test getting the species from different types
        """
        family = self.session.load(Family, 1)
        plant_ids = _get_all_plant_ids([family])
        self.assert_(plant_ids == range(1, 17), plant_ids)

        genus = self.session.load(Genus, 1)
        plant_ids = _get_all_plant_ids([genus])
        self.assert_(plant_ids == [1, 2, 3, 4, 5, 6, 7, 8], plant_ids)

        species = self.session.load(Species, 1)
        plant_ids = _get_all_plant_ids([species])
        self.assert_(plant_ids == [1, 2, 3, 4], plant_ids)

        accession = self.session.load(Accession ,1)
        plant_ids = _get_all_plant_ids([accession])
        self.assert_(plant_ids == [1, 2], plant_ids)

        plant = self.session.load(Plant, 1)
        plant_ids = _get_all_plant_ids([plant])
        self.assert_(plant_ids == [1], plant_ids)

        location = self.session.load(Location, 1)
        plant_ids = _get_all_plant_ids([location])
        self.assert_(plant_ids == [1], plant_ids)

        vn = self.session.load(VernacularName, 1)
        plant_ids = _get_all_plant_ids([vn])
        self.assert_(plant_ids == [1, 2, 3, 4], plant_ids)

        tag_objects('test', [family, genus])
        tag = self.session.query(Tag).filter_by(tag='test').one()
        plant_ids = _get_all_plant_ids([tag])
        self.assert_(plant_ids == range(1, 17), plant_ids)

        # now test all the objects
        plant_ids = _get_all_plant_ids([family, genus, species,
                                        accession, plant, location])
        self.assert_(plant_ids == range(1, 17), plant_ids)


class ReportTestSuite(unittest.TestSuite):

   def __init__(self):
       super(ReportTestSuite, self).__init__()
       self.addTests(map(ReportTests, ('test_get_all_species',
                                       'test_get_all_accessions',
                                       'test_get_all_plants')))


testsuite = ReportTestSuite




