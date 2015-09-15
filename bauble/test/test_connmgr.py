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
from bauble.editor import MockView


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


def diteglisempredisi(*args):
    return True
import bauble
import bauble.utils as utils
utils.yes_no_dialog = diteglisempredisi
import bauble.prefs as prefs
prefs.testing = True  # prevents overwriting


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
        prefs.prefs[bauble.conn_list_pref] = {}
        presenter = ConnMgrPresenter(view)

        self.assertFalse(presenter.view.widget_get_visible(
            'expander'))
        self.assertTrue(presenter.view.widget_get_visible(
            'noconnectionlabel'))

    def test_one_connection_shown_removed_message(self):
        view = MockView(combos={'name_combo': [],
                                'type_combo': []})
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
        prefs.prefs[bauble.conn_default_pref] = 'nugkui'
        prefs.prefs[bauble.conn_list_pref] = {
            'nugkui': {'type': 'SQLite',
                       'default': True,
                       'pictures': 'nugkui',
                       'file': 'nugkui.db'},
            'quisquis': {'type': 'PostgreSQL',
                         'passwd': False,
                         'pictures': '',
                         'db': 'quisquis',
                         'host': 'localhost',
                         'user': 'pg'}}
        presenter = ConnMgrPresenter(view)
        # T_0
        self.assertEquals(presenter.connection_name, 'nugkui')
        self.assertTrue(presenter.view.widget_get_visible(
            'sqlite_parambox'))
        # action
        view.widget_set_value('name_combo', 'quisquis')
        presenter.dbtype = 'PostgreSQL'  # who to trigger this in tests?
        presenter.on_name_combo_changed('name_combo')
        # result
        self.assertEquals(presenter.connection_name, 'quisquis')
        presenter.refresh_view()  # in reality this is triggered by gtk view
        self.assertEquals(presenter.dbtype, 'PostgreSQL')
        ## if the above succeeds, the following is riggered by the view!
        #presenter.on_combo_changed('type_combo', 'PostgreSQL')
        # T_1
        self.assertTrue(presenter.view.widget_get_visible(
            'dbms_parambox'))

    def test_set_default_toggles_sensitivity(self):
        view = MockView(combos={'name_combo': [],
                                'type_combo': []})
        prefs.prefs[bauble.conn_default_pref] = 'nugkui'
        prefs.prefs[bauble.conn_list_pref] = {
            'nugkui': {'type': 'SQLite',
                       'default': True,
                       'pictures': 'nugkui',
                       'file': 'nugkui.db'},
            }
        presenter = ConnMgrPresenter(view)
        view.widget_set_value('usedefaults_chkbx', True)
        presenter.on_usedefaults_chkbx_toggled('usedefaults_chkbx')
        self.assertFalse(view.widget_get_sensitive('file_entry'))
