import imp, unittest
from os import environ, path, remove
from optparse import OptionParser
import bauble.plugins as plugins

parser = OptionParser()
parser.add_option("-c", "--connection", dest="connection",
                  help="connect to CONN", metavar="CONN")
parser.add_option("-v", "--verbose",
                  action="store_false", dest="verbose", default=True,
                  help="display extra test information")


if __name__ == '__main__':
    (options, args) = parser.parse_args()    
    plugin_names = plugins._find_plugin_names()
    alltests = unittest.TestSuite()
    for name in plugin_names:
        try:
            print name
            mod = __import__('bauble.plugins.%s.test' % name, globals(), locals(), ['plugins'])
            if hasattr(mod, 'testsuite'):
                print 'adding tests from bauble.plugins.%s' % name
                alltests.addTest(mod.testsuite)                
        except (ImportError,), e:            
            # TODO: this could cause a problem  if there is an ImportError
            # inside the module when importing           
            #print e
            pass
    
    print '======================='
    runner = unittest.TextTestRunner()
    runner.run(alltests)    