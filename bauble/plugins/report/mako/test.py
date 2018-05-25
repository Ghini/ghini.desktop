# -*- coding: utf-8 -*-
#
# Copyright (c) 2005,2006,2007,2008,2009 Brett Adams <brett@belizebotanic.org>
# Copyright (c) 2012-2015 Mario Frasca <mario@anche.no>
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
    SpeciesDistribution, VernacularName, GeographicArea
from bauble.plugins.garden import Accession, Plant, Location
from bauble.plugins.report.mako import MakoFormatterPlugin

from bauble.plugins.report.mako import add_text, Code39, add_code39, add_qr

class MakoFormatterTests(BaubleTestCase):

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
        """
        MakoFormatterPlugin.format() runs without raising an error for all templates.
        """
        plants = self.session.query(Plant).all()
        td = os.path.join(os.path.dirname(__file__), 'templates')
        for tn in MakoFormatterPlugin.templates:
            filename = os.path.join(td, tn)
            report = MakoFormatterPlugin.format(plants, template=filename)
            self.assertTrue(isinstance(report, str))


class SvgProductionTest(BaubleTestCase):
    def test_add_text_a(self):
        g, x, y = add_text(0, 0, 'a', 2)
        self.assertEqual(y, 0)
        self.assertEqual(x, 31)
        self.assertEqual(g, '<g transform="translate(0, 0)scale(2)">\n'
                          '<use transform="translate(0,0)" xlink:href="#s1-u0061"/>\n'
                          '</g>')

    def test_add_text_tildes(self):
        g, x, y = add_text(0, 0, 'áà', 2)
        self.assertEqual(y, 0)
        self.assertEqual(x, 62)
        self.assertEqual(g, '<g transform="translate(0, 0)scale(2)">\n'
                          '<use transform="translate(0,0)" xlink:href="#s1-u00e1"/>\n'
                          '<use transform="translate(15.5,0)" xlink:href="#s1-u00e0"/>\n'
                          '</g>')

    def test_add_text_align_right(self):
        g, x, y = add_text(0, 0, 'áà', 2, align=1)
        self.assertEqual(y, 0)
        self.assertEqual(x, 0)
        self.assertEqual(g, '<g transform="translate(-62.0, 0.0)scale(2)">\n'
                          '<use transform="translate(0,0)" xlink:href="#s1-u00e1"/>\n'
                          '<use transform="translate(15.5,0)" xlink:href="#s1-u00e0"/>\n'
                          '</g>')

    def test_add_text_align_right(self):
        g, x, y = add_text(0, 0, 'áà', 2, align=0.5)
        self.assertEqual(y, 0)
        self.assertEqual(x, 31.0)
        self.assertEqual(g, '<g transform="translate(-31.0, 0.0)scale(2)">\n'
                          '<use transform="translate(0,0)" xlink:href="#s1-u00e1"/>\n'
                          '<use transform="translate(15.5,0)" xlink:href="#s1-u00e0"/>\n'
                          '</g>')

    def test_add_text_a_rotated_endpoint(self):
        g, x, y = add_text(0, 0, 'a', 2, align=0, rotate=0)
        self.assertAlmostEqual(y, 0)
        self.assertAlmostEqual(x, 31)
        g, x, y = add_text(0, 0, 'a', 2, align=0, rotate=90)
        self.assertAlmostEqual(y, 31)
        self.assertAlmostEqual(x, 0)
        g, x, y = add_text(0, 0, 'a', 2, align=0, rotate=-90)
        self.assertAlmostEqual(y, -31)
        self.assertAlmostEqual(x, 0)
        g, x, y = add_text(0, 0, 'a', 2, align=0, rotate=180)
        self.assertAlmostEqual(y, 0)
        self.assertAlmostEqual(x, -31)

    def test_add_text_a_rotated_aligned_endpoint(self):
        g, x, y = add_text(0, 0, 'a', 2, align=0.5, rotate=0)
        self.assertAlmostEqual(y, 0)
        self.assertAlmostEqual(x, 15.5)
        g, x, y = add_text(0, 0, 'a', 2, align=0.5, rotate=90)
        self.assertAlmostEqual(y, 15.5)
        self.assertAlmostEqual(x, 0)
        g, x, y = add_text(0, 0, 'a', 2, align=0.5, rotate=-90)
        self.assertAlmostEqual(y, -15.5)
        self.assertAlmostEqual(x, 0)
        g, x, y = add_text(0, 0, 'a', 2, align=0.5, rotate=180)
        self.assertAlmostEqual(y, 0)
        self.assertAlmostEqual(x, -15.5)

    def test_add_text_a_rotated_glyph(self):
        g, x, y = add_text(0, 0, 'a', 2, align=0, rotate=0)
        self.assertEqual(g, '<g transform="translate(0, 0)scale(2)">\n'
                          '<use transform="translate(0,0)" xlink:href="#s1-u0061"/>\n'
                          '</g>')
        g, x, y = add_text(0, 0, 'a', 2, align=0, rotate=90)
        self.assertEqual(g, '<g transform="translate(0, 0)scale(2)rotate(90)">\n'
                          '<use transform="translate(0,0)" xlink:href="#s1-u0061"/>\n'
                          '</g>')
        g, x, y = add_text(0, 0, 'a', 2, align=0, rotate=-90)
        self.assertEqual(g, '<g transform="translate(0, 0)scale(2)rotate(-90)">\n'
                          '<use transform="translate(0,0)" xlink:href="#s1-u0061"/>\n'
                          '</g>')
        g, x, y = add_text(0, 0, 'a', 2, align=0, rotate=180)
        self.assertEqual(g, '<g transform="translate(0, 0)scale(2)rotate(180)">\n'
                          '<use transform="translate(0,0)" xlink:href="#s1-u0061"/>\n'
                          '</g>')

    def test_add_text_a_rotated_aligned_glyph(self):
        g, x, y = add_text(0, 0, 'a', 2, align=0.5, rotate=0)
        self.assertEqual(g, '<g transform="translate(-15.5, 0.0)scale(2)">\n'
                          '<use transform="translate(0,0)" xlink:href="#s1-u0061"/>\n'
                          '</g>')
        g, x, y = add_text(0, 0, 'a', 2, align=0.5, rotate=90)
        g = g.replace('-0.0', '0.0')  # ignore sign on zero
        self.assertEqual(g, '<g transform="translate(0.0, -15.5)scale(2)rotate(90)">\n'
                          '<use transform="translate(0,0)" xlink:href="#s1-u0061"/>\n'
                          '</g>')
        g, x, y = add_text(0, 0, 'a', 2, align=0.5, rotate=-90)
        g = g.replace('-0.0', '0.0')  # ignore sign on zero
        self.assertEqual(g, '<g transform="translate(0.0, 15.5)scale(2)rotate(-90)">\n'
                          '<use transform="translate(0,0)" xlink:href="#s1-u0061"/>\n'
                          '</g>')
        g, x, y = add_text(0, 0, 'a', 2, align=0.5, rotate=180)
        g = g.replace('-0.0', '0.0')  # ignore sign on zero
        self.assertEqual(g, '<g transform="translate(15.5, 0.0)scale(2)rotate(180)">\n'
                          '<use transform="translate(0,0)" xlink:href="#s1-u0061"/>\n'
                          '</g>')


class Code39Tests(BaubleTestCase):
    def test_code39_path_0(self):
        # 0123456789abcde
        # | |   ||| ||| |
        g = Code39.path('0', 10)
        self.assertEqual(g,
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
        self.assertEqual(g,
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
        self.assertEqual(g,
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
        self.assertEqual(g,'<path d="M 0,0 0,5 M 1,5 1,0 M 2,0 2,5 M 6,5 6,0 M 8,0 8,5 M 10,5 10,0 M 11,0 11,5 M 12,5 12,0 M 14,0 14,5" style="stroke:#0000ff;stroke-width:1"/>')

    def test_code39_translated_letter_dot_5(self):
        g = Code39.letter('.', 5, (5,8))
        self.assertEqual(g,'<path transform="translate(5,8)" d="M 0,0 0,5 M 1,5 1,0 M 2,0 2,5 M 6,5 6,0 M 8,0 8,5 M 10,5 10,0 M 11,0 11,5 M 12,5 12,0 M 14,0 14,5" style="stroke:#0000ff;stroke-width:1"/>')

    def test_code39_text(self):
        g, x, y = add_code39(0, 0, '010810', unit=1, height=7)
        self.assertEqual(y, 0)
        self.assertEqual(x, 127)
        self.assertEqual(g, '<g transform="translate(0,0)scale(1,1)translate(0,0)"><path transform="translate(0,0)" d="M 0,0 0,7 M 4,7 4,0 M 6,0 6,7 M 7,7 7,0 M 8,0 8,7 M 10,7 10,0 M 11,0 11,7 M 12,7 12,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/><path transform="translate(16,0)" d="M 0,0 0,7 M 2,7 2,0 M 6,0 6,7 M 7,7 7,0 M 8,0 8,7 M 10,7 10,0 M 11,0 11,7 M 12,7 12,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/><path transform="translate(32,0)" d="M 0,0 0,7 M 1,7 1,0 M 2,0 2,7 M 4,7 4,0 M 8,0 8,7 M 10,7 10,0 M 12,0 12,7 M 13,7 13,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/><path transform="translate(48,0)" d="M 0,0 0,7 M 2,7 2,0 M 6,0 6,7 M 7,7 7,0 M 8,0 8,7 M 10,7 10,0 M 11,0 11,7 M 12,7 12,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/><path transform="translate(64,0)" d="M 0,0 0,7 M 1,7 1,0 M 2,0 2,7 M 4,7 4,0 M 8,0 8,7 M 10,7 10,0 M 11,0 11,7 M 12,7 12,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/><path transform="translate(80,0)" d="M 0,0 0,7 M 1,7 1,0 M 2,0 2,7 M 4,7 4,0 M 8,0 8,7 M 10,7 10,0 M 12,0 12,7 M 13,7 13,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/><path transform="translate(96,0)" d="M 0,0 0,7 M 2,7 2,0 M 6,0 6,7 M 7,7 7,0 M 8,0 8,7 M 10,7 10,0 M 11,0 11,7 M 12,7 12,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/><path transform="translate(112,0)" d="M 0,0 0,7 M 4,7 4,0 M 6,0 6,7 M 7,7 7,0 M 8,0 8,7 M 10,7 10,0 M 11,0 11,7 M 12,7 12,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/></g>')

    def test_code39_text_centre(self):
        g, x, y = add_code39(0, 0, '0', unit=1, height=7, align=0.5)
        self.assertEqual(y, 0)
        self.assertEqual(g, '<g transform="translate(0,0)scale(1,1)translate(-23.5,0)"><path transform="translate(0,0)" d="M 0,0 0,7 M 4,7 4,0 M 6,0 6,7 M 7,7 7,0 M 8,0 8,7 M 10,7 10,0 M 11,0 11,7 M 12,7 12,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/><path transform="translate(16,0)" d="M 0,0 0,7 M 2,7 2,0 M 6,0 6,7 M 7,7 7,0 M 8,0 8,7 M 10,7 10,0 M 11,0 11,7 M 12,7 12,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/><path transform="translate(32,0)" d="M 0,0 0,7 M 4,7 4,0 M 6,0 6,7 M 7,7 7,0 M 8,0 8,7 M 10,7 10,0 M 11,0 11,7 M 12,7 12,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/></g>')
        self.assertEqual(x, 23.5)

    def test_code39_text_left(self):
        g, x, y = add_code39(0, 0, '0', unit=1, height=7, align=0)
        self.assertEqual(y, 0)
        self.assertEqual(g, '<g transform="translate(0,0)scale(1,1)translate(0,0)"><path transform="translate(0,0)" d="M 0,0 0,7 M 4,7 4,0 M 6,0 6,7 M 7,7 7,0 M 8,0 8,7 M 10,7 10,0 M 11,0 11,7 M 12,7 12,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/><path transform="translate(16,0)" d="M 0,0 0,7 M 2,7 2,0 M 6,0 6,7 M 7,7 7,0 M 8,0 8,7 M 10,7 10,0 M 11,0 11,7 M 12,7 12,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/><path transform="translate(32,0)" d="M 0,0 0,7 M 4,7 4,0 M 6,0 6,7 M 7,7 7,0 M 8,0 8,7 M 10,7 10,0 M 11,0 11,7 M 12,7 12,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/></g>')
        self.assertEqual(x, 47)

    def test_code39_text_right(self):
        g, x, y = add_code39(0, 0, '0', unit=1, height=7, align=1)
        self.assertEqual(y, 0)
        self.assertEqual(g, '<g transform="translate(0,0)scale(1,1)translate(-47,0)"><path transform="translate(0,0)" d="M 0,0 0,7 M 4,7 4,0 M 6,0 6,7 M 7,7 7,0 M 8,0 8,7 M 10,7 10,0 M 11,0 11,7 M 12,7 12,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/><path transform="translate(16,0)" d="M 0,0 0,7 M 2,7 2,0 M 6,0 6,7 M 7,7 7,0 M 8,0 8,7 M 10,7 10,0 M 11,0 11,7 M 12,7 12,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/><path transform="translate(32,0)" d="M 0,0 0,7 M 4,7 4,0 M 6,0 6,7 M 7,7 7,0 M 8,0 8,7 M 10,7 10,0 M 11,0 11,7 M 12,7 12,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/></g>')
        self.assertEqual(x, 0)

    def test_code39_shortblack(self):
        g, x, y = add_code39(0, 0, 'M+/-%', unit=1, height=7, align=0)
        self.assertEqual(y, 0)
        self.assertEqual(g, '<g transform="translate(0,0)scale(1,1)translate(0,0)"><path transform="translate(0,0)" d="M 0,0 0,7 M 4,7 4,0 M 6,0 6,7 M 7,7 7,0 M 8,0 8,7 M 10,7 10,0 M 11,0 11,7 M 12,7 12,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/><path transform="translate(16,0)" d="M 0,0 0,7 M 1,7 1,0 M 2,0 2,7 M 4,7 4,0 M 5,0 5,7 M 6,7 6,0 M 8,0 8,7 M 10,7 10,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/><path transform="translate(32,0)" d="M 0,0 0,7 M 4,7 4,0 M 6,0 6,7 M 10,7 10,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/><path transform="translate(48,0)" d="M 0,0 0,7 M 4,7 4,0 M 8,0 8,7 M 10,7 10,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/><path transform="translate(64,0)" d="M 0,0 0,7 M 4,7 4,0 M 6,0 6,7 M 8,7 8,0 M 9,0 9,7 M 10,7 10,0 M 12,0 12,7 M 13,7 13,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/><path transform="translate(80,0)" d="M 0,0 0,7 M 2,7 2,0 M 6,0 6,7 M 10,7 10,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/><path transform="translate(96,0)" d="M 0,0 0,7 M 4,7 4,0 M 6,0 6,7 M 7,7 7,0 M 8,0 8,7 M 10,7 10,0 M 11,0 11,7 M 12,7 12,0 M 14,0 14,7" style="stroke:#0000ff;stroke-width:1"/></g>')
        self.assertEqual(x, 111)


class QRCodeTests(BaubleTestCase):
    path = '<path stroke="#000" class="pyqrline" d="M0 0.5h7m1 0h3m1 0h1m1 0h7m-21 1h1m5 0h1m2 0h2m3 0h1m5 0h1m-21 1h1m1 0h3m1 0h1m3 0h1m3 0h1m1 0h3m1 0h1m-21 1h1m1 0h3m1 0h1m1 0h1m2 0h2m1 0h1m1 0h3m1 0h1m-21 1h1m1 0h3m1 0h1m3 0h2m2 0h1m1 0h3m1 0h1m-21 1h1m5 0h1m2 0h1m1 0h1m2 0h1m5 0h1m-21 1h7m1 0h1m1 0h1m1 0h1m1 0h7m-12 1h1m2 0h1m-11 1h1m1 0h3m1 0h2m3 0h1m3 0h1m2 0h1m-18 1h2m2 0h2m3 0h1m1 0h2m3 0h2m-21 1h5m1 0h1m1 0h1m3 0h4m1 0h4m-21 1h4m1 0h1m2 0h2m1 0h2m2 0h2m2 0h1m-20 1h2m3 0h2m1 0h3m4 0h1m1 0h1m1 0h2m-13 1h1m1 0h3m4 0h1m2 0h1m-21 1h7m2 0h2m5 0h2m1 0h2m-21 1h1m5 0h1m1 0h3m1 0h1m1 0h1m4 0h1m-20 1h1m1 0h3m1 0h1m1 0h1m1 0h2m2 0h1m1 0h2m1 0h2m-21 1h1m1 0h3m1 0h1m2 0h1m4 0h2m3 0h1m-20 1h1m1 0h3m1 0h1m1 0h1m3 0h2m1 0h1m2 0h1m1 0h1m-21 1h1m5 0h1m2 0h3m1 0h5m1 0h1m-20 1h7m3 0h1m2 0h3m2 0h3"/>'
    def test_can_get_qr_as_string(self):
        g = add_qr(0, 0, 'test')
        parts = g.split('\n')
        self.assertEqual(len(parts), 1)
        self.assertEqual(parts[0], self.path)

    def test_can_get_qr_as_string_translated(self):
        g = add_qr(30, 10, 'test')
        parts = g.split('\n')
        self.assertEqual(len(parts), 3)
        self.assertEqual(parts[0], '<g transform="translate(30,10)">')
        self.assertEqual(parts[1], self.path)
        self.assertEqual(parts[2], '</g>')

    def test_can_get_qr_as_string_translated_framed(self):
        g = add_qr(30, 10, 'http://ghini.readthedocs.io/en/ghini-1.0-dev/', side=30)
        parts = g.split('\n')
        self.assertEqual(len(parts), 3)
        self.assertTrue(parts[0].startswith('<g transform="translate(30,10)scale(0.731707317073'))
        self.assertEqual(parts[2], '</g>')

        g = add_qr(30, 10, '2014.0018.2', side=30)
        parts = g.split('\n')
        self.assertEqual(len(parts), 3)
        self.assertEqual(parts[0], '<g transform="translate(30,10)scale(1.2)">')
        self.assertEqual(parts[2], '</g>')

        g = add_qr(30, 10, '2014.0018', side=30)
        parts = g.split('\n')
        self.assertEqual(len(parts), 3)
        self.assertTrue(parts[0].startswith('<g transform="translate(30,10)scale(1.4285714'))
        self.assertEqual(parts[2], '</g>')
