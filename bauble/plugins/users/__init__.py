
import os
import re

import gtk
from sqlalchemy import *
from sqlalchemy.exc import *
from sqlalchemy.orm.exc import *
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta

import bauble
import bauble.db as db
import bauble.paths as paths
import bauble.pluginmgr as pluginmgr
from bauble.utils.log import debug, warning
import bauble.utils as utils
from bauble.utils.log import debug, warning, error

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
    stmt = "select member from pg_auth_members where roleid = '%s'" % gid
    roleids = [r[0] for r in db.engine.execute(stmt).fetchall()]
    stmt = 'select rolname from pg_roles where oid in (select member ' \
        'from pg_auth_members where roleid = %s)' % gid
    return [r[0] for r in db.engine.execute(stmt).fetchall()]


def delete(role):
    drop(role)

def drop(role):
    # TODO: need to revoke all privileges first
    stmt = 'drop role %s;' % (role)
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

_database_privs = ['create', 'temporary', 'temp']

_table_privs = ['select', 'insert', 'update', 'delete', 'references',
                 'trigger', 'all']

__sequence_privs = ['usage', 'select', 'update', 'all']


def _parse_acl(acl):
    """
    returns a list of acls of (role, privs, granter)
    """
    rx = re.compile('[{]?(.*?)=(.*?)\/(.*?)[,}]')
    return rx.findall(acl)


def has_privileges(role, privilege):
    """Return True/False if role has privileges.

    Arguments:
    - `role`:
    - `privileges`:
    """
    # if the user has all on database with grant privileges he has
    # the grant privilege on the database then he has admin

    if privilege == 'admin':
        # test admin privileges on the database
        for priv in _database_privs:
            stmt = "select has_database_privilege('%s', '%s', '%s')" \
                % (role, bauble.db.engine.url.database, priv)
            r = db.engine.execute(stmt).fetchone()[0]
            if not r:
                # debug('%s does not have %s on database %s' % \
                #           (role, priv, bauble.db.engine.url.database))
                return False
        privs = set(_table_privs).intersection(_privileges['write'])
    else:
        privs = set(_table_privs).intersection(_privileges[privilege])


    # TODO: can we call had_table_privileges on a sequence

    # test the privileges on the tables and sequences
    for table in db.metadata.sorted_tables:
        for priv in privs:
            stmt = "select has_table_privilege('%s', '%s', '%s')" \
                % (role, table.name, priv)
            r = db.engine.execute(stmt).fetchone()[0]
            if not r:
                #debug('%s does not have %s on %s' % (role,priv,table.name))
                return False
    return True


def grant(role, privilege):
    """Grant privileges to role on the database.

    This method does not revoke any privileges so if a user has 'admin'
    privileges and you want to change them to 'read' privileges then
    you should revoke the privileges first.

    Arguments:
    - `role`:
    - `privilege`:
    """
    # TODO: should we revoke all before adding privileges
    conn = db.engine.connect()
    trans = conn.begin()
    privs = _privileges[privilege]
    try:
        # grant privileges on the database
        if privilege == 'admin':
            stmt = 'grant all on database %s to %s with grant option;' % \
                (bauble.db.engine.url.database, role)
            conn.execute(stmt)

        # grant privileges on the tables and sequences
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


def current_user():
    return db.engine.execute('select current_user;').fetchone()[0]


class UsersEditor(object):
    """
    """

    def __init__(self, ):
        """
        """

        path = os.path.join(paths.lib_dir(), 'plugins', 'users', 'ui.glade')
        self.widgets = utils.BuilderWidgets(path)


    def start(self):
        if not db.engine.name == 'postgres':
            msg = _('The users plugin is only valid on a PostgreSQL database')
            utils.message_dialog(utils.utf8(msg))
            return

        # TODO: should allow anyone to view the priveleges but only
        # admins to change them
        debug(current_user())
        if not has_privileges(current_user(), 'admin'):
            msg = _('You do not have privileges to change other '\
                        'user privileges')
            utils.message_dialog(utils.utf8(msg))
            return
        # setup the users tree
        tree = self.widgets.users_tree
        renderer = gtk.CellRendererText()
        def cell_data_func(col, cell, model, it):
            value = model[it][0]
            cell.set_property('text', value)
        tree.insert_column_with_data_func(0, _('Users'), renderer,
                                          cell_data_func)
        model = gtk.ListStore(str)
        for user in get_users():
            model.append([user])
        self.widgets.users_tree.set_model(model)

        def on_toggled(button, data=None):
            active = button.get_active()
            debug('%s: %s' % (data, active))

        self.widgets.read_button.connect('toggled', on_toggled, 'read')
        self.widgets.write_button.connect('toggled', on_toggled, 'write')
        self.widgets.admin_button.connect('toggled', on_toggled, 'admin')

        self.widgets.main_dialog.run()




class UsersTool(pluginmgr.Tool):

    label = _("Users")

    @classmethod
    def start(self):
        UsersEditor().start()

# TODO: need some way to disable the plugin/tool if not a postgres database

class UsersPlugin(pluginmgr.Plugin):

    tools = [UsersTool]

    @classmethod
    def init(cls):
        pass

plugin = UsersPlugin
