#
# geography.py
#
from datetime import datetime
from sqlalchemy import *
import bauble

geography_table = Table('geography',
                        Column('id', Integer, primary_key=True),
                        Column('name', String(255), nullable=False),
                        Column('tdwg_code', String(6)),
                        Column('iso_code', String(7)),
                        Column('parent_id', Integer,
                               ForeignKey('geography.id')),
                        Column('_created', DateTime,
                               default=func.current_timestamp()),
                        Column('_last_updated', DateTime,
                               default=func.current_timestamp(), 
                               onupdate=func.current_timestamp()))


class Geography(bauble.BaubleMapper):
    
    def __str__(self):
        return str(self.name)

# Geography mapper
Geography.mapper = mapper(Geography, geography_table,
    properties = {'children':
                  relation(Geography,
                           primaryjoin=geography_table.c.parent_id==geography_table.c.id,
                           cascade='all',
#                           order_by='name',
                           backref=backref("parent",
                                           remote_side=[geography_table.c.id])
                           )},
    order_by=[geography_table.c.name])
