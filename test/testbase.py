from sqlalchemy import *
import bauble
import bauble.plugins as plugins
from bauble.prefs import prefs


class BaubleTestCase(unittest.TestCase):
    
    def setUp(self):
        '''    
        '''
        prefs.init()
        plugins.init_plugins()
        if options.connection:
            uri = options.connection
        else:
            uri = 'sqlite:///:memory:'    
        global_connect(uri)
        bauble.app.create_database(False)
        self.session = create_session()

    
    def tearDown(self):
        '''
        need to find all tests and run their tearDown methods
        '''
        self.session.close()