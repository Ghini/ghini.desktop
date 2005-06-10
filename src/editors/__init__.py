
#
# editors module
#

import sys, os, os.path
import copy

import pygtk
pygtk.require("2.0")
import gtk

from sqlobject.sqlbuilder import *
from sqlobject import *

from tables import tables
from utils import *
#from bbl_utils import *
from prefs import Preferences

from utils.debug import debug
debug.enable = False


def createColumnMetaFromTable(sqlobj):
    """
    return a MetaViewColumn class built from an sqlobj
    """
    # TODO: visible should probably be a sequence instead of a flag
    # so it implies some order, it might be difficult though to keep the 
    # column order and the meta data synchronized
    meta = MetaViewColumn()
    for c in sqlobj._columns:
        if c.name[0] == "_": continue
        foreign = False
        visible = False 
        index = -1
        if type(c) == ForeignKey:
            foreign = True
        meta[c.name] = (c.name, visible, foreign)
    return meta


def validate_int(value):
    v = int(value)
    return v


def validate_accession(value):
    # should check the value fits the format of an accession number
    return value


class MetaViewColumn(dict):
    """
    contains a dictionary of Meta classes which store information
    about the different columns in the view
    """
    
    class Meta:
        def __init__(self, header = None, visible = False, foreign = False, 
                     values = None):
            self.header = header
            self.visible = visible
            self.foreign = foreign
            self.index = -1
            
            # TODO: should be able to set a default value for the 
            # renderer of the column which you could pass in when the 
            # editor is created
            # self.default = None
            
            # a dummy validate function
            self.validate = lambda x: x
            
#        def __cmp__(self, other):
#            if self.index < other.index: return -1
#            elif self.index > other.index: return 1
#            return 0
            

    # set column meta, value[0] = name, value[1] = visible, value[2] = foreign
    def __setitem__(self, item, value):
        dict.__setitem__(self, item, 
                         MetaViewColumn.Meta(value[0], value[1], value[2]))

        
class ModelDict(dict):
    """
    each row of the model will contain a ModelDict though each row may
    not have the same keys in  the dict
    """        
    def __init__(self, table_row=None, default=None):
        """
        if table is not None then build a dict from the table
        """
        if table_row is not None:
            self["id"] = table_row.id
            self.table_row = table_row            
            for c in table_row.sqlmeta._columns:
                eval_str = None                    
                if c.foreignKey:
                    id = eval("self.table_row.%s" % c.name)
                    eval_str = "tables.%s.get(id)" % c.foreignKey
                    name = c.origName                        
                else:                        
                    eval_str = ("self.table_row.%s") % c.name
                    name = c.name
                v = eval(eval_str)
                self[name] = v
        elif default is not None:
            for key, value in default.iteritems():
                self[key] = value

        
    def __getitem__(self, item):
        """
        allows us to use the dict syntax to dynamically create keys
        for the model though you have to be careful b/c 'if d[key] is None'
        can create the key
        """
        if not self.has_key(item):
            self[item] = None
        return self.get(item)


#
# TableEditor
#
# TODO:
# (1) make this a proper abstract class
# (2) ability to attach some sort of validator on the column
# which will always ensure that whatever is entered is of the correct format
# and would possible even complete some things for you like the "." in the
# middle of an accessions
# (3) should somehow check which columns have default values and which
# don't and treat them as required columns, so you can't change the visibility
# and can go to the next row having with out editing them
# (4) should have a label at the top which give information about what's
# being edited and what could be wrong ala eclipse
class TableEditorDialog(gtk.Dialog):
    """the model for the view in this class only has a single column which
    is a Table class which is really just a dict. each value in the dict
    relates to a column in the tree but
    this allows us to refer to the columns by name rather than by column
    number    
    """    
    
    def __init__(self, title="Table Editor", parent=None, select=None, defaults={}):
        gtk.Dialog.__init__(self, title, parent, 
                            gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, 
                            (gtk.STOCK_OK, gtk.RESPONSE_OK, 
                             gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
        self.view = None        
        self.columns = {} # self.columns[name] = gtkcolumn
        self.dirty = False
        self.defaults = copy.copy(defaults)
        self.create_gui(select)
                

    def get_table_values(self):
        """
        used by commit_changes to get the values from a table so they
        can be commited to the database
        """
        model = self.view.get_model()
        values = []
        from copy import copy
        for row in model:
            row = copy(row[0]) # copy it so we dont change the data in the model
            for c in row:
                if type(row[c]) == list: # convert foreign keys to ids
                    #print "get_table_values(): " + str(row[c])
                    row[c] = int(row[c][0])
            values.append(row)
        del values[len(model)-1] # the last one should always be empty
        return values                    
    

    def foreign_does_not_exist(self, name, value):
        """
        this is intended to be overridden in a subclass to do something
        interesting if the foreign key doesn't exist
        """
        d = gtk.MessageDialog(None, 
                              gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, 
                              gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, 
                              "%s does not exit in %s" % (value, name))
        d.run()
        d.destroy()
        
        
    def on_edited(self, renderer, path, new_text, colname):
        """
        """
        #print "on_edited: " + new_text
        new_text = new_text.strip()
        if new_text == None or new_text == "":
            return        
        model = self.view.get_model()
        i = model.get_iter(path)
        row = model.get_value(i, 0)
        if not self.column_data[colname].foreign:
            v = self.column_data[colname].validate(new_text)
            row[colname] = v
        else:
            # need to somehow get the id from the text value, is it possible?
            # if it is a foreign key then the row in the model should be
            # set when a match is selected in the EntryCompletion,
            # see on_completion_match_selected
            # *** i don't really like this, i would prefer to set the model
            # in one place
            pass
        self.dirty = True # something has changed
        self.view.check_resize()

        # edited the last row so add a new one,
        # i think this may a bit of a bastardization of path but works for now
        if new_text != "" and int(path) == len(model)-1:
            model = self.view.get_model()
            self.add_new_row()
            #model.append([ModelDict()])            

    def validate(self, colname, value):
        #type
        return value

    
    def on_completion_match_selected(self, completion, model, iter, 
                                     path, colname):
        """
        all foreign keys should use entry completion so you can't type in
        values that don't already exists in the database, therefore, allthough
        i don't like it the view.model.row is set here for foreign key columns
        and in self.on_edited for other column types                
        """        
        name = model.get_value(iter, 0)
        id = model.get_value(iter, 1)
        model = self.view.get_model()
        i = model.get_iter(path)
        row = model.get_value(i, 0)
        row[colname] = [id, name]
    

    def on_cell_key_press(self, widget, event, path, colname):
        """
        handled TreeView navigation
        """
        keyname = gtk.gdk.keyval_name(event.keyval)
        path, col = self.view.get_cursor()        
        if keyname == "Up" and path[0] != 0:            
            self.move_cursor_up(path, col)
        elif keyname == "Down" and path[0] != len(self.view.get_model()):
            # TODO: check if the entry completion is open and if so then
            # set the focus to the completions, eles move the cursor down
            print "%s - %s" % (str(path), str(col))   
            # current_entry is set in editing_started and removed in editing_done
            if self.current_entry is not None: 
                comp = self.current_entry.get_completion()                
            else: self.move_cursor_down(path, col)
        elif keyname == "Left":
            self.move_cursor_left(path, col)
            pass
        elif keyname == "Right":
            self.move_cursor_right(path, col)
            pass
        elif keyname == "Tab":            
            columns = self.view.get_columns()
            ncols = len(columns)
            # if last column and not last row,
            # TODO: this doesn't
            # work anymore now that we create all rows instead of just
            # the visible ones, we need to get the index of the highest
            # visible row
            if columns[ncols-1] == col and len(self.view.get_model()) != ncols:
                newpath = path[0]+1, 
                self.view.set_cursor_on_cell(newpath, columns[0], None, True)
            else: self.move_cursor_right(path, col) # else moveright
                

        
    def move_cursor_right(self, path, fromcol):
        """
        """
        newcol = fromcol
        columns = self.view.get_columns()
        fromcol_index = 100 # 100 is an arbitrary max
        for i in xrange(0, len(columns)): # find the columns index            
            if columns[i] == fromcol: fromcol_index = i
            if columns[i].get_visible() and i > fromcol_index:
                newcol = columns[i]
                break        
        self.view.set_cursor_on_cell(path, newcol, None, True)

        
    def move_cursor_left(self, path, fromcol):
        """
        """
        newcol = fromcol
        columns = self.view.get_columns()
        fromcol_index = -1
        for i in xrange(len(columns)-1, 0, -1): # iterate in reverse
            if columns[i] == fromcol: fromcol_index = i
            if columns[i].get_visible() and i < fromcol_index:
                newcol = columns[i]
                break
        self.view.set_cursor_on_cell(path, newcol, None, True)

    
    def move_cursor_up(self, path, col):
        newpath = path[0]-1, 
        self.view.set_cursor_on_cell(newpath, col, None, True)
        #renderer.stop_emit_by_name("key-press-event")

    
    def move_cursor_down(self, path, col):
        newpath = path[0]+1, 
        self.view.set_cursor_on_cell(newpath, col, None, True)
        #renderer.stop_emit_by_name("key-press-event")

    
    def on_editing_started(self, cell, editable, path, colname):
        #print "on_editing_started"

        # TODO: should disconnect this everytime "edited" is fired, or
        # should i???
        if isinstance(editable, gtk.Entry):            
            editable.connect("key-press-event", self.on_cell_key_press, 
                             path, colname)

            # set up a validator on the col depending on the sqlobj.column type
            editable.connect("insert-text", self.on_insert_text, 
                             path, colname)
            editable.connect("editing-done", self.on_editing_done)
            self.current_entry = editable
            # if not a foreign key then validate, foreign keys can only
            # be entered from existing values and so don't need to
            # be validated
            #if not self.column_data[colname].foreign:
            #    if self.column_data[colname].                

    def on_editing_done(self, editable, data=None):
        """
        not editing anymore, set current entry to None
        """
        print "TableEditorDialog.on_editing_done()"
        #self current entry to false
        self.current_entry = None
        
    def on_validate_date(self, entry, text, length, position):
        print "validate date"
        full_text = entry.get_text()

        
    def on_validate_int(self, entry, text, length, position):
        print "validate int"
        try:
            i = int(text)
        except ValueError:
            entry.stop_emission("insert-text")


    def on_insert_text(self, entry, text, length, position, path, colname):
        """
        handle text filtering/validation and completions
        """
        # TODO: the problem is only validates on letter at a time
        # we need to have a format string which is inserted
        # in the entry before typeing starts and fills in the gap
        # as the user types
        try:
            self.column_data[colname].validate(text)
        except ValueError:
            entry.stop_emission("insert_text")
        
        full_text = entry.get_text()
        if len(full_text) > 2: # add completions
            entry_completion = entry.get_completion()
            model, maxlen = self.get_completions(full_text, colname)
            if entry_completion is None and model is not None:
                entry_completion = gtk.EntryCompletion()
                entry_completion.set_minimum_key_length(2)
                entry_completion.set_text_column(0)
                entry_completion.connect("match-selected", 
                                         self.on_completion_match_selected, 
                                         path, colname)
                #entry_completion.set_inline_completion(True)
                #entry_completion.set_match_func(self.match_func, None)
                entry.set_completion(entry_completion)

            if entry_completion is None and self.column_data[colname].foreign:
                raise Exception("No completion defined for column %s" % colname)
            
            if entry_completion is not None:
                entry_completion.set_model(model)

    # Assumes that the func_data is set to the number of the text column in the
    # model.
    def match_func(self, completion, key, iter, column, data=None):
        model = completion.get_model()
        text = model.get_value(iter, column)
        if text.startswith(key):
          return True
        return False
    
    def on_column_clicked(self, column, data=None):
        """
        TODO: could view on column
        """
        print "on_column_clicked"

    
    def on_cursor_changed(self, view, data=None):
        path, column = self.view.get_cursor()
        print "on_cursor_changed: %s, %s" %(path, column)
        return
        print "BLOCK"
        view.handler_block(self.cursor_changed_id)
        #if stop
        view.set_cursor(path, column, True)
        print "UN block"
        view.handler_unblock(self.cursor_changed_id)
        #self.grab_focus(entry)


    def on_column_menu_toggle(self, item, colname=None):
        visible = item.get_active()
        self.columns[colname].set_visible(visible)
        self.column_data[colname].visible = visible
        #self.view.check_resize()
        self.view.resize_children()


    def on_column_changed(self, treeview, data=None):
        """
        keep up with the order of the columns to make key navigation
        easier
        NOTE: i'm not sure what i'm talking about here, i think this may be
        an old function i don't need anymore
        """
        pass
        

    def on_response(self, widget, response):
        self.store_visible_columns() # save preferences before we do anything
        if response == gtk.RESPONSE_OK:
            if self.commit_changes():
                self.destroy() # successfully commited
        elif response == gtk.RESPONSE_CANCEL and self.dirty:            
            msg = "Are you sure? You will lose your changes."
            d = gtk.MessageDialog(self, gtk.DIALOG_MODAL |
                                  gtk.DIALOG_DESTROY_WITH_PARENT, 
                                  gtk.MESSAGE_ERROR, gtk.BUTTONS_YES_NO, msg)
            r = d.run()
            d.destroy()
            if r == gtk.RESPONSE_YES:
                self.destroy()
        else: # cancel, not dirty
            self.destroy()
        return False
                                

    def commit_changes(self):
        """
        commit any change made in the table editor
        """        
        values = self.get_table_values()
        trans = sqlhub.threadConnection.transaction()
        for v in values:
            try:
                if v.has_key("id"):
                    print "TableEditorDialog.commit_changes(): updating"
                    p = self.sqlobj.get(v["id"])
                    del v["id"]
                    p.set(**v)
                else:
                    print "TableEditorDialog.commit_changes(): adding"
                    self.sqlobj(**v)
            except Exception, e:
                msg = "Could not commit changes.\n" + str(e)
                trans.rollback()
                d = gtk.MessageDialog(None, 
                                      gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                                      gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
                d.run()
                d.destroy()
                return False
        trans.commit()
        return True


    def get_model_value(self, col, cell, model, iter, column_name):
        """
        used by the tree view columns to get the value to be display
        from the model
        """
        v = model.get_value(iter, 0)
        row = v[column_name]
        if row is None: # no value in model
            cell.set_property('text', None)
        elif type(row) == list: # if a list then row[1] is the id
            cell.set_property('text', row[1])
        else: # just plain text in model column
            cell.set_property('text', str(row))                    


    def create_toolbar(self):
        """
        TODO: should make those columns that can't be null and don't
        have a default value, i.e. required columns show in the menu
        but they should be greyed out so you can't turn them off
        """
        self.toolbar = gtk.Toolbar()
        col_button = gtk.MenuToolButton(None, label="Columns")
        menu = gtk.Menu()
        # TODO: would rather sort case insensitive
        for key in sorted(self.column_data.keys()):        
            item = gtk.CheckMenuItem(self.column_data[key].header.
                                     replace('_', '__')) # no mnemonics
            item.set_active(self.column_data[key].visible)
            item.connect("toggled", self.on_column_menu_toggle, key)
            menu.append(item)
        menu.show_all()
        col_button.set_menu(menu)
        self.toolbar.insert(col_button, 0)            
            

    def create_gui(self, select=None):
        vbox = gtk.VBox(False)
        
        self.create_toolbar()        
        vbox.pack_start(self.toolbar, fill=False, expand=False)
        
        self.create_tree_view(select)
        vbox.pack_start(self.view)
        
        self.vbox.pack_start(vbox)
        
        self.connect("response", self.on_response)
        
        self.show_all()


    def create_view_column(self, name, column_meta):
        """
        return a gtk.TreeViewColumn from column_data
        """
        #
        # sqlobj.sqlmeta._columnDict: and sqlobj._columns store
        # the names differently so i can use this anymore to check
        # that the column exists
        #
        #if name not in self.sqlobj.sqlmeta._columnDict:
        #    raise Exception("** Error -- %s not a column in %s table" %
        #                    (name, self.sqlobj.sqlmeta.table))
        r = None
        # create a CellRendererCombo if the tables has predefined values
        # for the column
        if hasattr(self.sqlobj, "values") and self.sqlobj.values.has_key(name):
            r = gtk.CellRendererCombo()
            #r.set_property("has-entry", False)
            r.set_property("text-column", 0)
            model = gtk.ListStore(str, str)            
            for v in self.sqlobj.values[name]:
                model.append(v)
            r.set_property("model", model)
        else:
            r = gtk.CellRendererText()            
            
        # setup the renderer
        r.set_property("editable", True)
        r.set_property("editable-set", True)
        r.connect("edited", self.on_edited, name)
        r.connect("editing_started", self.on_editing_started, name)
        
        # setup the column
        # replace so the '_' so its not interpreted as a mnemonic
        column = gtk.TreeViewColumn(column_meta.header.replace("_", "__"), r)
        column.set_cell_data_func(r, self.get_model_value, name)
        column.set_min_width(120)
        column.set_clickable(True)
        column.connect("clicked", self.on_column_clicked)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        column.set_resizable(True)
        column.set_reorderable(True)
        column.set_visible(column_meta.visible)
        column.name = name # .name is my own data, not part of gtk
        return column
        
    def add_new_row(self, row=None):
        model = self.view.get_model()
        if model is None: raise Exception("no model in the row")
        model.append([ModelDict(row, self.defaults)])
            
            
    def create_tree_view(self, select=None):
        """
        create the main tree view
        """
        # create the columns from the meta data
        for name, meta in self.column_data.iteritems():            
            self.columns[name] = self.create_view_column(name, meta)
        
        #model = gtk.ListStore(object) # object will be type ModelDict
        self.view = gtk.TreeView(gtk.ListStore(object))
        self.view.connect("columns-changed", self.on_column_changed)
        self.view.set_headers_clickable(False)

        # create the model from the tree view and add rows if a
        # selectresult is passed
        
        if select is not None:
            for row in select:
                self.add_new_row(row)
                #model.append([ModelDict(row)])                
        else:
            self.add_new_row()
            #model.append([ModelDict()])
            
        

        # append the visible columns first
        # TODO: why isn't sorted keys in order with all the -1 index
        # at the beginning
        from operator import attrgetter
        sorted_keys = sorted(self.column_data.keys(), key=attrgetter("index"))
        for name in sorted_keys:
            index = self.column_data[name].index
            #if index != -1:
            col = self.columns[name]
            self.view.insert_column(col, index)


    def get_completions(self, text, colname):
        """
        return a list of completions relative to the current input and
        the length of the longest completion
        does nothing by default but is intended to be extended by other classes
        """
        #raise NotImplementedError
        return None, 0


    def set_visible_columns_from_prefs(self, prefs_key):
        """
        load the visible column from the preferences key and reset the visible
        attribute on each column
        this doesn't change the visibility in the tree view so the
        method name may be misleading
        """        
        visible_columns = Preferences[prefs_key]
        if visible_columns is None: return

        # set the index
        i=1
        for name in visible_columns:            
            self.column_data[name].index = i
            #debug("%s: %d" % (name, i))
            i += 1
            
        # reset all visibility
        for name, meta in self.column_data.iteritems():
            if name in visible_columns:
                meta.visible = True                    
            else: meta.visible = False

    def store_visible_columns(self):
        """
        get the currently visible columns and store them to the preferences
        """
        visible = []
        for c in self.view.get_columns():
            if c.get_visible():
                visible.append(c.name)
        Preferences[self.visible_columns_pref] = tuple(visible)
        Preferences.save() # this save all prefs not just visible columns
                
                    
class _editors(dict):
    def __init__(self):
        path, name = os.path.split(__file__)
        for d in os.listdir(path):
            full = path + os.sep + d 
            if os.path.isdir(full) and os.path.exists(full + os.sep + "__init__.py"):
                m = __import__("editors." + d, globals(), locals(), ['editors'])
                self[m.name] = m.editor
    
    def __getattr__(self, attr):
        if not self.has_key(attr):
            return None
        return self[attr]

editors = _editors()


                             


        

    


        
