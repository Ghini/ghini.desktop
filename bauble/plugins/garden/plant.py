# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Brett Adams
# Copyright 2015-2017 Mario Frasca <mario@anche.no>.
# Copyright 2017 Jardín Botánico de Quito
#
# This file is part of ghini.desktop.
#
# ghini.desktop is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ghini.desktop is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ghini.desktop. If not, see <http://www.gnu.org/licenses/>.
#

"""
Defines the plant table and handled editing plants
"""

import os
import traceback
from random import random

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

import gtk


from sqlalchemy import and_, func
from sqlalchemy import ForeignKey, Column, Unicode, Integer, Boolean, \
    UnicodeText, UniqueConstraint
from sqlalchemy.orm import relation, backref, object_mapper, validates
from sqlalchemy.orm.session import object_session
from sqlalchemy.exc import DBAPIError, OperationalError

import bauble.db as db
from bauble.error import CheckConditionError
from bauble.editor import GenericEditorView, GenericEditorPresenter, \
    GenericModelViewPresenterEditor, NotesPresenter, PicturesPresenter
import bauble.meta as meta
import bauble.paths as paths
from bauble.plugins.plants.species_model import Species
from bauble.plugins.garden.location import Location, LocationEditor
from bauble.plugins.garden.propagation import PlantPropagation
import bauble.prefs as prefs
from bauble.search import SearchStrategy
import bauble.btypes as types
import bauble.utils as utils
from bauble.view import InfoBox, InfoExpander, PropertiesExpander, \
    select_in_search_results, Action
import bauble.view as view

# TODO: might be worthwhile to have a label or textview next to the
# location combo that shows the description of the currently selected
# location

plant_delimiter_key = u'plant_delimiter'
default_plant_delimiter = u'.'


def edit_callback(plants):
    e = PlantEditor(model=plants[0])
    return e.start() is not None


def branch_callback(plants):
    if plants[0].quantity <= 1:
        msg = _("Not enough plants to split.  A plant should have at least "
                "a quantity of 2 before it can be divided")
        utils.message_dialog(msg, gtk.MESSAGE_WARNING)
        return

    e = PlantEditor(model=plants[0], branch_mode=True)
    return e.start() is not None


def remove_callback(plants):
    s = ', '.join([str(p) for p in plants])
    msg = _("Are you sure you want to remove the following plants?\n\n%s") \
        % utils.xml_safe(s)
    if not utils.yes_no_dialog(msg):
        return

    session = db.Session()
    for plant in plants:
        obj = session.query(Plant).get(plant.id)
        session.delete(obj)
    try:
        session.commit()
    except Exception, e:
        msg = _('Could not delete.\n\n%s') % utils.xml_safe(e)

        utils.message_details_dialog(msg, traceback.format_exc(),
                                     type=gtk.MESSAGE_ERROR)
    finally:
        session.close()
    return True


edit_action = Action('plant_edit', _('_Edit'),
                     callback=edit_callback,
                     accelerator='<ctrl>e', multiselect=True)

branch_action = Action('plant_branch', _('_Split'),
                       callback=branch_callback,
                       accelerator='<ctrl>b')

remove_action = Action('plant_remove', _('_Delete'),
                       callback=remove_callback,
                       accelerator='<ctrl>Delete', multiselect=True)

plant_context_menu = [
    edit_action, branch_action, remove_action, ]


def get_next_code(acc):
    """
    Return the next available plant code for an accession.

    This function should be specific to the institution.

    If there is an error getting the next code the None is returned.
    """
    # auto generate/increment the accession code
    session = db.Session()
    from bauble.plugins.garden import Accession
    codes = session.query(Plant.code).join(Accession).\
        filter(Accession.id == acc.id).all()
    next = 1
    if codes:
        try:
            next = max([int(code[0]) for code in codes])+1
        except Exception, e:
            logger.debug(e)
            return None
    return utils.utf8(next)


def is_code_unique(plant, code):
    """
    Return True/False if the code is a unique Plant code for accession.

    This method will also take range values for code that can be passed
    to utils.range_builder()
    """
    # if the range builder only creates one number then we assume the
    # code is not a range and so we test against the string version of
    # code
    codes = map(utils.utf8, utils.range_builder(code))  # test if a range
    if len(codes) == 1:
        codes = [utils.utf8(code)]

    # reference accesssion.id instead of accession_id since
    # setting the accession on the model doesn't set the
    # accession_id until the session is flushed
    session = db.Session()
    from bauble.plugins.garden import Accession
    count = session.query(Plant).join('accession').\
        filter(and_(Accession.id == plant.accession.id,
                    Plant.code.in_(codes))).count()
    session.close()
    return count == 0


class PlantSearch(SearchStrategy):

    def __init__(self):
        super(PlantSearch, self).__init__()

    def search(self, text, session):
        """returns a result if the text looks like a quoted plant code

        special search strategy, can't be obtained in MapperSearch
        """
        super(PlantSearch, self).search(text, session)

        if text[0] == text[-1] and text[0] in ['"', "'"]:
            text = text[1:-1]
        else:
            logger.debug("text is not quoted, should strategy apply?")
            #return []
        delimiter = Plant.get_delimiter()
        if delimiter not in text:
            logger.debug("delimiter not found, can't split the code")
            return []
        acc_code, plant_code = text.rsplit(delimiter, 1)
        logger.debug("ac: %s, pl: %s" % (acc_code, plant_code))

        try:
            from bauble.plugins.garden import Accession
            query = session.query(Plant).filter(
                Plant.code == unicode(plant_code)).join(Accession).filter(
                utils.ilike(Accession.code, u'%%%s' % unicode(acc_code)))
            return query.all()
        except Exception, e:
            logger.debug("%s %s" % (e.__class__.name, e))
            return []


def as_dict(self):
    result = db.Serializable.as_dict(self)
    result['plant'] = (self.plant.accession.code +
                       Plant.get_delimiter() + self.plant.code)
    return result

def retrieve(cls, session, keys):
    q = session.query(cls)
    if 'plant' in keys:
        acc_code, plant_code = keys['plant'].rsplit(
            Plant.get_delimiter(), 1)
        q = q.join(
            Plant).filter(Plant.code == unicode(plant_code)).join(
            Accession).filter(Accession.code == unicode(acc_code))
    if 'date' in keys:
        q = q.filter(cls.date == keys['date'])
    if 'category' in keys:
        q = q.filter(cls.category == keys['category'])
    try:
        return q.one()
    except:
        return None

def compute_serializable_fields(cls, session, keys):
    'plant is given as text, should be object'
    result = {'plant': None}

    acc_code, plant_code = keys['plant'].rsplit(
        Plant.get_delimiter(), 1)
    logger.debug("acc-plant: %s-%s" % (acc_code, plant_code))
    q = session.query(Plant).filter(
        Plant.code == unicode(plant_code)).join(
        Accession).filter(Accession.code == unicode(acc_code))
    plant = q.one()

    result['plant'] = plant

    return result

PlantNote = db.make_note_class('Plant', compute_serializable_fields, as_dict, retrieve)


# TODO: some of these reasons are specific to UBC and could probably be culled.
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
    parent_plant_id = Column(Integer, ForeignKey('plant.id'))

    # - if to_location_id is None changeis a removal
    # - if from_location_id is None then this change is a creation
    # - if to_location_id != from_location_id change is a transfer
    from_location_id = Column(Integer, ForeignKey('location.id'))
    to_location_id = Column(Integer, ForeignKey('location.id'))

    # the name of the person who made the change
    person = Column(Unicode(64))

    quantity = Column(Integer, autoincrement=False, nullable=False)
    note_id = Column(Integer, ForeignKey('plant_note.id'))

    reason = Column(types.Enum(values=change_reasons.keys(),
                               translations=change_reasons))

    # date of change
    date = Column(types.DateTime, default=func.now())

    # relations
    plant = relation('Plant', uselist=False,
                     primaryjoin='PlantChange.plant_id == Plant.id',
                     backref=backref('changes', cascade='all, delete-orphan'))
    parent_plant = relation(
        'Plant', uselist=False,
        primaryjoin='PlantChange.parent_plant_id == Plant.id',
        backref=backref('branches', cascade='delete, delete-orphan'))

    from_location = relation(
        'Location', primaryjoin='PlantChange.from_location_id == Location.id')
    to_location = relation(
        'Location', primaryjoin='PlantChange.to_location_id == Location.id')


condition_values = {
    u'Excellent': _('Excellent'),
    u'Good': _('Good'),
    u'Fair': _('Fair'),
    u'Poor': _('Poor'),
    u'Questionable': _('Questionable'),
    u'Indistinguishable': _('Indistinguishable Mass'),
    u'UnableToLocate': _('Unable to Locate'),
    u'Dead': _('Dead'),
    None: ''}

flowering_values = {
    u'Immature': _('Immature'),
    u'Flowering': _('Flowering'),
    u'Old': _('Old Flowers'),
    None: ''}

fruiting_values = {
    u'Unripe': _('Unripe'),
    u'Ripe': _('Ripe'),
    None: '',
}

# TODO: should sex be recorded at the species, accession or plant
# level or just as part of a check since sex can change in some species
sex_values = {
    u'Female': _('Female'),
    u'Male': _('Male'),
    u'Both': ''}

# class Container(db.Base):
#     __tablename__ = 'container'
#     __mapper_args__ = {'order_by': 'name'}
#     code = Column(Unicode)
#     name = Column(Unicode)


class PlantStatus(db.Base):
    """
    date: date checked
    status: status of plant
    comment: comments on check up
    checked_by: person who did the check
    """
    __tablename__ = 'plant_status'
    date = Column(types.Date, default=func.now())
    condition = Column(types.Enum(values=condition_values.keys(),
                                  translations=condition_values))
    comment = Column(UnicodeText)
    checked_by = Column(Unicode(64))

    flowering_status = Column(types.Enum(values=flowering_values.keys(),
                                         translations=flowering_values))
    fruiting_status = Column(types.Enum(values=fruiting_values.keys(),
                                        translations=fruiting_values))

    autumn_color_pct = Column(Integer, autoincrement=False)
    leaf_drop_pct = Column(Integer, autoincrement=False)
    leaf_emergence_pct = Column(Integer, autoincrement=False)

    sex = Column(types.Enum(values=sex_values.keys(),
                            translations=sex_values))

    # TODO: needs container table
    #container_id = Column(Integer)


acc_type_values = {u'Plant': _('Planting'),
                   u'Seed': _('Seed/Spore'),
                   u'Vegetative': _('Vegetative Part'),
                   u'Tissue': _('Tissue Culture'),
                   u'Other': _('Other'),
                   None: ''}


class Plant(db.Base, db.Serializable, db.DefiningPictures, db.WithNotes):
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

        *accession_id*: :class:`sqlalchemy.types.Integer`
            Required.

        *location_id*: :class:`sqlalchemy.types.Integer`
            Required.

    :Properties:
        *accession*:
            The accession for this plant.
        *location*:
            The location for this plant.
        *notes*:
            The notes for this plant.

    :Constraints:
        The combination of code and accession_id must be unique.
    """
    __tablename__ = 'plant'
    __table_args__ = (UniqueConstraint('code', 'accession_id'), {})
    __mapper_args__ = {'order_by': ['plant.accession_id', 'plant.code']}

    # columns
    code = Column(Unicode(6), nullable=False)

    @validates('code')
    def validate_stripping(self, key, value):
        if value is None:
            return None
        return value.strip()

    acc_type = Column(types.Enum(values=acc_type_values.keys(),
                                 translations=acc_type_values),
                      default=None)
    memorial = Column(Boolean, default=False)
    quantity = Column(Integer, autoincrement=False, nullable=False)

    accession_id = Column(Integer, ForeignKey('accession.id'), nullable=False)
    location_id = Column(Integer, ForeignKey('location.id'), nullable=False)

    propagations = relation('Propagation', cascade='all, delete-orphan',
                            single_parent=True,
                            secondary=PlantPropagation.__table__,
                            backref=backref('plant', uselist=False))

    _delimiter = None

    def search_view_markup_pair(self):
        '''provide the two lines describing object for SearchView row.
        '''
        import inspect
        logger.debug('entering search_view_markup_pair %s, %s' % (
            self, str(inspect.stack()[1])))
        sp_str = self.accession.species_str(markup=True)
        dead_color = "#9900ff"
        if self.quantity <= 0:
            dead_markup = '<span foreground="%s">%s</span>' % \
                (dead_color, utils.xml_safe(self))
            return dead_markup, sp_str
        else:
            located_counted = ('%s <span foreground="#555555" size="small" '
                               'weight="light">- %s alive in %s</span>') % (
                utils.xml_safe(self), self.quantity, utils.xml_safe(self.location))
            return located_counted, sp_str

    @classmethod
    def get_delimiter(cls, refresh=False):
        """
        Get the plant delimiter from the BaubleMeta table.

        The delimiter is cached the first time it is retrieved.  To refresh
        the delimiter from the database call with refresh=True.

        """
        if cls._delimiter is None or refresh:
            cls._delimiter = meta.get_default(
                plant_delimiter_key, default_plant_delimiter).value
        return cls._delimiter

    @property
    def date_of_death(self):
        if self.quantity != 0:
            return None
        try:
            return max([i.date for i in self.changes])
        except ValueError:
            return None

    def _get_delimiter(self):
        return Plant.get_delimiter()
    delimiter = property(lambda self: self._get_delimiter())

    def __str__(self):
        return "%s%s%s" % (self.accession, self.delimiter, self.code)

    def duplicate(self, code=None, session=None):
        """Return a Plant that is a flat (not deep) duplicate of self. For notes,
        changes and propagations, you should refer to the original plant.

        """
        plant = Plant()
        if not session:
            session = object_session(self)
            if session:
                session.add(plant)

        ignore = ('id', 'code', 'changes', 'notes', 'propagations', '_created')
        properties = filter(lambda p: p.key not in ignore,
                            object_mapper(self).iterate_properties)
        for prop in properties:
            setattr(plant, prop.key, getattr(self, prop.key))
        plant.code = code

        return plant

    def markup(self):
        return "%s%s%s (%s)" % (self.accession, self.delimiter, self.code,
                                self.accession.species_str(markup=True))

    def as_dict(self):
        result = db.Serializable.as_dict(self)
        result['accession'] = self.accession.code
        result['location'] = self.location.code
        return result

    @classmethod
    def compute_serializable_fields(cls, session, keys):
        result = {'accession': None,
                  'location': None}

        acc_keys = {}
        acc_keys.update(keys)
        acc_keys['code'] = keys['accession']
        accession = Accession.retrieve_or_create(
            session, acc_keys, create=(
                'taxon' in acc_keys and 'rank' in acc_keys))

        loc_keys = {}
        loc_keys.update(keys)
        if 'location' in keys:
            loc_keys['code'] = keys['location']
            location = Location.retrieve_or_create(
                session, loc_keys)
        else:
            location = None

        result['accession'] = accession
        result['location'] = location

        return result

    @classmethod
    def retrieve(cls, session, keys):
        try:
            return session.query(cls).filter(
                cls.code == keys['code']).join(Accession).filter(
                Accession.code == keys['accession']).one()
        except:
            return None

    def top_level_count(self):
        sd = self.accession.source and self.accession.source.source_detail
        return {(1, 'Plantings'): 1,
                (2, 'Accessions'): set([self.accession.id]),
                (3, 'Species'): set([self.accession.species.id]),
                (4, 'Genera'): set([self.accession.species.genus.id]),
                (5, 'Families'): set([self.accession.species.genus.family.id]),
                (6, 'Living plants'): self.quantity,
                (7, 'Locations'): set([self.location.id]),
                (8, 'Sources'): set(sd and [sd.id] or []),
                }


from bauble.plugins.garden.accession import Accession


class PlantEditorView(GenericEditorView):

    _tooltips = {
        'plant_code_entry': _('The planting code must be a unique code for '
                              'the accession.  You may also use ranges '
                              'like 1,2,7 or 1-3 to create multiple '
                              'plants.'),
        'plant_acc_entry': _('The accession must be selected from the list '
                             'of completions.  To add an accession use the '
                             'Accession editor.'),
        'plant_loc_comboentry': _(
            'The location of the planting in your collection.'),
        'plant_acc_type_combo': _('The type of the plant material.\n\n'
                                  'Possible values: %s') % (
            ', '.join(acc_type_values.values())),
        'plant_loc_add_button': _('Create a new location.'),
        'plant_loc_edit_button': _('Edit the selected location.'),
        'prop_add_button': _(
            'Create a new propagation record for this plant.'),
        'pad_cancel_button': _('Cancel your changes.'),
        'pad_ok_button': _('Save your changes.'),
        'pad_next_button': _(
            'Save your changes and add another plant.'),
        'pad_nextaccession_button': _(
            'Save your changes and add another accession.'),
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
                               minimum_key_length=2)
        self.init_translatable_combo('plant_acc_type_combo', acc_type_values)
        self.init_translatable_combo('reason_combo', change_reasons)
        utils.setup_date_button(self, 'plant_date_entry', 'plant_date_button')
        self.widgets.notebook.set_current_page(0)

    def get_window(self):
        return self.widgets.plant_editor_dialog

    def save_state(self):
        pass

    def restore_state(self):
        pass


class PlantEditorPresenter(GenericEditorPresenter):

    widget_to_field_map = {'plant_code_entry': 'code',
                           'plant_acc_entry': 'accession',
                           'plant_loc_comboentry': 'location',
                           'plant_acc_type_combo': 'acc_type',
                           'plant_memorial_check': 'memorial',
                           'plant_quantity_entry': 'quantity'
                           }

    PROBLEM_DUPLICATE_PLANT_CODE = str(random())
    PROBLEM_INVALID_QUANTITY = str(random())

    def __init__(self, model, view):
        '''
        :param model: should be an instance of Plant class
        :param view: should be an instance of PlantEditorView
        '''
        super(PlantEditorPresenter, self).__init__(model, view)
        self.create_toolbar()
        self.session = object_session(model)
        self._original_accession_id = self.model.accession_id
        self._original_code = self.model.code

        # if the model is in session.new then it might be a branched
        # plant so don't store it....is this hacky?
        self.upper_quantity_limit = float('inf')
        if model in self.session.new:
            self._original_quantity = None
            self.lower_quantity_limit = 1
        else:
            self._original_quantity = self.model.quantity
            self.lower_quantity_limit = 0
        self._dirty = False

        # set default values for acc_type
        if self.model.id is None and self.model.acc_type is None:
            self.model.acc_type = u'Plant'

        notes_parent = self.view.widgets.notes_parent_box
        notes_parent.foreach(notes_parent.remove)
        self.notes_presenter = NotesPresenter(self, 'notes', notes_parent)

        pictures_parent = self.view.widgets.pictures_parent_box
        pictures_parent.foreach(pictures_parent.remove)
        self.pictures_presenter = PicturesPresenter(
            self, 'notes', pictures_parent)

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

        self.refresh_view()  # put model values in view

        self.change = PlantChange()
        self.session.add(self.change)
        self.change.plant = self.model
        self.change.from_location = self.model.location
        self.change.quantity = self.model.quantity

        def on_reason_changed(combo):
            it = combo.get_active_iter()
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
            return query.filter(Accession.code.like(unicode('%s%%' % text))).\
                order_by(Accession.code)

        def on_select(value):
            self.set_model_attr('accession', value)
            # reset the plant code to check that this is a valid code for the
            # new accession, fixes bug #103946
            self.view.widgets.acc_species_label.set_markup('')
            if value is not None:
                sp_str = self.model.accession.species.str(markup=True)
                self.view.widgets.acc_species_label.set_markup(sp_str)
                self.view.widgets.plant_code_entry.emit('changed')
        self.assign_completions_handler('plant_acc_entry', acc_get_completions,
                                        on_select=on_select)
        if self.model.accession:
            sp_str = self.model.accession.species.str(markup=True)
        else:
            sp_str = ''
        self.view.widgets.acc_species_label.set_markup(sp_str)

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
        if self.model.quantity == 0:
            self.view.widgets.notebook.set_sensitive(False)
            msg = _('This plant is marked with quantity zero. \n'
                    'In practice, it is not any more part of the collection. \n'
                    'Are you sure you want to edit it anyway?')
            box = None
            def on_response(button, response):
                self.view.remove_box(box)
                if response:
                    self.view.widgets.notebook.set_sensitive(True)
            box = self.view.add_message_box(utils.MESSAGE_BOX_YESNO)
            box.message = msg
            box.on_response = on_response
            box.show()
            self.view.add_box(box)

    def is_dirty(self):
        return (self.pictures_presenter.is_dirty() or
                self.notes_presenter.is_dirty() or
                self.prop_presenter.is_dirty() or
                self._dirty)

    def on_date_entry_changed(self, entry, *args):
        self.change.date = entry.props.text

    def on_quantity_changed(self, entry, *args):
        value = entry.props.text
        try:
            value = int(value)
        except ValueError, e:
            logger.debug(e)
            value = None
        self.set_model_attr('quantity', value)
        if value < self.lower_quantity_limit or value >= self.upper_quantity_limit:
            self.add_problem(self.PROBLEM_INVALID_QUANTITY, entry)
        else:
            self.remove_problem(self.PROBLEM_INVALID_QUANTITY, entry)
        self.refresh_sensitivity()
        if value is None:
            return
        if self._original_quantity:
            self.change.quantity = \
                abs(self._original_quantity-self.model.quantity)
        else:
            self.change.quantity = self.model.quantity
        self.refresh_view()

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

        # add a problem if the code is not unique but not if it's the
        # same accession and plant code that we started with when the
        # editor was opened
        if self.model.code is not None and not \
                is_code_unique(self.model, self.model.code) and not \
                (self._original_accession_id == self.model.accession.id and
                 self.model.code == self._original_code):

                self.add_problem(self.PROBLEM_DUPLICATE_PLANT_CODE, entry)
        else:
            # remove_problem() won't complain if problem doesn't exist
            self.remove_problem(self.PROBLEM_DUPLICATE_PLANT_CODE, entry)
            entry.modify_bg(gtk.STATE_NORMAL, None)
            entry.modify_base(gtk.STATE_NORMAL, None)
            entry.queue_draw()

        self.refresh_sensitivity()

    def refresh_sensitivity(self):
        logger.debug('refresh_sensitivity()')
        try:
            logger.debug((self.model.accession is not None,
                          self.model.code is not None,
                          self.model.location is not None,
                          self.model.quantity is not None,
                          self.is_dirty(),
                          len(self.problems) == 0))
        except OperationalError, e:
            logger.debug('(%s)%s' % (type(e), e))
            return
        logger.debug(self.problems)

        # TODO: because we don't call refresh_sensitivity() every time a
        # character is entered then the edit button doesn't sensitize
        # properly
        #
        # combo_entry = self.view.widgets.plant_loc_comboentry.child
        # self.view.widgets.plant_loc_edit_button.\
        #     set_sensitive(self.model.location is not None \
        #                       and not self.has_problems(combo_entry))
        sensitive = (self.model.accession is not None and
                     self.model.code is not None and
                     self.model.location is not None and
                     self.model.quantity is not None) \
            and self.is_dirty() and len(self.problems) == 0
        self.view.widgets.pad_ok_button.set_sensitive(sensitive)
        self.view.widgets.pad_next_button.set_sensitive(sensitive)
        self.view.widgets.split_planting_button.props.visible = False

    def set_model_attr(self, field, value, validator=None):
        logger.debug('set_model_attr(%s, %s)' % (field, value))
        super(PlantEditorPresenter, self)\
            .set_model_attr(field, value, validator)
        self._dirty = True
        self.refresh_sensitivity()

    def on_loc_button_clicked(self, button, cmd=None):
        location = self.model.location
        combo = self.view.widgets.plant_loc_comboentry
        if cmd is 'edit' and location:
            LocationEditor(location, parent=self.view.get_window()).start()
            self.session.refresh(location)
            self.view.widget_set_value(combo, location)
        else:
            editor = LocationEditor(parent=self.view.get_window())
            if editor.start():
                location = self.model.location = editor.presenter.model
                self.session.add(location)
                self.remove_problem(None, combo)
                self.view.widget_set_value(combo, location)
                self.set_model_attr('location', location)

    def refresh_view(self):
        # TODO: is this really relevant since this editor only creates new
        # plants?  it also won't work while testing, and removing it while
        # testing has no impact on test results.
        if prefs.testing:
            return
        for widget, field in self.widget_to_field_map.iteritems():
            value = getattr(self.model, field)
            self.view.widget_set_value(widget, value)
            logger.debug('%s: %s = %s' % (widget, field, value))

        self.view.widget_set_value('plant_acc_type_combo',
                                   acc_type_values[self.model.acc_type],
                                   index=1)
        self.view.widgets.plant_memorial_check.set_inconsistent(False)
        self.view.widgets.plant_memorial_check.\
            set_active(self.model.memorial is True)

        self.refresh_sensitivity()

    def cleanup(self):
        super(PlantEditorPresenter, self).cleanup()
        msg_box_parent = self.view.widgets.message_box_parent
        map(msg_box_parent.remove, msg_box_parent.get_children())
        # the entry is made not editable for branch mode
        self.view.widgets.plant_acc_entry.props.editable = True
        self.view.get_window().props.title = _('Plant Editor')

    def start(self):
        return self.view.start()


def move_quantity_between_plants(from_plant, to_plant, to_plant_change=None):
    ######################################################
    s = object_session(to_plant)
    if to_plant_change is None:
        to_plant_change = PlantChange()
        s.add(to_plant_change)
    from_plant_change = PlantChange()
    s.add(from_plant_change)
    ######################################################
    from_plant.quantity -= to_plant.quantity
    ######################################################
    to_plant_change.plant = to_plant
    to_plant_change.parent_plant = from_plant
    to_plant_change.quantity = to_plant.quantity
    to_plant_change.to_location = to_plant.location
    to_plant_change.from_location = from_plant.location
    ######################################################
    from_plant_change.plant = from_plant
    from_plant_change.quantity = to_plant.quantity
    from_plant_change.to_location = to_plant.location
    from_plant_change.from_location = from_plant.location


class PlantEditor(GenericModelViewPresenterEditor):

    # these have to correspond to the response values in the view
    RESPONSE_NEXT = 22
    ok_responses = (RESPONSE_NEXT,)

    def __init__(self, model=None, parent=None, branch_mode=False):
        '''
        :param model: Plant instance or None
        :param parent: None
        :param branch_mode:
        '''
        if branch_mode:
            if model is None:
                raise CheckConditionError("branch_mode requires a model")
            elif object_session(model) and model in object_session(model).new:
                raise CheckConditionError(_("cannot split a new plant"))

        if model is None:
            model = Plant()

        self.branched_plant = None
        if branch_mode:
            # we work on 'model', we keep the original at 'branched_plant'.
            self.branched_plant, model = model, model.duplicate(code=None)
            model.quantity = 1

        super(PlantEditor, self).__init__(model, parent)

        if self.branched_plant and self.branched_plant not in self.session:
            # make a copy of the branched plant for this session
            self.branched_plant = self.session.merge(self.branched_plant)

        import bauble
        if not parent and bauble.gui:
            parent = bauble.gui.window
        self.parent = parent
        self._committed = []

        view = PlantEditorView(parent=self.parent)
        self.presenter = PlantEditorPresenter(self.model, view)
        if self.branched_plant:
            self.presenter.upper_quantity_limit = self.branched_plant.quantity

        # set default focus
        if self.model.accession is None:
            view.widgets.plant_acc_entry.grab_focus()
        else:
            view.widgets.plant_code_entry.grab_focus()

    def compute_plant_split_changes(self):
        move_quantity_between_plants(from_plant=self.branched_plant,
                                     to_plant=self.model,
                                     to_plant_change=self.presenter.change)

    def commit_changes(self):
        """
        """
        codes = utils.range_builder(self.model.code)
        if len(codes) <= 1 or self.model not in self.session.new \
                and not self.branched_plant:
            change = self.presenter.change
            if self.branched_plant:
                self.compute_plant_split_changes()
            elif change.quantity is None \
                    or (change.quantity == self.model.quantity and
                        change.from_location == self.model.location and
                        change.quantity == self.presenter._original_quantity):
                # if quantity and location haven't changed, nothing changed.
                utils.delete_or_expunge(change)
                self.model.change = None
            else:
                if self.model.location != change.from_location:
                    # transfer
                    change.to_location = self.model.location
                elif self.model.quantity > self.presenter._original_quantity \
                        and not change.to_location:
                    # additions should use to_location
                    change.to_location = self.model.location
                    change.from_location = None
                else:
                    # removal
                    change.quantity = -change.quantity
            super(PlantEditor, self).commit_changes()
            self._committed.append(self.model)
            return

        # this method will create new plants from self.model even if
        # the plant code is not a range....it's a small price to pay
        plants = []
        mapper = object_mapper(self.model)

        # TODO: precompute the _created and _last_updated attributes
        # in case we have to create lots of plants. it won't be too slow

        # we have to set the properties on the new objects
        # individually since session.merge won't create a new object
        # since the object is already in the session
        for code in codes:
            new_plant = Plant()
            self.session.add(new_plant)

            # TODO: can't we use Plant.duplicate here?
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
                if self.presenter.is_dirty():
                    # commit_changes() will append the commited plants
                    # to self._committed
                    self.commit_changes()
            except DBAPIError, e:
                exc = traceback.format_exc()
                logger.debug(exc)
                msg = _('Error committing changes.\n\n%s') % e.orig
                utils.message_details_dialog(msg, str(e), gtk.MESSAGE_ERROR)
                self.session.rollback()
                return False
            except Exception, e:
                msg = _('Unknown error when committing changes. See the '
                        'details for more information.\n\n%s') \
                    % utils.xml_safe(e)
                logger.debug(traceback.format_exc())
                utils.message_details_dialog(msg, traceback.format_exc(),
                                             gtk.MESSAGE_ERROR)
                self.session.rollback()
                return False
        elif (self.presenter.is_dirty() and utils.yes_no_dialog(not_ok_msg)) \
                or not self.presenter.is_dirty():
            self.session.rollback()
            return True
        else:
            return False

        # respond to responses
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
                  'the database before you can add plants.\n\nWould you '\
                  'like to open the Location editor?'
            if utils.yes_no_dialog(msg):
                # cleanup in case we start a new PlantEditor
                self.presenter.cleanup()
                sub_editor = LocationEditor()
                self._commited = sub_editor.start()

        if self.branched_plant:
            # set title if in branch mode
            self.presenter.view.get_window().props.title += \
                utils.utf8(' - %s' % _('Split Mode'))
            message_box_parent = self.presenter.view.widgets.message_box_parent
            map(message_box_parent.remove, message_box_parent.get_children())
            msg = _('Splitting from %(plant_code)s.  The quantity will '
                    'be subtracted from %(plant_code)s') \
                % {'plant_code': str(self.branched_plant)}
            box = self.presenter.view.add_message_box(utils.MESSAGE_BOX_INFO)
            box.message = msg
            box.show_all()

            # don't allow editing the accession code in a branched plant
            self.presenter.view.widgets.plant_acc_entry.props.editable = False

        if not sub_editor:
            while True:
                response = self.presenter.start()
                self.presenter.view.save_state()
                if self.handle_response(response):
                    break

        self.session.close()  # cleanup session
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

        self.widget_set_value('acc_code_data', '<big>%s</big>' %
                              utils.xml_safe(unicode(head)),
                              markup=True)
        self.widget_set_value('plant_code_data', '<big>%s</big>' %
                              utils.xml_safe(unicode(tail)), markup=True)
        self.widget_set_value('name_data',
                              row.accession.species_str(markup=True),
                              markup=True)
        self.widget_set_value('location_data', str(row.location))
        self.widget_set_value('quantity_data', row.quantity)

        status_str = _('Alive')
        if row.quantity <= 0:
            status_str = _('Dead')
        self.widget_set_value('status_data', status_str, False)

        self.widget_set_value('type_data', acc_type_values[row.acc_type],
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
        self.vbox.props.spacing = 5
        self.table = gtk.Table()
        self.vbox.pack_start(self.table, expand=False, fill=False)
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

        def _cmp(x, y):
            """
            Sort by change.date and then change._created.  If they are
            equal then removals sort before transfers.
            """
            if x.date < y.date:
                return -1
            elif x.date > y.date:
                return 1
            elif x.date == y.date and x._created < y._created:
                return -1
            elif x.date == y.date and x._created > y._created:
                return 1
            elif x.quantity < 0:
                return -1
            else:
                return 1

        for change in sorted(row.changes, cmp=_cmp, reverse=True):
            try:
                seconds, divided_plant = min(
                    [(abs((i.plant._created - change.date).total_seconds()), i.plant)
                     for i in row.branches])
                if seconds > 3:
                    divided_plant = None
            except:
                divided_plant = None

            date = change.date.strftime(date_format)
            label = gtk.Label('%s:' % date)
            label.set_alignment(0, 0)
            self.table.attach(label, 0, 1, current_row, current_row+1,
                              xoptions=gtk.FILL)
            if change.to_location and change.from_location:
                s = '%(quantity)s Transferred from %(from_loc)s to %(to)s' % \
                    dict(quantity=change.quantity,
                         from_loc=change.from_location, to=change.to_location)
            elif change.quantity < 0:
                s = '%(quantity)s Removed from %(location)s' % \
                    dict(quantity=-change.quantity,
                         location=change.from_location)
            elif change.quantity > 0:
                s = '%(quantity)s Added to %(location)s' % \
                    dict(quantity=change.quantity, location=change.to_location)
            else:
                s = '%s: %s -> %s' % (change.quantity, change.from_location,
                                      change.to_location)
            if change.reason is not None:
                s += '\n%s' % change_reasons[change.reason]
            label = gtk.Label(s)
            label.set_alignment(0, .5)
            self.table.attach(label, 1, 2, current_row, current_row+1,
                              xoptions=gtk.FILL)
            current_row += 1
            if change.parent_plant:
                s = _('<i>Split from %(plant)s</i>') % \
                    dict(plant=utils.xml_safe(change.parent_plant))
                label = gtk.Label()
                label.set_alignment(0.0, 0.0)
                label.set_markup(s)
                eb = gtk.EventBox()
                eb.add(label)
                self.table.attach(eb, 1, 2, current_row, current_row+1,
                                  xoptions=gtk.FILL)

                def on_clicked(widget, event, parent):
                    select_in_search_results(parent)

                utils.make_label_clickable(label, on_clicked,
                                           change.parent_plant)
                current_row += 1
            if divided_plant:
                s = _('<i>Split as %(plant)s</i>') % \
                    dict(plant=utils.xml_safe(divided_plant))
                label = gtk.Label()
                label.set_alignment(0.0, 0.0)
                label.set_markup(s)
                eb = gtk.EventBox()
                eb.add(label)
                self.table.attach(eb, 1, 2, current_row, current_row+1,
                                  xoptions=gtk.FILL)

                def on_clicked(widget, event, parent):
                    select_in_search_results(parent)

                utils.make_label_clickable(label, on_clicked, divided_plant)
                current_row += 1

        self.vbox.show_all()


def label_size_allocate(widget, rect):
    widget.set_size_request(rect.width, -1)


class PropagationExpander(InfoExpander):
    """
    Propagation Expander
    """

    def __init__(self, widgets):
        """
        """
        super(PropagationExpander, self).__init__(_('Propagations'), widgets)
        self.vbox.set_spacing(4)

    def update(self, row):
        sensitive = True
        if not row.propagations:
            sensitive = False
        self.props.expanded = sensitive
        self.props.sensitive = sensitive
        self.vbox.foreach(self.vbox.remove)
        format = prefs.prefs[prefs.date_format_pref]
        for prop in row.propagations:
            # (h1 (v1 (date_lbl)) (v2 (eventbox (accession_lbl)) (label)))
            h1 = gtk.HBox()
            h1.set_spacing(3)
            self.vbox.pack_start(h1)

            v1 = gtk.VBox()
            v2 = gtk.VBox()
            h1.pack_start(v1)
            h1.pack_start(v2)

            date_lbl = gtk.Label()
            v1.pack_start(date_lbl)
            date_lbl.set_markup("<b>%s</b>" % prop.date.strftime(format))
            date_lbl.set_alignment(0.0, 0.0)

            for acc in prop.accessions:
                accession_lbl = gtk.Label()
                eventbox = gtk.EventBox()
                eventbox.add(accession_lbl)
                v2.pack_start(eventbox)
                accession_lbl.set_alignment(0.0, 0.0)
                accession_lbl.set_text(acc.code)

                def on_clicked(widget, event, obj):
                    select_in_search_results(obj)

                utils.make_label_clickable(accession_lbl, on_clicked, acc)

            label = gtk.Label()
            v2.pack_start(label)

            label.set_text(prop.get_summary(partial=2))
            label.props.wrap = True
            label.set_alignment(0.0, 0.0)
            label.connect("size-allocate", label_size_allocate)
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

        urls = filter(lambda x: x != [],
                      [utils.get_urls(note.note) for note in row.notes])
        if not urls:
            self.links.props.visible = False
            self.links._sep.props.visible = False
        else:
            self.links.props.visible = True
            self.links._sep.props.visible = True
            self.links.update(row)

        self.props.update(row)
