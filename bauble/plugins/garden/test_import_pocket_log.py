#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2018 Mario Frasca <mario@anche.no>.
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

from .import_pocket_log import process_line

class ImportNewPlant(BaubleTestCase):
    def test_completely_identified_existing_species(self):
        # prepare T0
        fam = Family(epithet='Myrtaceae')
        gen = Genus(epithet='Eugenia', family=fam)
        spe = Species(epithet='stipitata', genus=gen)
        self.session.add_all([fam, gen, spe])
        self.session.commit()
        # test T0
        a = self.session.query(Accession).filter_by(code='2018.0001').first()
        self.assertEquals(a, None)
        eugenia = self.session.query(Genus).filter_by(epithet='Eugenia').first()
        self.assertNotEquals(eugenia, None)
        s = self.session.query(Species).filter_by(genus=eugenia, epithet='stipitata').first()
        self.assertNotEquals(s, None)
        # action
        line = '20180905_170619 :PENDING_EDIT: 2018.0001.1 : Eugenia stipitata : 1 : (@;@)'
        process_line(self.session, line, 1536845535)
        # T1
        a = self.session.query(Accession).filter_by(code='2018.0001').first()
        self.assertNotEquals(a, None)
        self.assertEquals(a.species.genus.epithet, 'Eugenia')
        self.assertEquals(a.species.epithet, 'stipitata')
        self.assertEquals(a.quantity_recvd, 1)
        self.assertEquals(len(a.plants), 1)
        self.assertEquals(a.plants[0].quantity, 1)

    def test_completely_identified_new_species(self):
        # prepare T0
        fam = Family(epithet='Myrtaceae')
        gen = Genus(epithet='Eugenia', family=fam)
        self.session.add_all([fam, gen])
        self.session.commit()
        # test T0
        a = self.session.query(Accession).filter_by(code='2018.0001').first()
        self.assertEquals(a, None)
        eugenia = self.session.query(Genus).filter_by(epithet='Eugenia').first()
        self.assertNotEquals(eugenia, None)
        s = self.session.query(Species).filter_by(genus=eugenia, epithet='stipitata').first()
        self.assertEquals(s, None)
        # action
        line = '20180905_170619 :PENDING_EDIT: 2018.0001.1 : Eugenia stipitata : 1 : (@;@)'
        process_line(self.session, line, 1536845535)
        # T1
        a = self.session.query(Accession).filter_by(code='2018.0001').first()
        self.assertNotEquals(a, None)
        self.assertEquals(a.species.genus.epithet, 'Eugenia')
        self.assertEquals(a.species.epithet, 'stipitata')
        self.assertEquals(a.quantity_recvd, 1)
        self.assertEquals(len(a.plants), 1)
        self.assertEquals(a.plants[0].quantity, 1)

    def test_genus_identified(self):
        # prepare T0
        fam = Family(epithet='Myrtaceae')
        gen = Genus(epithet='Eugenia', family=fam)
        self.session.add_all([fam, gen])
        self.session.commit()
        # test T0
        a = self.session.query(Accession).filter_by(code='2018.0001').first()
        self.assertEquals(a, None)
        eugenia = self.session.query(Genus).filter_by(epithet='Eugenia').first()
        self.assertNotEquals(eugenia, None)
        s = self.session.query(Species).filter_by(genus=eugenia, infrasp1='sp', infrasp1_rank=None).first()
        self.assertEquals(s, None)
        # action
        line = '20180905_170619 :PENDING_EDIT: 2018.0001.1 : Eugenia : 1 : (@;@)'
        process_line(self.session, line, 1536845535)
        # T1
        eugenia_sp = self.session.query(Species).filter_by(genus=eugenia, infrasp1='sp', infrasp1_rank=None).first()
        a = self.session.query(Accession).filter_by(code='2018.0001').first()
        self.assertNotEquals(a, None)
        self.assertEquals(a.species.genus, eugenia)
        self.assertEquals(a.species, eugenia_sp)
        self.assertEquals(a.quantity_recvd, 1)
        self.assertEquals(len(a.plants), 1)
        self.assertEquals(a.plants[0].quantity, 1)

    def test_not_identified(self):
        # prepare T0
        # test T0
        a = self.session.query(Accession).filter_by(code='2018.0001').first()
        self.assertEquals(a, None)
        s = self.session.query(Species).first()
        self.assertEquals(s, None)
        # action
        line = '20180905_170619 :PENDING_EDIT: 2018.0001.1 :  : 1 : (@;@)'
        process_line(self.session, line, 1536845535)
        # T1
        a = self.session.query(Accession).filter_by(code='2018.0001').first()
        self.assertNotEquals(a, None)
        self.assertEquals(a.species.infrasp1, 'sp')
        self.assertEquals(a.species.genus.epithet, 'Zzd-Plantae')
        self.assertEquals(a.species.genus.family.epithet, 'Zz-Plantae')
        
