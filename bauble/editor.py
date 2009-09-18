#
# editor.py
#
# Description: a collection of functions and abstract classes for creating
# editors for Bauble data
#
import traceback

import gtk
import gobject
from sqlalchemy import *
from sqlalchemy.orm import *

import bauble
from bauble.error import check, CheckConditionError, BaubleError
from bauble.prefs import prefs
import bauble.utils as utils
from bauble.error import CommitException
from bauble.utils.log import log, debug, warning

# TODO: create a generic date entry that can take a mask for the date format
# see the date entries for the accession and accession source presenters

class ValidatorError(Exception):
    pass

class StringOrNoneValidator(object):
    """
    If the value is an empty string then return None, else return the
    str() of the value.
    """

    def to_python(self, value):
        if value in (u'', ''):
            return None
        return str(value)


class UnicodeOrNoneValidator(object):
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



class IntOrNoneStringValidator(object):
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

class FloatOrNoneStringValidator(object):
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


def default_completion_match_func(completion, key_string, iter):
    '''
    the default completion match function for
    GenericEditorView.attach_completions, does a case-insensitive string
    comparison of the the completions model[iter][0]
    '''
    value = completion.get_model()[iter][0]
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

        # pygtk 2.12.1 on win32 for some reason doesn't support the new
        # gtk 2.12 gtk.Tooltip API
#        if False:
        if hasattr(gtk.Widget, 'set_tooltip_markup'):
            for widget_name, markup in self._tooltips.iteritems():
                try:
                    self.widgets[widget_name].set_tooltip_markup(markup)
                except Exception, e:
                    values = dict(widget_name=widget_name, exception=e)
                    debug(_('Couldn\'t set the tooltip on widget '\
                            '%(widget_name)s\n\n%(exception)s' % values))
        else:
            tooltips = gtk.Tooltips()
            for widget_name, markup in self._tooltips.iteritems():
                widget = self.widgets[widget_name]
                tooltips.set_tip(widget, markup)

        window = self.get_window()
        self.connect(window,  'delete-event',
                     self.on_window_delete)
        if isinstance(window, gtk.Dialog):
            self.connect(window, 'close', self.on_dialog_close)
            self.connect(window, 'response', self.on_dialog_response)



    def connect(self, obj, signal, callback, data=None):
        if isinstance(obj, basestring):
            obj = self.widgets[obj]
        if data:
            sid = obj.connect(signal, callback, data)
        else:
            sid = obj.connect(signal, callback)
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


    def attach_completion(self, entry_name,
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

        :param entry_name: the name of the entry to attach the completion

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
        completion.set_popup_set_width(True)
        if isinstance(entry_name, basestring):
            self.widgets[entry_name].set_completion(completion)
        else:
            entry_name.set_completion(completion)
        return completion


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
        if None in values:
            values.remove(None)
            values.insert(0, '')
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
        if validator:
            try:
                value = validator.to_python(value)
                self.remove_problem('BAD_VALUE_%s' % attr)
            except ValidatorError, e:
                self.add_problem('BAD_VALUE_%s' % attr)
                value = None # make sure the value in the model is reset
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
            def changed(combo, data=None):
                model = combo.get_model()
                if model is None:
                    return
                i = combo.get_active_iter()
                if i is None:
                    return
                data = combo.get_model()[combo.get_active_iter()][0]
                if isinstance(widget, gtk.ComboBoxEntry):
                    widget.child.set_text(str(data))
                self.set_model_attr(model_attr, data, validator)
            self.view.connect(widget, 'changed', changed)
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
        def add_completions(text):
            #debug('add_completions(%s)' % text)
            if get_completions is None:
                # get_completions is None usually means that the
                # completions model already has a static list of
                # completions
                return
            # always get completions from the first two characters from
            # a string
            values = get_completions(text[:1])
            def idle_callback(values):
                completion = widget.get_completion()
                utils.clear_model(completion)
                completion_model = gtk.ListStore(object)
                for v in values:
                    completion_model.append([v])
                completion.set_model(completion_model)
            gobject.idle_add(idle_callback, values)

        def on_changed(entry, *args):
            text = entry.get_text()
            #debug('on_changed: %s' % text)
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
                    return utils.utf8(row[0]) == text
                #debug('search for %s' % text)
                found = utils.search_tree_model(comp_model, text, _cmp)
                #debug(found)
                if len(found) == 1:
                    v = comp.get_model()[found[0]][0]
                    #debug('found: %s'  % str(v))
                    comp.emit('match-selected', comp.get_model(), found[0])

            if text != '' and not found and PROBLEM not in self.problems:
                self.add_problem(PROBLEM, widget)
                on_select(None)

            if (not comp_model and len(text)>2) or len(text) == 2:
                #debug('add_completions: %s' % text)
                add_completions(text)
            return True

        def on_match_select(completion, compl_model, treeiter):
            value = compl_model[treeiter][0]
            #debug('on_match_select(): %s' % value)
            widget.props.text = utils.utf8(value)
            widget.set_position(-1)
            self.remove_problem(PROBLEM, widget)
            on_select(value)
            return True # return True or on_changed() will be called with ''

        completion = widget.get_completion()
        check(completion is not None, 'the gtk.Entry %s doesn\'t have a '\
              'completion attached to it' % widget.get_name())

        self.view.connect(widget, 'changed', on_changed)
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


    def refresh_view(self):
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

    :param model: an instance of an object mapped to a SQLAlchemy Table
    :param parent: the parent windows for the view or None
    '''
    label = ''
    standalone = True
    ok_responses = ()

    def __init__(self, model, parent=None):
        self.session = bauble.Session()
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
        self.session.commit()
        return True


    def __del__(self):
        #debug('GenericEditor.__del__()')
        self.session.close()
