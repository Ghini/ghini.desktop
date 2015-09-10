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
    def __init__(self):
        self.widgets = type('MockWidgets', (object, ), {})

    def connect_signals(self, *args):
        pass

    def set_label(self, *args):
        pass

    def connect_after(self, *args):
        pass

    def get_widget_value(self, *args):
        pass

    def connect(self, *args):
        pass


class ConnMgrPresenterTests(BaubleTestCase):
    'Presenter manages view and model, implements view callbacks.'

    def test_can_create_presenter(self):
        view = MockView()
        ConnMgrPresenter(self, view)
