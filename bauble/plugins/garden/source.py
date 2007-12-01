#
# source.py
#
import bauble
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.orm.session import object_session


def source_markup_func(source):
    # TODO: should probably just make the source look and act like an accession
    # with the same markup and children in the view
    return source._accession, source


donation_table = bauble.Table('donation', bauble.metadata,
                       Column('id', Integer, primary_key=True),
                       Column('donor_id', Integer, ForeignKey('donor.id'),
                              nullable=False),
                       Column('donor_acc', Unicode(32)), # donor's accession id
                       Column('notes', Unicode),
                       Column('date', Date),
                       Column('accession_id', Integer,
                              ForeignKey('accession.id'), nullable=False))

class Donation(bauble.BaubleMapper):

    def __str__(self):
        return 'Donation from %s' % (self.donor or '<not set>')

# TODO: is there anyway to get this date format from BaubleMeta, also
#    i don't know why setting dateFormat here give me an error about getting
#    the date in unicode instead of a DateTimeCol eventhough i set this
#    column using a datetime object
# TODO: deleting this foreign accession deletes this collection
# TODO: this shouldn't be allowed to be None, UPDATE: what the hell am i talking about
collection_table = bauble.Table('collection', bauble.metadata,
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
                         Column('geography_id', Integer,
                                ForeignKey('geography.id')),
                         Column('notes', Unicode),
                         Column('accession_id', Integer,
                                ForeignKey('accession.id'), nullable=False))

class Collection(bauble.BaubleMapper):

    def __str__(self):
        return 'Collection at %s' % (self.locale or '<not set>')


# NOTE:
# 1. Donation has a donor property that is added as a backref Donor mapper
# 2. Both Donation and Collection have an "_accession" property created as
# a backref in the Accession mapper
mapper(Donation, donation_table)
mapper(Collection, collection_table)


