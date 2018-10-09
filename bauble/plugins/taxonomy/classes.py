# -*- coding: utf-8 -*-
#
# Copyright 2018 Mario Frasca <mario@anche.no>.
#
# This file is part of ghini.desktop.
#
# ghini.desktop is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ghini.desktop is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ghini.desktop. If not, see <http://www.gnu.org/licenses/>.
#


import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

from sqlalchemy import (
    Column, Unicode, Integer, Float, ForeignKey, UnicodeText,
    UniqueConstraint, func, and_)
from sqlalchemy.orm import relation, backref, validates, synonym, relationship

from bauble import db


class Rank(db.Base):
    __tablename__ = 'rank'
    name = Column(Unicode(12), nullable=False)
    depth = Column(Float, nullable=False)
    shows_as = Column(Unicode(48), nullable=False, default='')
    defines = Column(Unicode(12), nullable=False, default='')


class Taxon(db.Base, db.WithNotes):
    __tablename__ = 'taxon'
    rank_id = Column(ForeignKey('rank.id'), nullable=False)
    rank = relationship('Rank', backref=backref('taxa'))
    ## the Taxon.rank property is defined as backref in Rank.taxa
    epithet = Column(Unicode(48))
    author = Column(UnicodeText())
    year = Column(Integer)

    parent_id = Column(Integer, ForeignKey('taxon.id'), nullable=False)
    accepted_id = Column(Integer, ForeignKey('taxon.id'), nullable=True)

    def __getattr__(self, name, values=None):
        if name.startswith('_sa'):  # it's a SA field, don't even try to look it up
            raise AttributeError(name)
        if values is None:
            from sqlalchemy.orm.session import object_session
            from bauble.utils import get_distinct_values
            values = get_distinct_values(Rank.defines, object_session(self))
        if name not in values:
            super().__getattr__(self)
        print(self.epithet, self.parent)
        if name == self.rank.defines:
            if name == 'binomial':
                return self.parent.genus + ' ' + self.epithet
            else:
                return self.epithet
        if self.parent is not self:
            return self.parent.__getattr__(name, values)
        else:
            raise AttributeError(name)

    def show(self):
        def convert(match):
            item = match.group(0)
            field = item[1:]
            return getattr(self, field)
        import re
        return re.sub(r'\.[\w]+', convert, self.rank.shows_as.replace(']', '').replace('[', ''))

    @property
    def complete(self):
        return self.parent.show()


Taxon.children = relationship(Taxon, backref=backref('parent', remote_side=[Taxon.id]), foreign_keys=[Taxon.parent_id])
Taxon.synonyms = relationship(Taxon, backref=backref('accepted', remote_side=[Taxon.id]), foreign_keys=[Taxon.accepted_id])

def compute_serializable_fields(cls, session, keys):
    result = {'taxon': None}

    genus_dict = {'epithet': keys['genus']}
    result['taxon'] = Taxon.retrieve_or_create(
        session, taxon_keys, create=False)

    return result

TaxonNote = db.make_note_class('Taxon', compute_serializable_fields)
