#
# meta.py
#
import bauble
from datetime import datetime
from sqlalchemy import *
from sqlalchemy.orm import mapper

VERSION_KEY = u'version'
CREATED_KEY = u'created'
REGISTRY_KEY = u'registry'

# date format strings:
# yy - short year
# yyyy - long year
# dd - number day, always two digits
# d - number day, two digits when necessary
# mm -number month, always two digits
# m - number month, two digits when necessary
DATE_FORMAT_KEY = u'date_format'

class BaubleMeta(bauble.Base):
    __tablename__ = 'bauble'
    name = Column(Unicode(64), unique=True)
    value = Column(UnicodeText)

