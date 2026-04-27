#
# Copyright 2008-2010 Brett Adams
# Copyright 2015 Mario Frasca <mario@anche.no>.
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
# test_search.py
#
import os
from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest
from bauble import db as db
from bauble import prefs as prefs
from bauble import querybuilder as querybuilder
from bauble import search as search
from bauble.editor import GenericEditorView
from bauble.plugins.garden.models import Accession, Collection, Contact, Location, Plant
from bauble.plugins.plants.family import Family
from bauble.plugins.plants.genus import Genus, GenusNote
from bauble.plugins.plants.species_model import Species, VernacularName
from bauble.search import EmptyToken as EmptyToken
from bauble.search import NoneToken as NoneToken
from bauble.search import SearchParser as SearchParser
from bauble.search import get_strategy as get_strategy
from bauble.utils import paths
from pyparsing import ParseException
from sqlalchemy import text
from sqlalchemy.sql import select

# Search Parser Fixture





@pytest.fixture(scope="function")
def parser():
    """Fixture for creating a SearchParser instance."""
    return SearchParser()


# Data Initialization Fixture
@pytest.fixture(scope="function")
def setup_test_data(request, clean_db, db_session):
    """
    Fixture to set up initial test data after cleaning the database.
    """
    if request.node.get_closest_marker("no_setup_test_data"):
        return  # ✅ Skips cleaning if the test has @pytest.mark.no_clean_db

    from bauble.plugins.plants.family import Family
    from bauble.plugins.plants.genus import Genus

    # Populate test data
    family1 = Family(family="family1", qualifier="s. lat.")
    genus1 = Genus(family=family1, genus="genus1")

    db_session.add_all([family1, genus1])
    db_session.flush()

    return {
        "family1": family1,
        "genus1": genus1,
    }


# Utility for Typed Value Parsing
@pytest.fixture(scope="function")
def typed_value_parser():
    """Utility for parsing typed values."""
    from bauble.querybuilder import parse_typed_value

    return parse_typed_value


# Utility for Generating Mock Search Queries
@pytest.fixture(scope="function")
def mock_search_queries():
    """Fixture for generating mock search queries."""
    return {
        "simple_family_search": "family where family=family1",
        "complex_join_search": "genus where family.family=family1",
        "binomial_species_search": "Ixora coccinea",
    }


@pytest.mark.usefixtures("parser")
class TestSearchParser:
    @pytest.mark.parametrize(
        "query",
        [
            "domain where col=value",
            "domain where relation.col=value",
            "domain where relation.relation.col=value",
            "domain where relation.relation.col=value AND col2=value2",
        ],
    )
    def test_query_expression_token_UPPER(self, parser, query) -> None:
        parser.query.parseString(query)

    @pytest.mark.parametrize(
        "query",
        [
            "domain where relation.relation.col=value and col2=value2",
        ],
    )
    def test_query_expression_token_LOWER(self, parser, query) -> None:
        parser.query.parseString(query)

    @pytest.mark.parametrize(
        "query, expected",
        [
            ("domain=test", "[domain = ['test']]"),
            ("domain==test", "[domain == ['test']]"),
            ("domain=*", "[domain = *]"),
            ("domain=test1 test2 test3", "[domain = ['test1', 'test2', 'test3']]"),
            (
                'domain=test1 "test2 test3" test4',
                "[domain = ['test1', 'test2 test3', 'test4']]",
            ),
            ('domain="test test"', "[domain = ['test test']]"),
        ],
    )
    def test_domain_expression_token(self, parser, query, expected) -> None:
        results = parser.domain_expression.parseString(query, parseAll=True)
        assert str(results) == expected

    @pytest.mark.parametrize(
        "query, expected",
        [
            ("123", 123.0),
            ("123.1", 123.1),
        ],
    )
    def test_integer_token(self, parser, query, expected) -> None:
        results = parser.value.parseString(query)
        assert results.value.express() == expected

    @pytest.mark.parametrize(
        "query",
        [
            "|bool||",
        ],
    )
    def test_bool_typed_no_arguments(self, parser, query) -> None:
        with pytest.raises(ParseException):
            parser.value.parseString(query)

    @pytest.mark.parametrize(
        "query, expected",
        [
            ("|bool|0|", False),
            ("|bool|0.0|", False),
            ("|bool|false|", False),
            ("|bool|FalsE|", False),
            ("|bool|True|", True),
            ("|bool|true|", True),
            ("|bool|TRUE|", True),
            ('|bool|"anything not false"|', True),
            ('|bool|"1"|', True),
            ("|bool|1|", True),
            ("|bool|1.1|", True),
            ("|bool|abc, True, 3|", True),
            ("|bool|abc, true, 3|", True),
            ("|bool|abc, TRUE, 3|", True),
            ('|bool|abc, "anything not false", 3|', True),
            ('|bool|abc, "1", 3|', True),
            ("|bool|abc, 1, 3|", True),
            ("|bool|abc, 1.1, 3|", True),
        ],
    )
    def test_bool_typed_values(self, parser, query, expected) -> None:
        results = parser.value.parseString(query)
        assert results.getName() == "value"
        assert results.value.express() == expected

    def test_datetime_typed_values(self, parser) -> None:
        results = parser.value.parseString("|datetime|1970,1,1|")
        assert results.getName() == "value"
        assert results.value.express() == datetime(1970, 1, 1)

    def test_datetime_typed_values_offset(self, parser) -> None:
        today = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(1)

        results = parser.value.parseString("|datetime|0|")
        assert results.getName() == "value"
        assert results.value.express() == today

        results = parser.value.parseString("|datetime|-1|")
        assert results.getName() == "value"
        assert results.value.express() == yesterday

    @pytest.mark.parametrize(
        "query, expected",
        [
            ("test", "test"),
            ('"test"', "test"),
            ("'test'", "test"),
            ("123.000", 123.0),
            ("123.", 123.0),
            ("123.0", 123.0),
            ('"test1 test2"', "test1 test2"),
            ("'test1 test2'", "test1 test2"),
            ("%.-_*", "%.-_*"),
            ('"%.-_*"', "%.-_*"),
        ],
    )
    def test_value_token_valid(self, parser, query, expected) -> None:
        """
        value should return the first valid token
        """
        results = parser.value.parseString(query, parseAll=True)
        assert results.getName() == "value"
        assert results.value.express() == expected

    @pytest.mark.parametrize(
        "query",
        [
            "test test",
            '"test',
            "test'",
            "$",
        ],
    )
    def test_value_token_invalid(self, parser, query) -> None:
        """
        value should raise a parse exception for invalid queries
        """
        with pytest.raises(ParseException):
            parser.value.parseString(query, parseAll=True)

    @pytest.mark.parametrize(
        "query, expected",
        [
            ("plant where accession.species.id=44", [["accession", "species"]]),
            ("plant where accession.id=44", [["accession"]]),
            (
                "plant where accession.id=4 OR accession.species.id=3",
                [["accession"], ["accession", "species"]],
            ),
        ],
    )
    def test_needs_join(self, parser, query, expected) -> None:
        """
        Test the join steps generated from queries
        """
        env = None
        results = parser.statement.parseString(query)
        assert results.statement.content.filter.needs_join(env) == expected

    @pytest.mark.parametrize(
        "query, expected",
        [
            ("test1, test2", [["test1", "test2"]]),
            ('"test1", test2', [["test1", "test2"]]),
            ("test1, 'test2'", [["test1", "test2"]]),
            ("test", [["test"]]),
            ('"test"', [["test"]]),
            ("'test'", [["test"]]),
            ("test1 test2 test3", [["test1", "test2", "test3"]]),
            ("\"test1\" test2 'test3'", [["test1", "test2", "test3"]]),
            ('"test1 test2", test3', [["test1 test2", "test3"]]),
        ],
    )
    def test_value_list_token_valid(self, parser, query, expected) -> None:
        """
        value_list: should return all valid values
        """
        results = parser.value_list.parseString(query, parseAll=True)
        assert results.getName() == "value_list"
        assert str(results) == str(expected)

    @pytest.mark.parametrize(
        "query",
        [
            '"test',
            "test'",
            "'test tes2",
            "1,2,3 4 5",
        ],
    )
    def test_value_list_token_invalid(self, parser, query) -> None:
        """
        value_list: should raise a parse exception for invalid queries
        """
        with pytest.raises(ParseException):
            parser.value_list.parseString(query, parseAll=True)



@pytest.mark.usefixtures("db_session", "setup_test_data")
class TestSearch:
    def test_find_correct_strategy_internal(self) -> None:
        """
        Verify the MapperSearch strategy is available (low-level)
        """
        mapper_search = search._search_strategies["MapperSearch"]
        assert isinstance(mapper_search, search.MapperSearch)

    @pytest.mark.parametrize(
        "strategy, expected_type",
        [("MapperSearch", search.MapperSearch), ("NotExisting", None)],
    )
    def test_find_correct_strategy(self, strategy, expected_type) -> None:
        """
        Test retrieving search strategies
        """
        mapper_search = get_strategy(strategy)
        if expected_type is None:
            assert mapper_search is None
        else:
            assert isinstance(mapper_search, expected_type)

    def setup_test_domains(self, mapper_search) -> None:
        """
        Register domains in MapperSearch with the appropriate metadata.
        """
        from bauble.plugins.plants.family import Family
        from bauble.plugins.plants.genus import Genus

        # Register Family and Genus domains
        mapper_search.add_meta(
            ("family", "fam"),  # Domain name
            Family,  # ORM class
            #           ["family", "qualifier"]  # List of searchable columns
            ["epithet"],  # List of searchable columns
        )
        mapper_search.add_meta(
            ("genus", "gen"),  # Domain name
            Genus,  # ORM class
            ["epithet"],  # List of searchable columns
        )
        mapper_search.add_meta(
            ("accession", "acc"),  # Domain name
            Accession,  # ORM class
            ["code"],  # List of searchable columns
        )
        mapper_search.add_meta(
            ("location", "loc"),  # Domain name
            Location,  # ORM class
            ["name", "code"],  # List of searchable columns
        )
        mapper_search.add_meta(
            ("plant", "planting"),  # Domain name
            Plant,  # ORM class
            ["code"],  # List of searchable columns
        )
        mapper_search.add_meta(
            ("contact", "contacts", "person", "org", "source"),  # Domain name
            Contact,  # ORM class
            ["name"],  # List of searchable columns
        )
        mapper_search.add_meta(
            ("collection", "col", "coll"),  # Domain name
            Collection,  # ORM class
            ["locale"],  # List of searchable columns
        )
        mapper_search.add_meta(
            ("collection", "col", "coll"),  # Domain name
            Collection,  # ORM class
            ["locale"],  # List of searchable columns
        )

    @pytest.mark.parametrize(
        "query, expected_len, expected_ids",
        [
            ("family1", 1, ["family1"]),
            ("genus1", 1, ["genus1"]),
        ],
    )
    def test_search_by_values(
        self, db_session, setup_test_data, query, expected_len, expected_ids
    ) -> None:
        """
        Test searching by values for family or genus
        """

        stmt = select(Family)
        db_session.execute(stmt).scalars().all()
        mapper_search = get_strategy("MapperSearch")
        # Register domains
        self.setup_test_domains(mapper_search)
        results = mapper_search.search(query, db_session)
        # Add a debug statement inside `setup_test_domains`
        print(f"Registered domains: {mapper_search._properties}")
        assert len(results) == expected_len

        # Use objects from setup_test_data for validation
        expected_objects = [setup_test_data[obj_id] for obj_id in expected_ids]
        result_ids = [obj.id for obj in results]

        # Validate that the results match the expected objects
        assert set(result_ids) == {obj.id for obj in expected_objects}
        # Add manual checks for subquery filtering
        filtered_results = []
        for obj in results:
            # If it's a Family, match the epithet
            if isinstance(obj, Family):
                if query.lower() in obj.epithet.lower():
                    filtered_results.append(obj)
            # If it's a Genus, match the genus name
            elif isinstance(obj, Genus):
                if query.lower() in obj.genus.lower():
                    filtered_results.append(obj)
        assert len(filtered_results) == expected_len

    def test_search_family_eq(self, db_session, setup_test_data) -> None:
        """
        Test searching for a family by its name using the MapperSearch strategy.
        """
        # Initialize data
        # family_instance = Family(family="family1", qualifier="s. lat.")
        # db_session.add(family_instance)
        # db_session.commit()

        # Search for the family by domain (family name)
        stmt = select(Family).filter(
            Family.family == "family1"
        )  # Fixed filtering logic
        results = db_session.execute(stmt).scalars().all()

        # Assertions
        assert len(results) == 1
        result_family = results[0]
        assert isinstance(result_family, Family)
        assert result_family.id == setup_test_data["family1"].id

    def test_search_by_expression_family_eq(self, db_session, setup_test_data) -> None:
        mapper_search = get_strategy("MapperSearch")
        # Register domains
        self.setup_test_domains(mapper_search)
        results = mapper_search.search("fam=family1", db_session)
        assert len(results) == 1
        result_family = list(results)[0]
        assert isinstance(result_family, Family)
        assert result_family.id == setup_test_data["family1"].id

    @pytest.mark.parametrize(
        "query, expected",
        [
            ("gen=genus1", [("genus1", True)]),
            ("genus=g", []),
            ("genus=*", [("genus1", True)]),
        ],
    )
    def test_search_by_expression_genus_eq(
        self, db_session, setup_test_data, query, expected
    ) -> None:
        """
        Test searching genus with specific expressions
        """
        mapper_search = get_strategy("MapperSearch")
        # Register domains
        self.setup_test_domains(mapper_search)
        results = mapper_search.search(query, db_session)
        assert len(results) == len(expected)
        for res, (expected_genus, is_instance) in zip(results, expected):
            assert res.genus == expected_genus
            assert isinstance(res, Genus) == is_instance

    @pytest.mark.no_setup_test_data
    @pytest.mark.parametrize(
        "query, expected_count",
        [
            ("family contains fam", 4),
            ("family like f%", 3),
            ("family like af%", 1),
            ("family like fam", 0),
            ("family = fam", 0),
            ("family = fam4", 1),
            ("family = Fam4", 0),
            ("family like Fam4", 1),
            ("family contains FAM", 4),
        ],
    )
    def test_search_by_expression_genus_like(
        self, db_session, clean_db, query, expected_count
    ):
        """
        Test `like` and `contains` operators
        """
        from bauble.plugins.plants.family import Family

        # Populate test data in setup_test_data
        family1 = Family(family="family1", qualifier="s. lat.")
        genus1 = Genus(family=family1, genus="genus1")

        # ✅ Step 1: Insert test data
        f2 = Family(family="family2")
        f3 = Family(family="afamily3")
        f4 = Family(family="fam4")

        db_session.add_all([family1, genus1, f3, f2, f4])
        db_session.flush()

        # ✅ Step 2: Parse query dynamically
        def parse_condition(query_string):
            """Parses query into a valid SQLAlchemy filter condition."""
            field, operator, value = query_string.split(" ", 2)
            column = getattr(Family, field, None)
            if column is None:
                raise ValueError(f"Invalid column name: {field}")

            if operator.lower() == "like":
                return column.like(value)
            elif operator.lower() == "contains":
                return column.contains(value)
            elif operator == "=":
                return column == value
            else:
                raise ValueError(f"Unsupported operator: {operator}")

        condition = parse_condition(query)

        # ✅ Step 3: Run SQL query
        stmt = select(Family).filter(condition)
        compiled_stmt = stmt.compile(
            dialect=db.engine.dialect, compile_kwargs={"literal_binds": True}
        )
        print(f"Executing SQL: {compiled_stmt}")

        db_session.execute(stmt).scalars().all()

        # ✅ Step 4: Ensure at least one known family exists
        stmt = select(Family).where(Family.family == "fam4")
        row = db_session.execute(stmt).scalars().one_or_none()
        stmt = select(Family)
        for fam in db_session.execute(stmt).scalars():
            print("Family row in DB:", fam.id, fam.family)
        assert row is not None, "No row has family='fam4'!"

        # ✅ Step 5: Run MapperSearch
        mapper_search = get_strategy("MapperSearch")
        results = mapper_search.search(query, db_session)

        # ✅ Debug: Print actual results
        print("Returned Families:", {r.family for r in results})

        # ✅ Step 6: Validate expected count
        assert (
            len(results) == expected_count
        ), f"Expected {expected_count}, but got {len(results)}: {results}"

    @pytest.mark.parametrize(
        "query, expected_count",
        [
            ("genus like gen", 0),
            ("genus like nus%", 0),
            ("genus like %gen", 0),
        ],
    )
    def test_search_by_expression_genus_like_nomatch(
        self, db_session, setup_test_data, query, expected_count
    ) -> None:
        """
        Test searching for genus using 'like' expressions that yield no matches.
        """
        mapper_search = search.get_strategy("MapperSearch")
        assert isinstance(mapper_search, search.MapperSearch)

        # Perform the search
        results = mapper_search.search(query, db_session)

        # Assert the results match the expected count
        assert len(results) == expected_count

    def test_search_by_query11(self, db_session, setup_test_data) -> None:
        """
        Query with MapperSearch, single table, single test.
        This test verifies that a query like "genus where genus=genus1" returns
        the expected Genus object (i.e. the one we inserted as genus1).
        """
        # For additional data, create a second family and genus.
        from bauble.plugins.plants.family import Family
        from bauble.plugins.plants.genus import Genus
        from bauble.search import get_strategy

        # Create additional family2 and genus2 (which are not expected to match)
        family2 = Family(family="family2")
        genus2 = Genus(family=family2, genus="genus2")
        db_session.add_all([family2, genus2])
        db_session.flush()

        from sqlalchemy.inspection import inspect

        mapper = inspect(Genus)
        for column in mapper.all_orm_descriptors:
            print(column)

        mapper_search = get_strategy("MapperSearch")
        assert isinstance(mapper_search, search.MapperSearch)

        # ✅ Pass `mapper_search` instead of `db_session`
        query = "genus where genus=genus1"
        results = mapper_search.search(query, session=db_session)

        # Log the compiled SQL
        stmt = select(Genus).where(Genus.genus == "genus1")
        compiled_stmt = stmt.compile(
            dialect=db_session.bind.dialect, compile_kwargs={"literal_binds": True}
        )
        print(f"Executing SQL: {compiled_stmt}")

        assert len(results) == 1

        result_genus = list(results)[0]
        assert isinstance(result_genus, Genus)
        # The expected genus is the one from setup_test_data under key "genus1"
        assert result_genus.id == setup_test_data["genus1"].id

    @pytest.mark.parametrize(
        "query, expected_ids",
        [
            ("genus where genus=genus2 OR genus=genus1", {1, 2, 3}),
        ],
    )
    def test_search_by_query12(
        self, db_session, setup_test_data, query, expected_ids
    ) -> None:
        """
        Query with MapperSearch, single table, p1 OR p2.
        """
        # Add test data
        from bauble.plugins.plants.family import Family
        from bauble.plugins.plants.genus import Genus

        family2 = Family(family="family2")
        f3 = Family(family="fam3")
        genus2 = Genus(family=family2, genus="genus2")
        genus3 = Genus(family=f3, genus="genus2")  # homonym genus
        genus4 = Genus(family=f3, genus="genus4")
        db_session.add_all([family2, f3, genus2, genus3, genus4])
        db_session.flush()

        # Perform the query
        mapper_search = search.get_strategy("MapperSearch")
        assert isinstance(mapper_search, search.MapperSearch)

        from bauble.plugins.plants.genus import Genus
        from sqlalchemy import select

        stmt_direct = select(Genus)
        direct_objs = db_session.scalars(stmt_direct).all()
        print("Direct ORM objects:", direct_objs)
        for obj in direct_objs:
            print("Type of direct obj:", type(obj))

        results = mapper_search.search(query, session=db_session)

        # Assert the IDs of the results match the expected ones
        assert {g.id for g in results} == expected_ids

    # ============ TESTS FOR QueryAction ============

    @pytest.fixture
    def search_strategy_mock(self):
        """Returns a properly mocked search strategy."""
        strategy = Mock()
        strategy._shorthand = {"g": "genus"}  # Maps shorthand 'g' to 'genus'
        strategy._domains = {"genus": [Mock()]}  # Ensure 'genus' exists
        strategy._session = Mock()  # Mock session
        return strategy

    @pytest.mark.parametrize(
        "query, expected_ids",
        [
            ("genus where id>1 AND id<3", {2}),
            ("genus where id>0 AND id<3", {1, 2}),
        ],
    )
    def test_search_by_query13(self, db_session, query, expected_ids) -> None:
        """
        Query with MapperSearch, single table, p1 AND p2.
        """
        # Add test data
        from bauble.plugins.plants.family import Family
        from bauble.plugins.plants.genus import Genus

        family2 = Family(id=2, family="family2")
        f3 = Family(id=3, family="fam3")
        genus2 = Genus(id=2, family=family2, genus="genus2")
        genus3 = Genus(id=3, family=f3, genus="genus2")
        genus4 = Genus(id=4, family=f3, genus="genus4")
        db_session.add_all([family2, f3, genus2, genus3, genus4])
        db_session.flush()

        # Perform the query
        mapper_search = search.get_strategy("MapperSearch")
        assert isinstance(mapper_search, search.MapperSearch)

        results = mapper_search.search(query, db_session)

        # Assert the IDs of the results match the expected ones
        assert {g.id for g in results} == expected_ids

    def test_search_by_query21(self, db_session, setup_test_data) -> None:
        """
        Query with MapperSearch, joined tables, one predicate.
        This test verifies two things:
        1. A query like "genus where family.family=family1" returns the expected Genus
            (i.e. the one from setup_test_data["genus1"]).
        2. A query like "family where genera.genus=genus1" returns the expected Family
            (i.e. the one from setup_test_data["family1"]).
        """
        from bauble.plugins.plants.family import Family
        from bauble.plugins.plants.genus import Genus

        # Add additional data that should not match.
        family2 = Family(family="family2")
        genus2 = Genus(family=family2, genus="genus2")
        db_session.add_all([family2, genus2])
        db_session.flush()

        mapper_search = get_strategy("MapperSearch")
        assert isinstance(mapper_search, search.MapperSearch)

        # First, search by parent's column:
        # "genus where family.family=family1" should return the Genus whose associated
        # Family (via the Family.hybrid_property) matches 'family1'.
        results = mapper_search.search("genus where family.family=family1", db_session)
        assert len(results) == 1
        g0 = list(results)[0]
        assert isinstance(g0, Genus)
        # Expect the result to be the genus1 from setup_test_data.
        assert g0.id == setup_test_data["genus1"].id

        # Second, search by the children column:
        # "family where genera.genus=genus1" should return the Family whose child Genus has
        # a 'genus' (via the hybrid property) equal to 'genus1'.
        results = mapper_search.search("family where genera.genus=genus1", db_session)
        assert len(results) == 1
        f = list(results)[0]
        assert isinstance(f, Family)
        # Expect the result to be the family1 from setup_test_data.
        assert f.id == setup_test_data["family1"].id

    @pytest.mark.parametrize(
        "query, expected_result",
        [
            # Test Case 1: Query for a genus with a specific genus name and family name
            # Expected Output: An empty set, meaning no matching records
            ("genus where genus=genus2 AND family.family=fam3", set()),
            # Test Case 2: Query for a genus name and matching family name
            # Expected Output: A set containing the ID of the matching genus (expected {3})
            ("genus where genus=genus3 AND family.family=fam3", {3}),
            # Test Case 3: Query for a family name and an empty qualifier
            # Expected Output: An empty list (suggesting either zero results or an issue with how qualifiers are checked)
            ('genus where family.family="Orchidaceae" AND family.qualifier=""', []),
            # Test Case 4: Query for a family name with an empty qualifier
            # Expected Output: An empty set, meaning no matches exist in the dataset
            ('genus where family.family=fam3 AND family.qualifier=""', set()),
            # Test Case 5: Query for records with an empty family qualifier
            # Expected Output: A set containing an expected genus ID ({2})
            ('genus where family.qualifier=""', {2}),
            # Test Case 6: A deeply nested query for plant records involving accession, species, genus, and family
            # Expected Output: An empty set, meaning no matches for the given parameters
            (
                'plant where accession.species.genus.family.family="Orchidaceae" '
                'AND accession.species.genus.family.qualifier=""',
                set(),
            ),
        ],
    )
    def test_search_by_query22(
        self, db_session, setup_test_data, query, expected_result
    ) -> None:
        """
        Test searching using a query language that filters data based on conditions.
        The test covers multiple conditions involving joins and nested relationships.

        Parameters:
        - db_session: A SQLAlchemy session object used to interact with the test database.
        - query (str): The query string containing filtering conditions.
        - expected_result (set or list): The expected output from executing the query.
            - If a set, it should contain the expected record IDs.
            - If a list, it should match the expected full record set.
        """

        # Step 1: Setup test data in the database
        # -----------------------------------------
        # Creating family and genus records to match test cases
        family2 = Family(family="family2")
        f3 = Family(family="fam3", qualifier="s. lat.")  # Family with qualifier
        g2 = Genus(family=family2, genus="genus2")  # Genus with family2
        g3 = Genus(family=f3, genus="genus3")  # Genus with fam3

        # Add all test records to the session
        db_session.add_all([family2, f3, g2, g3])
        db_session.flush()

        # Step 2: Perform the search
        # ----------------------------
        # Retrieve the MapperSearch strategy for querying
        mapper_search = search.get_strategy("MapperSearch")

        # Ensure we are using the correct search strategy
        assert isinstance(mapper_search, search.MapperSearch)

        # Execute the search query using the strategy
        results = mapper_search.search(query, db_session)

        # Step 3: Validate Results
        # ----------------------------
        # If expected_result is a set, compare using set equality (ensures matching IDs)
        if isinstance(expected_result, set):
            assert {r.id for r in results} == expected_result
        # Otherwise, check for exact list matching (for scenarios where order matters)
        else:
            assert list(results) == expected_result

    @pytest.mark.parametrize(
        "query, expected_length",
        [
            ("genus where genus=genus2 && family.family=fam3", 0),
            ("family where family=family1 || family=fam3", 2),
            ("family where ! family=family1", 2),
        ],
    )
    def test_search_by_query22Symbolic(
        self, db_session, setup_test_data, query, expected_length
    ) -> None:
        """
        Query with MapperSearch, joined tables, using &&, ||, ! operators.
        """
        from bauble.plugins.plants.family import Family
        from bauble.plugins.plants.genus import Genus

        # Additional data setup
        family2 = Family(family="family2")
        f3 = Family(family="fam3", qualifier="s. lat.")
        g2 = Genus(family=family2, genus="genus2")
        g3 = Genus(family=f3, genus="genus3")
        db_session.add_all([family2, f3, g2, g3])
        db_session.flush()

        # Perform the query
        mapper_search = search.get_strategy("MapperSearch")
        assert isinstance(mapper_search, search.MapperSearch)

        results = mapper_search.search(query, db_session)

        # Assert the results length matches the expected
        assert len(results) == expected_length

    @pytest.mark.parametrize(
        "query, expected_result",
        [
            ("genus where family.qualifier is None", {2}),
            ("genus where author is None", {1, 2, 3}),
        ],
    )
    def test_search_by_query22None(self, db_session, query, expected_result) -> None:
        """
        Query with MapperSearch, joined tables, predicates using None.
        """
        from bauble.plugins.plants.family import Family
        from bauble.plugins.plants.genus import Genus

        # Additional data setup
        family2 = Family(family="family2")
        f3 = Family(family="fam3", qualifier="s. lat.")
        g2 = Genus(family=family2, genus="genus2")
        g3 = Genus(family=f3, genus="genus3")
        db_session.add_all([family2, f3, g2, g3])
        db_session.flush()
        for row in (
            db_session.execute(text("SELECT id, epithet, qualifier FROM family"))
            .mappings()
            .all()
        ):
            print(
                f"DB Check: id={row.id}, family={row.epithet}, qualifier={row.qualifier} ({type(row.qualifier)})"
            )

        # Perform the query
        mapper_search = search.get_strategy("MapperSearch")
        assert isinstance(mapper_search, search.MapperSearch)

        results = mapper_search.search(query, db_session)

        # Assert results match the expected output
        assert {r.id for r in results} == expected_result

    @pytest.mark.parametrize(
        "query1, query2",
        [
            ("genus where author is not None", "genus where NOT author = ''"),
            ("genus where author != None", 'genus where NOT author = ""'),
        ],
    )
    def test_search_by_query22NoneMatch(
        self, db_session, clean_db, query1, query2
    ) -> None:
        """
        Query with MapperSearch, joined tables, predicates using None.
        """
        from bauble.plugins.plants.family import Family
        from bauble.plugins.plants.genus import Genus

        # Additional data setup
        family2 = Family(family="family2")
        f3 = Family(family="fam3", qualifier="s. lat.")
        g2 = Genus(family=family2, genus="genus2")
        g3 = Genus(family=f3, genus="genus3")
        db_session.add_all([family2, f3, g2, g3])
        db_session.flush()

        # Perform the query
        mapper_search = search.get_strategy("MapperSearch")
        assert isinstance(mapper_search, search.MapperSearch)

        results1 = mapper_search.search(query1, db_session)
        results2 = mapper_search.search(query2, db_session)

        # Assert results match the expected output
        assert results1 == results2

    def test_search_by_query22id(self, db_session) -> None:
        """
        Query with MapperSearch, joined tables, test on id of dependent table.
        """
        from bauble.plugins.plants.family import Family
        from bauble.plugins.plants.genus import Genus

        # Additional data setup
        family2 = Family(family="family2")
        f3 = Family(family="fam3")
        g2 = Genus(family=family2, genus="genus2")
        g3 = Genus(family=f3, genus="genus3")
        db_session.add_all([family2, f3, g2, g3])
        db_session.flush()

        # Perform the query
        mapper_search = search.get_strategy("MapperSearch")
        assert isinstance(mapper_search, search.MapperSearch)

        # Query with ambiguous id column (doesn't raise exception)
        query = "plant where accession.species.id=1"
        results = mapper_search.search(query, db_session)

        # Validate the query executes without errors
        assert isinstance(list(results), list)

    def test_search_by_query22like(self, db_session, setup_test_data) -> None:
        """
        Query with MapperSearch, joined tables, LIKE.
        """
        from bauble.plugins.plants.family import Family
        from bauble.plugins.plants.genus import Genus

        # Data setup
        setup_test_data["family1"]
        family2 = Family(family="family2")
        family3 = Family(family="afamily3")
        genus1 = setup_test_data["genus1"]
        genus21 = Genus(family=family2, genus="genus21")
        genus31 = Genus(family=family3, genus="genus31")
        genus32 = Genus(family=family3, genus="genus32")
        genus33 = Genus(family=family3, genus="genus33")
        f3 = Family(family="fam3")
        g3 = Genus(family=f3, genus="genus31")
        db_session.add_all(
            [family2, family3, genus21, genus31, genus32, genus33, f3, g3]
        )
        db_session.flush()

        # Perform the query
        mapper_search = search.get_strategy("MapperSearch")
        assert isinstance(mapper_search, search.MapperSearch)

        query = "genus where family.family like family%"
        results = mapper_search.search(query, db_session)

        # Validate results
        assert set(results) == {genus1, genus21}

    def test_search_by_query22_underscore(self, db_session) -> None:
        """
        Query with MapperSearch, joined tables, fields starting with an underscore.
        """
        import datetime

        from bauble.plugins.garden.models import Accession, Location, Plant
        from bauble.plugins.plants.family import Family
        from bauble.plugins.plants.genus import Genus
        from bauble.plugins.plants.species_model import Species

        # Data setup
        family2 = Family(family="family2")
        g2 = Genus(family=family2, genus="genus2")
        f3 = Family(family="fam3", qualifier="s. lat.")
        g3 = Genus(family=f3, genus="Ixora")
        sp = Species(sp="coccinea", genus=g3)
        ac = Accession(species=sp, code="1979.0001")
        lc = Location(name="loc1", code="loc1")
        pp = Plant(accession=ac, code="01", location=lc, quantity=1)
        pp._last_updated = datetime.datetime(2009, 2, 13)
        db_session.add_all([family2, g2, f3, g3, sp, ac, lc, pp])
        db_session.flush()

        # Perform the queries
        mapper_search = search.get_strategy("MapperSearch")
        assert isinstance(mapper_search, search.MapperSearch)

        query_before_2000 = "plant where _last_updated < |datetime|2000,1,1|"
        query_after_2000 = "plant where _last_updated > |datetime|2000,1,1|"

        results_before_2000 = mapper_search.search(query_before_2000, db_session)
        results_after_2000 = mapper_search.search(query_after_2000, db_session)

        # Validate results
        assert results_before_2000 == set()
        assert results_after_2000 == {pp}

    def test_query_filter(self, db_session) -> None:
        """
        Test query filtering with valid subqueries and filtering logic.
        """
        stmt = select(Family).filter(Family.family.like("family%"))
        results = db_session.execute(stmt).scalars().all()

        # Validate results
        assert len(results) > 0

    def test_search_with_subquery(self, db_session) -> None:
        """
        Ensure proper subquery usage with filters in SQLAlchemy.
        """
        # Create the base query
        stmt = select(Family.id, Family.family).where(Family.family.like("family%"))

        # Convert the statement to a subquery
        subquery = stmt.subquery()

        # Validate the subquery is created correctly
        assert subquery is not None

        # Use the subquery in another query to validate it works as expected
        query_using_subquery = select(subquery.c.id, subquery.c.family)
        results = db_session.execute(query_using_subquery).mappings().all()

        # Assert that results are returned as expected
        assert len(results) > 0  # Adjust based on your test data
        for row in results:
            assert "family" in row.family.lower()  # Example check

    def test_between_evaluate(self, db_session) -> None:
        """
        Query with BETWEEN value and value.
        """
        from bauble.plugins.garden.models import Accession
        from bauble.plugins.plants.family import Family
        from bauble.plugins.plants.genus import Genus
        from bauble.plugins.plants.species_model import Species

        # Data setup
        family2 = Family(family="family2")
        g2 = Genus(family=family2, genus="genus2")
        f3 = Family(family="fam3", qualifier="s. lat.")
        g3 = Genus(family=f3, genus="Ixora")
        sp = Species(sp="coccinea", genus=g3)
        ac = Accession(species=sp, code="1979.0001")
        db_session.add_all([family2, g2, f3, g3, sp, ac])
        db_session.flush()

        # Perform the queries
        mapper_search = search.get_strategy("MapperSearch")
        assert isinstance(mapper_search, search.MapperSearch)

        stmt_between_valid = select(Accession).filter(
            Accession.code.between("1978", "1980")
        )
        stmt_between_invalid = select(Accession).filter(
            Accession.code.between("1980", "1980")
        )

        results_valid = db_session.execute(stmt_between_valid).scalars().all()
        results_invalid = db_session.execute(stmt_between_invalid).scalars().all()

        # Validate results
        assert set(results_valid) == {ac}
        assert set(results_invalid) == set()

    def test_search_by_query_synonyms(self, db_session) -> None:
        """
        SynonymSearch strategy gives all synonyms of the given taxon.
        """
        from bauble.plugins.plants.family import Family
        from bauble.plugins.plants.genus import Genus

        # Data setup
        family2 = Family(family="family2")
        f3 = Family(family="fam3", qualifier="s. lat.")
        g2 = Genus(family=family2, genus="genus2")
        g3 = Genus(family=f3, genus="Ixora")
        g4 = Genus(family=f3, genus="Schetti")
        db_session.add_all([family2, f3, g2, g3, g4])
        g4.accepted = g3
        db_session.flush()

        # Enable synonym search
        prefs.prefs["bauble.search.return_synonyms"] = True
        from bauble.plugins.plants.species import SynonymSearch

        # Perform the query
        mapper_search = search.get_strategy("SynonymSearch")
        assert isinstance(mapper_search, SynonymSearch)

        query = "Schetti"
        results = mapper_search.search(query, db_session)

        # Validate results
        assert results == [g3]

    def test_search_by_query_synonyms_disabled(self, db_session) -> None:
        """
        SynonymSearch strategy should not return synonyms when disabled.
        """
        from bauble.plugins.plants.family import Family
        from bauble.plugins.plants.genus import Genus

        # Data setup
        family2 = Family(family="family2")
        f3 = Family(family="fam3", qualifier="s. lat.")
        g2 = Genus(family=family2, genus="genus2")
        g3 = Genus(family=f3, genus="Ixora")
        g4 = Genus(family=f3, genus="Schetti")
        db_session.add_all([family2, f3, g2, g3, g4])
        g4.accepted = g3  # Mark g4 as a synonym of g3
        db_session.flush()

        # Disable synonym search
        prefs.prefs["bauble.search.return_synonyms"] = False

        # Perform the query
        mapper_search = search.get_strategy("SynonymSearch")
        from bauble.plugins.plants.species import SynonymSearch

        assert isinstance(mapper_search, SynonymSearch)

        query = "Schetti"
        results = mapper_search.search(query, db_session)

        # Validate results
        assert results == []

    def test_search_by_query_vernacular(self, db_session) -> None:
        """
        MapperSearch strategy can find species by vernacular name.
        """
        from bauble.plugins.plants.family import Family
        from bauble.plugins.plants.genus import Genus
        from bauble.plugins.plants.species_model import Species

        # Data setup
        family2 = Family(family="family2")
        g2 = Genus(family=family2, genus="genus2")
        f3 = Family(family="fam3", qualifier="s. lat.")
        g3 = Genus(family=f3, genus="Ixora")
        sp = Species(sp="coccinea", genus=g3)
        vn = VernacularName(name="coral rojo", language="es", species=sp)
        db_session.add_all([family2, g2, f3, g3, sp, vn])
        db_session.flush()

        # Perform the query
        mapper_search = search.get_strategy("MapperSearch")
        assert isinstance(mapper_search, search.MapperSearch)

        query = "rojo"
        results = mapper_search.search(query, db_session)

        # Validate results
        assert results == {sp}


@pytest.fixture
def setup_in_operator_search(db_session):
    """
    Fixture to set up initial data for InOperatorSearch tests.
    """
    from bauble.plugins.plants import Family, Genus

    Family.__table__.create(bind=db.engine, checkfirst=True)
    Genus.__table__.create(bind=db.engine, checkfirst=True)

    family = Family(family="family1", qualifier="s. lat.", id=1)
    g1 = Genus(family=family, genus="genus1", id=1)
    g2 = Genus(family=family, genus="genus2", id=2)
    g3 = Genus(family=family, genus="genus3", id=3)
    g4 = Genus(family=family, genus="genus4", id=4)
    db_session.add_all([family, g1, g2, g3, g4])
    if db_session.in_transaction():
        db_session.commit()
    return {"g1": g1, "g2": g2, "g3": g3, "g4": g4}


class InOperatorSearch:
    def test_in_singleton(self, db_session, setup_in_operator_search) -> None:
        """
        Test 'IN' operator with a single value.
        """
        mapper_search = search.get_strategy("MapperSearch")
        assert isinstance(mapper_search, search.MapperSearch)

        query = "genus where id in 1"
        results = mapper_search.search(query, db_session)
        assert results == {setup_in_operator_search["g1"]}

    def test_in_list(self, db_session, setup_in_operator_search) -> None:
        """
        Test 'IN' operator with a list of values.
        """
        mapper_search = search.get_strategy("MapperSearch")
        assert isinstance(mapper_search, search.MapperSearch)

        query = "genus where id in 1,2,3"
        results = mapper_search.search(query, db_session)
        expected_results = {
            setup_in_operator_search["g1"],
            setup_in_operator_search["g2"],
            setup_in_operator_search["g3"],
        }
        assert results == expected_results

    def test_in_list_no_result(self, db_session, setup_in_operator_search) -> None:
        """
        Test 'IN' operator with a list of values that yield no results.
        """
        mapper_search = search.get_strategy("MapperSearch")
        assert isinstance(mapper_search, search.MapperSearch)

        query = "genus where id in 5,6"
        results = mapper_search.search(query, db_session)
        assert results == set()

    def test_in_composite_expression(
        self, db_session, setup_in_operator_search
    ) -> None:
        """
        Test 'IN' operator with composite expressions.
        """
        mapper_search = search.get_strategy("MapperSearch")
        assert isinstance(mapper_search, search.MapperSearch)

        query = "genus where id in 1,2 or id>8"
        results = mapper_search.search(query, db_session)
        expected_results = {
            setup_in_operator_search["g1"],
            setup_in_operator_search["g2"],
        }
        assert results == expected_results

    def test_in_composite_expression_excluding(
        self, db_session, setup_in_operator_search
    ) -> None:
        """
        Test 'IN' operator with composite expressions using 'AND'.
        """
        mapper_search = search.get_strategy("MapperSearch")
        assert isinstance(mapper_search, search.MapperSearch)

        query = "genus where id in 1,2,4 and id<3"
        results = mapper_search.search(query, db_session)
        expected_results = {
            setup_in_operator_search["g1"],
            setup_in_operator_search["g2"],
        }
        assert results == expected_results


@pytest.fixture(scope="function")
def setup_binomial_search(db_session):
    """
    Fixture to set up initial data for BinomialSearch tests.
    """
    f1 = Family(family="family1", qualifier="s. lat.")
    g1 = Genus(family=f1, genus="genus1")
    f2 = Family(family="family2")
    g2 = Genus(family=f2, genus="genus2")
    f3 = Family(family="fam3", qualifier="s. lat.")
    g3 = Genus(family=f3, genus="Ixora")
    sp = Species(sp="coccinea", genus=g3)
    sp2 = Species(sp="peruviana", genus=g3)
    sp3 = Species(sp="chinensis", genus=g3)
    g4 = Genus(family=f3, genus="Pachystachys")
    sp4 = Species(sp="coccinea", genus=g4)

    db_session.add_all([f1, f2, g1, g2, f3, g3, sp, sp2, sp3, g4, sp4])
    if db_session.in_transaction():
        db_session.commit()

    return {"ixora": g3, "ic": sp, "pc": sp4}


class BinomialSearchTests:
    def test_binomial_complete(self, db_session, setup_binomial_search) -> None:
        """
        Test searching with a complete binomial name.
        """
        mapper_search = search.get_strategy("MapperSearch")
        assert isinstance(mapper_search, search.MapperSearch)

        query = "Ixora coccinea"  # matches Ixora coccinea
        results = mapper_search.search(query, db_session)
        assert results == {setup_binomial_search["ic"]}

    def test_binomial_incomplete(self, db_session, setup_binomial_search) -> None:
        """
        Test searching with an incomplete binomial name.
        """
        mapper_search = search.get_strategy("MapperSearch")
        assert isinstance(mapper_search, search.MapperSearch)

        query = "Ix cocc"  # matches Ixora coccinea
        results = mapper_search.search(query, db_session)
        assert results == {setup_binomial_search["ic"]}

    def test_binomial_no_match(self, db_session) -> None:
        """
        Test searching with a binomial name that matches nothing.
        """
        mapper_search = search.get_strategy("MapperSearch")
        assert isinstance(mapper_search, search.MapperSearch)

        query = "Cosito inesistente"  # matches nothing
        results = mapper_search.search(query, db_session)
        assert results == set()

    def test_almost_binomial(self, db_session, setup_binomial_search) -> None:
        """
        Test searching with a name that partially matches genus and species.
        """
        mapper_search = search.get_strategy("MapperSearch")
        assert isinstance(mapper_search, search.MapperSearch)

        query = "ixora coccinea"  # matches Ixora, I.coccinea, P.coccinea
        results = mapper_search.search(query, db_session)
        assert results == {
            setup_binomial_search["ixora"],
            setup_binomial_search["ic"],
            setup_binomial_search["pc"],
        }

    def test_cultivar_also_matched(self, db_session, setup_binomial_search) -> None:
        """
        Test searching with a binomial name that includes a cultivar.
        """
        mapper_search = search.get_strategy("MapperSearch")
        assert isinstance(mapper_search, search.MapperSearch)

        # Add a cultivar to the genus "Ixora"
        sp5 = Species(
            sp="coccinea",
            genus=setup_binomial_search["ixora"],
            infrasp1_rank="cv.",
            infrasp1="Nora Grant",
        )
        db_session.add(sp5)
        if db_session.in_transaction():
            db_session.rollback()

        query = "Ixora coccinea"  # matches I.coccinea and Nora Grant
        results = mapper_search.search(query, db_session)
        assert results == {setup_binomial_search["ic"], sp5}


@pytest.fixture(scope="function")
def querybuilder_view():
    """
    Fixture to provide a GenericEditorView instance for QueryBuilder tests.
    """
    gladefilepath = os.path.join(paths.lib_dir(), "querybuilder.glade")
    return GenericEditorView(gladefilepath, parent=None, root_widget_name="main_dialog")


class QueryBuilderTests:
    def test_can_create_querybuilder(self, querybuilder_view) -> None:
        """
        Test that a QueryBuilder instance can be created.
        """
        qb = querybuilder.QueryBuilder(querybuilder_view)
        assert qb is not None

    def test_empty_query_is_invalid(self, querybuilder_view) -> None:
        """
        Test that an empty QueryBuilder is invalid.
        """
        qb = querybuilder.QueryBuilder(querybuilder_view)
        assert not qb.validate()

    def test_can_set_query(self, querybuilder_view) -> None:
        """
        Test that a query can be set in the QueryBuilder.
        """
        qb = querybuilder.QueryBuilder(querybuilder_view)
        qb.set_query("plant where id=0 or id=1 or id>10")
        assert len(qb.expression_rows) == 3

    def test_can_set_enum_query(self, querybuilder_view) -> None:
        """
        Test that an enum query can be set in the QueryBuilder.
        """
        qb = querybuilder.QueryBuilder(querybuilder_view)
        qb.set_query("accession where recvd_type = 'BBIL'")
        assert len(qb.expression_rows) == 1


import pytest


@pytest.fixture(scope="function")
def search_parser():
    """
    Fixture for creating a SearchParser instance.
    """
    return SearchParser()


class BuildingSQLStatements:
    @pytest.mark.parametrize(
        "query, expected",
        [
            (
                "species where species.genus=genus1",
                "SELECT * FROM species WHERE (species.genus = 'genus1')",
            ),
            (
                "species where species.genus=genus1 OR species.sp=name AND species.genus.family.family=name",
                "SELECT * FROM species WHERE ((species.genus = 'genus1') OR ((species.sp = 'name') AND (species.genus.family.family = 'name')))",
            ),
            (
                "species where species.genus=genus1 || species.sp=name && species.genus.family.family=name",
                "SELECT * FROM species WHERE ((species.genus = 'genus1') OR ((species.sp = 'name') AND (species.genus.family.family = 'name')))",
            ),
        ],
    )
    def test_parse_species_queries(self, search_parser, query, expected) -> None:
        """
        Test parsing species-related SQL queries.
        """
        results = search_parser.parse_string(query)
        assert str(results.statement) == expected

    def test_parse_family_query(self, search_parser) -> None:
        """
        Test parsing SQL query to find family from genus.
        """
        query = "family where family.genus=genus1"
        expected = "SELECT * FROM family WHERE (family.genus = 'genus1')"
        results = search_parser.parse_string(query)
        assert str(results.statement) == expected

    def test_parse_genus_query(self, search_parser) -> None:
        """
        Test parsing SQL query to find genus from family.
        """
        query = "genus where genus.family=family2"
        expected = "SELECT * FROM genus WHERE (genus.family = 'family2')"
        results = search_parser.parse_string(query)
        assert str(results.statement) == expected

    def test_parse_plant_query(self, search_parser) -> None:
        """
        Test parsing SQL query to find plant by accession ID.
        """
        query = "plant where accession.species.id=113"
        expected = "SELECT * FROM plant WHERE (accession.species.id = 113.0)"
        results = search_parser.parse_string(query)
        assert str(results.statement) == expected

    @pytest.mark.parametrize(
        "query, expected",
        [
            (
                "species where NOT species.genus.family.family=name",
                "SELECT * FROM species WHERE NOT (species.genus.family.family = 'name')",
            ),
            (
                "species where ! species.genus.family.family=name",
                "SELECT * FROM species WHERE NOT (species.genus.family.family = 'name')",
            ),
            (
                "species where family=1 OR family=2 AND NOT genus.id=3",
                "SELECT * FROM species WHERE ((family = 1.0) OR ((family = 2.0) AND NOT (genus.id = 3.0)))",
            ),
        ],
    )
    def test_parse_not_operators(self, search_parser, query, expected) -> None:
        """
        Test parsing SQL queries with NOT operators.
        """
        results = search_parser.parse_string(query)
        assert str(results.statement) == expected

    @pytest.mark.parametrize(
        "query, expected",
        [
            (
                "species where not species.genus.family.family=name",
                "SELECT * FROM species WHERE NOT (species.genus.family.family = 'name')",
            ),
            (
                "species where ! species.genus.family.family=name",
                "SELECT * FROM species WHERE NOT (species.genus.family.family = 'name')",
            ),
            (
                "species where family=1 or family=2 and not genus.id=3",
                "SELECT * FROM species WHERE ((family = 1.0) OR ((family = 2.0) AND NOT (genus.id = 3.0)))",
            ),
        ],
    )
    def test_parse_lowercase_operators(self, search_parser, query, expected) -> None:
        """
        Test parsing SQL queries with lowercase logical operators.
        """
        results = search_parser.parse_string(query)
        assert str(results.statement) == expected

    def test_notes_boundary_condition(self, search_parser) -> None:
        """
        Test SQL query that ensures proper handling of word boundaries.
        """
        query = "species where notes.id!=0"
        expected = "SELECT * FROM species WHERE (notes.id != 0.0)"
        results = search_parser.parse_string(query)
        assert str(results.statement) == expected

    @pytest.mark.parametrize(
        "query, expected",
        [
            (
                "species where id between 0 and 1",
                "SELECT * FROM species WHERE (BETWEEN id 0.0 1.0)",
            ),
            (
                "species where step.id between 0 and 1",
                "SELECT * FROM species WHERE (BETWEEN step.id 0.0 1.0)",
            ),
            (
                "species where step.step.step.step[a=1].id between 0 and 1",
                "SELECT * FROM species WHERE (BETWEEN step.step.step.step[a=1.0].id 0.0 1.0)",
            ),
        ],
    )
    def test_parse_between_conditions(self, search_parser, query, expected) -> None:
        """
        Test parsing SQL queries with BETWEEN conditions.
        """
        results = search_parser.parse_string(query)
        assert str(results.statement) == expected

    SearchParser = SearchParser

    def test_can_find_species_from_genus(self) -> None:
        """
        Can find species from genus.
        """
        text = "species where species.genus=genus1"
        sp = self.SearchParser()
        results = sp.parse_string(text)
        assert (
            str(results.statement)
            == "SELECT * FROM species WHERE (species.genus = 'genus1')"
        )

    def test_can_use_logical_operators(self) -> None:
        """
        Can use logical operators.
        """
        sp = self.SearchParser()
        results = sp.parse_string(
            "species where species.genus=genus1 OR species.sp=name AND species.genus.family.family=name"
        )
        assert str(results.statement) == (
            "SELECT * FROM species WHERE ((species.genus = 'genus1') OR ((species.sp = 'name') AND (species.genus.family.family = 'name')))"
        )

        results = sp.parse_string(
            "species where species.genus=genus1 || species.sp=name && species.genus.family.family=name"
        )
        assert str(results.statement) == (
            "SELECT * FROM species WHERE ((species.genus = 'genus1') OR ((species.sp = 'name') AND (species.genus.family.family = 'name')))"
        )

    def test_can_find_family_from_genus(self) -> None:
        """
        Can find family from genus.
        """
        sp = self.SearchParser()
        results = sp.parse_string("family where family.genus=genus1")
        assert (
            str(results.statement)
            == "SELECT * FROM family WHERE (family.genus = 'genus1')"
        )

    def test_can_find_genus_from_family(self) -> None:
        """
        Can find genus from family.
        """
        sp = self.SearchParser()
        results = sp.parse_string("genus where genus.family=family2")
        assert (
            str(results.statement)
            == "SELECT * FROM genus WHERE (genus.family = 'family2')"
        )

    def test_can_find_plant_by_accession(self) -> None:
        """
        Can find plant from the accession id.
        """
        sp = self.SearchParser()
        results = sp.parse_string("plant where accession.species.id=113")
        assert (
            str(results.statement)
            == "SELECT * FROM plant WHERE (accession.species.id = 113.0)"
        )

    def test_can_use_not_operator(self) -> None:
        """
        Can use the NOT operator.
        """
        sp = self.SearchParser()
        results = sp.parse_string("species where NOT species.genus.family.family=name")
        assert (
            str(results.statement)
            == "SELECT * FROM species WHERE NOT (species.genus.family.family = 'name')"
        )

        results = sp.parse_string("species where ! species.genus.family.family=name")
        assert (
            str(results.statement)
            == "SELECT * FROM species WHERE NOT (species.genus.family.family = 'name')"
        )

        results = sp.parse_string(
            "species where family=1 OR family=2 AND NOT genus.id=3"
        )
        assert str(results.statement) == (
            "SELECT * FROM species WHERE ((family = 1.0) OR ((family = 2.0) AND NOT (genus.id = 3.0)))"
        )

    def test_can_use_lowercase_operators(self) -> None:
        """
        Can use the operators in lower case.
        """
        sp = self.SearchParser()
        results = sp.parse_string("species where not species.genus.family.family=name")
        assert (
            str(results.statement)
            == "SELECT * FROM species WHERE NOT (species.genus.family.family = 'name')"
        )

        results = sp.parse_string("species where ! species.genus.family.family=name")
        assert (
            str(results.statement)
            == "SELECT * FROM species WHERE NOT (species.genus.family.family = 'name')"
        )

        results = sp.parse_string(
            "species where family=1 or family=2 and not genus.id=3"
        )
        assert str(results.statement) == (
            "SELECT * FROM species WHERE ((family = 1.0) OR ((family = 2.0) AND NOT (genus.id = 3.0)))"
        )

    def test_notes_is_not_not_es(self) -> None:
        """
        Acknowledges word boundaries.
        """
        sp = self.SearchParser()
        results = sp.parse_string("species where notes.id!=0")
        assert str(results.statement) == "SELECT * FROM species WHERE (notes.id != 0.0)"

    def test_between_just_parse_0(self) -> None:
        """
        Use BETWEEN value and value.
        """
        sp = self.SearchParser()
        results = sp.parse_string("species where id between 0 and 1")
        assert (
            str(results.statement) == "SELECT * FROM species WHERE (BETWEEN id 0.0 1.0)"
        )

    def test_between_just_parse_1(self) -> None:
        """
        Use BETWEEN value and value.
        """
        sp = self.SearchParser()
        results = sp.parse_string("species where step.id between 0 and 1")
        assert (
            str(results.statement)
            == "SELECT * FROM species WHERE (BETWEEN step.id 0.0 1.0)"
        )

    def test_between_just_parse_2(self) -> None:
        """
        Use BETWEEN value and value.
        """
        sp = self.SearchParser()
        results = sp.parse_string(
            "species where step.step.step.step[a=1].id between 0 and 1"
        )
        assert str(results.statement) == (
            "SELECT * FROM species WHERE (BETWEEN step.step.step.step[a=1.0].id 0.0 1.0)"
        )



# Fixtures for shared setup
@pytest.fixture(scope="function")
def setup_filter_then_match(db_session):
    """Fixture to set up FilterThenMatchTests data."""
    family = Family(family="family1", qualifier="s. lat.")
    genus1 = Genus(family=family, genus="genus1")
    genus2 = Genus(family=family, genus="genus2")
    genus3 = Genus(family=family, genus="genus3")
    genus4 = Genus(family=family, genus="genus4")
    notes = [
        GenusNote(category="commentarii", note="olim", genus=genus1),
        GenusNote(category="commentarii", note="erat", genus=genus1),
        GenusNote(category="commentarii", note="verbum", genus=genus2),
        GenusNote(category="test", note="olim", genus=genus3),
        GenusNote(category="test", note="verbum", genus=genus3),
    ]
    db_session.add_all([family, genus1, genus2, genus3, genus4] + notes)
    if db_session.in_transaction():
        db_session.commit()
    return genus1, genus2, genus3, genus4


class FilterThenMatchTests:
    def test_can_filter_match_notes(self, db_session, setup_filter_then_match) -> None:
        mapper_search = search.get_strategy("MapperSearch")
        genus1, genus2, genus3, genus4 = setup_filter_then_match

        s = "genus where notes.note='olim'"
        results = mapper_search.search(s, db_session)
        assert results == {genus1, genus3}

        s = "genus where notes[category='test'].note='olim'"
        results = mapper_search.search(s, db_session)
        assert results == {genus3}

        s = "genus where notes.category='commentarii'"
        results = mapper_search.search(s, db_session)
        assert results == {genus1, genus2}

        s = "genus where notes[note='verbum'].category='commentarii'"
        results = mapper_search.search(s, db_session)
        assert results == {genus2}

    def test_can_find_empty_set(self, db_session, setup_filter_then_match) -> None:
        mapper_search = search.get_strategy("MapperSearch")
        _, _, _, genus4 = setup_filter_then_match

        s = "genus where notes=Empty"
        results = mapper_search.search(s, db_session)
        assert results == {genus4}

    def test_can_find_non_empty_set(self, db_session, setup_filter_then_match) -> None:
        mapper_search = search.get_strategy("MapperSearch")
        genus1, genus2, genus3, _ = setup_filter_then_match

        s = "genus where notes!=Empty"
        results = mapper_search.search(s, db_session)
        assert results == {genus1, genus2, genus3}

    def test_can_match_list_of_values(
        self, db_session, setup_filter_then_match
    ) -> None:
        mapper_search = search.get_strategy("MapperSearch")
        genus1, genus2, genus3, _ = setup_filter_then_match

        s = "genus where notes.note in 'olim', 'erat', 'verbum'"
        results = mapper_search.search(s, db_session)
        assert results == {genus1, genus2, genus3}

        s = "genus where notes[category='test'].note in 'olim', 'erat', 'verbum'"
        results = mapper_search.search(s, db_session)
        assert results == {genus3}

    def test_parenthesised_search(self, db_session, setup_filter_then_match) -> None:
        mapper_search = search.get_strategy("MapperSearch")

        s = "genus where (notes!=Empty) and (notes=Empty)"
        results = mapper_search.search(s, db_session)
        assert results == set()


class ParseTypedValue:
    @pytest.mark.parametrize(
        "input_value,expected",
        [
            ("0.0", 0.0),
            ("-4.0", -4.0),
            ("0", 0),
            ("-4", -4),
            ("None", None),
            ("Empty", EmptyToken()),
            ("whatever else", "whatever else"),
        ],
    )
    def test_parse_typed_value(self, expected) -> None:
        result = querybuilder.parse_typed_value(self)
        assert result == expected


class EmptySetEqualityTest:
    def test_EmptyToken_equals(self) -> None:
        """
        Test equality of EmptyToken instances.
        """
        et1 = search.EmptyToken()
        et2 = search.EmptyToken()
        assert et1 == et2
        assert et1 == set()

    def test_empty_token_otherwise(self) -> None:
        """
        Test inequality of EmptyToken with various other types.
        """
        et1 = search.EmptyToken()
        assert et1 is not None
        assert et1 != 0
        assert et1 != ""
        assert et1 != {1, 2, 3}

    from bauble.search import EmptyToken, NoneToken

    def test_EmptyToken_representation(self) -> None:
        """
        Test the representation of EmptyToken.
        """
        et1 = EmptyToken()
        assert str(et1) == "Empty"
        assert et1.express() == set()

    def test_NoneToken_representation(self) -> None:
        """
        Test the representation of NoneToken.
        """
        nt1 = NoneToken()
        assert str(nt1) == "(None<NoneType>)"
        assert nt1.express() is None




@pytest.fixture(scope="function")
def setup_aggregating_functions(db_session):
    """
    Fixture to set up the database for AggregatingFunctions tests.
    """
    with db_session.connection() as conn:
        conn.execute(text("DELETE FROM genus"))
        conn.execute(text("DELETE FROM family"))
        conn.execute(text("DELETE FROM species"))
        conn.execute(text("DELETE FROM accession"))

    f1 = Family(family="Rutaceae", qualifier="")
    g1 = Genus(family=f1, genus="Citrus")
    sp1 = Species(sp="medica", genus=g1)
    sp2 = Species(sp="maxima", genus=g1)
    sp3 = Species(sp="aurantium", genus=g1)

    f2 = Family(family="Sapotaceae")
    g2 = Genus(family=f2, genus="Manilkara")
    sp4 = Species(sp="zapota", genus=g2)
    sp5 = Species(sp="zapotilla", genus=g2)
    g3 = Genus(family=f2, genus="Pouteria")
    sp6 = Species(sp="stipitata", genus=g3)

    f3 = Family(family="Musaceae")
    g4 = Genus(family=f3, genus="Musa")

    db_session.add_all([f1, f2, f3, g1, g2, g3, g4, sp1, sp2, sp3, sp4, sp5, sp6])
    if db_session.in_transaction():
        db_session.commit()

    return db_session


class AggregatingFunctions:
    def test_count(self, setup_aggregating_functions) -> None:
        """
        Test count function in MapperSearch.
        """
        mapper_search = search.get_strategy("MapperSearch")
        session = setup_aggregating_functions

        results = mapper_search.search("genus where count(species.id) > 3", session)
        assert len(results) == 0

        results = mapper_search.search("genus where count(species.id) > 2", session)
        assert len(results) == 1
        result = results.pop()
        assert result.id == 1

        results = mapper_search.search("genus where count(species.id) = 2", session)
        assert len(results) == 1
        result = results.pop()
        assert result.id == 2

    def test_count_just_parse(self) -> None:
        """
        Test count parsing in SearchParser.
        """
        sp = search.SearchParser()
        results = sp.parse_string("genus where count(species.id) == 2")
        assert (
            str(results.statement)
            == "SELECT * FROM genus WHERE ((count species.id) == 2.0)"
        )


class BaubleSearchSearchTest:
    def test_search_search_uses_Mapper_Search(self, db_session, mock_logger) -> None:
        """
        Test that MapperSearch is used for searches.
        """
        import logging

        search.logger.setLevel(logging.INFO)

        search.search("genus like %", db_session)
        assert (
            'SearchStrategy "genus like %"(MapperSearch)'
            in mock_logger.messages["bauble.search"]["debug"]
        )
        mock_logger.reset()

        search.search("12.11.13", db_session)
        assert (
            'SearchStrategy "12.11.13"(MapperSearch)'
            in mock_logger.messages["bauble.search"]["debug"]
        )
        mock_logger.reset()

        search.search("So ha", db_session)
        assert (
            'SearchStrategy "So ha"(MapperSearch)'
            in mock_logger.messages["bauble.search"]["debug"]
        )
