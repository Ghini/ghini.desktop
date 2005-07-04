#
# locations.py
#

import gtk

import editors
from tables import tables
import bauble

class LocationsEditor(editors.TreeViewEditorDialog):

    visible_columns_pref = "editor.locations.columns"
    column_width_pref = "editor.locations.column_width"

    def __init__(self, parent=None, select=None, defaults={}):

        self.sqlobj = tables.Locations

        self.column_meta = editors.createColumnMetaFromTable(self.sqlobj)

        # set headers
        headers={"site": "Site",
                 "description": "Description"}
        self.column_meta.set_headers(headers)

        # set default visible
        default_visible_list = ['site', 'description'] 
        
        # set visible from stored prefs
        if not bauble.prefs.has_key(self.visible_columns_pref):
            bauble.prefs[self.visible_columns_pref] = default_visible_list
        self.set_visible_columns_from_prefs(self.visible_columns_pref)
        
        editors.TreeViewEditorDialog.__init__(self, "Location Editor",
                                              select=select, defaults=defaults)