#
# Plants table definition
#

import gtk, gobject
from sqlalchemy import *
from sqlalchemy.orm.session import object_session
from sqlalchemy.exceptions import SQLError
from bauble.editor import *
import bauble.utils as utils
from bauble.utils.log import debug
from bauble.types import Enum

# TODO: do a magic attribute on plant_id that checks if a plant id
# already exists with the accession number, this probably won't work though
# sense the acc_id may not be set when setting the plant_id

# TODO: should probably make acc_status required since whether a plant is 
# living or dead is pretty important

# TODO: need a way to search plants by the full accession number, 
# e.g. 2004.0011.02 would return a specific plant, probably need to be
# able to set a callback function like the children field of the view meta

# TODO: might be worthwhile to have a label or textview next to the location
# combo that shows the description of the currently selected location

def edit_callback(row):
    value = row[0]    
    e = PlantEditor(value)
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


plant_context_menu = [('Edit', edit_callback),
                      ('--', None),
                      ('Remove', remove_callback)]


def plant_markup_func(plant):
    '''
    '''
    return '%s (%s)' % (str(plant), 
                        plant.accession.species.markup(authors=False))


plant_history_table = Table('plant_history',
                            Column('id', Integer, primary_key=True),
                            Column('date', Date),
                            Column('description', Unicode),
                            Column('plant_id', Integer, ForeignKey('plant.id'),
                                   nullable=False))


class PlantHistory(bauble.BaubleMapper):
    def __str__(self):
        return '%s: %s' % (self.date, self.description)



# TODO: change plant_id to plant_code, or just code
plant_table = Table('plant', 
                    Column('id', Integer, primary_key=True),
                    Column('code', Unicode, nullable=False, unique='plant_index'),
                    Column('acc_type', 
                           Enum(values=['Plant', 'Seed/Spore', 
                                        'Vegetative Part',  'Tissue Culture', 
                                        'Other', None], empty_to_none=True)),
                    Column('acc_status', Enum(values=['Living accession', 
                                                      'Dead', 'Transferred', 
                                                      'Stored in dormant state', 
                                                      'Other', None], empty_to_none=True)),
                    Column('notes', Unicode),
                    Column('accession_id', Integer, ForeignKey('accession.id'), 
                           nullable=False, unique='plant_index'),
                    Column('location_id', Integer, ForeignKey('location.id'), 
                           nullable=False))

# TODO: configure the acc code and plant code separator, the default should
# be '.'
class Plant(bauble.BaubleMapper):
    
    def __str__(self): 
        return "%s.%s" % (self.accession, self.code)    
    
    def markup(self):
        #return "%s.%s" % (self.accession, self.plant_id)
        # FIXME: this makes expanding accessions look ugly with too many
        # plant names around but makes expanding the location essential
        # or you don't know what plants you are looking at
        return "%s.%s (%s)" % (self.accession, self.code, 
                               self.accession.species.markup())
        
        
        

from bauble.plugins.garden.accession import Accession
#
# setup mappers
# 
plant_mapper = mapper(Plant, plant_table,
       properties={'history': relation(PlantHistory, backref='plant')})
mapper(PlantHistory, plant_history_table, order_by='date')



'''
       # add to end of accession id, e.g. 04-0002.05
        # these are only unique when combined with an accession_id, see the 
        # id_index index    
        #plant_id = IntCol(notNull=True) 
        # makes sense that it should be an int but we won't restrict it that way,
        # if the editor wants to ensure that it is int then it should attach
        # a formencode.Validator on it
        #plant_code = column(Unicode, nullable=True, index='plant_index')
        plant_id = column(Unicode, nullable=True, index='plant_index')
        #plant_id = UnicodeCol(notNull=True)
    
    
        # Plant: Whole plant
        # Seed/Spore: Seed or Spore
        # Vegetative Part: Vegetative Part
        # Tissue Culture: Tissue culture
        # Other: Other, probably see notes for more information
        # None: no information, unknown
        #acc_type = EnumCol(enumValues=('Plant', 'Seed/Spore', 'Vegetative Part', 
        #                               'Tissue Culture', 'Other', None),
        #                   default=None)
        acc_type = column(Unicode)
                              
        # Accession Status
        # Living accession: Current accession in living collection
        # Dead: Noncurrent accession due to Death
        # Transfered: Noncurrent accession due to Transfer
        # Stored in dormant state: Stored in dormant state
        # Other: Other, possible see notes for more information
        # None: no information, unknown)
        #acc_status = EnumCol(enumValues=('Living accession', 'Dead', 'Transfered', 
        #                                 'Stored in dormant state', 'Other', None),
        #                     default=None)
        acc_status = column(Unicode)
        
        notes = column(Unicode)
        #notes = UnicodeCol(default=None)
    
        # indices
        #
        #id_index = DatabaseIndex('plant_id', 'accession', unique=True)
        
        # foreign key
        # 
        #accession = ForeignKey('Accession', notNull=True, cascade=False)
        accession_id = column(Integer, foreign_key=ForeignKey('accession.id'), 
                              nullable=False, index='plant_index')
        
        # TODO: change the "location" field to "site" and then add specific 
        # locations fields like geographic coordinates
        #location = ForeignKey("Location", notNull=True, cascade=False)
        location_id = column(Integer, foreign_key=ForeignKey('location.id'), 
                             nullable=False)
        
        # joins
        #
        #history = MultipleJoin('PlantHistory', joinColumn='plant_id')
        history = one_to_many('PlantHistory', colname='plant_id', 
                              backref='plant')
'''
   

    
class PlantEditorView(GenericEditorView):
    
    #source_expanded_pref = 'editor.accesssion.source.expanded'

    def __init__(self, parent=None):
        GenericEditorView.__init__(self, os.path.join(paths.lib_dir(), 
                                                      'plugins', 'garden', 
                                                      'editors.glade'),
                                   parent=parent)
        self.dialog = self.widgets.plant_dialog
        self.dialog.set_transient_for(parent)
        self.connect_dialog_close(self.dialog)
        def acc_cell_data_func(column, renderer, model, iter, data=None):
            v = model[iter][0]
            renderer.set_property('text', '%s (%s)' % (str(v), str(v.species)))
        self.attach_completion('plant_acc_entry', acc_cell_data_func)
        
    
    def save_state(self):
        pass
    
        
    def restore_state(self):
        pass

            
    def start(self):
        return self.dialog.run()    
        

class ObjectIdValidator(validators.FancyValidator):
    
    def _to_python(self, value, state):
        return value.id
#        try:
#            
#        except:
#            raise validators.Invalid('expected a int in column %s, got %s '\
#                                     'instead' % (self.name, type(value)), value, state)

class PlantEditorPresenter(GenericEditorPresenter):
    
    
#    PROBLEM_INVALID_DATE = 3
#    PROBLEM_INVALID_SPECIES = 4
#    PROBLEM_DUPLICATE_ACCESSION = 5
    widget_to_field_map = {'plant_code_entry': 'code',
                           'plant_acc_entry': 'accession_id',
                           'plant_loc_combo': 'location_id',
                           'plant_acc_type_combo': 'acc_type',
                           'plant_acc_status_combo': 'acc_status',
                           'plant_notes_textview': 'notes'}
    
    def __init__(self, model, view):
        '''
        @model: should be an instance of Plant class
        @view: should be an instance of PlantEditorView
        '''
        GenericEditorPresenter.__init__(self, ModelDecorator(model), view)
        self.session = object_session(model)

        # TODO: should we set these to the default value or leave them
        # be and let the default be set when the row is created, i'm leaning
        # toward the second, its easier if it works this way

        # initialize widgets
        self.init_location_combo()
#        self.init_acc_entry()
        self.init_enum_combo('plant_acc_status_combo', 'acc_status')
        self.init_enum_combo('plant_acc_type_combo', 'acc_type')
        
        
#        self.init_history_box()
        self.refresh_view() # put model values in view            
        
        # connect signals
        def acc_get_completions(text):            
            return self.session.query(Accession).select(Accession.c.code.like('%s%%' % text))
        def format_acc(accession):
            return '%s (%s)' % (accession, accession.species)
        def set_in_model(self, field, value):
            debug('set_in_model(%s, %s)' % (field, value))
            #setattr(self.model, field, value.id)
            setattr(self.model, field, value)
        self.assign_completions_handler('plant_acc_entry', 'accession', 
                                        acc_get_completions, 
                                        set_func=set_in_model, 
                                        format_func=format_acc)
        self.assign_simple_handler('plant_code_entry', 'code')
        #self.assign_simple_handler('plant_loc_combo', 'code')
        self.assign_simple_handler('plant_notes_textview', 'notes')
        self.assign_simple_handler('plant_loc_combo', 'location_id', ObjectIdValidator())
        self.assign_simple_handler('plant_acc_status_combo', 'acc_status', StringOrNoneValidator())
        self.assign_simple_handler('plant_acc_type_combo', 'acc_type', StringOrNoneValidator())        

        self.view.widgets.plant_loc_add_button.connect('clicked', self.on_loc_button_clicked, 'add')
        self.view.widgets.plant_loc_edit_button.connect('clicked', self.on_loc_button_clicked, 'edit')
        
        
    def on_loc_button_clicked(self, button, cmd=None):
        location = None
        combo = self.view.widgets.plant_loc_combo
        it = combo.get_active_iter()
        if it is not None:
            location = combo.get_model()[it][0]         
        if cmd is 'edit':           
            e = LocationEditor(location)
            #e = LocationEditor(model_or_defaults=location)
        else:
            e = LocationEditor()
        e.start()
        self.init_location_combo()
        
        debug(location)
        if location is not None:
            self.session.refresh(location)
            new = self.session.get(Location, location.id)
            utils.set_combo_from_value(combo, new)
        else:
            combo.set_active(-1)
                    
                
    def init_location_combo(self):
        def cell_data_func(column, cell, model, iter, data=None):
            v = model[iter][0]
            cell.set_property('text', str(v))

        locations = self.session.query(Location).select()
        renderer = gtk.CellRendererText()
        combo = self.view.widgets.plant_loc_combo
        combo.clear()
        combo.pack_start(renderer, True)
        combo.set_cell_data_func(renderer, cell_data_func)        
        model = gtk.ListStore(object)
        for loc in locations:
            model.append([loc])
        combo.set_model(model)
        # TODO: if len of location == 1 then set the first item as active,
        # we should probably just always set the first item as active
                
        
    def init_acc_entry(self):
        pass
    def init_type_and_status_combo(self):
        pass
    def init_history_box(self):
        pass
    
    def refresh_view(self):
        for widget, field in self.widget_to_field_map.iteritems():            
            if field is 'accession_id':
                value = self.model.accession
            elif field is 'location_id':
                value = self.model.location
            else:
                value = self.model[field]
            self.view.set_widget_value(widget, value)
    
    def start(self):
        return self.view.start()
    
    
class PlantEditor(GenericModelViewPresenterEditor):
    
    label = 'Plants'
    
    # these have to correspond to the response values in the view
    RESPONSE_NEXT = 22
    ok_responses = (RESPONSE_NEXT,)    
        
        
    def __init__(self, model=None, parent=None):
        '''
        @param model: Plant instance or None
        @param parent: None
        '''        
        if model is None:
            model = Plant()
        GenericModelViewPresenterEditor.__init__(self, model, parent)
        if parent is None: # should we even allow a change in parent
            parent = bauble.app.gui.window
        self.parent = parent
        self._committed = []
        
        
    def handle_response(self, response):
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
                debug(traceback.format_exc())
                utils.message_details_dialog(msg, traceback.format_exc(), 
                                             gtk.MESSAGE_ERROR)
                return False
        elif self.session.dirty and utils.yes_no_dialog(not_ok_msg):                
            return True
        elif not self.session.dirty:
            return True
        else:
            return False
        
        
#        # respond to responses
        more_committed = None
        if response == self.RESPONSE_NEXT:
            e = PlantEditor(parent=self.parent)
            more_committed = e.start()
                    
        if more_committed is not None:
            self._committed = [self._committed]
            if isinstance(more_committed, list):
                self._ommitted.extend(more_committed)
            else:
                self._committed.append(more_committed)                
        
        return True    
    
    
    def start(self):
        from bauble.plugins.garden.accession import Accession
        # TODO: should really open the accession and location editors here, and
        # ask 'Would you like to do that now?'
        if self.session.query(Accession).count() == 0:        
            msg = 'You must first add or import at least one Accession into the '\
                  'database before you can add plants.'
            utils.message_dialog(msg)
            return
        if self.session.query(Location).count() == 0:        
            msg = 'You must first add or import at least one Location into the '\
                  'database before you can add species.'
            utils.message_dialog(msg)
            return
        self.view = PlantEditorView(parent=self.parent)
        self.presenter = PlantEditorPresenter(self.model, self.view)
        
        # add quick response keys
        dialog = self.view.dialog        
        self.attach_response(dialog, gtk.RESPONSE_OK, 'Return', gtk.gdk.CONTROL_MASK)
        self.attach_response(dialog, self.RESPONSE_NEXT, 'n', gtk.gdk.CONTROL_MASK)        
        
        exc_msg = "Could not commit changes.\n"
        committed = None
        while True:
            response = self.presenter.start()
            self.view.save_state() # should view or presenter save state
            if self.handle_response(response):
                break
            
        self.session.close() # cleanup session
        return self._committed
        
        
        

        
#class Plant(BaubleTable):
#
#    class sqlmeta(BaubleTable.sqlmeta):
#	       defaultOrder = 'plant_id'
#
#    # add to end of accession id, e.g. 04-0002.05
#    # these are only unique when combined with an accession_id, see the 
#    # id_index index    
#    #plant_id = IntCol(notNull=True) 
#    # makes sense that it should be an int but we won't restrict it that way,
#    # if the editor wants to ensure that it is int then it should attach
#    # a formencode.Validator on it
#    plant_id = UnicodeCol(notNull=True)
#
#
#    # Plant: Whole plant
#    # Seed/Spore: Seed or Spore
#    # Vegetative Part: Vegetative Part
#    # Tissue Culture: Tissue culture
#    # Other: Other, probably see notes for more information
#    # None: no information, unknown
#    acc_type = EnumCol(enumValues=('Plant', 'Seed/Spore', 'Vegetative Part', 
#                                   'Tissue Culture', 'Other', None),
#                       default=None)
#                          
#    # Accession Status
#    # Living accession: Current accession in living collection
#    # Dead: Noncurrent accession due to Death
#    # Transfered: Noncurrent accession due to Transfer
#    # Stored in dormant state: Stored in dormant state
#    # Other: Other, possible see notes for more information
#    # None: no information, unknown)
#    acc_status = EnumCol(enumValues=('Living accession', 'Dead', 'Transfered', 
#                                     'Stored in dormant state', 'Other', None),
#                         default=None)
#    
#    notes = UnicodeCol(default=None)
#
#    # indices
#    #
#    id_index = DatabaseIndex('plant_id', 'accession', unique=True)
#    
#    # foreign key
#    # 
#    accession = ForeignKey('Accession', notNull=True, cascade=False)
#    
#    # TODO: change the "location" field to "site" and then add specific 
#    # locations fields like geographic coordinates
#    location = ForeignKey("Location", notNull=True, cascade=False)
#    
#    # joins
#    #
#    history = MultipleJoin('PlantHistory', joinColumn='plant_id')
#    
#
#    def __str__(self): 
#        return "%s.%s" % (self.accession, self.plant_id)
#    
#    
#    def markup(self):
#        #return "%s.%s" % (self.accession, self.plant_id)
#        # FIXME: this makes expanding accessions look ugly with too many
#        # plant names around but makes expanding the location essential
#        # or you don't know what plants you are looking at
#        return "%s.%s (%s)" % (self.accession, self.plant_id, 
#                               self.accession.species.markup())
    
#
# Plant editor
#
#class PlantEditor(TreeViewEditorDialog):
#
#    visible_columns_pref = "editor.plant.columns"
#    column_width_pref = "editor.plant.column_width"
#    default_visible_list = ['accession', 'plant_id'] 
#
#    label = 'Plants\\Clones'
#
#    def __init__(self, parent=None, select=None, defaults={}, **kwargs):
#        TreeViewEditorDialog.__init__(self, Plant, "Plants/Clones Editor", 
#                                      parent, select=select, defaults=defaults,
#                                      **kwargs)
#        # set headers
#        titles = {'plant_id': 'Plant ID',
#                   'accessionID': 'Accession ID',
#                   'locationID': 'Location',
#                   'acc_type': 'Accession Type',
#                   'acc_status': 'Accession Status',
#                   'notes': 'Notes'
#                   }
#        self.columns.titles = titles
#        self.columns['accessionID'].meta.get_completions = \
#            self.get_accession_completions
#        self.columns['locationID'].meta.get_completions = \
#            self.get_location_completions
#
#
#    def start(self, commit_transaction=True):
#        '''
#        '''
#        accessions = tables["Accession"].select()
#        if accessions.count() < 1:
#            msg = "You can't add plants/clones to the database without first " \
#                  "adding accessions.\n" \
#                  "Would you like to add accessions now?"
#            if utils.yes_no_dialog(msg):
#                acc_editor = editors["AccessionEditor"]()
#                acc_editor.start() # use the same transaction but commit
#                    
#        accessions = tables["Accession"].select()
#        if accessions.count() < 1:   # no accessions were added
#            return
#        
#        locations = tables["Location"].select()
#        # keep location committed b/c locations.select might return 1 since
#        # the location is just in the cache
#        loc_committed = [] 
#        if locations.count() < 1:
#            msg = "You are trying to add plants to the database but no " \
#                  "locations exists.\n" \
#                  "Would you like to add some locations now?"
#            if utils.yes_no_dialog(msg):
#                loc_editor = editors["LocationEditor"]()
#                loc_editor.start() # use the same transaction but commit
#        
#        locations = tables["Location"].select()
#        if locations.count() < 1:
#            return
#            
#        return super(PlantEditor, self).start(commit_transaction)
#
#
#    def get_accession_completions(self, text):
#        model = gtk.ListStore(str, object)
#        sr = tables["Accession"].select("acc_id LIKE '"+text+"%'")
#        for row in sr:
#            s = str(row) + " - " + str(row.species)
#            model.append([s, row])
#        return model
#            
#            
#    def get_location_completions(self, text):
#        model = gtk.ListStore(str, object)
#        sr = tables["Location"].select("site LIKE '" + text + "%'")
#        for row in sr:
#            model.append([str(row), row])
#        return model
        
        
#    # extending this so we can have different value that show for the completions
#    # than what is stored in the model on selection
#    def on_completion_match_selected(self, completion, model, iter, 
#                                     path, colname):
#        """
#        all foreign keys should use entry completion so you can't type in
#        values that don't already exists in the database, therefore, allthough
#        i don't like it the view.model.row is set here for foreign key columns
#        and in self.on_edited for other column types                
#        """
#        if colname == "accession":
#            name = model.get_value(iter, 1)
#            id = model.get_value(iter, 2)
#            model = self.view.get_model()
#            i = model.get_iter(path)
#            row = model.get_value(i, 0)
#            row[colname] = [id, name]
#        else:
#            name = model.get_value(iter, 0)
#            id = model.get_value(iter, 1)
#            model = self.view.get_model()
#            i = model.get_iter(path)
#            row = model.get_value(i, 0)
#            row[colname] = [id, name]

        
#    def get_completions(self, text, colname):
#        maxlen = -1
#        model = None        
#        if colname == "accession":
#            model = gtk.ListStore(str, str, int)
#            if len(text) > 2:
#                sr = tables["Accession"].select("acc_id LIKE '"+text+"%'")
#                for row in sr:
#                    s = str(row) + " - " + str(row.species)
#                    model.append([s, str(row), row.id])
#        elif colname == "location":
#            model = gtk.ListStore(str, int)
#            sr = tables["Location"].select()
#            for row in sr:
#                model.append([str(row), row.id])
#        return model, maxlen
        
        
try:
    import os
#    from xml.sax.saxutils import escape
    import bauble.paths as paths
    from bauble.plugins.searchview.infobox import InfoBox, InfoExpander
except ImportError:
    # TODO: this should probably be handled a bit more robustly
    class PlantInfoBox: 
        pass
else:
    
    class GeneralPlantExpander(InfoExpander):
        """
        general expander for the PlantInfoBox        
        """
        
        def __init__(self, widgets):
            '''
            '''
            InfoExpander.__init__(self, "General", widgets)
            general_box = self.widgets.general_box
            self.widgets.remove_parent(general_box)
            self.vbox.pack_start(general_box)
        
        
        def update(self, row):
            '''
            '''
            self.set_widget_value('name_data', 
                 '%s\n%s' % (row.accession.species.markup(True), str(row)))            
            self.set_widget_value('location_data',row.location.site)
            self.set_widget_value('status_data',
                             row.acc_status, False)
            self.set_widget_value('type_data',
                             row.acc_type, False)
#            utils.set_widget_value(self.glade_xml, 'name_data', 
#                 '%s\n%s' % (row.accession.species.markup(True), str(row)))            
#            utils.set_widget_value(self.glade_xml, 'location_data',row.location.site)
#            utils.set_widget_value(self.glade_xml, 'status_data',
#                             row.acc_status, False)
#            utils.set_widget_value(self.glade_xml, 'type_data',
#                             row.acc_type, False)
            
            
    class NotesExpander(InfoExpander):
        """
        the plants notes
        """
            
        def __init__(self, widgets):
            '''
            '''
            InfoExpander.__init__(self, "Notes", widgets)
            notes_box = self.widgets.notes_box
            self.widgets.remove_parent(notes_box)
            self.vbox.pack_start(notes_box)
        
        
        def update(self, row):
            '''
            '''
            self.set_widget_value('notes_data', row.notes)
        

    class PlantInfoBox(InfoBox):
        """
        an InfoBox for a Plants table row
        """
        
        def __init__(self):
            '''
            '''
            InfoBox.__init__(self)
            #loc = LocationExpander()
            #loc.set_expanded(True)
            glade_file = os.path.join(paths.lib_dir(), "plugins", "garden", "plant_infobox.glade")
            self.widgets = utils.GladeWidgets(glade_file)
            self.general = GeneralPlantExpander(self.widgets)
            self.add_expander(self.general)                    
            
            self.notes = NotesExpander(self.widgets)
            self.add_expander(self.notes)
            
        
        def update(self, row):
            '''
            '''
            # T.ODO: don't really need a location expander, could just
            # use a label in the general section
            #loc = self.get_expander("Location")
            #loc.update(row.location)
            self.general.update(row)
            
            if row.notes is None:
                self.notes.set_expanded(False)
                self.notes.set_sensitive(False)
            else:
                self.notes.set_expanded(True)
                self.notes.set_sensitive(True)
                self.notes.update(row)


from bauble.plugins.garden.accession import Accession
from bauble.plugins.garden.location import Location, LocationEditor
