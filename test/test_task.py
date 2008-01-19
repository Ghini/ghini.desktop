#
# test_plugin.py
#
import os, sys, unittest
from sqlalchemy import *
from testbase import BaubleTestCase, log
import bauble
import bauble.pluginmgr as pluginmgr
import bauble.meta as meta
import bauble.task
import bauble.utils.gtasklet as gtasklet
from bauble.utils.log import debug
import gtk


# TODO: this needs to be updated to use our own tasklet interface so we
# can get rid of gtasklet once and for all

def example_task(monitor):
    timeout = gtasklet.WaitForTimeout(1000)
    msgwait = gtasklet.WaitForMessages(accept='quit')
    for i in range(1, 10):
        debug(i)
        yield timeout
        gtasklet.get_event()
        try:
            if i == 2:
                #raise Exception
                pass
        except:
            gtasklet.WaitForMessages(accept='quit')
    #for i in xrange(10, 0, -1):
#        dialog.format_secondary_markup("Time left: <b>%i</b> seconds" % i)
#        yield timeout, msgwait
#        ev = self.get_event()
#        if isinstance(ev, gtasklet.Message) and ev.name == 'quit':
#            return
#        elif ev is timeout:
#            pass
#        else:
#            raise AssertionError
    yield gtasklet.Message('quit', dest=monitor)

class TaskTests(unittest.TestCase):


    def setUp(self):
        pass

    def testTask(self):
        return
#        def example_task(monitor):
#            yield gtasklet.Message('quit', dest=monitor)
        try:
            bauble.task.queue(example_task, None, gtk.main_quit)
        except:
            debug('caught exception')
        debug('call gtk.main()')
#        gtk.main()
        debug('past gtk.main()')

    def tearDown(self):
        pass


class TaskTestSuite(unittest.TestSuite):

    def __init__(self):
        unittest.TestSuite.__init__(self, map(TaskTests,
                                             ('testTask',)))


testsuite = TaskTestSuite

if __name__ == '__main__':
    uri = 'sqlite:///:memory:'
#    global_connect(uri)
#    bauble.create_database()
#    bauble.main(uri)
    unittest.main()
