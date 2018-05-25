# -*- coding: utf-8 -*-
#
# Copyright 2004-2010 Brett Adams
# Copyright 2015 Mario Frasca <mario@anche.no>.
#
# This file is part of ghini.desktop.
#
# ghini.desktop is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ghini.desktop is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ghini.desktop. If not, see <http://www.gnu.org/licenses/>.



import csv
import logging
logger = logging.getLogger(__name__)

import os
import shutil
import tempfile

from sqlalchemy import Column, Integer, Boolean

import bauble.db as db
from bauble.plugins.plants import (
    Familia, Family, Genus, Species, VernacularName, SpeciesNote)
from bauble.plugins.garden import Accession, Location, Plant, Contact, Source
import bauble.plugins.garden.test as garden_test
import bauble.plugins.plants.test as plants_test
from bauble.plugins.imex.csv_ import CSVImporter, CSVExporter, QUOTE_CHAR, \
    QUOTE_STYLE
from bauble.plugins.imex.iojson import JSONImporter, JSONExporter
from bauble.test import BaubleTestCase
import json
from bauble.editor import MockView


family_data = [{'id': 1, 'family': 'Orchidaceae', 'qualifier': None},
               {'id': 2, 'family': 'Myrtaceae'}]
genus_data = [
    {'id': 1, 'genus': 'Calopogon', 'family_id': 1, 'author': 'R. Br.'},
    {'id': 2, 'genus': 'Panisea', 'family_id': 1}, ]
species_data = [
    {'id': 1, 'sp': 'tuberosus', 'genus_id': 1, 'sp_author': None},
    {'id': 2, 'sp': 'albiflora', 'genus_id': 2, 'sp_author': '(Ridl.) Seidenf.'},
    {'id': 3, 'sp': 'distelidia', 'genus_id': 2, 'sp_author': 'I.D.Lund'},
    {'id': 4, 'sp': 'zeylanica', 'genus_id': 2, 'sp_author': '(Hook.f.) Aver.'}, ]
species_note_test_data = [
    {'id': 1, 'species_id': 18, 'category': 'CITES', 'note': 'I'},
    {'id': 2, 'species_id': 20, 'category': 'IUCN', 'note': 'LC'},
    {'id': 3, 'species_id': 18, 'category': '<price>', 'note': '19.50'}, ]
accession_data = [
    {'id': 1, 'species_id': 1, 'code': '2015.0001'},
    {'id': 2, 'species_id': 1, 'code': '2015.0002'},
    {'id': 3, 'species_id': 1, 'code': '2015.0003', 'private': True}, ]
location_data = [
    {'id': 1, 'code': '1'}, ]
plant_data = [
    {'id': 1, 'accession_id': 1, 'location_id': 1, 'code': '1',
     'quantity': 1},
    {'id': 2, 'accession_id': 3, 'location_id': 1, 'code': '1',
     'quantity': 1}, ]


class ImexTestCase(BaubleTestCase):

    def __init__(self, *args):
        super().__init__(*args)

    def setUp(self):
        super().setUp()
        plants_test.setUp_data()
        garden_test.setUp_data()


class TestImporter(CSVImporter):

    def on_error(self, exc):
        logger.debug(exc)
        raise


class CSVTests(ImexTestCase):

    def setUp(self):
        self.path = tempfile.mkdtemp()
        super().setUp()

        data = (('family', family_data), ('genus', genus_data),
                ('species', species_data))
        for table_name, data in data:
            filename = os.path.join(self.path, '%s.txt' % table_name)
            f = open(filename, 'w')
            format = {'delimiter': ',', 'quoting': QUOTE_STYLE,
                      'quotechar': QUOTE_CHAR}

            fields = list(data[0].keys())
            f.write('%s\n' % ','.join(fields))
            writer = csv.DictWriter(f, fields, **format)
            writer.writerows(data)
            f.flush()
            f.close()
            importer = TestImporter()
            importer.start([filename], force=True)

    def tearDown(self):
        shutil.rmtree(self.path)
        super().tearDown()

    def test_import_self_referential_table(self):
        """
        Test tables that are self-referenial are import in order.
        """
        geo_data = [{'id': 3, 'name': '3', 'parent_id': 1},
                    {'id': 1, 'name': '1', 'parent_id': None},
                    {'id': 2, 'name': '2', 'parent_id': 1},
                    ]
        filename = os.path.join(self.path, 'geographic_area.txt')
        f = open(filename, 'w')
        format = {'delimiter': ',', 'quoting': QUOTE_STYLE,
                  'quotechar': QUOTE_CHAR}
        fields = list(geo_data[0].keys())
        f.write('%s\n' % ','.join(fields))
        f.flush()
        writer = csv.DictWriter(f, fields, **format)
        writer.writerows(geo_data)
        f.flush()
        f.close()
        importer = TestImporter()
        importer.start([filename], force=True)

    def test_import_bool_column(self):
        """
        """
        class BoolTest(db.Base):
            __tablename__ = 'bool_test'
            id = Column(Integer, primary_key=True)
            col1 = Column(Boolean, default=False)
        table = BoolTest.__table__
        table.create(bind=db.engine)
        data = [{'id': 1, 'col1': 'True'},
                {'id': 2, 'col1': 'False'},
                {'id': 3, 'col1': ''},
                ]
        filename = os.path.join(self.path, 'bool_test.txt')
        f = open(filename, 'w')
        format = {'delimiter': ',', 'quoting': QUOTE_STYLE,
                  'quotechar': QUOTE_CHAR}
        fields = list(data[0].keys())
        f.write('%s\n' % ','.join(fields))
        f.flush()
        writer = csv.DictWriter(f, fields, **format)
        writer.writerows(data)
        f.flush()
        f.close()
        importer = TestImporter()
        importer.start([filename], force=True)

        t = self.session.query(BoolTest).get(1)
        self.assertTrue(t.col1 is True)

        t = self.session.query(BoolTest).get(2)
        self.assertTrue(t.col1 is False)

        t = self.session.query(BoolTest).get(3)
        self.assertTrue(t.col1 is False)
        table.drop(bind=db.engine)

    def test_with_open_connection(self):
        """
        Test that the import doesn't stall if we have a connection
        open to Family while importing to the family table
        """
        list(self.session.query(Family))
        filename = os.path.join(self.path, 'family.txt')
        f = open(filename, 'w')
        format = {'delimiter': ',', 'quoting': QUOTE_STYLE,
                  'quotechar': QUOTE_CHAR}
        fields = list(family_data[0].keys())
        f.write('%s\n' % ','.join(fields))
        writer = csv.DictWriter(f, fields, **format)
        writer.writerows(family_data)
        f.flush()
        f.close()
        importer = TestImporter()
        importer.start([filename], force=True)
        list(self.session.query(Family))

    def test_import_use_defaultxxx(self):
        """
        Test that if we import from a csv file that doesn't include a
        column and that column has a default value then that default
        value is executed.
        """
        self.session = db.Session()
        family = self.session.query(Family).filter_by(id=1).one()
        self.assertTrue(family.qualifier == '')

    def test_import_use_default(self):
        """
        Test that if we import from a csv file that doesn't include a
        column and that column has a default value then that default
        value is executed.
        """
        q = self.session.query(Family)
        ids = [r.id for r in q]
        self.assertEqual(ids, [1, 2])
        del q
        self.session.expunge_all()
        self.session = db.Session()
        family = self.session.query(Family).filter_by(id=1).one()
        self.assertTrue(family.qualifier == '')

    def test_import_no_default(self):
        """
        Test that if we import from a csv file that doesn't include a
        column and that column does not have a default value then that
        value is set to None
        """
        species = self.session.query(Species).filter_by(id=1).one()
        self.assertTrue(species.cv_group is None)

    def test_import_empty_is_none(self):
        """
        Test that if we import from a csv file that includes a column
        but that column is empty and doesn't have a default values
        then the column is set to None
        """
        species = self.session.query(Species).filter_by(id=1).one()
        self.assertTrue(species.cv_group is None)

    def test_import_empty_uses_default(self):
        """
        Test that if we import from a csv file that includes a column
        but that column is empty and has a default then the default is
        executed.
        """
        family = self.session.query(Family).filter_by(id=2).one()
        self.assertTrue(family.qualifier == '')

    def test_sequences(self):
        """
        Test that the sequences are set correctly after an import,
        bauble.util.test already has a method to test
        utils.reset_sequence but this test makes sure that it works
        correctly after an import
        """
        # turn off logger
        logging.getLogger('bauble.info').setLevel(logging.ERROR)
        highest_id = len(family_data)
        conn = db.engine.connect()
        if db.engine.name == 'postgresql':
            stmt = "SELECT currval('family_id_seq');"
            nextval = conn.execute(stmt).fetchone()[0]
        elif db.engine.name == 'sqlite':
            # max(id) isn't really safe in production use but is ok for a test
            stmt = "SELECT max(id) from family;"
            nextval = conn.execute(stmt).fetchone()[0] + 1
        else:
            raise Exception("no test for engine type: %s" % db.engine.name)

        #debug(list(conn.execute("SELECT * FROM family").fetchall()))
        maxid = conn.execute("SELECT max(id) FROM family").fetchone()[0]
        assert nextval > highest_id, \
            "bad sequence: highest_id(%s) > nexval(%s) -- %s" % \
            (highest_id, nextval, maxid)

    def test_import_unicode(self):
        """
        Test importing a unicode string.
        """
        genus = self.session.query(Genus).filter_by(id=1).one()
        self.assertTrue(genus.author == genus_data[0]['author'])

    def test_import_no_inherit(self):
        """
        Test importing a row with None doesn't inherit from previous row.
        """
        query = self.session.query(Genus)
        self.assertTrue(query[1].author != query[0].author,
                     (query[1].author, query[0].author))

    def test_export_none_is_empty(self):
        """
        Test exporting a None column exports a ''
        """
        species = Species(genus_id=1, sp='sp')
        self.assertTrue(species is not None)
        from tempfile import mkdtemp
        temp_path = mkdtemp()
        exporter = CSVExporter()
        exporter.start(temp_path)
        f = open(os.path.join(temp_path, 'species.txt'))
        reader = csv.DictReader(f, dialect=csv.excel)
        row = next(reader)
        self.assertTrue(row['cv_group'] == '')


class CSVTests2(ImexTestCase):

    def test_sequences(self):
        """
        Test that the sequences are set correctly after an import,
        bauble.util.test already has a method to test
        utils.reset_sequence but this test makes sure that it works
        correctly after an import

        This test requires the PlantPlugin
        """
        # turn off logger
        logging.getLogger('bauble.info').setLevel(logging.ERROR)
        # import the family data
        filename = os.path.join('bauble', 'plugins', 'plants', 'default',
                                'family.txt')
        importer = CSVImporter()
        importer.start([filename], force=True)
        # the highest id number in the family file is assumed to be
        # num(lines)-1 since the id numbers are sequential and
        # subtract for the file header
        highest_id = len(open(filename).readlines())-1
        currval = None
        conn = db.engine.contextual_connect()
        if db.engine.name == 'postgres':
            stmt = "SELECT currval('family_id_seq');"
            currval = conn.execute(stmt).fetchone()[0]
            self.assertEqual(currval, 0)
        elif db.engine.name == 'sqlite':
            # max(id) isn't really safe in production use but is ok for a test
            stmt = "SELECT max(id) from family;"
            nextval = conn.execute(stmt).fetchone()[0] + 1
        else:
            raise "no test for engine type: %s" % db.engine.name

        #debug(list(conn.execute("SELECT * FROM family").fetchall()))
        maxid = conn.execute("SELECT max(id) FROM family").fetchone()[0]
        assert nextval > highest_id, \
            "bad sequence: highest_id(%s) > nexval(%s) -- %s" % \
            (highest_id, nextval, maxid)

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
        from bauble.plugins.plants.geography import GeographicArea
        geographic_area_table = GeographicArea.__table__
        # u'Gal\xe1pagos' is the unencoded unicode object,
        # calling u.encode('utf-8') will convert the \xe1 to the a
        # with an accent
        data = {'name': 'Gal\xe1pagos'}
        geographic_area_table.insert().execute(data)
        query = self.session.query(GeographicArea)
        row_name = [r.name for r in query.all()
                    if r.name.startswith("Gal")][0]
        self.assertEqual(row_name, data['name'])

    def test_export(self):
        # 1. export the test data
        # 2. read the exported data into memory and make sure it matches
        # the test export string
        pass


class MockExportView:
    def widget_set_value(self, *args):
        pass

    def widget_get_value(self, *args):
        pass

    def connect_signals(self, *args):
        pass

    def connect(self, *args):
        pass

    def set_selection(self, a):
        self.__selection = a

    def get_selection(self):
        return self.__selection


class JSONExportTests(BaubleTestCase):

    def setUp(self):
        super().setUp()
        from tempfile import mkstemp
        handle, self.temp_path = mkstemp()

        data = ((Family, family_data),
                (Genus, genus_data),
                (Species, species_data),
                (Accession, accession_data),
                (Location, location_data),
                (Plant, plant_data))

        self.objects = []
        for klass, dics in data:
            for dic in dics:
                obj = klass(**dic)
                self.session.add(obj)
                self.objects.append(obj)

        self.session.commit()

    def tearDown(self):
        super().tearDown()
        os.remove(self.temp_path)

    def test_writes_complete_database(self):
        "exporting without specifying what: export complete database"

        exporter = JSONExporter(MockView())
        exporter.view.selection = None
        exporter.selection_based_on == 'sbo_selection'
        exporter.include_private = False
        exporter.filename = self.temp_path
        exporter.run()
        ## must still check content of generated file!
        result = json.load(open(self.temp_path))
        self.assertEqual(len(result), 14)
        families = [i for i in result
                    if i['object'] == 'taxon' and i['rank'] == 'familia']
        self.assertEqual(len(families), 2)
        genera = [i for i in result
                  if i['object'] == 'taxon' and i['rank'] == 'genus']
        self.assertEqual(len(genera), 2)
        species = [i for i in result
                   if i['object'] == 'taxon' and i['rank'] == 'species']
        self.assertEqual(len(species), 4)
        target = [
            {"epithet": "Orchidaceae", "object": "taxon", "rank": "familia"},
            {"epithet": "Myrtaceae", "object": "taxon", "rank": "familia"},
            {"author": "R. Br.", "epithet": "Calopogon", "ht-epithet": "Orchidaceae", "ht-rank": "familia", "object": "taxon", "rank": "genus"},
            {"author": "", "epithet": "Panisea", "ht-epithet": "Orchidaceae", "ht-rank": "familia", "object": "taxon", "rank": "genus"},
            {'ht-epithet': 'Calopogon', 'hybrid': False, 'object': 'taxon', 'ht-rank': 'genus', 'rank': 'species', 'epithet': 'tuberosus'},
            {'ht-epithet': 'Panisea', 'hybrid': False, 'object': 'taxon', 'ht-rank': 'genus', 'rank': 'species', 'sp_author': '(L.) Britton', 'epithet': 'albiflora', 'sp_author': '(Ridl.) Seidenf.'},
            {'ht-epithet': 'Panisea', 'hybrid': False, 'object': 'taxon', 'ht-rank': 'genus', 'rank': 'species', 'sp_author': '(L.) Britton', 'epithet': 'distelidia', 'sp_author': 'I.D.Lund'},
            {'ht-epithet': 'Panisea', 'hybrid': False, 'object': 'taxon', 'ht-rank': 'genus', 'rank': 'species', 'sp_author': '(L.) Britton', 'epithet': 'zeylanica', 'sp_author': '(Hook.f.) Aver.'},
            {"code": "2015.0001", "object": "accession", "private": False, "species": "Calopogon tuberosus"},
            {"code": "2015.0002", "object": "accession", "private": False, "species": "Calopogon tuberosus"},
            {"code": "2015.0003", "object": "accession", "private": True, "species": "Calopogon tuberosus"},
            {"code": "1", "object": "location"},
            {"accession": "2015.0001", "code": "1", "location": "1", "memorial": False, "object": "plant", "quantity": 1},
            {"accession": "2015.0003", "code": "1", "location": "1", "memorial": False, "object": "plant", "quantity": 1}]
        for o1 in result:
            self.assertTrue(o1 in target, o1)
        for o2 in target:
            self.assertTrue(o1 in result, o2)

    def test_when_selection_huge_ask(self):
        view = MockView()
        exporter = JSONExporter(view)
        exporter.selection_based_on == 'sbo_selection'
        view.selection = list(range(5000))
        view.reply_yes_no_dialog = [False]
        exporter.run()
        self.assertTrue('run_yes_no_dialog' in view.invoked)
        self.assertEqual(view.reply_yes_no_dialog, [])

    def test_writes_full_taxonomic_info(self):
        "exporting one family: export full taxonomic information below family"

        selection = self.session.query(Family).filter(
            Family.family == 'Orchidaceae').all()
        exporter = JSONExporter(MockView())
        exporter.selection_based_on == 'sbo_selection'
        exporter.include_private = False
        exporter.view.selection = selection
        exporter.filename = self.temp_path
        exporter.run()
        result = json.load(open(self.temp_path))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['rank'], 'familia')
        self.assertEqual(result[0]['epithet'], 'Orchidaceae')

    def test_writes_partial_taxonomic_info(self):
        "exporting one genus: all species below genus"

        selection = self.session.query(Genus).filter(
            Genus.genus == 'Calopogon').all()
        exporter = JSONExporter(MockView())
        exporter.view.selection = selection
        exporter.selection_based_on == 'sbo_selection'
        exporter.include_private = False
        exporter.filename = self.temp_path
        exporter.run()
        result = json.load(open(self.temp_path))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['rank'], 'genus')
        self.assertEqual(result[0]['epithet'], 'Calopogon')
        self.assertEqual(result[0]['ht-rank'], 'familia')
        self.assertEqual(result[0]['ht-epithet'], 'Orchidaceae')
        self.assertEqual(result[0]['author'], 'R. Br.')

    def test_writes_partial_taxonomic_info_species(self):
        "exporting one species: all species below species"

        selection = self.session.query(
            Species).filter(Species.sp == 'tuberosus').join(
            Genus).filter(Genus.genus == "Calopogon").all()
        exporter = JSONExporter(MockView())
        exporter.view.selection = selection
        exporter.selection_based_on == 'sbo_selection'
        exporter.include_private = False
        exporter.filename = self.temp_path
        exporter.run()
        result = json.load(open(self.temp_path))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['rank'], 'species')
        self.assertEqual(result[0]['epithet'], 'tuberosus')
        self.assertEqual(result[0]['ht-rank'], 'genus')
        self.assertEqual(result[0]['ht-epithet'], 'Calopogon')
        self.assertEqual(result[0]['hybrid'], False)

    def test_export_single_species_with_notes(self):
        selection = self.session.query(
            Species).filter(Species.sp == 'tuberosus').join(
            Genus).filter(Genus.genus == "Calopogon").all()
        note = SpeciesNote(category='<coords>', note='{1: 1, 2: 2}')
        note.species = selection[0]
        self.session.add(note)
        self.session.commit()
        exporter = JSONExporter(MockView())
        exporter.view.selection = selection
        exporter.selection_based_on == 'sbo_selection'
        exporter.include_private = False
        exporter.filename = self.temp_path
        exporter.run()
        result = json.load(open(self.temp_path))
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], {'ht-epithet': 'Calopogon', 'hybrid': False, 'object': 'taxon', 'ht-rank': 'genus', 'rank': 'species', 'epithet': 'tuberosus'})
        date_dict = result[1]['date']
        del result[1]['date']
        self.assertEqual(result[1], {'category': '<coords>', 'note': '{1: 1, 2: 2}', 'species': 'Calopogon tuberosus', 'object': 'species_note'})
        self.assertEqual(set(date_dict.keys()), set(['millis', '__class__']))

    def test_export_single_species_with_vernacular_name(self):
        selection = self.session.query(
            Species).filter(Species.sp == 'tuberosus').join(
            Genus).filter(Genus.genus == "Calopogon").all()
        vn = VernacularName(language="it", name='orchidea')
        selection[0].vernacular_names.append(vn)
        self.session.add(vn)
        self.session.commit()
        exporter = JSONExporter(MockView())
        exporter.view.selection = selection
        exporter.selection_based_on == 'sbo_selection'
        exporter.include_private = False
        exporter.filename = self.temp_path
        exporter.run()
        result = json.load(open(self.temp_path))
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], {'ht-epithet': 'Calopogon', 'hybrid': False, 'object': 'taxon', 'ht-rank': 'genus', 'rank': 'species', 'epithet': 'tuberosus'})
        self.assertEqual(result[1], {'language': 'it', 'name': 'orchidea', 'object': 'vernacular_name', 'species': 'Calopogon tuberosus'})

    def test_partial_taxonomic_with_synonymy(self):
        "exporting one genus which is not an accepted name."

        f = self.session.query(
            Family).filter(
            Family.family == 'Orchidaceae').one()
        bu = Genus(family=f, genus='Bulbophyllum')  # accepted
        zy = Genus(family=f, genus='Zygoglossum')  # synonym
        bu.synonyms.append(zy)
        self.session.add_all([f, bu, zy])
        self.session.commit()

        selection = self.session.query(Genus).filter(
            Genus.genus == 'Zygoglossum').all()
        exporter = JSONExporter(MockView())
        exporter.view.selection = selection
        exporter.selection_based_on == 'sbo_selection'
        exporter.include_private = True
        exporter.filename = self.temp_path
        exporter.run()
        result = json.load(open(self.temp_path))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['rank'], 'genus')
        self.assertEqual(result[0]['epithet'], 'Zygoglossum')
        self.assertEqual(result[0]['ht-rank'], 'familia')
        self.assertEqual(result[0]['ht-epithet'], 'Orchidaceae')
        accepted = result[0].get('accepted')
        self.assertTrue(isinstance(accepted, dict))
        self.assertEqual(accepted['rank'], 'genus')
        self.assertEqual(accepted['epithet'], 'Bulbophyllum')
        self.assertEqual(accepted['ht-rank'], 'familia')
        self.assertEqual(accepted['ht-epithet'], 'Orchidaceae')

    def test_export_ignores_private_if_sbo_selection(self):
        exporter = JSONExporter(MockView())
        selection = [o for o in self.objects if isinstance(o, Accession)]
        non_private = [a for a in selection if a.private is False]
        self.assertEqual(len(selection), 3)
        self.assertEqual(len(non_private), 2)
        exporter.view.selection = selection
        exporter.selection_based_on == 'sbo_selection'
        exporter.include_private = False
        exporter.filename = self.temp_path
        exporter.run()
        result = json.load(open(self.temp_path))
        self.assertEqual(len(result), 3)

    def test_export_non_private_if_sbo_accessions(self):
        exporter = JSONExporter(MockView())
        exporter.view.selection = None
        exporter.selection_based_on = 'sbo_accessions'
        exporter.include_private = False
        exporter.filename = self.temp_path
        exporter.run()
        result = json.load(open(self.temp_path))
        self.assertEqual(len(result), 5)

    def test_export_private_if_sbo_accessions(self):
        exporter = JSONExporter(MockView())
        exporter.view.selection = None
        exporter.selection_based_on = 'sbo_accessions'
        exporter.include_private = True
        exporter.filename = self.temp_path
        exporter.run()
        result = json.load(open(self.temp_path))
        self.assertEqual(len(result), 6)

    def test_export_non_private_if_sbo_plants(self):
        exporter = JSONExporter(MockView())
        exporter.view.selection = None
        exporter.selection_based_on = 'sbo_plants'
        exporter.include_private = False
        exporter.filename = self.temp_path
        exporter.run()
        result = json.load(open(self.temp_path))
        self.assertEqual(len(result), 6)

    def test_export_private_if_sbo_plants(self):
        exporter = JSONExporter(MockView())
        exporter.view.selection = None
        exporter.selection_based_on = 'sbo_plants'
        exporter.include_private = True
        exporter.filename = self.temp_path
        exporter.run()
        result = json.load(open(self.temp_path))
        self.assertEqual(len(result), 8)

    def test_export_with_vernacular(self):
        "exporting one genus which is not an accepted name."

        ## precondition
        sola = Family(family='Solanaceae')
        brug = Genus(family=sola, genus='Brugmansia')
        arbo = Species(genus=brug, sp='arborea')
        vern = VernacularName(species=arbo,
                              language="es", name="Floripondio")
        self.session.add_all([sola, brug, arbo, vern])
        self.session.commit()

        ## action
        exporter = JSONExporter(MockView())
        exporter.view.selection = None
        exporter.selection_based_on = 'sbo_taxa'
        exporter.include_private = False
        exporter.filename = self.temp_path
        exporter.run()

        ## check
        result = json.load(open(self.temp_path))
        vern_from_json = [i for i in result
                          if i['object'] == 'vernacular_name']
        self.assertEqual(len(vern_from_json), 1)
        self.assertEqual(vern_from_json[0]['language'], 'es')

    def test_on_btnbrowse_clicked(self):
        view = MockView()
        exporter = JSONExporter(view)
        view.reply_file_chooser_dialog = ['/tmp/test.json']
        exporter.on_btnbrowse_clicked('button')
        exporter.on_text_entry_changed('filename')
        self.assertEqual(exporter.filename, '/tmp/test.json')
        self.assertEqual(JSONExporter.last_folder, '/tmp')

    def test_includes_sources(self):

        ## precondition
        # Create an Accession a, then create a Source s, then assign a.source = s
        a = self.session.query(Accession).first()
        a.source = s = Source()
        s.source_detail = c = Contact(name='Summit')
        self.session.add_all([s, c])
        self.session.commit()

        ## action
        exporter = JSONExporter(MockView())
        selection = [a]
        exporter.view.selection = None
        exporter.selection_based_on = 'sbo_accessions'
        exporter.include_private = True
        exporter.filename = self.temp_path
        exporter.run()

        ## check
        result = json.load(open(self.temp_path))
        print(result)
        contacts_from_json = [i for i in result
                              if i['object'] == 'contact']
        self.assertEqual(len(contacts_from_json), 1)
        self.assertEqual(contacts_from_json[0]['name'], 'Summit')
        accessions_from_json = [i for i in result
                                if i['object'] == 'accession']
        self.assertEqual(len(accessions_from_json), 3)
        accessions_with_contact = [i for i in result
                                   if i['object'] == 'accession' and i.get('contact') is not None]
        self.assertEqual(len(accessions_with_contact), 1)
        self.assertEqual(accessions_with_contact[0]['contact'], 'Summit')


class JSONImportTests(BaubleTestCase):

    def setUp(self):
        super().setUp()
        from tempfile import mkstemp
        handle, self.temp_path = mkstemp()

        data = ((Familia, family_data),
                (Genus, genus_data),
                (Species, species_data))

        for klass, dics in data:
            for dic in dics:
                obj = klass(**dic)
                self.session.add(obj)
        self.session.commit()

    def tearDown(self):
        super().tearDown()
        os.remove(self.temp_path)

    def test_import_new_inserts(self):
        "importing new taxon adds it to database."
        json_string = '[{"rank": "Genus", "epithet": "Neogyna", '\
            '"ht-rank": "Familia", "ht-epithet": "Orchidaceae", '\
            '"author": "Rchb. f."}]'
        with open(self.temp_path, "w") as f:
            f.write(json_string)
        self.assertEqual(len(self.session.query(Genus).filter(
            Genus.genus == "Neogyna").all()), 0)
        importer = JSONImporter(MockView())
        importer.filename = self.temp_path
        importer.on_btnok_clicked(None)
        self.assertEqual(len(self.session.query(Genus).filter(
            Genus.genus == "Neogyna").all()), 1)

    def test_import_new_inserts_lowercase(self):
        "importing new taxon adds it to database, rank name can be\
        all lower case."
        json_string = '[{"rank": "genus", "epithet": "Neogyna", "ht-rank"'\
            ': "familia", "ht-epithet": "Orchidaceae", "author": "Rchb. f."}]'
        with open(self.temp_path, "w") as f:
            f.write(json_string)
        self.assertEqual(len(self.session.query(Genus).filter(
            Genus.genus == "Neogyna").all()), 0)
        importer = JSONImporter(MockView())
        importer.filename = self.temp_path
        importer.on_btnok_clicked(None)
        self.assertEqual(len(self.session.query(Genus).filter(
            Genus.genus == "Neogyna").all()), 1)

    def test_import_new_with_non_timestamped_note(self):
        json_string = (
            '[{"ht-epithet": "Calopogon", "epithet": "pallidus", "author": "Chapm.", '\
            ' "rank": "Species", "ht-rank": "Genus", "hybrid": false}, '\
            ' {"object": "species_note", "species": "Calopogon pallidus", "category": "<coords>", "note": "{lat: 8.5, lon: -80}"}]')
        with open(self.temp_path, "w") as f:
            f.write(json_string)
        importer = JSONImporter(MockView())
        importer.filename = self.temp_path
        importer.on_btnok_clicked(None)
        self.session.commit()
        afterwards = Species.retrieve_or_create(
            self.session, {'ht-epithet': "Calopogon",
                           'epithet': "pallidus"})
        self.assertEqual(afterwards.sp_author, 'Chapm.')
        self.assertEqual(len(afterwards.notes), 1)

    def test_import_new_with_three_array_notes(self):
        json_string = (
            '[{"ht-epithet": "Calopogon", "epithet": "pallidus", "author": "Chapm.", '\
            ' "rank": "Species", "ht-rank": "Genus", "hybrid": false}, '\
            ' {"object": "species_note", "species": "Calopogon pallidus", "category": "[x]", "note": "1"}, '\
            ' {"object": "species_note", "species": "Calopogon pallidus", "category": "[x]", "note": "1"}, '\
            ' {"object": "species_note", "species": "Calopogon pallidus", "category": "[x]", "note": "1"}]')
        with open(self.temp_path, "w") as f:
            f.write(json_string)
        importer = JSONImporter(MockView())
        importer.filename = self.temp_path
        importer.on_btnok_clicked(None)
        self.session.commit()
        afterwards = Species.retrieve_or_create(
            self.session, {'ht-epithet': "Calopogon",
                           'epithet': "pallidus"})
        self.assertEqual(afterwards.sp_author, 'Chapm.')
        self.assertEqual(len(afterwards.notes), 3)

    def test_import_new_same_picture_notes(self):
        before = Species.retrieve_or_create(
            self.session, {'ht-epithet': "Calopogon",
                           'epithet': "pallidus"})
        note = SpeciesNote(category='<picture>', note='a')
        self.session.commit()
        
        json_string = (
            '[{"ht-epithet": "Calopogon", "epithet": "pallidus", "author": "Chapm.", '\
            ' "rank": "Species", "ht-rank": "Genus", "hybrid": false}, '\
            ' {"object": "species_note", "species": "Calopogon pallidus", "category": "<picture>", "note": "a"}, '\
            ' {"object": "species_note", "species": "Calopogon pallidus", "category": "<picture>", "note": "b"}]')
        with open(self.temp_path, "w") as f:
            f.write(json_string)
        importer = JSONImporter(MockView())
        importer.filename = self.temp_path
        importer.on_btnok_clicked(None)
        self.session.commit()
        afterwards = Species.retrieve_or_create(
            self.session, {'ht-epithet': "Calopogon",
                           'epithet': "pallidus"})
        self.assertEqual(afterwards.sp_author, 'Chapm.')
        self.assertEqual(len(afterwards.notes), 2)

    def test_import_new_with_repeated_note(self):
        json_string = (
            '[{"ht-epithet": "Calopogon", "epithet": "pallidus", "author": "Chapm.", '\
            ' "rank": "Species", "ht-rank": "Genus", "hybrid": false}, '\
            ' {"object": "species_note", "species": "Calopogon pallidus", "category": "<price>", "note": "8"}, '\
            ' {"object": "species_note", "species": "Calopogon pallidus", "category": "<price>", "note": "10"}]')
        with open(self.temp_path, "w") as f:
            f.write(json_string)
        importer = JSONImporter(MockView())
        importer.filename = self.temp_path
        importer.on_btnok_clicked(None)
        self.session.commit()
        afterwards = Species.retrieve_or_create(
            self.session, {'ht-epithet': "Calopogon",
                           'epithet': "pallidus"})
        self.assertEqual(afterwards.sp_author, 'Chapm.')
        self.assertEqual(len(afterwards.notes), 1)
        self.assertEqual(afterwards.notes[0].note, '10')

    def test_import_new_with_timestamped_note(self):
        json_string = (
            '[{"ht-epithet": "Calopogon", "epithet": "pallidus", "author": "Chapm.", '\
            ' "rank": "Species", "ht-rank": "Genus", "hybrid": false}, '\
            ' {"object": "species_note", "species": "Calopogon pallidus", "category": "<coords>", "note": "{lat: 8.5, lon: -80}", "date": {"__class__": "datetime", "millis": 1234567890}}]')
        with open(self.temp_path, "w") as f:
            f.write(json_string)
        importer = JSONImporter(MockView())
        importer.filename = self.temp_path
        importer.on_btnok_clicked(None)
        self.session.commit()
        afterwards = Species.retrieve_or_create(
            self.session, {'ht-epithet': "Calopogon",
                           'epithet': "pallidus"})
        self.assertEqual(afterwards.sp_author, 'Chapm.')
        self.assertEqual(len(afterwards.notes), 1)
        import datetime
        self.assertEqual(afterwards.notes[0].date, datetime.date(2009, 2, 24))

    def test_import_existing_updates(self):
        "importing existing taxon updates it"
        json_string = '[{"rank": "Species", "epithet": "tuberosus", "ht-rank"'\
            ': "Genus", "ht-epithet": "Calopogon", "hybrid": false, "author"'\
            ': "Britton et al."}]'
        with open(self.temp_path, "w") as f:
            f.write(json_string)
        previously = Species.retrieve_or_create(
            self.session, {'ht-epithet': "Calopogon",
                           'epithet': "tuberosus"})
        self.assertEqual(previously.sp_author, None)
        importer = JSONImporter(MockView())
        importer.filename = self.temp_path
        importer.on_btnok_clicked(None)
        self.session.commit()
        afterwards = Species.retrieve_or_create(
            self.session, {'ht-epithet': "Calopogon",
                           'epithet': "tuberosus"})
        self.assertEqual(afterwards.sp_author, "Britton et al.")

    def test_import_ignores_id_new(self):
        "importing taxon disregards id value if present (new taxon)."
        previously = Genus.retrieve_or_create(
            self.session, {'epithet': "Neogyna"})
        self.assertEqual(previously, None)
        json_string = '[{"rank": "Genus", "epithet": "Neogyna", '\
            '"ht-rank": "Familia", "ht-epithet": "Orchidaceae", '\
            '"author": "Rchb. f.", "id": 1}]'
        with open(self.temp_path, "w") as f:
            f.write(json_string)
        importer = JSONImporter(MockView())
        importer.filename = self.temp_path
        importer.on_btnok_clicked(None)

        self.session.commit()
        real_id = Genus.retrieve_or_create(self.session,
                                           {'epithet': "Neogyna"}).id
        self.assertTrue(real_id != 1)

    def test_import_ignores_id_updating(self):
        "importing taxon disregards id value if present (updating taxon)."
        previously = Species.retrieve_or_create(self.session,
                                                {'ht-epithet': "Calopogon",
                                                 'epithet': "tuberosus"}).id
        json_string = '[{"rank": "Species", "epithet": "tuberosus", '\
            '"ht-rank": "Genus", "ht-epithet": "Calopogon", "hybrid": false, '\
            '"id": 8}]'
        with open(self.temp_path, "w") as f:
            f.write(json_string)
        importer = JSONImporter(MockView())
        importer.filename = self.temp_path
        importer.on_btnok_clicked(None)

        self.session.commit()
        afterwards = Species.retrieve_or_create(self.session,
                                                {'ht-epithet': "Calopogon",
                                                 'epithet': "tuberosus"}).id
        self.assertEqual(previously, afterwards)

    def test_import_species_to_new_genus_fails(self):
        "importing new species referring to non existing genus logs a warning."
        json_string = '[{"rank": "Species", "epithet": "lawrenceae", '\
            '"ht-rank": "Genus", "ht-epithet": "Aerides", "author": '\
            '"Rchb. f."}]'
        with open(self.temp_path, "w") as f:
            f.write(json_string)
        importer = JSONImporter(MockView())
        importer.filename = self.temp_path
        importer.on_btnok_clicked(None)

        ## should check the logs
        ## check the species is still not there
        sp = self.session.query(Species).filter(
            Species.sp == 'lawrenceae').join(Genus).filter(
            Genus.genus == 'Aerides').all()
        self.assertEqual(sp, [])

    def test_import_species_to_new_genus_and_family(self):
        "species referring to non existing genus (family is specified)"

        ## precondition: the species is not there
        sp = self.session.query(Species).filter(
            Species.sp == 'lawrenceae').join(Genus).filter(
            Genus.genus == 'Aerides').all()
        self.assertEqual(sp, [])

        json_string = '[{"rank": "Species", "epithet": "lawrenceae", '\
            '"ht-rank": "Genus", "ht-epithet": "Aerides", '\
            '"familia": "Orchidaceae", "author" : "Rchb. f."}]'
        with open(self.temp_path, "w") as f:
            f.write(json_string)
        importer = JSONImporter(MockView())
        importer.filename = self.temp_path
        importer.on_btnok_clicked(None)

        self.session.commit()
        ## postcondition: the species is there
        sp = self.session.query(Species).filter(
            Species.sp == 'lawrenceae').join(Genus).filter(
            Genus.genus == 'Aerides').all()
        self.assertEqual(len(sp), 1)
        sp = sp[0]
        genus = self.session.query(Genus).filter(
            Genus.genus == 'Aerides').first()
        family = self.session.query(Family).filter(
            Family.family == 'Orchidaceae').first()
        self.assertEqual(sp.genus, genus)
        self.assertEqual(genus.family, family)

    def test_import_with_synonym(self):
        "importing taxon with `accepted` field imports both taxa"
        json_string = '[{"rank": "Genus", "epithet": "Zygoglossum", '\
            '"ht-rank": "Familia", "ht-epithet": "Orchidaceae", '\
            '"author": "Reinw.", "accepted": {"rank": "Genus", '\
            '"epithet": "Bulbophyllum", "ht-rank": "Familia", '\
            '"ht-epithet": "Orchidaceae", "author": "Thouars"}}]'
        with open(self.temp_path, "w") as f:
            f.write(json_string)
        importer = JSONImporter(MockView())
        importer.filename = self.temp_path
        importer.on_btnok_clicked(None)

        self.session.commit()
        synonym = Genus.retrieve_or_create(
            self.session, {'epithet': "Zygoglossum"})
        self.assertEqual(synonym.accepted.__class__, Genus)
        accepted = Genus.retrieve_or_create(
            self.session, {'epithet': "Bulbophyllum"})
        self.assertEqual(synonym.accepted, accepted)

    def test_use_author_to_break_ties(self):
        "importing homonym taxon is possible if authorship breaks ties"
        # Anacampseros was used twice, by Linnaeus, and by Miller
        ataceae = Family(family='Anacampserotaceae')  # Eggli & Nyffeler
        linnaeus = Genus(family=ataceae, genus='Anacampseros', author='L.')
        claceae = Family(family='Crassulaceae')  # J. St.-Hil.
        miller = Genus(family=claceae, genus='Anacampseros', author='Mill.')
        self.session.add_all([claceae, ataceae, linnaeus, miller])
        self.session.commit()

        ## T_0
        accepted = Genus.retrieve_or_create(
            self.session, {'epithet': "Sedum"}, create=False)
        self.assertEqual(accepted, None)
        self.assertEqual(miller.accepted, None)

        ## what if we update Anacampseros Mill., with `accepted` information?
        json_string = ' {"author": "Mill.", "epithet": "Anacampseros", '\
            '"ht-epithet": "Crassulaceae", "ht-rank": "familia", '\
            '"object": "taxon", "rank": "genus", "accepted": {'\
            '"author": "L.", "epithet": "Sedum", "ht-epithet": '\
            '"Crassulaceae", "ht-rank": "familia", "object": "taxon", '\
            '"rank": "genus"}}'
        with open(self.temp_path, "w") as f:
            f.write(json_string)
        importer = JSONImporter(MockView())
        importer.filename = self.temp_path
        importer.on_btnok_clicked(None)
        self.session.commit()

        ## T_1
        accepted = Genus.retrieve_or_create(
            self.session, {'epithet': "Sedum"}, create=False)
        self.assertEqual(accepted.__class__, Genus)
        self.assertEqual(miller.accepted, accepted)

    def test_import_create_update(self):
        'existing gets updated, not existing is created'

        ## T_0
        ataceae = Family(family='Anacampserotaceae')  # Eggli & Nyffeler
        linnaeus = Genus(family=ataceae, genus='Anacampseros')  # L.
        self.session.add_all([ataceae, linnaeus])
        self.session.commit()

        ## offer two objects for import
        importer = JSONImporter(MockView())
        json_string = '[{"author": "L.", "epithet": "Anacampseros", '\
            '"ht-epithet": "Anacampserotaceae", "ht-rank": "familia", '\
            '"object": "taxon", "rank": "genus"}, {"author": "L.", '\
            '"epithet": "Sedum", "ht-epithet": "Crassulaceae", '\
            '"ht-rank": "familia", "object": "taxon", '\
            '"rank": "genus"}]'
        with open(self.temp_path, "w") as f:
            f.write(json_string)
        importer.filename = self.temp_path
        importer.create = True
        importer.update = True
        importer.on_btnok_clicked(None)
        self.session.commit()

        ## T_1
        sedum = Genus.retrieve_or_create(
            self.session, {'epithet': "Sedum"}, create=False)
        self.assertEqual(sedum.__class__, Genus)
        self.assertEqual(sedum.author, 'L.')
        anacampseros = Genus.retrieve_or_create(
            self.session, {'epithet': "Anacampseros"}, create=False)
        self.assertEqual(anacampseros.__class__, Genus)
        self.assertEqual(anacampseros.author, 'L.')

    def test_import_no_create_update(self):
        'existing gets updated, not existing is not created'

        ## T_0
        ataceae = Family(family='Anacampserotaceae')  # Eggli & Nyffeler
        linnaeus = Genus(family=ataceae, genus='Anacampseros')  # L.
        self.session.add_all([ataceae, linnaeus])
        self.session.commit()

        ## offer two objects for import
        importer = JSONImporter(MockView())
        json_string = '[{"author": "L.", "epithet": "Anacampseros", '\
            '"ht-epithet": "Anacampserotaceae", "ht-rank": "familia", '\
            '"object": "taxon", "rank": "genus"}, {"author": "L.", '\
            '"epithet": "Sedum", "ht-epithet": "Crassulaceae", '\
            '"ht-rank": "familia", "object": "taxon", '\
            '"rank": "genus"}]'
        with open(self.temp_path, "w") as f:
            f.write(json_string)
        importer.filename = self.temp_path
        importer.create = False
        importer.update = True
        importer.on_btnok_clicked(None)
        self.session.commit()

        ## T_1
        sedum = Genus.retrieve_or_create(
            self.session, {'epithet': "Sedum"}, create=False)
        self.assertEqual(sedum, None)
        anacampseros = Genus.retrieve_or_create(
            self.session, {'epithet': "Anacampseros"}, create=False)
        self.assertEqual(anacampseros.__class__, Genus)
        self.assertEqual(anacampseros.author, 'L.')

    def test_import_create_no_update(self):
        'existing remains untouched, not existing is created'

        ## T_0
        ataceae = Family(family='Anacampserotaceae')  # Eggli & Nyffeler
        linnaeus = Genus(family=ataceae, genus='Anacampseros')  # L.
        self.session.add_all([ataceae, linnaeus])
        self.session.commit()

        ## offer two objects for import
        importer = JSONImporter(MockView())
        json_string = '[{"author": "L.", "epithet": "Anacampseros", '\
            '"ht-epithet": "Anacampserotaceae", "ht-rank": "familia", '\
            '"object": "taxon", "rank": "genus"}, {"author": "L.", '\
            '"epithet": "Sedum", "ht-epithet": "Crassulaceae", '\
            '"ht-rank": "familia", "object": "taxon", '\
            '"rank": "genus"}]'
        with open(self.temp_path, "w") as f:
            f.write(json_string)
        importer.filename = self.temp_path
        importer.create = True
        importer.update = False
        importer.on_btnok_clicked(None)
        self.session.commit()

        ## T_1
        sedum = Genus.retrieve_or_create(
            self.session, {'epithet': "Sedum"}, create=False)
        self.assertEqual(sedum.__class__, Genus)
        self.assertEqual(sedum.author, 'L.')
        anacampseros = Genus.retrieve_or_create(
            self.session, {'epithet': "Anacampseros"}, create=False)
        self.assertEqual(anacampseros.__class__, Genus)
        self.assertEqual(anacampseros.author, '')

    def test_on_btnbrowse_clicked(self):
        view = MockView()
        exporter = JSONImporter(view)
        view.reply_file_chooser_dialog = ['/tmp/test.json']
        exporter.on_btnbrowse_clicked('button')
        exporter.on_text_entry_changed('input_filename')
        self.assertEqual(exporter.filename, '/tmp/test.json')
        self.assertEqual(JSONImporter.last_folder, '/tmp')

    def test_import_contact(self):
        ## T_0
        # empty database

        ## offer two objects for import
        importer = JSONImporter(MockView())
        json_string = '[{"name": "Summit", "object": "contact"}]'
        with open(self.temp_path, "w") as f:
            f.write(json_string)
        importer.filename = self.temp_path
        importer.create = True
        importer.update = True
        importer.on_btnok_clicked(None)
        self.session.commit()

        ## T_1
        summit = self.session.query(Contact).first()
        self.assertNotEqual(summit, None)


class GlobalFunctionsTests(BaubleTestCase):
    'Presenter manages view and model, implements view callbacks.'
    def test_json_serializer_datetime(self):
        import datetime
        from .iojson import serializedatetime
        stamp = datetime.datetime(2011, 11, 11, 12, 13)
        self.assertEqual(serializedatetime(stamp),
                          {'millis': 1321013580000, '__class__': 'datetime'})
