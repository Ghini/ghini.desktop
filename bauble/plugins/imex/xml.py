#
# Copyright (c) 2005,2006,2007,2008,2009 Brett Adams <brett@belizebotanic.org>
# Copyright (c) 2012-2015 Mario Frasca <mario@anche.no>
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
# XML import/export plugin
#
# Description: handle import and exporting from a simple XML format
#
import logging
import os
import traceback
from gettext import gettext as _
from typing import Any, Optional

import bauble.db as db
import bauble.pluginmgr as pluginmgr
import bauble.task
import bauble.utils as utils
from bauble.gtkinit import Gtk
from sqlalchemy import select

logger: Any = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# TODO: single file or one file per table


def ElementFactory(parent, name, **kwargs):
    try:
        text = kwargs.pop("text")
    except KeyError:
        text = None
    el = etree.SubElement(parent, name, **kwargs)
    try:
        if text is not None:
            el.text = (
                str(text)
                if isinstance(text, str)
                else text.decode("utf8", errors="ignore")
            )
    except Exception as e:
        logger.error(f"Error setting text for element: {e}")
    el.text = ""

    return el


class XMLExporter:

    selected_path_label: Any
    progress_bar: Any
    selected_path: Any

    def __init__(self) -> None:
        pass

    def start(self, path: Optional[Any] = None) -> None:

        dialog = Gtk.Dialog(
            title=_("Ghini - XML Exporter"),
            transient_for=bauble.gui.window,
            flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
        )
        dialog.set_icon_name("document-export")
        dialog.add_buttons(
            _("Cancel"),
            Gtk.ResponseType.REJECT,
            _("OK"),
            Gtk.ResponseType.ACCEPT,
        )

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        dialog.get_content_area().pack_start(box, True, True, 10)

        # Use a FileChooserDialog for file selection
        file_chooser_button = Gtk.Button(label=_("Select Directory"))
        file_chooser_button.connect("clicked", self.on_open_file_chooser_dialog)
        self.selected_path_label = Gtk.Label(label=_("No directory selected"))
        box.pack_start(file_chooser_button, False, False, 0)
        box.pack_start(self.selected_path_label, False, False, 0)

        # Progress Bar
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        self.progress_bar.set_text(_("Ready"))
        box.pack_start(self.progress_bar, False, False, 10)

        # Check button for "Save all data in one file"
        check = Gtk.CheckButton(_("Save all data in one file"))
        check.set_active(True)
        box.pack_start(check, False, False, 0)

        dialog.connect(
            "response",
            self.on_dialog_response,
            check,
        )
        dialog.show()

    def on_open_file_chooser_dialog(self, button) -> None:
        chooser = Gtk.FileChooserDialog(
            title=_("Select a Directory"),
            parent=None,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        chooser.add_buttons(
            _("Cancel"),
            Gtk.ResponseType.CANCEL,
            _("Select"),
            Gtk.ResponseType.OK,
        )
        response = chooser.run()
        if response == Gtk.ResponseType.OK:
            self.selected_path = chooser.get_filename()
            self.selected_path_label.set_text(self.selected_path)
        chooser.destroy()

    def on_dialog_response(self, dialog, response, file_chooser, check) -> None:
        filename = self.selected_path  # Use the selected path from the label
        one_file = check.get_active()  # Dynamically get the state of the checkbox
        if response == Gtk.ResponseType.ACCEPT:
            if not filename or not os.path.isdir(filename):
                # Ensure a valid directory is selected
                utils.message_dialog(_("Please select a valid directory"))
                return
            self.__export_task(filename, one_file)
        dialog.destroy()

    def __export_task(self, path, one_file: bool = True) -> None:
        # Get all tables from metadata
        tables = list(db.metadata.tables.items())
        total_tables = len(tables)
        tableset_el = None

        if one_file:
            # Create a single XML root element for all tables
            tableset_el = etree.Element("tableset")

        for index, (table_name, table) in enumerate(tables):
            # Update progress bar
            self.progress_bar.set_fraction((index + 1) / total_tables)
            self.progress_bar.set_text(
                f"Exporting {table_name}... ({index + 1}/{total_tables})"
            )
            while Gtk.events_pending():
                Gtk.main_iteration()

            if not one_file:
                tableset_el = etree.Element("tableset")

            logger.info(f"exporting {table_name}…")
            table_el = ElementFactory(tableset_el, "table", attrib={"name": table_name})

            # Query the data using SQLAlchemy 2.x's session
            stmt = select(table)

            try:
                results = self.session.execute(stmt).mappings().all()
                columns = list(table.c.keys())
                for row in results:
                    # Create a row element
                    row_el = ElementFactory(table_el, "row")
                    for col in columns:
                        ElementFactory(
                            row_el,
                            "column",
                            attrib={"name": col},
                            text=str(row[col]) if row[col] is not None else "",
                        )
            except ValueError as e:
                utils.message_details_dialog(
                    utils.xml_safe(e),
                    traceback.format_exc(),
                    Gtk.MessageType.ERROR,
                )
                return
            else:
                if one_file:
                    # Write the individual table's XML to a file
                    tree = etree.ElementTree(tableset_el)
                    filename = os.path.join(path, f"{table_name}.xml")
                    tree.write(filename, encoding="utf8", xml_declaration=True)

        # Finalize progress
        self.progress_bar.set_fraction(1.0)
        self.progress_bar.set_text(_("Export Complete"))


class XMLExportCommandHandler(pluginmgr.CommandHandler):

    command: str = "exxml"

    def __call__(self, cmd, arg) -> None:
        logger.debug(f"XMLExportCommandHandler({arg})")
        exporter = XMLExporter()
        logger.debug("starting")
        exporter.start(arg)
        logger.debug("started")


class XMLExportTool(pluginmgr.Tool):
    category: Any = _("Export")
    label: Any = _("XML")
    icon_name: str = "new-xml.png"

    @classmethod
    def start(cls) -> None:
        c = XMLExporter()
        c.start()


class XMLImexPlugin(pluginmgr.Plugin):
    tools: Any = [XMLExportTool]
    commands: Any = [XMLExportCommandHandler]


try:
    import lxml.etree as etree
except ImportError:
    utils.message_dialog(
        "The <i>lxml</i> package is required for the " "XML Import/Exporter plugin"
    )
    raise
