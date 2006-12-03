import imp, unittest, traceback
from os import environ, path, remove
from optparse import OptionParser
import bauble.plugins as plugins
import testbase

# TODO: right now this just runs all tests but should really be able to 
# pass individuals tests or test suites on the command line
parser = OptionParser()
parser.add_option("-c", "--connection", dest="connection", metavar="CONN",
                  default='sqlite:///:memory:', help="connect to CONN")
parser.add_option("-l", "--loglevel", dest='loglevel', metavar='LEVEL (0-61)',
                  type='int', default=30, help="display extra test information")

if __name__ == '__main__':        
    (options, args) = parser.parse_args()
    testbase.log.setLevel(options.loglevel)
    testbase.uri = options.connection
    plugin_names = plugins._find_plugin_names()
    alltests = unittest.TestSuite()
    for name in plugin_names:
        try:        
            mod = __import__('bauble.plugins.%s.test' % name, globals(), locals(), ['plugins'])
            if hasattr(mod, 'testsuite'):
                testbase.log.msg('adding tests from bauble.plugins.%s' % name)
                alltests.addTest(mod.testsuite())     
        except (ImportError,), e:
            # TODO: this could cause a problem  if there is an ImportError
            # inside the module when importing           
            testbase.log.debug(traceback.format_exc())
            # TODO: this is a bad hack
            if str(e) != 'No module named test':                
                print e
            
    
    testbase.log.msg('=======================')
    runner = unittest.TextTestRunner()
    runner.run(alltests)    