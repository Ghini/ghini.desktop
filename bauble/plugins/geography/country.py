
from sqlalchemy import *

country_table = Table('country',
                      Column('id', Integer, primary_key=True),
                      Column('country', Unicode(50)),
                      Column('code', String(2)),
                      Column('_created', DateTime, default=func.current_timestamp()),
                      Column('_last_updated', DateTime, default=func.current_timestamp(), 
                             onupdate=func.current_timestamp()))

class Country(object):    
    
    def __str__(self):
        return self.country
    
mapper(Country, country_table)