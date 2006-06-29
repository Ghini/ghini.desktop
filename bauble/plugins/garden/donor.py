#
# donor editor module
#

from sqlobject import * 
from bauble.plugins import BaubleTable, tables
from bauble.editor import *
from bauble.treevieweditor import TreeViewEditorDialog
import bauble.paths as paths

def edit_callback(row):
    value = row[0]
    # TODO: the select paramater can go away when we move FamilyEditor to the 
    # new style editors    
    e = DonorEditor(select=[value], model=value)
    e.start()
    

def remove_callback(row):
    value = row[0]
    s = '%s: %s' % (value.__class__.__name__, str(value))
    msg = "Are you sure you want to remove %s?" % s
        
    if utils.yes_no_dialog(msg):
        from sqlobject.main import SQLObjectIntegrityError
        try:
            value.destroySelf()
            # since we are doing everything in a transaction, commit it
            sqlhub.processConnection.commit() 
            #self.refresh_search()                
        except SQLObjectIntegrityError, e:
            msg = "Could not delete '%s'. It is probably because '%s' "\
                  "still has children that refer to it.  See the Details for "\
                  " more information." % (s, s)
            utils.message_details_dialog(msg, str(e))
        except:
            msg = "Could not delete '%s'. It is probably because '%s' "\
                  "still has children that refer to it.  See the Details for "\
                  " more information." % (s, s)
            utils.message_details_dialog(msg, traceback.format_exc())
            
    
    view = bauble.app.gui.get_current_view()
    debug('refresh search')
    view.refresh_search()


donor_context_menu = [('Edit', edit_callback),
                      ('--', None),
                      ('Remove', remove_callback)]


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
    RESPONSE_NEXT = 11
    ok_responses = (RESPONSE_NEXT,)
    
    def __init__(self, model=Donor, defaults={}, parent=None, **kwargs):
        '''
        @param model: either an Accession class or instance
        @param defaults: a dictionary of Accession field name keys with default
        @param values to enter in the model if none are give
        '''
        self.assert_args(model, Donor, defaults)
        GenericModelViewPresenterEditor.__init__(self, model, defaults, parent)
        self.model = SQLObjectProxy(model)
        self.parent = parent
        self.defaults = defaults
    
    def start(self, commit_transaction=True):    
        '''
        @param commit_transaction: where we should call 
            sqlobject.sqlhub.processConnection.commit() to commit our changes
        '''
        self.view = DonorEditorView(parent=self.parent)
        self.presenter = DonorEditorPresenter(self.model, self.view, self.defaults)
        
        not_ok_msg = 'Are you sure you want to lose your changes?'
        exc_msg = "Could not commit changes.\n"
        committed = None
        while True:
            response = self.presenter.start()
            self.view.save_state() # should view or presenter save state
            if response == gtk.RESPONSE_OK or response in self.ok_responses:
                try:
                    committed = self.commit_changes()                
                except DontCommitException:
                    continue
                except BadValue, e:
                    utils.message_dialog(saxutils.escape(str(e)),
                                         gtk.MESSAGE_ERROR)
                except CommitException, e:
                    debug(traceback.format_exc())
                    exc_msg + ' \n %s\n%s' % (str(e), e.row)
                    utils.message_details_dialog(saxutils.escape(exc_msg), 
                                 traceback.format_exc(), gtk.MESSAGE_ERROR)
                    sqlhub.processConnection.rollback()
                    sqlhub.processConnection.begin()
                except Exception, e:
                    debug(traceback.format_exc())
                    exc_msg + ' \n %s' % str(e)
                    utils.message_details_dialog(saxutils.escape(exc_msg), 
                                                 traceback.format_exc(),
                                                 gtk.MESSAGE_ERROR)
                    sqlhub.processConnection.rollback()
                    sqlhub.processConnection.begin()
                else:
                    break
            elif self.model.dirty and utils.yes_no_dialog(not_ok_msg):
                self.model.dirty = False
                break
            elif not self.model.dirty:
                break
            
        if commit_transaction:
            sqlhub.processConnection.commit()

        # respond to responses
        more_committed = None
        if response == self.RESPONSE_NEXT:
            if self.model.isinstance:
                model = self.model.so_object.__class__
            else:
                model = self.model.so_object
            e = DonorEditor(model, self.defaults, self.parent)
            more_committed = e.start(commit_transaction)
                    
        if more_committed is not None:
            committed = [committed]
            if isinstance(more_committed, list):
                committed.extend(more_committed)
            else:
                committed.append(more_committed)
                
        return committed        

    
    def commit_changes(self):
        debug('DonorEditor.commit_changes: %s' % self.model)
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
