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
    default_visible_list = ['label', 'uri', 'plantname'] 
    
    
    def __init__(self, parent=None, select=None, defaults={}):
        
        editors.TreeViewEditorDialog.__init__(self, tables.Images, 
                                            "Images Editor", parent,
                                            select=select, defaults=defaults)
        headers={"uri": "Location (URL)",
                 "label": "Label",
                 'plantname': 'Plant Name'}
        self.column_meta.headers = headers