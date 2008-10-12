# -*- coding: utf-8 -*-
#
# test imex plugins
#

import os, unittest
import logging
from sqlalchemy import *
from bauble.test import BaubleTestCase
import bauble
import bauble.plugins.plants.test as plants_test
import bauble.plugins.garden.test as garden_test
from bauble.plugins.imex.csv_ import CSVImporter, CSVExporter

# TODO: test that when we import data we get what we expect
# TODO: test that all Unicode works
# TODO: test that when we export data we get what we expect
# TODO: test that importing and then exporting gives the same data
# TODO: test that exporting and then importing gives the same data
# TODO: test XMLExporter

csv_test_data = ({})

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


class CSVTests(ImexTestCase):

    def test_import_defaults(self):
        # this test is usually not included in the test suite since it
        # takes so long
        import bauble
        import bauble.pluginmgr as pluginmgr
        #filenames = [p.default_filenames() for p in pluginmgr.plugins]
        filenames = []
        for p in pluginmgr.plugins.values():
            filenames.extend(p.default_filenames())
        importer = CSVImporter()
        def on_error(exc):
            raise exc
        # the bauble.DateTimeDecorator gives erros here when using a
        # postgres database
        importer.start(filenames=filenames, metadata=bauble.metadata,
                       force=True, on_error=on_error)

    def test_sequences(self):
        """
        test that the sequences are set correctly after an import,
        bauble.util.test already has a method to test
        utils.reset_sequence but this test makes sure that its works
        correctly after an import

        """
        # turn off logger
        logging.getLogger('bauble.info').setLevel(logging.ERROR)
        # import the family data
        from bauble.plugins.plants.family import Family
        from bauble.plugins.plants import PlantsPlugin
        family_table = Family.__table__
        filenames = PlantsPlugin.default_filenames()
        family_filename = [fn for fn in filenames \
                           if fn.endswith('family.txt')][0]
        importer = CSVImporter()
        importer.start([family_filename], force=True)

        # the highest id number in the family file is assumed to be
        # num(lines)-1 since the id numbers are sequential and
        # subtract for the file header
        highest_id =  len(open(family_filename).readlines())-1
        currval = None
        conn = bauble.engine.contextual_connect()
        if bauble.engine.name == 'postgres':
            stmt = "SELECT currval('family_id_seq');"
            currval = conn.execute(stmt).fetchone()[0]
        elif bauble.engine.name == 'sqlite':
            # max(id) isn't really safe in production use but is ok for a test
            stmt = "SELECT max(id) from family;"
            currval = conn.execute(stmt).fetchone()[0]
            currval += 1
        else:
            raise "no test for engine type: %s" % bauble.engine.name

        maxid = conn.execute("SELECT max(id) FROM family").fetchone()[0]
        assert currval > highest_id, \
               "bad sequence: highest_id(%s) != currval(%s) -- %s" % \
               (highest_id, currval, maxid)


    def test_import(self):
        # TODO: create a test to check that we aren't using an insert
        # statement for import that assumes a column value from the previous
        # insert values, could probably create an insert statement from a
        # row in the test data and then create an insert statement from some
        # other dummy data that has different columns from the test data and
        # see if any of the columns from the second insert statement has values
        # from the first statement

        # TODO: this test doesn't really test yet that any of the data was
        # correctly imported or exported, only that export and importing
        # run successfuly

        # 1. write the test data to a temporary file or files
        # 2. import the data and make sure the objects match field for field

        # the exporters and importers show logging information, turn it off
        import bauble.utils as utils
        logging.getLogger('bauble.info').setLevel(logging.ERROR)
        import tempfile
        tempdir = tempfile.mkdtemp()

        # export all the testdata
        exporter = CSVExporter()
        exporter.start(tempdir)

        # import all the files in the temp directory
        filenames = os.listdir(tempdir)
        importer = CSVImporter()
        # import twice to check for regression Launchpad #???
        importer.start([os.path.join(tempdir, name) for name in filenames],
                       force=True)
        importer.start([os.path.join(tempdir, name) for name in filenames],
                       force=True)
#        utils.log.echo(False)

    def test_unicode(self):
        from bauble.plugins.plants.geography import Geography
        geography_table = Geography.__table__
        # u'Gal\xe1pagos' is the unencoded unicode object,
        # calling u.encode('utf-8') will convert the \xe1 to the a
        # with an accent
        data = {'name': u'Gal\xe1pagos'}
        geography_table.insert().execute(data)
        query = self.session.query(Geography)
        row = query[0]
##        print str(row)
##        print data['name']
        assert row.name == data['name']


    def test_export(self):
        # 1. export the test data
        # 2. read the exported data into memory and make sure its matches
        # the test export string
        pass




