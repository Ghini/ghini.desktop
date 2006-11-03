# 
# source.py
#

from bauble import BaubleMapper
from sqlalchemy import *
from sqlalchemy.orm.session import object_session

# TODO: a donation or collection string should include the accession
# number, at least in the search results and should use the accession infobox
# as well

def source_markup_func(source):
    return '%s (%s)' % (source.accession, source)

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
                              ForeignKey('accession.id'), nullable=False),
                       Column('_created', DateTime, default=func.current_timestamp()),
                       Column('_last_updated', DateTime, default=func.current_timestamp(), 
                              onupdate=func.current_timestamp()))

class Donation(BaubleMapper):
        
    def __str__(self):
        return 'Donation from %s' % (self.donor or '<not set>')
        
# TODO: is there anyway to get this date format from BaubleMeta, also
#    i don't know why setting dateFormat here give me an error about getting
#    the date in unicode instead of a DateTimeCol eventhough i set this
#    column using a datetime object    
# TODO: deleting this foreign accession deletes this collection
# TODO: this shouldn't be allowed to be None, UPDATE: what the hell am i talking about
collection_table = Table('collection',
                         Column('id', Integer, primary_key=True),
                         Column('collector', Unicode(64)),
                         Column('collectors_code', Unicode(50)),
                         Column('date', Date),
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
                                ForeignKey('accession.id'), nullable=False),
                         Column('_created', DateTime, default=func.current_timestamp()),
                         Column('_last_updated', DateTime, default=func.current_timestamp(), 
                                onupdate=func.current_timestamp()))

class Collection(BaubleMapper):
        
    def __str__(self):
        return 'Collection at %s' % (self.locale or '<not set>')
    

mapper(Donation, donation_table)
mapper(Collection, collection_table)

