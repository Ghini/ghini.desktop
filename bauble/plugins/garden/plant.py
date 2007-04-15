#
# plant.py
#
# Description:
#

import gtk, gobject
from sqlalchemy import *
from sqlalchemy.orm.session import object_session
from sqlalchemy.exceptions import SQLError
from bauble.i18n import *
from bauble.editor import *
import bauble.utils as utils
from bauble.utils.log import debug
from bauble.types import Enum

# TODO: do a magic attribute on plant_id that checks if a plant id
# already exists with the accession number, this probably won't work though
# sense the acc_id may not be set when setting the plant_id

# TODO: might be worthwhile to have a label or textview next to the location
# combo that shows the description of the currently selected location

def edit_callback(plant):
    e = PlantEditor(plant)
    return e.start() != None


def remove_callback(plant):
    s = '%s: %s' % (plant.__class__.__name__, str(plant))
    msg = _("Are you sure you want to remove %s?") % utils.xml_safe(s)
    if not utils.yes_no_dialog(msg):
        return
    try:
        session = create_session()
        obj = session.load(plant.__class__, plant.id)
        session.delete(obj)
        session.flush()
    except Exception, e:
        msg = _('Could not delete.\n\n%s') % utils.xml_safe(e)
        utils.message_details_dialog(msg, traceback.format_exc(),
                                     type=gtk.MESSAGE_ERROR)
    return True


plant_context_menu = [('Edit', edit_callback),
                      ('--', None),
                      ('Remove', remove_callback)]


def plant_markup_func(plant):
    '''
    '''
    if plant.accession.id_qual is None:
        sp_str = plant.accession.species.markup(authors=False)
    else:
        sp_str = '%s %s' % (plant.accession.species.markup(authors=False),
                            plant.accession.id_qual)
    if plant.acc_status == 'Dead':
        color = '<span foreground="#666666">%s</span>'
        return color % str(plant), sp_str
    else:
        return str(plant), sp_str


plant_history_table = Table('plant_history',
                            Column('id', Integer, primary_key=True),
                            Column('date', Date),
                            Column('description', Unicode),
                            Column('plant_id', Integer, ForeignKey('plant.id'),
                                   nullable=False),
                            Column('_created', DateTime(True),
                                   default=func.current_timestamp()),
                            Column('_last_updated', DateTime(True),
                                   default=func.current_timestamp(),
                                   onupdate=func.current_timestamp()))


class PlantHistory(bauble.BaubleMapper):
    def __str__(self):
        return '%s: %s' % (self.date, self.description)


'''

acc_type
------------
Plant: Whole plant
Seed/Spore: Seed or Spore
Vegetative Part: Vegetative Part
Tissue Culture: Tissue culture
Other: Other, probably see notes for more information
None: no information, unknown

acc_status
-------------
Living accession: Current accession in living collection
Dead: Noncurrent accession due to Death
Transfered: Noncurrent accession due to Transfer
Stored in dormant state: Stored in dormant state
Other: Other, possible see notes for more information
None: no information, unknown)
'''

plant_table = Table('plant',
                    Column('id', Integer, primary_key=True),
                    Column('code', Unicode(6), nullable=False),
                    Column('acc_type',
                           Enum(values=['Plant', 'Seed/Spore',
                                        'Vegetative Part',  'Tissue Culture',
                                        'Other', None], empty_to_none=True)),
                    Column('acc_status', Enum(values=['Living accession',
                                                      'Dead', 'Transferred',
                                                     'Stored in dormant state',
                                                      'Other', None],
                                              empty_to_none=True)),
                    Column('notes', Unicode),
                    Column('accession_id', Integer, ForeignKey('accession.id'),
                           nullable=False),
                    Column('location_id', Integer, ForeignKey('location.id'),
                           nullable=False),
                    Column('_created', DateTime(True),
                           default=func.current_timestamp()),
                    Column('_last_updated', DateTime(True),
                           default=func.current_timestamp(),
                           onupdate=func.current_timestamp()),
                    UniqueConstraint('code', 'accession_id',
                                     name='plant_index'))



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
        if sys.platform == 'win32':
            self.do_win32_fixes()


    def do_win32_fixes(self):
        # these width functions are copied from accession.py and could probably
        # go in the utils
        import pango
        def get_char_width(widget):
            context = widget.get_pango_context()
            font_metrics = context.get_metrics(context.get_font_description(),
                                               context.get_language())
            width = font_metrics.get_approximate_char_width()
            return pango.PIXELS(width)

        def width_func(widget, col, multiplier=1.3):
            return int(round(get_char_width(widget) * \
                             plant_table.c[col].type.length*multiplier))

        acc_type_combo = self.widgets.plant_acc_type_combo
        acc_type_combo.set_size_request(width_func(acc_type_combo, 'acc_type'),
                                        -1)
        acc_status_combo = self.widgets.plant_acc_status_combo
        acc_status_combo.set_size_request(width_func(acc_status_combo,
                                                     'acc_status'), -1)


    def save_state(self):
        pass


    def restore_state(self):
        pass


    def start(self):
        return self.dialog.run()


class ObjectIdValidator(object):#(validators.FancyValidator):

    def to_python(self, value, state):
        return value.id
#        try:
#
#        except:
#            raise validators.Invalid('expected a int in column %s, got %s '\
#                                     'instead' % (self.name, type(value)), value, state)

class PlantEditorPresenter(GenericEditorPresenter):


    widget_to_field_map = {'plant_code_entry': 'code',
                           'plant_acc_entry': 'accession',
                           'plant_loc_combo': 'location',
                           'plant_acc_type_combo': 'acc_type',
                           'plant_acc_status_combo': 'acc_status',
                           'plant_notes_textview': 'notes'}

    PROBLEM_DUPLICATE_PLANT_CODE = 5

    def __init__(self, model, view):
        '''
        @model: should be an instance of Plant class
        @view: should be an instance of PlantEditorView
        '''
        GenericEditorPresenter.__init__(self, ModelDecorator(model), view)
        self.session = object_session(model)
        self._original_accession_id = self.model.accession_id
        self._original_code = self.model.code

        # initialize widgets
        self.init_location_combo()
        self.init_enum_combo('plant_acc_status_combo', 'acc_status')
        self.init_enum_combo('plant_acc_type_combo', 'acc_type')

#        self.init_history_box()
        self.refresh_view() # put model values in view

        # set default values for acc_status and acc_type
        if self.model.id is None and self.model.acc_type is None:
            default_acc_type = 'Plant'
            self.view.set_widget_value('plant_acc_type_combo',default_acc_type)
            self.model._set('acc_type', default_acc_type, dirty=False)
        if self.model.id is None and self.model.acc_status is None:
            default_acc_status = 'Living accession'
            self.view.set_widget_value('plant_acc_status_combo',
                                       default_acc_status)
            self.model._set('acc_status', default_acc_status, dirty=False)


        # connect signals
        def acc_get_completions(text):
            return self.session.query(Accession).select(Accession.c.code.like('%s%%' % text))
        def format_acc(accession):
            return '%s (%s)' % (accession, accession.species)
        def set_in_model(self, field, value):
#            debug('set_in_model(%s, %s)' % (field, value))
            setattr(self.model, field, value)
        self.assign_completions_handler('plant_acc_entry', 'accession',
                                        acc_get_completions,
                                        set_func=set_in_model,
                                        format_func=format_acc)
        #self.assign_simple_handler('plant_code_entry', 'code', StringOrNoneValidator())
        # TODO: could probably replace this by just passing a valdator
        # to assign_simple_handler...UPDATE: but can the validator handle
        # adding a problem to the widget
        self.view.widgets.plant_code_entry.connect('insert-text',
                                               self.on_plant_code_entry_insert)
        self.view.widgets.plant_code_entry.connect('delete-text',
                                               self.on_plant_code_entry_delete)
        self.assign_simple_handler('plant_notes_textview', 'notes')
        self.assign_simple_handler('plant_loc_combo', 'location')#, ObjectIdValidator())
        self.assign_simple_handler('plant_acc_status_combo', 'acc_status',
                                   StringOrNoneValidator())
        self.assign_simple_handler('plant_acc_type_combo', 'acc_type',
                                   StringOrNoneValidator())

        self.view.widgets.plant_loc_add_button.connect('clicked',
                                                    self.on_loc_button_clicked,
                                                    'add')
        self.view.widgets.plant_loc_edit_button.connect('clicked',
                                                    self.on_loc_button_clicked,
                                                    'edit')
        self.init_change_notifier()


    def dirty(self):
        return self.model.dirty


    def on_plant_code_entry_insert(self, entry, new_text, new_text_length,
                                   position, data=None):
        entry_text = entry.get_text()
        cursor = entry.get_position()
        full_text = entry_text[:cursor] + new_text + entry_text[cursor:]
        self._set_plant_code_from_text(full_text)


    def on_plant_code_entry_delete(self, entry, start, end, data=None):
        text = entry.get_text()
        full_text = text[:start] + text[end:]
        self._set_plant_code_from_text(full_text)


    def _set_plant_code_from_text(self, text):
        count_plants = lambda acc_id, code: plant_table.select(and_(plant_table.c.accession_id==acc_id, plant_table.c.code==code)).alias('__dummy').count().scalar()
        # NOTE: we have to reference self.model.accession.id instead of
        # self.model.accession_id b/c setting the first doesn't set the second
        def problem():
            self.add_problem(self.PROBLEM_DUPLICATE_PLANT_CODE,
                             self.view.widgets.plant_code_entry)
            self.model.code = None

        if self._original_accession_id == self.model.accession.id:
            if not text == self._original_code \
                   and count_plants(self.model.accession.id, text) > 0:
                problem()
                return
        elif count_plants(self.model.accession.id, text) > 0:
            problem()
            return

        self.remove_problem(self.PROBLEM_DUPLICATE_PLANT_CODE,
                            self.view.widgets.plant_code_entry)
        if text is '':
            self.model.code = None
        else:
            self.model.code = text


    def init_change_notifier(self):
        '''
        for each widget register a signal handler to be notified when the
        value in the widget changes, that way we can do things like sensitize
        the ok button
        '''
        for field in self.widget_to_field_map.values():
            self.model.add_notifier(field, self.on_field_changed)


    def refresh_sensitivity(self):
        def set_accept_buttons_sensitive(sensitive):
            self.view.widgets.plant_ok_button.set_sensitive(sensitive)
            self.view.widgets.plant_next_button.set_sensitive(sensitive)
        sensitive = (self.model.accession is not None and \
                     self.model.code is not None and \
                     self.model.location is not None) and self.model.dirty
        set_accept_buttons_sensitive(sensitive)


    def on_field_changed(self, model, field):
#        debug('on field changed: %s = %s' % (field, getattr(model, field)))
        self.refresh_sensitivity()


    def on_loc_button_clicked(self, button, cmd=None):
        location = None
        combo = self.view.widgets.plant_loc_combo
        it = combo.get_active_iter()
        if it is not None:
            location = combo.get_model()[it][0]
        if cmd is 'edit':
            e = LocationEditor(location, parent=self.view.dialog)
        else:
            e = LocationEditor(parent=self.view.dialog)
        e.start()
        self.init_location_combo()

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

        locs = sorted([l for l in locations], key=utils.natsort_key)
        for loc in locs:
            model.append([loc])
        combo.set_model(model)
        # TODO: if len of location == 1 then set the first item as active,
        # we should probably just always set the first item as active


#    def init_acc_entry(self):
#        pass
#    def init_type_and_status_combo(self):
#        pass
#    def init_history_box(self):
#        pass

    def refresh_view(self):
        for widget, field in self.widget_to_field_map.iteritems():
#            if field is 'accession_id':
#                value = self.model.accession
#            elif field is 'location_id':
#                value = self.model.location
#            else:
            value = self.model[field]
            self.view.set_widget_value(widget, value)
        self.refresh_sensitivity()


    def start(self):
        return self.view.start()


class PlantEditor(GenericModelViewPresenterEditor):

    label = 'Plant'
    mnemonic_label = '_Plant'

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
            parent = bauble.gui.window
        self.parent = parent
        self._committed = []


    def handle_response(self, response):
        not_ok_msg = _('Are you sure you want to lose your changes?')
        if response == gtk.RESPONSE_OK or response in self.ok_responses:
#                debug('session dirty, committing')
            try:
                if self.presenter.dirty():
                    self.commit_changes()
                    self._committed.append(self.model)
            except SQLError, e:
                exc = traceback.format_exc()
                msg = _('Error committing changes.\n\n%s') % e.orig
                utils.message_details_dialog(msg, str(e), gtk.MESSAGE_ERROR)
                return False
            except Exception, e:
                msg = _('Unknown error when committing changes. See the '\
                      'details for more information.\n\n%s') \
                      % utils.xml_safe(e)
                debug(traceback.format_exc())
                utils.message_details_dialog(msg, traceback.format_exc(),
                                             gtk.MESSAGE_ERROR)
                return False
        elif self.presenter.dirty() and utils.yes_no_dialog(not_ok_msg) or not self.presenter.dirty():
            return True
        else:
            return False

#        # respond to responses
        more_committed = None
        if response == self.RESPONSE_NEXT:
            e = PlantEditor(Plant(accession=self.model.accession),
                            parent=self.parent)
            more_committed = e.start()

        if more_committed is not None:
            self._committed = [self._committed]
            if isinstance(more_committed, list):
                self._committed.extend(more_committed)
            else:
                self._committed.append(more_committed)

        return True


    def start(self):
        from bauble.plugins.garden.accession import Accession
        # TODO: should really open the accession and location editors here, and
        # ask 'Would you like to do that now?'
        if self.session.query(Accession).count() == 0:
            msg = 'You must first add or import at least one Accession into '\
                  'the database before you can add plants.\n\nWould you like '\
                  'to open the Accession editor?'
            if utils.yes_no_dialog(msg):
                from bauble.plugins.garden.accession import AccessionEditor
                e = AccessionEditor()
                return e.start()
        if self.session.query(Location).count() == 0:
            msg = 'You must first add or import at least one Location into '\
                  'the database before you can add species.\n\nWould you '\
                  'like to open the Location editor?'
            if utils.yes_no_dialog(msg):
               e = LocationEditor()
               return e.start()
        self.view = PlantEditorView(parent=self.parent)
        self.presenter = PlantEditorPresenter(self.model, self.view)

        # add quick response keys
        dialog = self.view.dialog
        self.attach_response(dialog, gtk.RESPONSE_OK, 'Return',
                             gtk.gdk.CONTROL_MASK)
        self.attach_response(dialog, self.RESPONSE_NEXT, 'n',
                             gtk.gdk.CONTROL_MASK)

        # set default focus
        if self.model.accession is None:
            self.view.widgets.plant_acc_entry.grab_focus()
        else:
            self.view.widgets.plant_code_entry.grab_focus()

        exc_msg = "Could not commit changes.\n"
        committed = None
        while True:
            response = self.presenter.start()
            self.view.save_state() # should view or presenter save state
            if self.handle_response(response):
                break

        self.session.close() # cleanup session
        return self._committed



import os
import bauble.paths as paths
from bauble.view  import InfoBox, InfoExpander

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
             '%s %s\n%s' % (row.accession.species.markup(True),
                            row.accession.id_qual or '', str(row)))
        self.set_widget_value('location_data',row.location.site)
        self.set_widget_value('status_data',
                         row.acc_status, False)
        self.set_widget_value('type_data',
                              row.acc_type, False)



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
        glade_file = os.path.join(paths.lib_dir(), "plugins", "garden",
                                  "plant_infobox.glade")
        self.widgets = utils.GladeWidgets(glade_file)
        self.general = GeneralPlantExpander(self.widgets)
        self.add_expander(self.general)

        self.notes = NotesExpander(self.widgets)
        self.add_expander(self.notes)


    def update(self, row):
        '''
        '''
        # TODO: don't really need a location expander, could just
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
