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
from nose import SkipTest

class QBP(BaubleTestCase):
    def test_and_clauses(self):
        query = BuiltQuery('plant WHERE accession.species.genus.family.epithet=Fabaceae AND location.description="Block 10" and quantity > 0 and quantity == 0')
        self.assertEquals(len(query.parsed), 6)
        self.assertEquals(query.parsed[0], 'plant')
        self.assertEquals(query.parsed[1], 'where')
        self.assertEquals(len(query.parsed[2]), 3)
        for i in (3, 4, 5):
            self.assertEquals(query.parsed[i][0], 'and')
            self.assertEquals(len(query.parsed[i]), 4)

    def test_or_clauses(self):
        query = BuiltQuery('plant WHERE accession.species.genus.family.epithet=Fabaceae OR location.description="Block 10" or quantity > 0 or quantity == 0')
        self.assertEquals(len(query.parsed), 6)
        self.assertEquals(query.parsed[0], 'plant')
        self.assertEquals(query.parsed[1], 'where')
        self.assertEquals(len(query.parsed[2]), 3)
        for i in (3, 4, 5):
            self.assertEquals(query.parsed[i][0], 'or')
            self.assertEquals(len(query.parsed[i]), 4)

    def test_has_clauses(self):
        query = BuiltQuery('genus WHERE epithet=Inga')
        self.assertEquals(len(query.clauses), 1)
        query = BuiltQuery('genus WHERE epithet=Inga or epithet=Iris')
        self.assertEquals(len(query.clauses), 2)

    def test_has_domain(self):
        query = BuiltQuery('plant WHERE accession.species.genus.epithet=Inga')
        self.assertEquals(query.domain, 'plant')

    def test_clauses_have_fields(self):
        query = BuiltQuery('genus WHERE epithet=Inga or family.epithet=Poaceae')
        self.assertEquals(len(query.clauses), 2)
        self.assertEquals(query.clauses[0].connector, None)
        self.assertEquals(query.clauses[1].connector, 'or')
        self.assertEquals(query.clauses[0].field, 'epithet')
        self.assertEquals(query.clauses[1].field, 'family.epithet')
        self.assertEquals(query.clauses[0].operator, '=')
        self.assertEquals(query.clauses[1].operator, '=')
        self.assertEquals(query.clauses[0].value, 'Inga')
        self.assertEquals(query.clauses[1].value, 'Poaceae')
        query = BuiltQuery("species WHERE genus.epithet=Inga and accessions.code like '2010%'")
        self.assertEquals(len(query.clauses), 2)
        self.assertEquals(query.clauses[0].connector, None)
        self.assertEquals(query.clauses[1].connector, 'and')
        self.assertEquals(query.clauses[0].field, 'genus.epithet')
        self.assertEquals(query.clauses[1].field, 'accessions.code')
        self.assertEquals(query.clauses[0].operator, '=')
        self.assertEquals(query.clauses[1].operator, 'like')
        self.assertEquals(query.clauses[0].value, 'Inga')
        self.assertEquals(query.clauses[1].value, '2010%')

    def test_is_none_if_wrong(self):
        query = BuiltQuery("'species WHERE genus.epithet=Inga")
        self.assertEquals(query.is_valid, False)
        query = BuiltQuery("species like %")
        self.assertEquals(query.is_valid, False)
        query = BuiltQuery("Inga")
        self.assertEquals(query.is_valid, False)

    def test_is_case_insensitive(self):
        for s in ["species Where genus.epithet=Inga and accessions.code like '2010%'",
                  "species WHERE genus.epithet=Inga and accessions.code Like '2010%'",
                  "species Where genus.epithet=Inga and accessions.code LIKE '2010%'",
                  "species Where genus.epithet=Inga AND accessions.code like '2010%'",
                  "species WHERE genus.epithet=Inga AND accessions.code LIKE '2010%'", ]:
            query = BuiltQuery(s)
            self.assertEquals(len(query.clauses), 2)
            self.assertEquals(query.clauses[0].connector, None)
            self.assertEquals(query.clauses[1].connector, 'and')
            self.assertEquals(query.clauses[0].field, 'genus.epithet')
            self.assertEquals(query.clauses[1].field, 'accessions.code')
            self.assertEquals(query.clauses[0].operator, '=')
            self.assertEquals(query.clauses[1].operator, 'like')
            self.assertEquals(query.clauses[0].value, 'Inga')
            self.assertEquals(query.clauses[1].value, '2010%')

    def test_is_only_usable_clauses(self):
        # valid query, but not for the query builder
        query = BuiltQuery("species WHERE genus.epithet=Inga or count(accessions.id)>4")
        print query.parsed
        self.assertEquals(query.is_valid, True)
        self.assertEquals(len(query.clauses), 1)
        query = BuiltQuery("species WHERE a=1 or count(accessions.id)>4 or genus.epithet=Inga")
        print query, query.clauses
        self.assertEquals(query.is_valid, True)
        self.assertEquals(len(query.clauses), 2)

    def test_be_able_to_skip_first_query_if_invalid(self):
        # valid query, but not for the query builder
        raise SkipTest("we can't do that without rewriting the grammar")
        query = BuiltQuery("species WHERE count(accessions.id)>4 or genus.epithet=Inga")
        print query, query.clauses
        self.assertEquals(query.is_valid, True)
        self.assertEquals(len(query.clauses), 1)
