#
# plantnames.py
#

import pygtk
pygtk.require("2.0")
import gtk

import editors
from tables import tables

class PlantnamesEditor(editors.TableEditorDialog):
    
    visible_columns_pref = "editor.plantnames.columns"

    
    def __init__(self, parent=None, select=None, defaults={}):

        self.sqlobj = tables.Plantnames

        self.column_data = editors.createColumnMetaFromTable(self.sqlobj)

        # set headers
        self.column_data["genus"].header = "Genus"

        # set default visible
        self.column_data["genus"].visible = True

        # set visible from stored prefs
        self.set_visible_columns_from_prefs(self.visible_columns_pref)
                        
        editors.TableEditorDialog.__init__(self, "Plantnames Editor",
                                           select=select, defaults=defaults)

        
    def foreign_does_not_exist(self, name, value):
        self.add_genus(value)    


    def add_genus(self, name):
        msg = "The Genus %s does not exist. Would you like to add it?" % name
        if utils.yes_no_dialog(msg):
            print "add genus"

    def get_completions(self, text, colname):
        maxlen = -1
        model = None
        if colname == "genus":
            model = gtk.ListStore(str, int)
            if len(text) > 2:
                sr = tables.Genera.select("genus LIKE '"+text+"%'")
                for row in sr: model.append([str(row), row.id])
        return model, maxlen
