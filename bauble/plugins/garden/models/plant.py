#
# Copyright 2008-2010 Brett Adams
# Copyright 2015-2017 Mario Frasca <mario@anche.no>.
# Copyright 2017 Jardín Botánico de Quito
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
"""
Defines the plant table and handled editing plants
"""
from __future__ import annotations

import logging
from typing import Any, ClassVar, Optional

import bauble.btypes as types
import bauble.meta as meta
import bauble.utils as utils
from bauble.db import Base, DefiningPictures, Serializable, WithNotes, make_note_class
from bauble.plugins.garden.constants import acc_type_values
from bauble.search import SearchStrategy

# from sqlalchemy import text
from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    Unicode,
    UniqueConstraint,
    asc,
    select,
)
from sqlalchemy.orm import Mapped, mapped_column, object_mapper, relationship, validates
from sqlalchemy.orm.session import object_session

# from sqlalchemy.exc import DBAPIError


logger: Any = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# TODO: might be worthwhile to have a label or textview next to the
# location combo that shows the description of the currently selected
# location

plant_delimiter_key: str = "plant_delimiter"
default_plant_delimiter: str = "."




class PlantSearch(SearchStrategy):

    def __init__(self) -> None:
        super().__init__()

    def search(self, text, session):
        """returns a result if the text looks like a quoted plant code

        special search strategy, can't be obtained in MapperSearch
        """
        from bauble.plugins.garden.models import Accession
        super().search(text, session)

        if text[0] == text[-1] and text[0] in ['"', "'"]:
            text = text[1:-1]
        else:
            logger.debug("text is not quoted, should strategy apply?")
            # return []
        delimiter = Plant.get_delimiter()
        if delimiter not in text:
            logger.debug("delimiter not found, can't split the code")
            return []
        acc_code, plant_code = text.rsplit(delimiter, 1)
        logger.debug(f"ac: {acc_code}, pl: {plant_code}")

        try:

            query = session.execute(
                Plant.query_with_default_order()
                .join(Accession, Plant.accession_id == Accession.id)
                .where(
                    Plant.code == str(plant_code),
                    utils.ilike(Accession.code, f"%{acc_code}%"),
                )
            )
            return query.scalars().all()
        except Exception as e:
            logger.debug(f"{e.__class__.__name__} {e}")
            return []


def as_dict(self):
    result = Serializable.as_dict(self)
    result["plant"] = (
        self.plant.accession.code + Plant.get_delimiter() + self.plant.code
    )
    return result


def retrieve(cls, session, keys):

    from bauble.plugins.garden import Accession
    stmt = cls.query_with_default_order()
    if "plant" in keys:
        acc_code, plant_code = keys["plant"].rsplit(Plant.get_delimiter(), 1)
        stmt = (
            stmt.join(Plant)
            .join(Accession, Plant.accession_id == Accession.id)
            .where(
                Plant.code == str(plant_code),
                Accession.code == str(acc_code),
            )
        )
    if "date" in keys:
        stmt = stmt.where(cls.date == keys["date"])
    if "category" in keys:
        stmt = stmt.where(cls.category == keys["category"])

    return session.execute(stmt).scalars().one_or_none()


def compute_serializable_fields(cls, session, keys):
    "plant is given as text, should be object"
    from bauble.plugins.garden import Accession
    result = {"plant": None}

    acc_code, plant_code = keys["plant"].rsplit(Plant.get_delimiter(), 1)
    logger.debug(f"acc-plant: {acc_code}-{plant_code}")
    plant_stmt = (
        Plant.query_with_default_order()
        .join(Accession, Plant.accession_id == Accession.id)
        .where(
            Plant.code == str(plant_code),
            Accession.code == str(acc_code),
        )
    )

    result["plant"] = session.execute(plant_stmt).scalars().one()
    return result


class Plant(Base, Serializable, DefiningPictures, WithNotes):
    """
    :Table name: plant

    :Columns:
        *code*: :class:`sqlalchemy.types.Unicode`
            The plant code

        *acc_type*: :class:`bauble.types.Enum`
            The accession type

            Possible values:
                * Plant: Whole plant

                * Seed/Spore: Seed or Spore

                * Vegetative Part: Vegetative Part

                * Tissue Culture: Tissue culture

                * Other: Other, probably see notes for more information

                * None: no information, unknown

        *accession_id*: :class:`sqlalchemy.types.Integer`
            Required.

        *location_id*: :class:`sqlalchemy.types.Integer`
            Required.

    :Properties:
        *accession*:
            The accession for this plant.
        *location*:
            The location for this plant.
        *notes*:
            The notes for this plant.

    :Constraints:
        The combination of code and accession_id must be unique.
    """

    __tablename__: str = "plant"
    __table_args__: Any = (UniqueConstraint("code", "accession_id"), {})

    # columns
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(Unicode(6), nullable=False)

    @validates("code")
    def validate_stripping(self, key, value):
        if value is None:
            return None
        return value.strip()

    acc_type: Mapped[str] = mapped_column(
        types.Enum(
            values=list(acc_type_values.keys()),
            translations=acc_type_values,
            omit_aliases=False,
        ),
        default=None,
    )
    memorial: Mapped[bool] = mapped_column(Boolean, default=False)
    quantity: Mapped[int] = mapped_column(Integer, autoincrement=False, nullable=False)

    accession_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("accession.id"), nullable=False
    )
    location_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("location.id"), nullable=False
    )
    order_by: Any = [asc(accession_id), asc(code)]

    _delimiter: ClassVar[Any] = None

    def search_view_markup_pair(self):
        """provide the two lines describing object for SearchView row."""
        import inspect

        logger.debug(
            f"entering search_view_markup_pair {self}, {str(inspect.stack()[1])}"
        )
        sp_str = self.accession.species_str(markup=True, authors=True)
        dead_color = "#9900ff"
        if self.quantity <= 0:
            dead_markup = (
                f'<span foreground="{dead_color}">{utils.xml_safe(self)}</span>'
            )
            return dead_markup, sp_str
        else:
            located_counted = (
                f'{utils.xml_safe(self)} <span foreground="#555555" size="small" '
                f'weight="light">- {self.quantity} alive in {utils.xml_safe(self.location)}</span>'
            )
            return located_counted, sp_str

    @classmethod
    def get_delimiter(cls, refresh: bool = False):
        """
        Get the plant delimiter from the BaubleMeta table.

        The delimiter is cached the first time it is retrieved.  To refresh
        the delimiter from the database call with refresh=True.

        """
        if cls._delimiter is None or refresh:
            cls._delimiter = meta.get_default(
                plant_delimiter_key, default_plant_delimiter
            ).value
        return cls._delimiter

    @property
    def date_of_death(self):
        if self.quantity != 0:
            return None
        try:
            return max([i.date for i in self.changes])
        except ValueError:
            return None

    def _get_delimiter(self):
        return Plant.get_delimiter()

    delimiter: Any = property(lambda self: self._get_delimiter())

    def __str__(self) -> str:
        return f"{self.accession}{self.delimiter}{self.code}"

    def duplicate(self, code: Optional[Any] = None, session: Optional[Any] = None):
        """Return a Plant that is a flat (not deep) duplicate of self. For notes,
        changes and propagations, you should refer to the original plant.

        """
        plant = Plant()
        if not session:
            session = object_session(self)
            if session:
                session.add(plant)

        ignore = ("id", "code", "changes", "notes", "propagations", "_created")
        properties = [
            p for p in object_mapper(self).iterate_properties if p.key not in ignore
        ]
        for prop in properties:
            setattr(plant, prop.key, getattr(self, prop.key))
        plant.code = code

        return plant

    def markup(self):
        return f"{self.accession}{self.delimiter}{self.code} ({self.accession.species_str(markup=True, authors=True)})"

    def as_dict(self):
        result = Serializable.as_dict(self)
        result["accession"] = self.accession.code
        result["location"] = self.location.code
        return result

    @classmethod
    def compute_serializable_fields(cls, session, keys):

        from bauble.plugins.garden import Accession, Location
        result = {"accession": None, "location": None}

        acc_keys = {}
        acc_keys.update(keys)
        acc_keys["code"] = keys["accession"]
        accession = Accession.retrieve_or_create(
            session,
            acc_keys,
            create=("taxon" in acc_keys and "rank" in acc_keys),
        )

        loc_keys = {}
        loc_keys.update(keys)
        if "location" in keys:
            loc_keys["code"] = keys["location"]
            location = Location.retrieve_or_create(session, loc_keys)
        else:
            location = None

        result["accession"] = accession
        result["location"] = location

        return result

    @classmethod
    def retrieve(cls, session, keys):
        from bauble.plugins.garden import Accession

        stmt = (
            cls.query_with_default_order()
            .join(Accession, cls.accession_id == Accession.id)
            .where(
                cls.code == keys["code"],
                Accession.code == keys["accession"],
            )
        )
        return session.execute(stmt).scalars().one_or_none()
    def top_level_count(self):
        sd = self.accession.source and self.accession.source.source_detail
        return {
            (1, "Plantings"): 1,
            (2, "Accessions"): {self.accession.id},
            (3, "Species"): {self.accession.species.id},
            (4, "Genera"): {self.accession.species.genus.id},
            (5, "Families"): {self.accession.species.genus.family.id},
            (6, "Living plants"): self.quantity,
            (7, "Locations"): {self.location.id},
            (8, "Sources"): set(sd and [sd.id] or []),
        }


PlantNote: Any = make_note_class(
    "Plant", Plant, compute_serializable_fields, as_dict, retrieve
)
Plant.notes: Mapped["PlantNote"] = relationship(
    "PlantNote",
    back_populates="plant",
    cascade="all, delete-orphan",
    single_parent=True,
)
