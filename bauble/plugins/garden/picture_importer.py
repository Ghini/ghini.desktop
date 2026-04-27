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
import logging
import os.path
import re
import threading
from gettext import gettext as _
from typing import Any, Optional

from bauble import db as db
from bauble import pluginmgr as pluginmgr
from bauble import utils as utils
from bauble.editor import GenericEditorPresenter, GenericEditorView
from bauble.gtkinit import GdkPixbuf, GLib, Gtk
from sqlalchemy import select

logger: Any = logging.getLogger(__name__)


accno_re: Any = re.compile(
    r"([12][0-9][0-9][0-9]\.[0-9][0-9][0-9][0-9])(?:\.([0-9]+))?"
)
species_re: Any = re.compile(r"([A-Z][a-z]+(?: [a-z-]*)?)")
picname_re: Any = re.compile(r"([A-Z]+[0-9]+)")
number_re: Any = re.compile(r"([0-9]+)")


def decode_parts(name, acc_format: Optional[Any] = None):
    """return the dictionary of parts in name

    name is matched against the basic concepts in a plant description, like
    its accession or species.  all matching parts are used to construct a
    dictionary, which is then returned.

    accession, defaults to None,
    plant, defaults to 1,
    seq, defaults to 1,
    species, defaults to Zzz

    """

    # look for anything looking like (and remove it), in turn: species name,
    # accession number with optional plant number, original picture name,
    # some other number overruling the original picture name.

    # only scan name part, ignore location
    path, name = os.path.split(name)

    result = {"accession": None, "plant": "1", "seq": "1", "species": "Zzz"}

    if acc_format is None:
        use_accno_re = accno_re
    else:
        exp_str = acc_format.replace(".", r"\.").replace("#", "[0-9]")
        exp_str = rf"({exp_str})(?:\.([0-9]+))?"
        use_accno_re = re.compile(exp_str)
    for key, exp in [
        ("accession", use_accno_re),
        ("species", species_re),
        ("seq", picname_re),
        ("seq", number_re),
    ]:
        match = exp.search(name)
        if match:
            value = match.group(1)
            if not value:
                continue
            if key == "seq":
                value = re.sub(r"([A-Z]+0*)", "", value)
            result[key] = value
            if key == "accession" and match.group(2):
                result["plant"] = match.groups()[1]
            name = name.replace(match.group(0), "")
    if result["accession"] is None:
        return None
    return result


class ListStoreHandler(logging.Handler):
    container: Any

    def __init__(self, container, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.container = container
        GLib.idle_add(utils.none, self.container.clear)

    def emit(self, record) -> None:
        msg = self.format(record)
        stock = {
            11: "gtk-directory",
            12: "gtk-file",
            13: "gtk-new",
        }[record.levelno]
        GLib.idle_add(utils.none, self.container.append, [stock, msg])


def query_session_new(session, cls, **kwargs):
    for i in session.new:
        found = False
        if type(i) == cls:
            found = True
            for k, v in list(kwargs.items()):
                if getattr(i, k) != v:
                    found = False
        if found:
            return i


use_me_col: int = 0
filename_col: int = 1
accno_col: int = 2
binomial_col: int = 3
thumbnail_col: int = 4
iseditable_col: int = 5
orig_accno_col: int = 6
edited_accno_col: int = 7
full_filename_col: int = 8
orig_binomial_col: int = 9
edited_binomial_col: int = 10

from bauble.gtkinit import Gio


def get_first_or_none(session, stmt):
    """Return the first result from a scalars() query, or None if no results."""
    results = list(session.execute(stmt).scalars())
    return results[0] if results else None


class PictureImporterPresenter(GenericEditorPresenter):
    panes: Any
    review_liststore: Any
    running_thread: Any
    keep_running: Any
    should_commit: bool
    pixbufs_to_load: Any
    lock: Any
    widget_to_field_map: Any = {
        "accno_entry": "accno_format",
        "filepath_entry": "filepath",
        "recurse_checkbutton": "recurse",
    }

    def create_actions(self) -> None:
        actions = {
            "cancel": self.on_action_cancel_activate,
            "ok": self.on_action_ok_activate,
            "browse": self.on_action_browse_activate,
            "next": self.on_action_next_activate,
            "prev": self.on_action_prev_activate,
        }

        for action_name, callback in actions.items():
            action = Gio.SimpleAction.new(action_name, None)
            action.connect("activate", callback)
            # Actions are added to the application or window
            self.view.get_window().add_action(action)

    def __init__(self, model, view, **kwargs) -> None:
        kwargs["refresh_view"] = True
        super().__init__(model, view, **kwargs)

        self.panes = [
            self.view.widgets.box_define,
            self.view.widgets.box_review,
            self.view.widgets.box_log,
        ]
        self.review_liststore = self.view.widgets.review_liststore
        self.running_thread = None
        self.keep_running = None
        self.show_visible_pane()
        self.view.widgets.use_tvc.set_sort_column_id(use_me_col)
        self.view.widgets.filename_tvc.set_sort_column_id(filename_col)
        self.view.widgets.accno_tvc.set_sort_column_id(accno_col)
        self.view.widgets.binomial_tvc.set_sort_column_id(binomial_col)
        self.view.widgets.iseditable_tvc.set_sort_column_id(iseditable_col)

        from bauble.plugins.garden import init_location_comboentry

        def on_location_select(location):
            self.model.location = location.code

        init_location_comboentry(
            self, self.view.widgets.location_combobox, on_location_select
        )

        # Gio.SimpleActions setup:
        self.create_actions()

    def show_visible_pane(self) -> None:
        for n, i in enumerate(self.panes):
            i.set_visible(n == self.model.visible_pane)
        self.view.widgets.button_prev.set_sensitive(self.model.visible_pane > 0)
        self.view.widgets.button_next.set_sensitive(
            self.model.visible_pane < len(self.panes) - 1
        )
        self.view.widgets.button_ok.set_sensitive(False)
        self.should_commit = False  # reset inconditionally when changing pane
        if self.running_thread:
            self.keep_running = False
            if self.running_thread.name == "do_import":
                self.lock.release()
            self.running_thread.join()
            self.running_thread = None
        if self.model.visible_pane == 1:
            if self.session.in_transaction():
                self.session.rollback()  # clean up session

    def load_pixbufs(self) -> None:
        # to be run in different thread - or you're blocking the gui
        for fname, path in self.pixbufs_to_load:
            if not self.keep_running:
                return
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(fname)
            try:
                pixbuf = pixbuf.apply_embedded_orientation()
                scale_x = pixbuf.get_width() / 144
                scale_y = pixbuf.get_height() / 144
                scale = max(scale_x, scale_y, 1)
                x = int(pixbuf.get_width() / scale)
                y = int(pixbuf.get_height() / scale)
                pixbuf = pixbuf.scale_simple(x, y, GdkPixbuf.InterpType.BILINEAR)

                def set_thumbnail(store, path, col, value):
                    store[path][col] = value

                GLib.idle_add(
                    set_thumbnail,
                    self.review_liststore,
                    path,
                    thumbnail_col,
                    pixbuf,
                )
            except GLib.GError as e:
                logger.debug(f"picture {fname} caused GLib.GError {e}")
            except Exception as e:
                logger.warning(f"picture {fname} caused Exception {type(e)}:{e}")

    def add_rows(self, arg, dirname, fnames) -> None:
        for name in fnames:
            d = decode_parts(name, self.model.accno_format)
            if d is None:
                continue
            from bauble.plugins.garden.models import Plant

            complete_plant_code = d["accession"] + Plant.get_delimiter() + d["plant"]
            row = [
                True,
                name,
                complete_plant_code,
                d["species"],
                None,
                False,
                complete_plant_code,
                complete_plant_code,
                os.path.join(dirname, name),
                d["species"],
                d["species"],
            ]
            self.pixbufs_to_load.append(
                (os.path.join(dirname, name), (len(self.review_liststore),))
            )
            self.review_liststore.append(row)

    def on_cellrenderertext_edited(
        self, widget, path, new_text, *args, **kwargs
    ) -> None:
        if widget == self.view.widgets.accno_crtext:
            self.review_liststore[path][accno_col] = self.review_liststore[path][
                edited_accno_col
            ] = new_text
        elif widget == self.view.widgets.binomial_crtext:
            self.review_liststore[path][binomial_col] = self.review_liststore[path][
                edited_binomial_col
            ] = new_text

    def on_use_crtoggle_toggled(self, column_widget, path) -> None:
        self.review_liststore[path][use_me_col] = not self.review_liststore[path][
            use_me_col
        ]

    def on_edit_crtoggle_toggled(self, column_widget, path) -> None:
        self.review_liststore[path][iseditable_col] = not self.review_liststore[path][
            iseditable_col
        ]
        if not self.review_liststore[path][iseditable_col]:  # let's restore original
            self.review_liststore[path][accno_col] = self.review_liststore[path][
                orig_accno_col
            ]
            self.review_liststore[path][binomial_col] = self.review_liststore[path][
                orig_binomial_col
            ]
        else:  # otherwise: restore last edit
            self.review_liststore[path][accno_col] = self.review_liststore[path][
                edited_accno_col
            ]
            self.review_liststore[path][binomial_col] = self.review_liststore[path][
                edited_binomial_col
            ]

    def do_import(self) -> None:  # step 2
        session = db.Session()
        handler = ListStoreHandler(self.view.widgets.log_liststore)
        logger.addHandler(handler)
        self.view.widgets.log_treeview.scroll_to_point(0, 0)
        from bauble.plugins.garden.models import Accession, Location, Plant, PlantNote
        from bauble.plugins.plants import Genus, Species

        # make sure selected location exists
        if self.model.location is None:
            self.model.location = "imported"
        location_stmt = Location.query_with_default_order().where(Location.code == self.model.location)
        location = get_first_or_none(session, location_stmt)
        if location:
            logger.log(11, f"location {location} already in database")
        else:
            location = Location(code=self.model.location)
            session.add(location)
            logger.log(13, f"created new location {location}")

        # iterate over liststore content
        for row in self.review_liststore:
            if not self.keep_running:
                break
            if not row[use_me_col]:
                continue
            # get unicode strings from row
            epgn, epsp = str(row[binomial_col] + " sp").split(" ")[:2]
            filename = str(row[filename_col])
            complete_plant_code = str(row[accno_col])
            accession_code, plant_code = complete_plant_code.rsplit(
                Plant.get_delimiter(), 1
            )

            # create or retrieve genus and species
            genus_stmt = Genus.query_with_default_order().where(Genus.epithet == epgn)
            genus = get_first_or_none(session, genus_stmt)
            if not genus:
                raise ValueError(f"Genus {epgn} not found in database")

            species_stmt = Species.query_with_default_order().where(
                Species.genus == genus, Species.epithet == epsp
            )
            species = get_first_or_none(session, species_stmt)
            if species:
                logger.log(11, f"species {epgn} {epsp} already in database")
            else:
                species = query_session_new(session, Species, genus=genus, epithet=epsp)
                if species is None:
                    species = Species(genus=genus, epithet=epsp)
                    session.add(species)
                    logger.log(13, f"created species {epgn} {epsp}")
                else:
                    logger.log(12, f"reusing new species {epgn} {epsp}")

            # create or retrieve accession (needs species)
            accession_stmt = Accession.query_with_default_order().where(Accession.code == accession_code)
            accession = get_first_or_none(session, accession_stmt)
            if accession:
                logger.log(11, f"accession {accession_code} already in database")
            else:
                accession = query_session_new(session, Accession, code=accession_code)
                if accession is None:
                    accession = Accession(
                        species=species, code=accession_code, quantity_recvd=1
                    )
                    session.add(accession)
                    logger.log(
                        13,
                        f"created accession {accession_code} for species {epgn} {epsp}",
                    )
                else:
                    logger.log(12, f"reusing new accession {accession_code}")

            # create or retrieve plant (needs: accession, location)
            plant = get_first_or_none(
                session,
                select(Plant)
                .where(Plant.accession == accession)
                .where(Plant.code == plant_code),
            )

            if plant:
                logger.log(11, f"plant {complete_plant_code} already in database")
            else:
                plant = query_session_new(
                    session, Plant, accession=accession, code=plant_code
                )
                if plant is None:
                    plant = Plant(
                        accession=accession,
                        quantity=1,
                        location=location,
                        code=plant_code,
                    )
                    session.add(plant)
                    logger.log(13, f"created plant {complete_plant_code}")
                else:
                    logger.log(12, f"reusing new plant {complete_plant_code}")

            # copy picture file - possibly renaming it
            utils.copy_picture_with_thumbnail(self.model.filepath, filename)

            # add picture note
            note = get_first_or_none(
                session,
                select(PlantNote)
                .where(PlantNote.plant == plant)
                .where(PlantNote.note == filename)
                .where(PlantNote.category == "<picture>"),
            )

            if note:
                logger.log(
                    11, f"picture {filename} already in plant {complete_plant_code}"
                )
            else:
                note = query_session_new(
                    session,
                    PlantNote,
                    plant=plant,
                    note=filename,
                    category="<picture>",
                )
                if note is None:
                    note = PlantNote(
                        plant=plant,
                        note=filename,
                        category="<picture>",
                        user="initial-import",
                    )
                    session.add(note)
                    logger.log(
                        13,
                        f"picture {filename} added to plant {complete_plant_code}",
                    )
                else:
                    logger.log(
                        12,
                        f"reusing new picture {filename} in plant {complete_plant_code}",
                    )
        logger.removeHandler(handler)
        self.view.widgets.button_ok.set_sensitive(self.keep_running is True)
        self.lock.acquire()
        if self.should_commit:
            if session.in_transaction():
                session.commit()
        else:
            if session.in_transaction():
                if session.in_transaction():
                    session.rollback()
        self.lock.release()

    def on_picture_importer_dialog_response(self, widget, response, **kwargs) -> None:
        self.keep_running = None

    def on_action_prev_activate(self, action, parameter) -> None:
        self.model.visible_pane -= 1
        self.show_visible_pane()

    def on_action_next_activate(self, action, parameter) -> None:
        self.model.visible_pane += 1
        self.show_visible_pane()
        if self.model.visible_pane == 1:  # let user review import
            self.review_liststore.clear()
            self.view.widgets.review_treeview.scroll_to_point(0, 0)
            self.pixbufs_to_load = []
            os.path.walk(self.model.filepath, self.add_rows, None)
            self.keep_running = True
            self.running_thread = threading.Thread(
                target=self.load_pixbufs, name="load_pixbufs"
            )
            self.running_thread.start()
        elif self.model.visible_pane == 2:  # import as specified
            self.keep_running = True
            self.should_commit = False
            self.lock = threading.Lock()
            self.lock.acquire()
            self.running_thread = threading.Thread(
                target=self.do_import, name="do_import"
            )
            self.running_thread.start()

    def show_gtk_stock_icons(self) -> None:
        """this is just some code to show an overview of gtk stock name/image"""
        for i in Gtk.stock_list_ids():
            self.view.widgets.log_liststore.append([i, i])

    def on_action_cancel_activate(self, action, parameter) -> None:
        if self.running_thread:
            self.keep_running = None  # any running thread will return soon
            if self.running_thread.name == "do_import":
                self.lock.release()  # don't stop `do_import` at the lock
            self.running_thread.join()
            self.running_thread = None
        self.view.get_window().emit("response", Gtk.ResponseType.DELETE_EVENT)

    def on_action_ok_activate(self, action, parameter) -> None:
        # OK is set active only in do_import.  if we're here, means that
        # do_import has been running and is now waiting for us at the lock.
        self.should_commit = True
        self.lock.release()
        self.running_thread.join()  # do_import is now committing
        self.running_thread = None
        self.view.get_window().emit("response", Gtk.ResponseType.OK)

    def on_action_browse_activate(self, action, parameter) -> None:
        text = _("Select pictures source directory")
        parent = None
        action_type = Gtk.FileChooserAction.SELECT_FOLDER
        buttons = [
            _("Cancel"),
            Gtk.ResponseType.CANCEL,
            _("Ok"),
            Gtk.ResponseType.ACCEPT,
        ]
        last_folder = self.model.filepath
        target = "filepath_entry"
        self.view.run_file_chooser_dialog(
            text, parent, action_type, buttons, last_folder, target
        )


class PictureImporterTool(pluginmgr.Tool):
    category: Any = _("Import")
    label: Any = _("Picture Collection")
    icon_name: str = "emblem-photos"
    model: Any = type(
        "Model",
        (object,),
        {
            "visible_pane": 0,
            "filepath": "",
            "accno_format": "####.####",
            "recurse": False,
            "location": None,
            "rows": [],
            "log": [],
        },
    )
    import os.path

    from bauble import paths

    glade_path: Any = os.path.join(
        paths.lib_dir(), "plugins", "garden", "picture_importer.glade"
    )

    @classmethod
    def start(cls):
        cls.model.visible_pane = 0
        view = GenericEditorView(
            cls.glade_path,
            parent=None,
            root_widget_name="picture_importer_dialog",
        )
        presenter = PictureImporterPresenter(cls.model, view)
        presenter.start()
        try:
            from bauble import gui

            gui.get_view().update()
        except Exception:
            pass
        return True
