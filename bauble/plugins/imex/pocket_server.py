# -*- coding: utf-8 -*-
#
# Copyright 2018 Mario Frasca <mario@anche.no>.
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
# implements the xmlrcp server for the p2d and d2p streams
#

import logging
logger = logging.getLogger(__name__)

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import GLib

import datetime
import os.path

from bauble import paths
from bauble import pluginmgr
from bauble.editor import (
    GenericEditorView, GenericEditorPresenter)


def get_ip():
    '''get the ip address relative to default route

    see https://stackoverflow.com/a/28950776/78912

    '''
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


def get_code():
    import random
    return ''.join(chr(int(random.random()*24) + 97) for i in range(6))


class PocketServerPresenter(GenericEditorPresenter):
    '''manage the xmlrpc server for pocket communication

    '''

    widget_to_field_map = {
        'last_snapshot_date_entry': 'last_snapshot_date',
        'code_entry': 'code',
        'ip_address_entry': 'ip_address',
        'port_entry': 'port',
        }

    def __init__(self, view):
        self.port = 44464
        self.ip_address = get_ip()
        self.last_snapshot_date = ''
        self.code = get_code()

        super().__init__(model=self, view=view, refresh_view=True)

        # other initialization
        self.stop_spinner()
        
    def on_activity_expander_activate(self, target, *args):
        self.view.widgets.activity_log.set_visible(not target.get_expanded())

    def on_new_snapshot_button_clicked(self, target, *args):
        now = datetime.datetime.now().isoformat().split('.')[0]
        entry = self.view.widgets.last_snapshot_date_entry
        entry.set_text(now)
        target.set_sensitive(False)

    def on_remove_client_button_clicked(self, target, *args):
        selection = self.view.widgets.client_selection
        ls, iter = selection.get_selected()
        if iter is None:
            return
        ls.remove(iter)

    def on_refresh_code_button_clicked(self, target, *args):
        self.code = get_code()
        entry = self.view.widgets.code_entry
        entry.set_text(self.code)
        
    def start_stop_server(self, target, *args):
        if target.get_active():
            self.start_spinner()
            self.view.widgets.close_button.set_sensitive(False)
        else:
            self.stop_spinner()
            self.view.widgets.close_button.set_sensitive(True)

    def start_spinner(self, *args):
        if self.keep_spinning:
            return
        self.angle = 0
        self.keep_spinning = True
        GLib.timeout_add(50, self.rotate)

    def stop_spinner(self, *args):
        self.keep_spinning = False
    
    def rotate(self, *args):
        self.angle -= 15
        self.angle %= 360
        self.view.widgets.spinner.set_angle(self.angle)
        if self.keep_spinning:
            return True
        self.angle = 0
        self.view.widgets.spinner.set_angle(self.angle)


class PocketServerTool(pluginmgr.Tool):
    label = _('Pocket Server…')
    icon_name = "server"

    @classmethod
    def start(cls):
        filename = os.path.join(paths.lib_dir(), "plugins", "imex", 'select_export.glade')
        view = GenericEditorView(filename, root_widget_name='pocket_server_dialog')
        c = PocketServerPresenter(view)
        c.start()
        print(c.ip_address, c.port, c.code, c.last_snapshot_date)
