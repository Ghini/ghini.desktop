# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Brett Adams
# Copyright 2015-2016 Mario Frasca <mario@anche.no>.
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
#
# source.py
#
import os
import traceback
import weakref
from random import random

import logging
logger = logging.getLogger(__name__)

import gtk
import gobject

from sqlalchemy import Column, Unicode, Integer, ForeignKey,\
    Float, UnicodeText, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import relation, backref


import bauble.db as db
import bauble.editor as editor
from bauble.plugins.plants.geography import Geography, GeographyMenu
import bauble.utils as utils
import bauble.btypes as types
import bauble.view as view
import bauble.paths as paths
from types import StringTypes


def collection_edit_callback(coll):
    from bauble.plugins.garden.accession import edit_callback
    # TODO: set the tab to the source tab on the accession editor
    return edit_callback([coll[0].source.accession])


def collection_add_plants_callback(coll):
    from bauble.plugins.garden.accession import add_plants_callback
    return add_plants_callback([coll[0].source.accession])


def collection_remove_callback(coll):
    from bauble.plugins.garden.accession import remove_callback
    return remove_callback([coll[0].source.accession])

collection_edit_action = view.Action('collection_edit', _('_Edit'),
                                     callback=collection_edit_callback,
                                     accelerator='<ctrl>e')
collection_add_plant_action = \
    view.Action('collection_add', _('_Add plants'),
                callback=collection_add_plants_callback,
                accelerator='<ctrl>k')
collection_remove_action = view.Action('collection_remove', _('_Delete'),
                                       callback=collection_remove_callback,
                                       accelerator='<ctrl>Delete')

collection_context_menu = [collection_edit_action, collection_add_plant_action,
                           collection_remove_action]


class Source(db.Base):
    """connected 1-1 to Accession.

    Source objects have the function to add fields to one Accession.  From
    an Accession, to access the fields added here you obviously still need
    to go through its `.source` member.

    Create an Accession a, then create a Source s, then assign a.source = s

    """
    __tablename__ = 'source'
    # ITF2 - E7 - Donor's Accession Identifier - donacc
    sources_code = Column(Unicode(32))

    accession_id = Column(Integer, ForeignKey('accession.id'), unique=True)

    source_detail_id = Column(Integer, ForeignKey('source_detail.id'))
    source_detail = relation('Contact', uselist=False,
                             backref=backref('sources',
                                             cascade='all, delete-orphan'))

    collection = relation('Collection', uselist=False,
                          cascade='all, delete-orphan',
                          backref=backref('source', uselist=False))

    # relation to a propagation that is specific to this Source and
    # not attached to a Plant. 2017-06-04 : WHAT IS THIS ?
    propagation_id = Column(Integer, ForeignKey('propagation.id'))
    propagation = relation('Propagation', uselist=False, single_parent=True,
                           primaryjoin='Source.propagation_id==Propagation.id',
                           cascade='all, delete-orphan',
                           backref=backref('source', uselist=False))

    # an Accession of known Source (what we are describing here) may be in
    # relation to a successful Plant Propagation trial. In this case, the
    # Propagation points back to all Accessions that resulted from it, via
    # `used_source[i].accession`. Arguably not practical.
    plant_propagation_id = Column(Integer, ForeignKey('propagation.id'))
    plant_propagation = relation(
        'Propagation', uselist=False,
        primaryjoin='Source.plant_propagation_id==Propagation.id',
        backref=backref('used_source', uselist=True))


source_type_values = [(u'Expedition', _('Expedition')),
                      (u'GeneBank', _('Gene Bank')),
                      (u'BG', _('Botanic Garden or Arboretum')),
                      (u'Research/FieldStation', _('Research/Field Station')),
                      (u'Staff', _('Staff member')),
                      (u'UniversityDepartment', _('University Department')),
                      (u'Club', _('Horticultural Association/Garden Club')),
                      (u'MunicipalDepartment', _('Municipal department')),
                      (u'Commercial', _('Nursery/Commercial')),
                      (u'Individual', _('Individual')),
                      (u'Other', _('Other')),
                      (u'Unknown', _('Unknown')),
                      (None, '')]


# TODO: should have a label next to lat/lon entry to show what value will be
# stored in the database, might be good to include both DMS and the float
# so the user can see both no matter what is in the entry. it could change in
# time as the user enters data in the entry
# TODO: shouldn't allow entering altitude accuracy without entering altitude,
# same for geographic accuracy
# TODO: should show an error if something other than a number is entered in
# the altitude entry

# TODO: should provide a collection type: alcohol, bark, boxed,
# cytological, fruit, illustration, image, other, packet, pollen,
# print, reference, seed, sheet, slide, transparency, vertical,
# wood.....see HISPID standard, in general need to be more herbarium
# aware

# TODO: create a DMS column type to hold latitude and longitude,
# should probably store the DMS data as a string in decimal degrees

############################################################
#
# Collection
#

class Collection(db.Base):
    """
    :Table name: collection

    :Columns:
            *collector*: :class:`sqlalchemy.types.Unicode`

            *collectors_code*: :class:`sqlalchemy.types.Unicode`

            *date*: :class:`sqlalchemy.types.Date`

            *locale*: :class:`sqlalchemy.types.UnicodeText`

            *latitude*: :class:`sqlalchemy.types.Float`

            *longitude*: :class:`sqlalchemy.types.Float`

            *gps_datum*: :class:`sqlalchemy.types.Unicode`

            *geo_accy*: :class:`sqlalchemy.types.Float`

            *elevation*: :class:`sqlalchemy.types.Float`

            *elevation_accy*: :class:`sqlalchemy.types.Float`

            *habitat*: :class:`sqlalchemy.types.UnicodeText`

            *geography_id*: :class:`sqlalchemy.types.Integer`

            *notes*: :class:`sqlalchemy.types.UnicodeText`

            *accession_id*: :class:`sqlalchemy.types.Integer`


    :Properties:


    :Constraints:
    """
    __tablename__ = 'collection'

    # columns
    # ITF2 - F24 - Primary Collector's Name
    collector = Column(Unicode(64))
    # ITF2 - F.25 - Collector's Identifier
    collectors_code = Column(Unicode(50))
    # ITF2 - F.27 - Collection Date
    date = Column(types.Date)
    locale = Column(UnicodeText, nullable=False)
    # ITF2 - F1, F2, F3, F4 - Latitude, Degrees, Minutes, Seconds, Direction
    latitude = Column(Unicode(15))
    # ITF2 - F5, F6, F7, F8 - Longitude, Degrees, Minutes, Seconds, Direction
    longitude = Column(Unicode(15))
    gps_datum = Column(Unicode(32))
    # ITF2 - F9 - Accuracy of Geographical Referencing Data
    geo_accy = Column(Float)
    # ITF2 - F17 - Altitude
    elevation = Column(Float)
    # ITF2 - F18 - Accuracy of Altitude
    elevation_accy = Column(Float)
    # ITF2 - F22 - Habitat
    habitat = Column(UnicodeText)
    # ITF2 - F18 - Collection Notes
    notes = Column(UnicodeText)

    geography_id = Column(Integer, ForeignKey('geography.id'))
    region = relation(Geography, uselist=False)

    source_id = Column(Integer, ForeignKey('source.id'), unique=True)

    def search_view_markup_pair(self):
        '''provide the two lines describing object for SearchView row.
        '''
        acc = self.source.accession
        safe = utils.xml_safe
        return (
            '%s - <small>%s</small>' % (safe(acc), safe(acc.species_str())),
            safe(self))

    def __str__(self):
        return _('Collection at %s') % (self.locale or repr(self))


class CollectionPresenter(editor.ChildPresenter):

    """
    CollectionPresenter

    :param parent: an AccessionEditorPresenter
    :param model: a Collection instance
    :param view: an AccessionEditorView
    :param session: a sqlalchemy.orm.session
    """
    widget_to_field_map = {'collector_entry': 'collector',
                           'coll_date_entry': 'date',
                           'collid_entry': 'collectors_code',
                           'locale_entry': 'locale',
                           'lat_entry': 'latitude',
                           'lon_entry': 'longitude',
                           'geoacc_entry': 'geo_accy',
                           'alt_entry': 'elevation',
                           'altacc_entry': 'elevation_accy',
                           'habitat_textview': 'habitat',
                           'coll_notes_textview': 'notes',
                           'datum_entry': 'gps_datum',
                           'add_region_button': 'region',
                           }

    # TODO: could make the problems be tuples of an id and description to
    # be displayed in a dialog or on a label ala eclipse
    PROBLEM_BAD_LATITUDE = str(random())
    PROBLEM_BAD_LONGITUDE = str(random())
    PROBLEM_INVALID_DATE = str(random())
    PROBLEM_INVALID_LOCALE = str(random())

    def __init__(self, parent, model, view, session):
        super(CollectionPresenter, self).__init__(model, view)
        self.parent_ref = weakref.ref(parent)
        self.session = session
        self.refresh_view()

        self.assign_simple_handler('collector_entry', 'collector',
                                   editor.UnicodeOrNoneValidator())
        self.assign_simple_handler('locale_entry', 'locale',
                                   editor.UnicodeOrNoneValidator())
        self.assign_simple_handler('collid_entry', 'collectors_code',
                                   editor.UnicodeOrNoneValidator())
        self.assign_simple_handler('geoacc_entry', 'geo_accy',
                                   editor.IntOrNoneStringValidator())
        self.assign_simple_handler('alt_entry', 'elevation',
                                   editor.FloatOrNoneStringValidator())
        self.assign_simple_handler('altacc_entry', 'elevation_accy',
                                   editor.FloatOrNoneStringValidator())
        self.assign_simple_handler('habitat_textview', 'habitat',
                                   editor.UnicodeOrNoneValidator())
        self.assign_simple_handler('coll_notes_textview', 'notes',
                                   editor.UnicodeOrNoneValidator())
        # the list of completions are added in AccessionEditorView.__init__

        def on_match(completion, model, iter, data=None):
            value = model[iter][0]
            validator = editor.UnicodeOrNoneValidator()
            self.set_model_attr('gps_data', value, validator)
            completion.get_entry().set_text(value)
        completion = self.view.widgets.datum_entry.get_completion()
        self.view.connect(completion, 'match-selected', on_match)
        self.assign_simple_handler('datum_entry', 'gps_datum',
                                   editor.UnicodeOrNoneValidator())

        self.view.connect('lat_entry', 'changed', self.on_lat_entry_changed)
        self.view.connect('lon_entry', 'changed', self.on_lon_entry_changed)

        self.view.connect('coll_date_entry', 'changed',
                          self.on_date_entry_changed)

        utils.setup_date_button(view, 'coll_date_entry',
                                'coll_date_button')

        # don't need to connection to south/west since they are in the same
        # groups as north/east
        self.north_toggle_signal_id = \
            self.view.connect('north_radio', 'toggled',
                              self.on_north_south_radio_toggled)
        self.east_toggle_signal_id = \
            self.view.connect('east_radio', 'toggled',
                              self.on_east_west_radio_toggled)

        self.view.widgets.add_region_button.set_sensitive(False)

        def on_add_button_pressed(button, event):
            self.geo_menu.popup(None, None, None, event.button, event.time)
        self.view.connect('add_region_button', 'button-press-event',
                          on_add_button_pressed)

        def _init_geo():
            add_button = self.view.widgets.add_region_button
            self.geo_menu = GeographyMenu(self.set_region)
            self.geo_menu.attach_to_widget(add_button, None)
            add_button.set_sensitive(True)
        gobject.idle_add(_init_geo)

        self._dirty = False

    def set_region(self, menu_item, geo_id):
        geography = self.session.query(Geography).get(geo_id)
        self.set_model_attr('region', geography)
        self.set_model_attr('geography_id', geo_id)
        self.view.widgets.add_region_button.props.label = str(geography)

    def set_model_attr(self, field, value, validator=None):
        """
        Validates the fields when a field changes.
        """
        super(CollectionPresenter, self).set_model_attr(
            field, value, validator)
        self._dirty = True
        if self.model.locale is None or self.model.locale in ('', u''):
            self.add_problem(self.PROBLEM_INVALID_LOCALE)
        else:
            self.remove_problem(self.PROBLEM_INVALID_LOCALE)

        if field in ('longitude', 'latitude'):
            sensitive = self.model.latitude is not None \
                and self.model.longitude is not None
            self.view.widgets.geoacc_entry.set_sensitive(sensitive)
            self.view.widgets.datum_entry.set_sensitive(sensitive)

        if field == 'elevation':
            sensitive = self.model.elevation is not None
            self.view.widgets.altacc_entry.set_sensitive(sensitive)

        self.parent_ref().refresh_sensitivity()

    def start(self):
        raise Exception('CollectionPresenter cannot be started')

    def dirty(self):
        return self._dirty

    def refresh_view(self):
        from bauble.plugins.garden.accession import latitude_to_dms, \
            longitude_to_dms
        for widget, field in self.widget_to_field_map.iteritems():
            value = getattr(self.model, field)
            logger.debug('%s, %s, %s' % (widget, field, value))
            if value is not None and field == 'date':
                value = '%s/%s/%s' % (value.day, value.month,
                                      '%04d' % value.year)
            self.view.widget_set_value(widget, value)

        latitude = self.model.latitude
        if latitude is not None:
            dms_string = u'%s %s\u00B0%s\'%s"' % latitude_to_dms(latitude)
            self.view.widgets.lat_dms_label.set_text(dms_string)
            if float(latitude) < 0:
                self.view.widgets.south_radio.set_active(True)
            else:
                self.view.widgets.north_radio.set_active(True)
        else:
            self.view.widgets.lat_dms_label.set_text('')
            self.view.widgets.north_radio.set_active(True)

        longitude = self.model.longitude
        if longitude is not None:
            dms_string = u'%s %s\u00B0%s\'%s"' % longitude_to_dms(longitude)
            self.view.widgets.lon_dms_label.set_text(dms_string)
            if float(longitude) < 0:
                self.view.widgets.west_radio.set_active(True)
            else:
                self.view.widgets.east_radio.set_active(True)
        else:
            self.view.widgets.lon_dms_label.set_text('')
            self.view.widgets.east_radio.set_active(True)

        if self.model.elevation is None:
            self.view.widgets.altacc_entry.set_sensitive(False)

        if self.model.latitude is None or self.model.longitude is None:
            self.view.widgets.geoacc_entry.set_sensitive(False)
            self.view.widgets.datum_entry.set_sensitive(False)

    def on_date_entry_changed(self, entry, data=None):
        from bauble.editor import ValidatorError
        value = None
        PROBLEM = 'INVALID_DATE'
        try:
            value = editor.DateValidator().to_python(entry.props.text)
        except ValidatorError, e:
            logger.debug(e)
            self.parent_ref().add_problem(PROBLEM, entry)
        else:
            self.parent_ref().remove_problem(PROBLEM, entry)
        self.set_model_attr('date', value)

    def on_east_west_radio_toggled(self, button, data=None):
        direction = self._get_lon_direction()
        entry = self.view.widgets.lon_entry
        lon_text = entry.get_text()
        if lon_text == '':
            return

        try:
            # make sure that the first part of the string is an
            # integer before toggling
            int(lon_text.split(' ')[0])
        except Exception, e:
            logger.warn("east-west %s(%s)" % (type(e), e))
            return

        if direction == 'W' and lon_text[0] != '-':
            entry.set_text('-%s' % lon_text)
        elif direction == 'E' and lon_text[0] == '-':
            entry.set_text(lon_text[1:])

    def on_north_south_radio_toggled(self, button, data=None):
        direction = self._get_lat_direction()
        entry = self.view.widgets.lat_entry
        lat_text = entry.get_text()
        if lat_text == '':
            return

        try:
            # make sure that the first part of the string is an
            # integer before toggling
            int(lat_text.split(' ')[0])
        except Exception, e:
            logger.debug(e)
            return

        if direction == 'S' and lat_text[0] != '-':
            entry.set_text('-%s' % lat_text)
        elif direction == 'N' and lat_text[0] == '-':
            entry.set_text(lat_text[1:])

    @staticmethod
    def _parse_lat_lon(direction, text):
        """
        Parse a latitude or longitude in a variety of formats and
        return a degress decimal
        """

        import re
        from decimal import Decimal
        from bauble.plugins.garden.accession import dms_to_decimal
        parts = re.split(':| ', text.strip())
        if len(parts) == 1:
            dec = Decimal(text).copy_abs()
            if dec > 0 and direction in ('W', 'S'):
                dec = -dec
        elif len(parts) == 2:
            deg, min = map(Decimal, parts)
            dec = dms_to_decimal(direction, deg, min, 0)
        elif len(parts) == 3:
            dec = dms_to_decimal(direction, *map(Decimal, parts))
        else:
            raise ValueError(_('_parse_lat_lon() -- incorrect format: %s') %
                             text)
        return dec

    def _get_lat_direction(self):
        '''
        return N or S from the radio
        '''
        if self.view.widgets.north_radio.get_active():
            return 'N'
        elif self.view.widgets.south_radio.get_active():
            return 'S'
        raise ValueError(_('North/South radio buttons in a confused state'))

    def _get_lon_direction(self):
        '''
        return E or W from the radio
        '''
        if self.view.widgets.east_radio.get_active():
            return 'E'
        elif self.view.widgets.west_radio.get_active():
            return 'W'
        raise ValueError(_('East/West radio buttons in a confused state'))

    def on_lat_entry_changed(self, entry, date=None):
        '''
        set the latitude value from text
        '''
        from bauble.plugins.garden.accession import latitude_to_dms
        text = entry.get_text()
        latitude = None
        dms_string = ''
        try:
            if text != '' and text is not None:
                north_radio = self.view.widgets.north_radio
                north_radio.handler_block(self.north_toggle_signal_id)
                if text[0] == '-':
                    self.view.widgets.south_radio.set_active(True)
                else:
                    north_radio.set_active(True)
                north_radio.handler_unblock(self.north_toggle_signal_id)
                direction = self._get_lat_direction()
                latitude = CollectionPresenter._parse_lat_lon(direction, text)
                #u"\N{DEGREE SIGN}"
                dms_string = u'%s %s\u00B0%s\'%s"' % latitude_to_dms(latitude)
        except Exception:
            logger.debug(traceback.format_exc())
            #bg_color = gtk.gdk.color_parse("red")
            self.add_problem(self.PROBLEM_BAD_LATITUDE,
                             self.view.widgets.lat_entry)
        else:
            self.remove_problem(self.PROBLEM_BAD_LATITUDE,
                                self.view.widgets.lat_entry)

        self.view.widgets.lat_dms_label.set_text(dms_string)
        if text is None or text.strip() == '':
            self.set_model_attr('latitude', None)
        else:
            self.set_model_attr('latitude', utils.utf8(latitude))

    def on_lon_entry_changed(self, entry, data=None):
        from bauble.plugins.garden.accession import longitude_to_dms
        text = entry.get_text()
        longitude = None
        dms_string = ''
        try:
            if text != '' and text is not None:
                east_radio = self.view.widgets.east_radio
                east_radio.handler_block(self.east_toggle_signal_id)
                if text[0] == '-':
                    self.view.widgets.west_radio.set_active(True)
                else:
                    self.view.widgets.east_radio.set_active(True)
                east_radio.handler_unblock(self.east_toggle_signal_id)
                direction = self._get_lon_direction()
                longitude = CollectionPresenter._parse_lat_lon(direction, text)
                dms_string = u'%s %s\u00B0%s\'%s"' % longitude_to_dms(
                    longitude)
        except Exception:
            logger.debug(traceback.format_exc())
            #bg_color = gtk.gdk.color_parse("red")
            self.add_problem(self.PROBLEM_BAD_LONGITUDE,
                             self.view.widgets.lon_entry)
        else:
            self.remove_problem(self.PROBLEM_BAD_LONGITUDE,
                                self.view.widgets.lon_entry)

        self.view.widgets.lon_dms_label.set_text(dms_string)
        # self.set_model_attr('longitude', utils.utf8(longitude))
        if text is None or text.strip() == '':
            self.set_model_attr('longitude', None)
        else:
            self.set_model_attr('longitude', utils.utf8(longitude))


class PropagationChooserPresenter(editor.ChildPresenter):
    """
    Chooser for selecting an existing propagation for the source.

    :param parent: the parent AccessionEditorPresenter
    :param model: a Source instance
    :param view: an AccessionEditorView
    :param session: an sqlalchemy.orm.session
    """
    widget_to_field_map = {}

    PROBLEM_INVALID_DATE = random()

    def __init__(self, parent, model, view, session):
        super(PropagationChooserPresenter, self).__init__(model, view)
        self.parent_ref = weakref.ref(parent)
        self.session = session
        self._dirty = False

        self.refresh_view()

        cell = self.view.widgets.prop_toggle_cell
        self.view.widgets.prop_toggle_column.\
            set_cell_data_func(cell, self.toggle_cell_data_func)

        def on_toggled(cell, path, data=None):
            if cell.get_sensitive() is False:
                return
            prop = None
            if not cell.get_active():  # it's not active so we make it active
                treeview = self.view.widgets.source_prop_treeview
                prop = treeview.get_model()[path][0]
                acc_view = self.parent_ref().view
                acc_view.widget_set_value(
                    'acc_species_entry',
                    utils.utf8(prop.plant.accession.species))
                acc_view.widget_set_value(
                    'acc_quantity_recvd_entry',
                    utils.utf8(prop.accessible_quantity))
                from bauble.plugins.garden.accession import recvd_type_values
                from bauble.plugins.garden.propagation import prop_type_results
                acc_view.widget_set_value(
                    'acc_recvd_type_comboentry',
                    recvd_type_values[prop_type_results[prop.prop_type]],
                    index=1)
            self.model.plant_propagation = prop
            self._dirty = True
            self.parent_ref().refresh_sensitivity()

        self.view.connect_after(cell, 'toggled', on_toggled)

        self.view.widgets.prop_summary_column.\
            set_cell_data_func(self.view.widgets.prop_summary_cell,
                               self.summary_cell_data_func)

        #assign_completions_handler
        def plant_cell_data_func(column, renderer, model, iter, data=None):
            v = model[iter][0]
            renderer.set_property('text', '%s (%s)' %
                                  (str(v), str(v.accession.species)))

        self.view.attach_completion('source_prop_plant_entry',
                                    plant_cell_data_func, minimum_key_length=1)

        def plant_get_completions(text):
            logger.debug('in PropagationChooserPresenter:plant_get_completions')
            from bauble.plugins.garden.accession import Accession
            from bauble.plugins.garden.plant import Plant
            query = self.session.query(Plant).\
                    filter(Plant.propagations.any()).\
                    join('accession').\
                    filter(utils.ilike(Accession.code, u'%s%%' % text)).\
                    filter(Accession.id != self.model.accession.id).\
                    order_by(Accession.code, Plant.code)
            result = []
            for plant in query:
                has_accessible = False
                for propagation in plant.propagations:
                    if propagation.accessible_quantity > 0:
                        has_accessible = True
                if has_accessible:
                    result.append(plant)
            return result

        def on_select(value):
            logger.debug('on select: %s' % value)
            if isinstance(value, StringTypes):
                return
            # populate the propagation browser
            treeview = self.view.widgets.source_prop_treeview
            if not value:
                treeview.props.sensitive = False
                return
            utils.clear_model(treeview)
            model = gtk.ListStore(object)
            for propagation in value.propagations:
                if propagation.accessible_quantity == 0:
                    continue
                model.append([propagation])
            treeview.set_model(model)
            treeview.props.sensitive = True

        self.assign_completions_handler('source_prop_plant_entry',
                                        plant_get_completions,
                                        on_select=on_select)

    # def on_acc_entry_changed(entry, *args):
    #     # TODO: desensitize the propagation tree until on_select is called
    #     pass

    def refresh_view(self):
        treeview = self.view.widgets.source_prop_treeview
        if not self.model.plant_propagation:
            self.view.widgets.source_prop_plant_entry.props.text = ''
            utils.clear_model(treeview)
            treeview.props.sensitive = False
            return

        parent_plant = self.model.plant_propagation.plant
        # set the parent accession
        self.view.widgets.source_prop_plant_entry.props.text = str(
            parent_plant)

        if not parent_plant.propagations:
            treeview.props.sensitive = False
            return
        utils.clear_model(treeview)
        model = gtk.ListStore(object)
        for propagation in parent_plant.propagations:
            model.append([propagation])
        treeview.set_model(model)
        treeview.props.sensitive = True

    def toggle_cell_data_func(self, column, cell, model, treeiter, data=None):
        propagation = model[treeiter][0]
        active = self.model.plant_propagation == propagation
        cell.set_active(active)
        cell.set_sensitive(True)

    def summary_cell_data_func(self, column, cell, model, treeiter, data=None):
        propagation = model[treeiter][0]
        cell.props.text = propagation.get_summary()
        cell.set_sensitive(True)

    def dirty(self):
        return self._dirty


############################################################
#
# Contact / SourceDetails / Donor
#

def create_contact(parent=None):
    model = Contact()
    source_detail_edit_callback([model], parent)
    return [model]


def source_detail_edit_callback(details, parent=None):
    glade_path = os.path.join(paths.lib_dir(), "plugins", "garden",
                              "contact.glade")
    view = editor.GenericEditorView(
        glade_path,
        parent=parent,
        root_widget_name='source_details_dialog')
    model = details[0]
    presenter = ContactPresenter(model, view)
    result = presenter.start()
    return result is not None


def source_detail_remove_callback(details):
    detail = details[0]
    s = '%s: %s' % (detail.__class__.__name__, str(detail))
    msg = _("Are you sure you want to remove %s?") % utils.xml_safe(s)
    if not utils.yes_no_dialog(msg):
        return
    try:
        session = db.Session()
        obj = session.query(Contact).get(detail.id)
        session.delete(obj)
        session.commit()
    except Exception, e:
        msg = _('Could not delete.\n\n%s') % utils.xml_safe(e)
        utils.message_details_dialog(msg, traceback.format_exc(),
                                     type=gtk.MESSAGE_ERROR)
    finally:
        session.close()
    return True


source_detail_edit_action = view.Action('source_detail_edit', _('_Edit'),
                                        callback=source_detail_edit_callback,
                                        accelerator='<ctrl>e')
source_detail_remove_action = \
    view.Action('source_detail_remove', _('_Delete'),
                callback=source_detail_remove_callback,
                accelerator='<ctrl>Delete', multiselect=True)

source_detail_context_menu = [source_detail_edit_action,
                              source_detail_remove_action]


class Contact(db.Base, db.Serializable):
    __tablename__ = 'source_detail'
    __mapper_args__ = {'order_by': 'name'}

    # ITF2 - E6 - Donor
    name = Column(Unicode(75), unique=True)
    # extra description, not included in E6
    description = Column(UnicodeText)
    # ITF2 - E5 - Donor Type Flag
    source_type = Column(types.Enum(values=[i[0] for i in source_type_values],
                                    translations=dict(source_type_values)),
                         default=None)

    def __str__(self):
        return utils.utf8(self.name)

    def search_view_markup_pair(self):
        '''provide the two lines describing object for SearchView row.
        '''
        safe = utils.xml_safe
        return (
            safe(self.name),
            safe(self.source_type or ''))

    @classmethod
    def retrieve(cls, session, keys):
        try:
            return session.query(cls).filter(
                cls.name == keys['name']).one()
        except:
            return None


class ContactPresenter(editor.GenericEditorPresenter):

    widget_to_field_map = {'source_name_entry': 'name',
                           'source_type_combo': 'source_type',
                           'source_desc_textview': 'description',
                           }
    view_accept_buttons = ['sd_ok_button']

    def __init__(self, model, view):
        view.init_translatable_combo('source_type_combo', source_type_values)
        super(ContactPresenter, self).__init__(model, view, refresh_view=True,
                                               do_commit=True)
        self.create_toolbar()
        view.set_accept_buttons_sensitive(False)

    def on_textbuffer_changed_description(self, widget, value=None, attr=None):
        return self.on_textbuffer_changed(widget, value, attr='description')

    
class GeneralSourceDetailExpander(view.InfoExpander):
    '''
    Displays name, number of donations, address, email, fax, tel,
    type of contact
    '''
    def __init__(self, widgets):
        super(GeneralSourceDetailExpander, self).__init__(
            _('General'), widgets)
        gen_box = self.widgets.sd_gen_box
        self.widgets.remove_parent(gen_box)
        self.vbox.pack_start(gen_box)

    def update(self, row):
        #from textwrap import TextWrapper
        #wrapper = TextWrapper(width=50, subsequent_indent='  ')
        self.widget_set_value('sd_name_data', '<big>%s</big>' %
                              utils.xml_safe(row.name), markup=True)
        source_type = ''
        if row.source_type:
            source_type = utils.xml_safe(row.source_type)
        self.widget_set_value('sd_type_data', source_type)

        description = ''
        if row.description:
            description = utils.xml_safe(row.description)
        self.widget_set_value('sd_desc_data', description)

        source = Source.__table__
        nacc = select([source.c.id], source.c.source_detail_id == row.id).\
            count().execute().fetchone()[0]
        self.widget_set_value('sd_nacc_data', nacc)


class ContactInfoBox(view.InfoBox):

    def __init__(self):
        super(ContactInfoBox, self).__init__()
        filename = os.path.join(paths.lib_dir(), "plugins", "garden",
                                "source_detail_infobox.glade")
        self.widgets = utils.load_widgets(filename)
        self.general = GeneralSourceDetailExpander(self.widgets)
        self.add_expander(self.general)

    def update(self, row):
        self.general.update(row)
