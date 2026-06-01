import os

import pytest
from sqlalchemy import inspect, text


pytestmark = pytest.mark.postgresql


REQUIRED_TABLES = {
    "bauble",
    "family",
    "genus",
    "species",
    "accession",
    "plant",
    "location",
    "source",
    "collection",
    "propagation",
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
