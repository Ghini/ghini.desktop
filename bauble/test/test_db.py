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
# Refactored for Pytest and SQLAlchemy 2.0.36 compatibility

import pytest
from bauble import db
from bauble.plugins.garden.models import AccessionNote
from bauble.plugins.plants.genus import Genus
from bauble.prefs import prefs

prefs.testing = True

# db.sqlalchemy_debug(True)


# Tests
def test_class_of_object_genus() -> None:
    """
    Verify that db.class_of_object('genus') returns the correct Genus class.
    """
    assert db.class_of_object("genus") == Genus


def test_class_of_object_accession_note() -> None:
    """
    Verify that db.class_of_object('accession_note') returns the correct AccessionNote class.
    """
    assert db.class_of_object("accession_note") == AccessionNote


def test_class_of_object_not_existing() -> None:
    """
    Verify that db.class_of_object raises a ValueError for an invalid object type.
    """
    with pytest.raises(ValueError, match="Class not found for object: not_existing"):
        db.class_of_object("not_existing")
