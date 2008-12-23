#
# _gui.py
#

import os
import sys
import traceback

import gtk
import gobject

import bauble
import bauble.db as db
import bauble.utils as utils
import bauble.utils.desktop as desktop
import bauble.paths as paths
import bauble.pluginmgr as pluginmgr
from bauble.prefs import prefs
from bauble.utils.log import log, debug
from bauble.i18n import _
from bauble.utils.pyparsing import *
from bauble.view import SearchView
import bauble.error as error


class DefaultView(pluginmgr.View):
    '''
    DefaultView is not related to view.DefaultCommandHandler
    '''
    def __init__(self):
        super(DefaultView, self).__init__()
        image = gtk.Image()
        image.set_from_file(os.path.join(paths.lib_dir(), 'images',
                                         'bauble_logo.png'))
        self.pack_start(image)



class GUI(object):

    entry_history_pref = 'bauble.history'
    history_size_pref = 'bauble.history_size'
    window_geometry_pref = "bauble.geometry"
    _default_history_size = 12

    def __init__(self):
        glade_path = os.path.join(paths.lib_dir(), 'bauble.glade')
        self.glade = gtk.glade.XML(glade_path)
        self.widgets = utils.GladeWidgets(self.glade)
        self.window = self.widgets.main_window
        self.window.hide()

        # restore the window size
        geometry = prefs[self.window_geometry_pref]
        if geometry is not None:
            self.window.set_default_size(*geometry)

        self.window.connect('delete-event', self.on_delete_event)
        self.window.connect("destroy", self.on_quit)
        self.window.set_title(self.title)

        try:
            pixbuf = gtk.gdk.pixbuf_new_from_file(bauble.default_icon)
            self.window.set_icon(pixbuf)
        except:
            utils.message_details_dialog(_('Could not load icon from %s' % \
                                         bauble.default_icon),
                                         traceback.format_exc(),
                                         gtk.MESSAGE_ERROR)

        menubar = self.create_main_menu()
        self.widgets.menu_box.pack_start(menubar)

        self.populate_main_entry()
        main_entry = self.widgets.main_entry

#        main_entry.connect('key_press_event', self.on_main_entry_key_press)
        main_entry.connect('activate', self.on_main_entry_activate)
        accel_group = gtk.AccelGroup()
        main_entry.add_accelerator("grab-focus", accel_group, ord('L'),
                                   gtk.gdk.CONTROL_MASK, gtk.ACCEL_VISIBLE)
        self.window.add_accel_group(accel_group)

        go_button = self.widgets.go_button
        go_button.connect('clicked', self.on_go_button_clicked)

        self.set_default_view()

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

        cmd = StringStart() +':'+ Word(alphanums + '-_').setResultsName('cmd')
        arg = restOfLine.setResultsName('arg')
        self.cmd_parser = (cmd + StringEnd()) | (cmd + '=' + arg) | arg


        def on_expanded(*args):
            eb = self.widgets.msg_eventbox
            width, height = eb.size_request()
            eb.set_size_request(-1, -1)
            eb.queue_resize()
        self.widgets.msg_eventbox.hide()
        self.widgets.msg_details_expander.connect('notify::expanded',
                                                  on_expanded)
        img = gtk.Image()
        img.set_from_stock(gtk.STOCK_CLOSE, gtk.ICON_SIZE_SMALL_TOOLBAR)
        button = self.widgets.msg_close_button
        button.set_label('')
        button.set_image(img)
        button.set_relief(gtk.RELIEF_NONE)
#         def on_enter(button, *args):
#             debug(button)
#             button.emit_stop_by_name('enter')
#             button.stop_emission('enter')
#             #button.emit_stop_by_name('enter-notify-event')
#             #button.stop_emission('enter-notify-event')
#             return True
#         button.connect('enter', on_enter)
        self.widgets.msg_close_button.connect('clicked', self.close_msg_box)


    # TODO: need to handle the case where a message is added when
    # another message already exists or the message box is in the
    # middle of either opening or closing

    def close_msg_box(self, *args):
        # TODO: reverse animate?
        eb = self.widgets.msg_eventbox.hide()
        self.widgets.msg_details_expander.set_expanded(False)


    def _msg_common(self, msg, colors):
        eb = self.widgets.msg_eventbox
        colormap = eb.get_colormap()
        style = eb.get_style().copy()
        for attr, state, color in colors:
            c = colormap.alloc_color(color)
            getattr(style, attr)[state] = c
        # is it ok to set the style the expander and button even
        # though the style was copied from the eventbox
        eb.set_style(style)
        self.widgets.msg_details_expander.set_style(style)
        self.widgets.msg_close_button.set_style(style)
        self.widgets.msg_label.set_text(msg)


    def info_msg(self, msg):
        colors = [('bg', gtk.STATE_NORMAL, '#b6daf2')]
        self._msg_common(msg, colors)
        self.widgets.msg_eventbox.show()


    def error_msg(self, msg, details=None):
        colors = [('bg', gtk.STATE_NORMAL, '#FF9999'),
                  ('bg', gtk.STATE_PRELIGHT, '#FFAAAA')]
        self._msg_common(msg, colors)
        eb = self.widgets.msg_eventbox

        if not details:
            self.widgets.msg_details_expander.set_property('visible', False)
        else:
            self.widgets.msg_details_expander.set_property('visible', True)
            self.widgets.msg_details_label.set_text(details)
        width, height = eb.size_request()
        eb.set_size_request(width, 0)
        eb.show()
        def animate(final_height):
            width, height = eb.size_request()
            if height >= final_height:
                return False
            height = height + 5
            eb.set_size_request(width, height)
            return True
        gobject.timeout_add(10, animate, height)


    def show(self):
        self.build_tools_menu()
        self.window.show()


    def _get_history_size(self):
        history = prefs[self.history_size_pref]
        if history is None:
            prefs[self.history_size_pref] = self._default_history_size
        return int(prefs[self.history_size_pref])
    history_size = property(_get_history_size)


#     def on_main_entry_key_press(self, widget, event, data=None):
#         '''
#         '''
#         keyname = gtk.gdk.keyval_name(event.keyval)
#         if keyname == "Return":
#             self.widgets.go_button.emit("clicked")
#             return True
#         else:
#             return False


    def send_command(self, command):
        self.widgets.main_entry.set_text(command)
        self.widgets.go_button.emit("clicked")


    def on_main_entry_activate(self, widget, data=None):
        self.widgets.go_button.emit("clicked")


    def on_go_button_clicked(self, widget):
        '''
        '''
        self.close_msg_box()
        text = self.widgets.main_entry.get_text()
	if text == '':
	    return
        self.add_to_history(text)
        tokens = self.cmd_parser.parseString(text)
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


    def add_to_history(self, text, index=0):
        """
        add text to history, if text is already in the history then set its
        index to index parameter
        """
        if index < 0 or index > self.history_size:
            raise ValueError(_('history size must be greater than zero and '\
                               'less than the history size'))
        history = prefs.get(self.entry_history_pref, [])
        if text in history:
            history.remove(text)

        # trim the history if the size is larger than the history_size pref
        while len(history) >= self.history_size-1:
            history.pop()

        history.insert(index, text)
        prefs[self.entry_history_pref] = history
        self.populate_main_entry()


    def populate_main_entry(self):
        history = prefs[self.entry_history_pref]
        main_combo = self.widgets.main_comboentry
        model = main_combo.get_model()
        model.clear()
        completion = self.widgets.main_entry.get_completion()
        if completion is None:
            completion = gtk.EntryCompletion()
            completion.set_text_column(0)
            self.widgets.main_entry.set_completion(completion)
            compl_model = gtk.ListStore(str)
            completion.set_model(compl_model)
            completion.set_popup_completion(False)
            completion.set_inline_completion(True)
            completion.set_minimum_key_length(2)
        else:
            compl_model = completion.get_model()

        if history is not None:
            for herstory in history:
                main_combo.append_text(herstory)
                compl_model.append([herstory])
        main_combo.set_model(model)


    def __get_title(self):
        if bauble.conn_name is None:
            return '%s %s' % ('Bauble', bauble.version)
        else:
            return '%s %s - %s' % ('Bauble', bauble.version,
                                   bauble.conn_name)
    title = property(__get_title)


    def set_busy(self, busy):
        self.window.set_sensitive(not busy)
        if busy:
            self.window.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
        else:
            self.window.window.set_cursor(None)


    def set_default_view(self):
        if self.widgets.main_entry is not None:
            self.widgets.main_entry.set_text('')
        self.set_view(DefaultView())


    def set_view(self, view=None):
        '''
        set the view, if view is None then remove any views currently set

        @param view: default=None
        '''
        view_box = self.widgets.view_box
        if view_box is None:
            return # viewbox should never be None, why is this here?
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
##                                   ("edit_preferences", None,
##                                    _("_Preferences"),
##                                    "<control>P", None,
##                                    self.on_edit_menu_prefs),
                                  ("insert", None, _("_Insert")),
                                  ("tools", None, _("_Tools")),
				  ("help", None, _("_Help")),
				  ("help_contents", gtk.STOCK_HELP,
				   _("Contents"), None, None,
				   self.on_help_menu_contents),
				  ("help_bug", None, _("Report a bug"), None,
				   None, self.on_help_menu_bug),
				  ("help_web", gtk.STOCK_HOME,
				   _("Bauble website"), None,
				   None, self.on_help_menu_web),
				  ("help_about", gtk.STOCK_ABOUT, _("About"),
				   None, None, self.on_help_menu_about),
                                  ])
        self.ui_manager.insert_action_group(menu_actions, 0)

        # load ui
        ui_filename = os.path.join(paths.lib_dir(), 'bauble.ui')
        self.ui_manager.add_ui_from_file(ui_filename)

        # get menu bar from ui manager
        self.menubar = self.ui_manager.get_widget("/MenuBar")

        self.clear_menu('/ui/MenuBar/insert_menu')
        self.clear_menu('/ui/MenuBar/tools_menu')

        self.insert_menu= self.ui_manager.get_widget('/ui/MenuBar/insert_menu')
        return self.menubar


    def clear_menu(self, path):
        """
        remove all the menus items from a menu
        """
        # clear out the insert an tools menus
        menu = self.ui_manager.get_widget(path)
        submenu = menu.get_submenu()
        for c in submenu.get_children():
            submenu.remove(c)
        menu.show()


    def add_menu(self, name, menu, index=-1):
        '''
        add a menu to the menubar

        @param name:
        @param menu:
        @param index:
        '''
        menu_item = gtk.MenuItem(name)
        menu_item.set_submenu(menu)
	self.menubar.insert(menu_item, len(self.menubar.get_children())-1)
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
            i += 1


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
        for p in pluginmgr.plugins.values():
            for tool in p.tools:
                if tool.category is not None:
                    try:
                        tools[tool.category].append(tool)
                    except KeyError, e:
                        tools[tool.category] = []
                        tools[tool.category].append(tool)
                else:
                    tools['__root'].append(tool)

        # add the tools with no category to the root menu
        root_tools = sorted(tools.pop('__root'))
        for tool in root_tools:
            item = gtk.MenuItem(tool.label)
            item.show()
            item.connect("activate", self.on_tools_menu_item_activate, tool)
            menu.append(item)
            if not tool.enabled:
                item.set_sensitive(False)

        # create submenus for the categories and add the tools
        for category in sorted(tools.keys()):
            submenu = gtk.Menu()
            submenu_item = gtk.MenuItem(category)
            submenu_item.set_submenu(submenu)
            menu.append(submenu_item)
            for tool in sorted(tools[category],
                               cmp=lambda x, y: cmp(x.label, y.label)):
                item = gtk.MenuItem(tool.label)
                item.connect("activate", self.on_tools_menu_item_activate,
                             tool)
                submenu.append(item)
                if not tool.enabled:
                    item.set_sensitive(False)
        menu.show_all()
        return menu


    def on_tools_menu_item_activate(self, widget, tool):
#        debug('on_tools_menu_item_activate(%s)' % tool)
        try:
            tool.start()
        except Exception, e:
            utils.message_details_dialog(utils.xml_safe(str(e)),
                                         traceback.format_exc(),
                                         gtk.MESSAGE_ERROR)
            debug(traceback.format_exc())


    def on_insert_menu_item_activate(self, widget, editor):
        try:
            view = self.get_view()
            if isinstance(view, SearchView):
                expanded_rows = view.get_expanded_rows()
            e = editor()
            committed = e.start()
            if committed is not None and isinstance(view, SearchView):
                view.results_view.collapse_all()
                view.expand_to_all_refs(expanded_rows)
        except Exception, e:
            utils.message_details_dialog(utils.xml_safe(str(e)),
                                         traceback.format_exc(),
                                         gtk.MESSAGE_ERROR)
            debug(traceback.format_exc())


##     def on_edit_menu_prefs(self, widget, data=None):
##         p = PreferencesMgr()
##         p.run()
##         p.destroy()


    def on_edit_menu_cut(self, widget, data=None):
        self.widgets.main_entry.cut_clipboard()


    def on_edit_menu_copy(self, widget, data=None):
        self.widgets.main_entry.copy_clipboard()


    def on_edit_menu_paste(self, widget, data=None):
        self.widgets.main_entry.paste_clipboard()


    def on_file_menu_new(self, widget, data=None):
        msg = "If a database already exists at this connection then creating "\
              "a new database could destroy your data.\n\n<i>Are you sure "\
              "this is what you want to do?</i>"

        if not utils.yes_no_dialog(msg, yes_delay=2):
            return

        #if gui is not None and hasattr(gui, 'insert_menu'):
        submenu = self.insert_menu.get_submenu()
        for c in submenu.get_children():
            submenu.remove(c)
        self.insert_menu.show()
        db.create()
        pluginmgr.init()
        self.set_default_view()


    def on_file_menu_open(self, widget, data=None):
        """
        open the connection manager
        """
        from connmgr import ConnectionManager
        default_conn = prefs[bauble.conn_default_pref]
        cm = ConnectionManager(default_conn)
        name, uri = cm.start()
        if name is None:
            return

        engine = None
        try:
            engine = db.open(uri, False)
        except Exception, e:
            debug(e)
            if isinstance(e, error.DatabaseError):
                return
            msg = _("Could not open connection.\n\n%s") % \
                  utils.xml_safe_utf8(e)
            utils.message_details_dialog(msg, traceback.format_exc(),
                                         gtk.MESSAGE_ERROR)

        if engine is None:
            return

        # show a custom message if its a version error and continue to use
        # the same engine, if its a different error then verify again but
        # show_error_dialogs = True

        # TODO: there's no reason for us to call _verify_connection a
        # second time when we could just catch this exception in the
        # open_database above
        try:
            db._verify_connection(engine, show_error_dialogs=False)
        except error.VersionError, e:
            msg = _('You are using Bauble version %(version)s while the '\
                    'database you have connected to was created with '\
                    'version %(db_version)s\n\nSome things might not work as '\
                    'or some of your data may become unexpectedly '\
                    'corrupted.') % \
                    {'version': bauble.version,
                     'db_version':'%s' % e.version}
            utils.message_dialog(msg, gtk.MESSAGE_ERROR)
        except Exception, e:
            db._verify_connection(engine, show_error_dialogs=True)

        # everything seems to have passed ok so setup the rest of bauble
        if engine is not None:
            bauble.conn_name = name
            self.window.set_title(self.title)
            # TODO: come up with a better way to reset the handler than have
            # to bauble.last_handler = None
            #
            # we have to set last_handler to None since although the
            # view is changing the handler isn't so we might end up
            # using the same instance of a view that could have old
            # settings from the previous handler...
            bauble.last_handler = None
            self.set_default_view()
            self.clear_menu('/ui/MenuBar/insert_menu')
            pluginmgr.init()


    def on_help_menu_contents(self, widget, data=None):
	desktop.open('http://bauble.belizebotanic.org/using.html')


    def on_help_menu_bug(self, widget, data=None):
	desktop.open('https://bugs.launchpad.net/bauble/+bugs')


    def on_help_menu_web(self, widget, data=None):
	desktop.open('http://bauble.belizebotanic.org')


    def on_help_menu_about(self, widget, data=None):
	about = gtk.AboutDialog()
	about.set_name('Bauble')
	about.set_version(bauble.version)
	about.set_website(_('http://bauble.belizebotanic.org'))
	about.set_logo_icon_name('bauble')
	about.set_copyright(_(u'Copyright \u00A9 Belize Botanic Gardens'))
	about.run()
	about.destroy()


    def save_state(self):
        """
        this is usually called from bauble.py when it shuts down
        """
        rect = self.window.allocation
        prefs[self.window_geometry_pref] = rect.width, rect.height
        # prefs.save() is called in bauble/__init__.py


    def on_delete_event(self, *args):
        import bauble.task as task
        if task._flushing or not task._task_queue.empty():
            msg = _('Would you like the cancel the current tasks?')
            if not utils.yes_no_dialog(msg):
                # stop other handlers for being invoked for this event
                return True
        return False

    def on_quit(self, widget, data=None):
        bauble.quit()
