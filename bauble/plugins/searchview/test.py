#
# test.py
#
import os, sys, unittest
from testbase import BaubleTestCase, log
from bauble.plugins.searchview.search import SearchParser
from pyparsing import *

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

# just values
value_tests = ['test'
               '"test"',# with quotes
               'test,test',
               '"test",test,test', # three values
               '"test with space"',
               "'test with spaces'",
               '"test with spaces", test, \'test\'',
               '"test,test"', # value with commas
               '"test, test", test']

# expression, domain=value
domain_tests = ['domain=' + v for v in value_tests]

# query expression domain where subdomain = value
# single subdomain
#domain where sub = values
subdomain_tests = [t.replace('domain=','domain where sub=') \
           for t in domain_tests]

# subsubdomain
#domain where sub.sub = values
subsubdomain_tests = [t.replace('domain=','domain where sub.sub=') \
              for t in domain_tests]

all_tests = value_tests + domain_tests + subdomain_tests + subsubdomain_tests


class ParseTests(unittest.TestCase):

    def setUp(self):
        self.parser = SearchParser()        
    
    def tearDown(self):
        pass
    
    def testParse(self):
        t = None
        try:
            for t in all_tests:
                p = self.parser.parse_string(t)
                print '%s --> %s' % (t, p)
        except ParseException, e:
            sys.stderr.write(t)
            print '\nException on ** %s **\n' % t
            raise


class SearchTestSuite(unittest.TestSuite):
   def __init__(self):
       unittest.TestSuite.__init__(self, map(ParseTests,
                                             ('testParse',)))

testsuite = SearchTestSuite
