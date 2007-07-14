#
# test imex plugins
#

import os, unittest
from sqlalchemy import *
from testbase import BaubleTestCase, log
import bauble.plugins.plants.test as plants_test
import bauble.plugins.garden.test as garden_test
from bauble.plugins.imex.csv_ import CSVImporter, CSVExporter

# TODO: test that when we import data we get what we expect
# TODO: test that all Unicode works
# TODO: test that when we export data we get what we expect
# TODO: test that importing and then exporting gives the same data
# TODO: test that exporting and then importing gives the same data

csv_test_data = ({})

class TestCSVImporter(CSVImporter):

    def on_quit(self):
        gtk.main_quit()

class ImexTestCase(BaubleTestCase):

    def __init__(self, *args):
        super(ImexTestCase, self).__init__(*args)

    def setUp(self):
        super(ImexTestCase, self).setUp()
        plants_test.setUp_test_data()
        garden_test.setUp_test_data()

    def tearDown(self):
        super(ImexTestCase, self).tearDown()
        garden_test.tearDown_test_data()
        plants_test.tearDown_test_data()


class ImexCSVTestCase(ImexTestCase):

    def test_import(self):
        # TODO: this test doesn't really test yet that any of the data was
        # correctly imported or exported, only that export and importing
        # run successfuly

        # 1. write the test data to a temporary file or files
        # 2. import the data and make sure the objects match field for field

        # the exporters and importers show logging information, turn it off
        import logging
        logging.getLogger('bauble.info').setLevel(logging.ERROR)
        import tempfile
        tempdir = tempfile.mkdtemp()

        # export all the testdata
        exporter = CSVExporter()
        exporter.start(tempdir)

        # import all the files in the temp directory
        logging.getLogger('bauble').setLevel(logging.ERROR)
        filenames = os.listdir(tempdir)
        importer = CSVImporter()
        importer.start([os.path.join(tempdir, name) for name in filenames],
                       force=True)
        importer.start([os.path.join(tempdir, name) for name in filenames],
                       force=True)


    def test_export(self):
        # 1. export the test data
        # 2. read the exported data into memory and make sure its matches
        # the test export string
        pass


class ImexTestSuite(unittest.TestSuite):

    def __init__(self):
        super(ImexTestSuite, self).__init__()
        self.addTests(map(ImexCSVTestCase, ('test_import', 'test_export')))


testsuite = ImexTestSuite


