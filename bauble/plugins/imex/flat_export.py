# -*- coding: utf-8 -*-
#
# Copyright 2008, 2009, 2010 Brett Adams
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


from gi.repository import Gtk, Gdk
import os.path
from os.path import isdir, dirname
import os
from sqlalchemy.orm import class_mapper
from sqlalchemy.orm.properties import ColumnProperty
from sqlalchemy.types import Integer, Boolean, Float
import bauble
from bauble import utils
from bauble.search import MapperSearch
from bauble.editor import (
    GenericEditorView, GenericEditorPresenter)
from bauble import paths, pluginmgr
from bauble.querybuilder import SchemaMenu


class FlatFileExporter(GenericEditorPresenter):

    view_accept_buttons = ['cancel_button', 'confirm_button']

    def __init__(self, view=None):
        super().__init__(model=self, view=view, refresh_view=False)

        self.domain_map = MapperSearch.get_domain_classes().copy()
        self.domain = None
        self.mapper = None

        self.view.widgets.domain_ls.clear()
        for key in sorted(self.domain_map.keys()):
            self.view.widgets.domain_ls.append([key])
        self.signal_id = None
        self.on_output_file_changed()

    def get_model_fields(self):
        return {'output_file': self.view.widget_get_value('output_file'),
                'domain': self.view.widget_get_value('domain_combo'),
                'exported_fields': [r[0] for r in self.view.widgets.exported_fields_ls]}

    def set_model_fields(self, output_file=None, domain=None,
                         exported_fields=[],
                         **kwargs):
        if kwargs:
            logger.warning('set_model_fields received extra parameters %s' % kwargs)

        self.view.widget_set_value('output_file', output_file)

        self.view.widget_set_value('domain_combo', domain)
        self.domain = domain

        self.view.widgets.exported_fields_ls.clear()
        for i in exported_fields:
            self.view.widgets.exported_fields_ls.append((i, ))

    def on_open_btn_clicked(self, *args):
        """browse for output file

        """
        previously = self.view.widget_get_value('output_file')
        last_folder, bn = os.path.split(previously)
        self.view.run_file_chooser_dialog(
            _("Choose a file…"), None,
            action=Gtk.FileChooserAction.SAVE,
            buttons=(Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT,
                     Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL),
            last_folder=last_folder, target='output_file')

    def on_output_file_changed(self, *args):
        """set sensitivity of button, based on validity of path

        """
        current_path = self.view.widget_get_value('output_file')
        def iswritable(p):
            pass
        self.view.widget_set_sensitive('confirm_button', not isdir(current_path) and isdir(dirname(current_path)) and os.access(dirname(current_path), os.W_OK))

    def on_schema_menu_activated(self, menuitem, clause_field, prop):
        """add the selected item to the exported fields

        """
        self.view.widgets.exported_fields_ls.append((clause_field, ))

    def on_list_keypress(self, widget, event, *args, **kwargs):
        """handle delete and shift-cursor

        """
        if len(self.view.widgets.exported_fields_ls) == 0:
            return
        path, column = widget.get_cursor()
        store = self.view.widgets.exported_fields_ls
        this = store.get_iter(path)
        other = None
        if event.keyval in (Gdk.KEY_Delete, Gdk.KEY_KP_Delete):
            store.remove(this)
        elif event.keyval in (Gdk.KEY_Down, Gdk.KEY_J) and event.state==Gdk.ModifierType.SHIFT_MASK:
            other = store.iter_next(this)
        elif event.keyval in (Gdk.KEY_Up, Gdk.KEY_K) and event.state==Gdk.ModifierType.SHIFT_MASK:
            other = store.iter_previous(this)
        if other is not None:
            store.swap(this, other)
            return True

    def on_domain_combo_changed(self, *args):
        """
        Change the search domain.  Resets the expression table and
        deletes all the expression rows.
        """
        try:
            index = self.view.widgets.domain_combo.get_active()
        except AttributeError:
            return
        if index == -1:
            return

        self.domain = self.view.widgets.domain_ls[index][0]
        self.view.widgets.exported_fields_ls.clear()
        self.mapper = class_mapper(self.domain_map[self.domain])

        def on_prop_button_clicked(button, event, menu):
            menu.popup(None, None, None, None, event.button, event.time)

        def relation_filter(container, prop):
            if isinstance(prop, ColumnProperty):
                column = prop.columns[0]
                if isinstance(column.type, bauble.btypes.Date):
                    return False
                if container is None:
                    return True
                if not container.uselist:
                    return True
                if not isinstance(column.type, (Integer, Float, Boolean)):
                    return False
            else:
                if container is None:
                    return True
                if prop.mapper == container.parent:
                    return False
            return True

        self.schema_menu = SchemaMenu(self.mapper,
                                      self.on_schema_menu_activated,
                                      relation_filter,
                                      leading_items=['<str>'])
        if self.signal_id is not None:
            self.view.widgets.chooser_btn.disconnect(self.signal_id)
        self.signal_id = self.view.widgets.chooser_btn.connect('button-press-event', on_prop_button_clicked,
                                                               self.schema_menu)

    def do_export(self):
        from bauble import db
        from sqlalchemy.orm.collections import InstrumentedList
        import csv
        filename = self.view.widget_get_value('output_file')
        rows_count = 0
        with open(filename, 'w') as csvfile:
            spamwriter = csv.writer(csvfile, delimiter=',',
                                    quotechar='"', quoting=csv.QUOTE_MINIMAL)
            session = db.Session()
            for obj in session.query(self.mapper).all():
                row = []
                for j in self.view.widgets.exported_fields_ls:
                    # values is the list of the objects from which to read fields
                    values = [obj]
                    single_valued = True
                    *steps, field = j[0].split('.')
                    for step in steps:
                        values = [getattr(value, step) for value in values]
                        if values and isinstance(values[0], InstrumentedList):
                            values = [item for sublist in values for item in sublist]
                            single_valued = False
                    if field == '<str>':
                        value = str(values[0]).replace('\u200b', '')
                    else:
                        values = [getattr(value, field) for value in values]
                        if single_valued:
                            value = values[0]
                        else:
                            if field == 'id':
                                value = len(values)
                            else:
                                value = sum(x or 0 for x in values)
                    row.append(value)
                spamwriter.writerow(row)
                rows_count += 1
            session.rollback()
        return {'count': rows_count,
                'filename': filename}

class FlatFileExportTool(pluginmgr.Tool):
    category = _('Export')
    label = _('Flat file (csv)')
    last_model = {}

    @classmethod
    def start(cls):
        gladefilepath = os.path.join(paths.lib_dir(), "plugins", "imex", "flat_export.glade")
        view = GenericEditorView(
            gladefilepath,
            parent=None,
            root_widget_name='main_dialog')
        qb = FlatFileExporter(view)
        qb.set_model_fields(**cls.last_model)
        response = qb.start()
        if response == Gtk.ResponseType.OK:
            cls.last_model = qb.get_model_fields()
            report = qb.do_export()
            msg = _("Exported file %(filename)s contains %(count)s rows.\n"
                    "\n"
                    "Do you want to open it, or can we stop?") % report
            msg_dialog = utils.create_message_dialog(msg, buttons=Gtk.ButtonsType.NONE)
            msg_dialog.add_buttons(Gtk.STOCK_OPEN, 42,
                                   Gtk.STOCK_STOP, 40)
            msg_dialog.set_default_response(40)
            should_we_open = msg_dialog.run()
            msg_dialog.destroy()
            if should_we_open == 42:
                filename = report['filename']
                try:
                    utils.desktop.open('file://' + filename)
                except OSError:
                    utils.message_dialog(_('Could not open the report with the '
                                           'default program. You can open the '
                                           'file manually at %s') % filename)

        qb.cleanup()
