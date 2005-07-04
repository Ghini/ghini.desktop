#
# collections.py
#

import gtk

import editors
from tables import tables

class CollectionsEditor(editors.TreeViewEditorDialog):

    visible_columns_pref = "editor.collections.columns"
    column_width_pref = "editor.collections.column_width"

    def __init__(self, parent=None, select=None, defaults={}):

        self.sqlobj = tables.Collections

        self.column_meta = editors.createColumnMetaFromTable(self.sqlobj)

        # set headers
        #headers={"site": "Site",
        #         "description": "Description"}
        #self.column_meta.set_headers(headers)

        # set default visible
        #self.column_meta["site"].visible = True    
        #self.column_meta["description"].visible = True    
        
        # set visible from stored prefs
        self.set_visible_columns_from_prefs(self.visible_columns_pref)
        
        editors.TreeViewEditorDialog.__init__(self, "Collections Editor",
                                              select=select, defaults=defaults)