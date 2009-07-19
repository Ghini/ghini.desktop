#
# test for bauble.plugins.users
#

from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.exc import *

import bauble.db as db
from bauble.test import BaubleTestCase
import bauble.plugins.users as users
from bauble.utils.log import debug


class UsersTests(BaubleTestCase):

    table = Table('test_users', db.metadata,
                  Column('id', Integer, Sequence('test_users_id_seq'),
                         primary_key=True),
                  Column('test', String(128)))

    def __init__(self, *args):
        self.user = '_test_user'
        self.group = '_test_group'
        super(UsersTests, self).__init__(*args)


    def setUp(self):
        super(UsersTests, self).setUp()
        from nose import SkipTest

        # these tests are for postgres only
        if db.engine.name != 'postgres':
            raise SkipTest

        # the test user and group may still exist if a test didn't
        # clean up properly
        if self.user not in users.get_users():
            users.create_user(self.user)
        if self.group not in users.get_groups():
            users.create_group(self.group)

        # create a connection where the current user is set to
        # self.name
        self.conn = users.connect_as_user(self.user)

        # the tables are created and owned by the user who we used to
        # connect to the database in the first place, not our test
        # user
        self.table.create(checkfirst=True)


    def tearDown(self):
        self.conn.close()
        super(UsersTests, self).tearDown()

        # TODO: right now roles can't be dropped if they have been
        # granted permissions but we should eventually fix it

        #users.delete(self.group)
        #users.delete(self.user)
        self.table.drop(checkfirst=True)


    def test_group_members(self):
        # if db.engine.name != 'postgres':
        #     raise SkipTest
        # test adding a member to a group
        users.add_member(self.user, [self.group])
        members = users.get_members(self.group)
        self.assert_(self.user in members, members)

        # test removing a member from a group
        users.remove_member(self.user, [self.group])
        members = users.get_members(self.group)
        self.assert_(self.user not in members, members)


    def test_grant_read(self):
        """
        Test granting read permissions to a user.
        """
        text = 'some text'
        self.table.insert().values(test=text).execute(bind=db.engine)

        users.grant(self.user, 'read')

        # test that we can select from the table
        self.conn.execute(self.table.select())

        # test that we can't insert
        ins = self.table.insert().values(test='some text2')
        self.assertRaises(ProgrammingError, self.conn.execute, ins)

        # test can't delete
        dlt = self.table.delete(self.table.c.test==text)
        self.assertRaises(ProgrammingError, self.conn.execute, dlt)

        # test can't update
        upd = self.table.update().where(self.table.c.test==text).\
            values(test='new text')
        self.assertRaises(ProgrammingError, self.conn.execute, upd)

        # test doesn't have grant privileges
        for table in db.metadata.sorted_tables:
            for priv in filter(lambda x: x.lower()!='all', users._table_privs):
                stmt = "select has_table_privilege('%s', '%s', " \
                    "'%s WITH GRANT OPTION')" % (self.user, table.name, priv)
                r = db.engine.execute(stmt).fetchone()[0]
                self.assert_(not r, '%s does has grant privilege for %s ' \
                                 'on table %s' % (self.user, priv, table.name))


    def test_grant_write(self):
        """Test granting write permissions to a user.
        """
        text = 'some text'
        self.table.insert().values(test=text).execute(bind=db.engine)

        users.grant(self.user, 'write')

        # test that we can select from the table
        self.conn.execute(self.table.select())

        # test that we can't insert
        ins = self.table.insert().values(test='some text2')
        self.conn.execute(ins)
        #self.assertRaises(ProgrammingError, self.conn.execute, ins)

        # test can't delete
        dlt = self.table.delete(self.table.c.test==text)
        self.conn.execute(dlt)
        #self.assertRaises(ProgrammingError, self.conn.execute, dlt)

        # test can't update
        upd = self.table.update().where(self.table.c.test==text).\
            values(test='new text')
        self.conn.execute(upd)
        #self.assertRaises(ProgrammingError, self.conn.execute, upd)

        # test doesn't have grant privileges
        for table in db.metadata.sorted_tables:
            for priv in filter(lambda x: x.lower()!='all', users._table_privs):
                stmt = "select has_table_privilege('%s', '%s', " \
                    "'%s WITH GRANT OPTION')" % (self.user, table.name, priv)
                r = db.engine.execute(stmt).fetchone()[0]
                self.assert_(not r, '%s does has grant privilege for %s ' \
                                 'on table %s' % (self.user, priv, table.name))



    def test_grant_admin(self):
        """Test granting admin permissions to a user.
        """
        text = 'some text'
        self.table.insert().values(test=text).execute(bind=db.engine)

        users.grant(self.user, 'admin')

        # test that we can select from the table
        self.conn.execute(self.table.select())

        # test that we can't insert
        ins = self.table.insert().values(test='some text2')

        self.conn.execute(ins)
        #self.assertRaises(ProgrammingError, self.conn.execute, ins)

        # test can't delete
        dlt = self.table.delete(self.table.c.test==text)
        self.conn.execute(dlt)
        #self.assertRaises(ProgrammingError, self.conn.execute, dlt)

        # test can't update
        upd = self.table.update().where(self.table.c.test==text).\
            values(test='new text')
        self.conn.execute(upd)
        #self.assertRaises(ProgrammingError, self.conn.execute, upd)

        # test has grant privileges
        for table in db.metadata.sorted_tables:
            for priv in filter(lambda x: x.lower()!='all', users._table_privs):
                stmt = "select has_table_privilege('%s', '%s', " \
                    "'%s WITH GRANT OPTION')" % (self.user, table.name, priv)
                r = db.engine.execute(stmt).fetchone()[0]
                self.assert_(r, '%s does not have grant privilege for %s ' \
                                 'on table %s' % (self.user, priv, table.name))


    def test_has_privileges(self):

        # TODO: create the roles that we want to test with to make
        # sure they are clean...and delete them when done
        role = 'test_admin'
        if not role in users.get_users():
            users.create_user(role, admin=True)
        users.grant(role, 'admin')
        self.assert_(users.has_privileges(role, 'admin'),
                     "%s doesn't have admin privileges" % role)
        self.assert_(users.has_privileges(role, 'write'),
                     "%s doesnt' have write privileges" % role)
        self.assert_(users.has_privileges(role, 'read'),
                     "%s doesn't have read privileges" % role)
        #users.drop(role)

        role = 'test_write'
        if not role in users.get_users():
            users.create_user(role)
        users.grant(role, 'write')
        self.assert_(not users.has_privileges(role, 'admin'),
                     "%s has admin privileges" % role)
        self.assert_(users.has_privileges(role, 'write'),
                     "%s doesn't have write privileges" % role)
        self.assert_(users.has_privileges(role, 'read'),
                     "%s doesn't have read privileges" % role)
        #users.drop(role)

        role = 'test_read'
        if not role in users.get_users():
            users.create_user(role)
        users.grant(role, 'read')
        self.assert_(not users.has_privileges(role, 'admin'),
                     "%s has admin privileges" % role)
        self.assert_(not users.has_privileges(role, 'write'),
                     "%s has write privileges" % role)
        self.assert_(users.has_privileges(role, 'read'),
                     "%s doesn't have read privileges" % role)
        #users.drop(role)



    def itest_tool(self):
        users.UsersEditor().start()

