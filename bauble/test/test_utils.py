# -*- coding: utf-8 -*-
#
# Copyright (c) 2005,2006,2007,2008,2009 Brett Adams <brett@belizebotanic.org>
# Copyright (c) 2012-2016 Mario Frasca <mario@anche.no>
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

import bauble.utils as utils
from unittest import TestCase


class Utils(TestCase):

    def test_topological_sort_total(self):
        self.assertEqual(utils.topological_sort([1,2,3], [(2,1), (3,2)]), [3, 2, 1])

    def test_topological_sort_partial(self):
        self.assertEqual(utils.topological_sort([1,2,3,4], [(2,1)]), [4, 3, 2, 1])

    def test_topological_sort_loop(self):
        self.assertEqual(utils.topological_sort([1,2], [(2,1), (1,2)]), None)


class CacheTest(TestCase):
    def test_create_store_retrieve(self):
        from bauble.utils import Cache
        from functools import partial
        invoked = []

        def getter(x):
            invoked.append(x)
            return x

        cache = Cache(2)
        v = cache.get(1, partial(getter, 1))
        self.assertEquals(v, 1)
        self.assertEquals(invoked, [1])
        v = cache.get(1, partial(getter, 1))
        self.assertEquals(v, 1)
        self.assertEquals(invoked, [1])

    def test_respect_size(self):
        from bauble.utils import Cache
        from functools import partial
        invoked = []

        def getter(x):
            invoked.append(x)
            return x

        cache = Cache(2)
        cache.get(1, partial(getter, 1))
        cache.get(2, partial(getter, 2))
        cache.get(3, partial(getter, 3))
        cache.get(4, partial(getter, 4))
        self.assertEquals(invoked, [1, 2, 3, 4])
        self.assertEquals(sorted(cache.storage.keys()), [3, 4])

    def test_respect_timing(self):
        from bauble.utils import Cache
        from functools import partial
        invoked = []

        def getter(x):
            invoked.append(x)
            return x

        cache = Cache(2)
        cache.get(1, partial(getter, 1))
        cache.get(2, partial(getter, 2))
        cache.get(1, partial(getter, 1))
        cache.get(3, partial(getter, 3))
        cache.get(1, partial(getter, 1))
        cache.get(4, partial(getter, 4))
        self.assertEquals(invoked, [1, 2, 3, 4])
        self.assertEquals(sorted(cache.storage.keys()), [1, 4])

    def test_cache_on_hit(self):
        from bauble.utils import Cache
        from functools import partial
        invoked = []

        def getter(x):
            return x

        cache = Cache(2)
        cache.get(1, partial(getter, 1), on_hit=invoked.append)
        cache.get(1, partial(getter, 1), on_hit=invoked.append)
        cache.get(2, partial(getter, 2), on_hit=invoked.append)
        cache.get(1, partial(getter, 1), on_hit=invoked.append)
        cache.get(3, partial(getter, 3), on_hit=invoked.append)
        cache.get(1, partial(getter, 1), on_hit=invoked.append)
        cache.get(4, partial(getter, 4), on_hit=invoked.append)
        self.assertEquals(invoked, [1, 1, 1])
        self.assertEquals(sorted(cache.storage.keys()), [1, 4])


class GlobalFuncs(TestCase):
    def test_safe_int_valid(self):
        self.assertEquals(utils.safe_int('123'), 123)

    def test_safe_int_valid_not(self):
        self.assertEquals(utils.safe_int('123.2'), 0)

    def test_safe_numeric_valid(self):
        self.assertEquals(utils.safe_numeric('123'), 123)

    def test_safe_numeric_valid_decimal(self):
        self.assertEquals(utils.safe_numeric('123.2'), 123.2)

    def test_safe_numeric_valid_not(self):
        self.assertEquals(utils.safe_numeric('123a.2'), 0)
