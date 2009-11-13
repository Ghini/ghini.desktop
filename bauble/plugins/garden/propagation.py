# -*- coding: utf-8 -*-
#
# propagation module
#

import datetime
import os
from random import random
import re
import sys
import weakref
import traceback
import xml.sax.saxutils as saxutils

import dateutil.parser as date_parser
import gtk
import gobject
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.orm.session import object_session
from sqlalchemy.exc import SQLError

import bauble
import bauble.db as db
from bauble.error import check
import bauble.utils as utils
import bauble.paths as paths
import bauble.editor as editor
from bauble.utils.log import debug
import bauble.prefs as prefs
from bauble.error import CommitException
import bauble.types as types
from bauble.view import InfoBox, InfoExpander, PropertiesExpander, \
     select_in_search_results, Action
#from bauble.plugins.garden.plant import Plant


prop_type_values = {u'Seed': _("Seed"),
                    u'UnrootedCutting': _('Unrooted cutting'),
                    u'Other': _('Other')}


# TODO: create an add propagation field to an accession context menu


class Propagation(db.Base):
    """
    Propagation
    """
    __tablename__ = 'propagation'
    #recvd_as = Column(Unicode(10)) # seed, urcu, other
    #recvd_as_other = Column(UnicodeText) # ** maybe this should be in the notes
    prop_type = Column(types.Enum(values=prop_type_values.keys()),
                       nullable=False)
    notes = Column(UnicodeText)
    plant_id = Column(Integer, ForeignKey('plant.id'), nullable=False)
    date = Column(types.Date)

    _cutting = relation('PropCutting',
                      primaryjoin='Propagation.id==PropCutting.propagation_id',
                      cascade='all,delete-orphan', uselist=False,
                      backref=backref('propagation', uselist=False))
    _seed = relation('PropSeed',
                     primaryjoin='Propagation.id==PropSeed.propagation_id',
                     cascade='all,delete-orphan', uselist=False,
                     backref=backref('propagation', uselist=False))

    def _get_details(self):
        if self.prop_type == 'Seed':
            return self._seed
        elif self.prop_type == 'UnrootedCutting':
            return self._cutting
        else:
            raise NotImplementedError

    #def _set_details(self, details):
    #    return self._details

    details = property(_get_details)

    def get_summary(self):
        """
        """
        def get_date(date):
            if isinstance(date, datetime.date):
                return seed.date_sown.strftime(date_format)
            return date

        s = str(self)
        if self.prop_type == u'UnrootedCutting':
            c = self._cutting
            values = []
            values.append(_('Cutting type: %s') % \
                              cutting_type_values[c.cutting_type])
            if c.length:
                values.append(_('Length: %s%s') % (c.length,
                              length_unit_values[c.length_unit]))
            values.append(_('Tip: %s') % tip_values[c.tip])
            s = _('Leaves: %s') % leaves_values[c.leaves]
            if c.leaves == u'Removed' and c.leaves_reduced_pct:
                s.append('(%s%%)' % c.leaves_reduced_pct)
            values.append(s)
            values.append(_('Flower buds: %s') % \
                              flower_buds_values[c.flower_buds])
            values.append(_('Wounded: %s' % wound_values[c.wound]))
            if c.fungicide:
                values.append(_('Fungal soak: %s' % c.fungicide))
            if c.hormone:
                values.append(_('Hormone treatment: %s' % c.hormone))
            if c.bottom_heat_temp:
                values.append(_('Bottom heat: %s%s') % \
                               (c.bottom_heat_temp,
                                bottom_heat_unit_values[c.bottom_heat_unit]))
            if c.container:
                values.append(_('Container: %s' % c.container))
            if c.media:
                values.append(_('Media: %s' % c.media))
            if c.location:
                values.append(_('Location: %s' % c.location))
            if c.cover:
                values.append(_('Cover: %s' % c.cover))

            if c.rooted_pct:
                values.append(_('Rooted: %s%%') % c.rooted_pct)
            s = ', '.join(values)
        elif self.prop_type == u'Seed':
            s = str(self)
            seed = self._seed
            date_format = prefs.prefs[prefs.date_format_pref]
            values = []
            if seed.pretreatment:
                values.append(_('Pretreatment: %s') % seed.pretreatment)
            if seed.nseeds:
                values.append(_('# of seeds: %s') % seed.nseeds)
            date_sown = get_date(seed.date_sown)
            if date_sown:
                values.append(_('Date sown: %s') % date_sown)
            if seed.container:
                values.append(_('Container: %s') % seed.container)
            if seed.media:
                values.append(_('Media: %s') % seed.media)
            if seed.covered:
                values.append(_('Covered: %s') % seed.covered)
            if seed.location:
                values.append(_('Location: %s') % seed.location)
            germ_date = get_date(seed.germ_date)
            if germ_date:
                values.append(_('Germination date: %s') % germ_date)
            if seed.nseedlings:
                values.append(_('# of seedlings: %s') % seed.nseedlings)
            if seed.germ_pct:
                values.append(_('Germination rate: %s%%') % seed.germ_pct)
            date_planted = get_date(seed.date_planted)
            if date_planted:
                values.append(_('Date planted: %s') % seed.date_planted)
            s = ', '.join(values)

        return s



class PropRooted(db.Base):
    """
    Rooting dates for cutting
    """
    __tablename__ = 'prop_cutting_rooted'
    __mapper_args__ = {'order_by': 'date'}

    date = Column(types.Date)
    quantity = Column(Integer)
    cutting_id = Column(Integer, ForeignKey('prop_cutting.id'), nullable=False)



cutting_type_values = {u'Nodal': _('Nodal'),
                       u'InterNodal': _('Internodal'),
                       u'Other': _('Other')}

tip_values = {u'Intact': _('Intact'),
              u'Removed': _('Removed'),
              u'None': _('None')}

leaves_values = {u'Intact': _('Intact'),
                 u'Removed': _('Removed'),
                 u'None': _('None')}

flower_buds_values = {u'Removed': _('Removed'),
                      u'None': _('None')}

wound_values = {u'No': _('No'),
                u'Single': _('Singled'),
                u'Double': _('Double'),
                u'Slice': _('Slice')}

hormone_values = {u'Liquid': _('Liquid'),
                  u'Powder': _('Powder'),
                  u'No': _('No')}

bottom_heat_unit_values = {u'F': _('\302\260F'),
                           u'C': _('\302\260C'),
                           None: ''}

length_unit_values = {u'cm': _('cm'),
                      u'in': _('in'),
                      None: ''}

class PropCutting(db.Base):
    """
    A cutting
    """
    __tablename__ = 'prop_cutting'
    cutting_type = Column(types.Enum(values=cutting_type_values.keys()),
                          default=u'Other')
    tip = Column(types.Enum(values=tip_values.keys()), nullable=False)
    leaves = Column(types.Enum(values=leaves_values.keys()), nullable=False)
    leaves_reduced_pct = Column(Integer)
    length = Column(Integer)
    length_unit = Column(types.Enum(values=length_unit_values.keys()))

    # single/double/slice
    wound = Column(types.Enum(values=wound_values.keys()), nullable=False)

    # removed/None
    flower_buds = Column(types.Enum(values=flower_buds_values.keys()),
                         nullable=False)

    fungicide = Column(Unicode) # fungal soak
    hormone = Column(Unicode) # powder/liquid/None....solution

    media = Column(Unicode)
    container = Column(Unicode)
    location = Column(Unicode)
    cover = Column(Unicode) # vispore, poly, plastic dome, poly bag

    bottom_heat_temp = Column(Integer) # temperature of bottom heat

    # TODO: make the bottom heat unit required if bottom_heat_temp is
    # not null

    # F/C
    bottom_heat_unit = Column(types.Enum(values=\
                                             bottom_heat_unit_values.keys()),
                              nullable=True)
    rooted_pct = Column(Integer)
    #aftercare = Column(UnicodeText) # same as propgation.notes

    propagation_id = Column(Integer, ForeignKey('propagation.id'),
                            nullable=False)

    rooted = relation('PropRooted', cascade='all,delete-orphan',
                        backref=backref('cutting', uselist=False))


class PropSeed(db.Base):
    """
    """
    __tablename__ = 'prop_seed'
    pretreatment = Column(UnicodeText)
    nseeds = Column(Integer, nullable=False)
    date_sown = Column(types.Date, nullable=False)
    container = Column(Unicode) # 4" pot plug tray, other
    media = Column(Unicode) # seedling media, sphagnum, other

    # covered with #2 granite grit: no, yes, lightly heavily
    covered = Column(Unicode)

    # not same as location table, glasshouse(bottom heat, no bottom
    # heat), polyhouse, polyshade house, fridge in polybag
    location = Column(Unicode)

    # TODO: do we need multiple moved to->moved from and date fields
    moved_from = Column(Unicode)
    moved_to = Column(Unicode)
    moved_date = Column(types.Date)

    germ_date = Column(types.Date)

    nseedlings = Column(Integer) # number of seedling
    germ_pct = Column(Integer) # % of germination
    date_planted = Column(types.Date)

    propagation_id = Column(Integer, ForeignKey('propagation.id'),
                            nullable=False)


    def __str__(self):
        # what would the string be...???
        # cuttings of self.accession.species_str() and accession number
        return repr(self)



class PropagationTabPresenter(editor.GenericEditorPresenter):

    def __init__(self, parent, model, view, session):
        '''
        @param parent: an instance of AccessionEditorPresenter
        @param model: an instance of class Accession
        @param view: an instance of AccessionEditorView
        @param session:
        '''
        super(PropagationTabPresenter, self).__init__(model, view)
        self.parent_ref = weakref.ref(parent)
        self.session = session
        self.view.connect('prop_add_button', 'clicked',
                          self.on_add_button_clicked)
        tab_box = self.view.widgets.prop_tab_box
        for kid in tab_box:
            if isinstance(kid, gtk.Box):
                tab_box.remove(kid) # remove old prop boxes
        for prop in self.model.propagations:
            box = self.create_propagation_box(prop)
            tab_box.pack_start(box, expand=False, fill=True)
        self.__dirty = False


    def dirty(self):
        return self.__dirty or \
            True in [p in self.session.dirty for p in self.model.propagations]


    def add_propagation(self):
        # TODO: here the propagation editor doesn't commit the changes
        # since the accession editor will commit the changes when its
        # done...we should merge the propagation created by the
        # PropagationEditor into the parent accession session and
        # append it to the propagations relation so that when the
        # parent editor is saved then the propagations are save with
        # it

        # open propagation editor
        editor = PropagationEditor(parent=self.view.get_window())
        propagation = editor.start(commit=False)
        if propagation:
            propagation = self.session.merge(propagation)
            self.model.propagations.append(propagation)
            box = self.create_propagation_box(propagation)
            self.view.widgets.prop_tab_box.pack_start(box, expand=False,
                                                      fill=True)
            self.__dirty = True


    def create_propagation_box(self, propagation):
        """
        """
        hbox = gtk.HBox()
        expander = gtk.Expander()
        hbox.pack_start(expander, expand=True, fill=True)
        alignment = gtk.Alignment()
        hbox.pack_start(alignment, expand=False, fill=False)

        label = gtk.Label(propagation.get_summary())
        label.props.wrap = True
        label.set_alignment(0.1, 0.5)
        expander.add(label)

        def on_clicked(button, prop, label):
            editor = PropagationEditor(model=prop,
                                       parent=self.view.get_window())
            editor.start(commit=False)
            label.props.label = prop.get_summary()
            self.parent_ref().refresh_sensitivity()
        button = gtk.Button(stock=gtk.STOCK_EDIT)
        self.view.connect(button, 'clicked', on_clicked, propagation, label)
        alignment.add(button)
        # TODO: add a * to the propagation label for uncommitted propagations
        prop_type = prop_type_values[propagation.prop_type]
        title = ('%(prop_type)s on %(prop_date)s') \
            % dict(prop_type=prop_type, prop_date=propagation.date)
        expander.set_label(title)

        hbox.show_all()
        return hbox


    def remove_propagation(self):
        """
        """
        pass


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
                           'cutting_rooted_pct_entry': 'rooted_pct'
                           }

    def __init__(self, parent, model, view, session):
        '''
        @param model: an instance of class Propagation
        @param view: an instance of PropagationEditorView
        '''
        super(CuttingPresenter, self).__init__(model, view)
        self.parent_ref = weakref.ref(parent)
        self.session = session
        self.__dirty = False

        # make the model for the presenter a PropCutting instead of a
        # Propagation
        self.propagation = self.model
        if not self.propagation._cutting:
            self.propagation._cutting = PropCutting()
        self.model = self.model._cutting
        #self.session.add(self.model)

        self.init_translatable_combo('cutting_type_combo', cutting_type_values,
                                     editor.UnicodeOrNoneValidator())
        self.init_translatable_combo('cutting_length_unit_combo',
                                     length_unit_values)
        self.init_translatable_combo('cutting_tip_combo', tip_values)
        self.init_translatable_combo('cutting_leaves_combo', leaves_values)
        self.init_translatable_combo('cutting_buds_combo', flower_buds_values)
        self.init_translatable_combo('cutting_wound_combo', wound_values)
        self.init_translatable_combo('cutting_heat_unit_combo',
                                     bottom_heat_unit_values)

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

        model = gtk.ListStore(object)
        self.view.widgets.rooted_treeview.set_model(model)

        def _rooted_data_func(column, cell, model, treeiter, prop):
            v = model[treeiter][0]
            cell.set_property('text', getattr(v, prop))

        cell = self.view.widgets.rooted_date_cell
        cell.props.editable = True
        self.view.connect(cell, 'edited', self.on_rooted_cell_edited, 'date')
        self.view.widgets.rooted_date_column.\
            set_cell_data_func(cell, _rooted_data_func, 'date')

        cell = self.view.widgets.rooted_quantity_cell
        cell.props.editable = True
        self.view.connect(cell, 'edited', self.on_rooted_cell_edited,
                          'quantity')
        self.view.widgets.rooted_quantity_column.\
            set_cell_data_func(cell, _rooted_data_func, 'quantity')

        self.view.connect('rooted_add_button', "clicked",
                          self.on_rooted_add_clicked)
        self.view.connect('rooted_remove_button', "clicked",
                          self.on_rooted_remove_clicked)

        # set default units
        units = prefs.prefs[prefs.units_pref]
        if units == u'imperial':
            self.view.set_widget_value('cutting_length_unit_combo', u'in')
            self.view.set_widget_value('cutting_heat_unit_combo', u'F')
        else:
            self.view.set_widget_value('cutting_length_unit_combo', u'cm')
            self.view.set_widget_value('cutting_heat_unit_combo', u'C')


    def dirty(self):
        return self.__dirty


    def set_model_attr(self, field, value, validator=None):
        super(CuttingPresenter, self).set_model_attr(field, value, validator)
        self.__dirty = True
        self.parent_ref().refresh_sensitivity()


    def on_rooted_cell_edited(self, cell, path, new_text, prop):
        treemodel = self.view.widgets.rooted_treeview.get_model()
        rooted = treemodel[path][0]
        if getattr(rooted, prop) == new_text:
            return  # didn't change
        setattr(rooted, prop, utils.utf8(new_text))
        self.__dirty = True
        self.parent_ref().refresh_sensitivity()


    def on_rooted_add_clicked(self, button, *args):
        """
        """
        tree = self.view.widgets.rooted_treeview
        model = tree.get_model()
        rooted = PropRooted()
        rooted.cutting = self.model
        rooted.date = utils.today_str()
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
        self.__dirty = True
        self.parent_ref().refresh_sensitivity()


    def refresh_view(self):
        for widget, attr in self.widget_to_field_map.iteritems():
            value = getattr(self.model, attr)
            #debug('%s: %s' % (widget, value))
            self.view.set_widget_value(widget, value)



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
        @param model: an instance of class Propagation
        @param view: an instance of PropagationEditorView
        '''
        super(SeedPresenter, self).__init__(model, view)
        self.__dirty = False
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

        self.assign_simple_handler('seed_pretreatment_textview','pretreatment',
                                   editor.UnicodeOrNoneValidator())
        self.assign_simple_handler('seed_nseeds_entry', 'nseeds',
                                   editor.UnicodeOrNoneValidator())
        self.assign_simple_handler('seed_sown_entry', 'date_sown',
                                   editor.DateValidator())
        utils.setup_date_button(self.view.widgets.seed_sown_entry,
                                self.view.widgets.seed_sown_button)
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
        utils.setup_date_button(self.view.widgets.seed_germdate_entry,
                                self.view.widgets.seed_germdate_button)
        self.assign_simple_handler('seed_ngerm_entry', 'nseedlings')
        self.assign_simple_handler('seed_pctgerm_entry', 'germ_pct')
        self.assign_simple_handler('seed_date_planted_entry', 'date_planted',
                                   editor.DateValidator())
        utils.setup_date_button(self.view.widgets.seed_date_planted_entry,
                                self.view.widgets.seed_date_planted_button)


    def dirty(self):
        return self.__dirty


    def set_model_attr(self, field, value, validator=None):
        super(SeedPresenter, self).set_model_attr(field, value, validator)
        self.__dirty = True
        self.parent_ref().refresh_sensitivity()


    def refresh_view(self):
        for widget, attr in self.widget_to_field_map.iteritems():
            value = getattr(self.model, attr)
            self.view.set_widget_value(widget, value)


class PropagationEditorPresenter(editor.GenericEditorPresenter):

    widget_to_field_map = {'prop_type_combo': 'prop_type',
                           'prop_date_entry': 'date'}

    def __init__(self, model, view):
        '''
        @param model: an instance of class Propagation
        @param view: an instance of PropagationEditorView
        '''
        super(PropagationEditorPresenter, self).__init__(model, view)
        self.session = object_session(model)

        self.view.widgets.prop_ok_button.props.sensitive = False

        # initialize the propagation type combo and set the initial value
        self.init_translatable_combo('prop_type_combo', prop_type_values)
        self.view.connect('prop_type_combo', 'changed',
                          self.on_prop_type_changed)
        if self.model.prop_type:
            self.view.set_widget_value('prop_type_combo', self.model.prop_type)

        # don't allow changing the propagation type if we are editing
        # an existing propagation
        if model not in self.session.new or self.model.prop_type:
            self.view.widgets.prop_type_box.props.visible = False
        elif not self.model.prop_type:
            self.view.widgets.prop_type_box.props.visible = True
            self.view.widgets.prop_box_parent.props.visible = False

        self._cutting_presenter = CuttingPresenter(self, self.model, self.view,
                                                   self.session)
        self._seed_presenter = SeedPresenter(self, self.model, self.view,
                                                   self.session)

        self.assign_simple_handler('prop_date_entry', 'date',
                                   editor.DateValidator())
        utils.setup_date_button(self.view.widgets.prop_date_entry,
                                self.view.widgets.prop_date_button)

        if not self.model.date:
            # set it to empty first b/c if we set the date and its the
            # same as the date string already in the entry then it
            # won't fire the 'changed' signal
            self.view.set_widget_value(self.view.widgets.prop_date_entry, '')
            self.view.set_widget_value(self.view.widgets.prop_date_entry,
                                       utils.today_str())


    def on_prop_type_changed(self, combo, *args):
        it = combo.get_active_iter()
        prop_type = combo.get_model()[it][0]
        self.set_model_attr('prop_type', prop_type)

        prop_box_map = {u'Seed': self.view.widgets.seed_box,
                        u'UnrootedCutting': self.view.widgets.cutting_box,
                        u'Other': self.view.widgets.prop_notes_box}

        parent = self.view.widgets.prop_box_parent
        prop_box = prop_box_map[prop_type]
        child = parent.get_child()
        if child:
            parent.remove(child)
        self.view.widgets.remove_parent(prop_box)
        parent.add(prop_box)
        self.view.widgets.prop_box_parent.props.visible = True


    def dirty(self):
        if self.model.prop_type == u'UnrootedCutting':
            return self._cutting_presenter.dirty()
        elif self.model.prop_type == u'Seed':
            return self._seed_presenter.dirty()
        else:
            return False


    def set_model_attr(self, field, value, validator=None):
        """
        Set attributes on the model and update the GUI as expected.
        """
        #debug('set_model_attr(%s, %s)' % (field, value))
        super(PropagationEditorPresenter, self).set_model_attr(field, value,
                                                               validator)

    def refresh_sensitivity(self):
        sensitive = True
        model = None
        if self.model.prop_type == u'UnrootedCutting':
            model = self.model._cutting
        elif self.model.prop_type == u'Seed':
            model = self.model._seed


        if model:
            invalid = utils.get_invalid_columns(model)
            # TODO: highlight the widget with are associated with the
            # columns that have bad values
            if invalid:
                sensitive = False
            #     if self.model.prop_type == u'UnrootedCutting':
            #         presenter = self._cutting_presenter
            #         model = self.model._cutting
            #     elif self.model.prop_type == u'Seed':
            #         presenter = self._seed_presenter
            #         model = self.model._seed
        else:
            sensitive = False

        self.view.widgets.prop_ok_button.props.sensitive = sensitive


    def refresh_view(self):
        pass

    def start(self):
        r = self.view.start()
        return r


class PropagationEditor(editor.GenericModelViewPresenterEditor):

    # these have to correspond to the response values in the view
    RESPONSE_OK_AND_ADD = 11
    RESPONSE_NEXT = 22
    ok_responses = (RESPONSE_OK_AND_ADD, RESPONSE_NEXT)


    def __init__(self, model=None, parent=None):
        '''
        @param model: Propagation instance
        @param parent: the parent widget
        '''
        # the view and presenter are created in self.start()
        self.view = None
        self.presenter = None
        if model is None:
            debug('create propagation')
            model = Propagation()
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

        # add quick response keys
        self.attach_response(view.get_window(), gtk.RESPONSE_OK, 'Return',
                             gtk.gdk.CONTROL_MASK)
        self.attach_response(view.get_window(), self.RESPONSE_OK_AND_ADD, 'k',
                             gtk.gdk.CONTROL_MASK)
        self.attach_response(view.get_window(), self.RESPONSE_NEXT, 'n',
                             gtk.gdk.CONTROL_MASK)

        # set the default focus
        # if self.model.species is None:
        #     view.widgets.acc_species_entry.grab_focus()
        # else:
        #     view.widgets.acc_code_entry.grab_focus()

    def clean_model(self):
        if self.model.prop_type == u'UnrootedCutting':
            utils.delete_or_expunge(self.model._seed)
            self.model._seed = None
            del self.model._seed
            if not self.model._cutting.bottom_heat_temp:
                self.model._cutting.bottom_heat_unit = None
            if not self.model._cutting.length:
                self.model._cutting.length_unit = None
        elif self.model.prop_type == u'Seed':
            utils.delete_or_expunge(self.model._cutting)
            self.model._cutting = None
            del self.model._cutting


    def handle_response(self, response, commit=True):
        '''
        handle the response from self.presenter.start() in self.start()
        '''
        not_ok_msg = 'Are you sure you want to lose your changes?'
        self._return = None
        self.clean_model()
        if response == gtk.RESPONSE_OK or response in self.ok_responses:
            try:
                self._return = self.model
                if self.presenter.dirty() and commit:
                    self.commit_changes()
            except SQLError, e:
                msg = _('Error committing changes.\n\n%s') % \
                      utils.xml_safe_utf8(unicode(e.orig))
                utils.message_details_dialog(msg, str(e), gtk.MESSAGE_ERROR)
                if commit:
                    self.session.rollback()
                return False
            except Exception, e:
                msg = _('Unknown error when committing changes. See the '\
                        'details for more information.\n\n%s') \
                        % utils.xml_safe_utf8(e)
                debug(traceback.format_exc())
                utils.message_details_dialog(msg, traceback.format_exc(),
                                             gtk.MESSAGE_ERROR)
                if commit:
                    self.session.rollback()
                return False
        elif self.presenter.dirty() and utils.yes_no_dialog(not_ok_msg) \
                 or not self.presenter.dirty():
            if commit:
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
        # on an AccessionEditor
        #
        #self.session.close() # cleanup session
        self.presenter.cleanup()
        return self._return

