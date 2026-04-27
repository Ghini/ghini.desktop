#
# Copyright (c) 2005,2006,2007,2008,2009 Brett Adams <brett@belizebotanic.org>
# Copyright (c) 2012-2015 Mario Frasca <mario@anche.no>
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
# test_bauble.py
#
# Refactored to use Pytest and SQLAlchemy 2.0.36

import datetime
import logging
import os
import tempfile
import time
from collections.abc import Generator
from io import BytesIO
from typing import Any

import bauble.btypes as types
import pytest
from bauble import db, meta, prefs
from bauble.plugins.plants import Family
from bauble.test import check_dupids
from sqlalchemy import Integer, select, text
from sqlalchemy.orm import Mapped, mapped_column

logger: Any = logging.getLogger(__name__)
logger._cache.clear()
logger.setLevel(logging.INFO)
prefs.testing = True


# @pytest.fixture
# def clean_enum_table(db_session):
#     """
#     Fixture to clean and create the Enum test table for each test.
#     """
# #    metadata = db.Base.metadata
# #    if "test_enum_type" in metadata.tables:
# #        del metadata.tables["test_enum_type"]  # Remove existing table definition

#     class _TestEnum(db.Base):
#         __tablename__ = "test_enum_type"
#         id = Column(Integer, primary_key=True)
#         value = Column(types.Enum(values=["1", "2", ""]), default="")

#     metadata = db.Base.metadata
#     if "test_enum_type" in metadata.tables:
#         metadata.remove(_TestEnum.__table__)

#     _TestEnum.__table__.drop(bind=db_session.bind, checkfirst=True)
#     _TestEnum.__table__.create(bind=db_session.bind)

#     yield _TestEnum


#     _TestEnum.__table__.drop(bind=db_session.bind, checkfirst=True)
class _TestEnum(db.Base):
    __tablename__: str = "test_enum_type"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    value: Mapped[str] = mapped_column(
        types.Enum(values=["1", "2", ""], omit_aliases=False), default=""
    )


@pytest.fixture
def clean_enum_table(db_session) -> Generator[Any, None, None]:
    """
    Fixture to clean and create the Enum test table for each test.
    """

    # Ensure SQLAlchemy ORM is fully aware of metadata changes
    if db_session.in_transaction():
        db_session.rollback()  # Clear pending transactions

    # Drop the table if it exists
    _TestEnum.__table__.drop(bind=db_session.bind, checkfirst=True)

    # Remove the table from SQLAlchemy metadata to prevent caching issues
    metadata = db.Base.metadata
    if "test_enum_type" in metadata.tables:
        metadata.remove(metadata.tables["test_enum_type"])

    # Ensure the ORM is aware of the dropped table
    if db_session.in_transaction():
        db_session.commit()

    # Recreate the table
    _TestEnum.__table__.create(bind=db_session.bind)
    if db_session.in_transaction():
        db_session.commit()

    yield _TestEnum  # Provide the table for the test

    # Drop the table after the test
    _TestEnum.__table__.drop(bind=db_session.bind, checkfirst=True)
    if db_session.in_transaction():
        db_session.commit()


class TestEnumModel:
    """
    Tests for Enum-based SQLAlchemy model.
    """

    def test_insert_low_level(self, db_session, clean_enum_table) -> None:
        # ✅ Get database dialect (SQLite, PostgreSQL, etc.)
        dialect_name = db_session.bind.dialect.name

        # Check if the table exists before inserting
        if dialect_name == "sqlite":
            query = text("SELECT name FROM sqlite_master WHERE type='table';")
        else:
            query = text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='public';"
            )

        table_names = db_session.execute(query).all()
        print(f"Existing tables: {table_names}")
        # Debug: Ensure the row does not already exist
        existing_row = (
            db_session.execute(select(clean_enum_table).where(clean_enum_table.id == 1))
            .scalars()
            .first()
        )
        if existing_row:
            print(f"Row already exists before test: {existing_row}")
        else:
            print("No existing row, inserting...")

        # Perform the raw insert
        db_session.execute(clean_enum_table.__table__.insert().values(id=1))

        # Force the session to refresh its state
        db_session.expire_all()

        # Commit the transaction
        if db_session.in_transaction():
            db_session.commit()

        # Verify the row was inserted
        inserted_row = (
            db_session.execute(select(clean_enum_table).where(clean_enum_table.id == 1))
            .scalars()
            .first()
        )
        assert inserted_row is not None, "Row was not inserted properly!"

    def test_insert_alchemic(self, db_session, clean_enum_table) -> None:
        instance = clean_enum_table(id=1)
        db_session.add(instance)
        db_session.flush()

    def test_insert_by_value_ok(self, db_session, clean_enum_table) -> None:
        instance = clean_enum_table(value="1")
        db_session.add(instance)
        db_session.flush()

    def test_insert_by_value_wrong_value_seen_late(
        self, db_session, clean_enum_table
    ) -> None:
        from sqlalchemy.exc import StatementError

        instance = clean_enum_table(value="33")
        db_session.add(instance)
        with pytest.raises(StatementError):
            db_session.flush()
        # ✅ Ensure rollback after the test runs
        if db_session.in_transaction():
            db_session.rollback()

    def function_creating_enum(self, name, values, **kwargs):
        """
        Helper function to dynamically create an Enum-based table.
        """
        table_class = type(
            f"test_table_{name}",
            (db.Base,),
            {
                "__tablename__": f"test_enum_type_{name}",
                "id": mapped_column(Integer, primary_key=True),
                "value": mapped_column(
                    types.Enum(values=values, omit_aliases=False, **kwargs), default=""
                ),
            },
        )
        table_class.__table__.create(bind=db.engine, checkfirst=True)
        return table_class

    def test_bad_enum(self, db_session) -> None:
        """
        Test invalid Enum configurations.
        """
        self.function_creating_enum(
            "zero",
            ["1", "2", "3"],
        )

        with pytest.raises(types.EnumError):
            self.function_creating_enum("one", [])

        with pytest.raises(types.EnumError):
            self.function_creating_enum("two", None)

        with pytest.raises(types.EnumError):
            self.function_creating_enum("three", [1, ""])  # Invalid type

        with pytest.raises(types.EnumError):
            self.function_creating_enum("four", ["1", "1"])  # Duplicate values

        with pytest.raises(types.EnumError):
            self.function_creating_enum("five", ["1", [], None])  # Invalid types

        with pytest.raises(types.EnumError):
            self.function_creating_enum(
                "six", ["1", "2"], empty_to_none=True
            )  # empty_to_none with empty string
        # ✅ Ensure rollback after the test runs
        if db_session.in_transaction():
            db_session.rollback()

    def test_empty_to_none(self, db_session) -> None:
        """
        Test the `empty_to_none` functionality for Enums.
        """
        _TestEnum = self.function_creating_enum(
            "seven", ["1", None], empty_to_none=True
        )

        # Insert rows into the table
        row1 = _TestEnum(value="1")
        row2 = _TestEnum(value="")
        db_session.add_all([row1, row2])
        db_session.flush()

        # Query for empty string (should return nothing)
        query = db_session.execute(
            select(_TestEnum).where(_TestEnum.value == "")
        ).scalars()
        assert query.all() == []

        # Query for None (should return row2)
        query = db_session.execute(
            select(_TestEnum).where(_TestEnum.value is None)
        ).scalars()
        assert query.all() == [row2]

    def test_function_creating_enum_with_fixture(
        self, db_session, clean_enum_table
    ) -> None:
        """
        Ensure the `function_creating_enum` works with the clean_enum_table fixture.
        """
        # Test Enum setup
        row = clean_enum_table(value="1")
        db_session.add(row)
        db_session.flush()

        query = db_session.execute(
            select(clean_enum_table).where(clean_enum_table.value == "1")
        ).scalars()
        assert query.first() == row


@pytest.mark.usefixtures("clean_db")
class TestDateTypes:
    """
    Tests for Date and DateTime types in bauble.btypes.
    """

    def test_date_type(self) -> None:
        from bauble.btypes import Date

        dt = Date()

        # MM-DD-YYYY format
        prefs.dayfirst = False
        prefs.yearfirst = False
        s = "12-30-2008"
        v = dt.process_bind_param(s, None)
        assert v.month == 12 and v.day == 30 and v.year == 2008

        # DD-MM-YYYY format
        prefs.dayfirst = True
        prefs.yearfirst = False
        s = "30-12-2008"
        v = dt.process_bind_param(s, None)
        assert v.month == 12 and v.day == 30 and v.year == 2008

        # YYYY-MM-DD format
        prefs.dayfirst = False
        prefs.yearfirst = True
        s = "2008-12-30"
        v = dt.process_bind_param(s, None)
        assert v.month == 12 and v.day == 30 and v.year == 2008

    def test_datetime_type(self) -> None:
        from bauble.btypes import DateTime

        dt = DateTime()

        # DateTime with negative timezone
        s = "2008-12-1 11:50:01.001-05:00"
        result = "2008-12-01 11:50:01.001000-05:00"
        v = dt.process_bind_param(s, None)
        assert str(v) == result

        # DateTime with positive timezone
        s = "2008-12-1 11:50:01.001+05:00"
        result = "2008-12-01 11:50:01.001000+05:00"
        v = dt.process_bind_param(s, None)
        assert str(v) == result

        # DateTime with no timezone
        s = "2008-12-1 11:50:01.001"
        result = "2008-12-01 11:50:01.001000"
        v = dt.process_bind_param(s, None)
        assert str(v) == result

        # test with no milliseconds
        s = "2008-12-1 11:50:01"
        result = "2008-12-01 11:50:01"
        v = dt.process_bind_param(s, None)
        assert v.isoformat(" ") == result

    def test_base_table(self, db_session) -> None:
        """
        Test `_created` and `_last_updated` fields in `BaubleMeta`.
        """
        # Insert a new record
        m = meta.BaubleMeta(name="name", value="value")
        db_session.add(m)
        if db_session.in_transaction():
            db_session.commit()

        # Query the record back
        m = (
            db_session.execute(
                select(meta.BaubleMeta).where(meta.BaubleMeta.name == "name")
            )
            .scalars()
            .first()
        )

        # Assert `_created` and `_last_updated` are properly created
        assert hasattr(m, "_created") and isinstance(m._created, datetime.datetime)
        assert hasattr(m, "_last_updated") and isinstance(
            m._last_updated, datetime.datetime
        )

        # Save the timestamps for comparison
        created = m._created
        last_updated = m._last_updated

        # Sleep to ensure timestamp granularity and update the record
        time.sleep(1.1)
        m.value = "value2"
        if db_session.in_transaction():
            db_session.commit()
        db_session.expire(m)

        # Assert `_created` does not change but `_last_updated` does
        assert isinstance(m._created, datetime.datetime)
        assert m._created == created
        assert isinstance(m._last_updated, datetime.datetime)
        assert m._last_updated != last_updated

    def test_duplicate_ids(self) -> None:
        """
        Test for duplicate IDs in all `.glade` files.
        """
        import glob

        import bauble as mod

        # Get the directory of the module
        head, _ = os.path.split(mod.__file__)

        # Find all `.glade` files
        glade_files = glob.glob(os.path.join(head, "*.glade"))

        # Assert no duplicate IDs in any `.glade` file
        for f in glade_files:
            ids = check_dupids(f)
            assert ids == [], f"{f} has duplicate IDs: {ids}"


@pytest.mark.usefixtures("clean_db")
class TestHistory:
    """
    Tests for tracking history changes in the database.
    """

    def test_history_tracking(self, db_session) -> None:
        f = Family(family="Family")
        db_session.add(f)
        if db_session.in_transaction():
            db_session.commit()

        # Insert operation
        history = (
            db_session.execute(select(db.History).order_by(db.History.timestamp.desc()))
            .scalars()
            .first()
        )
        assert history.table_name == "family"
        assert history.operation == "insert"

        # Update operation
        f.family = "Family2"
        if db_session.in_transaction():
            db_session.commit()
        history = (
            db_session.execute(select(db.History).order_by(db.History.timestamp.desc()))
            .scalars()
            .first()
        )
        assert history.table_name == "family"
        assert history.operation == "update"

        # Delete operation
        db_session.delete(f)
        if db_session.in_transaction():
            db_session.commit()
        history = (
            db_session.execute(select(db.History).order_by(db.History.timestamp.desc()))
            .scalars()
            .first()
        )
        assert history.table_name == "family"
        assert history.operation == "delete"

    def verify_base_and_session(self) -> None:
        """
        Verify that the Base, session, and engine configurations are correct.
        """
        from bauble.plugins.plants import Family

        print(f"Family Base: {Family.__bases__}")
        print(f"db.Base class: {db.Base.__class__}")
        print(f"Family table: {Family.__table__}")
        print(f"Base metadata tables: {db.Base.metadata.tables.keys()}")
        print(f"Engine metadata bind: {db.Base.metadata.bind}")
        # Verify Base metadata binding
        assert (
            db.Base.metadata.bind == db.engine
        ), "Base metadata is not bound to the correct engine!"

        # Verify session binding
        assert (
            self.session.bind == db.engine
        ), "Session is not bound to the correct engine!"

        # Verify the model's Base

        assert issubclass(
            Family, db.Base
        ), "Family is not derived from the correct Base!"
        logger.info("All Base and session checks passed.")


from bauble.editor import GenericEditorPresenter, GenericEditorView


@pytest.mark.usefixtures("clean_db")
class TestMVP:
    """
    Tests for MVP (Model-View-Presenter) components.
    """

    def test_can_programmatically_connect_signals(self) -> None:
        """
        Ensure that signals can be programmatically connected.
        """

        class HandlerDefiningPresenter(GenericEditorPresenter):
            def on_tag_desc_textbuffer_changed(self, *args):
                pass

        model = db.History()

        # Step 1: Create a base dialog with no attached signals
        handle, fn = tempfile.mkstemp()
        os.close(handle)
        with open(fn, "w") as ntf:
            ntf.write(
                """\
<interface>
  <requires lib="gtk+" version="2.24"/>
  <!-- interface-naming-policy toplevel-contextual -->
  <object class="GtkDialog" id="handler-defining-view"/>
</interface>
"""
            )
        view = GenericEditorView(fn, None, "handler-defining-view")
        presenter = HandlerDefiningPresenter(model, view)

        initial_signal_count = len(presenter.view._GenericEditorView__attached_signals)

        # Step 2: Add a text buffer with a signal attached
        handle, fn = tempfile.mkstemp()
        os.close(handle)
        with open(fn, "w") as ntf:
            ntf.write(
                """\
<interface>
  <requires lib="gtk+" version="2.24"/>
  <!-- interface-naming-policy toplevel-contextual -->
  <object class="GtkTextBuffer" id="tag_desc_textbuffer">
    <signal name="changed" handler="on_tag_desc_textbuffer_changed" swapped="no"/>
  </object>
  <object class="GtkDialog" id="handler-defining-view"/>
</interface>
"""
            )
        view = GenericEditorView(fn, None, "handler-defining-view")
        presenter = HandlerDefiningPresenter(model, view)

        # Assert the number of signals attached has increased
        assert (
            len(presenter.view._GenericEditorView__attached_signals)
            == initial_signal_count + 1
        )

        # Ensure the handler is callable
        presenter.on_tag_desc_textbuffer_changed()  # Avoid uncounted line!


@pytest.mark.parametrize(
    "version_stream, expected_result",
    [
        (BytesIO(b'version = "1.0.0"  # comment'), False),
        (BytesIO(b'version = "1.0.99999"  # comment'), True),
        (BytesIO(b'version = "1.0.99999"  # comment'), "1.0.99999"),
        (BytesIO(b'version = "1.099999"  # comment'), False),
        (BytesIO(b'version = "1.0.99999-dev"  # comment'), False),
    ],
)
def test_newer_version_on_github(version_stream, expected_result) -> None:
    """
    Test parsing and evaluation of version strings for newer versions on GitHub.
    """
    from bauble.connmgr import newer_version_on_github

    if logger.isEnabledFor(logging.INFO):
        logger.info("running unreleased version")
    result = newer_version_on_github(version_stream)
    if isinstance(expected_result, bool):
        assert bool(result) is expected_result
    else:
        assert result == expected_result
