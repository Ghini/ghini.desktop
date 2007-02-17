#
# itest.py
#
# provides an interactive test environment
#
from sqlalchemy import *

import logging
logging.basicConfig()

uri = 'sqlite:///:memory:'

species_table = Table('species',
                  Column('id', Integer, primary_key=True),
                  Column('sp', String),
                  Column('genus_id', Integer, ForeignKey('genus.id')),
                  Column('default_vernacular_name_id', Integer))
#                         ForeignKey('vernacular_name.id')))


                    

vernacular_name_table = Table('vernacular_name',
                              Column('id', Integer, primary_key=True),
                              Column('name', Unicode(128)),
                              Column('language', Unicode(128)),
                              Column('species_id', Integer, 
                                     ForeignKey('species.id')))

genus_table = Table('genus',
                    Column('id', Integer, primary_key=True),
                    Column('genus', String))

class Genus(object):
    def __str__(self):
        return self.genus

class Species(object):
    def __str__(self):
        return '%s %s' % (self.genus, self.sp)
        
class VernacularName(object):
    def __str__(self):
        return self.name
    
mapper(Species, species_table,
       properties = {'vn': relation(VernacularName, lazy=False,
                                     backref=backref('species'))})
genus_mapper = mapper(Genus, genus_table,
       properties = {'species': relation(Species, lazy=False,
                                         backref=backref('genus'))})#, order_by=['sp'])})
mapper(VernacularName, vernacular_name_table)

global_connect(uri)
engine = default_metadata.engine
session = create_session()

default_metadata.create_all()
genus_table.insert().execute({'genus': 'Maxillaria'})
species_table.insert().execute({'genus_id': 1, 'sp': 'sp'})

#logging.getLogger('sqlalchemy').setLevel(logging.DEBUG)
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)

#
# where the action is
#

print '*********** query *********'
g = session.query(Genus).get_by(id=1)
print '*********** genus *********'
print str(g)

print '*********** sp **************'
print str(g.species)

print '********* vernacular ***********'
print str(g.species[0].vn)




