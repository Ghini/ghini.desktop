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
#
# test for bauble.meta
#

import bauble.meta as meta
from bauble.test import BaubleTestCase


class MetaTests(BaubleTestCase):

    def __init__(self, *args):
        super().__init__(*args)


    def test_get_default(self):
        """
        Test bauble.meta.get_default()
        """
        # test the object isn't created if it doesn't exist and we
        # don't pass a default value
        name = 'name'
        obj = meta.get_default(name)
        self.assertTrue(obj is None)

        # test that the obj is created if it doesn't exists and that
        # the default value is set
        value = 'value'
        meta.get_default(name, default=value)
        obj = self.session.query(meta.BaubleMeta).filter_by(name=name).one()
        self.assertTrue(obj.value == value)

        # test that the value isn't changed if it already exists
        value2 = 'value2'
        obj = meta.get_default(name, default=value2)
        self.assertTrue(obj.value == value)

        # test that if we pass our own session when we are creating a
        # new value that the object is added to the session but not committed
        obj = meta.get_default('name2', default=value, session=self.session)
        self.assertTrue(obj in self.session.new)
