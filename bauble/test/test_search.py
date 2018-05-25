# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Brett Adams
# Copyright 2015 Mario Frasca <mario@anche.no>.
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
# test_search.py
#
import unittest
from nose import SkipTest

import logging
logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)

from pyparsing import ParseException

import bauble.db as db
import bauble.search as search
from bauble.editor import MockView, GenericEditorView
from bauble import prefs
from bauble import paths
from bauble.test import BaubleTestCase
prefs.testing = True


parser = search.SearchParser()


class SearchParserTests(unittest.TestCase):
    error_msg = lambda me, s, v, e:  '%s: %s == %s' % (s, v, e)

    def test_query_expression_token_UPPER(self):
        s = 'domain where col=value'
        logger.debug(s)
        parser.query.parseString(s)

        s = 'domain where relation.col=value'
        parser.query.parseString(s)

        s = 'domain where relation.relation.col=value'
        parser.query.parseString(s)

        s = 'domain where relation.relation.col=value AND col2=value2'
        parser.query.parseString(s)

    def test_query_expression_token_LOWER(self):
        s = 'domain where relation.relation.col=value and col2=value2'
        parser.query.parseString(s)

    def test_statement_token(self):
        pass

    def test_domain_expression_token(self):
        """
        Test the domain_expression token
        """
        # allow dom=val1, val2, val3
        s = 'domain=test'
        expected = "[domain = ['test']]"
        results = parser.domain_expression.parseString(s, parseAll=True)
        self.assertEqual(results.getName(), 'domain_expression')
        self.assertEqual(str(results), expected)

        s = 'domain==test'
        expected = "[domain == ['test']]"
        results = parser.domain_expression.parseString(s, parseAll=True)
        self.assertEqual(str(results), expected)

        s = 'domain=*'
        expected = "[domain = *]"
        results = parser.domain_expression.parseString(s, parseAll=True)
        self.assertEqual(str(results), expected)

        s = 'domain=test1 test2 test3'
        expected = "[domain = ['test1', 'test2', 'test3']]"
        results = parser.statement.parseString(s, parseAll=True)
        self.assertEqual(str(results), expected)

        s = 'domain=test1 "test2 test3" test4'
        expected = "[domain = ['test1', 'test2 test3', 'test4']]"
        results = parser.domain_expression.parseString(s, parseAll=True)
        self.assertEqual(str(results), expected)

        s = 'domain="test test"'
        expected = "[domain = ['test test']]"
        results = parser.domain_expression.parseString(s, parseAll=True)
        self.assertEqual(str(results), expected)

    def test_integer_token(self):
        "recognizes integers or floats as floats"

        results = parser.value.parseString('123')
        self.assertEqual(results.getName(), 'value')
        self.assertEqual(results.value.express(), 123.0)
        results = parser.value.parseString('123.1')
        self.assertEqual(results.value.express(), 123.1)

    def test_bool_typed_no_arguments(self):
        "bool syntax needs at least one argument"

        self.assertRaises(ParseException, parser.value.parseString, '|bool||')

    def test_bool_typed_values(self):
        "recognizes bool syntax"

        results = parser.value.parseString('|bool|0|')
        self.assertEqual(results.getName(), 'value')
        self.assertEqual(results.value.express(), False)

        results = parser.value.parseString('|bool|0.0|')
        self.assertEqual(results.getName(), 'value')
        self.assertEqual(results.value.express(), False)

        results = parser.value.parseString('|bool|false|')
        self.assertEqual(results.getName(), 'value')
        self.assertEqual(results.value.express(), False)

        results = parser.value.parseString('|bool|FalsE|')
        self.assertEqual(results.getName(), 'value')
        self.assertEqual(results.value.express(), False)

        for i in ['True', 'true', 'TRUE', '"anything not false"', '"1"', '1', '1.1']:
            results = parser.value.parseString('|bool|%s|' % i)
            self.assertEqual(results.getName(), 'value')
            self.assertEqual(results.value.express(), True)

        for i in ['True', 'true', 'TRUE', '"anything not false"', '"1"', '1', '1.1']:
            results = parser.value.parseString('|bool|abc, %s, 3|' % i)
            self.assertEqual(results.getName(), 'value')
            self.assertEqual(results.value.express(), True)

    def test_datetime_typed_values(self):
        "recognizes datetime syntax"

        from datetime import datetime
        results = parser.value.parseString('|datetime|1970,1,1|')
        self.assertEqual(results.getName(), 'value')
        self.assertEqual(results.value.express(), datetime(1970, 1, 1))

    def test_datetime_typed_values_offset(self):
        "recognizes datetime offset syntax"

        from datetime import datetime, timedelta
        today = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(1)
        results = parser.value.parseString('|datetime|0|')
        self.assertEqual(results.getName(), 'value')
        self.assertEqual(results.value.express(), today)
        results = parser.value.parseString('|datetime|-1|')
        self.assertEqual(results.getName(), 'value')
        self.assertEqual(results.value.express(), yesterday)

    def test_value_token(self):
        "value should only return the first string or raise a parse exception"

        strings = ['test', '"test"', "'test'"]
        expected = 'test'
        for s in strings:
            results = parser.value.parseString(s, parseAll=True)
            self.assertEqual(results.getName(), 'value')
            self.assertEqual(results.value.express(), expected)

        strings = ['123.000', '123.', "123.0"]
        expected = 123.0
        for s in strings:
            results = parser.value.parseString(s)
            self.assertEqual(results.getName(), 'value')
            self.assertEqual(results.value.express(), expected)

        strings = ['"test1 test2"', "'test1 test2'"]
        expected = 'test1 test2'  # this is one string! :)
        for s in strings:
            results = parser.value.parseString(s, parseAll=True)
            self.assertEqual(results.getName(), 'value')
            self.assertEqual(results.value.express(), expected)

        strings = ['%.-_*', '"%.-_*"']
        expected = '%.-_*'
        for s in strings:
            results = parser.value.parseString(s, parseAll=True)
            self.assertEqual(results.getName(), 'value')
            self.assertEqual(results.value.express(), expected)

        # these should be invalid
        strings = ['test test', '"test', "test'", '$', ]
        for s in strings:
            self.assertRaises(ParseException, parser.value.parseString, s, parseAll=True)

    def test_needs_join(self):
        "check the join steps"

        env = None
        results = parser.statement.parseString("plant where accession.species."
                                               "id=44")
        self.assertEqual(results.statement.content.filter.needs_join(env),
                          [['accession', 'species']])
        results = parser.statement.parseString("plant where accession.id=44")
        self.assertEqual(results.statement.content.filter.needs_join(env),
                          [['accession']])
        results = parser.statement.parseString("plant where accession.id=4 OR "
                                               "accession.species.id=3")
        self.assertEqual(results.statement.content.filter.needs_join(env),
                          [['accession'], ['accession', 'species']])

    def test_value_list_token(self):
        """value_list: should return all values
        """

        strings = ['test1, test2',
                   '"test1", test2',
                   "test1, 'test2'"]
        expected = [['test1', 'test2']]
        for s in strings:
            results = parser.value_list.parseString(s, parseAll=True)
            self.assertEqual(results.getName(), 'value_list')
            self.assertEqual(str(results), str(expected))

        strings = ['test', '"test"', "'test'"]
        expected = [['test']]
        for s in strings:
            results = parser.value_list.parseString(s, parseAll=True)
            self.assertEqual(results.getName(), 'value_list')
            self.assertEqual(str(results), str(expected))

        strings = ['test1 test2 test3', '"test1" test2 \'test3\'']
        expected = [['test1', 'test2', 'test3']]
        for s in strings:
            results = parser.value_list.parseString(s, parseAll=True)
            self.assertEqual(str(results), str(expected))

        strings = ['"test1 test2", test3']
        expected = [['test1 test2', 'test3']]
        for s in strings:
            results = parser.value_list.parseString(s, parseAll=True)
            self.assertEqual(str(results), str(expected))

        # these should be invalid
        strings = ['"test', "test'", "'test tes2", "1,2,3 4 5"]
        for s in strings:
            self.assertRaises(ParseException, parser.value_list.parseString, s, parseAll=True)


class SearchTests(BaubleTestCase):
    def __init__(self, *args):
        super().__init__(*args)
        prefs.testing = True

    def setUp(self):
        super().setUp()
        db.engine.execute('delete from genus')
        db.engine.execute('delete from family')
        from bauble.plugins.plants.family import Family
        from bauble.plugins.plants.genus import Genus
        self.family = Family(family='family1', qualifier='s. lat.')
        self.genus = Genus(family=self.family, genus='genus1')
        self.Family = Family
        self.Genus = Genus
        self.session.add_all([self.family, self.genus])
        self.session.commit()

    def tearDown(self):
        super().tearDown()

    def test_find_correct_strategy_internal(self):
        "verify the MapperSearch strategy is available (low-level)"

        mapper_search = search._search_strategies['MapperSearch']
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

    def test_find_correct_strategy(self):
        "verify the MapperSearch strategy is available"

        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

    def test_look_for_wrong_strategy(self):
        "verify the NotExisting strategy gives None"

        mapper_search = search.get_strategy('NotExisting')

        self.assertIsNone(mapper_search)

    def test_search_by_values(self):
        "search by values"
        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        # search for family by family name
        results = mapper_search.search('family1', self.session)
        self.assertEqual(len(results), 1)
        f = list(results)[0]
        self.assertEqual(f.id, self.family.id)

        # search for genus by genus name
        results = mapper_search.search('genus1', self.session)
        self.assertEqual(len(results), 1)
        g = list(results)[0]
        self.assertEqual(g.id, self.genus.id)

    def test_search_by_expression_family_eq(self):
        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        # search for family by domain
        results = mapper_search.search('fam=family1', self.session)
        self.assertEqual(len(results), 1)
        f = list(results)[0]
        self.assertTrue(isinstance(f, self.Family))
        self.assertEqual(f.id, self.family.id)

    def test_search_by_expression_genus_eq_1match(self):
        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        # search for genus by domain
        results = mapper_search.search('gen=genus1', self.session)
        self.assertEqual(len(results), 1)
        g = list(results)[0]
        self.assertTrue(isinstance(g, self.Genus))
        self.assertEqual(g.id, self.genus.id)

    def test_search_by_expression_genus_eq_nomatch(self):
        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        # search for genus by domain
        results = mapper_search.search('genus=g', self.session)
        self.assertEqual(len(results), 0)

    def test_search_by_expression_genus_eq_everything(self):
        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        # search for genus by domain
        results = mapper_search.search('genus=*', self.session)
        self.assertEqual(len(results), 1)

    def test_search_by_expression_genus_like_nomatch(self):
        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        # search for genus by domain
        results = mapper_search.search('genus like gen', self.session)
        self.assertEqual(len(results), 0)
        # search for genus by domain
        results = mapper_search.search('genus like nus%', self.session)
        self.assertEqual(len(results), 0)
        # search for genus by domain
        results = mapper_search.search('genus like %gen', self.session)
        self.assertEqual(len(results), 0)

    def test_search_by_expression_genus_like_contains_eq(self):
        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))
        Family = self.Family
        f2 = Family(family='family2')
        f3 = Family(family='afamily3')
        f4 = Family(family='fam4')
        self.session.add_all([f3, f2, f4])
        self.session.commit()

        # search for family by domain
        results = mapper_search.search('family contains fam', self.session)
        self.assertEqual(len(results), 4)  # all do
        results = mapper_search.search('family like f%', self.session)
        self.assertEqual(len(results), 3)  # three start by f
        results = mapper_search.search('family like af%', self.session)
        self.assertEqual(len(results), 1)  # one starts by af
        results = mapper_search.search('family like fam', self.session)
        self.assertEqual(len(results), 0)
        results = mapper_search.search('family = fam', self.session)
        self.assertEqual(len(results), 0)
        results = mapper_search.search('family = fam4', self.session)
        self.assertEqual(len(results), 1)  # exact name match
        results = mapper_search.search('family = Fam4', self.session)
        self.assertEqual(len(results), 0)  # = is case sensitive
        results = mapper_search.search('family like Fam4', self.session)
        self.assertEqual(len(results), 1)  # like is case insensitive
        results = mapper_search.search('family contains FAM', self.session)
        self.assertEqual(len(results), 4)  # they case insensitively do

    def test_search_by_query11(self):
        "query with MapperSearch, single table, single test"

        # test does not depend on plugin functionality
        Family = self.Family
        Genus = self.Genus
        family2 = Family(family='family2')
        genus2 = Genus(family=family2, genus='genus2')
        self.session.add_all([family2, genus2])
        self.session.commit()

        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        # search cls.column
        results = mapper_search.search('genus where genus=genus1',
                                       self.session)
        self.assertEqual(len(results), 1)
        f = list(results)[0]
        self.assertTrue(isinstance(f, Genus))
        self.assertEqual(f.id, self.family.id)

    def test_search_by_query12(self):
        "query with MapperSearch, single table, p1 OR p2"

        # test does not depend on plugin functionality
        Family = self.Family
        Genus = self.Genus
        f2 = Family(family='family2')
        g2 = Genus(family=f2, genus='genus2')
        f3 = Family(family='fam3')
        # g3(homonym) is here just to have two matches on one value
        g3 = Genus(family=f3, genus='genus2')
        g4 = Genus(family=f3, genus='genus4')
        self.session.add_all([f2, g2, f3, g3, g4])
        self.session.commit()

        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        # search with or conditions
        s = 'genus where genus=genus2 OR genus=genus1'
        results = mapper_search.search(s, self.session)
        self.assertEqual(sorted([r.id for r in results]),
                          [g.id for g in (self.genus, g2, g3)])

    def test_search_by_query13(self):
        "query with MapperSearch, single table, p1 AND p2"

        # test does not depend on plugin functionality
        Family = self.Family
        Genus = self.Genus
        family2 = Family(family='family2')
        genus2 = Genus(family=family2, genus='genus2')
        f3 = Family(family='fam3')
        g3 = Genus(family=f3, genus='genus2')
        g4 = Genus(family=f3, genus='genus4')
        self.session.add_all([family2, genus2, f3, g3, g4])
        self.session.commit()

        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        s = 'genus where id>1 AND id<3'
        results = mapper_search.search(s, self.session)
        self.assertEqual(len(results), 1)
        result = results.pop()
        self.assertEqual(result.id, 2)

        s = 'genus where id>0 AND id<3'
        results = list(mapper_search.search(s, self.session))
        self.assertEqual(len(results), 2)
        self.assertEqual(set(i.id for i in results), set([1, 2]))

    def test_search_by_query21(self):
        "query with MapperSearch, joined tables, one predicate"

        # test does not depend on plugin functionality
        Family = self.Family
        Genus = self.Genus
        family2 = Family(family='family2')
        genus2 = Genus(family=family2, genus='genus2')
        self.session.add_all([family2, genus2])
        self.session.commit()

        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        # search cls.parent.column
        results = mapper_search.search('genus where family.family=family1',
                                       self.session)
        self.assertEqual(len(results), 1)
        g0 = list(results)[0]
        self.assertTrue(isinstance(g0, Genus))
        self.assertEqual(g0.id, self.genus.id)

        # search cls.children.column
        results = mapper_search.search('family where genera.genus=genus1',
                                       self.session)
        self.assertEqual(len(results), 1)
        f = list(results)[0]
        self.assertEqual(len(results), 1)
        self.assertTrue(isinstance(f, Family))
        self.assertEqual(f.id, self.family.id)

    def test_search_by_query22(self):
        "query with MapperSearch, joined tables, multiple predicates"

        # test does not depend on plugin functionality
        Family = self.Family
        Genus = self.Genus
        family2 = Family(family='family2')
        g2 = Genus(family=family2, genus='genus2')
        f3 = Family(family='fam3', qualifier='s. lat.')
        g3 = Genus(family=f3, genus='genus3')
        self.session.add_all([family2, g2, f3, g3])
        self.session.commit()

        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        s = 'genus where genus=genus2 AND family.family=fam3'
        results = mapper_search.search(s, self.session)
        self.assertEqual(len(results), 0)

        s = 'genus where genus=genus3 AND family.family=fam3'
        results = mapper_search.search(s, self.session)
        self.assertEqual(len(results), 1)
        g0 = list(results)[0]
        self.assertTrue(isinstance(g0, Genus))
        self.assertEqual(g0.id, g3.id)

        s = 'genus where family.family="Orchidaceae" AND family.qualifier=""'
        results = mapper_search.search(s, self.session)
        r = list(results)
        self.assertEqual(r, [])

        s = 'genus where family.family=fam3 AND family.qualifier=""'
        results = mapper_search.search(s, self.session)
        self.assertEqual(results, set([]))

        # sqlite3 stores None as the empty string.
        s = 'genus where family.qualifier=""'
        results = mapper_search.search(s, self.session)
        self.assertEqual(results, set([g2]))

        # test where the column is ambiguous so make sure we choose
        # the right one, in this case we want to make sure we get the
        # qualifier on the family and not the genus
        s = 'plant where accession.species.genus.family.family="Orchidaceae" '\
            'AND accession.species.genus.family.qualifier=""'
        results = mapper_search.search(s, self.session)
        self.assertEqual(results, set([]))

    def test_search_by_query22Symbolic(self):
        "query with &&, ||, !"

        # test does not depend on plugin functionality
        Family = self.Family
        Genus = self.Genus
        family2 = Family(family='family2')
        g2 = Genus(family=family2, genus='genus2')
        f3 = Family(family='fam3', qualifier='s. lat.')
        g3 = Genus(family=f3, genus='genus3')
        self.session.add_all([family2, g2, f3, g3])
        self.session.commit()

        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        s = 'genus where genus=genus2 && family.family=fam3'
        results = mapper_search.search(s, self.session)
        self.assertEqual(len(results), 0)

        s = 'family where family=family1 || family=fam3'
        results = mapper_search.search(s, self.session)
        self.assertEqual(len(results), 2)

        s = 'family where ! family=family1'
        results = mapper_search.search(s, self.session)
        self.assertEqual(len(results), 2)

    def test_search_by_query22None(self):
        """query with MapperSearch, joined tables, predicates using None

        results are irrelevant, because sqlite3 uses the empty string to
        represent None

        """

        # test does not depend on plugin functionality
        Family = self.Family
        Genus = self.Genus
        family2 = Family(family='family2')
        g2 = Genus(family=family2, genus='genus2')
        f3 = Family(family='fam3', qualifier='s. lat.')
        g3 = Genus(family=f3, genus='genus3')
        self.session.add_all([family2, g2, f3, g3])
        self.session.commit()

        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        s = 'genus where family.qualifier is None'
        results = mapper_search.search(s, self.session)
        self.assertEqual(results, set([]))

        # make sure None isn't treated as the string 'None' and that
        # the query picks up the is operator
        s = 'genus where author is None'
        results = mapper_search.search(s, self.session)
        self.assertEqual(results, set([]))

        s = 'genus where author is not None'
        resultsNone = mapper_search.search(s, self.session)
        s = 'genus where NOT author = ""'
        resultsEmptyString = mapper_search.search(s, self.session)
        self.assertEqual(resultsNone, resultsEmptyString)

        s = 'genus where author != None'
        resultsNone = mapper_search.search(s, self.session)
        s = 'genus where NOT author = ""'
        resultsEmptyString = mapper_search.search(s, self.session)
        self.assertEqual(resultsNone, resultsEmptyString)

    def test_search_by_query22id(self):
        "query with MapperSearch, joined tables, test on id of dependent table"

        # test does not depend on plugin functionality
        Family = self.Family
        Genus = self.Genus
        family2 = Family(family='family2')
        genus2 = Genus(family=family2, genus='genus2')
        f3 = Family(family='fam3')
        g3 = Genus(family=f3, genus='genus3')
        self.session.add_all([family2, genus2, f3, g3])
        self.session.commit()

        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        # id is an ambiguous column because it occurs on plant,
        # accesion and species...the results here don't matter as much
        # as the fact that the query doesn't raise and exception
        s = 'plant where accession.species.id=1'
        results = mapper_search.search(s, self.session)
        list(results)

    def test_search_by_query22like(self):
        "query with MapperSearch, joined tables, LIKE"

        # test does not depend on plugin functionality
        Family = self.Family
        Genus = self.Genus
        family2 = Family(family='family2')
        family3 = Family(family='afamily3')
        genus21 = Genus(family=family2, genus='genus21')
        genus31 = Genus(family=family3, genus='genus31')
        genus32 = Genus(family=family3, genus='genus32')
        genus33 = Genus(family=family3, genus='genus33')
        f3 = Family(family='fam3')
        g3 = Genus(family=f3, genus='genus31')
        self.session.add_all([family3, family2, genus21, genus31, genus32,
                              genus33, f3, g3])
        self.session.commit()

        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        # test partial string matches on a query
        s = 'genus where family.family like family%'
        results = mapper_search.search(s, self.session)
        self.assertEqual(set(results), set([self.genus, genus21]))

    def test_search_by_query22_underscore(self):
        """can use fields starting with an underscore"""

        import datetime
        Family = self.Family
        Genus = self.Genus
        from bauble.plugins.plants.species_model import Species
        from bauble.plugins.garden.accession import Accession
        from bauble.plugins.garden.location import Location
        from bauble.plugins.garden.plant import Plant
        family2 = Family(family='family2')
        g2 = Genus(family=family2, genus='genus2')
        f3 = Family(family='fam3', qualifier='s. lat.')
        g3 = Genus(family=f3, genus='Ixora')
        sp = Species(sp="coccinea", genus=g3)
        ac = Accession(species=sp, code='1979.0001')
        lc = Location(name='loc1', code='loc1')
        pp = Plant(accession=ac, code='01', location=lc, quantity=1)
        pp._last_updated = datetime.datetime(2009, 2, 13)
        self.session.add_all([family2, g2, f3, g3, sp, ac, lc, pp])
        self.session.commit()

        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        s = 'plant where _last_updated < |datetime|2000,1,1|'
        results = mapper_search.search(s, self.session)
        self.assertEqual(results, set())

        s = 'plant where _last_updated > |datetime|2000,1,1|'
        results = mapper_search.search(s, self.session)
        self.assertEqual(results, set([pp]))

    def test_between_evaluate(self):
        'use BETWEEN value and value'
        Family = self.Family
        Genus = self.Genus
        from bauble.plugins.plants.species_model import Species
        from bauble.plugins.garden.accession import Accession
        #from bauble.plugins.garden.location import Location
        #from bauble.plugins.garden.plant import Plant
        family2 = Family(family='family2')
        g2 = Genus(family=family2, genus='genus2')
        f3 = Family(family='fam3', qualifier='s. lat.')
        g3 = Genus(family=f3, genus='Ixora')
        sp = Species(sp="coccinea", genus=g3)
        ac = Accession(species=sp, code='1979.0001')
        self.session.add_all([family2, g2, f3, g3, sp, ac])
        self.session.commit()

        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        s = 'accession where code between "1978" and "1980"'
        results = mapper_search.search(s, self.session)
        self.assertEqual(results, set([ac]))
        s = 'accession where code between "1980" and "1980"'
        results = mapper_search.search(s, self.session)
        self.assertEqual(results, set())

    def test_search_by_query_synonyms(self):
        """SynonymSearch strategy gives all synonyms of given taxon."""
        Family = self.Family
        Genus = self.Genus
        family2 = Family(family='family2')
        g2 = Genus(family=family2, genus='genus2')
        f3 = Family(family='fam3', qualifier='s. lat.')
        g3 = Genus(family=f3, genus='Ixora')
        g4 = Genus(family=f3, genus='Schetti')
        self.session.add_all([family2, g2, f3, g3, g4])
        g4.accepted = g3
        self.session.commit()

        prefs.prefs['bauble.search.return_synonyms'] = True
        mapper_search = search.get_strategy('SynonymSearch')

        s = 'Schetti'
        results = mapper_search.search(s, self.session)
        self.assertEqual(results, [g3])

    def test_search_by_query_synonyms_disabled(self):
        """SynonymSearch strategy gives all synonyms of given taxon."""
        Family = self.Family
        Genus = self.Genus
        family2 = Family(family='family2')
        g2 = Genus(family=family2, genus='genus2')
        f3 = Family(family='fam3', qualifier='s. lat.')
        g3 = Genus(family=f3, genus='Ixora')
        g4 = Genus(family=f3, genus='Schetti')
        self.session.add_all([family2, g2, f3, g3, g4])
        g4.accepted = g3
        self.session.commit()

        prefs.prefs['bauble.search.return_synonyms'] = False
        mapper_search = search.get_strategy('SynonymSearch')

        s = 'Schetti'
        results = mapper_search.search(s, self.session)
        self.assertEqual(results, [])

    def test_search_by_query_vernacural(self):
        """can find species by vernacular name"""

        Family = self.Family
        Genus = self.Genus
        from bauble.plugins.plants.species_model import Species
        from bauble.plugins.plants.species_model import VernacularName
        family2 = Family(family='family2')
        g2 = Genus(family=family2, genus='genus2')
        f3 = Family(family='fam3', qualifier='s. lat.')
        g3 = Genus(family=f3, genus='Ixora')
        sp = Species(sp="coccinea", genus=g3)
        vn = VernacularName(name="coral rojo", language="es", species=sp)
        self.session.add_all([family2, g2, f3, g3, sp, vn])
        self.session.commit()

        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        s = "rojo"
        results = mapper_search.search(s, self.session)
        self.assertEqual(results, set([sp]))


class InOperatorSearch(BaubleTestCase):
    def __init__(self, *args):
        super().__init__(*args)

    def setUp(self):
        super().setUp()
        db.engine.execute('delete from genus')
        db.engine.execute('delete from family')
        from bauble.plugins.plants.family import Family
        from bauble.plugins.plants.genus import Genus
        self.family = Family(family='family1', qualifier='s. lat.', id=1)
        self.g1 = Genus(family=self.family, genus='genus1', id=1)
        self.g2 = Genus(family=self.family, genus='genus2', id=2)
        self.g3 = Genus(family=self.family, genus='genus3', id=3)
        self.g4 = Genus(family=self.family, genus='genus4', id=4)
        self.Family = Family
        self.Genus = Genus
        self.session.add_all([self.family, self.g1, self.g2, self.g3, self.g4])
        self.session.commit()

    def test_in_singleton(self):
        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        s = 'genus where id in 1'
        results = mapper_search.search(s, self.session)
        self.assertEqual(results, set([self.g1]))

    def test_in_list(self):
        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        s = 'genus where id in 1,2,3'
        results = mapper_search.search(s, self.session)
        self.assertEqual(results, set([self.g1, self.g2, self.g3]))

    def test_in_list_no_result(self):
        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        s = 'genus where id in 5,6'
        results = mapper_search.search(s, self.session)
        self.assertEqual(results, set())

    def test_in_composite_expression(self):
        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        s = 'genus where id in 1,2 or id>8'
        results = mapper_search.search(s, self.session)
        self.assertEqual(results, set([self.g1, self.g2]))

    def test_in_composite_expression_excluding(self):
        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        s = 'genus where id in 1,2,4 and id<3'
        results = mapper_search.search(s, self.session)
        self.assertEqual(results, set([self.g1, self.g2]))


class BinomialSearchTests(BaubleTestCase):
    def __init__(self, *args):
        super().__init__(*args)

    def setUp(self):
        super().setUp()
        db.engine.execute('delete from genus')
        db.engine.execute('delete from family')
        from bauble.plugins.plants.family import Family
        from bauble.plugins.plants.genus import Genus
        from bauble.plugins.plants.species import Species
        f1 = Family(family='family1', qualifier='s. lat.')
        g1 = Genus(family=f1, genus='genus1')
        f2 = Family(family='family2')
        g2 = Genus(family=f2, genus='genus2')
        f3 = Family(family='fam3', qualifier='s. lat.')
        g3 = Genus(family=f3, genus='Ixora')
        sp = Species(sp="coccinea", genus=g3)
        sp2 = Species(sp="peruviana", genus=g3)
        sp3 = Species(sp="chinensis", genus=g3)
        g4 = Genus(family=f3, genus='Pachystachys')
        sp4 = Species(sp='coccinea', genus=g4)
        self.session.add_all([f1, f2, g1, g2, f3, g3, sp, sp2, sp3, g4, sp4])
        self.session.commit()
        self.ixora, self.ic, self.pc = g3, sp, sp4

    def tearDown(self):
        super().tearDown()

    def test_binomial_complete(self):
        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        s = 'Ixora coccinea'  # matches Ixora coccinea
        results = mapper_search.search(s, self.session)
        self.assertEqual(results, set([self.ic]))

    def test_binomial_incomplete(self):
        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        s = 'Ix cocc'  # matches Ixora coccinea
        results = mapper_search.search(s, self.session)
        self.assertEqual(results, set([self.ic]))

    def test_binomial_no_match(self):
        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        s = 'Cosito inesistente'  # matches nothing
        results = mapper_search.search(s, self.session)
        self.assertEqual(results, set())

    def test_almost_binomial(self):
        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        s = 'ixora coccinea'  # matches Ixora, I.coccinea, P.coccinea
        results = mapper_search.search(s, self.session)
        self.assertEqual(results, set([self.ixora, self.ic, self.pc]))

    def test_cultivar_also_matched(self):
        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        from bauble.plugins.plants.species import Species
        from bauble.plugins.plants.genus import Genus
        g3 = self.session.query(Genus).filter(Genus.genus == 'Ixora').one()
        sp5 = Species(sp="coccinea", genus=g3,
                      infrasp1_rank='cv.', infrasp1='Nora Grant')
        self.session.add_all([sp5])
        self.session.commit()
        s = 'Ixora coccinea'  # matches I.coccinea and Nora Grant
        results = mapper_search.search(s, self.session)
        self.assertEqual(results, set([self.ic, sp5]))


class QueryBuilderTests(BaubleTestCase):

    def test_cancreatequerybuilder(self):
        import os
        gladefilepath = os.path.join(paths.lib_dir(), "querybuilder.glade")
        view = GenericEditorView(
            gladefilepath,
            parent=None,
            root_widget_name='main_dialog')
        search.QueryBuilder(view)

    def test_emptyisinvalid(self):
        import os
        gladefilepath = os.path.join(paths.lib_dir(), "querybuilder.glade")
        view = GenericEditorView(
            gladefilepath,
            parent=None,
            root_widget_name='main_dialog')
        qb = search.QueryBuilder(view)
        self.assertFalse(qb.validate())

    def test_cansetquery(self):
        import os
        gladefilepath = os.path.join(paths.lib_dir(), "querybuilder.glade")
        view = GenericEditorView(
            gladefilepath,
            parent=None,
            root_widget_name='main_dialog')
        qb = search.QueryBuilder(view)
        qb.set_query('plant where id=0 or id=1 or id>10')
        self.assertEqual(len(qb.expression_rows), 3)

    def test_cansetenumquery(self):
        import os
        gladefilepath = os.path.join(paths.lib_dir(), "querybuilder.glade")
        view = GenericEditorView(
            gladefilepath,
            parent=None,
            root_widget_name='main_dialog')
        qb = search.QueryBuilder(view)
        qb.set_query("accession where recvd_type = 'BBIL'")
        self.assertEqual(len(qb.expression_rows), 1)


class BuildingSQLStatements(BaubleTestCase):
    import bauble.search
    SearchParser = bauble.search.SearchParser

    def test_canfindspeciesfromgenus(self):
        'can find species from genus'

        text = 'species where species.genus=genus1'
        sp = self.SearchParser()
        results = sp.parse_string(text)
        self.assertEqual(
            str(results.statement),
            "SELECT * FROM species WHERE (species.genus = 'genus1')")

    def test_canuselogicaloperators(self):
        'can use logical operators'

        sp = self.SearchParser()
        results = sp.parse_string('species where species.genus=genus1 OR '
                                  'species.sp=name AND species.genus.family'
                                  '.family=name')
        self.assertEqual(str(results.statement), "SELECT * FROM species WHERE "
                         "((species.genus = 'genus1') OR ((species.sp = 'name'"
                         ") AND (species.genus.family.family = 'name')))")

        sp = self.SearchParser()
        results = sp.parse_string('species where species.genus=genus1 || '
                                  'species.sp=name && species.genus.family.'
                                  'family=name')
        self.assertEqual(str(results.statement), "SELECT * FROM species WHERE "
                         "((species.genus = 'genus1') OR ((species.sp = 'name'"
                         ") AND (species.genus.family.family = 'name')))")

    def test_canfindfamilyfromgenus(self):
        'can find family from genus'

        sp = self.SearchParser()
        results = sp.parse_string('family where family.genus=genus1')
        self.assertEqual(str(results.statement), "SELECT * FROM family WHERE ("
                         "family.genus = 'genus1')")

    def test_canfindgenusfromfamily(self):
        'can find genus from family'

        sp = self.SearchParser()
        results = sp.parse_string('genus where genus.family=family2')
        self.assertEqual(str(results.statement), "SELECT * FROM genus WHERE ("
                         "genus.family = 'family2')")

    def test_canfindplantbyaccession(self):
        'can find plant from the accession id'

        sp = self.SearchParser()
        results = sp.parse_string('plant where accession.species.id=113')
        self.assertEqual(str(results.statement), 'SELECT * FROM plant WHERE ('
                         'accession.species.id = 113.0)')

    def test_canuseNOToperator(self):
        'can use the NOT operator'

        sp = self.SearchParser()
        results = sp.parse_string('species where NOT species.genus.family.'
                                  'family=name')
        self.assertEqual(str(results.statement), "SELECT * FROM species WHERE "
                         "NOT (species.genus.family.family = 'name')")
        results = sp.parse_string('species where ! species.genus.family.family'
                                  '=name')
        self.assertEqual(str(results.statement), "SELECT * FROM species WHERE "
                         "NOT (species.genus.family.family = 'name')")
        results = sp.parse_string('species where family=1 OR family=2 AND NOT '
                                  'genus.id=3')
        self.assertEqual(str(results.statement), "SELECT * FROM species WHERE "
                         "((family = 1.0) OR ((family = 2.0) AND NOT (genus.id"
                         " = 3.0)))")

    def test_canuse_lowercase_operators(self):
        'can use the operators in lower case'

        sp = self.SearchParser()
        results = sp.parse_string('species where not species.genus.family.'
                                  'family=name')
        self.assertEqual(str(results.statement), "SELECT * FROM species WHERE "
                         "NOT (species.genus.family.family = 'name')")
        results = sp.parse_string('species where ! species.genus.family.family'
                                  '=name')
        self.assertEqual(str(results.statement), "SELECT * FROM species WHERE "
                         "NOT (species.genus.family.family = 'name')")
        results = sp.parse_string('species where family=1 or family=2 and not '
                                  'genus.id=3')
        self.assertEqual(str(results.statement), "SELECT * FROM species WHERE "
                         "((family = 1.0) OR ((family = 2.0) AND NOT (genus.id"
                         " = 3.0)))")

    def test_notes_is_not_not_es(self):
        'acknowledges word boundaries'

        sp = self.SearchParser()
        results = sp.parse_string('species where notes.id!=0')
        self.assertEqual(str(results.statement),
                         "SELECT * FROM species WHERE (notes.id != 0.0)")

    def test_between_just_parse_0(self):
        'use BETWEEN value and value'
        sp = self.SearchParser()
        results = sp.parse_string('species where id between 0 and 1')
        self.assertEqual(str(results.statement),
                         "SELECT * FROM species WHERE (BETWEEN id 0.0 1.0)")

    def test_between_just_parse_1(self):
        'use BETWEEN value and value'
        sp = self.SearchParser()
        results = sp.parse_string('species where step.id between 0 and 1')
        self.assertEqual(str(results.statement),
                         "SELECT * FROM species WHERE (BETWEEN step.id 0.0 1.0)")

    def test_between_just_parse_2(self):
        'use BETWEEN value and value'
        sp = self.SearchParser()
        results = sp.parse_string('species where step.step.step.step[a=1].id between 0 and 1')
        self.assertEqual(str(results.statement),
                         "SELECT * FROM species WHERE (BETWEEN step.step.step.step[a=1.0].id 0.0 1.0)")


class FilterThenMatchTests(BaubleTestCase):
    def __init__(self, *args):
        super().__init__(*args)
        prefs.testing = True

    def setUp(self):
        super().setUp()
        db.engine.execute('delete from genus')
        db.engine.execute('delete from family')
        db.engine.execute('delete from genus_note')
        from bauble.plugins.plants.family import Family
        from bauble.plugins.plants.genus import Genus, GenusNote
        self.family = Family(family='family1', qualifier='s. lat.')
        self.genus1 = Genus(family=self.family, genus='genus1')
        self.genus2 = Genus(family=self.family, genus='genus2')
        self.genus3 = Genus(family=self.family, genus='genus3')
        self.genus4 = Genus(family=self.family, genus='genus4')
        n1 = GenusNote(category='commentarii', note='olim', genus=self.genus1)
        n2 = GenusNote(category='commentarii', note='erat', genus=self.genus1)
        n3 = GenusNote(category='commentarii', note='verbum', genus=self.genus2)
        n4 = GenusNote(category='test', note='olim', genus=self.genus3)
        n5 = GenusNote(category='test', note='verbum', genus=self.genus3)
        self.session.add_all([self.family, self.genus1, self.genus2, self.genus3, self.genus4, n1, n2, n3, n4, n5])
        self.session.commit()

    def tearDown(self):
        super().tearDown()

    def test_can_filter_match_notes(self):
        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        s = "genus where notes.note='olim'"
        results = mapper_search.search(s, self.session)
        self.assertEqual(results, set([self.genus1, self.genus3]))

        s = "genus where notes[category='test'].note='olim'"
        results = mapper_search.search(s, self.session)
        self.assertEqual(results, set([self.genus3]))

        s = "genus where notes.category='commentarii'"
        results = mapper_search.search(s, self.session)
        self.assertEqual(results, set([self.genus1, self.genus2]))

        s = "genus where notes[note='verbum'].category='commentarii'"
        results = mapper_search.search(s, self.session)
        self.assertEqual(results, set([self.genus2]))

    def test_can_find_empty_set(self):
        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        s = "genus where notes=Empty"
        results = mapper_search.search(s, self.session)
        self.assertEqual(results, set([self.genus4]))

    def test_can_find_non_empty_set(self):
        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        s = "genus where notes!=Empty"
        results = mapper_search.search(s, self.session)
        self.assertEqual(results, set([self.genus1, self.genus2, self.genus3]))

    def test_can_match_list_of_values(self):
        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        s = "genus where notes.note in 'olim', 'erat', 'verbum'"
        results = mapper_search.search(s, self.session)
        self.assertEqual(results, set([self.genus1, self.genus2, self.genus3]))

        s = "genus where notes[category='test'].note in 'olim', 'erat', 'verbum'"
        results = mapper_search.search(s, self.session)
        self.assertEqual(results, set([self.genus3]))

    def test_parenthesised_search(self):
        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        s = "genus where (notes!=Empty) and (notes=Empty)"
        results = mapper_search.search(s, self.session)
        self.assertEqual(results, set())


class ParseTypedValue(BaubleTestCase):
    def test_parse_typed_value_floats(self):
        result = search.parse_typed_value('0.0')
        self.assertEqual(result, 0.0)
        result = search.parse_typed_value('-4.0')
        self.assertEqual(result, -4.0)

    def test_parse_typed_value_int(self):
        result = search.parse_typed_value('0')
        self.assertEqual(result, 0)
        result = search.parse_typed_value('-4')
        self.assertEqual(result, -4)

    def test_parse_typed_value_None(self):
        result = search.parse_typed_value('None')
        self.assertEqual(result, None)

    def test_parse_typed_value_empty_set(self):
        result = search.parse_typed_value('Empty')
        self.assertEqual(type(result), search.EmptyToken)

    def test_parse_typed_value_fallback(self):
        result = search.parse_typed_value('whatever else')
        self.assertEqual(result, 'whatever else')


class EmptySetEqualityTest(unittest.TestCase):
    def test_EmptyToken_equals(self):
        et1 = search.EmptyToken()
        et2 = search.EmptyToken()
        self.assertEqual(et1, et2)
        self.assertTrue(et1 == et2)
        self.assertTrue(et1 == set())

    def test_empty_token_otherwise(self):
        et1 = search.EmptyToken()
        self.assertFalse(et1 is None)
        self.assertFalse(et1 == 0)
        self.assertFalse(et1 == '')
        self.assertFalse(et1 == set([1, 2, 3]))

    def test_EmptyToken_representation(self):
        et1 = search.EmptyToken()
        self.assertEqual("%s" % et1, "Empty")
        self.assertEqual(et1.express(), set())

    def test_NoneToken_representation(self):
        nt1 = search.NoneToken()
        self.assertEqual("%s" % nt1, "(None<NoneType>)")
        self.assertEqual(nt1.express(), None)


class AggregatingFunctions(BaubleTestCase):
    def __init__(self, *args):
        super().__init__(*args)
        prefs.testing = True

    def setUp(self):
        super().setUp()
        db.engine.execute('delete from genus')
        db.engine.execute('delete from family')
        db.engine.execute('delete from species')
        db.engine.execute('delete from accession')
        from bauble.plugins.plants import Family, Genus, Species
        f1 = Family(family='Rutaceae', qualifier='')
        g1 = Genus(family=f1, genus='Citrus')
        sp1 = Species(sp="medica", genus=g1)
        sp2 = Species(sp="maxima", genus=g1)
        sp3 = Species(sp="aurantium", genus=g1)

        f2 = Family(family='Sapotaceae')
        g2 = Genus(family=f2, genus='Manilkara')
        sp4 = Species(sp='zapota', genus=g2)
        sp5 = Species(sp='zapotilla', genus=g2)
        g3 = Genus(family=f2, genus='Pouteria')
        sp6 = Species(sp='stipitata', genus=g3)

        f3 = Family(family='Musaceae')
        g4 = Genus(family=f3, genus='Musa')
        self.session.add_all([f1, f2, f3, g1, g2, g3, g4,
                              sp1, sp2, sp3, sp4, sp5, sp6])
        self.session.commit()

    def tearDown(self):
        super().tearDown()

    def test_count(self):
        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        s = 'genus where count(species.id) > 3'
        results = mapper_search.search(s, self.session)
        self.assertEqual(len(results), 0)

        s = 'genus where count(species.id) > 2'
        results = mapper_search.search(s, self.session)
        self.assertEqual(len(results), 1)
        result = results.pop()
        self.assertEqual(result.id, 1)

        s = 'genus where count(species.id) == 2'
        results = mapper_search.search(s, self.session)
        self.assertEqual(len(results), 1)
        result = results.pop()
        self.assertEqual(result.id, 2)

    def test_count_just_parse(self):
        'use BETWEEN value and value'
        import bauble.search
        SearchParser = bauble.search.SearchParser
        sp = SearchParser()
        s = 'genus where count(species.id) == 2'
        results = sp.parse_string(s)
        self.assertEqual(
            str(results.statement),
            "SELECT * FROM genus WHERE ((count species.id) == 2.0)")


class BaubleSearchSearchTest(BaubleTestCase):
    def test_search_search_uses_Mapper_Search(self):
        search.search("genus like %", self.session)
        self.assertTrue('SearchStrategy "genus like %"(MapperSearch)' in 
                   self.handler.messages['bauble.search']['debug'])
        self.handler.reset()
        search.search("12.11.13", self.session)
        self.assertTrue('SearchStrategy "12.11.13"(MapperSearch)' in 
                   self.handler.messages['bauble.search']['debug'])
        self.handler.reset()
        search.search("So ha", self.session)
        self.assertTrue('SearchStrategy "So ha"(MapperSearch)' in 
                   self.handler.messages['bauble.search']['debug'])
