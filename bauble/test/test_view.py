#
# test_view.py
#
import os
import sys
import unittest

from pyparsing import *
from sqlalchemy import *

import bauble
import bauble.db as db
from bauble.view import SearchParser
from bauble.view import SearchView, MapperSearch
from bauble.utils.log import debug
from bauble.test import BaubleTestCase


# TODO: test for memory leaks, could probably test

# TODO: allow AND and OR in possible values, especially so we can do...
# species where genus.family=='Orchidaceae' and accessions.acc_status!='Dead'

# TODO: this also means that we need to somehow support != as well as = which
# means we need to include the operator in the parse instead of just
# suppressing

parser = SearchParser()

# TODO: should we make these search tests independent of any plugins,
# we could use setup() to initialize a custom MapperSearch instead of
# expecting a plugin to set it up

class SearchParserTests(unittest.TestCase):


    def test_query_expression_token(self):
        s = 'domain where col=value'
        #debug(s)
        tokens = parser.query.parseString(s)
        #debug(tokens)

        s = 'domain where relation.col=value'
        tokens = parser.query.parseString(s)
        #debug(tokens)

        s = 'domain where relation.relation.col=value'
        tokens = parser.query.parseString(s)
        #debug(tokens)

        s = 'domain where relation.relation.col=value and col2=value2'
        tokens = parser.query.parseString(s)
        #debug(tokens)


    def test_statement_token(self):
        pass


    def test_domain_expression_token(self):
        """
        Test the domain_expression token
        """
        # allow dom=val1, val2, val3
        s = 'domain=test'
        expected = ['domain', '=', 'test']
        tokens = parser.domain_expression.parseString(s, parseAll=True)

        def breakup(tokens):
            domain, op, values = tokens
            values = list(values)
            return [domain, op, values]

        s = 'domain==test'
        expected = ['domain', '==', ['test']]
        tokens = parser.domain_expression.parseString(s, parseAll=True)
        self.assert_(breakup(tokens)==expected,
                     self.error_msg(s, breakup(tokens), expected))

        s = 'domain=test1 test2 test3'
        expected = ['domain', '=', ['test1', 'test2', 'test3']]
        tokens = parser.domain_expression.parseString(s, parseAll=True)
        self.assert_(breakup(tokens)==expected,
                     self.error_msg(s, breakup(tokens), expected))

        s = 'domain=test1 "test2 test3" test4'
        expected = ['domain', '=', ['test1', 'test2 test3', 'test4']]
        tokens = parser.domain_expression.parseString(s, parseAll=True)
        self.assert_(breakup(tokens)==expected,
                     self.error_msg(s, breakup(tokens), expected))

        s = 'domain="test test"'
        expected = ['domain', '=', ['test test']]
        tokens = parser.domain_expression.parseString(s, parseAll=True)
        self.assert_(breakup(tokens)==expected,
                     self.error_msg(s, breakup(tokens), expected))

        s = 'domain=*'
        expected = ['domain', '=', '*']
        tokens = parser.domain_expression.parseString(s, parseAll=True)
        self.assert_(list(tokens) == expected,
                     self.error_msg(s, tokens, expected))


    def test_value_token(self):
        """
        Test the value token
        """
        strings = ['test', '"test"', "'test'"]
        expected = ['test']
        for s in strings:
            tokens = parser.value.parseString(s, parseAll=True)
            self.assert_(list(tokens) == ['test'],
                         self.error_msg(s, tokens, expected))

        strings = ['"test1 test2"', "'test1 test2'"]
        expected = ['test1 test2']
        for s in strings:
            tokens = parser.value.parseString(s, parseAll=True)
            self.assert_(list(tokens) == expected,
                         self.error_msg(s, tokens, expected))


        strings = ['%.-_*', '"%.-_*"']
        expected = ['%.-_*']
        for s in strings:
            tokens = parser.value.parseString(s, parseAll=True)
            self.assert_(list(tokens) == expected,
                         self.error_msg(s, tokens, expected))


        # these should be invalid
        strings = ['test test', '"test', "test'", '$',]
        for s in strings:
            try:
                tokens = parser.value.parseString(s, parseAll=True)
            except ParseException, e:
                pass
            else:
                self.fail('ParseException not raised: "%s" - %s' \
                          % (s, tokens))

    error_msg = lambda me, s, v, e:  '%s: %s == %s' % (s, v, e)

    def test_value_list_token(self):
        """
        Test the value_list token
        """
        strings = ['test', '"test"', "'test'"]
        expected = ['test']
        for s in strings:
            tokens = parser.value_list.parseString(s, parseAll=True)
            self.assert_(list(tokens) == expected,
                         self.error_msg(s, tokens, expected))

        strings = ['test1, test2', '"test1", test2', "test1, 'test2'"]
        expected = ['test1', 'test2']
        for s in strings:
            tokens = parser.value_list.parseString(s, parseAll=True)
            self.assert_(list(tokens)==expected,
                          self.error_msg(s, tokens, expected))

        strings = ['test1 test2 test3', '"test1" test2 \'test3\'']
        expected = ['test1', 'test2', 'test3']
        for s in strings:
            tokens = parser.value_list.parseString(s, parseAll=True)
            self.assert_(list(tokens) == expected,
                         self.error_msg(s, tokens, expected))

        strings = ['"test1 test2", test3']
        expected = ['test1 test2', 'test3']
        for s in strings:
            tokens = parser.value_list.parseString(s, parseAll=True)
            self.assert_(list(tokens) == expected,
                         self.error_msg(s, tokens, expected))


        # these should be invalid
        strings = ['"test', "test'", "'test tes2"]
        for s in strings:
            try:
                tokens = parser.value_list.parseString(s, parseAll=True)
            except ParseException, e:
                pass
            else:
                self.fail('ParseException not raised: "%s" - %s' \
                          % (s, tokens))


class SearchTests(BaubleTestCase):

    def __init__(self, *args):
        super(SearchTests, self).__init__(*args)

    def setUp(self):
        super(SearchTests, self).setUp()

    def tearDown(self):
        super(SearchTests, self).tearDown()


    def test_search_by_values(self):
        """
        Test searching by values with MapperSearch

        This test does not test that of the plugins setup their search
        properly, it only tests the MapperSearch works as expected
        """
        from bauble.plugins.plants.family import Family
        from bauble.plugins.plants.genus import Genus
        view = SearchView()
        family = Family(family=u'family')
        genus = Genus(family=family, genus=u'genus')
        self.session.add_all([family, genus])
        self.session.commit()
        mapper_search = view.search_strategies[0]
        self.assert_(isinstance(mapper_search, MapperSearch))

        # search for family by family name
        results = mapper_search.search('family', self.session)
        f = list(results)[0]
        self.assert_(isinstance(f, Family) and f.id==family.id)

        # search for genus by genus name
        results = mapper_search.search('genus', self.session)
        g = list(results)[0]
        self.assert_(isinstance(g, Genus) and g.id==genus.id)


    def test_search_by_expression(self):
        """
        Test searching by expression with MapperSearch

        This test does not test that of the plugins setup their search
        properly, it only tests the MapperSearch works as expected
        """
        from bauble.plugins.plants.family import Family
        from bauble.plugins.plants.genus import Genus
        view = SearchView()
        family = Family(family=u'family')
        genus = Genus(family=family, genus=u'genus')
        self.session.add_all([family, genus])
        self.session.commit()
        mapper_search = view.search_strategies[0]
        self.assert_(isinstance(mapper_search, MapperSearch))

        # search for family by domain
        results = mapper_search.search('fam=family', self.session)
        f = list(results)[0]
        self.assert_(isinstance(f, Family) and f.id==family.id)

        # search for genus by domain
        results = mapper_search.search('gen=genus', self.session)
        g = list(results)[0]
        self.assert_(isinstance(g, Genus) and g.id==genus.id)


    def test_search_by_query(self):
        """
        Test searching by expression with MapperSearch

        This test does not test that of the plugins setup their search
        properly, it only tests the MapperSearch works as expected
        """
        from bauble.plugins.plants.family import Family
        from bauble.plugins.plants.genus import Genus
        view = SearchView()
        family = Family(family=u'family')
        family2 = Family(family=u'family2')
        genus = Genus(family=family, genus=u'genus')
        genus2 = Genus(family=family2, genus=u'genus2')
        self.session.add_all([family, family2, genus, genus2])
        self.session.commit()
        mapper_search = view.search_strategies[0]
        self.assert_(isinstance(mapper_search, MapperSearch))

        # search cls.column
        results = mapper_search.search('fam where family=family', self.session)
        f = list(results)[0]
        self.assert_(isinstance(f, Family) and f.id==family.id)

        # search cls.parent.column
        results = mapper_search.search('genus where family.family=family',
                                       self.session)
        g = list(results)[0]
        self.assert_(len(results) == 1 and isinstance(g, Genus) \
                     and g.id==genus.id, [str(o) for o in list(results)])

        # search cls.children.column
        results = mapper_search.search('family where genera.genus=genus',
                                       self.session)
        f = list(results)[0]
        self.assert_(len(results) == 1 and isinstance(f, Family) \
                         and f.id==family.id)

        # search with multiple conditions and'ed together
        #debug('--------')
        f3 = Family(family=u'fam3')
        g3 = Genus(family=f3, genus=u'genus2')
        self.session.add_all([f3, g3])
        self.session.commit()
        s = 'genus where genus=genus2 and family.family=fam3'
        results = mapper_search.search(s, self.session)
        g = list(results)[0]
        self.assert_(len(results) == 1 and isinstance(g, Genus) \
                     and g.id==g3.id)

        # search with or conditions
        g4 = Genus(family=f3, genus=u'genus4')
        self.session.add(g4)
        self.session.commit()
        s = 'genus where genus=genus2 or genus=genus'
        results = mapper_search.search(s, self.session)
        self.assert_(len(results) == 3)
        self.assert_(sorted([r.id for r in results]) \
                     == [g.id for g in (genus, genus2, g3)])

        s = 'genus where family.family="Orchidaceae" and family.qualifier=""'
        results = mapper_search.search(s, self.session)
        r = list(results)
        #debug(list(results))

        # TODO: create a query to test the =None statement, can't use
        # family.qualifier b/c its default value is ''
        s = 'genus where family.family=fam3 and family.qualifier=None'
        results = mapper_search.search(s, self.session)
        r = list(results)
        #debug(list(results))
        # self.assert_(results.count() == 3)
        # self.assert_(sorted([r.id for r in results]) \
        #              == [g.id for g in (genus, genus2, g3)])

        # test the searching with the empty string does exactly that
        # and does try to use None
        s = 'genus where family.family=Orchidaceae and family.qualifier = ""'
        results = mapper_search.search(s, self.session)
        r = list(results)
        #debug(list(results))

        # make sure None isn't treated as the string 'None' and that
        # the query picks up the is operator
        s = 'genus where family.qualifier is None'
        results = mapper_search.search(s, self.session)
        r = list(results)
        #debug(list(results))

        # test where the column is ambiguous so make sure we choose
        # the right one, in this case we want to make sure we get the
        # qualifier on the family and not the genus
        s = 'plant where accession.species.genus.family.family="Orchidaceae" '\
            'and accession.species.genus.family.qualifier=""'
        results = mapper_search.search(s, self.session)
        r = list(results)
        #debug(r)

        # id is an ambiguous column because it occurs on plant,
        # accesion and species...the results here don't matter as much
        # as the fact that the query doesn't raise and exception
        s = 'plant where accession.species.id=1'
        results = mapper_search.search(s, self.session)
        r = list(results)

        # test partial string matches on a query
        s = 'genus where family.family like family%'
        results = mapper_search.search(s, self.session)
        self.assert_(set(results) == set([genus, genus2]))

