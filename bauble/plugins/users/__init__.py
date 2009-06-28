
from sqlalchemy import *
from sqlalchemy.exc import *
from sqlalchemy.orm.exc import *
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta

import bauble
import bauble.db as db
import bauble.pluginmgr as pluginmgr
from bauble.utils.log import debug, warning
import bauble.utils as utils

# WARNING: "roles" are specific to PostgreSQL database from 8.1 and
# greater, therefore this module won't work on earlier PostgreSQL
# databases or other database types

# Read: can select and read data in the database
#
# Write: can add, edit and delete data but can't create new tables,
#        i.e. can't install plugins that create new tables, also
#        shouldn't be able to install a new database over an existing
#        database
#
# Admin: can create other users and grant privileges and create new
#        tables
#


# NOTE: see the following docs for how to get the privileges on a
# specific databas object
# http://www.postgresql.org/docs/8.3/interactive/functions-info.html


def connect_as_user(name=None):
    """
    Return a connection where the user is set to name.

    The returned connection should be closed when it is no longer
    needed or deadlocks may occur.
    """
    conn = db.engine.connect()
    # detach connection so when its closed it doesn't go back to the
    # pool where there could be the possibility of it being reused and
    # having future sql commands run as the user afer this connection
    # has been closed
    conn.detach()
    trans = conn.begin()
    try:
        conn.execute('set role %s' % name)
    except Exception, e:
        warning(utils.utf8(e))
        trans.rollback()
        conn.close()
        return None
    else:
        trans.commit()
    return conn


def get_users():
    """Return a list of user names.
    """
    stmt = 'select rolname from pg_roles where rolcanlogin is true;'
    return [r[0] for r in db.engine.execute(stmt)]


def get_groups():
    """Return a list of group names.
    """
    stmt = 'select rolname from pg_roles where rolcanlogin is false;'
    return [r[0] for r in db.engine.execute(stmt)]
    # filter out the ones that are groups, groups are an artificial
    # category and we consider groups as a role that can't login
    #filter(


def _create_role(name, password=None, login=False, admin=False):
    """
    """
    stmt = 'create role %s INHERIT' % name
    if login:
        stmt += ' LOGIN'
    if admin:
        stmt += ' CREATEROLE'
    if password:
        stmt += ' PASSWORD %s' % password
    #debug(stmt)
    db.engine.execute(stmt)


def create_user(name, password=None, admin=False, groups=[]):
    """
    Create a role that can login.
    """
    _create_role(name, password, login=True, admin=False)
    for group in groups:
        stmt = 'grant %s to %s;' % (group, name)
        db.engine.execute(stmt)
    # allow the new role to connect to the database
    stmt = 'grant connect on database %s to %s' % \
        (bauble.db.engine.url.database, name)
    #debug(stmt)
    db.engine.execute(stmt)


def create_group(name, admin=False):
    """
    Create a role that can't login.
    """
    _create_role(name, login=False, password=None, admin=admin)


def add_member(name, groups=[]):
    """
    Add name to groups.
    """
    conn = db.engine.connect()
    trans = conn.begin()
    try:
        for group in groups:
            stmt = 'grant "%s" to %s;' % (group, name)
            conn.execute(stmt)
    except:
        trans.rollback()
    else:
        trans.commit()
    conn.close()


def remove_member(name, groups=[]):
    """
    Remove name from groups.
    """
    conn = db.engine.connect()
    trans = conn.begin()
    try:
        for group in groups:
            stmt = 'revoke %s from %s;' % (group, name)
            conn.execute(stmt)
    except:
        trans.rollback()
    else:
        trans.commit()
    conn.close()


def get_members(group):
    """Return members of group

    Arguments:
    - `group`:
    """
    # get group id
    stmt = "select oid from pg_roles where rolname = '%s'" % group
    gid = db.engine.execute(stmt).fetchone()[0]
    # get members with the gid
    stmt = 'select member from pg_auth_members where roleid = %s' % gid
    roleids = [r[0] for r in db.engine.execute(stmt).fetchall()]
    stmt = 'select rolname from pg_roles where oid in (select member ' \
        'from pg_auth_members where roleid = %s)' % gid
    return [r[0] for r in db.engine.execute(stmt).fetchall()]


def delete(name):
    stmt = 'drop role %s;' %  name
    db.engine.execute(stmt)


def get_privileges(role):
    """Return the privileges the user has on the current database.

    Arguments:
    - `role`:
    """
    # TODO: should we return read, write, admin or the specific
    # privileges
    raise NotImplementedError


_privileges = {'read': ['connect', 'select'],
              'write': ['connect', 'usage', 'select', 'update', 'insert',
                        'delete', 'execute', 'trigger', 'references'],
              'admin': ['all']}

_table_privs = ['select', 'insert', 'update', 'delete', 'references',
                 'trigger', 'all']

__sequence_privs = ['usage', 'select', 'update', 'all']


def grant(role, privilege):
    """Grant privileges to role on the database.

    Arguments:
    - `role`:
    - `privilege`:
    """
    # TODO: should we revoke all before adding privileges
    conn = db.engine.connect()
    trans = conn.begin()
    privs = _privileges[privilege]
    try:
        for table in bauble.db.metadata.sorted_tables:
            tbl_privs = filter(lambda x: x.lower() in _table_privs, privs)
            for priv in tbl_privs:
                stmt = 'grant %s on %s to %s' % (priv, table.name, role)
                if privilege == 'admin':
                    stmt += ' with grant option'
                #debug(stmt)
                conn.execute(stmt)
            for col in table.c:
                seq_privs = filter(lambda x: x.lower() in __sequence_privs,
                                   privs)
                for priv in seq_privs:
                    if hasattr(col, 'sequence'):
                        stmt = 'grant %s on sequence %s to %s' % \
                            (priv, col.sequence.name, role)
                        #debug(stmt)
                        if privilege == 'admin':
                            stmt += ' with grant option'
                        conn.execute(stmt)
    except Exception, e:
        warning(e)
        trans.rollback()
    else:
        trans.commit()
    finally:
        conn.close()



def revoke(role, privileges):
    """Revoke a roles privileges on the current database.

    Arguments:
    - `role`:
    - `privileges`:
    """
    if privileges == 'read':
        _read_privileges('revoke', role)
    elif privileges == 'read':
        _write_privileges('revoke', role)
    elif privileges == 'admin':
        _write_privileges('revoke', role)
    else:
        raise ValueError('revoke() unknown privilege: %s' % privileges)



class UsersTool(pluginmgr.Tool):

    label = "Users"

    @classmethod
    def start(self):
        pass


class UsersPlugin(pluginmgr.Plugin):

    tools = [UsersTool]

    @classmethod
    def init(cls):
        pass

plugin = UsersPlugin
