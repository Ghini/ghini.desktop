#
# meta.py
#
import bauble
from datetime import datetime
from sqlalchemy import *
from sqlalchemy.orm import mapper

VERSION_KEY=u'version'
CREATED_KEY=u'created'
REGISTRY_KEY=u'registry'

bauble_meta_table = bauble.Table('bauble', bauble.metadata,
                          Column('id', Integer, primary_key=True),
                          Column('name', Unicode(64), unique=True),
                          Column('value', Unicode))


class BaubleMeta(object):

##     version = 'version'
##     created = 'created'

    def __init__(self, name=None, value=None):
        self.name = name
        self.value = value


    def __str__(self):
        return '%s=%s' % (self.name, self.value)



mapper(BaubleMeta, bauble_meta_table)
