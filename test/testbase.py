import unittest
from sqlalchemy import *
import bauble
import bauble.pluginmgr as pluginmgr
from bauble.prefs import prefs
import logging

# TODO: fix this logging stuff, i'm not really getting it

log = logging.getLogger('bauble.test')
def msg(msg):
    log.log(60, msg)
log.msg = msg
log.propagate = False

# info handler
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(message)s')
handler.setFormatter(formatter)
log.addHandler(handler)

# debug handler
#handler = logging.StreamHandler()
#handler.setLevel(logging.DEBUG)
#formatter = logging.Formatter('D: %(message)s')
#handler.setFormatter(formatter)
#log.addHandler(handler)

uri = None

__initialized = False

def init_bauble(uri):
    global __initialized
    if __initialized:
        return
    import bauble.db as db
    try:
        bauble.open_database(uri, verify=False)
    except Exception, e:
        print e
    bauble.create_database(False)
    prefs.init()
    pluginmgr.load()
    pluginmgr.init()
    __initialized = True


class BaubleTestCase(unittest.TestCase):

    uri = 'sqlite:///:memory:'

    def setUp(self):
        '''
        '''
        init_bauble(self.uri)
        # TODO: should have a default set of data that all of our tests can
        # rely on and we can use the same set of data for all database types
        # though the default should be to create the database in memory with
        # sqlite, each test should provide its own set of default data if
        # on plugin relies on another it should be able to access its parents
        # set of default data
        self.session = create_session()


    def tearDown(self):
        '''
        need to find all tests and run their tearDown methods
        '''
        self.session.close()
