# editor.py
#
# Description: a collection of functions and abstract classes for creating
# editors for Bauble data
#

import datetime
import os
import sys
import traceback
import weakref

import dateutil.parser as date_parser
import gtk
import gobject
import lxml.etree as etree
import pango
from sqlalchemy import *
from sqlalchemy.orm import *

import bauble
import bauble.db as db
from bauble.error import check, CheckConditionError, BaubleError
import bauble.paths as paths
import bauble.prefs as prefs
import bauble.utils as utils
from bauble.error import CommitException
from bauble.utils.log import debug, warning

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
            date = date_parser.parse(value, dayfirst=dayfirst,
                                     yearfirst=yearfirst, default=default)
            if date.year == default_year:
                raise ValueError
        except Exception, e:
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
        if value in (u'', ''):
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
        if value in (u'', ''):
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
        elif isinstance(value, (int, long)):
            return value
        try:
            return int(value)
        except Exception:
            raise ValidatorError('Could not convert value to int: %s (%s)' \
                                 % (value, type(value)))


class FloatOrNoneStringValidator(Validator):
    """
    If the value is an int, long, float or can be cast to float then
    return the number, else return None
    """

    def to_python(self, value):
        if value is None or (isinstance(value, str) and value == ''):
            return None
        elif isinstance(value, (int, long, float)):
            return value
        try:
            return float(value)
        except Exception:
            raise ValidatorError('Could not convert value to float: %s (%s)' \
                                 % (value, type(value)))



def default_completion_cell_data_func(column, renderer, model, treeiter,
                                      data=None):
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
    An generic object meant to be extended to provide the view for a
    GenericModelViewPresenterEditor

    :param filename: a gtk.Builder UI definition
    :param parent:
    """
    _tooltips = {}

    def __init__(self, filename, parent=None):
        builder = utils.BuilderLoader.load(filename)
        self.widgets = utils.BuilderWidgets(builder)
        if parent:
            self.get_window().set_transient_for(parent)
        elif bauble.gui:
            self.get_window().set_transient_for(bauble.gui.window)
        self.response = None
        self.__attached_signals = []

        # set the tooltips...use gtk.Tooltip api introducted in GTK+ 2.12
        for widget_name, markup in self._tooltips.iteritems():
            try:
                self.widgets[widget_name].set_tooltip_markup(markup)
            except Exception, e:
                values = dict(widget_name=widget_name, exception=e)
                debug(_('Couldn\'t set the tooltip on widget '\
                        '%(widget_name)s\n\n%(exception)s' % values))

        window = self.get_window()
        self.connect(window, 'delete-event', self.on_window_delete)
        if isinstance(window, gtk.Dialog):
            self.connect(window, 'close', self.on_dialog_close)
            self.connect(window, 'response', self.on_dialog_response)


    def connect(self, obj, signal, callback, *args):
        if isinstance(obj, basestring):
            obj = self.widgets[obj]
        sid = obj.connect(signal, callback, *args)
        self.__attached_signals.append((obj, sid))
        return sid


    def connect_after(self, obj, signal, callback, data=None):
        if isinstance(obj, basestring):
            obj = self.widgets[obj]
        if data:
            sid = obj.connect_after(signal, callback, data)
        else:
            sid = obj.connect_after(signal, callback)
        self.__attached_signals.append((obj, sid))
        return sid


    def disconnect_all(self):
        for obj, sid in self.__attached_signals:
            obj.disconnect(sid)
        del self.__attached_signals[:]


    def get_window(self):
        """
        Return the top level window for view
        """
        raise NotImplementedError


    def set_widget_value(self, widget, value, markup=True, default=None,
                         index=0):
        '''
        :param widget: a widget or name of a widget in self.widgets
        :param value: the value to put in the widgets
        :param markup: whether the data in value uses pango markup
        :param default: the default value to put in the widget if value is None
        :param index: the row index to use for those widgets who use a model

        This method caled bauble.utils.set_widget_value()
        '''
        if isinstance(widget, gtk.Widget):
            utils.set_widget_value(widget, value, markup, default, index)
        else:
            utils.set_widget_value(self.widgets[widget], value, markup,
                                   default, index)


    def on_dialog_response(self, dialog, response, *args):
        '''
        Called if self.get_window() is a gtk.Dialog and it receives
        the response signal.
        '''
        dialog.hide()
        self.response = response
        return response


    def on_dialog_close(self, dialog, event=None):
        """
        Called if self.get_window() is a gtk.Dialog and it receives
        the close signal.
        """
        dialog.hide()
        return False


    def on_window_delete(self, window, event=None):
        """
        Called when the window return by get_window() receives the
        delete event.
        """
        window.hide()
        return False


    def attach_completion(self, entry,
                          cell_data_func=default_completion_cell_data_func,
                          match_func=default_completion_match_func,
                          minimum_key_length=2,
                          text_column=-1):
        """
        Attach an entry completion to a gtk.Entry.  The defaults
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
        completion = gtk.EntryCompletion()
        cell = gtk.CellRendererText() # set up the completion renderer
        completion.pack_start(cell)
        completion.set_cell_data_func(cell, cell_data_func)
        completion.set_match_func(match_func)
        completion.set_property('text-column', text_column)
        completion.set_minimum_key_length(minimum_key_length)
        # TODO: inline completion doesn't work for me
        #completion.set_inline_completion(True)
        completion.set_popup_completion(True)
        completion.props.popup_set_width = False
        if isinstance(entry, basestring):
            self.widgets[entry].set_completion(completion)
        else:
            entry.set_completion(completion)

        # allow later access to the match func just in case
        completion._match_func = match_func

        return completion


    # TODO: add the ability to pass a sort function
    # TODO: add a default value to set in the combo
    def init_translatable_combo(self, combo, translations, default=None,
                                cmp=None):
        """
        Initialize a gtk.ComboBox with translations values where
        model[row][0] is the value that will be stored in the database
        and model[row][1] is the value that will be visible in the
        gtk.ComboBox.

        A gtk.ComboBox initialized with this method should work with
        self.assign_simple_handler()

        :param combo:
        :param translations: a dictionary of values->translation
        """
        if isinstance(combo, basestring):
            combo = self.widgets[combo]
        combo.clear()
        # using 'object' avoids SA unicode warning
        model = gtk.ListStore(object, str)
        for key, value in sorted(translations.iteritems(), key=lambda x: x[1]):
            model.append([key, value])
        combo.set_model(model)
        cell = gtk.CellRendererText()
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
        '''
        Must be implemented.
        '''
        raise NotImplementedError

    def cleanup(self):
        """
        Should be caled when after self.start() returns to cleanup
        undo any changes on the view.

        By default all it does is call self.disconnect_all()
        """
        self.disconnect_all()


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
    problem_color = gtk.gdk.color_parse('#FFDCDF')

    def __init__(self, model, view):
        widget_model_map = {}
        self.model = model
        self.view = view
        self.problems = set()


    # whether the presenter should be commited or not
    def dirty(self):
        """
        Returns True or False depending on whether the presenter has
        changed anything that needs to be committed.  This doesn't
        necessarily imply that the session is not dirty nor is it
        required to change back to True if the changes are committed.
        """
        raise NotImplementedError


    def has_problems(self, widget):
        from operator import getitem
        filter(lambda p: getitem(p, 1) == widget is not None, self.problems)


    def clear_problems(self):
        tmp = self.problems.copy()
        map(lambda p: self.remove_problem(p[0], p[1]), tmp)
        self.problems.clear()


    def remove_problem(self, problem_id, problem_widgets=None):
        """
        Remove problem_id from self.problems and reset the background
        color of the widget(s) in problem_widgets

        :param problem_id:
        :param problem_widgets:
        """
        if not problem_widgets:
            # remove all the problem ids regardless of the widgets
            # they are attached to

            # TODO: should this only remove problem ids if the widget
            # part of the problem is None?
            tmp = self.problems.copy()
            for p, w in tmp:
                if p == problem_id:
                    self.problems.remove((p, w))
            return
        elif isinstance(problem_widgets, (list, tuple)):
            # call remove_problem() on each item in problem_widgets
            map(lambda w: self.remove_problem(problem_id, w), problem_widgets)
            return

        try:
            while True:
                # keep removing matching problems until we get a key error
                self.problems.remove((problem_id, problem_widgets))
                problem_widgets.modify_bg(gtk.STATE_NORMAL, None)
                problem_widgets.modify_base(gtk.STATE_NORMAL, None)
                problem_widgets.queue_draw()
        except KeyError, e:
            #debug(e)
            pass


    def add_problem(self, problem_id, problem_widgets=None):
        """
        Add problem_id to self.problems and change the background of widget(s)
        in problem_widgets.

        :param problem_id:

        :param problem_widgets: either a widget or list of widgets
        whose background color should change to indicate a problem
        """
        if isinstance(problem_widgets, (tuple, list)):
            map(lambda w: self.add_problem(problem_id, w), problem_widgets)

        self.problems.add((problem_id, problem_widgets))
        if problem_widgets:
            problem_widgets.modify_bg(gtk.STATE_NORMAL, self.problem_color)
            problem_widgets.modify_base(gtk.STATE_NORMAL, self.problem_color)
            problem_widgets.queue_draw()


    def init_enum_combo(self, widget_name, field):
        """
        Initialize a gtk.ComboBox widget with name widget_name from
        enum values in self.model.field

        :param widget_name:

        :param field:
        """
        combo = self.view.widgets[widget_name]
        mapper = object_mapper(self.model)
        values = sorted(mapper.c[field].type.values)
        # WARNING: this is really dangerous since it might mean that a
        # value is stored in the column that is not in the Enum
        #
        #if None in values:
        #    values.remove(None)
        #    values.insert(0, '')
        utils.setup_text_combobox(combo, values)


#     def bind_widget_to_model(self, widget_name, model_field):
#         # TODO: this is just an idea stub, should we have a method like
#         # this so to put the model values in the view we just
#         # need a for loop over the keys of the widget_model_map
#         pass


    def set_model_attr(self, attr, value, validator=None):
        """
        It is best to use this method to set values on the model
        rather than setting them directly.  Derived classes can
        override this method to take action when the model changes.

        :param attr: the attribute on self.model to set
        :param value: the value the attribute will be set to
        :param validator: validates the value before setting it
        """
        #debug('editor.set_model_attr(%s, %s)' % (attr, value))
        if validator:
            try:
                value = validator.to_python(value)
                self.remove_problem('BAD_VALUE_%s' % attr)
            except ValidatorError, e:
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

        Note: Where widget is a gtk.ComboBox or gtk.ComboBoxEntry then
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
                    self.presenter.remove_problem('BAD_VALUE_%s' \
                                             % model_attr,widget)
                except Exception, e:
                    self.presenter.add_problem('BAD_VALUE_%s' \
                                              % model_attr, widget)
                    raise
                return value

        if validator:
            validator = ProblemValidator(self, validator)

        if isinstance(widget, gtk.Entry):
            def on_changed(entry):
                self.set_model_attr(model_attr, entry.props.text, validator)
            self.view.connect(widget, 'changed', on_changed)
        elif isinstance(widget, gtk.TextView):
            def on_changed(textbuff):
                self.set_model_attr(model_attr, textbuff.props.text, validator)
            buff = widget.get_buffer()
            self.view.connect(buff, 'changed', on_changed)
        elif isinstance(widget, gtk.ComboBox):
            # this also handles gtk.ComboBoxEntry since it extends
            # gtk.ComboBox
            def combo_changed(combo, data=None):
                if not combo.get_active_iter():
                    # get here if there is no model on the ComboBoxEntry
                    return
                model = combo.get_model()
                value = model[combo.get_active_iter()][0]
                if not isinstance(combo, gtk.ComboBoxEntry):
                    if model is None:
                        return
                    i = combo.get_active_iter()
                    if i is None:
                        return
                    value = combo.get_model()[combo.get_active_iter()][0]
                else:
                    value = combo.child.props.text
                #data = combo.get_model()[combo.get_active_iter()][0]
                #debug('%s=%s' % (model_attr, data))
                if isinstance(widget, gtk.ComboBoxEntry):
                    #debug(str(value))
                    widget.child.set_text(str(value))
                self.set_model_attr(model_attr, value, validator)
            def entry_changed(entry, data=None):
                self.set_model_attr(model_attr, entry.props.text, validator)
            self.view.connect(widget, 'changed', combo_changed)
            if isinstance(widget, gtk.ComboBoxEntry):
                self.view.connect(widget.child, 'changed', entry_changed)
        elif isinstance(widget, (gtk.ToggleButton, gtk.CheckButton,
                                 gtk.RadioButton)):
            def toggled(button, data=None):
                active = button.get_active()
#                debug('toggled %s: %s' % (widget_name, active))
                button.set_inconsistent(False)
                self.set_model_attr(model_attr, active, validator)
            self.view.connect(widget, 'toggled', toggled)
        else:
            raise ValueError('assign_simple_handler() -- '\
                             'widget type not supported: %s' % type(widget))


    def assign_completions_handler(self, widget, get_completions,
                                   on_select=lambda v: v):
        """
        Dynamically handle completions on a gtk.Entry.

        :param widget: a gtk.Entry instance or widget name

        :param get_completions: the method to call when a list of
          completions is requested, returns a list of completions

        :param on_select: callback for when a value is selected from
          the list of completions
        """
        if not isinstance(widget, gtk.Entry):
            widget = self.view.widgets[widget]
        PROBLEM = hash(widget.get_name())
        key_length = 2
        def add_completions(text):
            #debug('add_completions(%s)' % text)
            if get_completions is None:
                # get_completions is None usually means that the
                # completions model already has a static list of
                # completions
                return
            # always get completions from the first two characters from
            # a string
            def idle_callback(values):
                completion = widget.get_completion()
                utils.clear_model(completion)
                completion_model = gtk.ListStore(object)
                for v in values:
                    completion_model.append([v])
                completion.set_model(completion_model)
            values = get_completions(text[:key_length])
            gobject.idle_add(idle_callback, values)

        def on_changed(entry, *args):
            text = entry.get_text()
            comp = entry.get_completion()
            comp_model = comp.get_model()
            found = []
            if comp_model:
                # search the tree model to see if the text in the
                # entry matches one of the completions, if so then
                # emit the match-selected signal, this allows us to
                # entry a match in the entry without having to select
                # it from the popup
                def _cmp(row, data):
                    if hasattr(comp, '_match_func'):
                        return comp._match_func(comp, text, row.iter)
                    else:
                        return utils.utf8(row[0]) == text
                found = utils.search_tree_model(comp_model, text, _cmp)
                if len(found) == 1:
                    v = comp.get_model()[found[0]][0]
                    # only auto select if the full string has been entered
                    if text.lower() == utils.utf8(v).lower():
                        comp.emit('match-selected', comp.get_model(), found[0])
                    else:
                        found = None

            if text != '' and not found and PROBLEM not in self.problems:
                self.add_problem(PROBLEM, widget)
                on_select(None)

            if (not comp_model and len(text)>key_length) or \
                    len(text) == key_length:
                add_completions(text)
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
            return True # return True or on_changed() will be called with ''

        completion = widget.get_completion()
        check(completion is not None, 'the gtk.Entry %s doesn\'t have a '\
              'completion attached to it' % widget.get_name())

        _changed_sid = self.view.connect(widget, 'changed', on_changed)
        self.view.connect(completion, 'match-selected', on_match_select)


    def start(self):
        raise NotImplementedError


    def cleanup(self):
        """Revert any changes the presenter might have done to the
        widgets so that next time the same widgets are open everything
        will be normal.

        By default it only calls self.view.cleanup()
        """
        self.clear_problems()
        self.view.cleanup()


    def refresh_sensitivity(self):
        """
        Refresh the sensitivity of the dialog buttons.

        This is not a required method for classes tha extend
        GenericEditorPresenter.
        """
        pass


    def refresh_view(self):
        """
        Refresh the view with the model values.  This method should be
        called before any signal handlers are configured on the view
        so that the model isn't changed when the widget values are set.

        Any classes that extend GenericEditorPresenter are required to
        implement this method.
        """
        # TODO: should i provide a generic implementation of this method
        # as long as widget_to_field_map exist
        raise NotImplementedError



class GenericModelViewPresenterEditor(object):

    '''
    GenericModelViewPresenterEditor assume that model is an instance
    of object mapped to a SQLAlchemy table

    The editor creates it's own session and merges the model into
    it.  If the model is already in another session that original
    session will not be effected.

    :param model: an instance of an object mapped to a SQLAlchemy
      Table, the model will be copied and merged into self.session so
      that the original model will not be changed

    :param parent: the parent windows for the view or None
    '''
    label = ''
    standalone = True
    ok_responses = ()

    def __init__(self, model, parent=None):
        self.session = db.Session()
        self.model = self.session.merge(model)


    def attach_response(self, dialog, response, keyname, mask):
        '''
        Attach a response to dialog when keyname and mask are pressed
        '''
        def callback(widget, event, key, mask):
#            debug(gtk.gdk.keyval_name(event.keyval))
            if event.keyval == gtk.gdk.keyval_from_name(key) \
                   and (event.state & mask):
                widget.response(response)
        dialog.add_events(gtk.gdk.KEY_PRESS_MASK)
        dialog.connect("key-press-event", callback, keyname, mask)


    def commit_changes(self):
        '''
        Commit the changes to self.session()
        '''
        objs = list(self.session)
        try:
            self.session.commit()
        except Exception, e:
            warning(e)
            self.session.rollback()
            self.session.add_all(objs)
            raise
        return True


    def __del__(self):
        #debug('GenericEditor.__del__()')
        self.session.close()


# TODO: create a seperate class for browsing notes in a treeview
# structure

# TODO: add an "editable" property to the NotesPresenter and if it is
# True then show the add/remove buttons

class NotesPresenter(GenericEditorPresenter):

    def __init__(self, presenter, notes_property, parent_container):
        """
        :param presenter: the parent presenter of this presenter
        :param notes_property: the string name of the notes property of
        the presenter.mode
        :parent_container: the gtk.Container to add the notes editor box to
        """
        super(NotesPresenter, self).__init__(presenter.model, None)

        # open the glade file and extract the UI markup the presenter will use
        filename = os.path.join(paths.lib_dir(), 'notes.glade')
        xml = etree.parse(filename)
        builder = gtk.Builder()
        el = xml.find("//object[@id='notes_editor_box']")
        import sys
        if sys.platform == 'win32':
            # NOTE: PyGTK for Win32 is broken so we have to include
            # this little hack
            #
            # TODO: is this only a specific set of version of
            # PyGTK/GTK...it was only tested with PyGTK 2.12
            builder.add_from_string(etree.tostring(xml), -1)
        else:
            builder.add_from_string(etree.tostring(xml))
        self.widgets = utils.BuilderWidgets(builder)

        self.parent_ref = weakref.ref(presenter)
        self.note_cls = object_mapper(presenter.model).\
            get_property(notes_property).mapper.class_
        self.notes = getattr(presenter.model, notes_property)
        self.parent_container = parent_container
        editor_box = self.widgets.notes_editor_box#gtk.VBox()
        self.widgets.remove_parent(editor_box)
        parent_container.add(editor_box)

        self._dirty = False

        # the expander are added to self.box
        self.box = self.widgets.notes_expander_box

        for note in self.notes:
            box = self.add_note(note)
            box.set_expanded(False)

        if len(self.notes) < 1:
            self.add_note()

        self.box.get_children()[0].set_expanded(True) # expand first one

        self.widgets.notes_add_button.connect('clicked',
                                              self.on_add_button_clicked)
        self.box.show_all()


    def dirty(self):
        return self._dirty


    def on_add_button_clicked(self, *args):
        box = self.add_note()
        box.set_expanded(True)


    def add_note(self, note=None):
        expander = NotesPresenter.NoteBox(self, note)
        self.box.pack_start(expander, expand=False, fill=False)#, padding=10)
        self.box.reorder_child(expander, 0)
        expander.show_all()
        return expander


    class NoteBox(gtk.HBox):

        def __init__(self, presenter, model=None):
            super(NotesPresenter.NoteBox, self).__init__()

            # open the glade file and extract the markup that the
            # expander will use
            filename = os.path.join(paths.lib_dir(), 'notes.glade')
            xml = etree.parse(filename)
            el = xml.find("//object[@id='notes_box']")
            builder = gtk.Builder()
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
            self.pack_start(notes_box, expand=True, fill=True)

            self.session = object_session(presenter.model)
            self.presenter = presenter
            if model:
                self.model = model
            else:
                self.model = presenter.note_cls()

            self.widgets.notes_expander.props.use_markup = True
            self.widgets.notes_expander.props.label = ''
            self.widgets.notes_expander.props.label_widget.\
                ellipsize = pango.ELLIPSIZE_END

            # set the model values on the widgets
            mapper = object_mapper(self.model)
            values = utils.get_distinct_values(mapper.c['category'],
                                               self.session)
            utils.setup_text_combobox(self.widgets.category_comboentry, values)
            utils.set_widget_value(self.widgets.category_comboentry,
                                   self.model.category or '')
            utils.setup_date_button(self.widgets.date_entry,
                                    self.widgets.date_button)
            date_str = utils.today_str()
            if self.model.date:
                format = prefs.prefs[prefs.date_format_pref]
                date_str = self.model.date.strftime(format)
            utils.set_widget_value(self.widgets.date_entry, date_str)
            utils.set_widget_value(self.widgets.user_entry,
                                   self.model.user or '')
            buff = gtk.TextBuffer()
            self.widgets.note_textview.set_buffer(buff)
            utils.set_widget_value(self.widgets.note_textview,
                                   self.model.note or '')

            # connect the signal handlers
            self.widgets.date_entry.connect('changed',
                                            self.on_date_entry_changed)
            self.widgets.user_entry.connect('changed',
                                            self.on_user_entry_changed)
            # connect category comboentry widget and child entry
            self.widgets.category_comboentry.connect('changed',
                                             self.on_category_combo_changed)
            self.widgets.category_comboentry.child.connect('changed',
                                             self.on_category_entry_changed)
            buff.connect('changed', self.on_note_buffer_changed)
            self.widgets.notes_remove_button.connect('clicked',
                                             self.on_notes_remove_button)

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
            except Exception, e:
                self.presenter.add_problem(PROBLEM, entry)
            else:
                self.presenter.remove_problem(PROBLEM, entry)
                self.set_model_attr('date', text)


        def on_user_entry_changed(self, entry, *args):
            value = utils.utf8(entry.props.text)
            if not value: # if value == ''
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
            self.widgets.category_comboentry.child.props.text = \
                utils.utf8(text)


        def on_category_entry_changed(self, entry, *args):
            """
            """
            value = utils.utf8(entry.props.text)
            if not value: # if value == ''
                value = None
            self.set_model_attr('category', value)


        def on_note_buffer_changed(self, buff, *args):
            value = utils.utf8(buff.props.text)
            if not value: # if value == ''
                value = None
            self.set_model_attr('note', value)


        def update_label(self):
            label = []
            date_str = None
            if self.model.date and isinstance(self.model.date, datetime.date):
                format = prefs.prefs[prefs.date_format_pref]
                date_str =utils.xml_safe_utf8(self.model.date.strftime(format))
            elif self.model.date:
                date_str = utils.xml_safe_utf8(self.model.date)
            else:
                date_str = self.widgets.date_entry.props.text

            if self.model.user and date_str:# and self.model.date:
                label.append(_('%(user)s on %(date)s') % \
                             dict(user=utils.xml_safe_utf8(self.model.user),
                                  date=date_str))
            elif date_str:
                label.append('%s' % date_str)
            elif self.model.user:
                label.append('%s' % utils.xml_safe_utf8(self.model.user))

            if self.model.category:
                label.append('(%s)' % utils.xml_safe_utf8(self.model.category))

            if self.model.note:
                note_str = ' : %s' % utils.xml_safe_utf8(self.model.note).\
                    replace('\n', '  ')
                max_length = 25
                # label.props.ellipsize doesn't work properly on a
                # label in an expander we just do it ourselves here
                if len(self.model.note) > max_length:
                    label.append('%s ...' % note_str[0:max_length-1])
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

            # TODO: if refresh_sensitivity() part of the
            # GenericEditorPresenter interface???
            self.presenter.parent_ref().refresh_sensitivity()



