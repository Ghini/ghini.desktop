# -*- coding: utf-8 -*-
#
# Copyright 2018 Mario Frasca <mario@anche.no>.
# Copyright 2018 Tanager Botanical Garden <tanagertourism@gmail.com>
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
from bauble import meta


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


from threading import Thread
from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.server import SimpleXMLRPCRequestHandler


class RequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/API1',)


class PocketServer(Thread):
    def __init__(self, presenter):
        super().__init__()

        class API:
            def __init__(self, presenter):
                # different thread: we can read from and write to presenter
                # and list stores, but only read graphic widgets.
                self.presenter = presenter
                self.log = presenter.view.widgets.log_ls
                self.clients = presenter.view.widgets.clients_ls
                self.imei_to_user_name = dict((v[1], v[2]) for v in self.clients)

            def verify(self, client_id):
                self.log.append(("verify ›%s‹" % (client_id), ))
                user_name = self.imei_to_user_name.get(client_id, None)
                if user_name is None:
                    return 1
                else:
                    return user_name

            def register(self, client_id, user_name, security_code):
                self.presenter._dirty = True
                self.log.append(("register ›%s‹ ›%s‹" % (client_id, security_code), ))
                if not isinstance(client_id, str) or not isinstance(user_name, str):
                    return 2
                elif security_code != self.presenter.code:
                    return 3
                else:
                    if user_name == self.imei_to_user_name.get(client_id):
                        return 16
                    self.clients.append((len(self.clients), client_id, user_name, ))
                    self.imei_to_user_name[client_id] = user_name
                    return 0

            def get_snapshot(self, client_id):
                self.log.append(("get_snapshot ›%s‹ ›%s‹" % (client_id, self.presenter.pocket_fn), ))
                if client_id not in set((i[1] for i in self.clients)):
                    return 1
                elif not isinstance(client_id, str):
                    return 2
                import base64
                try:
                    with open(self.presenter.pocket_fn, "rb") as pocket_file:
                        encoded_string = base64.b64encode(pocket_file.read())
                        return encoded_string.decode("utf-8") 
                except:
                    return -1

            def put_change(self, client_id, log_lines, baseline):
                user_name = self.imei_to_user_name.get(client_id, None)
                from import_pocket_log import process_line
                self.log.append(("put_change ›%s‹ ›%s‹" % (client_id, len(log_lines)), ))
                db.current_user.override(user_name)
                for line in log_lines:
                    process_line(self.presenter.session, line, baseline)
                db.current_user.override()
                return 0

            def put_picture(self, client_id, name, base64_content):
                self.log.append(("put_picture ›%s‹ ›%s‹" % (client_id, name, ), ))
                if client_id not in set((i[1] for i in self.clients)):
                    return 1
                elif not isinstance(client_id, str) or not isinstance(name, str) or not isinstance(base64_content, str):
                    return 2
                from bauble import prefs
                filename = os.path.join(prefs.prefs[prefs.picture_root_pref], name)
                try:
                    with open(filename, "xb") as picture_file:
                        import base64
                        content = base64.b64decode(base64_content)
                        picture_file.write(content)
                        picture_file.close()
                        return 0
                except FileExistsError:
                    return 4
                except:
                    return -1

        self.ip = presenter.ip_address
        self.port = int(presenter.port)
        self.api = API(presenter)

    def run(self):
        self.server = SimpleXMLRPCServer((self.ip, self.port),
                                         requestHandler=RequestHandler,
                                         logRequests=False)
        self.server.register_introspection_functions()
        self.server.register_instance(self.api)
        self.server.serve_forever()

    def cancel(self):
        self.server.shutdown()
        self.server.server_close()


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
        # prepare fields
        self.port = 44464
        self.ip_address = get_ip()
        self.last_snapshot_date = ''
        self.code = get_code()
        # invoke constructor
        super().__init__(model=self, view=view, refresh_view=True, do_commit=True,
                         committing_results=[-5, -4, -1])  # close, ×, ESC
        # put list_store directly in presenter and grab list from database
        self.clients_ls = self.view.widgets.clients_ls
        # guarantee that self.pocket_fn exists
        import tempfile
        handle, self.pocket_fn = tempfile.mkstemp()
        os.close(handle)
        # other initialization
        self.stop_spinner()
        self.read_clients_list()
        self.on_new_snapshot_button_clicked()

    def cleanup(self):
        super().cleanup()
        self.cancel_threads()
        # remove self.pocket_fn
        os.unlink(self.pocket_fn)

    def read_clients_list(self):
        self.clients_ls.clear()
        query = (self.session.
                 query(meta.BaubleMeta).
                 filter_by(name='pocket-clients'))
        row = query.first()
        if row:
            elems = eval(row.value)
        else:
            elems = {}
        for i, key in enumerate(elems):
            self.clients_ls.append((i, key, elems[key]))

    def commit_changes(self):
        self.write_clients_list()

    def write_clients_list(self):
        query = (self.session.
                 query(meta.BaubleMeta).
                 filter_by(name='pocket-clients'))
        row = query.first()
        if row is None:
            row = meta.BaubleMeta(name='pocket-clients')
            self.session.add(row)
        row.value = str(dict((i[1], i[2]) for i in self.clients_ls))
        self.session.commit()
        
    def on_activity_expander_activate(self, target, *args):
        self.view.widgets.activity_log.set_visible(not target.get_expanded())

    def on_new_snapshot_button_clicked(self, *args):
        text = self.view.widgets.creating_snapshot_label.get_text()
        self.view.widgets.last_snapshot_date_entry.set_text(text)
        self.view.widgets.new_snapshot_button.set_sensitive(False)
        from threading import Thread
        from .exporttopocket import create_pocket, export_to_pocket
        create_pocket(self.pocket_fn)
        thread = Thread(target=export_to_pocket,
                        args=[self.pocket_fn, self.on_export_complete])
        thread.start()
        self.opacity = 0.0
        self.is_exporting = True
        GLib.timeout_add(50, self.flashing_creating)

    def on_export_complete(self):
        now = datetime.datetime.now().isoformat().split('.')[0]
        self.view.widgets.last_snapshot_date_entry.set_text(now)
        self.is_exporting = False
        
    def on_remove_client_button_clicked(self, target, *args):
        selection = self.view.widgets.client_selection
        ls, iter = selection.get_selected()
        if iter is None:
            return
        ls.remove(iter)
        self._dirty = True

    def on_refresh_code_button_clicked(self, target, *args):
        self.code = get_code()
        entry = self.view.widgets.code_entry
        entry.set_text(self.code)
        
    def start_stop_server(self, target, *args):
        if target.get_active():
            self.start_thread(PocketServer(presenter=self))
            self.start_spinner()
        else:
            self.cancel_threads()
            self.stop_spinner()

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

    def flashing_creating(self, *args):
        self.opacity += 0.08
        if self.opacity > 2.0:
            self.opacity -= 2.0
        opacity = abs(1.0 - self.opacity)
        self.view.widgets.creating_snapshot_label.set_opacity(opacity)
        self.view.widgets.last_snapshot_date_entry.set_opacity(1.0 - opacity)
        if not self.is_exporting:
            self.view.widgets.creating_snapshot_label.set_opacity(0)
            self.view.widgets.last_snapshot_date_entry.set_opacity(1)
            self.view.widgets.new_snapshot_button.set_sensitive(True)
            return False
        return True


class PocketServerTool(pluginmgr.Tool):
    item_position = 32
    label = _('Pocket Server…')
    icon_name = "server"

    @classmethod
    def start(cls):
        filename = os.path.join(paths.lib_dir(), "plugins", "garden", 'pocket_server.glade')
        view = GenericEditorView(filename, root_widget_name='pocket_server_dialog')
        c = PocketServerPresenter(view)
        c.start()
