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
    shows_as = Column(Unicode(48), nullable=False)
    defines = Column(Unicode(12))


class Taxon(db.Base, db.WithNotes):
    __tablename__ = 'taxon'
    rank_id = Column(ForeignKey('rank.id'), nullable=False)
    ## the Taxon.rank property is defined as backref in Rank.taxa
    epithet = Column(Unicode(48))
    author = Column(UnicodeText())
    year = Column(Integer)

    parent_id = Column(Integer, ForeignKey('taxon.id'), nullable=False)
    accepted_id = Column(Integer, ForeignKey('taxon.id'), nullable=True)

Taxon.children = relationship(Taxon, foreign_keys=Taxon.parent_id)
Taxon.synonyms = relationship(Taxon, foreign_keys=Taxon.accepted_id)

def compute_serializable_fields(cls, session, keys):
    result = {'taxon': None}

    genus_dict = {'epithet': keys['genus']}
    result['taxon'] = Taxon.retrieve_or_create(
        session, taxon_keys, create=False)

    return result

TaxonNote = db.make_note_class('Taxon', compute_serializable_fields)

Rank.taxa = relation('Taxon', cascade='all, delete-orphan',
                     order_by=[Taxon.epithet],
                     backref=backref('rank', uselist=False))

