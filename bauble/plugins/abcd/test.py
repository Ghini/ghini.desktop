#
# test.py
#
# Description: test the ABCD (Access to Biological Collection Data) plugin
#
import os, unittest, tempfile
import lxml.etree as etree
from sqlalchemy import *
from sqlalchemy.exc import *
import bauble
import bauble.paths as paths
from lxml.etree import Element, SubElement, ElementTree, dump
from bauble.test import BaubleTestCase
from bauble.plugins.garden.accession import Accession
from bauble.plugins.garden.location import Location
from bauble.plugins.garden.plant import Plant
from bauble.plugins.garden.donor import Donor
from bauble.plugins.garden.source import Donation, Collection
from bauble.plugins.plants.family import Family
from bauble.plugins.plants.genus import Genus
from bauble.plugins.plants.species_model import Species
from bauble.plugins.abcd import DataSets
import bauble.plugins.abcd as abcd
import bauble.plugins.plants.test as plants_test
import bauble.plugins.garden.test as garden_test


# TODO: the ABCD tests need to be completely reworked

class ABCDTestCase(BaubleTestCase):

    def __init__(self, *args):
        super(ABCDTestCase, self).__init__(*args)


    def setUp(self):
        super(ABCDTestCase, self).setUp()
        plants_test.setUp_test_data()
        garden_test.setUp_test_data()


        schema_file = os.path.join(paths.lib_dir(), 'plugins',
            'abcd','abcd_2.06.xsd')
        xmlschema_doc = etree.parse(schema_file)
        self.abcd_schema = etree.XMLSchema(xmlschema_doc)


    def tearDown(self):
        super(ABCDTestCase, self).tearDown()
        plants_test.tearDown_test_data()
        garden_test.tearDown_test_data()


    def test_abcd(self):
        # TODO: this needs to be updated, we don't use the
        # ElementFactory anymore
        pass
#         datasets = DataSets()
#         ds = ElementFactory(datasets, 'DataSet')
#         tech_contacts = ElementFactory( ds, 'TechnicalContacts')
#         tech_contact = ElementFactory(tech_contacts, 'TechnicalContact')
#         ElementFactory(tech_contact, 'Name', text='Brett')
#         ElementFactory(tech_contact, 'Email', text='brett@belizebotanic.org')
#         cont_contacts = ElementFactory(ds, 'ContentContacts')
#         cont_contact = ElementFactory(cont_contacts, 'ContentContact')
#         ElementFactory(cont_contact, 'Name', text='Brett')
#         ElementFactory(cont_contact, 'Email', text='brett@belizebotanic.org')
#         metadata = ElementFactory(ds, 'Metadata', )
#         description = ElementFactory(metadata, 'Description')
#           representation = ElementFactory(description, 'Representation',
#                                           attrib={'language': 'en'})
#         revision = ElementFactory(metadata, 'RevisionData')
#         ElementFactory(revision, 'DateModified', text='2001-03-01T00:00:00')
#         title = ElementFactory(representation, 'Title', text='TheTitle')
#         units = ElementFactory(ds, 'Units')
#         unit = ElementFactory(units, 'Unit')
#         ElementFactory(unit, 'SourceInstitutionID', text='BBG')
#         ElementFactory(unit, 'SourceID', text='1111')
#         unit_id = ElementFactory(unit, 'UnitID', text='2222')

#         self.assert_(self.validate(datasets), self.abcd_schema.error_log)


    def test_plants_to_abcd(self):
        plants = self.session.query(Plant)
        assert plants.count() > 0
        pass
        # create abcd from plants
#        data = abcd.plants_to_abcd(plants)
        # assert validate abcd
#        self.assert_(self.validate(data), self.abcd_schema.error_log)


    def validate(self, xml):
        return self.abcd_schema.validate(xml)


class ABCDTestSuite(unittest.TestSuite):

    def __init__(self):
        unittest.TestSuite.__init__(self)
        self.addTests(map(ABCDTestCase, ('test_abcd', 'test_plants_to_abcd')))


testsuite = ABCDTestSuite
