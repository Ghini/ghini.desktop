#
# locations.py
#

import gtk
from editors import TreeViewEditorDialog, editors
from tables import tables
import bauble

class ReferencesEditor(TreeViewEditorDialog):

    visible_columns_pref = "editor.references.columns"
    column_width_pref = "editor.references.column_width"
    #default_visible_list = ['site', 'description'] 

    label = 'References'

    def __init__(self, parent=None, select=None, defaults={}):
        TreeViewEditorDialog.__init__(self, tables.Reference,
                                      "References Editor", parent,
                                      select=select, defaults=defaults)                                          
        # set headers
        headers={"label": "Label",
                 "reference": "Reference"}
        self.column_meta.headers = headers

editors.register(ReferencesEditor, tables.References)
