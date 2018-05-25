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
# test for bauble.plugins.users
#
import os

from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.exc import *

import bauble.db as db
from bauble.test import BaubleTestCase, check_dupids
import bauble.plugins.users as users
from nose import SkipTest


def test_duplicate_ids():
    """
    Test for duplicate ids for all .glade files in the users plugin.
    """
    import bauble.plugins.users as mod
    import glob
    head, tail = os.path.split(mod.__file__)
    files = glob.glob(os.path.join(head, '*.glade'))
    for f in files:
        assert(not check_dupids(f))


class UsersTests(BaubleTestCase):

    table = Table('test_users', db.metadata,
                  Column('id', Integer, Sequence('test_users_id_seq'),
                         primary_key=True),
                  Column('test', String(128)))

    def __init__(self, *args):
        self.user = '_test_user'
        self.group = '_test_group'
        super().__init__(*args)

    def setUp(self):
        super().setUp()

        # these tests are for postgres only
        if db.engine.name != 'postgresql':
            raise SkipTest("users management only on PostgreSQL")

        # the test user and group may still exist if a test didn't
        # clean up properly
        if self.user not in users.get_users():
            users.create_user(self.user)
        if self.group not in users.get_groups():
            users.create_group(self.group)

        # create a connection where the current user is set to
        # self.name
        #self.conn = users.connect_as_user(self.user)
        self.conn = db.engine.connect()

        # the tables are created and owned by the user who we used to
        # connect to the database in the first place, not our test
        # user
        self.table.create(checkfirst=True)

    def tearDown(self):
        if self.conn:
            self.conn.close()
        users.delete(self.group, revoke=True)
        users.delete(self.user, revoke=True)
        self.table.drop(checkfirst=True)
        super().tearDown()

    def test_group_members(self):
        if db.engine.name != 'postgresql':
            raise SkipTest("users management only on PostgreSQL")

        # test adding a member to a group
        users.add_member(self.user, [self.group])
        members = users.get_members(self.group)
        self.assertTrue(self.user in members, members)

        # test removing a member from a group
        users.remove_member(self.user, [self.group])
        members = users.get_members(self.group)
        self.assertTrue(self.user not in members, members)

    def test_has_privileges(self):

        # test setting admin privileges
        users.set_privilege(self.user, 'admin')
        self.assertTrue(users.has_privileges(self.user, 'admin'),
                     "%s doesn't have admin privileges" % self.user)
        self.assertTrue(users.has_privileges(self.user, 'write'),
                     "%s doesnt' have write privileges" % self.user)
        self.assertTrue(users.has_privileges(self.user, 'read'),
                     "%s doesn't have read privileges" % self.user)

        users.set_privilege(self.user, 'write')
        self.assertTrue(not users.has_privileges(self.user, 'admin'),
                     "%s has admin privileges" % self.user)
        self.assertTrue(users.has_privileges(self.user, 'write'),
                     "%s doesn't have write privileges" % self.user)
        self.assertTrue(users.has_privileges(self.user, 'read'),
                     "%s doesn't have read privileges" % self.user)

        users.set_privilege(self.user, 'read')
        self.assertTrue(not users.has_privileges(self.user, 'admin'),
                     "%s has admin privileges" % self.user)
        self.assertTrue(not users.has_privileges(self.user, 'write'),
                     "%s has write privileges" % self.user)
        self.assertTrue(users.has_privileges(self.user, 'read'),
                     "%s doesn't have read privileges" % self.user)

        # revoke all
        users.set_privilege(self.user, None)
        self.assertTrue(not users.has_privileges(self.user, 'admin'),
                     "%s has admin privileges" % self.user)
        self.assertTrue(not users.has_privileges(self.user, 'write'),
                     "%s has write privileges" % self.user)
        self.assertTrue(not users.has_privileges(self.user, 'read'),
                     "%s has read privileges" % self.user)

    def test_tool(self):
        raise SkipTest('Not Implemented')
        users.UsersEditor().start()
