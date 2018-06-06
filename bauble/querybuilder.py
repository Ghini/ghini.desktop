# -*- coding: utf-8 -*-
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

from gi.repository import Gtk
import logging
logger = logging.getLogger(__name__)

from sqlalchemy.orm import class_mapper
from sqlalchemy.orm.properties import (
    ColumnProperty, RelationshipProperty)
RelationProperty = RelationshipProperty

import bauble

from .search import EmptyToken, MapperSearch
from .querybuilderparser import BuiltQuery
from bauble.editor import (
    GenericEditorView, GenericEditorPresenter)


def parse_typed_value(value):
    """parse the input string and return the corresponding typed value

    handles integers, floats, None, Empty, and falls back to string.
    """
    try:
        new_val = value
        new_val = float(value)
        new_val = int(value)
    except:
        if value == 'None':
            new_val = None
        if value == 'Empty':
            new_val = EmptyToken()
    value = new_val
    return value


class SchemaMenu(Gtk.Menu):
    """SchemaMenu

    TODO: Mario has the idea that this class is quite a mess: a smart GUI
    object, implementing non GUI logic.  then itself containing a menu,
    behaving as the top object, but not of its own class, so the logic is
    implemented in the top object alone, and needing to pass information
    around between smart and dumb objects.  some day someone can put order.

    :param mapper:
    :param activate cb:
    :param relation_filter:

    """

    def __init__(self, mapper, activate_cb=None,
                 relation_filter=lambda c, p: True,
                 leading_items=[]):
        super().__init__()
        self.activate_cb = activate_cb
        self.relation_filter = relation_filter
        self.leading_items = leading_items
        self.append_menuitems(mapper, target=self)
        self.show_all()

    def on_activate(self, menuitem, prop):
        """invoke activate_cb on selected menu item

        """
        path = []
        path = [menuitem.get_child().props.label]
        menu = menuitem.get_parent()
        while menu is not None:
            menuitem = menu.props.attach_widget
            if not menuitem:
                break
            label = menuitem.get_child().props.label
            path.append(label)
            menu = menuitem.get_parent()
        full_path = '.'.join(reversed(path))
        self.activate_cb(menuitem, full_path, prop)

    def on_select(self, menuitem, prop):
        """construct and show submenu corresponding to RelationProperty

        """
        submenu = menuitem.get_submenu()
        if len(submenu.get_children()) == 0:  # still empty: construct it
            self.append_menuitems(prop.mapper, prop, target=submenu)
        submenu.show_all()

    def append_menuitems(self, mapper, container=None, target=None):
        '''Populate target menu

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

        '''
        # When looping over iterate_properties leave out properties that
        # start with underscore since they are considered private.
        # Separate properties in column_properties and relation_properties.
        # Do not offer any foreign key: can be reached as 'id' of relation.
        # First in order is own 'id'.

        column_properties = sorted(
            [x for x in mapper.iterate_properties
             if isinstance(x, ColumnProperty)
             and not x.key.endswith('_id')
             and not x.key.startswith('_')],
            key=lambda k: (k.key!='id', k.key))
        relation_properties = sorted(
            [x for x in mapper.iterate_properties if isinstance(x, RelationProperty)
                   and not x.key.startswith('_')],
            key=lambda k: k.key)

        if container is None or not container.uselist:
            for key in self.leading_items:
                item = Gtk.MenuItem(key, use_underline=False)
                item.connect('activate', self.on_activate, None)
                target.append(item)

        for prop in column_properties:
            if not self.relation_filter(container, prop):
                continue
            item = Gtk.MenuItem(prop.key, use_underline=False)
            item.connect('activate', self.on_activate, prop)
            target.append(item)

        for prop in relation_properties:
            if not self.relation_filter(container, prop):
                continue
            item = Gtk.MenuItem(prop.key, use_underline=False)
            submenu = Gtk.Menu()
            item.set_submenu(submenu)
            item.connect('select', self.on_select, prop)
            target.append(item)


class ExpressionRow(object):
    """
    """

    conditions = ['=', '!=', '<', '<=', '>', '>=', 'like', 'contains']

    def __init__(self, query_builder, remove_callback, row_number):
        self.table = query_builder.view.widgets.expressions_table
        self.presenter = query_builder
        self.menu_item_activated = False

        self.and_or_combo = None
        if row_number != 1:
            self.and_or_combo = Gtk.ComboBoxText()
            self.and_or_combo.append_text("and")
            self.and_or_combo.append_text("or")
            self.and_or_combo.set_active(0)
            self.table.attach(self.and_or_combo, 0, 1,
                              row_number, row_number + 1)

        self.prop_button = Gtk.Button(_('Choose a property…'))
        self.prop_button.props.use_underline = False

        def on_prop_button_clicked(button, event, menu):
            menu.popup(None, None, None, None, event.button, event.time)

        self.schema_menu = SchemaMenu(self.presenter.mapper,
                                      self.on_schema_menu_activated,
                                      self.relation_filter)
        self.prop_button.connect('button-press-event', on_prop_button_clicked,
                                 self.schema_menu)
        self.table.attach(self.prop_button, 1, 2, row_number, row_number+1)

        self.cond_combo = Gtk.ComboBoxText()
        list(map(self.cond_combo.append_text, self.conditions))
        self.cond_combo.set_active(0)
        self.table.attach(self.cond_combo, 2, 3, row_number, row_number+1)

        # by default we start with an entry but value_widget can
        # change depending on the type of the property chosen in the
        # schema menu, see self.on_schema_menu_activated
        self.value_widget = Gtk.Entry()
        self.value_widget.connect('changed', self.on_value_changed)
        self.table.attach(self.value_widget, 3, 4, row_number, row_number+1)

        if row_number != 1:
            image = Gtk.Image.new_from_stock(Gtk.STOCK_REMOVE,
                                             Gtk.IconSize.BUTTON)
            self.remove_button = Gtk.Button()
            self.remove_button.props.image = image
            self.remove_button.connect('clicked',
                                       lambda b: remove_callback(self))
            self.table.attach(self.remove_button, 4, 5,
                              row_number, row_number + 1)

    def on_value_changed(self, widget, *args):
        """
        Call the QueryBuilder.validate() for this row.
        Set the sensitivity of the Gtk.ResponseType.OK button on the QueryBuilder.
        """
        self.presenter.validate()

    def on_schema_menu_activated(self, menuitem, path, prop):
        """
        Called when an item in the schema menu is activated
        """
        self.prop_button.props.label = path
        self.menu_item_activated = True
        top = self.table.child_get_property(self.value_widget, 'top-attach')
        bottom = self.table.child_get_property(self.value_widget,
                                               'bottom-attach')
        right = self.table.child_get_property(self.value_widget,
                                              'right-attach')
        left = self.table.child_get_property(self.value_widget, 'left-attach')
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
            self.value_widget.add_attribute(cell, 'text', 1)
            model = Gtk.ListStore(str, str)
            if prop.columns[0].type.translations:
                trans = prop.columns[0].type.translations
                prop_values = [(k, trans[k]) for k in sorted(trans.keys(), key=lambda x: (x is not None, x))]
            else:
                values = prop.columns[0].type.values
                prop_values = [(v, v) for v in sorted(values, key=lambda x: (x is not None, x))]
            for value, translation in prop_values:
                model.append([value, translation])
            self.value_widget.props.model = model
            self.value_widget.connect('changed', self.on_value_changed)
        elif not isinstance(self.value_widget, Gtk.Entry):
            self.value_widget = Gtk.Entry()
            self.value_widget.connect('changed', self.on_value_changed)

        self.table.attach(self.value_widget, left, right, top, bottom)
        self.table.show_all()
        self.presenter.validate()

    def relation_filter(self, container, prop):
        if isinstance(prop, ColumnProperty) and \
                isinstance(prop.columns[0].type, bauble.btypes.Date):
            return False
        return True

    def get_widgets(self):
        """
        Returns a tuple of the and_or_combo, prop_button, cond_combo,
        value_widget, and remove_button widgets.
        """
        return (i for i in (self.and_or_combo, self.prop_button, self.cond_combo,
                            self.value_widget, self.remove_button)
                if i)

    def get_expression(self):
        """
        Return the expression represented by this ExpressionRow.  If
        the expression is not valid then return None.

        :param self:
        """

        if not self.menu_item_activated:
            return None

        value = ''
        if isinstance(self.value_widget, Gtk.ComboBox):
            model = self.value_widget.props.model
            active_iter = self.value_widget.get_active_iter()
            if active_iter:
                value = model[active_iter][0]
        else:
            # assume it's a Gtk.Entry or other widget with a text property
            value = self.value_widget.props.text.strip()
        value = parse_typed_value(value)
        and_or = ''
        if self.and_or_combo:
            and_or = self.and_or_combo.get_active_text()
        field_name = self.prop_button.props.label
        if value == EmptyToken():
            field_name = field_name.rsplit('.', 1)[0]
        result = ' '.join([and_or, field_name,
                           self.cond_combo.get_active_text(),
                           repr(value)]).strip()
        return result


class QueryBuilder(GenericEditorPresenter):

    view_accept_buttons = ['cancel_button', 'confirm_button']
    default_size = None

    def __init__(self, view=None):
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
        self.view.widgets.add_clause_button.props.sensitive = False
        self.refresh_view()

    def on_domain_combo_changed(self, *args):
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
        self.view.widgets.add_clause_button.props.sensitive = True

    def validate(self):
        """
        Validate the search expression is a valid expression.
        """
        valid = False
        for row in self.expression_rows:
            value = None
            if isinstance(row.value_widget, Gtk.Entry):
                value = row.value_widget.props.text
            elif isinstance(row.value_widget, Gtk.ComboBox):
                value = row.value_widget.get_active() >= 0

            if value and row.menu_item_activated:
                valid = True
            else:
                valid = False
                break

        self.view.widgets.confirm_button.props.sensitive = valid
        return valid

    def remove_expression_row(self, row):
        """
        Remove a row from the expressions table.
        """
        [i.destroy() for i in row.get_widgets()]
        self.table_row_count -= 1
        self.expression_rows.remove(row)
        self.view.widgets.expressions_table.resize(self.table_row_count, 5)

    def on_add_clause(self, *args):
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
        return [i.get_expression()
                for i in self.expression_rows
                if i.get_expression()]

    def get_query(self):
        """
        Return query expression string.
        """

        query = [self.domain, 'where'] + self.valid_clauses
        return ' '.join(query)

    def set_query(self, q):
        parsed = BuiltQuery(q)
        if not parsed.is_valid:
            logger.debug('cannot restore query, invalid')
            return

        # locate domain in list of valid domains
        try:
            index = sorted(self.domain_map.keys()).index(parsed.domain)
        except ValueError as e:
            logger.debug('cannot restore query, %s(%s)' % (type(e), e))
            return
        # and set the domain_combo correspondently
        self.view.widgets.domain_combo.set_active(index)

        # now scan all clauses, one ExpressionRow per clause
        for clause in parsed.clauses:
            if clause.connector:
                self.on_add_clause()
            row = self.expression_rows[-1]
            if clause.connector:
                row.and_or_combo.set_active({'and': 0, 'or': 1}[clause.connector])

            # the part about the value is a bit more complex: where the
            # clause.field leads to an enumerated property, on_add_clause
            # associates a gkt.ComboBox to it, otherwise a Gtk.Entry.
            # To set the value of a gkt.ComboBox we match one of its
            # items. To set the value of a gkt.Entry we need set_text.
            steps = clause.field.split('.')
            cls = self.domain_map[parsed.domain]
            mapper = class_mapper(cls)
            for target in steps[:-1]:
                mapper = mapper.get_property(target).mapper
            prop = mapper.get_property(steps[-1])
            row.on_schema_menu_activated(None, clause.field, prop)
            if isinstance(row.value_widget, Gtk.Entry):
                row.value_widget.set_text(clause.value)
            elif isinstance(row.value_widget, Gtk.ComboBox):
                for item in row.value_widget.props.model:
                    if item[0] == clause.value:
                        row.value_widget.set_active_iter(item.iter)
                        break
            row.cond_combo.set_active(row.conditions.index(clause.operator))
