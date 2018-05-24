# -*- coding: utf-8 -*-
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
from sqlalchemy import Unicode, UnicodeText, Column

import bauble.db as db
import bauble.utils as utils

VERSION_KEY = 'version'
CREATED_KEY = 'created'
REGISTRY_KEY = 'registry'

# date format strings:
# yy - short year
# yyyy - long year
# dd - number day, always two digits
# d - number day, two digits when necessary
# mm -number month, always two digits
# m - number month, two digits when necessary
DATE_FORMAT_KEY = 'date_format'


def get_default(name, default=None, session=None):
    """
    Get a BaubleMeta object with name.  If the default value is not
    None then a BaubleMeta object is returned with name and the
    default value given.

    If a session instance is passed (session != None) then we
    don't commit the session.
    """
    commit = False
    if not session:
        session = db.Session()
        commit = True
    query = session.query(BaubleMeta)
    meta = query.filter_by(name=name).first()
    if not meta and default is not None:
        meta = BaubleMeta(name=utils.utf8(name), value=default)
        session.add(meta)
        if commit:
            session.commit()
            # load the properties so that we can close the session and
            # avoid getting errors when accessing the properties on the
            # returned meta
            meta.value
            meta.name

    if commit:
        # close the session whether we added anything or not
        session.close()
    return meta


class BaubleMeta(db.Base):
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
    __tablename__ = 'bauble'
    name = Column(Unicode(64), unique=True)
    value = Column(UnicodeText)
