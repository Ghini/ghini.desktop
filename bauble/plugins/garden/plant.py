#
# plant.py
#
"""
Defines the plant table and handled editing plants
"""
import datetime
import itertools
import os
import sys
import traceback
from random import random

import gtk
import gobject
import pango
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.orm.session import object_session
from sqlalchemy.exc import SQLError

import bauble.db as db
from bauble.error import check, CheckConditionError
from bauble.editor import *
import bauble.meta as meta
import bauble.paths as paths
from bauble.plugins.garden.location import Location, LocationEditor
from bauble.plugins.garden.propagation import PlantPropagation
import bauble.types as types
import bauble.utils as utils
from bauble.utils.log import debug
from bauble.view import InfoBox, InfoExpander, PropertiesExpander, \
    select_in_search_results, SearchStrategy, Action
import bauble.view as view


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


def branch_callback(plants):
    plant = plants[0].duplicate()
    plant.code = None
    e = PlantEditor(model=plant)
    return e.start() != None


def remove_callback(plants):
    s = ', '.join([str(p) for p in plants])
    msg = _("Are you sure you want to remove the following plants?\n\n%s") \
        % utils.xml_safe_utf8(s)
    if not utils.yes_no_dialog(msg):
        return

    session = db.Session()
    for plant in plants:
        obj = session.query(Plant).get(plant.id)
        session.delete(obj)
    try:
        session.commit()
    except Exception, e:
        msg = _('Could not delete.\n\n%s') % utils.xml_safe_utf8(e)

        utils.message_details_dialog(msg, traceback.format_exc(),
                                     type=gtk.MESSAGE_ERROR)
    finally:
        session.close()
    return True



edit_action = Action('plant_edit', _('_Edit'), callback=edit_callback,
                     accelerator='<ctrl>e', multiselect=True)

branch_action = Action('plant_branch', _('_Branch'), callback=branch_callback,
                       accelerator='<ctrl>b')

remove_action = Action('plant_remove', _('_Delete'), callback=remove_callback,
                       accelerator='<ctrl>Delete', multiselect=True)

plant_context_menu = [edit_action, branch_action, remove_action]


def plant_markup_func(plant):
    '''
    '''
    sp_str = plant.accession.species_str(markup=True)
    #dead_color = "#777"
    dead_color = "#9900ff"
    if plant.quantity <= 0:
        dead_markup = '<span foreground="%s">%s</span>' % \
            (dead_color, utils.xml_safe_utf8(plant))
        return dead_markup, sp_str
    else:
        return utils.xml_safe_utf8(plant), sp_str


def get_next_code(acc):
    """
    Return the next available plant code for an accession.

    This function should be specific to the institution.

    If there is an error getting the next code the None is returned.
    """
    # auto generate/increment the accession code
    session = db.Session()
    codes = session.query(Plant.code).join(Accession).\
        filter(Accession.id==acc.id).all()
    next = 1
    if codes:
        try:
            next = max([int(code[0]) for code in codes])+1
        except Exception, e:
            return None
    return utils.utf8(next)


def is_code_unique(plant, code):
    """
    Return True/False if the code is a unique Plant code for accession.

    This method will also take range values for code that can be passed
    to utils.range_builder()
    """
    # TODO: this assumes that codes are integers and could probably
    # use some more testing, e.g. for 0001 and 1
    codes = map(utils.utf8, utils.range_builder(code))
    codes.append(utils.utf8(code))
    # reference accesssion.id instead of accession_id since
    # setting the accession on the model doesn't set the
    # accession_id until the session is flushed
    session = db.Session()
    count = session.query(Plant).join('accession').\
        filter(and_(Accession.id==plant.accession.id,
                    Plant.code.in_(codes))).count()
    session.close()
    return count == 0


class PlantSearch(SearchStrategy):

    def __init__(self):
        super(PlantSearch, self).__init__()


    def search(self, text, session):
        # TODO: this doesn't support search like plant=2009.0039.1 or
        # plant where accession.code=2009.0039

        # TODO: searches like 2009.0039.% or * would be handy
        r1 = super(PlantSearch, self).search(text, session)
        delimiter = Plant.get_delimiter()
        if delimiter not in text:
            return []
        acc_code, plant_code = text.rsplit(delimiter, 1)
        query = session.query(Plant)
        from bauble.plugins.garden import Accession
        try:
            q = query.join('accession').\
                filter(and_(Accession.code==acc_code, Plant.code==plant_code))
        except Exception, e:
            debug(e)
            return []
        return q.all()



# TODO: what would happend if the PlantRemove.plant_id and
# PlantNote.plant_id were out of sink....how could we avoid these sort
# of cycles
class PlantNote(db.Base):
    __tablename__ = 'plant_note'
    __mapper_args__ = {'order_by': 'plant_note.date'}

    date = Column(types.Date, nullable=False)
    user = Column(Unicode(64))
    category = Column(Unicode(32))
    note = Column(UnicodeText, nullable=False)
    plant_id = Column(Integer, ForeignKey('plant.id'), nullable=False)
    plant = relation('Plant', uselist=False,
                      backref=backref('notes', cascade='all, delete-orphan'))


change_reasons = {
    u'DEAD': _('Dead'),
    u'DISC': _('Discarded'),
    u'DISW': _('Discarded, weedy'),
    u'LOST': _('Lost, whereabouts unknown'),
    u'STOL': _('Stolen'),
    u'WINK': _('Winter kill'),
    u'ERRO': _('Error correction'),
    u'DIST': _('Distributed elsewhere'),
    u'DELE': _('Deleted, yr. dead. unknown'),
    u'ASS#': _('Transferred to another acc.no.'),
    u'FOGS': _('Given to FOGs to sell'),
    u'PLOP': _('Area transf. to Plant Ops.'),
    u'BA40': _('Given to Back 40 (FOGs)'),
    u'TOTM': _('Transfered to Totem Field'),
    U'SUMK': _('Summer Kill'),
    u'DNGM': _('Did not germinate'),
    u'DISN': _('Discarded seedling in nursery'),
    u'GIVE': _('Given away (specify person)'),
    u'OTHR': _('Other'),
    None: ''
    }


class PlantChange(db.Base):
    """
    """
    __tablename__ = 'plant_change'
    __mapper_args__ = {'order_by': 'plant_change.date'}

    plant_id = Column(Integer, ForeignKey('plant.id'), nullable=False)

    # - if to_location_id is None changeis a removal
    # - if from_location_id is None then this change is a creation
    # - if to_location_id != from_location_id change is a transfer
    from_location_id = Column(Integer, ForeignKey('location.id'))
    to_location_id = Column(Integer, ForeignKey('location.id'))

    # the name of the person who made the change
    person = Column(Unicode(64))
    """The name of the person who made the change"""
    quantity = Column(Integer, autoincrement=False, nullable=False)
    note_id = Column(Integer, ForeignKey('plant_note.id'))

    reason = Column(types.Enum(values=change_reasons.keys()))

    # date of change
    date = Column(types.DateTime, default=func.now())

    # relations
    plant = relation('Plant', uselist=False,
                     backref=backref('changes',cascade='all, delete-orphan'))
    from_location = relation('Location',
                   primaryjoin='PlantChange.from_location_id == Location.id')
    to_location = relation('Location',
                   primaryjoin='PlantChange.to_location_id == Location.id')


status_values = {u'Healthy': _('Healthy'),
                 u'Very Poor Condition': _('Very Poor Condition'),
                 u'Dead': _('Dead')}

class PlantStatus(db.Base):
    """
    date: date checked
    status: status of plant
    comment: comments on check up
    checked_by: person who did the check
    """
    date = Column(types.Date, default=func.now())
    status = Column(types.Enum(values=status_values.keys()))
    comment = Column(UnicodeText)
    checked_by = Column(Unicode(64))


acc_type_values = {u'Plant': _('Plant'),
                   u'Seed': _('Seed/Spore'),
                   u'Vegetative': _('Vegetative Part'),
                   u'Tissue': _('Tissue Culture'),
                   u'Other': _('Other'),
                   None: ''}


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

        *accession_id*: :class:`sqlalchemy.types.ForeignKey`
            Required.

        *location_id*: :class:`sqlalchemy.types.ForeignKey`
            Required.

    :Properties:
        *accession*:
            The accession for this plant.
        *location*:
            The location for this plant.
        *notes*:
            Thoe notes for this plant.

    :Constraints:
        The combination of code and accession_id must be unique.
    """
    __tablename__ = 'plant'
    __table_args__ = (UniqueConstraint('code', 'accession_id'), {})
    __mapper_args__ = {'order_by': ['plant.accession_id', 'plant.code']}

    # columns
    code = Column(Unicode(6), nullable=False)
    acc_type = Column(types.Enum(values=acc_type_values.keys()), default=None)
    memorial = Column(Boolean, default=False)
    quantity = Column(Integer, autoincrement=False, nullable=False)

    # UBC: date_accd, date_recvd and operator were used in BGAS but
    # they aren't really relevant here, i've just added them so we
    # don't lose the data when converting from BGAS->Bauble...we don't
    # provide any interface for changing the values
    date_accd = Column(types.Date)
    date_recvd = Column(types.Date)
    operator = Column(Unicode(3))

    accession_id = Column(Integer, ForeignKey('accession.id'), nullable=False)
    location_id = Column(Integer, ForeignKey('location.id'), nullable=False)

    propagations = relation('Propagation', cascade='all, delete-orphan',
                            single_parent=True,
                            secondary=PlantPropagation.__table__,
                            backref=backref('plant', uselist=False))

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


    def duplicate(self, code=None, session=None):
        """
        Return a Plant that is a duplicate of this Plant with attached
        notes, changes and propagations.
        """
        if not session:
            session = object_session(self)
        plant = Plant()
        session.add(plant)

        ignore = ('id', 'changes', 'notes', 'propagations')
        properties = filter(lambda p: p.key not in ignore,
                            object_mapper(self).iterate_properties)
        for prop in properties:
            setattr(plant, prop.key, getattr(self, prop.key))
        plant.code = code

        # duplicate notes
        for note in self.notes:
            new_note = PlantNote()
            for prop in object_mapper(note).iterate_properties:
                setattr(new_note, prop.key, getattr(note, prop.key))
            new_note.id = None
            new_note.plant = plant

        # duplicate changes
        for change in self.changes:
            new_change = PlantChange()
            for prop in object_mapper(change).iterate_properties:
                setattr(new_change, prop.key, getattr(change, prop.key))
            new_change.id = None
            new_change.plant = plant

        # duplicate propagations
        for propagation in self.propagations:
            new_propagation = PlantPropagation()
            for prop in object_mapper(propagation).iterate_properties:
                setattr(new_propagation, prop.key,
                        getattr(propagation, prop.key))
            new_propagation.id = None
            new_propagation.plant = plant

        return plant


    def markup(self):
        #return "%s.%s" % (self.accession, self.plant_id)
        # FIXME: this makes expanding accessions look ugly with too many
        # plant names around but makes expanding the location essential
        # or you don't know what plants you are looking at
        return "%s%s%s (%s)" % (self.accession, self.delimiter, self.code,
                                self.accession.species_str(markup=True))


from bauble.plugins.garden.accession import Accession


class PlantEditorView(GenericEditorView):

    _tooltips = {
        'plant_code_entry': _('The plant code must be a unique code for '\
                                  'the accession.  You may also use ranges '\
                                  'like 1,2,7 or 1-3 to create multiple '\
                                  'plants.'),
        'plant_acc_entry': _('The accession must be selected from the list ' \
                             'of completions.  To add an accession use the '\
                             'Accession editor.'),
        'plant_loc_comboentry': _('The location of the plant in your '\
                                      'collection.'),
        'plant_acc_type_combo': _('The type of the plant material.\n\n' \
                                  'Possible values: %s') % \
                                  ', '.join(acc_type_values.values()),
        'plant_loc_add_button': _('Create a new location.'),
        'plant_loc_add_button': _('Edit the selected location.'),
        'prop_add_button': _('Create a new propagation record for this plant.'),
        'pad_cancel_button': _('Cancel your changes.'),
        'pad_ok_button': _('Save your changes.'),
        'pad_next_button': _('Save your changes changes and add another '
                             'plant.')
        }


    def __init__(self, parent=None):
        glade_file = os.path.join(paths.lib_dir(), 'plugins', 'garden',
                                  'plant_editor.glade')
        super(PlantEditorView, self).__init__(glade_file, parent=parent)
        self.widgets.pad_ok_button.set_sensitive(False)
        self.widgets.pad_next_button.set_sensitive(False)
        def acc_cell_data_func(column, renderer, model, treeiter, data=None):
            v = model[treeiter][0]
            renderer.set_property('text', '%s (%s)' % (str(v), str(v.species)))
        self.attach_completion('plant_acc_entry', acc_cell_data_func,
                               minimum_key_length=1)
        self.init_translatable_combo('plant_acc_type_combo', acc_type_values)
        self.init_translatable_combo('reason_combo', change_reasons)
        utils.setup_date_button(self, 'plant_date_entry', 'plant_date_button')
        self.widgets.plant_notebook.set_current_page(0)


    def get_window(self):
        return self.widgets.plant_editor_dialog


    def save_state(self):
        pass


    def restore_state(self):
        pass


    def start(self):
        return self.get_window().run()



class PlantEditorPresenter(GenericEditorPresenter):


    widget_to_field_map = {'plant_code_entry': 'code',
                           'plant_acc_entry': 'accession',
                           'plant_loc_comboentry': 'location',
                           'plant_acc_type_combo': 'acc_type',
                           'plant_memorial_check': 'memorial',
                           'plant_quantity_entry': 'quantity'
                           }

    PROBLEM_DUPLICATE_PLANT_CODE = str(random())

    def __init__(self, model, view):
        '''
        @param model: should be an instance of Plant class
        @param view: should be an instance of PlantEditorView
        '''
        super(PlantEditorPresenter, self).__init__(model, view)
        self.session = object_session(model)
        self._original_accession_id = self.model.accession_id
        self._original_code = self.model.code
        self._original_quantity = self.model.quantity
        self.__dirty = False

        # set default values for acc_type
        if self.model.id is None and self.model.acc_type is None:
            self.model.acc_type = u'Plant'

        notes_parent = self.view.widgets.notes_parent_box
        notes_parent.foreach(notes_parent.remove)
        self.notes_presenter = NotesPresenter(self, 'notes', notes_parent)
        from bauble.plugins.garden.propagation import PropagationTabPresenter
        self.prop_presenter = PropagationTabPresenter(self, self.model,
                                                     self.view, self.session)

        # if the PlantEditor has been started with a new plant but
        # the plant is already associated with an accession
        if self.model.accession and not self.model.code:
            code = get_next_code(self.model.accession)
            if code:
                # if get_next_code() returns None then there was an error
                self.set_model_attr('code', code)

        def _changes_data_func(column, cell, model, treeiter, prop):
            change = model[treeiter][1]
            if prop == 'reason' and change.reason:
                value = change_reasons[change.reason]
            elif prop == 'quantity' and change.quantity < 0:
                value = -change.quantity
            else:
                value = getattr(change, prop)
            cell.set_property('text', value)

        tree = self.view.widgets.plant_changes_treeview
        def setup_column(column, cell, prop):
            column = self.view.widgets[column]
            cell = self.view.widgets[cell]
            column.set_cell_data_func(cell, _changes_data_func, prop)

        setup_column('changes_date_column', 'changes_date_cell', 'date')
        setup_column('changes_from_column', 'changes_from_cell','from_location')
        setup_column('changes_to_column', 'changes_to_cell', 'to_location')
        setup_column('changes_quantity_column', 'changes_quantity_cell',
                     'quantity')
        setup_column('changes_reason_column', 'changes_reason_cell',
                     'reason')
        setup_column('changes_user_column', 'changes_user_cell', 'person')

        self.view.widgets.changes_change_column.\
            add_attribute(self.view.widgets.changes_change_cell, 'text', 0)

        model = gtk.ListStore(str, object)
        prev_quantity = 0
        for change in sorted(self.model.changes, key=lambda x: x.date):
            action = _('Nothing')
            if not change.from_location:
                action = _('Created')
                prev_quantity += change.quantity
            if change.quantity < 0:
                action = _('Removal')
            elif not change.to_location and change.quantity > 0:
                action = _('Addition')
            elif change.from_location != change.to_location:
                prev_quantity = change.quantity
                action = _('Transfer')
            model.insert(0, [action, change])
        self.view.widgets.plant_changes_treeview.set_model(model)
        self.refresh_view() # put model values in view

        self.change = PlantChange()
        self.change.plant = self.model
        self.change.from_location = self.model.location

        def on_reason_changed(combo):
            it = combo.get_active_iter()
            debug(combo.get_model()[it][0])
            self.change.reason = combo.get_model()[it][0]

        sensitive = False
        if self.model not in self.session.new:
            self.view.connect(self.view.widgets.reason_combo, 'changed',
                              on_reason_changed)
            sensitive = True
        self.view.widgets.reason_combo.props.sensitive = sensitive
        self.view.widgets.reason_label.props.sensitive = sensitive

        self.view.connect('plant_date_entry', 'changed',
                          self.on_date_entry_changed)

        def on_location_select(location):
            self.set_model_attr('location', location)
            if self.change.quantity is None:
                self.change.quantity = self.model.quantity
        from bauble.plugins.garden import init_location_comboentry
        init_location_comboentry(self, self.view.widgets.plant_loc_comboentry,
                                 on_location_select)

        # assign signal handlers to monitor changes now that the view has
        # been filled in
        def acc_get_completions(text):
            query = self.session.query(Accession)
            return query.filter(Accession.code.like(unicode('%s%%' % text)))

        def on_select(value):
            self.set_model_attr('accession', value)
            # reset the plant code to check that this is a valid code for the
            # new accession, fixes bug #103946
            if value is not None:
                self.view.widgets.plant_code_entry.emit('changed')
        self.assign_completions_handler('plant_acc_entry', acc_get_completions,
                                        on_select=on_select)

        self.view.connect('plant_code_entry', 'changed',
                          self.on_plant_code_entry_changed)

        self.assign_simple_handler('plant_acc_type_combo', 'acc_type')
        self.assign_simple_handler('plant_memorial_check', 'memorial')
        self.view.connect('plant_quantity_entry', 'changed',
                          self.on_quantity_changed)
        self.view.connect('plant_loc_add_button', 'clicked',
                          self.on_loc_button_clicked, 'add')
        self.view.connect('plant_loc_edit_button', 'clicked',
                          self.on_loc_button_clicked, 'edit')


    def dirty(self):
        return self.notes_presenter.dirty() or \
            self.prop_presenter.dirty() or self.__dirty


    def on_date_entry_changed(self, entry, *args):
        self.change.date = entry.props.text


    def on_quantity_changed(self, entry, *args):
        value = entry.props.text
        if value:
            self.set_model_attr('quantity', int(value))
            if self.model.quantity == self._original_quantity:
                self.change.quantity = self.model.quantity
            else:
                self.change.quantity = \
                    self.model.quantity-self._original_quantity
        else:
            self.set_model_attr('quantity', None)
        self.refresh_sensitivity()


    def on_plant_code_entry_changed(self, entry, *args):
        """
        Validates the accession number and the plant code from the editors.
        """
        text = utils.utf8(entry.get_text())
        if text == u'':
            self.set_model_attr('code', None)
        else:
            self.set_model_attr('code', utils.utf8(text))

        if not self.model.accession:
            self.remove_problem(self.PROBLEM_DUPLICATE_PLANT_CODE, entry)
            self.refresh_sensitivity()
            return

        # add a problem if the code is not unique but not if its the
        # same accession and plant code that we started with when the
        # editor was opened
        if self.model.code is not None and not \
                is_code_unique(self.model, self.model.code) and not \
                (self._original_accession_id==self.model.accession.id and \
                     self.model.code==self._original_code):

                self.add_problem(self.PROBLEM_DUPLICATE_PLANT_CODE, entry)
        else:
            # remove_problem() won't complain if problem doesn't exist
            self.remove_problem(self.PROBLEM_DUPLICATE_PLANT_CODE, entry)

            # if there are no problems and the code represents a range
            # then go into "bulk mode" and change the background color
            # to a light blue and disable the 'Add note' button
            from pyparsing import ParseException
            if len(utils.range_builder(self.model.code)) > 1 and \
                    self.model in self.session.new:
                color_str = '#B0C4DE' # light steel blue
                color = gtk.gdk.color_parse(color_str)
                sensitive = False
            else:
                color = None
                sensitive = True
            self.view.widgets.plant_notebook.get_nth_page(1).\
                props.sensitive = sensitive
            self.view.widgets.plant_notebook_prop_label.\
                props.sensitive = sensitive
            entry.modify_bg(gtk.STATE_NORMAL, color)
            entry.modify_base(gtk.STATE_NORMAL, color)
            entry.queue_draw()

        self.refresh_sensitivity()


    def refresh_sensitivity(self):
        #debug('refresh_sensitivity()')

        # TODO: because we don't call refresh_sensitivity() every time
        # a character is entered then the edit button doesn't
        #
        # sensitize properly
        # combo_entry = self.view.widgets.plant_loc_comboentry.child
        # self.view.widgets.plant_loc_edit_button.\
        #     set_sensitive(self.model.location is not None \
        #                       and not self.has_problems(combo_entry))
        sensitive = (self.model.accession is not None and \
                     self.model.code is not None and \
                     self.model.location is not None) \
                     and self.dirty() and len(self.problems)==0
        self.view.widgets.pad_ok_button.set_sensitive(sensitive)
        self.view.widgets.pad_next_button.set_sensitive(sensitive)


    def set_model_attr(self, field, value, validator=None):
        #debug('set_model_attr(%s, %s)' % (field, value))
        super(PlantEditorPresenter, self)\
            .set_model_attr(field, value, validator)
        self.__dirty = True
        self.refresh_sensitivity()


    def on_loc_button_clicked(self, button, cmd=None):
        location = self.model.location
        if cmd is 'edit' and location:
            combo = self.view.widgets.plant_loc_comboentry
            LocationEditor(location, parent=self.view.get_window()).start()
            self.session.refresh(location)
            self.view.set_widget_value(combo, location)
        else:
            # TODO: see if the location editor returns the new
            # location and if so set it directly
            LocationEditor(parent=self.view.get_window()).start()


    def refresh_view(self):
        # TODO: is this really relevant since this editor only creates
        # new plants
        for widget, field in self.widget_to_field_map.iteritems():
            value = getattr(self.model, field)
            self.view.set_widget_value(widget, value)

        self.view.set_widget_value('plant_acc_type_combo',
                                   acc_type_values[self.model.acc_type],
                                   index=1)
        self.view.widgets.plant_memorial_check.set_inconsistent(False)
        self.view.widgets.plant_memorial_check.\
            set_active(self.model.memorial is True)

        self.refresh_sensitivity()


    def start(self):
        return self.view.start()



class PlantEditor(GenericModelViewPresenterEditor):

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
        super(PlantEditor, self).__init__(model, parent)
        if not parent and bauble.gui:
            parent = bauble.gui.window
        self.parent = parent
        self._committed = []

        view = PlantEditorView(parent=self.parent)
        self.presenter = PlantEditorPresenter(self.model, view)

        # add quick response keys
        self.attach_response(view.get_window(), gtk.RESPONSE_OK, 'Return',
                             gtk.gdk.CONTROL_MASK)
        self.attach_response(view.get_window(), self.RESPONSE_NEXT, 'n',
                             gtk.gdk.CONTROL_MASK)

        # set default focus
        if self.model.accession is None:
            view.widgets.plant_acc_entry.grab_focus()
        else:
            view.widgets.plant_code_entry.grab_focus()


    def cleanup(self):
        super(PlantEditor, self).cleanup()
        # reset the code entry colors
        entry.modify_bg(gtk.STATE_NORMAL, color)
        entry.modify_base(gtk.STATE_NORMAL, color)


    def commit_changes(self):
        """
        """
        codes = utils.range_builder(self.model.code)
        if len(codes) <= 1 or self.model not in self.session.new:
            change = self.presenter.change
            if change.quantity is None \
                    or (change.quantity == self.model.quantity \
                            and change.from_location == self.model.location):
                # if the quantity and location haven't changed then
                # don't save the change
                self.model.change = None
                self.session.expunge(change)
            else:
                if self.model.location != self.presenter.change.from_location:
                    self.presenter.change.to_location = self.model.location
            super(PlantEditor, self).commit_changes()
            self._committed.append(self.model)
            return

        # this method will create new plants from self.model even if
        # the plant code is not a range....its a small price to pay
        plants = []
        mapper = object_mapper(self.model)
        # TODO: precompute the _created and _last_updated attributes
        # incase we have to create lots of plants it won't be too slow

        # we have to set the properties on the new objects
        # individually since session.merge won't create a new object
        # since the object is already in the session
        import sqlalchemy.orm as orm
        for code in codes:
            new_plant = Plant()
            self.session.add(new_plant)

            # TODO: can't we user Plant.duplicate here
            ignore = ('changes', 'notes', 'propagations')
            for prop in mapper.iterate_properties:
                if prop.key not in ignore:
                    setattr(new_plant, prop.key, getattr(self.model, prop.key))
            new_plant.code = utils.utf8(code)
            new_plant.id = None
            new_plant._created = None
            new_plant._last_updated = None
            plants.append(new_plant)
            for note in self.model.notes:
                new_note = PlantNote()
                for prop in object_mapper(note).iterate_properties:
                    setattr(new_note, prop.key, getattr(note, prop.key))
                new_note.plant = new_plant
        try:
            map(self.session.expunge, self.model.notes)
            self.session.expunge(self.model)
            super(PlantEditor, self).commit_changes()
        except:
            self.session.add(self.model)
            raise
        self._committed.extend(plants)


    def handle_response(self, response):
        not_ok_msg = _('Are you sure you want to lose your changes?')
        if response == gtk.RESPONSE_OK or response in self.ok_responses:
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
        elif (self.presenter.dirty() and utils.yes_no_dialog(not_ok_msg)) \
                or not self.presenter.dirty():
            self.session.rollback()
            return True
        else:
            return False

#        # respond to responses
        more_committed = None
        if response == self.RESPONSE_NEXT:
            self.presenter.cleanup()
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
        sub_editor = None
        if self.session.query(Accession).count() == 0:
            msg = 'You must first add or import at least one Accession into '\
                  'the database before you can add plants.\n\nWould you like '\
                  'to open the Accession editor?'
            if utils.yes_no_dialog(msg):
                # cleanup in case we start a new PlantEditor
                self.presenter.cleanup()
                from bauble.plugins.garden.accession import AccessionEditor
                sub_editor = AccessionEditor()
                self._commited = sub_editor.start()
        if self.session.query(Location).count() == 0:
            msg = 'You must first add or import at least one Location into '\
                  'the database before you can add species.\n\nWould you '\
                  'like to open the Location editor?'
            if utils.yes_no_dialog(msg):
                # cleanup in case we start a new PlantEditor
                self.presenter.cleanup()
                sub_editor = LocationEditor()
                self._commited = sub_editor.start()

        if not sub_editor:
            while True:
                response = self.presenter.start()
                self.presenter.view.save_state()
                if self.handle_response(response):
                    break

        self.session.close() # cleanup session
        self.presenter.cleanup()
        return self._committed



class GeneralPlantExpander(InfoExpander):
    """
    general expander for the PlantInfoBox
    """

    def __init__(self, widgets):
        '''
        '''
        super(GeneralPlantExpander, self).__init__(_("General"), widgets)
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
                                                utils.xml_safe(unicode(head)),
                              markup=True)
        self.set_widget_value('plant_code_data', '<big>%s</big>' % \
                              utils.xml_safe(unicode(tail)), markup=True)
        self.set_widget_value('name_data',
                              row.accession.species_str(markup=True),
                              markup=True)
        self.set_widget_value('location_data', str(row.location))
        self.set_widget_value('quantity_data', row.quantity)


        status_str = _('Alive')
        if row.quantity <= 0:
            status_str = _('Dead')
        self.set_widget_value('status_data', status_str, False)

        self.set_widget_value('type_data', acc_type_values[row.acc_type],
                              False)

        image_size = gtk.ICON_SIZE_MENU
        stock = gtk.STOCK_NO
        if row.memorial:
            stock = gtk.STOCK_YES
        self.widgets.memorial_image.set_from_stock(stock, image_size)


class ChangesExpander(InfoExpander):
    """
    ChangesExpander
    """

    def __init__(self, widgets):
        """
        """
        super(ChangesExpander, self).__init__(_('Changes'), widgets)
        self.table = gtk.Table()
        self.vbox.pack_start(self.table)
        self.table.props.row_spacing = 3
        self.table.props.column_spacing = 5


    def update(self, row):
        '''
        '''
        self.table.foreach(self.table.remove)
        if not row.changes:
            return
        nrows = len(row.changes)
        self.table.resize(nrows, 2)
        date_format = prefs.prefs[prefs.date_format_pref]
        current_row = 0
        action = ('Transfered', 'Added', 'Removed')
        for change in sorted(row.changes, key=lambda x: x.date, reverse=True):
            date = change.date.strftime(date_format)
            label = gtk.Label('%s:' % date)
            self.table.attach(label, 0, 1, current_row, current_row+1,
                              xoptions=gtk.FILL)
            if change.quantity < 0:
                s = '%(quantity)s Removed from %(location)s' % \
                    dict(quantity=-change.quantity,
                         location=change.from_location)
            elif not change.from_location:
                s = '%(quantity)s Create at %(location)s' % \
                    dict(quantity=change.quantity,location=change.to_location)
            elif not change.to_location and change.quantity > 0:
                s = '%(quantity)s Added to %(location)s' % \
                    dict(quantity=change.quantity,location=change.from_location)
            elif change.to_location != change.from_location:
                s = '%(quantity)s Transferred from %(from_loc)s to %(to)s' % \
                    dict(quantity=change.quantity,
                         from_loc=change.from_location, to=change.to_location)
            else:
                s = '%s: %s -> %s' % (change.quantity, change.from_location,
                                      change.to_location)
            label = gtk.Label(s)
            label.set_alignment(0, .5)
            self.table.attach(label, 1, 2, current_row, current_row+1)
            current_row += 1
        self.vbox.show_all()



class PropagationExpander(InfoExpander):
    """
    Propagation Expander
    """

    def __init__(self, widgets):
        """
        """
        super(PropagationExpander, self).__init__(_('Propagations'), widgets)
        self.vbox.set_spacing(3)


    def update(self, row):
        sensitive = True
        if not row.propagations:
            sensitive = False
        self.props.expanded = sensitive
        self.props.sensitive = sensitive

        self.vbox.foreach(self.vbox.remove)
        format = prefs.prefs[prefs.date_format_pref]
        for prop in row.propagations:
            s = '%s: %s' % (prop.date.strftime(format), prop.get_summary())
            label = gtk.Label(s)
            label.set_alignment(0.0, 0.5)
            self.vbox.pack_start(label)
        self.vbox.show_all()


class PlantInfoBox(InfoBox):
    """
    an InfoBox for a Plants table row
    """

    def __init__(self):
        '''
        '''
        InfoBox.__init__(self)
        filename = os.path.join(paths.lib_dir(), "plugins", "garden",
                                "plant_infobox.glade")
        self.widgets = utils.load_widgets(filename)
        self.general = GeneralPlantExpander(self.widgets)
        self.add_expander(self.general)

        self.transfers = ChangesExpander(self.widgets)
        self.add_expander(self.transfers)

        self.propagations = PropagationExpander(self.widgets)
        self.add_expander(self.propagations)

        self.links = view.LinksExpander('notes')
        self.add_expander(self.links)

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
        self.transfers.update(row)
        self.propagations.update(row)

        urls = filter(lambda x: x!=[], \
                          [utils.get_urls(note.note) for note in row.notes])
        if not urls:
            self.links.props.visible = False
            self.links._sep.props.visible = False
        else:
            self.links.props.visible = True
            self.links._sep.props.visible = True
            self.links.update(row)

        self.props.update(row)


from bauble.plugins.garden.accession import Accession
