import sys
import unittest

import bauble
import bauble.db as db
from bauble.prefs import prefs
import bauble.pluginmgr as pluginmgr

uri = 'sqlite:///:memory:'
#uri = 'postgres://test:test@ceiba/test'

def init_bauble(uri):
    try:
        db.open(uri, verify=False)
    except Exception, e:
        print >>sys.stderr, e
        #debug e
    prefs.init()
    pluginmgr.load()
    db.create(False)
    pluginmgr.init(True)


class BaubleTestCase(unittest.TestCase):

    def setUp(self):
        assert uri is not None, "The database URI is not set"
        init_bauble(uri)
        self.session = bauble.Session()

    def set_logging_level(self, level, logger='sqlalchemy'):
        logging.getLogger('sqlalchemy').setLevel(level)

    def tearDown(self):
        self.session.close()
        db.metadata.drop_all(bind=db.engine)
        bauble.pluginmgr.commands.clear()
        # why do we create the database again...?
        #db.create(False)
        pluginmgr.plugins.clear()
