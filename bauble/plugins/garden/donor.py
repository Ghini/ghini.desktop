#
# donor editor module
#

from sqlobject import * 
from bauble.plugins import BaubleTable, tables
from bauble.editor import *
from bauble.treevieweditor import TreeViewEditorDialog
import bauble.paths as paths

# TODO: show list of donations given by donor if searching for the donor name
# in the search view

class Donor(BaubleTable):

    class sqlmeta(BaubleTable.sqlmeta):
        defaultOrder = 'name'
    
    name = UnicodeCol(length=72, alternateID=True)
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
                                     None),
                                      # Unknown
                          default=None)
                             
    donations = MultipleJoin('Donation', joinColumn='donor_id')
    
    # contact information
    address = UnicodeCol(default=None)
    email = UnicodeCol(default=None)
    fax = UnicodeCol(default=None)
    tel = UnicodeCol(default=None)
    
    def __str__(self):
        return self.name


class DonorEditorView(GenericEditorView):
    
    def __init__(self, parent=None):
        GenericEditorView.__init__(self, os.path.join(paths.lib_dir(), 
                                                      'plugins', 'garden', 
                                                      'editors.glade'),
                                   parent=parent)
        self.connect_dialog_close(self.widgets.donor_dialog)
        if sys.platform == 'win32':
            import pango
            combo = self.widgets.don_type_combo
            context = combo.get_pango_context()        
            font_metrics = context.get_metrics(context.get_font_description(), 
                                               context.get_language())        
            width = font_metrics.get_approximate_char_width()            
            new_width = pango.PIXELS(width) * 20
            combo.set_size_request(new_width, -1)
            
        
    def start(self):
        return self.widgets.donor_dialog.run()


class DonorEditorPresenter(GenericEditorPresenter):
    
    widget_to_field_map = {'don_name_entry': 'name',
                           'don_type_combo': 'donor_type',
                           'don_address_textview': 'address',
                           'don_email_entry': 'email',
                           'don_tel_entry': 'tel',
                           'don_fax_entry': 'fax'
                           }
    
    def __init__(self, model, view, defaults={}):
        GenericEditorPresenter.__init__(self, model, view, defaults)
        model = gtk.ListStore(str)
        # init the donor types, only needs to be done once
        for value in self.model.columns['donor_type'].enumValues:
            model.append([value])
        self.view.widgets.don_type_combo.set_model(model)
        
        self.refresh_view()
        for widget, field in self.widget_to_field_map.iteritems():
            self.assign_simple_handler(widget, field)
        
        self.init_change_notifier()

    
    def on_field_changed(self, field):
        self.view.widgets.don_ok_button.set_sensitive(True)


    def init_change_notifier(self):
        '''
        for each widget register a signal handler to be notified when the
        value in the widget changes, that way we can do things like sensitize
        the ok button
        '''
        for widget, field in self.widget_to_field_map.iteritems():            
            w = self.view.widgets[widget]
            self.model.add_notifier(field, self.on_field_changed)


    def refresh_view(self):
        for widget, field in self.widget_to_field_map.iteritems():            
#            debug('donor refresh(%s, %s=%s)' % (widget, field, 
#                                                self.model[field]))
            self.view.set_widget_value(widget, self.model[field],
                                       self.defaults.get(field, None))         
        pass


    def start(self, commit_transaction=True):
        return self.view.start()



class DonorEditor(GenericModelViewPresenterEditor):
    
    label = 'Donors'
    RESPONSE_NEXT = 22
    ok_responses = (RESPONSE_NEXT,)
    
    def __init__(self, model=Donor, defaults={}, parent=None, **kwargs):
        '''
        model: either an Accession class or instance
        defaults: a dictionary of Accession field name keys with default
        values to enter in the model if none are give
        '''
        self.assert_args(model, Donor, defaults)
        GenericModelViewPresenterEditor.__init__(self, model, defaults, parent)
        self.model = SQLObjectProxy(model)
        self.view = DonorEditorView(parent=parent)
        self.presenter = DonorEditorPresenter(self.model, self.view, defaults)
            
            
    def commit_changes(self):
        committed = None
        if self.model.dirty:
            committed = self._commit(self.model)
        return committed
        

        
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
