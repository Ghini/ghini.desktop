#
# Locations table definition
#

from sqlalchemy import *
from sqlalchemy.orm.session import object_session
from sqlalchemy.exceptions import SQLError
import bauble
from bauble.editor import *
import bauble.utils as utils
import bauble.paths as paths


def edit_callback(row):
    value = row[0]    
    # TODO: the select paramater can go away when we move FamilyEditor to the 
    # new style editors    
    e = LocationEditor(select=[value], model=value)
    return e.start() != None


def add_plant_callback(row):
    value = row[0]
    e = PlantEditor(defaults={'locationID': value})
    return e.start() != None


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
            return True
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


loc_context_menu = [('Edit', edit_callback),
                    ('--', None),
                    ('Add plant', add_plant_callback),
                    ('--', None),
                    ('Remove', remove_callback)]


location_table = Table('location',
                       Column('id', Integer, primary_key=True),
                       Column('site', Unicode(64), unique=True),
                       Column('description', Unicode))
                   

# TODO: change location to site
class Location(bauble.BaubleMapper):
    def __str__(self):
        return self.site
    

from bauble.plugins.garden.plant import Plant

mapper(Location, location_table, order_by='site',
       properties={'plants': relation(Plant, backref='location')})
    

class LocationEditorView(GenericEditorView):
    
    #source_expanded_pref = 'editor.accesssion.source.expanded'

    def __init__(self, parent=None):
        GenericEditorView.__init__(self, os.path.join(paths.lib_dir(), 
                                                      'plugins', 'garden', 
                                                      'editors.glade'),
                                   parent=parent)
        self.widgets.location_dialog.set_transient_for(parent)
        self.connect_dialog_close(self.widgets.location_dialog)

            
    def start(self):
        return self.widgets.location_dialog.run()    
        

class LocationEditorPresenter(GenericEditorPresenter):
    
    widget_to_field_map = {'loc_location_entry': 'site',
                           'loc_desc_textview': 'description'}
    
#    PROBLEM_INVALID_DATE = 3
#    PROBLEM_INVALID_SPECIES = 4
#    PROBLEM_DUPLICATE_ACCESSION = 5
    
    def __init__(self, model, view):
        '''
        model: should be an instance of class Accession
        view: should be an instance of AccessionEditorView
        '''
        GenericEditorPresenter.__init__(self, ModelDecorator(model), view)
        self.session = object_session(model)

        # TODO: should we set these to the default value or leave them
        # be and let the default be set when the row is created, i'm leaning
        # toward the second, its easier if it works this way

        # initialize widgets

        self.refresh_view() # put model values in view            
        
        # connect signals
        self.assign_simple_handler('loc_location_entry', 'site')
        self.assign_simple_handler('loc_desc_textview', 'description')
        
        
    def refresh_view(self):
        for widget, field in self.widget_to_field_map.iteritems():
            value = self.model[field]
            self.view.set_widget_value(widget, value)

    
    def start(self):
        return self.view.start()
    
    
class LocationEditor(GenericModelViewPresenterEditor):
    
    label = 'Location'
    
    # these have to correspond to the response values in the view
    RESPONSE_OK_AND_ADD = 11
    RESPONSE_NEXT = 22
    ok_responses = (RESPONSE_OK_AND_ADD, RESPONSE_NEXT)    
        
        
    def __init__(self, model_or_defaults=None, parent=None):
        '''
        @param model_or_defaults: Location instance or default values
        @param defaults: {}
        @param parent: None
        '''        
        if isinstance(model_or_defaults, dict):
            model = Location(**model_or_defaults)
        elif model_or_defaults is None:
            model = Location()
        elif isinstance(model_or_defaults, Location):
            model = model_or_defaults
        else:
            raise ValueError('model_or_defaults argument must either be a '\
                             'dictionary or Location instance')
        GenericModelViewPresenterEditor.__init__(self, model, parent)
        if parent is None: # should we even allow a change in parent
            parent = bauble.app.gui.window
        self.parent = parent
        self._committed = []

    
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
                msg = 'Error committing changes.\n\n%s' % e.orig
                utils.message_details_dialog(msg, str(e), gtk.MESSAGE_ERROR)
                return False
            except:
                msg = 'Unknown error when committing changes. See the details '\
                      'for more information.'
                utils.message_details_dialog(msg, traceback.format_exc(), 
                                             gtk.MESSAGE_ERROR)
                return False
        elif self.session.dirty and utils.yes_no_dialog(not_ok_msg) or not self.session.dirty:
            return True
        else:
            return False
                
        # respond to responses
        more_committed = None
        if response == self.RESPONSE_NEXT:
            e = LocationEditor(parent=self.parent)
            more_committed = e.start()
        elif response == self.RESPONSE_OK_AND_ADD:
            e = PlantEditor(parent=self.parent, 
                            model_or_defaults={'location_id': self._committed[0].id})
            more_committed = e.start()
             
        if more_committed is not None:
            if isinstance(more_committed, list):
                self._committed.extend(more_committed)
            else:
                self._committed.append(more_committed)                
        
        return True            
    
    
    def start(self):
        self.view = LocationEditorView(parent=self.parent)
        self.presenter = LocationEditorPresenter(self.model, self.view)
        
        exc_msg = "Could not commit changes.\n"
        committed = None
        while True:
            response = self.presenter.start()
            self.view.save_state() # should view or presenter save state
            if self.handle_response(response):
                break
            
        self.session.close() # cleanup session
        return self._committed


#
# import here to avoid circular dependencies
#
from bauble.plugins.garden.plant import PlantEditor
