#
# Copyright 2015 Mario Frasca <mario@anche.no>.
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
import json
import logging
import os
from collections.abc import Generator
from gettext import gettext as _
from typing import Any

import bauble.task
from bauble import db, editor, paths, pb_set_fraction, pluginmgr
from bauble.gtkinit import Gtk
from bauble.plugins.garden.models import (
    Accession,
    AccessionNote,
    Location,
    Plant,
    PlantNote,
)
from bauble.plugins.plants import Familia, Genus, Species, SpeciesNote, VernacularName
from sqlalchemy import bindparam, select

logger: Any = logging.getLogger(__name__)


def serializedatetime(obj):
    """Default JSON serializer."""
    import calendar
    import datetime

    if isinstance(obj, (Familia, Genus, Species)):
        return str(obj)
    elif isinstance(obj, datetime.datetime):
        if obj.utcoffset() is not None:
            obj = obj - obj.utcoffset()
    millis = calendar.timegm(obj.timetuple()) * 1000
    try:
        millis += int(obj.microsecond / 1000)
    except AttributeError:
        pass
    return {"__class__": "datetime", "millis": millis}


class JSONExporter(editor.GenericEditorPresenter):
    """Export taxonomy and plants in JSON format.

    the Presenter ((M)VP)"""

    selection_based_on: str
    export_includes: str
    include_private: bool
    filename: str
    last_folder: str = ""
    widget_to_field_map: Any = {
        "sbo_selection": "selection_based_on",
        "sbo_taxa": "selection_based_on",
        "sbo_accessions": "selection_based_on",
        "sbo_plants": "selection_based_on",
        "ei_referred": "export_includes",
        "ei_referring": "export_includes",
        "chkincludeprivate": "include_private",
        "filename": "filename",
    }

    view_accept_buttons: Any = [
        "sed-button-ok",
        "sed-button-cancel",
    ]

    def __init__(self, view) -> None:
        self.selection_based_on = "sbo_selection"
        self.export_includes = "ei_referred"
        self.include_private = True
        self.filename = ""
        super().__init__(model=self, view=view, refresh_view=True)

    from sqlalchemy import bindparam

    def get_objects(self):
        """return the list of objects to be exported

        if "based_on" is "selection", return the top level selection only.

        if "based_on" is something else, return all that is needed to create
        a complete export.
        """
        if self.selection_based_on == "sbo_selection":
            if self.include_private:
                logger.info("exporting selection overrides `include_private`")
            result = self.view.get_selection()
            if result is None:
                return result

            vernacular = speciesnotes = plantnotes = accessionnotes = []

            # Handle species
            species = [j.id for j in result if isinstance(j, Species)]
            if species:
                vernacular = (
                    self.session.execute(
                        select(VernacularName)
                        .where(
                            VernacularName.species_id.in_(
                                bindparam("species_ids", expanding=True)
                            )
                        )
                        .params(species_ids=species)
                    )
                    .scalars()
                    .all()
                )
                speciesnotes = (
                    self.session.execute(
                        select(SpeciesNote)
                        .where(
                            SpeciesNote.species_id.in_(
                                bindparam("species_ids", expanding=True)
                            )
                        )
                        .params(species_ids=species)
                    )
                    .scalars()
                    .all()
                )

            # Handle plants
            plants = [j.id for j in result if isinstance(j, Plant)]
            if plants:
                plantnotes = (
                    self.session.execute(
                        select(PlantNote)
                        .where(
                            PlantNote.plant_id.in_(
                                bindparam("plant_ids", expanding=True)
                            )
                        )
                        .params(plant_ids=plants)
                    )
                    .scalars()
                    .all()
                )

            # Handle accessions
            accessions = [j.id for j in result if isinstance(j, Accession)]
            if accessions:
                accessionnotes = (
                    self.session.execute(
                        select(AccessionNote)
                        .where(
                            AccessionNote.accession_id.in_(
                                bindparam("accession_ids", expanding=True)
                            )
                        )
                        .params(accession_ids=accessions)
                    )
                    .scalars()
                    .all()
                )

            return result + vernacular + plantnotes + accessionnotes + speciesnotes

        # export disregarding selection
        result = []
        if self.selection_based_on == "sbo_plants":
            plant_query = (
                self.session.execute(
                    select(Plant)
                    .order_by(Plant.code)
                    .join(Plant.accession)
                    .order_by(Accession.code)
                )
            ).scalars()

            if self.include_private is False:
                plant_query = plant_query.where(
                    not Accession.private
                )  # `is` does not work

            plants = plant_query.all()

            # Plant notes with bindparam for dynamic expansion
            plantnotes = (
                self.session.execute(
                    select(PlantNote)
                    .where(
                        PlantNote.plant_id.in_(bindparam("plant_ids", expanding=True))
                    )
                    .params(plant_ids=[j.id for j in plants])
                )
                .scalars()
                .all()
            )

            # Locations with bindparam for dynamic expansion
            locations = (
                self.session.execute(
                    select(Location)
                    .where(Location.id.in_(bindparam("location_ids", expanding=True)))
                    .params(location_ids=[j.location_id for j in plants])
                )
                .scalars()
                .all()
            )

            # Accessions with bindparam for dynamic expansion
            accessions = (
                self.session.execute(
                    select(Accession)
                    .where(Accession.id.in_(bindparam("accession_ids", expanding=True)))
                    .params(accession_ids=[j.accession_id for j in plants])
                    .order_by(Accession.code)
                )
                .scalars()
                .all()
            )

            # Accession notes with bindparam for dynamic expansion
            accessionnotes = (
                self.session.execute(
                    select(AccessionNote)
                    .where(
                        AccessionNote.accession_id.in_(
                            bindparam("acc_note_ids", expanding=True)
                        )
                    )
                    .params(acc_note_ids=[j.id for j in accessions])
                )
                .scalars()
                .all()
            )

            # All unique contacts, no bindparam needed as it's a set operation
            contacts = list({a.source.source_detail for a in accessions if a.source})

            # Extend results with non-further-used objects
            result.extend(locations)
            result.extend(plants)
            result.extend(plantnotes)

        elif self.selection_based_on == "sbo_accessions":
            accessions = (
                self.session.execute(select(Accession).order_by(Accession.code))
                .scalars()
                .all()
            )

            if self.include_private is False:
                accessions = [j for j in accessions if j.private is False]

            # Accession notes with bindparam for dynamic expansion
            accessionnotes = (
                self.session.execute(
                    select(AccessionNote)
                    .where(
                        AccessionNote.accession_id.in_(
                            bindparam("acc_note_ids", expanding=True)
                        )
                    )
                    .params(acc_note_ids=[j.id for j in accessions])
                )
                .scalars()
                .all()
            )

            # Unique contacts without repetition
            contacts = list({a.source.source_detail for a in accessions if a.source})
        else:
            contacts = []

        # now the taxonomy, based either on all species or on the ones used
        if self.selection_based_on == "sbo_taxa":
            species = (
                self.session.execute(select(Species).order_by(Species.sp))
                .scalars()
                .all()
            )
        else:
            # Prepend results with accession data
            result = accessions + accessionnotes + result

            # Species query with dynamic expansion for the list of species IDs
            species = (
                self.session.execute(
                    select(Species)
                    .where(Species.id.in_(bindparam("species_ids", expanding=True)))
                    .params(species_ids=[j.species_id for j in accessions])
                    .order_by(Species.sp)
                )
                .scalars()
                .all()
            )

        # Vernacular names with dynamic list expansion
        vernacular = (
            self.session.execute(
                select(VernacularName)
                .where(
                    VernacularName.species_id.in_(
                        bindparam("vernacular_species_ids", expanding=True)
                    )
                )
                .params(vernacular_species_ids=[j.id for j in species])
            )
            .scalars()
            .all()
        )

        # All used genera with dynamic list expansion
        genera = (
            self.session.execute(
                select(Genus)
                .where(Genus.id.in_(bindparam("genus_ids", expanding=True)))
                .params(genus_ids=[j.genus_id for j in species])
                .order_by(Genus.genus)
            )
            .scalars()
            .all()
        )

        # Families with dynamic list expansion
        families = (
            self.session.execute(
                select(Familia)
                .where(Familia.id.in_(bindparam("family_ids", expanding=True)))
                .params(family_ids=[j.family_id for j in genera])
                .order_by(Familia.family)
            )
            .scalars()
            .all()
        )

        # Species notes with dynamic list expansion
        speciesnotes = (
            self.session.execute(
                select(SpeciesNote)
                .where(
                    SpeciesNote.species_id.in_(
                        bindparam("species_note_ids", expanding=True)
                    )
                )
                .params(species_note_ids=[j.id for j in species])
            )
            .scalars()
            .all()
        )

        # prepend the result with the taxonomic information
        result = (
            families + genera + species + speciesnotes + vernacular + contacts + result
        )

        # done, return the result
        return result

    def on_btnbrowse_clicked(self, button) -> None:
        self.view.run_file_chooser_dialog(
            _("Choose a file…"),
            parent=self,
            action=Gtk.FileChooserAction.SAVE,
            buttons=[
                _("Ok"),
                Gtk.ResponseType.ACCEPT,
                _("Cancel"),
                Gtk.ResponseType.CANCEL,
            ],
            last_folder=self.last_folder,
            target="filename",
        )
        filename = self.view.widget_get_value("filename")
        JSONExporter.last_folder, bn = os.path.split(filename)

    def on_btnok_clicked(self, widget) -> None:
        self.run()  # should go in the background really

    def on_btncancel_clicked(self, widget) -> None:
        pass

    def run(self) -> None:
        "perform the export"

        filename = self.filename
        if os.path.exists(filename) and not os.path.isfile(filename):
            raise ValueError(f"{filename} exists and is not a a regular file")

        objects = self.get_objects()
        # if objects is None then export all objects under classes Familia,
        # Genus, Species, Accession, Plant, Location.
        if objects is None:
            s = db.Session()
            objects = s.execute(select(Familia)).scalars().all()
            objects.extend(s.execute(select(Genus)).scalars().all())
            objects.extend(s.execute(select(Species)).scalars().all())
            objects.extend(s.execute(select(VernacularName)).scalars().all())
            objects.extend(s.execute(select(Accession)).scalars().all())
            objects.extend(s.execute(select(Plant)).scalars().all())
            objects.extend(s.execute(select(Location)).scalars().all())

        count = len(objects)
        if count > 3000:
            msg = _(
                "You are exporting %(nplants)s objects to JSON format.  "
                "Exporting this many objects may take several minutes.  "
                "\n\n<i>Would you like to continue?</i>"
            ) % ({"nplants": count})
            if not self.view.run_yes_no_dialog(msg):
                return

        import codecs

        with codecs.open(filename, "wb", "utf-8") as output:
            output.write("[")
            output.write(
                ",\n ".join(
                    [
                        json.dumps(
                            obj.as_dict(),
                            default=serializedatetime,
                            sort_keys=True,
                        )
                        for obj in objects
                    ]
                )
            )
            output.write("]")


class JSONImporter(editor.GenericEditorPresenter):
    """The import process will be queued as a bauble task. there is no callback
    informing whether it is successfully completed or not.

    the Presenter ((M)VP)
    Model (attributes container) is the Presenter itself.
    """

    filename: str
    update: bool
    create: bool
    __error: bool
    __cancel: bool
    __pause: bool
    __error_exc: bool
    widget_to_field_map: Any = {
        "chk_create": "create",
        "chk_update": "update",
        "input_filename": "filename",
    }
    last_folder: str = ""

    view_accept_buttons: Any = [
        "sid-button-ok",
        "sid-button-cancel",
    ]

    def __init__(self, view) -> None:
        self.filename = ""
        self.update = True
        self.create = True
        super().__init__(model=self, view=view, refresh_view=True)
        self.__error = False  # flag to indicate error on import
        self.__cancel = False  # flag to cancel importing
        self.__pause = False  # flag to pause importing
        self.__error_exc = False

    def on_btnbrowse_clicked(self, button) -> None:
        # Use the window from self.view
        parent_window = self.view.get_window()

        self.view.run_file_chooser_dialog(
            _("Choose a file…"),
            parent=parent_window,
            action=Gtk.FileChooserAction.OPEN,
            buttons=[
                _("Ok"),
                Gtk.ResponseType.ACCEPT,
                _("Cancel"),
                Gtk.ResponseType.CANCEL,
            ],
            last_folder=self.last_folder,
            target="input_filename",
        )
        filename = self.view.widget_get_value("input_filename")
        JSONImporter.last_folder, bn = os.path.split(filename)

    def on_btnok_clicked(self, widget) -> None:
        obj = json.load(open(self.filename))
        a = isinstance(obj, list) and obj or [obj]
        bauble.task.queue(self.run(a))

    def on_btncancel_clicked(self, widget) -> None:
        pass

    def run(self, objects) -> Generator[None, None, None]:
        # generator function. will be run as a task.
        session = db.Session()
        n = len(objects)
        for i, obj in enumerate(objects):
            try:
                print(obj)
                db.construct_from_dict(session, obj, self.create, self.update)
                if session.in_transaction():
                    session.commit()
            except Exception as e:
                if session.in_transaction():
                    if session.in_transaction():
                        session.rollback()
                logger.warning(f"could not import {obj} ({type(e).__name__}: {e.args})")
            pb_set_fraction(float(i) / n)
            yield
        if session.in_transaction():
            session.commit()
        try:
            from bauble import gui

            gui.get_view().update()
        except:
            pass


#
# plugin classes
#


class JSONImportTool(pluginmgr.Tool):
    category: Any = (_("Import"), "edit-undo")
    label: Any = _("JSON")
    icon_name: Any = _("new-json.png")

    @classmethod
    def start(cls) -> None:
        """
        Start the JSON importer.  This tool will also reinitialize the
        plugins after importing.
        """
        s = db.Session()
        filename = os.path.join(
            paths.lib_dir(), "plugins", "imex", "select_export.glade"
        )
        presenter = JSONImporter(
            view=editor.GenericEditorView(
                filename, root_widget_name="select_import_dialog"
            )
        )
        presenter.start()  # interact && run
        presenter.cleanup()
        s.close()


class JSONExportTool(pluginmgr.Tool):
    category: Any = (_("Export"), "edit-redo")
    label: Any = _("JSON")
    icon_name: str = "new-json.png"

    @classmethod
    def start(cls) -> None:
        # the presenter uses the view to interact with user then
        # performs the export, if this is the case.
        s = db.Session()
        filename = os.path.join(
            paths.lib_dir(), "plugins", "imex", "select_export.glade"
        )
        presenter = JSONExporter(
            view=editor.GenericEditorView(
                filename, root_widget_name="select_export_dialog"
            )
        )
        presenter.start()  # interact && run
        presenter.cleanup()
        s.close()
