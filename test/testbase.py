import unittest
from optparse import OptionParser
from sqlalchemy import *
from sqlalchemy.orm import *

# TODO: print a tests docs and quit
parser = OptionParser()
parser.add_option('-d', '--docs', dest='docs', default=False,
                  help='print the test\'s docs')

(options, args) = parser.parse_args()

species_table = None
genus_table = None
vernacular_name_table = None

class Genus(object):
    def __str__(self):
        return self.genus

class Species(object):
    def __str__(self):
        return '%s %s' % (self.genus, self.sp)
        
class VernacularName(object):
    def __str__(self):
        return self.name


class BasicTestCase(unittest.TestCase):
            
    def __init__(self, *args, **kwargs):
        super(BasicTestCase, self).__init__(*args, **kwargs)
        self.uri = 'sqlite:///:memory:'
        global_connect(self.uri)
        
    def setUp(self):                
        self.engine = default_metadata.engine
        self.session = create_session()
        
    def tearDown(self):
        self.session.close()
        
        
class BaubleTestCase(unittest.TestCase):
    
    #def __init__(self, *args, **kwargs):
    #    super(BaubleTestCase, self).__init__(*args, **kwargs)
    # TODO: we need a way to explicitly set a connection for instead
    # of having to choose one from the connection manager
    def setUp(self):
        super(BaubleTestCase, self).setUp()
        import bauble, bauble.plugins, bauble.prefs, bauble._app
        bauble.plugins.load()
        bauble.prefs.prefs.init()
        self.uri = 'sqlite:///:memory:'        
        bauble._app.BaubleApp.open_database(self.uri)
        self.engine = default_metadata.engine
        self.session = create_session()
        
    def tearDown(self):
        self.session.close()
        
        
        
    
class SchemaTestCase(BasicTestCase):
        
    def tearDown(self):
        super(SchemaTestCase, self).tearDown()
        default_metadata.drop_all()
        
    def insert(self, table, *values):
        return table.insert().execute(*values)
    
        
    def setUp(self):    
        super(SchemaTestCase, self).setUp()
        global species_table
        species_table = Table('species',
                          Column('id', Integer, primary_key=True),
                          Column('sp', String),
                          Column('genus_id', Integer, ForeignKey('genus.id')),
                          Column('default_vernacular_name_id', Integer, 
                                 ForeignKey('vernacular_name.id')))
    
        
                            
        global vernacular_name_table
        vernacular_name_table = Table('vernacular_name',
                                      Column('id', Integer, primary_key=True),
                                      Column('name', Unicode(128), unique='vn_index'),
                                      Column('language', Unicode(128), unique='vn_index'),
                                      Column('species_id', Integer, 
                                             ForeignKey('species.id'), unique='vn_index'))
                                             
       
        
        global genus_table        
        genus_table = Table('genus',
                            Column('id', Integer, primary_key=True),
                            Column('genus', String))
    
                            
#        mapper(Species, species_table)
#        mapper(Genus, genus_table,
#               properties = {'species': relation(Species, backref=backref('genus', lazy=False),
#                                                 order_by=['sp'])})
#        mapper(VernacularName, vernacular_name_table)
        
        default_metadata.create_all()
