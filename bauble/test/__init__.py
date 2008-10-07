import unittest
import bauble
from bauble.prefs import prefs
import bauble.pluginmgr as pluginmgr

uri = 'sqlite:///:memory:'
#uri = 'postgres://test:test@ceiba/test'

def init_bauble(uri):
    try:
        bauble.open_database(uri, verify=False)
    except Exception, e:
        print e
    prefs.init()
    pluginmgr.load()
    bauble.create_database(False)
    pluginmgr.init()


class BaubleTestCase(unittest.TestCase):

    def setUp(self):
        '''
        '''
        assert uri is not None, "The database URI is not set"
        init_bauble(uri)
        self.session = bauble.Session()

    def set_logging_level(self, level, logger='sqlalchemy'):
        logging.getLogger('sqlalchemy').setLevel(level)

    def tearDown(self):
        '''
        need to find all tests and run their tearDown methods
        '''
        self.session.close()
        bauble.metadata.drop_all()
        bauble.pluginmgr.commands.clear()
        bauble.create_database(False)
        pluginmgr.init()
#        tables()
#        logging.getLogger('sqlalchemy').setLevel(logging.ERROR)
