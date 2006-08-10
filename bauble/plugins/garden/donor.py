#
# donor.py
#

from sqlalchemy import *
from sqlalchemy.exceptions import SQLError
import bauble
from bauble.editor import *
import bauble.paths as paths
from bauble.types import Enum
from bauble.plugins.garden.source import Donation

# TODO: need to make it so you can't delete Donors if they still have 
# associated Donations

def edit_callback(row):
    value = row[0]
    e = DonorEditor(model_or_defaults=value)
    return e.start() != None
    
def remove_callback(row):
    value = row[0]    
    s = '%s: %s' % (value.__class__.__name__, str(value))
    msg = "Are you sure you want to remove %s?" % s
    if not utils.yes_no_dialog(msg):
        return    
    try:
        session = create_session()
        obj = session.load(value.__class__, value.id)
        session.delete(obj)
        session.flush()
    except Exception, e:
        msg = 'Could not delete.\nn%s' % str(e)        
        utils.message_details_dialog(msg, traceback.format_exc(), 
                                     type=gtk.MESSAGE_ERROR)
    return True


donor_context_menu = [('Edit', edit_callback),
                      ('--', None),
                      ('Remove', remove_callback)]


# TODO: show list of donations given by donor if searching for the donor name
# in the search view

donor_table = Table('donor',
                    Column('id', Integer, primary_key=True),
                    Column('name', Unicode(72), unique='donor_index'),
                    Column('donor_type', Enum(values=['Expedition', # Expedition
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
                                                      None], empty_to_none=True)),
                    Column('address', Unicode),
                    Column('email', Unicode(128)),
                    Column('fax', Unicode(64)),
                    Column('tel', Unicode(64)))

class Donor(bauble.BaubleMapper):
    
    def __str__(self):
        return self.name

mapper(Donor, donor_table,
       properties={'donations': relation(Donation, 
                                         backref=backref('donor', uselist=False))},
       order_by='name')
    
#class Donor(BaubleTable):
#
#    class sqlmeta(BaubleTable.sqlmeta):
#        defaultOrder = 'name'
#    
#    name = UnicodeCol(length=72, alternateID=True)
#    donor_type = EnumCol(enumValues=('Expedition', # Expedition
#                                     "Gene bank", # Gene bank
#                                     "Botanic Garden or Arboretum", # Botanic Garden or Arboretum
#                                     "Research/Field Station", # Other research, field or experimental station
#                                     "Staff member", # Staff of the botanic garden to which record system applies
#                                     "University Department", # University Department
#                                     "Horticultural Association/Garden Club", # Horticultural Association or Garden Club
#                                     "Municipal department", # Municipal department
#                                     "Nursery/Commercial", # Nursery or other commercial establishment
#                                     "Individual", # Individual
#                                     "Other", # Other
#                                     "Unknown",
#                                     None),
#                                      # Unknown
#                          default=None)
#                             
#    donations = MultipleJoin('Donation', joinColumn='donor_id')
#    
#    # contact information
#    address = UnicodeCol(default=None)
#    email = UnicodeCol(default=None)
#    fax = UnicodeCol(default=None)
#    tel = UnicodeCol(default=None)
#    
#    def __str__(self):
#        return self.name


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
    
    def __init__(self, model, view):
        GenericEditorPresenter.__init__(self, ModelDecorator(model), view)
        model = gtk.ListStore(str)
        # init the donor types, only needs to be done once
        #for value in self.model.columns['donor_type'].enumValues:
        #column = self.model.c[donor_type']]
        for enum in sorted(self.model.c.donor_type.type.values):
            model.append([enum])
        self.view.widgets.don_type_combo.set_model(model)
        
        self.refresh_view()
        for widget, field in self.widget_to_field_map.iteritems():
            self.assign_simple_handler(widget, field)
        
        self.init_change_notifier()

    
    def on_field_changed(self, model, field):
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
            self.view.set_widget_value(widget, self.model[field])


    def start(self, commit_transaction=True):
        return self.view.start()



class DonorEditor(GenericModelViewPresenterEditor):
    
    label = 'Donors'
    RESPONSE_NEXT = 11
    ok_responses = (RESPONSE_NEXT,)
    
    #def __init__(self, model=Donor, defaults={}, parent=None, **kwargs):
    def __init__(self, model_or_defaults=None, parent=None):
        '''
        @param model: Donor or dictionary of values for Donor
        @param defaults: a dictionary of Donor field name keys with default
        @param values to enter in the model if none are give
        '''
        if isinstance(model_or_defaults, dict):
            model = Donor(**model_or_defaults)
        elif model_or_defaults is None:
            model = Donor()
        elif isinstance(model_or_defaults, Donor):
            model = model_or_defaults
        else:
            raise ValueError('model_or_defaults argument must either be a '\
                             'dictionary or Donor instance')
        GenericModelViewPresenterEditor.__init__(self, model, parent)
        self.parent = parent
    
    
    _committed = None
    
    def handle_response(self, response):
        '''
        handle the response from self.presenter.start() in self.start()
        '''
        not_ok_msg = 'Are you sure you want to lose your changes?'
        if response == gtk.RESPONSE_OK or response in self.ok_responses:
#                debug('session dirty, committing')
            try:
                self.commit_changes()
                self._committed.append(self.model)
            except SQLError, e:                
                exc = traceback.format_exc()
                msg = 'Error committing changes.\n\n%s' % e.orig
                utils.message_details_dialog(msg, str(e), gtk.MESSAGE_ERROR)
                return False
            except:
                msg = 'Unknown error when committing changes. See the details '\
                      'for more information.'
                utils.message_details_dialog(msg, traceback.format_exc(), 
                                             gtk.MESSAGE_ERROR)
                return False
        elif (self.session.dirty and utils.yes_no_dialog(not_ok_msg)) or not self.session.dirty:
            return True
        else:
            return False
                
        # respond to responses
        more_committed = None
        if response == self.RESPONSE_NEXT:
            e = DonorEditor(parent=self.parent)
            more_committed = e.start()
        if more_committed is not None:
            self._committed.append(more_committed)
        
        return True        

        
    def start(self):
        self.view = DonorEditorView(parent=self.parent)
        self.presenter = DonorEditorPresenter(self.model, self.view)
        
        exc_msg = "Could not commit changes.\n"
        committed = None
        while True:
            response = self.presenter.start()
            self.view.save_state() # should view or presenter save state
            if self.handle_response(response):
                break
            
        self.session.close() # cleanup session
        return self._committed
    

        
try:
    from bauble.plugins.searchview.infobox import InfoBox, InfoExpander, \
        set_widget_value
except ImportError:
    # TODO: this should probably be handled a bit more robustly
    class DonorInfoBox:
        pass
else:
    class GeneralDonorExpander(InfoExpander):
        # name, number of donations, address, email, fax, tel, type of donor
        pass
    
    class DonorInfoBox(InfoBox):        
        
        def update(self, row):
            pass
