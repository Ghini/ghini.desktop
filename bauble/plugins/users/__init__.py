# -*- coding: utf-8 -*-
#
# Copyright (c) 2005,2006,2007,2008,2009 Brett Adams <brett@belizebotanic.org>
# Copyright (c) 2012-2017 Mario Frasca <mario@anche.no>
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

import os
import re

from gi.repository import Gtk

import logging
logger = logging.getLogger(__name__)

from sqlalchemy import *
from sqlalchemy.exc import *
from sqlalchemy.orm.exc import *
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta

import bauble
import bauble.editor as editor
from bauble.error import check, CheckConditionError
import bauble.db as db
import bauble.paths as paths
import bauble.pluginmgr as pluginmgr
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

# TODO: should allow each of the functions to be called with a
# different connection than db.engine, could probably create a
# descriptor to add the same functionality to all the functions in one
# fell swoop

# TODO: should provide a privilege error that can allow the caller to
# get more information about the error. e.g include the table, the
# permissions, what they were trying to do and the error
# class PrivilegeError(error.BaubleError):
#     """
#     """

#     def __init__(self, ):
#         """
#         """


# TODO: removed connect_as_user since for "set role" to be successful
# the current user has to be a member of the role/name passed to
# connect_as_user() which makes it not very useful

# def connect_as_user(name=None):
#     """
#     Return a connection where the user is set to name.

#     The returned connection should be closed when it is no longer
#     needed or deadlocks may occur.
#     """
#     conn = db.engine.connect()
#     # detach connection so when it's closed it doesn't go back to the
#     # pool where there could be the possibility of it being reused and
#     # having future sql commands run as the user afer this connection
#     # has been closed
#     conn.detach()
#     trans = conn.begin()
#     try:
#         conn.execute('set role %s' % name)
#     except Exception, e:
#         warning(utils.utf8(e))
#         trans.rollback()
#         conn.close()
#         return None
#     else:
#         trans.commit()
#     return conn


def get_users():
    """Return the list of user names.
    """
    stmt = 'select rolname from pg_roles where rolcanlogin is true;'
    return [r[0] for r in db.engine.execute(stmt)]


def get_groups():
    """Return the list of group names.
    """
    stmt = 'select rolname from pg_roles where rolcanlogin is false;'
    return [r[0] for r in db.engine.execute(stmt)]


def _create_role(name, password=None, login=False, admin=False):
    """
    """
    conn = db.engine.connect()
    trans = conn.begin()
    try:
        stmt = 'create role %s INHERIT' % name
        if login:
            stmt += ' LOGIN'
        if admin:
            stmt += ' CREATEROLE'
        if password:
            stmt += ' PASSWORD \'%s\'' % password
        conn.execute(stmt)
    except Exception as e:
        logger.error('users._create_role(): %s %s' % (type(e), utils.utf8(e)))
        trans.rollback()
        raise
    else:
        trans.commit()
    finally:
        conn.close()



def create_user(name, password=None, admin=False, groups=None):
    """
    Create a role that can login.
    """
    if groups is None:
        groups = []
    _create_role(name, password, login=True, admin=False)
    conn = db.engine.connect()
    trans = conn.begin()
    try:
        for group in groups:
            stmt = 'grant %s to %s;' % (group, name)
            db.engine.execute(stmt)
        # allow the new role to connect to the database
        stmt = 'grant connect on database %s to %s' % \
            (bauble.db.engine.url.database, name)
        logger.debug(stmt)
        conn.execute(stmt)
    except Exception as e:
        logger.error('users.create_user(): %s %s' % (type(e), utils.utf8(e)))
        trans.rollback()
        raise
    else:
        trans.commit()
    finally:
        conn.close()


def create_group(name, admin=False):
    """
    Create a role that can't login.
    """
    _create_role(name, login=False, password=None, admin=admin)


def add_member(name, groups=None):
    """
    Add name to groups.
    """
    if groups is None:
        groups = []
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
    finally:
        conn.close()


def remove_member(name, groups=None):
    """
    Remove name from groups.
    """
    if groups is None:
        groups = []
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
    finally:
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


def delete(role, revoke=False):
    """See drop()
    """
    drop(role, revoke)


def drop(role, revoke=False):
    """
    Drop a user from the database

    Arguments:
    - `role`:
    - `revoke`: If revoke is True then revoke the users permissions
      before dropping them
    """
    # TODO: need to revoke all privileges first
    conn = db.engine.connect()
    trans = conn.begin()
    try:
        if revoke:
            # if set privilege failes then dropping the role will fail
            # because the role will still have dependent users
            set_privilege(role, None)
        stmt = 'drop role %s;' % role
        conn.execute(stmt)
    except Exception as e:
        logger.error("users.drop(): %s %s" % (type(e), utils.utf8(e)))
        trans.rollback()
        raise
    else:
        trans.commit()
    finally:
        conn.close()


def get_privileges(role):
    """Return the privileges the user has on the current database.

    Arguments:
    - `role`:
    """
    # TODO: should we return read, write, admin or the specific
    # privileges...this can basically just be a wrapped call to
    # has_privileges()
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
    # if the user has all on database with grant privileges and he has
    # the grant privilege on the database then he has admin and he can
    # create roles
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


    # TODO: has_sequence_privileges will be introduced in PostgreSQL 8.5

    # test the privileges on the tables and sequences
    for table in db.metadata.sorted_tables:
        for priv in privs:
            stmt = "select has_table_privilege('%s', '%s', '%s')" \
                % (role, table.name, priv)
            try:
                r = db.engine.execute(stmt).fetchone()[0]
                if not r:
                    # debug('%s does not have %s on %s table' % \
                        #           (role,priv,table.name))
                    return False
            except ProgrammingError:
                # we get here if the table doesn't exists, if it
                # doesn't exist we don't care if we have permissions
                # on it...this usually happens if we are checking
                # permissions on a table in the metadata which doesn't
                # exist in the database which can happen if this
                # plugin is run on a mismatched version of bauble
                pass

    # if admin check that the user can also create roles
    if privilege == 'admin':
        stmt = "select rolname from pg_roles where rolcreaterole is true and rolname = '%s'" % role
        r = db.engine.execute(stmt).fetchone()
        if not r:
            return False

    return True


def has_implicit_sequence(column):
    # Tell me if there's an implicit sequence associated to the column, then
    # I assume that the sequence name is <table>_<column>_seq.  Seen at
    # https://www.programcreek.com/python/example/58771/sqlalchemy.schema.Sequence,
    # allegedly from project tg2jython, under directory
    # sqlalchemy60/lib/sqlalchemy/dialects/mssql, in source file base.py,
    # simplified based on assuptions valid in ghini
    return (column.primary_key and
            column.autoincrement and
            isinstance(column.type, Integer) and
            not column.foreign_keys)


def set_privilege(role, privilege):
    """Set the role's privileges.

    Arguments:
    - `role`:
    - `privilege`:
    """
    check(privilege in ('read', 'write', 'admin', None),
          'invalid privilege: %s' % privilege)
    conn = db.engine.connect()
    trans = conn.begin()

    if privilege:
        privs = _privileges[privilege]

    try:
        # revoke everything first
        for table in db.metadata.sorted_tables:
            stmt = 'revoke all on table %s from %s;' % (table.name, role)
            conn.execute(stmt)
            for col in table.c:
                if hasattr(col, 'sequence'):
                    stmt = ('revoke all on sequence %s from %s'
                            % (col.sequence.name, role))
                    conn.execute(stmt)

        stmt = 'revoke all on database %s from %s' \
            % (bauble.db.engine.url.database, role)
        conn.execute(stmt)

        stmt = 'alter role %s with nocreaterole' % role
        conn.execute(stmt)

        # privilege is None so all permissions are revoked
        if not privilege:
            trans.commit()
            conn.close()
            return

        # change privileges on the database
        if privilege == 'admin':
            stmt = 'grant all on database %s to %s' % \
                (bauble.db.engine.url.database, role)
            if privilege == 'admin':
                    stmt += ' with grant option'
            conn.execute(stmt)
            stmt = 'alter role %s with createuser' % role
            conn.execute(stmt)

        # grant privileges on the tables and sequences
        for table in bauble.db.metadata.sorted_tables:
            logger.debug('granting privileges on table %s' % table)
            tbl_privs = [x for x in privs if x.lower() in _table_privs]
            for priv in tbl_privs:
                stmt = 'grant %s on %s to %s' % (priv, table.name, role)
                if privilege == 'admin':
                    stmt += ' with grant option'
                logger.debug(stmt)
                conn.execute(stmt)
            for col in table.c:
                seq_privs = [x for x in privs if x.lower() in __sequence_privs]
                for priv in seq_privs:
                    if has_implicit_sequence(col):
                        sequence_name = "%s_%s_seq" % (table.name, col.name)
                        logger.debug('column %s of table %s has associated sequence %s' % (col, table, sequence_name))
                        stmt = 'grant %s on sequence %s to %s' % \
                            (priv, sequence_name, role)
                        logger.debug(stmt)
                        if privilege == 'admin':
                            stmt += ' with grant option'
                        conn.execute(stmt)
    except Exception as e:
        logger.error('users.set_privilege(): %s %s' % (type(e), utils.utf8(e)))
        trans.rollback()
        raise
    else:
        trans.commit()
    finally:
        conn.close()


def current_user():
    """Return the name of the current user.
    """
    r = db.engine.execute('select current_user;')
    user = r.fetchone()[0]
    r.close()
    return user


def set_password(password, user=None):
    """
    Set a user's password.

    If user is None then change the password of the current user.
    """
    if not user:
        user = current_user()
    conn = db.engine.connect()
    trans = conn.begin()
    try:
        stmt = "alter role %s with encrypted password '%s'" % (user, password)
        conn.execute(stmt)
    except Exception as e:
        logger.error('users.set_password(): %s %s' % (type(e), utils.utf8(e)))
        trans.rollback()
    else:
        trans.commit()
    finally:
        conn.close()


class UsersEditor(editor.GenericEditorView):
    """
    """

    def __init__(self, ):
        """
        """
        filename = os.path.join(
            paths.lib_dir(), 'plugins', 'users', 'ui.glade')
        super().__init__(filename)

        if db.engine.name not in ('postgres', 'postgresql'):
            msg = _('The Users editor is only valid on a PostgreSQL database')
            utils.message_dialog(utils.utf8(msg))
            return

        # TODO: should allow anyone to view the priveleges but only
        # admins to change them
        logger.debug('current user is %s' % current_user())
        if not has_privileges(current_user(), 'admin'):
            msg = _('You do not have privileges to change other '\
                        'user privileges')
            utils.message_dialog(utils.utf8(msg))
            return
        # setup the users tree
        tree = self.widgets.users_tree

        # remove any old columns
        for column in tree.get_columns():
            tree.remove_column(column)

        renderer = Gtk.CellRendererText()
        def cell_data_func(col, cell, model, it, data=None):
            value = model[it][0]
            cell.set_property('text', value)
        tree.insert_column_with_data_func(0, _('Users'), renderer,
                                          cell_data_func)
        self.connect(tree, 'cursor-changed', self.on_cursor_changed)
        self.connect(renderer, 'edited', self.on_cell_edited)

        # connect the filter_check and also adds the users to the users_tree
        self.connect('filter_check', 'toggled', self.on_filter_check_toggled)
        self.widgets.filter_check.set_active(True)

        def on_toggled(button, priv=None):
            buttons = (self.widgets.read_button, self.widgets.write_button,
                       self.widgets.admin_button)
            role = self.get_selected_user()
            active = button.get_active()
            if active and not has_privileges(role, priv):
                logger.debug('grant %s to %s' % (priv, role))
                try:
                    set_privilege(role, priv)
                except Exception as e:
                    utils.message_dialog(utils.utf8(e), Gtk.MessageType.ERROR,
                                         parent=self.get_window())
            return True

        self.connect('read_button', 'toggled', on_toggled, 'read')
        self.connect('write_button', 'toggled', on_toggled, 'write')
        self.connect('admin_button', 'toggled', on_toggled, 'admin')

        # only superusers can toggle the admin flag
        stmt = "select rolname from pg_roles where rolsuper is true and rolname = '%s'" % current_user()
        r = db.engine.execute(stmt).fetchone()
        if r:
            self.widgets.admin_button.props.sensitive = True
        else:
            self.widgets.admin_button.props.sensitive = False

        self.builder.connect_signals(self)

    def get_selected_user(self):
        """
        Return the user name currently selected in the users_tree
        """
        tree = self.widgets.users_tree
        path, column = tree.get_cursor()
        return tree.get_model()[path][0]

    new_user_message = _('Enter a user name')

    def on_add_button_clicked(self, button, *args):
        tree = self.widgets.users_tree
        column = tree.get_column(0)
        cell = column.get_cell_renderers()[0]
        model = tree.get_model()
        treeiter = model.append([self.new_user_message])
        path = model.get_path(treeiter)
        tree.set_cursor(path, column, start_editing=True)

    def on_remove_button_clicked(self, button, *args):
        """
        """
        user = self.get_selected_user()
        msg = _('Are you sure you want to remove user <b>%(name)s</b>?\n\n'
                '<i>It is possible that this user could have permissions '
                'on other databases not related to Ghini.</i>') \
            % {'name': user}
        if not utils.yes_no_dialog(msg):
            return

        try:
            drop(user, revoke=True)
        except Exception as e:
            utils.message_dialog(utils.utf8(e), Gtk.MessageType.ERROR,
                                 parent=self.get_window())
        else:
            active = self.widgets.filter_check.get_active()
            self.populate_users_tree(only_bauble=active)


    def  on_filter_check_toggled(self, button, *args):
        """
        """
        active = button.get_active()
        self.populate_users_tree(active)


    def populate_users_tree(self, only_bauble=True):
        """
        Populate the users tree with the users from the database.

        Arguments:
        - `only_bauble`: Show only those users with at least read
          permissions on the database.
        """
        tree = self.widgets.users_tree
        utils.clear_model(tree)
        model = Gtk.ListStore(str)
        for user in get_users():
            if only_bauble and has_privileges(user, 'read'):
                model.append([user])
            elif not only_bauble:
                model.append([user])
        tree.set_model(model)
        if len(model) > 0:
            tree.set_cursor('0')


    def on_pwd_button_clicked(self, button, *args):
        dialog = self.widgets.pwd_dialog
        dialog.set_transient_for(self.get_window())
        def _on_something(d, *args):
            d.hide()
            return True
        self.connect(dialog,  'delete-event', _on_something)
        self.connect(dialog, 'close', _on_something)
        self.connect(dialog, 'response', _on_something)
        self.widgets.pwd_entry1.set_text('')
        self.widgets.pwd_entry2.set_text('')
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            pwd1 = self.widgets.pwd_entry1.get_text()
            pwd2 = self.widgets.pwd_entry2.get_text()
            user = self.get_selected_user()
            if pwd1 == '' or pwd2 == '':
                msg = _('The password for user <b>%s</b> has not been '
                        'changed.') % user
                utils.message_dialog(msg, Gtk.MessageType.WARNING,
                                     parent=self.get_window())
                return
            elif pwd1 != pwd2:
                msg = _('The passwords do not match.  The password for '
                        'user <b>%s</b> has not been changed.') % user
                utils.message_dialog(msg, Gtk.MessageType.WARNING,
                                     parent=self.get_window())
                return
            else:
                try:
                    set_password(pwd1, user)
                except Exception as e:
                    utils.message_dialog(utils.utf8(e), Gtk.MessageType.ERROR,
                                         parent=self.get_window())

        # TODO: show a dialog that says the pwd has been changed or
        # just put a message in the status bar


    def get_window(self):
        return self.widgets.main_dialog


    def start(self):
        self.get_window().run()
        self.cleanup()


    buttons = {'admin': 'admin_button',
               'write': 'write_button',
               'read': 'read_button'}

    def on_cursor_changed(self, tree):
        """
        """

        def _set_buttons(mode):
            logger.debug('%s: %s' % (role, mode))
            if mode:
                self.widgets[self.buttons[mode]].set_active(True)
            not_modes = [p for p in list(self.buttons.keys()) if p != mode]
            for m in not_modes:
                self.widgets[self.buttons[m]].props.active = False

        role = self.get_selected_user()
        if role not in get_users():
            # the cell is being editing and the user hasn't been added
            # to the database
            column = tree.get_column(0)
            cell = column.get_cell_renderers()[0]
            cell.props.editable = True
            _set_buttons(None)
            return

        if has_privileges(role, 'admin'):
            _set_buttons('admin')
        elif has_privileges(role, 'write'):
            _set_buttons('write')
        elif has_privileges(role, 'read'):
            _set_buttons('read')
        else:
            _set_buttons(None)


    def on_cell_edited(self, cell, path, new_text, data=None):
        model = self.widgets.users_tree.get_model()
        user = new_text
        if user == self.new_user_message:
            # didn't change so don't add the user
            treeiter = model.get_iter((len(model)-1,))
            model.remove(treeiter)
            return True
        model[path] = (user,)
        try:
            create_user(user)
            set_privilege(user, 'read')
        except Exception as e:
            utils.message_dialog(utils.utf8(e), Gtk.MessageType.ERROR,
                                 parent=self.get_window())
            model.remove(model.get_iter(path))
        else:
            self.widgets.read_button.props.active = True
            cell.props.editable = False
        return False



class UsersTool(pluginmgr.Tool):

    label = _("Users")

    @classmethod
    def start(self):
        UsersEditor().start()

# TODO: need some way to disable the plugin/tool if not a postgres database

class UsersPlugin(pluginmgr.Plugin):

    tools = []

    @classmethod
    def init(cls):
        if bauble.db.engine.name != 'postgresql':
            del cls.tools[:]
        elif bauble.db.engine.name == 'postgresql' and not cls.tools:
            cls.tools.append(UsersTool)

plugin = UsersPlugin
