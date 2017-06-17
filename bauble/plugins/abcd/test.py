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
import bauble.plugins.abcd as abcd
from bauble.plugins.garden import Plant, Accession, Source, Collection
import bauble.plugins.plants.test as plants_test
import bauble.plugins.garden.test as garden_test


# TODO: the ABCD tests need to be completely reworked

class ABCDTestCase(BaubleTestCase):

    def __init__(self, *args):
        super(ABCDTestCase, self).__init__(*args)

    def setUp(self):
        super(ABCDTestCase, self).setUp()
        plants_test.setUp_data()
        garden_test.setUp_data()

        schema_file = os.path.join(
            paths.lib_dir(), 'plugins', 'abcd', 'abcd_2.06.xsd')
        xmlschema_doc = etree.parse(schema_file)
        self.abcd_schema = etree.XMLSchema(xmlschema_doc)

    def test_abcd(self):
        # TODO: this needs to be updated, we don't use the
        # ElementFactory anymore
        pass
        # datasets = DataSets()
        # ds = ElementFactory(datasets, 'DataSet')
        # tech_contacts = ElementFactory( ds, 'TechnicalContacts')
        # tech_contact = ElementFactory(tech_contacts, 'TechnicalContact')
        # ElementFactory(tech_contact, 'Name', text='Brett')
        # ElementFactory(tech_contact, 'Email', text='brett@belizebotanic.org')
        # cont_contacts = ElementFactory(ds, 'ContentContacts')
        # cont_contact = ElementFactory(cont_contacts, 'ContentContact')
        # ElementFactory(cont_contact, 'Name', text='Brett')
        # ElementFactory(cont_contact, 'Email', text='brett@belizebotanic.org')
        # metadata = ElementFactory(ds, 'Metadata', )
        # description = ElementFactory(metadata, 'Description')
        #   representation = ElementFactory(description, 'Representation',
        #                                   attrib={'language': 'en'})
        # revision = ElementFactory(metadata, 'RevisionData')
        # ElementFactory(revision, 'DateModified', text='2001-03-01T00:00:00')
        # title = ElementFactory(representation, 'Title', text='TheTitle')
        # units = ElementFactory(ds, 'Units')
        # unit = ElementFactory(units, 'Unit')
        # ElementFactory(unit, 'SourceInstitutionID', text='BBG')
        # ElementFactory(unit, 'SourceID', text='1111')
        # unit_id = ElementFactory(unit, 'UnitID', text='2222')

        # self.assert_(self.validate(datasets), self.abcd_schema.error_log)

    def test_export(self):
        """
        Test the ABCDExporter
        """
        self.assert_(self.session.query(Plant).count() > 0)
        accession = self.session.query(Accession).first()
        source = Source()
        accession.source = source
        source.sources_code = u'1'
        collection = Collection(collector=u'Bob', collectors_code=u'1',
                                geography_id=1, locale=u'locale',
                                date=datetime.date.today(),
                                latitude=u'1.1', longitude=u'1.1',
                                habitat=u'habitat description',
                                elevation=1, elevation_accy=1,
                                notes=u'some notes')
        source.collection = collection
        from bauble.plugins.garden import Institution
        inst = Institution()
        inst.name = inst.code = inst.contact = \
            inst.technical_contact = inst.email = 'test'
        inst.write()
        self.session.commit()
        dummy, filename = tempfile.mkstemp()
        xml = abcd.ABCDExporter().start(filename)
        logger.debug(xml)

    def test_plants_to_abcd(self):
        plants = self.session.query(Plant)
        assert plants.count() > 0
        pass
        # create abcd from plants
        # data = abcd.plants_to_abcd(plants)
        # assert validate abcd
        # self.assert_(self.validate(data), self.abcd_schema.error_log)

    def validate(self, xml):
        return self.abcd_schema.validate(xml)
