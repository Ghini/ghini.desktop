#
# images.py
#

import gtk

import editors
from tables import tables

class ImagesEditor(editors.TreeViewEditorDialog):

    visible_columns_pref = "editor.images.columns"
    column_width_pref = "editor.images.column_width"

    def __init__(self, parent=None, select=None, defaults={}):

        self.sqlobj = tables.Images

        self.column_data = editors.createColumnMetaFromTable(self.sqlobj)

        # set headers
        headers={"uri": "Location (URL)",
                 "label": "Label"}
        self.column_data.set_headers(headers)

        # set default visible
        self.column_data["uri"].visible = True    
        self.column_data["label"].visible = True    
        
        # set visible from stored prefs
        self.set_visible_columns_from_prefs(self.visible_columns_pref)
        
        editors.TreeViewEditorDialog.__init__(self, "Images Editor",
                                              select=select, defaults=defaults)