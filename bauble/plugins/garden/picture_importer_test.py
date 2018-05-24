# -*- coding: utf-8 -*-
#
# Copyright 2018 Mario Frasca <mario@anche.no>.
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


from unittest import TestCase
import logging
logger = logging.getLogger(__name__)
from nose import SkipTest

from bauble.plugins.garden.picture_importer import decode_parts
from bauble import prefs

prefs.testing = True


class DecodePartsTest(TestCase):

    def test_decode_parts_complete(self):
        result = decode_parts("2018.0020.1 (4) Epidendrum.jpg")
        self.assertEqual(result, {'accession': '2018.0020',
                                   'plant': '1',
                                   'seq': '4',
                                   'species': 'Epidendrum'})
        result = decode_parts("Masdevallia-2018.0020-2.jpg")
        self.assertEqual(result, {'accession': '2018.0020',
                                   'plant': '1',
                                   'seq': '2',
                                   'species': 'Masdevallia'})
        result = decode_parts("2007.0001 Annona muricata.jpg")
        self.assertEqual(result, {'accession': '2007.0001',
                                   'plant': '1',
                                   'seq': '1',
                                   'species': 'Annona muricata'})

    def test_decode_parts_none(self):
        result = decode_parts("20x18.0020.1 (4).jpg")
        self.assertEqual(result, None)

    def test_decode_parts_optional(self):
        result = decode_parts("2018.0020 (4) Dracula.jpg")
        self.assertEqual(result, {'accession': '2018.0020',
                                   'plant': '1',
                                   'seq': '4',
                                   'species': 'Dracula'})
        result = decode_parts("2018.0020.2 (4).jpg")
        self.assertEqual(result, {'accession': '2018.0020',
                                   'plant': '2',
                                   'seq': '4',
                                   'species': 'Zzz'})
        result = decode_parts("2018.0020 (4).jpg")
        self.assertEqual(result, {'accession': '2018.0020',
                                   'plant': '1',
                                   'seq': '4',
                                   'species': 'Zzz'})

    def test_decode_parts_seq_from_original(self):
        result = decode_parts("DSCN0123-2018.0020.JPG")
        self.assertEqual(result, {'accession': '2018.0020',
                                   'plant': '1',
                                   'seq': '123',
                                   'species': 'Zzz'})
        result = decode_parts("P1220810-2018.0020.JPG")
        self.assertEqual(result, {'accession': '2018.0020',
                                   'plant': '1',
                                   'seq': '1220810',
                                   'species': 'Zzz'})
        result = decode_parts("2018.0020 Vanda-P1220810.JPG")
        self.assertEqual(result, {'accession': '2018.0020',
                                   'plant': '1',
                                   'seq': '1220810',
                                   'species': 'Vanda'})

    def test_decode_parts_seq_from_original(self):
        result = decode_parts("DSCN0123-2018.0020.JPG")
        self.assertEqual(result, {'accession': '2018.0020',
                                   'plant': '1',
                                   'seq': '123',
                                   'species': 'Zzz'})
        result = decode_parts("P1220810-2018.0020.JPG")
        self.assertEqual(result, {'accession': '2018.0020',
                                   'plant': '1',
                                   'seq': '1220810',
                                   'species': 'Zzz'})
        result = decode_parts("2018.0020 Vanda-P1220810.JPG")
        self.assertEqual(result, {'accession': '2018.0020',
                                   'plant': '1',
                                   'seq': '1220810',
                                   'species': 'Vanda'})

    def test_decode_parts_custom_accession_format(self):
        result = decode_parts("2007.01.321 Annona muricata.jpg", '####.##.###')
        self.assertEqual(result, {'accession': '2007.01.321',
                                   'plant': '1',
                                   'seq': '1',
                                   'species': 'Annona muricata'})
        result = decode_parts("2007.01.321.2 Annona sp.jpg", '####.##.###')
        self.assertEqual(result, {'accession': '2007.01.321',
                                   'plant': '2',
                                   'seq': '1',
                                   'species': 'Annona sp'})
        result = decode_parts("2009.01.21.2 Opuntia ficus-indica.jpg", '####.##.##')
        self.assertEqual(result, {'accession': '2009.01.21',
                                   'plant': '2',
                                   'seq': '1',
                                   'species': 'Opuntia ficus-indica'})


    def test_decode_parts_only_scan_name(self):
        result = decode_parts("Location/2018.0020.1 (4) Epidendrum.jpg")
        self.assertEqual(result, {'accession': '2018.0020',
                                   'plant': '1',
                                   'seq': '4',
                                   'species': 'Epidendrum'})
        result = decode_parts("Pictures/Masdevallia-2018.0020-2.jpg")
        self.assertEqual(result, {'accession': '2018.0020',
                                   'plant': '1',
                                   'seq': '2',
                                   'species': 'Masdevallia'})
