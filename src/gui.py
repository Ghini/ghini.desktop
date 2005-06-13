#
# gui.py
#
# Description: TODO: finish the descriptions and check the other files have
#

import os
import time
import thread

import pygtk
pygtk.require("2.0")
import gtk
import gobject
import sqlobject
from views import views
from editors import editors
import tools.export
from prefs import *

#
# GUI
#
class GUI:
    
    current_view_pref = "gui.current_view"
    
    def __init__(self, bauble):
        print views.View
        self.bauble = bauble
        self.create_gui()

        # load the last view open from the prefs
        v = Preferences[self.current_view_pref]
        if v is not None:
            self.set_current_view(eval(v))
            
    
    def create_gui(self):            
        # create main window
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_default_size(800, 600)
        self.window.connect("destroy", self.on_quit)        
        self.window.set_title("Bauble")
    
        # top level vbox for menu, content, status bar
        main_vbox = gtk.VBox(False)
        self.window.add(main_vbox)

        menubar = self.create_main_menu()
        main_vbox.pack_start(menubar, False, True, 0)
        
        toolbar = self.create_toolbar()
        main_vbox.pack_start(toolbar, False, True, 0)
                
        self.content_hbox = gtk.HBox(False) # empty for now        
        self.content_frame = gtk.Frame()
        self.content_hbox.pack_start(self.content_frame)
        main_vbox.pack_start(self.content_hbox)

        # last part of main_vbox is status bar
        status_box = gtk.HBox(False)        
        self.statusbar = gtk.Statusbar()
        self.statusbar.set_has_resize_grip(False)     
        status_box.pack_start(self.statusbar, expand=True, fill=True)

        # create the progress bar and add it to the status pane
        self.progressbar = gtk.ProgressBar()
        self.progressbar.set_size_request(100, -1)
        status_box.pack_start(self.progressbar, expand=False, fill=False)
        
        #main_vbox.pack_start(self.statusbar, expand=False, fill=False)
        main_vbox.pack_start(status_box, expand=False, fill=False)
                
        # show everything
        self.window.show_all()


    def pb_pulse_worker(self):
        self.pb_lock.acquire() # ********** critical
        self.progressbar.set_pulse_step(.1)
        self.progressbar.set_fraction(1.0)
        while not self.stop_pulse:
            gtk.threads_enter()
            self.progressbar.pulse()
            gtk.threads_leave()
            time.sleep(.1)
        self.progressbar.set_fraction(1.0)
        self.pb_lock.release()

  
    def pulse_progressbar(self):
        """
        create a seperate thread the run the progress bar
        """
        if not hasattr(self, "pb_lock"):
            self.pb_lock = thread.allocate_lock()
        self.stop_pulse = False
        id = thread.start_new_thread(self.pb_pulse_worker, ())
        

    def stop_progressbar(self):
        """
        stop a progress bar
        """
        self.stop_pulse = True

    
    def create_toolbar(self):
        toolbar = gtk.Toolbar()

        # add all views modules
        button = gtk.MenuToolButton(gtk.STOCK_FIND_AND_REPLACE)
        button.set_label("View")
        menu = gtk.Menu()
        for name, view in views.iteritems():
            item = gtk.MenuItem(name)
            item.connect("activate", self.on_activate_view, view)
            menu.append(item)
        
        menu.show_all()
        button.set_menu(menu)
        toolbar.insert(button, 0)
        
        # add all editors modules
        button = gtk.MenuToolButton(gtk.STOCK_ADD)
        button.add_accelerator("show_menu", self.accel_group, ord("a"), 
                               gtk.gdk.CONTROL_MASK, gobject.SIGNAL_ACTION)
        menu = gtk.Menu()
        for name, editor in editors.iteritems():
            item = gtk.MenuItem(name)
            item.connect("activate", self.on_activate_editor, editor)
            menu.append(item)
        menu.show_all()
        button.set_menu(menu)
        toolbar.insert(button, 1)
        
        return toolbar
    
    
    def set_current_view(self, view_class):
        """
        set the current view, view is a class and will be instantiated
        here, that way the same view won't be created again if the current
        view os of the same type
        """
        current_view = self.content_frame.get_child()
        if type(current_view) == view_class: return
        elif current_view != None:
            self.content_frame.remove(current_view)
            current_view.destroy()
            current_view = None
        new_view = view_class(self.bauble)    
        self.content_frame.set_label(view_class.__name__)
        self.content_frame.add(new_view)
        
        
    def on_activate_view(self, menuitem, view):
        """
        set the selected view as current
        """
        self.set_current_view(view)


    def on_activate_editor(self, menuitem, editor):
        """
        show the dialog of the selected editor
        """
        e = editor()
        e.show()
        
        
    def create_main_menu(self):
        """
        get the main menu from the UIManager XML description, add its actions
        and return the menubar
        """
        ui_manager = gtk.UIManager()
        
        # add accel group
        self.accel_group = ui_manager.get_accel_group()
        self.window.add_accel_group(self.accel_group)

        # TODO: get rid of new, open, and just have a connection
        # menu item
        
        # create and addaction group for menu actions
        menu_actions = gtk.ActionGroup("MenuActions")
        menu_actions.add_actions([("file", None, "_File"), 
                                  ("file_new", gtk.STOCK_NEW, "_New", None, 
                                   None, self.on_file_menu_new), 
                                  ("file_open", gtk.STOCK_OPEN, "_Open", None, 
                                   None, self.on_file_menu_open), 
                                  ("file_import", None, "_Import", None, 
                                   None, self.on_file_menu_import), 
                                  ("file_quit", gtk.STOCK_QUIT, "_Quit", None, 
                                   None, self.on_quit), 
                                  ("edit", None, "_Edit"), 
                                  ("edit_cut", gtk.STOCK_CUT, "_Cut", None, 
                                   None, self.on_edit_menu_cut), 
                                  ("edit_copy", gtk.STOCK_COPY, "_Copy", None, 
                                   None, self.on_edit_menu_copy), 
                                  ("edit_paste", gtk.STOCK_PASTE, "_Paste", 
                                   None, None, self.on_edit_menu_paste), 
                                  ("edit_preferences", None , "_Preferences", 
                                   "<control>P", None, self.on_edit_menu_prefs), 
                                  ("tools", None, "_Tools"),
                                   ("export", None, "_Export", None, 
                                   None, self.on_tools_menu_export), 
                                  ])
        ui_manager.insert_action_group(menu_actions, 0)

        # load ui
        ui_manager.add_ui_from_file(self.bauble.path + os.sep + "bauble.ui")

        # get menu bar from ui manager
        mb = ui_manager.get_widget("/MenuBar")
        return mb
    

    def on_tools_menu_export(self, widget, data=None):
        d = tools.export.ExportDialog()
        d.run()
        d.destroy()

    def on_edit_menu_prefs(self, widget, data=None):
        print "on_edit_menu_prefs"
        p = PreferencesMgr()
        p.run()
        p.destroy()

        
    def on_edit_menu_cut(self, widget, data=None):
        pass

    
    def on_edit_menu_copy(self, widget, data=None):
        pass

    
    def on_edit_menu_paste(self, widget, data=None):
        pass


    def on_file_menu_import(self, widget, data=None):
        """
        choose a file to import, the filename should be table_name.txt
        to import to table table_name
        """
        
        def on_selection_changed(filechooser, data=None):
            """
            only make the ok button sensitive if the selection is a file
            """
            f = filechooser.get_preview_filename()
            if f is None: return
            ok = filechooser.action_area.get_children()[1]
            ok.set_sensitive(os.path.isfile(f))
            
        fc = gtk.FileChooserDialog("Choose file to import...",
                                  self.window,
                                  gtk.FILE_CHOOSER_ACTION_OPEN,
                                  (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
                                   gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT))
        fc.connect("selection-changed", on_selection_changed)
        fc.set_select_multiple(False)
        r = fc.run()
        filename = fc.get_filename()
        fc.destroy()
        if r == gtk.RESPONSE_CANCEL: 
            return
            
        # TODO: should probably check first that there is a table with 
        # the same name as the file in the database
            
        # read the first row of the file as the column names
        head, tail = os.path.split(filename)
        table, ext = os.path.splitext(tail)
        columns = file(filename).readline().strip()
        
        sql = "LOAD DATA LOCAL INFILE '%(file)s' " + \
            "INTO TABLE %(table)s " + \
            "FIELDS " + \
            "TERMINATED BY ',' "  + \
            "OPTIONALLY ENCLOSED BY '\"' "  + \
            'IGNORE 1 LINES '  + \
            '(%(columns)s);'

        print sql % {"file": filename, "table": table, "columns": columns}
        
        self.bauble.conn.query(sql % {"file": filename, 
                                      "table": table, 
                                      "columns": columns})
                                      
        # TODO: popup a message dialog that says "Success." or something
        # to indicate everything was imported without problems
        
    def on_file_menu_new(self, widget, date=None):
        cm = ConnectionManagerGUI()
        print "calling get params"
        params = cm.get_connection_parameters()
        print "returned"
        if params is not None:
            print "create"
            self.bauble.create_database(params)
            
        
    def on_file_menu_open(self, widget, data=None):        
        """
        open the selected database
        """
        # TODO: how do we check if the user needs a password, do we wait until
        # the connection fails and then ask for the password
        cm = ConnectionManagerGUI()
        params = cm.get_connection_parameters()
        if params is not None:
            self.bauble.open_database(params)
            

    def save_state(self):
        """
        this is usually called from bauble.py when it shuts down
        """
        current_view = self.content_frame.get_child()
        if current_view is not None:
            Preferences[self.current_view_pref] = "views." + current_view.__name__
        Preferences.save()
        
    def on_quit(self, widget, data=None):
        self.bauble.quit()
        
        

