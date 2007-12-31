import unittest
from sqlalchemy import *
from sqlalchemy.exceptions import *
from testbase import BaubleTestCase, log
import bauble.utils as utils
#import bauble.plugins.report as report_plugin
from bauble.plugins.report import _get_all_species_ids, get_all_species
from bauble.plugins.plants import Family, family_table, Genus, genus_table, \
     Species, species_table, VernacularName, vernacular_name_table
from bauble.plugins.garden import Accession, accession_table, Plant, \
     plant_table, Location, location_table


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
                                                  'species_id': sctr})
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

    def test_get_all_species(self):
        """
        test getting the species from different types
        """
        family = self.session.load(Family, 1)
        species_id = _get_all_species_ids([family])
        self.assert_(species_id == [1, 2, 3, 4])

        genus = self.session.load(Genus, 1)
        species_id = _get_all_species_ids([genus])
        self.assert_(species_id == [1, 2])

        species = self.session.load(Species, 1)
        species_id = _get_all_species_ids([species])
        self.assert_(species_id == [1])

        accession = self.session.load(Accession ,1)
        species_id = _get_all_species_ids([accession])
        self.assert_(species_id == [1])

        plant = self.session.load(Plant, 1)
        species_id = _get_all_species_ids([plant])
        self.assert_(species_id == [1])

        location = self.session.load(Location, 1)
        species_id = _get_all_species_ids([location])
        self.assert_(species_id == [1])

        # TODO: need to test vernacular_name, tag and any other possible types

        # now test all the objects
        species_id = _get_all_species_ids([family, genus, species,
                                           accession, plant, location])
        self.assert_(species_id == [1, 2, 3, 4])



class ReportTestSuite(unittest.TestSuite):

   def __init__(self):
       super(ReportTestSuite, self).__init__()
       self.addTests(map(ReportTests, ('test_get_all_species',)))


testsuite = ReportTestSuite




