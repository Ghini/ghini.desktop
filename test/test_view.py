#
# test_view.py
#
import os, sys, unittest
from sqlalchemy import *
from testbase import BaubleTestCase, log
from bauble.view import SearchParser
from bauble.utils.pyparsing import *
import bauble.plugins.plants.test as plants_test
import bauble.plugins.garden.test as garden_test
from bauble.view import SearchView, MapperSearch, ResultSet

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

class SearchTestCase(BaubleTestCase):

    def __init__(self, *args):
        super(SearchTestCase, self).__init__(*args)

    def setUp(self):
        super(SearchTestCase, self).setUp()
#        plants_test.setUp_test_data()
#        garden_test.setUp_test_data()

    def tearDown(self):
        super(SearchTestCase, self).tearDown()
#        garden_test.tearDown_test_data()
#        plants_test.tearDown_test_data()

    def test_search(self):
        view = SearchView()
        from bauble.plugins.plants.family import Family, family_table
        from bauble.plugins.plants.genus import Genus, genus_table
        # MySQL doesn't allow '0' for keys it seems
        family_ids = [1, 2]
        for f in family_ids:
            family_table.insert({'id': f, 'family': unicode(f)}).execute()
        genus_ids = [2, 3]
        for g in genus_ids:
            genus_table.insert({'id': g, 'genus': unicode(g),
                                'family_id': g-2}).execute()

        test_text = {'1': [(Family, 1)],
                     'fam=1': [(Family, 1)],
#                     'fam=1 gen=2': [(Family, 1), (Genus, 2)],
                     'fam where family=1': [(Family, 1)],
                     'gen where family.family=1': [(Genus, 3)]}

        for text, expected in test_text.iteritems():
            results = ResultSet()
            for strategy in view.search_strategies:
                results.add(strategy.search(text, session=self.session))

            es = set([self.session.load(cls, cls_id) for cls, cls_id in expected])
            obj_str = lambda o: '%s(%s)' % (o.__class__.__name__, o.id)
            self.assert_(es == set(results), [obj_str(o) for o in results])


    def test_parse(self):
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


class ViewTestSuite(unittest.TestSuite):
   def __init__(self):
       unittest.TestSuite.__init__(self, map(SearchTestCase,
                                             ('test_search', 'test_parse')))

testsuite = ViewTestSuite

if __name__ == '__main__':
    unittest.main()
