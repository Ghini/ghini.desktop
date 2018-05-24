# -*- coding: utf-8 -*-
#
# Copyright 2016 Mario Frasca <mario@anche.no>.
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


from nose import SkipTest

from bauble.plugins.plants.stored_queries import (
    StoredQueriesModel, StoredQueriesPresenter)
from bauble.test import BaubleTestCase
from bauble.editor import MockView

import bauble.prefs
bauble.prefs.testing = True


class StoredQueriesInitializeTests(BaubleTestCase):
    def test_initialize_model(self):
        m = StoredQueriesModel()
        for i in range(1, 9):
            self.assertEqual(m[i], '::')

    def test_initialize_has_defaults(self):
        m = StoredQueriesModel()
        for i in range(9, 11):
            self.assertNotEqual(m[i], '::')


class StoredQueriesTests(BaubleTestCase):
    def test_define_label(self):
        m = StoredQueriesModel()
        m.label = 'n=1'
        self.assertEqual(m.label, 'n=1')
        m.page = 2
        self.assertEqual(m.label, '')
        m.label = 'n=2'
        self.assertEqual(m.label, 'n=2')
        m.page = 1
        self.assertEqual(m.label, 'n=1')

    def test_define_tooltip(self):
        m = StoredQueriesModel()
        m.tooltip = 'n=1'
        self.assertEqual(m.tooltip, 'n=1')
        m.page = 2
        self.assertEqual(m.tooltip, '')
        m.tooltip = 'n=2'
        self.assertEqual(m.tooltip, 'n=2')
        m.page = 1
        self.assertEqual(m.tooltip, 'n=1')

    def test_define_query(self):
        m = StoredQueriesModel()
        m.query = 'n=1'
        self.assertEqual(m.query, 'n=1')
        m.page = 2
        self.assertEqual(m.query, '')
        m.query = 'n=2'
        self.assertEqual(m.query, 'n=2')
        m.page = 1
        self.assertEqual(m.query, 'n=1')

    def test_loop(self):
        m = StoredQueriesModel()
        before = [i for i in m]

        m.page = 1
        m.label = 'l=1'
        m.tooltip = 't=1'
        m.query = 'q=1'
        m.page = 2
        m.label = 'l=2'
        m.tooltip = 't=2'
        m.query = 'q=2'

        after = [i for i in before]
        after[0] = 'l=1:t=1:q=1'
        after[1] = 'l=2:t=2:q=2'
        self.assertEqual(m[1], after[0])
        self.assertEqual(m[2], after[1])
        self.assertEqual(m[3], '::')

        self.assertEqual([i for i in m], after)

    def test_setgetitem(self):
        m = StoredQueriesModel()
        before = [i for i in m]
        m[1] = 'l:t:q'
        m[4] = 'l:t:q'
        after = [i for i in m]
        for i, v in enumerate(after):
            if i in [0, 3]:
                self.assertEqual(after[i], 'l:t:q')
            else:
                self.assertEqual(after[i], before[i])

    def test_save(self):
        m = StoredQueriesModel()
        m[1] = 'l:t:q'
        m[4] = 'l:t:q'
        m.save()
        n = StoredQueriesModel()
        self.assertEqual([i for i in n], [k for k in m])
        self.assertFalse(id(n) == id(m))

    def test_save_overwrite(self):
        m = StoredQueriesModel()
        m[1] = 'l:t:q'
        m[4] = 'l:t:q'
        m.save()
        n = StoredQueriesModel()
        n[5] = 'l:t:q'
        n.save()
        m = StoredQueriesModel()
        self.assertEqual([i for i in n], [k for k in m])
        self.assertFalse(id(n) == id(m))


class StoredQueriesPresenterTests(BaubleTestCase):

    def test_create_presenter(self):
        view = MockView()
        m = StoredQueriesModel()
        presenter = StoredQueriesPresenter(m, view)
        self.assertEqual(presenter.view, view)
        self.assertEqual(id(presenter.model), id(m))

    def test_change_page(self):
        view = MockView()
        m = StoredQueriesModel()
        presenter = StoredQueriesPresenter(m, view)
        m.page = 2
        presenter.refresh_view()
        for i in range(1, 11):
            bname = 'stqr_%02d_button' % i
            self.assertTrue(('widget_set_active', (bname, i == m.page)) in
                            presenter.view.invoked_detailed)
            lname = 'stqr_%02d_label' % i
            self.assertTrue(('widget_set_attributes',
                             (lname, presenter.weight[i == m.page])) in
                            presenter.view.invoked_detailed)

    def test_next_page(self):
        view = MockView()
        m = StoredQueriesModel()
        presenter = StoredQueriesPresenter(m, view)
        self.assertEqual(m.page, 1)
        presenter.on_next_button_clicked(None)
        self.assertEqual(m.page, 2)
        presenter.on_next_button_clicked(None)
        self.assertEqual(m.page, 3)

    def test_prev_page(self):
        view = MockView()
        m = StoredQueriesModel()
        presenter = StoredQueriesPresenter(m, view)
        self.assertEqual(m.page, 1)
        presenter.on_prev_button_clicked(None)
        self.assertEqual(m.page, 10)
        presenter.on_prev_button_clicked(None)
        self.assertEqual(m.page, 9)

    def test_select_page(self):
        view = MockView()
        m = StoredQueriesModel()
        presenter = StoredQueriesPresenter(m, view)
        self.assertEqual(m.page, 1)
        bname = 'stqr_05_button'
        presenter.on_button_clicked(bname)
        self.assertEqual(m.page, 5)
        self.assertTrue(('widget_set_active', (bname, True)) in
                        presenter.view.invoked_detailed)
        self.assertTrue(('widget_set_active', ('stqr_01_button', False)) in
                        presenter.view.invoked_detailed)

    def test_label_entry_change(self):
        view = MockView()
        m = StoredQueriesModel()
        presenter = StoredQueriesPresenter(m, view)
        bname = 'stqr_04_button'
        presenter.on_button_clicked(bname)
        self.assertEqual(m.page, 4)
        presenter.view.values['stqr_label_entry'] = 'abc'
        presenter.on_label_entry_changed('stqr_label_entry')
        print(presenter.view.invoked_detailed)
        self.assertEqual(m.label, 'abc')
        self.assertTrue(('widget_set_text', ('stqr_04_label', 'abc')) in
                        presenter.view.invoked_detailed)
        presenter.view.values['stqr_label_entry'] = ''
        presenter.on_label_entry_changed('stqr_label_entry')
        self.assertEqual(m.label, '')
        self.assertTrue(('widget_set_text', ('stqr_04_label', '<empty>')) in
                        presenter.view.invoked_detailed)
