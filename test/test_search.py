# test all possible search types

import os, sys
#sys.path.append('..')
print sys.path.append(os.getcwd())
print sys.path
from bauble.plugins.searchview.search import SearchParser

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

# just values
value_tests = ['test', 
	       '"test"', 
	       'test,test',
	       '"test",test,test', # three values
# this one shouldn't work because values can't have commas in them
#	       '"test,test,test"' # one value # 
	       ]
print value_tests


# expression, domain=value
domain_tests = ['domain=' + v for v in value_tests]
print domain_tests

# query expression domain where subdomain = value
# single subdomain
#domain where sub = values
subdomain_tests = [t.replace('domain=','domain where sub=') \
		   for t in domain_tests]
print subdomain_tests

# subsubdomain
#domain where sub.sub = values
subsubdomain_tests = [t.replace('domain=','domain where sub.sub=') \
		      for t in domain_tests]
print subsubdomain_tests

all_tests = value_tests + domain_tests + subdomain_tests + subsubdomain_tests

parser = SearchParser()
for test in all_tests:
    print 'str: ', test    
    tokens = parser.parseString(test) 
    print tokens
    if 'domain' in tokens:
#	domain = tokens['domain']
#	if isinstance(domain, list):
#	    print 'domain: ', domain[0]
#	    print 'sub: ', domain[1]
#	else:
	print 'domain: ', tokens['domain']
    if 'subdomain' in tokens:
	print 'sub: ', tokens['subdomain']
	
    print 'values: ', tokens['values']
    print '-----'
