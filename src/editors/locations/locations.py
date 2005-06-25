#
# locations.py
#

import gtk

import editors
from tables import tables

class LocationsEditor(editors.TableEditorDialog):

    visible_columns_pref = "editor.locations.columns"

    def __init__(self, parent=None, select=None, defaults={}):

        self.sqlobj = tables.Locations

        self.column_data = editors.createColumnMetaFromTable(self.sqlobj)

        # set headers
        headers={"site": "Site",
                 "description": "Description"}
        self.column_data.set_headers(headers)

        # set default visible
        self.column_data["site"].visible = True    
        self.column_data["description"].visible = True    
        
        # set visible from stored prefs
        self.set_visible_columns_from_prefs(self.visible_columns_pref)
        
        editors.TableEditorDialog.__init__(self, "Location Editor",
                                           select=select, defaults=defaults)