#
# Copyright 2008-2010 Brett Adams
# Copyright 2014-2015 Mario Frasca <mario@anche.no>.
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
# Family table definition
#
import importlib
import logging
import os
import traceback
import weakref
from gettext import gettext as _
from typing import Any, ClassVar, List, Optional

import bauble
import bauble.btypes as types
import bauble.editor as editor
import bauble.paths as paths
import bauble.pluginmgr as pluginmgr
import bauble.utils as utils
from bauble.db import Base, Serializable, WithNotes, engine, make_note_class
from bauble.gtkinit import Gtk
from bauble.prefs import prefs
from bauble.shared import InfoExpander
from bauble.utils import handle_db_error, safe_set_props
from bauble.view import InfoBox, PropertiesExpander, select_in_search_results

# from sqlalchemy.types import Enum
# from sqlalchemy import text
from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    Unicode,
    UniqueConstraint,
    and_,
    asc,
    delete,
    distinct,
    select,
)
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.hybrid import hybrid_property

# from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship, validates
from sqlalchemy.orm.session import object_session

view: Any = importlib.import_module("bauble.view")
logger: Any = logging.getLogger(__name__)


def edit_callback(families):
    """
    Family context menu callback
    """
    family = families[0]
    return FamilyEditor(model=family).start() is not None


def add_genera_callback(families):
    """
    Callback to add a genus to the first family in the provided list.
    """
    with Session(engine) as session:  # Use SQLAlchemy 2.0 context manager
        family = session.merge(families[0])  # Ensure family is in the session
        genus_instance = get_genus_class()
        genus_editor = get_genus_editor()
        e = genus_editor(model=genus_instance(family=family))
        # The editor decides what to do with the object
        return e.start() is not None


def remove_callback(families):
    """
    The callback function to remove a family from the family context menu.
    """
    family = families[0]
    from bauble.plugins.plants.genus import Genus

    with Session(engine) as session:  # Use SQLAlchemy 2.0 context manager
        family = session.merge(family)  # Ensure the family is in the session

        # Use SQLAlchemy 2.0-style query
        from sqlalchemy import func

        ngen = session.execute(
            select(func.count()).select_from(Genus).filter_by(family_id=family.id)
        ).scalar_one()

        safe_str = utils.xml_safe(str(family))
        if ngen > 0:
            msg = _("The family <i>%(1)s</i> has %(2)s genera." "\n\n") % {
                "1": safe_str,
                "2": ngen,
            } + _("You cannot remove a family with genera.")
            utils.message_dialog(msg, type=Gtk.MessageType.WARNING)
            return
        else:
            msg = _("Are you sure you want to remove the family <i>%s</i>?") % safe_str

        if not utils.yes_no_dialog(msg):
            return

        try:
            # Use SQLAlchemy 2.0-style query for deletion
            obj = session.execute(select(Family).filter_by(id=family.id)).scalar_one()
            session.delete(obj)
            if session.in_transaction():
                session.commit()
        except Exception as e:
            msg = _("Could not delete.\n\n%s") % utils.xml_safe(str(e))
            utils.message_details_dialog(
                msg, traceback.format_exc(), type=Gtk.MessageType.ERROR
            )

    return True


edit_action: Any = view.Action(
    name="family_edit", label=_("_Edit"), callback=edit_callback, accelerator="<ctrl>e"
)

add_species_action: Any = view.Action(
    name="family_genus_add",
    label=_("_Add genus"),
    callback=add_genera_callback,
    accelerator="<ctrl>k",
)
remove_action: Any = view.Action(
    name="family_remove",
    label=_("_Delete"),
    callback=remove_callback,
    accelerator="<ctrl>Delete",
    multiselect=True,
)

family_context_menu: Any = [edit_action, add_species_action, remove_action]


#
# Family
#
def compute_serializable_fields(cls, session, keys):
    result = {"family": None}

    family_keys = {"epithet": keys["family"]}
    result["family"] = Family.retrieve_or_create(session, family_keys, create=False)

    return result


class FamilySynonym(Base):
    """
    :Table name: family_synonyms

    :Columns:
        *family_id*:

        *synonyms_id*:

    :Properties:
        *synonyms*:

        *family*:
    """

    __tablename__: str = "family_synonym"

    # columns
    id: Mapped[int] = mapped_column(primary_key=True, nullable=False)
    family_id: Mapped[int] = mapped_column(ForeignKey("family.id"), nullable=False)
    synonym_id: Mapped[int] = mapped_column(
        ForeignKey("family.id"), nullable=False, unique=True
    )

    # Relationships
    synonym: Mapped["Family"] = relationship(
        "Family",
        primaryjoin="FamilySynonym.synonym_id==Family.id",
    )
    #                       back_populates='synonyms_relationship')  # Renamed for clarity

    family: Mapped["Family"] = relationship(
        "Family",
        back_populates="_synonyms",
        primaryjoin="FamilySynonym.family_id==Family.id",
    )

    def __init__(self, synonym: Optional["Family"] = None, **kwargs) -> None:
        # it is necessary that the first argument here be synonym for
        # the Family.synonyms association_proxy to work
        self.synonym = synonym
        super().__init__(**kwargs)

    def __str__(self) -> str:
        return Family.str(self.synonym)


class Family(Base, Serializable, WithNotes):
    """
    :Table name: family

    :Columns:
        *family*:
            The name of the family. Required.

        *qualifier*:
            The family qualifier.

            Possible values:
                * s. lat.: aggregrate family (senso lato)

                * s. str.: segregate family (senso stricto)

                * '': the empty string

    :Properties:
        *synonyms*:
            An association to _synonyms that will automatically
            convert a Family object and create the synonym.

    :Constraints:
        The family table has a unique constraint on family/qualifier.
    """

    qualifier: Any
    synonyms: Any
    __tablename__: str = "family"
    __table_args__: Any = (UniqueConstraint("epithet"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False, autoincrement=True)
    rank: str = "familia"
    link_keys: Any = ["accepted"]

    @validates("epithet", "author")
    def validate_stripping(self, key, value):
        if value is None:
            return None
        return value.strip()

    @property
    def cites(self):
        """the cites status of this taxon, or None"""

        cites_notes = [
            i.note for i in self.notes if i.category and i.category.upper() == "CITES"
        ]
        if not cites_notes:
            return None
        return cites_notes[0]

    # columns
    epithet: Mapped[str] = mapped_column(String(45), nullable=False, index=True)
    # family = synonym("epithet")

    # Use hybrid property for the 'family' synonym
    @hybrid_property
    def family(self):
        return self.epithet

    @family.setter
    def family(self, value):
        self.epithet = value

    @family.expression
    def family(cls):
        return cls.epithet

    # use '' instead of None so that the constraints will work propertly
    author: Mapped[Optional[str]] = mapped_column(Unicode(255), default="", nullable=True)

    # we use the blank string here instead of None so that the
    # contraints will work properly,
    qualifier: Mapped[Optional[str]] = mapped_column(
        types.Enum(values=["s. lat.", "s. str.", ""], omit_aliases=False), default="", nullable=True
    )
    order_by: ClassVar[list[Any]] = [asc(epithet), asc(qualifier)]

    # relations
    # `genera` relation is defined outside of `Family` class definition
    synonyms = association_proxy("_synonyms", "synonym")

    _synonyms: Mapped[List["FamilySynonym"]] = relationship(
        "FamilySynonym",
        primaryjoin="Family.id==FamilySynonym.family_id",
        cascade="all, delete-orphan",
        uselist=True,
        back_populates="family",
        single_parent=True,
    )

    # this is a dummy relation, it is only here to make cascading work
    # correctly and to ensure that all synonyms related to this family
    # get deleted if this family gets deleted
    # synonyms_relationship = relationship('FamilySynonym',
    #                 primaryjoin='Family.id==FamilySynonym.synonym_id',
    #                 cascade='all, delete-orphan', uselist=True, single_parent=True)

    def __repr__(self) -> str:
        return Family.str(self)

    @staticmethod
    def str(family, qualifier: bool = False, author: bool = False):
        # author is not in the model but it really should
        if family.epithet is None:
            return Base.__repr__(family)
        else:
            return " ".join(
                [s for s in [family.epithet, family.qualifier] if s not in (None, "")]
            )

    @property
    def accepted(self) -> Any:
        "Name that should be used if name of self should be rejected"
        session = object_session(self)
        if not session:
            logger.warning("family:accepted - object not in session")
            return None
        syn = (
            session.execute(
                select(FamilySynonym).where(FamilySynonym.synonym_id == self.id)
            )
            .scalars()
            .first()
        )
        accepted = syn and syn.family
        return accepted

    @accepted.setter
    def accepted(self, value):
        "Name that should be used if name of self should be rejected"
        assert isinstance(value, self.__class__)
        if self in value.synonyms:
            return
        # remove any previous `accepted` link
        session = object_session(self)
        if not session:
            logger.warning("family:accepted.setter - object not in session")
            return
        session.execute(
            delete(FamilySynonym).where(FamilySynonym.synonym_id == self.id)
        )
        if session.in_transaction():
            session.commit()
        value.synonyms.append(self)

    def has_accessions(self):
        """true if family is linked to at least one accession"""

        return False

    def as_dict(self, recurse: bool = True):
        result = Serializable.as_dict(self)
        if "qualifier" in result:
            del result["qualifier"]
        result["object"] = "taxon"
        result["rank"] = self.rank
        result["epithet"] = self.epithet
        if recurse and self.accepted is not None:
            result["accepted"] = self.accepted.as_dict(recurse=False)
        return result

    @classmethod
    def retrieve(cls, session, keys):
        try:
            return (
                session.execute(select(cls).where(cls.epithet == keys["epithet"]))
                .scalars()
                .one()
            )
        except:
            return None

    @classmethod
    def correct_field_names(cls, keys) -> None:
        pass

    # def top_level_count(self):
    #     genera = {g for g in self.genera if g.species}
    #     species = [s for g in genera for s in g.species]
    #     accessions = [a for s in species for a in s.accessions]
    #     plants = [p for a in accessions for p in a.plants]
    #     return {
    #         (1, "Families"): {self.id},
    #         (2, "Genera"): genera,
    #         (3, "Species"): set(species),
    #         (4, "Accessions"): len(accessions),
    #         (5, "Plantings"): len(plants),
    #         (6, "Living plants"): sum(p.quantity for p in plants),
    #         (7, "Locations"): {p.location.id for p in plants},
    #         (8, "Sources"): {
    #             a.source.source_detail.id
    #             for a in accessions
    #             if a.source and a.source.source_detail
    #         },
    #     }

    def top_level_count(self):
        # Step 1: Filter genera that have species
        genera = set()
        for g in self.genera:
            if g.species:
                genera.add(g)

        # Step 2: Collect all species from the filtered genera
        species = []
        for g in genera:
            species.extend(g.species)

        # Step 3: Collect all accessions from the species
        accessions = []
        for s in species:
            accessions.extend(s.accessions)

        # Step 4: Collect all plants from the accessions
        plants = []
        for a in accessions:
            plants.extend(a.plants)

        # Step 5: Calculate the metrics
        result = {
            (1, "Families"): {self.id},
            (2, "Genera"): genera,
            (3, "Species"): set(species),
            (4, "Accessions"): len(accessions),
            (5, "Plantings"): len(plants),
            (6, "Living plants"): sum(p.quantity for p in plants),
            (7, "Locations"): {p.location.id for p in plants},
            (8, "Sources"): {
                a.source.source_detail.id
                for a in accessions
                if a.source and a.source.source_detail
            },
        }

        return result


# defining the latin alias to the class.
Familia = Family

FamilyNote: Any = make_note_class("Family", Family, compute_serializable_fields)
Family.notes = relationship(
    "FamilyNote",
    back_populates="family",
    cascade="all, delete-orphan",
    single_parent=True,
    uselist=True,
)


# Use lazy import where Genus is needed
def get_genus_class():
    from bauble.plugins.plants.genus import Genus

    return Genus


def get_genus_editor():
    from bauble.plugins.plants.genus import GenusEditor

    return GenusEditor


# Defer import of Species
def get_species():
    from bauble.plugins.plants.species_model import Species

    return Species


#
# late bindings
#

# only now that we have `Genus` can we define the sorted `genera` in the
# `Family` class.
Family.genera = (
    relationship(
        "Genus",
        order_by=asc(get_genus_class().genus),
        back_populates="family",
        cascade="all, delete-orphan",
        single_parent=True,
        uselist=True,
    )
    or []
)


class FamilyEditorView(editor.GenericEditorView):

    syn_expanded_pref: str = "editor.family.synonyms.expanded"

    _tooltips: Any = {
        "fam_family_entry": _("The family name."),
        "fam_qualifier_combo": _(
            "The family qualifier helps to remove "
            "ambiguities that might be associated with "
            "this family name."
        ),
        "fam_syn_frame": _(
            "A list of synonyms for this family.\n\nTo add a "
            "synonym enter a family name and select one from "
            "the list of completions.  Then click Add to add "
            "it to the list of synonyms."
        ),
        "fam_cancel_button": _("Cancel your changes."),
        "fam_ok_button": _("Save your changes."),
        "fam_ok_and_add_button": _(
            "Save your changes and add a " "genus to this family."
        ),
        "fam_next_button": _("Save your changes and add another " "family."),
    }

    def __init__(self, parent: Optional[Any] = None) -> None:
        filename = os.path.join(
            paths.lib_dir(), "plugins", "plants", "family_editor.glade"
        )
        super().__init__(filename, parent=parent)
        self.attach_completion("fam_syn_entry")
        self.set_accept_buttons_sensitive(False)
        self.widgets.notebook.set_current_page(0)
        self.restore_state()

    def get_window(self):
        return self.widgets.family_dialog

    def save_state(self) -> None:
        # prefs[self.syn_expanded_pref] = \
        # self.widgets.fam_syn_expander.get_expanded()
        pass

    def restore_state(self) -> None:
        # expanded = prefs.get(self.syn_expanded_pref, True)
        # self.widgets.fam_syn_expander.set_expanded(expanded)
        pass

    def set_accept_buttons_sensitive(self, sensitive) -> None:
        self.widgets.fam_ok_button.set_sensitive(sensitive)
        self.widgets.fam_ok_and_add_button.set_sensitive(sensitive)
        self.widgets.fam_next_button.set_sensitive(sensitive)

    def start(self):
        return self.get_window().run()


class FamilyEditorPresenter(editor.GenericEditorPresenter):

    session: Any
    synonyms_presenter: Any
    notes_presenter: Any
    _dirty: bool
    widget_to_field_map: Any = {
        "fam_family_entry": "family",
        "fam_qualifier_combo": "qualifier",
    }

    def __init__(self, model, view) -> None:
        """
        :param model: should be an instance of class Family
        :param view: should be an instance of FamilyEditorView
        """
        super().__init__(model, view)
        self.create_toolbar()
        self.session = object_session(model)

        # initialize widgets
        self.init_enum_combo("fam_qualifier_combo", "qualifier")
        self.synonyms_presenter = SynonymsPresenter(self)
        self.refresh_view()  # put model values in view

        # connect signals
        self.assign_simple_handler(
            "fam_family_entry", "epithet", editor.UnicodeOrNoneValidator()
        )
        self.assign_simple_handler(
            "fam_qualifier_combo",
            "qualifier",
            editor.UnicodeOrEmptyValidator(),
        )

        notes_parent = self.view.widgets.notes_parent_box
        notes_parent.foreach(notes_parent.remove)
        self.notes_presenter = editor.NotesPresenter(self, "notes", notes_parent)

        if self.model not in self.session.new:
            self.view.widgets.fam_ok_and_add_button.set_sensitive(True)

        self.view.widgets.fam_family_entry.connect(
            "focus-out-event", self.on_family_name_focus_out
        )

        # for each widget register a signal handler to be notified when the
        # value in the widget changes, that way we can do things like sensitize
        # the ok button
        self._dirty = False

    def on_family_name_focus_out(self, widget, event) -> None:
        """Triggered when the family name text box loses focus."""
        # Check if the entered family name exists in the database
        family_name = widget.get_text().strip()
        family = (
            self.session.execute(select(Family).where(Family.epithet == family_name))
            .scalars()
            .first()
        )

        if family_name:
            # If family is found, update the model and refresh synonyms view
            if family:
                family._synonyms = (
                    self.session.execute(select(FamilySynonym))
                    .scalars()
                    .join(Family, FamilySynonym.synonym_id == Family.id)
                    .where(FamilySynonym.family_id == family.id)
                    .all()
                )
                # Set the model to the retrieved family
                self.synonyms_presenter.model = family
                # Refresh the synonyms view with the current list of synonyms
                self.synonyms_presenter.refresh_view()
            else:
                # Clear the synonyms if no family is found
                self.synonyms_presenter.clear_view()

    def refresh_sensitivity(self) -> None:
        # TODO: check widgets for problems
        sensitive = False
        if self.dirty() and self.model.epithet:
            sensitive = True
        self.view.set_accept_buttons_sensitive(sensitive)

    def set_model_attr(self, field, value, validator: Optional[Any] = None) -> None:
        # debug('set_model_attr(%s, %s)' % (field, value))
        super().set_model_attr(field, value, validator)
        self._dirty = True
        self.refresh_sensitivity()

    def dirty(self):
        return (
            self._dirty
            or self.synonyms_presenter.dirty()
            or self.notes_presenter.dirty()
        )

    def refresh_view(self) -> None:
        # Refresh each widget associated with the Family model fields
        for widget, field in list(self.widget_to_field_map.items()):
            value = getattr(self.model, field, None)
            self.view.widget_set_value(widget, value)

    def cleanup(self) -> None:
        super().cleanup()
        self.synonyms_presenter.cleanup()
        self.notes_presenter.cleanup()

    def start(self):
        r = self.view.start()
        return r


class SynonymsPresenter(editor.GenericEditorPresenter):

    parent_ref: Any
    session: Any
    synonyms_to_add: Any
    _selected: Any
    _dirty: bool
    treeview: Any
    PROBLEM_INVALID_SYNONYM: int = 1

    def __init__(self, parent) -> None:
        """
        :param parent: FamilyEditorPresenter
        """
        self.parent_ref = weakref.ref(parent)
        super().__init__(self.parent_ref().model, self.parent_ref().view)
        self.session = self.parent_ref().session
        safe_set_props(self.view.widgets.fam_syn_entry, "text", "")
        self.init_treeview()

        # List to track new synonyms for addition to the database
        self.synonyms_to_add = []

        def fam_get_completions(text):
            query = self.session.execute(
                select(Family)
                .where(
                    and_(
                        Family.epithet.like(f"{text}%"),
                        Family.id != self.model.id,
                    )
                )
                .order_by(Family.epithet)
            ).scalars()
            return query

        # Populate initial synonym list in the view
        self.refresh_view()
        self._selected = None

        def on_select(value):
            # don't set anything in the model, just set self._selected
            sensitive = True
            if value is None:
                sensitive = False
            self.view.widgets.fam_syn_add_button.set_sensitive(sensitive)
            self._selected = value

        self.assign_completions_handler(
            "fam_syn_entry", fam_get_completions, on_select=on_select
        )
        self.view.connect("fam_syn_add_button", "clicked", self.on_add_button_clicked)
        self.view.connect(
            "fam_syn_remove_button", "clicked", self.on_remove_button_clicked
        )
        # Connect text entry box to the on_text_changed handler
        self.view.widgets.fam_syn_entry.connect("changed", self.on_text_changed)

        self._dirty = False

    def on_text_changed(self, entry) -> None:
        """Enable the 'Add' button if the entered text is unique and valid."""
        text = entry.get_text().strip()
        family = self.parent_ref().model

        # Gather current family name, existing synonyms, and new synonyms to be added
        family_name = family.epithet
        existing_synonyms = [syn.synonym.epithet for syn in family._synonyms]
        new_synonyms = [syn.epithet for syn in self.synonyms_to_add]

        # Check if the text is unique and valid
        is_not_family_name = text != family_name
        is_not_existing_synonym = text not in existing_synonyms
        is_not_new_synonym = text not in new_synonyms
        is_not_empty = bool(text)

        # Enable "Add" button only if all conditions are met
        if (
            is_not_empty
            and is_not_family_name
            and is_not_existing_synonym
            and is_not_new_synonym
        ):
            # No issues found; make sure the Add button is enabled
            self.remove_problem(self.PROBLEM_DUPLICATE, entry)
            self.view.widgets.fam_syn_add_button.set_sensitive(True)
        else:
            # If there's an issue, mark it as a problem and disable the Add button
            self.add_problem(self.PROBLEM_DUPLICATE, entry)
            self.view.widgets.fam_syn_add_button.set_sensitive(False)

    def dirty(self):
        return self._dirty

    def init_treeview(self) -> None:
        """
        initialize the Gtk.TreeView
        """
        self.treeview = self.view.widgets.fam_syn_treeview
        # remove any columns that were setup previous, this became a
        # problem when we starting reusing the glade files with
        # utils.BuilderLoader, the right way to do this would be to
        # create the columns in glade instead of here
        for col in self.treeview.get_columns():
            self.treeview.remove_column(col)

        def _syn_data_func(column, cell, model, iter, data=None):
            v = model[iter][0]
            cell.set_property("text", str(v))
            # just added so change the background color to indicate it's new
            if v.id is None:
                cell.set_property("foreground", "blue")
            else:
                cell.set_property("foreground", None)

        cell = Gtk.CellRendererText()
        col = Gtk.TreeViewColumn("Synonym", cell)
        col.set_cell_data_func(cell, _syn_data_func)
        self.treeview.append_column(col)

        tree_model = Gtk.ListStore(object)
        for syn in self.model._synonyms:
            tree_model.append([syn])
        self.treeview.set_model(tree_model)
        self.view.connect(self.treeview, "cursor-changed", self.on_tree_cursor_changed)

    def on_tree_cursor_changed(self, tree, data: Optional[Any] = None) -> None:
        """ """
        path, column = tree.get_cursor()
        self.view.widgets.fam_syn_remove_button.set_sensitive(True)

    def clear_view(self) -> None:
        """Clears the synonyms list in the tree view."""
        tree_model = self.treeview.get_model()
        tree_model.clear()

    def refresh_view(self) -> None:
        """Refresh the synonyms tree view with the current list of synonyms."""
        # Clear the current contents of the treeview model
        tree_model = self.treeview.get_model()
        tree_model.clear()

        # Add each synonym of the family to the treeview
        for synonym_entry in self.model._synonyms:
            synonym_name = synonym_entry.synonym.epithet
            tree_model.append([synonym_name])

    def on_add_button_clicked(self, button, data: Optional[Any] = None) -> None:
        """
        Adds the synonym from the synonym entry to the list of synonyms for this family.
        """
        if not self._selected or self._selected in [
            syn.synonym for syn in self.model._synonyms
        ]:
            utils.message_dialog(
                "This synonym already exists or is invalid.",
                type=Gtk.MessageType.WARNING,
            )
            return

        # Create new FamilySynonym association
        syn = FamilySynonym(family=self.model, synonym=self._selected)
        self.model._synonyms.append(syn)

        # Update the tree view with the new synonym
        tree_model = self.treeview.get_model()
        tree_model.append([self._selected.epithet])  # Display the epithet
        # tree_model.append([syn])

        # Clear selection and entry field
        self._selected = None
        entry = self.view.widgets.fam_syn_entry
        safe_set_props(entry, "text", "")
        entry.set_position(-1)
        self.view.widgets.fam_syn_add_button.set_sensitive(False)

        # Mark presenter as dirty to indicate unsaved changes
        self._dirty = True
        self.parent_ref().refresh_sensitivity()

    def on_remove_button_clicked(self, button, data: Optional[Any] = None) -> None:
        """
        Removes the currently selected synonym from the list of synonyms for this family.
        """
        tree = self.view.widgets.fam_syn_treeview
        path, col = tree.get_cursor()
        if path is None:
            return

        tree_model = tree.get_model()
        value = tree_model[tree_model.get_iter(path)][0]
        #        debug('%s: %s' % (value, type(value)))
        s = Family.str(value.synonym)
        msg = (
            f"Are you sure you want to remove {s} as a synonym to the "
            "current family?\n\n<i>Note: This will not remove the family "
            f"{s} from the database.</i>"
        )
        if utils.yes_no_dialog(msg, parent=self.view.get_window()):
            # Remove synonym from database and model
            self.model._synonyms.remove(value)
            tree_model.remove(tree_model.get_iter(path))
            utils.delete_or_expunge(value)
            self.session.flush([value])
            self._dirty = True
            self.refresh_sensitivity()


class FamilyEditor(editor.GenericModelViewPresenterEditor):

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
        :param model: Family instance or None
        :param parent: the parent window or None
        """
        if model is None:
            model = Family()
        super().__init__(model, parent)
        if not parent and bauble.gui:
            parent = bauble.gui.window
        self.parent = parent
        self._committed = []

        view = FamilyEditorView(parent=self.parent)
        self.presenter = FamilyEditorPresenter(self.model, view)

    def handle_response(self, response):
        """
        @return: return a list if we want to tell start() to close the editor,
        the list should either be empty or the list of committed values, return
        None if we want to keep editing
        """
        try:
            genus_editor = get_genus_editor()
            not_ok_msg = "Are you sure you want to lose your changes?"
            if response == Gtk.ResponseType.OK or response in self.ok_responses:
                if self.presenter.dirty():
                    self.commit_changes()
                    self._committed.append(self.model)

            elif (
                self.presenter.dirty() and utils.yes_no_dialog(not_ok_msg)
            ) or not self.presenter.dirty():
                if self.session.in_transaction():
                    self.session.rollback()
                return True
            else:
                return False

            # respond to responses
            more_committed = None
            if response == self.RESPONSE_NEXT:
                self.presenter.cleanup()
                e = FamilyEditor(parent=self.parent)
                more_committed = e.start()
            elif response == self.RESPONSE_OK_AND_ADD:
                genus_instance = get_genus_class()
                e = genus_editor(genus_instance(family=self.model), self.parent)
                more_committed = e.start()

            if more_committed is not None:
                if isinstance(more_committed, list):
                    self._committed.extend(more_committed)
                else:
                    self._committed.append(more_committed)

            return True

        except DBAPIError as db_err:
            handle_db_error(db_err, context=_("committing changes"))
            return False

        except Exception as exc:
            handle_db_error(exc, context=_("unknown error during commit"))
            return False

    def start(self):
        while True:
            response = self.presenter.start()
            self.presenter.view.save_state()
            if self.handle_response(response):
                break
        self.presenter.cleanup()
        self.session.close()  # cleanup session
        return self._committed


#
# Family infobox
#


class GeneralFamilyExpander(InfoExpander):
    """
    generic information about an family like number of genus, species,
    accessions and plants
    """

    current_obj: Any

    def __init__(self, widgets) -> None:
        """

        Arguments:
        - `widgets`:
        """
        InfoExpander.__init__(self, _("General"), widgets)
        general_box = self.widgets.fam_general_box
        self.widgets.remove_parent(general_box)
        self.vbox.pack_start(general_box, True, True, 0)

        def on_ngen_clicked(*args):
            f = self.current_obj
            cmd = f'genus where family.epithet="{f.epithet}" and family.qualifier="{f.qualifier}"'
            bauble.gui.send_command(cmd)

        utils.make_label_clickable(self.widgets.fam_ngen_data, on_ngen_clicked)

        def on_nsp_clicked(*args):
            f = self.current_obj
            cmd = (
                f'species where genus.family.epithet="{f.epithet}" '
                f'and genus.family.qualifier="{f.qualifier}"'
            )
            bauble.gui.send_command(cmd)

        utils.make_label_clickable(self.widgets.fam_nsp_data, on_nsp_clicked)

        def on_nacc_clicked(*args):
            f = self.current_obj
            cmd = (
                f'accession where species.genus.family.epithet="{f.epithet}" '
                f'and species.genus.family.qualifier="{f.qualifier}"'
            )
            bauble.gui.send_command(cmd)

        utils.make_label_clickable(self.widgets.fam_nacc_data, on_nacc_clicked)

        def on_nplants_clicked(*args):
            f = self.current_obj
            cmd = (
                f'plant where accession.species.genus.family.epithet="{f.epithet}" '
                f'and accession.species.genus.family.qualifier="{f.qualifier}"'
            )
            bauble.gui.send_command(cmd)

        utils.make_label_clickable(self.widgets.fam_nplants_data, on_nplants_clicked)

    def update(self, row) -> None:
        """
        update the expander

        :param row: the row to get the values from
        """
        genus_instance = get_genus_class()
        species = get_species()

        self.current_obj = row
        self.widget_set_value("fam_name_data", f"<big>{row}</big>", markup=True)
        session = object_session(row)
        # get the number of genera
        from sqlalchemy import func

        ngen = session.execute(
            select(func.count())
            .select_from(genus_instance)
            .where(genus_instance.family_id == row.id)
        ).scalar_one()
        self.widget_set_value("fam_ngen_data", ngen)

        # get the number of species
        nsp = session.execute(
            select(func.count())
            .select_from(species)
            .join(genus_instance, species.genus_id == genus_instance.id)
            .where(genus_instance.family_id == row.id)
        ).scalar_one()

        if nsp == 0:
            self.widget_set_value("fam_nsp_data", 0)
        else:
            species = get_species()
            ngen_in_sp = len(
                session.execute(
                    select(distinct(species.genus_id))
                    .join(genus_instance, species.genus_id == genus_instance.id)
                    .join(Family, genus_instance.family_id == Family.id)
                    .where(Family.id == row.id)
                )
                .scalars()
                .all()
            )
            self.widget_set_value("fam_nsp_data", f"{nsp} in {ngen_in_sp} genera")

        # stop here if no GardenPlugin
        if "GardenPlugin" not in pluginmgr.plugins:
            return

        # get the number of accessions in the family
        from bauble.plugins.garden.models import Accession, Plant

        nacc = session.execute(
            select(func.count())
            .select_from(Accession)
            .join(species, Accession.species_id == species.id)
            .join(genus_instance, species.genus_id == genus_instance.id)
            .join(Family, genus_instance.family_id == Family.id)
            .where(Family.id == row.id)
        ).scalar_one()
        if nacc == 0:
            self.widget_set_value("fam_nacc_data", nacc)
        else:
            species = get_species()
            nsp_in_acc = len(
                session.execute(
                    select(distinct(Accession.species_id))
                    .join(species, Accession.species_id == species.id)
                    .join(genus_instance, species.genus_id == genus_instance.id)
                    .join(Family, genus_instance.family_id == Family.id)
                    .where(Family.id == row.id)
                )
                .scalars()
                .all()
            )
            self.widget_set_value("fam_nacc_data", f"{nacc} in {nsp_in_acc} species")

        # get the number of plants in the family
        nplants = session.execute(
            select(func.count())
            .select_from(Plant)
            .join(Accession, Plant.accession_id == Accession.id)
            .join(species, Accession.species_id == species.id)
            .join(genus_instance, species.genus_id == genus_instance.id)
            .join(Family, genus_instance.family_id == Family.id)
            .where(Family.id == row.id)
        ).scalar_one()
        if nplants == 0:
            self.widget_set_value("fam_nplants_data", nplants)
        else:
            species = get_species()
            nacc_in_plants = len(
                session.execute(
                    select(distinct(Plant.accession_id))
                    .join(Accession, Plant.accession_id == Accession.id)
                    .join(species, Accession.species_id == species.id)
                    .join(genus_instance, species.genus_id == genus_instance.id)
                    .join(Family, genus_instance.family_id == Family.id)
                    .where(Family.id == row.id)
                )
                .scalars()
                .all()
            )
            self.widget_set_value(
                "fam_nplants_data",
                f"{nplants} in {nacc_in_plants} accessions",
            )


class SynonymsExpander(InfoExpander):

    expanded_pref: str = "infobox.family.synonyms.expanded"

    def __init__(self, widgets) -> None:
        InfoExpander.__init__(self, _("Synonyms"), widgets)
        synonyms_box = self.widgets.fam_synonyms_box
        self.widgets.remove_parent(synonyms_box)
        self.vbox.pack_start(synonyms_box, True, True, 0)

    def update(self, row):
        """
        update the expander

        :param row: the row to get thevalues from
        """
        syn_box = self.widgets.fam_synonyms_box
        # remove old labels
        syn_box.foreach(syn_box.remove)
        # use True comparison in case the preference isn't set
        self.set_expanded(prefs[self.expanded_pref] is True)
        logger.debug(
            f"family {row} is synonym of {row.accepted} and has synonyms {row.synonyms}"
        )
        self.set_label(_("Synonyms"))  # reset default value
        if row.accepted is not None:
            self.set_label(_("Accepted name"))

            def on_clicked(l, e, syn):
                return select_in_search_results(syn)

            # create clickable label that will select the synonym
            # in the search results
            box = Gtk.EventBox()
            label = Gtk.Label()
            label.set_alignment(0, 0.5)
            label.set_markup(Family.str(row.accepted, author=True))
            box.add(label)
            utils.make_label_clickable(label, on_clicked, row.accepted)
            syn_box.pack_start(box, False, False, 0)
            self.show_all()
            self.set_sensitive(True)
        elif len(row.synonyms) == 0:
            self.set_sensitive(False)
        else:

            def on_clicked(l, e, syn):
                return select_in_search_results(syn)

            for syn in row.synonyms:
                # create clickable label that will select the synonym
                # in the search results
                box = Gtk.EventBox()
                label = Gtk.Label()
                label.set_alignment(0, 0.5)
                label.set_markup(Family.str(syn))
                box.add(label)
                utils.make_label_clickable(label, on_clicked, syn)
                syn_box.pack_start(box, False, False, 0)
            self.show_all()
            self.set_sensitive(True)


class FamilyInfoBox(InfoBox):
    """ """

    widgets: Any
    general: Any
    synonyms: Any
    links: Any
    properties_expander: Any

    def __init__(self) -> None:
        """ """

        button_defs = [
            {
                "name": "IPNIButton",
                "_base_uri": "http://www.ipni.org/ipni/advPlantNameSearch.do?find_family=%(family)s&find_isAPNIRecord=on& find_isGCIRecord=on&find_isIKRecord=on&output_format=normal",
                "_space": " ",
                "title": _("Search IPNI"),
                "tooltip": _("Search the International Plant Names Index"),
            },
            {
                "name": "GoogleButton",
                "_base_uri": "http://www.google.com/search?q=%s",
                "_space": "+",
                "title": "Search Google",
                "tooltip": None,
            },
            {
                "name": "GBIFButton",
                "_base_uri": "http://www.gbif.org/species/search?q=%s",
                "_space": "+",
                "title": _("Search GBIF"),
                "tooltip": _("Search the Global Biodiversity Information Facility"),
            },
            {
                "name": "ITISButton",
                "_base_uri": "http://www.itis.gov/servlet/SingleRpt/SingleRpt?search_topic=Scientific_Name&search_value=%s&search_kingdom=Plant&search_span=containing&categories=All&source=html&search_credRating=All",
                "_space": "%20",
                "title": _("Search ITIS"),
                "tooltip": _("Search the Intergrated Taxonomic Information System"),
            },
            {
                "name": "GRINButton",
                "_base_uri": "http://www.ars-grin.gov/cgi-bin/npgs/swish/accboth?query=%s&submit=Submit+Text+Query&si=0",
                "_space": "+",
                "title": _("Search NPGS/GRIN"),
                "tooltip": _("Search National Plant Germplasm System"),
            },
            {
                "name": "ALAButton",
                "_base_uri": "http://bie.ala.org.au/search?q=%s",
                "_space": "+",
                "title": _("Search ALA"),
                "tooltip": _("Search the Atlas of Living Australia"),
            },
        ]
        InfoBox.__init__(self)
        filename = os.path.join(paths.lib_dir(), "plugins", "plants", "infoboxes.glade")
        self.widgets = utils.BuilderWidgets(filename)
        self.general = GeneralFamilyExpander(self.widgets)
        self.add_expander(self.general)
        self.synonyms = SynonymsExpander(self.widgets)
        self.add_expander(self.synonyms)
        self.links = view.LinksExpander("notes", links=button_defs)
        self.add_expander(self.links)
        self.properties_expander = PropertiesExpander()
        self.add_expander(self.properties_expander)

        if "GardenPlugin" not in pluginmgr.plugins:
            self.widgets.remove_parent("fam_nacc_label")
            self.widgets.remove_parent("fam_nacc_data")
            self.widgets.remove_parent("fam_nplants_label")
            self.widgets.remove_parent("fam_nplants_data")

    def update(self, row) -> None:
        """ """
        self.general.update(row)
        self.synonyms.update(row)
        self.links.update(row)
        self.properties_expander.update(row)
