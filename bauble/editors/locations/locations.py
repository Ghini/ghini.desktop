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
    default_visible_list = ['site', 'description'] 

    label = 'Locations'

    def __init__(self, parent=None, select=None, defaults={}):
        editors.TreeViewEditorDialog.__init__(self, tables.Locations,
                                              "Location Editor", parent,
                                              select=select, defaults=defaults)                                          
        # set headers
        headers={"site": "Site",
                 "description": "Description"}
        self.column_meta.headers = headers