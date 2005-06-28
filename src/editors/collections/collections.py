#
# collections.py
#

import gtk

import editors
from tables import tables

class CollectionsEditor(editors.TreeViewEditorDialog):

    visible_columns_pref = "editor.collections.columns"

    def __init__(self, parent=None, select=None, defaults={}):

        self.sqlobj = tables.Collections

        self.column_data = editors.createColumnMetaFromTable(self.sqlobj)

        # set headers
        #headers={"site": "Site",
        #         "description": "Description"}
        #self.column_data.set_headers(headers)

        # set default visible
        #self.column_data["site"].visible = True    
        #self.column_data["description"].visible = True    
        
        # set visible from stored prefs
        self.set_visible_columns_from_prefs(self.visible_columns_pref)
        
        editors.TreeViewEditorDialog.__init__(self, "Collections Editor",
                                              select=select, defaults=defaults)