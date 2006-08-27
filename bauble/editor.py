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
from sqlalchemy.attributes import InstrumentedList
from formencode import *
import bauble
from bauble.plugins import BaubleEditor, tables
from bauble.prefs import prefs
import bauble.utils as utils
from bauble.error import CommitException
from bauble.utils.log import log, debug

#
#from formencode import validators
#
#def check_constraints(table, values):
#    '''
#    table: a SQLObject class
#    values: dictionary of values for table    
#    '''
#    for name, value in values.iteritems():
#        if name in table.sqlmeta.columns:
#            col = table.sqlmeta.columns[name]
#            validators = col.createValidators()
#            # TODO: there is another possible bug here where the value is 
#            # not converted to the proper type in the values dict, e.g. a 
#            # string is entered for sp_author when it should be a unicode
#            # but maybe this is converted properly to unicode by
#            # formencode before going in the database, this would need to
#            # be checked better if we expect proper unicode support for
#            # unicode columns
#            # - should have a isUnicode constraint for UnicodeCols
#            if value is None and notNull not in col.constraints:
#                continue
#            for constraint in col.constraints:
#                # why are None's in the contraints?
#                if constraint is not None: 
#                    # TODO: when should we accept unicode values as strings
#                    # sqlite returns unicode values instead of strings
#                    # from an EnumCol
#                    if isinstance(col, (SOUnicodeCol, SOEnumCol)) and \
#                        constraint == constraints.isString and \
#                        isinstance(value, unicode):
#                        # do isString on unicode values if we're working
#                        # with a unicode col
#                        pass
#                    else:
#                        constraint(table.__name__, col, value)
#        else:        
#            # assume it's a join and don't do anything
#            pass
            

def commit_to_table(table, values):
    '''
    table: a SQLObject class
    values: dictionary of values for table    
    '''
    table_instance = None
    check_constraints(table, values)    
    if 'id' in values:# updating row
        table_instance = table.get(values["id"])                    
        del values["id"]
        table_instance.set(**values)
    else: # creating new row
#        debug(values)
#        debug(table)
        table_instance = table(**values)
    return table_instance
        

def get_widget_value(glade_xml, widget_name, column=0):
    """
    column is the column to use if the widget's value is a TreeModel
    """
    w = glade_xml.get_widget(widget_name)
    if isinstance(w, gtk.Entry):
        return w.get_text()
    elif isinstance(w, gtk.TextView):
        buffer = w.get_buffer()
        start = buffer.get_start_iter()
        end = buffer.get_end_iter()
        return buffer.get_text(start, end)
    elif isinstance(w, gtk.ComboBoxEntry) or isinstance(w, gtk.ComboBox):
        v = None
        i = w.get_active_iter()
        if i is not None:
            v = w.get_model().get_value(i, column)
        return v
    elif isinstance(w, gtk.CheckButton):
        return w.get_active()
    elif isinstance(w, gtk.Label):
        return w.get_text()
    raise ValueError("%s -- set_dict_value_from_widget: " \
                     " ** unknown widget type: %s " % (__file__,str(type(w))))
    

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
            raise validators.Invalid('expected a float in column %s, got %s '\
                                     'instead' % (self.name, type(value)), value, state)

#
# decorates and delegates to a SA mapped object
#
class ModelDecorator(object):
    '''
    creates notifiers and allows dict style access to our model
    '''
    
    __locals__ = ['__notifiers', 'model', '__pause']
    
    def __init__(self, model):
        super(ModelDecorator, self).__init__(model)
        super(ModelDecorator, self).__setattr__('__notifiers', {})
        super(ModelDecorator, self).__setattr__('model', model)
        super(ModelDecorator, self).__setattr__('__pause', False)

    
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
        
        
    def __set(self, name, value):
#        debug('ModelDecorator.__set(%s, %s)' % (name, value))
        model = super(ModelDecorator, self).__getattribute__('model')
        setattr(model, name, value)
        if not super(ModelDecorator, self).__getattribute__('__pause'):            
            notifiers = super(ModelDecorator, self).__getattribute__('__notifiers')
            if name in notifiers:
                for callback in notifiers[name]:
                    callback(model, name)
        
        
        
    def __setattr__(self, name, value):
        self.__set(name, value)        

    def __getitem__(self, name):
        return getattr(self.model, name)

    def __setitem__(self, name, value):
        self.__set(name, value)        
          
    def __str__(self):
        return str(self.model)

# TODO: this is a new, simpler ModelRowDict sort of class, it doesn't try
# to be as smart as ModelRowDict but it's a bit more elegant, the ModelRowDict
# should be abolished or at least changed to use SQLObjectProxy
# TODO: this should do some contraint checking before allowing the value to be
# set in the dict
# TODO: if you try to access a join in the so_object then it will add it
# to the dictionary, so then if you try to commit from the dict keys/value
# you will get an error, shouldn't allow this to happen though right
# now to get around this you can just access the joins through the so_object
# member
# TODO: i think we should only add things to self.dict if they are column types
# since this is used for committing, all other types aren't used in the commit
#class SQLObjectProxy(dict):    
#    '''
#    SQLObjectProxy does two things
#    1. if so_object is an instance it caches values from the database and
#    if those values are changed in the object then the values aren't changed
#    in the database, only in our copy of the values
#    2. if so_object is NOT an instance but simply an SQLObject derived class 
#    then this proxy will only set the values in our local store but will
#    make sure that the columns exist on item access and will return default
#    values from the model if the values haven't been set
#    3. keys will only exist in the dictionary if they have been accessed, 
#    either by read or write, so **self will give you the dictionary of only
#    those things that have been read or changed
#    
#    ** WARNING: ** this is definetely not thread safe or good for concurrent
#    access, this effectively caches values from the database so if while using
#    this class something changes in the database this class will still use
#    the cached value
#    '''
#    
#    # TODO: needs to be better tested
#    
#    def __init__(self, so_object):
#        # we have to set so_object this way since it is called in __contains__
#        # which is used by self.__setattr__                        
#        dict.__setattr__(self, 'so_object', so_object)
#        dict.__setattr__(self, 'dirty', False)
#        dict.__setattr__(self, 'isinstance', False)
#        dict.__setattr__(self, '_notifiers', {})
#        dict.__setattr__(self, '_pause', False)
#        
#        
#        #self._notifiers = {}
#        dict.__setattr__(self, '_notifiers', {})
#        if isinstance(so_object, SQLObject):
#            dict.__setattr__(self, 'isinstance', True)
#            #self.isinstance = True
#            self['id'] = so_object.id # always keep the id
#        elif not issubclass(so_object, SQLObject):
#            msg = 'row should be either an instance or class of SQLObject'
#            raise ValueError('SQLObjectProxy.__init__: ' + msg)  
#    
#            
#    def pause_notifiers(self, pause):
#        '''
#        @param pause: flags to disable calling notifier callbacks
#        @type pause: boolean
#        '''
#        dict.__setattr__(self, '_pause', pause)
#    
#    
#    # TODO: provide a way to remove notifiers
#    def clear_notifiers(self):
#        '''
#        remove all notifiers
#        '''
#        dict.__getattribute__(self, '_notifiers').clear()
#    
#    
#    def add_notifier(self, column, callback):
#        '''
#        add a callback function to be called whenever a column is changed
#        callback should be of the form C{def callback(field)}
#        
#        @param column: the name of the column in the SQLObject
#        @param callback: the call back to call when the column is changed
#        '''
#        try:
#            dict.__getattribute__(self, '_notifiers')[column].append(callback)
#        except KeyError:
#            dict.__getattribute__(self, '_notifiers')[column] = [callback]
#
#
#    def __contains__(self, item):
#        """
#        this will check if item is in the dictionary or if self.so_object has an
#        attribute by the name of item
#        
#        this causes the 'in' operator and has_key to behave differently,
#        e.g. 'in' will tell you if it exists in either the dictionary
#        or the table while has_key will only tell you if it exists in the 
#        dictionary, this is a very important difference
#        
#        @param item:  a field name for the SQLObject class this proxy wraps
#        """
#        if dict.__contains__(self, item):
#            return True
#        
#        return hasattr(dict.__getattribute__(self, 'so_object'), item)
#    
#    
#    def __getitem__(self, item):
#        '''
#        get items from the dict
#        if the item does not exist then we create the item in the dictionary
#        and set its value from the default or to None
#        
#        @param item:
#        '''
##        debug('_getitem_(%s)' % item)
#        
#        # item is already in the dict
#        if self.has_key(item): # use has_key to avoid __contains__
#            return self.get(item)                
#        
#        # avoid all the __getattr__ calls for a but of a speed improvement
#        self_so_object =  self.__getattribute__('so_object')
#        # else if row is an instance then get it from the table
#        v = None                        
#        if self.isinstance:            
#            v = getattr(self_so_object, item)            
#            # resolve foreign keys
#            # TODO: there might be a more reasonable wayto do this            
#            if item in self_so_object.sqlmeta.columns:
#                column = self_so_object.sqlmeta.columns[item]            
#                if v is not None and isinstance(column, SOForeignKey):
#                    table_name = column.foreignKey                    
#                    v = tables[table_name].get(v)
#        else:
#            # else not an instance so at least make sure that the item
#            # is an attribute in the row, should probably validate the type
#            # depending on the type of the attribute in row
#            #if not hasattr(self.so_object, item):
#            if not hasattr(self_so_object, item):
#                msg = '%s has no attribute %s' % (self_so_object.__class__, 
#                                                  item)
#                raise KeyError('ModelRowDict.__getitem__: ' + msg)                        
#                
#        
#        if v is None:
#            # we haven't gotten anything for v yet, first check the 
#            # default for the column
#            if item in self_so_object.sqlmeta.columns:
#                default = self_so_object.sqlmeta.columns[item].default
#                if default is NoDefault:
#                    default = None
#                v = default
#        
#        # this effectively caches the row item from the instance, the False
#        # is so that the row is set dirty only if it is changed from the 
#        # outside
#        self.__setitem__(item, v, False)
#        return v            
#           
#                
#    def __setitem__(self, key, value, dirty=True):
#        '''
#        set item in the dict, this does not change the database, only 
#        the cached values
#        
#        @param key:
#        @param value:
#        @param dirty:
#        '''
##        debug('setitem(%s, %s, %s)' % (key, value, dirty))
#        dict.__setitem__(self, key, value)
#        dict.__setattr__(self, 'dirty', dirty)
#        if dirty:
#            try:
#                # if we don't have this hasattr here we'll get infiniter 
#                # recursion on _contains_, im not real sure why
#                #if hasattr(self, '_notifiers') and not self._pause:
#                if hasattr(self, '_pause') and not dict.__getattribute__(self, '_pause'):
#                    #for callback in self._notifiers[key]:
#                    for callback in dict.__getattribute__(self, '_notifiers')[key]:
#                        callback(key)
#            except KeyError, AttributeError:
#                pass 
#    
#    
#    def __getattr__(self, name):
#        '''
#        override attribute read 
#        
#        @param name:
#        '''
##        debug('SQLObjectProxy.__getattr__(%s)' % name)
##        if dict.__contains__(self, name):        
#        if name in self: 
#            return self.__getitem__(name)
#        return dict.__getattribute__(self, name)
#    
#    
#    def __setattr__(self, name, value):
#        '''
#        override attribute write
#        
#        @param name:
#        @param value:
#        '''
##        debug('__setattr__(%s, %s)' % (name, value))        
#        if name in self:         
#            self.__setitem__(name, value)
#        elif hasattr(self, name):        
#            dict.__setattr__(self, name, value)    
#        else:
#            raise AttributeError('no attribute %s' % name)
#    
#    
#    def _get_columns(self):
#        '''
#        get the column dictionary from the sqlobject this proxy wraps
#        '''
#        return self.so_object.sqlmeta.columns
#    columns = property(_get_columns)


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
    
    
#    class _widgets(dict):
#        '''
#        dictionary and attribute access for widgets
#        '''
#
#        def __init__(self, glade_xml):
#            '''
#            @params glade_xml: a gtk.glade.XML object
#            '''
#            self.glade_xml = glade_xml
#        
#        def __getitem__(self, name):
#            '''
#            @param name:
#            '''
#            # TODO: raise a key error if there is no widget
#            return self.glade_xml.get_widget(name)
#    
#        def __getattr__(self, name):
#            '''
#            @param name:
#            '''
#            return self.glade_xml.get_widget(name)
        
        
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
        self.widgets[entry_name]
        completion = gtk.EntryCompletion()
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
        
        _problems = []
        
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
    '''
    the presenter of the Model View Presenter Pattern
    '''
    problem_color = gtk.gdk.color_parse('#FFDCDF')
#    def __init__(self, model, view, defaults={}):
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
#        self.defaults = defaults
        self.problems = Problems()


    def remove_problem(self, problem_id, problem_widgets):
        '''
        remove problem_id from self.problems and reset the background color
        of the widget(s) in problem_widgets
        
        @param problem_id:
        @param problem_widgets:
        '''
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
        '''
        add problem_id to self.problems and change the background of widget(s) 
        in problem_widgets
        problem_widgets: either a widget or list of widgets whose background
        color should change to indicate a problem
        
        @param problem_id:
        @param problem_widgets:
        '''
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
        assert widget is not None, 'no widget with name %s' % widget_name
            
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
    def assign_completions_handler(self, widget_name, field, 
                                   get_completions, 
                                   set_func=lambda self, f, v: setattr(self.model, f, v), 
                                   format_func=lambda x: str(x)):
        '''
        @param widget_name: the name of the widget in self.view.widgets
        @param field: the name of the field to set in the model
        @param set_func: the function to call to set the value in the model, 
            the default is lambda self, f, v: setattr(self.model, f, v)
        @param format_func: the func to call to format the value in the 
            completion, the default is lambda x: str(x)
        '''
        widget = self.view.widgets[widget_name]
        PROBLEM = hash(widget_name)
        insert_sid_name = '_insert_%s_sid' % widget_name
#        insert_sid = None
#        delete_sid = None
        def add_completions(text):
#            debug('add_completions(%s)' % text)
            values = get_completions(text)
            def idle_callback(values):
                model = gtk.ListStore(object)
                for v in values:
                    model.append([v])
                completion = widget.get_completion()
                completion.set_model(model)
            gobject.idle_add(idle_callback, values)
        def on_insert_text(entry, new_text, new_text_length, position, data=None):
            #debug('on_species_insert_text: \'%s\'' % new_text)
            # debug('%s' % self.model)
            if new_text == '':
                # this is to workaround the problem of having a second 
                # insert-text signal called with new_text = '' when there is a 
                # custom renderer on the entry completion for this entry
                # block the signal from here since it will call this same
                # method again and resetting the species completions
                #entry.handler_block(self.insert_genus_sid)
                entry.handler_block(getattr(self, insert_sid_name))
                entry.set_text(self.prev_text)
                #entry.handler_unblock(self.insert_genus_sid)
                entry.handler_unblock(getattr(self, insert_sid_name))
                return False # is this 'False' necessary, does it do anything?                
            entry_text = entry.get_text()                
            cursor = entry.get_position()
            full_text = entry_text[:cursor] + new_text + entry_text[cursor:]
            # this funny logic is so that completions are reset if the user
            # paste multiple characters in the entry    
            if len(new_text) == 1 and len(full_text) == 2:
                add_completions(full_text)
            elif new_text_length > 2:# and entry_text != '':
                add_completions(full_text[:2])
            self.prev_text = full_text
            
            if full_text != str(getattr(self.model, field)):
                self.add_problem(PROBLEM, widget)
                setattr(self.model, field, None)                
        def on_delete_text(entry, start, end, data=None):
            text = entry.get_text()
            full_text = text[:start] + text[end:]
            if full_text == '' or (full_text == str(self.model[field])):
                return
            self.add_problem(PROBLEM, widget)
            #setattr(self.model, field, None)
            debug(type(self.model))
            debug('self.model[%s] = None' % field)
            self.model[field] = None
        def on_match_select(completion, compl_model, iter):
            value = compl_model[iter][0]
            debug('on_match_select: %s' % str(value))
            #entry = self.view.widgets.sp_genus_entry
            
            #widget.handler_block(self.insert_genus_sid)
            widget.handler_block(getattr(self, insert_sid_name))
            widget.set_text(str(value))
            #widget.handler_unblock(self.insert_genus_sid)
            widget.handler_unblock(getattr(self, insert_sid_name))
            widget.set_position(-1)
            self.remove_problem(PROBLEM, widget)
            # TODO: temporarily disabled this when doing the set_func stuff
            #self.session.save(value)
            #setattr(self.model, field, value)
            #setattr(self.model, field, value.id)
            set_func(self, field, value)
            self.prev_text = str(value)            
                    
        completion = widget.get_completion()
        assert completion is not None, 'the gtk.Entry %s doesn\'t have a '\
            'completion attached to it' % widget_name
        
        completion.connect('match-selected', on_match_select)
        #if self.model.genus is not None:
        #    self.idle_add_genus_completions(str(self.model.genus)[:2])
        sid = widget.connect('insert-text', on_insert_text)
        setattr(self, insert_sid_name, sid)
        widget.connect('delete-text', on_delete_text)
    
    def start(self):
        raise NotImplementedError
    
    def refresh_view(self):
        # TODO: should i provide a generic implementation of this method
        # as long as widget_to_field_map exist
        raise NotImplementedError
    
    

class GenericModelViewPresenterEditor(BaubleEditor):

    label = ''
    standalone = True
    ok_responses = ()
    
    #def __init__(self, model, defaults={}, parent=None):
    def __init__(self, model, parent=None):
        '''
        @param model: an instance of a object mapped to an SQLAlchemy Table
        @param defaults: a dictionary of column names in the model and default 
            values for the columns if not other value is specified
        @param parent: the parent windows for th view
        '''
        self.session = create_session(bind_to=bauble.app.db_engine)            
        model_session = object_session(model)
        if model_session:            
            if model in model_session.new: # pending
                model_session.expunge(model)
                self.session.save(model)
                self.model = model
            else:                
                self.model = self.session.load(model.__class__, model.id)
        else:
            self.model = model
            self.session.save(self.model)

    
    def assert_args(self, model, type_class, defaults):
        '''
        to be called on the passed model and parameter and not on self.model
        this would normally be called by a class extending this class before
        GenericModelViewPresenterEditor.__init__() is called
        '''
        # FIXME: this can cause the wrong error in issubclass if model
        # is not and class type
        # either an instance or class of type_class
        assert(isinstance(model, type_class) or issubclass(model, type_class))
        # can't have both defaults and a model instance
        assert(not isinstance(model, type_class) or len(defaults.keys()) == 0)
        

    def start(self, commit_transaction=True):    
        '''
        @param commit_transaction:
        '''
        not_ok_msg = 'Are you sure you want to lose your changes?'
        exc_msg = "Could not commit changes.\n"
        committed = None
        while True:
            response = self.presenter.start()
            self.view.save_state() # should view or presenter save state
            if response == gtk.RESPONSE_OK or response in self.ok_responses:
                try:
                    committed = self.commit_changes()                
                except DontCommitException:
                    continue
                except BadValue, e:
                    utils.message_dialog(saxutils.escape(str(e)),
                                         gtk.MESSAGE_ERROR)
                except CommitException, e:
                    debug(traceback.format_exc())
                    exc_msg + ' \n %s\n%s' % (str(e), e.row)
                    utils.message_details_dialog(saxutils.escape(exc_msg), 
                                 traceback.format_exc(), gtk.MESSAGE_ERROR)
                    sqlhub.processConnection.rollback()
                    sqlhub.processConnection.begin()
                except Exception, e:
                    debug(traceback.format_exc())
                    exc_msg + ' \n %s' % str(e)
                    utils.message_details_dialog(saxutils.escape(exc_msg), 
                                                 traceback.format_exc(),
                                                 gtk.MESSAGE_ERROR)
                    sqlhub.processConnection.rollback()
                    sqlhub.processConnection.begin()
                else:
                    break
            elif self.model.dirty and utils.yes_no_dialog(not_ok_msg):
#                debug(self.model.dirty)
                sqlhub.processConnection.rollback()
                sqlhub.processConnection.begin()
                self.model.dirty = False
                break
            elif not self.model.dirty:
                break
            
        if commit_transaction:
            sqlhub.processConnection.commit()

        return committed


   # TODO: it would probably be better to validate the values when 
    # entering then into the interface instead of accepting any crap and 
    # validating it on commit
    # TODO: this has alot of work arounds, i don't think sqlobject.contraints
    # are complete or well tested, maybe we should create our own contraint 
    # system or at least help to complete SQLObject's constraints
    def _check_constraints(self, values):
        '''
        '''
        return check_contraints(self.table, values)


    def _commit(self, values):
        '''
        '''
        if self.model.isinstance:
            table_class = self.model.so_object.__class__
        else:
            table_class = self.model.so_object
        return commit_to_table(table_class, values)
    
    
    def commit_changes(self):
        '''
        '''
        self.session.flush()
        return True
    

# TODO: this isn't being used yet, it's only an idea stub
#class GenericEditor(BaubleEditor):
#    
#    def __init__(self, model):
#        '''
#        '''
#        pass
    
    
#
# editor interface
#
class TableEditor(BaubleEditor):

    standalone = True
    
    # the model parameter is only there to support the transition to the new
    # editor interface
    def __init__(self, table, select=None, defaults={}, parent=None, model=None):
        '''
        parent parameter added revision circa 242, allows
        any editor extending this class the set it modality properly
        '''
        super(TableEditor, self).__init__()
        self.defaults = copy.copy(defaults)
        self.table = table
        self.select = select                
        self.parent = parent
        self.__dirty = False
        
        
    def start(self, commit_transaction=True): 
        '''
        required to implement, should return the values committed by this 
        editor
        '''
        raise NotImplementedError


    #
    # dirty property
    #
    def _get_dirty(self):
        return self.__dirty    
    def _set_dirty(self, dirty):
        self.__dirty = dirty        
    dirty = property(_get_dirty, _set_dirty)


    # TODO: it would probably be better to validate the values when 
    # entering then into the interface instead of accepting any crap and 
    # validating it on commit
    # TODO: this has alot of work arounds, i don't think sqlobject.contraints
    # are complete or well tested, maybe we should create our own contraint 
    # system or at least help to complete SQLObject's constraints
    def _check_constraints(self, values):
        '''
        '''
        return check_contraints(self.table, values)


    def _commit(self, values):       
        '''
        '''
        return commit_to_table(self.table, values)
    

    def commit_changes(self):
        '''
        '''
        raise NotImplementedError
    


class TableEditorDialog(TableEditor):
    
    def __init__(self, table, title="Table Editor",
                 parent=None, select=None, 
                 defaults={}, dialog=None):
        '''
        '''
        super(TableEditorDialog, self).__init__(table, select, defaults)
        if parent is None: # should we even allow a change in parent
            parent = bauble.app.gui.window

        # allow the dialog to 
        if dialog is None:
            self.dialog = gtk.Dialog(title, parent, 
                         gtk.DIALOG_MODAL | \
                         gtk.DIALOG_DESTROY_WITH_PARENT,
                         (gtk.STOCK_OK, gtk.RESPONSE_OK, 
                          gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
        else: 
            self.dialog = dialog
        self._values = []

    
    def _run(self):
        '''
        '''
        # connect these here in case self.dialog is overwridden after the 
        # construct is called    
        self.dialog.connect('response', self.on_dialog_response)
        self.dialog.connect('close', self.on_dialog_close_or_delete)
        self.dialog.connect('delete-event', self.on_dialog_close_or_delete)
        '''
        loops until return
        '''
        committed = None
        not_ok_msg = 'Are you sure you want to lose your changes?'
        exc_msg = "Could not commit changes.\n"
        while True:
            response = self.dialog.run()
            self.save_state()
            if response == gtk.RESPONSE_OK:
                try:
                    committed = self.commit_changes()
                except BadValue, e:
                    utils.message_dialog(saxutils.escape(str(e)),
                                         gtk.MESSAGE_ERROR)
                except CommitException, e:
                    debug(traceback.format_exc())
                    exc_msg + ' \n %s\n%s' % (str(e), e.row)
                    utils.message_details_dialog(saxutils.escape(exc_msg), 
                                 traceback.format_exc(),
                                                         gtk.MESSAGE_ERROR)
                    self.reset_committed()
                    self.reset_background()
                    #set the flag to change the background color
                    e.row[1] = True 
                    sqlhub.processConnection.rollback()
                    sqlhub.processConnection.begin()
                except Exception, e:
                    debug(traceback.format_exc())
                    exc_msg + ' \n %s' % str(e)
                    utils.message_details_dialog(saxutils.escape(exc_msg), 
                                                 traceback.format_exc(),
                                                 gtk.MESSAGE_ERROR)
                    self.reset_committed()
                    self.reset_background()
                    sqlhub.processConnection.rollback()
                    sqlhub.processConnection.begin()
                else:
                    break
            elif self.dirty and utils.yes_no_dialog(not_ok_msg):
                sqlhub.processConnection.rollback()
                sqlhub.processConnection.begin()
                self.dirty = False
                break
            elif not self.dirty:
                break
        self.dialog.destroy()
        return committed        

        
    def reset_committed(self):    
        '''
        reset all of the ModelRowDict.committed attributes in the view
        '''
        for row in self.view.get_model():
            row[0].committed = False


    def reset_background(self):
        '''
        turn off all background-set attributes
        '''
        for row in self.view.get_model():
            row[1] = False


    def on_dialog_response(self, dialog, response, *args):
        # system-defined GtkDialog responses are always negative, in which
        # case we want to hide it
        #debug(dialog)
        if response < 0:
            self.dialog.hide()
            #self.dialog.emit_stop_by_name('response')
        #return response
    
    
    def on_dialog_close_or_delete(self, widget, event=None):
        self.dialog.hide()
        return True
            
            
    def start(self, commit_transaction=True):
        # at the least should call self._run()
        raise NotImplementedError('TableEditorDialog.start()')
    

    def save_state(self):
        '''
        save the state of the view by setting a value in the preferences
        that will be called restored in restore_state        
        e.g. prefs[pref_string] = pref_value 
        '''
        pass


        
