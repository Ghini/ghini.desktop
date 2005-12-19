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



# should be able to have a default column that doesn't use the row
# at all, just keeps the value of the selected row and returns the id 
# of the select row, right now this just emulates GenericViewModel but we 
# really should refactor GenericViewModel to allow for this sort of behavior
class DefaultColumn(gtk.TreeViewColumn):
    
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
        
        
    def on_toggled(self, renderer, path, data=None):
        self.dirty = True
        active = not renderer.get_active()
        model = self.view.get_model()
        self.selected_row = gtk.TreeRowReference(model, path)

            
    def get_selected(self):
        pass
    
    
    def cell_data_func(self, col, cell, model, iter, data=None):
        if self.selected_row is None:
            cell.set_property('active', False)            
        else:
            active = self.selected_row.get_path() == model.get_path(iter)
            cell.set_property('active', active)        
        
        
class VernacularNameEditor(TreeViewEditorDialog):

    visible_columns_pref = "editor.vernacular.columns"
    column_width_pref = "editor.vernacular.column_width"
    default_visible_list = ['speciesID', 'name', 'language'] 

    label = 'Vernacular Name'
    standalone = False

    def __init__(self, parent=None, select=None, defaults={}, connection=None):
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


#    def get_species_completions(self, text):
#        # see accession.py for notes about this method
#        parts = text.split(" ")
#        genus = parts[0]
#        sr = tables["Genus"].select("genus LIKE '"+genus+"%'",
#                                    connection=self.transaction)
#        model = gtk.ListStore(str, object) 
#        for row in sr:
#            for species in row.species:                
#                model.append((str(species), species))
#        return model
