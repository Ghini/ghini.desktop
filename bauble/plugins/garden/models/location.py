#
# Copyright 2008-2010 Brett Adams
# Copyright 2015 Mario Frasca <mario@anche.no>.
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
# location.py
#
from __future__ import annotations

import logging
from typing import Any, ClassVar, List

import bauble.utils as utils
from bauble.db import Base, Serializable, WithNotes, make_note_class

# from sqlalchemy import text
from sqlalchemy import Integer, Unicode, UnicodeText, asc, select
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

logger: Any = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def compute_serializable_fields(cls, session, keys):
    result = {"location": None}

    annotated_object_keys = {"code": keys["location"]}
    result["location"] = Location.retrieve_or_create(
        session, annotated_object_keys, create=False
    )

    return result


class Location(Base, Serializable, WithNotes):
    """
    :Table name: location

    :Columns:
        *name*:

        *description*:


    :Relation:
        *plants*:

    """

    __tablename__: str = "location"

    # columns
    # refers to beds by unique codes
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(Unicode(12), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(Unicode(80))
    description: Mapped[str] = mapped_column(UnicodeText)
    order_by: ClassVar[list[Any]] = [asc(name)]

    def search_view_markup_pair(self):
        """provide the two lines describing object for SearchView row."""
        if self.description is not None:
            return (
                utils.xml_safe(str(self)),
                utils.xml_safe(str(self.description)),
            )
        else:
            return utils.xml_safe(str(self))

    @validates("code", "name")
    def validate_stripping(self, key, value):
        if value is None:
            return None
        return value.strip()

    def __str__(self) -> str:
        if self.name:
            return f"({self.code}) {self.name}"
        else:
            return str(self.code)

    def has_accessions(self):
        """true if location is linked to at least one accession"""

        return False

    @classmethod
    def retrieve(cls, session, keys):
        stmt = cls.query_with_default_order().where(cls.code == keys["code"])
        return session.execute(stmt).scalar_one_or_none()

    def top_level_count(self):
        accessions = {p.accession for p in self.plants}
        species = {a.species for a in accessions}
        genera = {s.genus for s in species}
        return {
            (1, "Locations"): 1,
            (2, "Plantings"): len(self.plants),
            (3, "Living plants"): sum(p.quantity for p in self.plants),
            (4, "Accessions"): {a.id for a in accessions},
            (5, "Species"): {s.id for s in species},
            (6, "Genera"): {g.id for g in genera},
            (7, "Families"): {g.family.id for g in genera},
            (8, "Sources"): {
                a.source.source_detail.id
                for a in accessions
                if a.source and a.source.source_detail
            },
        }


# from .plant import PlantChange


LocationNote: Any = make_note_class("Location", Location, compute_serializable_fields)
Location.notes: Mapped[List["LocationNote"]] = relationship(
    "LocationNote",
    back_populates="location",
    cascade="all, delete-orphan",
    single_parent=True,
)
