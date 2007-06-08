#
# test.py
#
# Description: test for bauble.utils

import unittest
import bauble.utils as utils

class UtilsTests(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_xml_safe(self):
        assert utils.xml_safe('test string') == 'test string'
        assert utils.xml_safe(u'test string') == u'test string'
        assert utils.xml_safe(u'test< string') == u'test&lt; string'
        assert utils.xml_safe('test< string') == 'test&lt; string'

class UtilsTestSuite(unittest.TestSuite):

   def __init__(self):
       unittest.TestSuite.__init__(self)
       self.addTests(map(UtilsTests, ('test_xml_safe',)))


testsuite = UtilsTestSuite
