#
# module to provide a list of common names for a plantname
#

import gtk
from sqlobject import *
import bauble
from bauble.plugins import BaubleTable, tables, editors
from bauble.treevieweditor import TreeViewEditorDialog, ToggleColumn, \
    GenericViewColumn
from bauble.utils.log import log, debug

# TODO: getting a vernacular name in the search results isn't very useful,
# it would be nice if we could expand a list of species that might all share a 
# common name, e.g. citrus could return anything with citrus in the 
# vernacular name, also instead of displaying the vernacular name in the
# results we could just return the species the the vernacular name points to

# TODO: distribution doesn't seem to work in the species infobox

class VernacularName(BaubleTable):
    
    name = UnicodeCol(length=64)
    language = UnicodeCol(length=64)    
    
    # default=None b/c the VernacularNameEditor can only be invoked from the 
    # SpeciesEditor and it should set this on commit
    species = ForeignKey('Species', default=None, cascade=True)

    index = DatabaseIndex('name', 'language', 'species', unique=True)

    def __str__(self):
        return self.name
    


# should be able to have a default column that doesn't use the row
# at all, just keeps the value of the selected row and returns the id 
# of the select row, right now this just emulates GenericViewModel but we 
# really should refactor GenericViewModel to allow for this sort of behavior
class DefaultColumn(GenericViewColumn):
    '''
    this column is a toggle column which will represent which if the values
    in the model will be returned as the default vernacular name
    '''
    
    def __init__(self, tree_view_editor, header, name=None):
        super(DefaultColumn, self).__init__(tree_view_editor, header, 
                                            gtk.CellRendererToggle())
        self.selected_row = None	
        self.renderer.connect('toggled', self.on_toggled)
        self.meta.required = True
	
        
    def _get_name(self):
        return "default"        
        

    def on_toggled(self, renderer, path, data=None):
        # FIXME: don't allow selection of the last row, it's empty stupid
        self.dirty = True
        active = not renderer.get_active()
        model = self.table_editor.view.get_model()
        self.selected_row = gtk.TreeRowReference(model, path)
    
    
    def cell_data_func(self, column, renderer, model, iter, data=None):        
        row = model.get_value(iter, 0)
        if row.committed:
            renderer.set_property('sensitive', False)
            renderer.set_property('activatable', False)
        else:
            renderer.set_property('sensitive', True)
            renderer.set_property('activatable', True)
                        
	if len(model) == 1: 
	    # this is the only item in the model so set the selected row,
	    # this probably isn't the best place to be setting 
	    # self.selected_row since we'll be setting it over and over again,
	    # but it seems to work and it makes sure that if there is only
	    # one item in the model then it's always selected
	    model = self.table_editor.view.get_model()
	    self.selected_row = gtk.TreeRowReference(model, (0,))
            renderer.set_active(True)        
        elif self.selected_row is None:
            renderer.set_active(False)            
        else:
            active = self.selected_row.get_path() == model.get_path(iter)
            renderer.set_active(active)        
        
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


    def __init__(self, parent=None, select=None, default_name=None,
                 defaults={}, **kwargs):
        '''
        default_id is the id of the row in select that should be set as the 
        default name
        '''
        TreeViewEditorDialog.__init__(self, VernacularName, 
                                      "Vernacular Name Editor", parent,
                                      select=select, defaults=defaults, 
                                      **kwargs)
        # set headers
        titles = {"name": "Name",
                  "language": "Language",
                 }

        self.columns.titles = titles        
        self.columns.pop('speciesID')
        self.columns['default'] = DefaultColumn(self, 'Default')
        self.default_name = default_name
	self.default_values = None
        
    
    def pre_start_hook(self):
        # set the default toggle
        model = self.view.get_model()
        
        if len(model) == 1: 
            # only one value in the model, set it as the default
	    # TODO: this isn't doing anything, why is it here?
            model[0]
        else:
            for item in model: # skip last row which should be empty
                row = item[0]
                if 'id' in row and row['id'] == self.default_name.id:
    #                debug('default: %s' % row)
                    path = model.get_path(item.iter)
                    self.columns['default'].selected_row = \
                        gtk.TreeRowReference(model, path)
        self.default_name = None            	


    is_default = False
        
    def post_commit_hook(self, table_instance):
#        debug(self.columns['default'].selected_row)
        if self.is_default:
            self.default_name = table_instance
            self.is_default = False # reset 
        

    def _model_row_to_values(self, row):
	'''
	_model_row_to_values
	row: iter from self.model
	return None if you don't want to commit anything
	'''    
	values = super(VernacularNameEditor, self)._model_row_to_values(row)
	if values is None:
	    return None

	if values == self.default_values:
	    self.is_default = True
	else:
	    # reset to false incase commit_changes is called twice
	    self.is_default = False 
	    
	return values



    def commit_changes(self):
	selected_row = self.columns['default'].selected_row
	model = selected_row.get_model()
	self.default_values = model[model.get_iter(selected_row.get_path())][0]

        committed_rows = \
            super(VernacularNameEditor, self).commit_changes()

	selected_row = self.columns['default'].selected_row
	model = selected_row.get_model()
	sel = model[model.get_iter(selected_row.get_path())][0]

        if self.default_name is None:
            sr = self.columns['default'].selected_row
            model = sr.get_model()
            sel = model[model.get_iter(sr.get_path())][0]
            debug(sel)
	    if sel.isinstance:
		self.default_name = sel.row
	    else:
		raise bauble.BaubleError('no default selected')	    
        return self.default_name, committed_rows
                
    
