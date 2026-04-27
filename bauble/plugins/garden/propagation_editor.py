#
# Copyright 2008-2010 Brett Adams
# Copyright 2015-2017 Mario Frasca <mario@anche.no>.
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
# propagation module
#
import datetime
import logging
import os
import traceback
import weakref
from gettext import gettext as _
from typing import Any, Optional

import bauble
import bauble.paths as paths
import bauble.prefs as prefs
import bauble.utils as utils
from bauble import editor
from bauble.plugins.garden.constants import (
    bottom_heat_unit_values,
    cutting_type_values,
    flower_buds_values,
    leaves_values,
    length_unit_values,
    prop_type_values,
    tip_values,
    wound_values,
)
from bauble.utils import (
    add_to_relationship,
    count_relationship_items,
    get_object_session,
    handle_db_error,
    parse_date,
    remove_from_relationship,
)

logger: Any
from bauble.gtkinit import Gtk
from sqlalchemy.orm.session import object_session

# from sqlalchemy.ext.declarative import declared_attr

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class PropagationHandler:
    _dirty: bool

    def create_propagation_box(self, propagation):
        """
        Creates a propagation UI box with edit and remove buttons.
        GTK 3 Compatible.
        """
        hbox = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=5
        )  # Replaces Gtk.HBox
        expander = Gtk.Expander()

        # Set Expander Label First
        prop_type = prop_type_values[propagation.prop_type]
        from bauble.btypes import DateTime

        date = DateTime().process_bind_param(propagation.date, None)
        date_format = prefs.prefs[prefs.date_format_pref]
        date_str = date.strftime(date_format)
        expander.set_label(f"{prop_type} on {date_str}")

        hbox.pack_start(expander, True, True, 0)

        from bauble.plugins.garden.plant_editor import label_size_allocate

        # Label inside Expander
        label = Gtk.Label(label=propagation.get_summary())
        label.set_line_wrap(True)
        label.set_xalign(0)  # Replaces set_alignment(0, 0)
        label.set_margin_start(5)  # Instead of set_padding
        label.set_margin_end(5)
        label.connect("size-allocate", label_size_allocate)
        expander.add(label)

        def on_edit_clicked(button, prop, label):
            editor = PropagationEditor(model=prop, parent=self.view.get_window())
            if editor.start(commit=False) is not None:
                label.set_label(prop.get_summary())
                self._dirty = True
            self.parent_ref().refresh_sensitivity()

        # Right-aligned button box
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        hbox.pack_end(button_box, False, False, 0)  # Align to right

        # Edit Button
        edit_button = Gtk.Button()
        utils.set_button_contents(
            edit_button, label_text="Edit", icon_name="document-edit"
        )

        self.view.connect(edit_button, "clicked", on_edit_clicked, propagation, label)
        button_box.pack_start(edit_button, False, False, 0)

        def on_remove_clicked(button, propagation, box):
            count = count_relationship_items(propagation.accessions)
            potential = propagation.accessible_quantity
            if count == 0:
                msg = (
                    _(
                        "This propagation has produced %s plants.\n"
                        "It can already be accessioned.\n\n"
                        "Are you sure you want to remove it?"
                    )
                    % potential
                    if potential
                    else _(
                        "Are you sure you want to remove\n" "this propagation trial?"
                    )
                )

                if not utils.yes_no_dialog(msg):
                    return False
            else:
                msg = (
                    _(
                        "This propagation is referred to\n"
                        "by %s accessions.\n\n"
                        "You cannot remove it."
                    )
                    % count
                    if count > 1
                    else _(
                        "This propagation is referred to\n"
                        "by accession %s.\n\n"
                        "You cannot remove it."
                    )
                    % propagation.accessions[0]
                )

                utils.message_dialog(msg, type=Gtk.MessageType.WARNING)
                return False

            remove_from_relationship(self.model.propagations, propagation)
            self.view.widgets.prop_tab_box.remove(box)
            self._dirty = True
            self.parent_ref().refresh_sensitivity()

        # Remove Button
        remove_button = Gtk.Button()
        remove_icon = Gtk.Image.new_from_icon_name("edit-delete", Gtk.IconSize.BUTTON)
        # 7. issue_gtk_button_image_api (REMOVED, pack GtkImage manually inside GtkButton)
        if Gtk.get_major_version() >= 4:
            remove_button.set_child(remove_icon)
        else:
            remove_button.add(remove_icon)
            remove_button.show_all()
        self.view.connect(
            remove_button, "clicked", on_remove_clicked, propagation, hbox
        )
        button_box.pack_start(remove_button, False, False, 0)

        hbox.show_all()
        return hbox

    def on_add_button_clicked(self, *args) -> None:
        """Handle add button click."""
        self.add_propagation()
        self.parent_ref().refresh_sensitivity()


class PropagationTabPresenter(PropagationHandler, editor.GenericEditorPresenter):
    """PropagationTabPresenter

    :param parent: an instance of PlantEditorPresenter
    :param model: an instance of class Plant
    :param view: an instance of PlantEditorView
    :param session:
    """

    parent_ref: Any
    session: Any
    _dirty: bool

    def __init__(self, parent, model, view, session) -> None:
        super().__init__(model, view)
        self.parent_ref = weakref.ref(parent)
        self.session = session
        self.view.connect("prop_add_button", "clicked", self.on_add_button_clicked)
        tab_box = self.view.widgets.prop_tab_box
        for kid in list(tab_box.get_children()):
            if isinstance(kid, Gtk.Box):
                tab_box.remove(kid)  # remove old prop boxes
        for prop in self.model.propagations:
            box = self.create_propagation_box(prop)
            tab_box.pack_start(box, False, True, 0)
        self._dirty = False

    def is_dirty(self):
        return self._dirty

    def add_propagation(self) -> None:
        """
        Open the PropagationEditor and append the resulting
        propagation to self.model.propagations
        """
        from bauble.plugins.garden.models import Propagation as Propagation
        propagation = Propagation()
        propagation.prop_type = "Seed"  # a reasonable default
        add_to_relationship(self.model.propagations, propagation)
        editor = PropagationEditor(propagation, parent=self.view.get_window())
        # open propagation editor with start(commit=False) so that the
        # propagation editor doesn't commit its changes since we'll be
        # doing our own commit later
        committed = editor.start(commit=False)
        if committed:
            box = self.create_propagation_box(committed)
            self.view.widgets.prop_tab_box.pack_start(box, False, True, 0)
            self._dirty = True
        else:
            propagation.plant = None



class PropagationEditorView(editor.GenericEditorView):
    """ """

    _tooltips: Any = {}

    def __init__(self, parent: Optional[Any] = None) -> None:
        """ """
        super().__init__(
            os.path.join(paths.lib_dir(), "plugins", "garden", "prop_editor.glade"),
            parent=parent,
        )
        self.init_translatable_combo("prop_type_combo", prop_type_values)

    def get_window(self):
        """ """
        return self.widgets.prop_dialog

    def start(self):
        return self.get_window().run()


class CuttingPresenter(editor.GenericEditorPresenter):

    parent_ref: Any
    session: Any
    _dirty: bool
    propagation: Any
    model: Any
    widget_to_field_map: Any = {
        "cutting_type_combo": "cutting_type",
        "cutting_length_entry": "length",
        "cutting_length_unit_combo": "length_unit",
        "cutting_tip_combo": "tip",
        "cutting_leaves_combo": "leaves",
        "cutting_lvs_reduced_entry": "leaves_reduced_pct",
        "cutting_buds_combo": "flower_buds",
        "cutting_wound_combo": "wound",
        "cutting_fungal_comboentry": "fungicide",
        "cutting_media_comboentry": "media",
        "cutting_container_comboentry": "container",
        "cutting_hormone_comboentry": "hormone",
        "cutting_location_comboentry": "location",
        "cutting_cover_comboentry": "cover",
        "cutting_heat_entry": "bottom_heat_temp",
        "cutting_heat_unit_combo": "bottom_heat_unit",
        "cutting_rooted_pct_entry": "rooted_pct",
    }

    def __init__(self, parent, model, view, session) -> None:
        """
        :param model: an instance of class Propagation
        :param view: an instance of PropagationEditorView
        """
        from bauble.plugins.garden.models import PropCutting
        super().__init__(model, view)
        self.parent_ref = weakref.ref(parent)
        self.session = session
        self._dirty = False

        # instance is initialized with a Propagation instance as model, but
        # that's just the common parts.  This instance takes care of the
        # _cutting part of the propagation
        self.propagation = self.model
        if not self.propagation._cutting:
            self.propagation._cutting = PropCutting()
        self.model = self.model._cutting

        init_combo = self.view.init_translatable_combo
        init_combo(
            "cutting_type_combo",
            cutting_type_values,
            editor.UnicodeOrNoneValidator(),
        )
        init_combo("cutting_length_unit_combo", length_unit_values)
        init_combo("cutting_tip_combo", tip_values)
        init_combo("cutting_leaves_combo", leaves_values)
        init_combo("cutting_buds_combo", flower_buds_values)
        init_combo("cutting_wound_combo", wound_values)
        init_combo("cutting_heat_unit_combo", bottom_heat_unit_values)

        widgets = self.view.widgets

        def distinct(c):
            return utils.get_distinct_values(c, self.session)

        utils.setup_text_combobox(
            widgets.cutting_hormone_comboentry, distinct(PropCutting.hormone)
        )
        utils.setup_text_combobox(
            widgets.cutting_cover_comboentry, distinct(PropCutting.cover)
        )
        utils.setup_text_combobox(
            widgets.cutting_fungal_comboentry, distinct(PropCutting.fungicide)
        )
        utils.setup_text_combobox(
            widgets.cutting_location_comboentry, distinct(PropCutting.location)
        )
        utils.setup_text_combobox(
            widgets.cutting_container_comboentry,
            distinct(PropCutting.container),
        )
        utils.setup_text_combobox(
            widgets.cutting_media_comboentry, distinct(PropCutting.media)
        )

        # set default units
        units = prefs.prefs[prefs.units_pref]
        if units == "imperial":
            self.model.length_unit = "in"
            self.model.bottom_heat_unit = "F"
        else:
            self.model.length_unit = "mm"
            self.model.bottom_heat_unit = "C"

        # the liststore for rooted cuttings contains PropCuttingRooted
        # objects, not just their fields, so we cannot define it in the
        # glade file.
        rooted_liststore = Gtk.ListStore(object)
        self.view.widgets.rooted_treeview.set_model(rooted_liststore)

        from functools import partial

        def rooted_cell_data_func(
            attr_name, column, cell, rooted_liststore, treeiter, data=None
        ):
            # extract attr from the object and show it in the cell
            store_cell = rooted_liststore[treeiter][0]
            value = getattr(store_cell, attr_name)
            if isinstance(value, datetime.date):
                format = prefs.prefs[prefs.date_format_pref]
                value = value.strftime(format)
            cell.set_property("text", f"{value}")

        def on_rooted_cell_edited(attr_name, cell, treeiter, new_text):
            # update object if field was modified, refresh sensitivity
            v = rooted_liststore[treeiter][0]
            new_value = None
            if attr_name == "quantity":
                new_value = int(utils.to_unicode(new_text))
            elif attr_name == "date":
                new_value = parse_date(utils.to_unicode(new_text))
            if getattr(v, attr_name) == new_value:
                return  # didn't change
            setattr(v, attr_name, new_value)
            self._dirty = True
            self.parent_ref().refresh_sensitivity()

        sfw = self.view.widgets
        for cell, column, attr_name in [
            (sfw.rooted_date_cell, sfw.rooted_date_column, "date"),
            (sfw.rooted_quantity_cell, sfw.rooted_quantity_column, "quantity"),
        ]:
            cell.set_property("editable", True)
            self.view.connect(cell, "edited", partial(on_rooted_cell_edited, attr_name))
            column.set_cell_data_func(cell, partial(rooted_cell_data_func, attr_name))

        self.refresh_view()

        self.assign_simple_handler("cutting_type_combo", "cutting_type")
        self.assign_simple_handler("cutting_length_entry", "length")
        self.assign_simple_handler("cutting_length_unit_combo", "length_unit")
        self.assign_simple_handler("cutting_tip_combo", "tip")
        self.assign_simple_handler("cutting_leaves_combo", "leaves")
        self.assign_simple_handler("cutting_lvs_reduced_entry", "leaves_reduced_pct")

        self.assign_simple_handler(
            "cutting_media_comboentry",
            "media",
            editor.UnicodeOrNoneValidator(),
        )
        self.assign_simple_handler(
            "cutting_container_comboentry",
            "container",
            editor.UnicodeOrNoneValidator(),
        )

        self.assign_simple_handler("cutting_buds_combo", "flower_buds")
        self.assign_simple_handler("cutting_wound_combo", "wound")
        self.assign_simple_handler(
            "cutting_fungal_comboentry",
            "fungicide",
            editor.UnicodeOrNoneValidator(),
        )
        self.assign_simple_handler(
            "cutting_hormone_comboentry",
            "hormone",
            editor.UnicodeOrNoneValidator(),
        )
        self.assign_simple_handler(
            "cutting_location_comboentry",
            "location",
            editor.UnicodeOrNoneValidator(),
        )
        self.assign_simple_handler(
            "cutting_cover_comboentry",
            "cover",
            editor.UnicodeOrNoneValidator(),
        )
        self.assign_simple_handler("cutting_heat_entry", "bottom_heat_temp")
        self.assign_simple_handler("cutting_heat_unit_combo", "bottom_heat_unit")
        self.assign_simple_handler("cutting_rooted_pct_entry", "rooted_pct")

        self.view.connect("rooted_add_button", "clicked", self.on_rooted_add_clicked)
        self.view.connect(
            "rooted_remove_button", "clicked", self.on_rooted_remove_clicked
        )

    def is_dirty(self):
        return self._dirty

    def set_model_attr(self, field, value, validator: Optional[Any] = None) -> None:
        logger.debug(f"{field} = {value}")
        super().set_model_attr(field, value, validator)
        self._dirty = True
        self.parent_ref().refresh_sensitivity()

    def on_rooted_add_clicked(self, button, *args) -> None:
        """ """
        from bauble.plugins.garden import PropCuttingRooted
        tree = self.view.widgets.rooted_treeview
        rooted = PropCuttingRooted()
        rooted.cutting = self.model  # this lays the database link
        rooted.date = datetime.date.today()
        model = tree.get_model()
        treeiter = model.insert(0, [rooted])
        path = model.get_path(treeiter)
        column = tree.get_column(0)
        tree.set_cursor(path, column, start_editing=True)

    def on_rooted_remove_clicked(self, button, *args) -> None:
        """ """
        tree = self.view.widgets.rooted_treeview
        model, treeiter = tree.get_selection().get_selected()
        if not treeiter:
            return
        rooted = model[treeiter][0]
        rooted.cutting = None  # this removes the database link
        model.remove(treeiter)
        self._dirty = True
        self.parent_ref().refresh_sensitivity()

    def refresh_view(self) -> None:
        # TODO: not so sure. is this a 'refresh', or a 'init' view?
        for widget, attr in list(self.widget_to_field_map.items()):
            value = getattr(self.model, attr)
            self.view.widget_set_value(widget, value)
        rooted_liststore = self.view.widgets.rooted_treeview.get_model()
        rooted_liststore.clear()
        for rooted in self.model.rooted:
            rooted_liststore.append([rooted])


class SeedPresenter(editor.GenericEditorPresenter):

    _dirty: bool
    parent_ref: Any
    session: Any
    propagation: Any
    model: Any
    widget_to_field_map: Any = {
        "seed_pretreatment_textview": "pretreatment",
        "seed_nseeds_entry": "nseeds",
        "seed_sown_entry": "date_sown",
        "seed_container_comboentry": "container",
        "seed_media_comboentry": "media",
        "seed_location_comboentry": "location",
        "seed_mvdfrom_entry": "moved_from",
        "seed_mvdto_entry": "moved_to",
        "seed_germdate_entry": "germ_date",
        "seed_ngerm_entry": "nseedlings",
        "seed_pctgerm_entry": "germ_pct",
        "seed_date_planted_entry": "date_planted",
    }

    def __init__(self, parent, model, view, session) -> None:
        """
        :param model: an instance of class Propagation
        :param view: an instance of PropagationEditorView
        """
        from bauble.plugins.garden.models import PropSeed
        super().__init__(model, view)
        self._dirty = False
        self.parent_ref = weakref.ref(parent)
        self.session = session

        self.propagation = self.model
        if not self.propagation._seed:
            self.propagation._seed = PropSeed()
        self.model = self.model._seed

        # TODO: if % germinated is not entered and nseeds and #
        # germinated are then automatically calculate the % germinated

        self.view.widgets

        def distinct(c):
            return utils.get_distinct_values(c, self.session)

        # TODO: should also setup a completion on the entry
        utils.setup_text_combobox(
            self.view.widgets.seed_media_comboentry, distinct(PropSeed.media)
        )
        utils.setup_text_combobox(
            self.view.widgets.seed_container_comboentry,
            distinct(PropSeed.container),
        )
        utils.setup_text_combobox(
            self.view.widgets.seed_location_comboentry,
            distinct(PropSeed.location),
        )

        self.refresh_view()

        self.assign_simple_handler(
            "seed_pretreatment_textview",
            "pretreatment",
            editor.UnicodeOrNoneValidator(),
        )
        # TODO: this should validate to an integer
        self.assign_simple_handler(
            "seed_nseeds_entry", "nseeds", editor.UnicodeOrNoneValidator()
        )
        self.assign_simple_handler(
            "seed_sown_entry", "date_sown", editor.DateValidator()
        )
        utils.setup_date_button(self.view, "seed_sown_entry", "seed_sown_button")
        self.assign_simple_handler(
            "seed_container_comboentry",
            "container",
            editor.UnicodeOrNoneValidator(),
        )
        self.assign_simple_handler(
            "seed_media_comboentry", "media", editor.UnicodeOrNoneValidator()
        )
        self.assign_simple_handler(
            "seed_location_comboentry",
            "location",
            editor.UnicodeOrNoneValidator(),
        )
        self.assign_simple_handler(
            "seed_mvdfrom_entry", "moved_from", editor.UnicodeOrNoneValidator()
        )
        self.assign_simple_handler(
            "seed_mvdto_entry", "moved_to", editor.UnicodeOrNoneValidator()
        )
        self.assign_simple_handler(
            "seed_germdate_entry", "germ_date", editor.DateValidator()
        )
        utils.setup_date_button(
            self.view, "seed_germdate_entry", "seed_germdate_button"
        )
        self.assign_simple_handler("seed_ngerm_entry", "nseedlings")
        self.assign_simple_handler("seed_pctgerm_entry", "germ_pct")
        self.assign_simple_handler(
            "seed_date_planted_entry", "date_planted", editor.DateValidator()
        )
        utils.setup_date_button(
            self.view, "seed_date_planted_entry", "seed_date_planted_button"
        )

    def is_dirty(self):
        return self._dirty

    def set_model_attr(self, field, value, validator: Optional[Any] = None) -> None:
        # debug('%s = %s' % (field, value))
        super().set_model_attr(field, value, validator)
        self._dirty = True
        self.parent_ref().refresh_sensitivity()

    def refresh_view(self) -> None:
        date_format = prefs.prefs[prefs.date_format_pref]
        for widget, attr in list(self.widget_to_field_map.items()):
            value = getattr(self.model, attr)
            if isinstance(value, datetime.date):
                value = value.strftime(date_format)
            self.view.widget_set_value(widget, value)


class PropagationPresenter(editor.ChildPresenter):
    """PropagationPresenter is extended by SourcePropagationPresenter and
    PropagationEditorPresenter.

    """

    session: Any
    _cutting_presenter: Any
    _seed_presenter: Any
    _dirty: bool
    widget_to_field_map: Any = {
        "prop_type_combo": "prop_type",
        "prop_date_entry": "date",
    }

    def __init__(self, model, view) -> None:
        """
        :param model: an instance of class Propagation
        :param view: an instance of PropagationEditorView
        """
        super().__init__(model, view)
        self.session = get_object_session(model)

        if self.model.prop_type is None:
            view.widgets.prop_details_box.set_visible(False)

        # initialize the propagation type combo and set the initial value
        self.view.connect("prop_type_combo", "changed", self.on_prop_type_changed)
        if self.model.prop_type:
            self.view.widget_set_value("prop_type_combo", self.model.prop_type)

        self._cutting_presenter = CuttingPresenter(
            self, self.model, self.view, self.session
        )
        self._seed_presenter = SeedPresenter(self, self.model, self.view, self.session)

        self.assign_simple_handler("prop_date_entry", "date", editor.DateValidator())
        if self.model.date is None:
            date_str = utils.today_str()
        else:
            format = prefs.prefs[prefs.date_format_pref]
            date_str = self.model.date.strftime(format)
        self.view.widget_set_value(self.view.widgets.prop_date_entry, date_str)

        self._dirty = False
        utils.setup_date_button(self.view, "prop_date_entry", "prop_date_button")

    def on_prop_type_changed(self, combo, *args) -> None:
        it = combo.get_active_iter()
        prop_type = combo.get_model()[it][0]
        if self.model.prop_type != prop_type:
            # only call set_model_attr() if the value is changed to
            # avoid prematuraly calling dirty() and refresh_sensitivity()
            self.set_model_attr("prop_type", prop_type)
        prop_box_map = {
            "Seed": self.view.widgets.seed_box,
            "UnrootedCutting": self.view.widgets.cutting_box,
        }
        for type_, box in list(prop_box_map.items()):
            box.set_visible(prop_type == type_)

        self.view.widgets.prop_details_box.set_visible(True)

        if not self.model.date:
            self.view.widgets.prop_date_entry.emit("changed")

    def is_dirty(self):
        if self.model.prop_type == "UnrootedCutting":
            return self._cutting_presenter.is_dirty() or self._dirty
        elif self.model.prop_type == "Seed":
            return self._seed_presenter.is_dirty() or self._dirty
        else:
            return self._dirty

    def set_model_attr(self, field, value, validator: Optional[Any] = None) -> None:
        """
        Set attributes on the model and update the GUI as expected.
        """
        logging.debug(f"{field} = {value}")
        super().set_model_attr(field, value, validator)
        self._dirty = True
        self.refresh_sensitivity()

    def cleanup(self) -> None:
        self._cutting_presenter.cleanup()
        self._seed_presenter.cleanup()

    def refresh_sensitivity(self) -> None:
        pass

    def refresh_view(self) -> None:
        pass


class SourcePropagationPresenter(PropagationPresenter):
    """
    Presenter for creating a new Propagation for the
    Source.propagation property.  This type of propagation is not
    associated with a Plant.

    :param parent: AccessionEditorPresenter
    :param model:  Propagation instance
    :param view:  AccessionEditorView
    :param session: sqlalchemy.orm.sesssion
    """

    parent_ref: Any
    parent_session: Any
    _dirty: bool

    def __init__(self, parent, model, view, session) -> None:
        self.parent_ref = weakref.ref(parent)
        self.parent_session = session
        try:
            view.widgets.prop_main_box
        except:
            # only add the propagation editor widgets to the view
            # widgets if the widgets haven't yet been added
            filename = os.path.join(
                paths.lib_dir(), "plugins", "garden", "prop_editor.glade"
            )
            view.widgets.builder.add_from_file(filename)
        prop_main_box = view.widgets.prop_main_box
        view.widgets.remove_parent(prop_main_box)
        view.widgets.acc_prop_box_parent.add(prop_main_box)

        # since the view here will be an AccessionEditorView and not a
        # PropagationEditorView then we need to do anything here that
        # PropagationEditorView would do
        view.init_translatable_combo("prop_type_combo", prop_type_values)
        # add None to the prop types which is specific to
        # SourcePropagationPresenter since we might also need to
        # remove the propagation...this will need to be called before
        # the PropagationPresenter.on_prop_type_changed or it won't work
        view.widgets.prop_type_combo.get_model().append([None, ""])

        self._dirty = False
        super().__init__(model, view)

    def on_prop_type_changed(self, combo, *args) -> None:
        """
        Override PropagationPresenter.on_type_changed() to handle the
        None value in the prop_type_combo which is specific the
        SourcePropagationPresenter
        """
        logger.debug("SourcePropagationPresenter.on_prop_type_changed()")
        it = combo.get_active_iter()
        prop_type = combo.get_model()[it][0]
        if not prop_type:
            self.set_model_attr("prop_type", None)
            self.view.widgets.prop_details_box.set_visible(False)
        else:
            super().on_prop_type_changed(combo, *args)
        self._dirty = False

    def set_model_attr(self, attr, value, validator: Optional[Any] = None) -> None:
        logger.debug(f"set_model_attr({attr}, {value})")
        super().set_model_attr(attr, value)
        self._dirty = True
        self.refresh_sensitivity()

    def refresh_sensitivity(self) -> None:
        self.parent_ref().refresh_sensitivity()

    def is_dirty(self):
        return super().is_dirty() or self._dirty


class PropagationEditorPresenter(PropagationPresenter):

    def __init__(self, model, view) -> None:
        """
        :param model: an instance of class Propagation
        :param view: an instance of PropagationEditorView
        """
        super().__init__(model, view)
        # don't allow changing the propagation type if we are editing
        # an existing propagation
        self.view.widgets.prop_type_box.set_sensitive(model in self.session.new)
        self.view.widgets.prop_details_box.set_visible(True)
        self.view.widgets.prop_ok_button.set_sensitive(False)

    def start(self):
        r = self.view.start()
        return r

    def refresh_sensitivity(self) -> None:
        super().refresh_sensitivity()
        sensitive = True

        if utils.get_invalid_columns(self.model):
            sensitive = False

        model = None
        if get_object_session(self.model):
            if self.model.prop_type == "UnrootedCutting":
                model = self.model._cutting
            elif self.model.prop_type == "Seed":
                model = self.model._seed

        if model:
            invalid = utils.get_invalid_columns(model, ["id", "propagation_id"])
            # TODO: highlight the widget with are associated with the
            # columns that have bad values
            if invalid:
                sensitive = False
        else:
            sensitive = False
        self.view.widgets.prop_ok_button.set_sensitive(sensitive)


class PropagationEditor(editor.GenericModelViewPresenterEditor):

    # these have to correspond to the response values in the view
    view: Any
    presenter: Any
    session: Any
    model: Any
    parent: Any
    _return: Any
    RESPONSE_OK_AND_ADD: int = 11
    RESPONSE_NEXT: int = 22
    ok_responses: Any = (RESPONSE_OK_AND_ADD, RESPONSE_NEXT)

    def __init__(self, model, parent: Optional[Any] = None) -> None:
        """
        :param prop_parent: an instance with a propagation relation
        :param model: Propagation instance
        :param parent: the parent widget
        """
        # the view and presenter are created in self.start()
        self.view = None
        self.presenter = None
        super().__init__(model, parent)
        # if mode already has a session then use it, this is unique to
        # the PropagationEditor because so far it is the only editor
        # that dependent on a parent editor and the parent editor's
        # model and session
        sess = object_session(model)
        if sess:
            self.session.close()
            self.session = sess
            self.model = model

        if not parent and bauble.gui:
            parent = bauble.gui.window
        self.parent = parent

        view = PropagationEditorView(parent=self.parent)
        self.presenter = PropagationEditorPresenter(self.model, view)

    def handle_response(self, response, commit: bool = True):
        """
        Handle the response from the presenter and manage database commits or rollbacks.

        :param response: The Gtk response code from the dialog.
        :param commit: Whether to commit the changes to the database.
        :return: True if the operation was successful, False otherwise.
        """
        not_ok_msg = _("Are you sure you want to lose your changes?")
        self._return = None

        try:
            # Clean up the model before processing the response
            self.model.clean()

            if response in (Gtk.ResponseType.OK, *self.ok_responses):
                if self.presenter.is_dirty() and commit:
                    try:
                        self.commit_changes()
                    except Exception:
                        if self.session.in_transaction():
                            self.session.rollback()
                        return False
                self._return = self.model
            elif (
                self.presenter.is_dirty()
                and utils.yes_no_dialog(not_ok_msg)
                or not self.presenter.is_dirty()
            ):
                # Rollback changes if the user confirms losing changes
                if self.session.in_transaction():
                    self.session.rollback()
            else:
                # User canceled the operation without confirming
                return False
        except Exception as e:
            # Fallback for unexpected errors
            msg = _(
                "Unknown error occurred. See the details for more information.\n\n%s"
            ) % utils.xml_safe(str(e))
            logger.error(msg)
            logger.debug(traceback.format_exc())
            utils.message_details_dialog(
                msg, traceback.format_exc(), Gtk.MessageType.ERROR
            )
            if self.session.in_transaction():
                self.session.rollback()
            return False

        return True

    def __del__(self) -> None:
        # override the editor.GenericModelViewPresenterEditor since it
        # will close the session but since we are called with the
        # AccessionEditor's session we don't want that
        #
        # TODO: when should we close the session and not, what about
        # is self.commit is True
        pass

    def start(self, commit: bool = True):
        while True:
            response = self.presenter.start()
            self.presenter.view.save_state()
            if self.handle_response(response, commit):
                break

        # don't close the session since the PropagationEditor depends
        # on an PlantEditor...?
        #
        # self.session.close()  # cleanup session
        self.presenter.cleanup()
        return self._return
