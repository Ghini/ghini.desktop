#
# Copyright 2008-2010 Brett Adams
# Copyright 2015-2017 Mario Frasca <mario@anche.no>.
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
# propagation module
#

import logging
from typing import Any

from bauble.db import Base

# from sqlalchemy import text
from sqlalchemy import Column, ForeignKey, Integer, Table

# from sqlalchemy.ext.declarative import declared_attr

logger: Any = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


PlantPropagation: Any = Table(
    "plant_prop",
    Base.metadata,
    Column("plant_id", Integer, ForeignKey("plant.id"), primary_key=True),
    Column(
        "propagation_id",
        Integer,
        ForeignKey("propagation.id"),
        primary_key=True,
    ),
)
