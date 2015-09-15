# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Brett Adams
# Copyright 2015 Mario Frasca <mario@anche.no>.
#
# This file is part of bauble.classic.
#
# bauble.classic is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# bauble.classic is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bauble.classic. If not, see <http://www.gnu.org/licenses/>.
#
# connmgr.py
#

"""
The connection manager provides a GUI for creating and opening
connections. This is the first thing displayed when Bauble starts.
"""
import os
import copy
import traceback

import logging
logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)

import gtk

from bauble.i18n import _
import bauble.utils as utils
from bauble.error import check
import bauble
import bauble.paths as paths
import bauble.prefs as prefs

from bauble.editor import (
    GenericEditorView, GenericEditorPresenter)


working_dbtypes = []
dbtypes = []

## prepare the above global variables
try:
    try:
        import pysqlite2
        assert(pysqlite2)
    except Exception:
        import sqlite3
        assert(sqlite3)
    dbtypes.append('SQLite')
    working_dbtypes.append('SQLite')
except ImportError, e:
    logger.warning('ConnMgrPresenter: %s' % e)
for (module, name) in (
        ('psycopg2', 'PostgreSQL'),
        ('MySQLdb', 'MySQL'),
        ('pyodbc', 'MS SQL Server'),
        ('cx_Oracle', 'Oracle'),
        ):
    try:
        dbtypes.append(name)
        __import__(module)
        working_dbtypes.append(name)
    except ImportError, e:
        logger.info('ConnMgrPresenter: %s' % e)


def type_combo_cell_data_func(combo, renderer, model, iter, data=None):
    """passed to the gtk method set_cell_data_func

    item is sensitive iff in working_dbtypes
    """
    dbtype = model[iter][0]
    sensitive = dbtype in working_dbtypes
    renderer.set_property('sensitive', sensitive)
    renderer.set_property('text', dbtype)


class ConnMgrPresenter(GenericEditorPresenter):
    """
    The main class that starts the connection manager GUI.

    :param default: the name of the connection to select from the list
      of connection names
    """

    widget_to_field_map = {
        'name_combo': 'connection_name',  # and self.connection_names
        'usedefaults_chkbx': 'use_defaults',
        'type_combo': 'dbtype',
        'file_entry': 'filename',
        'database_entry': 'database',
        'host_entry': 'host',
        'user_entry': 'user',
        'passwd_chkbx': 'passwd',
        'pictureroot2_entry': 'pictureroot',
        'pictureroot_entry': 'pictureroot',
        }

    view_accept_buttons = ['cancel_button', 'connect_button']

    def __init__(self, view=None):
        self.filename = self.database = self.host = self.user = \
            self.pictureroot = self.connection_name = ''
        self.use_defaults = True
        self.passwd = False
        ## initialize comboboxes, so we can fill them in
        view.combobox_init('name_combo')
        view.combobox_init('type_combo', dbtypes, type_combo_cell_data_func)
        self.connection_names = []
        self.connections = prefs.prefs[bauble.conn_list_pref] or {}
        for ith_connection_name in self.connections:
            view.combobox_append_text('name_combo', ith_connection_name)
            self.connection_names.append(ith_connection_name)
        if self.connection_names:
            self.connection_name = prefs.prefs[bauble.conn_default_pref]
            if self.connection_name not in self.connections:
                self.connection_name = self.connection_names[0]
            self.dbtype = self.connections[self.connection_name]['type']
        else:
            self.dbtype = ''
            self.connection_name = None
        GenericEditorPresenter.__init__(
            self, model=self, view=view, refresh_view=True)
        logo_path = os.path.join(paths.lib_dir(), "images", "bauble_logo.png")
        view.image_set_from_file('logo_image', logo_path)
        view.set_title('%s %s' % ('Bauble', bauble.version))
        try:
            view.set_icon(gtk.gdk.pixbuf_new_from_file(bauble.default_icon))
        except:
            pass

    def refresh_view(self):
        GenericEditorPresenter.refresh_view(self)
        conn_list = self.connections
        if conn_list is None or len(conn_list.keys()) == 0:
            self.view.widget_set_visible('noconnectionlabel', True)
            self.view.widget_set_visible('expander', False)
        else:
            self.view.widget_set_visible('expander', True)
            self.view.widget_set_visible('noconnectionlabel', False)
            if self.dbtype == 'SQLite':
                self.view.widget_set_visible('sqlite_parambox', True)
                self.view.widget_set_visible('dbms_parambox', False)
                self.refresh_entries_sensitive()
            else:
                self.view.widget_set_visible('dbms_parambox', True)
                self.view.widget_set_visible('sqlite_parambox', False)

    def on_usedefaults_chkbx_toggled(self, widget, *args):
        self.on_chkbx_toggled(widget, *args)
        self.refresh_entries_sensitive()

    def refresh_entries_sensitive(self):
        x = not self.use_defaults
        self.view.widget_set_sensitive('file_entry', x)
        self.view.widget_set_sensitive('pictureroot_entry', x)
        self.view.widget_set_sensitive('file_btnbrowse', x)
        self.view.widget_set_sensitive('pictureroot_btnbrowse', x)

    def on_dialog_response(self, dialog, response, data=None):
        """
        The dialog's response signal handler.
        """
        self._error = False
        if response == gtk.RESPONSE_OK:
            settings = self.get_params()
            dbtype = self.dbtype
            if dbtype == 'SQLite':
                filename = settings['file']
                if not os.path.exists(filename):
                    path, f = os.path.split(filename)
                    if not os.access(path, os.R_OK):
                        self._error = True
                        msg = _("Bauble does not have permission to "
                                "read the directory:\n\n%s") % path
                        utils.message_dialog(msg, gtk.MESSAGE_ERROR)
                    elif not os.access(path, os.W_OK):
                        self._error = True
                        msg = _("Bauble does not have permission to "
                                "write to the directory:\n\n%s") % path
                        utils.message_dialog(msg, gtk.MESSAGE_ERROR)
                elif not os.access(filename, os.R_OK):
                    self._error = True
                    msg = _("Bauble does not have permission to read the "
                            "database file:\n\n%s") % filename
                    utils.message_dialog(msg, gtk.MESSAGE_ERROR)
                elif not os.access(filename, os.W_OK):
                    self._error = True
                    msg = _("Bauble does not have permission to "
                            "write to the database file:\n\n%s") % filename
                    utils.message_dialog(msg, gtk.MESSAGE_ERROR)
            if not self._error and not prefs.testing:
                self.save_current_to_prefs()
                prefs.prefs[prefs.picture_root_pref] = settings.get(
                    'pictures', '')
        elif response == gtk.RESPONSE_CANCEL or \
                response == gtk.RESPONSE_DELETE_EVENT:
            if not self.compare_prefs_to_saved(self.connection_name):
                msg = _("Do you want to save your changes?")
                if utils.yes_no_dialog(msg):
                    self.save_current_to_prefs()

        # system-defined GtkDialog responses are always negative, in which
        # case we want to hide it
        if response < 0:
            dialog.hide()
            #dialog.emit_stop_by_name('response')

        return response

    def on_dialog_close_or_delete(self, widget, event=None):
        self.view.get_window().hide()
        return True

    def set_active_connection_by_name(self, name):
        """initialize name_combo, then set active

        sets the name of the connection in the name combo, this
        causes on_name_combo_changed to be fired which changes the param
        box type and set the connection parameters
        """
        check(hasattr(self, "name_combo"))
        active = 0
        conn_list = self.connections
        if conn_list is None:
            return
        for i, conn in enumerate(conn_list):
            self.name_combo.insert_text(i, conn)
            if conn == name:
                active = i
        self.combobox_set_active('name_combo', active)

    def remove_connection(self, name):
        """remove named connection, from combobox and from self
        """
        if name in self.connection_names:
            position = self.connection_names.index(name)
            self.connection_names.remove(name)
            del self.connections[name]
            self.view.combobox_remove('name_combo', position)
            self.refresh_view()

    def on_remove_button_clicked(self, button, data=None):
        """
        remove the connection from connection list, this does not affect
        the database or its data
        """
        msg = (_('Are you sure you want to remove "%s"?\n\n'
                 '<i>Note: This only removes the connection to the database '
                 'and does not affect the database or its data</i>')
               % self.connection_name)

        if not utils.yes_no_dialog(msg):
            return
        self.remove_connection(self.connection_name)
        self.connection_name = None
        self.view.combobox_set_active('name_combo', 0)

    def on_add_button_clicked(self, button, data=None):
        d = gtk.Dialog(_("Enter a connection name"), self.view.get_window(),
                       gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                       (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        d.set_default_response(gtk.RESPONSE_ACCEPT)
        d.set_default_size(250, -1)
        entry = gtk.Entry()
        entry.connect("activate",
                      lambda entry: d.response(gtk.RESPONSE_ACCEPT))
        d.vbox.pack_start(entry)
        d.show_all()
        d.run()
        name = entry.get_text()
        d.destroy()
        if name is not '':
            self.view.combobox_prepend_text('name_combo', name)
            self.view.expander_set_expanded('expander', True)
            self.view.combobox_set_active('name_combo', 0)

    def save_current_to_prefs(self):
        """
        save connection parameters in the prefs
        """
        if self.connection_name is None or prefs.testing:
            return
        if bauble.conn_list_pref not in prefs.prefs:
            prefs.prefs[bauble.conn_list_pref] = {}
        params = copy.copy(self.get_params())
        params["type"] = self.dbtype
        conn_list = self.connections
        conn_list[self.connection_name] = params
        prefs.prefs[bauble.conn_list_pref] = conn_list
        prefs.prefs.save()

    def compare_prefs_to_saved(self, name):
        """
        name is the name of the connection in the prefs
        """
        if name is None:  # in case no name selected, can happen on first run
            return True
        conn_list = prefs.prefs[bauble.conn_list_pref]
        if conn_list is None or name not in conn_list:
            return False
        stored_params = conn_list[name]
        params = copy.copy(self.get_params())
        params["type"] = self.dbtype
        return params == stored_params

    def on_name_combo_changed(self, combo, data=None):
        """
        the name changed so fill in everything else
        """
        prev_connection_name = self.connection_name

        conn_list = self.connections
        if prev_connection_name is not None:
            ## we are leaving some valid settings
            if prev_connection_name not in conn_list:
                msg = _("Do you want to save %s?") % prev_connection_name
                if utils.yes_no_dialog(msg):
                    self.save_current_to_prefs()
                else:
                    self.remove_connection(prev_connection_name)
            elif not self.compare_prefs_to_saved(prev_connection_name):
                msg = (_("Do you want to save your changes to %s ?")
                       % prev_connection_name)
                if utils.yes_no_dialog(msg):
                    self.save_current_to_prefs()

        self.on_combo_changed(combo, data)  # this updates self.connection_name
        logger.debug("changing form >%s< to >%s<" %
                     (prev_connection_name, self.connection_name))

        if self.connection_name in conn_list:
            ## we are retrieving connection info from the global settings
            if conn_list[self.connection_name]['type'] not in dbtypes:
                # in case the connection type has changed or isn't supported
                # on this computer
                self.view.combobox_set_active('type_combo', -1)
            else:
                index = dbtypes.index(conn_list[self.connection_name]
                                      ["type"])
                self.view.combobox_set_active('type_combo', index)
                self.set_params(conn_list[self.connection_name])
        else:  # this is for new connections
            self.view.combobox_set_active('type_combo', 0)
        self.refresh_view()

    def get_passwd(self, title=_("Enter your password"), before_main=False):
        """
        Show a dialog with and entry and return the value entered.
        """
        # TODO: if self.dialog is None then ask from the command line
        # or just set dialog parent to None
        d = gtk.Dialog(title, self.view.get_window(),
                       gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                       (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        d.set_gravity(gtk.gdk.GRAVITY_CENTER)
        d.set_position(gtk.WIN_POS_CENTER)
        d.set_default_response(gtk.RESPONSE_ACCEPT)
        d.set_default_size(250, -1)
        entry = gtk.Entry()
        entry.set_visibility(False)
        entry.connect("activate",
                      lambda entry: d.response(gtk.RESPONSE_ACCEPT))
        d.vbox.pack_start(entry)
        d.show_all()
        d.run()
        passwd = entry.get_text()
        d.destroy()
        return passwd

    def parameters_to_uri(self, params):
        """
        return connections paramaters as a uri
        """
        import copy
        subs = copy.copy(params)
        if params['type'].lower() == "sqlite":
            filename = params['file'].replace('\\', '/')
            uri = "sqlite:///" + filename
            return uri
        subs['type'] = params['type'].lower()
        if 'port' in params:
            template = "%(type)s://%(user)s@%(host)s:%(port)s/%(db)s"
        else:
            template = "%(type)s://%(user)s@%(host)s/%(db)s"
        if params["passwd"] is True:
            subs["passwd"] = self.get_passwd()
            if subs["passwd"]:
                template = template.replace('@', ':%(passwd)s@')
        uri = template % subs
        options = []
        if 'options' in params:
            options = params['options'].join('&')
            uri.append('?')
            uri.append(options)
        return uri

    @property
    def connection_uri(self):
        type = self.dbtype

        params = copy.copy(self.get_params())
        params['type'] = type.lower()
        return self.parameters_to_uri(params)

    def _get_connection_name(self):
        return self.connection_name

    def check_parameters_valid(self):
        """
        check that all of the information in the current connection
        is valid and return true or false

        NOTE: this was meant to be used to implement an eclipse style
        information box at the top of the dialog but it's not really
        used right now
        """
        if self.name_combo.get_active_text() == "":
            return False, _("Please choose a name for this connection")
        params = self.params_box
        if params["user"] == "":
            return False, _("Please choose a user name for this connection")

    def get_params(self):
        if self.dbtype == 'SQLite':
            if self.use_defaults is True:
                self.filename = os.path.join(
                    paths.user_dir(), self.connection_name + '.db')
                self.pictureroot = os.path.join(
                    paths.user_dir(), self.connection_name)
            result = {'file': self.filename,
                      'default': self.use_defaults,
                      'pictures': self.pictureroot}
        else:
            result = {'db': self.database,
                      'host': self.host,
                      'user': self.user,
                      'pictures': self.pictureroot,
                      'passwd': self.passwd,
                      }
        return result

    def set_params(self, params):
        if self.dbtype == 'SQLite':
            self.filename = params['file']
            self.use_defaults = params['default']
            self.pictureroot = params['pictures']
        else:
            self.database = params['db']
            self.host = params['host']
            self.user = params['user']
            self.pictureroot = params['pictures']
            self.passwd = params['passwd']
        self.refresh_view()


def start_connection_manager(default_conn=None):
    '''activate connection manager and return connection name and uri
    '''
    glade_path = os.path.join(paths.lib_dir(), "connmgr.glade")
    view = GenericEditorView(
        glade_path,
        parent=None,
        root_widget_name='main_dialog')

    cm = ConnMgrPresenter(view)
    result = cm.start()
    if result == -5:
        return cm.connection_name, cm.connection_uri
    else:
        return None, None
