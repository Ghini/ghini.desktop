#
# gui.py
#

import os, sys, time, re
import gtk, gobject
import bauble
import bauble.utils as utils
import bauble.paths as paths
import bauble.pluginmgr as pluginmgr
from bauble.prefs import prefs, PreferencesMgr
from bauble.utils.log import log, debug
from bauble.i18n import *
from bauble.utils.pyparsing import *
from bauble.view import SearchView



class GUI(object):
        
    def __init__(self):
        glade_path = os.path.join(paths.lib_dir(), 'bauble.glade')
        self.glade = gtk.glade.XML(glade_path)
        self.widgets = utils.GladeWidgets(self.glade)        
        self.window = self.widgets.main_window
        self.window.hide()
        
        self.window.set_default_size(800, 600)
        self.window.connect("destroy", self.on_quit)
        self.window.set_title(self.title)
        filename = os.path.join(paths.lib_dir(), "images", "icon.svg")
        pixbuf = gtk.gdk.pixbuf_new_from_file(filename)
        self.window.set_icon(pixbuf)
        
        menubar = self.create_main_menu()
        self.widgets.menu_box.pack_start(menubar)
        
        main_entry = self.widgets.main_entry
        main_entry.connect('key_press_event', self.on_main_entry_key_press)
        accel_group = gtk.AccelGroup()
        main_entry.add_accelerator("grab-focus", accel_group, ord('L'),
                                   gtk.gdk.CONTROL_MASK, gtk.ACCEL_VISIBLE)
        self.window.add_accel_group(accel_group)
        
        go_button = self.widgets.go_button
        go_button.connect('clicked', self.on_go_button_clicked)
                    
#        label = gtk.Label()
#        label.set_markup('<big>Welcome to Bauble.</big>')
#        self.widgets.view_box.pack_start(label)
        image = gtk.Image()
        image.set_from_file(os.path.join(paths.lib_dir(), 'images', 
                                         'bauble_logo.png'))
        self.widgets.view_box.pack_start(image)
        self.widgets.view_box.show_all()

        # add a progress bar to the statusbar
        #vbox = gtk.VBox(True, 0)        
        #self.widgets.statusbar.pack_start(vbox, False, True, 0)
        #self.progressbar = gtk.ProgressBar()
        #vbox.pack_start(self.progressbar, False, False, 0)        
        #self.widgets.statusbar.pack_start(self.progress, False, True, 0)
        #self.progressbar.set_size_request(-1, 10)
        #vbox.show_all()
        
        # add a progressbar to the status bar
        # Warning: this relies on gtk.Statusbar internals and could break in 
        # future versions of gtk
        statusbar = self.widgets.statusbar
        statusbar.set_spacing(10)
        statusbar.set_has_resize_grip(True)
        
        # remove label from frame
        frame = statusbar.get_children()[0]
        #frame.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse('#FF0000'))
        label = frame.get_children()[0]        
        frame.remove(label)
        
        # replace label with hbox and put label and progress bar in hbox
        hbox = gtk.HBox(False, 5)
        frame.add(hbox)
        hbox.pack_start(label, True, True, 0)        
        vbox = gtk.VBox(True, 0)
        hbox.pack_end(vbox, False, True, 15)
        self.progressbar = gtk.ProgressBar() 
        vbox.pack_start(self.progressbar, False, False, 0)
        self.progressbar.set_size_request(-1, 10)
        vbox.show()
        hbox.show()


    def show(self):
        self.build_tools_menu()
        self.window.show()

        
    def on_main_entry_key_press(self, widget, event, data=None):
        '''
        '''
        keyname = gtk.gdk.keyval_name(event.keyval)
        if keyname == "Return":
            self.widgets.go_button.emit("clicked")

            
    cmd = StringStart() + ':' + Word(alphanums + '-_').setResultsName('cmd')
    arg = restOfLine.setResultsName('arg')
    parser = (cmd + StringEnd()) | (cmd + '=' + arg) | arg
    def on_go_button_clicked(self, widget):
        '''
        '''
        text = self.widgets.main_entry.get_text()
        tokens = self.parser.parseString(text)
        cmd = None
        arg = None
        try:
            cmd = tokens['cmd']
        except KeyError, e:
            pass
        
        try:
            arg = tokens['arg']            
        except KeyError, e:
            pass
        
        bauble.command_handler(cmd, arg)

            
    def __get_title(self):
        if bauble.conn_name is None:
            return '%s %s' % ('Bauble', bauble.version_str)
        else:
            return '%s %s - %s' % ('Bauble', bauble.version_str, 
                                   bauble.conn_name)
    title = property(__get_title)


    def set_busy(self, busy):
        self.window.set_sensitive(not busy)
        if busy:
            self.window.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
        else:
            self.window.window.set_cursor(None)


    def set_view(self, view=None):
        '''
        set the view, if view is None then remove any views currently set
        
        @param view: default=None
        '''
        view_box = self.widgets.view_box
        for kids in view_box.get_children():
            view_box.remove(kids)
        view_box.pack_start(view, True, True, 0)            
        view.show_all()


    def get_view(self):
        '''
        return the current view in the view box
        '''
        return self.widgets.view_box.get_children()[0]


    def create_main_menu(self):
        """
        get the main menu from the UIManager XML description, add its actions
        and return the menubar
        """
        self.ui_manager = gtk.UIManager()
        
        # add accel group
        self.accel_group = self.ui_manager.get_accel_group()
        self.window.add_accel_group(self.accel_group)

        # TODO: get rid of new, open, and just have a connection
        # menu item
        
        # create and addaction group for menu actions
        menu_actions = gtk.ActionGroup("MenuActions")
        menu_actions.add_actions([("file", None, _("_File")), 
                                  ("file_new", gtk.STOCK_NEW, _("_New"), None, 
                                   None, self.on_file_menu_new), 
                                  ("file_open", gtk.STOCK_OPEN, _("_Open"),
                                   None, None, self.on_file_menu_open), 
                                  ("file_quit", gtk.STOCK_QUIT, _("_Quit"),
                                   None, None, self.on_quit), 
                                  ("edit", None, _("_Edit")), 
                                  ("edit_cut", gtk.STOCK_CUT, _("_Cut"), None, 
                                   None, self.on_edit_menu_cut), 
                                  ("edit_copy", gtk.STOCK_COPY, _("_Copy"),
                                   None, None, self.on_edit_menu_copy), 
                                  ("edit_paste", gtk.STOCK_PASTE, _("_Paste"), 
                                   None, None, self.on_edit_menu_paste), 
                                  ("edit_preferences", None,_("_Preferences"), 
                                   "<control>P", None,self.on_edit_menu_prefs),
                                  ("insert", None, _("_Insert")),
                                  ("tools", None, _("_Tools")),
                                  ])
        self.ui_manager.insert_action_group(menu_actions, 0)

        # load ui
        ui_filename = os.path.join(paths.lib_dir(), 'bauble.ui')
        self.ui_manager.add_ui_from_file(ui_filename)

        # get menu bar from ui manager
        self.menubar = self.ui_manager.get_widget("/MenuBar")

        def clear_menu(path):
            # clear out the insert an tools menus
            menu = self.ui_manager.get_widget(path)
            submenu = menu.get_submenu()
            for c in submenu.get_children():
                submenu.remove(c)
            menu.show()
        clear_menu('/ui/MenuBar/insert_menu')
        clear_menu('/ui/MenuBar/tools_menu')

        self.insert_menu= self.ui_manager.get_widget('/ui/MenuBar/insert_menu')
        return self.menubar
    

    def add_menu(self, name, menu, index=-1):
        '''
        add a menu to the menubar

        @param name:
        @param menu:
        @param index:
        '''
        menu_item = gtk.MenuItem(name)
        menu_item.set_submenu(menu)
        # we'll just append them for now but really we should
        # get the number of children in the menubar and insert at len-1
        # to account for the Help menu
        self.menubar.append(menu_item)
        self.menubar.show_all()
        return menu_item


    __insert_menu_cache = {}
    def add_to_insert_menu(self, editor, label):
        """
        add an editor to the insert menu
        
        @param editor: the editor to add to the menu
        @param label: the label for the menu item
        """
        menu = self.ui_manager.get_widget('/ui/MenuBar/insert_menu')
        submenu = menu.get_submenu()
        item = gtk.MenuItem(label)
        item.connect('activate', self.on_insert_menu_item_activate, editor)
        submenu.append(item)
        self.__insert_menu_cache[label] = item
        item.show()
        # sort items
        i = 0
        for label in sorted(self.__insert_menu_cache.keys()):
            submenu.reorder_child(self.__insert_menu_cache[label], i)
            i+=1


    def build_tools_menu(self):
        """
        build the tools menu from the tools provided by the plugins
        """
        topmenu = self.ui_manager.get_widget('/ui/MenuBar/tools_menu')
        menu = topmenu.get_submenu()
        menu.show()
        tools = []
        tools = {'__root': []}
        # categorize the tools into a dict
        for p in pluginmgr.plugins:
            for tool in p.tools:
                if tool.category is not None:
                    try:
                        tools[tool.category].append(tool)
                    except KeyError, e:
                        tools[tool.category] = []
                        tools[tool.category].append(tool)
                else:
                    tools['__root'].append(tool)

        # add the tools with not category to the root menu
        root_tools = sorted(tools.pop('__root'))
        for t in root_tools:
            item = gtk.MenuItem(t.label)
            item.show()
            item.connect("activate", self.on_tools_menu_item_activate, tool)
            menu.append(item)
            if not t.enabled:
                item.set_sensitive(False)

        # create submenus for the categories and add the tools 
        for category in sorted(tools.keys()):
            submenu = gtk.Menu()
            submenu_item = gtk.MenuItem(category)
            submenu_item.set_submenu(submenu)
            menu.append(submenu_item)
            for tool in sorted(tools[category], cmp=lambda x, y: cmp(x.label, y.label)):            
                item = gtk.MenuItem(tool.label)
                item.connect("activate", self.on_tools_menu_item_activate,tool)
                submenu.append(item)
                if not tool.enabled:
                    item.set_sensitive(False)
        menu.show_all()
        return menu
        
        
    def on_tools_menu_item_activate(self, widget, tool):
        tool.start()
        
        
    def on_insert_menu_item_activate(self, widget, editor):
        view = self.get_view()
        if isinstance(view, SearchView):
            expanded_rows = view.get_expanded_rows()
        e = editor()
        committed = e.start()
        if committed is not None and isinstance(view, SearchView):
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
            bauble.create_database()
        
                
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

        if bauble.open_database(uri, name) is not None:
            self.window.set_title(self.title)
            

    def save_state(self):
        """
        this is usually called from bauble.py when it shuts down
        """        
        prefs.save()
        
        
    def on_quit(self, widget, data=None):
        bauble.quit()
