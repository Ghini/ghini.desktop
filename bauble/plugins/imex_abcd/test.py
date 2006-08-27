import os, unittest, tempfile
import lxml.etree as etree
import bauble.paths as paths
from lxml.etree import Element, SubElement, ElementTree
from testbase import BaubleTestCase, log
from bauble.plugins.imex_abcd.abcd import DataSets, ElementFactory


class ABCDTests(BaubleTestCase):
    
    def setUp(self):
        super(ABCDTests, self).setUp()
        
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

        tmp_file, tmp_filename = tempfile.mkstemp()
        ElementTree(datasets).write(tmp_filename, encoding='utf-8')
        
        doc = etree.parse(tmp_filename)
        schema_file = os.path.join(paths.lib_dir(), 'plugins',
            'imex_abcd','abcd_2.06.xsd')
        xmlschema_doc = etree.parse(schema_file)
        xmlschema = etree.XMLSchema(xmlschema_doc)
        self.assert_(xmlschema.validate(doc), xmlschema.error_log)
        
class ABCDTestSuite(unittest.TestSuite):
    
   def __init__(self):
       unittest.TestSuite.__init__(self)
       self.addTests(map(ABCDTests,('test_abcd',)))
    
       
testsuite = ABCDTestSuite