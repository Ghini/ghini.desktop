#
# Copyright 2008, 2009, 2010 Brett Adams
# Copyright 2014-2018 Mario Frasca <mario@anche.no>.
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
import logging
from gettext import gettext as _
from typing import Any, Optional

import bauble
from bauble.editor import GenericEditorPresenter
from bauble.gtkinit import Gtk
from bauble.utils import safe_set_text
from sqlalchemy.orm import class_mapper
from sqlalchemy.orm.properties import ColumnProperty, RelationshipProperty

from .querybuilderparser import BuiltQuery as BuiltQuery
from .search import EmptyToken as EmptyToken
from .search import MapperSearch as MapperSearch

logger: Any = logging.getLogger(__name__)


RelationProperty = RelationshipProperty


def parse_typed_value(value):
    """Parses input and returns corresponding typed value: int, float, None, or EmptyToken."""
    try:
        if value == "None":
            return None
        elif value == "Empty":
            return EmptyToken()
        try:
            new_val = int(value)
        except ValueError:
            new_val = float(value)
        return new_val
    except ValueError:
        logger.error("Invalid input type: %s", value)
        return value  # fallback to string


class SchemaMenu:
    """
    SchemaMenu - Manages a context menu populated based on the mapper properties.

    :param mapper: The mapper to extract properties from.
    :param activate_cb: Callback to invoke when a menu item is activated.
    :param relation_filter: Function to filter relations.
    :param leading_items: List of leading items to append to the menu.
    """

    mapper: Any
    activate_cb: Any
    relation_filter: Any
    leading_items: Any
    menu: Any

    def __init__(
        self,
        mapper,
        activate_cb: Optional[Any] = None,
        relation_filter=lambda c, p: True,
        leading_items: Optional[Any] = None,
    ) -> None:
        if leading_items is None:
            leading_items = []
        self.mapper = mapper
        self.activate_cb = activate_cb
        self.relation_filter = relation_filter
        self.leading_items = leading_items

        # Use Gtk.Menu as a contained widget instead of subclassing
        self.menu = Gtk.Menu()
        self.append_menuitems(mapper, target=self.menu)
        self.menu.show_all()

    def get_menu(self):
        """Returns the menu widget."""
        return self.menu

    def on_activate(self, menuitem, prop) -> None:
        """Invoke activate_cb on selected menu item."""
        path = []
        # path.append(menuitem.get_child().get_property("label"))
        path.append(menuitem.get_label())
        menu = menuitem.get_parent()
        while menu:
            menuitem = menu.get_attach_widget()
            if not menuitem:
                break
            # label = menuitem.get_child().get_property("label")
            label = menuitem.get_label()
            path.append(label)
            menu = menuitem.get_parent()
        full_path = ".".join(reversed(path))
        if self.activate_cb:
            self.activate_cb(menuitem, full_path, prop)

    def on_select(self, menuitem, prop) -> None:
        """Construct and show submenu corresponding to RelationProperty."""
        submenu = menuitem.get_submenu()
        if len(submenu.get_children()) == 0:  # If still empty, construct it
            self.append_menuitems(prop.mapper, prop, target=submenu)
        submenu.show_all()

    def append_menuitems(
        self, mapper, container: Optional[Any] = None, target: Optional[Any] = None
    ):
        """Populate target menu

        Construct as manu Gtk.MenuItem as the properties of `mapper` and
        append each new item to the target menu.

        ColumnProperties correspond to end-point MenuItems.  When
        activated, the interaction with the SchemaMenu is completed, and
        the top `activate_cb` is invoked.

        RelationProperties correspond to MenuItems with a cascade menu.
        When selected, the `on_select` callback checks whether the
        corresponding submenu is already in place, possibly constructs it
        (by invoking this same `append_menuitems`) and shows it.

        When the `target` menu is a submenu associated to some MenuItem,
        `container` is the property from which that MenuItem was created,
        in a previous invocation of append_menuitems.

        """
        # When looping over iterate_properties leave out properties that
        # start with underscore since they are considered private.
        # Separate properties in column_properties and relation_properties.
        # Do not offer any foreign key: can be reached as 'id' of relation.
        # First in order is own 'id'.
        column_properties = sorted(
            [
                x
                for x in mapper.iterate_properties
                if isinstance(x, ColumnProperty)
                and not x.key.endswith("_id")
                and not x.key.startswith("_")
            ],
            key=lambda k: (k.key != "id", k.key),
        )
        relation_properties = sorted(
            [
                x
                for x in mapper.iterate_properties
                if isinstance(x, RelationProperty) and not x.key.startswith("_")
            ],
            key=lambda k: k.key,
        )

        if container is None or not container.uselist:
            for key in self.leading_items:
                item = Gtk.MenuItem(label=key, use_underline=False)
                item.connect("activate", self.on_activate, None)
                target.append(item)

        for prop in column_properties:
            if not self.relation_filter(container, prop):
                continue
            item = Gtk.MenuItem(label=prop.key, use_underline=False)
            item.connect("activate", self.on_activate, prop)
            target.append(item)

        for prop in relation_properties:
            if not self.relation_filter(container, prop):
                continue
            item = Gtk.MenuItem(label=prop.key, use_underline=False)
            submenu = Gtk.Menu()
            item.set_submenu(submenu)
            item.connect("select", self.on_select, prop)
            target.append(item)

    def show_menu(self, widget, event) -> None:
        """Show the menu at the pointer position"""
        # Ensure that the menu shows up where the user clicked
        self.menu.popup_at_pointer(event)


class ExpressionRow:
    """ """

    table: Any
    presenter: Any
    menu_item_activated: bool
    and_or_combo: Any
    prop_button: Any
    schema_menu: Any
    cond_combo: Any
    value_widget: Any
    remove_button: Any
    conditions: Any = ["=", "!=", "<", "<=", ">", ">=", "like", "contains"]

    def __init__(self, query_builder, remove_callback, row_number) -> None:
        self.table = query_builder.view.widgets.expressions_table
        self.presenter = query_builder
        self.menu_item_activated = False

        self.and_or_combo = None
        if row_number != 1:
            self.and_or_combo = Gtk.ComboBoxText()
            self.and_or_combo.append_text("and")
            self.and_or_combo.append_text("or")
            self.and_or_combo.set_active(0)
            self.and_or_combo.set_hexpand(False)
            self.table.attach(self.and_or_combo, 0, row_number, 1, 1)

        self.prop_button = Gtk.Button(label=_("Choose a property…"))
        self.prop_button.set_property("use-underline", False)

        # def on_prop_button_clicked(button, event, menu):
        #    menu.popup(None, None, None, None, event.get_button(), event.time)  # 1. issue_gdkevent_structs
        def on_prop_button_clicked(button, event, menu):
            """Handle button click and show the menu at the pointer position"""
            # Assuming that 'menu' is a SchemaMenu instance
            menu.show_menu(button, event)  # Show the menu at the event position

        self.schema_menu = SchemaMenu(
            self.presenter.mapper,
            self.on_schema_menu_activated,
            self.relation_filter,
        )
        self.prop_button.connect(
            "button-press-event", on_prop_button_clicked, self.schema_menu
        )
        self.table.attach(self.prop_button, 1, row_number, 1, 1)

        self.cond_combo = Gtk.ComboBoxText()
        list(map(self.cond_combo.append_text, self.conditions))
        self.cond_combo.set_active(0)
        self.table.attach(self.cond_combo, 2, row_number, 1, 1)

        # by default we start with an entry but value_widget can
        # change depending on the type of the property chosen in the
        # schema menu, see self.on_schema_menu_activated
        self.value_widget = Gtk.Entry()
        self.value_widget.connect("changed", self.on_value_changed)
        self.table.attach(self.value_widget, 3, row_number, 1, 1)

        if row_number != 1:
            image = Gtk.Image.new_from_icon_name("edit-delete", Gtk.IconSize.BUTTON)
            self.remove_button = Gtk.Button()
            # 7. issue_gtk_button_image_api (REMOVED, pack GtkImage manually inside GtkButton)
            if Gtk.get_major_version() >= 4:
                self.remove_button.set_child(image)
            else:
                self.remove_button.add(image)
                self.remove_button.show_all()
            self.remove_button.connect("clicked", lambda b: remove_callback(self))
            self.table.attach(self.remove_button, 4, row_number, 1, 1)

    def on_value_changed(self, widget, *args) -> None:
        """
        Call the QueryBuilder.validate() for this row.
        Set the sensitivity of the Gtk.ResponseType.OK button on the QueryBuilder.
        """
        self.presenter.validate()

    def on_schema_menu_activated(self, menuitem, path, prop):
        """
        Called when an item in the schema menu is activated
        """
        self.prop_button.set_property("label", path)
        self.menu_item_activated = True
        row = self.table.child_get_property(self.value_widget, "top-attach")
        width = self.table.child_get_property(self.value_widget, "width")
        height = self.table.child_get_property(self.value_widget, "height")
        column = self.table.child_get_property(self.value_widget, "left-attach")
        self.table.remove(self.value_widget)

        # change the widget depending on the type of the selected property
        try:
            proptype = prop.columns[0].type
        except:
            proptype = None
        if isinstance(proptype, bauble.btypes.Enum):
            self.value_widget = Gtk.ComboBox()
            cell = Gtk.CellRendererText()
            self.value_widget.pack_start(cell, True)
            self.value_widget.add_attribute(cell, "text", 1)
            model = Gtk.ListStore(str, str)
            if prop.columns[0].type.translations:
                trans = prop.columns[0].type.translations
                prop_values = [
                    (k, trans[k])
                    for k in sorted(
                        list(trans.keys()), key=lambda x: (x is not None, x)
                    )
                ]
            else:
                values = prop.columns[0].type.values
                prop_values = [
                    (v, v) for v in sorted(values, key=lambda x: (x is not None, x))
                ]
            for value, translation in prop_values:
                model.append([value, translation])
            self.value_widget.set_property("model", model)
            self.value_widget.connect("changed", self.on_value_changed)
        elif not isinstance(self.value_widget, Gtk.Entry):
            self.value_widget = Gtk.Entry()
            self.value_widget.connect("changed", self.on_value_changed)

        self.table.attach(self.value_widget, column, row, width, height)
        self.table.show_all()
        self.presenter.validate()

    def relation_filter(self, container, prop):
        if isinstance(prop, ColumnProperty) and isinstance(
            prop.columns[0].type, bauble.btypes.Date
        ):
            return False
        return True

    def get_widgets(self):
        """
        Returns a tuple of the and_or_combo, prop_button, cond_combo,
        value_widget, and remove_button widgets.
        """
        return (
            i
            for i in (
                self.and_or_combo,
                self.prop_button,
                self.cond_combo,
                self.value_widget,
                self.remove_button,
            )
            if i
        )

    def get_expression(self):
        """
        Return the expression represented by this ExpressionRow.  If
        the expression is not valid then return None.

        :param self:
        """

        if not self.menu_item_activated:
            return None

        value = ""
        if isinstance(self.value_widget, Gtk.ComboBox):
            model = self.value_widget.get_property("model")
            active_iter = self.value_widget.get_active_iter()
            if active_iter:
                value = model[active_iter][0]
        else:
            # assume it's a Gtk.Entry or other widget with a text property
            value = self.value_widget.get_text().strip()
        value = parse_typed_value(value)
        and_or = ""
        if self.and_or_combo:
            and_or = self.and_or_combo.get_active_text()
        field_name = self.prop_button.get_property("label")
        if value == EmptyToken():
            field_name = field_name.rsplit(".", 1)[0]
        result = " ".join(
            [
                and_or,
                field_name,
                self.cond_combo.get_active_text(),
                repr(value),
            ]
        ).strip()
        return result


class QueryBuilder(GenericEditorPresenter):

    expression_rows: Any
    mapper: Any
    domain: Any
    table_row_count: int
    domain_map: Any
    view_accept_buttons: Any = ["cancel_button", "confirm_button"]
    default_size: Any = None

    def __init__(self, view: Optional[Any] = None) -> None:
        super().__init__(model=self, view=view, refresh_view=False)

        self.expression_rows = []
        self.mapper = None
        self.domain = None
        self.table_row_count = 0
        self.domain_map = MapperSearch.get_domain_classes().copy()

        self.view.widgets.domain_combo.set_active(-1)

        table = self.view.widgets.expressions_table
        list(map(table.remove, table.get_children()))

        self.view.widgets.domain_liststore.clear()
        for key in sorted(self.domain_map.keys()):
            self.view.widgets.domain_liststore.append([key])
        self.view.widgets.add_clause_button.set_sensitive = False
        self.refresh_view()

    def on_domain_combo_changed(self, *args) -> None:
        """
        Change the search domain.  Resets the expression table and
        deletes all the expression rows.
        """
        try:
            index = self.view.widgets.domain_combo.get_active()
        except AttributeError:
            return
        if index == -1:
            return

        self.domain = self.view.widgets.domain_liststore[index][0]

        # remove all clauses, they became useless in new domain
        table = self.view.widgets.expressions_table
        list(map(table.remove, table.get_children()))
        del self.expression_rows[:]
        # initialize view at 1 clause, however invalid
        self.table_row_count = 0
        self.on_add_clause()
        self.view.widgets.expressions_table.show_all()
        # let user add more clauses
        self.view.widgets.add_clause_button.set_sensitive = True

    def validate(self):
        """
        Validate the search expression is a valid expression.
        """
        valid = False
        for row in self.expression_rows:
            value = None
            if isinstance(row.value_widget, Gtk.Entry):
                value = row.value_widget.set_text
            elif isinstance(row.value_widget, Gtk.ComboBox):
                value = row.value_widget.get_active() >= 0

            if value and row.menu_item_activated:
                valid = True
            else:
                valid = False
                break

        self.view.widgets.confirm_button.set_sensitive = valid
        return valid

    def remove_expression_row(self, row) -> None:
        """
        Remove a row from the expressions table.
        """
        [i.destroy() for i in row.get_widgets()]
        self.table_row_count -= 1
        self.expression_rows.remove(row)
        self.view.widgets.expressions_table.resize(self.table_row_count, 5)

    def on_add_clause(self, *args) -> None:
        """
        Add a row to the expressions table.
        """
        domain = self.domain_map[self.domain]
        self.mapper = class_mapper(domain)
        self.table_row_count += 1
        row = ExpressionRow(self, self.remove_expression_row, self.table_row_count)
        self.expression_rows.append(row)
        self.view.widgets.expressions_table.show_all()

    def start(self):
        if self.default_size is None:
            self.__class__.default_size = self.view.widgets.main_dialog.get_size()
        else:
            self.view.widgets.main_dialog.resize(*self.default_size)
        return self.view.start()

    @property
    def valid_clauses(self):
        return [i.get_expression() for i in self.expression_rows if i.get_expression()]

    def get_query(self):
        """
        Return query expression string.
        """

        query = [self.domain, "where"] + self.valid_clauses
        return " ".join(query)

    def set_query(self, q) -> None:
        parsed = BuiltQuery(q)
        if not parsed.is_valid:
            logger.debug("cannot restore query, invalid")
            return

        # locate domain in list of valid domains
        try:
            index = sorted(self.domain_map.keys()).index(parsed.domain)
        except ValueError as e:
            logger.debug(f"cannot restore query, {type(e)}({e})")
            return
        # and set the domain_combo correspondently
        self.view.widgets.domain_combo.set_active(index)

        # now scan all clauses, one ExpressionRow per clause
        for clause in parsed.clauses:
            if clause.connector:
                self.on_add_clause()
            row = self.expression_rows[-1]
            if clause.connector:
                row.and_or_combo.set_active({"and": 0, "or": 1}[clause.connector])

            # the part about the value is a bit more complex: where the
            # clause.field leads to an enumerated property, on_add_clause
            # associates a gkt.ComboBox to it, otherwise a Gtk.Entry.
            # To set the value of a gkt.ComboBox we match one of its
            # items. To set the value of a gkt.Entry we need set_text.
            steps = clause.field.split(".")
            cls = self.domain_map[parsed.domain]
            mapper = class_mapper(cls)
            for target in steps[:-1]:
                mapper = mapper.get_property(target).mapper
            prop = mapper.get_property(steps[-1])
            row.on_schema_menu_activated(None, clause.field, prop)
            if isinstance(row.value_widget, Gtk.Entry):
                safe_set_text(row.value_widget, clause.value)
            elif isinstance(row.value_widget, Gtk.ComboBox):
                model = row.value_widget.get_property("model")
                for item in model:
                    # Process each item
                    if item[0] == clause.value:
                        row.value_widget.set_active_iter(item.iter)
                        break
            row.cond_combo.set_active(row.conditions.index(clause.operator))
