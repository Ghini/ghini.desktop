#
# geography.py
#
from datetime import datetime

from sqlalchemy import *
from sqlalchemy.orm import *

import bauble
import bauble.db as db
from bauble.view import ResultSet
from bauble.utils.log import debug


def get_species_in_geography(geo):#, session=None):
    """
    Return all the Species that have distribution in geo
    """
    session = object_session(geo)
    if not session:
        ValueError('get_species_in_geography(): geography is not in a session')

    # get all the geography children under geo
    from bauble.plugins.plants.species_model import SpeciesDistribution, \
        Species
    # get the children of geo
    geo_table = geo.__table__
    master_ids = set([geo.id])
    # populate master_ids with all the geography ids that represent
    # the children of particular geography id
    def get_geography_children(parent_id):
        stmt = select([geo_table.c.id], geo_table.c.parent_id==parent_id)
        kids = [r[0] for r in db.engine.execute(stmt).fetchall()]
        for kid in kids:
            grand_kids = get_geography_children(kid)
            master_ids.update(grand_kids)
        return kids
    geokids = get_geography_children(geo.id)
    master_ids.update(geokids)
    q = session.query(Species).join(SpeciesDistribution).\
        filter(SpeciesDistribution.geography_id.in_(master_ids))
    return list(q)



class Geography(db.Base):
    """
    Represents a geography unit.

    :Table name: geography

    :Columns:
        *name*:

        *tdwg_code*:

        *iso_code*:

        *parent_id*:

    :Properties:
        *children*:

    :Constraints:
    """
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
