#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2018 Mario Frasca <mario@anche.no>.
# Copyright 2018 Tanager Botanical Garden <tanagertourism@gmail.com>
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

import os
import datetime
from unittest import TestCase

from gi.repository import Gtk

import logging
logger = logging.getLogger(__name__)

from nose import SkipTest
import bauble.db as db
from bauble.test import BaubleTestCase
from bauble import utils
from bauble.plugins.garden.accession import Accession, Verification
from bauble.plugins.garden.plant import Plant, PlantNote, PlantChange
from bauble.plugins.garden.location import Location
from bauble.plugins.plants import Family, Genus, Species

from .import_pocket_log import process_line, lookup


class ImportNewPlant(BaubleTestCase):
    def test_importing_nothing(self):
        # prepare T0
        # test T0
        self.assertEqual(self.session.query(Accession).first(), None)
        self.assertEqual(self.session.query(Plant).first(), None)

        # action
        line = '20180905_170619 :PENDING_EDIT:  : Eugenia stipitata : 1 : (@;@)'
        process_line(self.session, line, 1536845535)

        # T1
        self.assertEqual(self.session.query(Accession).first(), None)
        self.assertEqual(self.session.query(Plant).first(), None)

    def test_completely_identified_existing_species(self):
        # prepare T0
        fam = Family(epithet='Myrtaceae')
        gen = Genus(epithet='Eugenia', family=fam)
        spe = Species(epithet='stipitata', genus=gen)
        self.session.add_all([fam, gen, spe])
        self.session.commit()
        # test T0
        a = self.session.query(Accession).filter_by(code='2018.0001').first()
        self.assertEqual(a, None)
        eugenia = self.session.query(Genus).filter_by(epithet='Eugenia').first()
        self.assertNotEqual(eugenia, None)
        s = self.session.query(Species).filter_by(genus=eugenia, epithet='stipitata').first()
        self.assertNotEqual(s, None)
        # action
        line = '20180905_170619 :PENDING_EDIT: 2018.0001.1 : Eugenia stipitata : 1 : (@;@)'
        process_line(self.session, line, 1536845535)
        # T1
        a = self.session.query(Accession).filter_by(code='2018.0001').first()
        self.assertNotEqual(a, None)
        self.assertEqual(a.species.genus.epithet, 'Eugenia')
        self.assertEqual(a.species.epithet, 'stipitata')
        self.assertEqual(a.quantity_recvd, 1)
        self.assertEqual(len(a.plants), 1)
        self.assertEqual(a.plants[0].quantity, 1)

    def test_completely_identified_new_species(self):
        # prepare T0
        fam = Family(epithet='Myrtaceae')
        gen = Genus(epithet='Eugenia', family=fam)
        self.session.add_all([fam, gen])
        self.session.commit()
        # test T0
        a = self.session.query(Accession).filter_by(code='2018.0001').first()
        self.assertEqual(a, None)
        eugenia = self.session.query(Genus).filter_by(epithet='Eugenia').first()
        self.assertNotEqual(eugenia, None)
        s = self.session.query(Species).filter_by(genus=eugenia, epithet='stipitata').first()
        self.assertEqual(s, None)

        # action
        db.current_user.override('Pasquale')
        line = '20180905_170619 :PENDING_EDIT: 2018.0001.1 : Eugenia stipitata : 1 : (@;@)'
        process_line(self.session, line, 1536845535)
        db.current_user.override()

        # T1
        a = self.session.query(Accession).filter_by(code='2018.0001').first()
        self.assertNotEqual(a, None)
        self.assertEqual(a.species.genus.epithet, 'Eugenia')
        self.assertEqual(a.species.epithet, 'stipitata')
        self.assertEqual(a.quantity_recvd, 1)
        self.assertEqual(len(a.plants), 1)
        self.assertEqual(a.plants[0].quantity, 1)
        self.assertEqual(len(a.verifications), 1)
        self.assertEqual(a.verifications[0].verifier, 'Pasquale')

    def test_genus_identified(self):
        # prepare T0
        fam = Family(epithet='Myrtaceae')
        gen = Genus(epithet='Eugenia', family=fam)
        self.session.add_all([fam, gen])
        self.session.commit()
        # test T0
        a = self.session.query(Accession).filter_by(code='2018.0001').first()
        self.assertEqual(a, None)
        eugenia = self.session.query(Genus).filter_by(epithet='Eugenia').first()
        self.assertNotEqual(eugenia, None)
        s = self.session.query(Species).filter_by(genus=eugenia, infrasp1='sp', infrasp1_rank=None).first()
        self.assertEqual(s, None)
        # action
        line = '20180905_170619 :PENDING_EDIT: 2018.0001.1 : Eugenia : 1 : (@;@)'
        process_line(self.session, line, 1536845535)
        # T1
        eugenia_sp = self.session.query(Species).filter_by(genus=eugenia, infrasp1='sp', infrasp1_rank=None).first()
        a = self.session.query(Accession).filter_by(code='2018.0001').first()
        self.assertNotEqual(a, None)
        self.assertEqual(a.species.genus, eugenia)
        self.assertEqual(a.species, eugenia_sp)
        self.assertEqual(a.quantity_recvd, 1)
        self.assertEqual(len(a.plants), 1)
        self.assertEqual(a.plants[0].quantity, 1)
        self.assertEqual(len(a.verifications), 0)

    def test_not_identified(self):
        # prepare T0
        # test T0
        a = self.session.query(Accession).filter_by(code='2018.0001').first()
        self.assertEqual(a, None)
        s = self.session.query(Species).first()
        self.assertEqual(s, None)
        # action
        line = '20180905_170619 :PENDING_EDIT: 2018.0001.1 :  : 1 : (@;@)'
        process_line(self.session, line, 1536845535)
        self.session.commit()
        # T1
        a = self.session.query(Accession).filter_by(code='2018.0001').first()
        self.assertNotEqual(a, None)
        self.assertEqual(a.species.infrasp1, 'sp')
        self.assertEqual(a.species.genus.epithet, 'Zzd-Plantae')
        self.assertEqual(a.species.genus.family.epithet, 'Zz-Plantae')
        self.assertEqual(a.quantity_recvd, 1)
        self.assertEqual(len(a.plants), 1)
        self.assertEqual(a.plants[0].quantity, 1)

    def test_not_identified_no_quantity_defaults_to_one(self):
        # prepare T0
        # test T0
        a = self.session.query(Accession).filter_by(code='2018.0001').first()
        self.assertEqual(a, None)
        s = self.session.query(Species).first()
        self.assertEqual(s, None)
        # action
        line = '20180905_170619 :PENDING_EDIT: 2018.0001.1 :  :  : (@;@)'
        process_line(self.session, line, 1536845535)
        self.session.commit()
        # T1
        a = self.session.query(Accession).filter_by(code='2018.0001').first()
        self.assertNotEqual(a, None)
        self.assertEqual(a.species.infrasp1, 'sp')
        self.assertEqual(a.species.genus.epithet, 'Zzd-Plantae')
        self.assertEqual(a.species.genus.family.epithet, 'Zz-Plantae')
        self.assertEqual(a.quantity_recvd, 1)
        self.assertEqual(len(a.plants), 1)
        self.assertEqual(a.plants[0].quantity, 1)

    def test_not_identified_some_quantity_not_one(self):
        # prepare T0
        # test T0
        a = self.session.query(Accession).filter_by(code='2018.0001').first()
        self.assertEqual(a, None)
        s = self.session.query(Species).first()
        self.assertEqual(s, None)
        # action
        line = '20180905_170619 :PENDING_EDIT: 2018.0001.1 :  : 3 : (@;@)'
        process_line(self.session, line, 1536845535)
        self.session.commit()
        # T1
        a = self.session.query(Accession).filter_by(code='2018.0001').first()
        self.assertNotEqual(a, None)
        self.assertEqual(a.species.infrasp1, 'sp')
        self.assertEqual(a.species.genus.epithet, 'Zzd-Plantae')
        self.assertEqual(a.species.genus.family.epithet, 'Zz-Plantae')
        self.assertEqual(a.quantity_recvd, 3)
        self.assertEqual(len(a.plants), 1)
        self.assertEqual(a.plants[0].quantity, 3)

    def test_not_identified_no_plant_code(self):
        # prepare T0
        # test T0
        a = self.session.query(Accession).filter_by(code='2018.0001').first()
        self.assertEqual(a, None)
        s = self.session.query(Species).first()
        self.assertEqual(s, None)
        # action
        line = '20180905_170619 :PENDING_EDIT: 2018.0001 :  : 1 : (@;@)'
        process_line(self.session, line, 1536845535)
        self.session.commit()
        # T1
        a = self.session.query(Accession).filter_by(code='2018.0001').first()
        self.assertNotEqual(a, None)
        self.assertEqual(a.species.infrasp1, 'sp')
        self.assertEqual(a.species.genus.epithet, 'Zzd-Plantae')
        self.assertEqual(a.species.genus.family.epithet, 'Zz-Plantae')
        self.assertEqual(a.quantity_recvd, 1)
        self.assertEqual(len(a.plants), 1)
        self.assertEqual(a.plants[0].quantity, 1)
        self.assertEqual(len(a.verifications), 0)

    def test_not_identified_quito_accession_code(self):
        # prepare T0
        # test T0
        a = self.session.query(Accession).filter_by(code='018901').first()
        self.assertEqual(a, None)
        s = self.session.query(Species).first()
        self.assertEqual(s, None)
        # action
        line = '20180905_170619 :PENDING_EDIT: 018901 :  : 1 : (@;@)'
        process_line(self.session, line, 1536845535)
        line = '20180905_170619 :PENDING_EDIT: 018901.2 :  : 2 : (@;@)'
        process_line(self.session, line, 1536845535)
        self.session.commit()
        # T1
        a = self.session.query(Accession).filter_by(code='018901').first()
        self.assertNotEqual(a, None)
        self.assertEqual(a.species.infrasp1, 'sp')
        self.assertEqual(a.species.genus.epithet, 'Zzd-Plantae')
        self.assertEqual(a.species.genus.family.epithet, 'Zz-Plantae')
        self.assertEqual(a.quantity_recvd, 1)
        self.assertEqual(len(a.plants), 2)
        self.assertEqual(a.plants[0].quantity, 1)
        self.assertEqual(a.plants[1].quantity, 2)


class ImportExistingPlant(BaubleTestCase):
    def setUp(self):
        super().setUp()
        fam_fictive = Family(epithet='Zz-Plantae')
        gen_fictive = Genus(epithet='Zzd-Plantae', family=fam_fictive)
        fam = Family(epithet='Myrtaceae')
        gen = Genus(epithet='Eugenia', family=fam)
        spe = Species(epithet='stipitata', genus=gen)
        self.session.add_all([fam, gen, spe, fam_fictive, gen_fictive])
        self.session.commit()
        self.fam, self.gen, self.spe, self.fam_fictive, self.gen_fictive = fam, gen, spe, fam_fictive, gen_fictive

    def test_import_unidentified_not_overwriting_existing_identification(self):
        # prepare T0
        l = lookup(self.session, Location, code='somewhere')
        a = lookup(self.session, Accession, code='2018.0001', species=self.spe)
        p = lookup(self.session, Plant, accession=a, code='1', location=l, quantity=1)
        # test T0
        a = self.session.query(Accession).filter_by(code='2018.0001').first()
        p = self.session.query(Plant).filter_by(code='1', accession=a).first()
        self.assertNotEqual(a, None)
        self.assertEqual(a.species.epithet, 'stipitata')
        self.assertEqual(a.species.genus.epithet, 'Eugenia')
        self.assertEqual(a.species.genus.family.epithet, 'Myrtaceae')
        self.assertNotEqual(p, None)
        self.assertEqual(p.location, l)
        self.assertEqual(p.quantity, 1)
        # action
        line = '20180905_170619 :PENDING_EDIT: 2018.0001.1 :  : 3 : (@;@)'
        process_line(self.session, line, 1536845535)
        # test T1
        a = self.session.query(Accession).filter_by(code='2018.0001').first()
        p = self.session.query(Plant).filter_by(code='1', accession=a).first()
        self.assertNotEqual(a, None)
        self.assertEqual(a.species.epithet, 'stipitata')
        self.assertEqual(a.species.genus.epithet, 'Eugenia')
        self.assertEqual(a.species.genus.family.epithet, 'Myrtaceae')
        self.assertNotEqual(p, None)
        self.assertEqual(p.location, l)
        self.assertEqual(p.quantity, 3)

    def test_import_identified_overwriting_identification(self):
        # prepare T0
        l = lookup(self.session, Location, code='somewhere')
        a = lookup(self.session, Accession, code='2018.0002', species=self.spe)
        p = lookup(self.session, Plant, accession=a, code='1', location=l, quantity=1)
        # test T0
        a = self.session.query(Accession).filter_by(code='2018.0002').first()
        self.assertNotEqual(a, None)
        p = self.session.query(Plant).filter_by(code='1', accession=a).first()
        self.assertNotEqual(p, None)
        self.assertEqual(a.species.epithet, 'stipitata')
        self.assertEqual(a.species.genus.epithet, 'Eugenia')
        self.assertEqual(a.species.genus.family.epithet, 'Myrtaceae')
        self.assertEqual(p.location, l)
        self.assertEqual(p.quantity, 1)
        initial_count = len(a.verifications)

        # action
        db.current_user.override('Pasquale')
        line = '20180905_170619 :PENDING_EDIT: 2018.0002.1 : Eugenia insignis : 1 : (@;@)'
        process_line(self.session, line, 1536845535)
        db.current_user.override()

        # test T1
        a = self.session.query(Accession).filter_by(code='2018.0002').first()
        p = self.session.query(Plant).filter_by(code='1', accession=a).first()
        self.assertNotEqual(a, None)
        self.assertEqual(a.species.epithet, 'insignis')
        self.assertEqual(a.species.genus.epithet, 'Eugenia')
        self.assertEqual(a.species.genus.family.epithet, 'Myrtaceae')
        self.assertNotEqual(p, None)
        self.assertEqual(p.location, l)
        self.assertEqual(p.quantity, 1)
        self.assertEqual(len(a.verifications), initial_count + 1)
        self.assertEqual(a.verifications[-1].verifier, 'Pasquale')

class ImportInventoryLines(BaubleTestCase):
    def setUp(self):
        super().setUp()
        loc = Location(code='somewhere')
        fam_fictive = Family(epithet='Zz-Plantae')
        gen_fictive = Genus(epithet='Zzd-Plantae', family=fam_fictive)
        fam = Family(epithet='Myrtaceae')
        gen = Genus(epithet='Eugenia', family=fam)
        spe = Species(epithet='stipitata', genus=gen)
        self.session.add_all([fam, gen, spe, fam_fictive, gen_fictive, loc])
        self.session.commit()
        self.loc, self.fam, self.gen, self.spe, self.fam_fictive, self.gen_fictive = (
            loc, fam, gen, spe, fam_fictive, gen_fictive)

    def test_inventory_existing_plant(self):
        # prepare T0
        a = lookup(self.session, Accession, code='2013.1317', species=self.spe)
        p = lookup(self.session, Plant, accession=a, code='1', location=self.loc, quantity=1)
        # test T0
        self.assertEqual(p.location, self.loc)

        # action
        line = '20180223_092139 :INVENTORY: A09x : 2013.1317 : 000000000000000'
        process_line(self.session, line, 1536845535)
        self.session.commit()

        # test T1
        a = self.session.query(Accession).filter_by(code='2013.1317').first()
        p = self.session.query(Plant).filter_by(code='1', accession=a).first()
        self.assertEqual(p.location.code, 'A09x')
        self.assertEqual(len(p.notes), 1)
        self.assertEqual(p.notes[0].category, 'inventory')
        self.assertEqual(p.notes[0].note, '2018-02-23')

    def test_inventory_unknown_plant(self):
        # prepare T0
        # test T0
        a = self.session.query(Accession).first()
        self.assertEqual(a, None)

        # action
        line = '20180223_092139 :INVENTORY: A09x : 2013.1317 : 000000000000000'
        process_line(self.session, line, 1536845535)
        self.session.commit()

        # test T1
        a = self.session.query(Accession).filter_by(code='2013.1317').first()
        p = self.session.query(Plant).filter_by(code='1', accession=a).first()
        self.assertEqual(p.location.code, 'A09x')
        self.assertEqual(len(p.notes), 1)

    def test_inventory_totally_useless_line(self):
        # prepare T0
        # test T0
        a = self.session.query(Accession).first()
        self.assertEqual(a, None)
        self.assertEqual(len(self.session.query(Location).all()), 1)

        # action
        line = '20180223_092139 :INVENTORY:  :  : 000000000000000'
        process_line(self.session, line, 1536845535)
        self.session.commit()

        # test T1
        a = self.session.query(Accession).first()
        self.assertEqual(a, None)
        self.assertEqual(len(self.session.query(Location).all()), 1)

    def test_inventory_existence_assertion_on_already_existing(self):
        # prepare T0
        a = lookup(self.session, Accession, code='2013.1317', species=self.spe)
        p = lookup(self.session, Plant, accession=a, code='1', location=self.loc, quantity=1)
        # test T0
        self.assertEqual(p.location, self.loc)

        # action
        line = '20180223_092139 :INVENTORY:  : 2013.1317 : 000000000000000'
        process_line(self.session, line, 1536845535)
        self.session.commit()

        # test T1
        a = self.session.query(Accession).filter_by(code='2013.1317').first()
        p = self.session.query(Plant).filter_by(code='1', accession=a).first()
        self.assertEqual(p.location.code, 'somewhere')
        self.assertEqual(len(p.notes), 1)  # inventory always noted

    def test_inventory_existence_assertion_on_not_existing(self):
        # prepare T0
        # test T0
        a = self.session.query(Accession).first()
        self.assertEqual(a, None)
        self.assertEqual(len(self.session.query(Location).all()), 1)

        # action
        line = '20180223_092139 :INVENTORY:  : 2013.1317 : 000000000000000'
        process_line(self.session, line, 1536845535)
        self.session.commit()

        # test T1
        self.assertEqual(len(self.session.query(Location).all()), 2)
        a = self.session.query(Accession).filter_by(code='2013.1317').first()
        self.assertNotEqual(a, None)
        p = self.session.query(Plant).filter_by(code='1', accession=a).first()
        self.assertNotEqual(p, None)
        self.assertEqual(p.location.code, 'default')
        self.assertEqual(len(p.notes), 1)  # inventory always noted


class ImportGPSCoordinates(BaubleTestCase):
    def setUp(self):
        super().setUp()
        loc = Location(code='somewhere')
        fam_fictive = Family(epithet='Zz-Plantae')
        gen_fictive = Genus(epithet='Zzd-Plantae', family=fam_fictive)
        self.session.add_all([fam_fictive, gen_fictive, loc])
        self.session.commit()
        self.loc, self.fam_fictive, self.gen_fictive = (
            loc, fam_fictive, gen_fictive)

    def test_gps_coordinates_defining(self):
        # prepare T0
        # test T0
        a = self.session.query(Accession).first()
        self.assertEqual(a, None)
        # action
        line = '20180905_170619 :PENDING_EDIT: 2018.0001 :  :  : (31.5215;-5.5312)'
        process_line(self.session, line, 1536845535)
        self.session.commit()
        # T1
        a = self.session.query(Accession).filter_by(code='2018.0001').first()
        self.assertNotEqual(a, None)
        self.assertEqual(len(a.plants), 1)
        p = a.plants[0]
        self.assertEqual(p.coords, {'lat': 31.5215, 'lon': -5.5312})

    def test_gps_coordinates_overwriting(self):
        # prepare T0
        l = lookup(self.session, Location, code='somewhere')
        s = lookup(self.session, Species, genus=self.gen_fictive, infrasp1='sp')
        a = lookup(self.session, Accession, code='2018.0002', species=s)
        p = lookup(self.session, Plant, accession=a, code='1', location=l, quantity=1)
        pn = lookup(self.session, PlantNote, plant=p, category='<coords>', note="{lat:32.2996,lon:-9.2395}")

        # test T0
        self.assertEqual(p.coords, {'lat': 32.2996, 'lon': -9.2395})

        # action
        line = '20180905_170619 :PENDING_EDIT: 2018.0002 :  :  : (31.5215;-5.5312)'
        process_line(self.session, line, 1536845535)
        self.session.commit()

        # T1
        a = self.session.query(Accession).filter_by(code='2018.0002').first()
        self.assertNotEqual(a, None)
        self.assertEqual(len(a.plants), 1)
        p = a.plants[0]
        self.assertEqual(p.coords, {'lat': 31.5215, 'lon': -5.5312})


class ImportPictures(BaubleTestCase):
    def setUp(self):
        super().setUp()
        loc = Location(code='somewhere')
        fam_fictive = Family(epithet='Zz-Plantae')
        gen_fictive = Genus(epithet='Zzd-Plantae', family=fam_fictive)
        self.session.add_all([fam_fictive, gen_fictive, loc])
        self.session.commit()
        self.loc, self.fam_fictive, self.gen_fictive = (
            loc, fam_fictive, gen_fictive)

    def test_pictures_adding_two(self):
        # prepare T0
        # test T0
        a = self.session.query(Accession).first()
        self.assertEqual(a, None)

        # action
        line = '20180223_130951 :PENDING_EDIT: 2015.0901 :  :  : (@;@) : file:///storage/sdcard/Android/data/me.ghini.pocket/files/Pictures/GPP_20180223_130931-958344128.jpg : file:///storage/sdcard/Android/data/me.ghini.pocket/files/Pictures/GPP_20180223_130943948184518.jpg'
        db.current_user.override('Antonio')
        process_line(self.session, line, 1536845535)
        db.current_user.override()
        self.session.commit()

        # T1
        a = self.session.query(Accession).filter_by(code='2015.0901').first()
        self.assertNotEqual(a, None)
        self.assertEqual(len(a.plants), 1)
        p = a.plants[0]
        self.assertEqual(len(p.pictures), 2)
