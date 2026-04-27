#
# Copyright (c) 2005,2006,2007,2008,2009 Brett Adams <brett@belizebotanic.org>
# Copyright (c) 2015-2016 Mario Frasca <mario@anche.no>
# Copyright 2017 Jardín Botánico de Quito
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
# utils module
#
# A common set of utility functions used throughout Ghini.
#
import base64
import datetime
import logging
import os
import re
import threading
import traceback
from collections.abc import Generator

# import xml.sax.saxutils as saxutils
from gettext import gettext as _
from logging import Logger
from typing import Any, Optional

import bauble
import dateutil.parser
import sqlalchemy
from bauble import paths as paths
from bauble import utils as utils
from bauble.error import check
from bauble.gtkinit import Gdk, GdkPixbuf, GLib, GObject, Gtk

# from sqlalchemy.exc import DBAPIError
from sqlalchemy import distinct, select
from sqlalchemy.orm.session import object_session

logger: Logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _install_css(css: str) -> None:

    from bauble.gtkinit import Gdk, Gtk

    provider = Gtk.CssProvider()
    provider.load_from_data(css.encode("utf-8"))
    # For GTK 3
    screen = Gdk.Screen.get_default()
    Gtk.StyleContext.add_provider_for_screen(
        screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )


def get_object_session(obj):
    """Get the SQLAlchemy session for a given object."""
    return object_session(obj)


def add_to_relationship(parent, child, relationship_name) -> None:
    """Add a child object to a parent's relationship."""
    relationship = getattr(parent, relationship_name, None)
    if relationship is not None:
        relationship.append(child)


def remove_from_relationship(parent, child, relationship_name) -> None:
    """Remove a child object from a parent's relationship."""
    relationship = getattr(parent, relationship_name, None)
    if relationship is not None and child in relationship:
        relationship.remove(child)


def get_column_value(obj, column_name):
    """Get the value of a specific column in an object."""
    return getattr(obj, column_name, None)


def set_column_value(obj, column_name, value) -> None:
    """Set the value of a specific column in an object."""
    setattr(obj, column_name, value)


def sorted_relationship(relationship, key):
    """Return a sorted list of a relationship by a specific key."""
    return sorted(relationship, key=lambda x: getattr(x, key, None))


def handle_deletion_error(e) -> None:
    """Handle errors specific to deletion."""
    if isinstance(e, sqlalchemy.exc.IntegrityError):
        message = _(
            "Could not delete: The item is referenced elsewhere (foreign key constraint)."
        )
    elif isinstance(e, sqlalchemy.orm.exc.UnmappedInstanceError):
        message = _("Could not delete: The item is not managed by the session.")
    elif isinstance(e, sqlalchemy.exc.InvalidRequestError):
        message = _("Could not delete: The request was invalid.")
    else:
        message = _("Could not delete the item. Unknown error.")

    details = traceback.format_exc()
    utils.message_details_dialog(message, details, Gtk.MessageType.ERROR)


def handle_generic_error(e) -> None:
    """Handle database-specific errors."""
    if isinstance(e, sqlalchemy.exc.IntegrityError):
        message = _("Integrity error: Check constraints or data conflicts.")
    elif isinstance(e, sqlalchemy.exc.OperationalError):
        message = _("Operational error: Database operation failed.")
    elif isinstance(e, sqlalchemy.exc.ProgrammingError):
        message = _("Programming error: Syntax or command issue.")
    else:
        message = _("Database error occurred.")

    details = traceback.format_exc()
    utils.message_details_dialog(message, details, Gtk.MessageType.ERROR)


def handle_db_error(exception, context: str = "database operation") -> None:
    """
    Handle database-specific errors.

    :param exception: The exception instance raised during the operation.
    :param context: Description of the operation (e.g., "deletion").
    """
    import traceback

    if isinstance(exception, sqlalchemy.exc.IntegrityError):
        message = _(
            f"Integrity error during {context}: Check constraints or data conflicts."
        )
    elif isinstance(exception, sqlalchemy.exc.OperationalError):
        message = _(f"Operational error during {context}: Database operation failed.")
    elif isinstance(exception, sqlalchemy.exc.ProgrammingError):
        message = _(f"Programming error during {context}: Syntax or command issue.")
    else:
        message = _(f"An unknown error occurred during {context}.")

    details = traceback.format_exc()
    utils.message_details_dialog(message, details, Gtk.MessageType.ERROR)


def count_relationship_items(obj, relationship_name):
    """Count the number of items in a relationship."""
    relationship = getattr(obj, relationship_name, None)
    if relationship is not None:
        return len(relationship)
    return 0


def safe_set_text(gtk_widget, text) -> None:
    """
    Sets the text of a Gtk widget, replacing None with an empty string
    and converting bytes to UTF-8 strings.

    :param gtk_widget: Instance of a Gtk widget
    :param text: The text to set, which may be None or bytes
    """
    try:
        if text is None:
            text = ""
        elif isinstance(text, bytes):
            text = text.decode("utf-8", errors="replace")  # Safely decode bytes
        elif not isinstance(text, str):
            text = str(text)  # Ensure it's a string
        gtk_widget.set_text(text)
    except AttributeError as e:
        raise TypeError(f"Invalid widget or text: {gtk_widget}, {text}") from e


def safe_set_props(widget, prop, value) -> None:
    """
    Safely set a property of a widget.

    Args:
        widget: The widget whose property needs to be set.
        prop: The name of the property to set (e.g., 'text', 'label').
        value: The value to set, can be a string, bytes, or None.
    """
    if value is None:
        value = ""
    elif isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    else:
        value = str(value)

    # Check if the widget has a specific method for the property
    setter_method = f"set_{prop}"
    if hasattr(widget, setter_method):
        # Use the set_<property> method if it exists
        getattr(widget, setter_method)(value)
    else:
        # Fallback to set_property for dynamic property setting
        widget.set_property(prop, value)


def read_in_chunks(file_object, chunk_size: int = 1024) -> Generator[Any, None, None]:
    """read a chunk from a stream

    Lazy function (generator) to read piece by piece from a file-like object.
    Default chunk size: 1k."""
    while True:
        data = file_object.read(chunk_size)
        if not data:
            break
        yield data


class Cache:
    """a simple class for caching images

    you instantiate a size 10 cache like this:
    >>> cache = ImageCache(10)

    if `getter` is a function that returns a picture, you don't immediately
    invoke it, you use the cache like this:
    >>> image = cache.get(name, getter)

    internally, the cache is stored in a dictionary, the key is the name of
    the image, the value is a pair with first the timestamp of the last usage
    of that key and second the value.
    """

    size: int
    storage: dict[str, Any]

    def __init__(self, size) -> None:
        self.size = size
        self.storage = {}

    def get(self, key, getter, on_hit=lambda x: None):
        if key in self.storage:
            value = self.storage[key][1]
            on_hit(value)
        else:
            value = getter()
            if len(self.storage) == self.size:
                # remove the oldest entry
                k = min(
                    list(
                        zip(
                            list(self.storage.values()),
                            list(self.storage.keys()),
                        )
                    )
                )[1]
                del self.storage[k]
        import time

        self.storage[key] = time.time(), value
        return value


def copy_picture_with_thumbnail(path, basename: Optional[Any] = None):
    """copy file from path to picture_root, and make thumbnail, preserving name

    return base64 representation of thumbnail
    """
    import os.path

    if basename is None:
        filename = path
        path, basename = os.path.split(filename)
    else:
        filename = os.path.join(path, basename)
    from bauble import prefs

    if not filename.startswith(prefs.prefs[prefs.picture_root_pref]):
        import shutil

        shutil.copy(filename, prefs.prefs[prefs.picture_root_pref])
    # make thumbnail in thumbs subdirectory
    from PIL import Image

    full_dest_path = os.path.join(
        prefs.prefs[prefs.picture_root_pref], "thumbs", basename
    )
    result = ""
    try:
        im = Image.open(filename)
        im.thumbnail((400, 400))
        logger.debug(f"copying {filename} to {full_dest_path}")
        im.save(full_dest_path)
        from io import BytesIO

        output = BytesIO()
        im.save(output, format="JPEG")
        im_data = output.getvalue()
        result = base64.b64encode(im_data)
    except OSError:
        logger.warning("can't make thumbnail")
    except Exception as e:
        logger.warning("unexpected exception making thumbnail: " f"({type(e)}){e}")
    return result


class ImageLoader(threading.Thread):
    box: Any
    loader: Any
    inline_picture_marker: str
    reader_function: Any
    url: Any
    cache: Any = Cache(12)  # class-global cached results

    def __init__(self, box, url, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.box = box  # will hold image or label
        self.loader = GdkPixbuf.PixbufLoader()
        self.inline_picture_marker = "|data:image/jpeg;base64,"
        if url.find(self.inline_picture_marker) != -1:
            self.reader_function = self.read_base64
            self.url = url
        elif url[: url.find("/")] in ["http:", "https:", "file:"]:
            self.reader_function = self.read_global_url
            self.url = url
        else:
            self.reader_function = self.read_local_url
            from bauble import prefs

            pfolder = prefs.prefs[prefs.picture_root_pref]
            self.url = os.path.join(pfolder, url)

    def callback(self) -> None:
        pixbuf = self.loader.get_pixbuf()
        try:
            pixbuf = pixbuf.apply_embedded_orientation()
            scale_x = pixbuf.get_width() / 400
            scale_y = pixbuf.get_height() / 400
            scale = max(scale_x, scale_y, 1)
            x = int(pixbuf.get_width() / scale)
            y = int(pixbuf.get_height() / scale)
            scaled_buf = pixbuf.scale_simple(x, y, GdkPixbuf.InterpType.BILINEAR)
            if self.box.get_children():
                image = self.box.get_children()[0]
            else:
                image = Gtk.Image()
                self.box.add(image)
            image.set_from_pixbuf(scaled_buf)
        except (GLib.GError, AttributeError) as e:
            logger.debug(f"picture {self.url} caused {type(e).__name__} {e}")
            text = _("picture file %s not found.") % self.url
            label = Gtk.Label()
            safe_set_text(label, text)
            self.box.add(label)
        except Exception as e:
            logger.warning(f"picture {self.url} caused Exception {type(e)}:{e}")
            label = Gtk.Label()
            safe_set_text(label, f"{e}")
            self.box.add(label)
        self.box.show_all()

    def loader_notified(self, pixbufloader) -> None:
        GObject.idle_add(self.callback)

    def run(self) -> None:
        self.loader.connect("closed", self.loader_notified)
        self.cache.get(self.url, self.reader_function, on_hit=self.loader.write)
        try:
            self.loader.close()
        except GLib.GError:
            logger.debug(f"broken picture {self.url}")

    def read_base64(self):
        self.loader.connect("area-prepared", self.loader_notified)
        thumb64pos = self.url.find(self.inline_picture_marker)
        offset = thumb64pos + len(self.inline_picture_marker)
        import base64

        return base64.b64decode(self.url[offset:])

    def read_global_url(self):
        self.loader.connect("area-prepared", self.loader_notified)
        import contextlib
        import urllib.error
        import urllib.parse
        import urllib.request

        pieces = []
        with contextlib.closing(urllib.request.urlopen(self.url)) as f:
            for piece in read_in_chunks(f, 4096):
                self.loader.write(piece)
                pieces.append(piece)
        return b"".join(pieces)

    def read_local_url(self):
        self.loader.connect("area-prepared", self.loader_notified)
        pieces = []
        try:
            with open(self.url, "rb") as f:
                for piece in read_in_chunks(f, 4096):
                    self.loader.write(piece)
                    pieces.append(piece)
        except FileNotFoundError as e:
            logger.debug(f"picture {self.url} caused FileNotFoundError {e}")
        return b"".join(pieces)


def find_dependent_tables(table, metadata: Optional[Any] = None):
    """
    Return an iterator with all tables that depend on table.  The
    tables are returned in the order that they depend on each
    other. For example you know that table[0] does not depend on
    tables[1].

    :param table: The tables who dependencies we want to find

    :param metadata: The :class:`sqlalchemy.engine.MetaData` object
      that holds the tables to search through.  If None then use
      bauble.db.metadata
    """
    # NOTE: we can't use bauble.metadata.sorted_tables here because it
    # returns all the tables in the metadata even if they aren't
    # dependent on table at all
    from sqlalchemy.sql.util import sort_tables

    if metadata is None:
        import bauble.db as db

        metadata = db.metadata
    tables = []

    def _impl(t2):
        for tbl in metadata.sorted_tables:
            for fk in tbl.foreign_keys:
                if fk.column.table == t2 and tbl not in tables and tbl is not table:
                    tables.append(tbl)
                    _impl(tbl)

    _impl(table)
    return sort_tables(tables=tables)


class BuilderWidgets:
    """
    Provides dictionary and attribute access for a
    :class:`Gtk.Builder` object.
    """

    builder: Any

    def __init__(self, ui) -> None:
        """
        :params filename: a Gtk.Builder XML UI file
        """
        if isinstance(ui, str):
            self.builder = Gtk.Builder()
            self.builder.add_from_file(ui)
        else:
            self.builder = ui

    def __getitem__(self, name):
        """
        :param name:
        """
        w = self.builder.get_object(name)
        if not w:
            raise KeyError(
                _('no widget named "%(widget_name)s" in glade file')
                % {"widget_name": name}
            )
        return w

    def __getattr__(self, name):
        if name == "_builder_":
            return self.builder
        w = self.builder.get_object(name)
        if not w:
            raise KeyError(
                _('no widget named "%(widget_name)s" in glade file')
                % {"widget_name": name}
            )
        return w

    def remove_parent(self, w) -> None:
        """Remove widget (or wrapper) from its parent."""
        if isinstance(w, str):
            w = self.builder.get_object(w)

        # If it's a wrapper (e.g., MessageBox/GenericMessageBox), unwrap to the Gtk.Widget
        if hasattr(w, "get_widget"):
            try:
                inner = w.get_widget()
                # Only replace if it's actually a Gtk.Widget
                if isinstance(inner, Gtk.Widget):
                    w = inner
            except Exception:
                pass

        parent = w.get_parent()
        if parent is not None:
            parent.remove(w)

def tree_model_has(tree, value):
    """
    Return True or False if value is in the tree.
    """
    return len(search_tree_model(tree, value)) > 0


def search_tree_model(parent, data, cmp=lambda row, data: row[0] == data):
    """
    Return a iterable of Gtk.TreeIter instances to all occurences
    of data in model

    :param parent: a Gtk.TreeModel or a Gtk.TreeModelRow instance
    :param data: the data to look for
    :param cmp: the function to call on each row to check if it matches
     data, default is C{lambda row, data: row[0] == data}
    """
    if isinstance(parent, Gtk.TreeModel):
        if not parent.get_iter_first():  # model empty
            return []
        return search_tree_model(parent[parent.get_iter_first()], data, cmp)
    results = set()

    def func(model, path, iter, dummy=None):
        if cmp(model[iter], data):
            results.add(iter)
        return False

    parent.model.foreach(func)
    return tuple(results)


def clear_model(obj_with_model) -> None:
    """
    :param obj_with_model: a gtk Widget that has a Gtk.TreeModel that
      can be retrieved with obj_with_mode.get_model

    Remove the model from the object, deletes all the items in the
    model, clear the model and then delete the model and set the model
    on the object to None
    """
    model = obj_with_model.get_model()
    if model is None:
        return

    ncols = model.get_n_columns()

    def del_cb(model, path, iter, data=None):
        for c in range(0, ncols):
            v = model.get_value(iter, c)
            del v
        del iter

    model.foreach(del_cb)
    model.clear()
    del model
    obj_with_model.set_model(None)


def combo_set_active_text(combo, value) -> None:
    """
    does the same thing as set_combo_from_value but this looks more like a
    GTK+ method
    """
    set_combo_from_value(combo, value)


def set_combo_from_value(combo, value, cmp=lambda row, value: row[0] == value):
    """
    Find value in combo model and set it as active, else raise ValueError
    cmp(row, value) is the a function to use for comparison

    .. note:: if more than one value is found in the combo then the
      first one in the list is set
    """
    model = combo.get_model()
    matches = search_tree_model(model, value, cmp)
    if len(matches) == 0:
        raise ValueError(
            "set_combo_from_value() - could not find value in " f"combo: {value}"
        )
    combo.set_active_iter(matches[0])
    combo.emit("changed")


def combo_get_value_iter(combo, value, cmp=lambda row, value: row[0] == value):
    """
    Returns a Gtk.TreeIter that points to first matching value in the
    combo's model.

    :param combo: the combo where we should search
    :param value: the value to search for
    :param cmp: the method to use to compare rows in the combo model and value,
      the default is C{lambda row, value: row[0] == value}

    .. note:: if more than one value is found in the combo then the first one
      in the list is returned
    """
    model = combo.get_model()
    matches = search_tree_model(model, value, cmp)
    if len(matches) == 0:
        return None
    return matches[0]


def get_widget_value(w, index: int = 0):
    """
    :param w: an instance of Gtk.Widget
    :param index: the row index to use for those widgets who use a model

    .. note:: any values passed in for widgets that expect a string will call
      the values __str__ method
    """

    if isinstance(w, Gtk.Label):
        return w.get_text()
    elif isinstance(w, Gtk.TextView):
        textbuffer = w.get_buffer()
        return textbuffer.get_text(
            textbuffer.get_start_iter(), textbuffer.get_end_iter(), ""
        )
    elif isinstance(w, Gtk.Entry):
        text = w.get_text()
        if isinstance(text, bytes):
            return text.decode("utf-8")
        return text
    elif isinstance(w, Gtk.ComboBox):
        if w.get_child() and isinstance(w.get_child(), Gtk.Entry):
            return w.get_child().get_text()
        if w.get_model() is None or w.get_active_iter() is None:
            return None
        return w.get_model()[w.get_active_iter()][0]
    elif isinstance(w, (Gtk.ToggleButton, Gtk.CheckButton, Gtk.RadioButton)):
        return w.get_active()
    elif isinstance(w, Gtk.Button):
        return w.get_property("label")

    else:
        raise TypeError(
            "utils.set_widget_value(): Don't know how to handle "
            f"the widget type {type(w)} with name {w.name}"
        )


def set_widget_value(
    widget, value, markup: bool = False, default: Optional[Any] = None, index: int = 0
):
    """
    :param widget: an instance of Gtk.Widget
    :param value: the value to put in the widget
    :param markup: whether or not value is markup
    :param default: the default value to put in the widget if the value is None
    :param index: the row index to use for those widgets who use a model

    .. note:: any values passed in for widgets that expect a string will call
      the values __str__ method
    """

    logger.debug(
        f"(widget ›{widget}‹, value ›{value}‹, markup ›{markup}‹, default ›{default}‹, index ›{index}‹)"
    )

    if value is None:  # set the value from the default
        if isinstance(widget, (Gtk.Label, Gtk.TextView, Gtk.Entry)) and default is None:
            value = ""
        else:
            value = default

    # assume that if value is a date then we want to display it with
    # the default date format
    import bauble.prefs as prefs

    if isinstance(value, datetime.date):
        date_format = prefs.prefs[prefs.date_format_pref]
        value = value.strftime(date_format)

    if isinstance(widget, Gtk.Label):
        # safe_set_text(widget, str(value))
        # FIXME: some of the enum values that have <not set> as a values
        # will give errors here, but we can't escape the string because
        # if someone does pass something that needs to be marked up
        # then it won't display as intended, maybe BaubleTable.markup()
        # should be responsible for returning a properly escaped values
        # or we should just catch the error(is there an error) and call
        # set_text if set_markup fails
        if markup:
            widget.set_markup(str(value) or "")
        else:
            safe_set_text(widget, str(value) or "")
    elif isinstance(widget, Gtk.TextView):
        safe_set_text(widget.get_buffer(), f"{value}")
    elif isinstance(widget, Gtk.TextBuffer):
        safe_set_text(widget, f"{value}")
    elif isinstance(widget, Gtk.Entry):
        safe_set_text(widget, str(value) or "")
    elif isinstance(widget, Gtk.ComboBox):
        treeiter = None
        if not widget.get_model():
            logger.warning(
                f"utils.set_widget_value: impossible on ComboBox without a model: {Gtk.Buildable.get_name(widget)}"
            )
        else:
            treeiter = combo_get_value_iter(
                widget, value, cmp=lambda row, value: row[index] == value
            )
            if treeiter:
                logger.debug(f"value found in model at {treeiter}")
                widget.set_active_iter(treeiter)
            else:
                logger.debug("value not found in model")
                widget.set_active(-1)
        if widget.get_child():
            widget.get_child().text = value or ""
    elif isinstance(widget, (Gtk.ToggleButton, Gtk.CheckButton, Gtk.RadioButton)):
        if isinstance(widget, Gtk.CheckButton) and isinstance(value, str):
            value = value == Gtk.Buildable.get_name(widget)
        if value is True:
            widget.set_inconsistent(False)
            widget.set_active(True)
        elif value is False:  # why do we need unset `inconsistent` for False?
            widget.set_inconsistent(False)
            widget.set_active(False)
        else:  # treat None as False, we do not handle inconsistent cases.
            widget.set_inconsistent(False)
            widget.set_active(False)
    elif isinstance(widget, Gtk.Button):
        if value is None:
            widget.set_label("")
        else:
            widget.set_label(str(value))

    else:
        raise TypeError(
            "utils.set_widget_value(): Don't know how to handle "
            f"the widget type {type(widget)} with name {widget.name}"
        )


def none(function, *args) -> None:
    """invoke function but drop return value

    meant to be used in GObject.idle_add, so that the function is not placed
    back in the queue.

    instead of:
    GObject.idle_add(f, a1, a2, a3)

    use:
    GObject.idle_add(utils.none, f, a1, a2, a3)

    """

    function(*args)
    return None


def create_message_dialog(
    msg,
    type=Gtk.MessageType.INFO,
    buttons=Gtk.ButtonsType.OK,
    parent: Optional[Any] = None,
):
    """Create a message dialog, display and return it ready to be run.

    :param msg: The markup to use for the message. The value should be
      escaped in case it contains any HTML entities.
    :param type: A GTK message type constant.  The default is Gtk.MessageType.INFO.
    :param buttons: A GTK buttons type constant.  The default is
      Gtk.ButtonsType.OK.
    :param parent:  The parent window for the dialog

    Returns a :class:`Gtk.MessageDialog`
    """
    if parent is None:
        try:  # this might get called before bauble has started
            parent = bauble.gui.window
        except Exception:
            parent = None
    d = Gtk.MessageDialog(
        transient_for=parent,
        modal=True,
        message_type=type,
        buttons=buttons,
    )
    d.set_title("Ghini")
    d.set_markup(msg)
    d.set_destroy_with_parent(True)  # Ensures destruction with parent

    # Ensure the dialog is destroyed when the parent closes
    if parent is None:
        # If there is no parent, manually force modal behavior
        d.set_modal(False)  # Ensure dialog blocks input properly
        d.connect("response", lambda dialog, response: dialog.destroy())

    if d.get_icon() is None:
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(bauble.default_icon)
            d.set_icon(pixbuf)
        except Exception:
            pass
        d.set_property("skip-taskbar-hint", False)
    d.show_all()

    return d


def idle_message(
    msg,
    type=Gtk.MessageType.INFO,
    buttons=Gtk.ButtonsType.OK,
    parent: Optional[Any] = None,
) -> None:
    """create and run message_dialog in GUI thread, once."""

    def run_me():
        d = create_message_dialog(msg, type, buttons, parent)
        d.run()
        d.destroy()

    GObject.idle_add(run_me)


def message_dialog(
    msg,
    type=Gtk.MessageType.INFO,
    buttons=Gtk.ButtonsType.OK,
    parent: Optional[Any] = None,
):
    """Create and run a temporary MessageDialog.

    Create a message dialog with :func:`bauble.utils.create_message_dialog`
    and run and destroy it.

    Returns the dialog's response.
    """
    d = create_message_dialog(msg, type, buttons, parent)
    r = d.run()
    d.destroy()
    return r


def create_yes_no_dialog(
    msg, parent: Optional[Any] = None, buttons=Gtk.ButtonsType.YES_NO
):
    """
    Create a dialog with yes/no buttons.
    """
    if parent is None:
        try:  # this might get called before bauble has started
            parent = bauble.gui.window
        except Exception:
            parent = None

    d = Gtk.MessageDialog(
        transient_for=parent,
        modal=True,
        message_type=Gtk.MessageType.QUESTION,
        buttons=buttons,
    )
    d.set_title("Ghini")
    d.set_markup(msg)
    d.set_destroy_with_parent(True)  # Ensures dialog is destroyed with parent

    # Ensure the dialog is destroyed when the parent closes
    if parent is not None:
        parent.connect("destroy", lambda *_: d.destroy())

    if d.get_icon() is None:
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(bauble.default_icon)
            d.set_icon(pixbuf)
        except Exception:
            pass
        d.set_property("skip-taskbar-hint", False)
    d.show_all()
    return d


def yes_no_cancel_dialog(
    msg,
    yes_label,
    no_label,
    cancel_label,
    parent: Optional[Any] = None,
    callback: Optional[Any] = None,
) -> None:
    """
    Displays a dialog with Yes, No, and Cancel options.
    Returns a DialogResponse enum value.
    """
    try:  # This might get called before bauble has started
        parent = parent or bauble.gui.window
    except Exception:
        parent = None

    dialog = Gtk.MessageDialog(
        transient_for=parent,
        modal=True,
        message_type=Gtk.MessageType.QUESTION,
        buttons=Gtk.ButtonsType.NONE,
    )
    dialog.set_title("Ghini")
    dialog.set_markup(msg)
    dialog.set_destroy_with_parent(True)  # Ensure it is destroyed with parent

    dialog.add_button(yes_label, Gtk.ResponseType.YES)
    dialog.add_button(no_label, Gtk.ResponseType.NO)
    dialog.add_button(cancel_label, Gtk.ResponseType.CANCEL)

    def on_response(dlg, response):
        dlg.destroy()
        if callback:
            if response == Gtk.ResponseType.YES:
                callback(utils.DialogResponse.YES)
            elif response == Gtk.ResponseType.NO:
                callback(utils.DialogResponse.NO)
            else:
                callback(utils.DialogResponse.CANCEL)

    dialog.connect("response", on_response)
    dialog.show_all()


def yes_no_dialog(msg, parent: Optional[Any] = None, yes_delay: int = -1):
    """
    Create and run a yes/no dialog.

    Return True if the dialog response equals Gtk.ResponseType.YES

    :param msg: the message to display in the dialog
    :param parent: the dialog's parent
    :param yes_delay: the number of seconds before the yes button should
      become sensitive
    """
    d = create_yes_no_dialog(msg, parent)
    if yes_delay > 0:
        d.set_response_sensitive(Gtk.ResponseType.YES, False)

        def on_timeout():
            if d.get_property("visible"):  # conditional avoids GTK+ warning
                d.set_response_sensitive(Gtk.ResponseType.YES, True)
            return False

        from bauble.gtkinit import GObject

        GObject.timeout_add(yes_delay * 1000, on_timeout)
    r = d.run()
    d.destroy()
    return r == Gtk.ResponseType.YES


def create_message_details_dialog(
    msg,
    details,
    type=Gtk.MessageType.INFO,
    buttons=Gtk.ButtonsType.OK,
    parent: Optional[Any] = None,
):
    """
    Create a message dialog with a details expander.

    :param msg: The main message to display.
    :param details: Additional details for the expander.
    :param type: A GTK message type constant (default: Gtk.MessageType.INFO).
    :param buttons: A GTK buttons type constant (default: Gtk.ButtonsType.OK).
    :param parent: The parent window (optional).
    :return: A Gtk.MessageDialog instance.
    """

    if parent is None:
        try:  # This might get called before bauble has started
            parent = bauble.gui.window
        except Exception:
            parent = None

    d = Gtk.MessageDialog(
        transient_for=parent,
        modal=True,
        message_type=type,
        buttons=buttons,
    )

    d.set_title("Ghini")
    d.set_markup(msg)
    d.set_destroy_with_parent(True)  # Ensure it is destroyed with parent

    # Ensure dialog closes when parent is destroyed
    if parent is not None:
        parent.connect("destroy", lambda *_: d.destroy())

    # Ensure the dialog has a reasonable width
    from bauble.gtkinit import Pango

    context = d.get_pango_context()
    font_metrics = context.get_metrics(
        context.get_font_description(), context.get_language()
    )
    width = font_metrics.get_approximate_char_width()

    if width / Pango.SCALE * len(msg) < 300:
        d.set_size_request(300, -1)

    # Create a details expander
    expand = Gtk.Expander(label=_("Details"))
    expand.set_expanded(False)

    # Create a scrollable text view for details
    text_view = Gtk.TextView()
    text_view.set_editable(False)
    text_view.set_wrap_mode(Gtk.WrapMode.WORD)

    tb = Gtk.TextBuffer()
    safe_set_text(tb, (details or "")[:4096])
    text_view.set_buffer(tb)

    sw = Gtk.ScrolledWindow()
    sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    sw.set_size_request(-1, 200)
    sw.add(text_view)

    expand.add(sw)
    d.get_content_area().pack_start(expand, True, True, 0)

    # Set the default response to OK
    d.set_default_response(Gtk.ResponseType.OK)

    # Set the icon if not already set
    if d.get_icon() is None:
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(bauble.default_icon)
            d.set_icon(pixbuf)
        except Exception:
            pass
        d.set_property("skip-taskbar-hint", False)

    d.show_all()
    return d


def message_details_dialog(
    msg,
    details,
    type=Gtk.MessageType.INFO,
    buttons=Gtk.ButtonsType.OK,
    parent: Optional[Any] = None,
):
    """
    Create and run a message dialog with a details expander.
    """
    d = create_message_details_dialog(msg, details, type, buttons, parent)
    r = d.run()
    d.destroy()
    return r


def setup_text_combobox(combo, values=None, cell_data_func=None, *, use_markup=False, min_chars=3):
    combo.clear()

    # model: one string column
    if isinstance(values, Gtk.ListStore):
        model = values
    else:
        model = Gtk.ListStore(str)
        seen = set()
        for v in (values or []):
            s = to_unicode(v)  # ensure str
            if s in seen:
                continue
            seen.add(s)
            model.append([s])
    combo.set_model(model)

    # dropdown renderer
    col_cell = Gtk.CellRendererText()
    combo.pack_start(col_cell, True)

    def _default_cdf(_col, cell, mdl, itr, _data=None):
        txt = mdl[itr][0]
        prop = "markup" if use_markup else "text"
        safe_set_props(cell, prop, txt)

    combo.set_cell_data_func(col_cell, cell_data_func or _default_cdf)

    # attach completion to entry
    entry = combo.get_child() if hasattr(combo, "get_child") else None
    if not isinstance(entry, Gtk.Entry):
        return

    completion = Gtk.EntryCompletion()
    completion.set_model(model)

    # custom popup renderer (no set_text_column here)
    cc = Gtk.CellRendererText()
    completion.pack_start(cc, True)
    completion.set_cell_data_func(cc, cell_data_func or _default_cdf)

    # UX knobs
    completion.set_inline_completion(True)
    completion.set_inline_selection(True)
    completion.set_popup_completion(True)
    completion.set_popup_single_match(False)
    completion.set_minimum_key_length(min_chars)

    # case-insensitive prefix, unicode-safe
    def match_func(_compl, key, itr, _data=None):
        return (model[itr][0] or "").casefold().startswith((key or "").casefold())
    completion.set_match_func(match_func)

    def on_match_select(_compl, mdl, itr):
        value = mdl[itr][0]
        set_combo_from_value(combo, value)
        entry.set_text(value)
        entry.set_position(-1)
        return True
    completion.connect("match-selected", on_match_select)

    entry.set_completion(completion)


def prettify_format(format):
    """
    Return the date format in a more human readable form.
    """
    f = format.replate("%Y", "yyyy")
    f = f.replace("%m", "mm")
    f = f.replace("%d", "dd")
    return f


def today_str(format: Optional[Any] = None):
    """
    Return a string for of today's date according to format.

    If format=None then the format uses the prefs.date_format_pref
    """
    import bauble.prefs as prefs

    if not format:
        format = prefs.prefs[prefs.date_format_pref]
    import datetime

    today = datetime.date.today()
    return today.strftime(format)


def set_button_contents(
    button,
    label_text: Optional[Any] = None,
    icon_name: Optional[Any] = None,
    orientation=Gtk.Orientation.HORIZONTAL,
) -> None:
    """
    Set button contents with optional icon and label.
    Works in both GTK 3 and GTK 4.
    """
    # Create a container box
    box = Gtk.Box(orientation=orientation, spacing=6)

    if icon_name:
        image = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.BUTTON)
        box.pack_start(image, False, False, 0)

    if label_text:
        label = Gtk.Label(label=label_text)
        box.pack_start(label, False, False, 0)

    # Set as button child using appropriate API
    if hasattr(button, "set_child"):  # GTK 4
        button.set_child(box)
    else:  # GTK 3
        button.add(box)
        button.show_all()


def setup_date_button(view, entry, button, date_func: Optional[Any] = None) -> None:
    """
    Associate a button with entry so that when the button is clicked a
    date is inserted into the entry.

    :param view: a bauble.editor.GenericEditorView

    :param entry: the entry that the data goes into

    :param button: the button that enters the data in entry

    :param date_func: the function that returns a string represention
      of the date
    """
    if isinstance(entry, str):
        entry = view.widgets[entry]
    if isinstance(button, str):
        button = view.widgets[button]
    icon = os.path.join(paths.lib_dir(), "images", "calendar.png")
    image = Gtk.Image()
    image.set_from_file(icon)
    button.set_tooltip_text(_("Today's date"))
    # 7. issue_gtk_button_image_api (REMOVED, pack GtkImage manually inside GtkButton)
    if Gtk.get_major_version() >= 4:
        button.set_child(image)
    else:
        button.add(image)
        button.show_all()

    def on_clicked(b):
        s = ""
        if date_func:
            s = date_func()
        else:
            s = today_str()
        safe_set_text(entry, s)

    if view and hasattr(view, "connect"):
        view.connect(button, "clicked", on_clicked)
    else:
        button.connect("clicked", on_clicked)


def to_unicode(obj, encoding: str = "utf-8"):
    """
    Convert an object to a Unicode string (str in Python 3).

    :param obj: The object to convert.
    :param encoding: The encoding to use for decoding if the object is bytes.
    :return: A Unicode string representation of the object.
    """
    try:
        if isinstance(obj, bytes):
            # Decode bytes to string using the specified encoding
            return obj.decode(encoding, errors="replace")
        elif isinstance(obj, str):
            # Return as is since it's already a string
            return obj
        else:
            # Convert any other type to string using str()
            return str(obj)
    except Exception as e:
        logging.warning(f"Failed to convert object to string: {e}")
        # Return a fallback representation of the object's type
        return type(obj).__name__


def to_bytes(obj, encoding: str = "utf-8"):
    """
    Only use where an API/file write truly requires bytes.
    """
    if obj is None:
        return b""
    if isinstance(obj, (bytes, bytearray)):
        return bytes(obj)
    return to_unicode(obj).encode(encoding, errors="replace")


def xml_safe(obj):
    """
    Convert an object to a string and escape XML special characters.

    :param obj: The object to sanitize.
    :return: A string safe for use in XML.
    """
    import html

    try:
        return html.escape(to_unicode(obj))
    except Exception as e:
        logger.error(f"Failed to escape XML characters: {obj} ({e})")
        return str(obj)  # Fallback to plain string


def safe_numeric(s):
    "evaluate the string as a number, or return zero"

    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return 0


def safe_int(s):
    "evaluate the string as an integer, or return zero"

    try:
        return int(s)
    except ValueError:
        pass
    return 0


__natsort_rx: Any = re.compile(r"(\d+(?:\.\d+)?)")


def natsort_key(obj):
    """
    a key getter for sort and sorted function

    the sorting is done on return value of obj.__str__() so we can sort
    generic objects as well.

    use like: sorted(some_list, key=utils.natsort_key)
    """

    item = f"{obj}"
    chunks = __natsort_rx.split(item)
    for ii in range(len(chunks)):
        if chunks[ii] and chunks[ii][0] in "0123456789":
            if "." in chunks[ii]:
                numtype = float
            else:
                numtype = int
            # wrap in tuple with '0' to explicitly specify numbers come first
            chunks[ii] = (0, numtype(chunks[ii]))
        else:
            chunks[ii] = (1, chunks[ii])
    return (chunks, item)


def delete_or_expunge(obj) -> None:
    """
    If the object is in object_session(obj).new then expunge it from the
    session.  If not then session.delete it.
    """
    from sqlalchemy.orm import object_session

    session = object_session(obj)
    if session is None:
        return
    if obj not in session.new:
        logger.debug(f"delete obj: {obj} -- {repr(obj)}")
        session.delete(obj)
    else:
        logger.debug(f"expunge obj: {obj} -- {repr(obj)}")
        session.expunge(obj)
        del obj


def reset_sequence(column):
    """
    If column.sequence is not None or the column is an Integer and
    column.autoincrement is true then reset the sequence for the next
    available value for the column...if the column doesn't have a
    sequence then do nothing and return

    The SQL statements are executed directly from db.engine

    This function only works for PostgreSQL database.  It does nothing
    for other database engines.
    """
    import bauble.db as db
    from sqlalchemy import schema
    from sqlalchemy.types import Integer

    if db.engine.name != "postgresql":
        return

    sequence_name = None
    if hasattr(column, "default") and isinstance(column.default, schema.Sequence):
        sequence_name = column.default.name
    elif (
        isinstance(column.type, Integer)
        and column.autoincrement
        and (
            column.default is None
            or (isinstance(column.default, schema.Sequence) and column.default.optional)
        )
        and not column.foreign_keys
    ):
        sequence_name = f"{column.table.name}_{column.name}_seq"
    else:
        return

    try:
        with db.engine.begin() as conn:
            stmt = f"SELECT {column.name} FROM {column.table.name} FOR UPDATE"
            result = conn.execute(stmt)
            vals = list(result)
            maxid = max(vals, key=lambda x: x[0])[0] if vals else None

            if maxid is None:
                stmt = f"SELECT nextval('{sequence_name}')"
            else:
                stmt = f"SELECT setval('{sequence_name}', max({column.name})+1) FROM {column.table.name}"
            conn.execute(stmt)
    except Exception as e:
        logger.warning("bauble.utils.reset_sequence(): %s", utf8(e))


class WidgetStyler:
    css_provider: Any

    def __init__(self) -> None:
        self.css_provider = Gtk.CssProvider()
        self.css_provider.load_from_data(
            b"""
            .background-set {
                background-color: #FAF8F7;
            }
            .foreground-set {
                color: blue;
            }
        """
        )

    def apply_styles(self, widget, label) -> None:
        """Apply the CSS styles for background and foreground."""
        widget_style_context = widget.get_style_context()
        label_style_context = label.get_style_context()

        # Apply the CSS provider once to the widget and label's style context
        widget_style_context.add_provider(
            self.css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        label_style_context.add_provider(
            self.css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # Add the respective CSS classes
        widget_style_context.add_class("background-set")
        label_style_context.add_class("foreground-set")

    def reset_styles(self, widget, label) -> None:
        """Reset the applied CSS classes."""
        widget_style_context = widget.get_style_context()
        label_style_context = label.get_style_context()

        # Remove the CSS classes
        widget_style_context.remove_class("background-set")
        label_style_context.remove_class("foreground-set")


# Example usage:
styler: Any = WidgetStyler()


def make_label_clickable(label, on_clicked, *args) -> None:
    """
    :param label: a Gtk.Label that has a Gtk.EventBox as its parent
    :param on_clicked: callback to be called when the label is clicked
      on_clicked(label, event, data)
    """
    eventbox = label.get_parent()

    check(eventbox is not None, "label must have a parent")
    check(
        isinstance(eventbox, Gtk.EventBox),
        "label must have an Gtk.EventBox as its parent",
    )
    label.__pressed = False
    label.__on_clicked = on_clicked

    def on_enter_notify(widget, event, label, *args):
        """Handles mouse entering the widget, changing background and foreground colors."""

        # Use Gdk.RGBA instead of deprecated Gdk.Color
        # bg_color = Gdk.RGBA()
        # fg_color = Gdk.RGBA()

        # Parse colors correctly
        # bg_color.parse("#FAF8F7")
        # fg_color.parse("blue")
        styler.apply_styles(widget, label)

        # Apply background and foreground colors
        # idget.get_style_context().add_class('background-set')  # This will add the CSS class
        # widget.override_color(bg_color)
        # label.get_style_context().add_class('foreground-set')  # This will add the CSS class
        # label.override_color(Gtk.StateFlags.NORMAL, fg_color)  # For text color

    def on_leave_notify(widget, event, label, *args):
        # Get the widget's style context
        # widget.get_style_context().add_class('background-set')  # This will add the CSS class
        # widget.override_color(Gdk.RGBA())

        # label.override_color(Gtk.StateFlags.NORMAL, None)
        styler.reset_styles(widget, label)
        label.__pressed = False

    def on_press(widget, event, label, *args):
        label.__pressed = True

    def on_release(widget, event, label, *args):
        if label.__pressed:
            label.__pressed = False
            styler.reset_styles(widget, label)
            label.__on_clicked(label, event, *args)

    try:
        eventbox.disconnect(label.__on_event)
        logger.debug("disconnected previous release-event handler")
        label.__on_event = eventbox.connect(
            "button_release_event", on_release, label, *args
        )
    except AttributeError:
        logger.debug("defining handlers")
        label.__on_event = eventbox.connect(
            "button_release_event", on_release, label, *args
        )
        eventbox.connect("enter_notify_event", on_enter_notify, label)
        eventbox.connect("leave_notify_event", on_leave_notify, label)
        eventbox.connect("button_press_event", on_press, label)


def enum_values_str(col):
    """
    :param col: a string if table.col where col is an enum type

    return a string with of the values on an enum type join by a comma
    """
    import bauble.db as db

    table_name, col_name = col.split(".")
    # debug('%s.%s' % (table_name, col_name))
    values = db.metadata.tables[table_name].c[col_name].type.values[:]
    if None in values:
        values[values.index(None)] = "&lt;None&gt;"
    return ", ".join(values)


def which(filename, path: Optional[Any] = None):
    """
    Return first occurence of file on the path.
    """
    if not path:
        path = os.environ["PATH"].split(os.pathsep)
    for dirname in path:
        candidate = os.path.join(dirname, filename)
        if os.path.isfile(candidate):
            return candidate
    return None


def ilike(col, val, engine: Optional[Any] = None):
    """
    Return a cross platform ilike function.
    """
    from sqlalchemy import func

    # from sqlalchemy.engine import Engine

    if not engine:
        from bauble.db import engine as default_engine

        engine = default_engine

    if engine.url.get_dialect().name == "postgresql":
        # Use native ilike for PostgreSQL
        return col.ilike(val)
    else:
        return func.lower(col).like(func.lower(val))


def range_builder(text):
    """Return a list of numbers from a string range of the form 1-3,4,5"""
    from pyparsing import (
        Group,
        ParseException,
        ParseResults,
        Suppress,
        Word,
        delimitedList,
        nums,
    )

    rng = Group(Word(nums) + Suppress("-") + Word(nums))
    range_list = delimitedList(rng | Word(nums))

    try:
        tokens = range_list.parseString(text)
    except (AttributeError, ParseException) as e:
        logger.debug(e)
        return []
    values = set()
    for rng in tokens:
        if isinstance(rng, ParseResults):
            # get here if the token is a range
            start = int(rng[0])
            end = int(rng[1]) + 1
            check(start < end, "start must be less than end")
            values.update(list(range(start, end)))
        else:
            # get here if the token is an integer
            values.add(int(rng))
    return list(values)


def gc_objects_by_type(tipe):
    """
    Return a list of objects from the garbage collector by type.
    """
    import gc
    import inspect

    if isinstance(tipe, str):
        return [o for o in gc.get_objects() if type(o).__name__ == tipe]
    elif inspect.isclass(tipe):
        return [o for o in gc.get_objects() if isinstance(o, tipe)]
    else:
        return [o for o in gc.get_objects() if isinstance(o, type(tipe))]


def mem(size: str = "rss"):
    """Generalization; memory sizes: rss, rsz, vsz."""
    import os

    return int(os.popen("ps -p %d -o %s | tail -1" % (os.getpid(), size)).read())


def topological_sort(items, partial_order):
    """return list of nodes sorted by dependencies

    :param items: a list of items to be sorted.

    :param partial_order: a list of pairs. If pair ('a', 'b') is in it, it
        means that 'a' should not appear after 'b'.

    Returns a list of the items in one of the possible orders, or None if
    partial_order contains a loop.

    We want a minimum list satisfying the requirements, and the partial
    ordering states dependencies, but they may list more nodes than
    necessary in the solution. for example, whatever dependencies are given,
    if you start from the emtpy items list, the empty list is the solution.

    """

    def add_node(graph, node):
        """Add a node to the graph if not already exists."""
        if node not in graph:
            graph[node] = [0]  # 0 = number of arcs coming into this node.

    def add_arc(graph, fromnode, tonode):
        """
        Add an arc to a graph. Can create multiple arcs. The end nodes must
        already exist.
        """
        graph.setdefault(fromnode, [0]).append(tonode)
        graph.setdefault(tonode, [0])
        # Update the count of incoming arcs in tonode.
        graph[tonode][0] += 1

    # step 1 - create a directed graph with an arc a->b for each input
    # pair (a,b).
    # The graph is represented by a dictionary. The dictionary contains
    # a pair item:list for each node in the graph. /item/ is the value
    # of the node. /list/'s 1st item is the count of incoming arcs, and
    # the rest are the destinations of the outgoing arcs. For example:
    # {'a':[0,'b','c'], 'b':[1], 'c':[1]}
    # represents the graph: a --> b, a --> c
    # The graph may contain loops and multiple arcs.

    # (ABCDE, (AB, BC, BD)) becomes:
    # {a: [0, b], b: [1, c, d], c: [1], d: [1], e: [0]}
    # requesting B and E from the above should result in including all except A, and prepending C and D to B.

    graph = {}
    for v in items:
        add_node(graph, v)
    for a, b in partial_order:
        add_arc(graph, a, b)

    # Step 2 - find all roots (nodes with zero incoming arcs).

    roots = [node for (node, nodeinfo) in list(graph.items()) if nodeinfo[0] == 0]

    # step 3 - repeatedly emit a root and remove it from the graph. Removing
    # a node may convert some of the node's direct children into roots.
    # Whenever that happens, we append the new roots to the list of
    # current roots.

    sorted = []
    while len(roots) != 0:
        # When len(roots) > 1, we can choose any root to send to the
        # output; this freedom represents the multiple complete orderings
        # that satisfy the input restrictions. We arbitrarily take one of
        # the roots using pop(). Note that for the algorithm to be efficient,
        # this operation must be done in O(1) time.
        root = roots.pop()
        sorted.append(root)

        # remove 'root' from the graph to be explored: first remove its
        # outgoing arcs, then remove the node. if any of the nodes which was
        # connected to 'root' remains without incoming arcs, it goes into
        # the 'roots' list.

        # if the input describes a complete ordering, len(roots) stays equal
        # to 1 at each iteration.
        for child in graph[root][1:]:
            graph[child][0] = graph[child][0] - 1
            if graph[child][0] == 0:
                roots.append(child)
        del graph[root]

    if len(list(graph.items())) != 0:
        # There is a loop in the input.
        return None

    return sorted


from bauble.gtkinit import Gtk, Pango


class GenericMessageBox:  # identify_subclassing_issues (Consider using composition instead of subclassing GtkWidget)
    """
    Abstract class for showing a message box at the top of an editor.
    """

    event_box: Any
    box: Any

    def __init__(self) -> None:
        self.event_box = Gtk.EventBox()
        self.box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.event_box.add(self.box)

    def get_parent(self):
        return self.event_box.get_parent()


    def hide(self):
        self.event_box.hide()

    def destroy(self):
        self.event_box.destroy()

    # def set_color(self, attr, state, color) -> None:
    #     """Sets background or foreground color dynamically using CSS."""
    #     context = self.event_box.get_style_context()

    #     # Convert the color to RGBA string
    #     color_str = f"rgba({int(color.red * 255)}, {int(color.green * 255)}, {int(color.blue * 255)})"

    #     # Create a dynamic CSS rule based on the provided attribute, state, and color
    #     css_rule = f"""
    #     .{attr}:{state} {{
    #         {attr}: {color_str};
    #     }}
    #     """

    #     # Create the CSS provider
    #     css_provider = Gtk.CssProvider()
    #     css_provider.load_from_data(css_rule.encode("utf-8"))

    #     # Apply the CSS provider to the widget's style context
    #     context.add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    def _ensure_widget_css_class(self):
        # one unique class per instance so rules don't leak
        if not hasattr(self, "_css_class"):
            self._css_class = f"msgbox-{id(self)}"
            self.event_box.get_style_context().add_class(self._css_class)
        return self._css_class

    def _color_to_css(self, value):
        # accepts Gdk.RGBA, Gdk.Color, '#rrggbb[aa]' or (r,g,b[,a])
        try:
            from bauble.gtkinit import Gdk
        except Exception:
            pass

        # Gdk.RGBA
        if hasattr(value, "red") and hasattr(value, "alpha"):
            r = int(round(value.red   * 255))
            g = int(round(value.green * 255))
            b = int(round(value.blue  * 255))
            a = float(value.alpha)
            return f"rgba({r},{g},{b},{a:.3f})"

        # Gdk.Color (GTK3 legacy)
        if hasattr(value, "red") and not hasattr(value, "alpha"):
            r = int(round(value.red   / 257))   # 0..65535 → 0..255
            g = int(round(value.green / 257))
            b = int(round(value.blue  / 257))
            return f"rgba({r},{g},{b},1.0)"

        # hex string
        if isinstance(value, str) and value.startswith("#"):
            hexv = value.lstrip("#")
            if len(hexv) == 6:
                r, g, b = int(hexv[0:2],16), int(hexv[2:4],16), int(hexv[4:6],16)
                return f"rgba({r},{g},{b},1.0)"
            if len(hexv) == 8:
                r, g, b = int(hexv[0:2],16), int(hexv[2:4],16), int(hexv[4:6],16)
                a = int(hexv[6:8],16) / 255.0
                return f"rgba({r},{g},{b},{a:.3f})"

        # tuple/list
        if isinstance(value, (tuple, list)):
            r, g, b = int(value[0]), int(value[1]), int(value[2])
            a = float(value[3]) if len(value) > 3 else 1.0
            return f"rgba({r},{g},{b},{a:.3f})"

        # fallback
        return "rgba(240,240,240,1.0)"

    def _state_to_pseudo(self, state):
        # Accept Gtk.StateType or strings ('normal', 'prelight', etc.)
        try:
            # Enum path (GTK 3)
            if state == Gtk.StateType.PRELIGHT:
                return ":hover"
            if state == Gtk.StateType.ACTIVE:
                return ":active"
            if state == Gtk.StateType.INSENSITIVE:
                return ":disabled"
            if state == Gtk.StateType.SELECTED:
                return ":selected"
            return ""  # NORMAL or anything else
        except Exception:
            pass

        # String path
        s = (str(state) if state is not None else "").lower()
        return {
            "normal": "",
            "prelight": ":hover",
            "hover": ":hover",
            "active": ":active",
            "insensitive": ":disabled",
            "disabled": ":disabled",
            "selected": ":selected",
        }.get(s, "")
    
    def set_color(self, attr, state, color):
        """
        Backwards-compatible: attr in {'bg','background','fg','foreground'}
        state: Gtk.StateType (NORMAL, PRELIGHT, ACTIVE, INSENSITIVE, SELECTED)
        color: Gdk.RGBA / Gdk.Color / '#rrggbb[aa]' / (r,g,b[,a])
        """
        css_prop = {
            "bg": "background-color",
            "background": "background-color",
            "fg": "color",
            "foreground": "color",
            "background-color": "background-color",
            "color": "color",
        }.get(str(attr).lower())

        if not css_prop:
            return  # ignore unknown attrs to stay forgiving

        pseudo = self._state_to_pseudo(state)

        klass = self._ensure_widget_css_class()
        color_css = self._color_to_css(color)
        css = f".{klass}{pseudo} {{ {css_prop}: {color_css}; }}\n"

        _install_css(css)


    def show_all(self) -> None:
        """
        Displays the widget and adjusts size dynamically.
        """
        # Always show our subtree
        self.event_box.show_all()
    
        parent = self.event_box.get_parent()
        if parent is not None:
            try:
                parent.show_all()
            except Exception:
                pass

        # Instead of forcing a fixed size, add margins for spacing
        self.event_box.set_margin_top(5)
        self.event_box.set_margin_bottom(5)
        # optional, for symmetry / RTL friendliness:
        self.event_box.set_margin_start(8)
        self.event_box.set_margin_end(8)

    def show(self) -> None:
        self.show_all()

    def add(self, child):
        # present in Gtk.Container on GTK3; we forward if needed
        if hasattr(self.event_box, "add"):
            self.event_box.add(child)

    def remove(self, child):
        if hasattr(self.event_box, "remove"):
            self.event_box.remove(child)

    def get_style_context(self):
        return self.event_box.get_style_context()

    def get_widget(self):
        """Returns the event box widget."""
        return self.event_box

    # As a last resort, forward unknown attributes to the underlying widget.
    def __getattr__(self, name):
        return getattr(self.event_box, name)

class MessageBox(GenericMessageBox):
    """
    A MessageBox that can display a message label at the top of an editor.
    """

    box: Any
    vbox: Any
    label: Any
    buffer: Any
    details_expander: Any
    details_label: Any

    def __init__(
        self, msg: Optional[Any] = None, details: Optional[Any] = None
    ) -> None:
        super().__init__()
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.box.pack_start(content, True, True, 0)
        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content.pack_start(self.vbox, True, True, 0)

        self.label = Gtk.TextView()
        self.label.set_can_focus(False)
        self.buffer = Gtk.TextBuffer()
        self.label.set_buffer(self.buffer)
        if msg:
            self.buffer.set_text(msg)
        content.pack_start(self.label, True, True, 0)

        # Button Box
        button_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content.pack_start(button_box, False, False, 0)
        button = Gtk.Button()
        image = Gtk.Image.new_from_icon_name(
            "window-close", Gtk.IconSize.BUTTON
        )  # Pack the Gtk.Image manually inside Gtk.Button
        button.set_image(image)
        button.set_relief(Gtk.ReliefStyle.NONE)
        button_box.pack_start(button, False, False, 0)

        # Details Expander
        self.details_expander = Gtk.Expander()
        content.pack_start(self.details_expander, True, True, 0)

        # Scrolled Window with Viewport
        sw = Gtk.ScrolledWindow()
        sw.set_size_request(-1, 200)
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        viewport = Gtk.Viewport()
        sw.add(viewport)
        self.details_label = Gtk.Label()
        self.details_label.set_line_wrap(True)
        self.details_label.set_xalign(0)  # Align text to the left
        self.details_label.set_property("ellipsize", Pango.EllipsizeMode.END)
        viewport.add(self.details_label)

        self.details = (details or "")[:4096]
        self.details_expander.add(sw)

        # Connect expanded signal
        self.details_expander.connect("notify::expanded", self.on_expanded)

        # Button Close Handler
        def on_close(*args):
            parent = self.get_parent()
            if parent is not None:
                parent.remove(self)

        button.connect("clicked", on_close, True)

        # Color setup
        colors = [
            ("background-color", "normal", Gdk.RGBA()),
            ("background-color", "prelight", Gdk.RGBA()),
        ]

        colors[0][2].parse("#FFFFFF")
        colors[1][2].parse("#FFFFFF")

        for color in colors:
            self.set_color(*color)

    def on_expanded(self, *args) -> None:
        """Adjust size when expanded."""
        width, height = self.box.get_preferred_size()[1]
        self.box.set_size_request(width, -1)
        self.box.queue_resize()

    def show_all(self) -> None:
        """
        Show the widget but hide the details expander if there is no text.
        """
        self.box.show_all()
        if not self.details_label.get_text():
            self.details_expander.hide()

    @property
    def message(self) -> Any:
        return self.buffer.get_text(
            self.buffer.get_start_iter(), self.buffer.get_end_iter(), True
        )

    @message.setter
    def message(self, msg):
        self.buffer.set_text(msg or "")

    @property
    def details(self) -> Any:
        return self.details_label.get_text()

    @details.setter
    def details(self, msg):
        if msg:
            self.details_label.set_text(msg)
        else:
            self.details_label.set_text("")

    def get_widget(self):
        # Return the box containing all the widgets
        return self.event_box


class YesNoMessageBox(GenericMessageBox):
    """
    A message box that can present a Yes or No question to the user
    """

    label: Any
    yes_button: Any
    no_button: Any

    def __init__(
        self, msg: Optional[Any] = None, on_response: Optional[Any] = None
    ) -> None:
        """
        on_response: callback method when the yes or no buttons are
        clicked.  The signature of the function should be
        func(button, response) where response is True/False
        depending on whether the user selected Yes or No, respectively.
        """
        super().__init__()
        self.label = Gtk.Label()
        if msg:
            self.label.set_markup(msg)
        self.label.set_alignment(0.1, 0.1)
        self.box.pack_start(self.label, True, True, 0)

        button_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.box.pack_start(button_box, False, False, 0)
        self.yes_button = Gtk.Button(label=_("Yes"))
        if on_response:
            self.yes_button.connect("clicked", on_response, True)
        button_box.pack_start(self.yes_button, False, False, 0)

        button_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.box.pack_start(button_box, False, False, 0)
        self.no_button = Gtk.Button(label=_("No"))
        if on_response:
            self.no_button.connect("clicked", on_response, False)
        button_box.pack_start(self.no_button, False, False, 0)

        colors = [
            ("background-color", "normal", Gdk.Color.parse("#FFFFFF").color),
            ("background-color", "prelight", Gdk.Color.parse("#FFFFFF").color),
        ]
        for color in colors:
            self.set_color(*color)

    def _set_on_response(self, func) -> None:
        self.yes_button.connect("clicked", func, True)
        self.no_button.connect("clicked", func, False)

    on_response: Any = property(fset=_set_on_response)

    def _get_message(self, msg):
        return self.label.text

    def _set_message(self, msg) -> None:
        self.label.set_markup(msg or "")

    message: Any = property(_get_message, _set_message)

    def get_widget(self):
        # Return the box containing all the widgets
        return self.event_box


MESSAGE_BOX_INFO: int = 1
MESSAGE_BOX_ERROR: int = 2
MESSAGE_BOX_YESNO: int = 3


def add_message_box(parent, type=MESSAGE_BOX_INFO):
    """
    :param parent: the parent :class:`Gtk.Box` width to add the
      message box to
    :param type: one of MESSAGE_BOX_INFO, MESSAGE_BOX_ERROR or
      MESSAGE_BOX_YESNO

    """
    msg_box = None
    if type == MESSAGE_BOX_INFO:
        msg_box = MessageBox()
    elif type == MESSAGE_BOX_ERROR:
        msg_box = MessageBox()  # check this
    elif type == MESSAGE_BOX_YESNO:
        msg_box = YesNoMessageBox()
    else:
        raise ValueError(f"unknown message box type: {type}")
    parent.pack_start(msg_box.get_widget(), True, True, 0)
    return msg_box


def get_distinct_values(column, session):
    """
    Return a list of all the distinct values in a table column
    """
    stmt = select(distinct(column))
    results = session.execute(stmt).scalars().all()
    return [v for v in results if v is not None]


def get_invalid_columns(obj, ignore_columns: Optional[Any] = None):
    """
    Return column names on a mapped object that have values
    which aren't valid for the model.

    Invalid columns meet the following criteria:
    - nullable columns with null values
    - ...what else?
    """
    # TODO: check for invalid enum types
    if ignore_columns is None:
        ignore_columns = ["id"]
    if not obj:
        return []

    table = obj.__table__
    invalid_columns = []
    for column in [c for c in table.c if c.name not in ignore_columns]:
        v = getattr(obj, column.name)
        # debug('%s.%s = %s' % (table.name, column.name, v))
        if v is None and not column.nullable:
            invalid_columns.append(column.name)
    return invalid_columns


def get_urls(text):
    """
    Return tuples of http/https links and labels for the links.  To
    label a link prefix it with [label text],
    e.g. [BBG]http://belizebotanic.org
    """
    rx = re.compile(r"(?:\[(.+?)\])?((?:(?:http)|(?:https))://\S+)", re.I)
    matches = []
    for match in rx.finditer(text):
        matches.append(match.groups())
    return matches


sloppy_iso8601: Any = re.compile("^[12][0-9][0-9][0-9]-[0-9][0-9]?-[0-9][0-9]?.*$")


def parse_date(value, dayfirst: bool = True, yearfirst: bool = False, **kwargs):
    if sloppy_iso8601.match(value) is not None:
        dayfirst = False
        yearfirst = True
    return dateutil.parser.parse(
        value, dayfirst=dayfirst, yearfirst=yearfirst, **kwargs
    )


def safe_rollback(session) -> None:
    if session.in_transaction():
        session.rollback()


def safe_commit(session) -> None:
    if session.in_transaction():
        session.commit()
