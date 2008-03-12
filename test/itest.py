#!/usr/bin/env python
#
# itest.py
#
# provides an interactive test environment
#
import sqlalchemy as sa
from sqlalchemy.orm import *

# TODO: should create another itest that will refect an existing
# database so that i can run tests against something more similar to a
# normal bauble database

import logging
logging.basicConfig()

uri = 'sqlite:///:memory:'

metadata = sa.MetaData()

class MyTable(sa.Table):

    def __init__(self, *args, **kwargs):
        super(MyTable, self).__init__(*args, **kwargs)
        self.append_column(sa.Column('_created', sa.DateTime(True),
                                     default=sa.func.now()))
        self.append_column(sa.Column('_last_updated', sa.DateTime(True),
                                     default=sa.func.now(),
                                     onupdate=sa.func.now()))

species_table = sa.Table('species', metadata,
                        sa.Column('id', sa.Integer,
                                  sa.Sequence('species_id_seq'),
                                  primary_key=True),
                        sa.Column('sp', sa.Text, nullable=False),
                        sa.Column('genus_id', sa.Integer,
                                  sa.ForeignKey('genus.id')),
                        sa.Column('default_vernacular_name_id', sa.Integer))


vernacular_name_table = sa.Table('vernacular_name', metadata,
                                 sa.Column('id', sa.Integer, primary_key=True),
                                 sa.Column('name', sa.Unicode(128),
                                           nullable=False),
                                 sa.Column('species_id', sa.Integer,
                                           sa.ForeignKey('species.id')))

genus_table =  sa.Table('genus', metadata,
                        sa.Column('id', sa.Integer, primary_key=True),
                        sa.Column('genus', sa.Text, nullable=False))

#for table in [species_table, vernacular_name_table, genus_table]:
for table in [genus_table, species_table]:
##    continue
#    default = 'today'
    default = sa.func.lower('today')
#    default = sa.func.now()
#    default = None
    table.append_column(sa.Column('_created',
                                  sa.String(100),
                                  #sa.DateTime(True),
                                  default=default))

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
        properties = {'vn': relation(VernacularName, lazy=False, uselist=False,
                                     cascade='all, delete-orphan',
                                     #backref=backref('species')
                                     )})
genus_mapper = mapper(Genus, genus_table,
       properties = {'species': relation(Species, lazy=False,
                                         backref=backref('genus',
                                                cascade='all, delete-orphan')
                                         )})#, order_by=['sp'])})
mapper(VernacularName, vernacular_name_table)

engine = sa.create_engine(uri)
engine.connect()
metadata.bind = engine
#session = create_session()
Session = sessionmaker(bind=engine, autoflush=False, transactional=True)
session = Session()

metadata.create_all()
genus_table.insert().execute({'genus': 'Maxillaria'})
#species_table.insert().execute({'genus_id': 1, 'sp': 'sp'})

#logging.getLogger('sqlalchemy').setLevel(logging.DEBUG)
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)

# *******************
# where the action is
# *******************

#g = session.load(Genus, 1)
#s = session.load(Species, 1)
g = Genus()
s = Species()
session.save(g)
session.save(s)
g.genus = "Genus"
s.genus = g
s.sp = "sp"

vn = VernacularName()
session.save(vn)
s.vn = vn

def print_state(obj, sess):
    print '%s: %s' % (obj, [obj in sess.new, obj in sess.dirty, obj in sess.deleted])
try:
    print_state(g, session)
    session.commit()
except:
    print_state(g, session)
    session.rollback()
vn.name = u"something"
## session.clear()
## session.save(g)
## session.save(s)
## session.save(vn)
session.expunge(g)
session.expunge(s)
#session.expunge(vn)
session.flush()
session.save(g)
session.save(s)
session.save(vn)
#print_state(g, session)
session.commit()
#print_state(g, session)
print s
