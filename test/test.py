import imp, unittest, traceback
import os, sys
from optparse import OptionParser
import bauble.pluginmgr as pluginmgr
import testbase


if 'PYTHONPATH' not in os.environ or os.environ['PYTHONPATH'] is '':
    msg = 'This test suite should be run from the top of the source tree '\
          'with the command:\n  PYTHONPATH=. python test/test.py'
    print msg
    sys.exit(1)

# TODO: right now this just runs all tests but should really be able to
# pass individuals tests or test suites on the command line
default_uri = 'sqlite:///:memory:'
parser = OptionParser()
parser.add_option("-c", "--connection", dest="connection", metavar="CONN",
                  default=default_uri, help="connect to CONN")
parser.add_option("-l", "--loglevel", dest='loglevel', metavar='LEVEL (0-61)',
                  type='int', default=30, help="display extra test information")

if __name__ == '__main__':
    (options, args) = parser.parse_args()
    testbase.log.setLevel(options.loglevel)
    testbase.uri = options.connection
    if testbase.uri != default_uri:
        print 'uri: %s' % testbase.uri
    module_names = pluginmgr._find_module_names(os.getcwd())
    alltests = unittest.TestSuite()
    for name in [m for m in module_names if m.startswith('bauble')]:
        try:
            mod = __import__('%s.test' % name, globals(), locals(), [name])
            if hasattr(mod, 'testsuite'):
                testbase.log.msg('adding tests from bauble.plugins.%s' % name)
                alltests.addTest(mod.testsuite())
        except ImportError, e:
            # TODO: this could cause a problem  if there is an ImportError
            # inside the module when importing
##            testbase.log.debug(traceback.format_exc())

            # TODO: this is a bad hack
            if str(e) != 'No module named test': #shouldn't rely on string here
                testbase.log.warning('** ImportError: Could not import '\
                                     '%s.test -- %s' \
                                     % (name, e))


    testbase.log.msg('=======================')
    runner = unittest.TextTestRunner()
    if len(args) > 0:
        # run a specific testsuite, would be nice to allow running specific
        # test cases or test methods
##        unittest.TestLoader().loadTestsFromNames(args)
        for t in alltests:
            if t.__class__.__name__ in args:
                runner.run(t)
#            else:
#                raise ValueError('unknown test: %s' % t)
    else:
        runner.run(alltests)
