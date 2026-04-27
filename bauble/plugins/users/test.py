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
# test for bauble.plugins.users
#
import glob
import os

import pytest
from sqlalchemy import Column, Integer, Sequence, String, Table

import bauble.plugins.users as users
from bauble import db
from bauble.test import check_dupids


from typing import Any
from collections.abc import Generator


@pytest.fixture
def test_user() -> Generator[Any, None, None]:
    """Fixture for setting up and tearing down a test user."""
    user = "_test_user"
    if user not in users.get_users():
        users.create_user(user)
    yield user
    users.delete(user, revoke=True)


@pytest.fixture
def test_group() -> Generator[Any, None, None]:
    """Fixture for setting up and tearing down a test group."""
    group = "_test_group"
    if group not in users.get_groups():
        users.create_group(group)
    yield group
    users.delete(group, revoke=True)


@pytest.fixture
def test_table() -> Generator[Any, None, None]:
    """Fixture for creating and dropping a test table."""
    table = Table(
        "test_users",
        db.metadata,
        Column("id", Integer, Sequence("test_users_id_seq"), primary_key=True),
        Column("test", String(128)),
    )
    table.create(checkfirst=True)
    yield table
    table.drop(checkfirst=True)


@pytest.fixture
def test_connection() -> Generator[Any, None, None]:
    """Fixture for creating and closing a database connection."""
    conn = db.engine.connect()
    yield conn
    conn.close()


def test_duplicate_ids() -> None:
    """Test for duplicate IDs in .glade files within the users plugin."""
    import bauble.plugins.users as mod

    head, _ = os.path.split(mod.__file__)
    files = glob.glob(os.path.join(head, "*.glade"))
    for f in files:
        assert not check_dupids(f)


@pytest.mark.skipif(db.engine.name != "postgresql", reason="Requires PostgreSQL")
def test_group_members(test_user, test_group) -> None:
    """Test adding and removing a user from a group."""
    # Add the user to the group
    users.add_member(test_user, [test_group])
    members = users.get_members(test_group)
    assert test_user in members

    # Remove the user from the group
    users.remove_member(test_user, [test_group])
    members = users.get_members(test_group)
    assert test_user not in members


@pytest.mark.skipif(db.engine.name != "postgresql", reason="Requires PostgreSQL")
def test_has_privileges(test_user) -> None:
    """Test setting and checking user privileges."""
    # Grant admin privileges
    users.set_privilege(test_user, "admin")
    assert users.has_privileges(test_user, "admin")
    assert users.has_privileges(test_user, "write")
    assert users.has_privileges(test_user, "read")

    # Change to write privileges
    users.set_privilege(test_user, "write")
    assert not users.has_privileges(test_user, "admin")
    assert users.has_privileges(test_user, "write")
    assert users.has_privileges(test_user, "read")

    # Change to read-only privileges
    users.set_privilege(test_user, "read")
    assert not users.has_privileges(test_user, "admin")
    assert not users.has_privileges(test_user, "write")
    assert users.has_privileges(test_user, "read")

    # Revoke all privileges
    users.set_privilege(test_user, None)
    assert not users.has_privileges(test_user, "admin")
    assert not users.has_privileges(test_user, "write")
    assert not users.has_privileges(test_user, "read")


def test_tool() -> None:
    """Placeholder for testing the UsersEditor tool."""
    pytest.skip("Not Implemented")
