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
from datetime import datetime
from typing import Any, ClassVar

import bauble.btypes as types
from bauble.db import Base
from bauble.plugins.garden.constants import change_reasons

# from sqlalchemy import text
from sqlalchemy import ForeignKey, Integer, Unicode, asc
from sqlalchemy.orm import Mapped, mapped_column

logger: Any = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# TODO: might be worthwhile to have a label or textview next to the
# location combo that shows the description of the currently selected
# location

plant_delimiter_key: str = "plant_delimiter"
default_plant_delimiter: str = "."

class PlantChange(Base):
    """ """

    __tablename__: str = "plant_change"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("plant.id"), nullable=False
    )
    parent_plant_id: Mapped[int] = mapped_column(Integer, ForeignKey("plant.id"))

    # - if to_location_id is None changeis a removal
    # - if from_location_id is None then this change is a creation
    # - if to_location_id != from_location_id change is a transfer
    from_location_id: Mapped[int] = mapped_column(Integer, ForeignKey("location.id"))
    to_location_id: Mapped[int] = mapped_column(Integer, ForeignKey("location.id"))

    # the name of the person who made the change
    person: Mapped[str] = mapped_column(Unicode(64))

    quantity: Mapped[int] = mapped_column(Integer, autoincrement=False, nullable=False)
    note_id: Mapped[int] = mapped_column(Integer, ForeignKey("plant_note.id"))

    reason: Mapped[str] = mapped_column(
        types.Enum(
            values=list(change_reasons.keys()),
            translations=change_reasons,
            omit_aliases=False,
        )
    )

    # date of change
    date: Mapped[types.DateTime] = mapped_column(
        types.DateTime, default=datetime.utcnow
    )
    order_by: ClassVar[list[Any]] = [asc(date)]

    # Relationships
