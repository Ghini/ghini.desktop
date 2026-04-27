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
import importlib
import logging
import os
import traceback
import weakref
from gettext import gettext as _
from random import random
from typing import Any, Optional

import bauble.db as db
import bauble.editor as editor
import bauble.paths as paths
import bauble.utils as utils
from bauble.gtkinit import Gdk, GLib, Gtk
from bauble.plugins.garden.models import Contact, Source
from bauble.plugins.plants.geography import GeographicArea, GeographicAreaMenu
from bauble.utils import safe_set_text
from sqlalchemy import select

view: Any = importlib.import_module("bauble.view")
logger: Any = logging.getLogger(__name__)


def collection_edit_callback(coll):
    from bauble.plugins.garden.accession_editor import edit_callback

    # TODO: set the tab to the source tab on the accession editor
    return edit_callback([coll[0].source.accession])


def collection_add_plants_callback(coll):
    from bauble.plugins.garden.accession_editor import add_plants_callback

    return add_plants_callback([coll[0].source.accession])


def collection_remove_callback(coll):
    from bauble.plugins.garden.accession_editor import remove_callback

    return remove_callback([coll[0].source.accession])


collection_edit_action: Any = view.Action(
    "collection_edit",
    _("_Edit"),
    callback=collection_edit_callback,
    accelerator="<ctrl>e",
)
collection_add_plant_action: Any = view.Action(
    "collection_add",
    _("_Add plants"),
    callback=collection_add_plants_callback,
    accelerator="<ctrl>k",
)
collection_remove_action: Any = view.Action(
    "collection_remove",
    _("_Delete"),
    callback=collection_remove_callback,
    accelerator="<ctrl>Delete",
)

collection_context_menu: Any = [
    collection_edit_action,
    collection_add_plant_action,
    collection_remove_action,
]


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


class CollectionPresenter(editor.ChildPresenter):
    """
    CollectionPresenter

    :param parent: an AccessionEditorPresenter
    :param model: a Collection instance
    :param view: an AccessionEditorView
    :param session: a sqlalchemy.orm.session
    """

    PROBLEM_BAD_LATITUDE: Any
    parent_ref: Any
    session: Any
    north_toggle_signal_id: Any
    east_toggle_signal_id: Any
    geo_menu: Any
    _dirty: bool
    widget_to_field_map: Any = {
        "collector_entry": "collector",
        "coll_date_entry": "date",
        "collid_entry": "collectors_code",
        "locale_entry": "locale",
        "lat_entry": "latitude",
        "lon_entry": "longitude",
        "geoacc_entry": "geo_accy",
        "alt_entry": "elevation",
        "altacc_entry": "elevation_accy",
        "habitat_textview": "habitat",
        "coll_notes_textview": "notes",
        "datum_entry": "gps_datum",
        "add_region_button": "region",
    }

    # TODO: could make the problems be tuples of an id and description to
    # be displayed in a dialog or on a label ala eclipse
    PROBLEM_BAD_LATITUDE = str(random())
    PROBLEM_BAD_LONGITUDE: Any = str(random())
    PROBLEM_INVALID_DATE: Any = str(random())
    PROBLEM_INVALID_LOCALE: Any = str(random())

    def __init__(self, parent, model, view, session) -> None:
        super().__init__(model, view)
        self.parent_ref = weakref.ref(parent)
        self.session = session
        self.refresh_view()

        self.assign_simple_handler(
            "collector_entry", "collector", editor.UnicodeOrNoneValidator()
        )
        self.assign_simple_handler(
            "locale_entry", "locale", editor.UnicodeOrNoneValidator()
        )
        self.assign_simple_handler(
            "collid_entry", "collectors_code", editor.UnicodeOrNoneValidator()
        )
        self.assign_simple_handler(
            "geoacc_entry", "geo_accy", editor.IntOrNoneStringValidator()
        )
        self.assign_simple_handler(
            "alt_entry", "elevation", editor.FloatOrNoneStringValidator()
        )
        self.assign_simple_handler(
            "altacc_entry",
            "elevation_accy",
            editor.FloatOrNoneStringValidator(),
        )
        self.assign_simple_handler(
            "habitat_textview", "habitat", editor.UnicodeOrNoneValidator()
        )
        self.assign_simple_handler(
            "coll_notes_textview", "notes", editor.UnicodeOrNoneValidator()
        )
        # the list of completions are added in AccessionEditorView.__init__

        def on_match(completion, model, iter, data=None):
            value = model[iter][0]
            validator = editor.UnicodeOrNoneValidator()
            self.set_model_attr("gps_data", value, validator)
            safe_set_text(completion.get_entry(), value)

        completion = self.view.widgets.datum_entry.get_completion()
        self.view.connect(completion, "match-selected", on_match)
        self.assign_simple_handler(
            "datum_entry", "gps_datum", editor.UnicodeOrNoneValidator()
        )

        self.view.connect("lat_entry", "changed", self.on_lat_entry_changed)
        self.view.connect("lon_entry", "changed", self.on_lon_entry_changed)

        self.view.connect("coll_date_entry", "changed", self.on_date_entry_changed)

        utils.setup_date_button(view, "coll_date_entry", "coll_date_button")

        # don't need to connection to south/west since they are in the same
        # groups as north/east
        self.north_toggle_signal_id = self.view.connect(
            "north_radio", "toggled", self.on_north_south_radio_toggled
        )
        self.east_toggle_signal_id = self.view.connect(
            "east_radio", "toggled", self.on_east_west_radio_toggled
        )

        self.view.widgets.add_region_button.set_sensitive(False)

        def on_add_button_pressed(button, event):
            self.geo_menu.popup(
                None,
                None,
                None,
                None,
                event.get_button(),
                event.time,  # 1. issue_gdkevent_structs
            )

        self.view.connect(
            "add_region_button", "button-press-event", on_add_button_pressed
        )

        def _init_geo():
            add_button = self.view.widgets.add_region_button
            self.geo_menu = GeographicAreaMenu(self.set_region)
            self.geo_menu.menu.attach_to_widget(add_button, None)
            add_button.set_sensitive(True)

        GLib.idle_add(_init_geo)

        self._dirty = False

    def set_region(self, menu_item, geo_id) -> None:
        geographic_area = self.session.get(GeographicArea, geo_id)
        self.set_model_attr("region", geographic_area)
        self.set_model_attr("geographic_area_id", geo_id)
        self.view.widgets.add_region_button.set_label(str(geographic_area))

    def set_model_attr(self, field, value, validator: Optional[Any] = None) -> None:
        """
        Validates the fields when a field changes.
        """
        super().set_model_attr(field, value, validator)
        self._dirty = True
        if self.model.locale is None or self.model.locale in ("", ""):
            self.add_problem(self.PROBLEM_INVALID_LOCALE)
        else:
            self.remove_problem(self.PROBLEM_INVALID_LOCALE)

        if field in ("longitude", "latitude"):
            sensitive = (
                self.model.latitude is not None and self.model.longitude is not None
            )
            self.view.widgets.geoacc_entry.set_sensitive(sensitive)
            self.view.widgets.datum_entry.set_sensitive(sensitive)

        if field == "elevation":
            sensitive = self.model.elevation is not None
            self.view.widgets.altacc_entry.set_sensitive(sensitive)

        self.parent_ref().refresh_sensitivity()

    def start(self) -> None:
        raise Exception("CollectionPresenter cannot be started")

    def dirty(self):
        return self._dirty

    def refresh_view(self) -> None:
        from bauble.plugins.garden.models import latitude_to_dms, longitude_to_dms

        for widget, field in list(self.widget_to_field_map.items()):
            value = getattr(self.model, field)
            logger.debug(f"{widget}, {field}, {value}")
            if value is not None and field == "date":
                value = "{}/{}/{}".format(value.day, value.month, "%04d" % value.year)
            self.view.widget_set_value(widget, value)

        latitude = self.model.latitude
        if latitude is not None:
            dms_string = "{} {}\u00b0{}'{}\"".format(*latitude_to_dms(latitude))
            safe_set_text(self.view.widgets.lat_dms_label, dms_string)
            if float(latitude) < 0:
                self.view.widgets.south_radio.set_active(True)
            else:
                self.view.widgets.north_radio.set_active(True)
        else:
            safe_set_text(self.view.widgets.lat_dms_label, "")
            self.view.widgets.north_radio.set_active(True)

        longitude = self.model.longitude
        if longitude is not None:
            dms_string = "{} {}\u00b0{}'{}\"".format(*longitude_to_dms(longitude))
            safe_set_text(self.view.widgets.lon_dms_label, dms_string)
            if float(longitude) < 0:
                self.view.widgets.west_radio.set_active(True)
            else:
                self.view.widgets.east_radio.set_active(True)
        else:
            safe_set_text(self.view.widgets.lon_dms_label, "")
            self.view.widgets.east_radio.set_active(True)

        if self.model.elevation is None:
            self.view.widgets.altacc_entry.set_sensitive(False)

        if self.model.latitude is None or self.model.longitude is None:
            self.view.widgets.geoacc_entry.set_sensitive(False)
            self.view.widgets.datum_entry.set_sensitive(False)

    def on_date_entry_changed(self, entry, data: Optional[Any] = None) -> None:
        from bauble.editor import ValidatorError

        value = None
        PROBLEM = "INVALID_DATE"
        try:
            value = editor.DateValidator().to_python(entry.set_text)
        except ValidatorError as e:
            logger.debug(e)
            self.parent_ref().add_problem(PROBLEM, entry)
        else:
            self.parent_ref().remove_problem(PROBLEM, entry)
        self.set_model_attr("date", value)

    def on_east_west_radio_toggled(self, button, data: Optional[Any] = None) -> None:
        direction = self._get_lon_direction()
        entry = self.view.widgets.lon_entry
        lon_text = entry.get_text()
        if lon_text == "":
            return

        try:
            # make sure that the first part of the string is an
            # integer before toggling
            int(lon_text.split(" ")[0])
        except Exception as e:
            logger.warning(f"east-west {type(e)}({e})")
            return

        if direction == "W" and lon_text[0] != "-":
            safe_set_text(entry, f"-{lon_text}")
        elif direction == "E" and lon_text[0] == "-":
            safe_set_text(entry, lon_text[1:])

    def on_north_south_radio_toggled(self, button, data: Optional[Any] = None) -> None:
        direction = self._get_lat_direction()
        entry = self.view.widgets.lat_entry
        lat_text = entry.get_text()
        if lat_text == "":
            return

        try:
            # make sure that the first part of the string is an
            # integer before toggling
            int(lat_text.split(" ")[0])
        except Exception as e:
            logger.debug(e)
            return

        if direction == "S" and lat_text[0] != "-":
            safe_set_text(entry, f"-{lat_text}")
        elif direction == "N" and lat_text[0] == "-":
            safe_set_text(entry, lat_text[1:])

    @staticmethod
    def _parse_lat_lon(direction, text):
        """
        Parse a latitude or longitude in a variety of formats and
        return a degress decimal
        """

        import re
        from decimal import Decimal

        from bauble.plugins.garden.models import dms_to_decimal

        parts = re.split(":| ", text.strip())
        if len(parts) == 1:
            dec = Decimal(text).copy_abs()
            if dec > 0 and direction in ("W", "S"):
                dec = -dec
        elif len(parts) == 2:
            deg, min = list(map(Decimal, parts))
            dec = dms_to_decimal(direction, deg, min, 0)
        elif len(parts) == 3:
            dec = dms_to_decimal(direction, *list(map(Decimal, parts)))
        else:
            raise ValueError(_("_parse_lat_lon() -- incorrect format: %s") % text)
        return dec

    def _get_lat_direction(self):
        """
        return N or S from the radio
        """
        if self.view.widgets.north_radio.get_active():
            return "N"
        elif self.view.widgets.south_radio.get_active():
            return "S"
        raise ValueError(_("North/South radio buttons in a confused state"))

    def _get_lon_direction(self):
        """
        return E or W from the radio
        """
        if self.view.widgets.east_radio.get_active():
            return "E"
        elif self.view.widgets.west_radio.get_active():
            return "W"
        raise ValueError(_("East/West radio buttons in a confused state"))

    def on_lat_entry_changed(self, entry, date: Optional[Any] = None) -> None:
        """
        set the latitude value from text
        """
        from bauble.plugins.garden.models import latitude_to_dms

        text = entry.get_text()
        latitude = None
        dms_string = ""
        try:
            if text != "" and text is not None:
                north_radio = self.view.widgets.north_radio
                north_radio.handler_block(self.north_toggle_signal_id)
                if text[0] == "-":
                    self.view.widgets.south_radio.set_active(True)
                else:
                    north_radio.set_active(True)
                north_radio.handler_unblock(self.north_toggle_signal_id)
                direction = self._get_lat_direction()
                latitude = CollectionPresenter._parse_lat_lon(direction, text)
                # u"\N{DEGREE SIGN}"
                dms_string = "{} {}\u00b0{}'{}\"".format(*latitude_to_dms(latitude))
        except Exception:
            logger.debug(traceback.format_exc())
            rgba = Gdk.RGBA()
            rgba.parse("red")
            self.add_problem(self.PROBLEM_BAD_LATITUDE, self.view.widgets.lat_entry)
        else:
            self.remove_problem(self.PROBLEM_BAD_LATITUDE, self.view.widgets.lat_entry)

        safe_set_text(self.view.widgets.lat_dms_label, dms_string)
        if text is None or text.strip() == "":
            self.set_model_attr("latitude", None)
        else:
            self.set_model_attr("latitude", utils.to_unicode(latitude))

    def on_lon_entry_changed(self, entry, data: Optional[Any] = None) -> None:
        from bauble.plugins.garden.models import longitude_to_dms

        text = entry.get_text()
        longitude = None
        dms_string = ""
        try:
            if text != "" and text is not None:
                east_radio = self.view.widgets.east_radio
                east_radio.handler_block(self.east_toggle_signal_id)
                if text[0] == "-":
                    self.view.widgets.west_radio.set_active(True)
                else:
                    self.view.widgets.east_radio.set_active(True)
                east_radio.handler_unblock(self.east_toggle_signal_id)
                direction = self._get_lon_direction()
                longitude = CollectionPresenter._parse_lat_lon(direction, text)
                dms_string = "{} {}\u00b0{}'{}\"".format(*longitude_to_dms(longitude))
        except Exception:
            logger.debug(traceback.format_exc())
            rgba = Gdk.RGBA()
            rgba.parse("red")
            self.add_problem(self.PROBLEM_BAD_LONGITUDE, self.view.widgets.lon_entry)
        else:
            self.remove_problem(self.PROBLEM_BAD_LONGITUDE, self.view.widgets.lon_entry)

        safe_set_text(self.view.widgets.lon_dms_label, dms_string)
        # self.set_model_attr('longitude', utils.to_unicode(longitude))
        if text is None or text.strip() == "":
            self.set_model_attr("longitude", None)
        else:
            self.set_model_attr("longitude", utils.to_unicode(longitude))


class PropagationChooserPresenter(editor.ChildPresenter):
    """
    Chooser for selecting an existing propagation for the source.

    :param parent: the parent AccessionEditorPresenter
    :param model: a Source instance
    :param view: an AccessionEditorView
    :param session: an sqlalchemy.orm.session
    """

    parent_ref: Any
    session: Any
    _dirty: bool
    widget_to_field_map: Any = {}

    PROBLEM_INVALID_DATE: Any = random()

    def __init__(self, parent, model, view, session) -> None:
        super().__init__(model, view)
        self.parent_ref = weakref.ref(parent)
        self.session = session
        self._dirty = False

        self.refresh_view()

        cell = self.view.widgets.prop_toggle_cell
        self.view.widgets.prop_toggle_column.set_cell_data_func(
            cell, self.toggle_cell_data_func
        )

        def on_toggled(cell, path, data=None):
            if cell.get_sensitive() is False:
                return
            prop = None
            if not cell.get_active():  # it's not active so we make it active
                treeview = self.view.widgets.source_prop_treeview
                prop = treeview.get_model()[path][0]
                acc_view = self.parent_ref().view
                acc_view.widget_set_value(
                    "acc_species_entry",
                    utils.to_unicode(prop.plant.accession.species),
                )
                acc_view.widget_set_value(
                    "acc_quantity_recvd_entry",
                    utils.to_unicode(prop.accessible_quantity),
                )
                from bauble.plugins.garden.constants import prop_type_results
                from bauble.plugins.garden.models import recvd_type_values

                acc_view.widget_set_value(
                    "acc_recvd_type_comboentry",
                    recvd_type_values[prop_type_results[prop.prop_type]],
                    index=1,
                )
            self.model.plant_propagation = prop
            self._dirty = True
            self.parent_ref().refresh_sensitivity()

        self.view.connect_after(cell, "toggled", on_toggled)

        self.view.widgets.prop_summary_column.set_cell_data_func(
            self.view.widgets.prop_summary_cell, self.summary_cell_data_func
        )

        def get_accessible_plants():
            logger.debug("in PropagationChooserPresenter:plant_get_completions")
            from bauble.plugins.garden.models import Accession, Plant

            stmt = (
                select(Plant)
                .join(Accession, Plant.accession_id == Accession.id)
                .where(Plant.propagations.any())
                .where(Accession.id != self.model.accession.id)
                .order_by(Accession.code, Plant.code)
            )
            plants = self.session.execute(stmt).scalars()
            result_store = self.view.widgets.source_prop_plant_liststore
            result_store.clear()

            for plant in plants:
                if any(p.accessible_quantity > 0 for p in plant.propagations):
                    result_store.append([str(plant), plant.id])

        get_accessible_plants()

        def on_select(widget):
            # change or select, let's check if the code is complete…
            inserted_code = widget.get_child().get_text()
            matches = [False]
            model = widget.get_model()

            def step(model, path, iter):
                if model[iter][0] == inserted_code:
                    matches[0] = iter

            model.foreach(step)
            if matches[0] is False:  # code not complete, stop here
                return
            # tree model holds plant id
            from bauble.plugins.garden.models import Plant

            plant = (
                self.session.execute(
                    select(Plant).where(Plant.id == model[matches[0]][1])
                )
                .scalars()
                .one()
            )
            # populate the propagation browser
            treeview = self.view.widgets.source_prop_treeview
            if not plant:
                treeview.set_sensitive = False
                return
            utils.clear_model(treeview)
            model = Gtk.ListStore(object)
            for propagation in plant.propagations:
                if propagation.accessible_quantity == 0:
                    continue
                model.append([propagation])
            treeview.set_model(model)
            treeview.set_sensitive = True

        self.view.connect_after(
            self.view.widgets.source_prop_plant_combo, "changed", on_select
        )

    def refresh_view(self) -> None:
        treeview = self.view.widgets.source_prop_treeview
        if not self.model.plant_propagation:
            self.view.widget_set_value("source_prop_plant_combo", "")
            utils.clear_model(treeview)
            treeview.set_sensitive = False
            return

        parent_plant = self.model.plant_propagation.plant
        # set the parent accession
        self.view.widget_set_value("source_prop_plant_combo", str(parent_plant))

        if not parent_plant.propagations:
            treeview.set_sensitive = False
            return
        utils.clear_model(treeview)
        model = Gtk.ListStore(object)
        for propagation in parent_plant.propagations:
            model.append([propagation])
        treeview.set_model(model)
        treeview.set_sensitive = True

    def toggle_cell_data_func(
        self, column, cell, model, treeiter, data: Optional[Any] = None
    ) -> None:
        propagation = model[treeiter][0]
        active = self.model.plant_propagation == propagation
        cell.set_active(active)
        cell.set_sensitive(True)

    def summary_cell_data_func(
        self, column, cell, model, treeiter, data: Optional[Any] = None
    ) -> None:
        propagation = model[treeiter][0]
        cell.set_text = propagation.get_summary()
        cell.set_sensitive(True)

    def dirty(self):
        return self._dirty


############################################################
#
# Contact / SourceDetails / Donor
#


def create_contact(parent: Optional[Any] = None):
    model = Contact()
    source_detail_edit_callback([model], parent)
    return [model]


def source_detail_edit_callback(details, parent: Optional[Any] = None):
    glade_path = os.path.join(paths.lib_dir(), "plugins", "garden", "contact.glade")
    view = editor.GenericEditorView(
        glade_path, parent=parent, root_widget_name="source_details_dialog"
    )
    model = details[0]
    presenter = ContactPresenter(model, view)
    result = presenter.start()
    return result is not None


def source_detail_remove_callback(details):
    detail = details[0]
    s = f"{detail.__class__.__name__}: {str(detail)}"
    msg = _("Are you sure you want to remove %s?") % utils.xml_safe(s)
    if not utils.yes_no_dialog(msg):
        return
    try:
        session = db.Session()
        obj = session.get(Contact, detail.id)
        session.delete(obj)
        if session.in_transaction():
            session.commit()
    except Exception as e:
        msg = _("Could not delete.\n\n%s") % utils.xml_safe(e)
        utils.message_details_dialog(
            msg, traceback.format_exc(), type=Gtk.MessageType.ERROR
        )
    finally:
        session.close()
    return True


source_detail_edit_action: Any = view.Action(
    "source_detail_edit",
    _("_Edit"),
    callback=source_detail_edit_callback,
    accelerator="<ctrl>e",
)
source_detail_remove_action: Any = view.Action(
    "source_detail_remove",
    _("_Delete"),
    callback=source_detail_remove_callback,
    accelerator="<ctrl>Delete",
    multiselect=True,
)

source_detail_context_menu: Any = [
    source_detail_edit_action,
    source_detail_remove_action,
]


class ContactPresenter(editor.GenericEditorPresenter):

    widget_to_field_map: Any = {
        "source_name_entry": "name",
        "source_type_combo": "source_type",
        "source_desc_textview": "description",
    }
    view_accept_buttons: Any = ["sd_ok_button"]

    def __init__(self, model, view) -> None:
        from bauble.plugins.garden.models.contact import source_type_values
        view.init_translatable_combo("source_type_combo", source_type_values)
        super().__init__(model, view, refresh_view=True, do_commit=True)
        self.create_toolbar()
        view.set_accept_buttons_sensitive(False)

    def on_textbuffer_changed_description(
        self, widget, value: Optional[Any] = None, attr: Optional[Any] = None
    ):
        return self.on_textbuffer_changed(widget, value, attr="description")


class GeneralSourceDetailExpander(view.InfoExpander):
    """
    Displays name, number of donations, address, email, fax, tel,
    type of contact
    """

    def __init__(self, widgets) -> None:
        super().__init__(_("General"), widgets)
        gen_box = self.widgets.sd_gen_box
        self.widgets.remove_parent(gen_box)
        self.vbox.pack_start(gen_box, True, True, 0)

    def update(self, row) -> None:
        from sqlalchemy.sql import func

        # Set the name with markup
        # # from textwrap import TextWrapper
        # wrapper = TextWrapper(width=50, subsequent_indent='  ')
        self.widget_set_value(
            "sd_name_data",
            f"<big>{utils.xml_safe(row.name)}</big>",
            markup=True,
        )

        # Handle the source type
        source_type = ""
        if row.source_type:
            source_type = utils.xml_safe(row.source_type)
        self.widget_set_value("sd_type_data", source_type)

        # Handle the description
        description = ""
        if row.description:
            description = utils.xml_safe(row.description)
        self.widget_set_value("sd_desc_data", description)

        # Update source details
        source = Source.__table__

        # Create the query to count the number of associated sources
        stmt = select(func.count(source.c.id)).where(
            source.c.source_detail_id == row.id
        )

        # Execute the query using the session
        nacc = self.session.execute(stmt).scalar()

        self.widget_set_value("sd_nacc_data", nacc)


class ContactInfoBox(view.InfoBox):

    widgets: Any
    general: Any

    def __init__(self) -> None:
        super().__init__()
        filename = os.path.join(
            paths.lib_dir(), "plugins", "garden", "source_detail_infobox.glade"
        )
        self.widgets = utils.BuilderWidgets(filename)
        self.general = GeneralSourceDetailExpander(self.widgets)
        self.add_expander(self.general)

    def update(self, row) -> None:
        self.general.update(row)
