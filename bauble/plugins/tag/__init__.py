#
# Copyright (c) 2005,2006,2007,2008,2009 Brett Adams <brett@belizebotanic.org>
# Copyright (c) 2012-2018 Mario Frasca <mario@anche.no>
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
# __init__.py -- tag plugin
#
# Description:
#
import logging
import os
import traceback
from collections.abc import Generator
from contextlib import contextmanager
from gettext import gettext as _
from typing import Any, ClassVar, Optional

import bauble
import sqlalchemy.orm
import sqlalchemy.orm.exc as orm_exc

# from bauble import ui
from bauble import db, editor, paths, pluginmgr, search, utils
from bauble.btypes import BaseModelProtocol as BaseModelProtocol
from bauble.editor import GenericEditorPresenter, GenericEditorView
from bauble.gtkinit import Gdk, Gtk
from bauble.shared import InfoExpander
from bauble.utils import safe_set_text
from bauble.view import Action, InfoBox, SearchView

# from sqlalchemy import text
from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    Unicode,
    UnicodeText,
    and_,
    select,
)
from sqlalchemy.exc import DBAPIError

# from sqlalchemy.exc import InvalidRequestError
# from sqlalchemy.orm import Session as SASession
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.orm.exc import DetachedInstanceError

# from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm.session import object_session

logger: Any = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@contextmanager
def session_scope() -> Generator[Any, None, None]:
    """Provide a transactional scope around a series of operations."""
    session = db.Session()
    try:
        yield session
    finally:
        session.close()


class TagsMenuManager:
    menu_item: Any
    active_tag_name: Any
    item_list: Any
    apply_active_tag_menu_item: Any
    remove_active_tag_menu_item: Any

    def __init__(self) -> None:
        self.menu_item: Optional[Gtk.MenuItem] = None
        self.active_tag_name: Optional[str] = None
        self.item_list: dict[str, Gtk.MenuItem] = {}
        self.apply_active_tag_menu_item: Optional[Gtk.MenuItem] = None
        self.remove_active_tag_menu_item: Optional[Gtk.MenuItem] = None

    def reset(self, make_active_tag: Optional[Any] = None) -> None:
        """Initialize or replace Tags menu in the main menu."""
        self.active_tag_name = make_active_tag.tag if make_active_tag else None
        tags_menu = self.build_menu()
        if not self.menu_item:
            self.menu_item = bauble.gui.add_menu(_("Tags"), tags_menu)
        else:
            self.menu_item.set_submenu(tags_menu)
            self.menu_item.show_all()

        logger.debug(f"Active tag set to: {self.active_tag_name}")
        if self.active_tag_name:
            self.show_active_tag()

    def show_active_tag(self) -> None:
        """Update UI to reflect the active tag."""
        # Remove any current tag icons
        for widget in self.item_list.values():
            if hasattr(widget, "set_child"):
                # GTK4
                widget.set_child(None)
            elif hasattr(widget, "set_image"):
                # GTK3
                widget.set_image(None)

        # Get the currently active tag widget
        widget = self.item_list.get(self.active_tag_name)

        if widget:
            # Create an image from the icon name (not stock)
            image = Gtk.Image.new_from_icon_name("apply", Gtk.IconSize.MENU)
            if isinstance(widget, Gtk.Button):
                # Use named icon (emblem-ok is a good alternative to STOCK_APPLY)
                image = Gtk.Image.new_from_icon_name("emblem-ok")

                # 7. issue_gtk_button_image_api (REMOVED, pack GtkImage manually inside GtkButton)
                if hasattr(widget, "set_child"):
                    widget.set_child(image)  # GTK4
                elif hasattr(widget, "set_image"):
                    widget.set_image(image)  # GTK3

                self.apply_active_tag_menu_item.set_sensitive(True)
                self.remove_active_tag_menu_item.set_sensitive(True)
            else:
                self.apply_active_tag_menu_item.set_sensitive(False)
                self.remove_active_tag_menu_item.set_sensitive(False)

        logger.debug(f"Showing active tag: {self.active_tag_name}")

    def item_activated(self, widget, tag_name) -> None:
        """Handle the activation of a tag menu item."""
        self.active_tag_name = tag_name
        self.show_active_tag()
        logger.debug(f"Activated tag: {tag_name}")
        bauble.gui.send_command(f'tag="{tag_name}"')

        view = bauble.gui.get_view()
        if isinstance(view, SearchView):
            first_path = Gtk.TreePath.new_first()
            if first_path:
                view.results_view.expand_to_path(first_path)

    def attach_path_to_menu(self, path, parent_menu, submenu_dict):
        """Attach a path to the menu structure."""
        full_path = ""
        for name in path:
            full_path += name
            if full_path not in submenu_dict:
                item = Gtk.ImageMenuItem(name)
                parent_menu.append(item)
                submenu_dict[full_path] = [item, Gtk.Menu()]
                item.set_submenu(submenu_dict[full_path][1])
            parent_menu = submenu_dict[full_path][1]
            full_path += "/"
        return parent_menu

    def build_menu(self):
        """Build tags Gtk.Menu based on current data."""
        self.item_list = {}
        tags_menu = Gtk.Menu()
        tag_dir = os.path.join(paths.lib_dir(), "plugins", "tag")

        add_tag_menu_item = bauble.ui.create_menu_item_with_image(
            _("Tag Selection"), "tag.png", tag_dir
        )
        add_tag_menu_item.connect("activate", self.on_add_tag_activated)
        self.apply_active_tag_menu_item = bauble.ui.create_menu_item_with_image(
            _("Apply active tag"), "tag_apply.png", tag_dir
        )
        self.apply_active_tag_menu_item.connect(
            "activate", self.on_apply_active_tag_activated
        )
        self.remove_active_tag_menu_item = bauble.ui.create_menu_item_with_image(
            _("Remove active tag"), "tag_remove.png", tag_dir
        )
        self.remove_active_tag_menu_item.connect(
            "activate", self.on_remove_active_tag_activated
        )

        if bauble.gui:
            accel_group = Gtk.AccelGroup()
            bauble.gui.window.add_accel_group(accel_group)
            self.register_accelerators(
                add_tag_menu_item, accel_group, ord("T"), Gdk.ModifierType.CONTROL_MASK
            )
            self.register_accelerators(
                self.apply_active_tag_menu_item,
                accel_group,
                ord("Y"),
                Gdk.ModifierType.CONTROL_MASK,
            )
            key, mask = Gtk.accelerator_parse("<Control><Shift>y")
            self.register_accelerators(
                self.remove_active_tag_menu_item, accel_group, key, mask
            )

        tags_menu.append(add_tag_menu_item)

        with session_scope() as session:
            # Fetch Tag query with ordering
            query = select(Tag).order_by(Tag.tag)
            tags = session.execute(query).scalars().all()  # Retrieve all tags
            has_tags = bool(tags)
            if has_tags:
                tags_menu.append(Gtk.SeparatorMenuItem())

            submenu = {"": [None, tags_menu]}  # Menu structure
            for tag in tags:
                *path, tail = tag.tag.split("/")
                head = "/".join(path)
                item = Gtk.ImageMenuItem(label=tail)
                submenu[tag.tag] = [item, None]
                item.set_always_show_image(True)
                self.item_list[tag.tag] = item
                item.connect("activate", self.item_activated, tag.tag)
                self.attach_path_to_menu(path, tags_menu, submenu)
                submenu[head][1].append(item)

        if has_tags:
            tags_menu.append(Gtk.SeparatorMenuItem())
            tags_menu.append(self.apply_active_tag_menu_item)
            tags_menu.append(self.remove_active_tag_menu_item)
            self.apply_active_tag_menu_item.set_sensitive(False)
            self.remove_active_tag_menu_item.set_sensitive(False)

        # Make sure all items and the menu are visible
        tags_menu.show_all()
        return tags_menu

    def register_accelerators(
        self, menu_item, accel_group, accel_key, modifiers
    ) -> None:
        """Add an accelerator key to a menu item."""
        try:
            menu_item.add_accelerator(
                "activate", accel_group, accel_key, modifiers, Gtk.AccelFlags.VISIBLE
            )
        except Exception as e:
            logger.error(
                f"Failed to register accelerator for {menu_item.get_label()}: {e}"
            )

    def toggle_tag(self, applying) -> None:
        view = bauble.gui.get_view()
        try:
            values = view.get_selected_values()
        except AttributeError:
            msg = _(
                "In order to tag or untag an item you must first search for "
                "something and select one of the results."
            )
            bauble.gui.show_message_box(msg)
            return
        if len(values) == 0:
            msg = _("Please select something in the search results.")
            utils.message_dialog(msg)
            return
        if self.active_tag_name is None:
            msg = _("Please make sure a tag is active.")
            utils.message_dialog(msg)
            return
        applying(self.active_tag_name, values)
        view.update_bottom_notebook()

    def on_add_tag_activated(self, *args, **kwargs) -> None:
        logger.debug("Add tag activated.")
        # Add implementation here

    def on_apply_active_tag_activated(self, *args, **kwargs) -> None:
        logger.debug(f"You're applying {self.active_tag_name} to the selection")
        self.toggle_tag(applying=utils.tag_objects)

    def on_remove_active_tag_activated(self, *args, **kwargs) -> None:
        logger.debug(f"You're removing {self.active_tag_name} from the selection")
        self.toggle_tag(applying=utils.untag_objects)


tags_menu_manager: Any = TagsMenuManager()


def edit_callback(tags):
    tag = tags[0]
    if tag is None:
        tag = Tag()
    view = GenericEditorView(
        os.path.join(paths.lib_dir(), "plugins", "tag", "tag.glade"),
        parent=None,
        root_widget_name="tag_dialog",
    )
    for note in tag.notes:
        view.widgets.notes_list.append(
            (note.category, "str", note.note, "gtk-apply", note.id, True)
        )
    presenter = TagEditorPresenter(tag, view, refresh_view=True)
    error_state = presenter.start()
    if error_state:
        if presenter.session.in_transaction():
            presenter.session.rollback()
    else:
        presenter.commit_changes()
        tags_menu_manager.reset()
    presenter.cleanup()
    return error_state


def remove_callback(tags):
    """
    :param tags: a list of :class:`Tag` objects.
    """
    tag = tags[0]
    s = f"{tag.__class__.__name__}: {utils.xml_safe(tag)}"
    msg = _("Are you sure you want to remove %s?") % s
    if not utils.yes_no_dialog(msg):
        return
    session = object_session(tag)
    try:
        obj = session.get(Tag, tag.id)
        session.delete(obj)
        if session.in_transaction():
            session.commit()
    except Exception as e:
        msg = _("Could not delete.\n\n%s") % utils.xml_safe(e)
        utils.message_details_dialog(
            msg, traceback.format_exc(), type=Gtk.MessageType.ERROR
        )

    # reinitialize the tag menu
    tags_menu_manager.reset()
    return True


edit_action: Any = Action(
    "acc_edit", _("_Edit"), callback=edit_callback, accelerator="<ctrl>e"
)
remove_action: Any = Action(
    "tag_remove",
    _("_Delete"),
    callback=remove_callback,
    accelerator="<ctrl>Delete",
    multiselect=True,
)

tag_context_menu: Any = [edit_action, remove_action]


class TagEditorPresenter(GenericEditorPresenter):

    last_entry: Any
    column: int
    widget_to_field_map: Any = {
        "tag_name_entry": "tag",
        "tag_desc_textbuffer": "description",
    }

    view_accept_buttons: Any = [
        "tag_ok_button",
        "tag_cancel_button",
    ]

    def on_cell_edited(self, widget, path, text) -> None:
        self.view.widgets.notes_list[path][self.column] = text

    def on_focus_child(self, tree, entry) -> None:
        if entry is not None:
            self.last_entry = entry
        else:
            tv, path = tree.get_selection().get_selected()
            self.view.widgets.notes_list[path][self.column] = self.last_entry.get_text()

    def on_cell_editing_started_col0(self, *args) -> None:
        self.column = 2

    def on_cell_editing_started_col1(self, *args) -> None:
        self.column = 0

    def on_toggle_row(self, tree, path, column) -> None:
        store = self.view.widgets.notes_list
        store[path][5] = not store[path][5]
        store[path][3] = {True: "gtk-apply", False: "gtk-cancel"}[store[path][5]]

    def on_add_a_note_clicked(self, *args) -> None:
        #            name --> type --> content --> icon-name --> id --> keep
        #               0        1           2             3      4        5
        self.view.widgets.notes_list.append(("", "str", "", "gtk-apply", -1, True))

    def on_tag_desc_textbuffer_changed(self, widget, value: Optional[Any] = None):
        return GenericEditorPresenter.on_textbuffer_changed(
            self, widget, value, attr="description"
        )

    def commit_changes(self) -> None:
        for row in self.view.widgets.notes_list:
            category, value_type, value, icon, note_id, keep = row
            if note_id == -1:
                if keep is True:
                    # create a new note and add it to the session
                    note = TagNote(
                        tag=self.model,
                        category=category,
                        note=value,
                        type=value_type,
                        user=db.current_user(),
                    )
                    self.session.add(note)
            else:
                # retrieve and update existing note
                note = (
                    self.session.execute(select(TagNote).where(id=note_id))
                    .scalars()
                    .one()
                )
                if keep is False:
                    self.session.delete(note)
                else:
                    note.category = category
                    note.note = value
                    note.type = value_type
        super().commit_changes()


class TagItemGUI(editor.GenericEditorView):
    """
    Interface for tagging individual items in the results of the SearchView
    """

    item_data_label: Any
    values: Any
    tag_tree: Any

    def __init__(self, values) -> None:
        filename = os.path.join(paths.lib_dir(), "plugins", "tag", "tag.glade")
        super().__init__(filename)
        self.item_data_label = self.widgets.items_data
        self.values = values
        safe_set_text(self.item_data_label, ", ".join([str(s) for s in self.values]))
        self.connect(self.widgets.new_button, "clicked", self.on_new_button_clicked)

    def get_window(self):
        return self.widgets.tag_item_dialog

    def on_new_button_clicked(self, *args) -> None:
        """
        create a new tag
        """
        session = db.Session()
        tag = Tag(description="")
        session.add(tag)
        error_state = edit_callback([tag])
        if not error_state:
            model = self.tag_tree.get_model()
            model.append([False, tag.tag, False])
            tags_menu_manager.reset(tag)
        session.close()

    def on_toggled(self, renderer, path, data: Optional[Any] = None) -> None:
        """
        tag or untag the objs in self.values
        """
        active = not renderer.get_active()
        model = self.tag_tree.get_model()
        iter = model.get_iter(path)
        model[iter][0] = active
        model[iter][2] = False
        name = model[iter][1]
        if active:
            tag_objects(name, self.values)
        else:
            untag_objects(name, self.values)

    def build_tag_tree_columns(self):
        """
        Build the tag tree columns.
        """
        renderer = Gtk.CellRendererToggle()
        self.connect(renderer, "toggled", self.on_toggled)
        renderer.set_property("activatable", True)
        toggle_column = Gtk.TreeViewColumn(None, renderer)
        toggle_column.add_attribute(renderer, "active", 0)
        toggle_column.add_attribute(renderer, "inconsistent", 2)

        renderer = Gtk.CellRendererText()
        tag_column = Gtk.TreeViewColumn(None, renderer, text=1)

        return [toggle_column, tag_column]

    def on_key_released(self, widget, event) -> None:
        """
        if the user hits the delete key on a selected tag in the tag editor
        then delete the tag
        """
        keyname = Gdk.keyval_name(event.get_keyval())  # 1. issue_gdkevent_structs
        if keyname != "Delete":
            return
        model, row_iter = self.tag_tree.get_selection().get_selected()
        tag_name = model[row_iter][1]
        msg = _('Are you sure you want to delete the tag "%s"?') % tag_name
        if not utils.yes_no_dialog(msg):
            return
        session = db.Session()
        try:
            tag = session.scalars(select(Tag).where(Tag.tag == str(tag_name))).one()
            session.delete(tag)
            if session.in_transaction():
                session.commit()
            model.remove(row_iter)
            tags_menu_manager.reset()
            view = bauble.gui.get_view()
            if hasattr(view, "update"):
                view.update()
        except Exception as e:
            utils.message_details_dialog(
                utils.xml_safe(str(e)),
                traceback.format_exc(),
                Gtk.MessageType.ERROR,
            )
        finally:
            session.close()

    def start(self) -> None:
        # we keep restarting the dialog here since the gui was created with
        # glade then the 'new tag' button emits a response we want to ignore
        self.tag_tree = self.widgets.tag_tree

        # we remove the old columns and create new ones each time the
        # tag editor is started since we have to connect and
        # disconnect the toggled signal each time
        list(map(self.tag_tree.remove_column, self.tag_tree.get_columns()))
        columns = self.build_tag_tree_columns()
        for col in columns:
            self.tag_tree.append_column(col)

        # create the model
        model = Gtk.ListStore(bool, str, bool)
        tag_all, tag_some, tag_none = get_tag_ids(self.values)
        session = db.Session()  # we need close it
        tag_query = session.execute(select(Tag)).scalars()
        for tag in tag_query:
            model.append([tag.id in tag_all, tag.tag, tag.id in tag_some])
        self.tag_tree.set_model(model)

        self.tag_tree.add_events(Gdk.EventMask.KEY_RELEASE_MASK)
        self.connect(self.tag_tree, "key-release-event", self.on_key_released)

        response = self.get_window().run()
        while (
            response != Gtk.ResponseType.OK
            and response != Gtk.ResponseType.DELETE_EVENT
        ):
            response = self.get_window().run()

        self.get_window().hide()
        self.disconnect_all()
        session.close()


class Tag(db.Base, db.WithNotes):
    """
    :Table name: tag
    :Columns:
      tag: :class:`sqlalchemy.types.Unicode`
        The tag name.
      description: :class:`sqlalchemy.types.Unicode`
        A description of this tag.
    """

    id: Any
    __tablename__: str = "tag"

    # columns
    id : Mapped[int]= mapped_column(Integer, primary_key=True)
    tag: Mapped[str] = mapped_column(Unicode(64), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(UnicodeText)

    # relations
    _objects: Mapped[list["TaggedObj"]] = relationship(
        "TaggedObj",
        cascade="all, delete-orphan",
        back_populates="tag",
        single_parent=True,
    )

    import datetime

    __my_own_timestamp: ClassVar[Optional[datetime.datetime]] = None
    __last_objects: ClassVar[Optional[list[Any]]] = None

    # Use a lambda to defer attribute access until runtime
    @staticmethod
    def order_by():
        return [Tag.tag]

    def __str__(self) -> str:
        try:
            return str(self.tag)
        except DetachedInstanceError:
            return db.Base.__str__(self)

    def markup(self) -> str:
        return f"{self.tag} Tag"

    def tag_objects(self, objects) -> None:
        """Add tags to the provided objects."""
        with db.Session() as session:
            for obj in objects:
                cls = and_(
                    TaggedObj.obj_class == type(obj).__name__,
                    TaggedObj.obj_id == obj.id,
                    TaggedObj.tag_id == self.id,
                )
                from sqlalchemy import func

                ntagged = session.execute(
                    select(func.count()).select_from(TaggedObj).where(cls)
                )
                if ntagged == 0:
                    tagged_obj = TaggedObj(
                        obj_class=type(obj).__name__, obj_id=obj.id, tag=self
                    )
                    session.add(tagged_obj)

    @property
    def objects(self) -> list:
        """Return all tagged objects, using a cache if possible."""
        # Check if the cached list is valid based on the database's latest history timestamp
        if self.__my_own_timestamp is not None:
            with db.Session() as session:
                last_history = (
                    session.execute(
                        select(db.History.timestamp)
                        .order_by(db.History.timestamp.desc())
                        .limit(1)
                    )
                ).scalars()
                if last_history and last_history > self.__my_own_timestamp:
                    # Invalidate the cache if the database has changed
                    self.__last_objects = None

        # If the cache is invalid or uninitialized, update it
        if self.__last_objects is None:
            from datetime import datetime

            self.__my_own_timestamp = datetime.now()  # Update the timestamp
            self.__last_objects = (
                self.get_tagged_objects()
            )  # Refresh the cached objects

        # Return the cached objects
        return self.__last_objects

    def is_tagging(self, obj: "BaseModelProtocol") -> bool:
        """tell whether self tags obj"""
        return obj in self.objects

    def get_tagged_objects(
        self, session: Optional[sqlalchemy.orm.Session] = None
    ) -> list:
        """
        Return all objects tagged with this tag.

        Reuses the logic of `_get_tagged_object_pairs` but optimizes queries by
        grouping objects by their class for batch retrieval.
        """
        session = session or object_session(self)

        # Retrieve mapper-object pairs
        tagged_pairs = _get_tagged_object_pairs(self)
        results = []

        # Group queries by mapper (class)
        mapper_to_ids = {}
        for mapper, obj_id in tagged_pairs:
            mapper_to_ids.setdefault(mapper, []).append(obj_id)

        # Query objects for each mapper in a single query
        for mapper, ids in mapper_to_ids.items():
            objects = (
                session.execute(select(mapper).where(mapper.id.in_(ids)))
                .scalars()
                .all()
            )
            results.extend(objects)

        # Filter out None references (orphans)
        return [obj for obj in results if obj is not None]

    @classmethod
    def attached_to(cls, obj: "BaseModelProtocol") -> list:
        """Return the list of tags attached to the given object."""
        with db.Session() as session:
            qto = session.execute(
                select(TaggedObj).where(
                    TaggedObj.obj_class == type(obj).__name__,
                    TaggedObj.obj_id == obj.id,
                )
            ).scalars()
            return [i.tag for i in qto.all()]

    def search_view_markup_pair(self):
        """provide the two lines describing object for SearchView row."""
        import inspect

        logging.debug(
            f"entering search_view_markup_pair {self}, {str(inspect.stack()[1])}"
        )
        objects = self.objects
        classes = {type(o) for o in objects}
        if len(classes) == 1:
            fine_prints = _("tagging %(1)s objects of type %(2)s") % {
                "1": len(objects),
                "2": classes.pop().__name__,
            }
        elif len(classes) == 0:
            fine_prints = _("tagging nothing")
        else:
            fine_prints = _("tagging %(1)s objects of %(2)s different types") % {
                "1": len(objects),
                "2": len(classes),
            }
            if len(classes) < 4:
                fine_prints += ": " + (", ".join(sorted(t.__name__ for t in classes)))
        first = f'{utils.xml_safe(self)} - <span weight="light">{fine_prints}</span>'
        second = '({}) - <span weight="light">{}</span>'.format(
            type(self).__name__,
            (self.description or "").replace("\n", " ")[:256],
        )
        return first, second


TagNote: Any = db.make_note_class("Tag", Tag)
Tag.notes = relationship(
    "TagNote",
    back_populates="tag",
    cascade="all,delete-orphan",
    single_parent=True,
)


class TaggedObj(db.Base):
    """
    :Table name: tagged_obj
    :Columns:
      obj_id: :class:`sqlalchemy.types.Integer`
        The id of the tagged object.
      obj_class: :class:`sqlalchemy.types.Unicode`
        The class name of the tagged object.
      tag_id: :class:`sqlalchemy.types.Integer`
        A ForeignKey to :class:`Tag`.

    """

    id: Any
    __tablename__: str = "tagged_obj"

    # columns
    id : Mapped[int] = mapped_column(Integer, primary_key=True)
    obj_id: Mapped[int] = mapped_column(Integer, autoincrement=False)
    obj_class: Mapped[str] = mapped_column(String(128))
    tag_id: Mapped[int] = mapped_column(Integer, ForeignKey("tag.id"))
    tag: Mapped["Tag"] = relationship(
        "Tag",
        cascade="all, delete-orphan",
        back_populates="_objects",
        single_parent=True,
    )

    def __str__(self) -> str:
        return f"{self.obj_class}: {self.obj_id}"


def _get_tagged_object_pairs(tag):
    """
    :param tag: a Tag instance
    """

    kids = []
    for obj in tag._objects:
        try:
            # __import__ "from_list" parameters has to be a list of strings
            module_name, _, cls_name = str(obj.obj_class).rpartition(".")
            module = __import__(
                module_name, globals(), locals(), module_name.split(".")[1:]
            )
            cls = getattr(module, cls_name)
            kids.append((cls, obj.obj_id))
        except KeyError as e:
            logger.warning(f"KeyError -- tag.get_tagged_objects({tag}): {e}")
            continue
        except DBAPIError as e:
            logger.warning(f"DBAPIError -- tag.get_tagged_objects({tag}): {e}")
            continue
        except AttributeError as e:
            logger.warning(f"AttributeError -- tag.get_tagged_objects({tag}): {e}")
            logger.warning(
                f"Could not get the object for {module_name}.{cls_name}({obj.obj_id})"
            )
            continue

    return kids


def create_named_empty_tag(name: str) -> None:
    """
    Ensure a tag with the specified name exists in the database.

    :param name: The name of the tag to create or verify.
    """
    with db.Session() as session:
        try:
            # Check if the tag already exists
            tag = session.execute(select(Tag).where(tag=name)).scalars().one()
        except orm_exc.NoResultFound:
            # Create the tag if it doesn't exist
            logger.debug(f"Tag '{name}' not found, creating it.")
            tag = Tag(tag=name)
            session.add(tag)
            if session.in_transaction():
                session.commit()
        except Exception as e:
            logger.error(f"An error occurred while creating tag '{name}': {e}")


def untag_objects(name: str, objs: list) -> None:
    """
    Remove the tag with the given name from the specified objects.

    :param name: The name of the tag to remove.
    :param objs: The list of objects to untag.
    """
    name = utils.to_unicode(name)

    if not objs:
        create_named_empty_tag(name)
        return

    # Use the session from the first object
    session = object_session(objs[0])
    if session is None:
        logger.error("No session found for the provided objects.")
        return

    try:
        # Retrieve the tag
        tag = session.execute(select(Tag).where(tag=name)).scalars().one()
    except orm_exc.NoResultFound:
        logger.info(f"Tag '{name}' does not exist. Nothing to remove.")
        return
    except Exception as e:
        logger.error(f"Unexpected error retrieving tag '{name}': {e}")
        return

    # Create a set of object identifiers (class name, ID) for comparison
    objs_to_untag = {(_classname(obj), obj.id) for obj in objs}

    # Iterate over tagged objects and remove matching ones
    for tagged_obj in tag._objects:
        if (tagged_obj.obj_class, tagged_obj.obj_id) in objs_to_untag:
            session.delete(tagged_obj)

    try:
        if session.in_transaction():
            session.commit()
        logger.info(f"Successfully removed tag '{name}' from specified objects.")
    except Exception as e:
        logger.error(f"Failed to commit changes while untagging objects: {e}")
        if session.in_transaction():
            if session.in_transaction():
                session.rollback()


# create the classname stored in the tagged_obj table
def _classname(x):
    return f"{type(x).__module__}.{type(x).__name__}"


def tag_objects(name: str, objects: list) -> None:
    """
    Create or retrieve a tag and use it to tag a list of objects.

    :param name: The name of the tag to create or retrieve.
    :param objects: The list of mapped objects to tag.
    """
    if not objects:
        create_named_empty_tag(name)
        return

    name = utils.to_unicode(name)
    session = object_session(objects[0])
    try:
        tag = session.execute(select(Tag).where(tag=name)).scalars().one()
    except orm_exc.NoResultFound:
        logger.debug(f"Tag '{name}' not found, creating it.")
        tag = Tag(tag=name)
        session.add(tag)
    except Exception as e:
        logger.error(f"An error occurred while retrieving tag '{name}': {e}")
        return

    try:
        tag.tag_objects(objects)
        if session.in_transaction():
            session.commit()
    except Exception as e:
        logger.error(f"An error occurred while tagging objects: {e}")
        if session.in_transaction():
            if session.in_transaction():
                session.rollback()


def get_tag_ids(objs):
    """
    Return a 3-tuple describing which tags apply to objs.

    The result tuple is composed of sets. The first set contains the IDs
    of the tags that apply to all objs. The second set contains the IDs
    of the tags that apply to one or more objs, but not all. The third set
    contains the IDs of the tags that do not apply to any objs.

    :param objs: a list or tuple of objects
    """
    if not objs:
        return set(), set(), set()

    session = object_session(objs[0])
    if not session:
        raise ValueError("Cannot retrieve session from the provided objects.")

    # Fetch all tag IDs at once
    all_tag_ids = set(session.scalars(select(Tag.id)))

    # Initialize sets for tags
    s_all = None
    s_some = set()
    s_none = all_tag_ids

    # Efficiently batch process objects
    for obj in objs:
        obj_classname = _classname(obj)

        applied_tag_ids = set(
            session.scalars(
                select(Tag.id)
                .join(TaggedObj, TaggedObj.tag_id == Tag.id)
                .where(TaggedObj.obj_class == obj_classname, TaggedObj.obj_id == obj.id)
            )
        )

        if s_all is None:
            s_all = applied_tag_ids
        else:
            s_all.intersection_update(applied_tag_ids)

        s_some.update(applied_tag_ids)
        s_none.difference_update(applied_tag_ids)

    # Tags that apply to some but not all
    s_some.difference_update(s_all)

    return s_all, s_some, s_none


def _on_add_tag_activated(*args, **kwargs) -> None:
    # get the selection from the search view
    view = bauble.gui.get_view()
    try:
        values = view.get_selected_values()
    except AttributeError:
        msg = _(
            "In order to tag an item you must first search for "
            "something and select one of the results."
        )
        bauble.gui.show_message_box(msg)
        return
    if len(values) == 0:
        msg = _("Nothing selected")
        utils.message_dialog(msg)
        return
    tagitem = TagItemGUI(values)
    tagitem.start()
    view.update_bottom_notebook()


class GeneralTagExpander(InfoExpander):
    """
    generic information about an accession like
    number of clones, provenance type, wild provenance type, speciess
    """

    table_cells: Any
    current_obj: Any

    def __init__(self, widgets) -> None:
        """ """
        super().__init__(_("General"), widgets)
        general_box = self.widgets.general_box
        self.widgets.general_window.remove(general_box)
        self.vbox.pack_start(general_box, True, True, 0)
        self.table_cells = []

    def update(self, row):
        def on_label_clicked(l, e, x):
            return bauble.gui.send_command(x)

        self.current_obj = row
        self.widget_set_value("ib_name_label", row.tag)
        self.widget_set_value("ib_description_label", row.description)
        objects = row.objects
        classes = {type(o) for o in objects}
        row_no = 1
        table = self.widgets.tag_ib_general_table
        for w in self.table_cells:
            table.remove(w)
        self.table_cells = []
        for c in classes:
            obj_ids = [str(o.id) for o in objects if isinstance(o, c)]
            lab = Gtk.Label()
            lab.set_alignment(0, 0.5)
            safe_set_text(lab, c.__name__)
            lab.set_hexpand(False)
            table.attach(lab, 0, row_no, 1, 1)

            eb = Gtk.EventBox()
            leb = Gtk.Label()
            leb.set_alignment(0, 0.5)
            eb.add(leb)
            eb.set_hexpand(False)
            table.attach(eb, 1, row_no, 1, 1)
            safe_set_text(leb, f" {len(obj_ids)} ")
            utils.make_label_clickable(
                leb,
                on_label_clicked,
                "{} where id in {}".format(c.__name__.lower(), ", ".join(obj_ids)),
            )

            self.table_cells.append(lab)
            self.table_cells.append(eb)

            row_no += 1
        table.show_all()


class TagInfoBox(InfoBox):
    """
    - general info
    - source
    """

    widgets: Any
    general: Any

    def __init__(self) -> None:
        super().__init__()
        filename = os.path.join(paths.lib_dir(), "plugins", "tag", "tag.glade")
        self.widgets = utils.BuilderWidgets(filename)
        self.general = GeneralTagExpander(self.widgets)
        self.add_expander(self.general)

    def update(self, row) -> None:
        self.general.update(row)


class TagPlugin(pluginmgr.Plugin):
    provides: Any = {"Tag": Tag}

    @classmethod
    def init(cls) -> None:
        pluginmgr.provided.update(cls.provides)
        from functools import partial

        from bauble.view import SearchView

        mapper_search = search.get_strategy("MapperSearch")
        mapper_search.add_meta(("tag", "tags"), Tag, ["tag"])
        SearchView.row_meta[Tag].set(
            children=partial(db.natsort, "objects"),
            infobox=TagInfoBox,
            context_menu=tag_context_menu,
        )
        SearchView.bottom_info[Tag] = {
            "page_widget": "taginfo_scrolledwindow",
            "fields_used": ["tag", "description"],
            "glade_name": os.path.join(paths.lib_dir(), "plugins/tag/tag.glade"),
            "name": _("Tags"),
        }
        if bauble.gui is not None:
            tags_menu_manager.reset()
        else:
            pass


plugin = TagPlugin
