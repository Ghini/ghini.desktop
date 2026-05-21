import os

import pytest
from sqlalchemy import text


pytestmark = pytest.mark.postgresql


@pytest.fixture(scope="module")
def postgresql_uri():
    uri = os.environ.get("GHINI_TEST_POSTGRES_URI")
    if not uri:
        pytest.skip(
            "set GHINI_TEST_POSTGRES_URI or use scripts/docker-dev postgres-check"
        )
    return uri


@pytest.fixture(scope="module")
def postgresql_database(postgresql_uri):
    import bauble.db as db

    engine = db.open(postgresql_uri, verify=False)
    assert engine is not None
    assert engine.dialect.name.startswith("postgresql")
    db.create(import_defaults=True)
    try:
        yield db
    finally:
        db.Session.remove()
        if db.engine is not None:
            db.engine.dispose()


def test_postgresql_database_create_imports_defaults(postgresql_database):
    with postgresql_database.engine.connect() as connection:
        family_count = connection.execute(
            text("select count(*) from family")
        ).scalar_one()
        geographic_count = connection.execute(
            text("select count(*) from geographic_area")
        ).scalar_one()

    assert family_count > 1000
    assert geographic_count > 1000


def test_postgresql_can_persist_core_taxonomy_fixture(postgresql_database):
    timestamp = "2026-05-20 00:00:00"
    with postgresql_database.engine.begin() as connection:
        family_id = connection.execute(
            text(
                "insert into family "
                "(epithet, author, qualifier, _created, _last_updated) "
                "values (:family, '', '', :created, :updated) "
                "returning id"
            ),
            {
                "family": "PGCHECKACEAE",
                "created": timestamp,
                "updated": timestamp,
            },
        ).scalar_one()
        genus_id = connection.execute(
            text(
                "insert into genus "
                "(epithet, author, qualifier, family_id, _created, _last_updated) "
                "values (:genus, '', '', :family_id, :created, :updated) "
                "returning id"
            ),
            {
                "genus": "Pgcheckgenus",
                "family_id": family_id,
                "created": timestamp,
                "updated": timestamp,
            },
        ).scalar_one()
        species_id = connection.execute(
            text(
                "insert into species (epithet, genus_id, _created, _last_updated) "
                "values (:species, :genus_id, :created, :updated) "
                "returning id"
            ),
            {
                "species": "pgcheckspecies",
                "genus_id": genus_id,
                "created": timestamp,
                "updated": timestamp,
            },
        ).scalar_one()
        connection.execute(
            text(
                "insert into accession "
                "(code, id_qual, private, species_id, _created, _last_updated) "
                "values (:code, '', false, :species_id, :created, :updated)"
            ),
            {
                "code": "PG-ACC-001",
                "species_id": species_id,
                "created": timestamp,
                "updated": timestamp,
            },
        )

    with postgresql_database.engine.connect() as connection:
        rows = connection.execute(
            text(
                "select accession.code, species.epithet, genus.epithet, family.epithet "
                "from accession "
                "join species on accession.species_id = species.id "
                "join genus on species.genus_id = genus.id "
                "join family on genus.family_id = family.id "
                "where accession.code = :code"
            ),
            {"code": "PG-ACC-001"},
        ).all()

    assert rows == [("PG-ACC-001", "pgcheckspecies", "Pgcheckgenus", "PGCHECKACEAE")]
