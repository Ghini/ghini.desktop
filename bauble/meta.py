#
# Copyright (c) 2005,2006,2007,2008,2009 Brett Adams <brett@belizebotanic.org>
# Copyright (c) 2012-2015 Mario Frasca <mario@anche.no>
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
# meta.py
#
# import bauble.utils as utils
from typing import Any, Optional

from bauble.db import Base, Session
from sqlalchemy import Integer, Unicode, UnicodeText
from sqlalchemy.orm import Mapped, mapped_column

DATE_FORMAT_KEY: str
VERSION_KEY: str = "version"
CREATED_KEY: str = "created"
REGISTRY_KEY: str = "registry"

# date format strings:
# yy - short year
# yyyy - long year
# dd - number day, always two digits
# d - number day, two digits when necessary
# mm -number month, always two digits
# m - number month, two digits when necessary
DATE_FORMAT_KEY = "date_format"


def get_default(name, default: Optional[Any] = None, session: Optional[Any] = None):
    """
    Get a BaubleMeta object with name.  If the default value is not
    None then a BaubleMeta object is returned with name and the
    default value given.

    If a session instance is passed (session != None) then we
    don't commit the session.
    """
    if not isinstance(name, str):
        raise TypeError(f"'name' must be a string, got {type(name).__name__}.")
    if session and not hasattr(session, "execute"):
        raise TypeError(
            f"'session' must be a valid SQLAlchemy session, got {type(session).__name__}."
        )

    commit = False
    if not session:
        session = Session()
        commit = True
    stmt = BaubleMeta.query_with_default_order().where(BaubleMeta.name == name)
    query = session.execute(stmt).scalars()
    meta = query.first()

    # If no result and default is provided, create a new entry
    if not meta and default is not None:
        meta = BaubleMeta(name=name, value=default)
        session.add(meta)
        if commit:
            if session.in_transaction():
                session.commit()

    if commit:
        # Ensure properties are loaded before closing the session
        # load the properties so that we can close the session and
        # avoid getting errors when accessing the properties on the
        # returned meta
        if meta:
            _ = meta.value
            _ = meta.name
        # close the session whether we added anything or not
        session.close()
    return meta


class BaubleMeta(Base):
    """
    The BaubleMeta class is used to set and retrieve meta information
    based on key/name values from the bauble meta table.

    :Table name: bauble

    :Columns:
      *name*:
        The name of the data.

      *value*:
        The value.

    """

    __tablename__: str = "bauble"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Unicode(64), unique=True)
    value: Mapped[Optional[str]] = mapped_column(UnicodeText, nullable=True)
