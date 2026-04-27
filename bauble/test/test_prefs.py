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
from tempfile import NamedTemporaryFile

import pytest

from bauble import prefs, version_tuple

from typing import Any
from collections.abc import Generator

prefs.testing = True


@pytest.fixture
def temp_prefs_file() -> Generator[Any, None, None]:
    """
    Provides a temporary preferences file for testing.
    """
    with NamedTemporaryFile(suffix=".dict", delete=True) as temp_file:
        yield temp_file.name


def test_create_does_not_save(temp_prefs_file) -> None:
    """
    Test that creating preferences does not save the file by default.
    """
    p = prefs._prefs(temp_prefs_file)
    p.init()
    with open(temp_prefs_file) as f:
        assert f.read() == "", "Preferences file should be empty after creation"


def test_assert_initial_values(temp_prefs_file) -> None:
    """
    Verify the default values in preferences.
    """
    p = prefs._prefs(temp_prefs_file)
    p.init()
    assert prefs.config_version_pref in p
    assert prefs.picture_root_pref in p
    assert prefs.date_format_pref in p
    assert prefs.parse_dayfirst_pref in p
    assert prefs.parse_yearfirst_pref in p
    assert prefs.units_pref in p
    assert p[prefs.config_version_pref] == version_tuple[:2]
    assert p[prefs.picture_root_pref] == ""
    assert p[prefs.date_format_pref] == "%d-%m-%Y"
    assert p[prefs.parse_dayfirst_pref] is True
    assert p[prefs.parse_yearfirst_pref] is False
    assert p[prefs.units_pref] == "metric"


def test_not_saved_while_testing(temp_prefs_file) -> None:
    """
    Verify that preferences are not saved during testing unless forced.
    """
    p = prefs._prefs(temp_prefs_file)
    p.init()
    p.save()
    with open(temp_prefs_file) as f:
        assert f.read() == "", "Preferences file should not be saved during testing"


def test_can_force_save(temp_prefs_file) -> None:
    """
    Verify that forcing a save writes to the preferences file.
    """
    p = prefs._prefs(temp_prefs_file)
    p.init()
    p.save(force=True)
    with open(temp_prefs_file) as f:
        assert f.read() != "", "Preferences file should not be empty after forced save"


def test_get_does_not_store_values(temp_prefs_file) -> None:
    """
    Verify that retrieving non-existent keys does not store them.
    """
    p = prefs._prefs(temp_prefs_file)
    p.init()
    assert "not_there_yet.1" not in p
    assert p["not_there_yet.1"] is None
    assert p.get("not_there_yet.2", 33) == 33
    assert p.get("not_there_yet.3", None) is None
    assert "not_there_yet.1" not in p
    assert "not_there_yet.2" not in p
    assert "not_there_yet.3" not in p


def test_use_setitem_to_store_value_and_create_section(temp_prefs_file) -> None:
    """
    Verify storing a value creates the section and the key.
    """
    p = prefs._prefs(temp_prefs_file)
    p.init()
    assert "test.not_there_yet-1" not in p
    p["test.not_there_yet-1"] = "all is a ball"
    assert "test.not_there_yet-1" in p
    assert p["test.not_there_yet-1"] == "all is a ball"
    assert p.get("test.not_there_yet-1", 33) == "all is a ball"


def test_most_values_converted_to_string(temp_prefs_file) -> None:
    """
    Verify that most values are converted to strings for storage.
    """
    p = prefs._prefs(temp_prefs_file)
    p.init()
    p["test.not_there_yet-1"] = 1
    assert (
        p["test.not_there_yet-1"] == "1"
    ), "Integer values should be converted to strings"
    p["test.not_there_yet-3"] = None
    assert (
        p["test.not_there_yet-3"] == "None"
    ), "None should be converted to the string 'None'"


def test_boolean_values_stay_boolean(temp_prefs_file) -> None:
    """
    Verify that boolean values retain their type.
    """
    p = prefs._prefs(temp_prefs_file)
    p.init()
    p["test.not_there_yet-1"] = True
    assert p["test.not_there_yet-1"] is True
    p["test.not_there_yet-2"] = False
    assert p["test.not_there_yet-2"] is False


def test_saved_dictionary_like_ini_file(temp_prefs_file) -> None:
    """
    Verify preferences are saved in a dictionary-like format.
    """
    p = prefs._prefs(temp_prefs_file)
    p.init()
    p["test.not_there_yet-1"] = 1
    p.save(force=True)
    with open(temp_prefs_file) as f:
        content = f.read()
        assert (
            "not_there_yet-1 = 1" in content
        ), "Key-value pair should be present in the file"
        assert "[test]" in content, "Section header should be present in the file"
