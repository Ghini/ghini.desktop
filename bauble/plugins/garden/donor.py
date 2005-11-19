#
# donor editor module
#

from sqlobject import * 
from bauble.plugins import BaubleTable, tables
from bauble.plugins.editor import TreeViewEditorDialog

# TODO: show list of donations given by donor if searching for the donor name
# in the search view

class Donor(BaubleTable):
    
    values = {}
    # herbarium, garden, individual, etc...
#    donor_type = StringCol(length=1)
#    values["donor_type"] = [("E", "Expedition"),
#                            ("G", "Gene bank"),
#                            ("B", "Botanic Garden or Arboretum"),
#                            ("R", "Other research, field or experimental station"),
#                            ("S", "Staff of the botanic garden to which record system applies"),
#                            ("U", "University Department"),
#                            ("H", "Horticultural Association or Garden Club"),
#                            ("M", "Municipal department"),
#                            ("N", "Nursery or other commercial establishment"),
#                            ("I", "Individual"),
#                            ("O", "Other"),
#                            ("U", "Unknown")]
#    donor_type = EnumCol(enumValues=("E", # Expedition
#                                     "G", # Gene bank
#                                     "B", # Botanic Garden or Arboretum
#                                     "R", # Other research, field or experimental station
#                                     "S", # Staff of the botanic garden to which record system applies
#                                     "U", # University Department
#                                     "H", # Horticultural Association or Garden Club
#                                     "M", # Municipal department
#                                     "N", # Nursery or other commercial establishment
#                                     "I", # Individual
#                                     "O", # Other
#                                     "U", # Unknown
#                                     None),
    donor_type = EnumCol(enumValues=('Expedition', # Expedition
                                     "Gene bank", # Gene bank
                                     "Botanic Garden or Arboretum", # Botanic Garden or Arboretum
                                     "Research/Field Station", # Other research, field or experimental station
                                     "Staff member", # Staff of the botanic garden to which record system applies
                                     "University Department", # University Department
                                     "Horticultural Association/Garden Club", # Horticultural Association or Garden Club
                                     "Municipal department", # Municipal department
                                     "Nursery/Commercial", # Nursery or other commercial establishment
                                     "Individual", # Individual
                                     "Other", # Other
                                     "Unknown"), # Unknown
                          default='Unknown')
                         
                            
    name = UnicodeCol(length=72)
    donations = MultipleJoin('Donation', joinColumn='donor_id')
    
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

    label = 'Donors'

    def __init__(self, parent=None, select=None, defaults={}, connection=None):
        TreeViewEditorDialog.__init__(self, Donor, "Donor Editor", 
                                      parent, select=select, defaults=defaults,
                                      connection=connection)
        titles = {"name": "Name",
                  "donor_type": "Donor Type",
                  'address': 'Address',
                  'email': 'Email',
                  'fax': 'Fax #',
                  'tel': 'Tel #'
                 }
        self.columns.titles = titles
        
try:
    from bauble.plugins.searchview.infobox import InfoBox, InfoExpander, \
        set_widget_value
except ImportError:
    pass
else:
    class GeneralDonorExpander(InfoExpander):
        # name, number of donations, address, email, fax, tel, type of donor
        pass
    
    class DonorInfoBox(InfoBox):        
        
        def update(self, row):
            pass