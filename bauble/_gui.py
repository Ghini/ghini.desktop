#
# gui.py
#

import os, sys, time, re
import gtk, gobject
import bauble
import bauble.utils as utils
import bauble.paths as paths
from bauble.plugins import plugins, tools, views, editors
from bauble.prefs import prefs, PreferencesMgr
import bauble.plugins.searchview.search
from bauble.utils.log import log, debug
from bauble.i18n import *

# TODO: ProgressBar idea stub
# - i would like to have a progress bar on the status bar or just popup above 
# the status bar when there is a task
# - with an integrated cancel button so that there is one place for any task
# to update the progress instead of each task creating their own progress 
# dialog
# - would probably make sense for it to drop down from below the search entry 
# when there is a task running and disappear when there isn't

#class ProgressTask:
#    '''
#    a task for the statusbarprogress
#    '''
#    name = None
#    fraction = 0.0
#    total_stepts = 0.0
#    
#    def __init__(self, progress_bar):
#        self.pb = progress_bar
#        
#    def update(self, nsteps):
#        fraction = float(nsteps)/total_steps
#        self.pb.set_fraction(fraction)
#        
#
#class FancyProgressBar(gtk.HBox):
#    
#    def __init__(self):
#        gtk.HBox.__init__(self)
#        self.label = gtk.Label()
#        self.progress_bar = gtk.ProgressBar()
#        #self.cancel_button = gtk.Button(stock=gtk.STOCK_CANCEL)
#        self.cancel_button = gtk.Button('Cancel')
#        self.pack_start(self.label, expand=False, fill=False)
#        self.pack_start(self.progress_bar, expand=False, fill=False)
#        self.pack_start(self.cancel_button, expand=False, fill=False)
#        
#        # create new task
#        # set progress state by task
#        
#    # create cancel_button
#    def push_task(self, progress_task):
#        pass
#    
#    def pop_task(self, progress_task):
#        pass
#    
#    def set_text(self, text):
#        '''
#        set the text on the label of the progress bar
#        '''
#        self.label.set_text(text)
#        
#    def cancel_connect(self, callback, task):
#        '''
#        connect to the clicked event on the cancel button
#        
#        callback -- the method to call
#        task -- the ProgressTask to cancel
#        '''
#        self.cancel_button.connect('clicked', callback, task)



class CommandHandler:
    
    def __init__(self):
        pass

class GUI:
        
    def __init__(self):
        glade_path = os.path.join(paths.lib_dir(), 'bauble.glade')
        self.glade = gtk.glade.XML(glade_path)
        self.widgets = utils.GladeWidgets(self.glade)        
        self.window = self.widgets.main_window
        
        self.window.set_default_size(800, 600)
        self.window.connect("destroy", self.on_quit)
        self.window.set_title(self.title)
        filename = os.path.join(paths.lib_dir(), "images", "icon.svg")
        pixbuf = gtk.gdk.pixbuf_new_from_file(filename)
        self.window.set_icon(pixbuf)
        
        menubar = self.create_main_menu()
        self.widgets.menu_box.pack_start(menubar)
                    
                    
#        label = gtk.Label()
#        label.set_markup('<big>Welcome to Bauble.</big>')
#        self.widgets.view_box.pack_start(label)
        image = gtk.Image()
        image.set_from_file(os.path.join(paths.lib_dir(), 'images', 
                                         'bauble_logo.png'))
        self.widgets.view_box.pack_start(image)
        self.widgets.view_box.show_all()

        
    def __get_title(self):
        return '%s %s - %s' % ('Bauble', bauble.version_str, 
                               bauble.app.conn_name)
    title = property(__get_title)


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
        self.add_menu("_Insert", self.build_insert_menu())
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
                try:
                    item = gtk.MenuItem(editor.mnemonic_label)
                except AttributeError:
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
        view = self.get_current_view()
        expanded_rows = view.get_expanded_rows()
        e = editor()
        committed = e.start()
        if committed is not None:
            view.results_view.collapse_all()
            view.expand_to_all_refs(expanded_rows)                        
            
            
        
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
            bauble.app.create_database()
        
                
    def on_file_menu_open(self, widget, data=None):        
        """
        open the connection manager
        """
        from conn_mgr import ConnectionManager
        default_conn = prefs[prefs.conn_default_pref]
        cm = ConnectionManager(default_conn)
        name, uri = cm.start()
        if name is None:
            return

        if bauble.app.open_database(uri, name) is not None:
            self.window.set_title(self.title)
            

    def save_state(self):
        """
        this is usually called from bauble.py when it shuts down
        """        
        prefs.save()
        
        
    def on_quit(self, widget, data=None):
        bauble.app.quit()


#class GUI_old:
#    
#    current_view_pref = "gui.current_view"
#    
#    def __init__(self):
#        self.create_gui()
#        
#            
#    def __get_title(self):
#        return '%s %s - %s' % ('Bauble', bauble.version_str, 
#                               bauble.app.conn_name)
#    title = property(__get_title)
#
#
#    def create_gui(self):
#        # create main window
#        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
#        self.window.set_default_size(800, 600)
#        self.window.connect("destroy", self.on_quit)
#        self.window.set_title(self.title)
##        if sys.platform == 'win32':
##            # TODO: need and svg pixbuf loaded for windows
##            filename = os.path.join(paths.lib_dir(), "images", "icon24.png")
##            pixbuf = gtk.gdk.pixbuf_new_from_file(filename)
##            self.window.set_icon(pixbuf)
##        else:
#            # TODO: need a svg pixbuf loaded for windows
#        filename = os.path.join(paths.lib_dir(), "images", "icon.svg")
#        pixbuf = gtk.gdk.pixbuf_new_from_file(filename)
#        self.window.set_icon(pixbuf)
#    
#        # top level vbox for menu, content, status bar
#        main_vbox = gtk.VBox()
#                
#        self.create_main_menu() # creates self.menubar
#        main_vbox.pack_start(self.menubar, False, True)            
#        
#        # holds the  view
#        self.content_hbox = gtk.HBox() # empty for now
#        main_vbox.pack_start(self.content_hbox, True, True)
#
#        # last part of main_vbox is status bar
#        status_box = gtk.HBox()        
#        self.statusbar = gtk.Statusbar()
#        self.statusbar.set_has_resize_grip(False)     
#        status_box.pack_start(self.statusbar, expand=True, fill=True)
#
#        # create the progress bar and add it to the status pane
#        #self.progressbar = FancyProgressBar()
#        #status_box.pack_start(self.progressbar, expand=False, fill=False)
#        #self.progressbar = gtk.ProgressBar()
#        #self.progressbar.set_size_request(100, -1)
#        #self.progressbar.set_fraction(1.0)
#        #status_box.pack_start(self.progressbar, expand=False, fill=False)
#        
#        #main_vbox.pack_start(self.statusbar, expand=False, fill=False)
#        main_vbox.pack_start(status_box, expand=False, fill=False)
#                
#        # show everything
#        self.window.add(main_vbox)
#        self.window.show_all()
#
#
##     def pb_pulse_worker(self, from_thread):
##         self.pb_lock.acquire() # ********** critical
##         while not self.stop_pulse:
##             #print "pulse"
##             if not from_thread: 
##                 gtk.gdk.threads_enter()
##             self.progressbar.pulse()
##             if not from_thread: 
##                 gtk.gdk.threads_leave()
##             time.sleep(.1)
## #        self.progressbar.set_fraction(1.0
##         if not from_thread: gtk.gdk.threads_enter()
##         self.progressbar.set_fraction(1.0)
##         if not from_thread: gtk.gdk.threads_leave()
##         self.pb_lock.release()
#        
#
#    def pulse_progressbar(self, from_thread=False):
#        """
#        create a seperate thread the run the progress bar
#        """	
#	raise NotImplemented()
#        # TODO: this needs to be rethought, we can't use threads        
##         if not hasattr(self, "pb_lock"):
##             self.pb_lock = thread.allocate_lock()
##         self.stop_pulse = False
##         self.progressbar.set_pulse_step(.1)
##         self.progressbar.set_fraction(1.0)
##         id = thread.start_new_thread(self.pb_pulse_worker, (from_thread,))
#        
#
#    def stop_progressbar(self):
#        """
#        stop a progress bar
#        """
#        self.stop_pulse = True
#        #self.pb_lock.acquire()
#        #self.progressbar.set_fraction(1.0)
#        #self.pb_lock.release()    
#    
#    
#    def set_current_view(self, view_class):
#        """
#        set the current view, view is a class and will be instantiated
#        here, that way the same view won't be created again if the current
#        view os of the same type
#        """
#        current_view = self.get_current_view()
#        if type(current_view) == view_class: 
#            return
#        elif current_view != None:
#            self.content_hbox.remove(current_view)
#            current_view.destroy()
#            current_view = None
#        new_view = view_class()
#        self.content_hbox.pack_start(new_view, True, True)
#        
#        
#    def get_current_view(self):
#        '''
#        right now we on have one view, the SearchView, so this 
#        method should always return a SearchView instance
#        '''
#        kids = self.content_hbox.get_children()
#        if len(kids) == 0:
#            return None
#        else: return kids[0]        
#        
#        
#    def on_activate_view(self, menuitem, view):
#        """
#        set the selected view as current
#        """
#        self.set_current_view(view)
#
#
#    def on_activate_editor(self, menuitem, editor):
#        """
#        show the dialog of the selected editor
#        """
#        debug('on_activate_editor')
#        e = editor()
#        committed = e.start()
#        
#        
#    def create_main_menu(self):
#        """
#        get the main menu from the UIManager XML description, add its actions
#        and return the menubar
#        """
#        ui_manager = gtk.UIManager()
#        
#        # add accel group
#        self.accel_group = ui_manager.get_accel_group()
#        self.window.add_accel_group(self.accel_group)
#
#        # TODO: get rid of new, open, and just have a connection
#        # menu item
#        
#        # create and addaction group for menu actions
#        menu_actions = gtk.ActionGroup("MenuActions")
#        menu_actions.add_actions([("file", None, "_File"), 
#                                  ("file_new", gtk.STOCK_NEW, "_New", None, 
#                                   None, self.on_file_menu_new), 
#                                  ("file_open", gtk.STOCK_OPEN, "_Open", None, 
#                                   None, self.on_file_menu_open), 
#                                  ("file_quit", gtk.STOCK_QUIT, "_Quit", None, 
#                                   None, self.on_quit), 
#                                  ("edit", None, "_Edit"), 
#                                  ("edit_cut", gtk.STOCK_CUT, "_Cut", None, 
#                                   None, self.on_edit_menu_cut), 
#                                  ("edit_copy", gtk.STOCK_COPY, "_Copy", None, 
#                                   None, self.on_edit_menu_copy), 
#                                  ("edit_paste", gtk.STOCK_PASTE, "_Paste", 
#                                   None, None, self.on_edit_menu_paste), 
#                                  ("edit_preferences", None , "_Preferences", 
#                                   "<control>P", None, self.on_edit_menu_prefs), 
#                                  ("tools", None, "_Tools"),
#                                  ])
#        ui_manager.insert_action_group(menu_actions, 0)
#
#        # load ui
#        ui_filename = paths.lib_dir() + os.sep + "bauble.ui"
#        ui_manager.add_ui_from_file(ui_filename)
#
#        # get menu bar from ui manager
#        self.menubar = ui_manager.get_widget("/MenuBar")
#        
#        # TODO: why does't using the tools menu from the ui manager work
#        self.add_menu("_Insert", self.build_insert_menu())
#        self.add_menu("Tools", self.build_tools_menu())
#        
#        return self.menubar
#    
#    def add_menu(self, name, menu, index=-1):
#        menu_item = gtk.MenuItem(name)
#        menu_item.set_submenu(menu)
#        # we'll just append them for now but really we should
#        # get the number of children in the menubar and insert at len-1
#        # to account for the Help menu
#        self.menubar.append(menu_item)
#        self.menubar.show_all()
#        return menu_item
#
#        
#    def build_insert_menu(self):
#        menu = gtk.Menu()
#        compare_labels = lambda x, y: cmp(x.label, y.label)
#        for editor in sorted(editors.values(), cmp=compare_labels):
#            if editor.standalone:
#                try:
#                    item = gtk.MenuItem(editor.mnemonic_label)
#                except AttributeError:
#                    item = gtk.MenuItem(editor.label)
#                item.connect("activate", self.on_insert_menu_item_activate, editor)
#                menu.append(item)
#        return menu
#    
#    
#    def build_tools_menu(self):        
#        menu = gtk.Menu()
#        submenus = {}
#        for tool in tools.values():
#
#            item = gtk.MenuItem(tool.label)
#            item.connect("activate", self.on_tools_menu_item_activate, tool)
#            if tool.category is None: # not category
#                menu.append(item)
#            else:
#                if tool.category not in submenus: # create new category
#                    category_menu_item = gtk.MenuItem(tool.category)
#                    category_menu = gtk.Menu()
#                    category_menu_item.set_submenu(category_menu)
#                    menu.prepend(category_menu_item)
#                    submenus[tool.category] = category_menu
#                submenus[tool.category].append(item)
#            if not tool.enabled:
#                item.set_sensitive(False)
#        return menu
#        
#        
#    def on_tools_menu_item_activate(self, widget, tool):
#        tool.start()
#        
#        
#    def on_insert_menu_item_activate(self, widget, editor):
#        view = self.get_current_view()
#        expanded_rows = view.get_expanded_rows()
#        e = editor()
#        committed = e.start()
#        if committed is not None:
#            view.results_view.collapse_all()
#            view.expand_to_all_refs(expanded_rows)                        
#            
#            
#        
#    def on_edit_menu_prefs(self, widget, data=None):
#        p = PreferencesMgr()
#        p.run()
#        p.destroy()
#
#        
#    def on_edit_menu_cut(self, widget, data=None):
#        pass
#
#    
#    def on_edit_menu_copy(self, widget, data=None):
#        pass
#
#    
#    def on_edit_menu_paste(self, widget, data=None):
#        pass
#
#        
#    def on_file_menu_new(self, widget, date=None):        
#        msg = "If a database already exists at this connection then creating "\
#              "a new database could destroy your data.\n\n<i>Are you sure "\
#              "this is what you want to do?</i>"
#        if utils.yes_no_dialog(msg):
#            bauble.app.create_database()
#	    
#        # reset the view, i think this is already set 
#        self.get_current_view().reset()
#            
#        
#    def on_file_menu_open(self, widget, data=None):        
#        """
#        open the connection manager
#        """
#        from conn_mgr import ConnectionManager
#        default_conn = prefs[prefs.conn_default_pref]
#        cm = ConnectionManager(default_conn)
#        name, uri = cm.start()
#        if name is None:
#            return
#
#    	if bauble.app.open_database(uri, name) is not None:
#    	    self.window.set_title(self.title)
#    
#    	# reset the search view
#    	self.get_current_view().reset()
#            
#
#    def save_state(self):
#        """
#        this is usually called from bauble.py when it shuts down
#        """        
#        current_view = self.get_current_view()
#        if current_view is not None:
#            prefs[self.current_view_pref] = str(current_view.__class__)
#            # get label of view
#            #for label, view in views.iteritems(): 
#            #    if view == current_view.__class__:
#            #        Preferences[self.current_view_pref] = views.modules[view]
#        prefs.save()
#        
#        
#    def on_quit(self, widget, data=None):
#        bauble.app.quit()
#        
        

