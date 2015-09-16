# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Brett Adams
# Copyright 2015 Mario Frasca <mario@anche.no>.
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
from bauble.test import BaubleTestCase


# TODO: test for memory leaks, could probably test


class Results(object):
    def __init__(self):
        self.results = {}

    def callback(self, *args, **kwargs):
        self.results['args'] = args
        self.results['kwargs'] = kwargs


parse_results = Results()

parser = search.SearchParser()


class SearchParserTests(unittest.TestCase):
    error_msg = lambda me, s, v, e:  '%s: %s == %s' % (s, v, e)

    def test_query_expression_token_UPPER(self):
        s = 'domain where col=value'
        #debug(s)
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
        self.assertEquals(results.getName(), 'domain_expression')
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
        self.assertEquals(results.getName(), 'value')
        self.assertEquals(results.value.express(), 123.0)
        results = parser.value.parseString('123.1')
        self.assertEquals(results.value.express(), 123.1)

    def test_datetime_token(self):
        "recognizes datetime syntax"

        from datetime import datetime
        results = parser.value.parseString('|datetime|1970,1,1|')
        self.assertEquals(results.getName(), 'value')
        self.assertEquals(results.value.express(), datetime(1970, 1, 1))

    def test_value_token(self):
        "value should only return the first string or raise a parse exception"

        strings = ['test', '"test"', "'test'"]
        expected = 'test'
        for s in strings:
            results = parser.value.parseString(s, parseAll=True)
            self.assertEquals(results.getName(), 'value')
            self.assertEquals(results.value.express(), expected)

        strings = ['123.000', '123.', "123.0"]
        expected = 123.0
        for s in strings:
            results = parser.value.parseString(s)
            self.assertEquals(results.getName(), 'value')
            self.assertEquals(results.value.express(), expected)

        strings = ['"test1 test2"', "'test1 test2'"]
        expected = 'test1 test2'  # this is one string! :)
        for s in strings:
            results = parser.value.parseString(s, parseAll=True)
            self.assertEquals(results.getName(), 'value')
            self.assertEquals(results.value.express(), expected)

        strings = ['%.-_*', '"%.-_*"']
        expected = '%.-_*'
        for s in strings:
            results = parser.value.parseString(s, parseAll=True)
            self.assertEquals(results.getName(), 'value')
            self.assertEquals(results.value.express(), expected)

        # these should be invalid
        strings = ['test test', '"test', "test'", '$', ]
        for s in strings:
            try:
                results = parser.value.parseString(s, parseAll=True)
            except ParseException:
                pass
            else:
                self.fail('ParseException not raised: "%s" - %s'
                          % (s, results))

    def test_needs_join(self):
        "check the join steps"

        env = None
        results = parser.statement.parseString("plant where accession.species."
                                               "id=44")
        self.assertEquals(results.statement.content.filter.needs_join(env),
                          [['accession', 'species']])
        results = parser.statement.parseString("plant where accession.id=44")
        self.assertEquals(results.statement.content.filter.needs_join(env),
                          [['accession']])
        results = parser.statement.parseString("plant where accession.id=4 OR "
                                               "accession.species.id=3")
        self.assertEquals(results.statement.content.filter.needs_join(env),
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
            self.assertEquals(results.getName(), 'value_list')
            self.assertEquals(str(results), str(expected))

        strings = ['test', '"test"', "'test'"]
        expected = [['test']]
        for s in strings:
            results = parser.value_list.parseString(s, parseAll=True)
            self.assertEquals(results.getName(), 'value_list')
            self.assertEquals(str(results), str(expected))

        strings = ['test1 test2 test3', '"test1" test2 \'test3\'']
        expected = [['test1', 'test2', 'test3']]
        for s in strings:
            results = parser.value_list.parseString(s, parseAll=True)
            self.assertEquals(str(results), str(expected))

        strings = ['"test1 test2", test3']
        expected = [['test1 test2', 'test3']]
        for s in strings:
            results = parser.value_list.parseString(s, parseAll=True)
            self.assertEquals(str(results), str(expected))

        # these should be invalid
        strings = ['"test', "test'", "'test tes2"]
        for s in strings:
            try:
                results = parser.value_list.parseString(s, parseAll=True)
            except ParseException:
                pass
            else:
                self.fail('ParseException not raised: "%s" - %s'
                          % (s, results))


class SearchTests(BaubleTestCase):
    def __init__(self, *args):
        super(SearchTests, self).__init__(*args)

    def setUp(self):
        super(SearchTests, self).setUp()
        db.engine.execute('delete from genus')
        db.engine.execute('delete from family')
        from bauble.plugins.plants.family import Family
        from bauble.plugins.plants.genus import Genus
        self.family = Family(family=u'family1', qualifier=u's. lat.')
        self.genus = Genus(family=self.family, genus=u'genus1')
        self.Family = Family
        self.Genus = Genus
        self.session.add_all([self.family, self.genus])
        self.session.commit()

    def tearDown(self):
        super(SearchTests, self).tearDown()

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
        """
        Test searching by values with MapperSearch

        test whether the MapperSearch works, not a test on plugins.
        """
        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        # search for family by family name
        results = mapper_search.search('family1', self.session)
        self.assertEquals(len(results), 1)
        f = list(results)[0]
        self.assertEqual(f.id, self.family.id)

        # search for genus by genus name
        results = mapper_search.search('genus1', self.session)
        self.assertEquals(len(results), 1)
        g = list(results)[0]
        self.assertEqual(g.id, self.genus.id)

    def test_search_by_expression(self):
        """
        Test searching by expression with MapperSearch

        test whether the MapperSearch works, not a test on plugins.
        """
        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        # search for family by domain
        results = mapper_search.search('fam=family1', self.session)
        self.assertEquals(len(results), 1)
        f = list(results)[0]
        self.assertTrue(isinstance(f, self.Family))
        self.assertEquals(f.id, self.family.id)

        # search for genus by domain
        results = mapper_search.search('gen=genus1', self.session)
        self.assertEquals(len(results), 1)
        g = list(results)[0]
        self.assertTrue(isinstance(g, self.Genus))
        self.assertEqual(g.id, self.genus.id)

    def test_search_by_query11(self):
        "query with MapperSearch, single table, single test"

        # test does not depend on plugin functionality
        Family = self.Family
        Genus = self.Genus
        family2 = Family(family=u'family2')
        genus2 = Genus(family=family2, genus=u'genus2')
        self.session.add_all([family2, genus2])
        self.session.commit()

        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        # search cls.column
        results = mapper_search.search('genus where genus=genus1',
                                       self.session)
        self.assertEquals(len(results), 1)
        f = list(results)[0]
        self.assertTrue(isinstance(f, Genus))
        self.assertEqual(f.id, self.family.id)

    def test_search_by_query12(self):
        "query with MapperSearch, single table, p1 OR p2"

        # test does not depend on plugin functionality
        Family = self.Family
        Genus = self.Genus
        family2 = Family(family=u'family2')
        genus2 = Genus(family=family2, genus=u'genus2')
        f3 = Family(family=u'fam3')
        g3 = Genus(family=f3, genus=u'genus2')
        g4 = Genus(family=f3, genus=u'genus4')
        self.session.add_all([family2, genus2, f3, g3, g4])
        self.session.commit()

        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        # search with or conditions
        s = 'genus where genus=genus2 OR genus=genus1'
        results = mapper_search.search(s, self.session)
        self.assertEqual(len(results), 3)
        self.assert_(sorted([r.id for r in results])
                     == [g.id for g in (self.genus, genus2, g3)])

    def test_search_by_query13(self):
        "query with MapperSearch, single table, p1 AND p2"

        # test does not depend on plugin functionality
        Family = self.Family
        Genus = self.Genus
        family2 = Family(family=u'family2')
        genus2 = Genus(family=family2, genus=u'genus2')
        f3 = Family(family=u'fam3')
        g3 = Genus(family=f3, genus=u'genus2')
        g4 = Genus(family=f3, genus=u'genus4')
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
        family2 = Family(family=u'family2')
        genus2 = Genus(family=family2, genus=u'genus2')
        self.session.add_all([family2, genus2])
        self.session.commit()

        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        # search cls.parent.column
        results = mapper_search.search('genus where family.family=family1',
                                       self.session)
        self.assertEquals(len(results), 1)
        g0 = list(results)[0]
        self.assertTrue(isinstance(g0, Genus))
        self.assertEquals(g0.id, self.genus.id)

        # search cls.children.column
        results = mapper_search.search('family where genera.genus=genus1',
                                       self.session)
        self.assertEquals(len(results), 1)
        f = list(results)[0]
        self.assertEqual(len(results), 1)
        self.assertTrue(isinstance(f, Family))
        self.assertEqual(f.id, self.family.id)

    def test_search_by_query22(self):
        "query with MapperSearch, joined tables, multiple predicates"

        # test does not depend on plugin functionality
        Family = self.Family
        Genus = self.Genus
        family2 = Family(family=u'family2')
        g2 = Genus(family=family2, genus=u'genus2')
        f3 = Family(family=u'fam3', qualifier=u's. lat.')
        g3 = Genus(family=f3, genus=u'genus3')
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
        family2 = Family(family=u'family2')
        g2 = Genus(family=family2, genus=u'genus2')
        f3 = Family(family=u'fam3', qualifier=u's. lat.')
        g3 = Genus(family=f3, genus=u'genus3')
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
        family2 = Family(family=u'family2')
        g2 = Genus(family=family2, genus=u'genus2')
        f3 = Family(family=u'fam3', qualifier=u's. lat.')
        g3 = Genus(family=f3, genus=u'genus3')
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
        family2 = Family(family=u'family2')
        genus2 = Genus(family=family2, genus=u'genus2')
        f3 = Family(family=u'fam3')
        g3 = Genus(family=f3, genus=u'genus3')
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
        family2 = Family(family=u'family2')
        genus2 = Genus(family=family2, genus=u'genus2')
        f3 = Family(family=u'fam3')
        g3 = Genus(family=f3, genus=u'genus3')
        self.session.add_all([family2, genus2, f3, g3])
        self.session.commit()

        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        # test partial string matches on a query
        s = 'genus where family.family like family%'
        results = mapper_search.search(s, self.session)
        self.assert_(set(results) == set([self.genus, genus2]))

    def test_search_by_query22_underscore(self):
        """can use fields starting with an underscore"""

        import datetime
        Family = self.Family
        Genus = self.Genus
        from bauble.plugins.plants.species_model import Species
        from bauble.plugins.garden.accession import Accession
        from bauble.plugins.garden.location import Location
        from bauble.plugins.garden.plant import Plant
        family2 = Family(family=u'family2')
        g2 = Genus(family=family2, genus=u'genus2')
        f3 = Family(family=u'fam3', qualifier=u's. lat.')
        g3 = Genus(family=f3, genus=u'Ixora')
        sp = Species(sp=u"coccinea", genus=g3)
        ac = Accession(species=sp, code=u'1979.0001')
        lc = Location(name=u'loc1', code=u'loc1')
        pp = Plant(accession=ac, code=u'01', location=lc, quantity=1)
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
        family2 = Family(family=u'family2')
        g2 = Genus(family=family2, genus=u'genus2')
        f3 = Family(family=u'fam3', qualifier=u's. lat.')
        g3 = Genus(family=f3, genus=u'Ixora')
        sp = Species(sp=u"coccinea", genus=g3)
        ac = Accession(species=sp, code=u'1979.0001')
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
        family2 = Family(family=u'family2')
        g2 = Genus(family=family2, genus=u'genus2')
        f3 = Family(family=u'fam3', qualifier=u's. lat.')
        g3 = Genus(family=f3, genus=u'Ixora')
        g4 = Genus(family=f3, genus=u'Schetti')
        self.session.add_all([family2, g2, f3, g3, g4])
        g4.accepted = g3
        self.session.commit()

        mapper_search = search.get_strategy('SynonymSearch')

        s = 'Schetti'
        results = mapper_search.search(s, self.session)
        self.assertEqual(results, [g3])

    def test_search_by_query_binomial(self):
        """can use genus_species binomial identification"""

        raise SkipTest
        Family = self.Family
        Genus = self.Genus
        from bauble.plugins.plants.species_model import Species
        family2 = Family(family=u'family2')
        g2 = Genus(family=family2, genus=u'genus2')
        f3 = Family(family=u'fam3', qualifier=u's. lat.')
        g3 = Genus(family=f3, genus=u'Ixora')
        sp = Species(sp=u"coccinea", genus=g3)
        self.session.add_all([family2, g2, f3, g3, sp])
        self.session.commit()

        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        s = '"Ixora coccinea"'
        results = mapper_search.search(s, self.session)
        self.assertEqual(results, set([sp]))

    def test_search_by_query_vernacural(self):
        """can find species by vernacular name"""

        Family = self.Family
        Genus = self.Genus
        from bauble.plugins.plants.species_model import Species
        from bauble.plugins.plants.species_model import VernacularName
        family2 = Family(family=u'family2')
        g2 = Genus(family=family2, genus=u'genus2')
        f3 = Family(family=u'fam3', qualifier=u's. lat.')
        g3 = Genus(family=f3, genus=u'Ixora')
        sp = Species(sp=u"coccinea", genus=g3)
        vn = VernacularName(name=u"coral rojo", language=u"es", species=sp)
        self.session.add_all([family2, g2, f3, g3, sp, vn])
        self.session.commit()

        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

        s = "rojo"
        results = mapper_search.search(s, self.session)
        self.assertEqual(results, set([sp]))


class QueryBuilderTests(BaubleTestCase):

    def test_cancreatequerybuilder(self):
        search.QueryBuilder()

    def test_emptyisinvalid(self):
        qb = search.QueryBuilder()
        self.assertFalse(qb.validate())


class BuildingSQLStatements(BaubleTestCase):
    import bauble.search
    SearchParser = bauble.search.SearchParser

    def test_canfindspeciesfromgenus(self):
        'can find species from genus'

        text = u'species where species.genus=genus1'
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

    def test_between_just_parse(self):
        'use BETWEEN value and value'
        sp = self.SearchParser()
        results = sp.parse_string('species where id between 0 and 1')
        self.assertEqual(str(results.statement),
                         "SELECT * FROM species WHERE (BETWEEN id 0.0 1.0)")
