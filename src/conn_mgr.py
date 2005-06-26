#
# conn_mgr.py
#

import copy
import gtk
import sqlobject
from prefs import *
import utils

# TODO: make the border red for anything the user changes so
# they know if something has changed and needs to be saved, or maybe
# a red line should indicate that the value are valid, i.e. the name
# is in the wrong format, or better just don't the use leave the entry until
# whatever is there is an the correct format


class ConnectionManagerDialog(gtk.Dialog):
    def __init__(self, current_name=None, 
                 title="Connection Manager", parent=None,
                 flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                 buttons=(gtk.STOCK_OK, gtk.RESPONSE_OK,
                          gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)):
        gtk.Dialog.__init__(self, title, parent, flags, buttons)
        self.current_name = None
        self.create_gui()
        self.show_all()
        self.connect("response", self.on_response)
        
        # set the focus on the OK button
        self.set_focus(self.action_area.get_children()[1])
        self.set_active_connection_by_name(current_name)
        

    def _get_supported_dbtypes(self):
        """
        get for self.supported_types property
        """
        if self._supported_dbtypes != None:
            return self._supported_dbtypes
        self._supported_dbtypes = {}
        i = 0
        if sqlobject.mysql.isSupported():
            self._supported_dbtypes["MySQL"] = i
            i += 1 
        if sqlobject.postgres.isSupported():
            self._supported_dbtypes["Postgres"] = i
            i += 1 
        if sqlobject.sqlite.isSupported():
            self._supported_dbtypes["SQLite"] = i
            i += 1 
        if sqlobject.firebird.isSupported():
            self._supported_dbtypes["Firebird"] = i
            i += 1 
        if sqlobject.maxdb.isSupported():
            self._supported_dbtypes["MaxDB"] = i
            i += 1 
        if sqlobject.sybase.isSupported(None): # i think this arg is a type
            self._supported_dbtypes["Sybase"] = i
            i += 1 
        return self._supported_dbtypes
        
     # this is a dict with the keys the names of the database types and
     # the value are the index in the type_combo
    supported_dbtypes = property(_get_supported_dbtypes)
    _supported_dbtypes = None
    

    def create_gui(self):
        self.vbox.set_spacing(10)
        self.params_box = None

        if self.supported_dbtypes is None:
            raise Exception("No Python database connectors installed.\n"\
                            "Please consult the documentation for the "\
                            "prerequesites for installing Bauble.")
        
        # an information label ala eclipse
        hbox = gtk.HBox(False)
        hbox.set_spacing(5)
        hbox.set_border_width(10)
        self.info_image = gtk.image_new_from_stock(gtk.STOCK_DIALOG_INFO,
                                                   gtk.ICON_SIZE_BUTTON)#gtk.ICON_SIZE_SMALL_TOOLBAR)
        hbox.pack_start(self.info_image, False, False)
        self.info_label = gtk.Label()
        self.set_info_label()
        self.info_label.set_padding(10, 10)
        self.info_label.set_alignment(0.0, .5)
        hbox.pack_start(self.info_label)
        
        event_box = gtk.EventBox()
        event_box.add(hbox)
        event_box.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("white"))
        self.vbox.pack_start(event_box, False, False)
        
        hbox = gtk.HBox(False)
        hbox.set_spacing(5)
        name_label = gtk.Label("Connection Name")
        hbox.pack_start(name_label)
        name_label.set_alignment(0.0, 0.5)
        
        self.name_combo = gtk.combo_box_new_text()
        self.name_combo.connect("changed", self.on_changed_name_combo)
        hbox.pack_start(self.name_combo)
        
        button = gtk.Button("New")
        hbox.pack_start(button, False, False)
        button.connect("clicked", self.on_clicked_new_button)
        
        button = gtk.Button("Remove")
        hbox.pack_start(button, False, False)
        button.connect("clicked", self.on_clicked_remove_button)
        
        self.vbox.pack_start(hbox, False, False)
        
        sep = gtk.HSeparator()
        self.vbox.pack_start(sep, False, False)
        
        # the type combo
        type_label = gtk.Label("Type")
        type_label.set_alignment(0.0, .5)
        self.type_combo = gtk.combo_box_new_text()
        
        # test for different supported database types, these have never been
        # test but if someone tries one and it
        # doesn't work then maybe someone they will let us know
        for type, index in self.supported_dbtypes.iteritems():
            self.type_combo.insert_text(index, type)
        
        self.type_combo.connect("changed", self.on_changed_type_combo)
        
        hbox = gtk.HBox(False)
        hbox.pack_start(type_label)
        hbox.pack_start(self.type_combo)
        self.vbox.pack_start(hbox, False, False)
    

    def set_active_connection_by_name(self, name):
        if not hasattr(self, "name_combo"):
            return
        i = 0
        active = 0
        conn_list = Preferences[conn_list_pref]
        if conn_list is None: return
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
        conn_list = Preferences[conn_list_pref]
        if conn_list.has_key(name):
            del conn_list[name]
            
        model = self.name_combo.get_model()
        for i in range(0, len(model)-1):
            row = model[i][0]
            if row == name:
                self.name_combo.remove_text(i)
                break
            
        #self.current_name = None
        self.name_combo.set_active(0)
        

    def on_clicked_remove_button(self, button, data=None):
        # TODO: do you want to delete all data associated with this connection?
        msg = "Are you sure you want to remove " + self.current_name + " ?"
        if not utils.yes_no_dialog(msg):
            return
        self.current_name = None
        self.remove_connection(self.name_combo.get_active_text())
        self.name_combo.set_active(0)
        
            
    def on_clicked_new_button(self, button, data=None):
        d = gtk.Dialog("Enter a connection name", None,
                       gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                       (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        d.set_default_response(gtk.RESPONSE_ACCEPT)
        d.set_default_size(250,-1)
        entry = gtk.Entry()
        entry.connect("activate", lambda entry: d.response(gtk.RESPONSE_ACCEPT))
        d.vbox.pack_start(entry)
        d.show_all()
        d.run()
        name = entry.get_text()
        d.destroy()
        self.name_combo.prepend_text(name)
        self.type_combo.set_active(0)
        self.name_combo.set_active(0)
        
        
            
    def on_response(self, dialog, response, data=None):
        if response == gtk.RESPONSE_OK:
            self.save_current_to_prefs()
        elif response == gtk.RESPONSE_CANCEL or response == gtk.RESPONSE_DELETE_EVENT:
            if not self.compare_params_to_prefs(self.current_name):
                msg="Do you want to save your changes?"
                if utils.yes_no_dialog(msg):
                    self.save_current_to_prefs()              
        return response


    def set_info_label(self, msg="Choose a connection"):
        self.info_label.set_text(msg)
        
        
    def save_current_to_prefs(self):
        if not Preferences.has_key(conn_list_pref):
            Preferences[conn_list_pref] = {}
        params = copy.copy(self.params_box.get_parameters())
        params["type"] = self.type_combo.get_active_text()
        conn_list = Preferences[conn_list_pref]
        conn_list[self.current_name] = params
        Preferences.save()
        

    def compare_params_to_prefs(self, name):
        """
        name is the name of the connection in the prefs
        """
        conn_list = Preferences[conn_list_pref]
        if conn_list is None or not conn_list.has_key(name):
            return False
        #if not conn_list.has_key(name): return False
        stored_params = conn_list[name]
        params = copy.copy(self.params_box.get_parameters())
        params["type"] = self.type_combo.get_active_text()
        print params
        print stored_params
        return params == stored_params

        
    def on_changed_name_combo(self, combo, data=None):
        """
        the name changed so fill in everything else
        """
        name = combo.get_active_text()
        conn_list = Preferences[conn_list_pref]
        #if self.params_box is not None and self.current_name is not None:
        if self.current_name is not None:
            if self.current_name not in conn_list: # do you want to save your changes,
                msg = "Do you want the save %s?" % self.current_name
                if utils.yes_no_dialog(msg):
                    self.save_current_to_prefs()
                else: 
                    self.remove_connection(self.current_name)
                    self.current_name == None
            elif not self.compare_params_to_prefs(self.current_name):
                msg = "Do you want to save your changes to %s ?" % self.current_name                
                if utils.yes_no_dialog(msg):
                    self.save_current_to_prefs()        
        if conn_list is not None and conn_list.has_key(name):
            conn = conn_list[name]
            self.type_combo.set_active(self.supported_dbtypes[conn["type"]])
            self.params_box.set_parameters(conn_list[name])
        else: # this is for new connections
            self.type_combo.set_active(0)
            self.type_combo.emit("changed") # in case 0 was already active
        self.current_name = name

        
    def on_changed_type_combo(self, combo, data=None):
        """
        the type changed so change the params_box
        """
        dbtype = combo.get_active_text()
        if self.params_box is not None:
            self.vbox.remove(self.params_box)
        # get the selected type
        self.params_box = CMParamsBoxFactory.createParamsBox(dbtype)
        self.vbox.pack_start(self.params_box, False, False)
        self.show_all()

    
    def get_passwd(self, title="Enter your password", before_main=False):
        d = gtk.Dialog(title, None,
                       gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                       (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        d.set_default_response(gtk.RESPONSE_ACCEPT)
        d.set_default_size(250,-1)
        entry = gtk.Entry()
        entry.set_visibility(False)
        entry.connect("activate", lambda entry: d.response(gtk.RESPONSE_ACCEPT))
        d.vbox.pack_start(entry)
        d.show_all()
        d.run()
        passwd = entry.get_text()
        d.destroy()
        return passwd
        
 
    def get_connection_uri(self):
        type = self.type_combo.get_active_text()
        params = copy.copy(self.params_box.get_parameters())
        if type.lower() == "sqlite":
            #uri = "sqlite:///" + params["file"]
            filename = params["file"].replace(":", "|")
            filename = filename.replace("\\", "/")
            uri = "sqlite:///" + filename
            return uri
        
        params["type"] = type.lower()
        template = "%(type)s://%(user)s@%(host)s/%(db)s"
        if params["passwd"] == True:    
            params["passwd"] = self.get_passwd()
            template = "%(type)s://%(user)s:%(passwd)s@%(host)s/%(db)s"
            
        uri = template % params
        return uri
            

    def get_connection_name(self):
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
            return False, "Please choose a name for this connection"
        params = self.params_box
        if params["user"] == "":
            return False, "Please choose a user name for this connection"
            

class CMParamsBox(gtk.Table):


    def __init__(self, rows=4, columns=2):
        gtk.Table.__init__(self, rows, columns)
        self.set_row_spacings(10)
        self.create_gui()
        

    def create_gui(self):
        label_alignment = (0.0, 0.5)
        label = gtk.Label("Database: ")
        label.set_alignment(*label_alignment)
        self.attach(label, 0, 1, 0, 1)
        self.db_entry = gtk.Entry()
        self.attach(self.db_entry, 1, 2, 0, 1)

        label = gtk.Label("Host: ")
        label.set_alignment(*label_alignment)
        self.attach(label, 0, 1, 1, 2)
        self.host_entry = gtk.Entry()
        self.host_entry.set_text("localhost")
        self.attach(self.host_entry, 1, 2, 1, 2)

        label = gtk.Label("User: ")
        label.set_alignment(*label_alignment)
        self.attach(label, 0, 1, 2, 3)
        self.user_entry = gtk.Entry()
        self.attach(self.user_entry, 1, 2, 2, 3)
            
        label = gtk.Label("Password: ")
        label.set_alignment(*label_alignment)
        self.attach(label, 0, 1, 3, 4)
        self.passwd_check = gtk.CheckButton()
        self.attach(self.passwd_check, 1, 2, 3, 4)
    
    
    def get_parameters(self):
        d = {}
        d["db"] = self.db_entry.get_text()
        d["host"] = self.host_entry.get_text()
        d["user"] = self.user_entry.get_text()
        d["passwd"] = self.passwd_check.get_active()
        return d

    def set_parameters(self, params):
        self.db_entry.set_text(params["db"])
        self.host_entry.set_text(params["host"])
        self.user_entry.set_text(params["user"])
        self.passwd_check.set_active(params["passwd"])


class SQLiteParamsBox(CMParamsBox):


    def __init__(self, rows=1, columns=2):
        CMParamsBox.__init__(self, rows, columns)
    

    def create_gui(self):
        label_alignment = (0.0, 0.5)
        label = gtk.Label("Filename")
        label.set_alignment(*label_alignment)
        self.attach(label, 0, 1, 0, 1)
        hbox = gtk.HBox(False)
        self.file_entry = gtk.Entry()
        hbox.pack_start(self.file_entry)
        file_button = gtk.Button("Browse...")
        file_button.connect("clicked", self.on_activate_browse_button)
        hbox.pack_start(file_button)
        self.attach(hbox, 1, 2, 0, 1)        
    
    
    def get_parameters(self):
        d = {}
        d["file"] = self.file_entry.get_text()
        return d
    

    def set_parameters(self, params):
        self.file_entry.set_text(params["file"])


    def on_activate_browse_button(self, widget, data=None):
        d = gtk.FileChooserDialog("Choose a file...", None,
                                  action=gtk.FILE_CHOOSER_ACTION_SAVE,
                                  buttons=(gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
                                  gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
        r = d.run()
        self.file_entry.set_text(d.get_filename())
        d.destroy()
        

#
# is this factory really necessary??
#
class CMParamsBoxFactory:
    
    def __init__(self):
        pass
        
    def createParamsBox(db_type):
        if db_type.lower() == "sqlite":
            return SQLiteParamsBox()
        return CMParamsBox()
    createParamsBox = staticmethod(createParamsBox)