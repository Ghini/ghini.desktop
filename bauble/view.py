#
# Copyright 2008-2010 Brett Adams
# Copyright 2015 Mario Frasca <mario@anche.no>.
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
# Description: the default view
#
import html
import itertools
import logging
import os
import sys
import threading
import traceback
from gettext import gettext as _
from typing import Any, Optional

import bauble
import sqlalchemy.exc as saexc

# from bauble import prefs
from bauble import db as db
from bauble import editor as editor
from bauble import gui as gui
from bauble import paths as paths
from bauble import pictures_view as pictures_view
from bauble import pluginmgr as pluginmgr
from bauble import search as search
from bauble import utils as utils
from bauble.error import BaubleError, check
from bauble.gtkinit import Champlain, Clutter, Gdk, Gio, GLib, Gtk, GtkClutter, Pango
from bauble.shared import InfoExpander
from pyparsing import ParseException
from sqlalchemy import func, select
from sqlalchemy.orm import object_session

logger: Any = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

display: Any
_substr_tmpl: str
 
# Ensure GTK is initialized and get the display
display = Gdk.Display.get_default()
if not display:
    raise RuntimeError("GDK Display could not be initialized.")

# Explicitly set Clutter's GDK display before initializing Clutter
Clutter.set_windowing_backend("x11")  # Use "x11" explicitly if running in X11

# Now initialize Clutter and GtkClutter
GtkClutter.init([])  # GtkClutter first
Clutter.init([])  # Then Clutter

css: bytes = b"""
#history_tv row:nth-child(even) {
    background: #F0F0F0; /* Light grey background for even rows */
}
"""


def apply_css() -> None:
    css_provider = Gtk.CssProvider()
    css_provider.load_from_data(css)

    display = Gdk.Display.get_default()

    try:
        # Try GTK 4 method
        Gtk.StyleContext.add_provider_for_display(
            display, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    except AttributeError:
        # Fallback to GTK 3 method
        screen = display.get_default_screen()
        Gtk.StyleContext.add_provider_for_screen(
            screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )


def safe_set_text(gtk_widget, text) -> None:
    """
    Sets the text of a Gtk widget replacing None with an empty string.

    :param label: Instance of a Gtk widget
    :param text: The text to set, which may be None
    """
    if text is None:
        text = ""
    gtk_widget.set_text(text)


# use different formatting template for the result view depending on the
# platform
_mainstr_tmpl: str = "<b>%s</b>"
if sys.platform == "win32":
    _substr_tmpl = "%s"
else:
    _substr_tmpl = "<small>%s</small>"

class Action:
    """
    An Action allows a label, tooltip, callback, and accelerator to be called
    when specific items are selected in the SearchView.

    Updated to use `Gio.SimpleAction` instead of deprecated `Gtk.Action`.
    """
    name: Any
    label: Any
    tooltip: Any
    stock_id: Any
    callback: Any
    multiselect: Any
    singleselect: Any
    accelerator: Any
    action: Any
    def __init__(
        self,
        name,
        label,
        tooltip: Optional[Any] = None,
        stock_id: Optional[Any] = None,
        callback: Optional[Any] = None,
        accelerator: Optional[Any] = None,
        multiselect: bool = False,
        singleselect: bool = True
    ) -> None:
        """
        :param name: Unique action name (e.g., "open").
        :param label: The action label.
        :param tooltip: Tooltip text.
        :param stock_id: Icon name for the action.
        :param callback: Function to execute when activated.
        :param accelerator: Keyboard shortcut (e.g., "<Ctrl>O").
        :param multiselect: Show menu when multiple items are selected.
        :param singleselect: Show menu when a single item is selected.
        :param app: The `Gtk.Application` where the action will be registered.
        """
        self.name = name
        self.label = label
        self.tooltip = tooltip
        self.stock_id = stock_id  # Save stock_id for potential icon use
        self.callback = callback
        self.multiselect = multiselect
        self.singleselect = singleselect
        self.accelerator = accelerator

        # Create the action
        self.action = Gio.SimpleAction.new(name, None)
        if callback:
            self.action.connect("activate", callback)

        from bauble import app

        app.gtk_app.add_action(self.action)

        # Register the action with the application if provided
        if accelerator:
            self.set_action_accelerator(app, name, accelerator)

    def set_action_accelerator(self, app, action_name, accelerator) -> None:
        """
        Set keyboard accelerators for an action, compatible with both GTK 3 and GTK 4.
        """
        if Gtk.get_major_version() >= 4:
            # GTK 4 uses set_accels_for_action
            app.set_accels_for_action(f"app.{action_name}", [accelerator])
        else:
            accel_path = f"<Actions>/app.{action_name}"
            key, mods = Gtk.accelerator_parse(accelerator)

            # Ensure we pass the correct number of arguments
            Gtk.AccelMap.add_entry(accel_path, key, mods)
            Gtk.AccelMap.change_entry(accel_path, key, mods, True)

    def _on_activate(self, action, param) -> None:
        """Call the provided callback function when activated."""
        if self.callback:
            self.callback()

    def set_enabled(self, enable) -> None:
        """Enable or disable the action (similar to set_visible)."""
        self.action.set_enabled(enable)

    def get_enabled(self):
        """Check if the action is enabled."""
        return self.action.get_enabled()

    enabled: Any = property(get_enabled, set_enabled)


class PropertiesExpander(InfoExpander):
    id_data: Any
    type_data: Any
    created_data: Any
    updated_data: Any
    def __init__(self) -> None:
        super().__init__(_("Properties"))
        table = Gtk.Grid()
        table.set_column_spacing(15)
        table.set_row_spacing(8)

        # Helper to create labels with alignment and markup
        def create_label(text, use_markup=False, align=(1, 0.5)):
            label = Gtk.Label(label=text)
            label.set_property("use_markup", use_markup)
            label.set_xalign(align[0])
            label.set_yalign(align[1])
            return label

        # Database ID
        id_label = create_label("<b>" + _("ID:") + "</b>", use_markup=True)
        self.id_data = create_label("--", align=(0, 0.5))

        table.attach(id_label, 0, 0, 1, 1)
        table.attach(self.id_data, 1, 0, 1, 1)

        # Object type
        type_label = create_label("<b>" + _("Type:") + "</b>", use_markup=True)
        self.type_data = create_label("--", align=(0, 0.5))

        table.attach(type_label, 0, 1, 1, 1)
        table.attach(self.type_data, 1, 1, 1, 1)

        # Date created
        created_label = create_label(
            "<b>" + _("Date created:") + "</b>", use_markup=True
        )
        self.created_data = create_label("--", align=(0, 0.5))

        table.attach(created_label, 0, 2, 1, 1)
        table.attach(self.created_data, 1, 2, 1, 1)

        # Last updated
        updated_label = create_label(
            "<b>" + _("Last updated:") + "</b>", use_markup=True
        )
        self.updated_data = create_label("--", align=(0, 0.5))

        table.attach(updated_label, 0, 3, 1, 1)
        table.attach(self.updated_data, 1, 3, 1, 1)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.pack_start(table, False, False, 0)
        self.vbox.pack_start(box, False, False, 0)

    def update(self, row) -> None:
        """Update the widget in the expander."""
        safe_set_text(self.id_data, str(row.id))
        safe_set_text(self.type_data, str(type(row).__name__))
        safe_set_text(
            self.created_data,
            row._created.strftime("%Y-%m-%d %H:%M:%S") if row._created else "",
        )
        safe_set_text(
            self.updated_data,
            (
                row._last_updated.strftime("%Y-%m-%d %H:%M:%S")
                if row._last_updated
                else ""
            ),
        )


class MapInfoExpander(InfoExpander):
    """
    Displays a location on a map using Champlain.
    """
    map_widget: Any
    get_points: Any
    layer: Any
    def __init__(self, get_points: Optional[Any] = None) -> None:
        super().__init__(_("Location on map"))

        self.map_widget = Champlain.View()
        self.map_widget.set_size_request(230, 230)
        self.vbox.pack_start(self.map_widget, False, False, 0)
        self.map_widget.set_horizontal_wrap(True)
        self.map_widget.set_sensitive(False)

        self.get_points = get_points
        self.layer = Champlain.MarkerLayer()
        self.map_widget.add_layer(self.layer)
        self.layer.show()

    def on_expanded(self, *args) -> None:
        """Toggle visibility based on expander state."""
        super().on_expanded(*args)
        self.map_widget.set_visible(self.get_expanded())

    def update(self, row) -> None:
        """Update the map with points from the row."""
        self.map_widget.set_visible(self.get_expanded())

        black = Gdk.RGBA(
            0, 0, 0, 0.5
        )  # Equivalent to Clutter.Color.new(0x00, 0x00, 0x00, 0x7F)

        self.layer.remove_all()
        if self.get_points is None:
            return

        i = None
        points = self.get_points(row)
        for i in points:
            marker = Champlain.Point()
            marker.set_color(black)
            marker.set_size(5)
            marker.set_location(i["lat"], i["lon"])
            self.layer.add_marker(marker)

        if i is not None:
            self.map_widget.center_on(i["lat"], i["lon"])
            self.map_widget.set_zoom_level(18)


class InfoBoxPage:
    """
    Container for :class:`bauble.view.InfoExpander` objects.
    Uses composition instead of subclassing Gtk.ScrolledWindow.
    """
    container: Any
    vbox: Any
    expanders: Any
    def __init__(self) -> None:
        self.container = Gtk.ScrolledWindow()
        self.container.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.container.add(self.vbox)
        self.expanders = {}

    def add_expander(self, expander) -> None:
        """
        Add an expander to the list of expanders in this infobox.

        :param expander: the bauble.view.InfoExpander to add to this infobox
        """
        self.vbox.pack_start(expander, False, True, 5)
        self.expanders[expander.get_label()] = (
            expander  # Use get_label() instead of get_property("label")
        )

        expander._sep = Gtk.Separator.new(orientation=Gtk.Orientation.HORIZONTAL)
        self.vbox.pack_start(expander._sep, False, False, 0)

    def get_expander(self, label):
        """
        Returns an expander by its label.

        :param label: the name of the expander to return
        """
        return self.expanders.get(label, None)

    def remove_expander(self, label):
        """
        Remove an expander from the infobox by its label.

        :param label: the name of the expander to remove.

        Return the removed expander.
        """
        expander = self.expanders.pop(label, None)
        if expander:
            self.vbox.remove(expander)
        return expander

    def update(self, row) -> None:
        """
        Updates the infobox with values from row.

        :param row: The mapped instance to use to update this infobox,
                    passed to each of the InfoExpander instances.
        """
        for expander in self.expanders.values():
            expander.update(row)


class InfoBox:
    """
    Holds a list of expanders with an optional tabbed layout.

    The default is to not use tabs. To create the InfoBox with tabs,
    use `InfoBox(tabbed=True)`. When using tabs, expanders can be added
    directly to the `InfoBoxPage` or via `InfoBox.add_expander(page_num)`.
    """
    notebook: Any
    row: Any
    def __init__(self, tabbed: bool = False) -> None:
        self.notebook = Gtk.Notebook()
        self.row = None
        self.notebook.set_show_border(False)

        if not tabbed:
            page = InfoBoxPage()
            self.notebook.append_page(
                page, None
            )  # insert_page → append_page for clarity
            self.notebook.set_show_tabs(False)

        self.notebook.set_current_page(0)
        self.notebook.connect("switch-page", self.on_switch_page)

    def on_switch_page(self, notebook, dummy_page, page_num, *args) -> None:
        """
        Called when a page is switched.
        """
        if self.row:
            page = self.notebook.get_nth_page(page_num)
            page.update(self.row)

    def add_expander(self, expander, page_num: int = 0) -> None:
        """
        Add an expander to a specific page.

        :param expander: The expander to add.
        :param page_num: The page index in the InfoBox to add the expander.
        """
        page = self.notebook.get_nth_page(page_num)
        page.add_expander(expander)

    def update(self, row) -> None:
        """
        Update the current page with the given row.
        """
        self.row = row
        page_num = self.notebook.get_current_page()
        self.notebook.get_nth_page(page_num).update(row)


class LinksExpander(InfoExpander):
    """
    Displays external links and notes associated with a row.
    """
    dynamic_box: Any
    notes: Any
    buttons: Any
    def __init__(self, notes: Optional[Any] = None, links: Optional[Any] = None) -> None:
        """
        :param notes: The name of the notes property on the row.
        """
        if links is None:
            links = []
        super().__init__(_("Links"))

        self.dynamic_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.vbox.pack_start(self.dynamic_box, True, True, 0)

        self.notes = notes
        self.buttons = []
        from bauble.utils.web import BaubleLinkButton

        for link in links:
            try:
                klass = type(link["name"], (BaubleLinkButton,), link)
                self.buttons.append(klass())
            except Exception as e:
                logger.warning(f"Invalid link definition {link}: {type(e)}({e})")

        for button in self.buttons:
            button.set_halign(Gtk.Align.START)
            self.vbox.pack_start(button, False, False, 0)

    def update(self, row) -> None:
        """
        Update links and notes for the given row.
        """
        list(map(self.dynamic_box.remove, self.dynamic_box.get_children()))

        for button in self.buttons:
            button.set_string(row)

        if self.notes:
            notes = getattr(row, self.notes, [])
            for note in notes:
                for label, url in utils.get_urls(note.note):
                    label_text = label or url
                    label = Gtk.Label(label=label_text)
                    label.set_property("ellipsize", Pango.EllipsizeMode.END)

                    button = Gtk.LinkButton(uri=url)

                    # GTK 4 requires set_child(), GTK 3 uses add()
                    if hasattr(button, "set_child"):
                        button.set_child(label)  # GTK 4
                    else:
                        button.add(label)  # GTK 3

                    button.set_halign(Gtk.Align.START)
                    self.dynamic_box.pack_start(button, False, False, 0)

            self.dynamic_box.show_all()




logger = logging.getLogger(__name__)


class AddOneDot(threading.Thread):
    """
    Adds dots to the status bar to indicate loading progress.
    """
    __stopped: Any
    dotno: int
    statusbar: Any
    sbcontext_id: Any
    def __init__(self) -> None:
        super().__init__()
        self.__stopped = threading.Event()
        self.dotno = 0
        self.statusbar = bauble.gui.widgets.statusbar
        self.sbcontext_id = self.statusbar.get_context_id("searchview.nresults")

    def cancel(self) -> None:
        self.__stopped.set()

    def run(self) -> None:
        while not self.__stopped.wait(1.0):
            self.dotno += 1
            GLib.idle_add(self.update_status)

    def update_status(self) -> None:
        """Update the status bar message on the main thread."""
        self.statusbar.pop(self.sbcontext_id)
        self.statusbar.push(self.sbcontext_id, _("counting results") + "." * self.dotno)


class CountResultsTask(threading.Thread):
    """
    Counts top-level results and updates the status bar.
    """
    klass: Any
    ids: Any
    dots_thread: Any
    __cancel: Any
    statusbar: Any
    sbcontext_id: Any
    def __init__(self, klass, ids, dots_thread) -> None:
        super().__init__()
        self.klass = klass
        self.ids = ids
        self.dots_thread = dots_thread
        self.__cancel = threading.Event()
        self.statusbar = bauble.gui.widgets.statusbar
        self.sbcontext_id = self.statusbar.get_context_id("searchview.nresults")

    def cancel(self) -> None:
        self.__cancel.set()

    def run(self) -> None:
        session = db.Session()
        klass = self.klass
        d = {}

        for ndx in self.ids:
            if self.__cancel.is_set():
                break

            item = (
                session.execute(select(klass).where(klass.id == ndx)).scalars().first()
            )
            if not item:
                logger.warning(f"object {klass.__name__}({ndx}) disappeared")
                break

            for k, v in item.top_level_count().items():
                d[k] = d.get(k, set()) | v if isinstance(v, set) else d.get(k, 0) + v

        if not self.__cancel.is_set():
            result = ", ".join(
                f"{k if isinstance(k, str) else k[1]}: {len(v) if isinstance(v, set) else v}"
                for k, v in sorted(d.items())
            )
            status_text = _("top level count: %s") % result

            GLib.idle_add(self.update_status, status_text)

        self.dots_thread.cancel()
        session.close()

    def update_status(self, text) -> None:
        """Update the status bar message on the main thread."""
        self.statusbar.pop(self.sbcontext_id)
        self.statusbar.push(self.sbcontext_id, text)


class PopulateResults(threading.Thread):
    """
    Populates search results asynchronously.
    """
    view: Any
    results: Any
    __stopped: Any
    statusbar: Any
    sbcontext_id: Any
    def __init__(self, view, results) -> None:
        super().__init__()
        self.view = view
        self.results = [(type(i).__name__, str(i), i) for i in results]
        self.__stopped = threading.Event()
        self.statusbar = bauble.gui.widgets.statusbar
        self.sbcontext_id = self.statusbar.get_context_id("searchview.nresults")

    def cancel(self) -> None:
        self.__stopped.set()

    def run(self):
        results = self.results
        nresults = len(results)
        steps_so_far = 0
        added = set()

        groups = sorted(
            (
                list(group)
                for _, group in itertools.groupby(
                    sorted(results, key=lambda x: x[:2]), key=lambda x: x[0]
                )
            ),
            key=lambda x: x[0][0],
            reverse=True,
        )

        model = self.view.results_view.get_model()

        def append_expandable_row(model, content):
            parent = model.append(None, [content])
            content_type = type(content)
            meta = self.view.row_meta[content_type]  # returns a ViewMeta.Meta
            if meta.children is not None:
                model.append(parent, ["-"])

        for _kname, _klass, obj in itertools.chain(*groups):
            if self.__stopped.is_set():
                return
            if obj in added:
                continue

            GLib.idle_add(append_expandable_row, model, obj)

            if not added:  # First iteration
                GLib.idle_add(self.view.results_view.set_cursor, 0)
                GLib.idle_add(self.view.results_view.scroll_to_cell, 0)

            steps_so_far += 1
            percent = steps_so_far / nresults
            if 0 < percent < 1.0:
                GLib.idle_add(bauble.gui.progressbar.set_fraction, percent)

            added.add(obj)

        # Final status update
        GLib.idle_add(self.update_status, _("counting results"))

        # If all results are of the same type, count top-level results
        unique_classes = {item[2].__class__ for item in results}
        if len(unique_classes) == 1:
            dots_thread = self.view.start_thread(AddOneDot())
            self.view.start_thread(
                CountResultsTask(
                    results[0][2].__class__, [i[2].id for i in results], dots_thread
                )
            )
        else:
            GLib.idle_add(
                self.update_status,
                _("size of non homogeneous result: %s") % len(results),
            )

    def update_status(self, text) -> None:
        """Update the status bar message on the main thread."""
        self.statusbar.pop(self.sbcontext_id)
        self.statusbar.push(self.sbcontext_id, text)


class SearchView(pluginmgr.View):
    """
    The SearchView is the main view for Ghini. It manages search results
    when text is entered into the main text entry.
    """
    widgets: Any
    view: Any
    context_menu_cache: Any
    infobox_cache: Any
    infobox: Any
    session: Any
    running_threads: Any
    installed_accels: Any
    results_view: Any
    accel_group: Any
    pane: Any
    picpane: Any
    class ViewMeta(dict):
        """
        This class shouldn't need to be instantiated directly.
        Access meta via `SearchView.row_meta`
        """

        class Meta:
            children: Any
            infobox: Any
            markup_func: Any
            actions: Any
            context_menu: Any
            def __init__(self) -> None:
                self.children = None
                self.infobox = None
                self.markup_func = None
                self.actions = []

            def set(
                self, children: Optional[Any] = None, infobox: Optional[Any] = None, context_menu: Optional[Any] = None, markup_func: Optional[Any] = None
            ) -> None:
                """
                Set metadata properties for the ViewMeta class.

                :param children: Function or attribute name for fetching children.
                :param infobox: Infobox class to display information.
                :param context_menu: List of actions for right-click context menus.
                :param markup_func: Function for generating markup.
                """
                self.children = children
                self.infobox = infobox
                self.markup_func = markup_func
                self.context_menu = context_menu

                self.actions = (
                    [x for x in context_menu if isinstance(x, Action)]
                    if context_menu
                    else []
                )

            def get_children(self, obj):
                if self.children is None:
                    return []
                return (
                    self.children(obj)
                    if callable(self.children)
                    else getattr(obj, self.children)
                )

        def __getitem__(self, item):
            if item not in self:
                self[item] = self.Meta()
            return self.get(item)

    row_meta: Any = ViewMeta()
    bottom_info: Any = ViewMeta()

    def __init__(self) -> None:
        logger.debug("SearchView::__init__")
        super().__init__()

        # Load UI
        filename = os.path.join(paths.lib_dir(), "bauble.glade")
        self.widgets = utils.BuilderWidgets(filename)
        self.view = editor.GenericEditorView(filename, root_widget_name="main_window")

        self.create_gui()

        # Picture view

        pictures_view.floating_window = pictures_view.PicturesView(
            parent=self.widgets.search_h2pane
        )

        # Internal caches
        self.context_menu_cache = {}
        self.infobox_cache = {}
        self.infobox = None

        # Database session
        self.session = db.Session()

        # UI setup
        self.add_notes_page_to_bottom_notebook()
        self.running_threads = []

    def add_notes_page_to_bottom_notebook(self) -> None:
        """add notebook page for notes

        this is a temporary function, will be removed when notes are
        implemented as a plugin. then notes will be added with the
        generic add_page_to_bottom_notebook.

        """
        page = self.widgets["notes_scrolledwindow"]
        self.widgets.remove_parent(page)
        label = Gtk.Label(label="Notes")
        self.widgets["bottom_notebook"].append_page(page, label)
        self.bottom_info[Note] = {
            "fields_used": ["date", "user", "category", "note"],
            "tree": page.get_children()[0],
            "label": label,
            "name": _("Notes"),
        }
        self.widgets.notes_treeview.connect("row-activated", self.on_note_row_activated)
        logger.debug("exiting add_notes_page_to_bottom_notebook")

    def on_note_row_activated(self, tree, path, column) -> None:
        logger.debug("entering on_note_row_activated")
        try:
            # retrieve the selected row from the results view (we know it's
            # one), and we only need it's domain name
            selected = self.get_selected_values()[0]
            domain = selected.__class__.__name__.lower()
            # retrieve the activated row
            row = tree.get_model()[path]
            # construct the query
            query = f"{domain} where notes[category='{row[2]}'].note='{row[3]}'"
            # fire it
            safe_set_text(bauble.gui.widgets.main_comboentry.child, query)
            bauble.gui.widgets.go_button.emit("clicked")
        except Exception as e:
            logger.debug(f"{type(e)}({e})")

    def add_page_to_bottom_notebook(self, bottom_info) -> None:
        """add notebook page for a plugin class"""
        logger.debug("entering add_page_to_bottom_notebook")
        # 1: get the intended content page
        builder = utils.BuilderWidgets(bottom_info["glade_name"])
        page = builder[bottom_info["page_widget"]]
        # 2: detach the page from parent (its container)
        builder.remove_parent(page)
        # 3: create the label object
        label = Gtk.Label(label=bottom_info["name"])
        # 4: append the page to the bottom notebook
        self.widgets["bottom_notebook"].append_page(page, label)
        # 5: store the values for later use
        bottom_info["tree"] = page.get_children()[0]
        bottom_info["label"] = label
        logger.debug("exiting add_page_to_bottom_notebook")

    def update_bottom_notebook(self) -> None:
        """
        Update the bottom_notebook from the currently selected row.

        bottom_notebook has one page per type of information. Every page
        is registered by its plugin, which adds an entry to the
        dictionary self.bottom_info.

        the GtkNotebook pages are ScrolledWindow containing a TreeView,
        this should have a model, and the ordered names of the fields to
        be stored in the model is in bottom_info['fields_used'].

        """
        logger.debug("update_bottom_notebook - entering")
        values = self.get_selected_values()
        # Only one should be selected
        if values is None or len(values) != 1:
            logger.debug("update_bottom_notebook - need one single row")
            self.view.widget_set_visible("bottom_notebook", False)
            return

        self.view.widget_set_visible("bottom_notebook", True)
        row = values[0]  # the selected row
        logger.debug(
            f"update_bottom_notebook - for {type(row).__name__}({row})"
        )

        # loop over bottom_info plugin classes (eg: Tag)
        for klass, bottom_info in list(self.bottom_info.items()):
            logger.debug(
                f"update_bottom_notebook - for {klass.__name__}({bottom_info})"
            )
            if "label" not in bottom_info:  # late initialization
                self.add_page_to_bottom_notebook(bottom_info)
            label = bottom_info["label"]
            if not hasattr(klass, "attached_to"):
                logging.warning(f"class {klass} does not implement attached_to")
                continue
            objs = klass.attached_to(row)
            model = bottom_info["tree"].get_model()
            model.clear()
            if len(objs) == 0:
                label.set_property("use_markup", False)
                label.set_label(bottom_info["name"])
            else:
                label.set_property("use_markup", True)
                label.set_label("<b>{}</b>".format(bottom_info["name"]))
                for obj in objs:
                    model.append(
                        [f"{getattr(obj, k)}" for k in bottom_info["fields_used"]]
                    )
            logger.debug(f"done {len(objs)} for {klass.__name__}")
        logger.debug("update_bottom_notebook - exiting")

    def update_infobox(self) -> None:
        """
        Sets the infobox according to the currently selected row.
        no infobox is shown if nothing is selected
        """

        def set_infobox_from_row(row):
            """implement the logic for update_infobox"""

            logger.debug(f"set_infobox_from_row: {row} --  {repr(row)}")
            # remove the current infobox if there is one and it is not needed
            if row is None:
                if self.infobox is not None and self.infobox.get_parent() == self.pane:
                    self.pane.remove(self.infobox)
                return

            new_infobox = None
            selected_type = type(row)

            # if we have already created an infobox of this type:
            if selected_type in list(self.infobox_cache.keys()):
                new_infobox = self.infobox_cache[selected_type]
            # if selected_type defines an infobox class:
            elif (
                selected_type in self.row_meta
                and self.row_meta[selected_type].infobox is not None
            ):
                logger.debug(
                    f"{selected_type} defines infobox class {self.row_meta[selected_type].infobox}"
                )
                # it might be in cache under different name
                for ib in list(self.infobox_cache.values()):
                    if isinstance(ib, self.row_meta[selected_type].infobox):
                        logger.debug("found same infobox under different name")
                        new_infobox = ib
                # otherwise create one and put in the infobox_cache
                if not new_infobox:
                    logger.debug("not found infobox, we make a new one")
                    new_infobox = self.row_meta[selected_type].infobox()
                self.infobox_cache[selected_type] = new_infobox
            logger.debug(
                f"created or retrieved infobox {type(new_infobox)} {new_infobox}"
            )

            # remove any old infoboxes connected to the pane
            if self.infobox is not None and type(self.infobox) != type(new_infobox):
                if self.infobox.get_parent() == self.pane:
                    self.pane.remove(self.infobox)

            # update the infobox and put it in the pane
            self.infobox = new_infobox
            if self.infobox is not None:
                self.pane.pack2(self.infobox, resize=False, shrink=True)
                self.pane.show_all()
                self.infobox.update(row)

        # start of update_infobox
        logger.debug("update_infobox")
        values = self.get_selected_values()
        if not values:
            set_infobox_from_row(None)
            return
        if not values[0]:
            set_infobox_from_row(None)
            return

        if object_session(values[0]) is None:
            logger.debug("cannot populate info box from detached object")
            return

        try:
            set_infobox_from_row(values[0])
        except Exception as e:
            # if an error occurrs, log it and empty infobox.
            logger.debug(f"SearchView.update_infobox: {e}")
            logger.debug(traceback.format_exc())
            logger.debug(values)
            set_infobox_from_row(None)

    def get_selected_values(self):
        """
        Return the values in all the selected rows.
        """
        model, rows = self.results_view.get_selection().get_selected_rows()
        if model is None:
            return None
        return [model[row][0] for row in rows]

    def on_cursor_changed(self, view):
        """
        Called when selection changes
        """
        self.update_infobox()
        self.update_bottom_notebook()

        pictures_view.floating_window.set_selection(self.get_selected_values())

        for accel, cb in self.installed_accels:
            r = self.accel_group.disconnect_key(accel[0], accel[1])
            if not r:
                logger.warning(f"Callback not removed: {cb}")

        self.installed_accels = []
        selected = self.get_selected_values()
        if not selected:
            return
        selected_type = type(selected[0])

        for action in self.row_meta[selected_type].actions:
            enabled = (len(selected) > 1 and action.multiselect) or (
                len(selected) <= 1 and action.singleselect
            )
            if not enabled:
                continue
            keyval, mod = Gtk.accelerator_parse(action.accelerator)
            if (keyval, mod) != (0, 0):

                def cb(func):
                    def _impl(*args):
                        sel = self.get_selected_values()
                        if func(sel):
                            self.update()

                    return _impl

                self.accel_group.connect(
                    keyval, mod, Gtk.AccelFlags.VISIBLE, cb(action.callback)
                )
                self.installed_accels.append(((keyval, mod), action.callback))

    nresults_statusbar_context: str = "searchview.nresults"

    def search(self, text):
        """
        Search the database using the provided text.

        This function updates the search results view with matches found in the database.
        It also ensures that error handling and status messages are properly managed.
        """
        logger.debug("SearchView.search(%s)", text)

        # Stop any currently running search operations
        self.cancel_threads()

        # Ensure the session is properly handled
        try:
            if self.session.in_transaction():
                self.session.rollback()  # Rollback any pending transactions
        except Exception as e:
            logger.warning("Failed to rollback session: %s", e)
            self.session = db.Session()  # Reinitialize session if rollback fails

        # Prepare variables
        error_msg = None
        error_details_msg = None
        results = []
        bold = "<b>%s</b>"

        try:
            # Perform the search query
            results = search.search(text, self.session)
            from collections import Counter
            print("🔎 UI received", len(results), "results")
            print("🔎 by class:", Counter(type(r).__name__ for r in results))
            if results:
                first = next(iter(results))
                print("🔎 sample:", type(first), getattr(first, "id", None), getattr(first, "epithet", None))
                
        except ParseException as err:
            error_msg = _("Error in search string at column %s") % err.column
        except (BaubleError, AttributeError, Exception, SyntaxError) as e:
            logger.debug(traceback.format_exc())
            error_msg = _("** Error: %s") % utils.xml_safe(e)
            error_details_msg = utils.xml_safe(traceback.format_exc())

        # Handle errors and display them if needed
        if error_msg:
            bauble.gui.show_error_box(error_msg, error_details_msg)
            return

        # Clear previous results and update the info box
        utils.clear_model(self.results_view)
        self.update_infobox()

        # Get status bar context
        statusbar = bauble.gui.widgets.statusbar
        sbcontext_id = statusbar.get_context_id("searchview.nresults")
        statusbar.pop(sbcontext_id)

        # Handle the case when no results are found
        if not results:
            model = Gtk.ListStore(str)
            msg = bold % html.escape(
                _('Couldn\'t find anything for search: "%s"') % text
            )
            model.append([msg])
            self.results_view.set_model(model)
            return

        # Check if the result set is too large
        if len(results) > 5000:
            msg = _(
                "This query returned %s results. It may take a long time to process. "
                "Are you sure you want to continue?"
            ) % len(results)
            if not utils.yes_no_dialog(msg):
                return

        # Update the status bar
        statusbar.push(
            sbcontext_id,
            _("Retrieving %s search results…") % len(results),
        )

        # Initialize a tree model for results
        model = Gtk.TreeStore(object)
        def cmp(model, it1, it2, _data):
            a = model.get_value(it1, 0)
            b = model.get_value(it2, 0)
            a = str(a) if not isinstance(a, str) else a
            b = str(b) if not isinstance(b, str) else b
            return (a > b) - (a < b)

        model.set_default_sort_func(cmp)
        model.set_sort_column_id(Gtk.TREE_SORTABLE_DEFAULT_SORT_COLUMN_ID,
                         Gtk.SortType.ASCENDING)

        # Clear the model and update the results view
        utils.clear_model(self.results_view)
        self.results_view.set_model(model)

        # Start a thread to populate results asynchronously
        self.idle_start_thread(PopulateResults, self, results)

        # Update the bottom notebook with additional details
        self.update_bottom_notebook()

    def remove_children(self, model, parent) -> None:
        """
        Remove all children of some parent in the model, reverse
        iterate through them so you don't invalidate the iter
        """
        while model.iter_has_child(parent):
            nkids = model.iter_n_children(parent)
            child = model.iter_nth_child(parent, nkids - 1)
            model.remove(child)

    def on_test_expand_row(self, view, treeiter, path, data: Optional[Any] = None):
        """
        Look up the table type of the selected row and if it has
        any children then add them to the row
        """
        model = view.get_model()
        row = model.get_value(treeiter, 0)

        # Make sure row is attached to this view's session before touching relationships
        if object_session(row) is None:
            row = self.session.merge(row, load=False)
            model.set_value(treeiter, 0, row)

        self.remove_children(model, treeiter)
        try:
            kids = self.row_meta[type(row)].get_children(row)
            if len(kids) == 0:
                return True
        except saexc.InvalidRequestError as e:
            logger.debug(utils.to_unicode(e))
            model = self.results_view.get_model()
            for found in utils.search_tree_model(model, row):
                model.remove(found)
            return True
        except Exception as e:
            logger.debug(utils.to_unicode(e))
            logger.debug(traceback.format_exc())
            return True
        else:
            self.append_children(model, treeiter, sorted(kids, key=utils.natsort_key))
            return False

    def append_children(self, model, parent, kids):
        """
        append object to a parent iter in the model

        :param model: the model the append to
        :param parent:  the parent Gtk.TreeIter
        :param kids: a list of kids to append
        @return: the model with the kids appended
        """
        check(parent is not None, "append_children(): need a parent")
        for k in kids:
            i = model.append(parent, [k])
            if self.row_meta[type(k)].children is not None:
                model.append(i, ["_dummy"])
        return model

    def cell_data_func(self, col, cell, model, treeiter, data: Optional[Any] = None) -> None:
        # start with a (redundant) check, whether the cell is visible.
        path = model.get_path(treeiter)
        tree_rect = self.results_view.get_visible_rect()
        cell_rect = self.results_view.get_cell_area(path, col)
        if cell_rect.y > tree_rect.height:
            return
        # now update the the cell
        value = model[treeiter][0]
        # logger.debug('TBR: far too detailed, please do not keep us here')
        # logger.debug('TBR: %s' % value)
        if isinstance(value, str):
            cell.set_property("markup", value)
        else:
            # if the value isn't part of a session then add it to the
            # view's session so that we can access its child
            # properties...this usually happens when one of the
            # ViewMeta's get_children() functions return a list of
            # object whose session was closed...we add it here for
            # performance reasons so we only add it once it's visible
            if not object_session(value):
                if value in self.session:
                    # expire the object in the session with the same key
                    self.session.expire(value)
                else:
                    self.session.merge(value)
            try:
                r = value.search_view_markup_pair()
                # logger.debug('TBR: %s' % str(r))
                try:
                    main, substr = r
                except:
                    main = r
                    substr = f"({type(value).__name__})"
                cell.set_property(
                    "markup",
                    f"{_mainstr_tmpl % utils.to_unicode(main)}\n{_substr_tmpl % utils.to_unicode(substr)}",
                )

            except (saexc.InvalidRequestError, TypeError) as e:
                logger.warning(
                    f"bauble.view.SearchView.cell_data_func(): \n({type(e)}){e}"
                )

                def remove():
                    model = self.results_view.get_model()
                    self.results_view.set_model(None)  # detach model
                    for found in utils.search_tree_model(model, value):
                        model.remove(found)
                    self.results_view.set_model(model)

                GLib.idle_add(remove)

            except Exception as e:
                logger.error(
                    f"bauble.view.SearchView.cell_data_func(): \n({type(e)}){e}"
                )
                raise

    def get_expanded_rows(self):
        """
        return all the rows in the model that are expanded
        """
        expanded_rows = []

        def expand(view, path):
            return expanded_rows.append(Gtk.TreeRowReference(view.get_model(), path))

        self.results_view.map_expanded_rows(expand)
        # seems to work better if we passed the reversed rows to
        # self.expand_to_all_refs
        expanded_rows.reverse()
        return expanded_rows

    def expand_to_all_refs(self, references) -> None:
        """
        :param references: a list of TreeRowReferences to expand to

        Note: This method calls get_path() on each
        Gtk.TreeRowReference in <references> which apparently
        invalidates the reference.
        """
        for ref in references:
            if ref.valid():
                self.results_view.expand_to_path(ref.get_path())

    def on_view_button_release(self, view, event, data: Optional[Any] = None):
        """right-mouse-button release.

        Popup a context menu on the selected row.
        """
        if event.get_button() != 3:  # 1. issue_gdkevent_structs
            return False  # if not right click then leave

        selected = self.get_selected_values()
        if not selected:
            return
        selected_types = set(map(type, selected))
        if len(selected_types) > 1:
            # issue #31: currently we only show the menu when all objects
            # are of the same type. we could also show a common menu in case
            # the selection is of different types.
            return False
        selected_type = selected_types.pop()

        if not self.row_meta[selected_type].actions:
            # no actions
            return True

        # issue #31: ** important ** we need a common menu for all types
        # that can be merged with the specific menu for the selection,
        # e.g. provide a menu with a "Tag" action so you can tag
        # everything...or we could just ignore this and add "Tag" to all of
        # our action lists
        menu = None
        try:
            menu = self.context_menu_cache[selected_type]
        except KeyError:
            menu = Gtk.Menu()
            for action in self.row_meta[selected_type].actions:
                logger.debug(f"path: {action.get_accel_path()}")
                item = action.create_menu_item()

                def on_activate(item, cb):
                    result = False
                    try:
                        # have to get the selected values again here
                        # because for some unknown reason using the
                        # "selected" variable from the parent scope
                        # will give us the objects but they won't be
                        # in an session...maybe it's a thread thing
                        values = self.get_selected_values()
                        result = cb(values)
                    except Exception as e:
                        msg = utils.xml_safe(str(e))
                        tb = utils.xml_safe(traceback.format_exc())
                        utils.message_details_dialog(msg, tb, Gtk.MessageType.ERROR)
                        logger.warning(traceback.format_exc())
                    if result:
                        self.update()

                item.connect("activate", on_activate, action.callback)
                menu.append(item)
            self.context_menu_cache[selected_type] = menu

        # enable/disable the menu items depending on the selection
        for action in self.row_meta[selected_type].actions:
            action.enabled = (len(selected) > 1 and action.multiselect) or (
                len(selected) <= 1 and action.singleselect
            )

        # (parent_menu_shell, parent_menu_item, func, data, button, activate_time)
        menu.popup(
            None, None, None, None, event.get_button(), event.time
        )  # 1. issue_gdkevent_structs
        return True

    def update(self) -> None:
        """
        Expire all the children in the model, collapse everything,
        reexpand the rows to the previous state where possible and
        update the infobox.
        """
        logger.debug("SearchView::update")
        model, paths = self.results_view.get_selection().get_selected_rows()
        ref = None
        try:
            # try to get the reference to the selected object, if the
            # object has been deleted then we won't try to reselect it later
            ref = Gtk.TreeRowReference(model, paths[0])
        except:
            pass

        self.session.expire_all()

        # the invalidate_str_cache() method are specific to Species
        # and Accession right now....it's a bit of a hack since there's
        # no real interface that the method complies to...but it does
        # fix our string caching issues
        def invalidate_cache(model, path, treeiter, data=None):
            obj = model[path][0]
            if hasattr(obj, "invalidate_str_cache"):
                obj.invalidate_str_cache()

        model.foreach(invalidate_cache)
        expanded_rows = self.get_expanded_rows()
        self.results_view.collapse_all()
        # expand_to_all_refs will invalidate the ref so get the path first
        if not ref:
            return
        path = None
        if ref.valid():
            path = ref.get_path()
        self.expand_to_all_refs(expanded_rows)
        self.results_view.set_cursor(path)

    def on_view_row_activated(self, view, path, column, data: Optional[Any] = None) -> None:
        """
        expand the row on activation
        """
        logger.debug(
            f"SearchView::on_view_row_activated {view} {path} {column} {data}"
        )
        view.expand_row(path, False)

    def create_gui(self):
        """
        Creates the user interface for the SearchView.
        """
        logger.debug("SearchView::create_gui")

        # Get the results view widget
        self.results_view = self.widgets.results_treeview
        self.results_view.set_headers_visible(False)

        # Set selection mode and enable rubber banding
        selection = self.results_view.get_selection()
        selection.set_mode(Gtk.SelectionMode.MULTIPLE)
        self.results_view.set_rubber_banding(True)

        # Configure column renderer for displaying search results
        renderer = Gtk.CellRendererText()
        renderer.set_fixed_height_from_font(2)
        renderer.set_property("ellipsize", Pango.EllipsizeMode.END)

        column = Gtk.TreeViewColumn("Name", renderer)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column.set_cell_data_func(renderer, self.cell_data_func)
        self.results_view.append_column(column)

        # View event connections
        self.results_view.connect("cursor-changed", self.on_cursor_changed)
        self.results_view.connect("test-expand-row", self.on_test_expand_row)
        self.results_view.connect("button-release-event", self.on_view_button_release)
        self.results_view.connect("row-activated", self.on_view_row_activated)

        # Handle right-click to prevent deselecting multiple items
        def on_press(view, event):
            """
            Ignores right-click selection to prevent unintended deselection.

            This ensures that users can open the context menu without losing their
            current selection when using a right-click.
            """
            if (
                event.get_button() == Gdk.BUTTON_SECONDARY
            ):  # Right-click  # 1. issue_gdkevent_structs
                if (event.get_state() & Gdk.ModifierType.CONTROL_MASK) == 0:
                    path_info = view.get_path_at_pos(
                        int(event.get_x()), int(event.get_y())
                    )  # 1. issue_gdkevent_structs
                    if path_info:
                        path, _, _, _ = path_info
                        if not view.get_selection().path_is_selected(path):
                            return False
                return True
            return False

        self.results_view.connect("button-press-event", on_press)

        # Initialize accelerator group for key bindings
        self.accel_group = Gtk.AccelGroup()
        self.installed_accels = []

        # Assign panes and UI elements
        self.pane = self.widgets.search_hpane
        self.picpane = self.widgets.search_h2pane

        # Retrieve and reparent the main search UI container
        vbox = self.widgets.search_vbox
        self.widgets.remove_parent(vbox)

        # Pack the search UI into the main interface
        self.pack_start(vbox, expand=True, fill=True, padding=0)

    def on_notes_size_allocation(self, treeview, allocation, column, cell) -> None:
        """
        Set the wrap width according to the widgth of the treeview
        """
        # This code came from the PyChess project
        otherColumns = (c for c in treeview.get_columns() if c != column)
        newWidth = allocation.width - sum(c.get_width() for c in otherColumns)
        newWidth -= treeview.style_get_property("horizontal-separator") * 2
        if cell.get_property("wrap-width") == newWidth or newWidth <= 0:
            return
        cell.set_property("wrap-width", newWidth)
        store = treeview.get_model()
        treeiter = store.get_iter_first()
        while treeiter and store.iter_is_valid(treeiter):
            store.row_changed(store.get_path(treeiter), treeiter)
            treeiter = store.iter_next(treeiter)
            treeview.set_size_request(0, -1)


class Note:
    """temporary patch before we implement Notes as a plugin"""

    @classmethod
    def attached_to(cls, obj):
        """return the list of notes connected to obj"""

        try:
            return obj.notes
        except:
            return []


class AppendThousandRows(threading.Thread):

    __stopped: Any
    view: Any
    def callback(self, rows) -> None:
        for row in rows:
            self.view.add_row(row)

    def cancel_callback(self) -> None:
        row = ["---"] * 6
        row[4] = "** " + _("interrupted") + " **"
        self.view.liststore.append(row)

    def __init__(self, view, group: Optional[Any] = None, verbose: Optional[Any] = None, **kwargs) -> None:
        super().__init__(group=group, target=None, name=None)
        self.__stopped = threading.Event()
        self.view = view

    def cancel(self) -> None:
        self.__stopped.set()

    def run(self) -> None:
        session = db.Session()
        q = session.execute(
            select(db.History).order_by(db.History.timestamp.desc())
        ).scalars()
        # add rows in small batches
        offset = 0
        step = 200
        # Query to count rows in the History table
        count = session.scalar(select(func.count()).select_from(db.History))

        while offset < count and not self.__stopped.isSet():
            rows = q.offset(offset).limit(step).all()
            GLib.idle_add(self.callback, rows)
            offset += step
        session.close()
        if offset < count:
            GLib.idle_add(self.cancel_callback)


class HistoryView(pluginmgr.View):
    """Show the tables row in the order they were last updated"""
    liststore: Any
    TVC_TIMESTAMP: int = 0
    TVC_OPERATION: int = 1
    TVC_USER: int = 2
    TVC_TABLE: int = 3
    TVC_USER_FRIENDLY: int = 4
    TVC_DICT: int = 5

    def __init__(self) -> None:
        logger.debug("PrefsView::__init__")
        super().__init__(
            filename=os.path.join(paths.lib_dir(), "bauble.glade"),
            root_widget_name="history_window",
        )
        self.view.connect_signals(self)
        self.liststore = self.view.widgets.history_ls
        apply_css()
        self.update()

    @staticmethod
    def key_for_item(v):
        key, value = v
        return (key != "id", value is None, key)

    @staticmethod
    def show_typed_value(v):
        try:
            eval(v)
            return v
        except:
            return f"»{v}«"

    def add_row(self, item) -> None:
        d = eval(item.values)
        del d["_created"]
        del d["_last_updated"]
        friendly = ", ".join(
            f"{k}: {self.show_typed_value(v)}"
            for k, v in sorted(list(d.items()), key=HistoryView.key_for_item)
        )
        self.liststore.append(
            [
                (f"{item.timestamp}")[:19],
                item.operation,
                item.user,
                item.table_name,
                friendly,
                item.values,
            ]
        )

    def on_row_activated(self, tree, path, column) -> None:
        row = self.liststore[path]
        dic = eval(row[self.TVC_DICT])
        table = row[self.TVC_TABLE]
        obj_id = int(dic["id"])
        for table_name, equivalent, key in [
            ("genus_note", "genus", "genus_id"),
            ("species_note", "species", "species_id"),
            ("location_note", "location", "location_id"),
            ("accession_note", "accession", "accession_id"),
            ("plant_note", "plant", "plant_id"),
            ("genus_synonym", "genus", "genus_id"),
            ("species_synonym", "species", "species_id"),
            ("vernacular_name", "species", "species_id"),
            ("default_vernacular_name", "species", "species_id"),
            ("plant_change", "plant", "plant_id"),
        ]:
            if table == table_name:
                table = equivalent
                obj_id = int(dic[key])
        mapper_search = search.get_strategy("MapperSearch")
        if table in mapper_search._domains:
            query = f"{table} where id={obj_id}"
            safe_set_text(bauble.gui.widgets.main_comboentry.get_child(), query)
            bauble.gui.widgets.go_button.emit("clicked")

    def update(self) -> None:
        """
        Add the history items to the view.
        """
        self.liststore.clear()
        self.start_thread(AppendThousandRows(self))


class HistoryCommandHandler(pluginmgr.CommandHandler):

    command: str = "history"
    view: Any = None

    def __init__(self) -> None:
        super().__init__()

    def get_view(self):
        if not self.view:
            self.__class__.view = HistoryView()
        return self.view

    def __call__(self, cmd, arg) -> None:
        self.view.update()


pluginmgr.register_command(HistoryCommandHandler)


def select_in_search_results(obj):
    """
    :param obj: the object the select
    @returns: a Gtk.TreeIter to the selected row

    Search the tree model for obj if it exists then select it if not
    then add it and select it.

    The the obj is not in the model then we add it.
    """
    check(obj is not None, "select_in_search_results: arg is None")
    view = bauble.gui.get_view()
    if not isinstance(view, SearchView):
        return None
    logger.debug(
        f"select_in_search_results {obj} is in session {obj in view.session}"
    )
    model = view.results_view.get_model()
    found = utils.search_tree_model(model, obj)
    row_iter = None
    if len(found) > 0:
        row_iter = found[0]
    else:
        row_iter = model.append(None, [obj])
        model.append(row_iter, ["-"])
    view.results_view.set_cursor(model.get_path(row_iter))
    return row_iter


class DefaultCommandHandler(pluginmgr.CommandHandler):

    def __init__(self) -> None:
        super().__init__()

    command: Any = [None]
    view: Any = None

    def get_view(self):
        if self.__class__.view is None:
            self.__class__.view = SearchView()
        return self.__class__.view

    def __call__(self, cmd, arg) -> None:
        self.view.search(arg)
