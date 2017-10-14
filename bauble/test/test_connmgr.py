# -*- coding: utf-8 -*-
#
# Copyright (c) 2015 Mario Frasca <mario@anche.no>
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

import os

## just keeping it here because I am forgetful and I never recall how to
## import SkipTest otherwise! and commented out because of FlyCheck.
from nose import SkipTest

from bauble.test import BaubleTestCase, check_dupids
from bauble.connmgr import ConnMgrPresenter
from bauble.editor import MockView, MockDialog
from gtk import RESPONSE_OK, RESPONSE_CANCEL


def test_duplicate_ids():
    """
    Test for duplicate ids for all .glade files in the tag plugin.
    """
    import bauble.connmgr as mod
    head, tail = os.path.split(mod.__file__)
    assert(not check_dupids(os.path.join(head, 'connmgr.glade')))


import bauble
import bauble.prefs as prefs
prefs.testing = True


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

    def test_one_connection_on_remove_confirm_negative(self):
        view = MockView(combos={'name_combo': [],
                                'type_combo': []})
        prefs.prefs[bauble.conn_list_pref] = {
            'nugkui': {'default': True,
                       'pictures': 'nugkui',
                       'type': 'SQLite',
                       'file': 'nugkui.db'}}
        presenter = ConnMgrPresenter(view)
        presenter.view.reply_yes_no_dialog.append(False)
        presenter.on_remove_button_clicked('button')
        ## nothing changes
        self.assertTrue(presenter.view.widget_get_visible(
            'expander'))
        self.assertFalse(presenter.view.widget_get_visible(
            'noconnectionlabel'))

    def test_one_connection_on_remove_confirm_positive(self):
        view = MockView(combos={'name_combo': [],
                                'type_combo': []})
        prefs.prefs[bauble.conn_list_pref] = {
            'nugkui': {'default': True,
                       'pictures': 'nugkui',
                       'type': 'SQLite',
                       'file': 'nugkui.db'}}
        presenter = ConnMgrPresenter(view)
        presenter.view.reply_yes_no_dialog.append(True)
        presenter.on_remove_button_clicked('button')
        ## visibility swapped
        self.assertFalse(presenter.view.widget_get_visible(
            'expander'))
        self.assertTrue(presenter.view.widget_get_visible(
            'noconnectionlabel'))

    def test_two_connection_initialize_default_first(self):
        view = MockView(combos={'name_combo': [],
                                'type_combo': []})
        prefs.prefs[bauble.conn_list_pref] = {
            'nugkui': {'default': True,
                       'pictures': 'nugkui',
                       'type': 'SQLite',
                       'file': 'nugkui.db'},
            'btuu': {'default': False,
                     'pictures': 'btuu',
                     'type': 'SQLite',
                     'file': 'btuu.db'}}
        prefs.prefs[bauble.conn_default_pref] = 'nugkui'
        presenter = ConnMgrPresenter(view)
        self.assertEquals(presenter.connection_name, 'nugkui')
        params = presenter.connections[presenter.connection_name]
        self.assertEquals(params['default'], True)
        self.assertTrue(view.widget_get_value('usedefaults_chkbx'))

    def test_two_connection_initialize_default_second(self):
        view = MockView(combos={'name_combo': [],
                                'type_combo': []})
        prefs.prefs[bauble.conn_list_pref] = {
            'nugkui': {'default': True,
                       'pictures': 'nugkui',
                       'type': 'SQLite',
                       'file': 'nugkui.db'},
            'btuu': {'default': False,
                     'pictures': 'btuu',
                     'type': 'SQLite',
                     'file': 'btuu.db'}}
        prefs.prefs[bauble.conn_default_pref] = 'bruu'
        presenter = ConnMgrPresenter(view)
        self.assertEquals(presenter.connection_name, 'btuu')
        params = presenter.connections[presenter.connection_name]
        self.assertEquals(params['default'], False)
        self.assertFalse(view.widget_get_value('usedefaults_chkbx'))

    def test_two_connection_on_remove_confirm_positive(self):
        view = MockView(combos={'name_combo': [],
                                'type_combo': []})
        prefs.prefs[bauble.conn_list_pref] = {
            'nugkui': {'default': True,
                       'pictures': 'nugkui',
                       'type': 'SQLite',
                       'file': 'nugkui.db'},
            'btuu': {'default': True,
                     'pictures': 'btuu',
                     'type': 'SQLite',
                     'file': 'btuu.db'}}
        presenter = ConnMgrPresenter(view)
        presenter.view.reply_yes_no_dialog.append(True)
        presenter.on_remove_button_clicked('button')
        ## visibility same
        self.assertTrue(presenter.view.widget_get_visible(
            'expander'))
        self.assertFalse(presenter.view.widget_get_visible(
            'noconnectionlabel'))
        self.assertTrue('combobox_set_active' in view.invoked)

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

    def test_check_parameters_valid(self):
        import copy
        view = MockView(combos={'name_combo': [],
                                'type_combo': []})
        prefs.prefs[bauble.conn_default_pref] = 'quisquis'
        prefs.prefs[bauble.conn_list_pref] = {
            'quisquis': {'type': 'PostgreSQL',
                         'passwd': False,
                         'pictures': '/tmp/',
                         'db': 'quisquis',
                         'host': 'localhost',
                         'user': 'pg'}}
        presenter = ConnMgrPresenter(view)
        params = presenter.connections['quisquis']
        valid, message = presenter.check_parameters_valid(params)
        self.assertTrue(valid)
        params = copy.copy(presenter.connections['quisquis'])
        params['user'] = ''
        valid, message = presenter.check_parameters_valid(params)
        self.assertFalse(valid)
        params = copy.copy(presenter.connections['quisquis'])
        params['db'] = ''
        valid, message = presenter.check_parameters_valid(params)
        self.assertFalse(valid)
        params = copy.copy(presenter.connections['quisquis'])
        params['host'] = ''
        valid, message = presenter.check_parameters_valid(params)
        self.assertFalse(valid)
        sqlite_params = {'type': 'SQLite',
                         'default': False,
                         'file': '/tmp/test.db',
                         'pictures': '/tmp/'}
        params = copy.copy(sqlite_params)
        valid, message = presenter.check_parameters_valid(params)
        self.assertTrue(valid)
        params = copy.copy(sqlite_params)
        params['file'] = '/usr/bin/sh'
        valid, message = presenter.check_parameters_valid(params)
        self.assertFalse(valid)

    def test_parameters_to_uri_sqlite(self):
        view = MockView(combos={'name_combo': [],
                                'type_combo': []})
        prefs.prefs[bauble.conn_default_pref] = None
        prefs.prefs[bauble.conn_list_pref] = {}
        presenter = ConnMgrPresenter(view)
        params = {'type': 'SQLite',
                  'default': False,
                  'file': '/tmp/test.db',
                  'pictures': '/tmp/'}
        self.assertEquals(presenter.parameters_to_uri(params),
                          'sqlite:////tmp/test.db')
        params = {'type': 'PostgreSQL',
                  'passwd': False,
                  'pictures': '/tmp/',
                  'db': 'quisquis',
                  'host': 'localhost',
                  'user': 'pg'}
        self.assertEquals(presenter.parameters_to_uri(params),
                          'postgresql://pg@localhost/quisquis')
        params = {'type': 'PostgreSQL',
                  'passwd': True,
                  'pictures': '/tmp/',
                  'db': 'quisquis',
                  'host': 'localhost',
                  'user': 'pg'}
        view.reply_entry_dialog.append('secret')
        self.assertEquals(presenter.parameters_to_uri(params),
                          'postgresql://pg:secret@localhost/quisquis')
        params = {'type': 'PostgreSQL',
                  'passwd': False,
                  'pictures': '/tmp/',
                  'port': '9876',
                  'db': 'quisquis',
                  'host': 'localhost',
                  'user': 'pg'}
        self.assertEquals(presenter.parameters_to_uri(params),
                          'postgresql://pg@localhost:9876/quisquis')
        params = {'type': 'PostgreSQL',
                  'passwd': True,
                  'pictures': '/tmp/',
                  'port': '9876',
                  'db': 'quisquis',
                  'host': 'localhost',
                  'user': 'pg'}
        view.reply_entry_dialog.append('secret')
        self.assertEquals(presenter.parameters_to_uri(params),
                          'postgresql://pg:secret@localhost:9876/quisquis')
        params = {'type': 'PostgreSQL',
                  'passwd': False,
                  'pictures': '/tmp/',
                  'options': ['is_this_possible=no',
                              'why_do_we_test=because'],
                  'db': 'quisquis',
                  'host': 'localhost',
                  'user': 'pg'}
        self.assertEquals(presenter.parameters_to_uri(params),
                          'postgresql://pg@localhost/quisquis?'
                          'is_this_possible=no&why_do_we_test=because')

    def test_connection_uri_property(self):
        view = MockView(combos={'name_combo': [],
                                'type_combo': []})
        prefs.prefs[bauble.conn_default_pref] = 'quisquis'
        prefs.prefs[bauble.conn_list_pref] = {
            'quisquis': {'type': 'PostgreSQL',
                         'passwd': False,
                         'pictures': '/tmp/',
                         'db': 'quisquis',
                         'host': 'localhost',
                         'user': 'pg'}}
        presenter = ConnMgrPresenter(view)
        self.assertEquals(presenter.connection_name, 'quisquis')
        self.assertEquals(presenter.dbtype, 'PostgreSQL')
        ## we need trigger all signals that would go by gtk
        p = presenter.connections[presenter.connection_name]
        presenter.view.widget_set_value('database_entry', p['db'])
        presenter.on_text_entry_changed('database_entry')
        presenter.view.widget_set_value('user_entry', p['user'])
        presenter.on_text_entry_changed('user_entry')
        presenter.view.widget_set_value('host_entry', p['host'])
        presenter.on_text_entry_changed('host_entry')
        self.assertEquals(presenter.connection_uri,
                          'postgresql://pg@localhost/quisquis')


class AddConnectionTests(BaubleTestCase):

    def test_no_connection_on_add_confirm_negative(self):
        view = MockView(combos={'name_combo': [],
                                'type_combo': []})
        prefs.prefs[bauble.conn_list_pref] = {}
        presenter = ConnMgrPresenter(view)
        presenter.view.reply_entry_dialog.append('')
        presenter.on_add_button_clicked('button')
        ## nothing changes
        self.assertFalse(presenter.view.widget_get_visible(
            'expander'))
        self.assertFalse(presenter.view.widget_get_sensitive(
            'connect_button'))
        self.assertTrue(presenter.view.widget_get_visible(
            'noconnectionlabel'))

    def test_no_connection_on_add_confirm_positive(self):
        view = MockView(combos={'name_combo': [],
                                'type_combo': []})
        prefs.prefs[bauble.conn_list_pref] = {}
        presenter = ConnMgrPresenter(view)
        presenter.view.reply_entry_dialog.append('conn_name')
        presenter.on_add_button_clicked('button')
        presenter.refresh_view()  # this is done by gtk
        ## visibility swapped
        self.assertTrue(presenter.view.widget_get_visible(
            'expander'))
        self.assertTrue(presenter.view.widget_get_sensitive(
            'connect_button'))
        self.assertFalse(presenter.view.widget_get_visible(
            'noconnectionlabel'))

    def test_one_connection_on_add_confirm_positive(self):
        view = MockView(combos={'name_combo': [],
                                'type_combo': []})
        prefs.prefs[bauble.conn_list_pref] = {
            'nugkui': {'default': True,
                       'pictures': 'nugkui',
                       'type': 'SQLite',
                       'file': 'nugkui.db'}}
        prefs.prefs[bauble.conn_default_pref] = 'nugkui'
        presenter = ConnMgrPresenter(view)
        presenter.view.reply_entry_dialog.append('new_conn')
        presenter.on_add_button_clicked('button')
        presenter.refresh_view()  # this is done by gtk
        self.assertTrue(('combobox_prepend_text', ['name_combo', 'new_conn'])
                        in presenter.view.invoked_detailed)
        self.assertTrue(('widget_set_value', ['name_combo', 'new_conn', ()])
                        in presenter.view.invoked_detailed)
        print presenter.view.invoked_detailed
        raise SkipTest("related to issue #194")


class MockRenderer(dict):
    def set_property(self, property, value):
        self[property] = value


class GlobalFunctionsTests(BaubleTestCase):
    'Presenter manages view and model, implements view callbacks.'
    def test_combo_cell_data_func(self):
        import bauble.connmgr
        wt, at = bauble.connmgr.working_dbtypes, bauble.connmgr.dbtypes
        bauble.connmgr.working_dbtypes = ['a', 'd']
        bauble.connmgr.dbtypes = ['a', 'b', 'c', 'd']

        renderer = MockRenderer()
        for iter, name in enumerate(bauble.connmgr.dbtypes):
            bauble.connmgr.type_combo_cell_data_func(
                None, renderer, bauble.connmgr.dbtypes, iter)
            self.assertEquals(renderer['sensitive'],
                              name in bauble.connmgr.working_dbtypes)
            self.assertEquals(renderer['text'], name)

        bauble.connmgr.working_dbtypes, bauble.connmgr.dbtypes = wt, at

    def test_is_package_name(self):
        from bauble.connmgr import is_package_name
        self.assertTrue(is_package_name("sqlite3"))
        self.assertFalse(is_package_name("sqlheavy42"))


class ButtonBrowseButtons(BaubleTestCase):
    def test_file_chosen(self):
        view = MockView(combos={'name_combo': [],
                                'type_combo': []})
        view.reply_file_chooser_dialog.append('chosen')
        presenter = ConnMgrPresenter(view)
        presenter.on_file_btnbrowse_clicked()
        presenter.on_text_entry_changed('file_entry')
        self.assertEquals(presenter.filename, 'chosen')

    def test_file_not_chosen(self):
        view = MockView(combos={'name_combo': [],
                                'type_combo': []})
        view.reply_file_chooser_dialog = []
        presenter = ConnMgrPresenter(view)
        presenter.filename = 'previously'
        presenter.on_file_btnbrowse_clicked()
        self.assertEquals(presenter.filename, 'previously')

    def test_pictureroot_chosen(self):
        view = MockView(combos={'name_combo': [],
                                'type_combo': []})
        view.reply_file_chooser_dialog.append('chosen')
        presenter = ConnMgrPresenter(view)
        presenter.on_pictureroot_btnbrowse_clicked()
        presenter.on_text_entry_changed('pictureroot_entry')
        self.assertEquals(presenter.pictureroot, 'chosen')

    def test_pictureroot_not_chosen(self):
        view = MockView(combos={'name_combo': [],
                                'type_combo': []})
        view.reply_file_chooser_dialog = []
        presenter = ConnMgrPresenter(view)
        presenter.pictureroot = 'previously'
        presenter.on_pictureroot_btnbrowse_clicked()
        self.assertEquals(presenter.pictureroot, 'previously')

    def test_pictureroot2_chosen(self):
        view = MockView(combos={'name_combo': [],
                                'type_combo': []})
        view.reply_file_chooser_dialog.append('chosen')
        presenter = ConnMgrPresenter(view)
        presenter.on_pictureroot2_btnbrowse_clicked()
        presenter.on_text_entry_changed('pictureroot2_entry')
        self.assertEquals(presenter.pictureroot, 'chosen')

    def test_pictureroot2_not_chosen(self):
        view = MockView(combos={'name_combo': [],
                                'type_combo': []})
        view.reply_file_chooser_dialog = []
        presenter = ConnMgrPresenter(view)
        presenter.pictureroot = 'previously'
        presenter.on_pictureroot2_btnbrowse_clicked()
        self.assertEquals(presenter.pictureroot, 'previously')


class OnDialogResponseTests(BaubleTestCase):
    def test_on_dialog_response_ok_invalid_params(self):
        view = MockView(combos={'name_combo': [],
                                'type_combo': []})
        prefs.prefs[bauble.conn_list_pref] = {}
        view.reply_file_chooser_dialog = []
        presenter = ConnMgrPresenter(view)
        dialog = MockDialog()
        presenter.on_dialog_response(dialog, RESPONSE_OK)
        self.assertTrue('run_message_dialog' in view.invoked)
        self.assertTrue(dialog.hidden)

    def test_on_dialog_response_ok_valid_params(self):
        view = MockView(combos={'name_combo': [],
                                'type_combo': []})
        prefs.prefs[bauble.conn_list_pref] = {
            'nugkui': {'default': False,
                       'pictures': '/tmp/nugkui',
                       'type': 'SQLite',
                       'file': '/tmp/nugkui.db'}}
        prefs.prefs[bauble.conn_default_pref] = 'nugkui'
        prefs.prefs[prefs.picture_root_pref] = '/tmp'
        view.reply_file_chooser_dialog = []
        presenter = ConnMgrPresenter(view)
        dialog = MockDialog()
        view.invoked = []
        presenter.on_dialog_response(dialog, RESPONSE_OK)
        self.assertFalse('run_message_dialog' in view.invoked)
        self.assertTrue(dialog.hidden)
        self.assertEquals(prefs.prefs[prefs.picture_root_pref], '/tmp/nugkui')

    def test_on_dialog_response_cancel(self):
        view = MockView(combos={'name_combo': [],
                                'type_combo': []})
        view.reply_file_chooser_dialog = []
        presenter = ConnMgrPresenter(view)
        dialog = MockDialog()
        view.reply_yes_no_dialog = [False]
        presenter.on_dialog_response(dialog, RESPONSE_CANCEL)
        self.assertFalse('run_message_dialog' in view.invoked)
        self.assertTrue(dialog.hidden)

    def test_on_dialog_response_cancel_params_changed(self):
        view = MockView(combos={'name_combo': [],
                                'type_combo': []})
        prefs.prefs[bauble.conn_list_pref] = {
            'nugkui': {'default': False,
                       'pictures': '/tmp/nugkui',
                       'type': 'SQLite',
                       'file': '/tmp/nugkui.db'}}
        prefs.prefs[bauble.conn_default_pref] = 'nugkui'
        view.reply_file_chooser_dialog = []
        presenter = ConnMgrPresenter(view)
        ## change something
        view.widget_set_value('usedefaults_chkbx', True)
        presenter.on_usedefaults_chkbx_toggled('usedefaults_chkbx')
        ## press escape
        dialog = MockDialog()
        view.reply_yes_no_dialog = [True]
        view.invoked = []
        presenter.on_dialog_response(dialog, RESPONSE_CANCEL)
        ## question was asked whether to save
        self.assertFalse('run_message_dialog' in view.invoked)
        self.assertTrue('run_yes_no_dialog' in view.invoked)
        self.assertTrue(dialog.hidden)

    def test_on_dialog_close_or_delete(self):
        view = MockView(combos={'name_combo': [],
                                'type_combo': []})
        view.reply_file_chooser_dialog = []
        presenter = ConnMgrPresenter(view)
        # T_0
        self.assertFalse(view.get_window().hidden)
        # action
        presenter.on_dialog_close_or_delete("widget")
        # T_1
        self.assertTrue(view.get_window().hidden)

    def test_on_dialog_response_ok_creates_picture_folders_exist(self):
        # make sure thumbnails and pictures folder already exist as folders.
        # create view and presenter
        # invoke action
        # superfluous action is not performed, view is closed
        raise SkipTest('related to issue 157')

    def test_on_dialog_response_ok_creates_picture_folders_half_exist(self):
        # make sure pictures and thumbs folders respectively do and do not
        # already exist as folders.
        import tempfile
        path = tempfile.mktemp()
        os.mkdir(path)
        view = MockView(combos={'name_combo': [],
                                'type_combo': []})
        prefs.prefs[bauble.conn_list_pref] = {
            'nugkui': {'default': False,
                       'pictures': path,
                       'type': 'SQLite',
                       'file': path + '.db'}}
        (prefs.prefs[prefs.picture_root_pref],
         prefs.prefs[bauble.conn_default_pref],
         ) = os.path.split(path)
        view.reply_file_chooser_dialog = []
        presenter = ConnMgrPresenter(view)
        dialog = MockDialog()
        view.invoked = []
        # invoke action
        presenter.on_dialog_response(dialog, RESPONSE_OK)

        # superfluous action is not performed, view is closed
        # check existence of pictures folder
        self.assertTrue(os.path.isdir(path))
        # check existence of thumbnails folder
        self.assertTrue(os.path.isdir(os.path.join(path, 'thumbs')))

    def test_on_dialog_response_ok_creates_picture_folders_no_exist(self):
        # make sure thumbnails and pictures folder do not exist.
        import tempfile
        path = tempfile.mktemp()
        # create view and presenter.
        view = MockView(combos={'name_combo': [],
                                'type_combo': []})
        prefs.prefs[bauble.conn_list_pref] = {
            'nugkui': {'default': False,
                       'pictures': path,
                       'type': 'SQLite',
                       'file': path + '.db'}}
        (prefs.prefs[prefs.picture_root_pref],
         prefs.prefs[bauble.conn_default_pref],
         ) = os.path.split(path)
        view.reply_file_chooser_dialog = []
        presenter = ConnMgrPresenter(view)
        dialog = MockDialog()
        view.invoked = []
        # invoke action
        presenter.on_dialog_response(dialog, RESPONSE_OK)

        # check existence of pictures folder
        self.assertTrue(os.path.isdir(path))
        # check existence of thumbnails folder
        self.assertTrue(os.path.isdir(os.path.join(path, 'thumbs')))

    def test_on_dialog_response_ok_creates_picture_folders_occupied(self):
        # make sure thumbnails and pictures folder already exist as files
        # create view and presenter
        # invoke action
        # action is not performed, view is not closed
        raise SkipTest('related to issue 157')
