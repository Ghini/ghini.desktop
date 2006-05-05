#
# donor editor module
#

from sqlobject import * 
from bauble.plugins import BaubleTable, tables
from bauble.treevieweditor import TreeViewEditorDialog

# TODO: show list of donations given by donor if searching for the donor name
# in the search view

class Donor(BaubleTable):

    class sqlmeta(BaubleTable.sqlmeta):
        defaultOrder = 'name'
    
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
                                     "Unknown",
                                     "<not set>"),
                                      # Unknown
                          default='<not set>')
                         
                            
    name = UnicodeCol(length=72, alternateID=True)
    donations = MultipleJoin('Donation', joinColumn='donor_id')
    
    # contact information
    address = StringCol(default=None)
    email = StringCol(default=None)
    fax = StringCol(default=None)
    tel = StringCol(default=None)
    
    def __str__(self):
        return self.name


#class DonorEditorView(GenericEditorView):
#
#    def __init__(self, ):
#
#class DonorEditorPresenter(GenericEditorPresenter):
#    
#    def __init__(self, model, view, defaults={}):
#        GenericEditorPresenter.__init__(self, model, view, defaults)
#    pass
#
#class DonorEditor(TableEditor):
#    def __init__(self, model=Donor, defaults={}, **kwargs):
#        '''
#        model: either an Accession class or instance
#        defaults: a dictionary of Accession field name keys with default
#        values to enter in the model if none are give
#        '''
#        TableEditor.__init__(self, table=Donor, select=None, 
#                             defaults=defaults)
#        # assert that the model is some form of an Accession
#        debug(repr(model))
#        debug(defaults)
#        if not isinstance(model, Donor):
#            assert(issubclass(model, Donor)) 
#            
#        # can't have both defaults and a model instance
#        assert(not isinstance(model, Accession) or len(defaults.keys()) == 0)
#        self.model = SQLObjectProxy(model)
#        self.view = DonorEditorView()
#        self.presenter = DonorEditorPresenter(self.model, self.view, defaults)
            
            


class DonorEditor(TreeViewEditorDialog):

    visible_columns_pref = "editor.donor.columns"
    column_width_pref = "editor.donor.column_width"

    label = 'Donors'

    def __init__(self, parent=None, select=None, defaults={}):
        TreeViewEditorDialog.__init__(self, Donor, "Donor Editor", 
                                      parent, select=select, defaults=defaults)
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
