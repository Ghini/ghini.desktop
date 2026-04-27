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
# accessions module
#

import logging
import os
import traceback
import weakref
from gettext import gettext as _
from random import random
from typing import TYPE_CHECKING, Any, ClassVar, Optional

import bauble
import bauble.editor as editor
import bauble.meta as meta
import bauble.paths as paths
import bauble.prefs as prefs
import bauble.utils as utils
import bauble.view as view
from bauble.db import Session
from bauble.gtkinit import Gtk, Pango
from bauble.plugins.garden.datums import datums

# ← pull in your ORM classes & lookup tables from models/
# you already import several things from models; include this mapping too
from bauble.plugins.garden.models import (
    Accession,
    Verification,
    Voucher,
    accession_type_to_plant_material,
    get_species_instance,
    latitude_to_dms,
    longitude_to_dms,
    prov_type_values,
    recvd_type_values,
    wild_prov_status_values,
)
from bauble.plugins.plants.genus import Genus
from bauble.plugins.plants.species_model import Species, SpeciesSynonym
from bauble.shared import InfoExpander

# NEW imports to satisfy pyflakes
from bauble.utils import check, ilike, safe_set_text
from bauble.view import (
    Action,
    InfoBox,
    MapInfoExpander,
    PropertiesExpander,
    select_in_search_results,
)
from lxml import etree
from sqlalchemy import delete, or_, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import object_session

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def generic_taxon_add_action(
    model, view, presenter, top_presenter, button, taxon_entry
) -> None:
    """user hit click on taxon add button

    new taxon goes into model.species;
    its string representation into taxon_entry.
    """

    from bauble.plugins.plants.species import edit_species

    committed = edit_species(parent_view=view.get_window(), is_dependent_window=True)
    if committed:
        if isinstance(committed, list):
            committed = committed[0]
        logger.debug("new taxon added from within AccessionEditor")
        # add the new taxon to the session and start using it
        presenter.session.add(committed)
        safe_set_text(taxon_entry, f"{committed}")
        presenter.remove_problem(hash(Gtk.Buildable.get_name(taxon_entry)), None)
        model.species = committed
        presenter._dirty = True
        top_presenter.refresh_sensitivity()
    else:
        logger.debug("new taxon not added after request from AccessionEditor")


def edit_callback(accessions):
    e = AccessionEditor(model=accessions[0])
    return e.start()


def add_plants_callback(accessions):

    from bauble.plugins.garden import PlantEditor
    from bauble.plugins.garden.models import Plant

    session = Session()
    acc = session.merge(accessions[0])
    e = PlantEditor(model=Plant(accession=acc))
    # session creates unbound object.  editor decides what to do with it.
    session.close()
    return e.start() is not None


def remove_callback(accessions):
    acc = accessions[0]
    if len(acc.plants) > 0:
        safe = utils.xml_safe
        plants = [str(plant) for plant in acc.plants]
        values = dict(num_plants=len(acc.plants), plant_codes=safe(", ".join(plants)))
        msg = _(
            "%(num_plants)s plants depend on this accession: "
            "<b>%(plant_codes)s</b>\n\n"
        ) % values + _("You cannot remove an accession with plants.")
        utils.message_dialog(msg, type=Gtk.MessageType.WARNING)
        return
    else:
        msg = _(
            "Are you sure you want to remove accession <b>%s</b>?"
        ) % utils.xml_safe(str(acc))
    if not utils.yes_no_dialog(msg):
        return
    try:
        session = Session()
        obj = session.get(Accession, acc.id)
        session.delete(obj)
        if session.in_transaction():
            session.commit()
    except Exception as e:
        msg = _("Could not delete.\n\n%s") % utils.xml_safe(str(e))
        utils.message_details_dialog(
            msg, traceback.format_exc(), type=Gtk.MessageType.ERROR
        )
    finally:
        session.close()
    return True


edit_action: Any = Action(
    "acc_edit", _("_Edit"), callback=edit_callback, accelerator="<ctrl>e"
)
add_plant_action: Any = Action(
    "acc_add",
    _("_Add plants"),
    callback=add_plants_callback,
    accelerator="<ctrl>k",
)
remove_action: Any = Action(
    "acc_remove",
    _("_Delete"),
    callback=remove_callback,
    accelerator="<ctrl>Delete",
)

acc_context_menu: Any = [edit_action, add_plant_action, remove_action]


ver_level_descriptions: ClassVar[dict[str, str]] = {
    0: _("The name of the record has not been checked by any authority."),
    1: _("The name of the record determined by comparison with other " "named plants."),
    2: _(
        "The name of the record determined by a taxonomist or by other "
        "competent persons using herbarium and/or library and/or "
        "documented living material."
    ),
    3: _(
        "The name of the plant determined by taxonomist engaged in "
        "systematic revision of the group."
    ),
    4: _(
        "The record is part of type gathering or propagated from type "
        "material by asexual methods."
    ),
}

herbarium_codes: Any = {}


class AccessionEditorView(editor.GenericEditorView):
    """
    AccessionEditorView provide the view part of the
    model/view/presenter paradigm.  It also acts as the view for any
    child presenter contained within the AccessionEditorPresenter.

    The primary function of the view is setup an parts of the
    interface that don't chage due to user interaction.  Although it
    also provides some utility methods for changing widget states.
    """

    expanders_pref_map: Any = {
        # 'acc_notes_expander': 'editor.accession.notes.expanded',
        # 'acc_source_expander': 'editor.accession.source.expanded'
    }

    _tooltips: Any = {
        "acc_species_entry": _(
            "The species must be selected from the list of completions. "
            "To add a species use the Species editor."
        ),
        "acc_code_entry": _("The accession ID must be a unique code"),
        "acc_id_qual_combo": (
            _("The ID Qualifier\n\n" "Possible values: %s")
            % utils.enum_values_str("accession.id_qual")
        ),
        "acc_id_qual_rank_combo": _(
            "The part of the taxon name that the id " "qualifier refers to."
        ),
        "acc_date_accd_entry": _("The date this species was accessioned."),
        "acc_date_recvd_entry": _("The date this species was received."),
        "acc_recvd_type_comboentry": _("The type of the accessioned material."),
        "acc_quantity_recvd_entry": _(
            "The amount of plant material at the " "time it was accessioned."
        ),
        "intended_loc_comboentry": _(
            "The intended location for plant " "material being accessioned."
        ),
        "intended2_loc_comboentry": _(
            "The intended location for plant " "material being accessioned."
        ),
        "intended_loc_create_plant_checkbutton": _(
            "Immediately create a plant at this location, using all plant material."
        ),
        "acc_prov_combo": (
            _("The origin or source of this accession.\n\n" "Possible values: %s")
            % ", ".join(i[1] for i in prov_type_values)
        ),
        "acc_wild_prov_combo": (
            _(
                "The wild status is used to clarify the "
                "provenance.\n\nPossible values: %s"
            )
            % ", ".join(i[1] for i in wild_prov_status_values)
        ),
        "acc_private_check": _(
            "Indicates whether this accession record " "should be considered private."
        ),
        "acc_cancel_button": _("Cancel your changes."),
        "acc_ok_button": _("Save your changes."),
        "acc_ok_and_add_button": _(
            "Save your changes and add a " "plant to this accession."
        ),
        "acc_next_button": _("Save your changes and add another " "accession."),
        "sources_code_entry": "ITF2 - E7 - Donor's Accession Identifier - donacc",
    }

    def __init__(self, parent: Optional[Any] = None) -> None:
        """ """
        super().__init__(
            os.path.join(paths.lib_dir(), "plugins", "garden", "acc_editor.glade"),
            parent=parent,
        )
        self.attach_completion(
            "acc_species_entry",
            cell_data_func=self.species_cell_data_func,
            match_func=self.species_match_func,
            minimum_key_length=3,
        )
        self.set_accept_buttons_sensitive(False)
        self.restore_state()

        # TODO: at the moment this also sets up some of the view parts
        # of child presenters like the CollectionPresenter, etc.

        # datum completions
        completion = self.attach_completion(
            "datum_entry",
            minimum_key_length=1,
            match_func=self.datum_match,
            text_column=0,
        )
        model = Gtk.ListStore(str)
        for abbr in sorted(datums.keys()):
            # TODO: should create a marked up string with the datum description
            model.append([abbr])
        completion.set_model(model)

        self.init_translatable_combo("acc_prov_combo", prov_type_values)
        self.init_translatable_combo("acc_wild_prov_combo", wild_prov_status_values)
        self.init_translatable_combo("acc_recvd_type_comboentry", recvd_type_values)
        adjustment = self.widgets.source_sw.get_vadjustment()
        adjustment.set_property("value", 0.0)
        self.widgets.source_sw.set_vadjustment(adjustment)

        # set current page so we don't open the last one that was open
        self.widgets.notebook.set_current_page(0)

    def get_window(self):
        return self.widgets.accession_dialog

    def set_accept_buttons_sensitive(self, sensitive) -> None:
        """
        set the sensitivity of all the accept/ok buttons for the editor dialog
        """
        self.widgets.acc_ok_button.set_sensitive(sensitive)
        self.widgets.acc_ok_and_add_button.set_sensitive(sensitive)
        self.widgets.acc_next_button.set_sensitive(sensitive)

    def save_state(self) -> None:
        """
        save the current state of the gui to the preferences
        """
        for expander, pref in list(self.expanders_pref_map.items()):
            prefs.prefs[pref] = self.widgets[expander].get_expanded()

    def restore_state(self) -> None:
        """
        restore the state of the gui from the preferences
        """
        for expander, pref in list(self.expanders_pref_map.items()):
            expanded = prefs.prefs.get(pref, True)
            self.widgets[expander].set_expanded(expanded)

    def start(self):
        return self.get_window().run()

    @staticmethod
    # staticmethod ensures the AccessionEditorView gets garbage collected.
    def datum_match(completion, key, treeiter, data: Optional[Any] = None):
        datum = completion.get_model()[treeiter][0]
        words = datum.split(" ")
        for w in words:
            if w.lower().startswith(key.lower()):
                return True
        return False

    @staticmethod
    # staticmethod ensures the AccessionEditorView gets garbage collected.
    def species_match_func(completion, key, treeiter, data: Optional[Any] = None):
        try:
            species = completion.get_model()[treeiter][0]
            epg, eps = (species.str(remove_zws=True).lower() + " ").split(" ")[:2]
            key_epg, key_eps = (key.replace("\u200b", "").lower() + " ").split(" ")[:2]
            if not epg:
                epg = str(species.genus.epithet).lower()
            if epg.startswith(key_epg) and eps.startswith(key_eps):
                return True
            return False
        except (PendingRollbackError, IntegrityError):
            self.session.rollback()
            return False

    @staticmethod
    # staticmethod ensures the AccessionEditorView gets garbage collected.
    def species_cell_data_func(
        column, renderer, model, treeiter, data: Optional[Any] = None
    ) -> None:
        v = model[treeiter][0]
        renderer.set_property("text", f"{v.str(authors=True)} ({v.genus.family})")


class VoucherPresenter(editor.GenericEditorPresenter):

    parent_ref: Any
    session: Any
    _dirty: bool

    def __init__(self, parent, model, view, session) -> None:
        super().__init__(model, view)
        self.parent_ref = weakref.ref(parent)
        self.session = session
        self._dirty = False
        # self.refresh_view()
        self.view.connect("voucher_add_button", "clicked", self.on_add_clicked)
        self.view.connect("voucher_remove_button", "clicked", self.on_remove_clicked)
        self.view.connect(
            "parent_voucher_add_button", "clicked", self.on_add_clicked, True
        )
        self.view.connect(
            "parent_voucher_remove_button",
            "clicked",
            self.on_remove_clicked,
            True,
        )

        def _voucher_data_func(column, cell, model, treeiter, prop):
            v = model[treeiter][0]
            cell.set_property("text", getattr(v, prop))

        def setup_column(tree, column, cell, prop):
            column = self.view.widgets[column]
            cell = self.view.widgets[cell]
            column.clear_attributes(cell)  # get rid of some warnings
            cell.set_property("editable", True)
            self.view.connect(cell, "edited", self.on_cell_edited, (tree, prop))
            column.set_cell_data_func(cell, _voucher_data_func, prop)

        setup_column(
            "voucher_treeview",
            "voucher_herb_column",
            "voucher_herb_cell",
            "herbarium",
        )
        setup_column(
            "voucher_treeview",
            "voucher_code_column",
            "voucher_code_cell",
            "code",
        )

        setup_column(
            "parent_voucher_treeview",
            "parent_voucher_herb_column",
            "parent_voucher_herb_cell",
            "herbarium",
        )
        setup_column(
            "parent_voucher_treeview",
            "parent_voucher_code_column",
            "parent_voucher_code_cell",
            "code",
        )

        # intialize vouchers treeview
        treeview = self.view.widgets.voucher_treeview
        utils.clear_model(treeview)
        model = Gtk.ListStore(object)
        for voucher in self.model.vouchers:
            if not voucher.parent_material:
                model.append([voucher])
        treeview.set_model(model)

        # initialize parent vouchers treeview
        treeview = self.view.widgets.parent_voucher_treeview
        utils.clear_model(treeview)
        model = Gtk.ListStore(object)
        for voucher in self.model.vouchers:
            if voucher.parent_material:
                model.append([voucher])
        treeview.set_model(model)

    def is_dirty(self):
        return self._dirty

    def on_cell_edited(self, cell, path, new_text, data) -> None:
        treeview, prop = data
        treemodel = self.view.widgets[treeview].get_model()
        voucher = treemodel[path][0]
        if getattr(voucher, prop) == new_text:
            return  # didn't change
        setattr(voucher, prop, utils.to_unicode(new_text))
        self._dirty = True
        self.parent_ref().refresh_sensitivity()

    def on_remove_clicked(self, button, parent: bool = False) -> None:
        if parent:
            treeview = self.view.widgets.parent_voucher_treeview
        else:
            treeview = self.view.widgets.voucher_treeview
        model, treeiter = treeview.get_selection().get_selected()
        if not model or not treeiter:          # ← guard
            return
        voucher = model[treeiter][0]
        voucher.accession = None
        model.remove(treeiter)
        self._dirty = True
        self.parent_ref().refresh_sensitivity()

    def on_add_clicked(self, button, parent: bool = False) -> None:
        """ """
        if parent:
            treeview = self.view.widgets.parent_voucher_treeview
        else:
            treeview = self.view.widgets.voucher_treeview
        voucher = Voucher()
        voucher.accession = self.model
        voucher.parent_material = parent
        model = treeview.get_model()
        treeiter = model.insert(0, [voucher])
        path = model.get_path(treeiter)
        column = treeview.get_column(0)
        treeview.set_cursor(path, column, start_editing=True)


class VerificationPresenter(editor.GenericEditorPresenter):
    """
    VerificationPresenter

    :param parent:
    :param model:
    :param view:
    :param session:
    """

    parent_ref: Any
    session: Any
    _dirty: bool
    PROBLEM_INVALID_DATE: Any = random()

    def __init__(self, parent, model, view, session) -> None:
        super().__init__(model, view)
        self.parent_ref = weakref.ref(parent)
        self.session = session
        self.view.connect("ver_add_button", "clicked", self.on_add_clicked)

        # remove any verification boxes that would have been added to
        # the widget in a previous run
        box = self.view.widgets.verifications_parent_box
        list(map(box.remove, box.get_children()))

        # order by date of the existing verifications
        for ver in model.verifications or []:
            expander = self.add_verification_box(model=ver)
            expander.set_expanded(False)  # all are collapsed to start

        # if no verifications were added then add an empty VerificationBox
        if len(self.view.widgets.verifications_parent_box.get_children()) < 1:
            self.add_verification_box()

        # expand the first verification expander
        #self.view.widgets.verifications_parent_box.get_children()[0].set_expanded(True)
        first_vb = next(self._iter_boxes(), None)
        if first_vb:
            first_vb.set_expanded(True)

        self._dirty = False

    def is_dirty(self):
        return self._dirty

    def refresh_view(self) -> None:
        pass

    def on_add_clicked(self, *args) -> None:
        self.add_verification_box()

    def _iter_boxes(self):
        # Yield VerificationBox instances corresponding to the widgets currently packed
        for child in self.view.widgets.verifications_parent_box.get_children():
            vb = getattr(child, "_vb", None)
            if vb is not None:
                yield vb

    def add_verification_box(self, model: Optional[Any] = None):
        vb = VerificationBox(self, model)
        parent = self.view.widgets.verifications_parent_box
        parent.pack_start(vb.box, False, False, 0)
        parent.reorder_child(vb.box, 0)

        # ← Back-reference so we can recover the VerificationBox from the Gtk widget
        vb.box._vb = vb

        vb.box.show_all()
        return vb

class VerificationBox:
    """
    A widget that manages the verification details for a species,
    allowing the user to input verification data such as date, verifier,
    species, and reference.
    """

    box: Any
    presenter: Any
    model: Any
    widgets: Any
    date_entry: Any
    _sid: Any

    def __init__(self, parent, model) -> None:
        check(not model or isinstance(model, Verification))

        # Create the container box for the layout
        self.box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        self.presenter = weakref.ref(parent)
        self.model = model

        if not self.model:
            self.model = Verification()
            self.model.prev_species = self.presenter().model.species

        # Load the UI from Glade file
        filename = os.path.join(
            paths.lib_dir(), "plugins", "garden", "acc_editor.glade"
        )
        xml = etree.parse(filename)
        el = xml.find(".//object[@id='ver_box']")
        builder = Gtk.Builder()

        s = f"<interface>{etree.tostring(el, encoding='utf-8').decode()}</interface>"
        builder.add_from_string(s)  # Ensure string is properly encoded

        # Create the widgets
        self.widgets = utils.BuilderWidgets(builder)

        # Remove the widgets from the parent and add them to the current box
        ver_box = self.widgets.ver_box
        self.widgets.remove_parent(ver_box)
        self.box.pack_start(ver_box, True, True, 0)

        # Set up the entry for the verifier
        entry = self.widgets.ver_verifier_entry
        if self.model.verifier:
            entry.set_text(self.model.verifier)
        self.presenter().view.connect(
            entry, "changed", self.on_entry_changed, "verifier"
        )

        # Set up the date entry
        self.date_entry = self.widgets.ver_date_entry
        if self.model.date:
            utils.set_widget_value(self.date_entry, self.model.date)
        else:
            self.date_entry.set_text(utils.today_str())
        self.presenter().view.connect(
            self.date_entry, "changed", self.on_date_entry_changed
        )

        # Set up the reference entry
        ref_entry = self.widgets.ver_ref_entry
        if self.model.reference:
            ref_entry.set_text(self.model.reference)
        self.presenter().view.connect(
            ref_entry, "changed", self.on_entry_changed, "reference"
        )

        # Set up the species entries
        self._setup_species_entries()

        # Set up the taxon level combo box
        self._setup_taxon_level_combo()

        # Set up the notes text view
        self._setup_notes_text_view()

        # Set up the remove and copy to taxon general buttons
        self._setup_buttons()

        # Update the label
        self.update_label()

    def _setup_species_entries(self):
        """Set up the species-related entries with auto-completion."""

        def sp_get_completions(text):
            result = (
                self.presenter()
                .session.execute(
                    select(Species)
                    .join(Genus, Species.genus_id == Genus.id)
                    .where(ilike(Genus.genus, f"{text}%"))
                    .where(
                        Species.id != (
                            self.model.species.id if self.model.species else -1
                        )
                    )
                    .order_by(Genus.genus, Species.sp)
                    .limit(100)
                )
                .scalars()
                .all()            # ← concrete list (not ScalarResult)
            )
            return result

        def sp_cell_data_func(col, cell, model, treeiter, data=None):
            v = model[treeiter][0]
            cell.set_property("text", f"{v.str(authors=True)} ({v.genus.family})")

        ver_prev_taxon_entry = self.widgets.ver_prev_taxon_entry

        def on_prevsp_select(value):
            self.set_model_attr("prev_species", value)

        self.presenter().view.attach_completion(ver_prev_taxon_entry, sp_cell_data_func)
        if self.model.prev_species:
            ver_prev_taxon_entry.set_text(f"{self.model.prev_species}")
        self.presenter().assign_completions_handler(
            ver_prev_taxon_entry, sp_get_completions, on_prevsp_select
        )

        ver_new_taxon_entry = self.widgets.ver_new_taxon_entry

        def on_sp_select(value):
            self.set_model_attr("species", value)

        self.presenter().view.attach_completion(ver_new_taxon_entry, sp_cell_data_func)
        if self.model.species:
            ver_new_taxon_entry.set_text(utils.to_unicode(self.model.species))
        self.presenter().assign_completions_handler(
            ver_new_taxon_entry, sp_get_completions, on_sp_select
        )

    def _setup_taxon_level_combo(self) -> None:
        """Set up the taxon level combo box."""
        combo = self.widgets.ver_level_combo
        renderer = Gtk.CellRendererText()
        renderer.set_property("wrap-mode", Pango.WrapMode.WORD)
        renderer.set_property("wrap-width", 400)
        combo.pack_start(renderer, True)

        def cell_data_func(col, cell, model, treeiter, data=None):
            level = model[treeiter][0]
            descr = model[treeiter][1]
            cell.set_property("markup", f"<b>{level}</b>  :  {descr}")

        combo.set_cell_data_func(renderer, cell_data_func)
        model = Gtk.ListStore(int, str)
        for level, descr in list(ver_level_descriptions.items()):
            model.append([level, descr])
        combo.set_model(model)
        if self.model.level:
            utils.set_widget_value(combo, self.model.level)
        self.presenter().view.connect(combo, "changed", self.on_level_combo_changed)

    def _setup_notes_text_view(self) -> None:
        """Set up the notes text view."""
        textview = self.widgets.ver_notes_textview
        textview.set_border_width(1)
        buff = Gtk.TextBuffer()
        if self.model.notes:
            buff.set_text(self.model.notes)
        textview.set_buffer(buff)
        self.presenter().view.connect(buff, "changed", self.on_entry_changed, "notes")

    def _setup_buttons(self) -> None:
        """Set up the remove and copy to taxon general buttons."""
        button = self.widgets.ver_remove_button
        self._sid_remove = self.presenter().view.connect(
            button, "clicked", self.on_remove_button_clicked
        )

        button = self.widgets.ver_copy_to_taxon_general
        self._sid_copy = self.presenter().view.connect(
            button, "clicked", self.on_copy_to_taxon_general_clicked
        )

    def on_entry_changed(self, entry, attr) -> None:
        """Update the model attribute when an entry is changed."""
        text = entry.get_text()
        if not text:
            self.set_model_attr(attr, None)
        else:
            self.set_model_attr(attr, utils.to_unicode(text))

    def on_level_combo_changed(self, combo, *args) -> None:
        """Update the level attribute when the combo box is changed."""
        i = combo.get_active_iter()
        if not i:              # ← guard
            self.set_model_attr("level", None)
            return
        level = combo.get_model()[i][0]
        self.set_model_attr("level", level)

    def on_date_entry_changed(self, entry, data: Optional[Any] = None) -> None:
        """Handle date entry change."""
        from bauble.editor import ValidatorError

        value = None
        PROBLEM = "INVALID_DATE"
        try:
            value = editor.DateValidator().to_python(entry.get_text())
        except ValidatorError as e:
            logger.debug(e)
            self.presenter().add_problem(PROBLEM, entry)
        else:
            self.presenter().remove_problem(PROBLEM, entry)
        self.set_model_attr("date", value)

    def on_copy_to_taxon_general_clicked(self, button) -> None:
        """Copy the selected verification species to the general Accession tab."""
        if self.model.species is None:
            return

        # Confirm with the user
        msg = _("Are you sure you want to copy this verification to the general taxon?")
        if not utils.yes_no_dialog(msg):
            return

        # Copy verification species to the General tab's species entry
        parent_presenter = self.presenter()
        if parent_presenter and parent_presenter.parent_ref():
            # same target widget as in the old code
            parent_presenter.parent_ref().view.widgets.acc_species_entry.set_text(
                utils.to_unicode(self.model.species)
            )
            parent_presenter._dirty = True
            parent_presenter.parent_ref().refresh_sensitivity()

    def on_remove_button_clicked(self, button) -> None:
        """Handle the remove button click."""
        parent = self.box.get_parent()
        msg = _("Are you sure you want to remove this verification?")
        if not utils.yes_no_dialog(msg):
            return
        if parent:
            parent.remove(self.box)

        # Disconnect the signal to allow garbage collection
        button.disconnect(self._sid_remove)
        button.disconnect(self._sid_copy)

        # Remove verification from accession
        if self.model.accession:
            self.model.accession.verifications.remove(self.model)
        self.presenter()._dirty = True
        self.presenter().parent_ref().refresh_sensitivity()

    def set_model_attr(self, attr, value) -> None:
        """Set the model attribute and handle side effects."""
        setattr(self.model, attr, value)
        if attr != "date" and not self.model.date:
            tmp = self.date_entry.get_text()
            self.date_entry.set_text("")
            self.date_entry.set_text(tmp)
        if not self.model.accession:
            self.presenter().model.verifications.append(self.model)
        self.presenter()._dirty = True
        self.update_label()
        self.presenter().parent_ref().refresh_sensitivity()

    def update_label(self) -> None:
        """Update the label that displays verification information."""
        parts = []
        if self.model.date:
            parts.append("<b>%(date)s</b> : ")
        if self.model.species:
            parts.append(_("verified as %(species)s "))
        if self.model.verifier:
            parts.append(_("by %(verifier)s"))
        label = " ".join(parts) % dict(
            date=self.model.date,
            species=self.model.species,
            verifier=self.model.verifier,
        )
        self.widgets.ver_expander_label.set_property("use-markup", True)
        self.widgets.ver_expander_label.set_property("label", label)

    def set_expanded(self, expanded) -> None:
        """
        Set the expanded state of the expander widget.
        """
        self.widgets.ver_expander.set_expanded(expanded)

    def on_taxon_add_button_clicked(self, button, taxon_entry) -> None:
        """
        This method is called when the user clicks the button to add a taxon.
        It allows the user to create a new verification associated with a new taxon.
        """
        generic_taxon_add_action(
            self.model,
            self.presenter().view,
            self.presenter(),
            self.presenter().parent_ref(),
            button,
            taxon_entry,
        )


class SourcePresenter(editor.GenericEditorPresenter):
    """
    SourcePresenter
    :param parent:
    :param model:
    :param view:
    :param session:
    """

    parent_ref: Any
    session: Any
    _dirty: bool
    source: Any
    collection: Any
    propagation: Any
    source_prop_presenter: Any
    prop_chooser_presenter: Any
    collection_presenter: Any
    garden_prop_str: Any = _("Garden Propagation")

    def __init__(self, parent, model, view, session) -> None:
        from bauble.plugins.garden.models import (
            Collection,
            Contact,
            Propagation,
            Source,
        )
        from bauble.plugins.garden.propagation_editor import SourcePropagationPresenter
        from bauble.plugins.garden.source import (
            CollectionPresenter,
            PropagationChooserPresenter,
        )

        super().__init__(model, view)
        self.parent_ref = weakref.ref(parent)
        self.session = session
        self._dirty = False

        self.view.connect(
            "new_source_button", "clicked", self.on_new_source_button_clicked
        )

        self.view.widgets.source_garden_prop_box.set_visible(False)
        self.view.widgets.source_sw.set_visible(False)
        self.view.widgets.source_none_label.set_visible(True)

        # populate the source combo
        def on_select(source):
            if not source:
                self.model.source = None
            elif isinstance(source, Contact):
                self.model.source = self.source
                self.model.source.source_detail = source
            elif source == self.garden_prop_str:
                self.model.source = self.source
                self.model.source.source_detail = None
            else:
                logger.warning(f"unknown source: {source}")
            # self.model.source = self.source
            # self.model.source.source_detail = source_detail

        self.init_source_comboentry(on_select)

        if self.model.source:
            self.source = self.model.source
            self.view.widgets.sources_code_entry.set_text(self.source.sources_code or "")
        else:
            self.source = Source()
            # self.model.source will be reset the None if the source
            # combo value is None in commit_changes()
            self.model.source = self.source
            self.view.widgets.sources_code_entry.set_text("")

        if self.source.collection:
            self.collection = self.source.collection
            enabled = True
        else:
            self.collection = Collection()
            self.session.add(self.collection)
            enabled = False
        self.view.widgets.source_coll_add_button.set_sensitive(not enabled)
        self.view.widgets.source_coll_remove_button.set_sensitive(enabled)
        self.view.widgets.source_coll_expander.set_expanded(enabled)
        self.view.widgets.source_coll_expander.set_sensitive(enabled)

        if self.source.propagation:
            self.propagation = self.source.propagation
            enabled = True
        else:
            self.propagation = Propagation()
            self.session.add(self.propagation)
            enabled = False
        self.view.widgets.source_prop_add_button.set_sensitive(not enabled)
        self.view.widgets.source_prop_remove_button.set_sensitive(enabled)
        self.view.widgets.source_prop_expander.set_expanded(enabled)
        self.view.widgets.source_prop_expander.set_sensitive(enabled)

        # TODO: all the sub presenters here take the
        # AccessionEditorPresenter as their parent though their real
        # parent is this SourcePresenter....having the
        # AccessionEditorPresenter is easier since what we really need
        # access to is refresh_sensitivity() and possible
        # set_model_attr() but having the SourcePresenter would be
        # more "correct"

        # presenter that allows us to create a new Propagation that is
        # specific to this Source and not attached to any Plant
        self.source_prop_presenter = SourcePropagationPresenter(
            self.parent_ref(), self.propagation, view, session
        )
        self.source_prop_presenter.register_clipboard()

        # presenter that allows us to select an existing propagation
        self.prop_chooser_presenter = PropagationChooserPresenter(
            self.parent_ref(), self.source, view, session
        )

        # collection data
        self.collection_presenter = CollectionPresenter(
            self.parent_ref(), self.collection, view, session
        )
        self.collection_presenter.register_clipboard()

        def on_changed(entry, *args):
            text = entry.get_text()
            if text.strip():
                self.source.sources_code = utils.to_unicode(text)
            else:
                self.source.sources_code = None
            self._dirty = True
            self.refresh_sensitivity()

        self.view.connect("sources_code_entry", "changed", on_changed)

        self.view.connect(
            "source_coll_add_button",
            "clicked",
            self.on_coll_add_button_clicked,
        )
        self.view.connect(
            "source_coll_remove_button",
            "clicked",
            self.on_coll_remove_button_clicked,
        )
        self.view.connect(
            "source_prop_add_button",
            "clicked",
            self.on_prop_add_button_clicked,
        )
        self.view.connect(
            "source_prop_remove_button",
            "clicked",
            self.on_prop_remove_button_clicked,
        )

    def all_problems(self):
        """
        Return a union of all the problems from this presenter and
        child presenters
        """
        return (
            self.problems
            | self.collection_presenter.problems
            | self.prop_chooser_presenter.problems
            | self.source_prop_presenter.problems
        )

    def cleanup(self) -> None:
        super().cleanup()
        self.collection_presenter.cleanup()
        self.prop_chooser_presenter.cleanup()
        self.source_prop_presenter.cleanup()

    def start(self) -> None:
        active = None
        if self.model.source:
            if self.model.source.source_detail:
                active = self.model.source.source_detail
            elif self.model.source.plant_propagation:
                active = self.garden_prop_str
        self.populate_source_combo(active)

    def is_dirty(self):
        return (
            self._dirty
            or self.source_prop_presenter.is_dirty()
            or self.prop_chooser_presenter.is_dirty()
            or self.collection_presenter.is_dirty()
        )

    def refresh_sensitivity(self) -> None:
        logger.warning(f"refresh_sensitivity: {str(self.problems)}")
        self.parent_ref().refresh_sensitivity()

    def on_coll_add_button_clicked(self, *args) -> None:
        self.model.source.collection = self.collection
        self.view.widgets.source_coll_expander.set_expanded( True)
        self.view.widgets.source_coll_expander.set_sensitive(True)
        self.view.widgets.source_coll_add_button.set_sensitive(False)
        self.view.widgets.source_coll_remove_button.set_sensitive(True)
        self._dirty = True
        self.refresh_sensitivity()

    def on_coll_remove_button_clicked(self, *args) -> None:
        self.model.source.collection = None
        self.view.widgets.source_coll_expander.set_expanded(False)
        self.view.widgets.source_coll_expander.set_sensitive(False)
        self.view.widgets.source_coll_add_button.set_sensitive(True)
        self.view.widgets.source_coll_remove_button.set_sensitive(False)
        self._dirty = True
        self.refresh_sensitivity()

    def on_prop_add_button_clicked(self, *args) -> None:
        self.model.source.propagation = self.propagation
        self.view.widgets.source_prop_expander.set_expanded(True)
        self.view.widgets.source_prop_expander.set_sensitive(True)
        self.view.widgets.source_prop_add_button.set_sensitive(False)
        self.view.widgets.source_prop_remove_button.set_sensitive(True)
        self._dirty = True
        self.refresh_sensitivity()

    def on_prop_remove_button_clicked(self, *args) -> None:
        self.model.source.propagation = None
        self.view.widgets.source_prop_expander.set_expanded(False)
        self.view.widgets.source_prop_expander.set_sensitive(False)
        self.view.widgets.source_prop_add_button.set_sensitive(True)
        self.view.widgets.source_prop_remove_button.set_sensitive(False)
        self._dirty = True
        self.refresh_sensitivity()

    def on_new_source_button_clicked(self, *args) -> None:
        """
        Opens a new ContactEditor when clicked and repopulates the
        source combo if a new Contact is created.
        """
        from bauble.plugins.garden.source import create_contact

        committed = create_contact(parent=self.view.get_window())
        new_detail = None
        if committed:
            new_detail = committed[0]
            self.session.add(new_detail)
            self.populate_source_combo(new_detail)

    def populate_source_combo(self, active: Optional[Any] = None) -> None:
        """
        If active=None then set whatever was previously active before
        repopulating the combo.
        """
        from bauble.plugins.garden.source import Contact

        combo = self.view.widgets.acc_source_comboentry
        if not active:
            treeiter = combo.get_active_iter()
            if treeiter:
                active = combo.get_model()[treeiter][0]
        combo.set_model(None)
        model = Gtk.ListStore(object)
        none_iter = model.append([""])
        model.append([self.garden_prop_str])
        list(
            [model.append([x]) for x in self.session.execute(Contact.query_with_default_order()).scalars()]
        )
        combo.set_model(model)
        combo.get_child().get_completion().set_model(model)

        combo._populate = True
        if active:
            results = utils.search_tree_model(model, active)
            if results:
                combo.set_active_iter(results[0])
        else:
            combo.set_active_iter(none_iter)
        combo._populate = False

    def init_source_comboentry(self, on_select):
        """
        A comboentry that allows the location to be entered requires
        more custom setup than view.attach_completion and
        self.assign_simple_handler can provides.  This method allows us to
        have completions on the location entry based on the location code,
        location name and location string as well as selecting a location
        from a combo drop down.

        :param on_select: called when an item is selected
        """
        from bauble.plugins.garden.source import Contact

        PROBLEM = "unknown_source"

        def cell_data_func(col, cell, model, treeiter, data=None):
            cell.set_property("text", utils.to_unicode(model[treeiter][0]))

        combo = self.view.widgets.acc_source_comboentry
        combo.clear()
        cell = Gtk.CellRendererText()
        combo.pack_start(cell, True)
        combo.set_cell_data_func(cell, cell_data_func)

        completion = Gtk.EntryCompletion()
        cell = Gtk.CellRendererText()  # set up the completion renderer
        completion.pack_start(cell, True)
        completion.set_cell_data_func(cell, cell_data_func)

        def match_func(completion, key, treeiter, data=None):
            model = completion.get_model()
            value = model[treeiter][0]
            # allows completions of source details by their ID
            if utils.to_unicode(value).lower().startswith(key.lower()) or (
                isinstance(value, Contact) and str(value.id).startswith(key)
            ):
                return True
            return False

        completion.set_match_func(match_func)

        entry = combo.get_child()
        entry.set_completion(completion)

        def update_visible():
            widget_visibility = dict(
                source_sw=False,
                source_garden_prop_box=False,
                source_none_label=False,
            )
            if entry.get_text() == self.garden_prop_str:
                widget_visibility["source_garden_prop_box"] = True
            elif not self.model.source or not self.model.source.source_detail:
                widget_visibility["source_none_label"] = True
            else:
                # self.model.source.source_detail = value
                widget_visibility["source_sw"] = True
            for widget, value in list(widget_visibility.items()):
                self.view.widgets[widget].set_visible(value)
            self.view.widgets.source_alignment.set_sensitive(True)

        def on_match_select(completion, model, treeiter):
            value = model[treeiter][0]
            # TODO: should we reset/store the entry values if the
            # source is changed and restore them if they are switched
            # back
            if not value:
                combo.get_child().set_text("")
                on_select(None)
            else:
                combo.get_child().set_text(utils.to_unicode(value))
                on_select(value)

            # don't set the model as dirty if this is called during
            # populate_source_combo
            if not combo._populate:
                self._dirty = True
                self.refresh_sensitivity()
            return True

        self.view.connect(completion, "match-selected", on_match_select)

        def on_entry_changed(entry, data=None):
            text = utils.to_unicode(entry.get_text())
            # see if the text matches a completion string
            comp = entry.get_completion()

            def _cmp(row, data):
                val = row[0]
                if utils.to_unicode(val) == data or (
                    isinstance(val, Contact) and str(val.id) == str(data)
                ):
                    return True
                else:
                    return False

            found = utils.search_tree_model(comp.get_model(), text, _cmp)
            if len(found) == 1:
                # the model and iter here should technically be the tree
                comp.emit("match-selected", comp.get_model(), found[0])
                self.remove_problem(PROBLEM, entry)
            else:
                self.add_problem(PROBLEM, entry)
            update_visible()
            return True

        self.view.connect(entry, "changed", on_entry_changed)

        def on_combo_changed(combo, *args):
            active = combo.get_active_iter()
            if active:
                detail = combo.get_model()[active][0]
                # set the text value on the entry since it does all the
                # validation
                if not detail:
                    combo.get_child().set_text("")
                else:
                    combo.get_child().set_text(utils.to_unicode(detail))
            update_visible()
            return True

        self.view.connect(combo, "changed", on_combo_changed)


class AccessionEditorPresenter(editor.GenericEditorPresenter):

    initializing: bool
    _dirty: bool
    session: Any
    _original_code: Any
    current_source_box: Any
    ver_presenter: Any
    voucher_presenter: Any
    source_presenter: Any
    notes_presenter: Any
    has_plants: Any
    widget_to_field_map: Any = {
        "acc_code_entry": "code",
        "acc_id_qual_combo": "id_qual",
        "acc_date_accd_entry": "date_accd",
        "acc_date_recvd_entry": "date_recvd",
        "acc_recvd_type_comboentry": "recvd_type",
        "acc_quantity_recvd_entry": "quantity_recvd",
        "intended_loc_comboentry": "intended_location",
        "intended2_loc_comboentry": "intended2_location",
        "acc_prov_combo": "prov_type",
        "acc_wild_prov_combo": "wild_prov_status",
        "acc_private_check": "private",
        "intended_loc_create_plant_checkbutton": "create_plant",
    }

    PROBLEM_INVALID_DATE: Any = random()
    PROBLEM_DUPLICATE_ACCESSION: Any = random()
    PROBLEM_ID_QUAL_RANK_REQUIRED: Any = random()

    def __init__(self, model, view) -> None:
        """
        :param model: an instance of class Accession
        ;param view: an instance of AccessionEditorView
        """
        super().__init__(model, view)
        self.initializing = True
        self.create_toolbar()
        self._dirty = False
        self.session = object_session(model)
        self._original_code = self.model.code
        self.current_source_box = None
        model.create_plant = False

        # set the default code and add it to the top of the code formats
        self.populate_code_formats(model.code or "")
        self.view.widget_set_value("acc_code_format_comboentry", model.code or "")
        if not model.code:
            model.code = model.get_next_code()
            if self.model.species:
                self._dirty = True

        self.ver_presenter = VerificationPresenter(
            self, self.model, self.view, self.session
        )
        self.voucher_presenter = VoucherPresenter(
            self, self.model, self.view, self.session
        )
        self.source_presenter = SourcePresenter(
            self, self.model, self.view, self.session
        )

        notes_parent = self.view.widgets.notes_parent_box
        notes_parent.foreach(notes_parent.remove)
        self.notes_presenter = editor.NotesPresenter(self, "notes", notes_parent)

        self.init_enum_combo("acc_id_qual_combo", "id_qual")

        # init id_qual_rank
        utils.setup_text_combobox(self.view.widgets.acc_id_qual_rank_combo)
        self.refresh_id_qual_rank_combo()

        def on_changed(combo, *args):
            it = combo.get_active_iter()
            if not it:
                self.model.id_qual_rank = None
                return
            text, col = combo.get_model()[it]
            self.set_model_attr("id_qual_rank", utils.to_unicode(col))

        self.view.connect("acc_id_qual_rank_combo", "changed", on_changed)

        # refresh_view will fire signal handlers for any connected widgets.

        from bauble.plugins.garden import init_location_comboentry

        def on_loc_select(field_name, value):
            if self.initializing:
                return
            self.set_model_attr(field_name, value)
            refresh_create_plant_checkbutton_sensitivity()

        from functools import partial

        init_location_comboentry(
            self,
            self.view.widgets.intended_loc_comboentry,
            partial(on_loc_select, "intended_location"),
            required=False,
        )
        init_location_comboentry(
            self,
            self.view.widgets.intended2_loc_comboentry,
            partial(on_loc_select, "intended2_location"),
            required=False,
        )

        # put model values in view before most handlers are connected
        self.initializing = True
        self.refresh_view()
        self.initializing = False

        # connect signals
        def sp_get_completions(text):
            try:
                # use the first token as genus while typing
                genus_name = text.split(" ", 1)[0].strip()
                result = (
                    self.session.execute(
                        select(Species)
                        .join(Genus, Species.genus_id == Genus.id)
                        .where(ilike(Genus.genus, f"{genus_name}%"))
                        .order_by(Genus.genus, Species.sp)
                        .limit(100)
                    )
                    .scalars()
                    .all()            # ← return a concrete list
                )
                return result
            except (PendingRollbackError, IntegrityError):
                self.session.rollback()
                return []
            
        def on_select(value):
            logger.debug("on select: %s", value)

            def set_model(v):
                self.set_model_attr("species", v)
                self.refresh_id_qual_rank_combo()

            # 0) Empty/cleared while typing — just clear the model, no dialog
            if value in (None, ""):
                set_model(None)
                return

            # 1) If we already got a Species instance, use it
            if isinstance(value, Species):
                chosen = value

            # 2) If it's text, only act when it looks complete: "Genus epithet"
            elif isinstance(value, str):
                text = value.strip().replace("\u200b", "")
                # ignore genus-only / partial tokens while typing
                if " " not in text:
                    set_model(None)
                    return
                genus_name, epithet = (text.split(" ", 1)[0], text.split(" ", 1)[1].strip())
                if not genus_name or not epithet:
                    set_model(None)
                    return

                # try to resolve to a Species, silently ignore if not found
                species_instance = get_species_instance(
                    session=self.session,
                    genus_epithet=genus_name,
                    epithet=epithet,
                    create=False,
                )
                if not species_instance:
                    set_model(None)
                    return
                chosen = species_instance

            # 3) Any other type — ignore
            else:
                set_model(None)
                return

            # Clear any previous inline message box
            for kid in self.view.widgets.message_box_parent.get_children():
                self.view.widgets.remove_parent(kid)

            # 4) Set resolved species, then (optionally) offer synonym swap inline
            set_model(chosen)
            stmt = SpeciesSynonym.query_with_default_order().where(
                SpeciesSynonym.synonym_id == chosen.id
            )
            syn = self.session.execute(stmt).scalars().first()
            if not syn:
                return

            msg = _(
                "The species <b>%(synonym)s</b> is a synonym of "
                "<b>%(species)s</b>.\n\nWould you like to choose "
                "<b>%(species)s</b> instead?"
            ) % {"synonym": syn.synonym, "species": syn.species}

            box = self.view.add_message_box(utils.MESSAGE_BOX_YESNO)
            box.message = msg

            def on_response(button, response):
                self.view.widgets.remove_parent(box)
                box.destroy()
                if response:
                    completion = self.view.widgets.acc_species_entry.get_completion()
                    utils.clear_model(completion)
                    model = Gtk.ListStore(object)
                    model.append([syn.species])
                    completion.set_model(model)
                    safe_set_text(self.view.widgets.acc_species_entry, utils.to_unicode(syn.species))
                    set_model(syn.species)

            box.on_response = on_response
            box.show()

        
        # Ensure the Entry has a completion and that it has a model
        species_entry = self.view.widgets.acc_species_entry
        comp = species_entry.get_completion()
        if comp is None:
            comp = Gtk.EntryCompletion()
            species_entry.set_completion(comp)
        if comp.get_model() is None:
            comp.set_model(Gtk.ListStore(object))
        # helpful UX flags (don’t fight your view’s match_func)
        try:
            comp.set_popup_completion(True)
            comp.set_inline_selection(True)
        except Exception:
            pass

        self.assign_completions_handler(
            species_entry, sp_get_completions, on_select=on_select
        )

        # Try to resolve the typed text once the entry loses focus (no popups while typing)
        def _resolve_on_blur(entry, *args):
            txt = entry.get_text().strip()
            # only try if it looks like "Genus epithet"; otherwise leave it alone
            if " " not in txt:
                self.set_model_attr("species", None)
                return False
            on_select(txt)   # on_select already handles strings / Species objects
            return False

        # either style works with your helper; pick one:
        self.view.connect("acc_species_entry", "focus-out-event", _resolve_on_blur)


        self.assign_simple_handler("acc_prov_combo", "prov_type")
        self.assign_simple_handler("acc_wild_prov_combo", "wild_prov_status")

        # connect recvd_type comboentry widget and child entry
        self.view.connect(
            "acc_recvd_type_comboentry",
            "changed",
            self.on_recvd_type_comboentry_changed,
        )
        self.view.connect(
            self.view.widgets.acc_recvd_type_comboentry.get_child(),
            "changed",
            self.on_recvd_type_entry_changed,
        )

        self.view.connect("acc_code_entry", "changed", self.on_acc_code_entry_changed)

        # date received
        self.view.connect(
            "acc_date_recvd_entry",
            "changed",
            self.on_date_entry_changed,
            "date_recvd",
        )
        utils.setup_date_button(
            self.view, "acc_date_recvd_entry", "acc_date_recvd_button"
        )

        # date accessioned
        self.view.connect(
            "acc_date_accd_entry",
            "changed",
            self.on_date_entry_changed,
            "date_accd",
        )
        utils.setup_date_button(
            self.view, "acc_date_accd_entry", "acc_date_accd_button"
        )

        self.view.connect(
            self.view.widgets.intended_loc_add_button,
            "clicked",
            self.on_loc_button_clicked,
            self.view.widgets.intended_loc_comboentry,
            "intended_location",
        )

        self.view.connect(
            self.view.widgets.intended2_loc_add_button,
            "clicked",
            self.on_loc_button_clicked,
            self.view.widgets.intended2_loc_comboentry,
            "intended2_location",
        )

        # add a taxon implies setting the acc_species_entry
        self.view.connect(
            self.view.widgets.acc_taxon_add_button,
            "clicked",
            lambda b, w: generic_taxon_add_action(
                self.model, self.view, self, self, b, w
            ),
            self.view.widgets.acc_species_entry,
        )

        self.has_plants = len(model.plants) > 0
        view.widget_set_sensitive(
            "intended_loc_create_plant_checkbutton", not self.has_plants
        )

        def refresh_create_plant_checkbutton_sensitivity(*args):
            if self.has_plants:
                view.widget_set_sensitive(
                    "intended_loc_create_plant_checkbutton", False
                )
                return
            location_chosen = bool(self.model.intended_location)
            has_quantity = (
                self.model.quantity_recvd
                and bool(int(self.model.quantity_recvd))
                or False
            )
            view.widget_set_sensitive(
                "intended_loc_create_plant_checkbutton",
                has_quantity and location_chosen,
            )

        self.assign_simple_handler("acc_quantity_recvd_entry", "quantity_recvd")
        self.view.connect_after(
            "acc_quantity_recvd_entry",
            "changed",
            refresh_create_plant_checkbutton_sensitivity,
        )
        self.assign_simple_handler(
            "acc_id_qual_combo", "id_qual", editor.UnicodeOrNoneValidator()
        )
        self.assign_simple_handler("acc_private_check", "private")

        self.refresh_sensitivity()
        refresh_create_plant_checkbutton_sensitivity()

        if self.model not in self.session.new:
            self.view.widgets.acc_ok_and_add_button.set_sensitive(True)
        self.initializing = False

    def populate_code_formats(
        self, entry_one: Optional[Any] = None, values: Optional[Any] = None
    ) -> None:
        logger.debug(f"populate_code_formats {entry_one} {values}")
        ls = self.view.widgets.acc_code_format_liststore
        if entry_one is None:
            it = ls.get_iter_first()
            entry_one = ls.get_value(it, 0) if it else ""   # ← guard
        ls.clear()
        ls.append([entry_one])
        if values is None:
            stmt = (
                select(meta.BaubleMeta)
                .where(meta.BaubleMeta.name.like("acidf_%"))
                .order_by(meta.BaubleMeta.name)
            )
            query = list(self.session.execute(stmt).scalars())

            if query:
                Accession.code_format = query[0].value
            values = [r.value for r in query]
        for v in values:
            ls.append([v])

    def on_acc_code_format_comboentry_changed(self, widget, *args) -> None:
        code_format = self.view.widget_get_value(widget)
        code = Accession.get_next_code(code_format)
        self.view.widget_set_value("acc_code_entry", code)

    def on_acc_code_format_edit_btn_clicked(self, widget, *args) -> None:
        view = editor.GenericEditorView(
            os.path.join(paths.lib_dir(), "plugins", "garden", "acc_editor.glade"),
            root_widget_name="acc_codes_dialog",
        )
        ls = view.widgets.acc_codes_liststore
        ls.clear()
        stmt = (
            select(meta.BaubleMeta)
            .where(meta.BaubleMeta.name.like("acidf_%"))
            .order_by(meta.BaubleMeta.name)
        )
        query = self.session.execute(stmt).scalars()
        for i, row in enumerate(query):
            ls.append([i + 1, row.value])
        ls.append([len(ls) + 1, ""])

        class Presenter(editor.GenericEditorPresenter):
            def on_acc_cf_renderer_edited(self, widget, iter, value):
                i = ls.get_iter_from_string(str(iter))
                ls.set_value(i, 1, value)
                if ls.iter_next(i) is None:
                    if value:
                        ls.append([len(ls) + 1, ""])
                elif value == "":
                    ls.remove(i)
                    while i:
                        ls.set_value(i, 0, ls.get_value(i, 0) - 1)
                        i = ls.iter_next(i)

        presenter = Presenter(ls, view, session=Session())
        if presenter.start() > 0:
            stmt = delete(meta.BaubleMeta).where(meta.BaubleMeta.name.like("acidf_%"))
            presenter.session.execute(stmt)
            presenter.session.commit()
            i = 1
            iter = ls.get_iter_first()
            values = []
            while iter:
                value = ls.get_value(iter, 1)
                iter = ls.iter_next(iter)
                i += 1
                if not value:
                    continue
                obj = meta.BaubleMeta(name="acidf_%02d" % i, value=value)
                values.append(value)
                presenter.session.add(obj)
            self.populate_code_formats(values=values)
            if presenter.session.in_transaction():
                presenter.session.commit()
        presenter.session.close()

    def refresh_id_qual_rank_combo(self) -> None:
        """
        Populate the id_qual_rank_combo with the parts of the species string
        """
        combo = self.view.widgets.acc_id_qual_rank_combo
        utils.clear_model(combo)
        if not self.model.species:
            return
        model = Gtk.ListStore(str, str)
        species = self.model.species
        it = model.append([str(species.genus), "genus"])
        active = None
        if self.model.id_qual_rank == "genus":
            active = it
        it = model.append([str(species.sp), "sp"])
        if self.model.id_qual_rank == "sp":
            active = it

        infrasp_parts = []
        for level in (1, 2, 3, 4):
            infrasp = [s for s in species.get_infrasp(level) if s is not None]
            if infrasp:
                infrasp_parts.append(" ".join(infrasp))
        if infrasp_parts:
            it = model.append([" ".join(infrasp_parts), "infrasp"])
            if self.model.id_qual_rank == "infrasp":
                active = it

        # if species.infrasp:
        #     s = ' '.join([str(isp) for isp in species.infrasp])
        #     if len(s) > 32:
        #         s = '%s...' % s[:29]
        #     it = model.append([s, 'infrasp'])
        #     if self.model.id_qual_rank == 'infrasp':
        #         active = it

        it = model.append(("", None))
        if not active:
            active = it
        combo.set_model(model)
        combo.set_active_iter(active)

    def on_loc_button_clicked(self, button, target_widget, target_field) -> None:
        logger.debug(
            f"on_loc_button_clicked {self}, {button}, {target_widget}, {target_field}"
        )
        from bauble.plugins.garden.location_editor import LocationEditor

        editor = LocationEditor(parent=self.view.get_window())
        if editor.start():
            location = editor.presenter.model
            self.session.add(location)
            self.remove_problem(None, target_widget)
            self.view.widget_set_value(target_widget, location)
            self.set_model_attr(target_field, location)

    def is_dirty(self):
        if self.initializing:
            return False
        presenters = [
            self.ver_presenter,
            self.voucher_presenter,
            self.notes_presenter,
            self.source_presenter,
        ]
        dirty_kids = [p.is_dirty() for p in presenters]
        return self._dirty or True in dirty_kids

    def on_recvd_type_comboentry_changed(self, combo, *args):
        """ """
        value = None
        treeiter = combo.get_active_iter()
        if treeiter:
            value = combo.get_model()[treeiter][0]
        else:
            # the changed handler is fired again after the
            # combo.get_child().set_text with the activer iter set to None
            return True
        # the entry change handler does the validation of the model
        combo.get_child().set_text(recvd_type_values[value])

    def on_recvd_type_entry_changed(self, entry, *args):
        """ """
        problem = "BAD_RECVD_TYPE"
        text = entry.get_text()
        if not text.strip():
            self.remove_problem(problem, entry)
            self.set_model_attr("recvd_type", None)
            return
        model = self.view.widgets.acc_recvd_type_comboentry.get_model()

        def match_func(row, data):
            return (
                str(row[0]).lower() == str(data).lower()
                or str(row[1]).lower() == str(data).lower()
            )

        results = utils.search_tree_model(model, text, match_func)
        if results and len(results) == 1:  # is match is unique
            self.remove_problem(problem, entry)
            self.set_model_attr("recvd_type", model[results[0]][0])
        else:
            self.add_problem(problem, entry)
            self.set_model_attr("recvd_type", None)

    def on_acc_code_entry_changed(self, entry, data: Optional[Any] = None) -> None:
        text = entry.get_text()
        from sqlalchemy import func

        stmt = (
            select(func.count())
            .select_from(Accession)
            .where(Accession.code == str(text))
        )
        count = self.session.execute(stmt).scalar_one()
        if text != self._original_code and count > 0:
            self.add_problem(
                self.PROBLEM_DUPLICATE_ACCESSION,
                self.view.widgets.acc_code_entry,
            )
            self.set_model_attr("code", None)
            return
        self.remove_problem(
            self.PROBLEM_DUPLICATE_ACCESSION, self.view.widgets.acc_code_entry
        )
        if text == "":
            self.set_model_attr("code", None)
        else:
            self.set_model_attr("code", utils.to_unicode(text))

    def on_date_entry_changed(self, entry, prop) -> None:
        """handle changed signal.

        used by acc_date_recvd_entry and acc_date_accd_entry

        :param prop: the model property to change, should be
          date_recvd or date_accd
        """
        from bauble.editor import ValidatorError

        value = None
        PROBLEM = "INVALID_DATE"
        try:
            value = editor.DateValidator().to_python(entry.get_text())
        except ValidatorError as e:
            logger.debug(e)
            self.add_problem(PROBLEM, entry)
        else:
            self.remove_problem(PROBLEM, entry)
        self.set_model_attr(prop, value)

    def set_model_attr(self, field, value, validator: Optional[Any] = None) -> None:
        """
        Set attributes on the model and update the GUI as expected.
        """
        # debug('set_model_attr(%s, %s)' % (field, value))
        super().set_model_attr(field, value, validator)
        self._dirty = True
        # TODO: add a test to make sure that the change notifiers are
        # called in the expected order
        wild_prov_combo = self.view.widgets.acc_wild_prov_combo
        if field == "prov_type":
            is_wild = (self.model.prov_type == "Wild")
            if is_wild:
                iter_ = wild_prov_combo.get_active_iter()
                if iter_:
                    model = wild_prov_combo.get_model()
                    self.model.wild_prov_status = model[iter_][0]
                else:
                    self.model.wild_prov_status = None
            else:
                # remove the value in the model from the wild_prov_combo
                self.model.wild_prov_status = None
                wild_prov_combo.set_active(-1)

            wild_prov_combo.set_sensitive(is_wild)

        if field == "id_qual" and not self.model.id_qual_rank:
            self.add_problem(
                self.PROBLEM_ID_QUAL_RANK_REQUIRED,
                self.view.widgets.acc_id_qual_rank_combo,
            )
        else:
            self.remove_problem(self.PROBLEM_ID_QUAL_RANK_REQUIRED)

        self.refresh_sensitivity()

    def validate(self, add_problems: bool = False):
        """
        Validate the self.model
        """
        # TODO: if add_problems=True then we should add problems to
        # all the required widgets that don't have values
        # Require a real Species instance, not just truthy text
        if not self.model.code or not isinstance(self.model.species, Species):
            return False
        
        if not self.model.code or not isinstance(self.model.species, Species):
            return False
        if not self.model.code or not self.model.species:
            return False

        for ver in self.model.verifications or []:
            ignore = ("id", "accession_id", "species_id", "prev_species_id")
            if (
                utils.get_invalid_columns(ver, ignore_columns=ignore)
                or not ver.species
                or not ver.prev_species
            ):
                return False

        for voucher in self.model.vouchers:
            ignore = ("id", "accession_id")
            if utils.get_invalid_columns(voucher, ignore_columns=ignore):
                return False

        # validate the source if there is one
        if self.model.source:
            coll = self.model.source.collection
            prop = self.model.source.propagation
            if coll and utils.get_invalid_columns(coll):
                return False
            if prop and utils.get_invalid_columns(prop):
                return False

            if not self.model.source.propagation:
                return True

            prop = self.model.source.propagation
            prop_ignore = ["id", "propagation_id"]
            prop_model = None
            if prop and prop.prop_type == "Seed":
                prop_model = prop._seed
            elif prop and prop.prop_type == "UnrootedCutting":
                prop_model = prop._cutting
            else:
                logger.debug("AccessionEditorPresenter.validate(): unknown prop_type")
                return True  # let user save it anyway

            if utils.get_invalid_columns(prop_model, prop_ignore):
                return False

        return True

    def refresh_sensitivity(self) -> None:
        """
        Refresh the sensitivity of the fields and accept buttons according
        to the current values in the model.
        """
        if self.model.species and self.model.id_qual:
            self.view.widgets.acc_id_qual_rank_combo.set_sensitive(True)
        else:
            self.view.widgets.acc_id_qual_rank_combo.set_sensitive(False)

        sensitive = (
            self.is_dirty()
            and self.validate()
            and not self.problems
            and not self.source_presenter.all_problems()
            and not self.ver_presenter.problems
            and not self.voucher_presenter.problems
        )
        self.view.set_accept_buttons_sensitive(sensitive)

    def refresh_view(self) -> None:
        """
        get the values from the model and put them in the view
        """
        prefs.prefs[prefs.date_format_pref]
        for widget, field in list(self.widget_to_field_map.items()):
            if field == "species_id":
                value = self.model.species
            else:
                value = getattr(self.model, field)
            self.view.widget_set_value(widget, value)

        self.view.widget_set_value(
            "acc_wild_prov_combo",
            dict(wild_prov_status_values).get(self.model.wild_prov_status, ""),
            index=1,
        )
        self.view.widget_set_value(
            "acc_prov_combo",
            dict(prov_type_values).get(self.model.prov_type, ""),
            index=1,
        )
        self.view.widget_set_value(
            "acc_recvd_type_comboentry",
            recvd_type_values.get(self.model.recvd_type, ""),
            index=1,
        )

        self.view.widgets.acc_private_check.set_inconsistent(False)
        self.view.widgets.acc_private_check.set_active(self.model.private is True)

        sensitive = self.model.prov_type == "Wild"
        self.view.widgets.acc_wild_prov_combo.set_sensitive(sensitive)

    def cleanup(self) -> None:
        super().cleanup()
        self.ver_presenter.cleanup()
        self.voucher_presenter.cleanup()
        self.source_presenter.cleanup()

    def start(self):
        self.source_presenter.start()
        r = self.view.start()
        return r


class AccessionEditor(editor.GenericModelViewPresenterEditor):

    # these have to correspond to the response values in the view
    parent: Any
    _committed: Any
    presenter: Any
    RESPONSE_OK_AND_ADD: int = 11
    RESPONSE_NEXT: int = 22
    ok_responses: Any = (RESPONSE_OK_AND_ADD, RESPONSE_NEXT)

    def __init__(
        self, model: Optional[Any] = None, parent: Optional[Any] = None
    ) -> None:
        """
        :param model: Accession instance or None
        :param parent: the parent widget
        """
        if model is None:
            model = Accession()

        super().__init__(model, parent)
        self.parent = parent
        self._committed = []

        view = AccessionEditorView(parent=parent)
        self.presenter = AccessionEditorPresenter(self.model, view)

        # set the default focus
        if self.model.species is None:
            view.widgets.acc_species_entry.grab_focus()
        else:
            view.widgets.acc_code_entry.grab_focus()

    def handle_response(self, response):
        """
        handle the response from self.presenter.start() in self.start()
        """
        if TYPE_CHECKING:
            from bauble.plugins.garden import PlantEditor
            from bauble.plugins.garden.models import Plant

        not_ok_msg = _("Are you sure you want to lose your changes?")
        if response == Gtk.ResponseType.OK or response in self.ok_responses:
            try:
                if not self.presenter.validate():
                    # TODO: ideally the accept buttons wouldn't have
                    # been sensitive until validation had already
                    # succeeded but we'll put this here either way and
                    # show a message about filling in the fields
                    #
                    # msg = _('Some required fields have not been completed')
                    return False
                if self.presenter.is_dirty():
                    self.commit_changes()
                    self._committed.append(self.model)
            except DBAPIError as e:
                msg = _("Error committing changes.\n\n%s") % utils.xml_safe(str(e.orig))
                utils.message_details_dialog(msg, str(e), Gtk.MessageType.ERROR)
                return False
            except Exception as e:
                msg = _(
                    "Unknown error when committing changes. See the "
                    "details for more information.\n\n%s"
                ) % utils.xml_safe(e)
                utils.message_details_dialog(
                    msg, traceback.format_exc(), Gtk.MessageType.ERROR
                )
                return False
        elif (
            self.presenter.is_dirty()
            and utils.yes_no_dialog(not_ok_msg)
            or not self.presenter.is_dirty()
        ):
            if self.session.in_transaction():
                self.session.rollback()
            return True
        else:
            return False

        # respond to responses
        more_committed = None
        if response == self.RESPONSE_NEXT:
            self.presenter.cleanup()
            e = AccessionEditor(parent=self.parent)
            more_committed = e.start()
        elif response == self.RESPONSE_OK_AND_ADD:
            from bauble.plugins.garden import PlantEditor
            from bauble.plugins.garden.models import Plant  
            e = PlantEditor(Plant(accession=self.model), self.parent)
            more_committed = e.start()

        if more_committed is not None:
            if isinstance(more_committed, list):
                self._committed.extend(more_committed)
            else:
                self._committed.append(more_committed)

        return True

    def start(self):
        from bauble.plugins.plants.species_model import Species
        from sqlalchemy import func

        if self.session.execute(select(func.count()).select_from(Species)).scalar_one() == 0:
            msg = _(
                "You must first add or import at least one species into "
                "the database before you can add accessions."
            )
            utils.message_dialog(msg)
            return

        while True:
            # debug(self.presenter.source_presenter.source)
            # debug(self.presenter.source_presenter.source.collection)
            response = self.presenter.start()
            self.presenter.view.save_state()
            if self.handle_response(response):
                break

        self.session.close()  # cleanup session
        self.presenter.cleanup()
        return self._committed

    @staticmethod
    def _cleanup_collection(model):
        """ """
        if not model:
            return
        # TODO: we should raise something besides commit ValueError
        # so we can give a meaningful response
        if model.latitude is not None or model.longitude is not None:
            if (model.latitude is not None and model.longitude is None) or (
                model.longitude is not None and model.latitude is None
            ):
                msg = _("model must have both latitude and longitude or " "neither")
                raise ValueError(msg)
            elif model.latitude is None and model.longitude is None:
                model.geo_accy = None  # don't save
        else:
            model.geo_accy = None  # don't save

        # reset the elevation accuracy if the elevation is None
        if model.elevation is None:
            model.elevation_accy = None
        return model

    def commit_changes(self):
        """
        Commit changes specific to accession and handle dependencies.
        """
        from bauble.plugins.garden.models import Plant  # ← keep this import
        from bauble.plugins.garden.models import Accession
        from bauble.plugins.plants.species_model import Species
        from sqlalchemy import inspect as sa_inspect

        # Ensure the Accession instance is attached to this session
        st = sa_inspect(self.model)
        if st.transient or st.pending:
            # brand new object, just add it to this session
            self.session.add(self.model)
        elif st.detached:
            # came from a different session, merge it (default load=True)
            self.model = self.session.merge(self.model)

        # --- NEW: make sure model.species is a real Species bound to this session ---
        sp = self.model.species

        # If a plain string slipped in (e.g., from the entry auto-binding), try to resolve it
        if isinstance(sp, str):
            txt = sp.strip().replace("\u200b", "")
            sp = None
            if " " in txt:
                gen, epithet = txt.split(" ", 1)
                # get_species_instance is already imported at top of the file
                sp = get_species_instance(
                    session=self.session,
                    genus_epithet=gen,
                    epithet=epithet.strip(),
                    create=False,
                )

        # Hard stop if we still don’t have a proper Species row
        if not isinstance(sp, Species):
            # optional: user-friendly message; remove if you prefer only the generic dialog upstream
            utils.message_dialog(
                _("You must select a valid species from the list."),
                type=Gtk.MessageType.WARNING,
            )
            # Raise to abort the commit (handle_response catches Exception and won’t append)
            raise ValueError("Invalid or missing species; refusing to commit accession.")

        # Make sure the Species is attached to this session as well
        sp_state = sa_inspect(sp)
        if sp_state.detached:
            sp = self.session.merge(sp)
        elif sp_state.transient:
            # shouldn’t happen for a taxon picked from DB, but handle gracefully
            self.session.add(sp)

        # Set both the relationship and (if exposed) the FK column
        self.model.species = sp
        if hasattr(self.model, "species_id"):
            self.model.species_id = sp.id
        # keep only this accession; expunge any other transient/new ones
        for obj in list(self.session.new):
            if isinstance(obj, Accession) and obj is not self.model:
                self.session.expunge(obj)

        # also a sanity guard: species_id must be set
        if not getattr(self.model, "species_id", None) and getattr(self.model, "species", None):
            self.model.species_id = self.model.species.id

        if not getattr(self.model, "species_id", None):
            raise ValueError("species_id not set just before commit")


        if self.model.source:
            if not self.model.source.collection:
                utils.delete_or_expunge(self.presenter.source_presenter.collection)

            if self.model.source.propagation:
                self.model.source.propagation.clean()
            else:
                utils.delete_or_expunge(self.presenter.source_presenter.propagation)
        else:
            utils.delete_or_expunge(self.presenter.source_presenter.source)
            utils.delete_or_expunge(self.presenter.source_presenter.collection)
            utils.delete_or_expunge(self.presenter.source_presenter.propagation)

        if self.model.id_qual is None:
            self.model.id_qual_rank = None

        # should we also add a plant for this accession?
        if self.model.create_plant:
            logger.debug("creating plant for new accession")
            accession = self.model
            location = accession.intended_location
            plant = Plant(
                accession=accession,
                code="1",
                quantity=accession.quantity_recvd,
                location=location,
                acc_type=accession_type_to_plant_material.get(self.model.recvd_type),
            )
            self.session.add(plant)

        try:
            logger.warning(
                "About to commit accession code=%s species=%r species_id=%s bound=%s",
                self.model.code,
                self.model.species,
                getattr(self.model, "species_id", None),
                object_session(self.model.species) is self.session,
            )
            super().commit_changes()
        except Exception:
            return False
        return True

# import at the bottom to avoid circular dependencies

#
# infobox for searchview
#


# TODO: i don't think this shows all field of an accession, like the
# accuracy values
class GeneralAccessionExpander(InfoExpander):
    """
    generic information about an accession like
    number of clones, provenance type, wild provenance type, speciess
    """

    current_obj: Any
    private_image: Any

    def __init__(self, widgets) -> None:
        """ """
        super().__init__(_("General"), widgets)
        general_box = self.widgets.general_box
        self.widgets.general_window.remove(general_box)
        self.vbox.pack_start(general_box, True, True, 0)
        self.current_obj = None
        self.private_image = self.widgets.acc_private_data

        def on_species_clicked(*args):
            select_in_search_results(self.current_obj.species)

        utils.make_label_clickable(self.widgets.name_data, on_species_clicked)

        def on_parent_plant_clicked(*args):
            src = getattr(self.current_obj, "source", None)
            pp = getattr(src, "plant_propagation", None) if src else None
            if pp and pp.plant:
                select_in_search_results(pp.plant)

        utils.make_label_clickable(
            self.widgets.parent_plant_data, on_parent_plant_clicked
        )

        def on_nplants_clicked(*args):
            cmd = f'plant where accession.code="{self.current_obj.code}"'
            bauble.gui.send_command(cmd)

        utils.make_label_clickable(self.widgets.nplants_data, on_nplants_clicked)

    def update(self, row) -> None:
        """ """
        from bauble.plugins.garden.models import Plant

        self.current_obj = row
        self.widget_set_value(
            "acc_code_data",
            f"<big>{utils.xml_safe(str(row.code))}</big>",
            markup=True,
        )

        acc_private = self.private_image
        if row.private:
            if acc_private.get_parent() != self.widgets.acc_code_box:
                self.widgets.acc_code_box.pack_start(acc_private, True, True, 0)
        else:
            self.widgets.remove_parent(acc_private)

        self.widget_set_value(
            "name_data",
            row.species_str(markup=True, authors=True),
            markup=True,
        )

        session = object_session(row)
        plant_locations = {}
        for plant in row.plants:
            if plant.quantity == 0:
                continue
            q = plant_locations.setdefault(plant.location, 0)
            plant_locations[plant.location] = q + plant.quantity
        if plant_locations:
            strs = []
            for location, quantity in list(plant_locations.items()):
                strs.append(
                    _("%(quantity)s in %(location)s")
                    % dict(location=str(location), quantity=quantity)
                )
            s = "\n".join(strs)
        else:
            s = "0"
        self.widget_set_value("living_plants_data", s)

        from sqlalchemy import func

        stmt = select(func.count()).select_from(Plant).where(Plant.accession_id == row.id)
        nplants = session.execute(stmt).scalar_one()

        self.widget_set_value("nplants_data", nplants)
        self.set_labeled_value("date_recvd", row.date_recvd)
        self.set_labeled_value("date_accd", row.date_accd)

        type_str = ""
        if row.recvd_type:
            type_str = recvd_type_values[row.recvd_type]
        self.set_labeled_value("recvd_type", type_str)
        quantity_str = ""
        if row.quantity_recvd:
            quantity_str = row.quantity_recvd
        self.set_labeled_value("quantity_recvd", quantity_str)

        prov_str = dict(prov_type_values).get(row.prov_type, "")
        if row.prov_type == "Wild" and row.wild_prov_status:
            prov_str = (
                f"{prov_str} ({dict(wild_prov_status_values).get(row.wild_prov_status, '')})"
            )
        self.set_labeled_value("prov", prov_str)

        image_size = Gtk.IconSize.SMALL_TOOLBAR
        icon_name = "dialog-no"
        if row.private:
            icon_name = "dialog-yes"
        self.private_image.set_from_icon_name(icon_name, image_size)

        loc_map = (
            ("intended_loc", "intended_location"),
            ("intended2_loc", "intended2_location"),
        )

        set_count = False
        for prefix, attr in loc_map:
            location_str = ""
            location = getattr(row, attr)
            if location:
                set_count = True
                if location.name and location.code:
                    location_str = f"{location.name} ({location.code})"
                elif location.name and not location.code:
                    location_str = f"{location.name}"
                elif not location.name and location.code:
                    location_str = f"({location.code})"
            self.set_labeled_value(prefix, location_str)
        self.widgets["intended_loc_separator"].set_visible(set_count)


class SourceExpander(InfoExpander):
    set_expanded: bool
    set_sensitive: bool

    def __init__(self, widgets) -> None:
        super().__init__(_("Source"), widgets)
        source_box = self.widgets.source_box
        self.widgets.source_window.remove(source_box)
        self.vbox.pack_start(source_box, True, True, 0)

    def update_collection(self, collection) -> None:
        self.widget_set_value("loc_data", collection.locale)
        self.widget_set_value("datum_data", collection.gps_datum)

        geo_accy = collection.geo_accy
        if not geo_accy:
            geo_accy = ""
        else:
            geo_accy = f"(+/- {geo_accy}m)"

        lat_str = ""
        if collection.latitude is not None:
            dir, deg, min, sec = latitude_to_dms(collection.latitude)
            lat_str = (
                f"{collection.latitude} ({dir} {deg}°{min}'{sec:.2f}\") {geo_accy}"
            )
        self.widget_set_value("lat_data", lat_str)

        long_str = ""
        if collection.longitude is not None:
            dir, deg, min, sec = longitude_to_dms(collection.longitude)
            long_str = (
                f"{collection.longitude} ({dir} {deg}°{min}'{sec:.2f}\") {geo_accy}"
            )
        self.widget_set_value("lon_data", long_str)

        elevation = ""
        if collection.elevation:
            elevation = f"{collection.elevation}m"
            if collection.elevation_accy:
                elevation += f" (+/- {collection.elevation_accy}m)"
        self.widget_set_value("elev_data", elevation)

        self.widget_set_value("coll_data", collection.collector)
        self.widget_set_value("date_data", collection.date)
        self.widget_set_value("collid_data", collection.collectors_code)
        self.widget_set_value("habitat_data", collection.habitat)
        self.widget_set_value("collnotes_data", collection.notes)

    def update(self, row) -> None:
        if not row.source:
            self.set_expanded(False)
            self.set_sensitive(False)
            return

        if row.source.source_detail:
            self.widgets.source_name_label.set_visible(True)
            self.widgets.source_name_data.set_visible(True)
            self.widget_set_value(
                "source_name_data", utils.to_unicode(row.source.source_detail)
            )

            def on_source_clicked(w, e, x):
                select_in_search_results(x)

            utils.make_label_clickable(
                self.widgets.source_name_data,
                on_source_clicked,
                row.source.source_detail,
            )
        else:
            self.widgets.source_name_label.set_visible(False)
            self.widgets.source_name_data.set_visible(False)

        sources_code = ""
        if row.source.sources_code:
            sources_code = row.source.sources_code
        self.widget_set_value("sources_code_data", utils.to_unicode(sources_code))

        if row.source.plant_propagation:
            self.widgets.parent_plant_label.set_visible(True)
            self.widgets.parent_plant_eventbox.set_visible(True)
            self.widget_set_value(
                "parent_plant_data", str(row.source.plant_propagation.plant)
            )
            self.widget_set_value(
                "propagation_data", row.source.plant_propagation.get_summary()
            )
        else:
            self.widgets.parent_plant_label.set_visible(False)
            self.widgets.parent_plant_eventbox.set_visible(False)

        prop_str = ""
        if row.source.propagation:
            prop_str = row.source.propagation.get_summary()
        self.widget_set_value("propagation_data", prop_str)

        if row.source.collection:
            self.widgets.collection_expander.set_expanded(True)
            self.widgets.collection_expander.set_sensitive(True)
            self.update_collection(row.source.collection)
        else:
            self.widgets.collection_expander.set_expanded(False)
            self.widgets.collection_expander.set_sensitive(False)


class VerificationsExpander(InfoExpander):
    """
    the accession's notes
    """

    def __init__(self, widgets) -> None:
        super().__init__(_("Verifications"), widgets)
        # notes_box = self.widgets.notes_box
        # self.widgets.notes_window.remove(notes_box)
        # self.vbox.pack_start(notes_box, True, True, 0)

    def update(self, row) -> None:
        pass
        # self.widget_set_value('notes_data', row.notes)


class VouchersExpander(InfoExpander):
    """
    the accession's notes
    """

    def __init__(self, widgets) -> None:
        super().__init__(_("Vouchers"), widgets)

    def update(self, row) -> None:
        for kid in self.vbox.get_children():
            self.vbox.remove(kid)

        if not row.vouchers:
            self.set_expanded(False)
            self.set_sensitive(False)
            return

        # TODO: should save/restore the expanded state of the vouchers
        self.set_expanded(True)
        self.set_sensitive(True)

        parents = [v for v in row.vouchers if v.parent_material]
        for voucher in parents:
            s = f"{voucher.herbarium} {voucher.code} (parent)"
            label = Gtk.Label(label=s)
            label.set_alignment(0.0, 0.5)
            self.vbox.pack_start(label, True, True, 0)
            label.show()

        not_parents = [v for v in row.vouchers if not v.parent_material]
        for voucher in not_parents:
            s = f"{voucher.herbarium} {voucher.code}"
            label = Gtk.Label(label=s)
            label.set_alignment(0.0, 0.5)
            self.vbox.pack_start(label, True, True, 0)
            label.show()


class AccessionInfoBox(InfoBox):
    """
    - general info
    - source
    """

    widgets: Any
    general: Any
    source: Any
    links: Any
    mapinfo: Any
    properties_expander: Any

    def __init__(self) -> None:
        super().__init__()
        filename = os.path.join(
            paths.lib_dir(), "plugins", "garden", "acc_infobox.glade"
        )
        self.widgets = utils.BuilderWidgets(filename)
        self.general = GeneralAccessionExpander(self.widgets)
        self.add_expander(self.general)
        self.source = SourceExpander(self.widgets)
        self.add_expander(self.source)

        # self.vouchers = VouchersExpander(self.widgets)
        # self.add_expander(self.vouchers)
        # self.verifications = VerificationsExpander(self.widgets)
        # self.add_expander(self.verifications)

        self.links = view.LinksExpander("notes")
        self.add_expander(self.links)

        self.mapinfo = MapInfoExpander(self.get_map_extents)
        self.add_expander(self.mapinfo)

        self.properties_expander = PropertiesExpander()
        self.add_expander(self.properties_expander)

    def get_map_extents(self, accession):
        result = []
        for plant in accession.plants:
            try:
                result.append(plant.coords)
            except Exception as e:
                logging.debug(f"Skipping plant without coordinates: {e}")
        return result

    def update(self, row) -> None:
        from bauble.plugins.garden.models import Collection

        if isinstance(row, Collection):
            row = row.source.accession

        self.general.update(row)
        self.mapinfo.update(row)
        self.properties_expander.update(row)

        # if row.verifications:
        #     self.verifications.update(row)
        # self.verifications.set_expanded(row.verifications != None)
        # self.verifications.set_sensitive(row.verifications != None)

        # self.vouchers.update(row)

        urls = [x for x in [utils.get_urls(note.note) for note in row.notes] if x != []]
        if not urls:
            self.links.set_visible(False)
            self.links._sep.set_visible(False)
        else:
            self.links.set_visible(True)
            self.links._sep.set_visible(True)
            self.links.update(row)

        self.source.set_sensitive(True)
        self.source.update(row)
