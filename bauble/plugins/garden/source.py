#
# source.py
#
import bauble
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.orm.session import object_session
from bauble.plugins.plants.geography import Geography


def source_markup_func(source):
    # TODO: should probably just make the source look and act like an accession
    # with the same markup and children in the view
    return source._accession, source


class Donation(bauble.Base):
    __tablename__ = 'donation'
    donor_id = Column(Integer, ForeignKey('donor.id'), nullable=False)
    donor_acc = Column(Unicode(32)) # donor's accession id
    notes = Column(UnicodeText)
    date = Column(Date)
    accession_id = Column(Integer, ForeignKey('accession.id'), nullable=False)

    def __str__(self):
        return 'Donation from %s' % (self.donor or repr(self))

# donation_table = bauble.Table('donation', bauble.metadata,
#                        Column('id', Integer, primary_key=True),
#                        Column('donor_id', Integer, ForeignKey('donor.id'),
#                               nullable=False),
#                        Column('donor_acc', Unicode(32)), # donor's accession id
#                        Column('notes', UnicodeText),
#                        Column('date', Date),
#                        Column('accession_id', Integer,
#                               ForeignKey('accession.id'), nullable=False))

# class Donation(bauble.BaubleMapper):

#     def __str__(self):
#         return 'Donation from %s' % (self.donor or '<not set>')

# TODO: is there anyway to get this date format from BaubleMeta, also
#    i don't know why setting dateFormat here give me an error about getting
#    the date in unicode instead of a DateTimeCol eventhough i set this
#    column using a datetime object
# TODO: deleting this foreign accession deletes this collection
# TODO: this shouldn't be allowed to be None, UPDATE: what the hell am i talking about
# TODO: collector combined with collectors_code should be a unique key, need to
# also indicate this in the UI
# TODO: should provide a collection type: alcohol, bark, boxed, cytological, fruit, illustration, image, other, packet, pollen, print, reference, seed, sheet, slide, transparency, vertical, wood.....see HISPID standard, in general need to be more herbarium aware

# TODO: create a DMS column type to hold latitude and longitude,
# should probably store the DMS data as a string in decimal degrees
class Collection(bauble.Base):
    __tablename__ = 'collection'
    collector = Column(Unicode(64)),
    collectors_code = Column(Unicode(50))
    date = Column(Date)
    locale = Column(UnicodeText, nullable=False)
    latitude = Column(Float)
    longitude = Column(Float)
    gps_datum = Column(Unicode(32))
    geo_accy = Column(Float)
    elevation = Column(Float)
    elevation_accy = Column(Float)
    habitat = Column(UnicodeText)
    geography_id = Column(Integer, ForeignKey('geography.id'))
    notes = Column(UnicodeText)
    accession_id = Column(Integer, ForeignKey('accession.id'), nullable=False)

    def __str__(self):
        return 'Collection at %s' % (self.locale or repr(self))

# collection_table = bauble.Table('collection', bauble.metadata,
#                          Column('id', Integer, primary_key=True),
#                          Column('collector', Unicode(64)),
#                          Column('collectors_code', Unicode(50)),
#                          Column('date', Date),
#                          Column('locale', UnicodeText, nullable=False),
#                          Column('latitude', Float),
#                          Column('longitude', Float),
#                          Column('gps_datum', Unicode(32)),
#                          Column('geo_accy', Float),
#                          Column('elevation', Float),
#                          Column('elevation_accy', Float),
#                          Column('habitat', UnicodeText),
#                          Column('geography_id', Integer,
#                                 ForeignKey('geography.id')),
#                          Column('notes', UnicodeText),
#                          Column('accession_id', Integer,
#                                 ForeignKey('accession.id'), nullable=False))

# class Collection(bauble.BaubleMapper):

#     def __str__(self):
#         return 'Collection at %s' % (self.locale or '<not set>')


# NOTE:
# 1. Donation has a donor property that is added as a backref Donor mapper
# 2. Both Donation and Collection have an "_accession" property created as
# a backref in the Accession mapper
#mapper(Donation, donation_table)
#mapper(Collection, collection_table)


