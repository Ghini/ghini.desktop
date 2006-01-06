#
# gui.py
#
# Description: TODO: finish the descriptions and check the other files have
#

import os, time, re
import gtk, gobject
import sqlobject
import bauble.utils as utils
import bauble.paths as paths
from bauble.plugins import plugins, tools, views, editors
from bauble.prefs import prefs, PreferencesMgr
import bauble.plugins.searchview.search
from bauble.utils.log import log, debug


# TODO: use this bit of code to set the window icon, also see the docs
# for gtk.Window.set_icon and gtk.Window.set_icon_list for providing the
# different icon sizes
#  w = gtk.Window()
#  icon = w.render_icon(gtk.STOCK_DIALOG_INFO, gtk.ICON_SIZE_BUTTON)
#  w.set_icon(icon)
#  w.show()
#  gtk.main()

#
# GUI
#
class GUI:
    
    current_view_pref = "gui.current_view"
    
    def __init__(self, bauble_app):
        self.bauble = bauble_app
        self.create_gui()
        
#        # load the last view open from the prefs
#        v = prefs[self.current_view_pref]
#        if v is None: # default view is the search view            
#            v = str(views["SearchView"])
#    
#        view_set = False
#        for name, view in views.iteritems():
#            if v == str(view):
#                self.set_current_view(view)
#                view_set = True
#                # TODO: if this view can't be shown then default to SearchView
#                
#        if not view_set:
#            self.set_current_view(views["SearchView"])
            
            
    def create_gui(self):            
        # create main window
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_default_size(800, 600)
        self.window.connect("destroy", self.on_quit)        
        self.window.set_title("Bauble %s" % bauble.version_str)
    
        # top level vbox for menu, content, status bar
        main_vbox = gtk.VBox()
                
        self.create_main_menu() # creates self.menubar
        main_vbox.pack_start(self.menubar, False, True)            
        
        # holds the  view
        self.content_hbox = gtk.HBox() # empty for now
        main_vbox.pack_start(self.content_hbox, True, True)

        # last part of main_vbox is status bar
        status_box = gtk.HBox()        
        self.statusbar = gtk.Statusbar()
        self.statusbar.set_has_resize_grip(False)     
        status_box.pack_start(self.statusbar, expand=True, fill=True)

        # create the progress bar and add it to the status pane
        self.progressbar = gtk.ProgressBar()
        self.progressbar.set_size_request(100, -1)
        self.progressbar.set_fraction(1.0)
        status_box.pack_start(self.progressbar, expand=False, fill=False)
        
        #main_vbox.pack_start(self.statusbar, expand=False, fill=False)
        main_vbox.pack_start(status_box, expand=False, fill=False)
                
        # show everything
        self.window.add(main_vbox)
        self.window.show_all()


#     def pb_pulse_worker(self, from_thread):
#         self.pb_lock.acquire() # ********** critical
#         while not self.stop_pulse:
#             #print "pulse"
#             if not from_thread: 
#                 gtk.gdk.threads_enter()
#             self.progressbar.pulse()
#             if not from_thread: 
#                 gtk.gdk.threads_leave()
#             time.sleep(.1)
# #        self.progressbar.set_fraction(1.0
#         if not from_thread: gtk.gdk.threads_enter()
#         self.progressbar.set_fraction(1.0)
#         if not from_thread: gtk.gdk.threads_leave()
#         self.pb_lock.release()
        

    def pulse_progressbar(self, from_thread=False):
        """
        create a seperate thread the run the progress bar
        """	
	raise NotImplemented()
        # TODO: this needs to be rethought, we can't use threads        
#         if not hasattr(self, "pb_lock"):
#             self.pb_lock = thread.allocate_lock()
#         self.stop_pulse = False
#         self.progressbar.set_pulse_step(.1)
#         self.progressbar.set_fraction(1.0)
#         id = thread.start_new_thread(self.pb_pulse_worker, (from_thread,))
        

    def stop_progressbar(self):
        """
        stop a progress bar
        """
        self.stop_pulse = True
        #self.pb_lock.acquire()
        #self.progressbar.set_fraction(1.0)
        #self.pb_lock.release()    
    
    
    def set_current_view(self, view_class):
        """
        set the current view, view is a class and will be instantiated
        here, that way the same view won't be created again if the current
        view os of the same type
        """
        current_view = self.get_current_view()
        if type(current_view) == view_class: 
            return
        elif current_view != None:
            self.content_hbox.remove(current_view)
            current_view.destroy()
            current_view = None
        new_view = view_class()
        self.content_hbox.pack_start(new_view, True, True)
        
        
    def get_current_view(self):
        '''
        right now we on have one view, the SearchView, so this 
        method should always return a SearchView instance
        '''
        kids = self.content_hbox.get_children()
        if len(kids) == 0:
            return None
        else: return kids[0]        
        
        
    def on_activate_view(self, menuitem, view):
        """
        set the selected view as current
        """
        self.set_current_view(view)


    def on_activate_editor(self, menuitem, editor):
        """
        show the dialog of the selected editor
        """
        debug('on_activate_editor')
        e = editor()
        committed = e.start()
#        if response == gtk.RESPONSE_OK or response == gtk.RESPONSE_ACCEPT:
#            debug('committing')
#            e.commit_changes()
#        else:
#            debug('rolling back')
#            e.transaction.rollback()
        
        
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
                                  ])
        ui_manager.insert_action_group(menu_actions, 0)

        # load ui
        ui_filename = paths.lib_dir() + os.sep + "bauble.ui"
        ui_manager.add_ui_from_file(ui_filename)

        # get menu bar from ui manager
        self.menubar = ui_manager.get_widget("/MenuBar")
        
        # TODO: why does't using the tools menu from the ui manager work
        self.add_menu("Insert", self.build_insert_menu())
        self.add_menu("Tools", self.build_tools_menu())
        
        return self.menubar
    
    def add_menu(self, name, menu, index=-1):
        menu_item = gtk.MenuItem(name)
        menu_item.set_submenu(menu)
        # we'll just append them for now but really we should
        # get the number of children in the menubar and insert at len-1
        # to account for the Help menu
        self.menubar.append(menu_item)
        self.menubar.show_all()
        return menu_item

        
    def build_insert_menu(self):
        menu = gtk.Menu()
        compare_labels = lambda x, y: cmp(x.label, y.label)
        for editor in sorted(editors.values(), cmp=compare_labels):
            if editor.standalone:
                item = gtk.MenuItem(editor.label)
                item.connect("activate", self.on_insert_menu_item_activate, editor)
                menu.append(item)
        return menu
    
    
    def build_tools_menu(self):        
        menu = gtk.Menu()
        submenus = {}
        for tool in tools.values():

            item = gtk.MenuItem(tool.label)
            item.connect("activate", self.on_tools_menu_item_activate, tool)
            if tool.category is None: # not category
                menu.append(item)
            else:
                if tool.category not in submenus: # create new category
                    category_menu_item = gtk.MenuItem(tool.category)                    
                    category_menu = gtk.Menu()
                    category_menu_item.set_submenu(category_menu)
                    menu.prepend(category_menu_item)
                    submenus[tool.category] = category_menu
                submenus[tool.category].append(item)
            if not tool.enabled:
                item.set_sensitive(False)
        return menu
        
        
    def on_tools_menu_item_activate(self, widget, tool):
        tool.start()
        
        
    def on_insert_menu_item_activate(self, widget, editor):
        e = editor()
        committed = e.start()
#        response = e.start()
#        if response == gtk.RESPONSE_OK or response == gtk.RESPONSE_ACCEPT:
#            e.commit_changes()
#        else:
#            e.transaction.rollback()
#        e.destroy()
            
        
    def on_edit_menu_prefs(self, widget, data=None):
        p = PreferencesMgr()
        p.run()
        p.destroy()

        
    def on_edit_menu_cut(self, widget, data=None):
        pass

    
    def on_edit_menu_copy(self, widget, data=None):
        pass

    
    def on_edit_menu_paste(self, widget, data=None):
        pass

        
    def on_file_menu_new(self, widget, date=None):        
        msg = "If a database already exists at this connection then creating "\
              "a new database could destroy your data.\n\n<i>Are you sure "\
              "this is what you want to do?</i>"
        if utils.yes_no_dialog(msg):
            self.bauble.create_database()
        # TODO: reset the view
            
        
    def on_file_menu_open(self, widget, data=None):        
        """
        open the connection manager
        """
        from conn_mgr import ConnectionManager
        cm = ConnectionManager()
        name, uri = cm.start()
        if name is None:
            return
        self.bauble.open_database(uri, name, True)
        
        # TODO reset the view
            

    def save_state(self):
        """
        this is usually called from bauble.py when it shuts down
        """        
        current_view = self.get_current_view()
        if current_view is not None:
            prefs[self.current_view_pref] = str(current_view.__class__)
            # get label of view
            #for label, view in views.iteritems(): 
            #    if view == current_view.__class__:
            #        Preferences[self.current_view_pref] = views.modules[view]
        prefs.save()
        
        
    def on_quit(self, widget, data=None):
        self.bauble.quit()
        
        

