#
# distribution.py
# 
# Description: schema for the TDWG World Geographical Scheme for Recording Plant 
#    Distributions, Edition 2
#
import os
import gtk
from sqlalchemy import *
import bauble


# FIXME: there are lots of problems with these tables
# 1. in some tables there is a row with no real values, i think this means
# from a cultivated source with no know origin but it should be verified and
# more intuitive
# 2. some row values that have default=None shouldn't, they are only set that
# way so that the mystery row with no values will import correctly
# 3. other stuff...


# TODO: don't allow continent to be deleted if region exists, in general
# fix cascading

# TODO: i wonder if it would be possible to store this in one table
# and remove some of the data we're not using

# level: the rank, this combined with the parent_id would give it's 
# exact place in the combo, e.g. level=0 would be the top level so
# we could do 
#for one in distribution_table.select(level=0):
#    for two in distribution_table.select(level=0):
# actually this way we really only need to know what is the top level
# and everything else can follow from the parent
#class GeographyMapper(bauble.BaubleMapper):
#    
#    _subdivisions_field = None
#    def _get_subdivisions(self):
#        '''
#        return all objects considered inside this geographic region
#        according to self._subdivisions_field
#        '''    
#        if self._subdivisions_field is None:
#            return None
#        
#        # select and return the subvisions
#        return []
#        
#    subdivisions = property(_get_subdivisions)
    

#
# place table (the gazetteer)
#
# TODO: if this is None then i think it means cultivated, should really do
        # something about this, like change the None to cultivated
        # NOTE: these two don't have names for some reason
        # ID*Gazetteer*L1 code*L2 code*L3 code*L4 code*Kew region code*Kew region subdivision*Kew region*Synonym*Notes
        #331**2,00*24,00*SOC*SOC-OO*10,00*C*North East Tropical Africa**
        #333**3,00*33,00*TCS*TCS-AB*2,00*A*Orient**
# TODO: should synonym be a key into this table
# NOTE: Mansel I. and Manu'a don't have continents ???

def region_markup_func(region):
    if region.continent is None:
        return region
    else:
        return region, region.continent

def botanicalcountry_markup_func(bc):
    if bc.region is None:
        return bc
    else:
        return bc, bc.region


def basicunit_markup_func(bu):
    if bu.botanical_country is None:
        return bu
    else:
        return bu, bu.botanical_country


def place_markup_func(place):
    if place.basic_unit is None:
        return place
    else:
        return place, place.basic_unit


place_table = Table('place',
                    Column('id', Integer, primary_key=True),
                    Column('place', Unicode(64)),
                    Column('code', String(4), unique=True, nullable=False),
                    Column('synonym', Unicode(255)),
                    Column('notes', Unicode),
                    Column('continent_id', Integer, ForeignKey('continent.id')),
                    Column('region_id', Integer, ForeignKey('region.id')),
                    Column('botanical_country_id', Integer, 
                           ForeignKey('botanical_country.id')),
                    Column('basic_unit_id', Integer, ForeignKey('basic_unit.id')),
                    Column('_created', DateTime, default=func.current_timestamp()),
                    Column('_last_updated', DateTime, default=func.current_timestamp(), 
                           onupdate=func.current_timestamp()))

class Place(object):

    def __str__(self): 
        return self.place or ''

mapper(Place, place_table, order_by='place')


#
# kew_region table
#
# TODO: one column in the data has none, i don't know why, i think it means
        # that its cultivated and its origin is unknown, neother code or region
        # should really be None
kew_region_table = Table('kew_region',
                         Column('id', Integer, primary_key=True),
                         Column('code', Integer, unique=True, nullable=False),
                         Column('region', Unicode(64)),
                         Column('subdiv', String(1)),
                         Column('_created', DateTime, default=func.current_timestamp()),
                         Column('_last_updated', DateTime, default=func.current_timestamp(), 
                                onupdate=func.current_timestamp()))

class KewRegion(object):
    
    def __str__(self):         
        if self.region is None: 
            return "" # **** TODO: don't do it
        if self.subdiv is not None:
            return "%s - %s" % (self.region, self.subdiv)
        return self.region
    
mapper(KewRegion, kew_region_table,
#       properties={'places': relation(Place, backref='kew_region')},
       order_by='region')


#
# state table
#
state_table = Table('state',
                    Column('id', Integer, primary_key=True),
                    Column('state', Unicode(64), unique=True, nullable=False),
                    Column('code', String(8), unique=True, nullable=False),
                    Column('iso_code', String(8)),
                    Column('ed2_status', Unicode(64)),
                    Column('notes', Unicode),
                    Column('area_id', Integer, ForeignKey('area.id')),
                    Column('_created', DateTime, default=func.current_timestamp()),
                    Column('_last_updated', DateTime, default=func.current_timestamp(), 
                           onupdate=func.current_timestamp()))

class State(object):

    def __str__(self): 
        return self.state

mapper(State, state_table,
#       properties={'places': relation(Place, backref='state')},
       order_by='state')


#
# area table
#
area_table = Table('area',
                   Column('id', Integer, primary_key=True),
                   Column('area', Unicode(64), unique=True, nullable=False),
                   Column('code', String(5), unique=True, nullable=False),
                   Column('iso_code', String(4)),
                   Column('ed2_status', Unicode(64)),
                   Column('notes', Unicode),
                   Column('region_id', Integer, ForeignKey('region.id')),
                   Column('_created', DateTime, default=func.current_timestamp()),
                   Column('_last_updated', DateTime, default=func.current_timestamp(), 
                          onupdate=func.current_timestamp()))

class Area(object):
    
    def __str__(self): 
        return self.area
    
mapper(Area, area_table,
       properties={'states': relation(State, cascade='all, delete-orphan',
                                      backref='area')},
       order_by='area')


# 
# basic_unit table
# 
basic_unit_table = Table('basic_unit',
                         Column('id', Integer, primary_key=True),
                         Column('name', Unicode(64)),
                         Column('code', String(8), unique=True, nullable=False),
                         Column('iso_code', String(8)),
                         Column('ed2_status', Unicode(64)),
                         Column('notes', Unicode),
                         Column('botanical_country_id', Integer, 
                                ForeignKey('botanical_country.id')),
                         Column('_created', DateTime, default=func.current_timestamp()),
                         Column('_last_updated', DateTime, default=func.current_timestamp(), 
                                onupdate=func.current_timestamp()))

class BasicUnit(object):
        
    def __str__(self): 
        return self.name

mapper(BasicUnit, basic_unit_table,
       properties = {'places': relation(Place, cascade='all, delete-orphan',
                                        backref='basic_unit')},
       order_by='name')


#
# botanical_country table
#
botanical_country_table = Table('botanical_country',
                                Column('id', Integer, primary_key=True),
                                Column('name', Unicode(64), nullable=False, unique=True),
                                Column('code', String(5), nullable=False, unique=True),
                                Column('iso_code', String(4)),
                                Column('ed2_status', Unicode(64)),
                                Column('notes', Unicode),
                                Column('region_id', Integer, ForeignKey('region.id')),
                                Column('_created', DateTime, default=func.current_timestamp()),
                                Column('_last_updated', DateTime, default=func.current_timestamp(), 
                                       onupdate=func.current_timestamp()))

class BotanicalCountry(object):
    
    def __str__(self): 
        return self.name
    
mapper(BotanicalCountry, botanical_country_table,       
       properties={'basic_units':
                   relation(BasicUnit, cascade='all, delete-orphan',
                            backref='botanical_country')},
       order_by='name')


# 
# region table
#
# TODO: iso_code isn't even used, remove it
region_table = Table('region',
                     Column('id', Integer, primary_key=True),
                     Column('region', Unicode(64), nullable=False, unique=True),
                     Column('code', Integer, nullable=False, unique=True),
                     Column('iso_code', String(1)),
                     Column('continent_id', Integer, ForeignKey('continent.id')),
                     Column('_created', DateTime, default=func.current_timestamp()),
                     Column('_last_updated', DateTime, default=func.current_timestamp(), 
                            onupdate=func.current_timestamp()))
            
class Region(object):
    
    def __str__(self): 
        return self.region

mapper(Region, region_table,
       properties={'botanical_countries': 
                   relation(BotanicalCountry, cascade='all, delete-orphan',
                            backref='region')},
       order_by='region')


# 
# continent table
#
continent_table = Table('continent',
                        Column('id', Integer, primary_key=True),
                        Column('continent', Unicode(24), nullable=False, unique=True) ,       
                        Column('code', Integer, nullable=False, unique=True),
                        Column('_created', DateTime, default=func.current_timestamp()),
                        Column('_last_updated', DateTime, default=func.current_timestamp(), 
                               onupdate=func.current_timestamp()))

class Continent(object):
    
    def __str__(self): 
        return self.continent
    
mapper(Continent, continent_table,
       properties = {'regions': relation(Region, cascade='all, delete-orphan',
                                         backref='continent')},
       order_by='continent')


