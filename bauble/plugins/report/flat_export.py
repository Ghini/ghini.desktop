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
import logging
import os.path
from gettext import gettext as _
from os.path import dirname, isdir
from typing import Any, Optional

import bauble
from bauble import paths, pluginmgr
from bauble import utils as butils
from bauble.editor import GenericEditorPresenter, GenericEditorView
from bauble.gtkinit import Gdk, Gtk
from bauble.querybuilder import SchemaMenu
from bauble.search import MapperSearch
from sqlalchemy import select
from sqlalchemy.orm import class_mapper
from sqlalchemy.orm.collections import InstrumentedList
from sqlalchemy.orm.properties import ColumnProperty
from sqlalchemy.types import Boolean, Float, Integer


def _resolve_export_value(obj, clause_field):
    """Resolve one Quick CSV field path from an exported object."""
    values = [obj]
    single_valued = True
    *steps, field = clause_field.split(".")
    for step in steps:
        next_values = []
        for value in values:
            if value is None:
                next_values.append(None)
                continue
            related_value = getattr(value, step)
            if isinstance(related_value, InstrumentedList):
                next_values.extend(related_value)
                single_valued = False
            else:
                next_values.append(related_value)
        values = next_values

    if field == "<str>":
        if not values or values[0] is None:
            return ""
        return str(values[0]).replace("\u200b", "")

    values = [None if value is None else getattr(value, field) for value in values]
    if single_valued:
        return values[0] if values else None
    if field == "id":
        return len(values)
    return sum(value or 0 for value in values)


class FlatFileExporter(GenericEditorPresenter):

    domain_map: Any
    domain: Any
    mapper: Any
    results_model: Any
    signal_id: Any
    toggling: bool
    active_toggle: Any
    active_ls: Any
    schema_menu: Any
    view_accept_buttons: Any = ["cancel_button", "confirm_button"]
    logger: Any = logging.getLogger(__name__)

    def __init__(self, view: Optional[Any] = None) -> None:
        super().__init__(model=self, view=view, refresh_view=False)

        self.domain_map = MapperSearch.get_domain_classes().copy()
        self.domain = None
        self.mapper = None
        self.results_model = bauble.gui.get_results_model(quiet=True)

        self.view.widgets.domain_ls.clear()
        for key in sorted(self.domain_map.keys()):
            self.view.widgets.domain_ls.append([key])
        self.view.widgets.searchable_ls.clear()
        for key in ["accession", "location", "plant", "species"]:
            self.view.widgets.searchable_ls.append([key])

        self.signal_id = None
        self.on_output_file_changed()
        self.toggling = False
        self.active_toggle = None
        self.view.widgets.do_collection_button.set_active(True)
        if self.results_model is None:
            self.view.widgets.do_selection_button.set_sensitive(False)

    def get_model_fields(self):
        return {
            "output_file": self.view.widget_get_value("output_file"),
            "domain": self.view.widget_get_value("domain_combo"),
            "exported_fields": [r[0] for r in self.view.widgets.exported_fields_ls],
        }

    def set_model_fields(
        self,
        output_file: Optional[Any] = None,
        domain: Optional[Any] = None,
        exported_fields: Optional[Any] = None,
        **kwargs,
    ) -> None:
        if exported_fields is None:
            exported_fields = []
        if kwargs:
            self.logger.warning(f"set_model_fields received extra parameters {kwargs}")

        self.view.widget_set_value("output_file", output_file)

        self.view.widget_set_value("domain_combo", domain)
        self.domain = domain

        self.view.widgets.exported_fields_ls.clear()
        for i in exported_fields:
            self.view.widgets.exported_fields_ls.append((i,))

    def on_toggle_toggled(self, target) -> None:
        if self.toggling:
            return
        self.toggling = True
        for button in (
            self.view.widgets.do_selection_button,
            self.view.widgets.do_collection_button,
        ):
            button.set_active(button == target)
        if target != self.active_toggle:
            domain = self.view.widget_get_value("domain_combo")
            if target == self.view.widgets.do_selection_button:
                self.active_ls = self.view.widgets.searchable_ls
            else:
                self.active_ls = self.view.widgets.domain_ls
            self.view.widgets.domain_combo.set_model(self.active_ls)
            self.view.widget_set_value("domain_combo", domain)
            self.on_domain_combo_changed()
        self.toggling = False

    def on_open_btn_clicked(self, *args) -> None:
        """browse for output file"""
        previously = self.view.widget_get_value("output_file")
        last_folder, bn = os.path.split(previously)

        # Use the window from self.view
        parent_window = self.view.get_window()

        self.view.run_file_chooser_dialog(
            _("Choose a file…"),
            parent=parent_window,
            action=Gtk.FileChooserAction.SAVE,
            buttons=[
                _("Ok"),
                Gtk.ResponseType.ACCEPT,
                _("Cancel"),
                Gtk.ResponseType.CANCEL,
            ],
            last_folder=last_folder,
            target="output_file",
        )

    def on_output_file_changed(self, *args) -> None:
        """set sensitivity of button, based on validity of path"""
        current_path = self.view.widget_get_value("output_file")

        def iswritable(p):
            pass

        self.view.widget_set_sensitive(
            "confirm_button",
            not isdir(current_path)
            and isdir(dirname(current_path))
            and os.access(dirname(current_path), os.W_OK),
        )

    def on_schema_menu_activated(self, menuitem, clause_field, prop) -> None:
        """add the selected item to the exported fields"""
        self.view.widgets.exported_fields_ls.append((clause_field,))

    def on_list_keypress(self, widget, event, *args, **kwargs):
        """handle delete and shift-cursor"""
        if len(self.view.widgets.exported_fields_ls) == 0:
            return
        path, column = widget.get_cursor()
        store = self.view.widgets.exported_fields_ls
        this = store.get_iter(path)
        other = None
        if event.get_keyval() in (
            Gdk.KEY_Delete,
            Gdk.KEY_KP_Delete,
        ):  # 1. issue_gdkevent_structs
            store.remove(this)
        elif (
            event.get_keyval() in (Gdk.KEY_Down, Gdk.KEY_J)  # 1. issue_gdkevent_structs
            and event.state == Gdk.ModifierType.SHIFT_MASK
        ):
            other = store.iter_next(this)
        elif (
            event.get_keyval() in (Gdk.KEY_Up, Gdk.KEY_K)  # 1. issue_gdkevent_structs
            and event.state == Gdk.ModifierType.SHIFT_MASK
        ):
            other = store.iter_previous(this)
        if other is not None:
            store.swap(this, other)
            return True

    def on_domain_combo_changed(self, *args):
        """react on new domain selection

        when user selects a new domain, reset the expression table and
        deletes all the expression rows.

        when user changes object selection criterium,

        """

        try:
            index = self.view.widgets.domain_combo.get_active()
        except AttributeError:
            index = -1
        if index == -1:
            self.view.widgets.exported_fields_ls.clear()
            if self.signal_id is not None:
                self.view.widgets.chooser_btn.disconnect(self.signal_id)
            return

        new_domain = self.active_ls[index][0]
        if new_domain == self.domain:
            # we were invoked because the combobox changed, not because the
            # selected text changed.  the underlying list changed, so the
            # index changed, but the text remains the same.
            return

        self.domain = new_domain
        self.view.widgets.exported_fields_ls.clear()
        self.mapper = class_mapper(self.domain_map[self.domain])

        def on_prop_button_clicked(button, event, menu):
            menu.popup(
                None, None, None, None, event.get_button(), event.time
            )  # 1. issue_gdkevent_structs

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

        self.schema_menu = SchemaMenu(
            self.mapper,
            self.on_schema_menu_activated,
            relation_filter,
            leading_items=["<str>"],
        )
        if self.signal_id is not None:
            self.view.widgets.chooser_btn.disconnect(self.signal_id)
        self.signal_id = self.view.widgets.chooser_btn.connect(
            "button-press-event", on_prop_button_clicked, self.schema_menu
        )

    def do_export(self):
        import csv

        from bauble import db

        filename = self.view.widget_get_value("output_file")
        rows_count = 0
        with open(filename, "w") as csvfile:
            spamwriter = csv.writer(
                csvfile,
                delimiter=",",
                quotechar='"',
                quoting=csv.QUOTE_MINIMAL,
            )
            session = None
            if self.active_ls == self.view.widgets.searchable_ls:
                model = bauble.gui.get_results_model()
                objs = [row[0] for row in model]
                from . import get_pertinent_objects

                todo = get_pertinent_objects(self.domain_map[self.domain], objs)
            else:
                session = db.Session()
                todo = session.execute(select(self.mapper)).scalars().all()
            try:
                for obj in todo:
                    row = []
                    for j in self.view.widgets.exported_fields_ls:
                        row.append(_resolve_export_value(obj, j[0]))
                    spamwriter.writerow(row)
                    rows_count += 1
            finally:
                if session is not None:
                    if session.in_transaction():
                        session.rollback()
        return {"count": rows_count, "filename": filename}


class FlatFileExportTool(pluginmgr.Tool):
    category: Any = _("Report")
    label: Any = _("Quick CSV")
    icon_name: str = "accessories-text-editor"
    last_model: Any = {}

    @classmethod
    def start(cls) -> None:
        gladefilepath = os.path.join(
            paths.lib_dir(), "plugins", "report", "flat_export.glade"
        )
        view = GenericEditorView(
            gladefilepath, parent=None, root_widget_name="main_dialog"
        )
        qb = FlatFileExporter(view)
        qb.set_model_fields(**cls.last_model)
        response = qb.start()
        if response == Gtk.ResponseType.OK:
            cls.last_model = qb.get_model_fields()
            report = qb.do_export()
            msg = (
                _(
                    "Exported file %(filename)s contains %(count)s rows.\n"
                    "\n"
                    "Do you want to open it, or can we stop?"
                )
                % report
            )
            msg_dialog = butils.create_message_dialog(msg, buttons=Gtk.ButtonsType.NONE)
            msg_dialog.add_buttons(Gtk.STOCK_OPEN, 42, Gtk.STOCK_STOP, 40)
            msg_dialog.set_default_response(40)
            should_we_open = msg_dialog.run()
            msg_dialog.destroy()
            if should_we_open == 42:
                filename = report["filename"]
                try:
                    butils.desktop.open("file://" + filename)
                except OSError:
                    butils.message_dialog(
                        _(
                            "Could not open the report with the "
                            "default program. You can open the "
                            "file manually at %s"
                        )
                        % filename
                    )

        qb.cleanup()
