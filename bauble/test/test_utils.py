# -*- coding: utf-8 -*-
#
# Copyright (c) 2005,2006,2007,2008,2009 Brett Adams <brett@belizebotanic.org>
# Copyright (c) 2012-2015 Mario Frasca <mario@anche.no>
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

import bauble.utils as utils
from bauble.test import BaubleTestCase

class Utils(BaubleTestCase):
    
    def test_topological_sort_total(self):
        self.assertEqual(utils.topological_sort([1,2,3], [(2,1), (3,2)]), [3, 2, 1])

    def test_topological_sort_partial(self):
        self.assertEqual(utils.topological_sort([1,2,3,4], [(2,1)]), [4, 3, 2, 1])

    def test_topological_sort_loop(self):
        self.assertEqual(utils.topological_sort([1,2], [(2,1), (1,2)]), None)
