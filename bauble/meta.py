#
# meta.py
#
from datetime import datetime
from sqlalchemy import *

VERSION_KEY='version'
CREATED_KEY='created'
REGISTRY_KEY='registry'

bauble_meta_table = Table('bauble',
                          Column('id', Integer, primary_key=True),
                          Column('name', Unicode(64), unique=True),
                          Column('value', Unicode),
                          Column('_created', DateTime(True),
                                 default=func.current_timestamp()),
                          Column('_last_updated', DateTime(True),
                                 default=func.current_timestamp(), 
                                 onupdate=func.current_timestamp())) 
        
class BaubleMeta(object):
    
##     version = 'version'
##     created = 'created'
    
    def __init__(self, name=None, value=None):
        self.name = name
        self.value = value


    def __str__(self):
        return '%s=%s' % (self.name, self.value)



mapper(BaubleMeta, bauble_meta_table)
