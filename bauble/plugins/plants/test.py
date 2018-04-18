# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Brett Adams
# Copyright 2015 Mario Frasca <mario@anche.no>.
# Copyright 2017 Jardín Botánico de Quito
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
#
# Description: test for the Plant plugin
#

import os
import sys
from unittest import TestCase

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import IntegrityError
from nose import SkipTest

import bauble.utils as utils
import bauble.db as db
from bauble.plugins.plants.species import (
    Species, VernacularName, SpeciesSynonym, edit_species,
    DefaultVernacularName, SpeciesDistribution, SpeciesNote)
from bauble.plugins.plants.family import (
    Family, FamilySynonym, FamilyEditor, FamilyNote)
from bauble.plugins.plants.genus import \
    Genus, GenusSynonym, GenusEditor, GenusNote
from bauble.plugins.plants.geography import Geography, get_species_in_geography
from bauble.test import BaubleTestCase, check_dupids, mockfunc

from functools import partial

import logging
logging.basicConfig()
#logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

#
# TODO: things to create tests for
#
# - test schema cascading works for all tables in the plants module
# - test unicode is working properly in the relevant fields, especially
# in the Species.str function
# - test the setting the default vernacular name on a species is working
# and that delete vernacular names and default vernacular names does
# proper  cascading
# make sure that deleting either of the species referred to in a synonym
# deletes the synonym

# TODO: create some scenarios that should fail


from bauble.plugins.plants.species_model import _remove_zws as remove_zws


family_test_data = (
    {'id': 1, 'family': u'Orchidaceae'},
    {'id': 2, 'family': u'Leguminosae', 'qualifier': u's. str.'},
    {'id': 3, 'family': u'Polypodiaceae'},
    {'id': 4, 'family': u'Solanaceae'},
    )

family_note_test_data = (
    {'id': 1, 'family_id': 1, 'category': u'CITES', 'note': u'II'},
    )

genus_test_data = (
    {'id': 1, 'genus': u'Maxillaria', 'family_id': 1},
    {'id': 2, 'genus': u'Encyclia', 'family_id': 1},
    {'id': 3, 'genus': u'Abrus', 'family_id': 2},
    {'id': 4, 'genus': u'Campyloneurum', 'family_id': 3},
    {'id': 5, 'genus': u'Paphiopedilum', 'family_id': 1},
    {'id': 6, 'genus': u'Laelia', 'family_id': 1},
    {'id': 7, 'genus': u'Brugmansia', 'family_id': 4},
    )

genus_note_test_data = (
    {'id': 1, 'genus_id': 5, 'category': u'CITES', 'note': u'I'},
    )

species_test_data = (
    {'id': 1, 'sp': u'variabilis', 'genus_id': 1,
     'sp_author': u'Bateman ex Lindl.'},
    {'id': 2, 'sp': u'cochleata', 'genus_id': 2,
     'sp_author': u'(L.) Lem\xe9e'},
    {'id': 3, 'sp': u'precatorius', 'genus_id': 3,
     'sp_author': u'L.'},
    {'id': 4, 'sp': u'alapense', 'genus_id': 4,
     'hybrid': True, 'sp_author': u'F\xe9e'},
    {'id': 5, 'sp': u'cochleata', 'genus_id': 2,
     'sp_author': u'(L.) Lem\xe9e',
     'infrasp1_rank': u'var.', 'infrasp1': u'cochleata'},
    {'id': 6, 'sp': u'cochleata', 'genus_id': 2,
     'sp_author': u'(L.) Lem\xe9e',
     'infrasp1_rank': u'cv.', 'infrasp1': u'Black Night'},
    {'id': 7, 'sp': u'precatorius', 'genus_id': 3,
     'sp_author': u'L.', 'cv_group': u'SomethingRidiculous'},
    {'id': 8, 'sp': u'precatorius', 'genus_id': 3,
     'sp_author': u'L.',
     'infrasp1_rank': u'cv.', 'infrasp1': u'Hot Rio Nights',
     'cv_group': u'SomethingRidiculous'},
    {'id': 9, 'sp': u'generalis', 'genus_id': 1,
     'hybrid': True,
     'infrasp1_rank': u'cv.', 'infrasp1': u'Red'},
    {'id': 10, 'sp': u'generalis', 'genus_id': 1,
     'hybrid': True, 'sp_author': u'L.',
     'infrasp1_rank': u'cv.', 'infrasp1': u'Red',
     'cv_group': u'SomeGroup'},
    {'id': 11, 'sp': u'generalis', 'genus_id': 1,
     'sp_qual': u'agg.'},
    {'id': 12, 'genus_id': 1, 'cv_group': u'SomeGroup'},
    {'id': 13, 'genus_id': 1,
     'infrasp1_rank': u'cv.', 'infrasp1': u'Red'},
    {'id': 14, 'genus_id': 1,
     'infrasp1_rank': u'cv.', 'infrasp1': u'Red & Blue'},
    {'id': 15, 'sp': u'cochleata', 'genus_id': 2,
     'sp_author': u'L.',
     'infrasp1_rank': u'subsp.', 'infrasp1': u'cochleata',
     'infrasp1_author': u'L.',
     'infrasp2_rank': u'var.', 'infrasp2': u'cochleata',
     'infrasp2_author': u'L.',
     'infrasp3_rank': u'cv.', 'infrasp3': u'Black',
     'infrasp3_author': u'L.'},
    {'id': 16, 'genus_id': 1, 'sp': u'test',
     'infrasp1_rank': u'subsp.', 'infrasp1': u'test',
     'cv_group': u'SomeGroup'},
    {'id': 17, 'genus_id': 5, 'sp': u'adductum', 'author': u'Asher'},
    {'id': 18, 'genus_id': 6, 'sp': u'lobata', 'author': u'H.J. Veitch'},
    {'id': 19, 'genus_id': 6, 'sp': u'grandiflora', 'author': u'Lindl.'},
    {'id': 20, 'genus_id': 2, 'sp': u'fragrans', 'author': u'Dressler'},
    {'id': 21, 'genus_id': 7, 'sp': u'arborea', 'author': u'Lagerh.'},
    {'id': 22, 'sp': u'', 'genus_id': 1, 'sp_author': u'',
     'infrasp1_rank': u'cv.', 'infrasp1': u'Layla Saida'},
    {'id': 23, 'sp': u'', 'genus_id': 1, 'sp_author': u'',
     'infrasp1_rank': u'cv.', 'infrasp1': u'Buonanotte'},
    {'id': 24, 'sp': u'', 'genus_id': 1, 'sp_author': u'',
     'infrasp1_rank': None, 'infrasp1': u'sp'},
    )

species_note_test_data = (
    {'id': 1, 'species_id': 18, 'category': u'CITES', 'note': u'I'},
    {'id': 2, 'species_id': 20, 'category': u'IUCN', 'note': u'LC'},
    {'id': 3, 'species_id': 18, 'category': u'<price>', 'note': u'19.50'},
    {'id': 4, 'species_id': 18, 'category': u'[list_var]', 'note': u'abc'},
    {'id': 5, 'species_id': 18, 'category': u'[list_var]', 'note': u'def'},
    {'id': 6, 'species_id': 18, 'category': u'<price_tag>', 'note': u'$19.50'},
    {'id': 7, 'species_id': 18, 'category': u'{dict_var:k}', 'note': u'abc'},
    {'id': 8, 'species_id': 18, 'category': u'{dict_var:l}', 'note': u'def'},
    {'id': 9, 'species_id': 18, 'category': u'{dict_var:m}', 'note': u'xyz'},
    )

species_str_map = {
    1: 'Maxillaria variabilis',
    2: 'Encyclia cochleata',
    3: 'Abrus precatorius',
    4: 'Campyloneurum %salapense' % Species.hybrid_char,
    5: 'Encyclia cochleata var. cochleata',
    6: "Encyclia cochleata 'Black Night'",
    7: 'Abrus precatorius SomethingRidiculous Group',
    8: "Abrus precatorius (SomethingRidiculous Group) 'Hot Rio Nights'",
    9: "Maxillaria %sgeneralis 'Red'" % Species.hybrid_char,
    10: ("Maxillaria %sgeneralis (SomeGroup Group) 'Red'"
         % Species.hybrid_char),
    11: "Maxillaria generalis agg.",
    12: "Maxillaria SomeGroup Group",
    13: "Maxillaria 'Red'",
    14: "Maxillaria 'Red & Blue'",
    15: "Encyclia cochleata subsp. cochleata var. cochleata 'Black'",
    16: "Maxillaria test subsp. test SomeGroup Group"
    }

species_markup_map = {
    1: '<i>Maxillaria</i> <i>variabilis</i>',
    2: '<i>Encyclia</i> <i>cochleata</i>',
    3: '<i>Abrus</i> <i>precatorius</i>',
    4: '<i>Campyloneurum</i> %s<i>alapense</i>' % Species.hybrid_char,
    5: '<i>Encyclia</i> <i>cochleata</i> var. <i>cochleata</i>',
    6: '<i>Encyclia</i> <i>cochleata</i> \'Black Night\'',
    12: "<i>Maxillaria</i> SomeGroup Group",
    14: "<i>Maxillaria</i> 'Red &amp; Blue'",
    15: ("<i>Encyclia</i> <i>cochleata</i> subsp. <i>"
         "cochleata</i> var. <i>cochleata</i> 'Black'"),
    }

species_str_authors_map = {
    1: 'Maxillaria variabilis Bateman ex Lindl.',
    2: u'Encyclia cochleata (L.) Lem\xe9e',
    3: 'Abrus precatorius L.',
    4: u'Campyloneurum %salapense F\xe9e' % Species.hybrid_char,
    5: u'Encyclia cochleata (L.) Lem\xe9e var. cochleata',
    6: u'Encyclia cochleata (L.) Lem\xe9e \'Black Night\'',
    7: 'Abrus precatorius L. SomethingRidiculous Group',
    8: "Abrus precatorius L. (SomethingRidiculous Group) 'Hot Rio Nights'",
    15: ("Encyclia cochleata L. subsp. "
         "cochleata L. var. cochleata L. 'Black' L."),
}

species_markup_authors_map = {
    1: '<i>Maxillaria</i> <i>variabilis</i> Bateman ex Lindl.',
    2: u'<i>Encyclia</i> <i>cochleata</i> (L.) Lem\xe9e',
    3: '<i>Abrus</i> <i>precatorius</i> L.',
    4: u'<i>Campyloneurum</i> %s<i>alapense</i> F\xe9e' % Species.hybrid_char,
    5: u'<i>Encyclia</i> <i>cochleata</i> (L.) Lem\xe9e var. <i>cochleata</i>',
    6: u'<i>Encyclia</i> <i>cochleata</i> (L.) Lem\xe9e \'Black Night\''}

sp_synonym_test_data = ({'id': 1, 'synonym_id': 1, 'species_id': 2},
                        )

vn_test_data = (
    {'id': 1, 'name': u'SomeName', 'language': u'English', 'species_id': 1},
    {'id': 2, 'name': u'SomeName 2', 'language': u'English', 'species_id': 1},
    {'id': 3, 'name': u'Floripondio', 'language': u'es', 'species_id': 21},
    {'id': 4, 'name': u'Toé', 'language': u'agr', 'species_id': 21},
    )

test_data_table_control = (
    (Family, family_test_data),
    (Genus, genus_test_data),
    (Species, species_test_data),
    (VernacularName, vn_test_data),
    (SpeciesSynonym, sp_synonym_test_data),
    (FamilyNote, family_note_test_data),
    (GenusNote, genus_note_test_data),
    (SpeciesNote, species_note_test_data),
    )


def setUp_data():
    """
    bauble.plugins.plants.test.setUp_test_data()

    if this method is called again before tearDown_test_data is called you
    will get an error about the test data rows already existing in the database
    """

    for mapper, data in test_data_table_control:
        table = mapper.__table__
        # insert row by row instead of doing an insert many since each
        # row will have different columns
        for row in data:
            table.insert().execute(row).close()
        for col in table.c:
            utils.reset_sequence(col)


class DuplicateIdsGlade(TestCase):
    def test_duplicate_ids(self):
        """
        Test for duplicate ids for all .glade files in the plants plugin.
        """
        import bauble.plugins.garden as mod
        import glob
        head, tail = os.path.split(mod.__file__)
        files = glob.glob(os.path.join(head, '*.glade'))
        for f in files:
            self.assertTrue(not check_dupids(f), f)


class PlantTestCase(BaubleTestCase):

    def __init__(self, *args):
        super(PlantTestCase, self).__init__(*args)
        from bauble import prefs
        prefs.testing = True

    def setUp(self):
        super(PlantTestCase, self).setUp()
        setUp_data()

    def tearDown(self):
        super(PlantTestCase, self).tearDown()


class FamilyTests(PlantTestCase):
    """
    Test for Family and FamilySynonym
    """
    def test_cascades(self):
        """
        Test that cascading is set up properly
        """
        family = Family(family=u'family')
        genus = Genus(family=family, genus=u'genus')
        self.session.add_all([family, genus])
        self.session.commit()

        # test that deleting a family deletes an orphaned genus
        self.session.delete(family)
        self.session.commit()
        query = self.session.query(Genus).filter_by(family_id=family.id)
        self.assertRaises(NoResultFound, query.one)

    def test_synonyms(self):
        """
        Test that Family.synonyms works correctly
        """
        family = Family(family=u'family')
        family2 = Family(family=u'family2')
        family.synonyms.append(family2)
        self.session.add_all([family, family2])
        self.session.commit()

        # test that family2 was added as a synonym to family
        family = self.session.query(Family).filter_by(family=u'family').one()
        self.assert_(family2 in family.synonyms)

        # test that the synonyms relation and family backref works
        self.assert_(family._synonyms[0].family == family)
        self.assert_(family._synonyms[0].synonym == family2)

        # test that the synonyms are removed properly
        family.synonyms.remove(family2)
        self.session.commit()
        self.assert_(family2 not in family.synonyms)

        # test synonyms contraints, e.g that a family cannot have the
        # same synonym twice
        family.synonyms.append(family2)
        self.session.commit()
        family.synonyms.append(family2)
        self.assertRaises(IntegrityError, self.session.commit)
        self.session.rollback()

        # test that clearing all the synonyms works
        family.synonyms.clear()
        self.session.commit()
        self.assert_(len(family.synonyms) == 0)
        self.assert_(self.session.query(FamilySynonym).count() == 0)

        # test that deleting a family that is a synonym of another family
        # deletes all the dangling object s
        family.synonyms.append(family2)
        self.session.commit()
        self.session.delete(family2)
        self.session.commit()
        self.assert_(self.session.query(FamilySynonym).count() == 0)

        # test that deleting the previous synonyms didn't delete the
        # family that it refered to
        self.assert_(self.session.query(Family).get(family.id))

        # test that deleting a family that has synonyms deletes all
        # the synonyms that refer to that family deletes all the
        family2 = Family(family=u'family2')
        self.session.add(family2)
        family.synonyms.append(family2)
        self.session.commit()
        self.session.delete(family)
        self.session.commit()
        self.assert_(self.session.query(FamilySynonym).count() == 0)

    def test_constraints(self):
        """
        Test that the family constraints were created correctly
        """
        values = [dict(family=u'family'),
                  dict(family=u'family', qualifier=u's. lat.')]
        for v in values:
            self.session.add(Family(**v))
            self.session.add(Family(**v))
            self.assertRaises(IntegrityError, self.session.commit)
            self.session.rollback()

        # test that family cannot be null
        self.session.add(Family(family=None))
        self.assertRaises(IntegrityError, self.session.commit)
        self.session.rollback()

    def test_str(self):
        """
        Test that the family str function works as expected
        """
        f = Family()
        self.assert_(str(f) == repr(f))
        f = Family(family=u'fam')
        self.assert_(str(f) == 'fam')
        f.qualifier = u's. lat.'
        self.assert_(str(f) == 'fam s. lat.')

    def test_editor(self):
        """
        Interactively test the FamilyEditor
        """
        raise SkipTest('Not Implemented')
        #loc = self.create(Family, name=u'some site')
        fam = Family(family='some family')
        editor = FamilyEditor(model=fam)
        editor.start()
        del editor
        assert utils.gc_objects_by_type('FamilyEditor') == [], \
            'FamilyEditor not deleted'
        assert utils.gc_objects_by_type('FamilyEditorPresenter') == [], \
            'FamilyEditorPresenter not deleted'
        assert utils.gc_objects_by_type('FamilyEditorView') == [], \
            'FamilyEditorView not deleted'

    def test_remove_callback_no_genera_no_confirm(self):
        # T_0
        f5 = Family(family=u'Arecaceae')
        self.session.add(f5)
        self.session.flush()
        self.invoked = []

        # action
        utils.yes_no_dialog = partial(
            mockfunc, name='yes_no_dialog', caller=self, result=False)
        utils.message_details_dialog = partial(
            mockfunc, name='message_details_dialog', caller=self)
        from bauble.plugins.plants.family import remove_callback
        result = remove_callback([f5])
        self.session.flush()

        # effect
        print self.invoked
        self.assertFalse('message_details_dialog' in
                         [f for (f, m) in self.invoked])
        self.assertTrue(('yes_no_dialog', u'Are you sure you want to '
                         'remove the family <i>Arecaceae</i>?')
                        in self.invoked)
        self.assertEquals(result, None)
        q = self.session.query(Family).filter_by(family=u"Arecaceae")
        matching = q.all()
        self.assertEquals(matching, [f5])

    def test_remove_callback_no_genera_confirm(self):
        # T_0
        f5 = Family(family=u'Arecaceae')
        self.session.add(f5)
        self.session.flush()
        self.invoked = []

        # action
        utils.yes_no_dialog = partial(
            mockfunc, name='yes_no_dialog', caller=self, result=True)
        utils.message_details_dialog = partial(
            mockfunc, name='message_details_dialog', caller=self)
        from bauble.plugins.plants.family import remove_callback
        result = remove_callback([f5])
        self.session.flush()

        # effect
        print self.invoked
        self.assertFalse('message_details_dialog' in
                         [f for (f, m) in self.invoked])
        self.assertTrue(('yes_no_dialog', u'Are you sure you want to '
                         'remove the family <i>Arecaceae</i>?')
                        in self.invoked)

        self.assertEquals(result, True)
        q = self.session.query(Family).filter_by(family=u"Arecaceae")
        matching = q.all()
        self.assertEquals(matching, [])

    def test_remove_callback_with_genera_cant_cascade(self):
        # T_0
        f5 = Family(family=u'Arecaceae')
        gf5 = Genus(family=f5, genus=u'Areca')
        self.session.add_all([f5, gf5])
        self.session.flush()
        self.invoked = []

        # action
        utils.yes_no_dialog = partial(
            mockfunc, name='yes_no_dialog', caller=self, result=True)
        utils.message_dialog = partial(
            mockfunc, name='message_dialog', caller=self, result=True)
        utils.message_details_dialog = partial(
            mockfunc, name='message_details_dialog', caller=self)
        from bauble.plugins.plants.family import remove_callback
        result = remove_callback([f5])
        self.session.flush()

        # effect
        print self.invoked
        self.assertFalse('message_details_dialog' in
                         [f for (f, m) in self.invoked])
        self.assertTrue(('message_dialog', u'The family <i>Arecaceae</i> has 1 genera.\n\nYou cannot remove a family with genera.')
                        in self.invoked)
        q = self.session.query(Family).filter_by(family=u"Arecaceae")
        matching = q.all()
        self.assertEquals(matching, [f5])
        q = self.session.query(Genus).filter_by(genus=u"Areca")
        matching = q.all()
        self.assertEquals(matching, [gf5])


class GenusTests(PlantTestCase):

    def test_synonyms(self):
        family = Family(family=u'family')
        genus = Genus(family=family, genus=u'genus')
        genus2 = Genus(family=family, genus=u'genus2')
        genus.synonyms.append(genus2)
        self.session.add_all([genus, genus2])
        self.session.commit()

        # test that genus2 was added as a synonym to genus
        genus = self.session.query(Genus).filter_by(genus=u'genus').one()
        self.assert_(genus2 in genus.synonyms)

        # test that the synonyms relation and genus backref works
        self.assert_(genus._synonyms[0].genus == genus)
        self.assert_(genus._synonyms[0].synonym == genus2)

        # test that the synonyms are removed properly
        genus.synonyms.remove(genus2)
        self.session.commit()
        self.assert_(genus2 not in genus.synonyms)

        # test synonyms contraints, e.g that a genus cannot have the
        # same synonym twice
        genus.synonyms.append(genus2)
        self.session.commit()
        genus.synonyms.append(genus2)
        self.assertRaises(IntegrityError, self.session.commit)
        self.session.rollback()

        # test that clearing all the synonyms works
        genus.synonyms.clear()
        self.session.commit()
        self.assert_(len(genus.synonyms) == 0)
        self.assert_(self.session.query(GenusSynonym).count() == 0)

        # test that deleting a genus that is a synonym of another genus
        # deletes all the dangling objects
        genus.synonyms.append(genus2)
        self.session.commit()
        self.session.delete(genus2)
        self.session.commit()
        self.assert_(self.session.query(GenusSynonym).count() == 0)

        # test that deleting the previous synonyms didn't delete the
        # genus that it refered to
        self.assert_(self.session.query(Genus).get(genus.id))

        # test that deleting a genus that has synonyms deletes all
        # the synonyms that refer to that genus
        genus2 = Genus(family=family, genus=u'genus2')
        self.session.add(genus2)
        genus.synonyms.append(genus2)
        self.session.commit()
        self.session.delete(genus)
        self.session.commit()
        self.assert_(self.session.query(GenusSynonym).count() == 0)

    def test_contraints(self):
        """
        Test that the genus constraints were created correctly
        """
        family = Family(family=u'family')
        self.session.add(family)

        # if any of these values are inserted twice they should raise
        # an IntegrityError because the UniqueConstraint on Genus
        values = [dict(family=family, genus=u'genus'),
                  dict(family=family, genus=u'genus', author=u'author'),
                  dict(family=family, genus=u'genus', qualifier=u's. lat.'),
                  dict(family=family, genus=u'genus', qualifier=u's. lat.',
                       author=u'author')
                  ]
        for v in values:
            self.session.add(Genus(**v))
            self.session.add(Genus(**v))
            self.assertRaises(IntegrityError, self.session.commit)
            self.session.rollback()

    def test_str(self):
        """
        Test that the Genus string functions works as expected
        """
        pass

    def test_editor(self):
        """
        Interactively test the GenusEditor
        """
        raise SkipTest('Not Implemented')
        #loc = self.create(Genus, name=u'some site')
        fam = Family(family=u'family')
        fam2 = Family(family=u'family2')
        fam2.synonyms.append(fam)
        self.session.add_all([fam, fam2])
        self.session.commit()
        gen = Genus(genus='some genus')
        editor = GenusEditor(model=gen)
        editor.start()
        del editor
        assert utils.gc_objects_by_type('GenusEditor') == [], \
            'GenusEditor not deleted'
        assert utils.gc_objects_by_type('GenusEditorPresenter') == [], \
            'GenusEditorPresenter not deleted'
        assert utils.gc_objects_by_type('GenusEditorView') == [], \
            'GenusEditorView not deleted'

    def test_can_use_epithet_field(self):
        family = Family(epithet=u'family')
        genus = Genus(family=family, genus=u'genus')
        self.session.add_all([family, genus])
        self.session.commit()
        g1 = self.session.query(Genus).filter(Genus.epithet=='genus').one()
        g2 = self.session.query(Genus).filter(Genus.genus=='genus').one()
        self.assertEquals(g1, g2)
        self.assertEquals(g1.genus, 'genus')
        self.assertEquals(g2.epithet, 'genus')

    def test_remove_callback_no_species_no_confirm(self):
        # T_0
        caricaceae = Family(family=u'Caricaceae')
        f5 = Genus(epithet=u'Carica', family=caricaceae)
        self.session.add(caricaceae)
        self.session.add(f5)
        self.session.flush()
        self.invoked = []

        # action
        utils.yes_no_dialog = partial(
            mockfunc, name='yes_no_dialog', caller=self, result=False)
        utils.message_details_dialog = partial(
            mockfunc, name='message_details_dialog', caller=self)
        from bauble.plugins.plants.genus import remove_callback
        result = remove_callback([f5])
        self.session.flush()

        # effect
        self.assertFalse('message_details_dialog' in
                         [f for (f, m) in self.invoked])
        self.assertTrue(('yes_no_dialog', u'Are you sure you want to '
                         'remove the genus <i>Carica</i>?')
                        in self.invoked)
        self.assertEquals(result, None)
        q = self.session.query(Genus).filter_by(genus=u"Carica")
        matching = q.all()
        self.assertEquals(matching, [f5])

    def test_remove_callback_no_species_confirm(self):
        # T_0
        caricaceae = Family(family=u'Caricaceae')
        f5 = Genus(epithet=u'Carica', family=caricaceae)
        self.session.add_all([caricaceae, f5])
        self.session.flush()
        self.invoked = []

        # action
        utils.yes_no_dialog = partial(
            mockfunc, name='yes_no_dialog', caller=self, result=True)
        utils.message_details_dialog = partial(
            mockfunc, name='message_details_dialog', caller=self)
        from bauble.plugins.plants.genus import remove_callback
        result = remove_callback([f5])
        self.session.flush()

        # effect
        print self.invoked
        self.assertFalse('message_details_dialog' in
                         [f for (f, m) in self.invoked])
        self.assertTrue(('yes_no_dialog', u'Are you sure you want to '
                         'remove the genus <i>Carica</i>?')
                        in self.invoked)

        self.assertEquals(result, True)
        q = self.session.query(Genus).filter_by(genus=u"Carica")
        matching = q.all()
        self.assertEquals(matching, [])

    def test_remove_callback_with_species_cant_cascade(self):
        # T_0
        caricaceae = Family(family=u'Caricaceae')
        f5 = Genus(epithet=u'Carica', family=caricaceae)
        gf5 = Species(genus=f5, sp=u'papaya')
        self.session.add_all([caricaceae, f5, gf5])
        self.session.flush()
        self.invoked = []

        # action
        utils.yes_no_dialog = partial(
            mockfunc, name='yes_no_dialog', caller=self, result=True)
        utils.message_dialog = partial(
            mockfunc, name='message_dialog', caller=self, result=True)
        utils.message_details_dialog = partial(
            mockfunc, name='message_details_dialog', caller=self)
        from bauble.plugins.plants.genus import remove_callback
        result = remove_callback([f5])
        self.session.flush()

        # effect
        print self.invoked
        self.assertFalse('message_details_dialog' in
                         [f for (f, m) in self.invoked])
        self.assertTrue(('message_dialog', u'The genus <i>Carica</i> has 1 species.\n\nYou cannot remove a genus with species.')
                        in self.invoked)
        q = self.session.query(Genus).filter_by(genus=u"Carica")
        matching = q.all()
        self.assertEquals(matching, [f5])
        q = self.session.query(Species).filter_by(sp=u"papaya")
        matching = q.all()
        self.assertEquals(matching, [gf5])
        

class GenusSynonymyTests(PlantTestCase):

    def setUp(self):
        super(GenusSynonymyTests, self).setUp()
        f = self.session.query(Family).filter(Family.family == u'Orchidaceae'
                                              ).one()
        bu = Genus(family=f, genus=u'Bulbophyllum')  # accepted
        zy = Genus(family=f, genus=u'Zygoglossum')  # synonym
        bu.synonyms.append(zy)
        self.session.add_all([f, bu, zy])
        self.session.commit()

    def test_forward_synonyms(self):
        "a taxon has a list of synonyms"
        bu = self.session.query(
            Genus).filter(
            Genus.genus == u'Bulbophyllum').one()
        zy = self.session.query(
            Genus).filter(
            Genus.genus == u'Zygoglossum').one()
        self.assertEquals(bu.synonyms, [zy])
        self.assertEquals(zy.synonyms, [])

    def test_backward_synonyms(self):
        "synonymy is used to get the accepted taxon"
        bu = self.session.query(
            Genus).filter(
            Genus.genus == u'Bulbophyllum').one()
        zy = self.session.query(
            Genus).filter(
            Genus.genus == u'Zygoglossum').one()
        self.assertEquals(zy.accepted, bu)
        self.assertEquals(bu.accepted, None)

    def test_synonymy_included_in_as_dict(self):
        bu = self.session.query(
            Genus).filter(
            Genus.genus == u'Bulbophyllum').one()
        zy = self.session.query(
            Genus).filter(
            Genus.genus == u'Zygoglossum').one()
        self.assertTrue('accepted' not in bu.as_dict())
        self.assertTrue('accepted' in zy.as_dict())
        self.assertEquals(zy.as_dict()['accepted'],
                          bu.as_dict(recurse=False))

    def test_define_accepted(self):
        # notice that same test should be also in Species and Family
        bu = self.session.query(
            Genus).filter(
            Genus.genus == u'Bulbophyllum').one()
        f = self.session.query(
            Family).filter(
            Family.family == u'Orchidaceae').one()
        he = Genus(family=f, genus=u'Henosis')  # one more synonym
        self.session.add(he)
        self.session.commit()
        self.assertEquals(len(bu.synonyms), 1)
        self.assertFalse(he in bu.synonyms)
        he.accepted = bu
        self.assertEquals(len(bu.synonyms), 2)
        self.assertTrue(he in bu.synonyms)

    def test_can_redefine_accepted(self):
        # Altamiranoa Rose used to refer to Villadia Rose for its accepted
        # name, it is now updated to Sedum L.

        ## T_0
        claceae = Family(family=u'Crassulaceae')  # J. St.-Hil.
        villa = Genus(family=claceae, genus=u'Villadia', author=u'Rose')
        alta = Genus(family=claceae, genus=u'Altamiranoa', author=u'Rose')
        alta.accepted = villa
        self.session.add_all([claceae, alta, villa])
        self.session.commit()

        sedum = Genus(family=claceae, genus=u'Sedum', author=u'L.')
        alta.accepted = sedum
        self.session.commit()


class SpeciesTests(PlantTestCase):

    def setUp(self):
        super(SpeciesTests, self).setUp()

    def tearDown(self):
        super(SpeciesTests, self).tearDown()

    def test_editor(self):
        raise SkipTest('Not Implemented')
        # import default geography data
        import bauble.paths as paths
        default_path = os.path.join(
            paths.lib_dir(), "plugins", "plants", "default")
        filenames = [os.path.join(default_path, f) for f in 'geography.txt',
                     'habit.txt']
        from bauble.plugins.imex.csv_ import CSVImporter
        importer = CSVImporter()
        importer.start(filenames, force=True)

        f = Family(family=u'family')
        g2 = Genus(genus=u'genus2', family=f)
        g = Genus(genus=u'genus', family=f)
        g2.synonyms.append(g)
        self.session.add(f)
        self.session.commit()
        sp = Species(genus=g, sp=u'sp')
        edit_species(model=sp)
        assert utils.gc_objects_by_type('SpeciesEditorMenuItem') == [], \
            'SpeciesEditor not deleted'
        assert utils.gc_objects_by_type('SpeciesEditorPresenter') == [], \
            'SpeciesEditorPresenter not deleted'
        assert utils.gc_objects_by_type('SpeciesEditorView') == [], \
            'SpeciesEditorView not deleted'

    def test_str(self):
        """
        Test the Species.str() method
        """
        def get_sp_str(id, **kwargs):
            return self.session.query(Species).get(id).str(**kwargs)

        for sid, expect in species_str_map.iteritems():
                sp = self.session.query(Species).get(sid)
                printable_name = remove_zws("%s" % sp)
                self.assertEquals(species_str_map[sid], printable_name)
                spstr = get_sp_str(sid)
                self.assertEquals(remove_zws(spstr), expect)

        for sid, expect in species_str_authors_map.iteritems():
            spstr = get_sp_str(sid, authors=True)
            self.assertEquals(remove_zws(spstr), expect)

        for sid, expect in species_markup_map.iteritems():
            spstr = get_sp_str(sid, markup=True)
            self.assertEquals(remove_zws(spstr), expect)

        for sid, expect in species_markup_authors_map.iteritems():
            spstr = get_sp_str(sid, markup=True, authors=True)
            self.assertEquals(remove_zws(spstr), expect)

    def test_lexicographic_order__unspecified_precedes_specified(self):
        def get_sp_str(id, **kwargs):
            return self.session.query(Species).get(id).str(**kwargs)

        self.assertTrue(get_sp_str(1) > get_sp_str(22))
        self.assertTrue(get_sp_str(1) > get_sp_str(23))
        self.assertTrue(get_sp_str(1) > get_sp_str(24))
        self.assertTrue(get_sp_str(16) > get_sp_str(22))
        self.assertTrue(get_sp_str(16) > get_sp_str(23))
        self.assertTrue(get_sp_str(16) > get_sp_str(24))

    # def test_dirty_string(self):
    #     """
    #     That that the cache on a string is invalidated if the species
    #     is changed or expired.
    #     """
    #     family = Family(family=u'family')
    #     genus = Genus(family=family, genus=u'genus')
    #     sp = Species(genus=genus, sp=u'sp')
    #     self.session.add_all([family, genus, sp])
    #     self.session.commit()

    #     str1 = Species.str(sp)
    #     sp.sp = u'sp2'
    #     self.session.commit()
    #     self.session.refresh(sp)
    #     sp = self.session.query(Species).get(sp.id)
    #     self.assert_(Species.str(sp) != str1)

    def test_vernacular_name(self):
        """
        Test the Species.vernacular_name property
        """
        family = Family(family=u'family')
        genus = Genus(family=family, genus=u'genus')
        sp = Species(genus=genus, sp=u'sp')
        self.session.add_all([family, genus, sp])
        self.session.commit()

        # add a name
        vn = VernacularName(name=u'name')
        sp.vernacular_names.append(vn)
        self.session.commit()
        self.assert_(vn in sp.vernacular_names)

        # test that removing a name removes deleted orphaned objects
        sp.vernacular_names.remove(vn)
        self.session.commit()
        q = self.session.query(VernacularName).filter_by(species_id=sp.id)
        self.assertRaises(NoResultFound, q.one)

    def test_default_vernacular_name(self):
        """
        Test the Species.default_vernacular_name property
        """
        family = Family(family=u'family')
        genus = Genus(family=family, genus=u'genus')
        sp = Species(genus=genus, sp=u'sp')
        vn = VernacularName(name=u'name')
        sp.vernacular_names.append(vn)
        self.session.add_all([family, genus, sp, vn])
        self.session.commit()

        # test that setting the default vernacular names
        default = VernacularName(name=u'default')
        sp.default_vernacular_name = default
        self.session.commit()
        self.assert_(vn in sp.vernacular_names)
        self.assert_(sp.default_vernacular_name == default)

        # test that set_attr work on default vernacular name
        default = VernacularName(name=u'default')
        setattr(sp, 'default_vernacular_name', default)
        self.session.commit()
        self.assert_(vn in sp.vernacular_names)
        self.assert_(sp.default_vernacular_name == default)

        # test that if you set the default_vernacular_name on a
        # species then it automatically adds it to vernacular_names
        default = VernacularName(name=u'default')
        sp.default_vernacular_name = default
        self.session.commit()
        self.assert_(vn in sp.vernacular_names)
        self.assert_(sp.default_vernacular_name == default)

        # test that removing a vernacular name removes it from
        # default_vernacular_name, this test also effectively tests VNList
        dvid = sp._default_vernacular_name.id
        sp.vernacular_names.remove(default)
        self.session.commit()
        self.assertEquals(sp.default_vernacular_name, None)
        q = self.session.query(DefaultVernacularName)
        self.assertRaises(NoResultFound, q.filter_by(species_id=sp.id).one)
        self.assertRaises(NoResultFound, q.filter_by(id=dvid).one)

        # test that setting default_vernacular_name to None
        # removes the name properly and deletes any orphaned objects
        sp.vernacular_names.append(vn)
        sp.default_vernacular_name = vn
        self.session.commit()
        dvid = sp._default_vernacular_name.id
        sp.default_vernacular_name = None
        self.session.commit()
        q = self.session.query(DefaultVernacularName)
        self.assertRaises(NoResultFound, q.filter_by(species_id=sp.id).one)
        self.assertRaises(NoResultFound, q.filter_by(id=dvid).one)

        # test that calling __del__ on a default vernacular name removes it
        sp.default_vernacular_name = vn
        self.session.commit()
        dvid = sp._default_vernacular_name.id
        del sp.default_vernacular_name
        self.session.commit()
        self.assertEquals(sp.default_vernacular_name, None)
        q = self.session.query(DefaultVernacularName)
        self.assertRaises(NoResultFound, q.filter_by(species_id=sp.id).one)
        self.assertRaises(NoResultFound, q.filter_by(id=dvid).one)

        # test for regression in bug Launchpad #123286
        vn1 = VernacularName(name=u'vn1')
        vn2 = VernacularName(name=u'vn2')
        sp.default_vernacular_name = vn1
        sp.default_vernacular_name = vn2
        self.session.commit()

    def test_synonyms_low_level(self):
        """
        Test the Species.synonyms property
        """
        load_sp = lambda id: self.session.query(Species).get(id)

        def syn_str(id1, id2, isit='not'):
            sp1 = load_sp(id1)
            sp2 = load_sp(id2)
            return '%s(%s).synonyms: %s' % \
                   (sp1, sp1.id,
                    str(map(lambda s: '%s(%s)' %
                            (s, s.id), sp1.synonyms)))

        def synonym_of(id1, id2):
            sp1 = load_sp(id1)
            sp2 = load_sp(id2)
            return sp2 in sp1.synonyms

        # test that appending a synonym works using species.synonyms
        sp1 = load_sp(1)
        sp2 = load_sp(2)
        sp1.synonyms.append(sp2)
        self.session.flush()
        self.assert_(synonym_of(1, 2), syn_str(1, 2))

        # test that removing a synonyms works using species.synonyms
        sp1.synonyms.remove(sp2)
        self.session.flush()
        self.failIf(synonym_of(1, 2), syn_str(1, 2))

        self.session.expunge_all()

        # test that appending a synonym works using species._synonyms
        sp1 = load_sp(1)
        sp2 = load_sp(2)
        syn = SpeciesSynonym(sp2)
        sp1._synonyms.append(syn)
        self.session.flush()
        self.assert_(synonym_of(1, 2), syn_str(1, 2))

        # test that removing a synonyms works using species._synonyms
        sp1._synonyms.remove(syn)
        self.session.flush()
        self.failIf(synonym_of(1, 2), syn_str(1, 2))

        # test adding a species and then immediately remove it
        self.session.expunge_all()
        sp1 = load_sp(1)
        sp2 = load_sp(2)
        sp1.synonyms.append(sp2)
        sp1.synonyms.remove(sp2)
        #self.session.flush()
        self.session.commit()
        assert sp2 not in sp1.synonyms

        # add a species and immediately add the same species
        sp2 = load_sp(2)
        sp1.synonyms.append(sp2)
        sp1.synonyms.remove(sp2)
        sp1.synonyms.append(sp2)
        #self.session.flush() # shouldn't raise an error
        self.session.commit()
        assert sp2 in sp1.synonyms

        # test that deleting a species removes it from the synonyms list
        assert sp2 in sp1.synonyms
        self.session.delete(sp2)
        self.session.commit()
        assert sp2 not in sp1.synonyms

        self.session.expunge_all()

    def test_no_synonyms_means_itself_accepted(self):
        def create_tmp_sp(id):
            sp = Species(id=id, epithet=u"sp%02d"%id, genus_id=1)
            self.session.add(sp)
            return sp

        sp1 = create_tmp_sp(51)
        sp2 = create_tmp_sp(52)
        sp3 = create_tmp_sp(53)
        sp4 = create_tmp_sp(54)
        self.session.commit()
        self.assertEquals(sp1.accepted, None)
        self.assertEquals(sp2.accepted, None) 
        self.assertEquals(sp3.accepted, None) 
        self.assertEquals(sp4.accepted, None)

    def test_synonyms_and_accepted_properties(self):
        def create_tmp_sp(id):
            sp = Species(id=id, epithet=u"sp%02d"%id, genus_id=1)
            self.session.add(sp)
            return sp

        # equivalence classes after changes
        sp1 = create_tmp_sp(41)
        sp2 = create_tmp_sp(42)
        sp3 = create_tmp_sp(43)
        sp4 = create_tmp_sp(44)  # (1), (2), (3), (4)
        sp3.accepted = sp1  # (1 3), (2), (4)
        self.assertEquals([i.epithet for i in sp1.synonyms], [sp3.epithet])
        sp1.synonyms.append(sp2)  # (1 3 2), (4)
        self.session.flush()
        print 'synonyms of 1', [i.epithet[-1] for i in sp1.synonyms]
        print 'synonyms of 4', [i.epithet[-1] for i in sp4.synonyms]
        self.assertEquals(sp2.accepted.epithet, sp1.epithet)  # just added
        self.assertEquals(sp3.accepted.epithet, sp1.epithet)  # no change
        sp2.accepted = sp4  # (1 3), (4 2)
        self.session.flush()
        print 'synonyms of 1', [i.epithet[-1] for i in sp1.synonyms]
        print 'synonyms of 4', [i.epithet[-1] for i in sp4.synonyms]
        self.assertEquals([i.epithet for i in sp4.synonyms], [sp2.epithet])
        self.assertEquals([i.epithet for i in sp1.synonyms], [sp3.epithet])
        self.assertEquals(sp1.accepted, None)
        self.assertEquals(sp2.accepted, sp4) 
        self.assertEquals(sp3.accepted, sp1) 
        self.assertEquals(sp4.accepted, None)
        sp2.accepted = sp4  # does not change anything
        self.assertEquals(sp1.accepted, None)
        self.assertEquals(sp2.accepted, sp4) 
        self.assertEquals(sp3.accepted, sp1) 
        self.assertEquals(sp4.accepted, None)

    def test_remove_callback_no_accessions_no_confirm(self):
        # T_0
        caricaceae = Family(family=u'Caricaceae')
        f5 = Genus(epithet=u'Carica', family=caricaceae)
        sp = Species(epithet=u'papaya', genus=f5)
        self.session.add_all([caricaceae, f5, sp])
        self.session.flush()
        self.invoked = []

        # action
        utils.yes_no_dialog = partial(
            mockfunc, name='yes_no_dialog', caller=self, result=False)
        utils.message_details_dialog = partial(
            mockfunc, name='message_details_dialog', caller=self)
        from bauble.plugins.plants.species import remove_callback
        result = remove_callback([sp])
        self.session.flush()

        # effect
        self.assertFalse('message_details_dialog' in
                         [f for (f, m) in self.invoked])
        print self.invoked
        self.assertTrue(('yes_no_dialog', u'Are you sure you want to remove the species <i>Carica \u200bpapaya</i>?')
                        in self.invoked)
        self.assertEquals(result, None)
        q = self.session.query(Species).filter_by(genus=f5, sp=u"papaya")
        matching = q.all()
        self.assertEquals(matching, [sp])

    def test_remove_callback_no_accessions_confirm(self):
        # T_0
        caricaceae = Family(family=u'Caricaceae')
        f5 = Genus(epithet=u'Carica', family=caricaceae)
        sp = Species(epithet=u'papaya', genus=f5)
        self.session.add_all([caricaceae, f5, sp])
        self.session.flush()
        self.invoked = []

        # action
        utils.yes_no_dialog = partial(
            mockfunc, name='yes_no_dialog', caller=self, result=True)
        utils.message_details_dialog = partial(
            mockfunc, name='message_details_dialog', caller=self)
        from bauble.plugins.plants.species import remove_callback
        result = remove_callback([sp])
        self.session.flush()

        # effect
        print self.invoked
        self.assertFalse('message_details_dialog' in
                         [f for (f, m) in self.invoked])
        self.assertTrue(('yes_no_dialog', u'Are you sure you want to remove the species <i>Carica \u200bpapaya</i>?')
                        in self.invoked)

        self.assertEquals(result, True)
        q = self.session.query(Species).filter_by(sp=u"Carica")
        matching = q.all()
        self.assertEquals(matching, [])

    def test_remove_callback_with_accessions_cant_cascade(self):
        # T_0
        caricaceae = Family(family=u'Caricaceae')
        f5 = Genus(epithet=u'Carica', family=caricaceae)
        sp = Species(epithet=u'papaya', genus=f5)
        from bauble.plugins.garden import (Accession)
        acc = Accession(code=u'0123456', species=sp)
        self.session.add_all([caricaceae, f5, sp, acc])
        self.session.flush()
        self.invoked = []

        # action
        utils.yes_no_dialog = partial(
            mockfunc, name='yes_no_dialog', caller=self, result=True)
        utils.message_dialog = partial(
            mockfunc, name='message_dialog', caller=self, result=True)
        utils.message_details_dialog = partial(
            mockfunc, name='message_details_dialog', caller=self)
        from bauble.plugins.plants.species import remove_callback
        result = remove_callback([sp])
        self.session.flush()

        # effect
        print self.invoked
        self.assertFalse('message_details_dialog' in
                         [f for (f, m) in self.invoked])
        self.assertTrue(('message_dialog', u'The species <i>Carica \u200bpapaya</i> has 1 accessions.\n\nYou cannot remove a species with accessions.')
                        in self.invoked)
        q = self.session.query(Species).filter_by(genus=f5, sp=u"papaya")
        matching = q.all()
        self.assertEquals(matching, [sp])
        q = self.session.query(Accession).filter_by(species=sp)
        matching = q.all()
        self.assertEquals(matching, [acc])


class GeographyTests(PlantTestCase):

    def __init__(self, *args):
        super(GeographyTests, self).__init__(*args)

    def setUp(self):
        super(GeographyTests, self).setUp()
        self.family = Family(family=u'family')
        self.genus = Genus(genus=u'genus', family=self.family)
        self.session.add_all([self.family, self.genus])
        self.session.flush()
        # import default geography data
        import bauble.paths as paths
        filename = os.path.join(paths.lib_dir(), "plugins", "plants",
                                "default", 'geography.txt')
        from bauble.plugins.imex.csv_ import CSVImporter
        importer = CSVImporter()
        importer.start([filename], force=True)
        self.session.commit()

    def tearDown(self):
        super(GeographyTests, self).tearDown()

    def test_get_species(self):
        mexico_id = 53
        mexico_central_id = 267
        oaxaca_id = 665
        northern_america_id = 7
        western_canada_id = 45

        # create a some species
        sp1 = Species(genus=self.genus, sp=u'sp1')
        dist = SpeciesDistribution(geography_id=mexico_central_id)
        sp1.distribution.append(dist)

        sp2 = Species(genus=self.genus, sp=u'sp2')
        dist = SpeciesDistribution(geography_id=oaxaca_id)
        sp2.distribution.append(dist)

        sp3 = Species(genus=self.genus, sp=u'sp3')
        dist = SpeciesDistribution(geography_id=western_canada_id)
        sp3.distribution.append(dist)

        self.session.commit()

        oaxaca = self.session.query(Geography).get(oaxaca_id)
        species = get_species_in_geography(oaxaca)
        self.assert_([s.id for s in species] == [sp2.id])

        mexico = self.session.query(Geography).get(mexico_id)
        species = get_species_in_geography(mexico)
        self.assert_([s.id for s in species] == [sp1.id, sp2.id])

        north_america = self.session.query(Geography).get(northern_america_id)
        species = get_species_in_geography(north_america)
        self.assert_([s.id for s in species] == [sp1.id, sp2.id, sp3.id])

    def test_species_distribution_str(self):
        # create a some species
        sp1 = Species(genus=self.genus, sp=u'sp1')
        dist = SpeciesDistribution(geography_id=267)
        sp1.distribution.append(dist)
        self.session.flush()
        self.assertEquals(sp1.distribution_str(), 'Mexico Central')
        dist = SpeciesDistribution(geography_id=45)
        sp1.distribution.append(dist)
        self.session.flush()
        self.assertEquals(sp1.distribution_str(), 'Mexico Central, Western Canada')


class FromAndToDictTest(PlantTestCase):
    """tests the retrieve_or_create and the as_dict methods
    """

    def test_can_grab_existing_families(self):
        all_families = self.session.query(Family).all()
        orc = Family.retrieve_or_create(
            self.session, {'rank': 'family',
                           'epithet': 'Orchidaceae'})
        leg = Family.retrieve_or_create(
            self.session, {'rank': 'family',
                           'epithet': 'Leguminosae'})
        pol = Family.retrieve_or_create(
            self.session, {'rank': 'family',
                           'epithet': 'Polypodiaceae'})
        sol = Family.retrieve_or_create(
            self.session, {'rank': 'family',
                           'epithet': 'Solanaceae'})
        self.assertEquals(set(all_families), set([orc, pol, leg, sol]))

    def test_grabbing_same_params_same_output_existing(self):
        orc1 = Family.retrieve_or_create(
            self.session, {'rank': 'family',
                           'epithet': 'Orchidaceae'})
        orc2 = Family.retrieve_or_create(
            self.session, {'rank': 'family',
                           'epithet': 'Orchidaceae'})
        self.assertTrue(orc1 is orc2)

    def test_can_create_family(self):
        all_families = self.session.query(Family).all()
        fab = Family.retrieve_or_create(
            self.session, {'rank': 'family',
                           'epithet': 'Fabaceae'})
        ## it's in the session, it wasn't there before.
        self.assertTrue(fab in self.session)
        self.assertFalse(fab in all_families)
        ## according to the session, it is in the database
        ses_families = self.session.query(Family).all()
        self.assertTrue(fab in ses_families)

    def test_where_can_object_be_found_before_commit(self):  # disabled
        raise SkipTest('Not Implemented')
        fab = Family.retrieve_or_create(
            self.session, {'rank': 'family',
                           'epithet': 'Fabaceae'})
        # created in a session, it's not in other sessions
        other_session = db.Session()
        db_families = other_session.query(Family).all()
        fab = Family.retrieve_or_create(
            other_session, {'rank': 'family',
                            'epithet': 'Fabaceae'})
        self.assertFalse(fab in db_families)  # fails, why?

    def test_where_can_object_be_found_after_commit(self):
        fab = Family.retrieve_or_create(
            self.session, {'rank': 'family',
                           'epithet': 'Fabaceae'})
        ## after commit it's in database.
        self.session.commit()
        other_session = db.Session()
        all_families = other_session.query(Family).all()
        fab = Family.retrieve_or_create(
            other_session, {'rank': 'family',
                            'epithet': 'Fabaceae'})
        self.assertTrue(fab in all_families)

    def test_grabbing_same_params_same_output_new(self):
        fab1 = Family.retrieve_or_create(
            self.session, {'rank': 'family',
                           'epithet': 'Fabaceae'})
        fab2 = Family.retrieve_or_create(
            self.session, {'rank': 'family',
                           'epithet': 'Fabaceae'})
        self.assertTrue(fab1 is fab2)

    def test_can_grab_existing_genera(self):
        orc = Family.retrieve_or_create(
            self.session, {'rank': 'family',
                           'epithet': 'Orchidaceae'})
        all_genera_orc = self.session.query(Genus).filter(
            Genus.family == orc).all()
        mxl = Genus.retrieve_or_create(
            self.session, {'ht-rank': 'family',
                           'ht-epithet': 'Orchidaceae',
                           'rank': 'genus',
                           'epithet': 'Maxillaria'})
        enc = Genus.retrieve_or_create(
            self.session, {'ht-rank': 'family',
                           'ht-epithet': 'Orchidaceae',
                           'rank': 'genus',
                           'epithet': 'Encyclia'})
        self.assertTrue(mxl in set(all_genera_orc))
        self.assertTrue(enc in set(all_genera_orc))


class FromAndToDict_create_update_test(PlantTestCase):
    "test the create and update fields in retrieve_or_create"

    def test_family_nocreate_noupdate_noexisting(self):
        # do not create if not existing
        obj = Family.retrieve_or_create(
            self.session, {'object': 'taxon',
                           'rank': 'familia',
                           'epithet': 'Arecaceae'},
            create=False)
        self.assertEquals(obj, None)

    def test_family_nocreate_noupdateeq_existing(self):
        ## retrieve same object, we only give the keys
        obj = Family.retrieve_or_create(
            self.session, {'object': 'taxon',
                           'rank': 'familia',
                           'epithet': 'Leguminosae'},
            create=False, update=False)
        self.assertTrue(obj is not None)
        self.assertEquals(obj.qualifier, 's. str.')

    def test_family_nocreate_noupdatediff_existing(self):
        ## do not update object with new data
        obj = Family.retrieve_or_create(
            self.session, {'object': 'taxon',
                           'rank': 'familia',
                           'epithet': 'Leguminosae',
                           'qualifier': u's. lat.'},
            create=False, update=False)
        self.assertEquals(obj.qualifier, u's. str.')

    def test_family_nocreate_updatediff_existing(self):
        ## update object in self.session
        obj = Family.retrieve_or_create(
            self.session, {'object': 'taxon',
                           'rank': 'familia',
                           'epithet': 'Leguminosae',
                           'qualifier': u's. lat.'},
            create=False, update=True)
        self.assertEquals(obj.qualifier, u's. lat.')

    def test_genus_nocreate_noupdate_noexisting_impossible(self):
        # do not create if not existing
        obj = Genus.retrieve_or_create(
            self.session, {'object': 'taxon',
                           'rank': 'genus',
                           'epithet': 'Masdevallia'},
            create=False)
        self.assertEquals(obj, None)

    def test_genus_create_noupdate_noexisting_impossible(self):
        # do not create if not existing
        obj = Genus.retrieve_or_create(
            self.session, {'object': 'taxon',
                           'rank': 'genus',
                           'epithet': 'Masdevallia'},
            create=True)
        self.assertEquals(obj, None)

    def test_genus_nocreate_noupdate_noexisting_possible(self):
        # do not create if not existing
        obj = Genus.retrieve_or_create(
            self.session, {'object': 'taxon',
                           'rank': 'genus',
                           'epithet': 'Masdevallia',
                           'ht-rank': 'familia',
                           'ht-epithet': 'Orchidaceae'},
            create=False)
        self.assertEquals(obj, None)

    def test_genus_nocreate_noupdateeq_existing(self):
        ## retrieve same object, we only give the keys
        obj = Genus.retrieve_or_create(
            self.session, {'object': 'taxon',
                           'rank': 'genus',
                           'epithet': 'Maxillaria'},
            create=False, update=False)
        self.assertTrue(obj is not None)
        self.assertEquals(obj.author, '')

    def test_genus_nocreate_noupdatediff_existing(self):
        ## do not update object with new data
        obj = Genus.retrieve_or_create(
            self.session, {'object': 'taxon',
                           'rank': 'genus',
                           'epithet': u'Maxillaria',
                           'author': u'Schltr.'},
            create=False, update=False)
        self.assertTrue(obj is not None)
        self.assertEquals(obj.author, '')

    def test_genus_nocreate_updatediff_existing(self):
        ## update object in self.session
        obj = Genus.retrieve_or_create(
            self.session, {'object': 'taxon',
                           'rank': 'genus',
                           'epithet': u'Maxillaria',
                           'author': u'Schltr.'},
            create=False, update=True)
        self.assertTrue(obj is not None)
        self.assertEquals(obj.author, u'Schltr.')

    def test_vernacular_name_as_dict(self):
        bra = self.session.query(Species).filter(Species.id == 21).first()
        vn_bra = self.session.query(VernacularName).filter(
            VernacularName.language == u'agr',
            VernacularName.species == bra).all()
        self.assertEquals(vn_bra[0].as_dict(),
                          {'object': 'vernacular_name',
                           'name': u'Toé',
                           'language': u'agr',
                           'species': 'Brugmansia arborea'})
        vn_bra = self.session.query(VernacularName).filter(
            VernacularName.language == u'es',
            VernacularName.species == bra).all()
        self.assertEquals(vn_bra[0].as_dict(),
                          {'object': 'vernacular_name',
                           'name': u'Floripondio',
                           'language': u'es',
                           'species': 'Brugmansia arborea'})

    def test_vernacular_name_nocreate_noupdate_noexisting(self):
        # do not create if not existing
        obj = VernacularName.retrieve_or_create(
            self.session, {'object': u'vernacular_name',
                           'language': u'nap',
                           'species': u'Brugmansia arborea'},
            create=False)
        self.assertEquals(obj, None)

    def test_vernacular_name_nocreate_noupdateeq_existing(self):
        ## retrieve same object, we only give the keys
        obj = VernacularName.retrieve_or_create(
            self.session, {'object': u'vernacular_name',
                           'language': u'agr',
                           'species': u'Brugmansia arborea'},
            create=False, update=False)
        self.assertTrue(obj is not None)
        self.assertEquals(obj.name, 'Toé')

    def test_vernacular_name_nocreate_noupdatediff_existing(self):
        ## do not update object with new data
        obj = VernacularName.retrieve_or_create(
            self.session, {'object': 'vernacular_name',
                           'language': u'agr',
                           'name': u'wronge',
                           'species': u'Brugmansia arborea'},
            create=False, update=False)
        self.assertEquals(obj.name, 'Toé')

    def test_vernacular_name_nocreate_updatediff_existing(self):
        ## update object in self.session
        obj = VernacularName.retrieve_or_create(
            self.session, {'object': 'vernacular_name',
                           'language': u'agr',
                           'name': u'wronge',
                           'species': u'Brugmansia arborea'},
            create=False, update=True)
        self.assertEquals(obj.name, 'wronge')


class CitesStatus_test(PlantTestCase):
    "we can retrieve the cites status as defined in family-genus-species"

    def test(self):
        obj = Genus.retrieve_or_create(
            self.session, {'object': 'taxon',
                           'rank': 'genus',
                           'epithet': u'Maxillaria'},
            create=False, update=False)
        self.assertEquals(obj.cites, u'II')
        obj = Genus.retrieve_or_create(
            self.session, {'object': 'taxon',
                           'rank': 'genus',
                           'epithet': u'Laelia'},
            create=False, update=False)
        self.assertEquals(obj.cites, u'II')
        obj = Species.retrieve_or_create(
            self.session, {'object': 'taxon',
                           'ht-rank': 'genus',
                           'ht-epithet': u'Paphiopedilum',
                           'rank': 'species',
                           'epithet': u'adductum'},
            create=False, update=False)
        self.assertEquals(obj.cites, u'I')
        obj = Species.retrieve_or_create(
            self.session, {'object': 'taxon',
                           'ht-rank': 'genus',
                           'ht-epithet': u'Laelia',
                           'rank': 'species',
                           'epithet': u'lobata'},
            create=False, update=False)
        self.assertEquals(obj.cites, u'I')
        obj = Species.retrieve_or_create(
            self.session, {'object': 'taxon',
                           'ht-rank': 'genus',
                           'ht-epithet': u'Laelia',
                           'rank': 'species',
                           'epithet': u'grandiflora'},
            create=False, update=False)
        self.assertEquals(obj.cites, u'II')


class GenusHybridMarker_test(PlantTestCase):

    def test_intergeneric_hybrid_not_hybrid(self):
        gen = Genus.retrieve_or_create(
            self.session, {'ht-rank': 'family',
                           'ht-epithet': u'Orchidaceae',
                           'rank': 'genus',
                           'epithet': u'Cattleya'})
        self.assertEquals(gen.hybrid_marker, u'')
        self.assertEquals(gen.hybrid_epithet, u'Cattleya')

    def test_intergeneric_hybrid_mult(self):
        gen = Genus.retrieve_or_create(
            self.session, {'ht-rank': 'family',
                           'ht-epithet': u'Orchidaceae',
                           'rank': 'genus',
                           'epithet': u'×Brassocattleya'})
        self.assertEquals(gen.hybrid_marker, u'×')
        self.assertEquals(gen.hybrid_epithet, u'Brassocattleya')

    def test_intergeneric_hybrid_x_becomes_mult(self):
        gen = Genus.retrieve_or_create(
            self.session, {'ht-rank': 'family',
                           'ht-epithet': u'Orchidaceae',
                           'rank': 'genus',
                           'epithet': u'xVascostylis'})
        self.assertEquals(gen.hybrid_marker, u'×')
        self.assertEquals(gen.hybrid_epithet, u'Vascostylis')

    def test_hybrid_formula_H(self):
        gen = Genus.retrieve_or_create(
            self.session, {'ht-rank': 'family',
                           'ht-epithet': u'Orchidaceae',
                           'rank': 'genus',
                           'epithet': u'Miltonia × Odontoglossum × Cochlioda'})
        self.assertEquals(gen.hybrid_marker, u'H')
        self.assertEquals(gen.hybrid_epithet, u'Miltonia × Odontoglossum × Cochlioda')

    def test_intergeneric_graft_hybrid_plus(self):
        gen = Genus.retrieve_or_create(
            self.session, {'ht-rank': 'family',
                           'ht-epithet': u'Rosaceae',
                           'rank': 'genus',
                           'epithet': u'+Crataegomespilus'})
        self.assertEquals(gen.hybrid_marker, u'+')
        self.assertEquals(gen.hybrid_epithet, u'Crataegomespilus')


class SpeciesInfraspecificProp(PlantTestCase):

    def test_cultivar_epithet_1(self):
        obj = Species.retrieve_or_create(
            self.session, {'object': 'taxon',
                           'ht-rank': 'genus',
                           'ht-epithet': u'Paphiopedilum',
                           'rank': 'species',
                           'epithet': u''})
        obj.infrasp1 = u'Eva Weigner'
        obj.infrasp1_rank = u'cv.'
        self.assertEquals(obj.cultivar_epithet, u'Eva Weigner')

    def test_cultivar_epithet_2(self):
        obj = Species.retrieve_or_create(
            self.session, {'object': 'taxon',
                           'ht-rank': 'genus',
                           'ht-epithet': u'Paphiopedilum',
                           'rank': 'species',
                           'epithet': u''})
        obj.infrasp2 = u'Eva Weigner'
        obj.infrasp2_rank = u'cv.'
        self.assertEquals(obj.cultivar_epithet, u'Eva Weigner')

    def include_cinnamomum_camphora(self):
        '''\
Lauraceae,,Cinnamomum,,"camphora",,"","(L.) J.Presl"
Lauraceae,,Cinnamomum,,"camphora",f.,"linaloolifera","(Y.Fujita) Sugim."
Lauraceae,,Cinnamomum,,"camphora",var.,"nominale","Hats. & Hayata"
'''
        Family.retrieve_or_create(
            self.session, {'object': 'taxon',
                           'rank': 'family',
                           'epithet': u'Lauraceae'})
        self.cinnamomum = Genus.retrieve_or_create(
            self.session, {'object': 'taxon',
                           'ht-rank': 'family',
                           'ht-epithet': u'Lauraceae',
                           'rank': 'genus',
                           'epithet': u'Cinnamomum'})
        self.cinnamomum_camphora = Species.retrieve_or_create(
            self.session, {'object': 'taxon',
                           'ht-rank': 'genus',
                           'ht-epithet': u'Cinnamomum',
                           'rank': 'species',
                           'epithet': u'camphora'})

    def test_infraspecific_1(self):
        self.include_cinnamomum_camphora()
        obj = Species(genus=self.cinnamomum,
                      sp=u'camphora',
                      infrasp1_rank=u'f.',
                      infrasp1=u'linaloolifera',
                      infrasp1_author=u'(Y.Fujita) Sugim.')
        self.assertEquals(obj.infraspecific_rank, u'f.')
        self.assertEquals(obj.infraspecific_epithet, u'linaloolifera')
        self.assertEquals(obj.infraspecific_author, u'(Y.Fujita) Sugim.')

    def test_infraspecific_2(self):
        self.include_cinnamomum_camphora()
        obj = Species(genus=self.cinnamomum,
                      sp=u'camphora',
                      infrasp2_rank=u'f.',
                      infrasp2=u'linaloolifera',
                      infrasp2_author=u'(Y.Fujita) Sugim.')
        self.assertEquals(obj.infraspecific_rank, u'f.')
        self.assertEquals(obj.infraspecific_epithet, u'linaloolifera')
        self.assertEquals(obj.infraspecific_author, u'(Y.Fujita) Sugim.')

    def include_gleditsia_triacanthos(self):
        "Gleditsia triacanthos var. inermis 'Sunburst'."
        Family.retrieve_or_create(
            self.session, {'object': 'taxon',
                           'rank': 'family',
                           'epithet': 'Fabaceae'})
        self.gleditsia = Genus.retrieve_or_create(
            self.session, {'object': 'taxon',
                           'ht-rank': 'family',
                           'ht-epithet': u'Fabaceae',
                           'rank': 'genus',
                           'epithet': u'Gleditsia'})
        self.gleditsia_triacanthos = Species.retrieve_or_create(
            self.session, {'object': 'taxon',
                           'ht-rank': 'genus',
                           'ht-epithet': u'Gleditsia',
                           'rank': 'species',
                           'epithet': u'triacanthos'})

    def test_variety_and_cultivar_1(self):
        self.include_gleditsia_triacanthos()
        obj = Species(genus=self.gleditsia,
                      sp=u'triacanthos',
                      infrasp1_rank=u'var.',
                      infrasp1=u'inermis',
                      infrasp2=u'Sunburst',
                      infrasp2_rank=u'cv.')
        self.assertEquals(obj.infraspecific_rank, u'var.')
        self.assertEquals(obj.infraspecific_epithet, u'inermis')
        self.assertEquals(obj.infraspecific_author, u'')
        self.assertEquals(obj.cultivar_epithet, u'Sunburst')

    def test_variety_and_cultivar_2(self):
        self.include_gleditsia_triacanthos()
        obj = Species(genus=self.gleditsia,
                      sp=u'triacanthos',
                      infrasp2_rank=u'var.',
                      infrasp2=u'inermis',
                      infrasp1=u'Sunburst',
                      infrasp1_rank=u'cv.')
        self.assertEquals(obj.infraspecific_rank, u'var.')
        self.assertEquals(obj.infraspecific_epithet, u'inermis')
        self.assertEquals(obj.infraspecific_author, u'')
        self.assertEquals(obj.cultivar_epithet, u'Sunburst')

    def test_infraspecific_props_is_lowest_ranked(self):
        '''Saxifraga aizoon\
        var. aizoon subvar. brevifolia f. multicaulis subf. surculosa'''
        Family.retrieve_or_create(
            self.session, {'object': 'taxon',
                           'rank': 'family',
                           'epithet': 'Saxifragaceae'})
        self.genus = Genus.retrieve_or_create(
            self.session, {'object': 'taxon',
                           'ht-rank': 'family',
                           'ht-epithet': u'Saxifragaceae',
                           'rank': 'genus',
                           'epithet': u'Saxifraga'})
        self.species = Species.retrieve_or_create(
            self.session, {'object': 'taxon',
                           'ht-rank': 'genus',
                           'ht-epithet': u'Saxifraga',
                           'rank': 'species',
                           'epithet': u'aizoon'})
        subvar = Species(genus=self.genus,
                         sp=u'aizoon',
                         infrasp1_rank=u'var.',
                         infrasp1=u'aizoon',
                         infrasp2_rank=u'subvar.',
                         infrasp2=u'brevifolia',
                         )
        subf = Species(genus=self.genus,
                       sp=u'aizoon',
                       infrasp2_rank=u'var.',
                       infrasp2=u'aizoon',
                       infrasp1_rank=u'subvar.',
                       infrasp1=u'brevifolia',
                       infrasp3_rank=u'f.',
                       infrasp3=u'multicaulis',
                       infrasp4_rank=u'subf.',
                       infrasp4=u'surculosa',
                       )
        self.assertEquals(subvar.infraspecific_rank, u'subvar.')
        self.assertEquals(subvar.infraspecific_epithet, u'brevifolia')
        self.assertEquals(subvar.infraspecific_author, u'')
        self.assertEquals(subvar.cultivar_epithet, u'')
        self.assertEquals(subf.infraspecific_rank, u'subf.')
        self.assertEquals(subf.infraspecific_epithet, u'surculosa')
        self.assertEquals(subf.infraspecific_author, u'')
        self.assertEquals(subf.cultivar_epithet, u'')
        "Saxifraga aizoon var. aizoon subvar. brevifolia f. multicaulis "
        "cv. 'Bellissima'"
        cv = Species(genus=self.genus,
                     sp=u'aizoon',
                     infrasp4_rank=u'var.',
                     infrasp4=u'aizoon',
                     infrasp1_rank=u'subvar.',
                     infrasp1=u'brevifolia',
                     infrasp3_rank=u'f.',
                     infrasp3=u'multicaulis',
                     infrasp2_rank=u'cv.',
                     infrasp2=u'Bellissima',
                     )
        self.assertEquals(cv.infraspecific_rank, u'f.')
        self.assertEquals(cv.infraspecific_epithet, u'multicaulis')
        self.assertEquals(cv.infraspecific_author, u'')
        self.assertEquals(cv.cultivar_epithet, u'Bellissima')


class SpeciesProperties_test(PlantTestCase):
    "we can retrieve species_note objects given species and category"

    def test_species_note_nocreate_noupdate_noexisting(self):
        # do not create if not existing
        obj = SpeciesNote.retrieve_or_create(
            self.session, {'object': u'species_note',
                           'category': u'IUCN',
                           'species': u'Laelia grandiflora'},
            create=False)
        self.assertEquals(obj, None)

    def test_species_note_nocreate_noupdateeq_existing(self):
        ## retrieve same object, we only give the keys
        obj = SpeciesNote.retrieve_or_create(
            self.session, {'object': u'species_note',
                           'category': u'IUCN',
                           'species': u'Encyclia fragrans'},
            create=False, update=False)
        self.assertTrue(obj is not None)
        self.assertEquals(obj.note, u'LC')

    def test_species_note_nocreate_noupdatediff_existing(self):
        ## do not update object with new data
        obj = SpeciesNote.retrieve_or_create(
            self.session, {'object': u'species_note',
                           'category': u'IUCN',
                           'species': u'Encyclia fragrans',
                           'note': u'EX'},
            create=False, update=False)
        self.assertEquals(obj.note, u'LC')

    def test_species_note_nocreate_updatediff_existing(self):
        ## update object in self.session
        obj = SpeciesNote.retrieve_or_create(
            self.session, {'object': u'species_note',
                           'category': u'IUCN',
                           'species': u'Encyclia fragrans',
                           'note': u'EX'},
            create=False, update=True)
        self.assertEquals(obj.note, u'EX')


class AttributesStoredInNotes(PlantTestCase):
    def test_proper_yaml_dictionary(self):
        obj = Species.retrieve_or_create(
            self.session, {'object': 'taxon',
                           'ht-rank': 'genus',
                           'rank': 'species',
                           'ht-epithet': u'Laelia',
                           'epithet': u'lobata'},
            create=False, update=False)
        note = SpeciesNote(category=u'<coords>', note=u'{1: 1, 2: 2}')
        note.species = obj
        self.session.commit()
        self.assertEquals(obj.coords, {'1': 1, '2': 2})

    def test_very_sloppy_json_dictionary(self):
        obj = Species.retrieve_or_create(
            self.session, {'object': 'taxon',
                           'ht-rank': 'genus',
                           'rank': 'species',
                           'ht-epithet': u'Laelia',
                           'epithet': u'lobata'},
            create=False, update=False)
        note = SpeciesNote(category=u'<coords>', note=u'lat:8.3,lon:-80.1')
        note.species = obj
        self.session.commit()
        self.assertEquals(obj.coords, {'lat': 8.3, 'lon': -80.1})

    def test_very_very_sloppy_json_dictionary(self):
        obj = Species.retrieve_or_create(
            self.session, {'object': 'taxon',
                           'ht-rank': 'genus',
                           'rank': 'species',
                           'ht-epithet': u'Laelia',
                           'epithet': u'lobata'},
            create=False, update=False)
        note = SpeciesNote(category=u'<coords>', note=u'lat:8.3;lon:-80.1;alt:1400.0')
        note.species = obj
        self.session.commit()
        self.assertEquals(obj.coords, {'lat': 8.3, 'lon': -80.1, 'alt': 1400.0})

    def test_atomic_value_interpreted(self):
        obj = Species.retrieve_or_create(
            self.session, {'object': 'taxon',
                           'ht-rank': 'genus',
                           'rank': 'species',
                           'ht-epithet': u'Laelia',
                           'epithet': u'lobata'},
            create=False, update=False)
        self.assertEquals(obj.price, 19.50)

    def test_atomic_value_verbatim(self):
        obj = Species.retrieve_or_create(
            self.session, {'object': 'taxon',
                           'ht-rank': 'genus',
                           'rank': 'species',
                           'ht-epithet': u'Laelia',
                           'epithet': u'lobata'},
            create=False, update=False)
        self.assertEquals(obj.price_tag, '$19.50')

    def test_list_value(self):
        obj = Species.retrieve_or_create(
            self.session, {'object': 'taxon',
                           'ht-rank': 'genus',
                           'rank': 'species',
                           'ht-epithet': u'Laelia',
                           'epithet': u'lobata'},
            create=False, update=False)
        self.assertEquals(obj.list_var, ['abc', 'def'])

    def test_dict_value(self):
        obj = Species.retrieve_or_create(
            self.session, {'object': 'taxon',
                           'ht-rank': 'genus',
                           'rank': 'species',
                           'ht-epithet': u'Laelia',
                           'epithet': u'lobata'},
            create=False, update=False)
        self.assertEquals(obj.dict_var, {'k': 'abc', 'l': 'def', 'm': 'xyz'})


class ConservationStatus_test(PlantTestCase):
    "can retrieve the IUCN conservation status as defined in species"

    def test(self):
        obj = Species.retrieve_or_create(
            self.session, {'object': 'taxon',
                           'ht-rank': 'genus',
                           'ht-epithet': u'Encyclia',
                           'rank': 'species',
                           'epithet': u'fragrans'},
            create=False, update=False)
        self.assertEquals(obj.conservation, u'LC')


from editor import GenericModelViewPresenterEditor, MockView


class PresenterTest(PlantTestCase):
    def test_canreeditobject(self):
        species = Species.retrieve_or_create(
            self.session, {'object': 'taxon',
                           'ht-rank': 'genus',
                           'ht-epithet': u'Paphiopedilum',
                           'rank': 'species',
                           'epithet': u'adductum'},
            create=False, update=False)
        presenter = GenericModelViewPresenterEditor(species, MockView())
        species.author = u'wrong'
        presenter.commit_changes()
        species.author = u'Asher'
        presenter.commit_changes()

    def test_cantinsertsametwice(self):
        'while binomial name in view matches database item, warn user'

        raise SkipTest('Not Implemented')  # presenter uses view internals
        from species_editor import SpeciesEditorPresenter
        model = Species.retrieve_or_create(
            self.session, {'object': 'taxon',
                           'ht-rank': 'genus',
                           'ht-epithet': u'Laelia',
                           'rank': 'species',
                           'epithet': u'lobata'},
            create=False, update=False)
        presenter = SpeciesEditorPresenter(model, MockView())
        presenter.on_text_entry_changed('sp_species_entry', 'grandiflora')

    def test_cantinsertsametwice_warnonce(self):
        'while binomial name in view matches database item, warn user'

        raise SkipTest('Not Implemented')  # presenter uses view internals


class GlobalFunctionsTest(PlantTestCase):
    def test_species_markup_func(self):
        eCo = Species.retrieve_or_create(
            self.session, {'object': 'taxon',
                           'ht-rank': 'genus',
                           'ht-epithet': u'Maxillaria',
                           'rank': 'species',
                           'epithet': u'variabilis'},
            create=False, update=False)
        model = Species.retrieve_or_create(
            self.session, {'object': 'taxon',
                           'ht-rank': 'genus',
                           'ht-epithet': u'Laelia',
                           'rank': 'species',
                           'epithet': u'lobata'},
            create=False, update=False)
        first, second = eCo.search_view_markup_pair()
        self.assertTrue(remove_zws(first).startswith(
            u'<i>Maxillaria</i> <i>variabilis</i>'))
        expect = '<i>Maxillaria</i> <i>variabilis</i> <span weight="light">'\
            'Bateman ex Lindl.</span><span foreground="#555555" size="small" '\
            'weight="light"> - synonym of <i>Encyclia</i> <i>cochleata</i> '\
            '(L.) Lemée</span>'
        self.assertEquals(remove_zws(first), expect)
        self.assertEquals(second, u'Orchidaceae -- SomeName, SomeName 2')
        first, second = model.search_view_markup_pair()
        self.assertEquals(remove_zws(first), u'<i>Laelia</i> <i>lobata</i>')
        self.assertEquals(second, u'Orchidaceae')

    def test_vername_markup_func(self):
        vName = self.session.query(VernacularName).filter_by(id=1).one()
        first, second = vName.search_view_markup_pair()
        self.assertEquals(remove_zws(second), u'<i>Maxillaria</i> <i>variabilis</i>')
        self.assertEquals(first, u'SomeName')

    def test_species_get_kids(self):
        mVa = self.session.query(Species).filter_by(id=1).one()
        self.assertEquals(partial(db.natsort, 'accessions')(mVa), [])

    def test_vernname_get_kids(self):
        vName = self.session.query(VernacularName).filter_by(id=1).one()
        self.assertEquals(partial(db.natsort, 'species.accessions')(vName), [])

import bauble.search
class BaubleSearchSearchTest(BaubleTestCase):
    def test_search_search_uses_Synonym_Search(self):
        bauble.search.search("genus like %", self.session)
        self.assertTrue('SearchStrategy "genus like %"(SynonymSearch)' in 
                   self.handler.messages['bauble.search']['debug'])
        self.handler.reset()
        bauble.search.search("12.11.13", self.session)
        self.assertTrue('SearchStrategy "12.11.13"(SynonymSearch)' in 
                   self.handler.messages['bauble.search']['debug'])
        self.handler.reset()
        bauble.search.search("So ha", self.session)
        self.assertTrue('SearchStrategy "So ha"(SynonymSearch)' in 
                   self.handler.messages['bauble.search']['debug'])
