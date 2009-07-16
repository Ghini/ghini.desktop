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



def default_completion_cell_data_func(column, renderer, model, iter,data=None):
    '''
    the default completion cell data function for
    GenericEditorView.attach_completions
    '''
    v = model[iter][0]
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
    """
    _tooltips = {}

    def __init__(self, glade_xml, parent=None):
        '''
        glade_xml either at gtk.glade.XML instance or a path to a glade
        XML file

        :param glade_xml:
        :param parent:
        '''
        if isinstance(glade_xml, gtk.glade.XML):
            self.glade_xml = glade_xml
        else: # assume it's a path string
            self.glade_xml = gtk.glade.XML(glade_xml)
        self.parent = parent
        self.widgets = utils.GladeWidgets(self.glade_xml)
        self.response = None

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


    def get_window(self):
        """
        Return the top level window for view
        """
        raise NotImplementedError


    def set_widget_value(self, widget_name, value, markup=True, default=None):
        '''
        :param widget_name: the name of the widget whose value we want to set
        :param value: the value to put in the widgets
        :param markup: whether the data in value uses pango markup
        :param default: the default value to put in the widget if value is None
        '''
        utils.set_widget_value(self.glade_xml, widget_name, value, markup,
                               default)


    def connect_dialog_close(self, dialog):
        '''
        :param dialog: the dialog to attache
          self.on_dialog_close_or_delete and self.on_dialog_response to
        '''
        dialog.connect('response', self.on_dialog_response)
        dialog.connect('close', self.on_dialog_close_or_delete)
        dialog.connect('delete-event', self.on_dialog_close_or_delete)


    def on_dialog_response(self, dialog, response, *args):
        '''
        Close when the dialog receives a response if
        self.connect_dialog_close is called.
        '''
        dialog.hide()
        self.response = response
        return response
        #if response < 0:
        #    dialog.hide()


    def on_dialog_close_or_delete(self, dialog, event=None):
        '''
        Called when a dialog receives the a close or delete event if
        self.connect_dialog_close is called.
        '''
        dialog.hide()
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
        completion.set_popup_completion(True)
        completion.set_popup_set_width(True)
        self.widgets[entry_name].set_completion(completion)
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
        Should be caled when self.start() returns.
        """
        try:
            self.get_window().destroy()
        except NotImplementedError:
            warning(_('Could not destroy window'))


class DontCommitException(Exception):
    """
    this is used for GenericModelViewPresenterEditor.commit_changes() to
    signal that for some reason the editor doesn't want to commit the current
    values and would like to redisplay
    """
    pass


# TODO: could use this to add to the problem list and it could give us more
# information about a problem and could have a unique id we could use to
# compare with
#class Problem:
#
#    def __init__(self, name, description):
#        id = some random number
#        pass
#
#    def __cmp__(self, other):
#        pass

class Problems(object):

    def __init__(self):
        self._problems = []


    def add(self, problem):
        '''
        :param problem: the problem to add
        '''
        self._problems.append(problem)


    def remove(self, problem):
        '''
        :param problem: the problem to remove

        NOTE: If the problem does not exist then there is no change
        and no error.
        '''
        while problem in self._problems:
            self._problems.remove(problem)


    def __len__(self):
        '''
        Return the number of problems
        '''
        return len(self._problems)


    def __str__(self):
        '''
        Return a string of the list of problems
        '''
        return str(self._problems)


class GenericEditorPresenter(object):
    """
    the presenter of the Model View Presenter Pattern
    """
    problem_color = gtk.gdk.color_parse('#FFDCDF')

    def __init__(self, model, view):
        '''
        :param model: an object instance mapped to an SQLAlchemy table
        :param view: should be an instance of GenericEditorView

        the presenter should usually be initialized in the following order:
        1. initialize the widgets
        2. refresh the view, put values from the model into the widgets
        3. connect the signal handlers
        '''
        widget_model_map = {}
        self.model = model
        self.view = view
        self.problems = Problems()
        # used by assign_completions_handler
        self._prev_text = {}


    # whether the presenter should be commited or not
    def dirty(self):
        """
        Returns True or False depending on whether the presenter has changed
        anything that needs to be committed.  This doesn't
        necessarily imply that the session is not dirty nor is it required to
        change back to True if the changes are committed.
        """
        raise NotImplementedError



    def remove_problem(self, problem_id, problem_widgets=None):
        """
        remove problem_id from self.problems and reset the background color
        of the widget(s) in problem_widgets

        :param problem_id:
        :param problem_widgets:
        """
        self.problems.remove(problem_id)
        if isinstance(problem_widgets, (tuple, list)):
            for w in problem_widgets:
                w.modify_bg(gtk.STATE_NORMAL, None)
                w.modify_base(gtk.STATE_NORMAL, None)
                w.queue_draw()
        elif problem_widgets is not None:
            problem_widgets.modify_bg(gtk.STATE_NORMAL, None)
            problem_widgets.modify_base(gtk.STATE_NORMAL, None)
            problem_widgets.queue_draw()


    def add_problem(self, problem_id, problem_widgets=None):
        """
        add problem_id to self.problems and change the background of widget(s)
        in problem_widgets
        problem_widgets: either a widget or list of widgets whose background
        color should change to indicate a problem

        :param problem_id:
        :param problem_widgets:
        """
        self.problems.add(problem_id)
        if isinstance(problem_widgets, (tuple, list)):
            for w in problem_widgets:
                w.modify_bg(gtk.STATE_NORMAL, self.problem_color)
                w.modify_base(gtk.STATE_NORMAL, self.problem_color)
                w.queue_draw()
        elif problem_widgets is not None:
            problem_widgets.modify_bg(gtk.STATE_NORMAL, self.problem_color)
            problem_widgets.modify_base(gtk.STATE_NORMAL, self.problem_color)
            problem_widgets.queue_draw()


    def init_enum_combo(self, widget_name, field):
        """
        initialize a gtk.ComboBox widget with name widget_name from enum values
        in self.model.field
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
        :param attr: the attribute on self.model to set
        :param value: the value the attribute will be set to
        :param validator: validates the value before setting it

        It is best to use this method to set values on the model
        rather than setting them directly.  Derived classes can
        override this method to take action when the model changes.
        """
        if validator is not None:
            try:
                value = validator.to_python(value)
                self.problems.remove('BAD_VALUE_%s' % attr)
            except ValidatorError, e:
                self.problems.add('BAD_VALUE_%s' % attr)
                value = None # make sure the value in the model is reset
        setattr(self.model, attr, value)

    # TODO: this should validate the data, i.e. convert strings to
    # int, or does commit do that?
    # TODO: here's our options
    # 1. validate on input, wouldn't be difficult just raise an error in
    # _set_in_model if the validation isn't good, add a problem to the
    # problem list, and set the event box red, the only thing is getting
    # the event box names into assign simple_handler
    # 2. validate on commit, not as nice for the user since it allows
    # them to put junk in the handler without them knowing and its not as
    # obviously clear where the problem is, but this is much easier to
    # implement
    def assign_simple_handler(self, widget_name, model_attr, validator=None):
        '''
        assign handlers to widgets to change fields in the model
        '''
        widget = self.view.widgets[widget_name]
        check(widget is not None, _('no widget with name %s') % widget_name)

        if isinstance(widget, gtk.Entry):
            def insert(entry, new_text, new_text_length, position):
                entry_text = entry.get_text()
                pos = entry.get_position()
                full_text = entry_text[:pos] + new_text + entry_text[pos:]
                #_set_in_model(full_text)
                self.set_model_attr(model_attr, full_text, validator)
            def delete(entry, start, end, data=None):
                text = entry.get_text()
                full_text = text[:start] + text[end:]
                #_set_in_model(full_text)
                self.set_model_attr(model_attr, full_text, validator)
            widget.connect('insert-text', insert)
            widget.connect('delete-text', delete)
        elif isinstance(widget, gtk.TextView):
            def insert(buffer, iter, new_text, length, data=None):
                buff_text = buffer.get_text(buffer.get_start_iter(),
                                            buffer.get_end_iter())
                text_start = buffer.get_text(buffer.get_start_iter(), iter)
                text_end = buffer.get_text(iter, buffer.get_end_iter())
                full_text = ''.join((text_start, new_text, text_end))
                #_set_in_model(new_text)
                self.set_model_attr(model_attr, full_text, validator)
            def delete(buffer, start_iter, end_iter, data=None):
                start = start_iter.get_offset()
                end = end_iter.get_offset()
                text = buffer.get_text(buffer.get_start_iter(),
                                       buffer.get_end_iter())
                new_text = text[:start] + text[end:]
                #_set_in_model(new_text)
                self.set_model_attr(model_attr, new_text, validator)
            widget.get_buffer().connect('insert-text', insert)
            widget.get_buffer().connect('delete-range', delete)
        elif isinstance(widget, gtk.ComboBox):
            def changed(combo, data=None):
                model = combo.get_model()
                if model is None:
                    return
                i = combo.get_active_iter()
                if i is None:
                    return
                data = combo.get_model()[combo.get_active_iter()][0]
                #_set_in_model(data, model_field)
                self.set_model_attr(model_attr, data, validator)
            widget.connect('changed', changed)
        elif isinstance(widget, (gtk.ToggleButton, gtk.CheckButton,
                                 gtk.RadioButton)):
            def toggled(button, data=None):
                active = button.get_active()
#                debug('toggled %s: %s' % (widget_name, active))
                button.set_inconsistent(False)
                #_set_in_model(active, model_field)
                self.set_model_attr(model_attr, active, validator)
            widget.connect('toggled', toggled)
        else:
            raise ValueError('assign_simple_handler() -- '\
                             'widget type not supported: %s' % type(widget))


    __changed_sid_name = lambda s, w: '__changed_%s_sid' % w.get_name()
    def pause_completions_handler(self, widget, pause=True):
        """
        Pause a completion handler previously assigned with
        assign_completions_handler()
        """
        if not isinstance(widget, gtk.Entry):
            widget = self.view.widgets[widget]
        sid = getattr(self, self.__changed_sid_name(widget))
        if pause:
            widget.handler_block(sid)
        else:
            widget.handler_unblock(sid)


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
        prev_text_name = '__prev_text_%s' % widget.get_name()
        setattr(self, prev_text_name, None)
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
            #debug('on_changed(%s)' % text)
            prev_text = getattr(self, prev_text_name)
            if text == '' and prev_text:
                # this works around a funny problem where after the
                # completion is selected the changed signal is fired
                # again with a empty string
                self.pause_completions_handler(entry, True)
                widget.set_text(prev_text)
                setattr(self, prev_text_name, None)
                self.pause_completions_handler(entry, False)
                return
            self.add_problem(PROBLEM, widget)
            on_select(None)
            compl_model = widget.get_completion().get_model()
            if (not compl_model and len(text)>2) \
               or len(text) == 2:
                add_completions(text)

        def on_match_select(completion, compl_model, iter):
            value = compl_model[iter][0]
            setattr(self, prev_text_name, utils.utf8(value))
            self.pause_completions_handler(widget, True)
            widget.set_text(utils.utf8(value))
            self.remove_problem(PROBLEM, widget)
            on_select(value)
            self.pause_completions_handler(widget, False)

        completion = widget.get_completion()
        check(completion is not None, 'the gtk.Entry %s doesn\'t have a '\
              'completion attached to it' % widget.get_name())
        sid = widget.connect('changed', on_changed)
        setattr(self, self.__changed_sid_name(widget), sid)
        completion.connect('match-selected', on_match_select)



    def start(self):
        raise NotImplementedError

    def cleanup(self):
        self.view.cleanup()

    def refresh_view(self):
        # TODO: should i provide a generic implementation of this method
        # as long as widget_to_field_map exist
        raise NotImplementedError



class GenericModelViewPresenterEditor(object):

    '''
    GenericModelViewPresenterEditor assume that model is an instance
    of object mapped to a SQLAlchemy table
    '''
    label = ''
    standalone = True
    ok_responses = ()

    def __init__(self, model, parent=None):
        """
        The editor creates it's own session and merges the model into
        it.  If the model is already in another session that original
        session will not be effected.

        :param model: an instance of an object mapped to a SQLAlchemy Table
        :param parent: the parent windows for the view or None
        """
        self.session = bauble.Session()
        self.model = self.session.merge(model)


    def attach_response(self, dialog, response, keyname, mask):
        '''
        attach a response to dialog when keyname and mask are pressed
        '''
        def callback(widget, event):
#            debug(gtk.gdk.keyval_name(event.keyval))
            if event.keyval == gtk.gdk.keyval_from_name(keyname) \
                   and (event.state & mask):
                dialog.response(response)
        dialog.add_events(gtk.gdk.KEY_PRESS_MASK)
        dialog.connect("key-press-event", callback)


    def commit_changes(self):
        '''
        Commit the changes.
        '''
        self.session.commit()
        return True
