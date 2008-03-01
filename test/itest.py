#
# itest.py
#
# provides an interactive test environment
#
from sqlalchemy import *
from sqlalchemy.orm import *

# TODO: should create another itest that will refect an existing
# database so that i can run tests against something more similar to a
# normal bauble database

import logging
logging.basicConfig()

uri = 'sqlite:///:memory:'


metadata = MetaData()

species_table = Table('species', metadata,
                  Column('id', Integer, Sequence('species_id_seq'),
                         primary_key=True),
                  Column('sp', Text),
                  Column('genus_id', Integer, ForeignKey('genus.id')),
                  Column('default_vernacular_name_id', Integer))
#                         ForeignKey('vernacular_name.id')))


vernacular_name_table = Table('vernacular_name', metadata,
                              Column('id', Integer, primary_key=True),
                              Column('name', Unicode(128)),
                              Column('language', Unicode(128)),
                              Column('species_id', Integer,
                                     ForeignKey('species.id')))

genus_table = Table('genus', metadata,
                    Column('id', Integer, primary_key=True),
                    Column('genus', Text))

class Genus(object):
    def __str__(self):
        return self.genus

class Species(object):
    def __str__(self):
        return '%s %s' % (self.genus, self.sp)

class VernacularName(object):
    def __str__(self):
        return self.name

species_mapper = mapper(Species, species_table,
       properties = {'vn': relation(VernacularName, lazy=False,
                                     backref=backref('species'))})
genus_mapper = mapper(Genus, genus_table,
       properties = {'species': relation(Species, lazy=False,
                                         backref=backref('genus'))})#, order_by=['sp'])})
mapper(VernacularName, vernacular_name_table)

#global_connect(uri)
engine = create_engine(uri)
engine.connect()
metadata.bind = engine
session = create_session()

metadata.create_all()
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




