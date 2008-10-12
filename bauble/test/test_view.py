#
# test_view.py
#
import os
import sys
import unittest

from sqlalchemy import *

import bauble
from bauble.view import SearchParser
from bauble.utils.pyparsing import *
from bauble.view import SearchView, MapperSearch, ResultSet
from bauble.utils.log import debug
from bauble.test import BaubleTestCase

# test search parser

# TODO: do a replacement on all the quotes in the tests to test for both single
# and double quotes

# TODO: replace all '=' with '=='

# TODO: add spaces in different places to check for ignoring whitespace

# TODO: create some invalid search strings that should definitely break the
# parser

# TODO: allow AND and OR in possbile values, especially so we can do...
# species where genus.family=='Orchidaceae' and accessions.acc_status!='Dead'

# TODO: this also means that we need to somehow support != as well as = which
# means we need to include the operator in the parse instead of just
# suppressing

# TODO: generate documentation directly from tables so its easier for the
# user to know which subdomain they can search, this could also include the
# search domains, table names, columns types, etc

# TODO: need to test that the parse results match up with the setResultsName
# parameter, maybe create a dict like {'test': {'values': [['test']]}} which
# means that 'test' would parse to tokens.value = [['test']]


#domain where sub=val,val,val and sub2=val2
#domain = val1, val2 and domain2 = val3 # join
#domain where expression logical_operator operator expression
# val1 val2 val3 = and(val1, val2, val3)
# "val1 with space" val2 val3 = and('val1 with spaces', val2, val3)

# expression =  identifier bin_op value [log_op expression]

# 1. domain where join1.join_or_col = val
# -- query statement with simple expressions after "where"
# find table for search domain, join1 must be a join, if join_or_col is a
# column then compare its value to val, if join_or_col is a join/object then
# find the search meta for this object type and search again the columns in the
# search meta
#
# 2. domain where join_or_col = val
# -- query statement with expressions after "where"
# find the table for search domain, if join_or_col is a join/object then
# find the search meta for this object type and search again the columns in the
# search meta
#
# 3. domain = value [ domain = value...]
# -- expression where domain must be in domain_map and multiple expressions
#    are OR'd together
# get the search meta for domain and search the columns in the meta
# for value
#
# 4. value [ value...]
# -- expression where domain is implied as all domains and the
#    operator is LIKE %val%) and multiple values are OR'd together]
# search all the search metas for all domain for value


# just values
#value_tests = [('test', {'values': ['test']}),
#               ('"test"', {'values': ['test']}),# with quotes
#               ('test1,test2', {'values': ['test1', 'test2']}),
#               ('"test1",test2,test3', {'values': ['test1', 'test2', 'test3']}),# three values
#               ('"test with spaces"', {'values': ['test with spaces']}),
#               ("'test with spaces'", {'values': ['test with spaces']}),
#               ('"test with spaces", test1, \'test2\'', {'values': ['test with spaces', 'test1', 'test2']}),
#               ]
value_tests = {'test': {'values': ['test']},
               'test1 test2': {'values': ['test1', 'test2']},
               'test1, test2': {'values': ['test1', 'test2']},
               'test1,test2,test3': {'values': ['test1', 'test2', 'test3']},
               '"test with spaces"': {'values': ['test with spaces']},
               "'test with spaces'": {'values': ['test with spaces']},
               '"test with spaces", test1, \'test2\'': \
                   {'values': ['test with spaces', 'test1', 'test2']}
                }


# domain expression
domain_tests = ['domain=%s' % v for v in value_tests.keys()]

# query expression
#[(c,v) for c in columns for v in values]
#query_tests = [t.replace('domain=', 'domain where prop.prop=') for t in value_tests]
query_tests = ['domain where prop.prop=%s' % v for v in value_tests.keys()]
#'domain where prop.prop=val and prop.prop=val
query_tests += ['%s and prop.prop=%s' % (q, v) for q in query_tests for v in value_tests.keys()]

# query expression domain where subdomain = value
# single subdomain
#domain where sub = values
#subdomain_tests = [t.replace('domain=','domain where sub=') \
#           for t in domain_tests]
#
## subsubdomain
##domain where sub.sub = values
#subsubdomain_tests = [t.replace('domain=','domain where sub.sub=') \
#              for t in domain_tests]

all_tests = value_tests.keys() + domain_tests + query_tests
#all_tests = value_tests# + domain_tests + subdomain_tests + subsubdomain_tests

parser = SearchParser()


# TODO: should we make these search tests independent of any plugins,
# we could use setup() to initialize a custom MapperSearch instead of
# expecting a plugin to set it up

# TODO: these tests still need to be more extensive, see the above
# values_tests


class SearchTests(BaubleTestCase):

    def __init__(self, *args):
        super(SearchTests, self).__init__(*args)

    def setUp(self):
        super(SearchTests, self).setUp()

    def tearDown(self):
        super(SearchTests, self).tearDown()


    def test_result_set(self):
        # TODO: This doesn't really do anything at the moment, i
        # started writing it to test out slicing with the ResultSet

        return

        from bauble.plugins.plants.family import Family
        ids = xrange(1,1000)
        table = Family.__table__
        values = []
        for i in ids:
            values.append({'id': i, 'family': u'%s' % i})
        bauble.engine.execute(table.insert(), values)
        view = SearchView()
        mapper_search = view.search_strategies[0]
        result = mapper_search.search('fam=*')
        #debug('list')
        for v in result: pass
        #debug('done')


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
        results = mapper_search.search('family')
        f = list(results)[0]
        self.assert_(isinstance(f, Family) and f.id==family.id)

        # search for genus by genus name
        results = mapper_search.search('genus')
        g = list(results)[0]
        self.assert_(isinstance(g, Genus) and g.id==genus.id)


    def test_search_by_expression(self):
        """
        Test searching by express with MapperSearch

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
        results = mapper_search.search('fam=family')
        f = list(results)[0]
        self.assert_(isinstance(f, Family) and f.id==family.id)

        # search for genus by domain
        results = mapper_search.search('gen=genus')
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
        results = mapper_search.search('fam where family=family')
        f = list(results)[0]
        self.assert_(isinstance(f, Family) and f.id==family.id)

        # search cls.parent.column
        results = mapper_search.search('genus where family.family=family')
        g = list(results)[0]
        self.assert_(results.count() == 1 and isinstance(g, Genus) \
                     and g.id==genus.id, [str(o) for o in list(results)])

        # search cls.children.column
        results = mapper_search.search('family where genera.genus=genus')
        f = list(results)[0]
        self.assert_(results.count() == 1 and isinstance(f, Family) \
                     and f.id==family.id)

        # search with multiple conditions and'ed together
        #debug('--------')
        f3 = Family(family=u'fam3')
        g3 = Genus(family=f3, genus=u'genus2')
        self.session.add_all([f3, g3])
        self.session.commit()
        s = 'genus where genus=genus2 and family.family=fam3'
        results = mapper_search.search(s)
        g = list(results)[0]
        self.assert_(results.count() == 1 and isinstance(g, Genus) \
                     and g.id==g3.id)

        # search with or conditions
        g4 = Genus(family=f3, genus=u'genus4')
        self.session.add(g4)
        self.session.commit()
        s = 'genus where genus=genus2 or genus=genus'
        results = mapper_search.search(s)
        self.assert_(results.count() == 3)
        self.assert_(sorted([r.id for r in results]) \
                     == [g.id for g in (genus, genus2, g3)])



    def test_search_parser(self):
        """
        Test the bauble.view.SearchParser
        """
        t = None
        s = ''
        tokens = None
        try:
            for s, expected  in value_tests.iteritems():
                tokens = parser.parse_string(s)
                for e_key, e_value in expected.iteritems():
#                    print tokens[e_key].getName()
#                    print tokens.getName()
                    self.assert_(tokens[e_key].asList() == e_value,
                                 ' - expected: %s\n - got: %s' % \
                                 ('%s=%s' % (e_key, e_value),
                                  '%s=%s' % (e_key, tokens[e_key])))

            for s in domain_tests:
                tokens = parser.parse_string(s)
            for s in query_tests:
                tokens = parser.parse_string(s)

        except Exception, e:
            self.fail('\nException parsing ** %s **\n%s\nParseResults:\n%s' % \
                          (s, e, tokens.dump(indent='  ')))



