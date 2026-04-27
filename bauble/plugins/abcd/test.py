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
import logging
import os
import tempfile
from typing import Any

import bauble.paths as paths
import bauble.plugins.garden.test as garden_test
import bauble.plugins.plants.test as plants_test
import pytest
from bauble.plugins.abcd import ABCDElement, ABCDExporter, DataSets, plants_to_abcd
from bauble.plugins.garden.models import Accession, Collection, Plant, Source
from lxml import etree
from sqlalchemy import select

logger: Any = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def abcd_schema():
    """
    Fixture to load and parse the ABCD schema for XML validation.
    """
    schema_file = os.path.join(paths.lib_dir(), "plugins", "abcd", "abcd_2.06.xsd")
    xmlschema_doc = etree.parse(schema_file)
    return etree.XMLSchema(xmlschema_doc)


@pytest.fixture
def setup_test_data(db_session) -> None:
    """
    Fixture to set up test data for plants and gardens.
    """
    plants_test.setUp_data()
    garden_test.setUp_data()

    from bauble.plugins.garden import Institution

    inst = Institution()
    inst.name = inst.code = inst.contact = inst.technical_contact = inst.email = "test"
    inst.write()
    if db_session.in_transaction():
        db_session.commit()


def test_abcd_structure(abcd_schema, setup_test_data) -> None:
    """
    Test the structure and validation of an ABCD dataset.
    """
    datasets = DataSets()
    ds = ABCDElement(datasets, "DataSet")
    tech_contacts = ABCDElement(ds, "TechnicalContacts")
    tech_contact = ABCDElement(tech_contacts, "TechnicalContact")
    ABCDElement(tech_contact, "Name", text="Brett")
    ABCDElement(tech_contact, "Email", text="brett@belizebotanic.org")
    cont_contacts = ABCDElement(ds, "ContentContacts")
    cont_contact = ABCDElement(cont_contacts, "ContentContact")
    ABCDElement(cont_contact, "Name", text="Brett")
    ABCDElement(cont_contact, "Email", text="brett@belizebotanic.org")
    metadata = ABCDElement(ds, "Metadata")
    description = ABCDElement(metadata, "Description")
    representation = ABCDElement(
        description, "Representation", attrib={"language": "en"}
    )
    revision = ABCDElement(metadata, "RevisionData")
    ABCDElement(revision, "DateModified", text="2001-03-01T00:00:00")
    ABCDElement(representation, "Title", text="TheTitle")
    units = ABCDElement(ds, "Units")
    unit = ABCDElement(units, "Unit")
    ABCDElement(unit, "SourceInstitutionID", text="BBG")
    ABCDElement(unit, "SourceID", text="1111")
    ABCDElement(unit, "UnitID", text="2222")

    # Validate the ABCD structure
    assert abcd_schema.validate(datasets), abcd_schema.error_log


def test_abcd_export(db_session, setup_test_data) -> None:
    """
    Test the ABCDExporter functionality.
    """
    from sqlalchemy import func

    plants_count = db_session.execute(select(func.count())).select_from(Plant)
    assert plants_count > 0, "No plants available for export."

    accession = db_session.execute(select(Accession)).scalars().first()
    source = Source()
    accession.source = source
    source.sources_code = "1"
    collection = Collection(
        collector="Bob",
        collectors_code="1",
        geographic_area_id=1,
        locale="locale",
        date=datetime.date.today(),
        latitude="1.1",
        longitude="1.1",
        habitat="habitat description",
        elevation=1,
        elevation_accy=1,
        notes="some notes",
    )
    source.collection = collection

    dummy, filename = tempfile.mkstemp()
    try:
        ABCDExporter().start(filename)
    finally:
        os.close(dummy)
        os.remove(filename)


def test_plants_to_abcd(db_session, abcd_schema, setup_test_data) -> None:
    """
    Test conversion of plants to ABCD format and validate the result.
    """
    plants = db_session.execute(select(Plant)).scalars().all()
    assert len(plants) > 0, "No plants available for conversion to ABCD."

    # Convert plants to ABCD XML
    data = plants_to_abcd(plants)
    assert data is not None, "Failed to convert plants to ABCD format."

    # Validate the ABCD XML
    assert abcd_schema.validate(data), abcd_schema.error_log
