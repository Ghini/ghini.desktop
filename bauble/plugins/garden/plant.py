#
# plant.py
#
"""
Defines the plant table and handled editing plants
"""
import os
import sys
import traceback
from random import random

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
from bauble.view import SearchStrategy, ResultSet, Action
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
    e = PlantEditor(model=plants)
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
    finally:
        session.close()
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
        self._results = ResultSet()


    def search(self, text, session):
        # TODO: this doesn't support search like plant=2009.0039.1 or
        # plant where accession.code=2009.0039

        # TODO: searches like 2009.0039.% or * would be handy
        r1 = super(PlantSearch, self).search(text, session)
        self._results.add(r1)
        delimiter = Plant.get_delimiter()
        if delimiter not in text:
            return []
        acc_code, plant_code = text.rsplit(delimiter, 1)
        query = session.query(Plant)
        from bauble.plugins.garden import Accession
        try:
            q = query.join('accession').\
                filter(and_(Accession.code==acc_code, Plant.code==plant_code))
            self._results.add(q)
        except Exception, e:
            debug(e)
            return []
        return q


# TODO: what would happend if the PlantRemove.plant_id and
# PlantNote.plant_id were out of sink....how could we avoid these sort
# of cycles
class PlantNote(db.Base):
    __tablename__ = 'plant_note'
    __mapper_args__ = {'order_by': 'date'}

    plant_id = Column(Integer, ForeignKey('plant.id'), nullable=False)
    date = Column(types.Date)
    note = Column(UnicodeText)
    user = Column(Unicode(32))
    category = Column(String(32))

    plant = relation('Plant', backref='notes')


# TODO: a plant should only be allowed one removal and then it becomes
# frozen...although you should be able to edit it in case you make a
# mistake, or maybe transfer it from being removed with a transfer
# reason of "mistake"....shoud a transfer from a removal delete the
# removal so that the plant can be removed again....since we can only
# have one removal would should probably add a removal_id to Plant so
# its a 1-1 relation
removal_reasons = {
    u'DEAD': _('Dead'),
    u'DISC': _('Discarded'),
    u'DISW': _('Discarded, weedy'),
    u'LOST': _('Lost, whereabouts unknown'),
    u'STOL': _('Stolen'),
    u'WINK': _('Winter kill'),
    u'ERRO': _('Error correction'),
    u'DIST': _('Distributed elsewhere'),
    u'DELE': _('Deleted, yr.dead unknown'),
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
    __mapper_args__ = {'order_by': 'date'}

    plant_id = Column(Integer, ForeignKey('plant.id'), nullable=False)
    from_location_id = Column(Integer, ForeignKey('location.id'),
                              nullable=False)

    reason = Column(types.Enum(values=removal_reasons.keys()))

    # TODO: is this redundant with note.date
    date = Column(types.Date)
    note_id = Column(Integer, ForeignKey('plant_note.id'))

    from_location = relation('Location',
                 primaryjoin='PlantRemoval.from_location_id == Location.id')

    # TODO: plan_id should probably go on the plant as removal_id
    # since in theory there can only be one removal for a plant
    plant = relation('Plant', backref='removal')


class PlantTransfer(db.Base):
    __tablename__ = 'plant_transfer'
    __mapper_args__ = {'order_by': 'date'}

    plant_id = Column(Integer, ForeignKey('plant.id'), nullable=False)

    # TODO: from_id != to_id
    from_location_id = Column(Integer, ForeignKey('location.id'),
                              nullable=False)
    to_location_id = Column(Integer, ForeignKey('location.id'), nullable=False)

    # the name of the person who made the transfer
    person = Column(Unicode(64))
    """The name of the person who made the transfer"""

    # TODO: do we need a standard set of reasons or shuld this just
    # be relegated to notes
    reason = Column(String(32))

    note_id = Column(Integer, ForeignKey('plant_note.id'))

    # TODO: is this redundant with note.date
    date = Column(types.Date)

    # relations
    plant = relation('Plant', backref='transfers')
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

acc_status_values = {u'Living': _('Living accession'),
                     u'Dead': _('Dead'),
                     u'Transferred': _('Transferred'),
                     u'Dormant': _('Stored in dormant state'),
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
    acc_type = Column(types.Enum(values=acc_type_values.keys()), default=None)
    acc_status = Column(types.Enum(values=acc_status_values.keys()),
                        default=None)

    # TODO: notes is now a relation to PlantNote
    #notes = Column(UnicodeText)
    accession_id = Column(Integer, ForeignKey('accession.id'), nullable=False)
    location_id = Column(Integer, ForeignKey('location.id'), nullable=False)

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


plant_actions = {'Removal': _("Removal"),
                 'Transfer': _("Tranfer"),
                 'AddNote': _("Add note")}

class PlantEditorView(GenericEditorView):
    def __init__(self, parent=None):
        path = os.path.join(paths.lib_dir(), 'plugins', 'garden',
                            'plant_editor.glade')
        super(PlantEditorView, self).__init__(path, parent)

        self.widgets.ped_ok_button.set_sensitive(False)


    def get_window(self):
        return self.widgets.plant_editor_dialog


    def save_state(self):
        pass


    def restore_state(self):
        pass


    def start(self):
        return self.get_window().run()



# class PlantTransferPresenter(GenericEditorPresenter):

#     def __init__(self, model, view):
#         '''
#         @param model: should be an list of Plants
#         @param view: should be an instance of PlantEditorView
#         '''
#         super(PlantTransferPresenter, self).__init__(model, view)


class PlantEditorPresenter(GenericEditorPresenter):


    widget_to_field_map = {'plant_code_entry': 'code',
                           'plant_acc_entry': 'accession',
                           'plant_loc_comboentry': 'location',
                           'plant_acc_type_combo': 'acc_type',
                           'plant_acc_status_combo': 'acc_status',
                           'plant_notes_textview': 'notes'}

    PROBLEM_DUPLICATE_PLANT_CODE = str(random())

    def __init__(self, model, view):
        '''
        @param model: should be an list of Plants
        @param view: should be an instance of PlantEditorView
        '''
        super(PlantEditorPresenter, self).__init__(model, view)
        #self.session = object_session(model[0])
        self.session = bauble.Session()
        # self._original_accession_id = self.model.accession_id
        # self._original_code = self.model.code
        self.__dirty = False

        self._transfer = PlantTransfer()
        self._note = PlantNote()
        self._removal = PlantRemoval()

        self. action_combo_map = {'Removal': self.view.widgets.removal_box,
                                  'Transfer': self.view.widgets.transfer_box,
                                  'AddNote': self.view.widgets.notes_box}

        # show the plants we are changing in the labels
        label = self.view.widgets.ped_plants_label
        label.set_text(', '.join([str(p) for p in self.model]))

        # on start hide the details until an action is chosen
        self.view.widgets.details_box.props.visible = False

        # set the user name entry to the current use if we're using postgres
        if db.engine.name in ('postgres', 'postgresql'):
            import bauble.plugins.users as users
            self.view.set_widget_value('ped_user_entry', users.current_user())
            # TODO: should we set the value to $USER if not postgres
        elif 'USER' in os.environ:
            self.view.set_widget_value('ped_user_entry', os.environ['USER'])
        elif 'USERNAME' in os.environ:
            self.view.set_widget_value('ped_user_entry',os.environ['USERNAME'])

        # initialize the date button

        utils.setup_date_button(self.view.widgets.ped_date_entry,
                                self.view.widgets.ped_date_button)
        def on_date_changed(*args):
            self._note.date = self.view.widgets.ped_date_entry.props.text
        self.view.connect(self.view.widgets.ped_date_entry, 'changed',
                          on_date_changed)
        self.view.widgets.ped_date_button.clicked() # insert todays date


        # connect handlers for all the widget even if they aren't
        # visible or relevant to the current action type so that we
        # save their state if the action type changes, we later
        # extract the values and save the action on commit_changes()

        # initialize the removal reason combo
        self.init_translatable_combo('rem_reason_combo', removal_reasons)
        def on_rem_reason_changed(combo, *args):
            model = combo.get_model()
            value = model[combo.get_active_iter()][0]
            #debug('rem: %s' % value)
            self._removal.reason = value
            self.__dirty = True
            self.refresh_sensitivity()
        self.view.connect('rem_reason_combo', 'changed', on_rem_reason_changed)

        # initialize the plant action combo
        self.init_translatable_combo('plant_action_combo', plant_actions)
        self.view.connect('plant_action_combo', 'changed',
                          self.on_action_combo_changed)
        def on_tran_to_select(value):
            debug('trans: %s' % value)
            self._transfer.to_location = value
            if value:
                self.__dirty = True
                self.refresh_sensitivity()
        self.init_location_combo(self.view.widgets.trans_to_comboentry,
                                 on_tran_to_select)

        def on_buff_changed(buff, data=None):
            self.__dirty = True
            self.refresh_sensitivity()
            self._note.note = utils.utf8(buff.props.text)
        self.view.connect(self.view.widgets.note_textview.get_buffer(),
                          'changed', on_buff_changed)

        def on_category_changed(combo, data=None):
            self.__dirty = True
            self.refresh_sensitivity()
            self._note.category = utils.utf8(combo.child.props.text)
        self.view.connect('note_category_comboentry', 'changed',
                          on_category_changed)


    def init_location_combo(self, combo, on_select):
        """
        Initialize a gtk.ComboEntry where the combo model values and
        completions in the entry are all the locations from the
        database.
        """
        entry = combo.child
        model = gtk.ListStore(object)
        for loc in self.session.query(Location):
            model.append([loc])
        utils.clear_model(combo)
        combo.set_model(model)
        combo.clear()
        renderer = gtk.CellRendererText()
        combo.pack_start(renderer, True)
        def cell_data_func(column, cell, model, it, data=None):
            # the cell data func for the combo
            v = model[it][0]
            cell.set_property('text', utils.utf8(v))
        combo.set_cell_data_func(renderer, cell_data_func)

        # attach a gtk.EntryCompletion
        self.view.attach_completion(combo.child, cell_data_func,
                                    minimum_key_length=1)

        # make the completion on the entry for the combo entry
        # have the same model as the combo
        combo.child.get_completion().set_model(model)

        self.assign_completions_handler(entry, None, on_select=on_select)
        def changed(combo, *args):
            it = combo.get_active_iter()
            if it:
                value = combo.get_model()[it][0]
                on_select(value)
                combo.child.props.text = value
                self.refresh_sensitivity()
        self.view.connect(combo, 'changed', changed)


    def dirty(self):
        return self.__dirty


    def refresh_sensitivity(self):
        sensitive = False
        action = self.get_current_action()
        if action == 'Removal' and self._removal.reason:
            sensitive = True
        elif action == 'Transfer' and self._transfer.to_location:
            sensitive = True
        elif action == 'AddNote' and self.view.widgets.note_textview.get_buffer().props.text:
            sensitive = True
        self.view.widgets.ped_ok_button.props.sensitive = sensitive


    def get_current_action(self):
        """
        Return the code for the currently selected action.
        """
        combo = self.view.widgets.plant_action_combo
        model = combo.get_model()
        value = model[combo.get_active_iter()][0]
        return value


    def on_action_combo_changed(self, combo, *args):
        """
        Called when the action combo changes.
        """
        # TODO: we need to create a removal, transfer or new note
        # depending on the action
        value = self.get_current_action()
        action_box = self.action_combo_map[value]
        action_parent_box = self.view.widgets.action_parent_box

        # unparent the action box
        self.view.widgets.remove_parent(action_box)

        # remove any children from the parent box
        child = action_parent_box.get_child()
        if child:
            action_parent_box.remove(child)

        # add the action box to the parent
        action_parent_box.add(action_box)

        #self.view.widgets.details_box.set_property('visible', False)# = False
        self.view.widgets.details_box.props.visible = True
        self.view.widgets.details_box.show_all()
        self.view.widgets.details_box.queue_resize()

        # refresh the sensitivity in case the values for the new
        # action are set correctly
        self.refresh_sensitivity()


    def start(self):
        return self.view.start()



class PlantEditor(GenericModelViewPresenterEditor):


    def __init__(self, model=None, parent=None):
        '''
        @param model: Plant instance or None
        @param parent: None
        '''
        # if model is None:
        #     model = Plant()
        #self.plants = model
        self.model = Plant()
        #GenericModelViewPresenterEditor.__init__(self, model, parent)
        #super(NewPlantEditor, self).__init__(model, parent)
        #self.template = Plant()
        super(PlantEditor, self).__init__(self.model, parent)
        if not parent and bauble.gui:
            parent = bauble.gui.window
        self.parent = parent
        self._committed = []

        # copy the plants into our session
        self.plants = map(self.session.merge, model)

        view = PlantEditorView(parent=self.parent)
        self.presenter = PlantEditorPresenter(self.plants, view)

        # add quick response keys
        self.attach_response(view.get_window(), gtk.RESPONSE_OK, 'Return',
                             gtk.gdk.CONTROL_MASK)

        # set default focus
        # if self.model.accession is None:
        #     view.widgets.plant_acc_entry.grab_focus()
        # else:
        #     view.widgets.plant_code_entry.grab_focus()


    def commit_changes(self):
        """
        """
        #debug('commit_changes()')
        action = self.presenter.get_current_action()
        #debug(action)
        if action == 'Removal':
            action_model = self.presenter._removal
            self._presenter._note.category = action
        elif action == 'Transfer':
            action_model = self.presenter._transfer
            self._presenter._note.category = action
        elif action == 'AddNote':
            action_model = self.presenter._note
            debug(action_model.category)
        else:
            raise ValueError('unknown plant action: %s' % action)

        # create a copy of the action_model for each plant and set the
        # .plant attribute on each...the easiest way to copy would
        # probably be to use session.merge
        for plant in self.plants:
            # make a copy of the action model in the plant's session
            session = object_session(plant)
            new_model = session.merge(action_model)
            new_model.plant = plant
            if action == 'Transfer':
                new_model.from_location = plant.location
                plant.location = new_model.to_location
                new_model.note = session.merge(self.presenter._note)
            elif action == 'Removal':
                new_model.from_location = plant.location
                new_model.note = session.merge(self.presenter._note)

        # delete dummy model and remove it from the session
        self.session.expunge(self.model)
        del self.model
        super(PlantEditor, self).commit_changes()


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


class AddPlantEditorView(GenericEditorView):

    #source_expanded_pref = 'editor.accesssion.source.expanded'

    _tooltips = {
        'plant_code_entry': _('The plant code must be a unique code'),
        'plant_acc_entry': _('The accession must be selected from the list ' \
                             'of completions.  To add an accession use the '\
                             'Accession editor'),
        'plant_loc_comboentry': _('The location of the plant in your '\
                                      'collection.'),
        'plant_acc_type_combo': _('The type of the plant material.\n\n' \
                                  'Possible values: %s') % \
                                  ', '.join(acc_type_values.values()),
        'plant_acc_status_combo': _('The status of this plant in the ' \
                                    'collection.\nPossible values: %s') % \
                                    ', '.join(acc_status_values.values()),
        'plant_notes_textview': _('Miscelleanous notes about this plant.'),
        }


    def __init__(self, parent=None):
        glade_file = os.path.join(paths.lib_dir(), 'plugins', 'garden',
                                  'plant_editor.glade')
        super(AddPlantEditorView, self).__init__(glade_file, parent=parent)
        self.widgets.pad_ok_button.set_sensitive(False)
        self.widgets.pad_next_button.set_sensitive(False)
        def acc_cell_data_func(column, renderer, model, iter, data=None):
            v = model[iter][0]
            renderer.set_property('text', '%s (%s)' % (str(v), str(v.species)))
        self.attach_completion('plant_acc_entry', acc_cell_data_func,
                               minimum_key_length=1)

        def loc_cell_data_func(col, renderer, model, it, data=None):
            # the cell_data_func for the entry completions
            v = model[it][0]
            renderer.set_property('text', '%s' % utils.utf8(v))

        entry = self.widgets.plant_loc_comboentry.child
        self.attach_completion(entry, loc_cell_data_func,
                               minimum_key_length=1)


    def get_window(self):
        return self.widgets.plant_add_dialog


    def __del__(self):
        #debug('PlantView.__del__()')
        #GenericEditorView.__del__(self)
        #self.dialog.destroy()
        pass


    def save_state(self):
        pass


    def restore_state(self):
        pass


    def start(self):
        return self.get_window().run()



class AddPlantEditorPresenter(GenericEditorPresenter):


    widget_to_field_map = {'plant_code_entry': 'code',
                           'plant_acc_entry': 'accession',
                           'plant_loc_comboentry': 'location',
                           'plant_acc_type_combo': 'acc_type',
                           'plant_acc_status_combo': 'acc_status',
                           'plant_notes_textview': 'notes'}

    PROBLEM_DUPLICATE_PLANT_CODE = str(random())

    def __init__(self, model, view):
        '''
        @param model: should be an instance of Plant class
        @param view: should be an instance of PlantEditorView
        '''
        super(AddPlantEditorPresenter, self).__init__(model, view)
        self.session = object_session(model)
        self._original_accession_id = self.model.accession_id
        self._original_code = self.model.code
        self.__dirty = False

        self.init_translatable_combo('plant_acc_status_combo',
                                     acc_status_values)
        self.init_translatable_combo('plant_acc_type_combo', acc_type_values)

#        self.init_history_box()

        # set default values for acc_status and acc_type
        if self.model.id is None and self.model.acc_type is None:
            self.model.acc_type = u'Plant'
        if self.model.id is None and self.model.acc_status is None:
            self.model.acc_status = u'Living'

        # intialize the locations comboentry
        loc_combo = self.view.widgets.plant_loc_comboentry
        model = gtk.ListStore(object)
        for loc in self.session.query(Location):
            model.append([loc])
        utils.clear_model(loc_combo)
        loc_combo.set_model(model)
        loc_combo.clear()
        renderer = gtk.CellRendererText()
        loc_combo.pack_start(renderer, True)
        def cell_data_func(column, cell, model, it, data=None):
            # the cell data func for the combo
            v = model[it][0]
            cell.set_property('text', utils.utf8(v))
        loc_combo.set_cell_data_func(renderer, cell_data_func)

        # make the completion on the entry for the combo entry
        # have the same model as the combo
        loc_combo.child.get_completion().set_model(model)

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

        # def loc_get_completions(text):
        #     query = self.session.query(Location)
        #     return query.filter(utils.ilike(Location.name,
        #                                     utils.utf8('%s%%' % text)))
        def on_loc_select(value):
            self.set_model_attr('location', value)

        plant_loc_entry = self.view.widgets.plant_loc_comboentry.child
        self.assign_completions_handler(plant_loc_entry, None,
                                        on_select=on_loc_select)
        self.assign_simple_handler('plant_loc_comboentry', 'location')#,
                                   #UnicodeOrNoneValidator())

        self.assign_simple_handler('plant_acc_status_combo', 'acc_status')
        self.assign_simple_handler('plant_acc_type_combo', 'acc_type')

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
        for code in utils.range_builder(code):
            # reference accesssion.id instead of accession_id since
            # setting the accession on the model doesn't set the
            # accession_id until the session is flushed
            code = utils.utf8(code)
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
        self.view.widgets.pad_ok_button.set_sensitive(sensitive)
        self.view.widgets.pad_next_button.set_sensitive(sensitive)


    def set_model_attr(self, field, value, validator=None):
        #debug('set_model_attr(%s, %s)' % (field, value))
        super(AddPlantEditorPresenter, self)\
            .set_model_attr(field, value, validator)
        self.__dirty = True
        self.refresh_sensitivity()


    def on_loc_button_clicked(self, button, cmd=None):
        location = self.model.location
        if cmd is 'edit':
            combo = self.view.widgets.plant_loc_comboentry
            LocationEditor(location, parent=self.view.get_window()).start()
            self.session.refresh(location)
            self.view.set_widget_value(combo, location)
        else:
            # TODO: see if the location editor returns the new
            # location and if so set it directly
            LocationEditor(parent=self.view.get_window()).start()


    def refresh_view(self):
        for widget, field in self.widget_to_field_map.iteritems():
            value = getattr(self.model, field)
            self.view.set_widget_value(widget, value)

        self.view.set_widget_value('plant_acc_status_combo',
                                   acc_status_values[self.model.acc_status],
                                   index=1)
        self.view.set_widget_value('plant_acc_type_combo',
                                   acc_type_values[self.model.acc_type],
                                   index=1)
        self.refresh_sensitivity()


    def start(self):
        r = self.view.start()
        return r



class AddPlantEditor(GenericModelViewPresenterEditor):

    # label = _('Plant')
    # mnemonic_label = _('_Plant')

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
        super(AddPlantEditor, self).__init__(model, parent)
        if not parent and bauble.gui:
            parent = bauble.gui.window
        self.parent = parent
        self._committed = []

        view = AddPlantEditorView(parent=self.parent)
        self.presenter = AddPlantEditorPresenter(self.model, view)

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


    def commit_changes(self):
        """
        """
        if ',' not in self.model.code and '-' not in self.model.code and \
                self.model not in self.session.new:
            self._committed.append(self.model)
            super(AddPlantEditor, self).commit_changes()
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
            super(AddPlantEditor, self).commit_changes()
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
        elif self.presenter.dirty() and utils.yes_no_dialog(not_ok_msg) \
                or not self.presenter.dirty():
            self.session.rollback()
            return True
        else:
            return False

#        # respond to responses
        more_committed = None
        if response == self.RESPONSE_NEXT:
            self.presenter.cleanup()
            e = AddPlantEditor(Plant(accession=self.model.accession),
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

        self.presenter.cleanup()
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
        InfoExpander.__init__(self, _("General"), widgets)
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
        self.set_widget_value('location_data',row.location.name)
        self.set_widget_value('status_data', acc_status_values[row.acc_status],
                              False)
        self.set_widget_value('type_data', acc_type_values[row.acc_type],
                              False)


class TransferExpander(InfoExpander):
    """
    Tranfer Expander
    """

    def __init__(self, widgets):
        """
        """
        super(TransferExpander, self).__init__(_('Transfers'), widgets)


    def update(self, row):
        '''
        '''
        # date: src to dest
        # TODO: remove previous children
        debug(row.transfers)
        for transfer in row.transfers:
            s = _('%s: %s to %s by') % (transfer.date, transfer.from_location,
                                     transfer.to_location, transfer.user)
            debug(s)
            self.vbox.pack_start(gtk.Label(s))
        self.vbox.show_all()
        #self.set_widget_value('notes_data', row.notes)


class NotesExpander(InfoExpander):
    """
    the plants notes
    """

    def __init__(self, widgets):
        '''
        '''
        InfoExpander.__init__(self, _("Notes"), widgets)
        notes_box = self.widgets.notes_box
        self.widgets.remove_parent(notes_box)
        self.vbox.pack_start(notes_box)

        # set up sorting
        treeview = self.widgets.notes_treeview
        for i in range(3):
            treeview.get_column(i).set_sort_column_id(i)

        # TODO: we might have to get the datetime object for this to
        # work correctly in case the date string format changes

        # sort by date by default
        treeview.get_model().set_sort_column_id(0, gtk.SORT_DESCENDING)

        # change the wrap width when the column width changes on the
        # notes column
        self.widgets.note_cell.props.wrap_mode = gtk.WRAP_WORD
        def on_width(*args):
            width = self.widgets.note_column.props.width
            self.widgets.note_cell.props.wrap_width = width
        self.widgets.note_column.connect('notify::width', on_width)

        # vertically align the text in the cells to the top
        self.widgets.date_cell.props.yalign = 0.0
        self.widgets.category_cell.props.yalign = 0.0
        self.widgets.note_cell.props.yalign = 0.0


    def update(self, row):
        '''
        '''
        model = self.widgets.notes_treeview.get_model()
        model.clear()
        for note in row.notes:
            model.append([note.date, note.category, note.note])
        # the 25 is arbitrary but should show enough of the tree for
        # the notes but not all the notes
        self.widgets.notes_treeview.set_size_request(-1, len(row.notes)*25)



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
        self.widgets = utils.load_widgets(filename)
        self.general = GeneralPlantExpander(self.widgets)
        self.add_expander(self.general)

        self.transfers = TransferExpander(self.widgets)
        self.add_expander(self.transfers)

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
        self.transfers.update(row)
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
