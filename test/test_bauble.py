#
# test_bauble.py
#
import os, sys, unittest
from sqlalchemy import *
from testbase import BaubleTestCase, log
from bauble.view import SearchParser
from bauble.utils.pyparsing import *
import bauble.plugins.plants.test as plants_test
import bauble.plugins.garden.test as garden_test
from bauble.view import SearchView, MapperSearch, ResultSet

class BaubleModuleTestCase(BaubleTestCase):

    def __init__(self, *args):
        super(BaubleModuleTestCase, self).__init__(*args)

    def setUp(self):
        super(BaubleModuleTestCase, self).setUp()

    def tearDown(self):
        super(BaubleModuleTestCase, self).tearDown()

    def test_date_time_decorator(self):
        # TODO: i don't think we use the DateTimeDecorator anymore
        return
        from bauble import DateTimeDecorator
        import bauble
        dt = DateTimeDecorator()
        #2008-02-17 17:35:22.525000-06:00
        #2008-02-17 17:35:22.525000
        #2008-02-17 17:35:22-06:00
        #2008-02-17 17:35:22
        dt.convert_bind_param("2008-02-17 17:35:22.525000-06:00", bauble.engine)


class BaubleModuleTestSuite(unittest.TestSuite):
    def __init__(self):
        unittest.TestSuite.__init__(self, map(BaubleModuleTestCase,
                                              ('test_date_time_decorator',)))

testsuite = BaubleModuleTestSuite
