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
#


from bauble.test import BaubleTestCase
from .taxonomy_check import species_to_fix
from bauble.plugins.plants.family import Family
from bauble.plugins.plants.genus import Genus


class TestOne(BaubleTestCase):

    def setUp(self):
        super().setUp()
        family = Family(family='Amaranthaceae')
        genus = Genus(family=family, genus='Salsola')
        self.session.add_all([family, genus])
        self.session.commit()

    def test_species_author(self):
        s = species_to_fix(self.session, 'Salsola kali', 'L.', True)
        self.assertEqual(s.sp, 'kali')
        self.assertEqual(s.sp_author, 'L.')
        self.assertEqual(s.infraspecific_rank, '')
        self.assertEqual(s.infraspecific_epithet, '')
        self.assertEqual(s.infraspecific_author, '')

    def test_subspecies_author(self):
        s = species_to_fix(self.session, 'Salsola kali subsp. tragus', '(L.) Čelak.', True)
        self.assertEqual(s.sp, 'kali')
        self.assertEqual(s.sp_author, None)
        self.assertEqual(s.infraspecific_rank, 'subsp.')
        self.assertEqual(s.infraspecific_epithet, 'tragus')
        self.assertEqual(s.infraspecific_author, '(L.) Čelak.')

    
