#
# module to provide a list of common names for a plantname
#

import gtk
from sqlobject import *
from bauble.plugins import BaubleTable, tables, editors
from bauble.plugins.editor import TreeViewEditorDialog, ToggleColumn, \
    GenericViewColumn
from bauble.utils.log import log, debug

class VernacularName(BaubleTable):
    
    name = UnicodeCol(length=64)
    language = UnicodeCol(length=64)    
    
    # default=None b/c the VernacularNameEditor can only be invoked from the 
    # SpeciesEditor and it should set this on commit
    species = ForeignKey('Species', default=None, cascade=True)

    def __str__(self):
        return self.name


# should be able to have a default column that doesn't use the row
# at all, just keeps the value of the selected row and returns the id 
# of the select row, right now this just emulates GenericViewModel but we 
# really should refactor GenericViewModel to allow for this sort of behavior
class DefaultColumn(gtk.TreeViewColumn):
    '''
    this column is a toggle column which will represent which if the values
    in the model will be returned as the default vernacular name
    '''
    
    def __init__(self, tree_view_editor, header):
        self.renderer = gtk.CellRendererToggle()
        self.view = tree_view_editor.view
        super(DefaultColumn, self).__init__(header, self.renderer)
        self.name = 'default'
        self.meta = GenericViewColumn.Meta()
        self.renderer.connect('toggled', self.on_toggled)
        self.set_cell_data_func(self.renderer, self.cell_data_func)
        self.set_clickable(True)
        self.set_resizable(True)
        self.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        self.set_reorderable(True)
        self.selected_row = None
        
    #def _get_name(self):
    #    return 'default'
    
    #def on_edited(self, *args):
    #    super
    def on_toggled(self, renderer, path, data=None):
        self.dirty = True
        active = not renderer.get_active()
        model = self.view.get_model()
        self.selected_row = gtk.TreeRowReference(model, path)

            
#    def get_selected(self):
#        pass
    
    
    def cell_data_func(self, col, cell, model, iter, data=None):
        if self.selected_row is None:
            cell.set_property('active', False)            
        else:
            active = self.selected_row.get_path() == model.get_path(iter)
            cell.set_property('active', active)        
        
#    
# VernacularNameEditor
#
class VernacularNameEditor(TreeViewEditorDialog):
    '''
    for editing the vernacular names of a species
    '''
    
    visible_columns_pref = "editor.vernacular.columns"
    column_width_pref = "editor.vernacular.column_width"
    default_visible_list = ['speciesID', 'name', 'language'] 

    label = 'Vernacular Name'
    standalone = False


    def __init__(self, parent=None, select=None, default_name=None, defaults={}, 
                 connection=None):
        '''
        default_id is the id of the row in select that should be set as the 
        default name
        '''
        #debug('defaults: %s' % defaults)
        #debug('select: %s' % select)
        #self.default_id = defaults['species'].default_vernacular_nameID
        #debug(self.default_id)
        #select = None
        #defaults = {}
        TreeViewEditorDialog.__init__(self, VernacularName, 
                                      "Vernacular Name Editor", parent,
                                      select=select, defaults=defaults,
                                      connection=connection)
        # set headers
        titles = {"name": "Name",
                  "language": "Language",
                  #"speciesID": "Species"
                 }

        self.columns.titles = titles        
        self.columns.pop('speciesID')
        self.columns['default'] = DefaultColumn(self, 'Default')
        #self.columns["speciesID"].meta.get_completions = \
        #    self.get_species_completions
        self.default_instance = None
        self.default_name = default_name
        
    
    def pre_start_hook(self):
        # set the default toggle
        model = self.view.get_model()
        for item in model: # skip last row which should be empty
            #path = model.get_path(item)
            debug(item)
            debug(item[0])
            row = item[0]
            if 'id' in row and row['id'] == self.default_name.id:
                debug('default: %s' % row)
                path = model.get_path(item.iter)
                self.columns['default'].selected_row = \
                    gtk.TreeRowReference(model, path)
            
            
    is_default = False
    def pre_commit_hook(self, values):
        #super(VernacularNameEditor, self).pre_commit_hook(values)
        debug('pre_commit_hook: %s'  % values)
        if values == self.default_values:
            debug('-- is default')
            self.is_default = True
        return True
        
        
    def post_commit_hook(self, table_instance):
        debug(self.column['default'].selected_row)
        if self.is_default:
            self.default_instance = table_instance
            self.is_default = False # reset 
        
        
    def commit_changes(self, commit_transaction=True):
        committed_rows = \
            super(VernacularNameEditor, self).commit_changes(commit_transaction)
        debug(committed_rows)
        debug(self.default_instance)        
        if self.default_instance is None and len(committed_rows) > 0:
            self.commit_changes(commit_transaction)
        if len(committed_rows) == 0:            
            return None, committed_rows
        else:
            self.dirty = True
            #return {'default_vernacular_nameID': self.default_instance, 
            #        "vernacular_names": committed_rows}
            return self.default_instance, committed_rows
                
    def _set_values_from_widgets(self):
        super(VernacularNameEditor, self)._set_values_from_widgets()
        # this is a bit silly b/c it loops over the model twice, once in 
        # super._set_values_from_widgets and once here, this shouldn't 
        # really be a performance hit though
        model = self.view.get_model()
        debug('_set_values_from_widgets')
        sr = self.columns['default'].selected_row
        if sr is None:
            return
        selected_item = sr.get_model().get_iter(sr.get_path())
        selected_value = model[selected_item][0]
        for item in model:                                        
            if item[0] == selected_value:
                self.default_values = selected_value
                return
        
