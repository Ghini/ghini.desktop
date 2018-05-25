# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Brett Adams
# Copyright 2015,2018 Mario Frasca <mario@anche.no>.
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
# Description: edit and store information about the institution in the bauble
# meta
#

import os
import gi

from gi.repository import Gtk, Gdk

# mapping stuff
gi.require_version('GtkClutter', '1.0')
gi.require_version('GtkChamplain', '0.12')
gi.require_version('Champlain', '0.12')
from gi.repository import GtkClutter, Clutter, GtkChamplain
GtkClutter.init([])  # needed before importing Champlain
from gi.repository import Champlain

import logging
logger = logging.getLogger(__name__)

import re

import bauble.editor as editor
import bauble.meta as meta
import bauble.paths as paths
import bauble.pluginmgr as pluginmgr
import bauble.utils as utils

PADDING=6
import math

class MapViewer(Gtk.Dialog):

    def __init__(self, title="", parent=None, *args, **kwargs):
        super().__init__(title, parent, *args, **kwargs)
        self.result = None
        GtkClutter.init([])

        self.connect("key-press-event", self.on_key_press)

        self.map_widget = GtkChamplain.Embed()
        self.map_widget.set_size_request(640, 480)
        self.clutter_view = self.map_widget.get_view()
        self.clutter_view.set_horizontal_wrap(True)

        box = self.get_content_area()
        box.add(self.map_widget)

        ## now the Clutter stuff
        self.map_widget.set_size_request(640, 480)
        self.clutter_view = self.map_widget.get_view()
        self.clutter_view.set_horizontal_wrap(True)

        self.layer = None

        self.clutter_view.center_on(5.0, 13.0)
        self.clutter_view.set_zoom_level(1)
        self.clutter_view.connect("animation-completed", self.on_animation_completed)
        self.clutter_view.set_reactive(True)
        self.clutter_view.connect("button-release-event", self.on_view_button_release)

        offset = PADDING
        self.buttons = buttons = Clutter.Actor()
        self.clutter_view.add_child(buttons)

        button = self.make_button(_('OK'))
        button.set_position(offset, PADDING)
        (width, height) = button.get_size()
        offset += width + PADDING
        buttons.add_child(button)
        button.set_reactive(True)
        button.connect('button-release-event', self.on_clutter_ok_button)

        button = self.make_button(_('Cancel'))
        button.set_position(offset, PADDING)
        (width, height) = button.get_size()
        offset += width + PADDING
        buttons.add_child(button)
        button.set_reactive(True)
        button.connect('button-release-event', self.on_clutter_cancel_button)

        self.place_button = button = self.make_button(_('Activate'))
        button.set_position(PADDING, 2 * PADDING + height)
        buttons.add_child(button)
        button.set_reactive(True)
        button.connect('button-release-event', self.on_clutter_place_button)

        self.clutter_view.center_on(5.0, 13.0)
        self.clutter_view.set_zoom_level(1)
        self.show_all()

    def make_button(self, text):
        black = Clutter.Color.new(0x00, 0x00, 0x00, 0xff)
        white = Clutter.Color.new(0xff, 0xff, 0xff, 0xff)

        button = Clutter.Actor()

        button_bg = Clutter.Actor()
        button_bg.set_background_color(white)
        button_bg.set_opacity(0xcc)
        button.add_child(button_bg)

        button_text = Clutter.Text.new_full("Sans 10", text, black)
        button.add_child(button_text)

        (width, height) = button_text.get_size()
        button_bg.set_size(width + PADDING * 2, height + PADDING * 2)
        button_bg.set_position(0, 0)
        button_text.set_position(PADDING, PADDING)

        return button

    def add_marker_layer(self):
        black = Clutter.Color.new(0x00, 0x00, 0x00, 0x7f)
        orange = Clutter.Color.new(0xf3, 0x94, 0x07, 0x60)
        layer = Champlain.MarkerLayer()

        self.marker_circle = marker_circle = Champlain.Point()
        marker_circle.set_color(orange)
        marker_circle.set_size(100)
        marker_circle.set_draggable(True)
        marker_circle.set_location(7.528178, -80.563788)
        layer.add_marker(marker_circle)

        self.marker_through = marker_through = Champlain.Point()
        marker_through.set_color(black)
        marker_through.set_size(10)
        lat, lon = marker_circle.get_latitude(), marker_circle.get_longitude()
        x = self.clutter_view.longitude_to_x(lon) + marker_circle.get_size() / 2
        lon = self.clutter_view.x_to_longitude(x)
        marker_through.set_location(lat, lon)
        marker_through.set_draggable(True)
        layer.add_marker(marker_through)

        self.marker_centre = marker_centre = Champlain.Point()
        marker_centre.set_color(black)
        marker_centre.set_size(10)
        lat, lon = marker_circle.get_latitude(), marker_circle.get_longitude()
        marker_centre.set_location(lat, lon)
        marker_centre.set_draggable(True)
        layer.add_marker(marker_centre)

        marker_circle.set_reactive(True)
        marker_through.set_reactive(True)
        marker_circle.connect("drag-motion", self.on_marker_button_release)
        marker_through.connect("drag-motion", self.on_marker_through_button_release)
        marker_centre.connect("drag-motion", self.on_marker_centre_button_release)

        layer.show()
        return layer

    def on_clutter_place_button(self, widget, event):
        # make sure the markers exist
        if self.layer is None:
            self.layer = self.add_marker_layer()
            self.clutter_view.add_layer(self.layer)
        # get the initial marker position
        lat, lon = self.marker_circle.get_latitude(), self.marker_circle.get_longitude()
        y0, x0 = self.clutter_view.latitude_to_y(lat), self.clutter_view.longitude_to_x(lon)
        # get the destination marker position
        if event.source == self.place_button:
            x1, y1 = [i/2 for i in self.clutter_view.get_size()]
        else:
            y1, x1 = event.y, event.x
        lon = self.clutter_view.x_to_longitude(x1)
        lat = self.clutter_view.y_to_latitude(y1)
        # move the circle
        self.marker_circle.set_location(lat, lon)
        # activate the trigger after moving the circle
        self.on_marker_button_release(self.marker_circle, x1-x0, y1-y0, None)
        # remove the button if still there
        if self.place_button is not None:
            self.buttons.remove_child(self.place_button)
            self.place_button = None
        
    def on_view_button_release(self, widget, event):
        if event.button == 3:
            self.on_clutter_place_button(widget, event)

    def on_clutter_ok_button(self, widget, event):
        if self.layer is None:
            return
        self.result = self.get_centre()
        self.response(Gtk.ResponseType.OK)

    def on_clutter_cancel_button(self, widget, event):
        self.response(Gtk.ResponseType.CANCEL)

    def on_animation_completed(self, *args, **kwargs):
        if self.layer is None:
            return
        lat, lon = self.marker_through.get_latitude(), self.marker_through.get_longitude()
        y2, x2 = self.clutter_view.latitude_to_y(lat), self.clutter_view.longitude_to_x(lon)
        lat, lon = self.marker_centre.get_latitude(), self.marker_centre.get_longitude()
        y, x = self.clutter_view.latitude_to_y(lat), self.clutter_view.longitude_to_x(lon)
        angle = math.atan2((y2-y), (x2-x))
        radius = self.marker_circle.get_size() / 2
        dx = math.cos(angle) * radius
        dy = math.sin(angle) * radius
        lat, lon = self.clutter_view.y_to_latitude(y + dy), self.clutter_view.x_to_longitude(x + dx)
        self.marker_through.set_location(lat, lon)

    def on_marker_button_release(self, marker_circle, dx, dy, event, *args, **kwargs):
        for marker in [self.marker_through, self.marker_centre]:
            lat, lon = marker.get_latitude(), marker.get_longitude()
            y, x = self.clutter_view.latitude_to_y(lat), self.clutter_view.longitude_to_x(lon)
            lat, lon = self.clutter_view.y_to_latitude(y + dy), self.clutter_view.x_to_longitude(x + dx)
            marker.set_location(lat, lon)

        # we're done, but the circle is dragged to the top in Z-order.
        # we push it back to the bottom, below all its siblings.
        self.layer.set_child_below_sibling(self.marker_circle)

    def on_marker_centre_button_release(self, marker_centre, dx, dy, event):
        lat, lon = self.marker_centre.get_latitude(), self.marker_centre.get_longitude()
        self.marker_circle.set_location(lat, lon)
        self.on_marker_through_button_release(self.marker_through, dx, dy, event)

    def on_marker_through_button_release(self, marker_through, dx, dy, event):
        lat, lon = marker_through.get_latitude(), marker_through.get_longitude()
        y2, x2 = self.clutter_view.latitude_to_y(lat), self.clutter_view.longitude_to_x(lon)
        lat, lon = self.marker_centre.get_latitude(), self.marker_centre.get_longitude()
        y, x = self.clutter_view.latitude_to_y(lat), self.clutter_view.longitude_to_x(lon)
        radius = math.sqrt((x-x2)**2 + (y-y2)**2)
        self.marker_circle.set_size(radius * 2)

    def on_key_press(self, widget, ev):
        deltax = self.map_widget.get_allocation().width / 4
        deltay = self.map_widget.get_allocation().height / 4
        if ev.keyval == Gdk.KEY_Left:
            self.scroll(-deltax, 0)
        elif ev.keyval == Gdk.KEY_Right:
            self.scroll(deltax, 0)
        elif ev.keyval == Gdk.KEY_Up:
            self.scroll(0, -deltay)
        elif ev.keyval == Gdk.KEY_Down:
            self.scroll(0, deltay)
        elif ev.keyval == Gdk.KEY_plus or ev.keyval == Gdk.KEY_KP_Add:
            self.clutter_view.zoom_in()
        elif ev.keyval == Gdk.KEY_minus or ev.keyval == Gdk.KEY_KP_Subtract:
            self.clutter_view.zoom_out()
        else:
            return False

    def scroll(self, deltax, deltay):
        lat = self.clutter_view.get_center_latitude()
        lon = self.clutter_view.get_center_longitude()

        x = self.clutter_view.longitude_to_x(lon) + deltax
        y = self.clutter_view.latitude_to_y(lat) + deltay

        lon = self.clutter_view.x_to_longitude(x)
        lat = self.clutter_view.y_to_latitude(y)

        self.clutter_view.center_on(lat, lon)

    def get_centre(self):
        from . import utm
        lat1 = self.marker_centre.get_latitude()
        lon1 = self.marker_centre.get_longitude()
        lat2 = self.marker_through.get_latitude()
        lon2 = self.marker_through.get_longitude()
        x1, y1, zone_number, zone_letter = utm.from_latlon(lat1, lon1)
        x2, y2, zone_number, zone_letter = utm.from_latlon(lat2, lon2, zone_number)
        return (lat1, lon1, 2 * math.sqrt((x2-x1)**2 + (y2-y1)**2))

    def set_centre(self, lat, lon, diam):
        from . import utm
        if self.layer is None:
            self.layer = self.add_marker_layer()
            self.clutter_view.add_layer(self.layer)
            self.buttons.remove_child(self.place_button)
            self.place_button = None
        self.marker_centre.set_location(lat, lon)
        self.marker_circle.set_location(lat, lon)
        x, y, zone_number, zone_letter = utm.from_latlon(lat, lon)
        lat2, lon2 = utm.to_latlon(x + diam / 2, y, zone_number, zone_letter)
        self.marker_through.set_location(lat2, lon2)
        self.clutter_view.center_on(lat, lon)
        zoom_level = int(-math.sqrt(2) * math.log(diam) + 26.2)
        zoom_level = max(1, zoom_level)
        zoom_level = min(19, zoom_level)
        self.clutter_view.set_zoom_level(zoom_level)
        self.on_marker_through_button_release(self.marker_through, 0, 0, None)

class Institution(object):
    '''
    Institution is a "live" object. When properties are changed the changes
    are immediately reflected in the database.

    Institution values are stored in the Ghini meta database and not in
    its own table
    '''
    __properties = ('name', 'abbreviation', 'code',
                    'contact', 'technical_contact', 'email',
                    'tel', 'fax', 'address',
                    'geo_latitude', 'geo_longitude', 'geo_diameter',
                    'uuid')

    table = meta.BaubleMeta.__table__

    def __init__(self):
        # initialize properties to None
        list(map(lambda p: setattr(self, p, None), self.__properties))

        for prop in self.__properties:
            db_prop = utils.utf8('inst_' + prop)
            result = self.table.select(self.table.c.name == db_prop).execute()
            row = result.fetchone()
            if row:
                setattr(self, prop, row['value'])
            result.close()

    def write(self):
        for prop in self.__properties:
            value = getattr(self, prop)
            db_prop = utils.utf8('inst_' + prop)
            if value is not None:
                value = utils.utf8(value)
            result = self.table.select(self.table.c.name == db_prop).execute()
            row = result.fetchone()
            result.close()
            # have to check if the property exists first because sqlite doesn't
            # raise an error if you try to update a value that doesn't exist
            # and do an insert and then catching the exception if it exists
            # and then updating the value is too slow
            if not row:
                logger.debug('insert: %s = %s' % (prop, value))
                self.table.insert().execute(name=db_prop, value=value)
            else:
                logger.debug('update: %s = %s' % (prop, value))
                self.table.update(
                    self.table.c.name == db_prop).execute(value=value)


class InstitutionPresenter(editor.GenericEditorPresenter):

    widget_to_field_map = {'inst_name': 'name',
                           'inst_abbr': 'abbreviation',
                           'inst_code': 'code',
                           'inst_contact': 'contact',
                           'inst_tech': 'technical_contact',
                           'inst_email': 'email',
                           'inst_tel': 'tel',
                           'inst_fax': 'fax',
                           'inst_addr_tb': 'address',
                           'inst_geo_latitude': 'geo_latitude',
                           'inst_geo_longitude': 'geo_longitude',
                           'inst_geo_diameter': 'geo_diameter',
                           }

    def __init__(self, model, view):
        self.message_box = None
        self.email_regexp = re.compile(r'.+@.+\..+')
        super().__init__(
            model, view, refresh_view=True)
        self.view.widget_grab_focus('inst_name')
        self.on_non_empty_text_entry_changed('inst_name')
        self.on_email_text_entry_changed('inst_email')
        if not model.uuid:
            import uuid
            model.uuid = str(uuid.uuid4())

    def cleanup(self):
        super().cleanup()
        if self.message_box:
            self.view.remove_box(self.message_box)
            self.message_box = None

    def on_non_empty_text_entry_changed(self, widget, value=None):
        value = super(
                      ).on_non_empty_text_entry_changed(widget, value)
        box = self.message_box
        if value:
            if box:
                self.view.remove_box(box)
                self.message_box = None
        elif not box:
            box = self.view.add_message_box(utils.MESSAGE_BOX_INFO)
            box.message = _('Please specify an institution name for this '
                            'database.')
            box.show()
            self.view.add_box(box)
            self.message_box = box

    def on_email_text_entry_changed(self, widget, value=None):
        value = super(
                      ).on_text_entry_changed(widget, value)
        self.view.widget_set_sensitive(
            'inst_register', self.email_regexp.match(value or ''))

    def get_sentry_handler(self):
        from bauble import prefs
        if prefs.testing:
            from bauble.test import MockLoggingHandler
            return MockLoggingHandler()
        else:
            from raven import Client
            from raven.handlers.logging import SentryHandler
            sentry_client = Client('https://59105d22a4ad49158796088c26bf8e4c:'
                                   '00268114ed47460b94ce2b1b0b2a4a20@'
                                   'app.getsentry.com/45704')
            sentry_client.name = hex(hash(sentry_client.name) + 2**64)[2:-1]
            return SentryHandler(sentry_client)

    def on_select_map_clicked(self, *args, **kwargs):
        map = MapViewer(_('Zoom to garden'), self.view.get_window())
        try:
            map.set_centre(float(self.model.geo_latitude), float(self.model.geo_longitude), float(self.model.geo_diameter))
        except Exception as e:
            pass
        if map.run() == Gtk.ResponseType.OK:
            lat, lon, diam = map.result
            self.view.widget_set_value('inst_geo_latitude', "%0.6f" % lat)
            self.view.widget_set_value('inst_geo_longitude', "%0.6f" % lon)
            self.view.widget_set_value('inst_geo_diameter', "%0.0f" % diam)
        map.destroy()

    def on_inst_register_clicked(self, *args, **kwargs):
        '''send the registration data as sentry info log message
        '''

        # create the handler first
        handler = self.get_sentry_handler()
        handler.setLevel(logging.INFO)

        # the registration logger gets the above handler
        registrations = logging.getLogger('bauble.registrations')
        registrations.setLevel(logging.INFO)
        registrations.addHandler(handler)

        # produce the log record
        registrations.info([(key, getattr(self.model, key))
                            for key in list(self.widget_to_field_map.values())])

        # remove the handler after usage
        registrations.removeHandler(handler)

        # disable button, so user will not send registration twice
        self.view.widget_set_sensitive('inst_register', False)

    def on_inst_addr_tb_changed(self, widget, value=None, attr=None):
        return self.on_textbuffer_changed(widget, value, attr='address')


def start_institution_editor():
    glade_path = os.path.join(paths.lib_dir(),
                              "plugins", "garden", "institution.glade")
    from bauble import prefs
    from bauble.editor import GenericEditorView, MockView
    if prefs.testing:
        view = MockView()
    else:
        view = GenericEditorView(
            glade_path,
            parent=None,
            root_widget_name='inst_dialog')
    view._tooltips = {
        'inst_name': _('The full name of the institution.'),
        'inst_abbr': _('The standard abbreviation of the '
                       'institution.'),
        'inst_code': _('The intitution code should be unique among '
                       'all institions.'),
        'inst_contact': _('The name of the person to contact for '
                          'information related to the institution.'),
        'inst_tech': _('The email address or phone number of the '
                       'person to contact for technical '
                       'information related to the institution.'),
        'inst_email': _('The email address of the institution.'),
        'inst_tel': _('The telephone number of the institution.'),
        'inst_fax': _('The fax number of the institution.'),
        'inst_addr': _('The mailing address of the institition.'),
        'inst_geo_latitude': _('The latitude of the geographic centre of the garden.'),
        'inst_geo_longitude': _('The longitude of the geographic centre of the garden.'),
        'inst_diameter': _('An approximation of the garden size: '
                           'the diameter of the smallest circle completely '
                           'containing the garden location.'),
        }

    o = Institution()
    inst_pres = InstitutionPresenter(o, view)
    response = inst_pres.start()
    if response == Gtk.ResponseType.OK:
        o.write()
        inst_pres.commit_changes()
    else:
        inst_pres.session.rollback()
    inst_pres.session.close()


class InstitutionCommand(pluginmgr.CommandHandler):
    command = ('inst', 'institution')
    view = None

    def __call__(self, cmd, arg):
        InstitutionTool.start()


class InstitutionTool(pluginmgr.Tool):
    label = _('Institution')

    @classmethod
    def start(cls):
        start_institution_editor()
