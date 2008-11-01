#
# source.py
#
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.orm.session import object_session

import bauble
import bauble.db as db
import bauble.types as types
from bauble.plugins.plants.geography import Geography


def source_markup_func(source):
    # TODO: should probably just make the source look and act like an accession
    # with the same markup and children in the view
    return source.accession, source


class Donation(db.Base):
    """
    :Table name: donation

    :Columns:
        *donor_id*: :class:`sqlalchemy.types.Integer(ForeignKey('donor.id'), nullable=False)`

        *donor_acc*: :class:`sqlalchemy.types.Unicode(32)`

        *notes*: :class:`sqlalchemy.types.UnicodeText`

        *date*: :class:`bauble.types..Date`

        *accession_id*: :class:`sqlalchemy.types.Integer(ForeignKey('accession.id'), nullable=False)`


    :Properties:

      donor:
        created as a backref from the Donor mapper

      _accession:
        created as a backref from the Accession mapper _donation property
    """
    __tablename__ = 'donation'

    donor_id = Column(Integer, ForeignKey('donor.id'), nullable=False)
    donor_acc = Column(Unicode(32)) # donor's accession id
    notes = Column(UnicodeText)
    date = Column(types.Date)
    accession_id = Column(Integer, ForeignKey('accession.id'), nullable=False)

    def __str__(self):
        if self.donor:
            return 'Donation from %s' % self.donor
        else:
            return repr(self)


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
class Collection(db.Base):
    """
    :Table name: collection

    :Columns:
            *collector*: :class:`sqlalchemy.types.Unicode(64)`

            *collectors_code*: :class:`sqlalchemy.types.Unicode(50)`

            *date*: :class:`sqlalchemy.types.Date`

            *locale*: :class:`sqlalchemy.types.UnicodeText(nullable=False)`

            *latitude*: :class:`sqlalchemy.types.Float`

            *longitude*: :class:`sqlalchemy.types.Float`

            *gps_datum*: :class:`sqlalchemy.types.Unicode(32)`

            *geo_accy*: :class:`sqlalchemy.types.Float`

            *elevation*: :class:`sqlalchemy.types.Float`

            *elevation_accy*: :class:`sqlalchemy.types.Float`

            *habitat*: :class:`sqlalchemy.types.UnicodeText`

            *geography_id*: :class:`sqlalchemy.types.Integer(ForeignKey('geography.id'))`

            *notes*: :class:`sqlalchemy.types.UnicodeText`

            *accession_id*: :class:`sqlalchemy.types.Integer(ForeignKey('accession.id'), nullable=False)`


    :Properties:

    Also contains an _accession property that was created as a backref
    from the Accession mapper

    :Constraints:
    """
    __tablename__ = 'collection'

    # columns
    collector = Column(Unicode(64))
    collectors_code = Column(Unicode(50))
    date = Column(types.Date)
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



