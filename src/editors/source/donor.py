#
# donor editor module
#

import gtk

import editors
from tables import tables
import bauble

class DonorsEditor(editors.TreeViewEditorDialog):

    visible_columns_pref = "editor.donors.columns"
    column_width_pref = "editor.donors.column_width"
    #default_visible_list = ['site', 'description'] 

    label = 'Donors'

    def __init__(self, parent=None, select=None, defaults={}):
        editors.TreeViewEditorDialog.__init__(self, tables.Donors,
                                              "Donors Editor", parent,
                                              select=select, defaults=defaults)                                          
        # set headers
        headers={"name": "Name",
                 "donor_type": "Donor Type"}
        self.column_meta.headers = headers