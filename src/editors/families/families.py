#
# families.py
#

import gtk

import editors
from tables import tables
import bauble

class FamiliesEditor(editors.TreeViewEditorDialog):

    visible_columns_pref = "editor.families.columns"
    column_width_pref = "editor.families.column_width"
    default_visible_list = ['family', 'comments']
    
    def __init__(self, parent=None, select=None, defaults={}):
        
        editors.TreeViewEditorDialog.__init__(self, tables.Families, 
                                              "Families Editor", parent,
                                              select=select, defaults=defaults)
        headers = {'family': 'Family',
                   'comments': 'Comments'}
        self.column_meta.headers = headers