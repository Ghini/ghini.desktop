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
# test for bauble.meta
#
# Import necessary modules
import pytest
from sqlalchemy import select

import bauble.meta as meta


@pytest.fixture
def session_with_meta(db_session, clean_db):
    """
    Fixture for setting up a clean database session with meta schema.
    """
    return db_session


def test_get_default_without_creation(session_with_meta) -> None:
    """
    Test bauble.meta.get_default() when object does not exist and no default value is provided.
    """
    name = "name"
    obj = meta.get_default(name, session=session_with_meta)
    assert obj is None, f"Expected None, but got {obj}"


def test_get_default_with_creation(session_with_meta) -> None:
    """
    Test bauble.meta.get_default() when object does not exist and a default value is provided.
    """
    name = "name"
    value = "value"
    meta.get_default(name, default=value, session=session_with_meta)
    if session_with_meta.in_transaction():
        session_with_meta.commit()  # Ensure the object is saved to the database
    obj = (
        session_with_meta.execute(
            select(meta.BaubleMeta).where(meta.BaubleMeta.name == name)
        )
        .scalars()
        .one()
    )
    assert obj.value == value, f"Expected value '{value}', but got {obj.value}"


def test_get_default_no_override(session_with_meta) -> None:
    """
    Test bauble.meta.get_default() does not override existing value when a new default is provided.
    """
    name = "name"
    value = "value"
    meta.get_default(name, default=value, session=session_with_meta)
    if session_with_meta.in_transaction():
        session_with_meta.commit()  # Ensure the object is saved to the database

    value2 = "value2"
    obj = meta.get_default(name, default=value2, session=session_with_meta)
    assert obj.value == value, f"Expected original value '{value}', but got {obj.value}"


def test_get_default_with_custom_session(session_with_meta) -> None:
    """
    Test bauble.meta.get_default() with a custom session and without committing the new object.
    """
    name = "name2"
    value = "value"
    obj = meta.get_default(name, default=value, session=session_with_meta)
    assert (
        obj in session_with_meta.new
    ), "Expected object to be in session's new objects."
