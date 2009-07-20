#
# plant.py
#
"""
Defines the plant table and handled editing plants
"""
import os
import sys
import traceback

import gtk
import gobject
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.orm.session import object_session
from sqlalchemy.exc import SQLError

import bauble.db as db
from bauble.error import check, CheckConditionError
from bauble.editor import *
import bauble.utils as utils
from bauble.utils.log import debug
import bauble.types as types
import bauble.meta as meta
from bauble.view import SearchStrategy, Action
from bauble.plugins.garden.location import Location, LocationEditor

# TODO: do a magic attribute on plant_id that checks if a plant id
# already exists with the accession number, this probably won't work
# though sense the acc_id may not be set when setting the plant_id

# TODO: might be worthwhile to have a label or textview next to the
# location combo that shows the description of the currently selected
# location

plant_delimiter_key = u'plant_delimiter'
default_plant_delimiter = u'.'


def edit_callback(plants):
    e = PlantEditor(model=plants[0])
    return e.start() != None


def remove_callback(plants):
    s = ', '.join([str(p) for p in plants])
    msg = _("Are you sure you want to remove the following plants?\n\n%s") \
        % utils.xml_safe_utf8(s)
    if not utils.yes_no_dialog(msg):
        return

    session = bauble.Session()
    for plant in plants:
        obj = session.query(Plant).get(plant.id)
        session.delete(obj)
    try:
        session.commit()
    except Exception, e:
        msg = _('Could not delete.\n\n%s') % utils.xml_safe_utf8(e)

        utils.message_details_dialog(msg, traceback.format_exc(),
                                     type=gtk.MESSAGE_ERROR)
    return True



edit_action = Action('plant_edit', ('_Edit'), callback=edit_callback,
                     accelerator='<ctrl>e')
remove_action = Action('plant_remove', ('_Remove'), callback=remove_callback,
                       accelerator='<delete>', multiselect=True)

plant_context_menu = [edit_action, remove_action]


def plant_markup_func(plant):
    '''
    '''
    sp_str = plant.accession.species_str(markup=True)
    if plant.acc_status == 'Dead':
        color = '<span foreground="#666666">%s</span>'
        return color % utils.xml_safe_utf8(plant), sp_str
    else:
        return utils.xml_safe_utf8(plant), sp_str



class PlantSearch(SearchStrategy):

    def __init__(self):
        super(PlantSearch, self).__init__()


    def search(self, text, session=None):
        if session is None:
            session = bauble.Session()
        delimiter = Plant.get_delimiter()
        if delimiter not in text:
            return []
        acc_code, plant_code = text.rsplit(delimiter, 1)
        query = session.query(Plant)
        from bauble.plugins.garden import Accession
        try:
            return query.join('accession').\
                filter(and_(Accession.code==acc_code, Plant.code==plant_code))
        except Exception, e:
            debug(e)
            return []



class PlantHistory(db.Base):
    __tablename__ = 'plant_history'
    _mapper_args__ = {'order_by': 'date'}
    date = Column(types.Date)
    description = Column(UnicodeText)
    plant_id = Column(Integer, ForeignKey('plant.id'), nullable=False)

    def __str__(self):
        return '%s: %s' % (self.date, self.description)



class Plant(db.Base):
    """
    :Table name: plant

    :Columns:
        *code*: :class:`sqlalchemy.types.Unicode`
            The plant code

        *acc_type*: :class:`bauble.types.Enum`
            The accession type

            Possible values:
                * Plant: Whole plant

                * Seed/Spore: Seed or Spore

                * Vegetative Part: Vegetative Part

                * Tissue Culture: Tissue culture

                * Other: Other, probably see notes for more information

                * None: no information, unknown

        *acc_status*: :class:`bauble.types.Enum`
            The accession status

            Possible values:
                * Living accession: Current accession in living collection

                * Dead: Noncurrent accession due to Death

                * Transfered: Noncurrent accession due to Transfer
                  Stored in dormant state: Stored in dormant state

                * Other: Other, possible see notes for more information

                * None: no information, unknown)

        *notes*: :class:`sqlalchemy.types.UnicodeText`
            Notes

        *accession_id*: :class:`sqlalchemy.types.ForeignKey`
            Required.

        *location_id*: :class:`sqlalchemy.types.ForeignKey`
            Required.

    :Properties:
        *accession*:
            The accession for this plant.
        *location*:
            The location for this plant.

    :Constraints:
        The combination of code and accession_id must be unique.
    """
    __tablename__ = 'plant'
    __table_args__ = (UniqueConstraint('code', 'accession_id'), {})
    __mapper_args__ = {'order_by': ['accession_id', 'plant.code']}

    # columns
    code = Column(Unicode(6), nullable=False)
    acc_type = Column(types.Enum(values=['Plant', 'Seed/Spore',
                                         'Vegetative Part', 'Tissue Culture',
                                         'Other', None]),
                      default=None)
    acc_status = Column(types.Enum(values=['Living accession', 'Dead',
                                           'Transferred',
                                           'Stored in dormant state', 'Other',
                                     None]),
                        default=None)
    notes = Column(UnicodeText)
    accession_id = Column(Integer, ForeignKey('accession.id'), nullable=False)
    location_id = Column(Integer, ForeignKey('location.id'), nullable=False)

    # relations
    history = relation('PlantHistory', backref='plant')


    _delimiter = None

    @classmethod
    def get_delimiter(cls, refresh=False):
        """
        Get the plant delimiter from the BaubleMeta table.

        The delimiter is cached the first time it is retrieved.  To refresh
        the delimiter from the database call with refresh=True.

        """
        if cls._delimiter is None or refresh:
            cls._delimiter = meta.get_default(plant_delimiter_key,
                                default_plant_delimiter).value
        return cls._delimiter

    def _get_delimiter(self):
        return Plant.get_delimiter()
    delimiter = property(lambda self: self._get_delimiter())


    def __str__(self):
        return "%s%s%s" % (self.accession, self.delimiter, self.code)


    def markup(self):
        #return "%s.%s" % (self.accession, self.plant_id)
        # FIXME: this makes expanding accessions look ugly with too many
        # plant names around but makes expanding the location essential
        # or you don't know what plants you are looking at
        return "%s%s%s (%s)" % (self.accession, self.delimiter, self.code,
                                self.accession.species_str(markup=True))


from bauble.plugins.garden.accession import Accession


class PlantEditorView(GenericEditorView):

    #source_expanded_pref = 'editor.accesssion.source.expanded'

    _tooltips = {
        'plant_code_entry': _('The plant code must be a unique code'),
        'plant_acc_entry': _('The accession must be selected from the list ' \
                             'of completions.  To add an accession use the '\
                             'Accession editor'),
        'plant_loc_entry': _('The location of the plant in your collection.'),
        'plant_acc_type_combo': _('The type of the plant material.\n\n' \
                                  'Possible values: %s') \
                                  % utils.enum_values_str('plant.acc_type'),
        'plant_acc_status_combo': _('The status of this plant in the ' \
                                    'collection.\nPossible values: %s') \
                                   % utils.enum_values_str('plant.acc_status'),
        'plant_notes_textview': _('Miscelleanous notes about this plant.'),
        }


    def __init__(self, parent=None):
        GenericEditorView.__init__(self, os.path.join(paths.lib_dir(),
                                                      'plugins', 'garden',
                                                      'plant_editor.glade'),
                                   parent=parent)
        self.dialog = self.widgets.plant_dialog
        self.dialog.set_transient_for(parent)
        self.connect_dialog_close(self.dialog)
        def acc_cell_data_func(column, renderer, model, iter, data=None):
            v = model[iter][0]
            renderer.set_property('text', '%s (%s)' % (str(v), str(v.species)))
        self.attach_completion('plant_acc_entry', acc_cell_data_func,
                               minimum_key_length=1)

        def loc_cell_data_func(col, renderer, model, it, data=None):
            v = model[it][0]
            renderer.set_property('text', '%s' % utils.utf8(v))
        self.attach_completion('plant_loc_entry', loc_cell_data_func,
                               minimum_key_length=1)

    def __del__(self):
        #debug('PlantView.__del__()')
        #GenericEditorView.__del__(self)
        self.dialog.destroy()


    def save_state(self):
        pass


    def restore_state(self):
        pass


    def start(self):
        return self.dialog.run()


class ObjectIdValidator(object):

    def to_python(self, value, state):
        return value.id


class PlantEditorPresenter(GenericEditorPresenter):


    widget_to_field_map = {'plant_code_entry': 'code',
                           'plant_acc_entry': 'accession',
                           'plant_loc_entry': 'location',
                           'plant_acc_type_combo': 'acc_type',
                           'plant_acc_status_combo': 'acc_status',
                           'plant_notes_textview': 'notes'}

    PROBLEM_DUPLICATE_PLANT_CODE = 5

    def __init__(self, model, view):
        '''
        @param model: should be an instance of Plant class
        @param view: should be an instance of PlantEditorView
        '''
        GenericEditorPresenter.__init__(self, model, view)
        self.session = object_session(model)
        self._original_accession_id = self.model.accession_id
        self._original_code = self.model.code
        self.__dirty = False

        # initialize widgets
        self.init_enum_combo('plant_acc_status_combo', 'acc_status')
        self.init_enum_combo('plant_acc_type_combo', 'acc_type')

#        self.init_history_box()

        # set default values for acc_status and acc_type
        if self.model.id is None and self.model.acc_type is None:
            default_acc_type = unicode('Plant')
            self.model.acc_type = default_acc_type
        if self.model.id is None and self.model.acc_status is None:
            default_acc_status = unicode('Living accession')
            self.model.acc_status = default_acc_status

        self.refresh_view() # put model values in view

        # connect signals
        def acc_get_completions(text):
            query = self.session.query(Accession)
            return query.filter(Accession.code.like(unicode('%s%%' % text)))

        def on_select(value):
            self.set_model_attr('accession', value)
            # reset the plant code to check that this is a valid code for the
            # new accession, fixes bug #103946
            if value is not None:
                self.on_plant_code_entry_changed()
        self.assign_completions_handler('plant_acc_entry', acc_get_completions,
                                        on_select=on_select)

        self.view.connect('plant_code_entry', 'changed',
                          self.on_plant_code_entry_changed)
        self.assign_simple_handler('plant_notes_textview', 'notes',
                                   UnicodeOrNoneValidator())

        def loc_get_completions(text):
            query = self.session.query(Location)
            return query.filter(utils.ilike(Location.site,
                                            utils.utf8('%s%%' % text)))
        def on_loc_select(value):
            self.set_model_attr('location', value)
        self.assign_completions_handler('plant_loc_entry', loc_get_completions,
                                        on_select=on_loc_select)

        self.assign_simple_handler('plant_acc_status_combo', 'acc_status',
                                   UnicodeOrNoneValidator())
        self.assign_simple_handler('plant_acc_type_combo', 'acc_type',
                                   UnicodeOrNoneValidator())

        self.view.connect('plant_loc_add_button', 'clicked',
                          self.on_loc_button_clicked, 'add')
        self.view.connect('plant_loc_edit_button', 'clicked',
                          self.on_loc_button_clicked, 'edit')


    def dirty(self):
        return self.__dirty


    def on_plant_code_entry_changed(self, *args):
        """
        Validates the accession number and the plant code from the editors.
        """
        text = utils.utf8(self.view.widgets.plant_code_entry.get_text())
        if text == u'':
            self.set_model_attr('code', None)
        else:
            self.set_model_attr('code', text)

        if self.model.accession is None:
            self.remove_problem(self.PROBLEM_DUPLICATE_PLANT_CODE,
                                self.view.widgets.plant_code_entry)
            self.refresh_sensitivity()
            return

        # add a problem if the code is not unique but not if its the
        # same accession and plant code that we started with when the
        # editor was opened
        if self.model.code is not None and not \
                self.is_code_unique(self.model.code) and not \
                (self._original_accession_id==self.model.accession.id and \
                     self.model.code==self._original_code):

                self.add_problem(self.PROBLEM_DUPLICATE_PLANT_CODE,
                                 self.view.widgets.plant_code_entry)
        else:
            # remove_problem() won't complain if problem doesn't exist
            self.remove_problem(self.PROBLEM_DUPLICATE_PLANT_CODE,
                                self.view.widgets.plant_code_entry)

            # if there are no problems and the code represents a range
            # then change the background color to a light blue
            from bauble.utils.pyparsing import ParseException
            if len(utils.range_builder(self.model.code)) > 1:
                entry = self.view.widgets.plant_code_entry
                color_str = '#B0C4DE' # light steel blue
                color = gtk.gdk.color_parse(color_str)
                entry.modify_bg(gtk.STATE_NORMAL, color)
                entry.modify_base(gtk.STATE_NORMAL, color)
                entry.queue_draw()

        self.refresh_sensitivity()


    def is_code_unique(self, code):
        """
        Return True/False if the code is unique for the current
        Accession on self.model.accession.

        This method will take range values for code that can be passed
        to utils.range_builder()
        """
        for code in utils.range_builder(self.model.code):
            # reference accesssion.id instead of accession_id since
            # setting the accession on the model doesn't set the
            # accession_id until the session is flushed
            num = self.session.query(Plant).join('accession').\
                filter(and_(Accession.id==self.model.accession.id,
                            Plant.code==code)).count()
            if num > 0:
                return False
        return True


    def refresh_sensitivity(self):
        #debug('refresh_sensitivity()')
        sensitive = (self.model.accession is not None and \
                     self.model.code is not None and \
                     self.model.location is not None) \
                     and self.dirty() and len(self.problems)==0
        self.view.widgets.plant_ok_button.set_sensitive(sensitive)
        self.view.widgets.plant_next_button.set_sensitive(sensitive)


    def set_model_attr(self, field, value, validator=None):
        #debug('set_model_attr(%s, %s)' % (field, value))
        super(PlantEditorPresenter, self)\
            .set_model_attr(field, value, validator)
        self.__dirty = True
        self.refresh_sensitivity()


    def on_loc_button_clicked(self, button, cmd=None):
        location = self.model.location
        if cmd is 'edit':
            entry = self.view.widgets.plant_loc_entry
            LocationEditor(location, parent=self.view.dialog).start()
            self.session.refresh(location)
            self.pause_completions_handler(entry, True)
            entry.set_text(utils.utf8(location))
            self.pause_completions_handler(entry, False)
        else:
            # TODO: see if the location editor returns the new
            # location and if so set it directly
            LocationEditor(parent=self.view.dialog).start()


    def refresh_view(self):
        for widget, field in self.widget_to_field_map.iteritems():
            value = getattr(self.model, field)
            self.view.set_widget_value(widget, value)
        self.refresh_sensitivity()


    def start(self):
        r = self.view.start()
        self.view.disconnect_all()
        return r



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
        if not parent and bauble.gui:
            parent = bauble.gui.window
        self.parent = parent
        self._committed = []


    def commit_changes(self):
        """
        """
        if ',' not in self.model.code and '-' not in self.model.code and \
                self.model not in self.session.new:
            self._committed.append(self.model)
            super(PlantEditor, self).commit_changes()
            return

        plants = []
        codes = utils.range_builder(self.model.code)
        mapper = object_mapper(self.model)
        for code in codes:
            new_plant = Plant()
            self.session.add(new_plant)
            for prop in mapper.iterate_properties:
                setattr(new_plant, prop.key, getattr(self.model, prop.key))
            new_plant.code = utils.utf8(code)
            new_plant.id = None
            new_plant._created = None
            new_plant._last_updated = None
            plants.append(new_plant)
        try:
            self.session.expunge(self.model)
            super(PlantEditor, self).commit_changes()
        except:
            self.session.add(self.model)
            raise
        self._committed.extend(plants)



    def handle_response(self, response):
        not_ok_msg = _('Are you sure you want to lose your changes?')
        if response == gtk.RESPONSE_OK or response in self.ok_responses:
#                debug('session dirty, committing')
            try:
                if self.presenter.dirty():
                    # commit_changes() will append the commited plants
                    # to self._committed
                    self.commit_changes()
            except SQLError, e:
                exc = traceback.format_exc()
                msg = _('Error committing changes.\n\n%s') % e.orig
                utils.message_details_dialog(msg, str(e), gtk.MESSAGE_ERROR)
                self.session.rollback()
                return False
            except Exception, e:
                msg = _('Unknown error when committing changes. See the '\
                      'details for more information.\n\n%s') \
                      % utils.xml_safe_utf8(e)
                debug(traceback.format_exc())
                utils.message_details_dialog(msg, traceback.format_exc(),
                                             gtk.MESSAGE_ERROR)
                self.session.rollback()
                return False
        elif self.presenter.dirty() and utils.yes_no_dialog(not_ok_msg) \
                or not self.presenter.dirty():
            self.session.rollback()
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
        view = PlantEditorView(parent=self.parent)
        self.presenter = PlantEditorPresenter(self.model, view)

        # add quick response keys
        self.attach_response(view.dialog, gtk.RESPONSE_OK, 'Return',
                             gtk.gdk.CONTROL_MASK)
        self.attach_response(view.dialog, self.RESPONSE_NEXT, 'n',
                             gtk.gdk.CONTROL_MASK)

        # set default focus
        if self.model.accession is None:
            view.widgets.plant_acc_entry.grab_focus()
        else:
            view.widgets.plant_code_entry.grab_focus()

        while True:
            response = self.presenter.start()
            view.save_state() # should view or presenter save state
            if self.handle_response(response):
                break

        self.session.close() # cleanup session
        return self._committed



import os
import bauble.paths as paths
from bauble.view  import InfoBox, InfoExpander, PropertiesExpander, \
     select_in_search_results


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
        self.current_obj = None

        def on_acc_code_clicked(*args):
            select_in_search_results(self.current_obj.accession)
        utils.make_label_clickable(self.widgets.acc_code_data,
                                   on_acc_code_clicked)

        def on_species_clicked(*args):
            select_in_search_results(self.current_obj.accession.species)
        utils.make_label_clickable(self.widgets.name_data, on_species_clicked)

        def on_location_clicked(*args):
            select_in_search_results(self.current_obj.location)
        utils.make_label_clickable(self.widgets.location_data,
                                   on_location_clicked)


    def update(self, row):
        '''
        '''
        self.current_obj = row
        acc_code = str(row.accession)
        plant_code = str(row)
        head, tail = plant_code[:len(acc_code)], plant_code[len(acc_code):]

        self.set_widget_value('acc_code_data', '<big>%s</big>' % \
                                                utils.xml_safe(unicode(head)))
        self.set_widget_value('plant_code_data', '<big>%s</big>' % \
                              utils.xml_safe(unicode(tail)))
        self.set_widget_value('name_data',
                              row.accession.species_str(markup=True))
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
        filename = os.path.join(paths.lib_dir(), "plugins", "garden",
                                "plant_infobox.glade")
        builder = utils.BuilderLoader.load(filename)
        self.widgets = utils.BuilderWidgets(builder)
        self.general = GeneralPlantExpander(self.widgets)
        self.add_expander(self.general)
        self.notes = NotesExpander(self.widgets)
        self.add_expander(self.notes)
        self.props = PropertiesExpander()
        self.add_expander(self.props)


    def update(self, row):
        '''
        '''
        # TODO: don't really need a location expander, could just
        # use a label in the general section
        #loc = self.get_expander("Location")
        #loc.update(row.location)
        self.general.update(row)
        self.props.update(row)

        if row.notes is None:
            self.notes.set_expanded(False)
            self.notes.set_sensitive(False)
        else:
            self.notes.set_expanded(True)
            self.notes.set_sensitive(True)
            self.notes.update(row)


from bauble.plugins.garden.accession import Accession
#from bauble.plugins.garden.location import Location, LocationEditor
