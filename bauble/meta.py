#
# meta.py
#
from sqlalchemy import *

import bauble
import bauble.db as db
import bauble.utils as utils
from bauble.utils.log import debug

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

def get_default(name, default=None, session=None):
    """
    Get a BaubleMeta object with name.  If the default value is not
    None then a BaubleMeta object is returned with name and the
    default value given.  If a session instance is passed then we
    don't commit the session.
    """
    commit = False
    if not session:
        session = bauble.Session()
        commit = True
    query = session.query(BaubleMeta)
    meta = query.filter_by(name=name).first()
    if not meta and default is not None:
        meta = BaubleMeta(name=utils.utf8(name), value=default)
        session.add(meta)
    if commit:
        session.commit()
    return meta


class BaubleMeta(db.Base):
    __tablename__ = 'bauble'
    name = Column(Unicode(64), unique=True)
    value = Column(UnicodeText)
