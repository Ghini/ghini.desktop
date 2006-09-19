import os, unittest, tempfile
import lxml.etree as etree
from sqlalchemy import *    
from sqlalchemy.exceptions import *    
import bauble.paths as paths
from lxml.etree import Element, SubElement, ElementTree, dump
from testbase import BaubleTestCase, log
from bauble.plugins.garden.accession import Accession, accession_table
from bauble.plugins.garden.location import location_table
from bauble.plugins.garden.plant import Plant, plant_table
from bauble.plugins.garden.donor import Donor, donor_table
from bauble.plugins.garden.source import Donation, Collection
from bauble.plugins.plants.family import family_table
from bauble.plugins.plants.genus import genus_table
from bauble.plugins.plants.species_model import species_table
#from bauble.plugins.abcd.abcd import DataSets, ElementFactory
from bauble.plugins.abcd import DataSets, ElementFactory
import bauble.plugins.abcd as abcd

class ABCDTests(BaubleTestCase):
    
    def setUp(self):
        super(ABCDTests, self).setUp()
        family_name = 'TestABCDFamily'
        genus_name = 'TestABCDGenus'
        sp_name = 'testabcdspecies'
        acc_code='TestABCDCode'
        site='TestABCDSite'
        family_table.insert().execute(family=family_name)
        family_id = select([family_table.c.id], family_table.c.family==family_name).scalar()
        genus_table.insert().execute(genus=genus_name, family_id=family_id)
        genus_id = select([genus_table.c.id], genus_table.c.genus==genus_name).scalar()
        species_table.insert().execute(genus_id=genus_id, sp=sp_name)
        species_id = select([species_table.c.id], species_table.c.sp==sp_name)
        insert = accession_table.insert()        
        insert.execute(species_id=species_id, code='TestABCDCode')
        acc_id = select([accession_table.c.id], accession_table.c.code==acc_code)
        donor_table.insert().execute(name='TestABCDDonor')
        insert = location_table.insert()
        insert.execute(site=site)
        location_id = select([location_table.c.id], location_table.c.site==site)
        insert = plant_table.insert()
        insert.execute(accession_id=acc_id, location_id=location_id, code='TestABCDPlantCode1')
        insert.execute(accession_id=acc_id, location_id=location_id, code='TestABCDPlantCode2')
        
        schema_file = os.path.join(paths.lib_dir(), 'plugins',
            'abcd','abcd_2.06.xsd')
        xmlschema_doc = etree.parse(schema_file)
        self.abcd_schema = etree.XMLSchema(xmlschema_doc)
        
    def test_abcd(self):
        datasets = DataSets()
        ds = ElementFactory(datasets, 'DataSet')
        tech_contacts = ElementFactory( ds, 'TechnicalContacts')
        tech_contact = ElementFactory(tech_contacts, 'TechnicalContact')
        ElementFactory(tech_contact, 'Name', text='Brett')
        ElementFactory(tech_contact, 'Email', text='brett@belizebotanic.org')
        cont_contacts = ElementFactory(ds, 'ContentContacts')
        cont_contact = ElementFactory(cont_contacts, 'ContentContact')
        ElementFactory(cont_contact, 'Name', text='Brett')
        ElementFactory(cont_contact, 'Email', text='brett@belizebotanic.org')
        metadata = ElementFactory(ds, 'Metadata', )
        description = ElementFactory(metadata, 'Description')
        representation = ElementFactory(description, 'Representation', attrib={'language': 'en'})
        revision = ElementFactory(metadata, 'RevisionData')
        ElementFactory(revision, 'DateModified', text='2001-03-01T00:00:00')
        title = ElementFactory(representation, 'Title', text='TheTitle')
        units = ElementFactory(ds, 'Units')
        unit = ElementFactory(units, 'Unit')
        ElementFactory(unit, 'SourceInstitutionID', text='BBG')
        ElementFactory(unit, 'SourceID', text='1111')
        unit_id = ElementFactory(unit, 'UnitID', text='2222')

        self.assert_(self.validate(datasets), self.abcd_schema.error_log)
        
        
    def test_plants_to_abcd(self):                
        plants = self.session.query(Plant).select()    
        # create abcd from plants
        data = abcd.plants_to_abcd(plants)
        # assert validate abcd
        self.assert_(self.validate(data), self.abcd_schema.error_log)        
        
        
    def validate(self, xml):        
        return self.abcd_schema.validate(xml)        
        
        
class ABCDTestSuite(unittest.TestSuite):
    
   def __init__(self):
       unittest.TestSuite.__init__(self)
       self.addTests(map(ABCDTests,('test_abcd','test_plants_to_abcd')))
    
       
testsuite = ABCDTestSuite