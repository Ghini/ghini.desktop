#
# editor.py
#
# Description: a collection of functions and abstract classes for creating
# editors for Bauble data
#

import os, sys, re, copy, traceback
import xml.sax.saxutils as saxutils
import gtk, gobject
from sqlalchemy import *
from sqlalchemy.orm.session import object_session
from sqlalchemy.orm.properties import PropertyLoader
#from sqlalchemy.attributes import InstrumentedList
from formencode import *
import bauble
from bauble.prefs import prefs
import bauble.utils as utils
from bauble.error import CommitException
from bauble.utils.log import log, debug
from bauble.i18n import *

# TODO: create a generic date entry that can take a mask for the date format
# see the date entries for the accession and accession source presenters

class StringOrNoneValidator(validators.FancyValidator):
    
    def _to_python(self, value, state):
        if value is u'':
            return None
        return str(value)


class UnicodeOrNoneValidator(validators.FancyValidator):    
    
    def _to_python(self, value, state):
        if value is '':
            return None
        return unicode(value, 'utf-8')
    
    
class IntOrNoneStringValidator(validators.FancyValidator):
    
    def _to_python(self, value, state):
        if value is None or (isinstance(value, str) and value == ''):
            return None
        elif isinstance(value, (int, long)):
            return value
        try:
            return int(value)
        except:
            raise validators.Invalid('expected a int in column %s, got %s '\
                                     'instead' % (self.name, type(value)), value, state)
            

class FloatOrNoneStringValidator(validators.FancyValidator):
    
    def _to_python(self, value, state):
        if value is None or (isinstance(value, str) and value == ''):
            return None
        elif isinstance(value, (int, long, float)):
            return value
        try:
            return float(value)
        except:
            raise validators.Invalid(_('expected a float in column %(name)s, '\
                                       'got %(type)s instead') % \
                                       ({'name': self.name, 'type': type(value)}), 
                                         value, state)

#
# decorates and delegates to a SA mapped object
#
class ModelDecorator(object):
    '''
    creates notifiers and allows dict style access to our model
    '''
    
    __locals__ = ['__notifiers', 'model', '__pause', '__dirty', 'dirty']
    
    def __init__(self, model):
        super(ModelDecorator, self).__init__(model)
        super(ModelDecorator, self).__setattr__('__dirty', False)
        super(ModelDecorator, self).__setattr__('__notifiers', {})
        super(ModelDecorator, self).__setattr__('model', model)
        super(ModelDecorator, self).__setattr__('__pause', False)

    
    def _get_dirty(self):
        return super(ModelDecorator, self).__getattribute__('__dirty')
    dirty = property(_get_dirty)
    
    
    def add_notifier(self, column, callback):
        notifiers = super(ModelDecorator, self).__getattribute__('__notifiers')
        try:
            notifiers[column].append(callback)
        except KeyError:
            notifiers[column] = [callback]
    
        
    def clear_notifers(self):
        super(ModelDecorator, self).__getattribute__('__notifiers').clear()
    
        
    def pause_notifiers(self, pause):
        '''
        @param pause: flags to disable calling notifier callbacks
        @type pause: boolean
        '''
        super(ModelDecorator, self).__setattr__('__pause', False)

        
    def __getattr__(self, name):
#        debug('__getattr__(%s)' % name)
        #if name not in ModelDecorator.__dict__['__locals__']:
        if name not in super(ModelDecorator, self).__getattribute__('__locals__'):        
            return getattr(self.model, name)
        else:
            return super(ModelDecorator, self).__getattribute__(name)
        
        
    def _set(self, name, value, dirty=True):
#        debug('ModelDecorator._set(%s, %s)' % (name, value))
        model = super(ModelDecorator, self).__getattribute__('model')        
        setattr(model, name, value)
        super(ModelDecorator, self).__setattr__('__dirty', dirty)
        if name not in super(ModelDecorator, self).__getattribute__('__locals__') and \
          not super(ModelDecorator, self).__getattribute__('__pause'):            
            notifiers = super(ModelDecorator, self).__getattribute__('__notifiers')
            if name in notifiers:
                for callback in notifiers[name]:
                    callback(model, name)
        
    
    def __cmp__(self, other):
        return self.model == other
        
    def __setattr__(self, name, value):
        self._set(name, value)        

    def __getitem__(self, name):
        return getattr(self.model, name)

    def __setitem__(self, name, value):
        self._set(name, value)        
          
    def __str__(self):
        return str(self.model)



def default_completion_cell_data_func(column, renderer, model, iter, data=None):
    '''
    the default completion cell data function for 
    GenericEditorView.attach_completions
    '''
    v = model[iter][0]
    renderer.set_property('markup', str(v))
    
    
def default_completion_match_func(completion, key_string, iter):
    '''
    the default completion match function for 
    GenericEditorView.attach_completions, does a case-insensitive string 
    comparison of the the completions model[iter][0]
    '''
    value = completion.get_model()[iter][0]
    return str(value).lower().startswith(key_string.lower()) 



class GenericEditorView:
            
    def __init__(self, glade_xml, parent=None):
        '''
        glade_xml either at gtk.glade.XML instance or a path to a glade 
        XML file
        
        @param glade_xml:
        @param parent:
        '''
        if isinstance(glade_xml, gtk.glade.XML):
            self.glade_xml = glade_xml
        else: # assume it's a path string
            self.glade_xml = gtk.glade.XML(glade_xml)
        self.parent = parent
        #self.widgets = GenericEditorView._widgets(self.glade_xml)
        self.widgets = utils.GladeWidgets(self.glade_xml)
        self.response = None
    
    
    def set_widget_value(self, widget_name, value, markup=True, default=None):
        '''
        @param widget_name: the name of the widget whose value we want to set
        @param value: the value to put in the widgets
        @param markup: whether the data in value uses pango markup
        @param default: the default value to put in the widget if value is None
        '''
        utils.set_widget_value(self.glade_xml, widget_name, value, markup, 
                               default)
        
        
    def connect_dialog_close(self, dialog):
        '''
        @param dialog:
        '''
        dialog.connect('response', self.on_dialog_response)
        dialog.connect('close', self.on_dialog_close_or_delete)
        dialog.connect('delete-event', self.on_dialog_close_or_delete)    
        
        
    def on_dialog_response(self, dialog, response, *args):
        '''
        '''
        dialog.hide()
        self.response = response
        #if response < 0:
        #    dialog.hide()
    
    
    def on_dialog_close_or_delete(self, dialog, event=None):
        '''
        '''
        dialog.hide()
        return True
    

    def attach_completion(self, entry_name, 
                          cell_data_func=default_completion_cell_data_func, 
                          match_func=default_completion_match_func):
        '''
        @return: the completion attached to the entry
        '''
        # TODO: we should add a default ctrl-space to show the list of
        # completions regardless of the length of the string
        entry = self.widgets[entry_name]
        completion = gtk.EntryCompletion()
        completion.set_popup_set_width(True)
        completion.set_match_func(match_func)        
        cell = gtk.CellRendererText() # set up the completion renderer
        completion.pack_start(cell)            
        completion.set_cell_data_func(cell, cell_data_func)
        completion.set_minimum_key_length(2)
        completion.set_popup_completion(True)        
        self.widgets[entry_name].set_completion(completion)       
        return completion
    
    
    def save_state(self):
        '''
        save the state of the view by setting a value in the preferences
        that will be called restored in restore_state        
        e.g. prefs[pref_string] = pref_value 
        '''
        pass
        
    def restore_state(self):
        '''
        resore the state of the view, this is usually done by getting a value
        by the preferences and setting the equivalent in the interface
        '''        
        pass
        
    def start(self):
        '''
        '''
        raise NotImplementedError()
        
        
class DontCommitException(Exception):
    '''
    this is used for GenericModelViewPresenterEditor.commit_changes() to
    signal that for some reason the editor doesn't want to commit the current
    values and would like to redisplay
    '''
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
    
class Problems:
        
        def __init__(self):            
            self._problems = []
        
        def add(self, problem):
            '''
            @param problem: the problem to add
            '''
            self._problems.append(problem)
            
        def remove(self, problem):
            '''
            @param problem: the problem to remove
            '''
            # TODO: nothing happens if problem does not exist in self.problems
            # should we ignore it or do..
            # if problem not in self.problems
            #   raise KeyError()
            while 1:
                try:
                    self._problems.remove(problem)
                except:
                    break
            
        def __len__(self):
            '''
            @return: the number of problems
            '''
            return len(self._problems)
            
        def __str__(self):
            '''
            @return: a string of the list of problems
            '''
            return str(self._problems)
            
    
class GenericEditorPresenter:
    """
    the presenter of the Model View Presenter Pattern
    """
    problem_color = gtk.gdk.color_parse('#FFDCDF')

    def __init__(self, model, view):    
        '''
        @param model: an object instance mapped to an SQLAlchemy table
        @param view: should be an instance of GenericEditorView
        
        the presenter should usually be initialized in the following order:
        1. initialize the widgets
        2. refresh the view, put values from the model into the widgets
        3. connect the signal handlers
        '''
        widget_model_map = {}
        self.model = model
        self.view = view
        self.problems = Problems()

    
    # whether the presenter should be commited or not
    def dirty(self):
        """
        returns True or False depending on whether the presenter has changed 
        anything that needs to be committed.  This doesn't 
        necessarily imply that the session is not dirty nor is it required to
        change back to True if the changes are committed.        
        """
        raise NotImplementedError

    
    def remove_problem(self, problem_id, problem_widgets):
        """
        remove problem_id from self.problems and reset the background color
        of the widget(s) in problem_widgets
        
        @param problem_id:
        @param problem_widgets:
        """
        self.problems.remove(problem_id)
        if isinstance(problem_widgets, (tuple, list)):
            for w in problem_widgets:
                w.modify_bg(gtk.STATE_NORMAL, None)
                w.modify_base(gtk.STATE_NORMAL, None)
                w.queue_draw()
        else:
            problem_widgets.modify_bg(gtk.STATE_NORMAL, None)
            problem_widgets.modify_base(gtk.STATE_NORMAL, None)
            problem_widgets.queue_draw()
            
            
    def add_problem(self, problem_id, problem_widgets=None):
        """
        add problem_id to self.problems and change the background of widget(s) 
        in problem_widgets
        problem_widgets: either a widget or list of widgets whose background
        color should change to indicate a problem
        
        @param problem_id:
        @param problem_widgets:
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
        model = gtk.ListStore(str)
        for enum in sorted(self.model.c[field].type.values):
            if enum == None:
                model.append([''])
            else:
                model.append([enum])
        combo.set_model(model)
        
#    def bind_widget_to_model(self, widget_name, model_field):
#        # TODO: this is just an idea stub, should we have a method like
#        # this so to put the model values in the view we just
#        # need a for loop over the keys of the widget_model_map
#        pass
    

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
    def assign_simple_handler(self, widget_name, model_field, validator=None):
        '''
        assign handlers to widgets to change fields in the model
        '''
        def _set_in_model(value, field=model_field):            
#            debug('_set_in_model(%s, %s)' % (value, field))
#            debug('type(value) = %s' % type(value))
            if validator is not None:
                try:                    
                    value = validator.to_python(value, None)
                    self.problems.remove('BAD_VALUE_%s' % model_field)
                except validators.Invalid, e:
                    self.problems.add('BAD_VALUE_%s' % model_field)
                    value = None # make sure the value in the model is reset                
#            debug('%s: %s' % (value, type(value)))
            setattr(self.model, field, value)
            
        widget = self.view.widgets[widget_name]
        assert widget is not None, _('no widget with name %s') % widget_name
            
        if isinstance(widget, gtk.Entry):            
            def insert(entry, new_text, new_text_length, position):
                entry_text = entry.get_text()                
                pos = entry.get_position()
                full_text = entry_text[:pos] + new_text + entry_text[pos:]    
                _set_in_model(full_text)
            def delete(entry, start, end, data=None):
                text = entry.get_text()
                full_text = text[:start] + text[end:]
                _set_in_model(full_text)
            widget.connect('insert-text', insert)
            widget.connect('delete-text', delete)
        elif isinstance(widget, gtk.TextView):
            def insert(buffer, iter, new_text, length, data=None):
                buff_text = buffer.get_text(buffer.get_start_iter(), 
                                            buffer.get_end_iter())
                text_start = buffer.get_text(buffer.get_start_iter(), iter)
                text_end = buffer.get_text(iter, buffer.get_end_iter())
                full_text = ''.join((text_start, new_text, text_end))
                _set_in_model(full_text)
            def delete(buffer, start_iter, end_iter, data=None):
                start = start_iter.get_offset()
                end = end_iter.get_offset()                
                text = buffer.get_text(buffer.get_start_iter(),
                                       buffer.get_end_iter())                
                new_text = text[:start] + text[end:]
                _set_in_model(new_text)
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
                _set_in_model(data, model_field)                                
            widget.connect('changed', changed)
        elif isinstance(widget, (gtk.ToggleButton, gtk.CheckButton, 
                                 gtk.RadioButton)):
            def toggled(button, data=None):                
                active = button.get_active()
#                debug('toggled %s: %s' % (widget_name, active))
                button.set_inconsistent(False)
                _set_in_model(active, model_field)                
            widget.connect('toggled', toggled)
            
        else:
            raise ValueError('assign_simple_handler() -- '\
                             'widget type not supported: %s' % type(widget))
    
    
    # TODO: probably need a on_match_select in case we want to do anything after
    # the regular on_match_select
    # TODO: assign ctrl-space to match on whatever is currently in the entry
    # regardless of the length
    def assign_completions_handler(self, widget_name, field, 
                                   get_completions, 
                                   set_func=lambda self, f, v: \
                                      setattr(self.model, f, v), 
                                   format_func=lambda x: str(x),
                                   model=None):
        '''
        @param widget_name: the name of the widget in self.view.widgets
        @param field: the name of the field to set in the model
        @param set_func: the function to call to set the value in the model, 
            the default is lambda self, f, v: setattr(self.model, f, v)
        @param format_func: the func to call to format the value in the 
            completion, the default is lambda x: str(x)
        @param model: the model to set for the completions, if None then 
        use self.model
        '''
        widget = self.view.widgets[widget_name]
        if model is None:
            model = self.model
        # TODO: this works with Ctrl-Space and all but i don't know how to pop up
        # the completion
#        def callback(w, event):                
#            debug(gtk.gdk.keyval_name(event.keyval))
#            if event.keyval == gtk.gdk.keyval_from_name('space') and (event.state & gtk.gdk.CONTROL_MASK):                
#                try:
#                    c = w.get_completion() # just in case it's been deleted
#                    for kid in c.get_children():
#                        debug(kid)
#                    debug('complete')
#                    c.complete()
#                    #c.insert_prefix()
#                    debug('completd')
#                except Exception, e:
#                    debug(e)                    
#        widget.add_events(gtk.gdk.KEY_PRESS_MASK)
#        widget.connect("key-press-event", callback)
        
        PROBLEM = hash(widget_name)
        insert_sid_name = '_insert_%s_sid' % widget_name
        def add_completions(text):
#            debug('add_completions(%s)' % text)
            values = get_completions(text)
            def idle_callback(values):
                completion_model = gtk.ListStore(object)
                for v in values:
                    completion_model.append([v])
                completion = widget.get_completion()
                completion.set_model(completion_model)
            gobject.idle_add(idle_callback, values)
        def on_insert_text(entry, new_text, new_text_length, position,
                           data=None):
            if new_text == '':
                # this is to workaround the problem of having a second 
                # insert-text signal called with new_text = '' when there is a 
                # custom renderer on the entry completion for this entry
                # block the signal from here since it will call this same
                # method again and resetting the species completions
                entry.handler_block(getattr(self, insert_sid_name))
                entry.set_text(self.prev_text)
                entry.handler_unblock(getattr(self, insert_sid_name))
                return False # is this 'False' necessary, does it do anything?                
            entry_text = entry.get_text()                
            cursor = entry.get_position()
            full_text = entry_text[:cursor] + new_text + entry_text[cursor:]
            
            # TODO: need to improve completion logic for corner cases and for
            # ctrl-space handling
            compl_model = widget.get_completion().get_model()
            if (compl_model is None or len(compl_model) == 0) and len(full_text) > 0:            
                add_completions(full_text[0])
            elif len(full_text) == 1:
                add_completions(full_text[0])
                    
#            # this funny logic is so that completions are reset if the user
#            # paste multiple characters in the entry    
#            if len(new_text) == 1 and len(full_text) == 2:
#                add_completions(full_text)
#            elif new_text_length > 2:# and entry_text != '':
#                add_completions(full_text[:2])
#            self.prev_text = full_text
            
            # i think this is making sure the value in the entry was chosen
            # from the popup, i.e. set in the model
            if full_text != str(getattr(model, field)):
                self.add_problem(PROBLEM, widget)
                setattr(model, field, None)                
        def on_delete_text(entry, start, end, data=None):
            text = entry.get_text()
            full_text = text[:start] + text[end:]
            if full_text == '' or (full_text == str(model[field])):
                return            
            compl_model = widget.get_completion().get_model()
            if (compl_model is None or len(compl_model) == 0) and len(full_text) > 0:            
                add_completions(full_text[0])
            elif len(full_text) == 1:
                add_completions(full_text[0])                
            self.add_problem(PROBLEM, widget)
            model[field] = None
        def on_match_select(completion, compl_model, iter):
            value = compl_model[iter][0]
            debug('on_match_select: %s' % str(value))
            widget.handler_block(getattr(self, insert_sid_name))
            widget.set_text(str(value))
            widget.handler_unblock(getattr(self, insert_sid_name))
            widget.set_position(-1)
            self.remove_problem(PROBLEM, widget)
            set_func(self, field, value)
            debug('set prev text')
            self.prev_text = str(value)            
                    
        completion = widget.get_completion()
        
        assert completion is not None, 'the gtk.Entry %s doesn\'t have a '\
            'completion attached to it' % widget_name
        
        completion.connect('match-selected', on_match_select)
        sid = widget.connect('insert-text', on_insert_text)
        setattr(self, insert_sid_name, sid)
        widget.connect('delete-text', on_delete_text)

    
    def start(self):
        raise NotImplementedError
    
    
    def refresh_view(self):
        # TODO: should i provide a generic implementation of this method
        # as long as widget_to_field_map exist
        raise NotImplementedError
    
    

class GenericModelViewPresenterEditor(object):

    label = ''
    standalone = True
    ok_responses = ()
    
    def __init__(self, model, parent=None):
        '''
        @param model: an instance of a object mapped to an SQLAlchemy Table
        @param parent: the parent windows for the view or None
        '''                
        # the editor does all of it's work in it's own session,
        # so put a copy of the model in our session
        self.session = create_session(bind_to=bauble.db_engine)#, echo_uow=True)
        obj_session = object_session(model)              
        if obj_session is not None:
            if model in obj_session.new:
                # TODO: i would rather not touch the model's session, can we 
                # just copy the model into the new session without removing it
                # from the previous one
                obj_session.expunge(model)
                self.model = model
            else:
                self.model = self.session.load(model.__class__, model.id)
        else:
            self.model = model
                
        for name, prop in object_mapper(model).props.iteritems():
            value = getattr(self.model, name)
            if value not in (None, []) and hasattr(value, '_instance_key'):
                new_value = self.session.load(value.__class__, value.id)
                setattr(self.model, name, new_value)
        
        self.session.save_or_update(self.model)        
            
         #########   
#        model_session = object_session(model)
#        if model_session:            
#            if model in model_session.new: # pending
#                model_session.expunge(model)
#                self.session.save(model)
#                self.model = model
#            else:                
#                self.model = self.session.load(model.__class__, model.id)
#        else:
#            self.model = model
#            self.session.save(self.model)
        ########
    
    def attach_response(self, dialog, response, keyname, mask):
        '''
        attach a response to dialog when keyname and mask are pressed
        '''
        def callback(widget, event):    
#            debug(gtk.gdk.keyval_name(event.keyval))
            if event.keyval == gtk.gdk.keyval_from_name(keyname) and (event.state & mask):
                dialog.response(response)
        dialog.add_events(gtk.gdk.KEY_PRESS_MASK)
        dialog.connect("key-press-event", callback)    

    
    
    def commit_changes(self):
        '''
        '''
        
#        for obj in self.session:
#            if obj in self.session.new:
#                debug('new: %s' % obj)
#            elif obj in self.session.deleted:
#                debug('deleted: %s' % obj)
#            elif obj in self.session.dirty:
#                debug('dirty: %s' % obj)
#            else:
#                debug('nowhere: %s' % obj)
#            debug('%s' % repr(obj))
#        import logging
#        logging.getLogger('sqlalchemy').setLevel(logging.INFO)
        self.session.flush()
#        logging.getLogger('sqlalchemy').setLevel(1)
        return True
    

# TODO: this isn't being used yet, it's only an idea stub
#class GenericEditor(BaubleEditor):
#    
#    def __init__(self, model):
#        '''
#        '''
#        pass


        
