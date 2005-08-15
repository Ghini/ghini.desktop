#
# donor editor module
#

from sqlobject import * 
from bauble.plugins import BaubleTable, tables
from bauble.plugins.editor import TreeViewEditorDialog

class Donor(BaubleTable):
    
    values = {}
    # herbarium, garden, individual, etc...
    donor_type = StringCol(length=1)
    values["donor_type"] = [("E", "Expedition"),
                            ("G", "Gene bank"),
                            ("B", "Botanic Garden or Arboretum"),
                            ("R", "Other research, field or experimental station"),
                            ("S", "Staff of the botanic garden to which record system applies"),
                            ("U", "University Department"),
                            ("H", "Horticultural Association or Garden Club"),
                            ("M", "Municipal department"),
                            ("N", "Nursery or other commercial establishment"),
                            ("I", "Individual"),
                            ("O", "Other"),
                            ("U", "Unknown")]
                            
    name = StringCol(length=72)
    donations = MultipleJoin('Donations', joinColumn='donor_id')
    
    # contact information
    address = StringCol(default=None)
    email = StringCol(default=None)
    fax = StringCol(default=None)
    tel = StringCol(default=None)
    
    def __str__(self):
        return self.name


class DonorEditor(TreeViewEditorDialog):

    visible_columns_pref = "editor.donor.columns"
    column_width_pref = "editor.donor.column_width"
    #default_visible_list = ['site', 'description'] 

    label = 'Donors'

    def __init__(self, parent=None, select=None, defaults={}):
        TreeViewEditorDialog.__init__(self, Donor, "Donors Editor", 
                                      parent, select=select, defaults=defaults)                                          
        # set headers
        headers={"name": "Name",
                 "donor_type": "Donor Type"}
        self.column_meta.headers = headers