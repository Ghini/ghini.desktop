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

import gtk
from sqlalchemy import *

import bauble.utils as utils
from bauble.error import check, CheckConditionError
import bauble
import bauble.paths as paths
from bauble.prefs import prefs
from bauble.utils.log import log, debug, warning
from bauble.i18n import _

# TODO: make the border red for anything the user changes so
# they know if something has changed and needs to be saved, or maybe
# a red line should indicate that the value are valid, i.e. the name
# is in the wrong format, or better just don't the allow the user to leave the
# entry until whatever is there is an the correct format

# TODO: when you start and there are no connections defined then make the user
# create a connection or at least inform them

# TODO: should redo this to use a model view presenter pattern like the new
# editors, makes it easier to handle things like status on the entries

# TODO: allow connecting to a database first to see if the database even,
# exists will probably have to connected using python's dbapi first and
# if the database doesn't exist then we can create it, set some permissions,
# close the connection and then open it using SQLAlchemy

class ConnectionManager:

    """
    The main class that starts the connection manager GUI.
    """

    def _get_working_dbtypes(self, retry=False):
        """
        get for self.working_dbtypes property

        this sets self._working_dbtypes to a dictionary where the
        keys are the database names and the values are the index in
        the connectiona manager's database types
        """
        if self._working_dbtypes != [] and not retry:
            return self._working_dbtypes
        self._working_dbtypes = []
        try:
            try:
                import pysqlite2
            except:
                import sqlite3
            self._working_dbtypes.append('SQLite')
        except ImportError, e:
            warning('ConnectionManager: %s' % e)
        try:
            import psycopg2
            self._working_dbtypes.append('Postgres')
        except ImportError, e:
            warning('ConnectionManager: %s' % e)
        try:
            import MySQLdb
            self._working_dbtypes.append('MySQL')
        except ImportError, e:
            warning('ConnectionManager: %s' % e)

        return self._working_dbtypes

    _dbtypes = ['SQLite', 'Postgres', 'MySQL']
    # a list of dbtypes that are importable
    working_dbtypes = property(_get_working_dbtypes)
    _working_dbtypes = []

    def __init__(self, default=None):
        """
        @param default: the name of the connection to select from the list
        of connection names
        """
        self.default_name = default
        self.current_name = None
        # old_params is used to cache the parameter values for when the param
        # box changes but we want to keep the values, e.g. when the type
        # changes
        self.old_params = {}


    def start(self):
        """
        Show the connection manager.
        """
        self.create_gui()
        self.dialog.connect('response', self.on_dialog_response)
        self.dialog.connect('close', self.on_dialog_close_or_delete)
        self.dialog.connect('delete-event', self.on_dialog_close_or_delete)
        conn_list = prefs[bauble.conn_list_pref]
        if conn_list is None or len(conn_list.keys()) == 0:
            msg = _('You don\'t have any connections in your connection '\
                    'list.\nClose this message and click on "Add" to create '\
                    'a new connection.')
            utils.message_dialog(msg)
        else:
            self.set_active_connection_by_name(self.default_name)
            self._dirty = False

        self._error = True
        name = None
        uri = None
        while name is None or self._error:
            response = self.dialog.run()
            if response == gtk.RESPONSE_OK:
                name = self._get_connection_name()
                uri = self._get_connection_uri()
                if name is None:
                    msg = _('You have to choose or create a new connection ' \
                            'before you can connect to the database.')
                    utils.message_dialog(msg)
            else:
                name = uri = None
                break
        self.dialog.destroy()
        return name, uri


    def on_dialog_response(self, dialog, response, data=None):
        """
        """
        self._error = False
        if response == gtk.RESPONSE_OK:
            settings = self.params_box.get_prefs()
            dbtype = self.widgets.type_combo.get_active_text()
            if dbtype == 'SQLite':
                filename = settings['file']
                if not os.path.exists(filename):
                    path, f = os.path.split(filename)
                    if not os.access(path, os.R_OK):
                        self._error = True
                        msg = _("Bauble does not have permission to "\
                                "read the directory:\n\n%s") % path
                        utils.message_dialog(msg, gtk.MESSAGE_ERROR)
                    elif not os.access(path, os.W_OK):
                        self._error = True
                        msg = _("Bauble does not have permission to "\
                                "write to the directory:\n\n%s") % path
                        utils.message_dialog(msg, gtk.MESSAGE_ERROR)
                elif not os.access(filename, os.R_OK):
                    self._error = True
                    msg = _("Bauble does not have permission to read the "\
                            "database file:\n\n%s") % filename
                    utils.message_dialog(msg, gtk.MESSAGE_ERROR)
                elif not os.access(filename, os.W_OK):
                    self._error = True
                    msg = _("Bauble does not have permission to "\
                            "write to the database file:\n\n%s") % filename
                    utils.message_dialog(msg, gtk.MESSAGE_ERROR)
            if not self._error:
                self.save_current_to_prefs()
        elif response == gtk.RESPONSE_CANCEL or \
             response == gtk.RESPONSE_DELETE_EVENT:
            if not self.compare_prefs_to_saved(self.current_name):
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
        self.dialog.hide()
        return True


    def create_gui(self):
        if self.working_dbtypes is None or len(self.working_dbtypes) == 0:
            msg = _("No Python database connectors installed.\n"\
                    "Please consult the documentation for the "\
                    "prerequesites for installing Bauble.")
            utils.message_dialog(msg, gtk.MESSAGE_ERROR)
            raise Exception(msg)

        glade_path = os.path.join(paths.lib_dir(), "connmgr.glade")
        self.widgets = utils.GladeWidgets(glade_path)

        self.dialog = self.widgets.main_dialog
        try:
            pixbuf = gtk.gdk.pixbuf_new_from_file(bauble.default_icon)
            self.dialog.set_icon(pixbuf)
        except Exception, e:
            utils.message_details_dialog(_('Could not load icon from %s' % \
                                         bauble.default_icon),
                                         traceback.format_exc(),
                                         gtk.MESSAGE_ERROR)

        if bauble.gui is not None and bauble.gui.window is not None:
            self.dialog.set_transient_for(bauble.gui.window)
            if not bauble.gui.window.get_property('visible'):
                self.dialog.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
                self.dialog.set_property('skip-taskbar-hint', False)


        handlers = {'on_add_button_clicked': self.on_add_button_clicked,
                    'on_remove_button_clicked': self.on_remove_button_clicked,
                   }
        self.widgets.signal_autoconnect(handlers)

        # set the logo image manually, its hard to depend on glade to
        # get this right since the image paths may change
        logo = self.widgets.logo_image
        logo_path = os.path.join(paths.lib_dir(), "images", "bauble_logo.png")
        logo.set_from_file(logo_path)

        self.params_box = None
        self.expander_box = self.widgets.expander_box

        # setup the type combo
        self.type_combo = self.widgets.type_combo
        def type_combo_cell_data_func(combo, renderer, model, iter, data=None):
            """
            if the database type is not in self.working_dbtypes then
            make it not sensitive
            """
            dbtype = model[iter][0]
            sensitive = dbtype in self.working_dbtypes
            renderer.set_property('sensitive', sensitive)
            renderer.set_property('text', dbtype)
        utils.setup_text_combobox(self.type_combo, self._dbtypes,
                                  type_combo_cell_data_func)
        self.type_combo.connect("changed", self.on_changed_type_combo)

        # setup the name combo
        self.name_combo = self.widgets.name_combo
        utils.setup_text_combobox(self.name_combo)
        self.name_combo.connect("changed", self.on_changed_name_combo)

        self.dialog.set_focus(self.widgets.connect_button)


    def set_active_connection_by_name(self, name):
        """
        sets the name of the connection in the name combo, this
        causes on_changed_name_combo to be fired which changes the param
        box type and set the connection parameters
        """
        check(hasattr(self, "name_combo"))
        i = 0
        active = 0
        conn_list = prefs[bauble.conn_list_pref]
        if conn_list is None:
            return
        for conn in conn_list:
            self.name_combo.insert_text(i, conn)
            if conn == name:
                active = i
            i += 1
        self.name_combo.set_active(active)


    def remove_connection(self, name):
        """
        if we restrict the user to only removing the current connection
        then it saves us the trouble of having to iter through the model
        """
        conn_list = prefs[bauble.conn_list_pref]
        if name in conn_list:#conn_list.has_key(name):
            del conn_list[name]
            prefs[bauble.conn_list_pref] = conn_list

        model = self.name_combo.get_model()
        for i in range(0, len(model)):
            row = model[i][0]
            if row == name:
                self.name_combo.remove_text(i)
                break


    def on_remove_button_clicked(self, button, data=None):
        """
        remove the connection from connection list, this does not affect
        the database or it's data
        """
        msg = _('Are you sure you want to remove "%s"?\n\n' \
              '<i>Note: This only removes the connection to the database '\
              'and does not affect the database or it\'s data</i>') \
              % self.current_name

        if not utils.yes_no_dialog(msg):
            return
        self.current_name = None
        self.remove_connection(self.name_combo.get_active_text())
        self.name_combo.set_active(0)


    def on_add_button_clicked(self, button, data=None):
        d = gtk.Dialog(_("Enter a connection name"), self.dialog,
                       gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                       (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        d.set_default_response(gtk.RESPONSE_ACCEPT)
        d.set_default_size(250,-1)
        entry = gtk.Entry()
        entry.connect("activate",
		      lambda entry: d.response(gtk.RESPONSE_ACCEPT))
        d.vbox.pack_start(entry)
        d.show_all()
        d.run()
        name = entry.get_text()
        d.destroy()
        if name is not '':
            self.name_combo.prepend_text(name)
            expander = self.widgets.expander.set_expanded(True)
            self.name_combo.set_active(0)

            # TODO:
            # if sqlite.is_supported then sqlite, else set_active(0)
            #self.type_combo.set_active(0)


##    def set_info_label(self, msg=_("Choose a connection")):
##        self.info_label.set_text(msg)


    def save_current_to_prefs(self):
        """
        save connection parameters from the widgets in the prefs
        """
        if self.current_name is None:
            return
        if bauble.conn_list_pref not in prefs:
            prefs[bauble.conn_list_pref] = {}
        settings = copy.copy(self.params_box.get_prefs())
        settings["type"] = self.type_combo.get_active_text()
        conn_list = prefs[bauble.conn_list_pref]
        if conn_list is None:
            conn_list = {}
        conn_list[self.current_name] = settings
        prefs[bauble.conn_list_pref] = conn_list
        prefs.save()


    def compare_prefs_to_saved(self, name):
        """
        name is the name of the connection in the prefs
        """
        if name is None: # in case no name selected, can happen on first run
            return True
        conn_list = prefs[bauble.conn_list_pref]
        if conn_list is None or name not in conn_list:
            return False
        stored_params = conn_list[name]
        params = copy.copy(self.params_box.get_prefs())
        params["type"] = self.type_combo.get_active_text()
        return params == stored_params


    def on_changed_name_combo(self, combo, data=None):
        """
        the name changed so fill in everything else
        """
        name = combo.get_active_text()
        if name is None:
            return

        conn_list = prefs[bauble.conn_list_pref]
        if self.current_name is not None:
            if self.current_name not in conn_list:
                msg = _("Do you want to save %s?") % self.current_name
                if utils.yes_no_dialog(msg):
                    self.save_current_to_prefs()
                else:
                    self.remove_connection(self.current_name)
		    #combo.set_active_iter(active_iter)
                    self.current_name = None
            elif not self.compare_prefs_to_saved(self.current_name):
                msg = _("Do you want to save your changes to %s ?") \
                      % self.current_name
                if utils.yes_no_dialog(msg):
                    self.save_current_to_prefs()

        if conn_list is not None and name in conn_list:
            conn = conn_list[name]
            self.type_combo.set_active(self._dbtypes.index(conn["type"]))
	    self.params_box.refresh_view(conn_list[name])
        else: # this is for new connections
            self.type_combo.set_active(0)
            self.type_combo.emit("changed") # in case 0 was already active
        self.current_name = name
        self.old_params.clear()


    def on_changed_type_combo(self, combo, data=None):
        """
        the type changed so change the params_box
        """
        if self.params_box is not None:
	    self.old_params.update(self.params_box.get_parameters())
	    self.expander_box.remove(self.params_box)

        dbtype = combo.get_active_text()
        if dbtype == None:
            self.params_box = None
            return

        sensitive = dbtype in self._working_dbtypes
        self.widgets.connect_button.set_sensitive(sensitive)

        # get parameters box for the dbtype
        self.params_box = CMParamsBoxFactory.createParamsBox(dbtype, self)

        # if the type changed but is the same type of the connection
        # in the name entry then set the prefs
        conn_list = prefs[bauble.conn_list_pref]
        if conn_list is not None:
            name = self.name_combo.get_active_text()
            if name in conn_list:
                self.params_box.refresh_view(conn_list[name])
            elif len(self.old_params.keys()) != 0:
                self.params_box.refresh_view(self.old_params)

        self.expander_box.pack_start(self.params_box, False, False)
        self.dialog.show_all()


    def get_passwd(self, title=_("Enter your password"), before_main=False):
        """
        show a dialog with and entry and returh the value entered
        """
        # TODO: if self.dialog is None then ask from the command line
        # or just set dialog parent to None
        d = gtk.Dialog(title, self.dialog,
                       gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                       (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
    	d.set_gravity(gtk.gdk.GRAVITY_CENTER)
    	d.set_position(gtk.WIN_POS_CENTER)
        d.set_default_response(gtk.RESPONSE_ACCEPT)
        d.set_default_size(250,-1)
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
        template = "%(type)s://%(user)s@%(host)s/%(db)s"
        if params["passwd"] == True:
            subs["passwd"] = self.get_passwd()
            template = "%(type)s://%(user)s:%(passwd)s@%(host)s/%(db)s"
        return template % subs


    def _get_connection_uri(self):
        type = self.type_combo.get_active_text()

        # no db has been selected, this can happen on first run
        if self.params_box is None:
            return None

        params = copy.copy(self.params_box.get_parameters())
        params['type'] = type.lower()
        return self.parameters_to_uri(params)


    def _get_connection_name(self):
        return self.current_name


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


class CMParamsBox(gtk.Table):


    def __init__(self, conn_mgr, rows=4, columns=2):
        gtk.Table.__init__(self, rows, columns)
        self.set_row_spacings(10)
        self.create_gui()


    def create_gui(self):
        label_alignment = (0.0, 0.5)
        label = gtk.Label(_("Database: "))
        label.set_alignment(*label_alignment)
        self.attach(label, 0, 1, 0, 1)
        self.db_entry = gtk.Entry()
        self.attach(self.db_entry, 1, 2, 0, 1)

        label = gtk.Label(_("Host: "))
        label.set_alignment(*label_alignment)
        self.attach(label, 0, 1, 1, 2)
        self.host_entry = gtk.Entry()
        self.host_entry.set_text("localhost")
        self.attach(self.host_entry, 1, 2, 1, 2)

        label = gtk.Label(_("User: "))
        label.set_alignment(*label_alignment)
        self.attach(label, 0, 1, 2, 3)
        self.user_entry = gtk.Entry()
        self.attach(self.user_entry, 1, 2, 2, 3)

        label = gtk.Label(_("Password: "))
        label.set_alignment(*label_alignment)
        self.attach(label, 0, 1, 3, 4)
        self.passwd_check = gtk.CheckButton()
        self.attach(self.passwd_check, 1, 2, 3, 4)


    def get_prefs(self):
        """
        see get_prefs
        """
        return self.get_parameters()


    def get_parameters(self):
        """
        return only those preferences that are used to build the connection uri
        """
        d = {}
        d["db"] = self.db_entry.get_text()
        d["host"] = self.host_entry.get_text()
        d["user"] = self.user_entry.get_text()
        d["passwd"] = self.passwd_check.get_active()
        return d


    def refresh_view(self, prefs):
        """
        refresh the widget values from prefs
        """
    	try:
    	    self.db_entry.set_text(prefs["db"])
    	    self.host_entry.set_text(prefs["host"])
    	    self.user_entry.set_text(prefs["user"])
    	    self.passwd_check.set_active(prefs["passwd"])
    	except KeyError, e:
            debug('KeyError: %s' % e)
    	    #debug(traceback.format_exc())


class SQLiteParamsBox(CMParamsBox):


    def __init__(self, conn_mgr):
        self.conn_mgr = conn_mgr
        CMParamsBox.__init__(self, conn_mgr, rows=1, columns=2)


    def create_gui(self):
        self.default_check = gtk.CheckButton(_('Use default filename'))
        self.attach(self.default_check, 0, 2, 0, 1)
        self.default_check.connect('toggled', lambda button: \
                        self.file_box.set_sensitive(not button.get_active()))

        label_alignment = (0.0, 0.5)
        label = gtk.Label(_("Filename: "))
        label.set_alignment(*label_alignment)
        self.attach(label, 0, 1, 1, 2)

        self.file_box = gtk.HBox(False)
        self.file_entry = gtk.Entry()
        self.file_box.pack_start(self.file_entry)
        file_button = gtk.Button("Browse...")
        file_button.connect("clicked", self.on_activate_browse_button)
        self.file_box.pack_start(file_button)
        self.attach(self.file_box, 1, 2, 1, 2)


    def get_prefs(self):
        prefs = self.get_parameters()
        prefs['default'] = self.default_check.get_active()
        return prefs


    def get_parameters(self):
        d = {}
        invalid_chars = ', "\'():;'
        if self.default_check.get_active():
            name = self.conn_mgr._get_connection_name()
            from string import maketrans
            fixed = name.translate(maketrans(invalid_chars,
                                             '_'*len(invalid_chars)))
            d['file'] = os.path.join(paths.user_dir(), '%s.db' % fixed)
        else:
            d['file'] = self.file_entry.get_text()
        return d


    def refresh_view(self, prefs):
    	try:
            self.default_check.set_active(prefs['default'])
    	    self.file_entry.set_text(prefs['file'])
    	except KeyError, e:
            debug('KeyError: %s' % e)
    	    #debug(traceback.format_exc())


    def on_activate_browse_button(self, widget, data=None):
        d = gtk.FileChooserDialog(_("Choose a file..."), None,
                                  action=gtk.FILE_CHOOSER_ACTION_SAVE,
                                  buttons=(gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
                                  gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
        r = d.run()
        self.file_entry.set_text(d.get_filename())
        d.destroy()



class CMParamsBoxFactory:

    def __init__(self):
        pass

    def createParamsBox(db_type, conn_mgr):
        if db_type.lower() == "sqlite":
            return SQLiteParamsBox(conn_mgr)
        return CMParamsBox(conn_mgr)
    createParamsBox = staticmethod(createParamsBox)

