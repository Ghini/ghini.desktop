#
# module to provide a list of common names for a plantname
#

import gtk
from sqlobject import *
from bauble.plugins import BaubleTable, tables, editors
from bauble.plugins.editor import TreeViewEditorDialog
from bauble.utils.log import log, debug

class VernacularName(BaubleTable):
    
    name = UnicodeCol()
    language = UnicodeCol()    
    species = ForeignKey('Species', notNull=True)

    
class VernacularNameEditor(TreeViewEditorDialog):

    visible_columns_pref = "editor.vernacular.columns"
    column_width_pref = "editor.vernacular.column_width"
    default_visible_list = ['speciesID', 'name', 'language'] 

    label = 'Vernacular Name'

    def __init__(self, parent=None, select=None, defaults={}, connection=None):
        debug(defaults)
        TreeViewEditorDialog.__init__(self, VernacularName, 
                                      "Vernacular Name Editor", parent,
                                      select=select, defaults=defaults,
                                      connection=connection)
        # set headers
        titles = {"name": "Name",
                  "language": "Language",
                  "speciesID": "Species"
                 }
        self.columns.titles = titles        
        self.columns["speciesID"].meta.get_completions = \
            self.get_species_completions


    def get_species_completions(self, text):
        # see accession.py for notes about this method
        parts = text.split(" ")
        genus = parts[0]
        sr = tables["Genus"].select("genus LIKE '"+genus+"%'",
                                    connection=self.transaction)
        model = gtk.ListStore(str, object) 
        for row in sr:
            for species in row.species:                
                model.append((str(species), species))
        return model
