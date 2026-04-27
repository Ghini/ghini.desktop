#
# Copyright 2008-2010 Brett Adams
# Copyright 2015,2018 Mario Frasca <mario@anche.no>.
# Copyright 2018 Tanager Botanical Garden <tanagertourism@gmail.com>
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
#
# ui.py
#
import logging
import os
import traceback
from gettext import gettext as _
from typing import Any, Optional

import bauble
import bauble.db as db
import bauble.paths as paths
import bauble.pluginmgr as pluginmgr
import bauble.utils as utils
import bauble.utils.desktop as desktop
from bauble import querybuilder
from bauble.editor import GenericEditorView
from bauble.gtkinit import Gdk, GdkPixbuf, GLib, Gtk
from bauble.prefs import prefs
from bauble.view import SearchView

logger: Any = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def safe_set_text(gtk_widget, text) -> None:
    """
    Sets the text of a Gtk widget replacing None with an empty string.

    :param label: Instance of a Gtk widget
    :param text: The text to set, which may be None
    """
    if text is None:
        text = ""
    gtk_widget.set_text(text)


class DefaultView(pluginmgr.View):
    """ghini's home screen

    come back here if you want the numeric overview and the stored queries.

    in Bauble this was just a splash screen, displayed at program start and
    never again.  it was basically a "what do I do now" screen.

    DefaultView is related to the SplashCommandHandler,
    not to the view.DefaultCommandHandler

    """

    hbox: Any
    infobox: Any
    infoboxclass: Any = None

    def __init__(self) -> None:
        super().__init__()

        # splash window contains a hbox: left half is for the proper splash,
        # right half for infobox, only one infobox is allowed.

        self.hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        self.hbox.set_margin_start(5)
        self.add(self.hbox)

        image = Gtk.Image()
        image.set_from_file(os.path.join(paths.lib_dir(), "images", "bauble_logo.png"))
        self.hbox.pack_start(image, True, True, 0)

        # the following means we do not have an infobox yet
        self.infobox = None

    def update(self) -> None:
        logger.debug("DefaultView::update")
        if self.infoboxclass and not self.infobox:
            logger.debug("DefaultView::update - creating infobox")
            self.infobox = self.infoboxclass()
            self.hbox.pack_end(self.infobox, False, True, 8)
            self.infobox.show()
        if self.infobox:
            logger.debug("DefaultView::update - updating infobox")
            self.infobox.update()


class SplashCommandHandler(pluginmgr.CommandHandler):

    def __init__(self) -> None:
        super().__init__()
        if self.view is None:
            logger.warning("SplashCommandHandler.view is None, expect trouble")

    command: Any = ["home", "splash"]
    view: Any = None

    def get_view(self):
        if self.view is None:
            self.view = DefaultView()
        return self.view

    def __call__(self, cmd, arg) -> None:
        self.view.update()


def create_menu_item_with_image(
    label, icon_name: Optional[Any] = None, base_dir: Optional[Any] = None
):
    """Return a MenuItem with an associated image, if provided.

    Args:
        label (str or object): The label or object representing the menu item.
        icon_name (str, optional): The name or path of the icon to display.
        base_dir (str, optional): Base directory for icon lookup.

    Returns:
        Gtk.MenuItem: A Gtk.MenuItem, with an optional image if provided.
    """
    if not isinstance(label, str):
        # Extract attributes if label is an object
        tool = label
        label = getattr(tool, "label", "Unknown")
        icon_name = getattr(tool, "icon_name", None)
        path_to_module = tool.__module__.split(".")[1:]
        if path_to_module[-2] != "plugins":
            path_to_module = path_to_module[:-1]
        base_dir = os.path.join(paths.lib_dir(), *path_to_module)

    logger.debug(f"create_menu_item_with_image {label} {icon_name} {base_dir}")

    # Resolve full path for PNG icons
    if base_dir and icon_name and icon_name.endswith(".png"):
        icon_name = os.path.join(base_dir, icon_name)

    image = None
    if icon_name:
        try:
            if icon_name.endswith(".png"):
                # Load and scale PNG icon
                pb = GdkPixbuf.Pixbuf.new_from_file(icon_name)
                (what, width, height) = Gtk.IconSize.lookup(Gtk.IconSize.MENU)
                pb = pb.scale_simple(width, height, GdkPixbuf.InterpType.BILINEAR)
                image = Gtk.Image.new_from_pixbuf(pb)
            else:
                # Load theme icon
                image = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.MENU)
        except (GLib.Error, FileNotFoundError):
            logger.debug(f"Cannot load icon: {icon_name}")

    # Create the menu item
    item = Gtk.MenuItem()
    hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    if image:
        hbox.pack_start(image, False, False, 0)
    label_widget = Gtk.Label(label=label)
    hbox.pack_start(label_widget, True, True, 0)
    item.add(hbox)

    return item


class GUI:

    widgets: Any
    window: Any
    previous_view: Any
    _cids: Any
    progressbar: Any
    cmd_parser: Any
    menubar: Any
    insert_menu: Any
    tools_menu: Any
    entry_history_pref: str = "bauble.history"
    history_size_pref: str = "bauble.history_size"
    window_geometry_pref: str = "bauble.geometry"
    _default_history_size: int = 12

    def __init__(self) -> None:
        filename = os.path.join(paths.lib_dir(), "bauble.glade")
        self.widgets = utils.BuilderWidgets(filename)
        self.window = self.widgets.main_window
        self.window.hide()
        self.previous_view = None

        # restore the window size
        geometry = prefs[self.window_geometry_pref]
        if geometry is not None:
            self.window.set_default_size(*geometry)

        self.window.connect("delete-event", self.on_delete_event)
        self.window.connect("destroy", self.on_quit)
        self.window.set_title(self.title)

        try:
            logger.debug(f"loading icon from {bauble.default_icon}")
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(bauble.default_icon)
            self.window.set_icon(pixbuf)
        except Exception:
            logger.warning(_("Could not load icon from %s") % bauble.default_icon)
            logger.warning(traceback.format_exc())

        self.create_main_menu()

        combo = self.widgets.main_comboentry
        model = Gtk.ListStore(str)
        combo.set_model(model)
        self.populate_main_entry()

        main_entry = combo.get_child()
        main_entry.connect("activate", self.on_main_entry_activate)

        # Add modern shortcut for focus (GTK 3 equivalent)
        accel_group = Gtk.AccelGroup()

        # Add the accel group to the main window
        self.window.add_accel_group(accel_group)

        # Bind the shortcut (Ctrl+L) to focus on the main_entry widget
        key, mod = Gtk.accelerator_parse("<Control>L")
        accel_group.connect(
            key,
            mod,
            Gtk.AccelFlags.VISIBLE,
            lambda accel_group, acceleratable, keyval, modifier: main_entry.grab_focus(),
        )

        self.widgets.home_button.connect("clicked", self.on_home_button_clicked)

        self.widgets.prev_view_button.connect(
            "clicked", self.on_prev_view_button_clicked
        )

        self.widgets.go_button.connect("clicked", self.on_go_button_clicked)

        self.widgets.query_button.connect("clicked", self.on_query_button_clicked)

        self.set_default_view()

        # add a progressbar to the status bar
        # Warning: this relies on Gtk.Statusbar internals and could break in
        # future versions of gtk
        statusbar = self.widgets.statusbar
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        statusbar.add(hbox)
        self._cids = []

        statusbar.connect("text-pushed", self.on_statusbar_push)

        # remove label from frame
        frame = statusbar.get_children()[0]
        label = frame.get_children()[0]
        frame.remove(label)

        # replace label with hbox and put label and progress bar in hbox
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        frame.add(hbox)
        hbox.pack_start(label, True, True, 0)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        hbox.pack_end(vbox, False, True, 15)
        self.progressbar = Gtk.ProgressBar()
        vbox.pack_start(self.progressbar, False, False, 0)
        self.progressbar.set_size_request(-1, 10)
        vbox.show()
        hbox.show()

        from pyparsing import StringEnd, StringStart, Word, alphanums, restOfLine

        cmd = StringStart() + ":" + Word(alphanums + "-_").setResultsName("cmd")
        arg = restOfLine.setResultsName("arg")
        self.cmd_parser = (cmd + StringEnd()) | (cmd + "=" + arg) | arg

        combo.grab_focus()

    def on_statusbar_push(self, sb, cid, txt) -> None:
        if cid not in self._cids:
            self._cids.append(cid)

    def close_message_box(self, *args) -> None:
        parent = self.widgets.msg_box_parent
        for kid in self.widgets.msg_box_parent:
            parent.remove(kid)
        return

    def show_yesno_box(self, msg) -> None:
        self.close_message_box()
        box = utils.add_message_box(
            self.widgets.msg_box_parent, utils.MESSAGE_BOX_YESNO
        )
        box.message = msg
        box.show()

    def show_error_box(self, msg, details: Optional[Any] = None) -> None:
        self.close_message_box()
        box = utils.add_message_box(self.widgets.msg_box_parent, utils.MESSAGE_BOX_INFO)
        box.message = msg
        box.details = details
        rgba1 = Gdk.RGBA()
        rgba1.parse("#FF9999")

        rgba2 = Gdk.RGBA()
        rgba2.parse("#FFAAAA")

        colors = [
            ("bg", Gtk.StateType.NORMAL, rgba1),
            ("bg", Gtk.StateType.PRELIGHT, rgba2),
        ]
        for color in colors:
            box.set_color(*color)
        box.show()

    def show_message_box(self, msg) -> None:
        """
        Show an info message in the message drop down box
        """
        self.close_message_box()
        box = utils.add_message_box(self.widgets.msg_box_parent, utils.MESSAGE_BOX_INFO)
        box.message = msg
        box.show()

    #        colors = [('bg', Gtk.StateType.NORMAL, Gdk.Color.parse('#b6daf2').color)]
    #        self._msg_common(msg, colors)
    #        self.widgets.msg_eventbox.show()

    def show(self) -> None:
        self.window.show()

    def _get_history_size(self):
        history = prefs[self.history_size_pref]
        if history is None:
            prefs[self.history_size_pref] = self._default_history_size
        return int(prefs[self.history_size_pref])

    history_size: Any = property(_get_history_size)

    def send_command(self, command) -> None:
        safe_set_text(self.widgets.main_comboentry.get_child(), command)
        self.widgets.go_button.emit("clicked")

    def on_main_entry_activate(self, widget, data: Optional[Any] = None) -> None:
        self.widgets.go_button.emit("clicked")

    def on_home_button_clicked(self, widget) -> None:
        """ """
        bauble.command_handler("home", None)

    def on_prev_view_button_clicked(self, widget) -> None:
        """ """
        safe_set_text(self.widgets.main_comboentry.get_child(), "")
        bauble.gui.set_view("previous")

    def on_go_button_clicked(self, widget) -> None:
        """ """
        self.close_message_box()
        text = self.widgets.main_comboentry.get_child().get_text()
        if text == "":
            return
        self.add_to_history(text)
        tokens = self.cmd_parser.parseString(text)
        cmd = None
        arg = None
        try:
            cmd = tokens["cmd"]
        except KeyError:
            pass

        try:
            arg = tokens["arg"]
        except KeyError as e:
            logger.debug(e)

        bauble.command_handler(cmd, arg)

    def on_query_button_clicked(self, widget) -> None:
        gladefilepath = os.path.join(paths.lib_dir(), "querybuilder.glade")
        view = GenericEditorView(
            gladefilepath, parent=None, root_widget_name="main_dialog"
        )
        qb = querybuilder.QueryBuilder(view)
        qb.set_query(self.widgets.main_comboentry.get_child().get_text())
        response = qb.start()
        if response == Gtk.ResponseType.OK:
            query = qb.get_query()
            safe_set_text(self.widgets.main_comboentry.get_child(), query)
            self.widgets.go_button.emit("clicked")
        qb.cleanup()

    def add_to_history(self, text, index: int = 0) -> None:
        """
        add text to history, if text is already in the history then set its
        index to index parameter
        """
        if index < 0 or index > self.history_size:
            raise ValueError(
                _(
                    "history size must be greater than zero and "
                    "less than the history size"
                )
            )
        history = prefs.get(self.entry_history_pref, [])
        if text in history:
            history.remove(text)

        # trim the history if the size is larger than the history_size pref
        while len(history) >= self.history_size - 1:
            history.pop()

        history.insert(index, text)
        prefs[self.entry_history_pref] = history
        self.populate_main_entry()

    def populate_main_entry(self) -> None:
        history = prefs[self.entry_history_pref]
        main_combo = self.widgets.main_comboentry
        model = main_combo.get_model()
        model.clear()
        main_entry = self.widgets.main_comboentry.get_child()
        completion = main_entry.get_completion()
        if completion is None:
            completion = Gtk.EntryCompletion()
            completion.set_text_column(0)
            main_entry.set_completion(completion)
            compl_model = Gtk.ListStore(str)
            completion.set_model(compl_model)
            completion.set_property("popup_completion", False)
            completion.set_property("inline_completion", True)
            completion.set_minimum_key_length(2)
        else:
            compl_model = completion.get_model()

        if history is not None:
            for herstory in history:
                main_combo.append_text(herstory)
                compl_model.append([herstory])

    def __get_title(self):
        if bauble.conn_name is None:
            return "{} {}".format("Ghini", bauble.version)
        else:
            return "{} {} - {}".format("Ghini", bauble.version, bauble.conn_name)

    title: Any = property(__get_title)

    def set_busy(self, busy) -> None:
        self.widgets.main_box.set_sensitive(not busy)
        if busy:
            self.window.get_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.WATCH))
        else:
            self.window.get_window().set_cursor(None)

    def set_default_view(self) -> None:
        main_entry = self.widgets.main_comboentry.get_child()
        if main_entry is not None:
            main_entry.set_text("")
        SplashCommandHandler.view = DefaultView()
        self.set_view(SplashCommandHandler.view)
        pluginmgr.register_command(SplashCommandHandler)

    def set_view(self, view: Optional[Any] = None) -> None:
        """
        set the view, if view is None then remove any views currently set

        :param view: default=None
        """
        if view == "previous":
            view = self.previous_view
            self.previous_view = None
        if view is None:
            return
        view_box = self.widgets.view_box
        must_add_this_view = True
        for kid in view_box.get_children():
            if view == kid:
                must_add_this_view = False
                kid.set_visible(True)
            else:
                if kid.get_visible() is True:
                    self.previous_view = kid
                kid.set_visible(False)
                kid.cancel_threads()
        if must_add_this_view:
            view_box.pack_start(view, True, True, 0)
        view.show_all()

    def get_view(self):
        """
        return the current view in the view box
        """
        for kid in self.widgets.view_box.get_children():
            if kid.get_visible():
                return kid
        return None

    def get_results_model(self, quiet: bool = False):
        model = None
        view = bauble.gui.get_view()
        from bauble.view import SearchView

        if isinstance(view, SearchView):
            model = view.results_view.get_model()

        if model is None and not quiet:
            utils.message_dialog(_("Search for something first."))

        return model

    def create_main_menu(self):
        """
        Create the main menu programmatically without relying on deprecated Gtk.UIManager.

        The menu structure and actions are dynamically built to mimic the original functionality,
        including the use of `add_actions` for defining callbacks and shortcuts.
        """
        # Create the MenuBar
        self.menubar = Gtk.MenuBar()

        # Add an AccelGroup for keyboard shortcuts
        accel_group = Gtk.AccelGroup()
        self.window.add_accel_group(accel_group)

        # --- File Menu ---
        file_menu_item = Gtk.MenuItem(label=_("File"))
        file_menu = Gtk.Menu()
        file_menu_item.set_submenu(file_menu)
        self.menubar.append(file_menu_item)

        # File menu entries
        new_item = Gtk.MenuItem(label=_("New"))
        new_item.connect("activate", self.on_file_menu_new)
        new_item.set_sensitive(False)
        file_menu.append(new_item)

        open_item = Gtk.MenuItem(label=_("Open"))
        open_item.connect("activate", self.on_file_menu_open)
        open_item.set_sensitive(True)
        file_menu.append(open_item)

        # Add a keyboard shortcut (Ctrl+O) for the Open menu item
        open_item.add_accelerator(
            "activate",
            accel_group,
            ord("O"),
            Gdk.ModifierType.CONTROL_MASK,
            Gtk.AccelFlags.VISIBLE,
        )

        quit_item = Gtk.MenuItem(label=_("Quit"))
        quit_item.connect("activate", self.on_quit)
        file_menu.append(quit_item)

        # Add a keyboard shortcut (Ctrl+Q) for the Quit menu item
        quit_item.add_accelerator(
            "activate",
            accel_group,
            ord("Q"),
            Gdk.ModifierType.CONTROL_MASK,
            Gtk.AccelFlags.VISIBLE,
        )

        # --- Edit Menu ---
        edit_menu_item = Gtk.MenuItem(label=_("Edit"))
        edit_menu = Gtk.Menu()
        edit_menu_item.set_submenu(edit_menu)
        self.menubar.append(edit_menu_item)

        # Edit menu entries
        cut_item = Gtk.MenuItem(label=_("Cut"))
        cut_item.connect("activate", self.on_edit_menu_cut)
        edit_menu.append(cut_item)

        copy_item = Gtk.MenuItem(label=_("Copy"))
        copy_item.connect("activate", self.on_edit_menu_copy)
        edit_menu.append(copy_item)

        paste_item = Gtk.MenuItem(label=_("Paste"))
        paste_item.connect("activate", self.on_edit_menu_paste)
        edit_menu.append(paste_item)

        # --- Insert Menu ---
        insert_menu_item = Gtk.MenuItem(label=_("Insert"))
        self.insert_menu = Gtk.Menu()
        insert_menu_item.set_submenu(self.insert_menu)
        self.menubar.append(insert_menu_item)

        # Dynamically populated later by plugins
        self.clear_menu(self.insert_menu)

        # --- Tools Menu ---
        tools_menu_item = Gtk.MenuItem(label=_("Tools"))
        self.tools_menu = Gtk.Menu()
        tools_menu_item.set_submenu(self.tools_menu)
        self.menubar.append(tools_menu_item)

        # Dynamically populated later by plugins
        self.clear_menu(self.tools_menu)

        # --- Help Menu ---
        help_menu_item = Gtk.MenuItem(label=_("Help"))
        help_menu = Gtk.Menu()
        help_menu_item.set_submenu(help_menu)
        self.menubar.append(help_menu_item)

        # Help menu entries
        help_contents_item = Gtk.MenuItem(label=_("Contents"))
        help_contents_item.connect("activate", self.on_help_menu_contents)
        help_menu.append(help_contents_item)

        bug_report_item = Gtk.MenuItem(label=_("Report a Bug"))
        try:
            icon_name = os.path.join(paths.lib_dir(), "images", "menu-help-bug.png")
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(icon_name)
            (what, width, height) = Gtk.IconSize.lookup(Gtk.IconSize.MENU)
            pixbuf = pixbuf.scale_simple(width, height, GdkPixbuf.InterpType.BILINEAR)
            image = Gtk.Image.new_from_pixbuf(pixbuf)
            # 7. issue_gtk_button_image_api (REMOVED, pack GtkImage manually inside GtkButton)
            bug_report_item.set_child(image)
            if Gtk.get_major_version() >= 4:
                bug_report_item.set_child(image)
            else:
                bug_report_item.add(image)
                bug_report_item.show_all()
        except Exception as e:
            logger.debug(f"Cannot set icon {icon_name}: {e}")
        bug_report_item.connect("activate", self.on_help_menu_bug)
        help_menu.append(bug_report_item)

        log_file_item = Gtk.MenuItem(label=_("Open the log-file"))
        log_file_item.connect("activate", self.on_help_menu_logfile)
        help_menu.append(log_file_item)

        web_devel_item = Gtk.MenuItem(label=_("Ghini development website"))
        web_devel_item.connect("activate", self.on_help_menu_web_devel)
        help_menu.append(web_devel_item)

        ghini_news_item = Gtk.MenuItem(label=_("Ghini news"))
        ghini_news_item.connect("activate", self.on_help_menu_web_wiki)
        help_menu.append(ghini_news_item)

        ghini_forum_item = Gtk.MenuItem(label=_("Ghini news"))
        ghini_forum_item.connect("activate", self.on_help_menu_web_forum)
        help_menu.append(ghini_forum_item)

        about_item = Gtk.MenuItem(label=_("About"))
        about_item.connect("activate", self.on_help_menu_about)
        help_menu.append(about_item)

        # Add the MenuBar to the main window
        self.widgets.menu_box.pack_start(self.menubar, False, False, 0)
        self.menubar.show_all()

        return self.menubar

    def clear_menu(self, menu) -> None:
        """
        Remove all items from a Gtk.Menu.

        :param menu: Gtk.Menu object to clear.
        """
        if not isinstance(menu, Gtk.Menu):
            logger.error(f"clear_menu expects a Gtk.Menu, got: {type(menu)}")
            return

        for item in menu.get_children():
            menu.remove(item)
        menu.show()

    def add_menu(self, name, menu, index: int = -1):
        """
        add a menu to the menubar

        :param name:
        :param menu:
        :param index:
        """
        menu_item = Gtk.MenuItem(label=name)
        menu_item.set_submenu(menu)
        self.menubar.insert(menu_item, len(self.menubar.get_children()) - 1)
        self.menubar.show_all()
        return menu_item

    __insert_menu_cache: Any = {}

    def add_to_insert_menu(
        self,
        editor,
        label,
        icon_name: Optional[Any] = None,
        base_dir: Optional[Any] = None,
    ) -> None:
        """
        Add an editor to the insert menu.

        :param editor: the editor class or callable to add to the menu
        :param label: the label for the menu item
        :param icon_name: optional icon name or path for the menu item
        :param base_dir: base directory for the icon, if applicable
        """
        # Ensure the insert menu exists
        if self.insert_menu is None:
            logger.error("Insert menu is not initialized.")
            return

        # Create a menu item with an optional image
        item = create_menu_item_with_image(label, icon_name, base_dir)

        # Connect the menu item activation to the provided editor
        item.connect("activate", self.on_insert_menu_item_activate, editor)

        # Append the item to the insert menu
        self.insert_menu.append(item)

        # Optionally cache the item by its label
        self.__insert_menu_cache[label] = item

        # Make the menu item visible
        item.show()

    def add_to_tools_menu(
        self, menu, tool, on_activate_callback, base_dir: Optional[Any] = None
    ) -> None:
        """
        Helper function to add a tool to a tools menu.

        Args:
            menu (Gtk.Menu): The menu to which the tool should be added.
            tool (object): The tool object containing label, icon, and other metadata.
            on_activate_callback (function): The callback to execute when the tool is activated.
        """
        base = None
        if base_dir is not None:
            base = os.path.join(paths.lib_dir(), base_dir)
        item = create_menu_item_with_image(tool.label, tool.icon_name, base)
        item.connect("activate", on_activate_callback, tool)
        menu.append(item)
        if not tool.enabled:
            item.set_sensitive(False)
        item.show()

    def build_tools_menu(self):
        """
        Build the tools menu from the tools provided by the plugins.

        This method dynamically updates the Tools menu after plugin initialization.
        """
        # Assuming self.tools_menu is a Gtk.Menu instance
        tools_menu = self.tools_menu  # Direct reference to the tools Gtk.Menu
        if not tools_menu:
            logger.error("Tools menu is not defined!")
            return

        # Clear existing menu items
        for child in tools_menu.get_children():
            tools_menu.remove(child)

        tools = {}
        category_icon = {}

        # Categorize tools into a dictionary
        for plugin in pluginmgr.plugins.values():
            for tool in plugin.tools:
                if isinstance(tool.category, tuple):
                    tool.category, icon = tool.category
                    category_icon[tool.category] = icon
                tools.setdefault(tool.category, []).append(tool)

        # Add tools with no category to the root menu
        root_tools = tools.pop(None, [])
        for tool in sorted(root_tools, key=lambda x: getattr(x, "item_position", 0)):
            self.add_to_tools_menu(
                tools_menu, tool, self.on_tools_menu_item_activate, tool.icon_dir
            )
        tools_menu.show_all()

        # Create submenus for categorized tools
        for category in sorted(tools.keys()):
            submenu = Gtk.Menu()
            submenu_item = create_menu_item_with_image(
                category, category_icon.get(category), paths.lib_dir()
            )
            submenu_item.set_submenu(submenu)
            tools_menu.append(submenu_item)
            submenu_item.show()

            for tool in sorted(tools[category], key=lambda x: x.label):
                try:
                    self.add_to_tools_menu(
                        submenu, tool, self.on_tools_menu_item_activate, tool.icon_dir
                    )
                except:
                    self.add_to_tools_menu(
                        submenu, tool, self.on_tools_menu_item_activate, tool.icon_dir
                    )
            submenu_item.show_all()

        # Ensure all menu items are visible
        tools_menu.show_all()

    def on_tools_menu_item_activate(self, widget, tool) -> None:
        """
        Start a tool on the Tool menu.
        """
        try:
            tool.start()
        except Exception as e:
            utils.message_details_dialog(
                utils.xml_safe(str(e)),
                traceback.format_exc(),
                Gtk.MessageType.ERROR,
            )
            logger.debug(traceback.format_exc())

    def on_insert_menu_item_activate(self, widget, editor_cls):
        try:
            view = self.get_view()
            if isinstance(view, SearchView):
                expanded_rows = view.get_expanded_rows()
            # editor_cls can be a class, of which we get an instance, and we
            # invoke the `start` method of this instance. or it is a
            # callable, then we just use its return value and we are done.
            if isinstance(editor_cls, type(lambda x: x)):
                editor = None
                committed = editor_cls()
            else:
                editor = editor_cls()
                committed = editor.start()
            if committed is not None and isinstance(view, SearchView):
                view.results_view.collapse_all()
                view.expand_to_all_refs(expanded_rows)
        except Exception as e:
            utils.message_details_dialog(
                utils.xml_safe(str(e)),
                traceback.format_exc(),
                Gtk.MessageType.ERROR,
            )
            logger.error(
                f"bauble.gui.on_insert_menu_item_activate():\n {traceback.format_exc()}"
            )
            return

        if editor is None:
            return

        presenter_cls = view_cls = None
        if hasattr(editor, "presenter"):
            presenter_cls = type(editor.presenter)
            view_cls = type(editor.presenter.view)

        # delete the editor
        del editor

        # check for leaks
        obj = utils.gc_objects_by_type(editor_cls)
        if obj != []:
            logger.warning(f"{editor_cls.__name__} leaked: {obj}")

        if presenter_cls:
            obj = utils.gc_objects_by_type(presenter_cls)
            if obj != []:
                logger.warning(f"{presenter_cls.__name__} leaked: {obj}")
            obj = utils.gc_objects_by_type(view_cls)
            if obj != []:
                logger.warning(f"{view_cls.__name__} leaked: {obj}")

    def on_edit_menu_cut(self, widget, data: Optional[Any] = None) -> None:
        self.widgets.main_comboentry.get_child().cut_clipboard()

    def on_edit_menu_copy(self, widget, data: Optional[Any] = None) -> None:
        self.widgets.main_comboentry.get_child().copy_clipboard()

    def on_edit_menu_paste(self, widget, data: Optional[Any] = None) -> None:
        self.widgets.main_comboentry.get_child().paste_clipboard()

    def on_file_menu_new(self, widget, data: Optional[Any] = None) -> None:
        msg = (
            "If a database already exists at this connection then creating "
            "a new database could destroy your data.\n\n<i>Are you sure "
            "this is what you want to do?</i>"
        )

        if not utils.yes_no_dialog(msg, yes_delay=2):
            return

        # if gui is not None and hasattr(gui, 'insert_menu'):
        submenu = self.insert_menu.get_submenu()
        for c in submenu.get_children():
            submenu.remove(c)
        self.insert_menu.show()
        try:
            db.create()
            pluginmgr.init()
        except Exception as e:
            msg = _("Could not create a new database.\n\n%s") % utils.xml_safe(e)
            tb = utils.xml_safe(traceback.format_exc())
            utils.message_details_dialog(msg, tb, Gtk.MessageType.ERROR)
            return
        self.set_default_view()

    def on_file_menu_open(self, widget, data: Optional[Any] = None) -> None:
        """Open the connection manager."""
        from .connmgr import start_connection_manager

        default_conn = prefs[bauble.conn_default_pref]
        name, uri = start_connection_manager(default_conn)
        if name is None:
            return

        global engine
        if engine is not None:
            engine.dispose()
            engine = None
        try:
            engine = db.open(uri, True, True)
        except Exception as e:
            # we don't do anything to handle the exception since db.open()
            # should have shown an error dialog if there was a problem
            # opening the database as long as the show_error_dialogs
            # parameter is True
            logger.warning(e)

        if engine is None:
            # the database wasn't open
            return

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
            self.get_view().update()
            self.clear_menu("/ui/MenuBar/insert_menu")
            self.statusbar_clear()
            pluginmgr.init()

    def statusbar_clear(self) -> None:
        """
        Call Gtk.Statusbar.pop() for each context_id that had previously
        been pushed() onto the the statusbar stack.  This might not clear
        all the messages in the statusbar but it's the best we can do
        without knowing how many messages are in the stack.
        """
        # TODO: to clear everything in the statusbar we would probably
        # have to subclass Gtk.Statusbar to keep track of the message
        # ids and context ids so we can properly clear the statusbar.
        for cid in self._cids:
            self.widgets.statusbar.pop(cid)

    def on_help_menu_contents(self, widget, data: Optional[Any] = None) -> None:
        desktop.open(
            "http://ghini.readthedocs.io/en/ghini-3.1-dev/",
            dialog_on_error=True,
        )

    def on_help_menu_bug(self, widget, data: Optional[Any] = None) -> None:
        desktop.open(
            "https://github.com/Ghini/ghini.desktop/issues/new",
            dialog_on_error=True,
        )

    def on_help_menu_logfile(self, widget, data: Optional[Any] = None) -> None:
        filename = "file://" + os.path.join(paths.appdata_dir(), "bauble.log")
        desktop.open(filename, dialog_on_error=True)

    def on_help_menu_web_devel(self, widget, data: Optional[Any] = None) -> None:
        desktop.open("http://github.com/Ghini/ghini.desktop/", dialog_on_error=True)

    def on_help_menu_web_wiki(self, widget, data: Optional[Any] = None) -> None:
        desktop.open("http://ghini.github.io/", dialog_on_error=True)

    def on_help_menu_web_forum(self, widget, data: Optional[Any] = None) -> None:
        desktop.open(
            "https://groups.google.com/forum/#!forum/bauble",
            dialog_on_error=True,
        )

    def on_help_menu_about(self, widget, data: Optional[Any] = None) -> None:
        about = Gtk.AboutDialog()
        about.set_name("Ghini")
        about.set_version(bauble.version)
        about.set_website(_("http://ghini.github.io"))
        f = os.path.join(paths.lib_dir(), "images", "icon.svg")
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(f)
        about.set_logo(pixbuf)
        about.set_copyright(_("Copyright © by its contributors."))

        import codecs

        with codecs.open(
            os.path.join(paths.installation_dir(), "share", "ghini", "LICENSE")
        ) as f:
            license = f.read()
        about.set_license(license)  # not translated
        about.set_comments(
            _(
                "This version installed on: %s\n"
                "Latest published version: %s\n"
                "Publication date: %s"
            )
            % (
                bauble.installation_date,
                bauble.release_version,
                bauble.release_date,
            )
        )
        about.run()
        about.destroy()

    def save_state(self) -> None:
        """
        this is usually called from bauble.py when it shuts down
        """
        rect = self.window.get_allocation()
        prefs[self.window_geometry_pref] = rect.width, rect.height
        # prefs.save() is called in bauble/__init__.py

    def on_delete_event(self, *args):
        import bauble.task as task

        if task.running():
            msg = _("Would you like the cancel the current tasks?")
            if not utils.yes_no_dialog(msg):
                # stop other handlers for being invoked for this event
                return True
            task.kill()
        return False

    def on_quit(self, widget, data: Optional[Any] = None) -> None:
        bauble.quit()
