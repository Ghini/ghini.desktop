# -*- coding: utf-8 -*-
#
# Copyright 2016 Mario Frasca <mario@anche.no>.
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

from nose import SkipTest

from bauble.plugins.plants.stored_queries import StoredQueriesModel
from bauble.test import BaubleTestCase

import bauble.prefs
bauble.prefs.testing = True


class StoredQueriesInitializeTests(BaubleTestCase):
    def test_initialize_model(self):
        m = StoredQueriesModel()
        for i in range(1, 11):
            self.assertEquals(m[i], '::')


class StoredQueriesTests(BaubleTestCase):
    def test_define_label(self):
        m = StoredQueriesModel()
        m.label = 'n=1'
        self.assertEquals(m.label, 'n=1')
        m.page = 2
        self.assertEquals(m.label, '')
        m.label = 'n=2'
        self.assertEquals(m.label, 'n=2')
        m.page = 1
        self.assertEquals(m.label, 'n=1')

    def test_define_tooltip(self):
        m = StoredQueriesModel()
        m.tooltip = 'n=1'
        self.assertEquals(m.tooltip, 'n=1')
        m.page = 2
        self.assertEquals(m.tooltip, '')
        m.tooltip = 'n=2'
        self.assertEquals(m.tooltip, 'n=2')
        m.page = 1
        self.assertEquals(m.tooltip, 'n=1')

    def test_define_query(self):
        m = StoredQueriesModel()
        m.query = 'n=1'
        self.assertEquals(m.query, 'n=1')
        m.page = 2
        self.assertEquals(m.query, '')
        m.query = 'n=2'
        self.assertEquals(m.query, 'n=2')
        m.page = 1
        self.assertEquals(m.query, 'n=1')

    def test_loop(self):
        m = StoredQueriesModel()
        m.page = 1
        m.label = 'l=1'
        m.tooltip = 't=1'
        m.query = 'q=1'
        m.page = 2
        m.label = 'l=2'
        m.tooltip = 't=2'
        m.query = 'q=2'

        self.assertEquals(m[1], 'l=1:t=1:q=1')
        self.assertEquals(m[2], 'l=2:t=2:q=2')
        self.assertEquals(m[3], '::')

        self.assertEquals([i for i in m], [u'l=1:t=1:q=1',
                                           u'l=2:t=2:q=2',
                                           u'::',
                                           u'::',
                                           u'::',
                                           u'::',
                                           u'::',
                                           u'::',
                                           u'::',
                                           u'::'])

    def test_setgetitem(self):
        m = StoredQueriesModel()
        m[1] = 'l:t:q'
        m[4] = 'l:t:q'
        self.assertEquals([i for i in m], [u'l:t:q',
                                           u'::',
                                           u'::',
                                           u'l:t:q',
                                           u'::',
                                           u'::',
                                           u'::',
                                           u'::',
                                           u'::',
                                           u'::'])

    def test_save(self):
        m = StoredQueriesModel()
        m[1] = 'l:t:q'
        m[4] = 'l:t:q'
        m.save()
        n = StoredQueriesModel()
        self.assertEquals([i for i in n], [k for k in m])
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
        self.assertEquals([i for i in n], [k for k in m])
        self.assertFalse(id(n) == id(m))
