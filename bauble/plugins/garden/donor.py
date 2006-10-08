#
# donor.py
#

from sqlalchemy import *
from sqlalchemy.exceptions import SQLError
import bauble
from bauble.editor import *
import bauble.paths as paths
from bauble.types import Enum
from bauble.plugins.garden.source import Donation, donation_table

# TODO: need to make it so you can't delete Donors if they still have 
# associated Donations

def edit_callback(row):
    value = row[0]
    e = DonorEditor(model=value)
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
        msg = 'Could not delete.\n\n%s' % utils.xml_safe(e)        
        utils.message_details_dialog(msg, traceback.format_exc(), 
                                     type=gtk.MESSAGE_ERROR)
    return True


donor_context_menu = [('Edit', edit_callback),
                      ('--', None),
                      ('Remove', remove_callback)]


# TODO: show list of donations given by donor if searching for the donor name
# in the search view
# TODO: the donor_type could be either be character codes or possible a foreign
# key into another table
donor_table = Table('donor',
                    Column('id', Integer, primary_key=True),
                    Column('name', Unicode(72), unique='donor_index'),
                    Column('donor_type', Enum(values=['Expedition',
                                                      "Gene bank",
                                                      "Botanic Garden or Arboretum", 
                                                      "Research/Field Station",
                                                      "Staff member",
                                                      "University Department",
                                                      "Horticultural Association/Garden Club",
                                                      "Municipal department",
                                                      "Nursery/Commercial",
                                                      "Individual",
                                                      "Other",
                                                      "Unknown",
                                                      None], empty_to_none=True)),
                    Column('address', Unicode),
                    Column('email', Unicode(128)),
                    Column('fax', Unicode(64)),
                    Column('tel', Unicode(64)),
                    Column('notes', Unicode),
                    Column('_created', DateTime, default=func.current_timestamp()),
                    Column('_last_updated', DateTime, default=func.current_timestamp(), 
                           onupdate=func.current_timestamp()))

class Donor(bauble.BaubleMapper):
    
    def __str__(self):
        return self.name

# TODO: make sure that you can't delete the donor if donations exist, this
# should have a test
mapper(Donor, donor_table,
       properties={'donations': relation(Donation, 
                                         backref=backref('donor', uselist=False))},
       order_by='name')


class DonorEditorView(GenericEditorView):
    
    def __init__(self, parent=None):
        GenericEditorView.__init__(self, os.path.join(paths.lib_dir(), 
                                                      'plugins', 'garden', 
                                                      'editors.glade'),
                                   parent=parent)
        self.dialog = self.widgets.donor_dialog
        self.connect_dialog_close(self.dialog)
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
        return self.dialog.run()


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

    
    def dirty(self):
        return self.model.dirty
    
    
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


# TODO: need to create a widget to edit the notes
class DonorEditor(GenericModelViewPresenterEditor):
    
    label = 'Donor'
    mnemonic_label = '_Donor'
    RESPONSE_NEXT = 11
    ok_responses = (RESPONSE_NEXT,)
    
    def __init__(self, model=None, parent=None):
        '''
        @param model: Donor instance or None
        @param values to enter in the model if none are give
        '''
        if model is None:
            model = Donor()
        GenericModelViewPresenterEditor.__init__(self, model, parent)
        self.parent = parent
        self._committed = []

    
    def handle_response(self, response):
        '''
        handle the response from self.presenter.start() in self.start()
        '''
        not_ok_msg = 'Are you sure you want to lose your changes?'
        if response == gtk.RESPONSE_OK or response in self.ok_responses:
            try:
                if self.presenter.dirty():
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
        elif self.presenter.dirty() and utils.yes_no_dialog(not_ok_msg) or not self.presenter.dirty():
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
        
        # add quick response keys
        dialog = self.view.dialog        
        self.attach_response(dialog, gtk.RESPONSE_OK, 'Return', gtk.gdk.CONTROL_MASK)
        self.attach_response(dialog, self.RESPONSE_NEXT, 'n', gtk.gdk.CONTROL_MASK)                
        
        exc_msg = "Could not commit changes.\n"
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
        '''
        displays name, number of donations, address, email, fax, tel, 
        type of donor
        '''
        def __init__(self, widgets):
            InfoExpander.__init__(self, "Genera", widgets)
            gen_box = self.widgets.don_gen_box
            self.widgets.don_gen_window.remove(gen_box)
            self.vbox.pack_start(gen_box)
        
                
        def update(self, row):
            self.set_widget_value('don_name_data', row.name)
            self.set_widget_value('don_address_data', row.address)
            self.set_widget_value('don_email_data', row.email)
            self.set_widget_value('don_tel_data', row.tel)
            self.set_widget_value('don_fax_data', row.fax)
            
            ndons = select([donation_table.c.id], 
                           donation_table.c.donor_id==row.id).count().scalar()
            self.set_widget_value('don_ndons_data', ndons)            
    
    
    class NotesExpander(InfoExpander):
        """
        displays notes about the donor
        """
    
        def __init__(self, widgets):
            InfoExpander.__init__(self, "Notes", widgets)            
            notes_box = self.widgets.don_notes_box
            self.widgets.don_notes_window.remove(notes_box)
            self.vbox.pack_start(notes_box)
        
            
        def update(self, row):
            if row.notes is None:
                self.set_sensitive(False)
                self.set_expanded(False)            
            else:
                # TODO: get expanded state from prefs
                self.set_sensitive(True)
                self.set_widget_value('don_notes_data', row.notes)       
    
    class DonorInfoBox(InfoBox):        
        
        def __init__(self):
            InfoBox.__init__(self)
            glade_file = os.path.join(paths.lib_dir(), "plugins", "garden", 
                                "infoboxes.glade")
            self.widgets = utils.GladeWidgets(gtk.glade.XML(glade_file))            
            self.general = GeneralDonorExpander(self.widgets)
            self.add_expander(self.general)
            self.notes = NotesExpander(self.widgets)
            self.add_expander(self.notes)
            
        def update(self, row):
            self.general.update(row)
            self.notes.update(row)
            
