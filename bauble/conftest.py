#
# Copyright (c) 2005,2006,2007,2008,2009 Brett Adams <brett@belizebotanic.org>
# Copyright (c) 2012-2015 Mario Frasca <mario@anche.no>
# Copyright 2017 Jardin Botanico de Quito
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
import logging
import os
import sys
from collections.abc import Generator
from typing import Any

import pytest
from bauble import db, pluginmgr
from bauble.error import BaubleError
from bauble.prefs import prefs

logger: Any = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)
prefs.testing = True

DEFAULT_SQLITE_URI = "sqlite:////tmp/sqlite_test_db"
TEST_DB_URI = os.environ.get("GHINI_TEST_DB_URI", DEFAULT_SQLITE_URI)


@pytest.fixture(scope="session")
def init_bauble() -> None:
    """Initialize the database and plugins for tests."""
    prefs.init()
    prefs.testing = True
    try:
        db.open(TEST_DB_URI, verify=False)
    except Exception as e:
        print(e, file=sys.stderr)
        raise BaubleError("Failed to connect to the test database.") from e
    if not db.engine:
        raise BaubleError("Database engine is not initialized.")

    pluginmgr.load()
    from bauble.db import ensure_relationships_wired

    ensure_relationships_wired()
    db.metadata.create_all(bind=db.engine)
    pluginmgr.init(force=True)


@pytest.fixture(scope="function")
def db_session(init_bauble) -> Generator[Any, None, None]:
    """Return a test database session.

    Several legacy tests create/drop tables or commit explicitly, so a nested
    transaction wrapper is not reliable across SQLite and PostgreSQL. The
    autouse clean_db fixture provides isolation by recreating tables instead.
    """
    db.Session.remove()
    session = db.Session()

    try:
        yield session
    finally:
        if session.in_transaction():
            session.rollback()
        db.Session.remove()


@pytest.fixture(autouse=True)
def clean_db(db_session) -> None:
    """Drop and recreate all tables for a clean database before each test."""
    db.metadata.drop_all(bind=db.engine)
    db.metadata.create_all(bind=db.engine)


@pytest.fixture
def mock_logger(request) -> Generator[Any, None, None]:
    """Capture logs during tests."""
    from bauble.test import MockLoggingHandler

    handler = MockLoggingHandler()
    long_test_module_path = request.node.fspath.dirname.replace("/", ".")
    test_module_name = request.node.fspath.basename.rsplit(".", 1)[0]
    test_module_path = long_test_module_path.removeprefix(".app.")
    default_logger_name = f"{test_module_path}.{test_module_name}"

    test_class = request.cls
    test_func = request.function
    logger_name = (
        getattr(test_class, "logger_name", None)
        or getattr(test_func, "logger_name", None)
        or default_logger_name
    )

    target_logger = logging.getLogger(logger_name)
    target_logger.addHandler(handler)
    yield handler
    target_logger.removeHandler(handler)
