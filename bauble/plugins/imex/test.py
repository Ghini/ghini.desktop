"""
Copyright 2004-2010 Brett Adams
Copyright 2015 Mario Frasca <mario@anche.no>

This file is part of ghini.desktop.

ghini.desktop is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

ghini.desktop is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with ghini.desktop. If not, see <http://www.gnu.org/licenses/>.
"""

import csv
import json
import logging
import os
import shutil
import tempfile
from collections.abc import Generator
from tempfile import mkdtemp, mkstemp
from typing import Any

import bauble.plugins.garden.test as garden_test
import bauble.plugins.plants.test as plants_test
import pytest
from bauble.db import Base, engine
from bauble.editor import MockView
from bauble.plugins.garden.models import Accession as Accession
from bauble.plugins.garden.models import Contact as Contact
from bauble.plugins.garden.models import Location as Location
from bauble.plugins.garden.models import Plant as Plant
from bauble.plugins.garden.models import Source as Source
from bauble.plugins.imex.csv_ import QUOTE_CHAR as QUOTE_CHAR
from bauble.plugins.imex.csv_ import QUOTE_STYLE as QUOTE_STYLE
from bauble.plugins.imex.csv_ import CSVExporter as CSVExporter
from bauble.plugins.imex.csv_ import CSVImporter as CSVImporter
from bauble.plugins.imex.iojson import JSONExporter, JSONImporter
from bauble.plugins.plants import Family as Family
from bauble.plugins.plants import Genus as Genus
from bauble.plugins.plants import Species as Species
from bauble.plugins.plants import SpeciesNote as SpeciesNote
from bauble.plugins.plants import VernacularName as VernacularName
from bauble.plugins.plants.geography import GeographicArea
from sqlalchemy import Boolean, Integer, select
from sqlalchemy.orm import mapped_column

family_data: Any
logger: Any = logging.getLogger(__name__)

# Test Data Definitions
family_data = [
    {"id": 1, "epithet": "Orchidaceae", "qualifier": None},
    {"id": 2, "epithet": "Myrtaceae"},
]
genus_data: Any = [
    {"id": 1, "epithet": "Calopogon", "family_id": 1, "author": "R. Br."},
    {"id": 2, "epithet": "Panisea", "family_id": 1},
]
species_data: Any = [
    {"id": 1, "epithet": "tuberosus", "genus_id": 1, "author": None},
    {"id": 2, "epithet": "albiflora", "genus_id": 2, "author": "(Ridl.) Seidenf."},
    {"id": 3, "epithet": "distelidia", "genus_id": 2, "author": "I.D.Lund"},
    {"id": 4, "epithet": "zeylanica", "genus_id": 2, "author": "(Hook.f.) Aver."},
]
species_note_test_data: Any = [
    {"id": 1, "species_id": 18, "category": "CITES", "note": "I"},
    {"id": 2, "species_id": 20, "category": "IUCN", "note": "LC"},
    {"id": 3, "species_id": 18, "category": "<price>", "note": "19.50"},
]
accession_data: Any = [
    {"id": 1, "species_id": 1, "code": "2015.0001"},
    {"id": 2, "species_id": 1, "code": "2015.0002"},
    {"id": 3, "species_id": 1, "code": "2015.0003", "private": True},
]
location_data: Any = [{"id": 1, "code": "1"}]
plant_data: Any = [
    {"id": 1, "accession_id": 1, "location_id": 1, "code": "1", "quantity": 1},
    {"id": 2, "accession_id": 3, "location_id": 1, "code": "1", "quantity": 1},
]


class TestImporter(CSVImporter):
    """
    Custom CSVImporter with enhanced error handling.
    """

    def on_error(self, exc) -> None:
        """
        Logs and raises any exceptions encountered during import.
        """
        logger.debug(exc)
        raise


@pytest.fixture
def test_directory() -> Generator[Any, None, None]:
    """
    Fixture for setting up and tearing down a temporary directory for tests.
    """
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path)


@pytest.fixture
def setup_database() -> None:
    """
    Fixture for setting up test data in the database.
    """
    plants_test.setUp_data()
    garden_test.setUp_data()


@pytest.fixture
def setup_test_files(test_directory):
    """
    Fixture to set up test files for CSV imports.
    """

    def create_file(filename, data, fields):
        file_path = os.path.join(test_directory, filename)
        with open(file_path, "w") as f:
            format_options = {
                "delimiter": ",",
                "quoting": QUOTE_STYLE,
                "quotechar": QUOTE_CHAR,
            }
            f.write(",".join(fields) + "\n")
            writer = csv.DictWriter(f, fields, **format_options)
            writer.writerows(data)
        return file_path

    return create_file


class TestCSV:
    """
    Test suite for CSV import/export functionality.
    """

    def test_import_self_referential_table(
        self, db_session, test_directory, setup_test_files
    ) -> None:
        """
        Test tables with self-referential relationships are imported in order.
        """
        geo_data = [
            {"id": 3, "name": "3", "parent_id": 1},
            {"id": 1, "name": "1", "parent_id": None},
            {"id": 2, "name": "2", "parent_id": 1},
        ]
        fields = list(geo_data[0].keys())
        filename = setup_test_files("geographic_area.txt", geo_data, fields)

        importer = TestImporter()
        importer.start([filename], force=True)

    def test_import_bool_column(
        self, db_session, test_directory, setup_test_files
    ) -> None:
        """
        Test importing CSV data with a boolean column.
        """

        class BoolTest(Base):
            __tablename__ = "bool_test"
            id: Mapped[int] = mapped_column(Integer, primary_key=True)
            col1 : Mapped[bool]= mapped_column(Boolean, default=False)

        BoolTest.__table__.create(bind=engine)

        data = [
            {"id": 1, "col1": "True"},
            {"id": 2, "col1": "False"},
            {"id": 3, "col1": ""},
        ]
        fields = list(data[0].keys())
        filename = setup_test_files("bool_test.txt", data, fields)

        importer = TestImporter()
        importer.start([filename], force=True)

        t = db_session.get(BoolTest, 1)
        assert t.col1 is True

        t = db_session.get(BoolTest, 2)
        assert t.col1 is False

        t = db_session.get(BoolTest, 3)
        assert t.col1 is False

        BoolTest.__table__.drop(bind=engine)

    def test_with_open_connection(
        self, db_session, test_directory, setup_test_files
    ) -> None:
        """
        Test that imports don't stall if a connection is open to the same table.
        """
        db_session.execute(select(Family)).scalars()

        family_data = [
            {"id": 1, "epithet": "Orchidaceae", "qualifier": None},
            {"id": 2, "epithet": "Myrtaceae"},
        ]
        fields = list(family_data[0].keys())
        filename = setup_test_files("family.txt", family_data, fields)

        importer = TestImporter()
        importer.start([filename], force=True)

        db_session.execute(select(Family)).scalars()

    def test_import_use_default(
        self, db_session, test_directory, setup_test_files
    ) -> None:
        """
        Test importing a CSV file applies default values to missing columns.
        """
        family_data = [
            {"id": 1, "epithet": "Orchidaceae", "qualifier": None},
            {"id": 2, "epithet": "Myrtaceae"},
        ]
        fields = list(family_data[0].keys())
        filename = setup_test_files("family.txt", family_data, fields)

        importer = TestImporter()
        importer.start([filename], force=True)

        family = (
            db_session.execute(select(Family).where(Family.id == 1)).scalars().one()
        )
        assert family.qualifier == ""

    def test_export_none_is_empty(self, db_session, test_directory) -> None:
        """
        Test exporting a CSV file where None values are represented as empty.
        """
        species = Species(genus_id=1, epithet="sp")
        db_session.add(species)
        if db_session.in_transaction():
            db_session.commit()

        temp_path = mkdtemp()
        exporter = CSVExporter()
        exporter.start(temp_path)

        with open(os.path.join(temp_path, "species.txt")) as f:
            reader = csv.DictReader(f)
            row = next(reader)
            assert row._mapping["cv_group"] == ""


class TestCSV2:
    """
    Test suite for CSV import/export and additional edge cases.
    """

    def test_sequences(self, db_session) -> None:
        """
        Test that sequences are correctly updated after imports.
        """
        from sqlalchemy import text

        # Import family data
        filename = os.path.join("bauble", "plugins", "plants", "default", "family.txt")
        importer = CSVImporter()
        importer.start([filename], force=True)

        # Check sequence handling
        highest_id = len(open(filename).readlines()) - 1
        conn = engine.connect()

        if engine.name == "postgresql":
            stmt = text("SELECT currval('family_id_seq');")
            currval = conn.execute(stmt).scalar_one_or_none()
            assert currval == 0
        elif engine.name == "sqlite":
            stmt = text("SELECT max(id) from family;")
            nextval = conn.execute(stmt).scalar_one_or_none() + 1
        else:
            pytest.fail(f"Unsupported engine type: {engine.name}")

        from sqlalchemy import text

        maxid = conn.execute(text("SELECT max(id) FROM family")).scalar_one_or_none()
        assert (
            nextval > highest_id
        ), f"Bad sequence: highest_id({highest_id}) > nextval({nextval}) -- {maxid}"

    def test_import(self, temp_directory) -> None:
        """
        Test import functionality by exporting and re-importing test data.
        """
        # Export all test data
        exporter = CSVExporter()
        exporter.start(temp_directory)

        # Re-import all exported files
        filenames = os.listdir(temp_directory)
        importer = CSVImporter()

        # Import twice to test for idempotency and regression handling
        importer.start(
            [os.path.join(temp_directory, name) for name in filenames], force=True
        )
        importer.start(
            [os.path.join(temp_directory, name) for name in filenames], force=True
        )

    def test_unicode(self, db_session) -> None:
        """
        Test importing and handling Unicode strings.
        """
        geo_data = {"name": "Galápagos"}
        stmt = GeographicArea.__table__.insert().values(geo_data)
        db_session.execute(stmt)
        db_session.commit()

        # Query and validate the Unicode handling
        query = db_session.execute(select(GeographicArea)).scalars()
        row_name = [r.name for r in query.all() if r.name.startswith("Gal")][0]
        assert row_name == geo_data["name"]

    def test_export(self, temp_directory, db_session) -> None:
        """
        Test export functionality to ensure data integrity.
        """
        # Export all test data
        exporter = CSVExporter()
        exporter.start(temp_directory)

        # Validate exported files
        exported_files = os.listdir(temp_directory)
        assert len(exported_files) > 0

        # Example validation of content (add specific checks if needed)
        for filename in exported_files:
            with open(os.path.join(temp_directory, filename)) as f:
                reader = csv.reader(f)
                rows = list(reader)
                assert len(rows) > 1  # Header + at least one row


class MockExportView:
    """
    Mock class for simulating export view interactions.
    """

    __selection: Any

    def widget_set_value(self, *args) -> None:
        pass

    def widget_get_value(self, *args) -> None:
        pass

    def connect_signals(self, *args) -> None:
        pass

    def connect(self, *args) -> None:
        pass

    def set_selection(self, a) -> None:
        self.__selection = a

    def get_selection(self):
        return self.__selection

@pytest.fixture
def temp_file() -> Generator[Any, None, None]:
    """
    Fixture to create and clean up a temporary file for tests.
    """
    handle, path = mkstemp()
    os.close(handle)
    yield path
    os.remove(path)


@pytest.fixture
def populate_database(db_session):
    """
    Fixture to populate the database with test data.
    """
    test_data = [
        (Family, family_data),
        (Genus, genus_data),
        (Species, species_data),
        (Accession, accession_data),
        (Location, location_data),
        (Plant, plant_data),
    ]

    objects = []
    for klass, data in test_data:
        for entry in data:
            obj = klass(**entry)
            db_session.add(obj)
            objects.append(obj)
    if db_session.in_transaction():
        db_session.commit()
    return objects


class TestJSONExport:
    """
    Test suite for JSON export functionality.
    """

    def test_export_empty_selection_writes_complete_database(
        self, temp_file, populate_database
    ) -> None:
        exporter = JSONExporter(MockView())
        exporter.view.selection = None
        exporter.selection_based_on = "sbo_selection"
        exporter.include_private = False
        exporter.filename = temp_file
        exporter.run()

        # Verify the generated file
        with open(temp_file) as f:
            result = json.load(f)

        assert len(result) == 14

        families = [
            i for i in result if i["object"] == "taxon" and i["rank"] == "familia"
        ]
        assert len(families) == 2

        genera = [i for i in result if i["object"] == "taxon" and i["rank"] == "genus"]
        assert len(genera) == 2

        species = [
            i for i in result if i["object"] == "taxon" and i["rank"] == "species"
        ]
        assert len(species) == 4

        target = [
            {"epithet": "Orchidaceae", "object": "taxon", "rank": "familia"},
            {"epithet": "Myrtaceae", "object": "taxon", "rank": "familia"},
            {
                "author": "R. Br.",
                "epithet": "Calopogon",
                "ht-epithet": "Orchidaceae",
                "ht-rank": "familia",
                "object": "taxon",
                "rank": "genus",
            },
            {
                "epithet": "Panisea",
                "ht-epithet": "Orchidaceae",
                "ht-rank": "familia",
                "object": "taxon",
                "rank": "genus",
            },
            {
                "ht-epithet": "Calopogon",
                "hybrid": False,
                "object": "taxon",
                "ht-rank": "genus",
                "rank": "species",
                "epithet": "tuberosus",
            },
            {
                "ht-epithet": "Panisea",
                "hybrid": False,
                "object": "taxon",
                "ht-rank": "genus",
                "rank": "species",
                "author": "(L.) Britton",
                "epithet": "albiflora",
                "author": "(Ridl.) Seidenf.",
            },
            {
                "ht-epithet": "Panisea",
                "hybrid": False,
                "object": "taxon",
                "ht-rank": "genus",
                "rank": "species",
                "author": "(L.) Britton",
                "epithet": "distelidia",
                "author": "I.D.Lund",
            },
            {
                "ht-epithet": "Panisea",
                "hybrid": False,
                "object": "taxon",
                "ht-rank": "genus",
                "rank": "species",
                "author": "(L.) Britton",
                "epithet": "zeylanica",
                "author": "(Hook.f.) Aver.",
            },
            {
                "code": "2015.0001",
                "object": "accession",
                "private": False,
                "species": "Calopogon tuberosus",
            },
            {
                "code": "2015.0002",
                "object": "accession",
                "private": False,
                "species": "Calopogon tuberosus",
            },
            {
                "code": "2015.0003",
                "object": "accession",
                "private": True,
                "species": "Calopogon tuberosus",
            },
            {"code": "1", "object": "location"},
            {
                "accession": "2015.0001",
                "code": "1",
                "location": "1",
                "memorial": False,
                "object": "plant",
                "quantity": 1,
            },
            {
                "accession": "2015.0003",
                "code": "1",
                "location": "1",
                "memorial": False,
                "object": "plant",
                "quantity": 1,
            },
        ]

        # Final asserts
        assert len(result) == len(target)
        for obj in result:
            assert obj in target
        for obj in target:
            assert obj in result

    def test_when_selection_huge_ask(self) -> None:
        """
        Test that the export process prompts the user when the selection is too large.
        """
        view = MockView()
        exporter = JSONExporter(view)
        exporter.selection_based_on = "sbo_selection"
        view.selection = list(range(5000))  # Simulate a large selection
        view.reply_yes_no_dialog = [False]  # Simulate user response to dialog
        exporter.run()

        assert "run_yes_no_dialog" in getattr(view, "invoked", [])
        assert view.reply_yes_no_dialog == []

    def test_writes_full_taxonomic_info(self, temp_file, db_session) -> None:
        """
        Test exporting one family with full taxonomic information below family level.
        """

        from sqlalchemy import select

        stmt = select(Family).where(Family.epithet == "Orchidaceae")
        selection = db_session.execute(stmt).scalars().all()

        exporter = JSONExporter(MockView())
        exporter.selection_based_on = "sbo_selection"
        exporter.include_private = False
        exporter.view.selection = selection
        exporter.filename = temp_file
        exporter.run()

        with open(temp_file) as f:
            result = json.load(f)

        assert len(result) == 1
        assert result[0]["rank"] == "familia"
        assert result[0]["epithet"] == "Orchidaceae"

    def test_writes_partial_taxonomic_info(self, temp_file, db_session) -> None:
        """
        Test exporting one genus with all species below genus level.
        """
        from sqlalchemy import select

        stmt = select(Genus).where(Genus.epithet == "Calopogon")
        selection = db_session.execute(stmt).scalars().all()

        exporter = JSONExporter(MockView())
        exporter.view.selection = selection
        exporter.selection_based_on = "sbo_selection"
        exporter.include_private = False
        exporter.filename = temp_file
        exporter.run()

        with open(temp_file) as f:
            result = json.load(f)

        assert len(result) == 1
        assert result[0]["rank"] == "genus"
        assert result[0]["epithet"] == "Calopogon"
        assert result[0]["ht-rank"] == "familia"
        assert result[0]["ht-epithet"] == "Orchidaceae"
        assert result[0]["author"] == "R. Br."

    def test_writes_partial_taxonomic_info_species(self, temp_file, db_session) -> None:
        """
        Test exporting one species and ensuring all species below genus level are exported.
        """
        from sqlalchemy import select

        stmt = (
            select(Species)
            .join(Genus)
            .where(Species.epithet == "tuberosus", Genus.epithet == "Calopogon")
        )
        selection = db_session.execute(stmt).scalars().all()
        exporter = JSONExporter(MockView())
        exporter.view.selection = selection
        exporter.selection_based_on = "sbo_selection"
        exporter.include_private = False
        exporter.filename = temp_file
        exporter.run()

        with open(temp_file) as f:
            result = json.load(f)

        assert len(result) == 1
        assert result[0]["rank"] == "species"
        assert result[0]["epithet"] == "tuberosus"
        assert result[0]["ht-rank"] == "genus"
        assert result[0]["ht-epithet"] == "Calopogon"
        assert result[0]["hybrid"] is False

    def test_export_single_species_with_notes(self, temp_file, db_session) -> None:
        """
        Test exporting a single species with associated notes.
        """
        # Select species and add a note
        from sqlalchemy import select

        stmt = (
            select(Species)
            .join(Genus)
            .where(Species.epithet == "tuberosus", Genus.epithet == "Calopogon")
        )
        selection = db_session.execute(stmt).scalars().all()
        note = SpeciesNote(category="<coords>", note="{1: 1, 2: 2}")
        note.species = selection[0]
        db_session.add(note)
        if db_session.in_transaction():
            db_session.commit()

        # Export
        exporter = JSONExporter(MockView())
        exporter.view.selection = selection
        exporter.selection_based_on = "sbo_selection"
        exporter.include_private = False
        exporter.filename = temp_file
        exporter.run()

        # Validate
        with open(temp_file) as f:
            result = json.load(f)

        assert len(result) == 2
        assert result[0] == {
            "ht-epithet": "Calopogon",
            "hybrid": False,
            "object": "taxon",
            "ht-rank": "genus",
            "rank": "species",
            "epithet": "tuberosus",
        }
        date_dict = result[1].pop("date")
        assert result[1] == {
            "category": "<coords>",
            "note": "{1: 1, 2: 2}",
            "species": "Calopogon tuberosus",
            "object": "species_note",
        }
        assert set(date_dict.keys()) == {"millis", "__class__"}

    def test_export_single_species_with_vernacular_name(
        self, temp_file, db_session
    ) -> None:
        """
        Test exporting a single species with a vernacular name.
        """
        # Select species and add a vernacular name
        from sqlalchemy import select

        stmt = (
            select(Species)
            .join(Genus)
            .where(Species.epithet == "tuberosus", Genus.epithet == "Calopogon")
        )
        selection = db_session.execute(stmt).scalars().all()
        vernacular_name = VernacularName(language="it", name="orchidea")
        selection[0].vernacular_names.append(vernacular_name)
        db_session.add(vernacular_name)
        if db_session.in_transaction():
            db_session.commit()

        # Export
        exporter = JSONExporter(MockView())
        exporter.view.selection = selection
        exporter.selection_based_on = "sbo_selection"
        exporter.include_private = False
        exporter.filename = temp_file
        exporter.run()

        # Validate
        with open(temp_file) as f:
            result = json.load(f)

        assert len(result) == 2
        assert result[0] == {
            "ht-epithet": "Calopogon",
            "hybrid": False,
            "object": "taxon",
            "ht-rank": "genus",
            "rank": "species",
            "epithet": "tuberosus",
        }
        assert result[1] == {
            "language": "it",
            "name": "orchidea",
            "object": "vernacular_name",
            "species": "Calopogon tuberosus",
        }

    def test_partial_taxonomic_with_synonymy(self, temp_file, db_session) -> None:
        """
        Test exporting one genus that is a synonym with its accepted name.
        """
        # Create taxonomic structure
        from sqlalchemy import select

        stmt = select(Family).where(Family.epithet == "Orchidaceae")
        family = db_session.execute(stmt).scalars().one()

        accepted_genus = Genus(family=family, epithet="Bulbophyllum")
        synonym_genus = Genus(family=family, epithet="Zygoglossum")
        accepted_genus.synonyms.append(synonym_genus)
        db_session.add_all([family, accepted_genus, synonym_genus])
        if db_session.in_transaction():
            db_session.commit()

        # Select synonym genus
        stmt = select(Genus).where(Genus.epithet == "Zygoglossum")
        selection = db_session.execute(stmt).scalars().all()

        # Export
        exporter = JSONExporter(MockView())
        exporter.view.selection = selection
        exporter.selection_based_on = "sbo_selection"
        exporter.include_private = True
        exporter.filename = temp_file
        exporter.run()

        # Validate
        with open(temp_file) as f:
            result = json.load(f)

        assert len(result) == 1
        assert result[0]["rank"] == "genus"
        assert result[0]["epithet"] == "Zygoglossum"
        assert result[0]["ht-rank"] == "familia"
        assert result[0]["ht-epithet"] == "Orchidaceae"
        accepted = result[0]["accepted"]
        assert isinstance(accepted, dict)
        assert accepted["rank"] == "genus"
        assert accepted["epithet"] == "Bulbophyllum"
        assert accepted["ht-rank"] == "familia"
        assert accepted["ht-epithet"] == "Orchidaceae"

    def test_export_ignores_private_if_sbo_selection(self, temp_file) -> None:
        """
        Test exporting accessions ignoring private entries when `include_private` is False.
        """
        # Select all accessions
        exporter = JSONExporter(MockView())
        selection = [obj for obj in self if isinstance(obj, Accession)]
        non_private = [acc for acc in selection if not acc.private]

        # Assertions on selection
        assert len(selection) == 3
        assert len(non_private) == 2

        # Export
        exporter.view.selection = selection
        exporter.selection_based_on = "sbo_selection"
        exporter.include_private = False
        exporter.filename = temp_file
        exporter.run()

        # Validate
        with open(temp_file) as f:
            result = json.load(f)

        assert len(result) == 3

    def test_export_non_private_if_sbo_accessions(self, populate_database) -> None:
        """
        Test exporting non-private accessions when `include_private` is False.
        """
        exporter = JSONExporter(MockView())
        exporter.view.selection = None
        exporter.selection_based_on = "sbo_accessions"
        exporter.include_private = False
        exporter.filename = self
        exporter.run()

        with open(self) as f:
            result = json.load(f)

        assert len(result) == 5

    def test_export_private_if_sbo_accessions(self, populate_database) -> None:
        """
        Test exporting all accessions, including private, when `include_private` is True.
        """
        exporter = JSONExporter(MockView())
        exporter.view.selection = None
        exporter.selection_based_on = "sbo_accessions"
        exporter.include_private = True
        exporter.filename = self
        exporter.run()

        with open(self) as f:
            result = json.load(f)

        assert len(result) == 6

    def test_export_non_private_if_sbo_plants(self, populate_database) -> None:
        """
        Test exporting non-private plants when `include_private` is False.
        """
        exporter = JSONExporter(MockView())
        exporter.view.selection = None
        exporter.selection_based_on = "sbo_plants"
        exporter.include_private = False
        exporter.filename = self
        exporter.run()

        with open(self) as f:
            result = json.load(f)

        assert len(result) == 6

    def test_export_private_if_sbo_plants(self, populate_database) -> None:
        """
        Test exporting all plants, including private, when `include_private` is True.
        """
        exporter = JSONExporter(MockView())
        exporter.view.selection = None
        exporter.selection_based_on = "sbo_plants"
        exporter.include_private = True
        exporter.filename = self
        exporter.run()

        with open(self) as f:
            result = json.load(f)

        assert len(result) == 8

    def test_export_with_vernacular(self, db_session) -> None:
        """
        Test exporting a genus with a vernacular name.
        """
        # Setup
        sola = Family(epithet="Solanaceae")
        brug = Genus(family=sola, epithet="Brugmansia")
        arbo = Species(genus=brug, epithet="arborea")
        vern = VernacularName(species=arbo, language="es", name="Floripondio")
        db_session.add_all([sola, brug, arbo, vern])
        if db_session.in_transaction():
            db_session.commit()

        # Action
        exporter = JSONExporter(MockView())
        exporter.view.selection = None
        exporter.selection_based_on = "sbo_taxa"
        exporter.include_private = False
        exporter.filename = self
        exporter.run()

        # Validate
        with open(self) as f:
            result = json.load(f)

        vern_from_json = [
            item for item in result if item["object"] == "vernacular_name"
        ]
        assert len(vern_from_json) == 1
        assert vern_from_json[0]["language"] == "es"

    def test_on_btnbrowse_clicked() -> None:
        """
        Test browse button updates the filename correctly.
        """
        view = MockView()
        exporter = JSONExporter(view)
        view.reply_file_chooser_dialog = ["/tmp/test.json"]
        exporter.on_btnbrowse_clicked("button")
        exporter.on_text_entry_changed("filename")
        assert exporter.filename == "/tmp/test.json"
        assert JSONExporter.last_folder == "/tmp"

    def test_includes_sources(self, db_session) -> None:
        """
        Test exporting accessions with source details included.
        """
        # Precondition: Setup source and contact
        from sqlalchemy import select

        stmt = select(Accession)
        accession = db_session.execute(stmt).scalars().first()
        # Ensure test is meaningful
        assert (
            accession is not None
        ), "Test requires at least one accession in the database."

        source = Source()
        contact = Contact(name="Summit")
        source.source_detail = contact
        accession.source = source
        db_session.add_all([source, contact, accession])
        if db_session.in_transaction():
            db_session.commit()

        # Action
        exporter = JSONExporter(MockView())
        exporter.view.selection = None
        exporter.selection_based_on = "sbo_accessions"
        exporter.include_private = True
        exporter.filename = self
        exporter.run()

        # Validate
        with open(self) as f:
            result = json.load(f)

        contacts_from_json = [
            item for item in result if item.get("object") == "contact"
        ]
        accessions_from_json = [
            item for item in result if item.get("object") == "accession"
        ]
        accessions_with_contact = [
            item
            for item in result
            if item.get("object") == "accession" and "contact" in item
        ]

        assert len(contacts_from_json) == 1
        assert contacts_from_json[0]["name"] == "Summit"
        assert len(accessions_from_json) == 3
        assert len(accessions_with_contact) == 1
        assert accessions_with_contact[0]["contact"] == "Summit"


@pytest.fixture
def temp_file2():
    """Fixture for creating and cleaning up a temporary file."""
    _, path = tempfile.mkstemp()
    yield path
    os.remove(path)


def test_import_new_inserts(temp_file2, db_session) -> None:
    """Test importing a new taxon adds it to the database."""
    json_string = (
        '[{"rank": "Genus", "epithet": "Neogyna", '
        '"ht-rank": "Familia", "ht-epithet": "Orchidaceae", '
        '"author": "Rchb. f."}]'
    )
    with open(temp_file, "w") as f:
        f.write(json_string)

    stmt = select(Genus).where(Genus.epithet == "Neogyna")
    assert db_session.execute(stmt).scalars().first() is None

    importer = JSONImporter(MockView())
    importer.filename = temp_file2
    importer.on_btnok_clicked(None)

    assert db_session.execute(stmt).scalars().first() is not None


def test_import_new_inserts_lowercase(temp_file2, db_session) -> None:
    """Test importing a new taxon adds it to the database with lowercase rank."""
    json_string = (
        '[{"rank": "genus", "epithet": "Neogyna", "ht-rank"'
        ': "familia", "ht-epithet": "Orchidaceae", "author": "Rchb. f."}]'
    )
    with open(temp_file2, "w") as f:
        f.write(json_string)

    stmt = select(Genus).where(Genus.epithet == "Neogyna")
    assert db_session.execute(stmt).scalars().first() is None

    importer = JSONImporter(MockView())
    importer.filename = temp_file2
    importer.on_btnok_clicked(None)

    assert db_session.execute(stmt).scalars().first() is not None


def test_import_new_with_non_timestamped_note(temp_file2, db_session) -> None:
    """Test importing a new taxon with a non-timestamped note."""
    json_string = (
        '[{"ht-epithet": "Calopogon", "epithet": "pallidus", "author": "Chapm.", '
        ' "rank": "Species", "ht-rank": "Genus", "hybrid": false}, '
        ' {"object": "species_note", "species": "Calopogon pallidus", "category": "<coords>", "note": "{lat: 8.5, lon: -80}"}]'
    )
    with open(temp_file, "w") as f:
        f.write(json_string)

    importer = JSONImporter(MockView())
    importer.filename = temp_file2
    importer.on_btnok_clicked(None)

    species = Species.retrieve_or_create(
        db_session, {"ht-epithet": "Calopogon", "epithet": "pallidus"}
    )
    assert species.author == "Chapm."
    assert len(species.notes) == 1


def test_import_new_with_three_array_notes(temp_file2, db_session) -> None:
    """Test importing a new taxon with three identical notes."""
    json_string = (
        '[{"ht-epithet": "Calopogon", "epithet": "pallidus", "author": "Chapm.", '
        ' "rank": "Species", "ht-rank": "Genus", "hybrid": false}, '
        ' {"object": "species_note", "species": "Calopogon pallidus", "category": "[x]", "note": "1"}, '
        ' {"object": "species_note", "species": "Calopogon pallidus", "category": "[x]", "note": "1"}, '
        ' {"object": "species_note", "species": "Calopogon pallidus", "category": "[x]", "note": "1"}]'
    )
    with open(temp_file2, "w") as f:
        f.write(json_string)

    importer = JSONImporter(MockView())
    importer.filename = temp_file2
    importer.on_btnok_clicked(None)

    species = Species.retrieve_or_create(
        db_session, {"ht-epithet": "Calopogon", "epithet": "pallidus"}
    )
    assert species.author == "Chapm."
    assert len(species.notes) == 3


def test_import_existing_updates(temp_file2, db_session) -> None:
    """Test importing an existing taxon updates it."""
    json_string = (
        '[{"rank": "Species", "epithet": "tuberosus", "ht-rank"'
        ': "Genus", "ht-epithet": "Calopogon", "hybrid": false, "author"'
        ': "Britton et al."}]'
    )
    with open(temp_file2, "w") as f:
        f.write(json_string)

    species = Species.retrieve_or_create(
        db_session, {"ht-epithet": "Calopogon", "epithet": "tuberosus"}
    )
    assert species.author is None

    importer = JSONImporter(MockView())
    importer.filename = temp_file2
    importer.on_btnok_clicked(None)

    species = Species.retrieve_or_create(
        db_session, {"ht-epithet": "Calopogon", "epithet": "tuberosus"}
    )
    assert species.author == "Britton et al."


def test_import_ignores_id_new(temp_file2, db_session) -> None:
    """Test importing a new taxon disregards the provided ID."""
    json_string = (
        '[{"rank": "Genus", "epithet": "Neogyna", '
        '"ht-rank": "Familia", "ht-epithet": "Orchidaceae", '
        '"author": "Rchb. f.", "id": 1}]'
    )
    with open(temp_file2, "w") as f:
        f.write(json_string)

    importer = JSONImporter(MockView())
    importer.filename = temp_file2
    importer.on_btnok_clicked(None)

    genus = Genus.retrieve_or_create(db_session, {"epithet": "Neogyna"})
    assert genus.id != 1


def test_import_ignores_id_updating(temp_file2, db_session) -> None:
    """Test importing an existing taxon disregards the provided ID."""
    species = Species.retrieve_or_create(
        db_session, {"ht-epithet": "Calopogon", "epithet": "tuberosus"}
    )
    initial_id = species.id

    json_string = (
        '[{"rank": "Species", "epithet": "tuberosus", '
        '"ht-rank": "Genus", "ht-epithet": "Calopogon", "hybrid": false, '
        '"id": 8}]'
    )
    with open(temp_file2, "w") as f:
        f.write(json_string)

    importer = JSONImporter(MockView())
    importer.filename = temp_file2
    importer.on_btnok_clicked(None)

    species = Species.retrieve_or_create(
        db_session, {"ht-epithet": "Calopogon", "epithet": "tuberosus"}
    )
    assert species.id == initial_id


@pytest.fixture
def temp_file3():
    """Fixture for creating and cleaning up a temporary file."""
    _, path = tempfile.mkstemp()
    yield path
    os.remove(path)


def test_import_species_to_new_genus_fails(temp_file3, db_session) -> None:
    """Test importing new species referring to a non-existing genus logs a warning."""
    json_string = (
        '[{"rank": "Species", "epithet": "lawrenceae", '
        '"ht-rank": "Genus", "ht-epithet": "Aerides", "author": "Rchb. f."}]'
    )
    with open(temp_file3, "w") as f:
        f.write(json_string)

    importer = JSONImporter(MockView())
    importer.filename = temp_file3
    importer.on_btnok_clicked(None)

    sp = (
        db_session.execute(
            select(Species)
            .where(Species.epithet == "lawrenceae")
            .join(Genus)
            .where(Genus.epithet == "Aerides")
        )
        .scalars()
        .all()
    )
    assert sp == []


def test_import_species_to_new_genus_and_family(temp_file3, db_session) -> None:
    """Test importing a species referring to a non-existing genus with a specified family."""
    sp = (
        db_session.execute(
            select(Species)
            .where(Species.epithet == "lawrenceae")
            .join(Genus)
            .where(Genus.epithet == "Aerides")
        )
        .scalars()
        .all()
    )
    assert sp == []

    json_string = (
        '[{"rank": "Species", "epithet": "lawrenceae", '
        '"ht-rank": "Genus", "ht-epithet": "Aerides", '
        '"familia": "Orchidaceae", "author": "Rchb. f."}]'
    )
    with open(temp_file3, "w") as f:
        f.write(json_string)

    importer = JSONImporter(MockView())
    importer.filename = temp_file3
    importer.on_btnok_clicked(None)
    if db_session.in_transaction():
        db_session.commit()

    sp = (
        db_session.execute(
            select(Species)
            .where(Species.epithet == "lawrenceae")
            .join(Genus)
            .where(Genus.epithet == "Aerides")
        )
        .scalars()
        .all()
    )
    assert len(sp) == 1

    genus = (
        db_session.execute(select(Genus).where(Genus.epithet == "Aerides"))
        .scalars()
        .first()
    )
    family = (
        db_session.execute(select(Family).where(Family.epithet == "Orchidaceae"))
        .scalars()
        .first()
    )

    assert sp[0].genus == genus
    assert genus.family == family


def test_import_with_synonym(temp_file3, db_session) -> None:
    """Test importing a taxon with an `accepted` field imports both taxa."""
    json_string = (
        '[{"rank": "Genus", "epithet": "Zygoglossum", '
        '"ht-rank": "Familia", "ht-epithet": "Orchidaceae", '
        '"author": "Reinw.", "accepted": {"rank": "Genus", '
        '"epithet": "Bulbophyllum", "ht-rank": "Familia", '
        '"ht-epithet": "Orchidaceae", "author": "Thouars"}}]'
    )
    with open(temp_file3, "w") as f:
        f.write(json_string)

    importer = JSONImporter(MockView())
    importer.filename = temp_file3
    importer.on_btnok_clicked(None)
    if db_session.in_transaction():
        db_session.commit()

    synonym = (
        db_session.execute(select(Genus).where(Genus.epithet == "Zygoglossum"))
        .scalars()
        .first()
    )
    accepted = (
        db_session.execute(select(Genus).where(Genus.epithet == "Bulbophyllum"))
        .scalars()
        .first()
    )

    assert synonym is not None
    assert synonym.accepted == accepted
    assert accepted is not None


def test_use_author_to_break_ties(temp_file3, db_session) -> None:
    """Test importing homonym taxa is possible if authorship breaks ties."""
    ataceae = Family(epithet="Anacampserotaceae")
    linnaeus = Genus(family=ataceae, epithet="Anacampseros", author="L.")
    claceae = Family(epithet="Crassulaceae")
    miller = Genus(family=claceae, epithet="Anacampseros", author="Mill.")
    db_session.add_all([claceae, ataceae, linnaeus, miller])
    if db_session.in_transaction():
        db_session.commit()

    json_string = (
        '{"author": "Mill.", "epithet": "Anacampseros", '
        '"ht-epithet": "Crassulaceae", "ht-rank": "familia", '
        '"object": "taxon", "rank": "genus", "accepted": {'
        '"author": "L.", "epithet": "Sedum", "ht-epithet": '
        '"Crassulaceae", "ht-rank": "familia", "object": "taxon", '
        '"rank": "genus"}}'
    )
    with open(temp_file3, "w") as f:
        f.write(json_string)

    importer = JSONImporter(MockView())
    importer.filename = temp_file3
    importer.on_btnok_clicked(None)
    if db_session.in_transaction():
        db_session.commit()

    accepted = Genus.retrieve_or_create(db_session, {"epithet": "Sedum"}, create=False)
    assert accepted.__class__ == Genus
    assert miller.accepted == accepted


def test_import_create_update(temp_file3, db_session) -> None:
    """Test that existing records are updated and new records are created."""
    ataceae = Family(epithet="Anacampserotaceae")
    linnaeus = Genus(family=ataceae, epithet="Anacampseros")
    db_session.add_all([ataceae, linnaeus])
    if db_session.in_transaction():
        db_session.commit()

    json_string = (
        '[{"author": "L.", "epithet": "Anacampseros", '
        '"ht-epithet": "Anacampserotaceae", "ht-rank": "familia", '
        '"object": "taxon", "rank": "genus"}, {"author": "L.", '
        '"epithet": "Sedum", "ht-epithet": "Crassulaceae", '
        '"ht-rank": "familia", "object": "taxon", '
        '"rank": "genus"}]'
    )
    with open(temp_file3, "w") as f:
        f.write(json_string)

    importer = JSONImporter(MockView())
    importer.filename = temp_file3
    importer.create = True
    importer.update = True
    importer.on_btnok_clicked(None)
    if db_session.in_transaction():
        db_session.commit()

    sedum = Genus.retrieve_or_create(db_session, {"epithet": "Sedum"}, create=False)
    anacampseros = Genus.retrieve_or_create(
        db_session, {"epithet": "Anacampseros"}, create=False
    )

    assert sedum.__class__ == Genus
    assert sedum.author == "L."
    assert anacampseros.__class__ == Genus
    assert anacampseros.author == "L."


@pytest.fixture
def temp_file4():
    """Fixture to create and clean up a temporary file."""
    _, path = tempfile.mkstemp()
    yield path
    os.remove(path)


def test_import_no_create_update(temp_file4, db_session) -> None:
    """Existing records get updated; non-existing records are not created."""
    # Setup
    ataceae = Family(epithet="Anacampserotaceae")
    linnaeus = Genus(family=ataceae, epithet="Anacampseros")
    db_session.add_all([ataceae, linnaeus])
    if db_session.in_transaction():
        db_session.commit()

    json_string = (
        '[{"author": "L.", "epithet": "Anacampseros", '
        '"ht-epithet": "Anacampserotaceae", "ht-rank": "familia", '
        '"object": "taxon", "rank": "genus"}, {"author": "L.", '
        '"epithet": "Sedum", "ht-epithet": "Crassulaceae", '
        '"ht-rank": "familia", "object": "taxon", '
        '"rank": "genus"}]'
    )
    with open(temp_file4, "w") as f:
        f.write(json_string)

    importer = JSONImporter(MockView())
    importer.filename = temp_file4
    importer.create = False
    importer.update = True
    importer.on_btnok_clicked(None)
    if db_session.in_transaction():
        db_session.commit()

    # Assertions
    sedum = Genus.retrieve_or_create(db_session, {"epithet": "Sedum"}, create=False)
    assert sedum is None

    anacampseros = Genus.retrieve_or_create(
        db_session, {"epithet": "Anacampseros"}, create=False
    )
    assert isinstance(anacampseros, Genus)
    assert anacampseros.author == "L."


def test_import_create_no_update(temp_file4, db_session) -> None:
    """Existing records remain untouched; non-existing records are created."""
    # Setup
    ataceae = Family(epithet="Anacampserotaceae")
    linnaeus = Genus(family=ataceae, epithet="Anacampseros")
    db_session.add_all([ataceae, linnaeus])
    if db_session.in_transaction():
        db_session.commit()

    json_string = (
        '[{"author": "L.", "epithet": "Anacampseros", '
        '"ht-epithet": "Anacampserotaceae", "ht-rank": "familia", '
        '"object": "taxon", "rank": "genus"}, {"author": "L.", '
        '"epithet": "Sedum", "ht-epithet": "Crassulaceae", '
        '"ht-rank": "familia", "object": "taxon", '
        '"rank": "genus"}]'
    )
    with open(temp_file4, "w") as f:
        f.write(json_string)

    importer = JSONImporter(MockView())
    importer.filename = temp_file4
    importer.create = True
    importer.update = False
    importer.on_btnok_clicked(None)
    if db_session.in_transaction():
        db_session.commit()

    # Assertions
    sedum = (
        db_session.execute(select(Genus).where(Genus.epithet == "Sedum"))
        .scalars()
        .first()
    )
    assert isinstance(sedum, Genus)
    assert sedum.author == "L."

    anacampseros = (
        db_session.execute(select(Genus).where(Genus.epithet == "Anacampseros"))
        .scalars()
        .first()
    )
    assert isinstance(anacampseros, Genus)
    assert anacampseros.author == ""


def test_on_btnbrowse_clicked() -> None:
    """Test that file browsing works as expected."""
    view = MockView()
    importer = JSONImporter(view)
    view.reply_file_chooser_dialog = ["/tmp/test.json"]
    importer.on_btnbrowse_clicked("button")
    importer.on_text_entry_changed("input_filename")

    assert importer.filename == "/tmp/test.json"
    assert JSONImporter.last_folder == "/tmp"


def test_import_contact(temp_file4, db_session) -> None:
    """Test importing a contact object."""
    json_string = '[{"name": "Summit", "object": "contact"}]'
    with open(temp_file4, "w") as f:
        f.write(json_string)

    importer = JSONImporter(MockView())
    importer.filename = temp_file4
    importer.create = True
    importer.update = True
    importer.on_btnok_clicked(None)
    if db_session.in_transaction():
        db_session.commit()

    stmt = select(Contact).where(Contact.name == "Summit")
    summit = db_session.execute(stmt).scalars().first()
    assert summit is not None


def test_json_serializer_datetime() -> None:
    """Test JSON serialization of datetime objects."""
    import datetime

    from .iojson import serializedatetime

    stamp = datetime.datetime(2011, 11, 11, 12, 13)
    result = serializedatetime(stamp)
    expected = {"millis": 1321013580000, "__class__": "datetime"}

    assert result == expected
