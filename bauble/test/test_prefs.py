# -*- coding: utf-8 -*-
#
# Copyright (c) 2005,2006,2007,2008,2009 Brett Adams <brett@belizebotanic.org>
# Copyright (c) 2012-2015 Mario Frasca <mario@anche.no>
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
logger = logging.getLogger(__name__)


from bauble.test import BaubleTestCase
from bauble import prefs
from tempfile import mkstemp
from bauble import version_tuple


prefs.testing = True


class PreferencesTests(BaubleTestCase):

    def test_create_does_not_save(self):
        handle, pname = mkstemp(suffix='.dict')
        p = prefs._prefs(pname)
        p.init()
        with open(pname) as f:
            self.assertEquals(f.read(), '')

    def test_assert_initial_values(self):
        handle, pname = mkstemp(suffix='.dict')
        p = prefs._prefs(pname)
        p.init()
        self.assertTrue(prefs.config_version_pref in p)
        self.assertTrue(prefs.picture_root_pref in p)
        self.assertTrue(prefs.date_format_pref in p)
        self.assertTrue(prefs.parse_dayfirst_pref in p)
        self.assertTrue(prefs.parse_yearfirst_pref in p)
        self.assertTrue(prefs.units_pref in p)
        self.assertEquals(p[prefs.config_version_pref], version_tuple[:2])
        self.assertEquals(p[prefs.picture_root_pref], '')
        self.assertEquals(p[prefs.date_format_pref], '%d-%m-%Y')
        self.assertEquals(p[prefs.parse_dayfirst_pref], True)
        self.assertEquals(p[prefs.parse_yearfirst_pref], False)
        self.assertEquals(p[prefs.units_pref], 'metric')

    def test_not_saved_while_testing(self):
        handle, pname = mkstemp(suffix='.dict')
        p = prefs._prefs(pname)
        p.init()
        p.save()
        with open(pname) as f:
            self.assertEquals(f.read(), '')

    def test_can_force_save(self):
        handle, pname = mkstemp(suffix='.dict')
        p = prefs._prefs(pname)
        p.init()
        p.save(force=True)
        with open(pname) as f:
            self.assertFalse(f.read() == '')

    def test_get_does_not_store_values(self):
        handle, pname = mkstemp(suffix='.dict')
        p = prefs._prefs(pname)
        p.init()
        self.assertFalse('not_there_yet.1' in p)
        self.assertIsNone(p['not_there_yet.1'])
        self.assertEquals(p.get('not_there_yet.2', 33), 33)
        self.assertIsNone(p.get('not_there_yet.3', None))
        self.assertFalse('not_there_yet.1' in p)
        self.assertFalse('not_there_yet.2' in p)
        self.assertFalse('not_there_yet.3' in p)
        self.assertFalse('not_there_yet.4' in p)

    def test_use___setitem___to_store_value_and_create_section(self):
        handle, pname = mkstemp(suffix='.dict')
        p = prefs._prefs(pname)
        p.init()
        self.assertFalse('test.not_there_yet-1' in p)
        p['test.not_there_yet-1'] = 'all is a ball'
        self.assertTrue('test.not_there_yet-1' in p)
        self.assertEquals(p['test.not_there_yet-1'], 'all is a ball')
        self.assertEquals(p.get('test.not_there_yet-1', 33), 'all is a ball')

    def test_most_values_converted_to_string(self):
        handle, pname = mkstemp(suffix='.dict')
        p = prefs._prefs(pname)
        p.init()
        self.assertFalse('test.not_there_yet-1' in p)
        p['test.not_there_yet-1'] = 1
        self.assertTrue('test.not_there_yet-1' in p)
        self.assertEquals(p['test.not_there_yet-1'], '1')
        # is the following really useful?
        p['test.not_there_yet-3'] = None
        self.assertEquals(p['test.not_there_yet-3'], 'None')

    def test_boolean_values_stay_boolean(self):
        handle, pname = mkstemp(suffix='.dict')
        p = prefs._prefs(pname)
        p.init()
        self.assertFalse('test.not_there_yet-1' in p)
        p['test.not_there_yet-1'] = True
        self.assertEquals(p['test.not_there_yet-1'], True)
        p['test.not_there_yet-2'] = False
        self.assertEquals(p['test.not_there_yet-2'], False)

    def test_saved_dictionary_like_ini_file(self):
        handle, pname = mkstemp(suffix='.dict')
        p = prefs._prefs(pname)
        p.init()
        self.assertFalse('test.not_there_yet-1' in p)
        p['test.not_there_yet-1'] = 1
        self.assertTrue('test.not_there_yet-1' in p)
        p.save(force=True)
        with open(pname) as f:
            content = f.read()
            self.assertTrue(content.index('not_there_yet-1 = 1') > 0)
            self.assertTrue(content.index('[test]') > 0)
