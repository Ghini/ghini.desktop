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
import logging
import os
import re
from gettext import gettext as _
from typing import Any, Optional

import bauble
import bauble.db as db
import bauble.editor as editor
import bauble.paths as paths
import bauble.pluginmgr as pluginmgr
import bauble.utils as utils
from bauble.error import check

# from bauble.error import CheckConditionError


logger: Any
from bauble.gtkinit import Gtk

# from sqlalchemy import *
from sqlalchemy import Integer

# from sqlalchemy.exc import *
from sqlalchemy.exc import ProgrammingError

# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.ext.declarative import DeclarativeMeta
# from sqlalchemy.orm.exc import *


logger = logging.getLogger(__name__)


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
#         warning(utils.to_unicode(e))
#         trans.rollback()
#         conn.close()
#         return None
#     else:
#         trans.commit()
#     return conn


def safe_set_text(gtk_widget, text) -> None:
    """
    Sets the text of a Gtk widget replacing None with an empty string.

    :param label: Instance of a Gtk widget
    :param text: The text to set, which may be None
    """
    if text is None:
        text = ""
    gtk_widget.set_text(text)


def get_users():
    """Return the list of user names."""
    stmt = "select rolname from pg_roles where rolcanlogin is true;"
    return [r[0] for r in db.engine.execute(stmt)]


def get_groups():
    """Return the list of group names."""
    stmt = "select rolname from pg_roles where rolcanlogin is false;"
    return [r[0] for r in db.engine.execute(stmt)]


def _create_role(
    name, password: Optional[Any] = None, login: bool = False, admin: bool = False
) -> None:
    """Internal helper to create a role."""
    try:
        with db.engine.begin() as conn:
            stmt = f"create role {name} INHERIT"
            if login:
                stmt += " LOGIN"
            if admin:
                stmt += " CREATEROLE"
            if password:
                stmt += f" PASSWORD '{password}'"
            conn.execute(stmt)
    except Exception as e:
        logger.error("users._create_role(): %s %s", type(e), utils.to_unicode(e))
        raise


def create_user(
    name,
    password: Optional[Any] = None,
    admin: bool = False,
    groups: Optional[Any] = None,
) -> None:
    """Create a role that can login."""
    if groups is None:
        groups = []

    _create_role(name, password, login=True, admin=False)

    try:
        with db.engine.begin() as conn:
            from sqlalchemy import text

            for group in groups:
                conn.execute(text(f"grant {group} to {name}"))
            conn.execute(
                text(
                    f"grant connect on database {bauble.db.engine.url.database} to {name}"
                )
            )
    except Exception as e:
        logger.error("users.create_user(): %s %s", type(e), utils.to_unicode(e))
        raise


def create_group(name, admin: bool = False) -> None:
    """
    Create a role that can't login.
    """
    _create_role(name, login=False, password=None, admin=admin)


def add_member(name, groups: Optional[Any] = None) -> None:
    """Add name to groups."""
    if groups is None:
        groups = []
    try:
        with db.engine.begin() as conn:
            from sqlalchemy import text

            for group in groups:
                conn.execute(text(f'grant "{group}" to {name}'))
    except Exception as e:
        logger.error("users.add_member(): %s %s", type(e), utils.to_unicode(e))


def remove_member(name, groups: Optional[Any] = None) -> None:
    """Remove name from groups."""
    if groups is None:
        groups = []
    try:
        with db.engine.begin() as conn:
            from sqlalchemy import text

            for group in groups:
                conn.execute(text(f"revoke {group} from {name}"))
    except Exception as e:
        logger.error("users.remove_member(): %s %s", type(e), utils.to_unicode(e))


from sqlalchemy import text


def get_members(group):
    """Return members of group."""
    with db.engine.connect() as conn:
        # Get group OID
        stmt = text("SELECT oid FROM pg_roles WHERE rolname = :group")
        gid = conn.execute(stmt, {"group": group}).scalar_one_or_none()
        if gid is None:
            return []

        # Get members' role names
        stmt = text(
            """
            SELECT rolname FROM pg_roles
            WHERE oid IN (
                SELECT member FROM pg_auth_members WHERE roleid = :gid
            )
        """
        )
        result = conn.execute(stmt, {"gid": gid})
        return [r[0] for r in result.all()]


def delete(role, revoke: bool = False) -> None:
    """See drop()"""
    drop(role, revoke)


def drop(role, revoke: bool = False) -> None:
    """Drop a user from the database."""
    try:
        with db.engine.begin() as conn:
            if revoke:
                set_privilege(role, None)
            from sqlalchemy import text

            conn.execute(text(f"drop role {role};"))
    except Exception as e:
        logger.error("users.drop(): %s %s", type(e), utils.to_unicode(e))
        raise


def get_privileges(role) -> None:
    """Return the privileges the user has on the current database.

    Arguments:
    - `role`:
    """
    # TODO: should we return read, write, admin or the specific
    # privileges...this can basically just be a wrapped call to
    # has_privileges()
    raise NotImplementedError


_privileges: Any = {
    "read": ["connect", "select"],
    "write": [
        "connect",
        "usage",
        "select",
        "update",
        "insert",
        "delete",
        "execute",
        "trigger",
        "references",
    ],
    "admin": ["all"],
}

_database_privs: Any = ["create", "temporary", "temp"]

_table_privs: Any = [
    "select",
    "insert",
    "update",
    "delete",
    "references",
    "trigger",
    "all",
]

__sequence_privs: Any = ["usage", "select", "update", "all"]


def _parse_acl(acl):
    """
    returns a list of acls of (role, privs, granter)
    """
    rx = re.compile(r"[{]?(.*?)=(.*?)\/(.*?)[,}]")
    return rx.findall(acl)


def has_privileges(role, privilege):
    """Return True/False if role has privileges.

    Arguments:
    - `role`:
    - `privileges`:
    """
    from sqlalchemy import text

    # if the user has all on database with grant privileges and he has
    # the grant privilege on the database then he has admin and he can
    # create roles
    if privilege == "admin":
        # test admin privileges on the database
        for priv in _database_privs:
            stmt = text("select has_database_privilege(:role, :db, :priv)")
            with db.engine.connect() as conn:
                r = conn.execute(
                    stmt,
                    {"role": role, "db": bauble.db.engine.url.database, "priv": priv},
                ).scalar_one_or_none()
                if not r:
                    return False
        privs = set(_table_privs).intersection(_privileges["write"])
    else:
        privs = set(_table_privs).intersection(_privileges[privilege])

    # TODO: has_sequence_privileges will be introduced in PostgreSQL 8.5

    # test the privileges on the tables and sequences
    for table in db.metadata.sorted_tables:
        for priv in privs:
            stmt = text("select has_table_privilege(:role, :table, :priv)")
            try:
                with db.engine.connect() as conn:
                    r = conn.execute(
                        stmt, {"role": role, "table": table.name, "priv": priv}
                    ).scalar_one_or_none()
                    if not r:
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
    if privilege == "admin":
        stmt = f"select rolname from pg_roles where rolcreaterole is true and rolname = '{role}'"
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
    return (
        column.primary_key
        and column.autoincrement
        and isinstance(column.type, Integer)
        and not column.foreign_keys
    )


def set_privilege(role, privilege) -> None:
    """Set the role's privileges."""
    check(
        privilege in ("read", "write", "admin", None),
        f"invalid privilege: {privilege}",
    )
    if privilege:
        privs = _privileges[privilege]

    try:
        from sqlalchemy import text

        with db.engine.begin() as conn:
            # revoke everything first
            for table in db.metadata.sorted_tables:
                conn.execute(text(f"revoke all on table {table.name} from {role};"))
                for col in table.c:
                    if hasattr(col, "sequence"):
                        conn.execute(
                            text(
                                f"revoke all on sequence {col.sequence.name} from {role};"
                            )
                        )

            conn.execute(
                text(
                    f"revoke all on database {bauble.db.engine.url.database} from {role}"
                )
            )
            conn.execute(text(f"alter role {role} with nocreaterole"))

            if not privilege:
                return

            # Grant privileges on the database
            if privilege == "admin":
                stmt = f"grant all on database {bauble.db.engine.url.database} to {role} with grant option"
                conn.execute(stmt)
                conn.execute(text(f"alter role {role} with createuser"))

            # Grant on tables and sequences
            for table in bauble.db.metadata.sorted_tables:
                logger.debug("granting privileges on table %s", table)
                for priv in [x for x in privs if x.lower() in _table_privs]:
                    stmt = f"grant {priv} on {table.name} to {role}"
                    if privilege == "admin":
                        stmt += " with grant option"
                    logger.debug(stmt)
                    conn.execute(stmt)

                for col in table.c:
                    for priv in [x for x in privs if x.lower() in __sequence_privs]:
                        if has_implicit_sequence(col):
                            sequence_name = f"{table.name}_{col.name}_seq"
                            stmt = f"grant {priv} on sequence {sequence_name} to {role}"
                            if privilege == "admin":
                                stmt += " with grant option"
                            logger.debug(stmt)
                            conn.execute(stmt)

    except Exception as e:
        logger.error("users.set_privilege(): %s %s", type(e), utils.to_unicode(e))
        raise


def current_user():
    """Return the name of the current user."""
    return db.current_user()


def set_password(password, user: Optional[Any] = None) -> None:
    """Set a user's password."""
    if not user:
        user = current_user()

    try:
        with db.engine.begin() as conn:
            stmt = f"alter role {user} with encrypted password '{password}'"
            conn.execute(stmt)
    except Exception as e:
        logger.error("users.set_password(): %s %s", type(e), utils.to_unicode(e))


class UsersEditor(editor.GenericEditorView):
    """ """

    def __init__(self) -> None:
        """ """
        filename = os.path.join(paths.lib_dir(), "plugins", "users", "ui.glade")
        super().__init__(filename)

        if db.engine.name not in ("postgres", "postgresql"):
            msg = _("The Users editor is only valid on a PostgreSQL database")
            utils.message_dialog(utils.to_unicode(msg))
            return

        # TODO: should allow anyone to view the priveleges but only
        # admins to change them
        logger.debug(f"current user is {current_user()}")
        if not has_privileges(current_user(), "admin"):
            msg = _("You do not have privileges to change other " "user privileges")
            utils.message_dialog(utils.to_unicode(msg))
            return
        # setup the users tree
        tree = self.widgets.users_tree

        # remove any old columns
        for column in tree.get_columns():
            tree.remove_column(column)

        renderer = Gtk.CellRendererText()

        def cell_data_func(col, cell, model, it, data=None):
            value = model[it][0]
            cell.set_property("text", value)

        tree.insert_column_with_data_func(0, _("Users"), renderer, cell_data_func)
        self.connect(tree, "cursor-changed", self.on_cursor_changed)
        self.connect(renderer, "edited", self.on_cell_edited)

        # connect the filter_check and also adds the users to the users_tree
        self.connect("filter_check", "toggled", self.on_filter_check_toggled)
        self.widgets.filter_check.set_active(True)

        def on_toggled(button, priv=None):
            role = self.get_selected_user()
            active = button.get_active()
            if active and not has_privileges(role, priv):
                logger.debug(f"grant {priv} to {role}")
                try:
                    set_privilege(role, priv)
                except Exception as e:
                    utils.message_dialog(
                        utils.to_unicode(e),
                        Gtk.MessageType.ERROR,
                        parent=self.get_window(),
                    )
            return True

        self.connect("read_button", "toggled", on_toggled, "read")
        self.connect("write_button", "toggled", on_toggled, "write")
        self.connect("admin_button", "toggled", on_toggled, "admin")

        # only superusers can toggle the admin flag
        stmt = f"select rolname from pg_roles where rolsuper is true and rolname = '{current_user()}'"
        r = db.engine.execute(stmt).fetchone()
        if r:
            self.widgets.admin_button.set_sensitive = True
        else:
            self.widgets.admin_button.set_sensitive = False

        self.builder.connect_signals(self)

    def get_selected_user(self):
        """
        Return the user name currently selected in the users_tree
        """
        tree = self.widgets.users_tree
        path, column = tree.get_cursor()
        return tree.get_model()[path][0]

    new_user_message: Any = _("Enter a user name")

    def on_add_button_clicked(self, button, *args) -> None:
        tree = self.widgets.users_tree
        column = tree.get_column(0)
        column.get_cell_renderers()[0]
        model = tree.get_model()
        treeiter = model.append([self.new_user_message])
        path = model.get_path(treeiter)
        tree.set_cursor(path, column, start_editing=True)

    def on_remove_button_clicked(self, button, *args) -> None:
        """ """
        user = self.get_selected_user()
        msg = _(
            "Are you sure you want to remove user <b>%(name)s</b>?\n\n"
            "<i>It is possible that this user could have permissions "
            "on other databases not related to Ghini.</i>"
        ) % {"name": user}
        if not utils.yes_no_dialog(msg):
            return

        try:
            drop(user, revoke=True)
        except Exception as e:
            utils.message_dialog(
                utils.to_unicode(e), Gtk.MessageType.ERROR, parent=self.get_window()
            )
        else:
            active = self.widgets.filter_check.get_active()
            self.populate_users_tree(only_bauble=active)

    def on_filter_check_toggled(self, button, *args) -> None:
        """ """
        active = button.get_active()
        self.populate_users_tree(active)

    def populate_users_tree(self, only_bauble: bool = True) -> None:
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
            if only_bauble and has_privileges(user, "read"):
                model.append([user])
            elif not only_bauble:
                model.append([user])
        tree.set_model(model)
        if len(model) > 0:
            tree.set_cursor("0")

    def on_pwd_button_clicked(self, button, *args) -> None:
        dialog = self.widgets.pwd_dialog
        dialog.set_transient_for(self.get_window())

        safe_set_text(self.widgets.pwd_entry1, "")
        safe_set_text(self.widgets.pwd_entry2, "")

        def on_response(d, response_id):
            if response_id == Gtk.ResponseType.OK:
                pwd1 = self.widgets.pwd_entry1.get_text()
                pwd2 = self.widgets.pwd_entry2.get_text()
                user = self.get_selected_user()

                if pwd1 == "" or pwd2 == "":
                    msg = (
                        _("The password for user <b>%s</b> has not been changed.")
                        % user
                    )
                    utils.message_dialog(
                        msg, Gtk.MessageType.WARNING, parent=self.get_window()
                    )
                elif pwd1 != pwd2:
                    msg = (
                        _(
                            "The passwords do not match. The password for user <b>%s</b> has not been changed."
                        )
                        % user
                    )
                    utils.message_dialog(
                        msg, Gtk.MessageType.WARNING, parent=self.get_window()
                    )
                else:
                    try:
                        set_password(pwd1, user)
                    except Exception as e:
                        utils.message_dialog(
                            utils.to_unicode(e),
                            Gtk.MessageType.ERROR,
                            parent=self.get_window(),
                        )

            dialog.destroy()

        dialog.connect("response", on_response)
        dialog.show()

        # TODO: show a dialog that says the pwd has been changed or
        # just put a message in the status bar

    def get_window(self):
        return self.widgets.main_dialog

    def start(self) -> None:
        self.get_window().run()
        self.cleanup()

    buttons: Any = {
        "admin": "admin_button",
        "write": "write_button",
        "read": "read_button",
    }

    def on_cursor_changed(self, tree) -> None:
        """ """

        def _set_buttons(mode):
            logger.debug(f"{role}: {mode}")
            if mode:
                self.widgets[self.buttons[mode]].set_active(True)
            not_modes = [p for p in list(self.buttons.keys()) if p != mode]
            for m in not_modes:
                self.widgets[self.buttons[m]].set_active(False)

        role = self.get_selected_user()
        if role not in get_users():
            # the cell is being edited and the user hasn't been added
            # to the database
            column = tree.get_column(0)
            cell = column.get_cell_renderers()[0]
            cell.set_property("editable", True)
            _set_buttons(None)
            return

        if has_privileges(role, "admin"):
            _set_buttons("admin")
        elif has_privileges(role, "write"):
            _set_buttons("write")
        elif has_privileges(role, "read"):
            _set_buttons("read")
        else:
            _set_buttons(None)

    def on_cell_edited(self, cell, path, new_text, data: Optional[Any] = None):
        model = self.widgets.users_tree.get_model()
        user = new_text
        if user == self.new_user_message:
            # didn't change so don't add the user
            treeiter = model.get_iter((len(model) - 1,))
            model.remove(treeiter)
            return True
        model[path] = (user,)
        try:
            create_user(user)
            set_privilege(user, "read")
        except Exception as e:
            utils.message_dialog(
                utils.to_unicode(e), Gtk.MessageType.ERROR, parent=self.get_window()
            )
            model.remove(model.get_iter(path))
        else:
            self.widgets.read_button.set_active(True)
            cell.set_property("editable", False)
        return False


class UsersTool(pluginmgr.Tool):
    item_position: int = 5
    label: Any = _("Users")
    icon_name: str = "system-users"

    @classmethod
    def start(cls) -> None:
        UsersEditor().start()


# TODO: need some way to disable the plugin/tool if not a postgres database


class UsersPlugin(pluginmgr.Plugin):

    tools: Any = []

    @classmethod
    def init(cls) -> None:
        if bauble.db.engine.name != "postgresql":
            del cls.tools[:]
        elif bauble.db.engine.name == "postgresql" and not cls.tools:
            cls.tools.append(UsersTool)


plugin = UsersPlugin
