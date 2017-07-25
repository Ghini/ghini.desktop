# -*- coding: utf-8 -*-
#
# Copyright (c) 2005,2006,2007,2008,2009 Brett Adams <brett@belizebotanic.org>
# Copyright (c) 2012-2015 Mario Frasca <mario@anche.no>
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

from bauble.plugins.report.mako import add_text, Code39, add_code39

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


class SvgProductionTest(BaubleTestCase):
    def test_add_text_a(self):
        g, x, y = add_text(0, 0, 'a', 2)
        self.assertEquals(y, 0)
        self.assertEquals(x, 31)
        self.assertEquals(g, '<g transform="translate(0.0, 0.0)scale(2)">\n'
                          '<use transform="translate(0,0)" xlink:href="#s1-u0061"/>\n'
                          '</g>')

    def test_add_text_tildes(self):
        g, x, y = add_text(0, 0, u'áà', 2)
        self.assertEquals(y, 0)
        self.assertEquals(x, 62)
        self.assertEquals(g, '<g transform="translate(0.0, 0.0)scale(2)">\n'
                          '<use transform="translate(0,0)" xlink:href="#s1-u00e1"/>\n'
                          '<use transform="translate(15.5,0)" xlink:href="#s1-u00e0"/>\n'
                          '</g>')

    def test_add_text_align_right(self):
        g, x, y = add_text(0, 0, u'áà', 2, align=1)
        self.assertEquals(y, 0)
        self.assertEquals(x, 0)
        self.assertEquals(g, '<g transform="translate(-62.0, 0.0)scale(2)">\n'
                          '<use transform="translate(0,0)" xlink:href="#s1-u00e1"/>\n'
                          '<use transform="translate(15.5,0)" xlink:href="#s1-u00e0"/>\n'
                          '</g>')

    def test_add_text_align_right(self):
        g, x, y = add_text(0, 0, u'áà', 2, align=0.5)
        self.assertEquals(y, 0)
        self.assertEquals(x, 31.0)
        self.assertEquals(g, '<g transform="translate(-31.0, 0.0)scale(2)">\n'
                          '<use transform="translate(0,0)" xlink:href="#s1-u00e1"/>\n'
                          '<use transform="translate(15.5,0)" xlink:href="#s1-u00e0"/>\n'
                          '</g>')

    def test_add_text_a_rotated_endpoint(self):
        g, x, y = add_text(0, 0, 'a', 2, align=0, rotate=0)
        self.assertAlmostEquals(y, 0)
        self.assertAlmostEquals(x, 31)
        g, x, y = add_text(0, 0, 'a', 2, align=0, rotate=90)
        self.assertAlmostEquals(y, 31)
        self.assertAlmostEquals(x, 0)
        g, x, y = add_text(0, 0, 'a', 2, align=0, rotate=-90)
        self.assertAlmostEquals(y, -31)
        self.assertAlmostEquals(x, 0)
        g, x, y = add_text(0, 0, 'a', 2, align=0, rotate=180)
        self.assertAlmostEquals(y, 0)
        self.assertAlmostEquals(x, -31)

    def test_add_text_a_rotated_aligned_endpoint(self):
        g, x, y = add_text(0, 0, 'a', 2, align=0.5, rotate=0)
        self.assertAlmostEquals(y, 0)
        self.assertAlmostEquals(x, 15.5)
        g, x, y = add_text(0, 0, 'a', 2, align=0.5, rotate=90)
        self.assertAlmostEquals(y, 15.5)
        self.assertAlmostEquals(x, 0)
        g, x, y = add_text(0, 0, 'a', 2, align=0.5, rotate=-90)
        self.assertAlmostEquals(y, -15.5)
        self.assertAlmostEquals(x, 0)
        g, x, y = add_text(0, 0, 'a', 2, align=0.5, rotate=180)
        self.assertAlmostEquals(y, 0)
        self.assertAlmostEquals(x, -15.5)

    def test_add_text_a_rotated_glyph(self):
        g, x, y = add_text(0, 0, 'a', 2, align=0, rotate=0)
        self.assertEquals(g, '<g transform="translate(0.0, 0.0)scale(2)">\n'
                          '<use transform="translate(0,0)" xlink:href="#s1-u0061"/>\n'
                          '</g>')
        g, x, y = add_text(0, 0, 'a', 2, align=0, rotate=90)
        self.assertEquals(g, '<g transform="translate(0.0, 0.0)scale(2)rotate(90)">\n'
                          '<use transform="translate(0,0)" xlink:href="#s1-u0061"/>\n'
                          '</g>')
        g, x, y = add_text(0, 0, 'a', 2, align=0, rotate=-90)
        self.assertEquals(g, '<g transform="translate(0.0, 0.0)scale(2)rotate(-90)">\n'
                          '<use transform="translate(0,0)" xlink:href="#s1-u0061"/>\n'
                          '</g>')
        g, x, y = add_text(0, 0, 'a', 2, align=0, rotate=180)
        self.assertEquals(g, '<g transform="translate(0.0, 0.0)scale(2)rotate(180)">\n'
                          '<use transform="translate(0,0)" xlink:href="#s1-u0061"/>\n'
                          '</g>')

    def test_add_text_a_rotated_aligned_glyph(self):
        g, x, y = add_text(0, 0, 'a', 2, align=0.5, rotate=0)
        self.assertEquals(g, '<g transform="translate(-15.5, 0.0)scale(2)">\n'
                          '<use transform="translate(0,0)" xlink:href="#s1-u0061"/>\n'
                          '</g>')
        g, x, y = add_text(0, 0, 'a', 2, align=0.5, rotate=90)
        g = g.replace('-0.0', '0.0')  # ignore sign on zero
        self.assertEquals(g, '<g transform="translate(0.0, -15.5)scale(2)rotate(90)">\n'
                          '<use transform="translate(0,0)" xlink:href="#s1-u0061"/>\n'
                          '</g>')
        g, x, y = add_text(0, 0, 'a', 2, align=0.5, rotate=-90)
        g = g.replace('-0.0', '0.0')  # ignore sign on zero
        self.assertEquals(g, '<g transform="translate(0.0, 15.5)scale(2)rotate(-90)">\n'
                          '<use transform="translate(0,0)" xlink:href="#s1-u0061"/>\n'
                          '</g>')
        g, x, y = add_text(0, 0, 'a', 2, align=0.5, rotate=180)
        g = g.replace('-0.0', '0.0')  # ignore sign on zero
        self.assertEquals(g, '<g transform="translate(15.5, 0.0)scale(2)rotate(180)">\n'
                          '<use transform="translate(0,0)" xlink:href="#s1-u0061"/>\n'
                          '</g>')


class Code39Tests(BaubleTestCase):
    def test_code39_path_0(self):
        # 0123456789abcde
        # | |   ||| ||| |
        g = Code39.path('0', 10)
        self.assertEquals(g,
                          'M 0,0 0,10 '
                          'M 2,10 2,0 '
                          'M 6,0 6,10 '
                          'M 7,10 7,0 '
                          'M 8,0 8,10 '
                          'M 10,10 10,0 '
                          'M 11,0 11,10 '
                          'M 12,10 12,0 '
                          'M 14,0 14,10')

    def test_code39_path_dot(self):
        # 0123456789abcde
        # |||   | | ||| |
        g = Code39.path('.', 10)
        self.assertEquals(g,
                          'M 0,0 0,10 '
                          'M 1,10 1,0 '
                          'M 2,0 2,10 '
                          'M 6,10 6,0 '
                          'M 8,0 8,10 '
                          'M 10,10 10,0 '
                          'M 11,0 11,10 '
                          'M 12,10 12,0 '
                          'M 14,0 14,10')

    def test_code39_path_dot_5(self):
        # 0123456789abcde
        # |||   | | ||| |
        g = Code39.path('.', 5)
        self.assertEquals(g,
                          'M 0,0 0,5 '
                          'M 1,5 1,0 '
                          'M 2,0 2,5 '
                          'M 6,5 6,0 '
                          'M 8,0 8,5 '
                          'M 10,5 10,0 '
                          'M 11,0 11,5 '
                          'M 12,5 12,0 '
                          'M 14,0 14,5')

    def test_code39_letter_dot_5(self):
        g = Code39.letter('.', 5)
        self.assertEquals(g,'<path d="M 0,0 0,5 M 1,5 1,0 M 2,0 2,5 M 6,5 6,0 M 8,0 8,5 M 10,5 10,0 M 11,0 11,5 M 12,5 12,0 M 14,0 14,5" style="stroke:#0000ff;stroke-width:1"/>')

    def test_code39_translated_letter_dot_5(self):
        g = Code39.letter('.', 5, (5,8))
        self.assertEquals(g,'<path transform="translate(5,8)" d="M 0,0 0,5 M 1,5 1,0 M 2,0 2,5 M 6,5 6,0 M 8,0 8,5 M 10,5 10,0 M 11,0 11,5 M 12,5 12,0 M 14,0 14,5" style="stroke:#0000ff;stroke-width:1"/>')

    def test_code39_text(self):
        g, x, y = add_code39(0, 0, u'010810', unit=1, height=7)
        self.assertEquals(y, 0)
        self.assertEquals(x, 127)
        self.assertEquals(g, '<g transform="translate(0,0)scale(1,1)translate(0,0)"><path transform="translate(0,0)" d="M 0,0 0,7 M 4,7 4,0 M 6,0 6,7 M 7,7 7,0 M 8,0 8,7 M 10,7 10,0 M 11,0 11,7 M 12,7 12,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/><path transform="translate(16,0)" d="M 0,0 0,7 M 2,7 2,0 M 6,0 6,7 M 7,7 7,0 M 8,0 8,7 M 10,7 10,0 M 11,0 11,7 M 12,7 12,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/><path transform="translate(32,0)" d="M 0,0 0,7 M 1,7 1,0 M 2,0 2,7 M 4,7 4,0 M 8,0 8,7 M 10,7 10,0 M 12,0 12,7 M 13,7 13,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/><path transform="translate(48,0)" d="M 0,0 0,7 M 2,7 2,0 M 6,0 6,7 M 7,7 7,0 M 8,0 8,7 M 10,7 10,0 M 11,0 11,7 M 12,7 12,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/><path transform="translate(64,0)" d="M 0,0 0,7 M 1,7 1,0 M 2,0 2,7 M 4,7 4,0 M 8,0 8,7 M 10,7 10,0 M 11,0 11,7 M 12,7 12,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/><path transform="translate(80,0)" d="M 0,0 0,7 M 1,7 1,0 M 2,0 2,7 M 4,7 4,0 M 8,0 8,7 M 10,7 10,0 M 12,0 12,7 M 13,7 13,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/><path transform="translate(96,0)" d="M 0,0 0,7 M 2,7 2,0 M 6,0 6,7 M 7,7 7,0 M 8,0 8,7 M 10,7 10,0 M 11,0 11,7 M 12,7 12,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/><path transform="translate(112,0)" d="M 0,0 0,7 M 4,7 4,0 M 6,0 6,7 M 7,7 7,0 M 8,0 8,7 M 10,7 10,0 M 11,0 11,7 M 12,7 12,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/></g>')

    def test_code39_text_centre(self):
        g, x, y = add_code39(0, 0, u'0', unit=1, height=7, align=0.5)
        self.assertEquals(y, 0)
        self.assertEquals(g, '<g transform="translate(0,0)scale(1,1)translate(-23.5,0)"><path transform="translate(0,0)" d="M 0,0 0,7 M 4,7 4,0 M 6,0 6,7 M 7,7 7,0 M 8,0 8,7 M 10,7 10,0 M 11,0 11,7 M 12,7 12,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/><path transform="translate(16,0)" d="M 0,0 0,7 M 2,7 2,0 M 6,0 6,7 M 7,7 7,0 M 8,0 8,7 M 10,7 10,0 M 11,0 11,7 M 12,7 12,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/><path transform="translate(32,0)" d="M 0,0 0,7 M 4,7 4,0 M 6,0 6,7 M 7,7 7,0 M 8,0 8,7 M 10,7 10,0 M 11,0 11,7 M 12,7 12,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/></g>')
        self.assertEquals(x, 23.5)

    def test_code39_text_left(self):
        g, x, y = add_code39(0, 0, u'0', unit=1, height=7, align=0)
        self.assertEquals(y, 0)
        self.assertEquals(g, '<g transform="translate(0,0)scale(1,1)translate(0,0)"><path transform="translate(0,0)" d="M 0,0 0,7 M 4,7 4,0 M 6,0 6,7 M 7,7 7,0 M 8,0 8,7 M 10,7 10,0 M 11,0 11,7 M 12,7 12,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/><path transform="translate(16,0)" d="M 0,0 0,7 M 2,7 2,0 M 6,0 6,7 M 7,7 7,0 M 8,0 8,7 M 10,7 10,0 M 11,0 11,7 M 12,7 12,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/><path transform="translate(32,0)" d="M 0,0 0,7 M 4,7 4,0 M 6,0 6,7 M 7,7 7,0 M 8,0 8,7 M 10,7 10,0 M 11,0 11,7 M 12,7 12,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/></g>')
        self.assertEquals(x, 47)

    def test_code39_text_right(self):
        g, x, y = add_code39(0, 0, u'0', unit=1, height=7, align=1)
        self.assertEquals(y, 0)
        self.assertEquals(g, '<g transform="translate(0,0)scale(1,1)translate(-47,0)"><path transform="translate(0,0)" d="M 0,0 0,7 M 4,7 4,0 M 6,0 6,7 M 7,7 7,0 M 8,0 8,7 M 10,7 10,0 M 11,0 11,7 M 12,7 12,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/><path transform="translate(16,0)" d="M 0,0 0,7 M 2,7 2,0 M 6,0 6,7 M 7,7 7,0 M 8,0 8,7 M 10,7 10,0 M 11,0 11,7 M 12,7 12,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/><path transform="translate(32,0)" d="M 0,0 0,7 M 4,7 4,0 M 6,0 6,7 M 7,7 7,0 M 8,0 8,7 M 10,7 10,0 M 11,0 11,7 M 12,7 12,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/></g>')
        self.assertEquals(x, 0)

    def test_code39_shortblack(self):
        g, x, y = add_code39(0, 0, u'M+/-%', unit=1, height=7, align=0)
        self.assertEquals(y, 0)
        self.assertEquals(g, '<g transform="translate(0,0)scale(1,1)translate(0,0)"><path transform="translate(0,0)" d="M 0,0 0,7 M 4,7 4,0 M 6,0 6,7 M 7,7 7,0 M 8,0 8,7 M 10,7 10,0 M 11,0 11,7 M 12,7 12,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/><path transform="translate(16,0)" d="M 0,0 0,7 M 1,7 1,0 M 2,0 2,7 M 4,7 4,0 M 5,0 5,7 M 6,7 6,0 M 8,0 8,7 M 10,7 10,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/><path transform="translate(32,0)" d="M 0,0 0,7 M 4,7 4,0 M 6,0 6,7 M 10,7 10,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/><path transform="translate(48,0)" d="M 0,0 0,7 M 4,7 4,0 M 8,0 8,7 M 10,7 10,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/><path transform="translate(64,0)" d="M 0,0 0,7 M 4,7 4,0 M 6,0 6,7 M 8,7 8,0 M 9,0 9,7 M 10,7 10,0 M 12,0 12,7 M 13,7 13,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/><path transform="translate(80,0)" d="M 0,0 0,7 M 2,7 2,0 M 6,0 6,7 M 10,7 10,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/><path transform="translate(96,0)" d="M 0,0 0,7 M 4,7 4,0 M 6,0 6,7 M 7,7 7,0 M 8,0 8,7 M 10,7 10,0 M 11,0 11,7 M 12,7 12,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/></g>')
        self.assertEquals(x, 111)
