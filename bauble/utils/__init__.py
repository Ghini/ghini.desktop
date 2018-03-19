# -*- coding: utf-8 -*-
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

"""
A common set of utility functions used throughout Ghini.
"""
import datetime
import os
import re
import textwrap
import xml.sax.saxutils as saxutils

import gtk
import gobject
import glib

import logging
logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)

import threading


import bauble
from bauble.error import check
from bauble import paths


def read_in_chunks(file_object, chunk_size=1024):
    """read a chunk from a stream

    Lazy function (generator) to read piece by piece from a file-like object.
    Default chunk size: 1k."""
    while True:
        data = file_object.read(chunk_size)
        if not data:
            break
        yield data


class Cache:
    '''a simple class for caching images

    you instantiate a size 10 cache like this:
    >>> cache = ImageCache(10)

    if `getter` is a function that returns a picture, you don't immediately
    invoke it, you use the cache like this:
    >>> image = cache.get(name, getter)

    internally, the cache is stored in a dictionary, the key is the name of
    the image, the value is a pair with first the timestamp of the last usage
    of that key and second the value.
    '''

    def __init__(self, size):
        self.size = size
        self.storage = {}

    def get(self, key, getter, on_hit=lambda x: None):
        if key in self.storage:
            value = self.storage[key][1]
            on_hit(value)
        else:
            if len(self.storage) == self.size:
                # remove the oldest entry
                k = min(zip(self.storage.values(), self.storage.keys()))[1]
                del self.storage[k]
            value = getter()
        import time
        self.storage[key] = time.time(), value
        return value

def copy_picture_with_thumbnail(path, basename=None):
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
    ## make thumbnail in thumbs subdirectory
    from PIL import Image
    full_dest_path = os.path.join(prefs.prefs[prefs.picture_root_pref],
                                  'thumbs', basename)
    result = ""
    try:
        im = Image.open(filename)
        im.thumbnail((400, 400))
        logger.debug('copying %s to %s' % (filename, full_dest_path))
        im.save(full_dest_path)
        from io import BytesIO
        output = BytesIO()
        im.save(output, format='JPEG')
        im_data = output.getvalue()
        result = base64.b64encode(im_data)
    except IOError, e:
        logger.warning("can't make thumbnail")
    except Exception, e:
        logger.warning("unexpected exception making thumbnail: "
                       "(%s)%s" % (type(e), e))
    return result


class ImageLoader(threading.Thread):
    cache = Cache(12)  # class-global cached results

    def __init__(self, box, url, *args, **kwargs):
        super(ImageLoader, self).__init__(*args, **kwargs)
        self.box = box  # will hold image or label
        self.loader = gtk.gdk.PixbufLoader()
        self.inline_picture_marker = "|data:image/jpeg;base64,"
        if url.find(self.inline_picture_marker) != -1:
            self.reader_function = self.read_base64
            self.url = url
        elif (url.startswith('http://') or url.startswith('https://')):
            self.reader_function = self.read_global_url
            self.url = url
        else:
            self.reader_function = self.read_local_url
            from bauble import prefs
            pfolder = prefs.prefs[prefs.picture_root_pref]
            self.url = os.path.join(pfolder, url)

    def callback(self):
        pixbuf = self.loader.get_pixbuf()
        try:
            pixbuf = pixbuf.apply_embedded_orientation()
            scale_x = pixbuf.get_width() / 400
            scale_y = pixbuf.get_height() / 400
            scale = max(scale_x, scale_y, 1)
            x = int(pixbuf.get_width() / scale)
            y = int(pixbuf.get_height() / scale)
            scaled_buf = pixbuf.scale_simple(x, y, gtk.gdk.INTERP_BILINEAR)
            if self.box.get_children():
                image = self.box.get_children()[0]
            else:
                image = gtk.Image()
                self.box.add(image)
            image.set_from_pixbuf(scaled_buf)
        except glib.GError, e:
            logger.debug("picture %s caused glib.GError %s" %
                         (self.url, e))
            text = _('picture file %s not found.') % self.url
            label = gtk.Label()
            label.set_text(text)
            self.box.add(label)
        except Exception, e:
            logger.warning("picture %s caused Exception %s:%s" %
                           (self.url, type(e), e))
            label = gtk.Label()
            label.set_text(str(e))
            self.box.add(label)
        self.box.show_all()

    def loader_notified(self, pixbufloader):
        gobject.idle_add(self.callback)

    def run(self):
        self.loader.connect("closed", self.loader_notified)
        self.cache.get(
            self.url, self.reader_function, on_hit=self.loader.write)
        self.loader.close()

    def read_base64(self):
        self.loader.connect("area-prepared", self.loader_notified)
        thumb64pos = self.url.find(self.inline_picture_marker)
        offset = thumb64pos + len(self.inline_picture_marker)
        import base64
        return base64.b64decode(self.url[offset:])

    def read_global_url(self):
        self.loader.connect("area-prepared", self.loader_notified)
        import urllib
        import contextlib
        pieces = []
        with contextlib.closing(urllib.urlopen(self.url)) as f:
            for piece in read_in_chunks(f, 4096):
                self.loader.write(piece)
                pieces.append(piece)
        return ''.join(pieces)

    def read_local_url(self):
        self.loader.connect("area-prepared", self.loader_notified)
        pieces = []
        with open(self.url, "rb") as f:
            for piece in read_in_chunks(f, 4096):
                self.loader.write(piece)
                pieces.append(piece)
        return ''.join(pieces)


def find_dependent_tables(table, metadata=None):
    '''
    Return an iterator with all tables that depend on table.  The
    tables are returned in the order that they depend on each
    other. For example you know that table[0] does not depend on
    tables[1].

    :param table: The tables who dependencies we want to find

    :param metadata: The :class:`sqlalchemy.engine.MetaData` object
      that holds the tables to search through.  If None then use
      bauble.db.metadata
    '''
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
                if fk.column.table == t2 and tbl not in tables \
                        and tbl is not table:
                    tables.append(tbl)
                    _impl(tbl)
    _impl(table)
    return sort_tables(tables=tables)


def load_widgets(filename):
    b = BuilderLoader.load(filename)
    return BuilderWidgets(b)


class BuilderLoader(object):
    """
    This class caches the gtk.Builder objects so that loading the same
    file with the same name returns the same gtk.Builder.

    It might seem crazy to keep them around instead of deleting them
    and freeing the memory but in reality the memory is never returned
    to the system. By using this class you can keep the size of the
    application from growing if the same UI decription is loaded
    several times.  e.g. everytime you open an editor or infobox
    """
    # NOTE: this builder loader is really only used because of a bug
    # in PyGTK where a gtk.Builder doesn't free some memory so we use
    # this to keep the memory from growing out of control. if the
    # gtk/pygtk people fix that bug we should be able to get rid of
    # this class
    # http://bugzilla.gnome.org/show_bug.cgi?id=589057,560822

    builders = {}

    @classmethod
    def load(cls, filename):
        """
        """
        if filename in cls.builders.keys():
            return cls.builders[filename]
        b = gtk.Builder()
        b.add_from_file(filename)
        cls.builders[filename] = b
        return b


class BuilderWidgets(dict):
    """
    Provides dictionary and attribute access for a
    :class:`gtk.Builder` object.
    """

    def __init__(self, ui):
        '''
        :params filename: a gtk.Builder XML UI file
        '''
        if isinstance(ui, basestring):
            self.builder = gtk.Builder()
            self.builder.add_from_file(ui)
        else:
            self.builder = ui

    def __getitem__(self, name):
        '''
        :param name:
        '''
        w = self.builder.get_object(name)
        if not w:
            raise KeyError(
                _('no widget named "%(widget_name)s" in glade file') %
                {'widget_name': name})
        return w

    def __getattr__(self, name):
        '''
        :param name:
        '''
        if name == '_builder_':
            return self.builder
        w = self.builder.get_object(name)
        if not w:
            raise KeyError(
                _('no widget named "%(widget_name)s" in glade file') %
                {'widget_name': name})
        return w

    def remove_parent(self, widget):
        """
        Remove widgets from its parent.
        """
        # if parent is the last reference to widget then widget may be
        # automatically destroyed
        if isinstance(widget, str):
            w = self[widget]
        else:
            w = widget
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
    Return a iterable of gtk.TreeIter instances to all occurences
    of data in model

    :param parent: a gtk.TreeModel or a gtk.TreeModelRow instance
    :param data: the data to look for
    :param cmp: the function to call on each row to check if it matches
     data, default is C{lambda row, data: row[0] == data}
    """
    if isinstance(parent, gtk.TreeModel):
        if not parent.get_iter_root():  # model empty
            return []
        return search_tree_model(parent[parent.get_iter_root()], data, cmp)
    results = set()

    def func(model, path, iter, dummy=None):
        if cmp(model[iter], data):
            #debug('add: %s' % model[iter])
            results.add(iter)
        return False
    parent.model.foreach(func)
    return tuple(results)


def clear_model(obj_with_model):
    """
    :param obj_with_model: a gtk Widget that has a gtk.TreeModel that
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
        for c in xrange(0, ncols):
            v = model.get_value(iter, c)
            del v
        del iter
    model.foreach(del_cb)
    model.clear()
    del model
    obj_with_model.set_model(None)


def combo_set_active_text(combo, value):
    '''
    does the same thing as set_combo_from_value but this looks more like a
    GTK+ method
    '''
    set_combo_from_value(combo, value)


def set_combo_from_value(combo, value, cmp=lambda row, value: row[0] == value):
    '''
    Find value in combo model and set it as active, else raise ValueError
    cmp(row, value) is the a function to use for comparison

    .. note:: if more than one value is found in the combo then the
      first one in the list is set
    '''
    model = combo.get_model()
    matches = search_tree_model(model, value, cmp)
    if len(matches) == 0:
        raise ValueError('set_combo_from_value() - could not find value in '
                         'combo: %s' % value)
    combo.set_active_iter(matches[0])
    combo.emit('changed')


def combo_get_value_iter(combo, value, cmp=lambda row, value: row[0] == value):
    '''
    Returns a gtk.TreeIter that points to first matching value in the
    combo's model.

    :param combo: the combo where we should search
    :param value: the value to search for
    :param cmp: the method to use to compare rows in the combo model and value,
      the default is C{lambda row, value: row[0] == value}

    .. note:: if more than one value is found in the combo then the first one
      in the list is returned
    '''
    model = combo.get_model()
    matches = search_tree_model(model, value, cmp)
    if len(matches) == 0:
        return None
    return matches[0]


def get_widget_value(widget, index=0):
    '''
    :param widget: an instance of gtk.Widget
    :param index: the row index to use for those widgets who use a model

    .. note:: any values passed in for widgets that expect a string will call
      the values __str__ method
    '''

    if isinstance(widget, gtk.Label):
        return utf8(widget.get_text())
    elif isinstance(widget, gtk.TextView):
        textbuffer = widget.get_buffer()
        return utf8(textbuffer.get_text(textbuffer.get_start_iter(), textbuffer.get_end_iter()))
    elif isinstance(widget, gtk.Entry):
        return utf8(widget.get_text())
    elif isinstance(widget, gtk.ComboBox):
        if isinstance(widget, gtk.ComboBoxEntry):
            return utf8(widget.child.props.text)
    elif isinstance(widget,
                    (gtk.ToggleButton, gtk.CheckButton, gtk.RadioButton)):
        return widget.get_active()
    elif isinstance(widget, gtk.Button):
        return utf8(widget.props.label)

    else:
        raise TypeError('utils.set_widget_value(): Don\'t know how to handle '
                        'the widget type %s with name %s' %
                        (type(widget), widget.name))


def set_widget_value(widget, value, markup=False, default=None, index=0):
    '''
    :param widget: an instance of gtk.Widget
    :param value: the value to put in the widget
    :param markup: whether or not value is markup
    :param default: the default value to put in the widget if the value is None
    :param index: the row index to use for those widgets who use a model

    .. note:: any values passed in for widgets that expect a string will call
      the values __str__ method
    '''

    if value is None:  # set the value from the default
        if isinstance(widget, (gtk.Label, gtk.TextView, gtk.Entry)) \
                and default is None:
            value = ''
        else:
            value = default

    # assume that if value is a date then we want to display it with
    # the default date format
    import bauble.prefs as prefs
    if isinstance(value, datetime.date):
        date_format = prefs.prefs[prefs.date_format_pref]
        value = value.strftime(date_format)

    if isinstance(widget, gtk.Label):
        #widget.set_text(str(value))
        # FIXME: some of the enum values that have <not set> as a values
        # will give errors here, but we can't escape the string because
        # if someone does pass something that needs to be marked up
        # then it won't display as intended, maybe BaubleTable.markup()
        # should be responsible for returning a properly escaped values
        # or we should just catch the error(is there an error) and call
        # set_text if set_markup fails
        if markup:
            widget.set_markup(utf8(value))
        else:
            widget.set_text(utf8(value))
    elif isinstance(widget, gtk.TextView):
        widget.get_buffer().set_text(str(value))
    elif isinstance(widget, gtk.TextBuffer):
        widget.set_text(str(value))
    elif isinstance(widget, gtk.Entry):
        widget.set_text(utf8(value))
    elif isinstance(widget, gtk.ComboBox):
        # handles gtk.ComboBox and gtk.ComboBoxEntry
        treeiter = None
        if not widget.get_model():
            logger.warning(
                "utils.set_widget_value(): combo doesn't have a model: %s" %
                gtk.Buildable.get_name(widget))
        else:
            treeiter = combo_get_value_iter(
                widget, value, cmp=lambda row, value: row[index] == value)
            if treeiter:
                widget.set_active_iter(treeiter)
            else:
                widget.set_active(-1)
        if isinstance(widget, gtk.ComboBoxEntry):
            widget.child.props.text = value or ''
    elif isinstance(widget,
                    (gtk.ToggleButton, gtk.CheckButton, gtk.RadioButton)):
        from types import StringTypes
        if (isinstance(widget, gtk.CheckButton)
                and isinstance(value, StringTypes)):
            value = (value == gtk.Buildable.get_name(widget))
        if value is True:
            widget.set_inconsistent(False)
            widget.set_active(True)
        elif value is False:  # why do we need unset `inconsistent` for False?
            widget.set_inconsistent(False)
            widget.set_active(False)
        else: # treat None as False, we do not handle inconsistent cases.
            widget.set_inconsistent(False)
            widget.set_active(False)
    elif isinstance(widget, gtk.Button):
        if value is None:
            widget.props.label = ''
        else:
            widget.props.label = utf8(value)

    else:
        raise TypeError('utils.set_widget_value(): Don\'t know how to handle '
                        'the widget type %s with name %s' %
                        (type(widget), widget.name))


def create_message_dialog(msg, type=gtk.MESSAGE_INFO, buttons=gtk.BUTTONS_OK,
                          parent=None):
    '''
    Create a message dialog.

    :param msg: The markup to use for the message. The value should be
      escaped in case it contains any HTML entities.
    :param type: A GTK message type constant.  The default is gtk.MESSAGE_INFO.
    :param buttons: A GTK buttons type constant.  The default is
      gtk.BUTTONS_OK.
    :param parent:  The parent window for the dialog

    Returns a :class:`gtk.MessageDialog`
    '''
    if parent is None:
        try:  # this might get called before bauble has started
            parent = bauble.gui.window
        except Exception:
            parent = None
    d = gtk.MessageDialog(flags=gtk.DIALOG_MODAL |
                          gtk.DIALOG_DESTROY_WITH_PARENT,
                          parent=parent, type=type, buttons=buttons)
    d.set_title('Ghini')
    d.set_markup(msg)

    # get the width of a character
    context = d.get_pango_context()
    font_metrics = context.get_metrics(context.get_font_description(),
                                       context.get_language())
    width = font_metrics.get_approximate_char_width()
    import pango
    # if the character width is less than 300 pixels then set the
    # message dialog's label to be 300 to avoid tiny dialogs
    if width/pango.SCALE*len(msg) < 300:
        # TODO: got this message but i don't really know what it
        # means..should we set the width with markup???
        #
        #./bauble/utils/__init__.py:347: DeprecationWarning: use
        #set_markup() instead  d.label.set_size_request(300, -1)
        d.label.set_size_request(300, -1)

    if d.get_icon() is None:
        try:
            pixbuf = gtk.gdk.pixbuf_new_from_file(bauble.default_icon)
            d.set_icon(pixbuf)
        except Exception:
            pass
        d.set_property('skip-taskbar-hint', False)
    d.show_all()
    return d


def message_dialog(msg, type=gtk.MESSAGE_INFO, buttons=gtk.BUTTONS_OK,
                   parent=None):
    '''
    Create a message dialog with :func:`bauble.utils.create_message_dialog`
    and run and destroy it.

    Returns the dialog's response.
    '''
    d = create_message_dialog(msg, type, buttons, parent)
    r = d.run()
    d.destroy()
    return r


def create_yes_no_dialog(msg, parent=None):
    """
    Create a dialog with yes/no buttons.
    """
    if parent is None:
        try:  # this might get called before bauble has started
            parent = bauble.gui.window
        except Exception:
            parent = None
    d = gtk.MessageDialog(flags=gtk.DIALOG_MODAL |
                          gtk.DIALOG_DESTROY_WITH_PARENT,
                          parent=parent, type=gtk.MESSAGE_QUESTION,
                          buttons=gtk.BUTTONS_YES_NO)
    d.set_title('Ghini')
    d.set_markup(msg)
    if d.get_icon() is None:
        try:
            pixbuf = gtk.gdk.pixbuf_new_from_file(bauble.default_icon)
            d.set_icon(pixbuf)
        except Exception:
            pass
        d.set_property('skip-taskbar-hint', False)
    d.show_all()
    return d


def yes_no_dialog(msg, parent=None, yes_delay=-1):
    """
    Create and run a yes/no dialog.

    Return True if the dialog response equals gtk.RESPONSE_YES

    :param msg: the message to display in the dialog
    :param parent: the dialog's parent
    :param yes_delay: the number of seconds before the yes button should
      become sensitive
    """
    d = create_yes_no_dialog(msg, parent)
    if yes_delay > 0:
        d.set_response_sensitive(gtk.RESPONSE_YES, False)

        def on_timeout():
            if d.get_property('visible'):  # conditional avoids GTK+ warning
                d.set_response_sensitive(gtk.RESPONSE_YES, True)
            return False
        import gobject
        gobject.timeout_add(yes_delay*1000, on_timeout)
    r = d.run()
    d.destroy()
    return r == gtk.RESPONSE_YES


def create_message_details_dialog(msg, details, type=gtk.MESSAGE_INFO,
                                  buttons=gtk.BUTTONS_OK, parent=None):
    '''
    Create a message dialog with a details expander.
    '''
    if parent is None:
        try:  # this might get called before bauble has started
            parent = bauble.gui.window
        except Exception:
            parent = None

    d = gtk.MessageDialog(flags=gtk.DIALOG_MODAL |
                          gtk.DIALOG_DESTROY_WITH_PARENT,
                          parent=parent, type=type, buttons=buttons)
    d.set_title('Ghini')
    d.set_markup(msg)

    # get the width of a character
    context = d.get_pango_context()
    font_metrics = context.get_metrics(context.get_font_description(),
                                       context.get_language())
    width = font_metrics.get_approximate_char_width()
    import pango
    # if the character width is less than 300 pixels then set the
    # message dialog's label to be 300 to avoid tiny dialogs
    if width/pango.SCALE*len(msg) < 300:
        d.set_size_request(300, -1)

    expand = gtk.Expander(_("Details"))
    text_view = gtk.TextView()
    text_view.set_editable(False)
    text_view.set_wrap_mode(gtk.WRAP_WORD)
    tb = gtk.TextBuffer()
    tb.set_text(details)
    text_view.set_buffer(tb)
    sw = gtk.ScrolledWindow()
    sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
    sw.set_size_request(-1, 200)
    sw.add(text_view)
    expand.add(sw)
    d.vbox.pack_start(expand)
    # make "OK" the default response
    d.set_default_response(gtk.RESPONSE_OK)
    if d.get_icon() is None:
        try:
            pixbuf = gtk.gdk.pixbuf_new_from_file(bauble.default_icon)
            d.set_icon(pixbuf)
        except Exception:
            pass
        d.set_property('skip-taskbar-hint', False)

    d.show_all()
    return d


def message_details_dialog(msg, details, type=gtk.MESSAGE_INFO,
                           buttons=gtk.BUTTONS_OK, parent=None):
    '''
    Create and run a message dialog with a details expander.
    '''
    d = create_message_details_dialog(msg, details, type, buttons, parent)
    r = d.run()
    d.destroy()
    return r


def setup_text_combobox(combo, values=None, cell_data_func=None):
    """
    Configure a gtk.ComboBox as a text combobox

    NOTE: If you pass a cell_data_func that is a method of an object that
    holds a reference to combo then the object will not be properly
    garbage collected.  To avoid this problem either don't pass a
    method of object or make the method static

    :param combo: gtk.ComboBox
    :param values: list vales or gtk.ListStore
    :param cell_date_func:
    """
    combo.clear()
    if isinstance(values, gtk.ListStore):
        model = values
    else:
        if values is None:
            values = []
        model = gtk.ListStore(str)
        map(lambda v: model.append([v]), values)

    combo.clear()
    combo.set_model(model)
    renderer = gtk.CellRendererText()
    combo.pack_start(renderer, True)
    combo.add_attribute(renderer, 'text', 0)

    if cell_data_func:
        combo.set_cell_data_func(renderer, cell_data_func)

    if not isinstance(combo, gtk.ComboBoxEntry):
        return

    # enables things like scrolling through values with keyboard and
    # other goodies
    combo.props.text_column = 0

    # if combo is a gtk.ComboBoxEntry then setup completions
    def compl_cell_data_func(col, cell, model, treeiter, data=None):
        cell.props.text = utf8(model[treeiter][0])
    completion = gtk.EntryCompletion()
    completion.set_model(model)
    cell = gtk.CellRendererText()  # set up the completion renderer
    completion.pack_start(cell)
    completion.set_cell_data_func(cell, compl_cell_data_func)
    completion.props.text_column = 0
    combo.child.set_completion(completion)

    def match_func(completion, key, treeiter, data=None):
        model = completion.get_model()
        value = model[treeiter][0]
        return utf8(value).lower().startswith(key.lower())
    completion.set_match_func(match_func)

    def on_match_select(completion, model, treeiter):
        value = model[treeiter][0]
        if value:
            set_combo_from_value(combo, value)
            combo.child.props.text = utf8(value)
        else:
            combo.child.props.text = ''

    # TODO: we should be able to disconnect this signal handler
    completion.connect('match-selected', on_match_select)


def prettify_format(format):
    """
    Return the date format in a more human readable form.
    """
    f = format.replate('%Y', 'yyyy')
    f = f.replace('%m', 'mm')
    f = f.replace('%d', 'dd')
    return f


def today_str(format=None):
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


def setup_date_button(view, entry, button, date_func=None):
    """
    Associate a button with entry so that when the button is clicked a
    date is inserted into the entry.

    :param view: a bauble.editor.GenericEditorView

    :param entry: the entry that the data goes into

    :param button: the button that enters the data in entry

    :param date_func: the function that returns a string represention
      of the date
    """
    if isinstance(entry, basestring):
        entry = view.widgets[entry]
    if isinstance(button, basestring):
        button = view.widgets[button]
    icon = os.path.join(paths.lib_dir(), 'images', 'calendar.png')
    image = gtk.Image()
    image.set_from_file(icon)
    button.set_tooltip_text(_("Today's date"))
    button.set_image(image)

    def on_clicked(b):
        s = ''
        if date_func:
            s = date_func()
        else:
            s = today_str()
        entry.set_text(s)
    if view and hasattr(view, 'connect'):
        view.connect(button, 'clicked', on_clicked)
    else:
        button.connect('clicked', on_clicked)


def to_unicode(obj, encoding='utf-8'):
    """
    Return obj converted to unicode.  If obj is already a unicode
    object it will not try to decode it to converted it to <encoding>
    but will just return the original obj
    """
    if isinstance(obj, basestring):
        if not isinstance(obj, unicode):
            obj = unicode(obj, encoding)
    else:
        try:
            obj = unicode(obj, encoding)
        except Exception:
            obj = unicode(str(obj), encoding)
    return obj


def utf8(obj):
    """
    This function is an alias for to_unicode(obj, 'utf-8')
    """
    return to_unicode(obj, 'utf-8')


def xml_safe(obj, encoding='utf-8'):
    '''
    Return a string with character entities escaped safe for xml, if the
    str parameter is a string a string is returned, if str is a unicode object
    then a unicode object is returned
    '''
    obj = to_unicode(obj, encoding)
    return saxutils.escape(obj)


def xml_safe_utf8(obj):
    """
    This method is deprecated and just returns xml_safe(obj)
    """
    logger.warning('invoking deprecated function')

    return xml_safe(obj)


def safe_numeric(s):
    'evaluate the string as a number, or return zero'

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
    'evaluate the string as an integer, or return zero'

    try:
        return int(s)
    except ValueError:
        pass
    return 0


__natsort_rx = re.compile('(\d+(?:\.\d+)?)')


def natsort_key(obj):
    """
    a key getter for sort and sorted function

    the sorting is done on return value of obj.__str__() so we can sort
    generic objects as well.

    use like: sorted(some_list, key=utils.natsort_key)
    """

    item = str(obj)
    chunks = __natsort_rx.split(item)
    for ii in range(len(chunks)):
        if chunks[ii] and chunks[ii][0] in '0123456789':
            if '.' in chunks[ii]:
                numtype = float
            else:
                numtype = int
            # wrap in tuple with '0' to explicitly specify numbers come first
            chunks[ii] = (0, numtype(chunks[ii]))
        else:
            chunks[ii] = (1, chunks[ii])
    return (chunks, item)


def delete_or_expunge(obj):
    """
    If the object is in object_session(obj).new then expunge it from the
    session.  If not then session.delete it.
    """
    from sqlalchemy.orm import object_session
    session = object_session(obj)
    if session is None:
        return
    if obj not in session.new:
        logger.debug('delete obj: %s -- %s' % (obj, repr(obj)))
        session.delete(obj)
    else:
        logger.debug('expunge obj: %s -- %s' % (obj, repr(obj)))
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
    from sqlalchemy.types import Integer
    from sqlalchemy import schema
    if not db.engine.name == 'postgresql':
        return

    sequence_name = None
    if hasattr(column, 'default') and \
            isinstance(column.default, schema.Sequence):
        sequence_name = column.default.name
    elif (isinstance(column.type, Integer) and column.autoincrement) and \
            (column.default is None or
             (isinstance(column.default, schema.Sequence) and
              column.default.optional)) and \
            len(column.foreign_keys) == 0:
        sequence_name = '%s_%s_seq' % (column.table.name, column.name)
    else:
        return
    conn = db.engine.connect()
    trans = conn.begin()
    try:
        # the FOR UPDATE locks the table for the transaction
        stmt = "SELECT %s from %s FOR UPDATE;" % (
            column.name, column.table.name)
        result = conn.execute(stmt)
        maxid = None
        vals = list(result)
        if vals:
            maxid = max(vals, key=lambda x: x[0])[0]
        result.close()
        if maxid is None:
            # set the sequence to nextval()
            stmt = "SELECT nextval('%s');" % (sequence_name)
        else:
            stmt = "SELECT setval('%s', max(%s)+1) from %s;" \
                % (sequence_name, column.name, column.table.name)
        conn.execute(stmt)
    except Exception, e:
        logger.warning('bauble.utils.reset_sequence(): %s' % utf8(e))
        trans.rollback()
    else:
        trans.commit()
    finally:
        conn.close()


def make_label_clickable(label, on_clicked, *args):
    """
    :param label: a gtk.Label that has a gtk.EventBox as its parent
    :param on_clicked: callback to be called when the label is clicked
      on_clicked(label, event, data)
    """
    eventbox = label.parent

    check(eventbox is not None, 'label must have a parent')
    check(isinstance(eventbox, gtk.EventBox),
          'label must have an gtk.EventBox as its parent')
    label.__pressed = False

    def on_enter_notify(widget, *args):
        widget.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#faf8f7"))
        label.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("blue"))

    def on_leave_notify(widget, *args):
        widget.modify_bg(gtk.STATE_NORMAL, None)
        label.modify_fg(gtk.STATE_NORMAL, None)
        label.__pressed = False

    def on_press(*args):
        label.__pressed = True

    def on_release(widget, event, *args):
        if label.__pressed:
            label.__pressed = False
            label.modify_fg(gtk.STATE_NORMAL, None)
            on_clicked(label, event, *args)

    try:
        eventbox.disconnect(label.__on_event)
        logger.debug('disconnected previous release-event handler')
        label.__on_event = eventbox.connect(
            'button_release_event', on_release, *args)
    except AttributeError:
        logger.debug('defining handlers')
        label.__on_event = eventbox.connect(
            'button_release_event', on_release, *args)
        eventbox.connect('enter_notify_event', on_enter_notify)
        eventbox.connect('leave_notify_event', on_leave_notify)
        eventbox.connect('button_press_event', on_press)


def enum_values_str(col):
    """
    :param col: a string if table.col where col is an enum type

    return a string with of the values on an enum type join by a comma
    """
    import bauble.db as db
    table_name, col_name = col.split('.')
    #debug('%s.%s' % (table_name, col_name))
    values = db.metadata.tables[table_name].c[col_name].type.values[:]
    if None in values:
        values[values.index(None)] = '&lt;None&gt;'
    return ', '.join(values)


def which(filename, path=None):
    """
    Return first occurence of file on the path.
    """
    if not path:
        path = os.environ['PATH'].split(os.pathsep)
    for dirname in path:
        candidate = os.path.join(dirname, filename)
        if os.path.isfile(candidate):
            return candidate
    return None


def ilike(col, val, engine=None):
    """
    Return a cross platform ilike function.
    """
    from sqlalchemy import func
    if not engine:
        engine = bauble.db.engine
    if engine.name == 'postgresql':
        return col.op('ILIKE')(val)
    else:
        return func.lower(col).like(func.lower(val))


def range_builder(text):
    """Return a list of numbers from a string range of the form 1-3,4,5
    """
    from pyparsing import Word, Group, Suppress, delimitedList, nums, \
        ParseException, ParseResults
    rng = Group(Word(nums) + Suppress('-') + Word(nums))
    range_list = delimitedList(rng | Word(nums))

    token = None
    try:
        tokens = range_list.parseString(text)
    except (AttributeError, ParseException), e:
        logger.debug(e)
        return []
    values = set()
    for rng in tokens:
        if isinstance(rng, ParseResults):
            # get here if the token is a range
            start = int(rng[0])
            end = int(rng[1]) + 1
            check(start < end, 'start must be less than end')
            values.update(range(start, end))
        else:
            # get here if the token is an integer
            values.add(int(rng))
    return list(values)


def gc_objects_by_type(tipe):
    """
    Return a list of objects from the garbage collector by type.
    """
    import inspect
    import gc
    if isinstance(tipe, basestring):
        return [o for o in gc.get_objects() if type(o).__name__ == tipe]
    elif inspect.isclass(tipe):
        return [o for o in gc.get_objects() if isinstance(o, tipe)]
    else:
        return [o for o in gc.get_objects() if isinstance(o, type(tipe))]


def mem(size="rss"):
    """Generalization; memory sizes: rss, rsz, vsz."""
    import os
    return int(os.popen('ps -p %d -o %s | tail -1' %
                        (os.getpid(), size)).read())


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

    roots = [node for (node, nodeinfo) in graph.items() if nodeinfo[0] == 0]

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

    if len(graph.items()) != 0:
        # There is a loop in the input.
        return None

    return sorted


class GenericMessageBox(gtk.EventBox):
    """
    Abstract class for showing a message box at the top of an editor.
    """
    def __init__(self):
        super(GenericMessageBox, self).__init__()
        self.box = gtk.HBox()
        self.box.set_spacing(10)
        self.add(self.box)

    def set_color(self, attr, state, color):
        colormap = self.get_colormap()
        style = self.get_style().copy()
        c = colormap.alloc_color(color)
        getattr(style, attr)[state] = c
        # is it ok to set the style the expander and button even
        # though the style was copied from the eventbox
        self.set_style(style)
        return style

    def show_all(self):
        self.get_parent().show_all()
        width, height = self.size_request()
        self.set_size_request(width, height+10)

    def show(self):
        self.show_all()


class MessageBox(GenericMessageBox):
    """
    A MessageBox that can display a message label at the top of an editor.
    """

    def __init__(self, msg=None, details=None):
        super(MessageBox, self).__init__()
        self.vbox = gtk.VBox()
        self.box.pack_start(self.vbox)

        self.label = gtk.TextView()
        self.label.set_can_focus(False)
        self.buffer = gtk.TextBuffer()
        self.label.set_buffer(self.buffer)
        if msg:
            self.buffer.set_text(msg)
        self.vbox.pack_start(self.label, expand=True, fill=True)

        button_box = gtk.VBox()
        self.box.pack_start(button_box, expand=False, fill=False)
        button = gtk.Button()
        image = gtk.Image()
        image.set_from_stock(gtk.STOCK_CLOSE, gtk.ICON_SIZE_BUTTON)
        button.props.image = image
        button.set_relief(gtk.RELIEF_NONE)
        button_box.pack_start(button, expand=False, fill=False)

        self.details_expander = gtk.Expander(_('Show details'))
        self.vbox.pack_start(self.details_expander)

        sw = gtk.ScrolledWindow()
        sw.set_size_request(-1, 200)
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        viewport = gtk.Viewport()
        sw.add(viewport)
        self.details_label = gtk.Label()
        viewport.add(self.details_label)

        self.details = details
        self.details_expander.add(sw)

        def on_expanded(*args):
            width, height = self.size_request()
            self.set_size_request(width, -1)
            self.queue_resize()
        self.details_expander.connect('notify::expanded', on_expanded)

        def on_close(*args):
            parent = self.get_parent()
            if parent is not None:
                parent.remove(self)
        button.connect('clicked', on_close, True)

        colors = [('bg', gtk.STATE_NORMAL, '#FFFFFF'),
                  ('bg', gtk.STATE_PRELIGHT, '#FFFFFF')]
        for color in colors:
            self.set_color(*color)

    def show_all(self):
        super(MessageBox, self).show_all()
        if not self.details_label.get_text():
            self.details_expander.hide()

    def _get_message(self, msg):
        return self.buffer.text

    def _set_message(self, msg):
        # TODO: we could probably do something smarter here that
        # involved check the font size and window width and adjust the
        # wrap widget accordingly
        if msg:
            self.buffer.set_text(msg)
        else:
            self.buffer.set_text('')
    message = property(_get_message, _set_message)

    def _get_details(self, msg):
        return self.details_label.text

    def _set_details(self, msg):
        if msg:
            msg = '\n'.join(textwrap.wrap(msg, 100))
            self.details_label.set_markup(msg)
        else:
            self.details_label.set_markup('')
    details = property(_get_details, _set_details)


class YesNoMessageBox(GenericMessageBox):
    """
    A message box that can present a Yes or No question to the user
    """

    def __init__(self, msg=None, on_response=None):
        """
        on_response: callback method when the yes or no buttons are
        clicked.  The signature of the function should be
        func(button, response) where response is True/False
        depending on whether the user selected Yes or No, respectively.
        """
        super(YesNoMessageBox, self).__init__()
        self.label = gtk.Label()
        if msg:
            self.label.set_markup(msg)
        self.label.set_alignment(.1, .1)
        self.box.pack_start(self.label, expand=True, fill=True)

        button_box = gtk.VBox()
        self.box.pack_start(button_box, expand=False, fill=False)
        self.yes_button = gtk.Button(stock=gtk.STOCK_YES)
        if on_response:
            self.yes_button.connect('clicked', on_response, True)
        button_box.pack_start(self.yes_button, expand=False, fill=False)

        button_box = gtk.VBox()
        self.box.pack_start(button_box, expand=False, fill=False)
        self.no_button = gtk.Button(stock=gtk.STOCK_NO)
        if on_response:
            self.no_button.connect('clicked', on_response, False)
        button_box.pack_start(self.no_button, expand=False, fill=False)

        colors = [('bg', gtk.STATE_NORMAL, '#FFFFFF'),
                  ('bg', gtk.STATE_PRELIGHT, '#FFFFFF')]
        for color in colors:
            self.set_color(*color)

    def _set_on_response(self, func):
        self.yes_button.connect('clicked', func, True)
        self.no_button.connect('clicked', func, False)
    on_response = property(fset=_set_on_response)

    def _get_message(self, msg):
        return self.label.text

    def _set_message(self, msg):
        if msg:
            self.label.set_markup(msg)
        else:
            self.label.set_markup('')
    message = property(_get_message, _set_message)


MESSAGE_BOX_INFO = 1
MESSAGE_BOX_ERROR = 2
MESSAGE_BOX_YESNO = 3


def add_message_box(parent, type=MESSAGE_BOX_INFO):
    """
    :param parent: the parent :class:`gtk.Box` width to add the
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
        raise ValueError('unknown message box type: %s' % type)
    parent.pack_start(msg_box, expand=True, fill=True)
    return msg_box


def get_distinct_values(column, session):
    """
    Return a list of all the distinct values in a table column
    """
    q = session.query(column).distinct()
    return [v[0] for v in q if v != (None,)]


def get_invalid_columns(obj, ignore_columns=['id']):
    """
    Return column names on a mapped object that have values
    which aren't valid for the model.

    Invalid columns meet the following criteria:
    - nullable columns with null values
    - ...what else?
    """
    # TODO: check for invalid enum types
    if not obj:
        return []

    table = obj.__table__
    invalid_columns = []
    for column in filter(lambda c: c.name not in ignore_columns, table.c):
        v = getattr(obj, column.name)
        #debug('%s.%s = %s' % (table.name, column.name, v))
        if v is None and not column.nullable:
            invalid_columns.append(column.name)
    return invalid_columns


def get_urls(text):
    """
    Return tuples of http/https links and labels for the links.  To
    label a link prefix it with [label text],
    e.g. [BBG]http://belizebotanic.org
    """
    rx = re.compile('(?:\[(.+?)\])?((?:(?:http)|(?:https))://\S+)', re.I)
    matches = []
    for match in rx.finditer(text):
        #print match.groups()
        matches.append(match.groups())
    return matches
