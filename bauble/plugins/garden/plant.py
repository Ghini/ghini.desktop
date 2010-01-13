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


def change_status_callback(plants):
    if 0 in [p.quantity for p in plants]:
        return
    e = PlantStatusEditor(model=plants)
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



edit_action = Action('plant_edit', ('_Edit'), callback=edit_callback,
                     accelerator='<ctrl>e', multiselect=True)

change_action = Action('plant_status', ('_Transfer/Remove'),
                       callback=change_status_callback,
                       accelerator='<ctrl>x', multiselect=True)

remove_action = Action('plant_remove', ('_Delete'), callback=remove_callback,
                       accelerator='<ctrl>Delete', multiselect=True)

plant_context_menu = [edit_action, change_action, remove_action]


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
    codes = session.query(Plant.code).join(Accession).filter(Accession.id==acc.id).all()
    next = 1
    if codes:
        try:
            next = max([int(code[0]) for code in codes])+1
        except Exception, e:
            return None
    return next


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


# TODO: a plant should only be allowed one removal and then it becomes
# frozen...although you should be able to edit it in case you make a
# mistake, or maybe transfer it from being removed with a transfer
# reason of "mistake"....shoud a transfer from a removal delete the
# removal so that the plant can be removed again....since we can only
# have one removal would should probably add a removal_id to Plant so
# its a 1-1 relation....but if we have a table with a removal code
# then how do we translate it unless we just hardcode the translation
# strings here
removal_reasons = {
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
    u'OTHR': _('Other')
    }



class PlantRemoval(db.Base):
    __tablename__ = 'plant_removal'
    __mapper_args__ = {'order_by': 'plant_removal.date'}

    plant_id = Column(Integer, ForeignKey('plant.id'), nullable=False)
    from_location_id = Column(Integer, ForeignKey('location.id'),
                              nullable=False)

    reason = Column(types.Enum(values=removal_reasons.keys()))
    person = Column(Unicode(64))
    quantity = Column(Integer, autoincrement=False, nullable=False)

    # TODO: is this redundant with note.date
    date = Column(types.Date)
    note_id = Column(Integer, ForeignKey('plant_note.id'))

    from_location = relation('Location',
                 primaryjoin='PlantRemoval.from_location_id == Location.id')

    plant = relation('Plant', uselist=False,
                     backref=backref('removals', cascade='all, delete-orphan'))


class PlantTransfer(db.Base):
    __tablename__ = 'plant_transfer'
    __mapper_args__ = {'order_by': 'plant_transfer.date'}

    plant_id = Column(Integer, ForeignKey('plant.id'), nullable=False)

    # TODO: from_id != to_id
    from_location_id = Column(Integer, ForeignKey('location.id'),
                              nullable=False)
    to_location_id = Column(Integer, ForeignKey('location.id'), nullable=False)

    # the name of the person who made the transfer
    person = Column(Unicode(64))
    """The name of the person who made the transfer"""
    quantity = Column(Integer, autoincrement=False, nullable=False)
    note_id = Column(Integer, ForeignKey('plant_note.id'))

    # TODO: is this redundant with note.date
    date = Column(types.Date)

    # relations
    plant = relation('Plant', uselist=False,
                     backref=backref('transfers',cascade='all, delete-orphan'))
    from_location = relation('Location',
                   primaryjoin='PlantTransfer.from_location_id == Location.id')
    to_location = relation('Location',
                   primaryjoin='PlantTransfer.to_location_id == Location.id')


acc_type_values = {u'Plant': _('Plant'),
                   u'Seed': _('Seed/Spore'),
                   u'Vegetative': _('Vegetative Part'),
                   u'Tissue': _('Tissue Culture'),
                   u'Other': _('Other'),
                   None: _('')}


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


    def markup(self):
        #return "%s.%s" % (self.accession, self.plant_id)
        # FIXME: this makes expanding accessions look ugly with too many
        # plant names around but makes expanding the location essential
        # or you don't know what plants you are looking at
        return "%s%s%s (%s)" % (self.accession, self.delimiter, self.code,
                                self.accession.species_str(markup=True))


from bauble.plugins.garden.accession import Accession

REMOVAL_ACTION = 'Removal'
TRANSFER_ACTION = 'Transfer'

plant_actions = {REMOVAL_ACTION: _("Removal"),
                 TRANSFER_ACTION: _("Transfer")}


class PlantStatusEditorView(GenericEditorView):
    def __init__(self, parent=None):
        path = os.path.join(paths.lib_dir(), 'plugins', 'garden',
                            'plant_editor.glade')
        super(PlantStatusEditorView, self).__init__(path, parent)
        self.widgets.ped_ok_button.set_sensitive(False)
        self.init_translatable_combo('rem_reason_combo', removal_reasons)


    def get_window(self):
        return self.widgets.plant_editor_dialog


    def save_state(self):
        pass


    def restore_state(self):
        pass


    def start(self):
        return self.get_window().run()



class PlantStatusEditorPresenter(GenericEditorPresenter):

    PROBLEM_DUPLICATE_PLANT_CODE = str(random())

    def __init__(self, model, view):
        '''
        @param model: should be an list of Plants
        @param view: should be an instance of PlantEditorView
        '''
        super(PlantStatusEditorPresenter, self).__init__(model, view)
        self.session = db.Session()
        self.__dirty = False

        self._transfer = PlantTransfer()
        self._note = PlantNote()
        self._removal = PlantRemoval()

        # TODO: we should put this in a scrolled window or something
        # since the list of labels will get way to big when working on
        # lots of species

        # show the plants we are changing in the labels
        label = self.view.widgets.ped_plants_label
        label_str = ''
        getsid = lambda x: x.accession.species.id
        if len(self.model) > 100:
            label_str = _('<i>(changing over 100 plants)</i>')
        elif len(self.model) < 13:
            label_str = ', '.join([str(p) for p in self.model])
        elif len(self.model) < 100:
            for sid, group in itertools.groupby(self.model, getsid):
                if label_str:
                    label_str += '\n'
                plants = list(group)
                s = '<b>%s</b>: %s' % (plants[0].accession.species_str(),
                                       ', '.join([str(p) for p in plants]))
                label_str += s
        label.set_markup(label_str)

        def on_user_changed(*args):
            # we don't set the note user here since that gets set in
            # commit_changes()
            person = utils.utf8(self.view.widgets.ped_user_entry.props.text)
            self._transfer.person = person
            self._removal.person = person
        self.view.connect('ped_user_entry', 'changed', on_user_changed)

        # set the user name entry to the current use if we're using postgres
        if db.engine.name in ('postgres', 'postgresql'):
            import bauble.plugins.users as users
            self.view.widgets.ped_user_entry.props.text = users.current_user()
        elif 'USER' in os.environ:
            self.view.set_widget_value('ped_user_entry', os.environ['USER'])
        elif 'USERNAME' in os.environ:
            self.view.set_widget_value('ped_user_entry',os.environ['USERNAME'])

        # initialize the date button
        utils.setup_date_button(view, 'ped_date_entry', 'ped_date_button')
        def on_date_changed(*args):
            # we don't set the note date here since that gets set in
            # commit_changes()
            self._transfer.date = self.view.widgets.ped_date_entry.props.text
            self._removal.date = self.view.widgets.ped_date_entry.props.text
            self.__dirty = True
            self.refresh_sensitivity()
        self.view.connect(self.view.widgets.ped_date_entry, 'changed',
                          on_date_changed)
        # set the text to the empty string to make sure the
        # on_date_changed() handler is called
        self.view.widgets.ped_date_entry.props.text = ''
        self.view.widgets.ped_date_button.clicked() # insert todays date

        def on_quantity_changed(entry, *args):
            text = entry.props.text
            problem = 'BAD_QUANTITY'
            if not text or int(text) < 0 or int(text) > self.model[0].quantity:
                self.add_problem(problem, entry)
                quantity = None
            else:
                self.remove_problem(problem, entry)
                quantity = int(text)
            self._transfer.quantity = quantity
            self._removal.quantity = quantity
            self.__dirty = True
            self.refresh_sensitivity()

        if len(self.model) > 1:
            self.view.widgets.ped_quantity_label.props.label = _('(all)')
            self.view.widgets.ped_quantity_entry.props.sensitive = False
        else:
            quantity = self.model[0].quantity
            if quantity > 1:
                label_str = '1-%s' % quantity
            else:
                label_str = ''
            self.view.widgets.ped_quantity_label.props.label = label_str
            self.view.widgets.ped_quantity_entry.props.sensitive = True
            self.view.connect(self.view.widgets.ped_quantity_entry, 'changed',
                              on_quantity_changed)
            self.view.widgets.ped_quantity_entry.props.text = quantity

        # connect handlers for all the widget even if they aren't
        # visible or relevant to the current action type so that we
        # save their state if the action type changes, we later
        # extract the values and save the action on commit_changes()

        # initialize the removal reason combo
        def on_rem_reason_changed(combo, *args):
            model = combo.get_model()
            value = model[combo.get_active_iter()][0]
            self._removal.reason = value
            self.__dirty = True
            self.refresh_sensitivity()
        self.view.connect('rem_reason_combo', 'changed', on_rem_reason_changed)

        self.view.connect('plant_transfer_radio', 'toggled',
                          self.on_plant_transfer_radio_toggled)
        self.view.widgets.plant_transfer_radio.toggled()

        # initialize the location combo
        def on_tran_to_select(value):
            self._transfer.to_location = value
            if value:
                self.__dirty = True
                self.refresh_sensitivity()
        from bauble.plugins.garden import init_location_comboentry
        self.view.widgets.trans_to_comboentry.child.props.text = ''
        init_location_comboentry(self, self.view.widgets.trans_to_comboentry,
                                 on_tran_to_select)

        def on_buff_changed(buff, data=None):
            self.__dirty = True
            self.refresh_sensitivity()
            self._note.note = utils.utf8(buff.props.text)
        self.view.widgets.note_textview.props.buffer.props.text = ''
        self.view.connect(self.view.widgets.note_textview.get_buffer(),
                          'changed', on_buff_changed)


    def dirty(self):
        return self.__dirty


    def refresh_sensitivity(self):
        sensitive = False
        action = self.get_current_action()
        transfer_ignore = ['id', 'plant_id', 'from_location_id',
                           'to_location_id']
        removal_ignore = ['id', 'plant_id', 'from_location_id']
        if action == REMOVAL_ACTION and \
                not utils.get_invalid_columns(self._removal, removal_ignore) \
                and self._removal.reason:
            sensitive = True
        elif action == TRANSFER_ACTION and \
                not utils.get_invalid_columns(self._transfer, transfer_ignore) \
                and self._transfer.to_location:
            sensitive = True
        self.view.widgets.ped_ok_button.props.sensitive = sensitive


    def get_current_action(self):
        """
        Return the code for the currently selected action.
        """
        radio = self.view.widgets.plant_transfer_radio
        if radio.props.active:
            return TRANSFER_ACTION
        return REMOVAL_ACTION


    def on_plant_transfer_radio_toggled(self, radio, *args):
        action = self.get_current_action()
        if action == TRANSFER_ACTION:
            action_box = self.view.widgets.plant_transfer_box
            action_box.props.visible = True
            self.view.widgets.plant_removal_box.props.visible = False
        else:
            action_box = self.view.widgets.plant_removal_box
            action_box.props.visible = True
            self.view.widgets.plant_transfer_box.props.visible = False

        # refresh the sensitivity in case the values for the new
        # action are set correctly
        self.refresh_sensitivity()


    def start(self):
        return self.view.start()



class PlantStatusEditor(GenericModelViewPresenterEditor):


    def __init__(self, model=None, parent=None):
        '''
        @param model: Plant instance or None
        @param parent: None
        '''
        self.model = Plant()
        super(PlantStatusEditor, self).__init__(self.model, parent)
        if not parent and bauble.gui:
            parent = bauble.gui.window
        self.parent = parent
        self._committed = []

        # copy the plants into our session
        self.plants = map(self.session.merge, model)

        view = PlantStatusEditorView(parent=self.parent)
        self.presenter = PlantStatusEditorPresenter(self.plants, view)

        # add quick response keys
        self.attach_response(view.get_window(), gtk.RESPONSE_OK, 'Return',
                             gtk.gdk.CONTROL_MASK)


    def commit_changes(self):
        """
        """
        action = self.presenter.get_current_action()
        if action == REMOVAL_ACTION:
            action_model = self.presenter._removal
            self.presenter._note.category = action
        elif action == TRANSFER_ACTION:
            action_model = self.presenter._transfer
            self.presenter._note.category = action
        else:
            raise ValueError('unknown plant action: %s' % action)

        # create a copy of the action_model for each plant and set the
        # .plant attribute on each
        for plant in self.plants:
            # make a copy of the action model in the plant's session
            session = object_session(plant)
            new_action = type(action_model)()
            for prop in object_mapper(new_action).iterate_properties:
                setattr(new_action, prop.key, getattr(action_model, prop.key))
            if action == 'Transfer':
                new_action.to_location = \
                    session.merge(action_model.to_location)
                # change the location of the plant
                new_action.from_location = plant.location
                plant.location = new_action.to_location
            elif action == 'Removal':
                new_action.from_location = plant.location
                plant.quantity -= new_action.quantity

            new_action.plant = plant

            # copy the note
            if self.presenter._note.note:
                new_note = PlantNote()
                new_note.note = self.presenter._note.note
                category = plant_actions[self.presenter.get_current_action()]
                new_note.category = utils.utf8(category)
                new_note.date = new_action.date
                new_note.user = new_action.person
                new_note.plant = plant
                action_model.note = new_note

        # delete dummy model and remove it from the session
        self.session.expunge(self.model)
        del self.model
        super(PlantStatusEditor, self).commit_changes()


    def handle_response(self, response):
        not_ok_msg = _('Are you sure you want to lose your changes?')
        if response == gtk.RESPONSE_OK:
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

        self.presenter.cleanup()
        self.session.close() # cleanup session
        return self._committed


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
        self.widgets.plant_notebook.set_current_page(0)


    def get_window(self):
        return self.widgets.plant_add_dialog


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
        # that is already associated with an accession
        if self.model.accession and not self.model.code:
            code = get_next_code(self.model.accession)
            if code:
                # if get_next_code() returns None then there was an error
                self.model.code = utils.utf8(code)

        # the location and quantity can only be changed on on a new plant
        if self.model not in self.session.new:
            self.view.widgets.plant_loc_hbox.props.sensitive = False
            self.view.widgets.plant_quantity_entry.props.sensitive = False
        else:
            self.view.widgets.plant_loc_hbox.props.sensitive = True
            self.view.widgets.plant_quantity_entry.props.sensitive = True

        self.refresh_view() # put model values in view

        def on_location_select(location):
            self.set_model_attr('location', location)
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
        self.assign_simple_handler('plant_quantity_entry', 'quantity')
        self.view.connect('plant_loc_add_button', 'clicked',
                          self.on_loc_button_clicked, 'add')
        self.view.connect('plant_loc_edit_button', 'clicked',
                          self.on_loc_button_clicked, 'edit')


    def dirty(self):
        return self.notes_presenter.dirty() or \
            self.prop_presenter.dirty() or self.__dirty


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
                self.is_code_unique(self.model.code) and not \
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


    def is_code_unique(self, code):
        """
        Return True/False if the code is unique for the current
        Accession on self.model.accession.

        This method will take range values for code that can be passed
        to utils.range_builder()
        """
        codes = map(utils.utf8, utils.range_builder(code))
        # reference accesssion.id instead of accession_id since
        # setting the accession on the model doesn't set the
        # accession_id until the session is flushed
        q = self.session.query(Plant).join('accession').\
            filter(and_(Accession.id==self.model.accession.id,
                        Plant.code.in_(codes)))
        return q.count() == 0



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
            ignore = ('removal', 'transfers', 'notes', 'propagations')
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


class TransferExpander(InfoExpander):
    """
    Transfer Expander
    """

    def __init__(self, widgets):
        """
        """
        super(TransferExpander, self).__init__(_('Transfers/Removal'), widgets)
        self.table = gtk.Table()
        self.vbox.pack_start(self.table)
        self.table.props.row_spacing = 3
        self.table.props.column_spacing = 5


    def update(self, row):
        '''
        '''
        self.table.foreach(self.table.remove)
        nrows = len(row.transfers) + len(row.removals)
        self.table.resize(nrows, 2)
        date_format = prefs.prefs[prefs.date_format_pref]
        current_row = 0

        def removal_str(removal):
            if not removal.reason:
                reason = _('(no reason)')
            else:
                reason=utils.utf8(removal_reasons[removal.reason])
            s = _('Removed %(quantity)s from %(from_loc)s: %(reason)s') % \
                dict(from_loc=removal.from_location, quantity=removal.quantity,
                     reason=reason)
            return s

        def transfer_str(transfer):
            if not transfer.person:
                person = _('(unknown)')
            else:
                person = transfer.person
            s = _('Transferred %(quantity)s from %(from_loc)s to %(to)s '
                  'by %(person)s') % \
                  dict(from_loc=transfer.from_location,
                       quantity=transfer.quantity, to=transfer.to_location,
                       person=person)
            return s

        # sort the transfers and removals by date
        movements = sorted(itertools.chain(row.removals, row.transfers),
                           key=lambda x: x.date, reverse=True)
        for move in movements:
            date = move.date.strftime(date_format)
            label = gtk.Label('%s:' % date)
            self.table.attach(label, 0, 1, current_row, current_row+1,
                              xoptions=gtk.FILL)
            if isinstance(move, PlantTransfer):
                s = transfer_str(move)
            else:
                s = removal_str(move)
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

        self.transfers = TransferExpander(self.widgets)
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
