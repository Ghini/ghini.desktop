import unittest
from sqlalchemy import *
import bauble
import bauble.plugins as plugins
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

class BaubleTestCase(unittest.TestCase):
    
    def setUp(self):
        '''    
        '''
        prefs.init()
        plugins.init_plugins()
        global_connect(uri)
        bauble.create_database(False)
        self.session = create_session()

    
    def tearDown(self):
        '''
        need to find all tests and run their tearDown methods
        '''
        self.session.close()
