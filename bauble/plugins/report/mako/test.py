# -*- coding: utf-8 -*-
#
# Copyright (c) 2005,2006,2007,2008,2009 Brett Adams <brett@belizebotanic.org>
# Copyright (c) 2012-2015 Mario Frasca <mario@anche.no>
#
# This file is part of bauble.classic.
#
# bauble.classic is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# bauble.classic is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bauble.classic. If not, see <http://www.gnu.org/licenses/>.

import os

# TURN OFF desktop.open for this module so that the test doesn't open
# the report
import bauble.utils.desktop as desktop
desktop.open = lambda x: x

from bauble.test import BaubleTestCase
#import bauble.plugins.report as report_plugin
from bauble.plugins.report import (
    get_species_pertinent_to, get_accessions_pertinent_to,
    get_plants_pertinent_to)
from bauble.plugins.plants import Family, Genus, Species, \
    SpeciesDistribution, VernacularName, Geography
from bauble.plugins.garden import Accession, Plant, Location
from bauble.plugins.report.mako import MakoFormatterPlugin


class MakoFormatterTests(BaubleTestCase):

    def __init__(self, *args):
        super(MakoFormatterTests, self).__init__(*args)

    def setUp(self, *args):
        super(MakoFormatterTests, self).setUp()
        fctr = gctr = sctr = actr = pctr = 0
        for f in xrange(2):
            fctr+=1
            family = Family(id=fctr, family=u'fam%s' % fctr)
            self.session.add(family)
            for g in range(2):
                gctr+=1
                genus = Genus(id=gctr, family=family, genus=u'gen%s' % gctr)
                self.session.add(genus)
                for s in range(2):
                    sctr+=1
                    sp = Species(id=sctr, genus=genus, sp=u'sp%s' % sctr)
                    # TODO: why doesn't this geography, species
                    # distribution stuff seem to work
                    geo = Geography(id=sctr, name=u'Mexico%s' % sctr)
                    dist = SpeciesDistribution(geography_id=sctr)
                    sp.distribution.append(dist)
                    vn = VernacularName(id=sctr, species=sp,
                                        name=u'name%s' % sctr)
                    self.session.add_all([sp, geo, dist, vn])
                    for a in range(2):
                        actr+=1
                        acc = Accession(id=actr, species=sp, code=u'%s' % actr)
                        self.session.add(acc)
                        for p in range(2):
                            pctr+=1
                            loc = Location(id=pctr, code=u'%s' % pctr,
                                           name=u'site%s' % pctr)
                            plant = Plant(id=pctr, accession=acc, location=loc,
                                          code=u'%s' % pctr, quantity=1)
                            #debug('fctr: %s, gctr: %s, actr: %s, pctr: %s' \
                            #      % (fctr, gctr, actr, pctr))
                            self.session.add_all([loc, plant])
        self.session.commit()

    def tearDown(self, *args):
        super(MakoFormatterTests, self).tearDown(*args)

    def test_format(self):
        """
        Test the MakoFormatterPlugin.format() runs without raising an error.
        """
        plants = self.session.query(Plant).all()
        filename = os.path.join(os.path.dirname(__file__), 'example.csv')
        report = MakoFormatterPlugin.format(plants, template=filename)
        assert(isinstance(report, basestring))
        open('/tmp/testlabels.csv', 'w').write(report)
        #print >>sys.stderr, report
