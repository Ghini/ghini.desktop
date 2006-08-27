# 
# source.py
#

from bauble import BaubleMapper
from sqlalchemy import *
from sqlalchemy.orm.session import object_session


# TODO: don't allow donor to be deleted if donor still has donations
# TODO: maybe change donor_acc to donor_code
donation_table = Table('donation',
                       Column('id', Integer, primary_key=True),
                       Column('donor_id', Integer, ForeignKey('donor.id'), 
                              nullable=False),
                       Column('donor_acc', Unicode(32)),  # donor's accession id
                       Column('notes', Unicode),
                       Column('date', Date),
                       Column('accession_id', Integer, 
                              ForeignKey('accession.id'), nullable=False))

class Donation(BaubleMapper):
        
    def __str__(self):
        return 'Donation from %s' % (self.donor or '<not set>')
        

# TODO: change coll_id to collectors_code
# TODO: change coll_date to just date
# TODO: is there anyway to get this date format from BaubleMeta, also
#    i don't know why setting dateFormat here give me an error about getting
#    the date in unicode instead of a DateTimeCol eventhough i set this
#    column using a datetime object    
# TODO: deleting this foreign accession deletes this collection
# TODO: this shouldn't be allowed to be None
collection_table = Table('collection',
                         Column('id', Integer, primary_key=True),
                         Column('collector', Unicode(64)),
                         Column('coll_id', Unicode(50)),
                         Column('coll_date', Date),
                         Column('locale', Unicode, nullable=False),
                         Column('latitude', Float),
                         Column('longitude', Float),
                         Column('geo_accy', Float),
                         Column('elevation', Float),
                         Column('elevation_accy', Float),
                         Column('habitat', Unicode),
                         Column('notes', Unicode),
                         Column('country_id', Integer, ForeignKey('country.id')),
                         Column('accession_id', Integer, 
                                ForeignKey('accession.id'), nullable=False))

class Collection(BaubleMapper):
        
    def __str__(self):
        return 'Collection at %s' % (self.locale or '<not set>')
    
from bauble.plugins.garden.accession import Accession

mapper(Donation, donation_table)
#mapper(Donation, donation_table, 
#       properties = {'accession': relation(Accession, uselist=False, 
#                                           backref=backref('_donation', uselist=False, 
#                                                            cascade='all, delete-orphan'))})

#                                                           private=True))})
#                                           backref=backref('_donation',
#                                                           cascade='all, delete-orphan',
#                                                           uselist=False))})#, private=True))})
mapper(Collection, collection_table)
#mapper(Collection, collection_table,
#       properties = {'accession': relation(Accession, uselist=False,
#                                           backref=backref('_collection', uselist=False, 
#                                                           cascade='all, delete-orphan'))})

#                                                           private=True))})
#                                           backref=backref('_collection',
#                                                           cascade='all, delete-orphan',
#                                                           uselist=False))})#, private=True))})
    
from bauble.plugins.garden.donor import Donor

#class Collection(BaubleTable):
#    
#    _cacheValue = False
#    
#    collector = UnicodeCol(length=50, default=None)  # primary collector's name
##    collector2 = UnicodeCol(length=50, default=None) # additional collectors name
#    coll_id = UnicodeCol(length=50, default=None)    # collector's/collection id
#    
#    
#    # collection date
#    # TODO: is there anyway to get this date format from BaubleMeta, also
#    # i don't know why setting dateFormat here give me an error about getting
#    # the date in unicode instead of a DateTimeCol eventhough i set this
#    # column using a datetime object    
#    #coll_date = DateCol(default=None, dateFormat='%d/%m/%Y')    
#    coll_date = DateCol(default=None)
#    
#    locale = UnicodeCol() # text of where collected
#    
#    # this could also just be a float and we could convert back and 
#    # forth to deg, min, sec with a utility function
#    latitude = FloatCol(default=None)
#    longitude = FloatCol(default=None)
#    geo_accy = IntCol(default=None) # geo accuracy in meters
#    
#    # should altitude be a plus or minus and get rid of depth
#    elevation = FloatCol(default=None) # altitude
#    elevation_accy = FloatCol(default=None) # altitude accuracy
#    #altitude_max = IntCol(default=None) # maximum altitude
#    #altitude_mac_accy = IntCol(default=None) # maximum altitude accuracy
#    
#    # depth under water, same as minus altitude
#    #depth = FloatCol(default=None) 
#    
#    habitat = UnicodeCol(default=None) # habitat, free text
#    notes = UnicodeCol(default=None)
#    
#    # we'll have to set a default to none here because of the way our editors
#    # are set up have to commit this table and then set the foreign key later,
#    # we have to be careful we don't get dangling tables without an accession
#    #
#    # these are only for recording plant distribution and should
#    # be put in a distribution table so the species can do a single join
#    # on them, the only thing we need here is the country name
#    #area = ForeignKey('Areas', default=None)
#    #region = ForeignKey('Regions', default=None)
#    #place = ForeignKey('Places', default=None)
#    #state = ForeignKey('States', default=None)    
#    country = ForeignKey('Country', default=None) # where collected
#    
#    # deleting this foreign accession deletes this collection
#    # TODO: this shouldn't be allowed to be None
#    accession = ForeignKey('Accession', default=None, cascade=True)
#    
#    def __str__(self):
#        #if self.label == None: 
#        #    return self.locale
#        #return self.label
#        return self.locale 


