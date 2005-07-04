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

    def __init__(self, parent=None, select=None, defaults={}):

        self.sqlobj = tables.Families

        self.column_meta = editors.createColumnMetaFromTable(self.sqlobj)

        # set headers
        headers = {'family': 'Family',
                   'comments': 'Comments'}
        self.column_meta.set_headers(headers)

        # set default visible
        default_visible_list = ['family', 'comments']
        
        # set visible from stored prefs
        if not bauble.prefs.has_key(self.visible_columns_pref):
            bauble.prefs[self.visible_columns_pref] = default_visible_list
        self.set_visible_columns_from_prefs(self.visible_columns_pref)
        
        editors.TreeViewEditorDialog.__init__(self, "Families Editor",
                                              select=select, defaults=defaults)