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
#
# test.py
#
# Description: test for bauble.utils
from collections.abc import Generator
from typing import Any

import bauble.utils as utils
import pytest
from bauble.error import CheckConditionError
from bauble.gtkinit import Gtk
from bauble.utils import topological_sort
from sqlalchemy import Column, ForeignKey, Integer, Sequence, Table


def test_create_message_details_dialog() -> None:
    pytest.skip("Not Implemented")  # Skip the test with pytest's skip functionality
    details = """these are the lines that i want to test
asdasdadasddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd
dasd
asd
addasdadadad"""
    msg = "msg"
    dialog = utils.create_message_details_dialog(msg, details)
    dialog.show()
    dialog.response(Gtk.ResponseType.OK)
    dialog.destroy()


def test_create_message_dialog() -> None:
    pytest.skip("Not Implemented")  # Skip the test with pytest's skip functionality
    msg = "msg"
    # msg = ' this is a longer message to test that the dialog width is correct.....but what if it keeps going'
    dialog = utils.create_message_dialog(msg)
    dialog.show()
    dialog.response(Gtk.ResponseType.OK)
    dialog.destroy()


def test_search_tree_model() -> None:

    from bauble.gtkinit import Gtk

    model = Gtk.TreeStore(str)

    # The rows that should be found
    to_find = []

    row = model.append(None, ["1"])
    model.append(row, ["1.1"])
    to_find.append(model.append(row, ["something"]))
    model.append(row, ["1.3"])

    row = model.append(None, ["2"])
    to_find.append(model.append(row, ["something"]))
    model.append(row, ["2.1"])

    to_find.append(model.append(None, ["something"]))

    root = model.get_iter_first()
    results = utils.search_tree_model(model[root], "something")

    # Convert paths to strings for easier comparison
    found_paths = sorted([model.get_path(r).to_string() for r in results])
    expected_paths = sorted([model.get_path(r).to_string() for r in to_find])

    assert (
        found_paths == expected_paths
    ), f"Expected paths: {expected_paths}, but found: {found_paths}"


def test_xml_safe():
    class Test:
        def __str__(self):
            return repr(self)

        def __unicode__(self):
            return repr(self)

    import re

    assert re.match(r"&lt;.*?&gt;", utils.xml_safe(str(Test())))
    assert utils.xml_safe("test string") == "test string"
    assert utils.xml_safe("test< string") == "test&lt; string"


def test_range_builder() -> None:
    assert utils.range_builder("1-3") == [1, 2, 3]
    assert utils.range_builder("1-3,5-7") == [1, 2, 3, 5, 6, 7]
    assert utils.range_builder("1-3,5") == [1, 2, 3, 5]
    assert utils.range_builder("1-3,5,7-9") == [1, 2, 3, 5, 7, 8, 9]
    assert utils.range_builder("1,2,3,4") == [1, 2, 3, 4]
    assert utils.range_builder("11") == [11]

    # Bad range strings
    assert utils.range_builder("-1") == []
    assert utils.range_builder("a-b") == []

    with pytest.raises(CheckConditionError):
        utils.range_builder("2-1")


def test_get_urls() -> None:
    text = "There a link in here: http://bauble.belizebotanic.org"
    urls = utils.get_urls(text)
    assert urls == [(None, "http://bauble.belizebotanic.org")]

    text = (
        "There a link in here: http://bauble.belizebotanic.org "
        "and some text afterwards."
    )
    urls = utils.get_urls(text)
    assert urls == [(None, "http://bauble.belizebotanic.org")]

    text = (
        "There is a link here: http://bauble.belizebotanic.org "
        "and here: https://belizebotanic.org and some text afterwards."
    )
    urls = utils.get_urls(text)
    assert urls == [
        (None, "http://bauble.belizebotanic.org"),
        (None, "https://belizebotanic.org"),
    ]

    text = (
        "There a labeled link in here: "
        "[BBG]http://bauble.belizebotanic.org and some text afterwards."
    )
    urls = utils.get_urls(text)
    assert urls == [("BBG", "http://bauble.belizebotanic.org")]


@pytest.fixture
def dependent_tables_metadata(db_session) -> Generator[Any, None, None]:
    """
    Fixture to set up the test metadata and tables for dependency tests.
    Cleans up after the test.
    """
    metadata = db_session.bind.metadata

    # table1 does not depend on any tables
    table1 = Table("table1", metadata, Column("id", Integer, primary_key=True))

    # table2 depends on table1
    table2 = Table(
        "table2",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("table1", Integer, ForeignKey("table1.id")),
    )

    # table3 depends on table2 and table4
    table3 = Table(
        "table3",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("table2", Integer, ForeignKey("table2.id")),
        Column("table4", Integer, ForeignKey("table4.id")),
    )

    # table4 depends on table2
    table4 = Table(
        "table4",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("table2", Integer, ForeignKey("table2.id")),
    )

    metadata.create_all(bind=db_session.bind)

    yield table1, table2, table3, table4

    metadata.drop_all(bind=db_session.bind)


def test_find_dependent_tables(db_session, dependent_tables_metadata) -> None:
    """
    Test `utils.find_dependent_tables` for various table dependency scenarios.
    """
    metadata = db_session.bind.metadata
    table1, table2, table3, table4 = dependent_tables_metadata

    # Tables that depend on table1: table2, table4, table3
    depends = list(utils.find_dependent_tables(table1, metadata))
    assert depends == [
        table2,
        table4,
        table3,
    ], f"Expected [table2, table4, table3], got {depends}"

    # Tables that depend on table2: table4, table3
    depends = list(utils.find_dependent_tables(table2, metadata))
    assert depends == [table4, table3], f"Expected [table4, table3], got {depends}"

    # No tables depend on table3
    depends = list(utils.find_dependent_tables(table3, metadata))
    assert depends == [], f"Expected [], got {depends}"

    # Tables that depend on table4: table3
    depends = list(utils.find_dependent_tables(table4, metadata))
    assert depends == [table3], f"Expected [table3], got {depends}"


def get_currval(session, col):
    """
    Helper function to get the current sequence value for a column.
    """
    engine = session.bind
    if engine.name == "postgresql":
        name = f"{col.table.name}_{col.name}_seq"
        stmt = f"SELECT currval('{name}');"
        return session.execute(stmt).scalar()
    elif engine.name == "sqlite":
        stmt = f"SELECT max({col.name}) FROM {col.table.name}"
        return session.execute(stmt).scalar() + 1
    else:
        raise NotImplementedError("Unsupported database engine.")


@pytest.fixture
def test_table(db_session) -> Generator[Any, None, None]:
    """
    Fixture to provide a simple test table for sequence-related operations.
    """
    table = Table(
        "test_reset_sequence",
        db_session.bind.metadata,
        Column("id", Integer, primary_key=True),
    )
    table.create(bind=db_session.bind, checkfirst=True)
    yield table
    table.drop(bind=db_session.bind, checkfirst=True)


@pytest.fixture
def test_table_with_sequence(db_session) -> Generator[Any, None, None]:
    """
    Fixture to provide a test table with an explicit sequence for the primary key.
    """
    table = Table(
        "test_reset_sequence",
        db_session.bind.metadata,
        Column(
            "id",
            Integer,
            Sequence("test_reset_sequence_id_seq"),
            primary_key=True,
            unique=True,
        ),
    )
    table.create(bind=db_session.bind, checkfirst=True)
    yield table
    table.drop(bind=db_session.bind, checkfirst=True)


def test_no_col_sequence(db_session, test_table) -> None:
    """
    Test utils.reset_sequence on a column without an explicit sequence.
    """
    # Insert a record into the table
    db_session.execute(test_table.insert().values(id=1))

    # Reset the sequence and ensure no errors occur
    utils.reset_sequence(test_table.c.id)


def test_empty_col_sequence(db_session, test_table) -> None:
    """
    Test utils.reset_sequence on an empty table without an explicit sequence.
    """
    # Reset the sequence and ensure no errors occur
    utils.reset_sequence(test_table.c.id)


def test_with_col_sequence(db_session, test_table_with_sequence) -> None:
    """
    Test utils.reset_sequence on a column with an explicit sequence.
    """
    rangemax = 10

    # Insert records into the table
    for i in range(1, rangemax + 1):
        db_session.execute(test_table_with_sequence.insert().values(id=i))

    # Reset the sequence
    utils.reset_sequence(test_table_with_sequence.c.id)

    # Verify the sequence has been reset
    currval = get_currval(db_session, test_table_with_sequence.c.id)
    assert (
        currval > rangemax
    ), f"Sequence value {currval} is not greater than {rangemax}."


def test_empty_dependencies() -> None:
    r = topological_sort(["a", "b", "c"], [])
    assert "a" in r
    assert "b" in r
    assert "c" in r


def test_full_dependencies() -> None:
    r = topological_sort(["a", "b", "c"], [("a", "b"), ("b", "c")])
    assert "a" in r
    assert "b" in r
    assert "c" in r
    assert r.pop() == "c"
    assert r.pop() == "b"
    assert r.pop() == "a"


def test_partial_dependencies() -> None:
    r = topological_sort(["b", "e"], [("a", "b"), ("b", "c"), ("b", "d")])
    print(r)
    assert "e" in r
    r.remove("e")
    any_set = {r.pop(), r.pop()}
    assert any_set == {"c", "d"}
    assert r.pop() == "b"
    # assert r == []  # This assertion is commented in the original


def test_empty_input_full_dependencies() -> None:
    topological_sort([], [("a", "b"), ("b", "c"), ("b", "d")])
    # assert r == []  # This assertion is commented in the original
