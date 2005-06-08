#
# families.py
#

import pygtk
pygtk.require("2.0")
import gtk

import editors
from tables import tables

class FamiliesEditor(editors.TableEditorDialog):

    visible_columns_pref = "editor.families.columns"

    def __init__(self, parent=None, select=None):

        self.sqlobj = tables.Families

        self.column_data = editors.createColumnMetaFromTable(self.sqlobj)

        # set headers
        self.column_data["family"].header = "Family"
        self.column_data["comments"].header = "Comments"

        # set default visible
        self.column_data["family"].visible = True
        self.column_data["comments"].visible = True
        
        # set visible from stored prefs
        self.set_visible_columns_from_prefs(self.visible_columns_pref)
        
        editors.TableEditorDialog.__init__(self, "Families Editor", select=select)