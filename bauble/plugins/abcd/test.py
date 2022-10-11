# -*- coding: utf-8 -*-
#
# Copyright (c) 2005,2006,2007,2008,2009 Brett Adams <brett@belizebotanic.org>
# Copyright (c) 2012-2016 Mario Frasca <mario@anche.no>
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
#
# test.py
#
# Description: test the ABCD (Access to Biological Collection Data) plugin
#
import datetime
import lxml.etree as etree
import os
import tempfile

import logging
logger = logging.getLogger(__name__)

import bauble.paths as paths
from bauble.test import BaubleTestCase
from bauble.plugins.garden import Plant, Accession, Source, Collection
import bauble.plugins.plants.test as plants_test
import bauble.plugins.garden.test as garden_test
from nose import SkipTest

from bauble.plugins.abcd import *

# TODO: the ABCD tests need to be completely reworked

class ABCDTestCase(BaubleTestCase):

    def __init__(self, *args):
        super().__init__(*args)

    def setUp(self):
        super().setUp()
        plants_test.setUp_data()
        garden_test.setUp_data()

        schema_file = os.path.join(
            paths.lib_dir(), 'plugins', 'abcd', 'abcd_2.06.xsd')
        xmlschema_doc = etree.parse(schema_file)
        self.abcd_schema = etree.XMLSchema(xmlschema_doc)
        from bauble.plugins.garden import Institution
        inst = Institution()
        inst.name = inst.code = inst.contact = \
            inst.technical_contact = inst.email = 'test'
        inst.write()
        self.session.commit()

    def test_abcd(self):
        datasets = DataSets()
        ds = ABCDElement(datasets, 'DataSet')
        tech_contacts = ABCDElement( ds, 'TechnicalContacts')
        tech_contact = ABCDElement(tech_contacts, 'TechnicalContact')
        ABCDElement(tech_contact, 'Name', text='Brett')
        ABCDElement(tech_contact, 'Email', text='brett@belizebotanic.org')
        cont_contacts = ABCDElement(ds, 'ContentContacts')
        cont_contact = ABCDElement(cont_contacts, 'ContentContact')
        ABCDElement(cont_contact, 'Name', text='Brett')
        ABCDElement(cont_contact, 'Email', text='brett@belizebotanic.org')
        metadata = ABCDElement(ds, 'Metadata', )
        description = ABCDElement(metadata, 'Description')
        representation = ABCDElement(description, 'Representation',
                                        attrib={'language': 'en'})
        revision = ABCDElement(metadata, 'RevisionData')
        ABCDElement(revision, 'DateModified', text='2001-03-01T00:00:00')
        title = ABCDElement(representation, 'Title', text='TheTitle')
        units = ABCDElement(ds, 'Units')
        unit = ABCDElement(units, 'Unit')
        ABCDElement(unit, 'SourceInstitutionID', text='BBG')
        ABCDElement(unit, 'SourceID', text='1111')
        unit_id = ABCDElement(unit, 'UnitID', text='2222')

        self.assertTrue(self.abcd_schema.validate(datasets), self.abcd_schema.error_log)

    def test_export(self):
        """
        Test the ABCDExporter
        """
        self.assertTrue(self.session.query(Plant).count() > 0)
        accession = self.session.query(Accession).first()
        source = Source()
        accession.source = source
        source.sources_code = '1'
        collection = Collection(collector='Bob', collectors_code='1',
                                geographic_area_id=1, locale='locale',
                                date=datetime.date.today(),
                                latitude='1.1', longitude='1.1',
                                habitat='habitat description',
                                elevation=1, elevation_accy=1,
                                notes='some notes')
        source.collection = collection
        dummy, filename = tempfile.mkstemp()
        ABCDExporter().start(filename)

    def test_plants_to_abcd(self):
        plants = self.session.query(Plant)
        assert plants.count() > 0
        # create abcd from plants
        data = plants_to_abcd(plants)
        self.assertNotEqual(data, None)
        # assert validate abcd
        self.assertTrue(self.abcd_schema.validate(data), self.abcd_schema.error_log)
