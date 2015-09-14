# -*- coding: utf-8 -*-
#
# Copyright (c) 2015 Mario Frasca <mario@anche.no>
#
# This file is part of bauble.classic.
#
# bauble.classic is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# bauble.classic is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bauble.classic. If not, see <http://www.gnu.org/licenses/>.

import os

from nose import SkipTest

from bauble.test import BaubleTestCase, check_dupids
from bauble.connmgr import ConnMgrPresenter


def test_duplicate_ids():
    """
    Test for duplicate ids for all .glade files in the tag plugin.
    """
    import bauble.connmgr as mod
    head, tail = os.path.split(mod.__file__)
    assert(not check_dupids(os.path.join(head, 'connmgr.glade')))


class TagTests(BaubleTestCase):

    family_ids = [1, 2]

    def setUp(self):
        pass

    def tearDown(self):
        pass


class MockView:
    def __init__(self, **kwargs):
        self.widgets = type('MockWidgets', (object, ), {})
        self.visible = {}
        for name, value in kwargs.items():
            setattr(self, name, value)

    def image_set_from_file(self, *args):
        pass

    def set_title(self, *args):
        pass

    def set_icon(self, *args):
        pass

    def image_set_from_file(self, *args):
        pass

    def combobox_init(self, *args):
        pass

    def connect_signals(self, *args):
        pass

    def set_label(self, *args):
        pass

    def connect_after(self, *args):
        pass

    def widget_get_value(self, *args):
        pass

    def widget_set_value(self, *args):
        pass

    def connect(self, *args):
        pass

    def widget_get_visible(self, name):
        return self.visible.get(name)

    def widget_set_visible(self, name, value=True):
        self.visible[name] = value

    def combobox_remove(self, name, item):
        model = self.combos[name]
        if isinstance(item, int):
            del model[item]
        else:
            model.remove(item)

    def combobox_append_text(self, name, value):
        model = self.combos[name]
        model.append(value)

    def set_accept_buttons_sensitive(self, sensitive=True):
        pass


class ConnMgrPresenterTests(BaubleTestCase):
    'Presenter manages view and model, implements view callbacks.'

    def test_can_create_presenter(self):
        view = MockView(combos={'name_combo': [],
                                'type_combo': []})
        presenter = ConnMgrPresenter(view)
        self.assertEquals(presenter.view, view)

    def test_no_connections_then_message(self):
        view = MockView(combos={'name_combo': [],
                                'type_combo': []})
        import bauble
        import bauble.prefs as prefs
        prefs.prefs[bauble.conn_list_pref] = {}
        presenter = ConnMgrPresenter(view)

        self.assertFalse(presenter.view.widget_get_visible(
            'expander'))
        self.assertTrue(presenter.view.widget_get_visible(
            'noconnectionlabel'))

    def test_one_connection_shown_removed_message(self):
        view = MockView(combos={'name_combo': [],
                                'type_combo': []})
        import bauble
        import bauble.prefs as prefs
        prefs.prefs[bauble.conn_list_pref] = {
            'nugkui': {'default': True,
                       'pictures': 'nugkui',
                       'type': 'SQLite',
                       'file': 'nugkui.db'}}
        presenter = ConnMgrPresenter(view)
        # T_0
        self.assertTrue(presenter.view.widget_get_visible(
            'expander'))
        self.assertFalse(presenter.view.widget_get_visible(
            'noconnectionlabel'))
        # action
        presenter.remove_connection('nugkui')
        # T_1
        self.assertTrue(presenter.view.widget_get_visible(
            'noconnectionlabel'))
        self.assertFalse(presenter.view.widget_get_visible(
            'expander'))

    def test_one_connection_shown_and_selected_sqlite(self):
        view = MockView(combos={'name_combo': [],
                                'type_combo': []})
        import bauble
        import bauble.prefs as prefs
        prefs.prefs[bauble.conn_list_pref] = {
            'nugkui': {'default': True,
                       'pictures': 'nugkui',
                       'type': 'SQLite',
                       'file': 'nugkui.db'}}
        prefs.prefs[bauble.conn_default_pref] = 'nugkui'
        presenter = ConnMgrPresenter(view)
        self.assertEquals(presenter.connection_name, 'nugkui')
        self.assertTrue(presenter.view.widget_get_visible(
            'expander'))
        self.assertFalse(presenter.view.widget_get_visible(
            'noconnectionlabel'))

    def test_one_connection_shown_and_selected_postgresql(self):
        view = MockView(combos={'name_combo': [],
                                'type_combo': []})
        import bauble
        import bauble.prefs as prefs
        prefs.prefs[bauble.conn_list_pref] = {
            'quisquis': {'passwd': False,
                         'pictures': '',
                         'db': 'quisquis',
                         'host': 'localhost',
                         'user': 'pg',
                         'type': 'PostgreSQL'}}
        prefs.prefs[bauble.conn_default_pref] = 'quisquis'
        presenter = ConnMgrPresenter(view)
        self.assertEquals(presenter.connection_name, 'quisquis')
        self.assertTrue(presenter.view.widget_get_visible(
            'expander'))
        self.assertTrue(presenter.view.widget_get_visible(
            'dbms_parambox'))
        self.assertFalse(presenter.view.widget_get_visible(
            'sqlite_parambox'))
        self.assertFalse(presenter.view.widget_get_visible(
            'noconnectionlabel'))

    def test_one_connection_shown_and_selected_oracle(self):
        view = MockView(combos={'name_combo': [],
                                'type_combo': []})
        import bauble
        import bauble.prefs as prefs
        prefs.prefs[bauble.conn_list_pref] = {
            'quisquis': {'passwd': False,
                         'pictures': '',
                         'db': 'quisquis',
                         'host': 'localhost',
                         'user': 'pg',
                         'type': 'Oracle'}}
        prefs.prefs[bauble.conn_default_pref] = 'quisquis'
        presenter = ConnMgrPresenter(view)
        self.assertEquals(presenter.connection_name, 'quisquis')
        self.assertTrue(presenter.view.widget_get_visible(
            'expander'))
        self.assertTrue(presenter.view.widget_get_visible(
            'dbms_parambox'))
        self.assertFalse(presenter.view.widget_get_visible(
            'sqlite_parambox'))
        self.assertFalse(presenter.view.widget_get_visible(
            'noconnectionlabel'))

    def test_two_connections_wrong_default_use_first_one(self):
        view = MockView(combos={'name_combo': [],
                                'type_combo': []})
        import bauble
        import bauble.prefs as prefs
        prefs.prefs[bauble.conn_default_pref] = 'nugkui'
        prefs.prefs[bauble.conn_list_pref] = {
            'nugkui': {'default': True,
                       'pictures': 'nugkui',
                       'type': 'SQLite',
                       'file': 'nugkui.db'},
            'quisquis': {'passwd': False,
                         'pictures': '',
                         'db': 'quisquis',
                         'host': 'localhost',
                         'user': 'pg',
                         'type': 'Oracle'}}
        prefs.prefs[bauble.conn_default_pref] = 'nonce'
        presenter = ConnMgrPresenter(view)
        as_list = presenter.connection_names
        self.assertEquals(presenter.connection_name, as_list[0])

    def test_when_user_selects_different_type(self):
        view = MockView(combos={'name_combo': [],
                                'type_combo': []})
        import bauble
        import bauble.prefs as prefs
        prefs.prefs[bauble.conn_default_pref] = 'nugkui'
        prefs.prefs[bauble.conn_list_pref] = {
            'nugkui': {'default': True,
                       'pictures': 'nugkui',
                       'type': 'SQLite',
                       'file': 'nugkui.db'},
            'quisquis': {'passwd': False,
                         'pictures': '',
                         'db': 'quisquis',
                         'host': 'localhost',
                         'user': 'pg',
                         'type': 'Oracle'}}
        presenter = ConnMgrPresenter(view)
        # T_0
        self.assertEquals(presenter.connection_name, 'nugkui')
        self.assertTrue(presenter.view.widget_get_visible(
            'sqlite_parambox'))
        # action
        presenter.on_combo_changed('name_combo', 'quisquis')
        ## in reality, this ist riggered by the view!
        presenter.on_combo_changed('type_combo', 'Oracle')
        # T_1
        self.assertEquals(presenter.connection_name, 'quisquis')
        self.assertTrue(presenter.view.widget_get_visible(
            'dbms_parambox'))
