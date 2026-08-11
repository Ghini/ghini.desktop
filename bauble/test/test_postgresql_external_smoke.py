import os

import pytest
from sqlalchemy import inspect, text


pytestmark = pytest.mark.postgresql


REQUIRED_TABLES = {
    "bauble",
    "contact",
    "family",
    "genus",
    "species",
    "vernacular_name",
    "default_vernacular_name",
    "accession",
    "source",
    "collection",
    "plant",
    "location",
    "plant_prop",
    "propagation",
    "prop_seed",
    "species_note",
    "accession_note",
    "plant_note",
}


@pytest.fixture(scope="module")
def external_postgresql_uri():
    uri = os.environ.get("GHINI_EXTERNAL_POSTGRES_URI")
    if not uri:
        pytest.skip(
            "set GHINI_EXTERNAL_POSTGRES_URI or use scripts/docker-dev postgres-smoke"
        )
    return uri


@pytest.fixture(scope="module")
def external_postgresql_database(external_postgresql_uri):
    import bauble.db as db
    import bauble.error as error

    try:
        engine = db.open(external_postgresql_uri, verify=True)
    except error.VersionError:
        # The application permits opening older Ghini databases after warning.
        engine = db.open(external_postgresql_uri, verify=False)

    assert engine is not None
    assert engine.dialect.name.startswith("postgresql")

    try:
        yield db
    finally:
        db.Session.remove()
        if db.engine is not None:
            db.engine.dispose()


def test_external_postgresql_has_required_tables(external_postgresql_database):
    inspector = inspect(external_postgresql_database.engine)
    table_names = set(inspector.get_table_names())

    assert REQUIRED_TABLES <= table_names


def test_external_postgresql_can_read_core_counts(external_postgresql_database):
    with external_postgresql_database.engine.connect() as connection:
        counts = {
            table_name: connection.execute(
                text(f"select count(*) from {table_name}")
            ).scalar_one()
            for table_name in REQUIRED_TABLES
        }

    assert all(isinstance(count, int) for count in counts.values())
    assert all(count >= 0 for count in counts.values())


def test_external_postgresql_can_read_daily_join(
    external_postgresql_database,
):
    query = text(
        "select accession.code, species.epithet, genus.epithet, family.epithet "
        "from accession "
        "join species on accession.species_id = species.id "
        "join genus on species.genus_id = genus.id "
        "join family on genus.family_id = family.id "
        "order by accession.code "
        "limit 1"
    )

    with external_postgresql_database.engine.connect() as connection:
        rows = connection.execute(query).all()

    assert len(rows) <= 1


def test_external_postgresql_can_read_daily_plant_location_join(
    external_postgresql_database,
):
    query = text(
        "select plant.code, accession.code, location.code, "
        "species.epithet, genus.epithet, family.epithet "
        "from plant "
        "join accession on plant.accession_id = accession.id "
        "join location on plant.location_id = location.id "
        "join species on accession.species_id = species.id "
        "join genus on species.genus_id = genus.id "
        "join family on genus.family_id = family.id "
        "order by plant.code "
        "limit 1"
    )

    with external_postgresql_database.engine.connect() as connection:
        rows = connection.execute(query).all()

    assert len(rows) <= 1


def test_external_postgresql_can_read_source_contact_collection_join(
    external_postgresql_database,
):
    query = text(
        "select accession.code, source.sources_code, contact.name, "
        "collection.locale "
        "from source "
        "join accession on source.accession_id = accession.id "
        "left join contact on source.source_detail_id = contact.id "
        "left join collection on collection.source_id = source.id "
        "order by accession.code "
        "limit 1"
    )

    with external_postgresql_database.engine.connect() as connection:
        rows = connection.execute(query).all()

    assert len(rows) <= 1


def test_external_postgresql_can_read_vernacular_names_and_species_notes(
    external_postgresql_database,
):
    vernacular_query = text(
        "select species.epithet, vernacular_name.name, "
        "vernacular_name.language, "
        "default_vernacular_name.vernacular_name_id is not null "
        "from species "
        "left join vernacular_name on vernacular_name.species_id = species.id "
        "left join default_vernacular_name "
        "on default_vernacular_name.species_id = species.id "
        "and default_vernacular_name.vernacular_name_id = vernacular_name.id "
        "order by species.id, vernacular_name.id "
        "limit 1"
    )
    note_query = text(
        "select species.epithet, species_note.category, species_note.note "
        "from species_note "
        "join species on species_note.species_id = species.id "
        "order by species_note.id "
        "limit 1"
    )

    with external_postgresql_database.engine.connect() as connection:
        vernacular_rows = connection.execute(vernacular_query).all()
        note_rows = connection.execute(note_query).all()

    assert len(vernacular_rows) <= 1
    assert len(note_rows) <= 1


def test_external_postgresql_can_read_propagation_join(
    external_postgresql_database,
):
    query = text(
        "select propagation.prop_type, propagation.date, prop_seed.nseeds, "
        "prop_seed.date_sown, plant.code, accession.code "
        "from propagation "
        "left join plant_prop on propagation.id = plant_prop.propagation_id "
        "left join plant on plant_prop.plant_id = plant.id "
        "left join accession on plant.accession_id = accession.id "
        "left join prop_seed on propagation.id = prop_seed.propagation_id "
        "order by propagation.id "
        "limit 1"
    )

    with external_postgresql_database.engine.connect() as connection:
        rows = connection.execute(query).all()

    assert len(rows) <= 1


def test_external_postgresql_session_recovers_after_read_rollback(
    external_postgresql_database,
):
    session = external_postgresql_database.Session()

    try:
        assert session.execute(text("select 1")).scalar_one() == 1
        session.rollback()
        assert session.execute(text("select 1")).scalar_one() == 1
    finally:
        session.close()
        external_postgresql_database.Session.remove()
