#
# geography.py
#
from datetime import datetime
from sqlalchemy import *
from sqlalchemy.orm import *
import bauble
from bauble.view import ResultSet
from bauble.utils.log import debug


def get_species_in_geography(geo):
    # get all the geography children under geo
    from bauble.plugins.plants.species import SpeciesDistribution, \
         species_distribution_table, Species, species_table
    geo_kids = []
    # TODO: getting the kids is too slow, is there a better way?
    # TODO: it might be better to put this in a tasklet or something so
    # that we can atleast do a set_busy() on the gui so the user only clicks
    # on the item once, or just disable double clicking until everything has
    # expanded properly....that's probably not a bad idea in general, just
    # before we get an items children in the results view we should disable
    # clicking in the view and once the item has expanded we reenable it
    #
    # TODO: need to change this to use the new queries on the mapper
    # or to update the select statements if we don't want to create
    # full on Geography objects
    raise NotImplementedError
    kids_stmt = select([geography_table.c.id],
                       geography_table.c.parent_id==bindparam('parent_id'))
    def get_kids(parent_id):
        for kid_id, in kids_stmt.execute(parent_id=parent_id):
            geo_kids.append(kid_id)
            get_kids(kid_id)
        geo_kids.append(parent_id)
    get_kids(geo.id)
    session = object_session(geo)
    species_ids = select([species_distribution_table.c.species_id],
                    species_distribution_table.c.geography_id.in_(geo_kids))
    return ResultSet(session.query(Species).\
                     filter(species_table.c.id.in_(species_ids)))



class Geography(bauble.Base):
    __tablename__ = 'geography'

    # columns
    name = Column(Unicode(255), nullable=False)
    tdwg_code = Column(String(6))
    iso_code = Column(String(7))
    parent_id = Column(Integer, ForeignKey('geography.id'))


    def __str__(self):
        return self.name


# late bindings
Geography.children = relation(Geography,
                              primaryjoin=Geography.parent_id==Geography.id,
                              cascade='all',
                              backref=backref("parent",
                                    remote_side=[Geography.__table__.c.id]),
                              order_by=[Geography.name])

# geography_table = bauble.Table('geography', bauble.metadata,
#                         Column('id', Integer, primary_key=True),
#                         Column('name', Unicode(255), nullable=False),
#                         Column('tdwg_code', String(6)),
#                         Column('iso_code', String(7)),
#                         Column('parent_id', Integer,
#                                ForeignKey('geography.id')))



# class Geography(bauble.BaubleMapper):

#     def __str__(self):
#         return self.name

#     def __unicode__(self):
#         return self.name



# Geography mapper
# Geography.mapper = mapper(Geography, geography_table,
#     properties = {'children':
#         relation(Geography,
#                  primaryjoin=geography_table.c.parent_id==geography_table.c.id,
#                  cascade='all', backref=backref("parent",
#                                             remote_side=[geography_table.c.id])
#                  )},
#     order_by=[geography_table.c.name])
