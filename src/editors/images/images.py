#
# images.py
#

import gtk

import editors
from tables import tables
import bauble

class ImagesEditor(editors.TreeViewEditorDialog):

    visible_columns_pref = "editor.images.columns"
    column_width_pref = "editor.images.column_width"

    def __init__(self, parent=None, select=None, defaults={}):

        self.sqlobj = tables.Images

        self.column_meta = editors.createColumnMetaFromTable(self.sqlobj)

        # set headers
        headers={"uri": "Location (URL)",
                 "label": "Label"}
        self.column_meta.set_headers(headers)

        # set default visible
        default_visible_list = ['label', 'uri']  
        
        # set visible from stored prefs
        if not bauble.prefs.has_key(self.visible_columns_pref):
            bauble.prefs[self.visible_columns_pref] = default_visible_list
        self.set_visible_columns_from_prefs(self.visible_columns_pref)
        
        editors.TreeViewEditorDialog.__init__(self, "Images Editor",
                                              select=select, defaults=defaults)