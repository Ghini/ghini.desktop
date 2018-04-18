# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Brett Adams
# Copyright 2015-2017 Mario Frasca <mario@anche.no>.
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
# propagation module
#

import datetime
import os
import weakref
import traceback

import gtk

import logging
logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)

from sqlalchemy import Column, Integer, ForeignKey, UnicodeText, Unicode
from sqlalchemy.orm import backref, relation
from sqlalchemy.orm.session import object_session
from sqlalchemy.exc import DBAPIError

import bauble
import bauble.db as db
import bauble.utils as utils
import bauble.paths as paths
import bauble.editor as editor
import bauble.prefs as prefs
import bauble.btypes as types


prop_type_values = {u'Seed': _("Seed"),
                    u'UnrootedCutting': _('Unrooted cutting'),
                    u'Other': _('Other')}

prop_type_results = {
    u'Seed': u'SEDL',
    u'UnrootedCutting': u'RCUT',
    u'Other': u'UNKN',
}


class PlantPropagation(db.Base):
    """
    PlantPropagation provides an intermediate relation from
    Plant->Propagation
    """
    __tablename__ = 'plant_prop'
    plant_id = Column(Integer, ForeignKey('plant.id'), nullable=False)
    propagation_id = Column(Integer, ForeignKey('propagation.id'),
                            nullable=False)

    propagation = relation('Propagation', uselist=False)
    plant = relation('Plant', uselist=False)


class Propagation(db.Base):
    """
    Propagation
    """
    __tablename__ = 'propagation'
    prop_type = Column(types.Enum(values=prop_type_values.keys(),
                                  translations=prop_type_values),
                       nullable=False)
    notes = Column(UnicodeText)
    date = Column(types.Date)

    _cutting = relation(
        'PropCutting',
        primaryjoin='Propagation.id==PropCutting.propagation_id',
        cascade='all,delete-orphan', uselist=False,
        backref=backref('propagation', uselist=False))
    _seed = relation(
        'PropSeed',
        primaryjoin='Propagation.id==PropSeed.propagation_id',
        cascade='all,delete-orphan', uselist=False,
        backref=backref('propagation', uselist=False))

    @property
    def accessions(self):
        if not self.used_source:
            return []
        accessions = []
        session = object_session(self.used_source[0].accession)
        for us in self.used_source:
            if us.accession not in session.new:
                accessions.append(us.accession)
        return sorted(accessions)

    @property
    def accessible_quantity(self):
        """the resulting product minus the already accessed material

        return 1 if the propagation is not completely specified.

        """
        quantity = None
        incomplete = True
        if self.prop_type == u'UnrootedCutting':
            incomplete = self._cutting is None  # cutting without fields
            if not incomplete:
                quantity = self._cutting.rooted_pct
        elif self.prop_type == u'Seed':
            incomplete = self._seed is None  # seed without fields
            if not incomplete:
                quantity = self._seed.nseedlings
        if incomplete:
            return 1  # let user grab one at a time, in any case
        if quantity is None:
            quantity = 0
        removethis = sum((a.quantity_recvd or 0) for a in self.accessions)
        return max(quantity - removethis, 0)

    def get_summary(self, partial=False):
        """compute a textual summary for this propagation

        a full description contains all fields, in `key:value;` format, plus
        a prefix telling us whether the resulting material of the
        propagation was added as accessed in the collection.

        partial==1 means we only want to get the list of resulting
        accessions.

        partial==2 means we do not want the list of resulting accessions.

        """
        date_format = prefs.prefs[prefs.date_format_pref]

        def get_date(date):
            if isinstance(date, datetime.date):
                return date.strftime(date_format)
            return date

        values = []
        accession_codes = []

        if self.used_source and partial != 2:
            values = [_('used in') + ': %s' % acc.code for acc in self.accessions]
            accession_codes = [acc.code for acc in self.accessions]

        if partial == 1:
            return ';'.join(accession_codes)

        if self.prop_type == u'UnrootedCutting':
            c = self._cutting
            values.append(_('Cutting'))
            if c.cutting_type is not None:
                values.append(_('Cutting type') + ': %s' %
                              cutting_type_values[c.cutting_type])
            if c.length:
                values.append(_('Length: %(length)s%(unit)s') %
                              dict(length=c.length,
                                   unit=length_unit_values[c.length_unit]))
            if c.tip:
                values.append(_('Tip') + ': %s' % tip_values[c.tip])
            if c.leaves:
                s = _('Leaves') + ': %s' % leaves_values[c.leaves]
                if c.leaves == u'Removed' and c.leaves_reduced_pct:
                    s.append('(%s%%)' % c.leaves_reduced_pct)
                values.append(s)
            if c.flower_buds:
                values.append(_('Flower buds') + ': %s' %
                              flower_buds_values[c.flower_buds])
            if c.wound is not None:
                values.append(_('Wounded') + ': %s' % wound_values[c.wound])
            if c.fungicide:
                values.append(_('Fungal soak') + ': %s' % c.fungicide)
            if c.hormone:
                values.append(_('Hormone treatment') + ': %s' % c.hormone)
            if c.bottom_heat_temp:
                values.append(
                    _('Bottom heat: %(temp)s%(unit)s') %
                    dict(temp=c.bottom_heat_temp,
                         unit=bottom_heat_unit_values[c.bottom_heat_unit]))
            if c.container:
                values.append(_('Container') + ': %s' % c.container)
            if c.media:
                values.append(_('Media') + ': %s' % c.media)
            if c.location:
                values.append(_('Location') + ': %s' % c.location)
            if c.cover:
                values.append(_('Cover') + ': %s' % c.cover)

            if c.rooted_pct:
                values.append(_('Rooted: %s%%') % c.rooted_pct)
        elif self.prop_type == u'Seed':
            seed = self._seed
            values.append(_('Seed'))
            if seed.pretreatment:
                values.append(_('Pretreatment') + ': %s' % seed.pretreatment)
            if seed.nseeds:
                values.append(_('# of seeds') + ': %s' % seed.nseeds)
            date_sown = get_date(seed.date_sown)
            if date_sown:
                values.append(_('Date sown') + ': %s' % date_sown)
            if seed.container:
                values.append(_('Container') + ': %s' % seed.container)
            if seed.media:
                values.append(_('Media') + ': %s' % seed.media)
            if seed.covered:
                values.append(_('Covered') + ': %s' % seed.covered)
            if seed.location:
                values.append(_('Location') + ': %s' % seed.location)
            germ_date = get_date(seed.germ_date)
            if germ_date:
                values.append(_('Germination date') + ': %s' % germ_date)
            if seed.nseedlings:
                values.append(_('# of seedlings') + ': %s' % seed.nseedlings)
            if seed.germ_pct:
                values.append(_('Germination rate') + ': %s%%' % seed.germ_pct)
            date_planted = get_date(seed.date_planted)
            if date_planted:
                values.append(_('Date planted') + ': %s' % date_planted)
        elif self.notes:
            values.append(_('Other'))
            values.append(utils.utf8(self.notes))
        else:
            values.append(str(self))

        s = '; '.join(values)

        return s

    def clean(self):
        if self.prop_type == u'UnrootedCutting':
            utils.delete_or_expunge(self._seed)
            self._seed = None
            if not self._cutting.bottom_heat_temp:
                self._cutting.bottom_heat_unit = None
            if not self._cutting.length:
                self._cutting.length_unit = None
        elif self.prop_type == u'Seed':
            utils.delete_or_expunge(self._cutting)
            self._cutting = None
        else:
            utils.delete_or_expunge(self._seed)
            utils.delete_or_expunge(self._cutting)
            self._seed = None
            self._cutting = None


class PropCuttingRooted(db.Base):
    """
    Rooting dates for cutting
    """
    __tablename__ = 'prop_cutting_rooted'
    __mapper_args__ = {'order_by': 'date'}

    date = Column(types.Date)
    quantity = Column(Integer, autoincrement=False)
    cutting_id = Column(Integer, ForeignKey('prop_cutting.id'), nullable=False)


cutting_type_values = {u'Nodal': _('Nodal'),
                       u'InterNodal': _('Internodal'),
                       u'Other': _('Other')}

tip_values = {u'Intact': _('Intact'),
              u'Removed': _('Removed'),
              u'None': _('None'),
              None: ''}

leaves_values = {u'Intact': _('Intact'),
                 u'Removed': _('Removed'),
                 u'None': _('None'),
                 None: ''}

flower_buds_values = {u'Removed': _('Removed'),
                      u'None': _('None'),
                      None: ''}

wound_values = {u'No': _('No'),
                u'Single': _('Singled'),
                u'Double': _('Double'),
                u'Slice': _('Slice'),
                None: ''}

hormone_values = {u'Liquid': _('Liquid'),
                  u'Powder': _('Powder'),
                  u'No': _('No')}

bottom_heat_unit_values = {u'F': _('\302\260F'),
                           u'C': _('\302\260C'),
                           None: ''}

length_unit_values = {u'mm': _('mm'),
                      u'cm': _('cm'),
                      u'in': _('in'),
                      None: ''}


class PropCutting(db.Base):
    """
    A cutting
    """
    __tablename__ = 'prop_cutting'
    cutting_type = Column(types.Enum(values=cutting_type_values.keys(),
                                     translations=cutting_type_values),
                          default=u'Other')
    tip = Column(types.Enum(values=tip_values.keys(),
                            translations=tip_values))
    leaves = Column(types.Enum(values=leaves_values.keys(),
                               translations=leaves_values))
    leaves_reduced_pct = Column(Integer, autoincrement=False)
    length = Column(Integer, autoincrement=False)
    length_unit = Column(types.Enum(values=length_unit_values.keys(),
                                    translations=length_unit_values))

    # single/double/slice
    wound = Column(types.Enum(values=wound_values.keys(),
                              translations=wound_values))

    # removed/None
    flower_buds = Column(types.Enum(values=flower_buds_values.keys(),
                                    translations=flower_buds_values))

    fungicide = Column(UnicodeText)  # fungal soak
    hormone = Column(UnicodeText)  # powder/liquid/None....solution

    media = Column(UnicodeText)
    container = Column(UnicodeText)
    location = Column(UnicodeText)
    cover = Column(UnicodeText)  # vispore, poly, plastic dome, poly bag

    # temperature of bottom heat
    bottom_heat_temp = Column(Integer, autoincrement=False)

    # TODO: make the bottom heat unit required if bottom_heat_temp is
    # not null

    # F/C
    bottom_heat_unit = Column(types.Enum(values=bottom_heat_unit_values.keys(),
                                         translations=bottom_heat_unit_values),
                              nullable=True)
    rooted_pct = Column(Integer, autoincrement=False)

    propagation_id = Column(Integer, ForeignKey('propagation.id'),
                            nullable=False)

    rooted = relation('PropCuttingRooted', cascade='all,delete-orphan',
                      primaryjoin='PropCutting.id==PropCuttingRooted.cutting_id',
                      backref=backref('cutting', uselist=False))


class PropSeed(db.Base):
    """
    """
    __tablename__ = 'prop_seed'
    pretreatment = Column(UnicodeText)
    nseeds = Column(Integer, nullable=False, autoincrement=False)
    date_sown = Column(types.Date, nullable=False)
    container = Column(UnicodeText)  # 4" pot plug tray, other
    media = Column(UnicodeText)  # seedling media, sphagnum, other

    # covered with #2 granite grit: no, yes, lightly heavily
    covered = Column(UnicodeText)

    # not same as location table, glasshouse(bottom heat, no bottom
    # heat), polyhouse, polyshade house, fridge in polybag
    location = Column(UnicodeText)

    # TODO: do we need multiple moved to->moved from and date fields
    moved_from = Column(UnicodeText)
    moved_to = Column(UnicodeText)
    moved_date = Column(types.Date)

    germ_date = Column(types.Date)

    nseedlings = Column(Integer, autoincrement=False)  # number of seedling
    germ_pct = Column(Integer, autoincrement=False)  # % of germination
    date_planted = Column(types.Date)

    propagation_id = Column(Integer, ForeignKey('propagation.id'),
                            nullable=False)

    def __str__(self):
        # what would the string be...???
        # cuttings of self.accession.species_str() and accession number
        return repr(self)


class PropagationTabPresenter(editor.GenericEditorPresenter):

    """PropagationTabPresenter

    :param parent: an instance of PlantEditorPresenter
    :param model: an instance of class Plant
    :param view: an instance of PlantEditorView
    :param session:
    """

    def __init__(self, parent, model, view, session):
        super(PropagationTabPresenter, self).__init__(model, view)
        self.parent_ref = weakref.ref(parent)
        self.session = session
        self.view.connect('prop_add_button', 'clicked',
                          self.on_add_button_clicked)
        tab_box = self.view.widgets.prop_tab_box
        for kid in tab_box:
            if isinstance(kid, gtk.Box):
                tab_box.remove(kid)  # remove old prop boxes
        for prop in self.model.propagations:
            box = self.create_propagation_box(prop)
            tab_box.pack_start(box, expand=False, fill=True)
        self._dirty = False

    def is_dirty(self):
        return self._dirty

    def add_propagation(self):
        """
        Open the PropagationEditor and append the resulting
        propagation to self.model.propagations
        """
        propagation = Propagation()
        propagation.plant = self.model
        editor = PropagationEditor(propagation, parent=self.view.get_window())
        # open propagation editor with start(commit=False) so that the
        # propagation editor doesn't commit its changes since we'll be
        # doing our own commit later
        committed = editor.start(commit=False)
        if committed:
            box = self.create_propagation_box(committed)
            self.view.widgets.prop_tab_box.pack_start(box, expand=False,
                                                      fill=True)
            self._dirty = True
        else:
            propagation.plant = None

    def create_propagation_box(self, propagation):
        """
        """
        hbox = gtk.HBox()
        expander = gtk.Expander()
        hbox.pack_start(expander, expand=True, fill=True)

        from bauble.plugins.garden.plant import label_size_allocate
        label = gtk.Label(propagation.get_summary())
        label.props.wrap = True
        label.set_alignment(0, 0)
        label.set_padding(0, 2)
        label.connect("size-allocate", label_size_allocate)
        expander.add(label)

        def on_edit_clicked(button, prop, label):
            editor = PropagationEditor(model=prop,
                                       parent=self.view.get_window())
            if editor.start(commit=False) is not None:
                label.props.label = prop.get_summary()
                self._dirty = True
            self.parent_ref().refresh_sensitivity()

        alignment = gtk.Alignment()
        hbox.pack_start(alignment, expand=False, fill=False)
        button_box = gtk.HBox(spacing=5)
        alignment.add(button_box)
        button = gtk.Button(stock=gtk.STOCK_EDIT)
        self.view.connect(button, 'clicked', on_edit_clicked, propagation,
                          label)
        button_box.pack_start(button, expand=False, fill=False)

        def on_remove_clicked(button, propagation, box):
            count = len(propagation.accessions)
            potential = propagation.accessible_quantity
            if count == 0:
                if potential:
                    msg = _("This propagation has produced %s plants.\n"
                            "It can already be accessioned.\n\n"
                            "Are you sure you want to remove it?") % potential
                else:
                    msg = _("Are you sure you want to remove\n"
                            "this propagation trial?")
                if not utils.yes_no_dialog(msg):
                    return False
            else:
                if count == 1:
                    msg = _("This propagation is referred to\n"
                            "by accession %s.\n\n"
                            "You cannot remove it.") % propagation.accessions[0]
                elif count > 1:
                    msg = _("This propagation is referred to\n"
                            "by %s accessions.\n\n"
                            "You cannot remove it.") % count
                utils.message_dialog(msg, type=gtk.MESSAGE_WARNING)
                return False
            self.model.propagations.remove(propagation)
            self.view.widgets.prop_tab_box.remove(box)
            self._dirty = True
            self.parent_ref().refresh_sensitivity()

        remove_button = gtk.Button()
        img = gtk.image_new_from_stock(gtk.STOCK_REMOVE, gtk.ICON_SIZE_BUTTON)
        remove_button.props.image = img
        self.view.connect(remove_button, 'clicked', on_remove_clicked,
                          propagation, hbox)
        button_box.pack_start(remove_button, expand=False, fill=False)

        # TODO: add a * to the propagation label for uncommitted propagations
        prop_type = prop_type_values[propagation.prop_type]

        # hack to format date properly
        from bauble.btypes import DateTime
        date = DateTime().process_bind_param(propagation.date, None)
        date_format = prefs.prefs[prefs.date_format_pref]
        date_str = date.strftime(date_format)
        title = ('%(prop_type)s on %(prop_date)s') \
            % dict(prop_type=prop_type, prop_date=date_str)
        expander.set_label(title)

        hbox.show_all()
        return hbox

    def on_add_button_clicked(self, *args):
        """
        """
        self.add_propagation()
        self.parent_ref().refresh_sensitivity()


class PropagationEditorView(editor.GenericEditorView):
    """
    """

    _tooltips = {}

    def __init__(self, parent=None):
        """
        """
        super(PropagationEditorView, self).\
            __init__(os.path.join(paths.lib_dir(), 'plugins', 'garden',
                                  'prop_editor.glade'),
                     parent=parent)
        self.init_translatable_combo('prop_type_combo', prop_type_values)

    def get_window(self):
        """
        """
        return self.widgets.prop_dialog

    def start(self):
        return self.get_window().run()

# TODO: if you edit an existing cutting and the the OK is not set sensitive

# TODO: if you reopen an accession editor the list of propagations
# doesn't get reset properly


class CuttingPresenter(editor.GenericEditorPresenter):

    widget_to_field_map = {'cutting_type_combo': 'cutting_type',
                           'cutting_length_entry': 'length',
                           'cutting_length_unit_combo': 'length_unit',
                           'cutting_tip_combo': 'tip',
                           'cutting_leaves_combo': 'leaves',
                           'cutting_lvs_reduced_entry': 'leaves_reduced_pct',
                           'cutting_buds_combo': 'flower_buds',
                           'cutting_wound_combo': 'wound',
                           'cutting_fungal_comboentry': 'fungicide',
                           'cutting_media_comboentry': 'media',
                           'cutting_container_comboentry': 'container',
                           'cutting_hormone_comboentry': 'hormone',
                           'cutting_location_comboentry': 'location',
                           'cutting_cover_comboentry': 'cover',
                           'cutting_heat_entry': 'bottom_heat_temp',
                           'cutting_heat_unit_combo': 'bottom_heat_unit',
                           'cutting_rooted_pct_entry': 'rooted_pct',
                           }

    def __init__(self, parent, model, view, session):
        '''
        :param model: an instance of class Propagation
        :param view: an instance of PropagationEditorView
        '''
        super(CuttingPresenter, self).__init__(model, view)
        self.parent_ref = weakref.ref(parent)
        self.session = session
        self._dirty = False

        # instance is initialized with a Propagation instance as model, but
        # that's just the common parts.  This instance takes care of the
        # _cutting part of the propagation
        self.propagation = self.model
        if not self.propagation._cutting:
            self.propagation._cutting = PropCutting()
        self.model = self.model._cutting

        init_combo = self.view.init_translatable_combo
        init_combo('cutting_type_combo', cutting_type_values,
                   editor.UnicodeOrNoneValidator())
        init_combo('cutting_length_unit_combo', length_unit_values)
        init_combo('cutting_tip_combo', tip_values)
        init_combo('cutting_leaves_combo', leaves_values)
        init_combo('cutting_buds_combo', flower_buds_values)
        init_combo('cutting_wound_combo', wound_values)
        init_combo('cutting_heat_unit_combo', bottom_heat_unit_values)

        widgets = self.view.widgets

        distinct = lambda c: utils.get_distinct_values(c, self.session)
        utils.setup_text_combobox(widgets.cutting_hormone_comboentry,
                                  distinct(PropCutting.hormone))
        utils.setup_text_combobox(widgets.cutting_cover_comboentry,
                                  distinct(PropCutting.cover))
        utils.setup_text_combobox(widgets.cutting_fungal_comboentry,
                                  distinct(PropCutting.fungicide))
        utils.setup_text_combobox(widgets.cutting_location_comboentry,
                                  distinct(PropCutting.location))
        utils.setup_text_combobox(widgets.cutting_container_comboentry,
                                  distinct(PropCutting.container))
        utils.setup_text_combobox(widgets.cutting_media_comboentry,
                                  distinct(PropCutting.media))

        # set default units
        units = prefs.prefs[prefs.units_pref]
        if units == u'imperial':
            self.model.length_unit = u'in'
            self.model.bottom_heat_unit = u'F'
        else:
            self.model.length_unit = u'mm'
            self.model.bottom_heat_unit = u'C'

        # the liststore for rooted cuttings contains PropCuttingRooted
        # objects, not just their fields, so we cannot define it in the
        # glade file.
        rooted_liststore = gtk.ListStore(object)
        self.view.widgets.rooted_treeview.set_model(rooted_liststore)

        from functools import partial
        def rooted_cell_data_func(attr_name, column, cell, rooted_liststore, treeiter):
            # extract attr from the object and show it in the cell
            v = rooted_liststore[treeiter][0]
            cell.set_property('text', getattr(v, attr_name))

        def on_rooted_cell_edited(attr_name, cell, path, new_text):
            # update object if field was modified, refresh sensitivity
            rooted = rooted_liststore[path][0]
            if getattr(rooted, attr_name) == new_text:
                return  # didn't change
            setattr(rooted, attr_name, utils.utf8(new_text))
            self._dirty = True
            self.parent_ref().refresh_sensitivity()

        sfw = self.view.widgets
        for cell, column, attr_name in [
                (sfw.rooted_date_cell, sfw.rooted_date_column, 'date'),
                (sfw.rooted_quantity_cell, sfw.rooted_quantity_column, 'quantity')]:
            cell.props.editable = True
            self.view.connect(
                cell, 'edited', partial(on_rooted_cell_edited, attr_name))
            column.set_cell_data_func(
                cell, partial(rooted_cell_data_func, attr_name))

        self.refresh_view()

        self.assign_simple_handler('cutting_type_combo', 'cutting_type')
        self.assign_simple_handler('cutting_length_entry', 'length')
        self.assign_simple_handler('cutting_length_unit_combo', 'length_unit')
        self.assign_simple_handler('cutting_tip_combo', 'tip')
        self.assign_simple_handler('cutting_leaves_combo', 'leaves')
        self.assign_simple_handler('cutting_lvs_reduced_entry',
                                   'leaves_reduced_pct')

        self.assign_simple_handler('cutting_media_comboentry', 'media',
                                   editor.UnicodeOrNoneValidator())
        self.assign_simple_handler('cutting_container_comboentry', 'container',
                                   editor.UnicodeOrNoneValidator())

        self.assign_simple_handler('cutting_buds_combo', 'flower_buds')
        self.assign_simple_handler('cutting_wound_combo', 'wound')
        self.assign_simple_handler('cutting_fungal_comboentry', 'fungicide',
                                   editor.UnicodeOrNoneValidator())
        self.assign_simple_handler('cutting_hormone_comboentry', 'hormone',
                                   editor.UnicodeOrNoneValidator())
        self.assign_simple_handler('cutting_location_comboentry', 'location',
                                   editor.UnicodeOrNoneValidator())
        self.assign_simple_handler('cutting_cover_comboentry', 'cover',
                                   editor.UnicodeOrNoneValidator())
        self.assign_simple_handler('cutting_heat_entry', 'bottom_heat_temp')
        self.assign_simple_handler('cutting_heat_unit_combo',
                                   'bottom_heat_unit')
        self.assign_simple_handler('cutting_rooted_pct_entry',
                                   'rooted_pct')

        self.view.connect('rooted_add_button', "clicked",
                          self.on_rooted_add_clicked)
        self.view.connect('rooted_remove_button', "clicked",
                          self.on_rooted_remove_clicked)

    def is_dirty(self):
        return self._dirty

    def set_model_attr(self, field, value, validator=None):
        #debug('%s = %s' % (field, value))
        super(CuttingPresenter, self).set_model_attr(field, value, validator)
        self._dirty = True
        self.parent_ref().refresh_sensitivity()

    def on_rooted_add_clicked(self, button, *args):
        """
        """
        tree = self.view.widgets.rooted_treeview
        rooted = PropCuttingRooted()
        rooted.cutting = self.model
        rooted.date = utils.today_str()
        model = tree.get_model()
        treeiter = model.insert(0, [rooted])
        path = model.get_path(treeiter)
        column = tree.get_column(0)
        tree.set_cursor(path, column, start_editing=True)

    def on_rooted_remove_clicked(self, button, *args):
        """
        """
        tree = self.view.widgets.rooted_treeview
        model, treeiter = tree.get_selection().get_selected()
        if not treeiter:
            return
        rooted = model[treeiter][0]
        rooted.cutting = None
        model.remove(treeiter)
        self._dirty = True
        self.parent_ref().refresh_sensitivity()

    def refresh_view(self):
        # TODO: not so sure. is this a 'refresh', or a 'init' view?
        for widget, attr in self.widget_to_field_map.iteritems():
            value = getattr(self.model, attr)
            self.view.widget_set_value(widget, value)
        rooted_liststore = self.view.widgets.rooted_treeview.get_model()
        rooted_liststore.clear()
        for rooted in self.model.rooted:
            rooted_liststore.append([rooted])


class SeedPresenter(editor.GenericEditorPresenter):

    widget_to_field_map = {'seed_pretreatment_textview': 'pretreatment',
                           'seed_nseeds_entry': 'nseeds',
                           'seed_sown_entry': 'date_sown',
                           'seed_container_comboentry': 'container',
                           'seed_media_comboentry': 'media',
                           'seed_location_comboentry': 'location',
                           'seed_mvdfrom_entry': 'moved_from',
                           'seed_mvdto_entry': 'moved_to',
                           'seed_germdate_entry': 'germ_date',
                           'seed_ngerm_entry': 'nseedlings',
                           'seed_pctgerm_entry': 'germ_pct',
                           'seed_date_planted_entry': 'date_planted'}

    def __init__(self, parent, model, view, session):
        '''
        :param model: an instance of class Propagation
        :param view: an instance of PropagationEditorView
        '''
        super(SeedPresenter, self).__init__(model, view)
        self._dirty = False
        self.parent_ref = weakref.ref(parent)
        self.session = session

        self.propagation = self.model
        if not self.propagation._seed:
            self.propagation._seed = PropSeed()
        self.model = self.model._seed

        # TODO: if % germinated is not entered and nseeds and #
        # germinated are then automatically calculate the % germinated

        widgets = self.view.widgets
        distinct = lambda c: utils.get_distinct_values(c, self.session)
        # TODO: should also setup a completion on the entry
        utils.setup_text_combobox(self.view.widgets.seed_media_comboentry,
                                  distinct(PropSeed.media))
        utils.setup_text_combobox(self.view.widgets.seed_container_comboentry,
                                  distinct(PropSeed.container))
        utils.setup_text_combobox(self.view.widgets.seed_location_comboentry,
                                  distinct(PropSeed.location))

        self.refresh_view()

        self.assign_simple_handler('seed_pretreatment_textview',
                                   'pretreatment',
                                   editor.UnicodeOrNoneValidator())
        # TODO: this should validate to an integer
        self.assign_simple_handler('seed_nseeds_entry', 'nseeds',
                                   editor.UnicodeOrNoneValidator())
        self.assign_simple_handler('seed_sown_entry', 'date_sown',
                                   editor.DateValidator())
        utils.setup_date_button(self.view, 'seed_sown_entry',
                                'seed_sown_button')
        self.assign_simple_handler('seed_container_comboentry', 'container',
                                   editor.UnicodeOrNoneValidator())
        self.assign_simple_handler('seed_media_comboentry', 'media',
                                   editor.UnicodeOrNoneValidator())
        self.assign_simple_handler('seed_location_comboentry', 'location',
                                   editor.UnicodeOrNoneValidator())
        self.assign_simple_handler('seed_mvdfrom_entry', 'moved_from',
                                   editor.UnicodeOrNoneValidator())
        self.assign_simple_handler('seed_mvdto_entry', 'moved_to',
                                   editor.UnicodeOrNoneValidator())
        self.assign_simple_handler('seed_germdate_entry', 'germ_date',
                                   editor.DateValidator())
        utils.setup_date_button(self.view, 'seed_germdate_entry',
                                'seed_germdate_button')
        self.assign_simple_handler('seed_ngerm_entry', 'nseedlings')
        self.assign_simple_handler('seed_pctgerm_entry', 'germ_pct')
        self.assign_simple_handler('seed_date_planted_entry', 'date_planted',
                                   editor.DateValidator())
        utils.setup_date_button(self.view, 'seed_date_planted_entry',
                                'seed_date_planted_button')

    def is_dirty(self):
        return self._dirty

    def set_model_attr(self, field, value, validator=None):
        #debug('%s = %s' % (field, value))
        super(SeedPresenter, self).set_model_attr(field, value, validator)
        self._dirty = True
        self.parent_ref().refresh_sensitivity()

    def refresh_view(self):
        date_format = prefs.prefs[prefs.date_format_pref]
        for widget, attr in self.widget_to_field_map.iteritems():
            value = getattr(self.model, attr)
            if isinstance(value, datetime.date):
                value = value.strftime(date_format)
            self.view.widget_set_value(widget, value)


class PropagationPresenter(editor.ChildPresenter):
    """PropagationPresenter is extended by SourcePropagationPresenter and
    PropagationEditorPresenter.

    """
    widget_to_field_map = {'prop_type_combo': 'prop_type',
                           'prop_date_entry': 'date',
                           'notes_textview': 'notes'}

    def __init__(self, model, view):
        '''
        :param model: an instance of class Propagation
        :param view: an instance of PropagationEditorView
        '''
        super(PropagationPresenter, self).__init__(model, view)
        self.session = object_session(model)

        # initialize the propagation type combo and set the initial value
        self.view.connect('prop_type_combo', 'changed',
                          self.on_prop_type_changed)
        if self.model.prop_type:
            self.view.widget_set_value('prop_type_combo', self.model.prop_type)

        self._cutting_presenter = CuttingPresenter(self, self.model, self.view,
                                                   self.session)
        self._seed_presenter = SeedPresenter(self, self.model, self.view,
                                             self.session)

        if not self.model.prop_type:
            view.widgets.prop_details_box.props.visible = False

        if self.model.date:
            format = prefs.prefs[prefs.date_format_pref]
            date = self.model.date.strftime(format)
            self.view.widget_set_value(self.view.widgets.prop_date_entry, date)
        else:
            self.view.widget_set_value(self.view.widgets.prop_date_entry,
                                       utils.today_str())

        self.view.widget_set_value(self.view.widgets.notes_textview,
                                   self.model.notes)

        self._dirty = False
        utils.setup_date_button(self.view, 'prop_date_entry',
                                'prop_date_button')
        self.assign_simple_handler('prop_date_entry', 'date',
                                   editor.DateValidator())
        self.assign_simple_handler('notes_textview', 'notes',
                                   editor.UnicodeOrNoneValidator())

        def on_expanded(*args):
            if self.model.prop_type == u'Other':
                # i don't really understand why setting the expanded
                # property to false here cause the notes_expander to
                # always stay expanded but it works
                self.view.widgets.notes_expander.props.expanded = False
        self.view.connect('notes_expander', 'activate', on_expanded)

    def on_prop_type_changed(self, combo, *args):
        it = combo.get_active_iter()
        prop_type = combo.get_model()[it][0]
        if self.model.prop_type != prop_type:
            # only call set_model_attr() if the value is changed to
            # avoid prematuraly calling dirty() and refresh_sensitivity()
            self.set_model_attr('prop_type', prop_type)
        prop_box_map = {u'Seed': self.view.widgets.seed_box,
                        u'UnrootedCutting': self.view.widgets.cutting_box,
                        }
        for type_, box in prop_box_map.iteritems():
            box.props.visible = (prop_type == type_)

        self.view.widgets.notes_box.props.visible = True
        if prop_type == u'Other' or self.model.notes:
            self.view.widgets.notes_expander.props.expanded = True

        self.view.widgets.prop_details_box.props.visible = True

        if not self.model.date:
            self.view.widgets.prop_date_entry.emit('changed')

    def is_dirty(self):
        if self.model.prop_type == u'UnrootedCutting':
            return self._cutting_presenter.is_dirty() or self._dirty
        elif self.model.prop_type == u'Seed':
            return self._seed_presenter.is_dirty() or self._dirty
        else:
            return self._dirty

    def set_model_attr(self, field, value, validator=None):
        """
        Set attributes on the model and update the GUI as expected.
        """
        logging.debug('%s = %s' % (field, value))
        super(PropagationPresenter, self).\
            set_model_attr(field, value, validator)
        self._dirty = True
        self.refresh_sensitivity()

    def cleanup(self):
        self._cutting_presenter.cleanup()
        self._seed_presenter.cleanup()

    def refresh_sensitivity(self):
        pass

    def refresh_view(self):
        pass


class SourcePropagationPresenter(PropagationPresenter):
    """
    Presenter for creating a new Propagation for the
    Source.propagation property.  This type of propagation is not
    associated with a Plant.

    :param parent: AccessionEditorPresenter
    :param model:  Propagation instance
    :param view:  AccessionEditorView
    :param session: sqlalchemy.orm.sesssion
    """
    def __init__(self, parent, model, view, session):
        self.parent_ref = weakref.ref(parent)
        self.parent_session = session
        try:
            view.widgets.prop_main_box
        except:
            # only add the propagation editor widgets to the view
            # widgets if the widgets haven't yet been added
            filename = os.path.join(paths.lib_dir(), 'plugins', 'garden',
                                    'prop_editor.glade')
            view.widgets.builder.add_from_file(filename)
        prop_main_box = view.widgets.prop_main_box
        view.widgets.remove_parent(prop_main_box)
        view.widgets.acc_prop_box_parent.add(prop_main_box)

        # since the view here will be an AccessionEditorView and not a
        # PropagationEditorView then we need to do anything here that
        # PropagationEditorView would do
        view.init_translatable_combo('prop_type_combo', prop_type_values)
        # add None to the prop types which is specific to
        # SourcePropagationPresenter since we might also need to
        # remove the propagation...this will need to be called before
        # the PropagationPresenter.on_prop_type_changed or it won't work
        view.widgets.prop_type_combo.get_model().append([None, ''])

        self._dirty = False
        super(SourcePropagationPresenter, self).__init__(model, view)

    def on_prop_type_changed(self, combo, *args):
        """
        Override PropagationPresenter.on_type_changed() to handle the
        None value in the prop_type_combo which is specific the
        SourcePropagationPresenter
        """
        logger.debug('SourcePropagationPresenter.on_prop_type_changed()')
        it = combo.get_active_iter()
        prop_type = combo.get_model()[it][0]
        if not prop_type:
            self.set_model_attr('prop_type', None)
            self.view.widgets.prop_details_box.props.visible = False
        else:
            super(SourcePropagationPresenter, self).\
                on_prop_type_changed(combo, *args)
        self._dirty = False

    def set_model_attr(self, attr, value, validator=None):
        logger.debug('set_model_attr(%s, %s)' % (attr, value))
        super(SourcePropagationPresenter, self).set_model_attr(attr, value)
        self._dirty = True
        self.refresh_sensitivity()

    def refresh_sensitivity(self):
        self.parent_ref().refresh_sensitivity()

    def is_dirty(self):
        return super(SourcePropagationPresenter, self).is_dirty() or self._dirty


class PropagationEditorPresenter(PropagationPresenter):

    def __init__(self, model, view):
        '''
        :param model: an instance of class Propagation
        :param view: an instance of PropagationEditorView
        '''
        super(PropagationEditorPresenter, self).__init__(model, view)
        # don't allow changing the propagation type if we are editing
        # an existing propagation
        if model not in self.session.new or self.model.prop_type:
            self.view.widgets.prop_type_box.props.visible = False
        elif not self.model.prop_type:
            self.view.widgets.prop_type_box.props.visible = True
            self.view.widgets.prop_details_box.props.visible = False
        self.view.widgets.prop_ok_button.props.sensitive = False

    def start(self):
        r = self.view.start()
        return r

    def refresh_sensitivity(self):
        super(PropagationEditorPresenter, self).refresh_sensitivity()
        sensitive = True

        if utils.get_invalid_columns(self.model):
            sensitive = False

        model = None
        if object_session(self.model):
            if self.model.prop_type == u'UnrootedCutting':
                model = self.model._cutting
            elif self.model.prop_type == u'Seed':
                model = self.model._seed

        if model:
            invalid = utils.get_invalid_columns(
                model, ['id', 'propagation_id'])
            # TODO: highlight the widget with are associated with the
            # columns that have bad values
            if invalid:
                sensitive = False
        elif self.model.notes:
            sensitive = True
        else:
            sensitive = False
        self.view.widgets.prop_ok_button.props.sensitive = sensitive


class PropagationEditor(editor.GenericModelViewPresenterEditor):

    # these have to correspond to the response values in the view
    RESPONSE_OK_AND_ADD = 11
    RESPONSE_NEXT = 22
    ok_responses = (RESPONSE_OK_AND_ADD, RESPONSE_NEXT)

    def __init__(self, model, parent=None):
        '''
        :param prop_parent: an instance with a propagation relation
        :param model: Propagation instance
        :param parent: the parent widget
        '''
        # the view and presenter are created in self.start()
        self.view = None
        self.presenter = None
        super(PropagationEditor, self).__init__(model, parent)
        # if mode already has a session then use it, this is unique to
        # the PropagationEditor because so far it is the only editor
        # that dependent on a parent editor and the parent editor's
        # model and session
        sess = object_session(model)
        if sess:
            self.session.close()
            self.session = sess
            self.model = model

        if not parent and bauble.gui:
            parent = bauble.gui.window
        self.parent = parent

        view = PropagationEditorView(parent=self.parent)
        self.presenter = PropagationEditorPresenter(self.model, view)
            
    def handle_response(self, response, commit=True):
        '''
        handle the response from self.presenter.start() in self.start()
        '''
        not_ok_msg = 'Are you sure you want to lose your changes?'
        self._return = None
        self.model.clean()
        if response == gtk.RESPONSE_OK or response in self.ok_responses:
            try:
                self._return = self.model
                if self.presenter.is_dirty() and commit:
                    self.commit_changes()
            except DBAPIError, e:
                msg = _('Error committing changes.\n\n%s') % \
                    utils.xml_safe(unicode(e.orig))
                utils.message_details_dialog(msg, str(e), gtk.MESSAGE_ERROR)
                self.session.rollback()
                return False
            except Exception, e:
                msg = _('Unknown error when committing changes. See the '
                        'details for more information.\n\n%s') %\
                    utils.xml_safe(e)
                logger.debug(traceback.format_exc())
                utils.message_details_dialog(msg, traceback.format_exc(),
                                             gtk.MESSAGE_ERROR)
                self.session.rollback()
                return False
        elif self.presenter.is_dirty() and utils.yes_no_dialog(not_ok_msg) \
                or not self.presenter.is_dirty():
            self.session.rollback()
            return True
        else:
            return False

        return True

    def __del__(self):
        # override the editor.GenericModelViewPresenterEditor since it
        # will close the session but since we are called with the
        # AccessionEditor's session we don't want that
        #
        # TODO: when should we close the session and not, what about
        # is self.commit is True
        pass

    def start(self, commit=True):
        while True:
            response = self.presenter.start()
            self.presenter.view.save_state()
            if self.handle_response(response, commit):
                break

        # don't close the session since the PropagationEditor depends
        # on an PlantEditor...?
        #
        #self.session.close()  # cleanup session
        self.presenter.cleanup()
        return self._return
