# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Brett Adams
# Copyright 2015,2017 Mario Frasca <mario@anche.no>.
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





import os
import datetime
from unittest import TestCase

from gi.repository import Gtk

import logging
logger = logging.getLogger(__name__)

from nose import SkipTest
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import object_session

#import bauble
import bauble.db as db
from bauble.test import BaubleTestCase, update_gui, check_dupids, mockfunc
import bauble.utils as utils
from bauble.plugins.garden.accession import Accession, AccessionEditor, \
    AccessionNote, Voucher, SourcePresenter, Verification, dms_to_decimal, \
    latitude_to_dms, longitude_to_dms, AccessionEditorView
from bauble.plugins.garden.source import Source, Collection, Contact, \
    create_contact, CollectionPresenter, ContactPresenter
from bauble.plugins.garden.plant import Plant, PlantNote, \
    PlantChange, PlantEditor, is_code_unique, branch_callback
from bauble.plugins.garden.location import Location, LocationEditor
from bauble.plugins.garden.propagation import Propagation, PropCuttingRooted, \
    PropCutting, PropSeed, PropagationEditor
from bauble.plugins.plants.geography import GeographicArea
from bauble.plugins.plants.family import Family
from bauble.plugins.plants.genus import Genus
from bauble.plugins.plants.species_model import Species
import bauble.plugins.plants.test as plants_test
from bauble.plugins.garden.institution import Institution, InstitutionPresenter
from bauble import prefs

from functools import partial

from bauble.meta import BaubleMeta

from bauble.plugins.plants.species_model import _remove_zws as remove_zws
prefs.testing = True


accession_test_data = ({'id': 1, 'code': '2001.1', 'species_id': 1},
                       {'id': 2, 'code': '2001.2', 'species_id': 2,
                        'source_type': 'Collection'},
                       )

plant_test_data = ({'id': 1, 'code': '1', 'accession_id': 1,
                    'location_id': 1, 'quantity': 1},
                   {'id': 2, 'code': '1', 'accession_id': 2,
                    'location_id': 1, 'quantity': 1},
                   {'id': 3, 'code': '2', 'accession_id': 2,
                    'location_id': 1, 'quantity': 1},
                   )

location_test_data = ({'id': 1, 'name': 'Somewhere Over The Rainbow',
                       'code': 'RBW'},
                      )

geographic_area_test_data = [{'id': 1, 'name': 'Somewhere'}]

collection_test_data = ({'id': 1, 'accession_id': 2, 'locale': 'Somewhere',
                         'geographic_area_id': 1},
                        )

default_propagation_values = \
    {'notes': 'test notes',
     'date': datetime.date(2011, 11, 25)}

default_cutting_values = \
    {'cutting_type': 'Nodal',
     'length': 2,
     'length_unit': 'mm',
     'tip': 'Intact',
     'leaves': 'Intact',
     'leaves_reduced_pct': 25,
     'flower_buds': 'None',
     'wound': 'Single',
     'fungicide': 'Physan',
     'media': 'standard mix',
     'container': '4" pot',
     'hormone': 'Auxin powder',
     'cover': 'Poly cover',
     'location': 'Mist frame',
     'bottom_heat_temp': 65,
     'bottom_heat_unit': 'F',
     'rooted_pct': 90}

default_seed_values = {
    'pretreatment': 'Soaked in peroxide solution',
    'nseeds': 24,
    'date_sown': datetime.date(2017, 1, 1),
    'container': "tray",
    'media': 'standard seed compost',
    'location': 'mist tent',
    'moved_from': 'mist tent',
    'moved_to': 'hardening table',
    'media': 'standard mix',
    'germ_date': datetime.date(2017, 2, 1),
    'germ_pct': 99,
    'nseedlings': 23,
    'date_planted': datetime.date(2017,2,8),
    }

test_data_table_control = ((Accession, accession_test_data),
                           (Location, location_test_data),
                           (Plant, plant_test_data),
                           (GeographicArea, geographic_area_test_data),
                           (Collection, collection_test_data))
testing_today = datetime.date(2017, 1, 1)

def setUp_data():
    for cls, data in test_data_table_control:
        table = cls.__table__
        for row in data:
            table.insert().execute(row).close()
        for col in table.c:
            utils.reset_sequence(col)
    i = Institution()
    i.name = 'TestInstitution'
    i.technical_contact = 'TestTechnicalContact Name'
    i.email = 'contact@test.com'
    i.contact = 'TestContact Name'
    i.code = 'TestCode'


# TODO: if we ever get a GUI tester then do the following
# test all possible combinations of entering data into the accession editor
# 1. new accession without source
# 2. new accession with source
# 3. existing accession without source
# 4. existing accession with new source
# 5. existing accession with existing source
# - create test for parsing latitude/longitude entered into the lat/lon entries

class DuplicateIdsGlade(TestCase):
    def test_duplicate_ids(self):
        import bauble.plugins.garden as mod
        import glob
        head, tail = os.path.split(mod.__file__)
        files = glob.glob(os.path.join(head, '*.glade'))
        for f in files:
            self.assertTrue(not check_dupids(f), f)


class GardenTestCase(BaubleTestCase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        prefs.testing = True

    def setUp(self):
        super().setUp()
        plants_test.setUp_data()
        self.family = Family(family='Cactaceae')
        self.genus = Genus(family=self.family, genus='Echinocactus')
        self.species = Species(genus=self.genus, sp='grusonii')
        self.sp2 = Species(genus=self.genus, sp='texelensis')
        self.session.add_all([self.family, self.genus, self.species, self.sp2])
        self.session.commit()

    def tearDown(self):
        super().tearDown()

    def create(self, class_, **kwargs):
        obj = class_(**kwargs)
        self.session.add(obj)
        return obj


class PlantTests(GardenTestCase):

    def __init__(self, *args):
        super().__init__(*args)

    def setUp(self):
        super().setUp()
        self.accession = self.create(Accession,
                                     species=self.species, code='1')
        self.location = self.create(Location, name='site', code='STE')
        self.plant = self.create(Plant, accession=self.accession,
                                 location=self.location, code='1', quantity=1)
        self.session.commit()

    def tearDown(self):
        super().tearDown()

    def test_constraints(self):
        # test that we can't have duplicate codes with the same accession
        plant2 = Plant(accession=self.accession, location=self.location,
                       code=self.plant.code, quantity=1)
        self.session.add(plant2)
        self.assertRaises(IntegrityError, self.session.commit)
        # rollback the IntegrityError so tearDown() can do its job
        self.session.rollback()

    def test_delete(self):
        raise SkipTest('Not Implemented')

    def test_editor_addnote(self):
        raise SkipTest('Not Implemented')

    def test_duplicate(self):
        p = Plant(accession=self.accession, location=self.location, code='2',
                  quantity=52)
        self.session.add(p)
        note = PlantNote(note='some note')
        note.plant = p
        note.date = datetime.date.today()
        change = PlantChange(from_location=self.location,
                             to_location=self.location, quantity=1)
        change.plant = p
        self.session.commit()
        dup = p.duplicate(code='3')
        assert dup.notes is not []
        assert dup.changes is not []
        self.session.commit()

    def test_search_view_markup_pair(self):
        # living plant
        p = Plant(accession=self.accession, location=self.location, code='2',
                  quantity=52)
        self.session.add(p)
        self.assertEqual(p.search_view_markup_pair(),
                          ('1.2 <span foreground="#555555" size="small" weight="light">- 52 alive in (STE) site</span>',
                           '<i>Echinocactus</i> <i>grusonii</i>'))
        # dead plant
        p = Plant(accession=self.accession, location=self.location, code='2',
                  quantity=0)
        self.session.add(p)
        self.assertEqual(p.search_view_markup_pair(),
                          ('<span foreground="#9900ff">1.2</span>',
                           '<i>Echinocactus</i> <i>grusonii</i>'))

    def test_bulk_plant_editor(self):
        from gi.repository import Gtk

        # use our own plant because PlantEditor.commit_changes() will
        # only work in bulk mode when the plant is in session.new
        p = Plant(accession=self.accession, location=self.location, code='2',
                  quantity=52)
        self.editor = PlantEditor(model=p)
        #editor.start()
        update_gui()
        rng = '2,3,4-6'

        for code in utils.range_builder(rng):
            q = self.session.query(Plant).join('accession').\
                filter(and_(Accession.id == self.plant.accession.id,
                            Plant.code == utils.utf8(code)))
            self.assertTrue(not q.first(), 'code already exists')

        widgets = self.editor.presenter.view.widgets
        # make sure the entry gets a Problem added to it if an
        # existing plant code is used in bulk mode
        widgets.plant_code_entry.set_text('1,' + rng)
        widgets.plant_quantity_entry.set_text('2')
        update_gui()
        problem = (self.editor.presenter.PROBLEM_DUPLICATE_PLANT_CODE,
                   self.editor.presenter.view.widgets.plant_code_entry)
        self.assertTrue(problem in self.editor.presenter.problems,
                     'no problem added for duplicate plant code')

        # create multiple plant codes
        widgets.plant_code_entry.set_text(rng)
        update_gui()
        self.editor.handle_response(Gtk.ResponseType.OK)

        for code in utils.range_builder(rng):
            q = self.session.query(Plant).join('accession').\
                filter(and_(Accession.id == self.plant.accession.id,
                            Plant.code == utils.utf8(code)))
            self.assertTrue(q.first(), 'plant %s.%s not created' %
                         (self.accession, code))

    def test_editor(self):
        raise SkipTest('separate view from presenter, then test presenter')
        for plant in self.session.query(Plant):
            self.session.delete(plant)
        for location in self.session.query(Location):
            self.session.delete(location)
        self.session.commit()

        #editor = PlantEditor(model=self.plant)
        loc = Location(name='site1', code='1')
        loc2 = Location(name='site2', code='2')
        loc2a = Location(name='site2a', code='2a')
        self.session.add_all([loc, loc2, loc2a])
        self.session.commit()
        p = Plant(accession=self.accession, location=loc, quantity=1)
        editor = PlantEditor(model=p)
        editor.start()

    def test_double_change(self):
        plant = Plant(accession=self.accession, code='11', location=self.location, quantity=10)
        loc2a = Location(name='site2a', code='2a')
        self.session.add_all([plant, loc2a])
        self.session.flush()
        editor = PlantEditor(model=plant, branch_mode=True)
        loc2a = object_session(editor.branched_plant).query(Location).filter(Location.code == '2a').one()
        editor.branched_plant.location = loc2a
        update_gui()
        editor.model.quantity = 3
        editor.compute_plant_split_changes()

        self.assertEqual(editor.branched_plant.quantity, 7)
        change = editor.branched_plant.changes[0]
        self.assertEqual(change.plant, editor.branched_plant)
        self.assertEqual(change.quantity, editor.model.quantity)
        self.assertEqual(change.to_location, editor.model.location)
        self.assertEqual(change.from_location, editor.branched_plant.location)

        self.assertEqual(editor.model.quantity, 3)
        change = editor.model.changes[0]
        self.assertEqual(change.plant, editor.model)
        self.assertEqual(change.quantity, editor.model.quantity)
        self.assertEqual(change.to_location, editor.model.location)
        self.assertEqual(change.from_location, editor.branched_plant.location)

    def test_branch_editor(self):
        from gi.repository import Gtk

        # test argument checks
        #
        # TODO: these argument checks make future tests fail because
        # the PlantEditor is never cleaned up
        #
        # self.assert_(PlantEditor())
        # self.assertRaises(CheckConditionError, PlantEditor, branch_mode=True)

        # plant = Plant(accession=self.accession, location=self.location,
        #               code=u'33', quantity=5)
        # self.assertRaises(CheckConditionError, PlantEditor, model=plant,
        #                   branch_mode=True)
        #self.accession.plants.remove(plant) # remove from session
        # TODO: test check where quantity < 2

        quantity = 5
        self.plant.quantity = quantity
        self.session.commit()
        self.editor = PlantEditor(model=self.plant, branch_mode=True)
        update_gui()

        widgets = self.editor.presenter.view.widgets
        new_quantity = 2
        widgets.plant_quantity_entry.props.text = "%s" % new_quantity
        update_gui()
        self.editor.handle_response(Gtk.ResponseType.OK)

        # there should only be three plants,
        new_plant = self.session.query(Plant).\
            filter(Plant.code != self.plant.code).first()
        # test the quantity was set properly on the new plant
        assert new_plant.quantity == new_quantity, new_plant.quantity
        self.session.refresh(self.plant)
        # test the quantity is updated on the original plant
        assert self.plant.quantity == quantity - new_plant.quantity, \
            "%s == %s - %s" % (self.plant.quantity, quantity,
                               new_plant.quantity)
        # test the quantity for the change is the same as the quantity
        # for the plant
        assert new_plant.changes[0].quantity == new_plant.quantity, \
            "%s == %s" % (new_plant.changes[0].quantity, new_plant.quantity)
        # test the parent_plant for the change is the same as the
        # original plant
        assert new_plant.changes[0].parent_plant == self.plant, \
            'change.parent_plant != original plant'

    def test_branch_callback(self):
        raise SkipTest('Not Implemented')
        for plant in self.session.query(Plant):
            self.session.delete(plant)
        for location in self.session.query(Location):
            self.session.delete(location)
        self.session.commit()

        #editor = PlantEditor(model=self.plant)
        loc = Location(name='site1', code='1')
        loc2 = Location(name='site2', code='2')
        quantity = 5
        plant = Plant(accession=self.accession, code='1', location=loc,
                      quantity=quantity)
        self.session.add_all([loc, loc2, plant])
        self.session.commit()

        branch_callback([plant])
        new_plant = self.session.query(Plant).filter(
            Plant.code != '1').first()
        self.session.refresh(plant)
        self.assertEqual(plant.quantity, quantity - new_plant.quantity)
        self.assertEqual(new_plant.changes[0].quantity, new_plant.quantity)

    def test_is_code_unique(self):
        self.assertFalse(is_code_unique(self.plant, '1'))
        self.assertTrue(is_code_unique(self.plant, '01'))
        self.assertFalse(is_code_unique(self.plant, '1-2'))
        self.assertFalse(is_code_unique(self.plant, '01-2'))

    def test_living_plant_has_no_date_of_death(self):
        self.assertEqual(self.plant.date_of_death, None)

    def test_setting_quantity_to_zero_defines_date_of_death(self):
        self.change = PlantChange()
        self.session.add(self.change)
        self.change.plant = self.plant
        self.change.from_location = self.plant.location
        self.change.quantity = self.plant.quantity
        self.plant.quantity = 0
        self.session.flush()
        self.assertNotEqual(self.plant.date_of_death, None)


class PropagationTests(GardenTestCase):

    def __init__(self, *args):
        super().__init__(*args)

    def setUp(self):
        super().setUp()
        self.accession = self.create(
            Accession, species=self.species, code='1')
        self.plants = []

    def add_plants(self, plant_codes=[]):
        loc = self.create(Location, name='name', code='code')
        for pc in plant_codes:
            self.plants.append(self.create(
                Plant,
                accession=self.accession, location=loc, code=pc, quantity=1))
        self.session.commit()

    def add_propagations(self, propagation_types=[]):
        for i, pt in enumerate(propagation_types):
            prop = Propagation()
            prop.prop_type = pt
            prop.plant = self.plants[i]
            if pt == 'Seed':
                specifically = PropSeed(**default_seed_values)
            elif pt == 'UnrootedCutting':
                specifically = PropCutting(**default_cutting_values)
            else:
                specifically = type('FooBar', (object,), {})()
            specifically.propagation = prop
        self.session.commit()

    def tearDown(self):
        self.session.query(Plant).delete()
        self.session.query(Location).delete()
        self.session.query(Accession).delete()
        self.session.commit()
        super().tearDown()

    def test_propagation_cutting_quantity_new_zero(self):
        self.add_plants(['1'])
        prop = Propagation()
        prop.prop_type = 'UnrootedCutting'
        prop.plant = self.plants[0]
        spec = PropCutting(cutting_type='Nodal')
        spec.propagation = prop
        self.session.commit()
        self.assertEqual(prop.accessible_quantity, 0)
        prop = Propagation()
        prop.prop_type = 'UnrootedCutting'
        prop.plant = self.plants[0]
        spec = PropCutting(cutting_type='Nodal', rooted_pct=0)
        spec.propagation = prop
        self.session.commit()
        self.assertEqual(prop.accessible_quantity, 0)

    def test_propagation_seed_quantity_new_zero(self):
        self.add_plants(['1'])
        prop = Propagation()
        prop.prop_type = 'Seed'
        prop.plant = self.plants[0]
        spec = PropSeed(nseeds=30, date_sown=datetime.date(2017, 1, 1))
        spec.propagation = prop
        self.session.commit()
        self.assertEqual(prop.accessible_quantity, 0)
        prop = Propagation()
        prop.prop_type = 'Seed'
        prop.plant = self.plants[0]
        spec = PropSeed(nseeds=30, date_sown=datetime.date(2017, 1, 1), nseedlings=0)
        spec.propagation = prop
        self.session.commit()
        self.assertEqual(prop.accessible_quantity, 0)

    def test_propagation_seed_unaccessed_quantity(self):
        self.add_plants(['1'])
        prop = Propagation()
        prop.prop_type = 'Seed'
        prop.plant = self.plants[0]
        seed = PropSeed(**default_seed_values)
        seed.propagation = prop
        self.session.commit()
        summary = prop.get_summary()
        self.assertEqual(prop.accessible_quantity, 23)

    def test_propagation_cutting_accessed_remaining_quantity(self):
        self.add_plants(['1'])
        self.add_propagations(['Seed'])
        accession2 = self.create(Accession, species=self.species, code='2', quantity_recvd=10)
        source2 = self.create(Source, plant_propagation=self.plants[0].propagations[0])
        accession2.source = source2
        self.session.commit()
        prop = self.plants[0].propagations[0]
        self.assertEqual(prop.accessible_quantity, 13)

    def test_propagation_other_unaccessed_remaining_quantity_1(self):
        self.add_plants(['1'])
        self.add_propagations(['Other'])
        prop = self.plants[0].propagations[0]
        self.assertEqual(prop.accessible_quantity, 1)

    def test_propagation_other_accessed_remaining_quantity_1(self):
        self.add_plants(['1'])
        self.add_propagations(['Other'])
        accession2 = self.create(Accession, species=self.species, code='2', quantity_recvd=10)
        source2 = self.create(Source, plant_propagation=self.plants[0].propagations[0])
        accession2.source = source2
        self.session.commit()
        prop = self.plants[0].propagations[0]
        self.assertEqual(prop.accessible_quantity, 1)

    def test_accession_propagations_is_union_of_plant_propagations(self):
        self.add_plants(['1', '2'])
        self.add_propagations(['UnrootedCutting', 'Seed'])
        self.assertEqual(len(self.accession.plants), 2)
        self.assertEqual(len(self.plants[0].propagations), 1)
        self.assertEqual(len(self.plants[1].propagations), 1)
        self.assertEqual(len(self.accession.propagations), 2)
        p1, p2 = self.plants[0].propagations[0], self.plants[1].propagations[0]
        self.assertTrue(p1 in self.accession.propagations)
        self.assertTrue(p2 in self.accession.propagations)

    def test_propagation_links_back_to_correct_plant(self):
        self.add_plants(['1', '2', '3'])
        self.add_propagations(['UnrootedCutting', 'Seed', 'Seed'])
        for plant in self.plants:
            self.assertEqual(len(plant.propagations), 1)
            prop = plant.propagations[0]
            self.assertEqual(prop.plant, plant)

    def test_get_summary_cutting_complete(self):
        self.add_plants(['1'])
        prop = Propagation()
        prop.prop_type = 'UnrootedCutting'
        prop.plant = self.plants[0]
        cutting = PropCutting(**default_cutting_values)
        cutting.propagation = prop
        rooted = PropCuttingRooted()
        rooted.cutting = cutting
        self.session.commit()
        summary = prop.get_summary()
        self.maxDiff = None
        self.assertEqual(summary, 'Cutting; Cutting type: Nodal; Length: 2mm; Tip: Intact; Leaves: Intact; Flower buds: None; Wounded: Singled; Fungal soak: Physan; Hormone treatment: Auxin powder; Bottom heat: 65°F; Container: 4" pot; Media: standard mix; Location: Mist frame; Cover: Poly cover; Rooted: 90%')

    def test_get_summary_seed_complete(self):
        self.add_plants(['1'])
        prop = Propagation()
        prop.prop_type = 'Seed'
        prop.plant = self.plants[0]
        seed = PropSeed(**default_seed_values)
        seed.propagation = prop
        self.session.commit()
        summary = prop.get_summary()
        self.assertEqual(summary, 'Seed; Pretreatment: Soaked in peroxide solution; # of seeds: 24; Date sown: 01-01-2017; Container: tray; Media: standard mix; Location: mist tent; Germination date: 01-02-2017; # of seedlings: 23; Germination rate: 99%; Date planted: 08-02-2017')

    def test_get_summary_seed_partial_1_still_unused(self):
        self.add_plants(['1'])
        self.add_propagations(['Seed'])
        prop = self.plants[0].propagations[0]
        self.assertEqual(prop.get_summary(partial=1), '')

    def test_get_summary_seed_partial_2_still_unused(self):
        self.add_plants(['1'])
        self.add_propagations(['Seed'])
        prop = self.plants[0].propagations[0]
        self.assertEqual(prop.get_summary(partial=2),
                          prop.get_summary())

    def test_get_summary_seed_partial_1_used_once(self):
        self.add_plants(['1'])
        self.add_propagations(['Seed'])
        accession2 = self.create(Accession, species=self.species, code='2')
        source2 = self.create(Source, plant_propagation=self.plants[0].propagations[0])
        accession2.source = source2
        self.session.commit()
        prop = self.plants[0].propagations[0]
        self.assertEqual(prop.get_summary(partial=1), accession2.code)

    def test_get_summary_seed_partial_1_used_twice(self):
        self.add_plants(['1'])
        self.add_propagations(['Seed'])
        using = ['2', '3']
        for c in using:
            a = self.create(Accession, species=self.species, code=c)
            s = self.create(Source, plant_propagation=self.plants[0].propagations[0])
            a.source = s
        self.session.commit()
        prop = self.plants[0].propagations[0]
        self.assertEqual(prop.get_summary(partial=1),
                          ';'.join("%s" % a for a in prop.accessions))

    def test_propagation_accessions_used_once(self):
        self.add_plants(['1'])
        self.add_propagations(['Seed'])
        accession2 = self.create(Accession, species=self.species, code='2')
        source2 = self.create(Source, plant_propagation=self.plants[0].propagations[0])
        accession2.source = source2
        self.session.commit()
        prop = self.plants[0].propagations[0]
        self.assertEqual(prop.accessions, [accession2])

    def test_propagation_accessions_used_twice(self):
        self.add_plants(['1'])
        self.add_propagations(['Seed'])
        prop = self.plants[0].propagations[0]
        using = ['2', '3']
        accs = []
        for c in using:
            a = self.create(Accession, species=self.species, code=c)
            s = self.create(Source, plant_propagation=prop)
            a.source = s
            accs.append(a)
        self.session.commit()
        self.assertEqual(len(prop.accessions), 2)
        self.assertEqual(sorted(accs, key=lambda x: x.code), sorted(prop.accessions, key=lambda x: x.code))

    def test_accession_source_plant_propagation_points_at_parent_plant(self):
        self.add_plants(['1'])
        self.add_propagations(['Seed'])
        prop = self.plants[0].propagations[0]
        using = ['2', '3']
        for c in using:
            a = self.create(Accession, species=self.species, code=c)
            s = self.create(Source, plant_propagation=prop)
            a.source = s
        self.session.commit()
        for a in prop.accessions:
            self.assertEqual(a.source.plant_propagation.plant, self.plants[0])
            self.assertEqual(a.parent_plant, self.plants[0])

    def test_accession_without_parent_plant(self):
        self.assertEqual(self.accession.parent_plant, None)

    def test_cutting_property(self):
        self.add_plants(['1'])
        prop = Propagation()
        prop.plant = self.plants[0]
        prop.prop_type = 'UnrootedCutting'
        prop.accession = self.accession
        cutting = PropCutting(**default_cutting_values)
        cutting.propagation = prop
        rooted = PropCuttingRooted()
        rooted.cutting = cutting
        self.session.add(rooted)
        self.session.commit()

        self.assertTrue(rooted in prop._cutting.rooted)

        rooted_id = rooted.id
        cutting_id = cutting.id
        self.assertTrue(rooted_id, 'no prop_rooted.id')

        # setting the _cutting property on Propagation should cause
        # the cutting and its rooted children to be deleted
        prop._cutting = None
        self.session.commit()
        self.assertTrue(not self.session.query(PropCutting).get(cutting_id))
        self.assertTrue(not self.session.query(PropCuttingRooted).get(rooted_id))

    def test_accession_links_to_parent_plant(self):
        '''we can reach the parent plant from an accession'''

        self.add_plants(['1'])
        pass

    def test_seed_property(self):
        loc = Location(name='name', code='code')
        plant = Plant(accession=self.accession, location=loc, code='1',
                      quantity=1)
        prop = Propagation()
        plant.propagations.append(prop)
        prop.prop_type = 'Seed'
        prop.accession = self.accession
        seed = PropSeed(**default_seed_values)
        self.session.add(seed)
        seed.propagation = prop
        self.session.commit()

        self.assertEqual(seed, prop._seed)
        seed_id = seed.id

        # this should cause the cutting and its rooted children to be deleted
        prop._seed = None
        self.session.commit()
        self.assertTrue(not self.session.query(PropSeed).get(seed_id))

    def test_cutting_editor(self):
        loc = Location(name='name', code='code')
        plant = Plant(accession=self.accession, location=loc, code='1',
                      quantity=1)
        propagation = Propagation()
        plant.propagations.append(propagation)
        self.editor = PropagationEditor(model=propagation)
        widgets = self.editor.presenter.view.widgets
        self.assertTrue(widgets is not None)
        view = self.editor.presenter.view
        view.widget_set_value('prop_type_combo', 'UnrootedCutting')
        view.widget_set_value('prop_date_entry', utils.today_str())
        cutting_presenter = self.editor.presenter._cutting_presenter
        for widget, attr in cutting_presenter.widget_to_field_map.items():
            #debug('%s=%s' % (widget, default_cutting_values[attr]))
            view.widget_set_value(widget, default_cutting_values[attr])
        update_gui()
        self.editor.handle_response(Gtk.ResponseType.OK)
        self.editor.commit_changes()
        model = self.editor.model
        s = object_session(model)
        s.expire(model)
        self.assertEqual(model.prop_type, 'UnrootedCutting')
        for attr, value in default_cutting_values.items():
            v = getattr(model._cutting, attr)
            self.assertEqual(v, value)
        self.editor.session.close()

    def test_seed_editor_commit(self):
        loc = Location(name='name', code='code')
        plant = Plant(accession=self.accession, location=loc, code='1',
                      quantity=1)
        propagation = Propagation()
        plant.propagations.append(propagation)
        editor = PropagationEditor(model=propagation)
        widgets = editor.presenter.view.widgets
        seed_presenter = editor.presenter._seed_presenter
        view = editor.presenter.view

        # set default values in editor widgets
        view.widget_set_value('prop_type_combo', 'Seed')
        view.widget_set_value('prop_date_entry',
                              default_propagation_values['date'])
        view.widget_set_value('notes_textview',
                              default_propagation_values['notes'])
        for widget, attr in seed_presenter.widget_to_field_map.items():
            w = widgets[widget]
            if isinstance(w, Gtk.ComboBox) and w.get_child() and not w.get_model():
                widgets[widget].get_child().props.text = default_seed_values[attr]
            view.widget_set_value(widget, default_seed_values[attr])

        # update the editor, send the RESPONSE_OK signal and commit the changes
        update_gui()
        editor.handle_response(Gtk.ResponseType.OK)
        editor.presenter.cleanup()
        model_id = editor.model.id
        editor.commit_changes()
        editor.session.close()

        s = db.Session()
        propagation = s.query(Propagation).get(model_id)

        self.assertEqual(propagation.prop_type, 'Seed')
        # make sure the each value in default_seed_values matches the model
        for attr, expected in default_seed_values.items():
            v = getattr(propagation._seed, attr)
            if isinstance(v, datetime.date):
                format = prefs.prefs[prefs.date_format_pref]
                v = v.strftime(format)
                if isinstance(expected, datetime.date):
                    expected = expected.strftime(format)
            self.assertEqual(v, expected)

        for attr, expected in default_propagation_values.items():
            v = getattr(propagation, attr)
            self.assertEqual(v, expected)

        s.close()

    def test_seed_editor_load(self):
        loc = Location(name='name', code='code')
        plant = Plant(accession=self.accession, location=loc, code='1',
                      quantity=1)
        propagation = Propagation(**default_propagation_values)
        propagation.prop_type = 'Seed'
        propagation._seed = PropSeed(**default_seed_values)
        plant.propagations.append(propagation)

        editor = PropagationEditor(model=propagation)
        widgets = editor.presenter.view.widgets
        seed_presenter = editor.presenter._seed_presenter
        view = editor.presenter.view
        self.assertTrue(view is not None)

        update_gui()

        # check that the values loaded correctly from the model in the
        # editor widget
        def get_widget_text(w):
            if isinstance(w, Gtk.TextView):
                return w.get_buffer().props.text
            elif isinstance(w, Gtk.Entry):
                return w.props.text
            elif isinstance(w, Gtk.ComboBox) and w.get_child() and isinstance(w.get_child(), Gtk.Entry):
                return w.get_child().get_active_text()
            elif isinstance(w, Gtk.ComboBox):
                if w.get_model() is None or w.get_active_iter() is None:
                    return None
                return w.get_model()[w.get_active_iter()][0]
            else:
                raise ValueError('%s not supported' % type(w))

        # check that the values loaded correctly from the model in the
        # editor widget
        def get_widget_text(w):
            return utils.get_widget_value(w)

        # make sure the default values match the values in the widgets
        date_format = prefs.prefs[prefs.date_format_pref]
        for widget, attr in editor.presenter.widget_to_field_map.items():
            if not attr in default_propagation_values:
                continue
            default = default_propagation_values[attr]
            if isinstance(default, datetime.date):
                default = default.strftime(date_format)
            value = get_widget_text(widgets[widget])
            self.assertEqual(value, default)

        # check the default for the PropSeed and SeedPresenter
        for widget, attr in seed_presenter.widget_to_field_map.items():
            if not attr in default_seed_values:
                continue
            default = default_seed_values[attr]
            if isinstance(default, datetime.date):
                default = default.strftime(date_format)
            if isinstance(default, int):
                default = str(default)
            value = get_widget_text(widgets[widget])
            self.assertEqual(value, default)

    def test_editor(self):
        raise SkipTest('separate view from presenter, then test presenter')
        from bauble.plugins.garden.propagation import PropagationEditor
        propagation = Propagation()
        #propagation.prop_type = u'UnrootedCutting'
        propagation.accession = self.accession
        editor = PropagationEditor(model=propagation)
        propagation = editor.start()
        logger.debug(propagation)
        self.assertTrue(propagation.accession)


class AccessionEditorSpeciesMatchTests(GardenTestCase):

    def setUp(self):
        super().setUp()
        self.sp3 = Species(genus=self.genus, sp='inexistente')
        self.session.add_all([self.sp3])
        self.session.commit()

        class MockCompletion:
            def __init__(self, values):
                self.model = [[i] for i in values]

            def get_model(self):
                return self.model

        self.MockCompletion = MockCompletion
        self.completion = MockCompletion([self.species, self.sp2, self.sp3])

    def test_full_name(self):
        key = 'Echinocactus grusonii'
        species_match_func = AccessionEditorView.species_match_func
        self.assertTrue(species_match_func(self.completion, key, 0))
        self.assertFalse(species_match_func(self.completion, key, 1))
        self.assertFalse(species_match_func(self.completion, key, 2))

    def test_only_full_genus(self):
        key = 'Echinocactus'
        species_match_func = AccessionEditorView.species_match_func
        self.assertTrue(species_match_func(self.completion, key, 0))
        self.assertTrue(species_match_func(self.completion, key, 1))
        self.assertTrue(species_match_func(self.completion, key, 2))

    def test_only_partial_genus(self):
        key = 'Echinoc'
        species_match_func = AccessionEditorView.species_match_func
        self.assertTrue(species_match_func(self.completion, key, 0))
        self.assertTrue(species_match_func(self.completion, key, 1))
        self.assertTrue(species_match_func(self.completion, key, 2))

    def test_only_partial_binomial(self):
        key = 'Echi t'
        species_match_func = AccessionEditorView.species_match_func
        self.assertFalse(species_match_func(self.completion, key, 0))
        self.assertTrue(species_match_func(self.completion, key, 1))
        self.assertFalse(species_match_func(self.completion, key, 2))


class VoucherTests(GardenTestCase):

    def __init__(self, *args):
        super().__init__(*args)

    def setUp(self):
        super().setUp()
        self.accession = self.create(
            Accession, species=self.species, code='1')
        self.session.commit()

    def tearDown(self):
        super().tearDown()

    def test_voucher(self):
        voucher = Voucher(herbarium='ABC', code='1234567')
        voucher.accession = self.accession
        self.session.commit()
        voucher_id = voucher.id
        self.accession.vouchers.remove(voucher)
        self.session.commit()
        self.assertTrue(not self.session.query(Voucher).get(voucher_id))

        # test that if we set voucher.accession to None then the
        # voucher is deleted but not the accession
        voucher = Voucher(herbarium='ABC', code='1234567')
        voucher.accession = self.accession
        self.session.commit()
        voucher_id = voucher.id
        acc_id = voucher.accession.id
        voucher.accession = None
        self.session.commit()
        self.assertTrue(not self.session.query(Voucher).get(voucher_id))
        self.assertTrue(self.session.query(Accession).get(acc_id))


class SourceTests(GardenTestCase):

    def __init__(self, *args):
        super().__init__(*args)

    def setUp(self):
        super().setUp()
        self.accession = self.create(
            Accession, species=self.species, code='1')

    def tearDown(self):
        super().tearDown()

    def _make_prop(self, source):
        '''associate a seed Propagation to source

        we create a seed propagation that is referred to by both a PropSeed
        and a PropCutting, something that is not going to happen in the
        code, we're just being lazy.

        '''
        source.propagation = Propagation(prop_type='Seed')

        seed = PropSeed(**default_seed_values)
        seed.propagation = source.propagation
        cutting = PropCutting(**default_cutting_values)
        cutting.propagation = source.propagation
        self.session.commit()
        return (source.propagation.id,
                source.propagation._seed.id,
                source.propagation._cutting.id)

    def test_propagation(self):
        source = Source()
        self.accession.source = source
        prop_id, seed_id, cutting_id = self._make_prop(source)
        self.assertTrue(seed_id)
        self.assertTrue(cutting_id)
        self.assertTrue(prop_id)
        # make sure the propagation gets cleaned up when we set the
        # source.propagation attribute to None - and commit
        source.propagation = None
        self.session.commit()
        self.assertTrue(not self.session.query(PropSeed).get(seed_id))
        self.assertTrue(not self.session.query(PropCutting).get(cutting_id))
        self.assertTrue(not self.session.query(Propagation).get(prop_id))

    def test(self):
        # I consider this test a very good example of how NOT TO write unit
        # tests: it has a non-descriptive name, it does not state what it
        # tests, it uses a non-standard 'assert_' method, it tests several
        # things at the same time, it does not fit in a single page, it even
        # contains commented code, which distracts the reader by describing
        # things that do not happen. Dear Reader: you're welcome decyphering
        # it and rewriting it as unit tests. (Mario Frasca)
        source = Source()
        #self.assert_(hasattr(source, 'plant_propagation'))

        location = Location(code='1', name='site1')
        plant = Plant(accession=self.accession, location=location, code='1',
                      quantity=1)
        plant.propagations.append(Propagation(prop_type='Seed'))
        self.session.commit()

        source.source_detail = Contact()
        source.source_detail.name = 'name'
        source.sources_code = '1'
        source.collection = Collection(locale='locale')
        source.propagation = Propagation(prop_type='Seed')
        source.plant_propagation = plant.propagations[0]
        source.accession = self.accession  # test source's accession property
        self.session.commit()

        # test that cascading works properly
        source_detail_id = source.source_detail.id
        coll_id = source.collection.id
        prop_id = source.propagation.id
        plant_prop_id = source.plant_propagation.id
        self.accession.source = None  # tests the accessions source
        self.session.commit()

        # the Collection and Propagation should be
        # deleted since they are specific to the source
        self.assertTrue(not self.session.query(Collection).get(coll_id))
        self.assertTrue(not self.session.query(Propagation).get(prop_id))

        # the Contact and plant Propagation shouldn't be deleted
        # since they are independent of the source
        self.assertTrue(self.session.query(Propagation).get(plant_prop_id))
        self.assertTrue(self.session.query(Contact).get(source_detail_id))


class AccessionQualifiedTaxon(GardenTestCase):

    def __init__(self, *args):
        super().__init__(*args)

    def setUp(self):
        super().setUp()
        self.sp3 = Species(genus=self.genus, sp='grusonii',
                           infrasp1_rank='var.', infrasp1='albispinus')
        self.session.add(self.sp3)
        self.session.commit()
        self.ac1 = self.create(Accession, species=self.species, code='1')
        self.ac2 = self.create(Accession, species=self.sp3, code='2')

    def tearDown(self):
        super().tearDown()

    def test_species_str_plain(self):
        s = 'Echinocactus grusonii'
        sp_str = self.ac1.species_str()
        self.assertEqual(remove_zws(sp_str), s)

        s = '<i>Echinocactus</i> <i>grusonii</i> var. <i>albispinus</i>'
        sp_str = self.ac2.species_str(markup=True)
        self.assertEqual(remove_zws(sp_str), s)

    def test_species_str_without_zws(self):
        s = 'Echinocactus grusonii'
        sp_str = self.species.str(remove_zws=True)
        self.assertEqual(sp_str, s)
        s = 'Echinocactus grusonii var. albispinus'
        sp_str = self.sp3.str(remove_zws=True)
        self.assertEqual(sp_str, s)
        s = '<i>Echinocactus</i> <i>grusonii</i> var. <i>albispinus</i>'
        sp_str = self.sp3.str(remove_zws=True, markup=True)
        self.assertEqual(sp_str, s)

    def test_species_str_with_qualification_too_deep(self):
        self.ac1.id_qual = '?'
        self.ac1.id_qual_rank = 'infrasp'
        s = '<i>Echinocactus</i> <i>grusonii</i>'
        sp_str = self.ac1.species_str(markup=True)
        self.assertEqual(remove_zws(sp_str), s)
        s = 'Echinocactus grusonii'
        sp_str = self.ac1.species_str()
        self.assertEqual(sp_str, s)

        self.ac1.id_qual = 'cf.'
        self.ac1.id_qual_rank = 'infrasp'
        s = 'Echinocactus grusonii'
        sp_str = self.ac1.species_str()
        self.assertEqual(remove_zws(sp_str), s)

    def test_species_str_with_qualification_correct(self):
        self.ac1.id_qual = '?'
        self.ac1.id_qual_rank = 'sp'
        s = '<i>Echinocactus</i> ? <i>grusonii</i>'
        sp_str = self.ac1.species_str(markup=True)
        self.assertEqual(remove_zws(sp_str), s)

        # aff. before qualified epithet
        self.ac1.id_qual = 'aff.'
        self.ac1.id_qual_rank = 'genus'
        s = 'aff. <i>Echinocactus</i> <i>grusonii</i>'
        sp_str = self.ac1.species_str(markup=True)
        self.assertEqual(remove_zws(sp_str), s)

        self.ac1.id_qual_rank = 'sp'
        s = '<i>Echinocactus</i> aff. <i>grusonii</i>'
        sp_str = self.ac1.species_str(markup=True)
        self.assertEqual(remove_zws(sp_str), s)

        self.ac2.id_qual = 'aff.'
        self.ac2.id_qual_rank = 'infrasp'
        s = '<i>Echinocactus</i> <i>grusonii</i> aff. var. <i>albispinus</i>'
        sp_str = self.ac2.species_str(markup=True)
        self.assertEqual(remove_zws(sp_str), s)

        self.ac1.id_qual = 'cf.'
        self.ac1.id_qual_rank = 'sp'
        s = '<i>Echinocactus</i> cf. <i>grusonii</i>'
        sp_str = self.ac1.species_str(markup=True)
        self.assertEqual(remove_zws(sp_str), s)

        self.ac1.id_qual = 'aff.'
        self.ac1.id_qual_rank = 'sp'
        s = 'Echinocactus aff. grusonii'
        sp_str = self.ac1.species_str()
        self.assertEqual(remove_zws(sp_str), s)

        self.ac1.id_qual = 'forsan'
        self.ac1.id_qual_rank = 'sp'
        s = 'Echinocactus forsan grusonii'
        sp_str = self.ac1.species_str()
        self.assertEqual(remove_zws(sp_str), s)

        ## add cultivar to species and refer to it as cf.
        self.ac1.species.set_infrasp(1, 'cv.', 'Cultivar')
        self.ac1.id_qual = 'cf.'
        self.ac1.id_qual_rank = 'infrasp'
        s = "Echinocactus grusonii cf. 'Cultivar'"
        sp_str = self.ac1.species_str()
        self.assertEqual(remove_zws(sp_str), s)

    def test_species_str_qualification_appended(self):
        # previously, if the id_qual is set but the id_qual_rank isn't then
        # we would get an error. now we just log a warning and append it
        #
        # self.ac1.id_qual = 'aff.'
        # self.ac1.id_qual_rank = None
        # self.assertRaises(CheckConditionError, self.ac1.species_str)

        self.ac1.id_qual = None
        self.ac1.id_qual = '?'
        s = 'Echinocactus grusonii (?)'
        sp_str = self.ac1.species_str()
        self.assertEqual(remove_zws(sp_str), s)

        # species.infrasp is still none but these just get pasted on
        # the end so it doesn't matter
        self.ac1.id_qual = 'incorrect'
        self.ac1.id_qual_rank = 'infrasp'
        s = 'Echinocactus grusonii (incorrect)'
        sp_str = self.ac1.species_str()
        self.assertEqual(remove_zws(sp_str), s)

        self.ac1.id_qual = 'incorrect'
        self.ac1.id_qual_rank = 'sp'
        s = '<i>Echinocactus</i> <i>grusonii</i> (incorrect)'
        sp_str = self.ac1.species_str(markup=True)
        self.assertEqual(remove_zws(sp_str), s)

    def test_species_str_is_cached(self):
        self.ac1.species.set_infrasp(1, 'cv.', 'Cultivar')
        self.ac1.id_qual = 'cf.'
        self.ac1.id_qual_rank = 'infrasp'
        s = "Echinocactus grusonii cf. 'Cultivar'"
        sp_str = self.ac1.species_str()
        self.assertEqual(remove_zws(sp_str), s)

        # have to commit because the cached string won't be returned
        # on dirty species
        self.session.commit()
        s2 = self.ac1.species_str()
        self.assertEqual(id(sp_str), id(s2))

    def test_species_str_be_specific_in_infraspecific(self):
        'be specific qualifying infraspecific identification - still unused'
        ## add  to species with variety and refer to it as cf.
        self.sp3.set_infrasp(2, 'cv.', 'Cultivar')
        self.ac2.id_qual = 'cf.'
        self.ac2.id_qual_rank = 'cv.'
        s = "Echinocactus grusonii var. albispinus cf. 'Cultivar'"
        sp_str = self.ac2.species_str()
        self.assertEqual(remove_zws(sp_str), s)

        self.ac2.id_qual = 'cf.'
        self.ac2.id_qual_rank = 'var.'
        s = "Echinocactus grusonii var. cf. albispinus 'Cultivar'"
        sp_str = self.ac2.species_str()
        self.assertEqual(remove_zws(sp_str), s)

    def test_species_str_unsorted_infraspecific(self):
        'be specific qualifying infraspecific identification - still unused'
        ## add  to species with variety and refer to it as cf.
        self.sp3.set_infrasp(1, 'var.', 'aizoon')
        self.sp3.set_infrasp(2, 'subvar.', 'brevifolia')
        self.sp3.set_infrasp(3, 'f.', 'multicaulis')
        self.ac2.id_qual = 'cf.'
        self.ac2.id_qual_rank = 'f.'
        #s = u"Echinocactus grusonii f. cf. multicaulis"
        sp_str = self.ac2.species_str()
        #self.assertEquals(remove_zws(sp_str), s)
        self.assertTrue(sp_str.endswith("f. cf. multicaulis"))

        self.sp3.set_infrasp(4, 'subf.', 'surculosa')
        self.ac2.id_qual = 'cf.'
        self.ac2.id_qual_rank = 'subf.'
        #s = u"Echinocactus grusonii subf. cf. surculosa"
        sp_str = self.ac2.species_str()
        #self.assertEquals(remove_zws(sp_str), s)
        self.assertTrue(sp_str.endswith("subf. cf. surculosa"))


class AccessionTests(GardenTestCase):

    def __init__(self, *args):
        super().__init__(*args)

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_delete(self):
        acc = self.create(Accession, species=self.species, code='1')
        plant = self.create(Plant, accession=acc, quantity=1,
                            location=Location(name='site', code='STE'),
                            code='1')
        self.session.commit()

        # test that the plant is deleted after being orphaned
        plant_id = plant.id
        self.session.delete(acc)
        self.session.commit()
        self.assertTrue(not self.session.query(Plant).get(plant_id))

    def test_constraints(self):
        acc = Accession(species=self.species, code='1')
        self.session.add(acc)
        self.session.commit()

        # test that accession.code is unique
        acc = Accession(species=self.species, code='1')
        self.session.add(acc)
        self.assertRaises(IntegrityError, self.session.commit)

    def test_accession_source_editor(self, accession=None):
        ## create an accession, a location, a plant
        parent = self.create(Accession, species=self.species, code='parent',
                             quantity_recvd=1)
        plant = self.create(Plant, accession=parent, quantity=1,
                            location=Location(name='site', code='STE'),
                            code='1')
        ## create a propagation without a related seed/cutting
        prop = self.create(Propagation, prop_type='Seed')
        plant.propagations.append(prop)
        ## commit all the above to the database
        self.session.commit()
        self.assertTrue(prop.id > 0)  # we got a valid id after the commit
        plant_prop_id = prop.id

        acc = Accession(code='code', species=self.species, quantity_recvd=2)
        self.editor = AccessionEditor(acc)
        # normally called by editor.presenter.start() but we don't call it here
        self.editor.presenter.source_presenter.start()
        widgets = self.editor.presenter.view.widgets
        update_gui()

        # set the date so the presenter will be "dirty"
        widgets.acc_date_recvd_entry.props.text = utils.today_str()

        # set the source type as "Garden Propagation"
        widgets.acc_source_comboentry.get_child().props.text = \
            SourcePresenter.garden_prop_str
        self.assertTrue(not self.editor.presenter.problems)

        # set the source plant
        widgets.source_prop_plant_entry.props.text = str(plant)
        logger.debug('about to update the gui')
        update_gui()
        comp = widgets.source_prop_plant_entry.get_completion()
        comp.emit('match-selected', comp.get_model(),
                  comp.get_model().get_iter_first())

        logger.debug('about to update the gui')
        update_gui()  # ensures idle callback is called

        # assert that the propagations were added to the treeview
        treeview = widgets.source_prop_treeview
        self.assertTrue(treeview.get_model())

        # select the first/only propagation in the treeview
        toggle_cell = widgets.prop_toggle_cell.emit('toggled', 0)
        self.assertTrue(toggle_cell is None)

        # commit the changes and cleanup
        self.editor.handle_response(Gtk.ResponseType.OK)
        self.editor.session.close()

        # open a separate session and make sure everything committed
        session = db.Session()
        acc = session.query(Accession).filter_by(code='code')[0]
        self.assertTrue(acc is not None)
        logger.debug(acc.id)
        parent = session.query(Accession).filter_by(code='parent')[0]
        self.assertTrue(parent is not None)
        logger.debug(parent.id)
        logger.debug("acc plants : %s" % [str(i) for i in acc.plants])
        logger.debug("parent plants : %s" % [str(i) for i in parent.plants])
        logger.debug(acc.source.__dict__)
        self.assertEqual(acc.source.plant_propagation_id, plant_prop_id)

    def test_accession_editor(self):
        raise SkipTest('Problem cannot be found in presenter')
        acc = Accession(code='code', species=self.species)
        self.editor = AccessionEditor(acc)
        update_gui()

        widgets = self.editor.presenter.view.widgets
        # make sure there is a problem if the species entry text isn't
        # a species string
        widgets.acc_species_entry.set_text('asdasd')
        self.assertTrue(self.editor.presenter.problems)

        # make sure the problem is removed if the species entry text
        # is set to a species string

        # fill in the completions
        widgets.acc_species_entry.set_text(str(self.species)[0:3])
        update_gui()  # ensures idle callback is called to add completions
        # set the fill string which should match from completions
        widgets.acc_species_entry.set_text(str(self.species))
        assert not self.editor.presenter.problems, \
            self.editor.presenter.problems

        # commit the changes and cleanup
        self.editor.model.name = 'asda'
        from gi.repository import Gtk
        self.editor.handle_response(Gtk.ResponseType.OK)
        self.editor.session.close()

    def test_editor(self):
        raise SkipTest('separate view from presenter, then test presenter')
        #donor = self.create(Donor, name=u'test')
        sp2 = Species(genus=self.genus, sp='species')
        sp2.synonyms.append(self.species)
        self.session.add(sp2)
        self.session.commit()
        # import datetime again since sometimes i get an weird error
        import datetime
        acc_code = '%s%s1' % (
            datetime.date.today().year, Plant.get_delimiter())
        acc = self.create(Accession, species=self.species, code=acc_code)
        voucher = Voucher(herbarium='abcd', code='123')
        acc.vouchers.append(voucher)

        def mem(size="rss"):
            """Generalization; memory sizes: rss, rsz, vsz."""
            import os
            return int(os.popen('ps -p %d -o %s | tail -1' %
                       (os.getpid(), size)).read())

        # add verificaiton
        ver = Verification()
        ver.verifier = 'me'
        ver.date = datetime.date.today()
        ver.prev_species = self.species
        ver.species = self.species
        ver.level = 1
        acc.verifications.append(ver)

        location = Location(name='loc1', code='loc1')
        plant = Plant(accession=acc, location=location, code='1', quantity=1)
        prop = Propagation(prop_type='Seed')
        seed = PropSeed(**default_seed_values)
        seed.propagation = prop
        plant.propagations.append(prop)

        source_detail = Contact(name='Test Source',
                                     source_type='Expedition')
        source = Source(sources_code='22')
        source.source_detail = source_detail
        acc.source = source

        self.session.commit()

        self.editor = AccessionEditor(model=acc)
        try:
            self.editor.start()
        except Exception as e:
            import traceback
            logger.debug(traceback.format_exc(0))
            logger.debug(e)

    def test_remove_callback_no_plants_no_confirm(self):
        # T_0
        added = []
        added.append(Family(family='Caricaceae'))
        added.append(Genus(epithet='Carica', family=added[-1]))
        added.append(Species(epithet='papaya', genus=added[-1]))
        added.append(Accession(code='010101', species=added[-1]))
        sp, acc = added[-2:]
        self.session.add_all(added)
        self.session.flush()
        self.invoked = []

        # action
        utils.yes_no_dialog = partial(mockfunc, name='yes_no_dialog', caller=self, result=False)
        utils.message_details_dialog = partial(mockfunc, name='message_details_dialog', caller=self)
        from bauble.plugins.garden.accession import remove_callback
        result = remove_callback([acc])
        self.session.flush()

        # effect
        self.assertFalse('message_details_dialog' in [f for (f, m) in self.invoked])
        print(self.invoked)
        self.assertTrue(('yes_no_dialog', 'Are you sure you want to remove accession <b>010101</b>?')
                        in self.invoked)
        self.assertEqual(result, None)
        q = self.session.query(Accession).filter_by(code='010101', species=sp)
        matching = q.all()
        self.assertEqual(matching, [acc])

    def test_remove_callback_no_accessions_confirm(self):
        # T_0
        added = []
        added.append(Family(family='Caricaceae'))
        added.append(Genus(epithet='Carica', family=added[-1]))
        added.append(Species(epithet='papaya', genus=added[-1]))
        added.append(Accession(code='010101', species=added[-1]))
        sp, acc = added[-2:]
        self.session.add_all(added)
        self.session.flush()
        self.invoked = []

        # action
        utils.yes_no_dialog = partial(
            mockfunc, name='yes_no_dialog', caller=self, result=True)
        utils.message_details_dialog = partial(
            mockfunc, name='message_details_dialog', caller=self)
        from bauble.plugins.garden.accession import remove_callback
        result = remove_callback([acc])
        self.session.flush()

        # effect
        print(self.invoked)
        self.assertFalse('message_details_dialog' in
                         [f for (f, m) in self.invoked])
        self.assertTrue(('yes_no_dialog', 'Are you sure you want to remove accession <b>010101</b>?')
                        in self.invoked)

        self.assertEqual(result, True)
        q = self.session.query(Species).filter_by(sp="Carica")
        matching = q.all()
        self.assertEqual(matching, [])

    def test_remove_callback_with_accessions_cant_cascade(self):
        # T_0
        added = []
        added.append(Location(code='INV99'))
        added.append(Family(family='Caricaceae'))
        added.append(Genus(epithet='Carica', family=added[-1]))
        added.append(Species(epithet='papaya', genus=added[-1]))
        added.append(Accession(code='010101', species=added[-1]))
        added.append(Plant(code='1', accession=added[-1], quantity=1, location=added[0]))
        sp, acc, plant = added[-3:]
        self.session.add_all(added)
        self.session.flush()
        self.invoked = []

        # action
        utils.yes_no_dialog = partial(mockfunc, name='yes_no_dialog', caller=self, result=True)
        utils.message_dialog = partial(mockfunc, name='message_dialog', caller=self, result=True)
        utils.message_details_dialog = partial(mockfunc, name='message_details_dialog', caller=self)
        from bauble.plugins.garden.accession import remove_callback
        result = remove_callback([acc])
        self.session.flush()

        # effect
        print(self.invoked)
        self.assertFalse('message_details_dialog' in
                         [f for (f, m) in self.invoked])
        self.assertTrue(('message_dialog', '1 plants depend on this accession: <b>010101.1</b>\n\n'
                         'You cannot remove an accession with plants.')
                        in self.invoked)
        q = self.session.query(Accession).filter_by(species=sp)
        matching = q.all()
        self.assertEqual(matching, [acc])
        q = self.session.query(Plant).filter_by(accession=acc)
        matching = q.all()
        self.assertEqual(matching, [plant])


class VerificationTests(GardenTestCase):

    def __init__(self, *args):
        super().__init__(*args)

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_verifications(self):
        acc = self.create(Accession, species=self.species, code='1')
        self.session.add(acc)
        self.session.commit()

        ver = Verification()
        ver.verifier = 'me'
        ver.date = datetime.date.today()
        ver.level = 1
        ver.species = acc.species
        ver.prev_species = acc.species
        acc.verifications.append(ver)
        self.session.commit()
        self.assertTrue(ver in acc.verifications)
        self.assertTrue(ver in self.session)


class LocationTests(GardenTestCase):

    def __init__(self, *args):
        super().__init__(*args)

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_location_editor(self):
        loc = self.create(Location, name='some site', code='STE')
        self.session.commit()
        editor = LocationEditor(model=loc)
        update_gui()
        widgets = editor.presenter.view.widgets

        # test that the accept buttons are NOT sensitive since nothing
        # has changed and that the text entries and model are the same
        self.assertEqual(widgets.loc_name_entry.get_text(), loc.name)
        self.assertEqual(widgets.loc_code_entry.get_text(), loc.code)
        self.assertFalse(widgets.loc_ok_button.props.sensitive)
        self.assertFalse(widgets.loc_next_button.props.sensitive)

        # test the accept buttons become sensitive when the name entry
        # is changed
        widgets.loc_name_entry.set_text('something')
        update_gui()
        self.assertTrue(widgets.loc_ok_button.props.sensitive)
        self.assertTrue(widgets.loc_ok_and_add_button.props.sensitive)
        self.assertTrue(widgets.loc_next_button.props.sensitive)

        # test the accept buttons become NOT sensitive when the code
        # entry is empty since this is a required field
        widgets.loc_code_entry.set_text('')
        update_gui()
        self.assertFalse(widgets.loc_ok_button.props.sensitive)
        self.assertFalse(widgets.loc_ok_and_add_button.props.sensitive)
        self.assertFalse(widgets.loc_next_button.props.sensitive)

        # test the accept buttons aren't sensitive from setting the textview
        buff = Gtk.TextBuffer()
        buff.set_text('saasodmadomad')
        widgets.loc_desc_textview.set_buffer(buff)
        self.assertFalse(widgets.loc_ok_button.props.sensitive)
        self.assertFalse(widgets.loc_ok_and_add_button.props.sensitive)
        self.assertFalse(widgets.loc_next_button.props.sensitive)

        # commit the changes and cleanup
        editor.model.name = editor.model.code = 'asda'
        editor.handle_response(Gtk.ResponseType.OK)
        editor.session.close()
        editor.presenter.cleanup()
        return

    def test_deleting_editor(self):
        raise SkipTest('TODO: what is this garbage collection testing?')
        loc = self.create(Location, name='some site', code='STE')
        editor = LocationEditor(model=loc)

        del editor
        self.assertEqual(utils.gc_objects_by_type('LocationEditor'), [],
                          'LocationEditor not deleted')
        self.assertEqual(
            utils.gc_objects_by_type('LocationEditorPresenter'), [],
            'LocationEditorPresenter not deleted')
        self.assertEqual(utils.gc_objects_by_type('LocationEditorView'), [],
                          'LocationEditorView not deleted')


class CollectionTests(GardenTestCase):

    def __init__(self, *args):
        super().__init__(*args)

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_collection_search_view_markup_pair(self):
        acc = Accession(code='2001.0002', species=self.species)
        acc.source = Source()
        collection = Collection(locale='some location')
        acc.source.collection = collection
        self.assertEqual(
            collection.search_view_markup_pair(),
            ('2001.0002 - <small>Echinocactus grusonii</small>',
             'Collection at some location'))


class InstitutionTests(GardenTestCase):

    def test_init__9_props(self):
        o = Institution()
        o.name = 'Ghini'
        o.write()
        fields = self.session.query(BaubleMeta).filter(
            utils.ilike(BaubleMeta.name, 'inst_%')).all()
        self.assertEqual(len(fields), 13)  # 13 props define the institution

    def test_init__one_institution(self):
        o = Institution()
        o.name = 'Fictive'
        o.write()
        o.name = 'Ghini'
        o.write()
        fieldObjects = self.session.query(BaubleMeta).filter(
            utils.ilike(BaubleMeta.name, 'inst_%')).all()
        self.assertEqual(len(fieldObjects), 13)

    def test_init__always_initialized(self):
        o = Institution()
        o.name = 'Fictive'
        o.write()
        u = Institution()
        self.assertEqual(u.name, 'Fictive')
        o.name = 'Ghini'
        o.write()
        u = Institution()
        self.assertEqual(u.name, 'Ghini')

    def test_init__has_all_attributes(self):
        o = Institution()
        for a in ('name', 'abbreviation', 'code', 'contact',
                  'technical_contact', 'email', 'tel', 'fax', 'address'):
            self.assertTrue(hasattr(o, a))

    def test_write__None_stays_None(self):
        o = Institution()
        o.name = 'Ghini'
        o.email = 'bauble@anche.no'
        o.write()
        fieldObjects = self.session.query(BaubleMeta).filter(
            utils.ilike(BaubleMeta.name, 'inst_%')).all()
        fields = dict((i.name[5:], i.value)
                      for i in fieldObjects
                      if i.value is not None)
        self.assertEqual(fields['name'], 'Ghini')
        self.assertEqual(fields['email'], 'bauble@anche.no')
        self.assertEqual(len(fields), 2)


class InstitutionPresenterTests(GardenTestCase):

    def test_can_create_presenter(self):
        from bauble.editor import MockView
        view = MockView()
        o = Institution()
        print(dir(o))
        presenter = InstitutionPresenter(o, view)
        self.assertEqual(presenter.view, view)

    def test_empty_name_is_a_problem(self):
        from bauble.editor import MockView
        view = MockView()
        o = Institution()
        o.name = ''
        InstitutionPresenter(o, view)
        self.assertTrue('add_box' in view.invoked)
        self.assertEqual(len(view.boxes), 1)

    def test_initially_empty_name_then_specified_is_ok(self):
        from bauble.editor import MockView
        view = MockView()
        o = Institution()
        o.name = ''
        presenter = InstitutionPresenter(o, view)
        presenter.view.widget_set_value('inst_name', 'bauble')
        presenter.on_non_empty_text_entry_changed('inst_name')
        self.assertTrue('remove_box' in view.invoked)
        self.assertEqual(o.name, 'bauble')
        self.assertEqual(presenter.view.boxes, set())

    def test_no_email_means_no_registering(self):
        from bauble.editor import MockView
        view = MockView(sensitive={'inst_register': None,
                                   'inst_ok': None})
        o = Institution()
        o.name = 'bauble'
        o.email = ''
        print(dir(o))
        InstitutionPresenter(o, view)
        self.assertFalse(view.widget_get_sensitive('inst_register'))

    def test_invalid_email_means_no_registering(self):
        from bauble.editor import MockView
        view = MockView(sensitive={'inst_register': None,
                                   'inst_ok': None})
        o = Institution()
        o.name = 'bauble'
        o.email = 'mario'
        print(dir(o))
        InstitutionPresenter(o, view)
        self.assertFalse(view.widget_get_sensitive('inst_register'))

    def test_no_email_means_can_register(self):
        from bauble.editor import MockView
        view = MockView(sensitive={'inst_register': None,
                                   'inst_ok': None})
        o = Institution()
        o.name = 'bauble'
        o.email = 'bauble@anche.no'
        InstitutionPresenter(o, view)
        self.assertTrue(view.widget_get_sensitive('inst_register'))

    def test_when_user_registers_info_is_logged(self):
        from bauble.utils import desktop
        from bauble.test import mockfunc
        from functools import partial
        self.invoked = []
        desktop.open = partial(mockfunc, name='desktop.open', caller=self)
        from bauble.editor import MockView
        view = MockView(sensitive={'inst_register': None,
                                   'inst_ok': None})
        o = Institution()
        p = InstitutionPresenter(o, view)
        p.on_inst_register_clicked()
        print(self.handler.messages['bauble.registrations']['info'][0])
        target = [('fax', None), ('address', None), ('name', ''), 
                                  ('contact', None), ('technical_contact', None), ('geo_diameter', None), 
                                  ('abbreviation', None), ('code', None), ('geo_longitude', None), 
                                  ('tel', None), ('email', ''), ('geo_latitude', None)]
        for i in eval(self.handler.messages['bauble.registrations']['info'][0]):
            self.assertTrue(i in target, i)

# latitude: deg[0-90], min[0-59], sec[0-59]
# longitude: deg[0-180], min[0-59], sec[0-59]

ALLOWED_DECIMAL_ERROR = 5
THRESHOLD = .01

# indexs into conversion_test_date
DMS = 0  # DMS
DEG_MIN_DEC = 1  # Deg with minutes decimal
DEG_DEC = 2  # Degrees decimal
UTM = 3  # Datum(wgs84/nad83 or nad27), UTM Zone, Easting, Northing

# decimal points to accuracy in decimal degrees
# 1 +/- 8000m
# 2 +/- 800m
# 3 +/- 80m
# 4 +/- 8m
# 5 +/- 0.8m
# 6 +/- 0.08m

from decimal import Decimal
dec = Decimal
conversion_test_data = (((('N', 17, 21, dec(59)), ('W', 89, 1, 41)),  # dms
                         ((dec(17), dec('21.98333333')), (dec(-89), dec('1.68333333'))),  # deg min_dec
                         (dec('17.366389'), dec('-89.028056')),  # dec deg
                         (('wgs84', 16, 284513, 1921226))),  # utm
                        \
                        ((('S', 50, 19, dec('32.59')), ('W', 74, 2, dec('11.6'))),  # dms
                         ((dec(-50), dec('19.543166')), (dec(-74), dec('2.193333'))),  # deg min_dec
                         (dec('-50.325719'), dec('-74.036556')),  # dec deg
                         (('wgs84', 18, 568579, 568579)),
                         (('nad27', 18, 568581, 4424928))),
                        \
                        ((('N', 9, 0, dec('4.593384')), ('W', 78, 3, dec('28.527984'))),
                         ((9, dec('0.0765564')), (-78, dec('3.4754664'))),
                         (dec('9.00127594'), dec('-78.05792444'))),
                        \
                        ((('N', 49, 10, 28), ('W', 121, 40, 39)),
                         ((49, dec('10.470')), (-121, dec('40.650'))),
                         (dec('49.174444'), dec('-121.6775')))
                        )


parse_lat_lon_data = ((('N', '17 21 59'), dec('17.366389')),
                      (('N', '17 21.983333'), dec('17.366389')),
                      (('N', '17.03656'), dec('17.03656')),
                      (('W', '89 1 41'), dec('-89.028056')),
                      (('W', '89 1.68333333'), dec('-89.028056')),
                      (('W', '-89 1.68333333'), dec('-89.028056')),
                      (('E', '121 40 39'), dec('121.6775')))


class DMSConversionTests(TestCase):

    # test coordinate conversions
    def test_dms_to_decimal(self):
        # test converting DMS to degrees decimal
        ALLOWED_ERROR = 6
        for data_set in conversion_test_data:
            dms_data = data_set[DMS]
            dec_data = data_set[DEG_DEC]
            lat_dec = dms_to_decimal(*dms_data[0])
            lon_dec = dms_to_decimal(*dms_data[1])
            self.assertAlmostEqual(lat_dec, dec_data[0], ALLOWED_ERROR)
            self.assertAlmostEqual(lon_dec, dec_data[1], ALLOWED_ERROR)

    def test_decimal_to_dms(self):
        # test converting degrees decimal to dms, allow a certain
        # amount of error in the seconds
        ALLOWABLE_ERROR = 2
        for data_set in conversion_test_data:
            dms_data = data_set[DMS]
            dec_data = data_set[DEG_DEC]

            # convert to DMS
            lat_dms = latitude_to_dms(dec_data[0])
            self.assertEqual(lat_dms[0:2], dms_data[0][0:2])
            # test seconds with allowable error
            self.assertAlmostEqual(lat_dms[3], dms_data[0][3], ALLOWABLE_ERROR)

            lon_dms = longitude_to_dms(dec_data[1])
            self.assertEqual(lon_dms[0:2], dms_data[1][0:2])
            # test seconds with allowable error
            self.assertAlmostEqual(lon_dms[3], dms_data[1][3], ALLOWABLE_ERROR)

    def test_parse_lat_lon(self):
        parse = CollectionPresenter._parse_lat_lon
        for data, dec in parse_lat_lon_data:
            result = parse(*data)
            self.assertEqual(result, dec)


class FromAndToDictTest(GardenTestCase):

    def test_add_accession_at_species_rank(self):
        acc = Accession.retrieve_or_create(
            self.session, {'code': '010203',
                           'rank': 'species',
                           'taxon': 'Echinocactus grusonii'})
        self.assertEqual(acc.species, self.species)

    def test_add_accession_at_genus_rank(self):
        acc = Accession.retrieve_or_create(
            self.session, {'code': '010203',
                           'rank': 'genus',
                           'taxon': 'Echinocactus'})
        self.assertEqual(acc.species.genus, self.genus)

    def test_add_plant(self):
        acc = Accession.retrieve_or_create(
            self.session, {'code': '010203',
                           'rank': 'species',
                           'taxon': 'Echinocactus grusonii'})
        plt = Plant.retrieve_or_create(
            self.session, {'accession': '010203',
                           'code': '1',
                           'location': 'wrong one',
                           'quantity': 1})
        self.assertEqual(plt.accession, acc)

    def test_set_create_timestamp_european(self):
        from datetime import datetime
        ## insert an object with a timestamp
        Location.retrieve_or_create(
            self.session, {'code': '1',
                           '_created': '10/12/2001'})
        ## retrieve same object from other session
        session = db.Session()
        loc = Location.retrieve_or_create(session, {'code': '1', })
        self.assertEqual(loc._created, datetime(2001, 12, 10))

    def test_set_create_timestamp_iso8601(self):
        from datetime import datetime
        ## insert an object with a timestamp
        Location.retrieve_or_create(
            self.session, {'code': '1',
                           '_created': '2001-12-10'})
        ## retrieve same object from other session
        session = db.Session()
        loc = Location.retrieve_or_create(session, {'code': '1', })
        self.assertEqual(loc._created, datetime(2001, 12, 10))


class FromAndToDict_create_update_test(GardenTestCase):
    "test the create and update fields in retrieve_or_create"

    def setUp(self):
        GardenTestCase.setUp(self)
        acc = Accession(species=self.species, code='010203')
        loc = Location(code='123')
        loc2 = Location(code='213')
        plt = Plant(accession=acc, code='1', quantity=1, location=loc)
        self.session.add_all([acc, loc, loc2, plt])
        self.session.commit()

    def test_accession_nocreate_noupdate_noexisting(self):
        # do not create if not existing
        acc = Accession.retrieve_or_create(
            self.session, {'code': '030201',
                           'rank': 'species',
                           'taxon': 'Echinocactus texelensis'},
            create=False)
        self.assertEqual(acc, None)

    def test_accession_nocreate_noupdateeq_existing(self):
        ## retrieve same object, we only give the keys
        acc = Accession.retrieve_or_create(
            self.session, {'code': '010203'},
            create=False, update=False)
        self.assertTrue(acc is not None)
        self.assertEqual(acc.species, self.species)

    def test_accession_nocreate_noupdatediff_existing(self):
        ## do not update object with new data
        acc = Accession.retrieve_or_create(
            self.session, {'code': '010203',
                           'rank': 'species',
                           'taxon': 'Echinocactus texelensis'},
            create=False, update=False)
        self.assertEqual(acc.species, self.species)

    def test_accession_nocreate_updatediff_existing(self):
        ## update object in self.session
        acc = Accession.retrieve_or_create(
            self.session, {'code': '010203',
                           'rank': 'species',
                           'taxon': 'Echinocactus texelensis'},
            create=False, update=True)
        self.assertEqual(acc.species, self.sp2)

    def test_plant_nocreate_noupdate_noexisting(self):
        # do not create if not existing
        plt = Plant.retrieve_or_create(
            self.session, {'accession': '010203',
                           'code': '2',
                           'quantity': 1,
                           'location': '123'},
            create=False)
        self.assertEqual(plt, None)

    def test_plant_nocreate_noupdateeq_existing(self):
        ## retrieve same object, we only give the keys
        plt = Plant.retrieve_or_create(
            self.session, {'accession': '010203',
                           'code': '1'},
            create=False, update=False)
        self.assertTrue(plt is not None)
        self.assertEqual(plt.quantity, 1)

    def test_plant_nocreate_noupdatediff_existing(self):
        ## do not update object with new data
        plt = Plant.retrieve_or_create(
            self.session, {'accession': '010203',
                           'code': '1',
                           'quantity': 3},
            create=False, update=False)
        self.assertTrue(plt is not None)
        self.assertEqual(plt.quantity, 1)

    def test_plant_nocreate_updatediff_existing(self):
        ## update object in self.session
        plt = Plant.retrieve_or_create(
            self.session, {'accession': '010203',
                           'code': '1',
                           'quantity': 3},
            create=False, update=True)
        self.assertTrue(plt is not None)
        self.assertEqual(plt.quantity, 3)
        self.assertEqual(plt.location.code, '123')
        plt = Plant.retrieve_or_create(
            self.session, {'accession': '010203',
                           'code': '1',
                           'location': '213'},
            create=False, update=True)
        self.assertTrue(plt is not None)
        self.assertTrue(plt.location is not None)
        self.assertEqual(plt.location.code, '213')


class AccessionNotesSerializeTest(GardenTestCase):
    ## for the sake of retrieve_or_update, we consider as keys:
    ## accession, category, and date.

    def setUp(self):
        GardenTestCase.setUp(self)
        acc = Accession(species=self.species, code='010203')
        self.session.add(acc)
        self.session.flush()
        note1 = AccessionNote(accession=acc, category='factura',
                              date='2014-01-01', note='992288')
        note2 = AccessionNote(accession=acc, category='foto',
                              date='2014-01-01', note='file://')
        self.session.add_all([note1, note2])
        self.session.commit()

    def test_accession_note_nocreate_noupdate_noexisting(self):
        # do not create if not existing
        obj = AccessionNote.retrieve_or_create(
            self.session, {'object': 'accession_note',
                           'accession': '010203',
                           'category': 'newcat',
                           'date': '2014-01-01',
                           },
            create=False)
        self.assertTrue(obj is None)

    def test_accession_note_nocreate_noupdateeq_existing(self):
        ## retrieve same object, we only give the keys
        obj = AccessionNote.retrieve_or_create(
            self.session, {'object': 'accession_note',
                           'accession': '010203',
                           'category': 'foto',
                           'date': '2014-01-01',
                           },
            create=False)
        self.assertTrue(obj is not None)
        self.assertEqual(obj.note, "file://")

    def test_accession_note_nocreate_noupdatediff_existing(self):
        ## do not update object with new data
        obj = AccessionNote.retrieve_or_create(
            self.session, {'object': 'accession_note',
                           'accession': '010203',
                           'category': 'foto',
                           'date': '2014-01-01',
                           'note': 'url://'
                           },
            create=False, update=False)
        self.assertTrue(obj is not None)
        self.assertEqual(obj.note, "file://")

    def test_accession_note_nocreate_updatediff_existing(self):
        ## update object in self.session
        obj = AccessionNote.retrieve_or_create(
            self.session, {'object': 'accession_note',
                           'accession': '010203',
                           'category': 'foto',
                           'date': '2014-01-01',
                           'note': 'url://'
                           },
            create=False, update=True)
        self.assertTrue(obj is not None)
        self.assertEqual(obj.note, "url://")

import bauble.search as search


class PlantSearchTest(GardenTestCase):
    def __init__(self, *args):
        super().__init__(*args)

    def setUp(self):
        super().setUp()
        setUp_data()

    def test_searchbyplantcode_unquoted(self):
        mapper_search = search.get_strategy('PlantSearch')

        results = mapper_search.search('1.1.1', self.session)
        self.assertEqual(len(results), 1)
        self.assertEqual(self.handler.messages['bauble.plugins.garden.plant']['debug'][0],
            'text is not quoted, should strategy apply?')
        p = results.pop()
        ex = self.session.query(Plant).filter(Plant.id == 1).first()
        self.assertEqual(p, ex)
        results = mapper_search.search('1.2.1', self.session)
        logger.debug(results)
        self.assertEqual(len(results), 1)
        p = results.pop()
        ex = self.session.query(Plant).filter(Plant.id == 2).first()
        self.assertEqual(p, ex)
        results = mapper_search.search('1.2.2', self.session)
        self.assertEqual(len(results), 1)
        p = results.pop()
        ex = self.session.query(Plant).filter(Plant.id == 3).first()
        self.assertEqual(p, ex)

    def test_searchbyplantcode_quoted(self):
        mapper_search = search.get_strategy('PlantSearch')

        results = mapper_search.search('"1.1.1"', self.session)
        self.assertEqual(len(results), 1)
        p = results.pop()
        ex = self.session.query(Plant).filter(Plant.id == 1).first()
        self.assertEqual(p, ex)
        results = mapper_search.search("'1.2.1'", self.session)
        logger.debug(results)
        self.assertEqual(len(results), 1)
        p = results.pop()
        ex = self.session.query(Plant).filter(Plant.id == 2).first()
        self.assertEqual(p, ex)
        results = mapper_search.search('\'1.2.2\'', self.session)
        self.assertEqual(len(results), 1)
        p = results.pop()
        ex = self.session.query(Plant).filter(Plant.id == 3).first()
        self.assertEqual(p, ex)

    def test_searchbyplantcode_invalid_values(self):
        mapper_search = search.get_strategy('PlantSearch')

        results = mapper_search.search('1.11', self.session)
        self.assertEqual(len(results), 0)
        self.assertEqual(self.handler.messages['bauble.plugins.garden.plant']['debug'], [
            'text is not quoted, should strategy apply?', 'ac: 1, pl: 11'])
        self.handler.reset()
        results = mapper_search.search("'121'", self.session)
        self.assertEqual(len(results), 0)
        self.assertEqual(self.handler.messages['bauble.plugins.garden.plant']['debug'], [
            "delimiter not found, can't split the code"])

    def test_searchbyaccessioncode(self):
        mapper_search = search.get_strategy('MapperSearch')

        results = mapper_search.search('2001.1', self.session)
        self.assertEqual(len(results), 1)
        a = results.pop()
        expect = self.session.query(Accession).filter(
            Accession.id == 1).first()
        logger.debug("%s, %s" % (a, expect))
        self.assertEqual(a, expect)
        results = mapper_search.search('2001.2', self.session)
        self.assertEqual(len(results), 1)
        a = results.pop()
        expect = self.session.query(Accession).filter(
            Accession.id == 2).first()
        logger.debug("%s, %s" % (a, expect))
        self.assertEqual(a, expect)

    def test_plant_from_dict(self):
        p = Plant.retrieve_or_create(
            self.session, {'object': 'plant',
                           'accession': '2001.1',
                           'code': '1'},
            create=False)
        self.assertFalse(p is None)

    def test_plant_note_from_dict(self):
        p = PlantNote.retrieve_or_create(
            self.session, {'object': 'plant_note',
                           'plant': '2001.1.1',
                           'note': '1',
                           'category': 'RBW'},
            create=True)
        self.assertFalse(p is None)


from bauble.plugins.garden.location import mergevalues


class AccessionGetNextCode(GardenTestCase):
    def test_get_next_code_first_this_year(self):
        this_year = str(datetime.date.today().year)
        self.assertEqual(Accession.get_next_code(), this_year + '.0001')

    def test_get_next_code_second_this_year(self):
        this_year = str(datetime.date.today().year)
        this_code = Accession.get_next_code()
        acc = Accession(species=self.species, code=str(this_code))
        self.session.add(acc)
        self.session.flush()
        self.assertEqual(Accession.get_next_code(), this_year + '.0002')

    def test_get_next_code_absolute_beginning(self):
        this_year = str(datetime.date.today().year)
        self.session.query(Accession).delete()
        self.session.flush()
        self.assertEqual(Accession.get_next_code(), this_year + '.0001')

    def test_get_next_code_next_with_hole(self):
        this_year = str(datetime.date.today().year)
        this_code = this_year + '.0050'
        acc = Accession(species=self.species, code=this_code)
        self.session.add(acc)
        self.session.flush()
        self.assertEqual(Accession.get_next_code(), this_year + '.0051')

    def test_get_next_code_alter_format_first(self):
        this_year = str(datetime.date.today().year)
        this_code = this_year + '.0050'
        orig = Accession.code_format
        acc = Accession(species=self.species, code=this_code)
        self.session.add(acc)
        self.session.flush()
        Accession.code_format = 'H.###'
        self.assertEqual(Accession.get_next_code(), 'H.001')
        Accession.code_format = 'SD.###'
        self.assertEqual(Accession.get_next_code(), 'SD.001')
        Accession.code_format = orig

    def test_get_next_code_alter_format_next(self):
        orig = Accession.code_format
        acc = Accession(species=self.species, code='H.012')
        self.session.add(acc)
        acc = Accession(species=self.species, code='SD.002')
        self.session.add(acc)
        self.session.flush()
        Accession.code_format = 'H.###'
        self.assertEqual(Accession.get_next_code(), 'H.013')
        Accession.code_format = 'SD.###'
        self.assertEqual(Accession.get_next_code(), 'SD.003')
        Accession.code_format = orig

    def test_get_next_code_alter_format_first_specified(self):
        this_year = str(datetime.date.today().year)
        this_code = this_year + '.0050'
        acc = Accession(species=self.species, code=this_code)
        self.session.add(acc)
        self.session.flush()
        self.assertEqual(Accession.get_next_code('H.###'), 'H.001')
        self.assertEqual(Accession.get_next_code('SD.###'), 'SD.001')

    def test_get_next_code_alter_format_next_specified(self):
        acc = Accession(species=self.species, code='H.012')
        self.session.add(acc)
        acc = Accession(species=self.species, code='SD.002')
        self.session.add(acc)
        self.session.flush()
        self.assertEqual(Accession.get_next_code('H.###'), 'H.013')
        self.assertEqual(Accession.get_next_code('SD.###'), 'SD.003')

    def test_get_next_code_plain_numeric_zero(self):
        self.assertEqual(Accession.get_next_code('#####'), '00001')

    def test_get_next_code_plain_numeric_next(self):
        acc = Accession(species=self.species, code='00012')
        self.session.add(acc)
        self.session.flush()
        self.assertEqual(Accession.get_next_code('#####'), '00013')

    def test_get_next_code_plain_numeric_next_multiple(self):
        acc = Accession(species=self.species, code='00012')
        ac2 = Accession(species=self.species, code='H.0987')
        ac3 = Accession(species=self.species, code='2112.0019')
        self.session.add_all([acc, ac2, ac3])
        self.session.flush()
        self.assertEqual(Accession.get_next_code('#####'), '00013')

    def test_get_next_code_fixed(self):
        acc = Accession(species=self.species, code='00012')
        ac2 = Accession(species=self.species, code='H.0987')
        ac3 = Accession(species=self.species, code='2112.0019')
        self.session.add_all([acc, ac2, ac3])
        self.session.flush()
        self.assertEqual(Accession.get_next_code('2112.003'), '2112.003')
        self.assertEqual(Accession.get_next_code('2112.0003'), '2112.0003')
        self.assertEqual(Accession.get_next_code('00003'), '00003')
        self.assertEqual(Accession.get_next_code('H.0003'), 'H.0003')

    def test_get_next_code_previous_year_subst(self):
        this_year = datetime.date.today().year
        last_year = this_year - 1
        acc = Accession(species=self.species, code='%s.0012' % last_year)
        ac2 = Accession(species=self.species, code='%s.0987' % this_year)
        self.session.add_all([acc, ac2])
        self.session.flush()
        self.assertEqual(Accession.get_next_code('%{Y-1}.####')[5:], '0013')
        self.assertEqual(Accession.get_next_code('%Y.####')[5:], '0988')


class GlobalFunctionsTests(GardenTestCase):

    def test_mergevalues_equal(self):
        'if the values are equal, return it'
        self.assertEqual(mergevalues('1', '1', '%s|%s'), '1')

    def test_mergevalues_conflict(self):
        'if they conflict, return both'
        self.assertEqual(mergevalues('2', '1', '%s|%s'), '2|1')

    def test_mergevalues_one_empty(self):
        'if one is empty, return the non empty one'
        self.assertEqual(mergevalues('2', None, '%s|%s'), '2')
        self.assertEqual(mergevalues(None, '2', '%s|%s'), '2')
        self.assertEqual(mergevalues('2', '', '%s|%s'), '2')

    def test_mergevalues_both_empty(self):
        'if both are empty, return the empty string'
        self.assertEqual(mergevalues(None, None, '%s|%s'), '')


class ContactTests(GardenTestCase):

    def __init__(self, *args):
        super().__init__(*args)

    def test_delete(self):

        # In theory, we'd rather not be allowed to delete contact if it
        # being referred to as the source for an accession.  However, this
        # just works.  As long as the trouble is theoretic we accept it.

        acc = self.create(Accession, species=self.species, code='2001.0001')
        contact = Contact(name='name')
        source = Source()
        source.source_detail = contact
        acc.source = source
        self.session.commit()
        self.session.close()

        # we can delete a contact even if used as source
        session = db.Session()
        contact = session.query(Contact).filter_by(name='name').one()
        session.delete(contact)
        session.commit()

        # the source field in the accession got removed
        session = db.Session()
        acc = session.query(Accession).filter_by(code='2001.0001').one()
        self.assertEqual(acc.source, None)

    def test_representation_of_contact(self):
        contact = Contact(name='name')
        self.assertEqual("%s" % contact, 'name')
        self.assertEqual(contact.search_view_markup_pair(), ('name', ''))


class ContactPresenterTests(BaubleTestCase):

    def test_create_presenter_automatic_session(self):
        from bauble.editor import MockView
        view = MockView()
        m = Contact()
        presenter = ContactPresenter(m, view)
        self.assertEqual(presenter.view, view)
        self.assertTrue(presenter.session is not None)
        # model might have been re-instantiated to fit presenter.session

    def test_create_presenter(self):
        from bauble.editor import MockView
        view = MockView()
        m = Contact()
        s = db.Session()
        s.add(m)
        presenter = ContactPresenter(m, view)
        self.assertEqual(presenter.view, view)
        self.assertTrue(presenter.session is not None)
        # m belongs to s; presenter.model is the same object
        self.assertEqual(id(presenter.model), id(m))

    def test_liststore_is_initialized(self):
        from bauble.editor import MockView
        view = MockView(combos={'source_type_combo': []})
        m = Contact(name='name', source_type='Expedition', description='desc')
        presenter = ContactPresenter(m, view)
        self.assertEqual(presenter.view.widget_get_text('source_name_entry'), 'name')
        self.assertEqual(presenter.view.widget_get_text('source_type_combo'), 'Expedition')
        self.assertEqual(presenter.view.widget_get_text('source_desc_textview'), 'desc')


import bauble.search
class BaubleSearchSearchTest(BaubleTestCase):
    def test_search_search_uses_Plant_Search(self):
        bauble.search.search("genus like %", self.session)
        self.assertTrue('SearchStrategy "genus like %"(PlantSearch)' in
                   self.handler.messages['bauble.search']['debug'])
        self.handler.reset()
        bauble.search.search("12.11.13", self.session)
        self.assertTrue('SearchStrategy "12.11.13"(PlantSearch)' in
                   self.handler.messages['bauble.search']['debug'])
        self.handler.reset()
        bauble.search.search("So ha", self.session)
        self.assertTrue('SearchStrategy "So ha"(PlantSearch)' in
                   self.handler.messages['bauble.search']['debug'])


from bauble.plugins.garden.exporttopocket import create_pocket, export_to_pocket

class TestExportToPocket(GardenTestCase):

    def test_export_empty_database(self):
        GardenTestCase.setUp(self)
        import tempfile
        filename = tempfile.mktemp()
        create_pocket(filename)
        export_to_pocket(filename)

        import sqlite3
        cn = sqlite3.connect(filename)
        cr = cn.cursor()
        cr.execute('select * from "species"')
        content = cr.fetchall()
        self.assertEqual(len(content), 0)
        cr.execute('select * from "accession"')
        content = cr.fetchall()
        self.assertEqual(len(content), 0)
        cr.execute('select * from "plant"')
        content = cr.fetchall()
        self.assertEqual(len(content), 0)

    def test_export_two_plants(self):
        GardenTestCase.setUp(self)
        acc = Accession(species=self.species, code='010203')
        loc = Location(code='123')
        loc2 = Location(code='213')
        plt1 = Plant(accession=acc, code='1', quantity=1, location=loc)
        plt2 = Plant(accession=acc, code='2', quantity=1, location=loc)
        self.session.add_all([acc, loc, loc2, plt1, plt2])
        self.session.commit()
        import tempfile
        filename = tempfile.mktemp()
        create_pocket(filename)
        export_to_pocket(filename)

        import sqlite3
        cn = sqlite3.connect(filename)
        cr = cn.cursor()
        cr.execute('select * from "species"')
        content = cr.fetchall()
        self.assertEqual(len(content), 1)
        cr.execute('select * from "accession"')
        content = cr.fetchall()
        self.assertEqual(len(content), 1)
        cr.execute('select * from "plant"')
        content = cr.fetchall()
        self.assertEqual(len(content), 2)
