# Copyright 2018 Mario Frasca <mario@anche.no>.
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
from bauble.plugins.plants.family import Family
from bauble.plugins.plants.genus import Genus
from sqlalchemy import text

from .taxonomy_check import species_to_fix as species_to_fix


@pytest.fixture(scope="function")
def setup_data(db_session):
    """
    Fixture to initialize the test database with required data.
    """
    family1 = Family(epithet="Amaranthaceae")
    family2 = Family(epithet="Fabaceae")
    genus1 = Genus(family=family1, epithet="Salsola")
    genus2 = Genus(family=family2, epithet="Trifolium")
    db_session.add_all([family1, family2, genus1, genus2])
    if db_session.in_transaction():
        db_session.commit()
    return db_session


@pytest.fixture(autouse=True)
def clear_family_table(db_session) -> None:
    """
    Ensure the family table is cleared before each test.
    """
    db_session.execute(text("DELETE FROM genus"))
    db_session.execute(text("DELETE FROM family"))
    if db_session.in_transaction():
        db_session.commit()


@pytest.mark.usefixtures("db_session", "setup_data")
class TestTaxonomyCheck:

    def test_species_author(self, db_session) -> None:
        """
        Test that the species author is correctly handled.
        """
        s = species_to_fix(db_session, "Salsola kali", "L.", True)
        assert s is not None
        assert s.epithet == "kali"
        assert s.author == "L."
        assert s.infraspecific_rank == ""
        assert s.infraspecific_epithet == ""
        assert s.infraspecific_author == ""

    def test_subspecies_author(self, db_session) -> None:
        """
        Test that the subspecies author is correctly handled.
        """
        s = species_to_fix(
            db_session, "Salsola kali subsp. tragus", "(L.) Čelak.", True
        )
        assert s is not None
        assert s.epithet == "kali"
        assert s.author is None
        assert s.infraspecific_rank == "subsp."
        assert s.infraspecific_epithet == "tragus"
        assert s.infraspecific_author == "(L.) Čelak."
