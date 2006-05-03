#
# editors module
#

import os, sys, re, copy, traceback
import xml.sax.saxutils as saxutils
import warnings
import gtk
from sqlobject.sqlbuilder import *
from sqlobject import *
from sqlobject.constraints import BadValue, notNull
from sqlobject.joins import SOJoin, SOSingleJoin
import bauble
from bauble.plugins import BaubleEditor, BaubleTable, tables
from bauble.prefs import prefs
import bauble.utils as utils
from bauble.error import CommitException

from bauble.utils.log import log, debug


# TODO: if the last column is made smaller from draggin the rightmost part
# of the header then automagically reduce the size of  the dialog so that the 
# there isn't the extra junk past the, and i guess do the same to the leftmost
# side of the the first column

# TODO: need some type of smart dialog resizing like when columns are added
# change the size of the dialog to fit unless you get bigger than the screen
# then turn on the scroll bar, and something similar for adding rows 

# FIXME: everytime you open and close a TreeViewEditorDialog the dialog
# get a little bigger, i think the last column is creeping, only happens
# when there is a vertical scrollbar, it might be wise to turn off the 
# scrollbar before getting the widths to see if this changes anything
# UPDATE: i did a quick fix for this, grep for self.view_window or see
# add_new_row
# - got an email from the bug i filed on this which give a workaround
    
# TODO: create a contextual helps so that pressing ctrl-space on a cell
# gives a tooltip or dialog giving you more information about the current
# cell you are editing
 
# TODO:  i was using ModelRowDict.committed to indicate which rows have been 
# committed so that when there was a problem and an exception was raised on a 
# commit then
# the next time around in commit_changes we would only have to commit those
# rows which hadn't yet been committed, this didn't work because sometimes
# the exception would invalidate the transaction and we have to start over
# either way, i don't think there's any reason to keep this committed attribute
# around, we should remove it from ModelRowDict and all of the 
# cell_data_func function in the columns

# TODO: the TreeViewEditorDialog has been fixed to support deleting the value
# in a column this may mean that using None in and EnumCol work so since it 
# would be better to store None in an EnumCol instead of a bunch of empty 
# strings so we should check and change all the models if so

# TODO: remove underscores in the context menu and would probably be good to
# capitalize the first letter of the first work in the add section of the 
# context menu. i.e. Vernacular names


#class CellRendererButton(gtk.GenericCellRenderer):
#    
#    def __init__(self, *args, **kwargs):
#        super(CellRendererButton, self).__init__(*args, **kwargs)
#        
#    def on_get_size(self, widget, cell_area):
#        pass
#    
#    def on_render(self, window, widget, background_area, cell_area, 
#                  expose_area, flags):
#        pass
#    
#    def on_activate(self, event, widget, path, background_area, cell_area, 
#                    flags):
#        pass
#    
#    def on_start_editing(self, event, widget, path, background_area, cell_area,
#                         flags):
#        pass




class GenericViewColumn(gtk.TreeViewColumn):
    
    def __init__(self, tree_view_editor, header, renderer):
        #renderer.weight = 900    
        super(GenericViewColumn, self).__init__(header, renderer, 
                        cell_background_set=1)
        renderer.set_property('cell-background-gdk', 
                              gtk.gdk.color_parse('#EC9FA4'))
        #renderer.set_property('cell-background', 'red')
        #renderer.cell_background = 'pink'
        if not isinstance(tree_view_editor, TreeViewEditorDialog):
            raise ValueError('tree_view_editor must be an isntance of '\
                             'TreeViewEditorDialog')
                             
        self.__dirty = False # property
        self.table_editor = tree_view_editor
        self.renderer = renderer
        self.set_cell_data_func(renderer, self.cell_data_func)
                
        self.meta = GenericViewColumn.Meta()            
        self.set_visible(self.meta.required)
        self.set_min_width(50)
        self.set_clickable(True)
        self.set_resizable(True)
        self.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        self.set_reorderable(True)
        
    class Meta:
        # the SQLObject column this ViewColumn represents
        so_col = None
        
        #
        # the method to call to get this list of completions for this
        # column is the column is a text entry, 
        # method signature: get_completions(complete_for_str)
        # TODO: how would i add this field to the class Meta 
        # inside TextColumn so that this field is only relevant 
        # to TextColumn
        #
        get_completions = None
        
        # the column provides its own editor
        editor = None
        
        # is self.required is True then you can't hide this column
        # from the view
        required = False
        
        # if self.getter is set then use this method to return the values
        # for the row, e.g. self.meta[colname].getter(row)
        getter = None
 
        # a method to validate the data in the column before it is set
        validate = lambda x: x
             
    #
    # dirty property
    #         
    def _get_dirty(self):
        return self.__dirty
    def _set_dirty(self, dirty):
        self.__dirty = dirty
        if not self.table_editor.dirty: # can't undirty the editor
            self.table_editor.dirty = dirty         
    dirty = property(_get_dirty, _set_dirty)
    
   
    #
    # name property
    #
    def _get_name(self):
        if isinstance(self.meta.so_col, SOJoin):
            return self.meta.so_col.joinMethodName        
        elif self.meta.so_col is not None:
            return self.meta.so_col.name
        else:
            return self.get_title()
    name = property(_get_name)
    

    def _set_view_model_value(self, path, value):        
        model = self.table_editor.view.get_model()
        i = model.get_iter(path)
        row = model.get_value(i, 0)        
        row[self.name] = value
    
            
    def cell_data_func(self, column, renderer, model, iter, data=None):
        # NOTE: all classes that extend GenericViewColumn should add this
        # at the top of the cell_data_func method so that behavior is 
        # consistent for rows that have already been committed
#        row = model.get_value(iter, 0)
#        if row.committed:
#            renderer.set_property('sensitive', False)
#            renderer.set_property('editable', False)
#        else:
#            renderer.set_property('sensitive', True)
#            renderer.set_property('editable', True)
        raise NotImplementedError, "%s.cell_data_func not implemented" % \
            self.__class__.__name__               
 
    
class SOViewColumn(GenericViewColumn):
    
    def __init__(self,  tree_view_editor, header, renderer, so_col):
        '''
        so_col could be either a SOCol or and SOJoin, see SQLObject
        '''        
        super(SOViewColumn, self).__init__(tree_view_editor, header, renderer)
        assert so_col is not None
        self.meta.so_col = so_col  
        if isinstance(so_col, SOCol) and so_col._default == NoDefault:
            self.meta.required = True
            self.meta.default = so_col._default
            self.set_visible(True)
                        
    class Meta(GenericViewColumn.Meta):
        so_col = None
                     
#
#
#
class TextColumn(SOViewColumn):
    
    def __init__(self, tree_view_editor, header, renderer=None, so_col=None):
        if renderer is None:
            renderer = gtk.CellRendererText()            
        super(TextColumn, self).__init__(tree_view_editor, header, renderer, 
                                         so_col)
        #SOViewColumn.__init__(self, tree_view_editor, header, renderer, so_col)
        self.renderer.set_property("editable", True)
        self.renderer.connect("editing_started", self.on_editing_started, 
                              tree_view_editor)
        self.renderer.connect('edited', self.on_edited)
        #self.set_dirty = GenericViewColumn.set_dirty
        #self.dirty = super(TextColumn, self).dirty
    
    
            
    def cell_data_func(self, column, renderer, model, iter, data=None):
        row = model.get_value(iter, 0)
#        if colname not in row: 
#            return # this should never happen
        if row.committed:
            renderer.set_property('sensitive', False)
            renderer.set_property('editable', False)
        else:
            renderer.set_property('sensitive', True)
            renderer.set_property('editable', True)
            
        value = row[self.name]
        if value is None: # no value in model
            renderer.set_property('text', None)     
        elif isinstance(value, tuple):     
            # the tuple should be the number of items in the column and the
            # number of values waiting to be committed
            if value[0] is None:
                text = '%d pending' % (len(value[1]))
            else:
                text = '%d values, %d pending' % (len(value[0]), len(value[1]))
            renderer.set_property('text', text)
        elif isinstance(value, list):  # the item is a of values
            text = '%s values' % len(value)
            renderer.set_property('text', text)
        else: 
            # just plain text in model column or something convertible 
            # to string like a table row
            renderer.set_property('text', str(value))
            

    def on_edited(self, renderer, path, new_text, set_in_model=True):
        # means that the value is set by the on_match_completed function,
        # there should be a way to set either on_edited or on_completion
        # but not both
        # TODO: what happens when you type something into the column
        # that has a completion but what you type isn't a completion
        # we should either query for the value or don't allow it to 
        # be set
        # don't allow empty strings in the model, this usually means a null
        # value in the cell
        if new_text == "":
            value = None
        else:
            value = new_text
            
        if self.meta.get_completions is not None:
            return          
        if self.meta.editor is None:
            self._set_view_model_value(path, value)
            self.dirty = True 
            
                                           
    def on_editing_started(self, cell, entry, path, view):
        # if the cell has it's own editor we shouldn't be here
        if self.meta.editor is not None: 
            entry.connect('key-press-event', self.on_key_press, path)
            entry.set_property('editable', False)
                
        #entry.connect("key-press-event", self.on_cell_key_press, 
#                         path, colname)
# TODO: set up a validator on the col depending on the sqlobj.column type
        
        if isinstance(self.meta.so_col, SOForeignKey) and \
          not self.meta.get_completions and not self.meta.editor:
              msg  = "%s is a foreign key but there are no completions and "\
                     "no editor has been defined for this column" % self.name
              utils.message_dialog(msg, gtk.MESSAGE_ERROR)
              entry.set_property('editable', False)
              return

        entry.connect("insert-text", self.on_insert_text, path)
        #entry.connect("editing-done", self.on_editing_done)
        #self.current_entry = editable        
        # if not a foreign key then validate, foreign keys can only
        # be entered from existing values and so don't need to
        # be validated
        #if not self.column_meta[colname].foreign:
        #    if self.column_meta[colname].  
      

    def on_completion_match_selected(self, completion, model, iter, 
                                     view_model_path):
        """
        all foreign keys should use entry completion so you can't type in
        values that don't already exists in the database, therefore, allthough
        i don't like it the view.model.row is set here for foreign key columns
        and in self.on_edited for other column types                
        """        
        # we assume on a successfull completion that 0 is the value
        # that we matched on and 1 is the value we want in the model
        self.dirty = True
        value = model.get_value(iter, 1)
        self._set_view_model_value(view_model_path, value)
        
        
    def on_insert_text(self, entry, text, length, position, path):
        """
        handle text filtering/validation and completions
        """
    # TODO: this is flawed since we can't get the index into the entry
    # where the text is being inserted so if the used inserts text into 
    # the middle of the string then this could break
        # TODO: the problem is only validates on letter at a time
        # we need to have a format string which is inserted
        # in the entry before typeing starts and fills in the gap
        # as the user types
#        try:
#            self.column_meta[colname].validate(text)
#        except ValueError:
#            entry.stop_emission("insert_text")
        
        
        # there are no completions, disconnect from signal
        # TODO: we should really be disconnecting with the signal with
        # this signal id so we don't stop all insert_text signals        
        if self.meta.get_completions is None:
            return
                    
        full_text = entry.get_text() + text      
#        debug(full_text)
        if len(full_text) == 0: # remove the completion when entry is empty
            entry.set_completion(None)
            return
          
        entry_completion = entry.get_completion()        
#        debug(entry_completion)
        if entry_completion is None:
 #           debug('create completion')
            entry_completion = gtk.EntryCompletion()
            entry_completion.set_minimum_key_length(2)
            entry_completion.set_text_column(0)
            entry_completion.connect("match-selected", 
                                     self.on_completion_match_selected, 
                                     path)
            entry.set_completion(entry_completion)
            
        if len(full_text) >= 2:
#            debug('get completion')
            # this could take too long if there are alot of completions
            model = self.meta.get_completions(full_text)            
            entry_completion.set_model(model)


    def _start_editor(self, path):
        '''
        this provides the standard behavior of starting an external editor
        on a column and adding the value returned from editor.commit_changes
        into the model
        _start_editor can abe extended to make it easier to use external 
        editors that don\'t provide standard behavior
        '''
    # TODO: should make it possible to pass a parent to the sub editor
    # so that the sub editor can be modal to this editor
        model = self.table_editor.view.get_model()
        row = model[model.get_iter(path)][0]
        existing = row[self.name]
        old_committed = []
        select = None
        if isinstance(existing, tuple): # existing/committed paot
            existing, old_committed = existing
            select = existing+old_committed
        else:
            select = existing
        e = self.meta.editor(select=select)
        committed = e.start(False)        
        if committed is not None:
            if isinstance(committed, list):
                self._set_view_model_value(path, (existing,
                                                  old_committed+committed))
            else:
                self._set_view_model_value(path, committed)
            self.dirty = True
            self.renderer.emit('edited', path, committed)
            
        
    def on_key_press(self, widget, event, path):
        '''
        if the column has an editor, invoke it
        '''
        keyname = gtk.gdk.keyval_name(event.keyval)
        if keyname == 'Return':
            # start the editor for the cell if there is one
            if self.meta.editor is not None:
                self._start_editor(path)

#
#
#   
class ToggleColumn(SOViewColumn):
    
    def __init__(self, tree_view_editor, header, so_col=None):        
        super(ToggleColumn, self).__init__(tree_view_editor, header, 
                                           gtk.CellRendererToggle(),
                                           so_col)
        self.renderer.connect("toggled", self.on_toggled)
        self.set_resizable(False)
        self.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
            
            
    def on_toggled(self, renderer, path, data=None):
        self.dirty = True
        active = not renderer.get_active()
        self._set_view_model_value(path, active)    
        
        
    #def cell_data_func(self, col, cell, model, iter, data=None):
    def cell_data_func(self, column, renderer, model, iter, data=None):        
        row = model.get_value(iter, 0)
        value = row[self.name]
        if row.committed:
            renderer.set_property('sensitive', False)
            renderer.set_property('editable', False)
        else:
            renderer.set_property('sensitive', True)
            renderer.set_property('editable', True)
        if value is None:
            # this should really get the default value from the table
            #debug('inconsistent')
            renderer.set_property('inconsistent', False) 
        else:
            #debug('active: ' + str(value))
            renderer.set_property('active', value)
            
            
#
#
#            
class ComboColumn(SOViewColumn):
    
    def __init__(self, tree_view_editor, header, so_col):
        """
        we allow a renderer to be passed here so the user can attach
        custom models to the combo instead of doing it in 
        on_editing_started
        """
        super(ComboColumn, self).__init__(tree_view_editor, header, 
                                          gtk.CellRendererCombo(), so_col)
        # which column from the combo model to display
        self.renderer.set_property('has-entry', False)
        self.renderer.set_property("text-column", 0)
        self.renderer.connect('edited', self.on_edited)


    def on_edited(self, renderer, path, new_text, set_in_model=True):
        self._set_view_model_value(path, new_text)
        self.dirty =  True
        

    def cell_data_func(self, column, renderer, model, iter, data=None):
        # assumes the text column is 0 but the value we want 
        # to store in the model column 1
        row = model.get_value(iter, 0)        
        if row.committed:
            renderer.set_property('sensitive', False)
            renderer.set_property('editable', False)
        else:
            renderer.set_property('sensitive', True)
            renderer.set_property('editable', True)        
        if row is not None:
            v = row[self.name]
            #debug(v)
            renderer.set_property('text', v)
                                
        
    def __get_model(self):
        return self.renderer.get_property('model')            
    def __set_model(self, model):
        self.renderer.set_property('model', model)        
    model = property(__get_model, __set_model)    
                                               
                                           
    def on_editing_started(self, cell, editable, path, view):                
        #debug('on_editing_started')
        pass


def set_dict_value_from_widget(dic, dict_key, glade_xml, widget_name,
                               model_col=0, validator=lambda x: x):
    w = glade_xml.get_widget(widget_name)
    v = get_widget_value(glade_xml, widget_name, model_col)
    
    if v == "": 
        v = None
    elif isinstance(v, BaubleTable):
        v = v.id
        
    if v is not None:
        v = validator(v)
        dic[dict_key] = v
        

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
    

def set_widget_value(glade_xml, widget_name, value):
    print 'set_widget_value: ' + widget_name
    if value is None: return
    w = glade_xml.get_widget(widget_name)
    if w is None:
        raise ValueError("set_widget_value: no widget by the name "+\
                         widget_name)
    print type(value)
    if type(value) == ForeignKey:
        pass
    elif isinstance(w, gtk.Entry):
        w.set_text(value)



class TableMeta:
    """
    hold information about the table we will be editing with the table editor
    """
    def __init__(self):
        self.foreign_keys = []
        self.joins = []
    
    
# TODO: this is a new, simpler ModelRowDict sort of class, it doesn't try
# to be as smart as ModelRowDict but it's a bit more elegant, the ModelRowDict
# should be abolished or at least changed to usr SQLObjectProxy
# TODO: this should do some contraint checking before allowing the value to be
# set in the dict
class SQLObjectProxy(dict):    
    '''
    SQLObjectProxy does two things
    1. if so_object is an instance it caches values from the database and
    if those values are changed in the object then the values aren't changed
    in the database, only in our copy of the values
    2. if so_object is NOT an instance but simply an SQLObject derived class 
    then this proxy will only set the values in our local store but will
    make sure that the columns exist on item access and will return default
    values from the model if the values haven't been set
    3. keys will only exist in the dictionary if they have been accessed, 
    either by read or write, so **self will give you the dictionary of only
    those things  that have been read or changed
    
    ** WARNING: ** this is definetely not thread safe or good for concurrent
    access, this effectively caches values from the database so if while using
    this class something changes in the database this class will still use
    the cached value
    '''
    
    # TODO: needs to be better tested
    
    def __init__(self, so_object):
        # we have to set so_object this way since it is called in __contains__
        # which is used by self.__setattr__
        dict.__setattr__(self, 'so_object', so_object)
        dict.__setattr__(self, 'dirty', False)
        #self.dirty = False
                
        self.isinstance = False        
        if isinstance(so_object, SQLObject):
            self.isinstance = True
            self['id'] = so_object.id # always keep the id
        elif not issubclass(so_object, SQLObject):
            msg = 'row should be either an instance or class of SQLObject'
            raise ValueError('SQLObjectProxy.__init__: ' + msg)        
        
    __notifiers__ = {}
    
    def add_notifier(self, column, callback):
        '''
        add a callback function to be called whenever a column is changed
        callback should be of the form:
        def callback(field)
        '''
        try:
            self.__notifiers__[column].append(callback)
        except KeyError:
            self.__notifiers__[column] = [callback]


    def __contains__(self, item):
        """
        this causes the 'in' operator and has_key to behave differently,
        e.g. 'in' will tell you if it exists in either the dictionary
        or the table while has_key will only tell you if it exists in the 
        dictionary, this is a very important difference
        """
        if dict.__contains__(self, item):
            return True
        return hasattr(self.so_object, item)
    
    
    def __getitem__(self, item):
        '''
        get items from the dict
        if the item does not exist then we create the item in the dictionary
        and set its value from the default or to None
        '''
        
        # item is already in the dict
        if self.has_key(item): # use has_key to avoid __contains__
            return self.get(item)                
        
        # else if row is an instance then get it from the table
        v = None                        
        if self.isinstance:
            v = getattr(self.so_object, item)
            # resolve foreign keys
            # TODO: there might be a more reasonable wayto do this
            if item in self.so_object.sqlmeta.columns:
                column = self.so_object.sqlmeta.columns[item]            
                if v is not None and isinstance(column, SOForeignKey):
                    table_name = column.foreignKey                    
                    v = tables[table_name].get(v)
        else:
            # else not an instance so at least make sure that the item
            # is an attribute in the row, should probably validate the type
            # depending on the type of the attribute in row
            if not hasattr(self.so_object, item):
                msg = '%s has no attribute %s' % (self.so_object.__class__, 
                                                  item)
                raise KeyError('ModelRowDict.__getitem__: ' + msg)                        
                
        
        if v is None:
            # we haven't gotten anything for v yet, first check the 
            # default for the column
            if item in self.so_object.sqlmeta.columns:
                default = self.so_object.sqlmeta.columns[item].default
                if default is NoDefault:
                    default = None
                v = default
        
        # this effectively caches the row item from the instance, the False
        # is so that the row is set dirty only if it is changed from the 
        # outside
        self.__setitem__(item, v, False)
        return v            
           
                
    def __setitem__(self, key, value, dirty=True):
        '''
        set item in the dict, this does not change the database, only 
        the cached values
        '''
#        debug('setitem(%s, %s, %s)' % (key, value, dirty))
        dict.__setitem__(self, key, value)
        dict.__setattr__(self, 'dirty', dirty)
        if dirty:
            try:
                for callback in self.__notifiers__[key]:
                    callback(key)
            except KeyError:
                pass
        #self.dirty = dirty
    
    
    def __getattr__(self, name):
        '''
        override attribute read 
        '''
        if name in self:
            return self.__getitem__(name)
        return dict.__getattribute__(self, name)
    
    
    def __setattr__(self, name, value):
        '''
        override attribute write
        '''
        if name in self:            
            self.__setitem__(name, value)
        else:
            dict.__setattr__(self, name, value)    
    
    
    def _get_columns(self):
        return self.so_object.sqlmeta.columns
    columns = property(_get_columns)
    
    
    
class ModelRowDict(dict):
    """
    a dictionary representation of an SQLObject used for storing table
    rows in a gtk.TreeModel
    dictionary values are only stored in self if they are accessed, this
    saves on database queries lookups (i think, should test). this also
    means that when we retrieve the dictionary to commit the values then
    we only get those values that have been accessed
    """
    def __init__(self, row, columns, defaults={}):
        # if row is an instance of BaubleTable then get the values
        # from the instance else check that the items are valid table
        # attributes and don't let the editors set attributes that 
        # aren't valid
        # if row is not an instance then make sure
        self.dirty = False
        
        # committed is set to True if the row has been committed to the 
        # database, this doesn't necessarily imply that transaction.commit() 
        # has been called but it means that the table this row represents
        # has been created or it values have been changed to match this dict
        self.committed = False 
        
        self.isinstance = False
        if isinstance(row, BaubleTable):
            self.isinstance = True
            self['id'] = row.id # always keep the id
        elif not issubclass(row, BaubleTable):
            msg = 'row should be either an instance or class of BaubleTable'
            raise ValueError('ModelRowDict.__init__: ' + msg)
        
        
            
        #if row is not None and not isinstance(row, BaubleTable):
        #    raise ValueError('ModelRowDict.__init__: row is not an instance')
        
        self.row = row # either None or an instance of BaubleTable
        self.defaults = defaults or {}
        
        # getters are a way that a column can provide a custom function
        # on what it wants to return from a row, this is pretty much
        # a bad idea but we need it in some cases
        # FIXME: this is inefficient to do this everytime a row is added
        self.getters = {}
        for c in columns.values():
            if c.meta.getter is not None:
                self.getters[c.name] = c.meta.getter
            

    def __contains__(self, item):
        """
        this causes the 'in' operator and has_key to behave differently,
        e.g. 'in' will tell you if it exists in either the dictionary
        or the table while has_key will only tell you if it exists in the 
        dictionary, this is a very important difference
        """
        if self.has_key(item):
            return True
        elif self.row is not None:             
            return hasattr(self.row, item)
        else: 
            return False
        #if self.row is not None:
        #    return hasattr(self.row, item)
        #else: self.has_key(item)


    def __getitem__(self, item):
        """
        get items from the dict
        if the item does not exist then we create the item in the dictionary
        and set its value from the default or to None
        """
        # TODO: this method could use alot of love        
        if self.has_key(item): # use has_key to avoid __contains__
            return self.get(item)

        # else if row is an instance then get it from the table
        v = None        
        if self.isinstance:
#            if self.meta[item].getter is not None:
#                v = self.meta[item].getter(self.row)
            if item in self.getters:
                v = self.getters[item](self.row)
            else: # we want this to fail if item doesn't exist in row
                v = getattr(self.row, item)
                
            # resolve foreign keys
            # TODO: there might be a more reasonable wayto do this
            if item in self.row.sqlmeta.columns:
                column = self.row.sqlmeta.columns[item]            
                if v is not None and isinstance(column, SOForeignKey):
                    table_name = column.foreignKey                    
                    v = tables[table_name].get(v)
        else:
            # else not an instance so at least make sure that the item
            # is an attribute in the row, should probably validate the type
            # depending on the type of the attribute in row
            if not hasattr(self.row, item):
                msg = '%s has no attribute %s' % (self.row.__class__, item)
                raise KeyError('ModelRowDict.__getitem__: ' + msg)
        
#        debug(item)    
        if v is None:
            if item in self.defaults:
                v = self.defaults[item]
            elif item in self.row.sqlmeta.columns:
                default = self.row.sqlmeta.columns[item].default
                if default is NoDefault:
                    default = None
                v = default
        
        # this effectively caches the row item from the instance, the False
        # is so that the row is set dirty only if it is changed from the 
        # outside
        self.__setitem__(item, v, False)
        return v
       

    def __setitem__(self, key, value, dirty=True):
#        debug('[%s] = %s : %s' % (key, value, dirty))
        dict.__setitem__(self, key, value)
        self.dirty = dirty
       

#
# editor interface
#
class TableEditor(BaubleEditor):

    standalone = True
    
    def __init__(self, table, select=None, defaults={}, parent=None):
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
#        debug(values)
        for name, value in values.iteritems():
            if name in self.table.sqlmeta.columns:
                col = self.table.sqlmeta.columns[name]
                validators = col.createValidators()
                # TODO: there is another possible bug here where the value is 
                # not converted to the proper type in the values dict, e.g. a 
                # string is entered for sp_author when it should be a unicode
                # but maybe this is converted properly to unicode by
                # formencode before going in the database, this would need to
                # be checked better if we expect proper unicode support for
                # unicode columns
                # - should have a isUnicode constraint for UnicodeCols
                if value is None and notNull not in col.constraints:
                    continue
#                debug(name)
#                debug(col)
#                debug(col.constraints)
                for constraint in col.constraints:
                    # why are None's in the contraints?
#                    debug(constraint)
                    if constraint is not None: 
                        # TODO: when should we accept unicode values as strings
                        # sqlite returns unicode values instead of strings
                        # from an EnumCol
                        if isinstance(col, (SOUnicodeCol, SOEnumCol)) and \
                            constraint == constraints.isString and \
                            isinstance(value, unicode):
                            # do isString on unicode values if we're working
                            # with a unicode col
                            pass
                        else:
                            constraint(self.table.__name__, col, value)
            else:        
                # assume it's a join and don't do anything
                pass
        
    
    def _commit(self, values):       
        table_instance = None
        self._check_constraints(values)    
        if 'id' in values:# updating row
            table_instance = self.table.get(values["id"])                    
            del values["id"]
            table_instance.set(**values)
        else: # creating new row
            table_instance = self.table(**values)
        return table_instance
    
    
    def commit_changes(self):
        raise NotImplementedError
    
#
#
#
class TableEditorDialog(TableEditor):
    
    def __init__(self, table, title="Table Editor",
                 parent=None, select=None, 
                 defaults={}, dialog=None):
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
        save the state of the editor whether it be the gui or whatever, this 
        should not make database commits unless to BaubleMeta,
        not required to implement
        '''        
        pass

#
# TreeViewEditorDialog
# a spreadsheet style editor
#
# TODO:
# (2) ability to attach some sort of validator on the column
# which will always ensure that whatever is entered is of the correct format
# and would possible even complete some things for you like the "." in the
# middle of an accessions
# (3) should somehow check which columns have default values and which
# don't and treat them as required columns, so you can't change the visibility
# and can go to the next row having with out editing them
# (4) should have a label at the top which give information about what's
# being edited and what could be wrong ala eclipse
# TODO: separate TreeViewEditor and TreeViewEditorDialog so we could use
# the TreeViewEditor outside of a dialog in the future
class TreeViewEditorDialog(TableEditorDialog):
    """the model for the view in this class only has a single column which
    is a Table class which is really just a dict. each value in the dict
    relates to a column in the tree but
    this allows us to refer to the columns by name rather than by column
    number    
    """    
    visible_columns_pref = None
    column_width_pref = None
    default_visible_list = []

    class ColumnDict(dict):
        """
        hold a dictionary of columns by their names
        """
        def __init__(self):
            self.joins = [] # populate in start_tree_view
            self.foreign_keys = [] # 
            
            
        def __set_titles(self, titles):
            for name, title in titles.iteritems():
                self[name].set_property('title', title)
        
        titles = property(fset=__set_titles)


    #
    # view property
    # 
    # TODO: is making the view read only really a necessary
    def _get_view(self):
        return self.__view
    view = property(_get_view)

    #
    # model property
    #
    def _get_model(self):
        return self.view.get_model()
    def _set_model(self, model):
        self.view.set_model(model)
    model = property(_get_model, _set_model)
        

    def __init__(self, table, title="Table Editor", parent=None, select=None, 
                 defaults={}):
        super(TreeViewEditorDialog, self).__init__(table, title, parent, 
               select, defaults)
        self.__view = None        
        self.__dirty = False # accessed via self.dirty property
        self.table_meta = TableMeta()        
        self.init_gui()
        
        # this is used to indicate that the last row is a valid row
        # or it is one that was added automatically but never used
        self.dummy_row = False
        #self.connect('response', self.on_response)
                
        
    def pre_start_hook(self):
        '''
        this is a pretty rough hack i put it to get thinkgs working if you
        are using a column that doesn't have a representation as a column
        in a SQLObject, see vernacularname.py e.g.
        '''
        pass
    
    
    def start(self, commit_transaction=True):
        # this ensures that the visibility is set properly in the meta before
        # before everything is created
        if self.visible_columns_pref is not None:
            if not self.visible_columns_pref in prefs:
                prefs[self.visible_columns_pref] = self.default_visible_list
            self.set_visible_columns_from_prefs(self.visible_columns_pref)
                    
        self.start_gui()
        self.pre_start_hook()
        
        # TODO: check that all required columns have been filled in and make
        # sure that a dialog pops up and asks the user if they are sure
        # that they want to close the dialog even though the fields aren't 
        # complete
        
        committed = self._run()
        if commit_transaction:
            sqlhub.processConnection.commit()
        return committed

        
    def init_gui(self):
        self.init_tree_view()
        
    
    def start_gui(self):
        self.start_tree_view()
        self.create_toolbar()                
        self.dialog.vbox.pack_start(self.toolbar, fill=False, expand=False)
        
        self.view_window = gtk.ScrolledWindow()        
        self.view_window.set_policy(gtk.POLICY_NEVER, gtk.POLICY_NEVER)
        self.view_window.add(self.view)
        self.dialog.vbox.pack_start(self.view_window)
        self.dialog.set_default_size(-1, 300) # an arbitrary size
                
        # set ok button insensitive
        ok_button = self.dialog.action_area.get_children()[1]
        ok_button.set_sensitive(False)        
        
        self.dialog.show_all()                
           
                
    def init_tree_view(self):
        """
        create the main tree view
        """
    # the gboolean is here to control whether to turn on the background 
    # color
        self.__view = gtk.TreeView(gtk.ListStore(object, 'gboolean'))
        self.columns = self.create_view_columns()
        self.view.set_headers_clickable(False)
  
    
    def start_tree_view(self):
        
        # put a star at the end of the column names that have external
        # editors
        # TODO: maybe we should be iterating through the columns again
        # FIXME: this doesn't work b/c by now the columns have already been
        # added to the view so if we removed the columns and appended them
        # back it would screw up the column order and world of other things
        # if somehow we could delay creating the TreeViewColumns until
        # now it would be easier but that would require alot of big changes
        for name, column in self.columns.iteritems():
            if column.meta.editor is not None:
                column.set_title(column.get_title() + '*')
                
        
        # remove join columns if they don't have an editor associated
        column_names = self.columns.keys()
        for join in self.table.sqlmeta.joins:
            # we create columns for the joins in create_view_columns
            # but we remove the column hereif there isn't an external editor, 
            # this
            # allows classes that extend this editor class to setup the editor
            # in their constructor like they would do with normal column
            name = join.joinMethodName
            if name in column_names:
                if self.columns[name].meta.editor is None:
                    self.columns.pop(name)
                else:
                    self.columns.joins.append(name)
            
        # create the model from the tree view and add rows if a
        # selectresult is passed
#        debug('select: %s' % str(self.select))
        if self.select is not None:
            for row in self.select:
                self.add_new_row(row)
        self.add_new_row()
            
        # enter the columns from the visible list, the column visibility
        # should already have been set before creation from the prefs,
        # here we just have to add them in order
        visible_list = ()
        if self.visible_columns_pref != None and \
           self.visible_columns_pref in prefs:
            visible_list = list(prefs[self.visible_columns_pref][:])
            visible_list.reverse()
            for name in visible_list:
                if name in self.columns:
                    self.view.insert_column(self.columns[name], 0)
        
        # append the rest of the column to the end and set all the widths
        width_dict = self.get_column_widths_from_prefs()            
        for name, column in self.columns.iteritems():
            if name not in visible_list:
                self.view.append_column(self.columns[name])
            if name in width_dict and width_dict[name] > 0:
                column.set_fixed_width(width_dict[name])                
            
        
        # now that all the columns are here, let us know if anything 
        # changes
#        self.view.connect("move-cursor", self.on_view_move_cursor)
        self.view.connect("cursor-changed", self.on_cursor_changed)
        self.view.connect("button-release-event", self.on_view_button_release)
        
    
    def create_toolbar(self):
        """
        TODO: should make those columns that can't be null and don't
        have a default value, i.e. required columns show in the menu
        but they should be greyed out so you can't turn them off
        """
    # FIXME: why doesn the label not show up here????
        self.toolbar = gtk.Toolbar()
        col_button = gtk.MenuToolButton(None, label="Columns")
        menu = gtk.Menu()
        # TODO: would rather sort case insensitive
        for name, col in sorted(self.columns.iteritems()):
            #if meta.join and not meta.type == SOSingleJoin and not meta.editor:
            #    continue            
            title = col.get_property('title').replace('_', '__') # no mnemonics
            item = gtk.CheckMenuItem(title)            
            if col.meta.required:
                item.set_sensitive(False)                
            item.set_active(col.get_visible())
            item.connect("toggled", self.on_column_menu_toggle, name)
            menu.append(item)
            item.show()
        col_button.set_menu(menu)
        self.toolbar.insert(col_button, -1)  
        
            
    # TODO: we don't use this anymore since we require that the foreign
    # key values have to be in the in the completion list
    # - the only place that this is implemented is in species.pu but it 
    # doesn't matter since foreign_does_not_exists is never called
    # - it wouldn't
    # be a bad idea if we wanted to make it easier to add new items, right now
    # e.g. a genus that doesn't exists could be added before the species is 
    # committed
    
    def foreign_does_not_exist(self, name, value):
        """
        this is intended to be overridden in a subclass to do something
        interesting if the foreign key doesn't exist
        """
        msg = "%s does not exist in %s" % (value, name)
        utils.message_dialog(msg, gtk.MESSAGE_ERROR)
        
        
    def set_ok_sensitive(self, sensitive):
        ok_button = self.dialog.action_area.get_children()[1]
        ok_button.set_sensitive(sensitive)
        
    
    #
    # dirty property
    #
    def _get_dirty(self):
        return self.__dirty
   
    def _set_dirty(self, dirty):
        #super(TreeViewEditorDialog, self)._set_dirty(dirty)
        self.__dirty = dirty
        self.set_ok_sensitive(dirty)
        
    dirty = property(_get_dirty, _set_dirty)
                    
                    
    # attache to mouse clicks
    def on_view_button_release(self, view, event, data=None):
        """
        popup a context menu on the selected row
        """
        if event.button != 3: 
            return # if not right click then leave
        sel = view.get_selection()
        model, i = sel.get_selected()
        if model == None:
            return # nothing to pop up a context menu on
        value = model.get_value(i, 0) 
        
        # can't remove the last row
        if len(model) == 1:
            return
            
        menu = gtk.Menu()
        remove_item = gtk.MenuItem("Remove") # remove the row from the editor
        remove_item.connect("activate", lambda x: model.remove(i))
        menu.add(remove_item)        
        menu.show_all()
        menu.popup(None, None, None, event.button, event.time)
            
        
    def on_column_menu_toggle(self, item, colname=None):
        visible = item.get_active()
        self.columns[colname].set_visible(visible)
        
        # could do this with a property notify signal
#        self.view.resize_children()
         
    
    def post_commit_hook(self, table_instance):
        '''
        called after some values have been committed with the table instance
        those values were committed to
        '''
        return True
    

    def _model_row_to_values(self, row):
        '''
        _model_row_to_values
        row: iter from self.model
        return None if you don't want to commit anything
        '''
        if not row[0].dirty or row[0].committed:
            # then this row hasn't changed or has already been committed
            return None
        values = row[0].copy()
        for name, value in values.iteritems():
            if isinstance(value, tuple):
                values[name] = value[1]
        return values
        
    
    def _commit_model_rows(self):
        committed_rows = []
        table_instance = None
        model = self.view.get_model()        
        for item in model:
            row = self._model_row_to_values(item)
            if row is None:
                continue
                        
            for fk in self.columns.foreign_keys: # get foreign keys from row
                if fk in row and row[fk] is not None:
                    row[fk] = row[fk].id

            join_values = {}
            for join in self.columns.joins: # get joins from row
                if join in row:
                    if row[join]:
                        join_values[join] = row.pop(join)
                    else:
                        row.pop(join) # so we don't try to commit joins
    
            try: # commit
                table_instance = self._commit(row)
                # have to set the join this way since 
                # table_instance.joinColumnName doesn't seem to work here, 
                # maybe b/c the table_instance hasn't been committed
                for join in table_instance.sqlmeta.joins:
                    if join.joinMethodName in join_values:
                        if isinstance(join, SOSingleJoin):
                            join_table_instance = join_values.pop(join.joinMethodName)
                            join_table_instance.set(**{join.joinColumn[:-3]:
                                                       table_instance.id})
                        else: # must be a multple join???
                            for join_table_instance in join_values.pop(join.joinMethodName):
                                join_table_instance.set(**{join.joinColumn[:-3]:
                                                           table_instance.id})
            except BadValue, e:
                # TODO: should we try and highlight the offending row or column
                # we could also just use the CommitException exception wrapper
                # and do an if isinstance(CommitException.exc, BadValue)
                # so we don't do a rollback on BadValues
                raise e
            except Exception, exc:
                debug(traceback.format_exc())
                raise CommitException(exc, item)
                
            if len(join_values) > 0:
                raise ValueError("join_values isn't empty")
                
            self.post_commit_hook(table_instance)
            committed_rows.append(table_instance)            
            item[0].committed = True
            #model.remove(item.iter) # on success remove from model
        return committed_rows
            
            
    def commit_changes(self):
        return self._commit_model_rows()
            
    
    def on_cursor_changed(self, view, data=None):
        # TODO: this should be reworked to have some sort of information
        # panel for the editor, similar to eclipse
        path, column = view.get_cursor()
        if column is None:
            return
        editor_status_context_id = 5698
        if column.meta.editor is not None:
            bauble.app.gui.statusbar.push(editor_status_context_id,
                                          'Press enter to edit the %s' \
                                          % column.get_property('title'))
        else:
            bauble.app.gui.statusbar.pop(editor_status_context_id)


    def create_view_columns(self):                
        columns = TreeViewEditorDialog.ColumnDict()        
        # create tree columns for table columns
        for name, col in self.table.sqlmeta.columns.iteritems():
            #debug("create_view_column: %s -- %s", name, col)
            if name.startswith("_"): # private/not editable
                continue
            title = name.replace('_', '__') # not a mnemonic
            if isinstance(col, SOEnumCol):
                column = ComboColumn(self, title, so_col=col)
                model = gtk.ListStore(str)
                for v in column.meta.so_col.enumValues:
                    model.append([v])
                column.model = model
            elif isinstance(col, SOBoolCol):
                column = ToggleColumn(self, title, so_col=col)
            else:
                column = TextColumn(self, title, so_col=col)
            columns[name] = column
            
            if isinstance(col, SOForeignKey):
                columns.foreign_keys.append(name)
            
            # set handlers for the view
            # TODO should i do issubclass here instead, just in case
            # we derive one of these columns it will still work the same
            if isinstance(column, TextColumn):
                column.renderer.connect('edited', self.on_column_edited,
                                        column)
#            elif isinstance(column, ToggleColumn):
#                column.renderer.connect('toggled', self.on_column_toggled,
#                                        column)
        
        for join in self.table.sqlmeta.joins:
            # we create columns for the joins here but we remove the column
            # once the view is created if there isn't an external editor, this
            # allows classes that extend this editor class to setup the editor
            # in their constructor like they would do with normal column
            name = join.joinMethodName
            if not isinstance(join, SOJoin):
                continue
            column = TextColumn(self, title, so_col=join)
            column.renderer.connect('edited', self.on_column_edited, column)
            columns[name] = column
            
        return columns            
    
    
    def on_column_edited(self, renderer, path, new_text, column):
        # edited the last row so add a new one,
        # i think this may a bit of a bastardization of path but works for now
        model = self.view.get_model()
        if new_text != "" and int(path) == len(model)-1:
            self.add_new_row()
            self.dummy_row = True
    
    
    number_of_adds = 0
    def add_new_row(self, row=None):
        model = self.view.get_model()
        if model is None: 
            raise bauble.BaubleError("the view doesn't have a model")
        if row is None:
            row = self.table        
        
        self.number_of_adds += 1
        if self.number_of_adds > 8: # this is a hack to avoid the column creep
            self.view_window.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
    # the False is for the background color
        model.append([ModelRowDict(row, self.columns, self.defaults), False])


    def set_visible_columns_from_prefs(self, prefs_key):
        visible_columns = prefs[prefs_key]
        if visible_columns is None: 
            return
        # reset all visibility from prefs
        for name, col in self.columns.iteritems():            
            if name in visible_columns:
                col.set_visible(True)
            elif col.meta.required:
                col.set_visible(True)
            else:
                col.set_visible(False)                

    
    def get_column_widths_from_prefs(self):
        if self.column_width_pref is None or self.column_width_pref not in prefs:
            return {}        
        return prefs[self.column_width_pref]


    def save_state(self):
        self._store_column_widths()
        self._store_visible_columns()
        
        
    def _store_column_widths(self):
        """
        store the column widths as a dict in the preferences, self
        if self.column_width_pref is None then just don't store the prefs
        """
        if self.column_width_pref is None:
            return 
                    
        width_dict = {}
        for name, col in self.columns.iteritems():
            width_dict[name] = col.get_width()
        
        pref_dict = prefs[self.column_width_pref]
        if pref_dict is None:
            prefs[self.column_width_pref] = width_dict
        else: 
            pref_dict.update(width_dict)            
            prefs[self.column_width_pref] = pref_dict

        
    def _store_visible_columns(self):
        """
        get the currently visible columns and store them to the preferences
        """
        if self.visible_columns_pref == None:
            return
        visible = []
        for c in self.view.get_columns():
            if c.get_visible():
                visible.append(c.name)
        prefs[self.visible_columns_pref] = visible

        
