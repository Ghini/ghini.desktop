# Copyright (c) 2017 Mario Frasca <mario@anche.no>
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

import pytest
from bauble.querybuilderparser import BuiltQuery


def test_and_clauses() -> None:
    query = BuiltQuery(
        'plant WHERE accession.species.genus.family.epithet=Fabaceae AND location.description="Block 10" and quantity > 0 and quantity == 0'
    )
    assert len(query.parsed) == 6
    assert query.parsed[0] == "plant"
    assert query.parsed[1] == "where"
    assert len(query.parsed[2]) == 3
    for i in (3, 4, 5):
        assert query.parsed[i][0] == "and"
        assert len(query.parsed[i]) == 4


def test_or_clauses() -> None:
    query = BuiltQuery(
        'plant WHERE accession.species.genus.family.epithet=Fabaceae OR location.description="Block 10" or quantity > 0 or quantity == 0'
    )
    assert len(query.parsed) == 6
    assert query.parsed[0] == "plant"
    assert query.parsed[1] == "where"
    assert len(query.parsed[2]) == 3
    for i in (3, 4, 5):
        assert query.parsed[i][0] == "or"
        assert len(query.parsed[i]) == 4


def test_has_clauses() -> None:
    query = BuiltQuery("genus WHERE epithet=Inga")
    assert len(query.clauses) == 1

    query = BuiltQuery("genus WHERE epithet=Inga or epithet=Iris")
    assert len(query.clauses) == 2


def test_has_domain() -> None:
    query = BuiltQuery("plant WHERE accession.species.genus.epithet=Inga")
    assert query.domain == "plant"


def test_clauses_have_fields() -> None:
    query = BuiltQuery("genus WHERE epithet=Inga or family.epithet=Poaceae")
    assert len(query.clauses) == 2
    assert query.clauses[0].connector is None
    assert query.clauses[1].connector == "or"
    assert query.clauses[0].field == "epithet"
    assert query.clauses[1].field == "family.epithet"
    assert query.clauses[0].operator == "="
    assert query.clauses[1].operator == "="
    assert query.clauses[0].value == "Inga"
    assert query.clauses[1].value == "Poaceae"

    query = BuiltQuery(
        "species WHERE genus.epithet=Inga and accessions.code like '2010%'"
    )
    assert len(query.clauses) == 2
    assert query.clauses[0].connector is None
    assert query.clauses[1].connector == "and"
    assert query.clauses[0].field == "genus.epithet"
    assert query.clauses[1].field == "accessions.code"
    assert query.clauses[0].operator == "="
    assert query.clauses[1].operator == "like"
    assert query.clauses[0].value == "Inga"
    assert query.clauses[1].value == "2010%"


def test_is_none_if_wrong() -> None:
    query = BuiltQuery("'species WHERE genus.epithet=Inga")
    assert query.is_valid is False

    query = BuiltQuery("species like %")
    assert query.is_valid is False

    query = BuiltQuery("Inga")
    assert query.is_valid is False


@pytest.mark.parametrize(  # type: ignore[misc]
    "query_string",
    [
        "species Where genus.epithet=Inga and accessions.code like '2010%'",
        "species WHERE genus.epithet=Inga and accessions.code Like '2010%'",
        "species Where genus.epithet=Inga and accessions.code LIKE '2010%'",
        "species Where genus.epithet=Inga AND accessions.code like '2010%'",
        "species WHERE genus.epithet=Inga AND accessions.code LIKE '2010%'",
    ],
)
def test_is_case_insensitive(query_string: str) -> None:
    query = BuiltQuery(query_string)
    assert len(query.clauses) == 2
    assert query.clauses[0].connector is None
    assert query.clauses[1].connector == "and"
    assert query.clauses[0].field == "genus.epithet"
    assert query.clauses[1].field == "accessions.code"
    assert query.clauses[0].operator == "="
    assert query.clauses[1].operator == "like"
    assert query.clauses[0].value == "Inga"
    assert query.clauses[1].value == "2010%"


def test_is_only_usable_clauses() -> None:
    query = BuiltQuery("species WHERE genus.epithet=Inga or count(accessions.id)>4")
    assert query.is_valid is True
    assert len(query.clauses) == 1

    query = BuiltQuery(
        "species WHERE a=1 or count(accessions.id)>4 or genus.epithet=Inga"
    )
    assert query.is_valid is True
    assert len(query.clauses) == 2


def test_be_able_to_skip_first_query_if_invalid() -> None:
    """
    Skipped: Grammar rewriting is required to handle this case.
    """
    pytest.skip(
        "we can't do that without rewriting the grammar", allow_module_level=True
    )
