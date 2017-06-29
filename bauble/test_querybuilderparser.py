# Copyright (c) 2017 Mario Frasca <mario@anche.no>
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


from querybuilderparser import BuiltQuery
from bauble.test import BaubleTestCase

class QBP(BaubleTestCase):
    def test_and_clauses(self):
        query = BuiltQuery('plant WHERE accession.species.genus.family.epithet=Fabaceae AND location.description="Block 10" and quantity > 0 and quantity == 0')
        self.assertEquals(len(query.parsed), 6)
        self.assertEquals(query.parsed[0], 'plant')
        self.assertEquals(query.parsed[1], 'WHERE')
        self.assertEquals(len(query.parsed[2]), 3)
        for i in (3, 4, 5):
            self.assertEquals(query.parsed[i][0], 'AND')
            self.assertEquals(len(query.parsed[i]), 4)

    def test_or_clauses(self):
        query = BuiltQuery('plant WHERE accession.species.genus.family.epithet=Fabaceae OR location.description="Block 10" or quantity > 0 or quantity == 0')
        self.assertEquals(len(query.parsed), 6)
        self.assertEquals(query.parsed[0], 'plant')
        self.assertEquals(query.parsed[1], 'WHERE')
        self.assertEquals(len(query.parsed[2]), 3)
        for i in (3, 4, 5):
            self.assertEquals(query.parsed[i][0], 'OR')
            self.assertEquals(len(query.parsed[i]), 4)
