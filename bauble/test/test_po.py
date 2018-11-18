# -*- coding: utf-8 -*-
#
# Copyright (c) 2018 Mario Frasca <mario@anche.no>
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

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

import re
import unittest
import glob
import os

class PoTests(unittest.TestCase):
    def test_same_keys(self):
        pattern = re.compile(r"%\([a-z0-9_]*\)s")
        parts = __file__.split(os.path.sep)[:-3]
        po_dir = os.path.sep.join(parts)
        files = glob.glob(os.path.join(po_dir, 'po', '*.po'))
        try:
            from babel.messages.pofile import read_po
        except:
            from nose import SkipTest
            raise SkipTest("don't test on appveyor")

        for filename in files:
            catalog = read_po(open(filename))
            for msg in catalog:
                if not msg.id:
                    # not a translation
                    continue
                if not msg.string:
                    # not translated
                    continue
                incoming = set(pattern.findall(msg.id))
                translated = set(pattern.findall(msg.string))
                self.assertEqual((filename, incoming), (filename, translated))
