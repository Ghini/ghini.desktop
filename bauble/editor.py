# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Brett Adams
# Copyright 2015-2017 Mario Frasca <mario@anche.no>.
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
# Description: a collection of functions and abstract classes for creating
# editors for Ghini data
#



import datetime
import os
import sys
import weakref

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

import glib
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import GdkPixbuf

from random import random
import lxml.etree as etree
from gi.repository import Pango
from sqlalchemy.orm import object_mapper, object_session
from sqlalchemy.orm.exc import UnmappedInstanceError


import bauble
import bauble.db as db
from bauble.error import check
import bauble.paths as paths
import bauble.prefs as prefs
import bauble.utils as utils
from bauble.error import CheckConditionError

# TODO: create a generic date entry that can take a mask for the date format
# see the date entries for the accession and accession source presenters


class ValidatorError(Exception):

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class Validator(object):
    """
    The interface that other validators should implement.
    """

    def to_python(self, value):
        raise NotImplementedError


from bauble.utils import parse_date

class DateValidator(Validator):
    """
    Validate that string is parseable with dateutil
    """
    def to_python(self, value):
        if not value:
            return None
        dayfirst = prefs.prefs[prefs.parse_dayfirst_pref]
        yearfirst = prefs.prefs[prefs.parse_yearfirst_pref]
        default_year = 1
        default = datetime.date(1, 1, default_year)
        try:
            date = parse_date(value, dayfirst=dayfirst,
                              yearfirst=yearfirst, default=default)
            if date.year == default_year:
                raise ValueError
        except Exception as e:
            raise ValidatorError(str(e))
        return value


# class DateTimeValidator(object):
#     pass


class StringOrNoneValidator(Validator):
    """
    If the value is an empty string then return None, else return the
    str() of the value.
    """

    def to_python(self, value):
        if value in ('', '', None):
            return None
        return str(value)


class UnicodeOrNoneValidator(Validator):
    """
    If the value is an empty unicode string then return None, else
    return the unicode() of the value. The default encoding is
    'utf-8'.
    """
    def __init__(self, encoding='utf-8'):
        self.encoding = encoding

    def to_python(self, value):
        if value in ('', '', None):
            return None
        return utils.to_unicode(value, self.encoding)


class UnicodeOrEmptyValidator(Validator):
    """
    If the value is an empty unicode string then return '', else
    return the unicode() of the value. The default encoding is
    'utf-8'.
    """
    def __init__(self, encoding='utf-8'):
        self.encoding = encoding

    def to_python(self, value):
        if not value.strip():
            return ''
        return utils.to_unicode(value, self.encoding)


class IntOrNoneStringValidator(Validator):
    """
    If the value is an int, long or can be cast to int then return the
    number, else return None
    """

    def to_python(self, value):
        if value is None or (isinstance(value, str) and value == ''):
            return None
        elif isinstance(value, int):
            return value
        try:
            return int(value)
        except Exception:
            raise ValidatorError('Could not convert value to int: %s (%s)'
                                 % (value, type(value)))


class FloatOrNoneStringValidator(Validator):
    """
    If the value is an int, long, float or can be cast to float then
    return the number, else return None
    """

    def to_python(self, value):
        if value is None or (isinstance(value, str) and value == ''):
            return None
        elif isinstance(value, (int, float)):
            return value
        try:
            return float(value)
        except Exception:
            raise ValidatorError('Could not convert value to float: %s (%s)'
                                 % (value, type(value)))


def default_completion_cell_data_func(column, renderer, model, treeiter, data=None):
    '''
    the default completion cell data function for
    GenericEditorView.attach_completions
    '''
    v = model[treeiter][0]
    renderer.set_property('markup', utils.to_unicode(v))


def default_completion_match_func(completion, key_string, treeiter):
    '''
    the default completion match function for
    GenericEditorView.attach_completions, does a case-insensitive string
    comparison of the the completions model[iter][0]
    '''
    value = completion.get_model()[treeiter][0]
    return str(value).lower().startswith(key_string.lower())


class GenericEditorView(object):
    """
    A generic class meant (not) to be subclassed, to provide the view
    for the Ghini Model-View-Presenter pattern. The idea is that you
    subclass the Presenter alone, and that the View remains as 'stupid'
    as it is conceivable.

    The presenter should interact with the view by the sole interface,
    please consider all members of the view as private, this is
    particularly true for the ones having anything to do with GTK.

    :param filename: a Gtk.Builder UI definition

    :param parent: a Gtk.Window or subclass to use as the parent
     window, if parent=None then bauble.gui.window is used
    """
    _tooltips = {}

    def __init__(self, filename, parent=None, root_widget_name=None):
        self.root_widget_name = root_widget_name
        builder = self.builder = Gtk.Builder()
        builder.add_from_file(filename)
        self.filename = filename
        self.widgets = utils.BuilderWidgets(builder)
        if parent:
            self.get_window().set_transient_for(parent)
        elif bauble.gui:
            self.get_window().set_transient_for(bauble.gui.window)
        self.response = None
        self.__attached_signals = []
        self.boxes = set()

        # set the tooltips...use Gtk.Tooltip api introducted in GTK+ 2.12
        for widget_name, markup in self._tooltips.items():
            try:
                self.widgets[widget_name].set_tooltip_markup(markup)
            except Exception as e:
                values = dict(widget_name=widget_name, exception=e)
                logger.debug(_('Couldn\'t set the tooltip on widget '
                               '%(widget_name)s\n\n%(exception)s') % values)

        try:
            window = self.get_window()
        except:
            window = None
        if window is not None:
            self.connect(window, 'delete-event', self.on_window_delete)
            if isinstance(window, Gtk.Dialog):
                self.connect(window, 'close', self.on_dialog_close)
                self.connect(window, 'response', self.on_dialog_response)
        self.box = set()  # the top level, meant for warnings.

    def cancel_threads(self):
        pass

    def update(self):
        pass

    def run_file_chooser_dialog(
            self, text, parent, action, buttons, last_folder, target):
        """create and run FileChooserDialog, then write result in target

        this is just a bit more than a wrapper. it adds 'last_folder', a
        string indicationg the location where to put the FileChooserDialog,
        and 'target', an Entry widget or its name.

        make sure you have a Gtk.ResponseType.ACCEPT button.

        """
        chooser = Gtk.FileChooserDialog(text, parent, action, buttons)
        #chooser.set_do_overwrite_confirmation(True)
        #chooser.connect("confirm-overwrite", confirm_overwrite_callback)
        try:
            if last_folder:
                chooser.set_current_folder(last_folder)
            if chooser.run() == Gtk.ResponseType.ACCEPT:
                filename = chooser.get_filename()
                if filename:
                    self.widget_set_value(target, filename)
        except Exception as e:
            logger.warning("unhandled %s exception in editor.py: %s" %
                           (type(e), e))
        chooser.destroy()

    def run_entry_dialog(self, title, parent, flags, buttons, visible=True):
        d = Gtk.Dialog(title, parent, flags, buttons)
        d.set_default_response(Gtk.ResponseType.ACCEPT)
        d.set_default_size(250, -1)
        entry = Gtk.Entry()
        if visible is not True:
            entry.set_visibility(False)
        entry.connect("activate",
                      lambda entry: d.response(Gtk.ResponseType.ACCEPT))
        d.vbox.pack_start(entry, True, True, 0)
        d.show_all()
        d.run()
        user_reply = entry.get_text()
        d.destroy()
        return user_reply

    def run_message_dialog(self, msg, type=Gtk.MessageType.INFO,
                           buttons=Gtk.ButtonsType.OK, parent=None):
        utils.message_dialog(msg, type, buttons, parent)

    def run_yes_no_dialog(self, msg, parent=None, yes_delay=-1):
        return utils.yes_no_dialog(msg, parent, yes_delay)

    def get_selection(self):
        '''return the selection in the graphic interface'''
        class EmptySelectionException(Exception):
            pass
        from bauble.view import SearchView
        view = bauble.gui.get_view()
        try:
            check(isinstance(view, SearchView))
            tree_view = view.results_view.get_model()
            check(tree_view is not None)
        except CheckConditionError:
            self.run_message_dialog(_('Search for something first.'))
            return

        return [row[0] for row in tree_view]

    def set_title(self, title):
        self.get_window().set_title(title)

    def set_icon(self, icon):
        self.get_window().set_icon(icon)

    def image_set_from_file(self, widget, value):
        widget = (isinstance(widget, Gtk.Widget)
                  and widget
                  or self.widgets[widget])
        widget.set_from_file(value)

    def set_label(self, widget_name, value):
        getattr(self.widgets, widget_name).set_markup(value)

    def close_boxes(self):
        while self.boxes:
            logger.debug('box is being forcibly removed')
            box = self.boxes.pop()
            self.widgets.remove_parent(box)
            box.destroy()

    def add_box(self, box):
        logger.debug('box is being added')
        self.boxes.add(box)

    def remove_box(self, box):
        logger.debug('box is being removed')
        if box in self.boxes:
            self.boxes.remove(box)
            self.widgets.remove_parent(box)
            box.destroy()
        else:
            logger.debug('box to be removed is not there')

    def add_message_box(self, message_box_type=utils.MESSAGE_BOX_INFO):
        """add a message box to the message_box_parent container

        :param type: one of MESSAGE_BOX_INFO, MESSAGE_BOX_ERROR or
          MESSAGE_BOX_YESNO
        """
        return utils.add_message_box(self.widgets.message_box_parent,
                                     message_box_type)

    def connect_signals(self, target):
        'connect all signals declared in the glade file'
        if not hasattr(self, 'signals'):
            from lxml import etree
            doc = etree.parse(self.filename)
            self.signals = doc.xpath('//signal')
        for s in self.signals:
            try:
                handler = getattr(target, s.get('handler'))
            except AttributeError as text:
                logger.debug("AttributeError: %s" % text)
                continue
            signaller = getattr(self.widgets, s.getparent().get('id'))
            handler_id = signaller.connect(s.get('name'), handler)
            self.__attached_signals.append((signaller, handler_id))

    def set_accept_buttons_sensitive(self, sensitive):
        '''set the sensitivity of all the accept/ok buttons

        '''
        for wname in self.accept_buttons:
            getattr(self.widgets, wname).set_sensitive(sensitive)

    def connect(self, obj, signal, callback, *args):
        """
        Attach a signal handler for signal on obj.  For more
        information see :meth:`GObject.connect_after`

        :param obj: An instance of a subclass of gobject that will
          receive the signal

        :param signal: the name of the signal the object will receive

        :param callback: the function or method to call the object
          receives the signal

        :param args: extra args to pass the the callback
        """
        if isinstance(obj, str):
            obj = self.widgets[obj]
        sid = obj.connect(signal, callback, *args)
        self.__attached_signals.append((obj, sid))
        return sid

    def connect_after(self, obj, signal, callback, *args):  # data=None):
        """
        Attach a signal handler for signal on obj.  For more
        information see :meth:`GObject.connect_after`

        :param obj: An instance of a subclass of gobject that will
          receive the signal

        :param signal: the name of the signal the object will receive

        :param callback: the function or method to call the object
          receives the signal

        :param args: extra args to pass the the callback
        """
        if isinstance(obj, str):
            obj = self.widgets[obj]
        sid = obj.connect_after(signal, callback, *args)
        # if data:
        #     sid = obj.connect_after(signal, callback, data)
        # else:
        #     sid = obj.connect_after(signal, callback)
        self.__attached_signals.append((obj, sid))
        return sid

    def disconnect_all(self):
        """
        Disconnects all the signal handlers attached with
        :meth:`GenericEditorView.connect` or
        :meth:`GenericEditorView.connect_after`
        """
        logger.debug('GenericEditorView:disconnect_all')
        for obj, sid in self.__attached_signals:
            obj.disconnect(sid)
        del self.__attached_signals[:]

    def disconnect_widget_signals(self, widget):
        """disconnect all signals attached to widget"""

        removed = []
        for obj, sid in self.__attached_signals:
            if obj == widget:
                widget.disconnect(sid)
                removed.append((obj, sid))

        for item in removed:
            self.__attached_signals.remove(item)

    def get_window(self):
        """
        Return the top level window for view
        """
        if self.root_widget_name is not None:
            return getattr(self.widgets, self.root_widget_name)
        else:
            raise NotImplementedError

    def __get_widget(self, widget):
        p = widget
        if isinstance(widget, Gtk.Widget):
            return widget
        elif isinstance(widget, tuple):
            if len(widget) == 1:
                return self.__get_widget(widget[0])
            parent, widget = widget[:-1], widget[-1]
            parent = self.__get_widget(parent)
            for c in parent.get_children():
                if Gtk.Buildable.get_name(c) == widget:
                    return c
        else:
            return self.widgets[widget]
        logger.warn('cannot solve widget reference %s' % str(p))
        return None

    def widget_append_page(self, widget, page, label):
        widget = self.__get_widget(widget)
        widget.append_page(page, label)

    def widget_add(self, widget, child):
        widget = self.__get_widget(widget)
        widget.add(child)

    def widget_get_model(self, widget):
        widget = self.__get_widget(widget)
        return widget.get_model()

    def widget_grab_focus(self, widget):
        widget = self.__get_widget(widget)
        return widget.grab_focus()

    def widget_get_active(self, widget):
        widget = self.__get_widget(widget)
        return widget.get_active()

    def widget_set_active(self, widget, active=True):
        widget = self.__get_widget(widget)
        return widget.set_active(active)

    def widget_set_attributes(self, widget, attribs):
        widget = self.__get_widget(widget)
        return widget.set_attributes(attribs)

    def widget_set_inconsistent(self, widget, value):
        widget = self.__get_widget(widget)
        widget.set_inconsistent(value)

    def combobox_init(self, widget, values=None, cell_data_func=None):
        combo = self.__get_widget(widget)
        model = Gtk.ListStore(str)
        combo.clear()
        combo.set_model(model)
        renderer = Gtk.CellRendererText()
        combo.pack_start(renderer, True)
        combo.add_attribute(renderer, 'text', 0)
        self.combobox_setup(combo, values, cell_data_func)

    def combobox_setup(self, combo, values, cell_data_func):
        if values is None:
            return
        return utils.setup_text_combobox(combo, values, cell_data_func)

    def combobox_remove(self, widget, item):
        widget = self.__get_widget(widget)
        if isinstance(item, str):
            # remove matching
            model = widget.get_model()
            for i, row in enumerate(model):
                if item == row[0]:
                    widget.remove_text(i)
                    break
            logger.warning("combobox_remove - not found >%s<" % item)
        elif isinstance(item, int):
            # remove at position
            widget.remove_text(item)
        else:
            logger.warning('invoked combobox_remove with item=(%s)%s' %
                           (type(item), item))

    def combobox_append_text(self, widget, value):
        widget = self.__get_widget(widget)
        widget.append_text(value)

    def combobox_prepend_text(self, widget, value):
        widget = self.__get_widget(widget)
        widget.prepend_text(value)

    def combobox_get_active_text(self, widget):
        widget = self.__get_widget(widget)
        return widget.get_active_text()

    def combobox_get_active(self, widget):
        widget = self.__get_widget(widget)
        return widget.get_active()

    def combobox_set_active(self, widget, index):
        widget = self.__get_widget(widget)
        widget.set_active(index)

    def combobox_get_model(self, widget):
        'get the list of values in the combo'
        widget = self.__get_widget(widget)
        return widget.get_model()

    def widget_emit(self, widget, value):
        widget = self.__get_widget(widget)
        widget.emit(value)

    def widget_set_expanded(self, widget, value):
        widget = self.__get_widget(widget)
        widget.set_expanded(value)

    def widget_set_sensitive(self, widget, value=True):
        widget = self.__get_widget(widget)
        widget.set_sensitive(value and True or False)

    def widget_set_visible(self, widget, visible=True):
        widget = self.__get_widget(widget)
        widget.set_visible(visible)

    def widget_get_visible(self, widget):
        widget = self.__get_widget(widget)
        return widget.get_visible()

    def widget_set_text(self, widget, text):
        widget = self.__get_widget(widget)
        widget.set_text(text)

    def widget_get_text(self, widget):
        widget = self.__get_widget(widget)
        return widget.get_text()

    def widget_get_value(self, widget, index=0):
        widget = self.__get_widget(widget)
        return utils.get_widget_value(widget, index)

    def widget_set_value(self, widget, value, markup=False, default=None,
                         index=0):
        '''
        :param widget: a widget or name of a widget in self.widgets
        :param value: the value to put in the widgets
        :param markup: whether the data in value uses pango markup
        :param default: the default value to put in the widget if value is None
        :param index: the row index to use for those widgets who use a model

        This method calls bauble.utils.set_widget_value()
        '''
        if isinstance(widget, Gtk.Widget):
            utils.set_widget_value(widget, value, markup, default, index)
        else:
            utils.set_widget_value(self.widgets[widget], value, markup,
                                   default, index)

    def on_dialog_response(self, dialog, response, *args):
        '''
        Called if self.get_window() is a Gtk.Dialog and it receives
        the response signal.
        '''
        logger.debug('on_dialog_response')
        dialog.hide()
        self.response = response
        return response

    def on_dialog_close(self, dialog, event=None):
        """
        Called if self.get_window() is a Gtk.Dialog and it receives
        the close signal.
        """
        logger.debug('on_dialog_close')
        dialog.hide()
        return False

    def on_window_delete(self, window, event=None):
        """
        Called when the window return by get_window() receives the
        delete event.
        """
        logger.debug('on_window_delete')
        window.hide()
        return False

    def attach_completion(self, entry,
                          cell_data_func=default_completion_cell_data_func,
                          match_func=default_completion_match_func,
                          minimum_key_length=2,
                          text_column=-1):
        """
        Attach an entry completion to a Gtk.Entry.  The defaults
        values for this attach_completion assumes the completion popup
        only shows text and that the text is in the first column of
        the model.

        Return the completion attached to the entry.

        NOTE: If you are selecting completions from strings in your model
        you must set the text_column parameter to the column in the
        model that holds the strings or else when you select the string
        from the completions it won't get set properly in the entry
        even though you call entry.set_text().

        :param entry: the name of the entry to attach the completion

        :param cell_data_func: the function to use to display the rows in
          the completion popup

        :param match_func: a function that returns True/False if the
          value from the model should be shown in the completions

        :param minimum_key_length: default=2

        :param text_column: the value of the text-column property on the entry,
          default is -1
        """

        # TODO: we should add a default ctrl-space to show the list of
        # completions regardless of the length of the string
        completion = Gtk.EntryCompletion()
        cell = Gtk.CellRendererText()  # set up the completion renderer
        completion.pack_start(cell, True)
        completion.set_cell_data_func(cell, cell_data_func)
        completion.set_match_func(match_func)
        completion.set_property('text-column', text_column)
        completion.set_minimum_key_length(minimum_key_length)
        completion.set_popup_completion(True)
        completion.props.popup_set_width = False
        if isinstance(entry, str):
            self.widgets[entry].set_completion(completion)
        else:
            entry.set_completion(completion)

        # allow later access to the match func just in case
        completion._match_func = match_func

        return completion

    # TODO: add a default value to set in the combo
    def init_translatable_combo(self, combo, translations, default=None,
                                cmp=None):
        """
        Initialize a Gtk.ComboBox with translations values where
        model[row][0] is the value that will be stored in the database
        and model[row][1] is the value that will be visible in the
        Gtk.ComboBox.

        A Gtk.ComboBox initialized with this method should work with
        self.assign_simple_handler()

        :param combo:
        :param translations: a list of pairs, or a dictionary,
            of values->translation.
        """
        if isinstance(combo, str):
            combo = self.widgets[combo]
        combo.clear()
        # using 'object' avoids SA unicode warning
        model = Gtk.ListStore(object, str)
        if isinstance(translations, dict):
            translations = sorted(iter(translations.items()), key=lambda x: x[1])
        if cmp is not None:
            translations = sorted(translations,
                                  key=lambda a: a[0])
        for key, value in translations:
            model.append([key, value])
        combo.set_model(model)
        cell = Gtk.CellRendererText()
        combo.pack_start(cell, True)
        combo.add_attribute(cell, 'text', 1)

    def save_state(self):
        '''
        Save the state of the view by setting a value in the preferences
        that will be called restored in restore_state
        e.g. prefs[pref_string] = pref_value
        '''
        pass

    def restore_state(self):
        '''
        Restore the state of the view, this is usually done by getting a value
        by the preferences and setting the equivalent in the interface
        '''
        pass

    def start(self):
        ## while being ran, the view will invoke callbacks in the presenter
        ## which, in turn, will alter the attributes in the model.
        return self.get_window().run()

    def cleanup(self):
        """
        Should be called when after self.start() returns.

        By default all it does is call self.disconnect_all()
        """
        self.disconnect_all()

    def mark_problem(self, widget):
        pass


class MockDialog:
    def __init__(self):
        self.hidden = False
        self.content_area = Gtk.VBox()

    def hide(self):
        self.hidden = True

    def run(self):
        pass

    def show(self):
        pass

    def add_accel_group(self, group):
        pass

    def get_content_area(self):
        return self.content_area


class MockView:
    '''mocking the view, but so generic that we share it among clients
    '''
    def __init__(self, **kwargs):
        self.widgets = type('MockWidgets', (object, ), {})()
        self.models = {}  # dictionary of list of tuples
        self.invoked = []
        self.invoked_detailed = []
        self.visible = {}
        self.sensitive = {}
        self.expanded = {}
        self.values = {}
        self.index = {}
        self.selection = []
        self.reply_entry_dialog = []
        self.reply_yes_no_dialog = []
        self.reply_file_chooser_dialog = []
        self.__window = MockDialog()
        for name, value in list(kwargs.items()):
            setattr(self, name, value)
        self.boxes = set()

    def init_translatable_combo(self, *args):
        self.invoked.append('init_translatable_combo')
        self.invoked_detailed.append((self.invoked[-1], args))
        pass

    def get_selection(self):
        'fakes main UI search result - selection'
        return self.selection

    def image_set_from_file(self, *args):
        self.invoked.append('image_set_from_file')
        self.invoked_detailed.append((self.invoked[-1], args))
        pass

    def run_file_chooser_dialog(
            self, text, parent, action, buttons, last_folder, target):
        args = [text, parent, action, buttons, last_folder, target]
        self.invoked.append('run_file_chooser_dialog')
        self.invoked_detailed.append((self.invoked[-1], args))
        try:
            reply = self.reply_file_chooser_dialog.pop()
        except:
            reply = ''
        self.widget_set_value(target, reply)

    def run_entry_dialog(self, *args, **kwargs):
        self.invoked.append('run_entry_dialog')
        self.invoked_detailed.append((self.invoked[-1], args))
        try:
            return self.reply_entry_dialog.pop()
        except:
            return ''

    def run_message_dialog(self, msg, type=Gtk.MessageType.INFO,
                           buttons=Gtk.ButtonsType.OK, parent=None):
        self.invoked.append('run_message_dialog')
        args = [msg, type, buttons, parent]
        self.invoked_detailed.append((self.invoked[-1], args))

    def run_yes_no_dialog(self, msg, parent=None, yes_delay=-1):
        self.invoked.append('run_yes_no_dialog')
        args = [msg, parent, yes_delay]
        self.invoked_detailed.append((self.invoked[-1], args))
        try:
            return self.reply_yes_no_dialog.pop()
        except:
            return True

    def set_title(self, *args):
        self.invoked.append('set_title')
        self.invoked_detailed.append((self.invoked[-1], args))
        pass

    def set_icon(self, *args):
        self.invoked.append('set_icon')
        self.invoked_detailed.append((self.invoked[-1], args))
        pass

    def combobox_init(self, name, values=None, *args):
        self.invoked.append('combobox_init')
        self.invoked_detailed.append((self.invoked[-1], [name, values, args]))
        self.models[name] = []
        for i in values or []:
            self.models[name].append((i, ))

    def connect_signals(self, *args):
        self.invoked.append('connect_signals')
        self.invoked_detailed.append((self.invoked[-1], args))
        pass

    def set_label(self, *args):
        self.invoked.append('set_label')
        self.invoked_detailed.append((self.invoked[-1], args))
        pass

    def connect_after(self, *args):
        self.invoked.append('connect_after')
        self.invoked_detailed.append((self.invoked[-1], args))
        pass

    def widget_get_value(self, widget, *args):
        self.invoked.append('widget_get_value')
        self.invoked_detailed.append((self.invoked[-1], [widget, args]))
        return self.values.get(widget)

    def widget_set_value(self, widget, value, *args):
        self.invoked.append('widget_set_value')
        self.invoked_detailed.append((self.invoked[-1], [widget, value, args]))
        self.values[widget] = value
        if widget in self.models:
            if (value, ) in self.models[widget]:
                self.index[widget] = self.models[widget].index((value, ))
            else:
                self.index[widget] = -1

    def connect(self, *args):
        self.invoked.append('connect')
        self.invoked_detailed.append((self.invoked[-1], args))
        pass

    def widget_get_visible(self, name):
        self.invoked.append('widget_get_visible')
        self.invoked_detailed.append((self.invoked[-1], [name]))
        return self.visible.get(name)

    def widget_set_visible(self, name, value=True):
        self.invoked.append('widget_set_visible')
        self.invoked_detailed.append((self.invoked[-1], [name, value]))
        self.visible[name] = value

    def widget_set_expanded(self, widget, value):
        self.invoked.append('widget_set_expanded')
        self.invoked_detailed.append((self.invoked[-1], [widget, value]))
        self.expanded[widget] = value

    def widget_set_sensitive(self, name, value=True):
        self.invoked.append('widget_set_sensitive')
        self.invoked_detailed.append((self.invoked[-1], [name, value]))
        self.sensitive[name] = value and True or False

    def widget_get_sensitive(self, name):
        self.invoked.append('widget_get_sensitive')
        self.invoked_detailed.append((self.invoked[-1], [name]))
        return self.sensitive[name]

    def widget_set_inconsistent(self, *args):
        self.invoked.append('widget_set_inconsistent')
        self.invoked_detailed.append((self.invoked[-1], args))
        pass

    def widget_get_text(self, widget, *args):
        self.invoked.append('widget_get_text')
        self.invoked_detailed.append((self.invoked[-1], [widget, args]))
        return self.values[widget]

    def widget_set_text(self, *args):
        self.invoked.append('widget_set_text')
        self.invoked_detailed.append((self.invoked[-1], args))
        self.values[args[0]] = args[1]

    def widget_grab_focus(self, *args):
        self.invoked.append('widget_grab_focus')
        self.invoked_detailed.append((self.invoked[-1], args))

    def widget_set_active(self, *args):
        self.invoked.append('widget_set_active')
        self.invoked_detailed.append((self.invoked[-1], args))

    def widget_set_attributes(self, *args):
        self.invoked.append('widget_set_attributes')
        self.invoked_detailed.append((self.invoked[-1], args))

    def get_window(self):
        self.invoked.append('get_window')
        self.invoked_detailed.append((self.invoked[-1], []))
        return self.__window

    widget_get_active = widget_get_value

    def combobox_remove(self, name, item):
        self.invoked.append('combobox_remove')
        self.invoked_detailed.append((self.invoked[-1], [name, item]))
        model = self.models.setdefault(name, [])
        if isinstance(item, int):
            del model[item]
        else:
            model.remove((item, ))

    def combobox_append_text(self, name, value):
        self.invoked.append('combobox_append_text')
        self.invoked_detailed.append((self.invoked[-1], [name, value]))
        model = self.models.setdefault(name, [])
        model.append((value, ))

    def combobox_prepend_text(self, name, value):
        self.invoked.append('combobox_prepend_text')
        self.invoked_detailed.append((self.invoked[-1], [name, value]))
        model = self.models.setdefault(name, [])
        model.insert(0, (value, ))

    def combobox_set_active(self, widget, index):
        self.invoked.append('combobox_set_active')
        self.invoked_detailed.append((self.invoked[-1], [widget, index]))
        self.index[widget] = index
        self.values[widget] = self.models[widget][index][0]

    def combobox_get_active_text(self, widget):
        self.invoked.append('combobox_get_active_text')
        self.invoked_detailed.append((self.invoked[-1], [widget, ]))
        return self.values[widget]

    def combobox_get_active(self, widget):
        self.invoked.append('combobox_get_active')
        self.invoked_detailed.append((self.invoked[-1], [widget, ]))
        return self.index.setdefault(widget, 0)

    def combobox_get_model(self, widget):
        self.invoked.append('combobox_get_model')
        self.invoked_detailed.append((self.invoked[-1], [widget, ]))
        return self.models[widget]

    def set_accept_buttons_sensitive(self, sensitive=True):
        self.invoked.append('set_accept_buttons_sensitive')
        self.invoked_detailed.append((self.invoked[-1], [sensitive, ]))
        pass

    def mark_problem(self, widget):
        pass

    def add_message_box(self, message_box_type=utils.MESSAGE_BOX_INFO):
        self.invoked.append('set_accept_buttons_sensitive')
        self.invoked_detailed.append((self.invoked[-1], [message_box_type, ]))
        return MockDialog()

    def add_box(self, box):
        self.invoked.append('add_box')
        self.invoked_detailed.append((self.invoked[-1], [box, ]))
        self.boxes.add(box)

    def remove_box(self, box):
        self.invoked.append('remove_box')
        self.invoked_detailed.append((self.invoked[-1], [box, ]))
        if box in self.boxes:
            self.boxes.remove(box)


class DontCommitException(Exception):
    """
    This is used for GenericModelViewPresenterEditor.commit_changes() to
    signal that for some reason the editor doesn't want to commit the current
    values and would like to redisplay
    """
    pass


class GenericEditorPresenter(object):
    """
    The presenter of the Model View Presenter Pattern

    :param model: an object instance mapped to an SQLAlchemy table
    :param view: should be an instance of GenericEditorView

    The presenter should usually be initialized in the following order:
    1. initialize the widgets
    2. refresh the view, put values from the model into the widgets
    3. connect the signal handlers
    """
    problem_color = Gdk.color_parse('#FFDCDF')
    widget_to_field_map = {}
    view_accept_buttons = []

    PROBLEM_DUPLICATE = random()
    PROBLEM_EMPTY = random()

    def __init__(self, model, view, refresh_view=False, session=None,
                 do_commit=False, committing_results=[Gtk.ResponseType.OK]):
        self.model = model
        self.view = view
        self.problems = set()
        self._dirty = False
        self.is_committing_presenter = do_commit
        self.committing_results = committing_results
        self.running_threads = []
        self.owns_session = False
        self.session = session
        self.clipboard_presenters = []
        if not hasattr(self.__class__, 'clipboard'):
            logging.debug('creating clipboard in presenter class %s' % self.__class__.__name__)
            self.__class__.clipboard = {}

        if session is None:
            try:
                self.session = object_session(model)
            except Exception as e:
                logger.debug("GenericEditorPresenter::__init__ - %s, %s" % (type(e), e))

            if self.session is None:  # object_session gave None without error
                if db.Session is not None:
                    self.session = db.Session()
                    self.owns_session = True
                    if isinstance(model, db.Base):
                        self.model = model = self.session.merge(model)
                else:
                    logger.debug('db.Session was None, I cannot get a session.')
                    self.session = None

        if view:
            view.accept_buttons = self.view_accept_buttons
            if model and refresh_view:
                self.refresh_view()
            view.connect_signals(self)

    def create_toolbar(self, *args, **kwargs):
        view, model = self.view, self.model
        logging.debug('creating toolbar in content_area presenter %s' % self.__class__.__name__)
        actiongroup = Gtk.ActionGroup('window-clip-actions')
        accelgroup = Gtk.AccelGroup()
        fake_toolbar = Gtk.Toolbar()
        fake_toolbar.set_name('toolbar')
        view.get_window().add_accel_group(accelgroup)
        view.get_window().get_content_area().pack_start(fake_toolbar, True, True, 0)
        for shortcut, cb in (('<ctrl><shift>c', self.on_window_clip_copy),
                             ('<ctrl><shift>v', self.on_window_clip_paste)):
            action = Gtk.Action(shortcut, shortcut, 'clip-action', None)
            actiongroup.add_action_with_accel(action, shortcut)
            action.connect("activate", cb)
            action.set_accel_group(accelgroup)
            action.connect_accelerator()
            toolitem = action.create_tool_item()
            fake_toolbar.insert(toolitem, -1)
        fake_toolbar.set_visible(False)
        self.clipboard_presenters.append(self)

    def register_clipboard(self):
        parent = self.parent_ref()
        parent.clipboard_presenters.append(self)

    def on_window_clip_copy(self, widget, *args, **kwargs):
        try:
            notebook = self.view.widgets['notebook']
            current_page_no = notebook.get_current_page()
            current_page_widget = notebook.get_nth_page(current_page_no)
        except:
            notebook = None
            current_page_widget = self.view.get_window().get_content_area()
        for presenter in self.clipboard_presenters:
            for name in presenter.widget_to_field_map:
                container = presenter.view.widgets[name]
                while container.parent != notebook:
                    if current_page_widget == container:
                        break
                    container = container.parent
                if current_page_widget == container:
                    value = presenter.view.widget_get_value(name)
                    logger.debug('writing »%s« in clipboard %s for %s' % (value, presenter.__class__.__name__, name))
                    presenter.clipboard[name] = value

    def on_window_clip_paste(self, widget, *args, **kwargs):
        try:
            notebook = self.view.widgets['notebook']
            current_page_no = notebook.get_current_page()
            current_page_widget = notebook.get_nth_page(current_page_no)
        except:
            notebook = None
            current_page_widget = self.view.get_window().get_content_area()
        for presenter in self.clipboard_presenters:
            for name in presenter.widget_to_field_map:
                container = presenter.view.widgets[name]
                while container.parent != notebook:
                    if current_page_widget == container:
                        break
                    container = container.parent
                if current_page_widget == container:
                    if presenter.view.widget_get_value(name):
                        logger.debug('skipping %s in clipboard %s because widget has value' % (name, presenter.__class__.__name__))
                        continue
                    clipboard_value = presenter.clipboard.get(name)
                    if not clipboard_value:
                        logger.debug('skipping %s because clipboard %s has no value' % (name, presenter.__class__.__name__))
                        continue
                    logger.debug('setting »%s« from clipboard %s for %s' % (clipboard_value, presenter.__class__.__name__, name))
                    presenter.view.widget_set_value(name, clipboard_value)

    def refresh_sensitivity(self):
        logger.debug('you should implement this in your subclass')

    def refresh_view(self):
        '''fill the values in the widgets as the field values in the model

        for radio button groups, we have several widgets all referring
        to the same model attribute.

         '''
        for widget, attr in list(self.widget_to_field_map.items()):
            value = getattr(self.model, attr)
            value = (value is not None) and value or ''
            self.view.widget_set_value(widget, value)

    def cancel_threads(self):
        for k in self.running_threads:
            k.cancel()
        for k in self.running_threads:
            k.join()
        self.running_threads = []

    def start_thread(self, thread):
        self.running_threads.append(thread)
        thread.start()
        return thread

    def commit_changes(self):
        '''
        Commit the changes to self.session()
        '''
        objs = list(self.session)
        try:
            self.session.commit()
            try:
                bauble.gui.get_view().update()
            except Exception as e:
                pass
        except Exception as e:
            self.session.rollback()
            self.session.add_all(objs)
            raise
        finally:
            if self.owns_session:
                self.session.close()
        return True

    def __set_model_attr(self, attr, value):
        if getattr(self.model, attr) != value:
            setattr(self.model, attr, value)
            self._dirty = True
            self.view._dirty = True
            self.view.set_accept_buttons_sensitive(not self.has_problems())

    def __get_widget_name(self, widget):
        return (isinstance(widget, str)
                and widget
                or Gtk.Buildable.get_name(widget))

    widget_get_name = __get_widget_name

    def __get_widget_attr(self, widget):
        return self.widget_to_field_map.get(self.__get_widget_name(widget))

    def on_textbuffer_changed(self, widget, value=None, attr=None):
        """handle 'changed' signal on textbuffer widgets.

        this will not work directly. check the unanswered question
        http://stackoverflow.com/questions/32106765/

        to use it, you need pass the `attr` yourself.
        """

        if attr is None:
            attr = self.__get_widget_attr(widget)
        if attr is None:
            return
        if value is None:
            value = widget.props.text
            value = value and utils.utf8(value) or None
        logger.debug("on_text_entry_changed(%s, %s) - %s → %s"
                     % (widget, attr, getattr(self.model, attr), value))
        self.__set_model_attr(attr, value)

    def on_text_entry_changed(self, widget, value=None):
        "handle 'changed' signal on generic text entry widgets."

        attr = self.__get_widget_attr(widget)
        if attr is None:
            return
        value = self.view.widget_get_value(widget)
        logger.debug("on_text_entry_changed(%s, %s) - %s → %s"
                     % (widget, attr, getattr(self.model, attr), value))
        self.__set_model_attr(attr, value)
        return value

    def on_numeric_text_entry_changed(self, widget, value=None):
        "handle 'changed' signal on numeric text entry widgets."

        attr = self.__get_widget_attr(widget)
        if attr is None:
            return
        value = self.view.widget_get_value(widget)
        if value == '':
            value = 0
        try:
            value = int(value)
            logger.debug("on_text_entry_changed(%s, %s) - %s → %s"
                         % (widget, attr, getattr(self.model, attr), value))
            self.__set_model_attr(attr, value)
        except:
            value = getattr(self.model, attr)
            self.view.widget_set_value(widget, value)
        return value

    def on_non_empty_text_entry_changed(self, widget, value=None):
        "handle 'changed' signal on compulsory text entry widgets."

        value = self.on_text_entry_changed(widget, value)
        if not value:
            self.add_problem(self.PROBLEM_EMPTY, widget)
        else:
            self.remove_problem(self.PROBLEM_EMPTY, widget)
        return value

    def on_unique_text_entry_changed(self, widget, value=None):
        "handle 'changed' signal on text entry widgets with an uniqueness "
        "constraint."

        attr = self.__get_widget_attr(widget)
        if attr is None:
            return
        if value is None:
            value = widget.props.text
            value = value and utils.utf8(value) or None
        if not value:
            self.add_problem(self.PROBLEM_EMPTY, widget)
        else:
            self.remove_problem(self.PROBLEM_EMPTY, widget)
        if getattr(self.model, attr) == value:
            return
        logger.debug("on_unique_text_entry_changed(%s, %s) - %s → %s"
                     % (widget, attr, getattr(self.model, attr), value))
        ## check uniqueness
        klass = self.model.__class__
        k_attr = getattr(klass, attr)
        q = self.session.query(klass)
        q = q.filter(k_attr == value)
        omonym = q.first()
        if omonym is not None and omonym is not self.model:
            self.add_problem(self.PROBLEM_DUPLICATE, widget)
        else:
            self.remove_problem(self.PROBLEM_DUPLICATE, widget)
        ## ok
        self.__set_model_attr(attr, value)

    def on_datetime_entry_changed(self, widget, value=None):
        "handle 'changed' signal on datetime entry widgets."

        attr = self.__get_widget_attr(widget)
        logger.debug("on_datetime_entry_changed(%s, %s)" % (widget, attr))
        if value is None:
            value = widget.props.text
            value = value and utils.utf8(value) or None
        self.__set_model_attr(attr, value)

    def on_check_toggled(self, widget, value=None):
        "handle toggled signal on check buttons"
        attr = self.__get_widget_attr(widget)
        if value is None:
            value = self.view.widget_get_active(widget)
            self.view.widget_set_inconsistent(widget, False)
        if attr is not None:
            self.__set_model_attr(attr, value)
        else:
            logging.debug("presenter %s does not know widget %s" % (
                self.__class__.__name__, self.__get_widget_name(widget)))

    on_chkbx_toggled = on_check_toggled

    def on_relation_entry_changed(self, widget, value=None):
        attr = self.__get_widget_attr(widget)
        logger.debug(
            'calling unimplemented on_relation_entry_changed(%s, %s, %s(%s))'
            % (widget, attr, type(value), value))

    def on_group_changed(self, widget, *args):
        "handle group-changed signal on radio-button"
        if args:
            logger.warning("on_group_changed received extra arguments" +
                           str(args))
        attr = self.__get_widget_attr(widget)
        value = self.__get_widget_name(widget)
        self.__set_model_attr(attr, value)

    def on_combo_changed(self, widget, value=None, *args):
        """handle changed signal on combo box

        value is only specified while testing"""
        attr = self.__get_widget_attr(widget)
        if value is None:
            index = self.view.combobox_get_active(widget)
            widget_model = self.view.combobox_get_model(widget)
            value = widget_model[index][0]
        self.__set_model_attr(attr, value)
        self.refresh_view()

    def dirty(self):
        logger.info('calling deprecated "dirty". use "is_dirty".')
        return self.is_dirty()

    # whether the presenter should be commited or not
    def is_dirty(self):
        """is the presenter dirty?

        the presenter is dirty depending on whether it has changed anything
        that needs to be committed.  This doesn't necessarily imply that the
        session is not dirty nor is it required to change back to True if
        the changes are committed.
        """
        return self._dirty

    def has_problems(self, widget=None):
        """
        Return True/False depending on if widget has any problems
        attached to it. if no widget is specified, result is True if
        there is any problem at all.
        """
        if widget is None:
            return self.problems and True or False
        for p, w in self.problems:
            if widget == w:
                return True
        return False

    def clear_problems(self):
        """
        Clear all the problems from all widgets associated with the presenter
        """
        tmp = self.problems.copy()
        list(map(lambda p: self.remove_problem(p[0], p[1]), tmp))
        self.problems.clear()

    def remove_problem(self, problem_id, widget=None):
        """
        Remove problem_id from self.problems and reset the background
        color of the widget(s) in problem_widgets.  If problem_id is
        None and problem_widgets is None then method won't do anything.

        :param problem_id: the problem to remove, if None then remove
         any problem from the problem_widget(s)

        :param problem_widgets: a Gtk.Widget instance to remove the problem
         from, if None then remove all occurrences of problem_id regardless
         of the widget
        """
        logger.debug('remove_problem(%s, %s, %s)' %
                     (self, problem_id, widget))
        if problem_id is None and widget is None:
            logger.warning('invoke remove_problem with None, None')
            # if no problem id and not problem widgets then don't do anything
            return

        if not isinstance(widget, (Gtk.Widget, type(None))):
            try:
                widget = getattr(self.view.widgets, widget)
            except:
                logger.info("can't get widget %s" % widget)

        tmp = self.problems.copy()
        for p, w in tmp:
            if (w == widget and p == problem_id) or \
                    (widget is None and p == problem_id) or \
                    (w == widget and problem_id is None):
                if w and not prefs.testing:
                    w.modify_bg(Gtk.StateType.NORMAL, None)
                    w.modify_base(Gtk.StateType.NORMAL, None)
                    w.queue_draw()
                self.problems.remove((p, w))
        logger.debug('problems now: %s' % self.problems)

    def add_problem(self, problem_id, problem_widgets=None):
        """
        Add problem_id to self.problems and change the background of widget(s)
        in problem_widgets.

        :param problem_id: A unique id for the problem.

        :param problem_widgets: either a widget or list of widgets
          whose background color should change to indicate a problem
          (default=None)
        """
        ## map case list of widget to list of cases single widget.
        logger.debug('add_problem(%s, %s, %s)' %
                     (self, problem_id, problem_widgets))
        if isinstance(problem_widgets, (tuple, list)):
            list(map(lambda w: self.add_problem(problem_id, w), problem_widgets))
            return

        ## here single widget.
        widget = problem_widgets
        if not isinstance(widget, Gtk.Widget):
            try:
                widget = getattr(self.view.widgets, widget)
            except:
                logger.info("can't get widget %s" % widget)
        self.problems.add((problem_id, widget))
        if isinstance(widget, str):
            self.view.mark_problem(widget)
        elif widget is not None:
            widget.modify_bg(Gtk.StateType.NORMAL, self.problem_color)
            widget.modify_base(Gtk.StateType.NORMAL, self.problem_color)
            widget.queue_draw()
        logger.debug('problems now: %s' % self.problems)

    def init_enum_combo(self, widget_name, field):
        """
        Initialize a Gtk.ComboBox widget with name widget_name from
        enum values in self.model.field

        :param widget_name:

        :param field:
        """
        combo = self.view.widgets[widget_name]
        mapper = object_mapper(self.model)
        values = mapper.c[field].type.values
        if None in values:
            logger.debug("None value found in column %s, that is not in the Enum" % field)
            values.remove(None)
            values.insert(0, '')
        values = sorted(values)
        utils.setup_text_combobox(combo, values)

    def set_model_attr(self, attr, value, validator=None):
        """
        It is best to use this method to set values on the model
        rather than setting them directly.  Derived classes can
        override this method to take action when the model changes.

        :param attr: the attribute on self.model to set
        :param value: the value the attribute will be set to
        :param validator: validates the value before setting it
        """
        logger.debug('editor.set_model_attr(%s, %s)' % (attr, value))
        if validator:
            try:
                value = validator.to_python(value)
                self.remove_problem('BAD_VALUE_%s' % attr)
            except ValidatorError as e:
                logger.debug("GenericEditorPresenter.set_model_attr %s" % e)
                self.add_problem('BAD_VALUE_%s' % attr)
            else:
                setattr(self.model, attr, value)
        else:
            setattr(self.model, attr, value)

    def assign_simple_handler(self, widget_name, model_attr, validator=None):
        '''
        Assign handlers to widgets to change fields in the model.

        :param widget_name:

        :param model_attr:

        :param validator:

        Note: Where widget is a Gtk.ComboBox or Gtk.ComboBoxEntry then
        the value is assumed to be stored in model[row][0]
        '''
        widget = self.view.widgets[widget_name]
        check(widget is not None, _('no widget with name %s') % widget_name)

        class ProblemValidator(Validator):

            def __init__(self, presenter, wrapped):
                self.presenter = presenter
                self.wrapped = wrapped

            def to_python(self, value):
                try:
                    value = self.wrapped.to_python(value)
                    self.presenter.remove_problem('BAD_VALUE_%s'
                                                  % model_attr, widget)
                except Exception as e:
                    logger.debug("GenericEditorPresenter.ProblemValidator"
                                 ".to_python %s" % e)
                    self.presenter.add_problem('BAD_VALUE_%s'
                                               % model_attr, widget)
                    raise
                return value

        if validator:
            validator = ProblemValidator(self, validator)

        if isinstance(widget, Gtk.Entry):
            def on_changed(entry):
                self.set_model_attr(model_attr, entry.props.text, validator)
            self.view.connect(widget, 'changed', on_changed)
        elif isinstance(widget, Gtk.TextView):
            def on_changed(textbuff):
                self.set_model_attr(model_attr, textbuff.props.text, validator)
            buff = widget.get_buffer()
            self.view.connect(buff, 'changed', on_changed)
        elif isinstance(widget, Gtk.ComboBox):
            # this also handles Gtk.ComboBoxEntry since it extends
            # Gtk.ComboBox
            def combo_changed(combo, data=None):
                if not combo.get_active_iter():
                    # get here if there is no model on the ComboBoxEntry
                    return
                model = combo.get_model()
                if model is None or combo.get_active_iter() is None:
                    return
                value = model[combo.get_active_iter()][0]
                value = combo.get_model()[combo.get_active_iter()][0]
                if isinstance(widget, Gtk.ComboBox) and isinstance(widget.get_child(), Gtk.Entry):
                    widget.get_child().set_text(utils.utf8(value))
                self.set_model_attr(model_attr, value, validator)

            def entry_changed(entry, data=None):
                self.set_model_attr(model_attr, entry.props.text, validator)

            self.view.connect(widget, 'changed', combo_changed)
            if isinstance(widget, Gtk.ComboBox) and isinstance(widget.get_child(), Gtk.Entry):
                self.view.connect(widget.get_child(), 'changed', entry_changed)
        elif isinstance(widget, (Gtk.ToggleButton, Gtk.CheckButton,
                                 Gtk.RadioButton)):
            def toggled(button, data=None):
                active = button.get_active()
                logger.debug('toggled %s: %s' % (widget_name, active))
                button.set_inconsistent(False)
                self.set_model_attr(model_attr, active, validator)
            self.view.connect(widget, 'toggled', toggled)
        else:
            raise ValueError('assign_simple_handler() -- '
                             'widget type not supported: %s' % type(widget))

    def assign_completions_handler(self, widget, get_completions,
                                   on_select=lambda v: v):
        """Dynamically handle completions on a Gtk.Entry.

        :param widget: a Gtk.Entry instance or widget name

        :param get_completions: the callable to invoke when a list of
          completions is requested, accepts the string typed, returns an
          iterable of completions

        :param on_select: callback for when a value is selected from
          the list of completions

        """

        logger.debug('assign_completions_handler %s' % widget)
        if not isinstance(widget, Gtk.Entry):
            widget = self.view.widgets[widget]
        PROBLEM = hash(Gtk.Buildable.get_name(widget))

        def add_completions(text):
            if get_completions is None:
                logger.debug("completion model has static list")
                # get_completions is None usually means that the
                # completions model already has a static list of
                # completions
                return
            # get the completions using [0:key_length] as the start of
            # the string

            def idle_callback(values):
                completion = widget.get_completion()
                utils.clear_model(completion)
                completion_model = Gtk.ListStore(object)
                for v in values:
                    completion_model.append([v])
                completion.set_model(completion_model)

            key_length = widget.get_completion().props.minimum_key_length
            values = get_completions(text[:key_length])
            logger.debug('completions to add: %s' % str([i for i in values]))
            GObject.idle_add(idle_callback, values)

        def on_changed(entry, *args):
            logger.debug('assign_completions_handler::on_changed %s %s'
                         % (entry, args))
            text = entry.get_text()

            key_length = widget.get_completion().props.minimum_key_length
            if len(text) > key_length:
                logger.debug('recomputing completions matching %s' % text)
                add_completions(text)

            def idle_callback(text):
                logger.debug('on_changed - part two')
                comp = entry.get_completion()
                comp_model = comp.get_model()
                found = []
                if comp_model:
                    comp_model.foreach(lambda m, p, i, ud: logger.debug("item(%s) of comp_model: %s" % (p, m[p][0])), None)
                    # search the tree model to see if the text in the
                    # entry matches one of the completions, if so then
                    # emit the match-selected signal, this allows us to
                    # type a match in the entry without having to select
                    # it from the popup
                    def _cmp(row, data):
                        return utils.utf8(row[0])[:len(text)].lower() == data.lower()
                    found = utils.search_tree_model(comp_model, text, _cmp)
                    logger.debug("matches found in ListStore: %s" % str(found))
                    if not found:
                        logger.debug('nothing found, nothing to select from')
                    elif len(found) == 1:
                        logger.debug('one match, decide whether to select it - %s' % found[0])
                        v = comp.get_model()[found[0]][0]
                        # only auto select if the full string has been entered
                        if text.lower() == utils.utf8(v).lower():
                            comp.emit('match-selected', comp.get_model(), found[0])
                        else:
                            found = None
                    else:
                        logger.debug('multiple matches, we cannot select any - %s' % str(found))

                if text != '' and not found and PROBLEM not in self.problems:
                    self.add_problem(PROBLEM, widget)
                    on_select(None)

                # if entry is empty select nothing and remove all problem
                if text == '':
                    on_select(None)
                    self.remove_problem(PROBLEM, widget)
                elif not comp_model:
                    ## completion model is not in place when object is forced
                    ## programmatically.
                    on_select(text)  # `on_select` will know how to convert the
                                     # text into a properly typed value.
                    self.remove_problem(PROBLEM, widget)
                logger.debug('on_changed - part two - returning')

            GObject.idle_add(idle_callback, text)
            logger.debug('on_changed - part one - returning')
            return True

        def on_match_select(completion, compl_model, treeiter):
            value = compl_model[treeiter][0]
            # temporarily block the changed ID so that this function
            # doesn't get called twice
            widget.handler_block(_changed_sid)
            widget.props.text = utils.utf8(value)
            widget.handler_unblock(_changed_sid)
            self.remove_problem(PROBLEM, widget)
            on_select(value)
            return True  # return True or on_changed() will be called with ''

        completion = widget.get_completion()
        check(completion is not None, 'the Gtk.Entry %s doesn\'t have a '
              'completion attached to it' % widget.get_name())

        _changed_sid = self.view.connect(widget, 'changed', on_changed)
        self.view.connect(completion, 'match-selected', on_match_select)

    def start(self):
        """run the dialog associated to the view

        """
        result = self.view.get_window().run()
        if (self.is_committing_presenter
            and result in self.committing_results
            and self._dirty):
            self.commit_changes()
        self.cleanup()
        return result

    def cleanup(self):
        """
        Revert any changes the presenter might have done to the
        widgets so that next time the same widgets are open everything
        will be normal.

        By default it only calls self.view.cleanup()
        """
        self.clear_problems()
        if isinstance(self.view, GenericEditorView):
            self.view.cleanup()


class ChildPresenter(GenericEditorPresenter):
    """
    This Presenter acts as a proxy to another presenter that shares
    the same view. This avoids circular references by not having a
    presenter within a presenter that both hold references to the
    view.

    This Presenter keeps a weakref to the parent presenter and
    provides a pass through to the parent presenter for calling
    methods that reference the view.
    """

    def __init__(self, model, view):
        super().__init__(model, view)
        #self._view_ref = weakref.ref(view)

    def _get_view(self):
        return self._view_ref()

    def _set_view(self, view):
        if isinstance(view, GenericEditorView):
            self._view_ref = weakref.ref(view)
        else:
            raise ValueError('view must be an instance of GenericEditorView')

    view = property(_get_view, _set_view)


class GenericModelViewPresenterEditor(object):
    '''
    GenericModelViewPresenterEditor assume that model is an instance
    of object mapped to a SQLAlchemy table

    The editor creates its own session and merges the model into
    it.  If the model is already in another session that original
    session will not be effected.

    When creating a subclass of this editor then you should explicitly
    close the session when you are finished with it.

    :param model: an instance of an object mapped to a SQLAlchemy
      Table, the model will be copied and merged into self.session so
      that the original model will not be changed

    :param parent: the parent windows for the view or None
    '''
    ok_responses = ()

    def __init__(self, model, parent=None):
        self.session = db.Session()
        self.model = self.session.merge(model)

    def commit_changes(self):
        '''
        Commit the changes to self.session()
        '''
        objs = list(self.session)
        try:
            self.session.commit()
            try:
                bauble.gui.get_view().update()
            except Exception as e:
                pass
        except Exception as e:
            logger.warning("can't commit changes: (%s) %s" % (type(e), e))
            self.session.rollback()
            self.session.add_all(objs)
            raise
        return True

    def __del__(self):
        if hasattr(self, 'session'):
            # in case one of the check()'s fail in __init__
            self.session.commit()
            self.session.close()


class NoteBox(Gtk.HBox):
    glade_ui = 'notes.glade'

    def set_content(self, text):
        buff = Gtk.TextBuffer()
        self.widgets.note_textview.set_buffer(buff)
        utils.set_widget_value(self.widgets.note_textview,
                               text or '')
        if not text:
            self.presenter.add_problem(self.presenter.PROBLEM_EMPTY, self.widgets.note_textview)
        buff.connect('changed', self.on_note_buffer_changed, self.widgets.note_textview)

    def __init__(self, presenter, model=None):
        super().__init__()

        # open the glade file and extract the markup that the
        # expander will use
        filename = os.path.join(paths.lib_dir(), self.glade_ui)
        xml = etree.parse(filename)
        el = xml.find("//object[@id='notes_box']")
        builder = Gtk.Builder()
        s = '<interface>%s</interface>' % etree.tostring(el)
        if sys.platform == 'win32':
            # NOTE: PyGTK for Win32 is broken so we have to include
            # this little hack
            #
            # TODO: is this only a specific set of version of
            # PyGTK/GTK...it was only tested with PyGTK 2.12
            builder.add_from_string(s, -1)
        else:
            builder.add_from_string(s)
        self.widgets = utils.BuilderWidgets(builder)

        notes_box = self.widgets.notes_box
        self.widgets.remove_parent(notes_box)
        self.pack_start(notes_box, True, True, 0)

        self.session = object_session(presenter.model)
        self.presenter = presenter
        if model:
            self.model = model
        else:
            self.model = presenter.note_cls()

        self.widgets.notes_expander.props.use_markup = True
        self.widgets.notes_expander.props.label = ''
        self.widgets.notes_expander.props.label_widget.\
            ellipsize = Pango.EllipsizeMode.END

        # set the model values on the widgets
        mapper = object_mapper(self.model)
        values = utils.get_distinct_values(mapper.c['category'],
                                           self.session)
        utils.setup_text_combobox(self.widgets.category_comboentry, values)
        utils.set_widget_value(self.widgets.category_comboentry,
                               self.model.category or '')
        utils.setup_date_button(None, self.widgets.date_entry,
                                self.widgets.date_button)
        date_str = utils.today_str()
        if self.model.date:
            format = prefs.prefs[prefs.date_format_pref]
            date_str = self.model.date.strftime(format)
        utils.set_widget_value(self.widgets.date_entry, date_str)
        utils.set_widget_value(self.widgets.user_entry,
                               self.model.user or '')
        self.set_content(self.model.note)

        # connect the signal handlers
        self.widgets.date_entry.connect(
            'changed', self.on_date_entry_changed)
        self.widgets.user_entry.connect(
            'changed', self.on_user_entry_changed)
        # connect category comboentry widget and child entry
        self.widgets.category_comboentry.connect(
            'changed', self.on_category_combo_changed)
        self.widgets.category_comboentry.get_child().connect(
            'changed', self.on_category_entry_changed)
        self.widgets.notes_remove_button.connect(
            'clicked', self.on_notes_remove_button)

        self.update_label()
        self.show_all()

    def set_expanded(self, expand):
        self.widgets.notes_expander.props.expanded = expand

    def on_notes_remove_button(self, button, *args):
        """
        """
        if self.model in self.presenter.notes:
            self.presenter.notes.remove(self.model)
        self.widgets.remove_parent(self.widgets.notes_box)
        self.presenter._dirty = True
        self.presenter.parent_ref().refresh_sensitivity()

    def on_date_entry_changed(self, entry, *args):
        PROBLEM = 'BAD_DATE'
        text = entry.props.text
        try:
            text = DateValidator().to_python(text)
        except Exception as e:
            logger.debug(e)
            self.presenter.add_problem(PROBLEM, entry)
        else:
            self.presenter.remove_problem(PROBLEM, entry)
            self.set_model_attr('date', text)

    def on_user_entry_changed(self, entry, *args):
        value = utils.utf8(entry.props.text)
        if not value:  # if value == ''
            value = None
        self.set_model_attr('user', value)

    def on_category_combo_changed(self, combo, *args):
        """
        Sets the text on the entry.  The model value is set in the
        entry "changed" handler.
        """
        text = ''
        treeiter = combo.get_active_iter()
        if treeiter:
            text = utils.utf8(combo.get_model()[treeiter][0])
        else:
            return
        self.widgets.category_comboentry.get_child().props.text = \
            utils.utf8(text)

    def on_category_entry_changed(self, entry, *args):
        """
        """
        value = utils.utf8(entry.props.text)
        if not value:  # if value == ''
            value = None
        self.set_model_attr('category', value)

    def on_note_buffer_changed(self, buff, widget, *args):
        value = utils.utf8(buff.props.text)
        if not value:  # if value == ''
            value = None
            self.presenter.add_problem(self.presenter.PROBLEM_EMPTY, widget)
        else:
            self.presenter.remove_problem(self.presenter.PROBLEM_EMPTY, widget)
        self.set_model_attr('note', value)

    def update_label(self):
        label = []
        date_str = None
        if self.model.date and isinstance(self.model.date, datetime.date):
            format = prefs.prefs[prefs.date_format_pref]
            date_str = utils.xml_safe(
                self.model.date.strftime(format))
        elif self.model.date:
            date_str = utils.xml_safe(self.model.date)
        else:
            date_str = self.widgets.date_entry.props.text

        if self.model.user and date_str:  # and self.model.date:
            label.append(_('%(user)s on %(date)s') %
                         dict(user=utils.xml_safe(self.model.user),
                              date=date_str))
        elif date_str:
            label.append('%s' % date_str)
        elif self.model.user:
            label.append('%s' % utils.xml_safe(self.model.user))

        if self.model.category:
            label.append('(%s)' % utils.xml_safe(self.model.category))

        if self.model.note:
            note_str = ' : %s' % utils.xml_safe(self.model.note).\
                replace('\n', '  ')
            max_length = 25
            # label.props.ellipsize doesn't work properly on a
            # label in an expander we just do it ourselves here
            if len(self.model.note) > max_length:
                label.append('%s …' % note_str[0:max_length-1])
            else:
                label.append(note_str)

        self.widgets.notes_expander.set_label(' '.join(label))

    def set_model_attr(self, attr, value):
        setattr(self.model, attr, value)
        self.presenter._dirty = True
        if attr != 'date' and not self.model.date:
            # this is a little voodoo to set the date on the model
            # since when we create a new note box we add today's
            # date to the entry but we don't set the model so the
            # presenter doesn't appear dirty...we have to use a
            # tmp variable since the changed signal won't fire if
            # the new value is the same as the old
            entry = self.widgets.date_entry
            tmp = entry.props.text
            entry.props.text = ''
            entry.props.text = tmp
            # if the note is new and isn't yet associated with an
            # accession then set the accession when we start
            # changing values, this way we can setup a dummy
            # verification in the interface
            self.presenter.notes.append(self.model)

        self.update_label()

        self.presenter.parent_ref().refresh_sensitivity()

    @classmethod
    def is_valid_note(cls, note):
        return True


class PictureBox(NoteBox):
    glade_ui = 'pictures.glade'
    last_folder = '.'

    def __init__(self, presenter, model=None):
        super().__init__(presenter, model)
        utils.set_widget_value(self.widgets.category_comboentry,
                               '<picture>')
        self.presenter._dirty = False

        self.widgets.picture_button.connect(
            "clicked", self.on_activate_browse_button)

    def set_content(self, basename):
        for w in list(self.widgets.picture_button.get_children()):
            w.destroy()
        if basename is not None:
            im = Gtk.Image()
            try:
                thumbname = os.path.join(
                    prefs.prefs[prefs.picture_root_pref], 'thumbs', basename)
                filename = os.path.join(
                    prefs.prefs[prefs.picture_root_pref], basename)
                if os.path.isfile(thumbname):
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file(thumbname)
                else:
                    fullbuf = GdkPixbuf.Pixbuf.new_from_file(filename)
                    fullbuf = fullbuf.apply_embedded_orientation()
                    scale_x = fullbuf.get_width() / 400.0
                    scale_y = fullbuf.get_height() / 400.0
                    scale = max(scale_x, scale_y, 1)
                    x = int(fullbuf.get_width() / scale)
                    y = int(fullbuf.get_height() / scale)
                    pixbuf = fullbuf.scale_simple(
                        x, y, GdkPixbuf.InterpType.BILINEAR)
                im.set_from_pixbuf(pixbuf)
            except glib.GError as e:
                logger.debug("picture %s caused glib.GError %s" %
                             (basename, e))
                label = _('picture file %s not found.') % basename
                im = Gtk.Label()
                im.set_text(label)
            except Exception as e:
                logger.warning("can't commit changes: (%s) %s" % (type(e), e))
                im = Gtk.Label()
                im.set_text(e)
        else:
            # make button hold some text
            im = Gtk.Label()
            im.set_text(_('Choose a file…'))
        im.show()
        self.widgets.picture_button.add(im)
        self.widgets.picture_button.show()

    def on_activate_browse_button(self, widget, data=None):
        fileChooserDialog = Gtk.FileChooserDialog(
            _("Choose a file…"), None,
            buttons=(Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT,
                     Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL))
        try:
            logger.debug('about to set current folder - %s' % self.last_folder)
            fileChooserDialog.set_current_folder(self.last_folder)
            fileChooserDialog.run()
            filename = fileChooserDialog.get_filename()
            if filename:
                ## remember chosen location for next time
                PictureBox.last_folder, basename = os.path.split(str(filename))
                logger.debug('new current folder is: %s' % self.last_folder)
                ## copy file to picture_root_dir (if not yet there),
                ## also receiving thumbnail base64
                thumb = utils.copy_picture_with_thumbnail(self.last_folder, basename)
                ## make sure the category is <picture>
                self.set_model_attr('category', '<picture>')
                ## append thumbnail base64 to content string
                basename = basename + "|data:image/jpeg;base64," + thumb
                ## store basename in note field and fire callbacks.
                self.set_model_attr('note', basename)
                self.set_content(basename)
        except Exception as e:
            logger.warning("unhandled exception in editor.py: "
                           "(%s)%s" % (type(e), e))
        fileChooserDialog.destroy()

    def on_category_entry_changed(self, entry, *args):
        pass

    @classmethod
    def is_valid_note(cls, note):
        return note.category == '<picture>'


# TODO: create a separate class for browsing notes in a treeview
# structure

# TODO: add an "editable" property to the NotesPresenter and if it is
# True then show the add/remove buttons

class NotesPresenter(GenericEditorPresenter):
    """
    The NotesPresenter provides a generic presenter for editor notes
    on an item in the database.  This presenter requires that the
    notes property provide a specific interface.

    :param presenter: the parent presenter of this presenter
    :param notes_property: the string name of the notes property of
      the presenter.model
    :param parent_container: the Gtk.Container to add the notes editor box to
    """

    ContentBox = NoteBox

    def __init__(self, presenter, notes_property, parent_container):
        super().__init__(presenter.model, None)

        # The glade file named in ContentBox is structured with two top
        # GtkWindow next to each other. Here, by not doing any lookup, we
        # get the first one, from which we extract the 'notes_editor_box'
        # child. This is expected to contain a 'notes_expander_box' vertical
        # box, which will host all expanders.  In the content box we
        # extract, from the same file, the widget named 'notes_box'.
        filename = os.path.join(paths.lib_dir(), self.ContentBox.glade_ui)
        self.widgets = utils.BuilderWidgets(filename)

        self.parent_ref = weakref.ref(presenter)
        self.note_cls = object_mapper(presenter.model).\
            get_property(notes_property).mapper.class_
        self.notes = getattr(presenter.model, notes_property)
        self.parent_container = parent_container
        editor_box = self.widgets.notes_editor_box  # Gtk.VBox()
        self.widgets.remove_parent(editor_box)
        parent_container.add(editor_box)

        # the `expander`s are added to self.box
        self.box = self.widgets.notes_expander_box

        valid_notes_count = 0
        for note in self.notes:
            if self.ContentBox.is_valid_note(note):
                box = self.add_note(note)
                box.set_expanded(False)
                valid_notes_count += 1

        logger.debug('notes: %s' % self.notes)
        logger.debug('children: %s' % self.box.get_children())

        self.widgets.notes_add_button.connect(
            'clicked', self.on_add_button_clicked)
        self.box.show_all()

    def on_add_button_clicked(self, *args):
        box = self.add_note()
        box.set_expanded(True)

    def add_note(self, note=None):
        """
        Add a new note to the model.
        """
        expander = self.ContentBox(self, note)
        self.box.pack_start(expander, False, False, 0)
        self.box.reorder_child(expander, 0)
        expander.show_all()
        return expander


class PicturesPresenter(NotesPresenter):
    """pictures are associated to notes of category <picture>.

    you add a picture and you see a picture but the database will just hold
    the name of the corresponding file.

    as for other presenters, you can expand/collapse each inserted
    picture, you add or remove pictures, you see them on screen.

    this class works just the same as the NotesPresenter, with the
    note_textview replaced by a Button containing an Image.
    """

    ContentBox = PictureBox

    def __init__(self, presenter, notes_property, parent_container):
        super().__init__(
            presenter, notes_property, parent_container)

        notes = self.box.get_children()
        if notes:
            notes[0].set_expanded(False)  # expand none
