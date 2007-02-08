#
# test.py
#
import os, sys, unittest
from testbase import BaubleTestCase, log
from bauble.view import SearchParser
from bauble.utils.pyparsing import *

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

# just values
#value_tests = [('test', {'values': ['test']}),
#               ('"test"', {'values': ['test']}),# with quotes
#               ('test1,test2', {'values': ['test1', 'test2']}),
#               ('"test1",test2,test3', {'values': ['test1', 'test2', 'test3']}),# three values
#               ('"test with spaces"', {'values': ['test with spaces']}),
#               ("'test with spaces'", {'values': ['test with spaces']}),
#               ('"test with spaces", test1, \'test2\'', {'values': ['test with spaces', 'test1', 'test2']}),
#               ]
value_tests = [('test'),
               ('"test"'),# with quotes
               ('test1,test2'),
               ('"test1",test2,test3'),# three values
               ('"test with spaces"'),
               ("'test with spaces'"),
               ('"test with spaces", test1, \'test2\''),
               ]
               #('"test,test"', {'values': ['test,test']}),# value with commas
               #('"test, test", test', {'values': ['test, test', 'test']})]

# domain expression
domain_tests = ['domain=%s' % v for v in value_tests]

# query expression
#[(c,v) for c in columns for v in values]
#query_tests = [t.replace('domain=', 'domain where prop.prop=') for t in value_tests]
query_tests = ['domain where prop.prop=%s' % v for v in value_tests]
#'domain where prop.prop=val and prop.prop=val
query_tests += ['%s and prop.prop=%s' % (q, v) for q in query_tests for v in value_tests]

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

all_tests = value_tests + domain_tests + query_tests
#all_tests = value_tests# + domain_tests + subdomain_tests + subsubdomain_tests

parser = SearchParser()

class ParseTests(unittest.TestCase):

    def setUp(self):
        pass
    
    def tearDown(self):
        pass
    
    def testParse(self):
        t = None
        try:
            #print value_tests
            #for s, results in all_tests:
            for s in all_tests:
                print 'parsing: %s' % s
                tokens = parser.parse_string(s)
#                print tokens.asDict
#                print tokens.asDict() == results
#                for key, value in results.iteritems():
#                    self.assert_(key in tokens, 'didn\'t match %s in %s' % (key, s))
#                    tok = tokens[key]
##                    print '%s: %s' % (str(tok), type(tok))
##                    print '%s: %s' % (str(value), type(value))
##                    print tok == value
##                    #print tokens
##                    
##                    #self.assert_(tokens[key] == value, 'tokens[%s]=%s, expected %s' % (key, tokens[key], value))
#                    self.assertEquals(str(tok), str(value), 'tokens[%s]=%s, expected %s' % (key, tokens[key], value))
                #print '%s --> %s' % (t, p)
        #except ParseException, e:
        except Exception, e:
            #sys.stderr.write(t)
            print '\nException on ** %s **\n' % s
            raise


class SearchTestSuite(unittest.TestSuite):
   def __init__(self):
       unittest.TestSuite.__init__(self, map(ParseTests,
                                             ('testParse',)))

testsuite = SearchTestSuite

if __name__ == '__main__':
    unittest.main()
