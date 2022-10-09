# -*- coding: utf-8 -*-
#
# Copyright (c) 2005,2006,2007,2008,2009 Brett Adams <brett@belizebotanic.org>
# Copyright (c) 2012-2018 Mario Frasca <mario@anche.no>
# Copyright 2017 Jardín Botánico de Quito
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

import logging
logger = logging.getLogger(__name__)

import os

# TURN OFF desktop.open for this module so that the test doesn't open
# the report
import bauble.utils.desktop as desktop
desktop.open = lambda x: x

import bauble
from bauble.test import BaubleTestCase
from unittest import TestCase
from bauble.plugins.plants import Family, Genus, Species, \
    SpeciesDistribution, VernacularName, GeographicArea
from bauble.plugins.garden import Accession, Plant, Location
from bauble.plugins.report.jinja2 import Jinja2FormatterPlugin
from bauble.plugins.report import get_pertinent_objects
from bauble import utils as butils

class Jinja2FormatterTests(BaubleTestCase):

    def __init__(self, *args):
        super().__init__(*args)

    def setUp(self, *args):
        super().setUp()
        fctr = gctr = sctr = actr = pctr = 0
        for f in range(2):
            fctr+=1
            family = Family(id=fctr, family='fam%s' % fctr)
            self.session.add(family)
            for g in range(2):
                gctr+=1
                genus = Genus(id=gctr, family=family, genus='gen%s' % gctr)
                self.session.add(genus)
                for s in range(2):
                    sctr+=1
                    sp = Species(id=sctr, genus=genus, sp='sp%s' % sctr)
                    # TODO: why doesn't this geographic_area, species
                    # distribution stuff seem to work
                    geo = GeographicArea(id=sctr, name='Mexico%s' % sctr)
                    dist = SpeciesDistribution(geographic_area_id=sctr)
                    sp.distribution.append(dist)
                    vn = VernacularName(id=sctr, species=sp,
                                        name='name%s' % sctr)
                    self.session.add_all([sp, geo, dist, vn])
                    for a in range(2):
                        actr+=1
                        acc = Accession(id=actr, species=sp, code='%s' % actr)
                        self.session.add(acc)
                        for p in range(2):
                            pctr+=1
                            loc = Location(id=pctr, code='%s' % pctr,
                                           name='site%s' % pctr)
                            plant = Plant(id=pctr, accession=acc, location=loc,
                                          code='%s' % pctr, quantity=1)
                            #debug('fctr: %s, gctr: %s, actr: %s, pctr: %s' \
                            #      % (fctr, gctr, actr, pctr))
                            self.session.add_all([loc, plant])
        self.session.commit()

    def tearDown(self, *args):
        super().tearDown(*args)

    def test_format_all_templates(self):
        selection = self.session.query(Plant).all()
        # td is this module name, minus mako/test, plus templates
        td = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
        for i, tn in enumerate(os.listdir(td)):
            if not tn.endswith('.jj2'):
                continue
            filename = os.path.join(td, tn)
            domain = Jinja2FormatterPlugin.get_iteration_domain(filename)
            if domain == '':
                self.assertEqual(tn[:5], 'base.')
                continue
            try:
                cls = {
                    'plant': Plant,
                    'accession': Accession,
                    'species': Species,
                    'location': Location,
                }[domain]
                todo = sorted(get_pertinent_objects(cls, selection),
                              key=butils.natsort_key)
            except KeyError:
                todo = selection
            logger.debug('formatting ›%s‹' % filename)
            report = Jinja2FormatterPlugin.format(todo, template=filename)
            self.assertEqual((i, filename, type(report)), (i, filename, bytes))
