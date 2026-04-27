#
# Copyright 2008-2010 Brett Adams
# Copyright 2015-2017 Mario Frasca <mario@anche.no>.
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
"""
Defines the plant table and handled editing plants
"""
from __future__ import annotations

import logging
import os
import traceback
from gettext import gettext as _
from random import random
from typing import TYPE_CHECKING, Any, Optional

import bauble.db as db
import bauble.paths as paths
import bauble.prefs as prefs
import bauble.utils as utils
import bauble.view as view
from bauble.editor import GenericEditorPresenter as GenericEditorPresenter
from bauble.editor import GenericEditorView as GenericEditorView
from bauble.editor import (
    GenericModelViewPresenterEditor as GenericModelViewPresenterEditor,
)
from bauble.editor import NotesPresenter, PicturesPresenter
from bauble.error import CheckConditionError
from bauble.gtkinit import Gtk
from bauble.plugins.garden.constants import acc_type_values, change_reasons
from bauble.shared import InfoExpander
from bauble.utils import safe_set_text
from bauble.view import (
    Action,
    InfoBox,
    MapInfoExpander,
    PropertiesExpander,
    select_in_search_results,
)

# from sqlalchemy import text
from sqlalchemy import and_, bindparam, func, select

# from sqlalchemy.exc import DBAPIError
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import object_mapper
from sqlalchemy.orm.session import object_session

if TYPE_CHECKING:
    from bauble.plugins.garden.models import Accession, Location


# at module load time
utils._install_css("""
.entry-error { background-color: rgba(255, 235, 235, 1); }
.entry-error:focus { background-color: rgba(255, 217, 217, 1); }
""")



# if TYPE_CHECKING:
#    from .location import Location

logger: Any = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# TODO: might be worthwhile to have a label or textview next to the
# location combo that shows the description of the currently selected
# location

plant_delimiter_key: str = "plant_delimiter"
default_plant_delimiter: str = "."


def edit_callback(plants):
    e = PlantEditor(model=plants[0])
    return e.start() is not None


def branch_callback(plants):
    if plants[0].quantity <= 1:
        msg = _(
            "Not enough plants to split.  A plant should have at least "
            "a quantity of 2 before it can be divided"
        )
        utils.message_dialog(msg, Gtk.MessageType.WARNING)
        return

    e = PlantEditor(model=plants[0], branch_mode=True)
    return e.start() is not None


def remove_callback(plants):
    from bauble.plugins.garden import Plant
    s = ", ".join([str(p) for p in plants])
    msg = _(
        "Are you sure you want to remove the following plants?\n\n%s"
    ) % utils.xml_safe(s)
    if not utils.yes_no_dialog(msg):
        return

    session = db.Session()
    for plant in plants:
        obj = session.get(Plant, plant.id)
        session.delete(obj)
    try:
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


edit_action: Any = Action(
    "plant_edit",
    _("_Edit"),
    callback=edit_callback,
    accelerator="<ctrl>e",
    multiselect=True,
)

branch_action: Any = Action(
    "plant_branch",
    _("_Split"),
    callback=branch_callback,
    accelerator="<ctrl>b",
)

remove_action: Any = Action(
    "plant_remove",
    _("_Delete"),
    callback=remove_callback,
    accelerator="<ctrl>Delete",
    multiselect=True,
)

plant_context_menu: Any = [
    edit_action,
    branch_action,
    remove_action,
]


def get_next_code(acc):
    """
    Return the next available plant code for an accession.

    This function should be specific to the institution.

    If there is an error getting the next code the None is returned.
    """
    from bauble.plugins.garden import Plant

    # auto generate/increment the accession code
    session = db.Session()
    from bauble.plugins.garden.models import Accession

    codes = (
        session.execute(
            select(Plant.code)
            .join(Accession, Plant.accession_id == Accession.id)
            .where(Accession.id == acc.id)
        )
        .scalars()
        .all()
    )
    next = 1
    if codes:
        try:
            next = max([int(code[0]) for code in codes]) + 1
        except Exception as e:
            logger.debug(e)
            return None
    return utils.to_unicode(next)





def is_code_unique(plant, code):
    """
    Return True/False if the code is a unique Plant code for accession.

    This method will also take range values for code that can be passed
    to utils.range_builder().
    """
    from bauble.plugins.garden import Plant

    # if the range builder only creates one number then we assume the
    # code is not a range and so we test against the string version of
    # code
    codes = list(map(utils.to_unicode, utils.range_builder(code)))  # test if a range
    if len(codes) == 1:
        codes = [utils.to_unicode(code)]

    # reference accesssion.id instead of accession_id since
    # setting the accession on the model doesn't set the
    # accession_id until the session is flushed
    session = db.Session()

    stmt = select(func.count()).select_from(
        select(Plant)
        .join(Accession, Plant.accession_id == Accession.id)
        .where(
            and_(
                Accession.id == plant.accession.id,
                Plant.code.in_(bindparam("codes", expanding=True)),
            )
        )
        .subquery()
    )

    count = session.execute(stmt, {"codes": codes}).scalar_one()
    session.close()
    return count == 0


class PlantEditorView(GenericEditorView):

    _tooltips: Any = {
        "plant_code_entry": _(
            "The planting code must be a unique code for "
            "the accession.  You may also use ranges "
            "like 1,2,7 or 1-3 to create multiple "
            "plants."
        ),
        "plant_acc_entry": _(
            "The accession must be selected from the list "
            "of completions.  To add an accession use the "
            "Accession editor."
        ),
        "plant_loc_comboentry": _("The location of the planting in your collection."),
        "plant_acc_type_combo": _(
            "The type of the plant material.\n\n" "Possible values: %s"
        )
        % (", ".join(list(acc_type_values.values()))),
        "plant_loc_add_button": _("Create a new location."),
        "plant_loc_edit_button": _("Edit the selected location."),
        "prop_add_button": _("Create a new propagation record for this plant."),
        "pad_cancel_button": _("Cancel your changes."),
        "pad_ok_button": _("Save your changes."),
        "pad_next_button": _("Save your changes and add another plant."),
        "pad_nextaccession_button": _("Save your changes and add another accession."),
    }

    def __init__(self, parent: Optional[Any] = None) -> None:
        glade_file = os.path.join(
            paths.lib_dir(), "plugins", "garden", "plant_editor.glade"
        )
        super().__init__(glade_file, parent=parent)
        self.widgets.pad_ok_button.set_sensitive(False)
        self.widgets.pad_next_button.set_sensitive(False)

        def acc_cell_data_func(column, renderer, model, treeiter, data=None):
            v = model[treeiter][0]
            renderer.set_property("text", f"{str(v)} ({str(v.species)})")

        self.attach_completion(
            "plant_acc_entry", acc_cell_data_func, minimum_key_length=2
        )
        self.init_translatable_combo("plant_acc_type_combo", acc_type_values)
        self.init_translatable_combo("reason_combo", change_reasons)
        utils.setup_date_button(self, "plant_date_entry", "plant_date_button")
        self.widgets.notebook.set_current_page(0)

    def get_window(self):
        return self.widgets.plant_editor_dialog

    def save_state(self) -> None:
        pass

    def restore_state(self) -> None:
        pass


class PlantEditorPresenter(GenericEditorPresenter):

    session: Any
    _original_accession_id: Any
    _original_code: Any
    upper_quantity_limit: Any
    _original_quantity: Any
    lower_quantity_limit: int
    _dirty: bool
    notes_presenter: Any
    pictures_presenter: Any
    prop_presenter: Any
    initializing: bool
    change: Any
    widget_to_field_map: Any = {
        "plant_code_entry": "code",
        "plant_acc_entry": "accession",
        "plant_loc_comboentry": "location",
        "plant_acc_type_combo": "acc_type",
        "plant_memorial_check": "memorial",
        "plant_quantity_entry": "quantity",
    }

    PROBLEM_DUPLICATE_PLANT_CODE: Any = str(random())
    PROBLEM_INVALID_QUANTITY: Any = str(random())

    def __init__(self, model, view) -> None:
        """
        :param model: should be an instance of Plant class
        :param view: should be an instance of PlantEditorView
        """
        from bauble.plugins.garden.models import PlantChange
        super().__init__(model, view)
        self.create_toolbar()
        self.session = object_session(model)
        self._original_accession_id = self.model.accession_id
        self._original_code = self.model.code

        # if the model is in session.new then it might be a branched
        # plant so don't store it....is this hacky?
        self.upper_quantity_limit = float("inf")
        if model in self.session.new:
            self._original_quantity = None
            self.lower_quantity_limit = 1
        else:
            self._original_quantity = self.model.quantity
            self.lower_quantity_limit = 0
        self._dirty = False

        # set default values for acc_type
        if self.model.id is None and self.model.acc_type is None:
            self.model.acc_type = "Plant"

        notes_parent = self.view.widgets.notes_parent_box
        notes_parent.foreach(notes_parent.remove)
        self.notes_presenter = NotesPresenter(self, "notes", notes_parent)

        pictures_parent = self.view.widgets.pictures_parent_box
        pictures_parent.foreach(pictures_parent.remove)
        self.pictures_presenter = PicturesPresenter(self, "notes", pictures_parent)

        from bauble.plugins.garden.propagation_editor import PropagationTabPresenter

        self.prop_presenter = PropagationTabPresenter(
            self, self.model, self.view, self.session
        )

        # if the PlantEditor has been started with a new plant but
        # the plant is already associated with an accession
        if self.model.accession and not self.model.code:
            code = get_next_code(self.model.accession)
            if code:
                # if get_next_code() returns None then there was an error
                self.set_model_attr("code", code)

        # need to build the ComboBox logic before refreshing the view AND
        # make sure that refreshing the view will not be seen as a change.
        self.initializing = True

        def on_location_select(location):
            if self.initializing:
                return
            self.set_model_attr("location", location)
            if self.change.quantity is None:
                self.change.quantity = self.model.quantity

        from bauble.plugins.garden import init_location_comboentry

        init_location_comboentry(
            self, self.view.widgets.plant_loc_comboentry, on_location_select
        )

        self.refresh_view()  # put model values in view
        self.initializing = False

        self.change = PlantChange()
        self.session.add(self.change)
        self.change.plant = self.model
        self.change.from_location = self.model.location
        self.change.quantity = self.model.quantity

        def on_reason_changed(combo):
            it = combo.get_active_iter()
            self.change.reason = combo.get_model()[it][0]

        sensitive = False
        if self.model not in self.session.new:
            self.view.connect(
                self.view.widgets.reason_combo, "changed", on_reason_changed
            )
            sensitive = True
        self.view.widgets.reason_combo.set_sensitive = sensitive
        self.view.widgets.reason_label.set_sensitive = sensitive

        self.view.connect("plant_date_entry", "changed", self.on_date_entry_changed)

        # assign signal handlers to monitor changes now that the view has
        # been filled in
        def acc_get_completions(text):
            from bauble.plugins.garden.models import Accession

            query = self.session.execute(
                select(Accession)
                .where(Accession.code.like(str(f"{text}%")))
                .order_by(Accession.code)
            ).scalars()
            return query

        def on_select(value):
            self.set_model_attr("accession", value)
            # reset the plant code to check that this is a valid code for the
            # new accession, fixes bug #103946
            self.view.widgets.acc_species_label.set_markup("")
            if value is not None:
                sp_str = self.model.accession.species.str(markup=True)
                self.view.widgets.acc_species_label.set_markup(sp_str)
                self.view.widgets.plant_code_entry.emit("changed")

        self.assign_completions_handler(
            "plant_acc_entry", acc_get_completions, on_select=on_select
        )
        if self.model.accession:
            sp_str = self.model.accession.species.str(markup=True)
        else:
            sp_str = ""
        self.view.widgets.acc_species_label.set_markup(sp_str)

        self.view.connect(
            "plant_code_entry", "changed", self.on_plant_code_entry_changed
        )

        self.assign_simple_handler("plant_acc_type_combo", "acc_type")
        self.assign_simple_handler("plant_memorial_check", "memorial")
        self.view.connect("plant_quantity_entry", "changed", self.on_quantity_changed)
        self.view.connect(
            "plant_loc_add_button",
            "clicked",
            self.on_loc_button_clicked,
            "add",
        )
        self.view.connect(
            "plant_loc_edit_button",
            "clicked",
            self.on_loc_button_clicked,
            "edit",
        )
        if self.model.quantity == 0:
            self.view.widgets.notebook.set_sensitive(False)
            msg = _(
                "This plant is marked with quantity zero. \n"
                "In practice, it is not any more part of the collection. \n"
                "Are you sure you want to edit it anyway?"
            )
            box = None

            def on_response(button, response):
                self.view.remove_box(box)
                if response:
                    self.view.widgets.notebook.set_sensitive(True)

            box = self.view.add_message_box(utils.MESSAGE_BOX_YESNO)
            box.message = msg
            box.on_response = on_response
            self.view.add_box(box)
            box.show()

    def is_dirty(self):
        return (
            self.pictures_presenter.is_dirty()
            or self.notes_presenter.is_dirty()
            or self.prop_presenter.is_dirty()
            or self._dirty
        )

    def on_date_entry_changed(self, entry, *args) -> None:
        self.change.date = entry.set_text

    def on_quantity_changed(self, entry, *args) -> None:
        value = entry.set_text
        try:
            value = int(value)
        except ValueError as e:
            logger.debug(e)
            value = None
        self.set_model_attr("quantity", value)
        if value < self.lower_quantity_limit or value >= self.upper_quantity_limit:
            self.add_problem(self.PROBLEM_INVALID_QUANTITY, entry)
        else:
            self.remove_problem(self.PROBLEM_INVALID_QUANTITY, entry)
        self.refresh_sensitivity()
        if value is None:
            return
        if self._original_quantity:
            self.change.quantity = abs(self._original_quantity - self.model.quantity)
        else:
            self.change.quantity = self.model.quantity
        self.refresh_view()

    def on_plant_code_entry_changed(self, entry, *args) -> None:
        """
        Validates the accession number and the plant code from the editors.
        """
        text = utils.to_unicode(entry.get_text())
        if text == "":
            self.set_model_attr("code", None)
        else:
            self.set_model_attr("code", utils.to_unicode(text))

        if not self.model.accession:
            self.remove_problem(self.PROBLEM_DUPLICATE_PLANT_CODE, entry)
            self.refresh_sensitivity()
            return

        # add a problem if the code is not unique but not if it's the
        # same accession and plant code that we started with when the
        # editor was opened
        if (
            self.model.code is not None
            and not is_code_unique(self.model, self.model.code)
            and not (
                self._original_accession_id == self.model.accession.id
                and self.model.code == self._original_code
            )
        ):

            self.add_problem(self.PROBLEM_DUPLICATE_PLANT_CODE, entry)
            # highlight as invalid
            entry.get_style_context().add_class("entry-error")
        else:
            # remove_problem() won't complain if problem doesn't exist
            self.remove_problem(self.PROBLEM_DUPLICATE_PLANT_CODE, entry)
            entry.get_style_context().remove_class("entry-error")

        self.refresh_sensitivity()

    def refresh_sensitivity(self) -> None:
        logger.debug("refresh_sensitivity()")
        try:
            logger.debug(
                (
                    self.model.accession is not None,
                    self.model.code is not None,
                    self.model.location is not None,
                    self.model.quantity is not None,
                    self.is_dirty(),
                    len(self.problems) == 0,
                )
            )
        except OperationalError as e:
            logger.debug(f"({type(e)}){e}")
            return
        logger.debug(self.problems)

        # TODO: because we don't call refresh_sensitivity() every time a
        # character is entered then the edit button doesn't sensitize
        # properly
        #
        # combo_entry = self.view.widgets.plant_loc_comboentry.get_child()
        # self.view.widgets.plant_loc_edit_button.\
        #     set_sensitive(self.model.location is not None \
        #                       and not self.has_problems(combo_entry))
        sensitive = (
            (
                self.model.accession is not None
                and self.model.code is not None
                and self.model.location is not None
                and self.model.quantity is not None
            )
            and self.is_dirty()
            and len(self.problems) == 0
        )
        self.view.widgets.pad_ok_button.set_sensitive(sensitive)
        self.view.widgets.pad_next_button.set_sensitive(sensitive)
        self.view.widgets.split_planting_button.set_visible = False

    def set_model_attr(self, field, value, validator: Optional[Any] = None) -> None:
        logger.debug(f"set_model_attr({field}, {value})")
        super().set_model_attr(field, value, validator)
        self._dirty = True
        self.refresh_sensitivity()

    def on_loc_button_clicked(self, button, cmd: Optional[Any] = None) -> None:
        from bauble.plugins.garden import LocationEditor as LocationEditor
        location = self.model.location
        combo = self.view.widgets.plant_loc_comboentry
        if cmd == "edit" and location:
            LocationEditor(location, parent=self.view.get_window()).start()
            self.session.refresh(location)
            self.view.widget_set_value(combo, location)
        else:
            editor = LocationEditor(parent=self.view.get_window())
            if editor.start():
                location = self.model.location = editor.presenter.model
                self.session.add(location)
                self.remove_problem(None, combo)
                self.view.widget_set_value(combo, location)
                self.set_model_attr("location", location)

    def refresh_view(self) -> None:
        # TODO: is this really relevant since this editor only creates new
        # plants?  it also won't work while testing, and removing it while
        # testing has no impact on test results.
        if prefs.testing:
            return
        for widget, field in list(self.widget_to_field_map.items()):
            value = getattr(self.model, field)
            self.view.widget_set_value(widget, value)
            logger.debug(f"{widget}: {field} = {value}")

        self.view.widget_set_value(
            "plant_acc_type_combo",
            acc_type_values[self.model.acc_type],
            index=1,
        )
        self.view.widgets.plant_memorial_check.set_inconsistent(False)
        self.view.widgets.plant_memorial_check.set_active(self.model.memorial is True)

        self.refresh_sensitivity()

    def cleanup(self) -> None:
        super().cleanup()
        msg_box_parent = self.view.widgets.message_box_parent
        list(map(msg_box_parent.remove, msg_box_parent.get_children()))
        # the entry is made not editable for branch mode
        self.view.widgets.plant_acc_entry.set_property("editable", True)
        self.view.get_window().set_title(_("Plant Editor"))

    def start(self):
        return self.view.start()


def move_quantity_between_plants(
    from_plant, to_plant, to_plant_change: Optional[Any] = None
) -> None:
    from bauble.plugins.garden.models import PlantChange as PlantChange

    ######################################################
    s = object_session(to_plant)
    if to_plant_change is None:
        to_plant_change = PlantChange()
        s.add(to_plant_change)
    from_plant_change = PlantChange()
    s.add(from_plant_change)
    ######################################################
    from_plant.quantity -= to_plant.quantity
    ######################################################
    to_plant_change.plant = to_plant
    to_plant_change.parent_plant = from_plant
    to_plant_change.quantity = to_plant.quantity
    to_plant_change.to_location = to_plant.location
    to_plant_change.from_location = from_plant.location
    ######################################################
    from_plant_change.plant = from_plant
    from_plant_change.quantity = to_plant.quantity
    from_plant_change.to_location = to_plant.location
    from_plant_change.from_location = from_plant.location


class PlantEditor(GenericModelViewPresenterEditor):

    # these have to correspond to the response values in the view
    branched_plant: Any
    parent: Any
    _committed: Any
    presenter: Any
    _commited: Any
    RESPONSE_NEXT: int = 22
    ok_responses: Any = (RESPONSE_NEXT,)

    def __init__(
        self,
        model: Optional[Any] = None,
        parent: Optional[Any] = None,
        branch_mode: bool = False,
    ) -> None:
        """
        :param model: Plant instance or None
        :param parent: None
        :param branch_mode:
        """
        from bauble.plugins.garden.models import Plant as Plant
        if branch_mode:
            if model is None:
                raise CheckConditionError("branch_mode requires a model")
            elif object_session(model) and model in object_session(model).new:
                raise CheckConditionError(_("cannot split a new plant"))

        if model is None:
            model = Plant()

        self.branched_plant = None
        if branch_mode:
            # we work on 'model', we keep the original at 'branched_plant'.
            self.branched_plant, model = model, model.duplicate(code=None)
            model.quantity = 1

        super().__init__(model, parent)

        if self.branched_plant and self.branched_plant not in self.session:
            # make a copy of the branched plant for this session
            self.branched_plant = self.session.merge(self.branched_plant)

        import bauble

        if not parent and bauble.gui:
            parent = bauble.gui.window
        self.parent = parent
        self._committed = []

        view = PlantEditorView(parent=self.parent)
        self.presenter = PlantEditorPresenter(self.model, view)
        if self.branched_plant:
            self.presenter.upper_quantity_limit = self.branched_plant.quantity

        # set default focus
        if self.model.accession is None:
            view.widgets.plant_acc_entry.grab_focus()
        else:
            view.widgets.plant_code_entry.grab_focus()

    def compute_plant_split_changes(self) -> None:
        move_quantity_between_plants(
            from_plant=self.branched_plant,
            to_plant=self.model,
            to_plant_change=self.presenter.change,
        )

    def commit_changes(self) -> None:
        """ """
        from bauble.plugins.garden.models import Plant as Plant
        from bauble.plugins.garden.models import PlantNote as PlantNote

        codes = utils.range_builder(self.model.code)
        if (
            len(codes) <= 1
            or self.model not in self.session.new
            and not self.branched_plant
        ):
            change = self.presenter.change
            if self.branched_plant:
                self.compute_plant_split_changes()
            elif change.quantity is None or (
                change.quantity == self.model.quantity
                and change.from_location == self.model.location
                and change.quantity == self.presenter._original_quantity
            ):
                # if quantity and location haven't changed, nothing changed.
                utils.delete_or_expunge(change)
                self.model.change = None
            else:
                if self.model.location != change.from_location:
                    # transfer
                    change.to_location = self.model.location
                elif (
                    self.model.quantity > self.presenter._original_quantity
                    and not change.to_location
                ):
                    # additions should use to_location
                    change.to_location = self.model.location
                    change.from_location = None
                else:
                    # removal
                    change.quantity = -change.quantity
            super().commit_changes()
            self._committed.append(self.model)
            return

        # this method will create new plants from self.model even if
        # the plant code is not a range....it's a small price to pay
        plants = []
        mapper = object_mapper(self.model)

        # TODO: precompute the _created and _last_updated attributes
        # in case we have to create lots of plants. it won't be too slow

        # we have to set the properties on the new objects
        # individually since session.merge won't create a new object
        # since the object is already in the session
        for code in codes:
            new_plant = Plant()
            self.session.add(new_plant)

            # TODO: can't we use Plant.duplicate here?
            ignore = ("changes", "notes", "propagations")
            for prop in mapper.iterate_properties:
                if prop.key not in ignore:
                    setattr(new_plant, prop.key, getattr(self.model, prop.key))
            new_plant.code = utils.to_unicode(code)
            new_plant.id = None
            new_plant._created = None
            new_plant._last_updated = None
            plants.append(new_plant)
            for note in self.model.notes:
                new_note = PlantNote()
                for prop in object_mapper(note).iterate_properties:
                    setattr(new_note, prop.key, getattr(note, prop.key))
                new_note.plant = new_plant
        try:
            list(map(self.session.expunge, self.model.notes))
            self.session.expunge(self.model)
            super().commit_changes()
        except:
            self.session.add(self.model)
            raise
        self._committed.extend(plants)

    def handle_response(self, response):
        from bauble.plugins.garden.models import Plant as Plant
        not_ok_msg = _("Are you sure you want to lose your changes?")
        if response == Gtk.ResponseType.OK or response in self.ok_responses:
            if self.presenter.dirty():
                try:
                    self.commit_changes()
                except Exception:
                    if self.session.in_transaction():
                        self.session.rollback()
                    return False

        # Handle rollback or losing change
        elif (
            self.presenter.is_dirty() and utils.yes_no_dialog(not_ok_msg)
        ) or not self.presenter.is_dirty():
            if self.session.in_transaction():
                self.session.rollback()
            return True
        else:
            return False

        # respond to responses
        more_committed = None
        if response == self.RESPONSE_NEXT:
            self.presenter.cleanup()
            e = PlantEditor(Plant(accession=self.model.accession), parent=self.parent)
            more_committed = e.start()

        if more_committed is not None:
            self._committed = [self._committed]
            if isinstance(more_committed, list):
                self._committed.extend(more_committed)
            else:
                self._committed.append(more_committed)

        return True

    def start(self):
        from bauble.plugins.garden import LocationEditor as LocationEditor
        from bauble.plugins.garden.models import Accession as Accession
        from bauble.plugins.garden.models import Location as Location
        sub_editor = None
        from sqlalchemy import func

        count = self.session.scalar(select(func.count()).select_from(Accession))
        if count == 0:
            msg = (
                "You must first add or import at least one Accession into "
                "the database before you can add plants.\n\nWould you like "
                "to open the Accession editor?"
            )
            if utils.yes_no_dialog(msg):
                # cleanup in case we start a new PlantEditor
                self.presenter.cleanup()
                from bauble.plugins.garden.accession_editor import AccessionEditor

                sub_editor = AccessionEditor()
                self._commited = sub_editor.start()
        if self.session.execute(select(func.count()).select_from(Location)) == 0:
            msg = (
                "You must first add or import at least one Location into "
                "the database before you can add plants.\n\nWould you "
                "like to open the Location editor?"
            )
            if utils.yes_no_dialog(msg):
                # cleanup in case we start a new PlantEditor
                self.presenter.cleanup()
                sub_editor = LocationEditor()
                self._commited = sub_editor.start()

        if self.branched_plant:
            # set title if in branch mode
            current_title = self.presenter.view.get_window().get_title()
            new_title = current_title + utils.to_unicode(" - {}".format(_("Split Mode")))
            self.presenter.view.get_window().set_title(new_title)
            message_box_parent = self.presenter.view.widgets.message_box_parent
            list(
                map(
                    message_box_parent.remove,
                    message_box_parent.get_children(),
                )
            )
            msg = _(
                "Splitting from %(plant_code)s.  The quantity will "
                "be subtracted from %(plant_code)s"
            ) % {"plant_code": str(self.branched_plant)}
            box = self.presenter.view.add_message_box(utils.MESSAGE_BOX_INFO)
            box.message = msg
            box.show_all()

            # don't allow editing the accession code in a branched plant
            self.presenter.view.widgets.plant_acc_entry.set_property("editable", False)

        if not sub_editor:
            while True:
                response = self.presenter.start()
                self.presenter.view.save_state()
                if self.handle_response(response):
                    break

        self.session.close()  # cleanup session
        self.presenter.cleanup()
        return self._committed


class GeneralPlantExpander(InfoExpander):
    """
    general expander for the PlantInfoBox
    """

    current_obj: Any

    def __init__(self, widgets) -> None:
        """ """
        super().__init__(_("General"), widgets)
        general_box = self.widgets.general_box
        self.widgets.remove_parent(general_box)
        self.vbox.pack_start(general_box, True, True, 0)
        self.current_obj = None

        def on_acc_code_clicked(*args):
            select_in_search_results(self.current_obj.accession)

        utils.make_label_clickable(self.widgets.acc_code_data, on_acc_code_clicked)

        def on_species_clicked(*args):
            select_in_search_results(self.current_obj.accession.species)

        utils.make_label_clickable(self.widgets.name_data, on_species_clicked)

        def on_location_clicked(*args):
            select_in_search_results(self.current_obj.location)

        utils.make_label_clickable(self.widgets.location_data, on_location_clicked)

    def update(self, row) -> None:
        """ """
        self.current_obj = row
        acc_code = str(row.accession)
        plant_code = str(row)
        head, tail = plant_code[: len(acc_code)], plant_code[len(acc_code) :]

        self.widget_set_value(
            "acc_code_data",
            f"<big>{utils.xml_safe(str(head))}</big>",
            markup=True,
        )
        self.widget_set_value(
            "plant_code_data",
            f"<big>{utils.xml_safe(str(tail))}</big>",
            markup=True,
        )
        self.widget_set_value(
            "name_data",
            row.accession.species_str(markup=True, authors=True),
            markup=True,
        )
        self.widget_set_value("location_data", str(row.location))
        self.widget_set_value("quantity_data", row.quantity)

        status_str = _("Alive")
        if row.quantity <= 0:
            status_str = _("Dead")
        self.widget_set_value("status_data", status_str, False)

        self.widget_set_value("type_data", acc_type_values[row.acc_type], False)

        image_size = Gtk.IconSize.SMALL_TOOLBAR
        icon_name = "dialog-no"
        if row.memorial:
            icon_name = "dialog-yes"
        self.widgets.memorial_image.set_from_icon_name(icon_name, image_size)


class ChangesExpander(InfoExpander):
    """
    ChangesExpander
    """

    table: Any

    def __init__(self, widgets) -> None:
        """ """
        super().__init__(_("Changes"), widgets)
        self.vbox.set_spacing(5)  # Replace self.vbox.props.spacing

        self.table = Gtk.Grid()
        self.vbox.pack_start(self.table, False, False, 0)

        self.table.set_row_spacing(3)  # Replace self.table.props.row_spacing
        self.table.set_column_spacing(5)  # Replace self.table.props.column_spacing

    def update(self, row):
        """ """
        self.table.foreach(self.table.remove)
        if not row.changes:
            return
        len(row.changes)
        date_format = prefs.prefs[prefs.date_format_pref]
        current_row = 0

        for change in sorted(
            row.changes, key=lambda x: (x.date, x._created), reverse=True
        ):
            try:
                seconds, divided_plant = min(
                    [
                        (
                            abs((i.plant._created - change.date).total_seconds()),
                            i.plant,
                        )
                        for i in row.branches
                    ]
                )
                if seconds > 3:
                    divided_plant = None
            except:
                divided_plant = None

            date = change.date.strftime(date_format)
            label = Gtk.Label(label=f"{date}:")
            label.set_alignment(0, 0)
            self.table.attach(label, 0, current_row, 1, 1)
            if change.to_location and change.from_location:
                s = "{quantity} Transferred from {from_loc} to {to}".format(
                    **dict(
                        quantity=change.quantity,
                        from_loc=change.from_location,
                        to=change.to_location,
                    )
                )
            elif change.quantity < 0:
                s = "{quantity} Removed from {location}".format(
                    **dict(quantity=-change.quantity, location=change.from_location)
                )
            elif change.quantity > 0:
                s = "{quantity} Added to {location}".format(
                    **dict(quantity=change.quantity, location=change.to_location)
                )
            else:
                s = f"{change.quantity}: {change.from_location} -> {change.to_location}"
            if change.reason is not None:
                s += f"\n{change_reasons[change.reason]}"
            label = Gtk.Label(label=s)
            label.set_alignment(0, 0.5)
            self.table.attach(label, 1, current_row, 1, 1)
            current_row += 1
            if change.parent_plant:
                s = _("<i>Split from %(plant)s</i>") % dict(
                    plant=utils.xml_safe(change.parent_plant)
                )
                label = Gtk.Label()
                label.set_alignment(0.0, 0.0)
                label.set_markup(s)
                eb = Gtk.EventBox()
                eb.add(label)
                self.table.attach(eb, 1, current_row, 1, 1)

                def on_clicked(widget, event, parent):
                    select_in_search_results(parent)

                utils.make_label_clickable(label, on_clicked, change.parent_plant)
                current_row += 1
            if divided_plant:
                s = _("<i>Split as %(plant)s</i>") % dict(
                    plant=utils.xml_safe(divided_plant)
                )
                label = Gtk.Label()
                label.set_alignment(0.0, 0.0)
                label.set_markup(s)
                eb = Gtk.EventBox()
                eb.add(label)
                self.table.attach(eb, 1, current_row, 1, 1)

                def on_clicked(widget, event, parent):
                    select_in_search_results(parent)

                utils.make_label_clickable(label, on_clicked, divided_plant)
                current_row += 1

        self.vbox.show_all()


def label_size_allocate(widget, rect) -> None:
    widget.set_size_request(rect.width, -1)



class PropagationExpander(InfoExpander):
    """
    Propagation Expander (GTK 3 Compatible)
    """

    def __init__(self, widgets) -> None:
        super().__init__(_("Propagations"), widgets)
        self.vbox.set_spacing(4)

    def update(self, row) -> None:
        """
        Update the UI with propagation data.
        """
        sensitive = bool(row.propagations)  # Enable/disable UI based on data
        self.set_expanded(sensitive)
        self.set_sensitive(sensitive)

        # Remove all existing children safely
        for child in self.vbox.get_children():
            self.vbox.remove(child)

        date_format = prefs.prefs[prefs.date_format_pref]

        for prop in row.propagations:
            # Create horizontal box (h1) containing v1 (date) and v2 (accessions)
            h1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
            self.vbox.pack_start(h1, True, True, 0)

            v1 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            v2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            h1.pack_start(v1, True, True, 0)
            h1.pack_start(v2, True, True, 0)

            # Date Label
            date_lbl = Gtk.Label()
            date_lbl.set_markup(f"<b>{prop.date.strftime(date_format)}</b>")
            date_lbl.set_xalign(0.0)  # Align left
            v1.pack_start(date_lbl, False, False, 0)

            # Accession Labels
            for acc in prop.accessions:
                accession_lbl = Gtk.Label()
                eventbox = Gtk.EventBox()
                eventbox.add(accession_lbl)
                v2.pack_start(eventbox, False, False, 0)
                accession_lbl.set_xalign(0.0)  # Align left
                safe_set_text(accession_lbl, acc.code)

                def on_clicked(widget, event, obj=acc):
                    select_in_search_results(obj)

                utils.make_label_clickable(accession_lbl, on_clicked, acc)

            # Summary Label
            label = Gtk.Label()
            safe_set_text(label, prop.get_summary(partial=2))
            label.set_line_wrap(True)  # Enable text wrapping
            label.set_xalign(0.0)  # Align left
            label.connect("size-allocate", label_size_allocate)
            v2.pack_start(label, False, False, 0)

        self.vbox.show_all()


class PlantInfoBox(InfoBox):
    """
    An InfoBox for a Plants table row.
    """

    widgets: Any
    general: Any
    transfers: Any
    propagations: Any
    links: Any
    mapinfo: Any
    properties_expander: Any

    def __init__(self) -> None:
        """Initialize PlantInfoBox."""
        super().__init__()
        filename = os.path.join(
            paths.lib_dir(), "plugins", "garden", "plant_infobox.glade"
        )
        self.widgets = utils.BuilderWidgets(filename)
        self.general = GeneralPlantExpander(self.widgets)
        self.add_expander(self.general)

        self.transfers = ChangesExpander(self.widgets)
        self.add_expander(self.transfers)

        self.propagations = PropagationExpander(self.widgets)
        self.add_expander(self.propagations)

        self.links = view.LinksExpander("notes")
        self.add_expander(self.links)

        self.mapinfo = MapInfoExpander(self.get_map_extents)
        self.add_expander(self.mapinfo)

        self.properties_expander = PropertiesExpander()
        self.add_expander(self.properties_expander)

    def get_map_extents(self, plant):
        """Get map extents for the given plant."""
        result = []
        try:
            result.append(plant.coords)
        except AttributeError:  # Specify exception type for clarity
            pass
        return result

    def update(self, row) -> None:
        """Update the InfoBox with data from a row."""
        # TODO: don't really need a location expander, could just
        # use a label in the general section
        # loc = self.get_expander("Location")
        # loc.update(row.location)
        #
        # General section
        self.general.update(row)

        # Transfers section
        self.transfers.update(row)

        # Propagations section
        self.propagations.update(row)

        # Links section
        urls = [x for x in [utils.get_urls(note.note) for note in row.notes] if x]
        is_visible = bool(urls)
        self.links.set_visible(is_visible)
        self.links._sep.set_visible(is_visible)
        if is_visible:
            self.links.update(row)

        # Map info
        self.mapinfo.update(row)

        # Properties expander
        self.properties_expander.update(row)
