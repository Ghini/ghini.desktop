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

    def get_widget_visible(self, name):
        return self.visible.get(name)

    def set_widget_visible(self, name, value=True):
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

        self.assertFalse(presenter.view.get_widget_visible(
            'sqlite_parambox'))
        self.assertFalse(presenter.view.get_widget_visible(
            'dbms_parambox'))
        self.assertTrue(presenter.view.get_widget_visible(
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
        self.assertTrue(presenter.view.get_widget_visible(
            'sqlite_parambox'))
        presenter.remove_connection('nugkui')
        self.assertTrue(presenter.view.get_widget_visible(
            'noconnectionlabel'))
