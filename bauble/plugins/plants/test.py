#
# Copyright 2008-2010 Brett Adams
# Copyright 2015 Mario Frasca <mario@anche.no>.
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
# Description: test for the Plant plugin
#
import glob
import logging
import os
from collections.abc import Generator
from functools import partial
from typing import Any
from unittest.mock import patch

import pytest
from bauble import db, utils
from bauble.editor import MockView
from bauble.plugins.imex.csv_ import CSVImporter
from bauble.plugins.plants.family import Family as Family
from bauble.plugins.plants.family import FamilySynonym as FamilySynonym
from bauble.plugins.plants.family import remove_callback as remove_callback
from bauble.plugins.plants.genus import Genus, GenusSynonym
from bauble.plugins.plants.geography import GeographicArea as GeographicArea
from bauble.plugins.plants.geography import (
    get_species_in_geographic_area as get_species_in_geographic_area,
)
from bauble.plugins.plants.species import DefaultVernacularName as DefaultVernacularName
from bauble.plugins.plants.species import Species as Species
from bauble.plugins.plants.species import SpeciesNote as SpeciesNote
from bauble.plugins.plants.species import SpeciesSynonym as SpeciesSynonym
from bauble.plugins.plants.species import edit_species as edit_species
from bauble.plugins.plants.species_distribution import SpeciesDistribution
from bauble.plugins.plants.species_editor import SpeciesEditorPresenter
from bauble.plugins.plants.species_model import _remove_zws as remove_zws
from bauble.test import check_dupids, mockfunc
from editor import GenericModelViewPresenterEditor
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, NoResultFound


@pytest.fixture
def setup_plant_data() -> Generator[None, None, None]:
    """Fixture to populate the database with test data."""
    from bauble.plugins.plants.test import setUp_data

    setUp_data()
    yield
    db.metadata.drop_all(bind=db.engine)
    db.metadata.create_all(bind=db.engine)


def test_duplicate_ids_glade() -> None:
    """Test for duplicate IDs in .glade files within the plants plugin."""
    import bauble.plugins.plants as mod

    head, _ = os.path.split(mod.__file__)
    files = glob.glob(os.path.join(head, "*.glade"))
    for f in files:
        assert not check_dupids(f), f


@pytest.mark.usefixtures("setup_plant_data")
class TestFamily:
    """Tests related to the Family entity."""

    def test_cascades(self, session) -> None:
        family = Family(epithet="family")
        genus = Genus(family=family, epithet="genus")
        session.add_all([family, genus])
        if session.in_transaction():
            session.commit()

        # Test deleting a family deletes an orphaned genus
        session.delete(family)
        if session.in_transaction():
            session.commit()
        query = session.execute(select(Genus).where(Genus.family_id == family.id))
        with pytest.raises(NoResultFound):
            query.scalar_one()

    def test_synonyms(self, session) -> None:
        family = Family(epithet="family")
        family2 = Family(epithet="family2")
        family.synonyms.append(family2)
        session.add_all([family, family2])
        if session.in_transaction():
            session.commit()

        # Check synonym relation
        retrieved_family = session.execute(
            select(Family).where(Family.epithet == "family")
        ).scalar_one()
        assert family2 in retrieved_family.synonyms

        # Remove synonym
        family.synonyms.remove(family2)
        if session.in_transaction():
            session.commit()
        assert family2 not in family.synonyms

        # Test duplicate synonym constraint
        family.synonyms.append(family2)
        if session.in_transaction():
            session.commit()
        family.synonyms.append(family2)
        with pytest.raises(IntegrityError):
            if session.in_transaction():
                session.commit()
        if session.in_transaction():
            if session.in_transaction():
                session.rollback()

        # Clear all synonyms
        family.synonyms.clear()
        if session.in_transaction():
            session.commit()
        assert len(family.synonyms) == 0
        from sqlalchemy import func

        assert (
            session.execute(
                select(func.count()).select_from(FamilySynonym)
            ).scalar_one()
            == 0
        )

        # Delete a family with synonyms
        family.synonyms.append(family2)
        if session.in_transaction():
            session.commit()
        session.delete(family2)
        if session.in_transaction():
            session.commit()
        assert (
            session.execute(
                select(func.count()).select_from(FamilySynonym)
            ).scalar_one()
            == 0
        )

    def test_constraints(self, session) -> None:
        values = [
            {"epithet": "family"},
            {"epithet": "family", "qualifier": "s. lat."},
        ]
        for v in values:
            session.add(Family(**v))
            session.add(Family(**v))
            with pytest.raises(IntegrityError):
                if session.in_transaction():
                    session.commit()
            if session.in_transaction():
                if session.in_transaction():
                    session.rollback()

        # Family epithet cannot be null
        session.add(Family(epithet=None))
        with pytest.raises(IntegrityError):
            if session.in_transaction():
                session.commit()
        if session.in_transaction():
            if session.in_transaction():
                session.rollback()

    def test_str(self) -> None:
        f = Family()
        assert str(f) == repr(f)
        f = Family(epithet="fam")
        assert str(f) == "fam"
        f.qualifier = "s. lat."
        assert str(f) == "fam s. lat."

    @pytest.mark.skip(reason="Not implemented")
    def test_editor(self) -> None:
        """Placeholder for FamilyEditor tests."""
        pass


@pytest.mark.usefixtures("setup_plant_data")
class TestRemoveCallback:
    """Tests for the remove_callback function."""

    def test_remove_callback_no_genera_no_confirm(self, session) -> None:
        family = Family(epithet="Arecaceae")
        session.add(family)
        if session.in_transaction():
            session.commit()
        invoked = []

        utils.yes_no_dialog = partial(
            mockfunc, name="yes_no_dialog", caller=invoked, result=False
        )
        utils.message_details_dialog = partial(
            mockfunc, name="message_details_dialog", caller=invoked
        )

        result = remove_callback([family])
        if session.in_transaction():
            session.commit()

        assert "message_details_dialog" not in [func for func, _ in invoked]
        assert (
            "yes_no_dialog",
            "Are you sure you want to remove the family <i>Arecaceae</i>?",
        ) in invoked
        assert result is None

    def test_remove_callback_no_genera_confirm(self, session) -> None:
        family = Family(epithet="Arecaceae")
        session.add(family)
        if session.in_transaction():
            session.commit()
        invoked = []

        utils.yes_no_dialog = partial(
            mockfunc, name="yes_no_dialog", caller=invoked, result=True
        )
        utils.message_details_dialog = partial(
            mockfunc, name="message_details_dialog", caller=invoked
        )

        result = remove_callback([family])
        if session.in_transaction():
            session.commit()

        assert "message_details_dialog" not in [func for func, _ in invoked]
        assert (
            "yes_no_dialog",
            "Are you sure you want to remove the family <i>Arecaceae</i>?",
        ) in invoked
        assert result is True

    def test_remove_callback_with_genera_cant_cascade(self, session) -> None:
        family = Family(epithet="Arecaceae")
        genus = Genus(family=family, epithet="Areca")
        session.add_all([family, genus])
        if session.in_transaction():
            session.commit()
        invoked = []

        utils.yes_no_dialog = partial(
            mockfunc, name="yes_no_dialog", caller=invoked, result=True
        )
        utils.message_dialog = partial(
            mockfunc, name="message_dialog", caller=invoked, result=True
        )
        utils.message_details_dialog = partial(
            mockfunc, name="message_details_dialog", caller=invoked
        )

        remove_callback([family])
        if session.in_transaction():
            session.commit()

        assert "message_details_dialog" not in [func for func, _ in invoked]
        assert (
            "message_dialog",
            "The family <i>Arecaceae</i> has 1 genera.\n\nYou cannot remove a family with genera.",
        ) in invoked


@pytest.mark.usefixtures("setup_plant_data")
class TestGenus:
    """Tests related to the Genus entity."""

    def test_synonyms(self, session) -> None:
        family = Family(epithet="family")
        genus = Genus(family=family, epithet="genus")
        genus2 = Genus(family=family, epithet="genus2")
        genus.synonyms.append(genus2)
        session.add_all([genus, genus2])
        if session.in_transaction():
            session.commit()

        # Verify genus2 was added as a synonym
        retrieved_genus = session.execute(
            select(Genus).where(Genus.epithet == "genus")
        ).scalar_one()
        assert genus2 in retrieved_genus.synonyms

        # Verify backref works
        assert genus.synonyms[0].genus == genus
        assert genus.synonyms[0].synonym == genus2

        # Remove synonym and verify
        genus.synonyms.remove(genus2)
        if session.in_transaction():
            session.commit()
        assert genus2 not in genus.synonyms

        # Test duplicate synonym constraint
        genus.synonyms.append(genus2)
        if session.in_transaction():
            session.commit()
        genus.synonyms.append(genus2)
        with pytest.raises(IntegrityError):
            if session.in_transaction():
                session.commit()
        if session.in_transaction():
            if session.in_transaction():
                session.rollback()

        # Clear synonyms
        genus.synonyms.clear()
        if session.in_transaction():
            session.commit()
        assert len(genus.synonyms) == 0
        from sqlalchemy import func

        count_stmt = select(func.count()).select_from(GenusSynonym)
        count = session.execute(count_stmt).scalar_one()
        assert count == 0, f"Expected 0 synonyms, got {count}"

        # Test deletion of genus as synonym
        genus.synonyms.append(genus2)
        if session.in_transaction():
            session.commit()
        session.delete(genus2)
        if session.in_transaction():
            session.commit()
        count = session.execute(count_stmt).scalar_one()
        assert count == 0, f"Expected 0 synonyms, got {count}"

    def test_constraints(self, session) -> None:
        family = Family(epithet="family")
        session.add(family)

        values = [
            {"family": family, "epithet": "genus"},
            {"family": family, "epithet": "genus", "author": "author"},
            {"family": family, "epithet": "genus", "qualifier": "s. lat."},
            {
                "family": family,
                "epithet": "genus",
                "qualifier": "s. lat.",
                "author": "author",
            },
        ]

        for value in values:
            session.add(Genus(**value))
            session.add(Genus(**value))
            with pytest.raises(IntegrityError):
                if session.in_transaction():
                    session.commit()
            if session.in_transaction():
                if session.in_transaction():
                    session.rollback()

    def test_remove_callback_no_species_no_confirm(self, session) -> None:
        family = Family(epithet="Caricaceae")
        genus = Genus(epithet="Carica", family=family)
        session.add_all([family, genus])
        if session.in_transaction():
            session.commit()
        invoked = []

        # Mock confirmation dialogs
        utils.yes_no_dialog = partial(
            mockfunc, name="yes_no_dialog", caller=invoked, result=False
        )
        utils.message_details_dialog = partial(
            mockfunc, name="message_details_dialog", caller=invoked
        )

        result = remove_callback([genus])
        if session.in_transaction():
            session.commit()

        assert "message_details_dialog" not in [func for func, _ in invoked]
        assert (
            "yes_no_dialog",
            "Are you sure you want to remove the genus <i>Carica</i>?",
        ) in invoked
        assert result is None

    def test_remove_callback_with_species_cant_cascade(self, session) -> None:
        family = Family(epithet="Caricaceae")
        genus = Genus(epithet="Carica", family=family)
        species = Species(genus=genus, epithet="papaya")
        session.add_all([family, genus, species])
        if session.in_transaction():
            session.commit()
        invoked = []

        # Mock confirmation dialogs
        utils.yes_no_dialog = partial(
            mockfunc, name="yes_no_dialog", caller=invoked, result=True
        )
        utils.message_dialog = partial(mockfunc, name="message_dialog", caller=invoked)

        remove_callback([genus])
        if session.in_transaction():
            session.commit()

        assert "message_details_dialog" not in [func for func, _ in invoked]
        assert (
            "message_dialog",
            "The genus <i>Carica</i> has 1 species.\n\nYou cannot remove a genus with species.",
        ) in invoked
        assert genus in session.execute(select(Genus)).scalars().all()


@pytest.mark.usefixtures("setup_plant_data")
class TestGenusSynonymy:
    """Tests related to Genus synonymy."""

    def test_forward_synonyms(self, session) -> None:
        family = Family(epithet="Orchidaceae")
        genus = Genus(family=family, epithet="Bulbophyllum")
        synonym = Genus(family=family, epithet="Zygoglossum")
        genus.synonyms.append(synonym)
        session.add_all([family, genus, synonym])
        if session.in_transaction():
            session.commit()

        assert genus.synonyms == [synonym]
        assert synonym.synonyms == []

    def test_backward_synonyms(self, session) -> None:
        family = Family(epithet="Orchidaceae")
        genus = Genus(family=family, epithet="Bulbophyllum")
        synonym = Genus(family=family, epithet="Zygoglossum")
        genus.synonyms.append(synonym)
        session.add_all([family, genus, synonym])
        if session.in_transaction():
            session.commit()

        assert synonym.accepted == genus
        assert genus.accepted is None

    def test_define_accepted(self, session) -> None:
        family = Family(epithet="Orchidaceae")
        genus = Genus(family=family, epithet="Bulbophyllum")
        new_synonym = Genus(family=family, epithet="Henosis")
        session.add_all([family, genus, new_synonym])
        if session.in_transaction():
            session.commit()

        new_synonym.accepted = genus
        if session.in_transaction():
            session.commit()

        assert new_synonym in genus.synonyms
        assert len(genus.synonyms) == 1

    def test_can_redefine_accepted(self, session) -> None:
        family = Family(epithet="Crassulaceae")
        genus_villa = Genus(family=family, epithet="Villadia", author="Rose")
        genus_alta = Genus(family=family, epithet="Altamiranoa", author="Rose")
        genus_alta.accepted = genus_villa
        session.add_all([family, genus_alta, genus_villa])
        if session.in_transaction():
            session.commit()

        genus_sedum = Genus(family=family, epithet="Sedum", author="L.")
        genus_alta.accepted = genus_sedum
        if session.in_transaction():
            session.commit()

        assert genus_alta.accepted == genus_sedum





@pytest.mark.usefixtures("setup_plant_data")
class TestSpecies:
    """Tests for the Species functionality."""

    invoked: Any

    def test_species_editor(self, session) -> None:
        """
        Test the Species editor and its interaction with the database and garbage collection.
        """

        # Step 1: Mock CSV Importer for importing default data
        with patch("bauble.paths.lib_dir", return_value="/mock/path/to/lib"):
            default_path = "/mock/path/to/lib/plugins/plants/default"
            filenames = [
                f"{default_path}/geographic_area.txt",
                f"{default_path}/habit.txt",
            ]

            importer = CSVImporter()
            importer.start(filenames, force=True)

        # Step 2: Set up Family, Genus, and Species relationships
        family = Family(epithet="family")
        genus_1 = Genus(epithet="genus", family=family)
        genus_2 = Genus(epithet="genus2", family=family)
        genus_2.synonyms.append(genus_1)
        session.add_all([family, genus_1, genus_2])
        if session.in_transaction():
            session.commit()

        # Step 3: Create a species and open it in the editor
        species = Species(genus=genus_1, epithet="sp")
        edit_species(model=species)

        # Step 4: Check if editor-related objects are deleted from memory
        assert (
            utils.gc_objects_by_type("SpeciesEditor") == []
        ), "SpeciesEditor not deleted"
        assert (
            utils.gc_objects_by_type("SpeciesEditorPresenter") == []
        ), "SpeciesEditorPresenter not deleted"
        assert (
            utils.gc_objects_by_type("SpeciesEditorView") == []
        ), "SpeciesEditorView not deleted"

    def test_species_string(self, session, species_str_map):
        """
        Test the string representation of Species objects.
        """

        def get_species_string(species_id, **kwargs):
            """Helper function to fetch the string representation of a Species."""
            species = session.get(Species, species_id)
            return species.str(**kwargs)

        for species_id, expected_string in species_str_map.items():
            species = session.get(Species, species_id)

            # Verify basic string output
            printable_name = remove_zws(str(species))
            assert (
                printable_name == expected_string
            ), f"Mismatch in string representation for species ID {species_id}."

            # Verify helper function output
            species_string = get_species_string(species_id)
            assert (
                remove_zws(species_string) == expected_string
            ), f"Helper function string mismatch for species ID {species_id}."

    def test_species_string_with_authors(self, session, species_str_authors_map):
        """
        Test the string representation of Species with author information.
        """

        def get_species_string(species_id, **kwargs):
            """Helper function to fetch the string representation of a Species."""
            species = session.get(Species, species_id)
            return species.str(**kwargs)

        for species_id, expected_string in species_str_authors_map.items():
            species_string = get_species_string(species_id, authors=True)
            assert (
                remove_zws(species_string) == expected_string
            ), f"Mismatch in string representation with authors for species ID {species_id}."

    def test_species_string_with_markup(self, session, species_markup_map):
        """
        Test the string representation of Species with markup enabled.
        """

        def get_species_string(species_id, **kwargs):
            """Helper function to fetch the string representation of a Species."""
            species = session.get(Species, species_id)
            return species.str(**kwargs)

        for species_id, expected_string in species_markup_map.items():
            species_string = get_species_string(species_id, markup=True)
            assert (
                remove_zws(species_string) == expected_string
            ), f"Markup mismatch for species ID {species_id}."

    def test_species_string_with_markup_and_authors(
        self, session, species_markup_authors_map
    ):
        """
        Test the string representation of Species with markup and authors enabled.
        """

        def get_species_string(species_id, **kwargs):
            """Helper function to fetch the string representation of a Species."""
            species = session.get(Species, species_id)
            return species.str(**kwargs)

        for species_id, expected_string in species_markup_authors_map.items():
            species_string = get_species_string(species_id, markup=True, authors=True)
            assert (
                remove_zws(species_string) == expected_string
            ), f"Markup and authors mismatch for species ID {species_id}."

    def test_unspecified_precedes_specified(self, session):
        """
        Test that unspecified species names precede specified ones in lexicographic order.
        """

        def get_species_string(species_id, **kwargs):
            """Helper function to fetch the string representation of a Species."""
            species = session.execute(select(Species)).scalars().get(species_id)
            return species.str(**kwargs)

        # Define test cases
        test_cases = [
            (1, 22),
            (1, 23),
            (1, 24),
            (16, 22),
            (16, 23),
            (16, 24),
        ]

        # Validate lexicographic order
        for higher_id, lower_id in test_cases:
            higher_str = get_species_string(higher_id)
            lower_str = get_species_string(lower_id)
            assert higher_str > lower_str, (
                f"Expected '{higher_str}' (ID: {higher_id}) to precede "
                f"'{lower_str}' (ID: {lower_id}) in lexicographic order."
            )

    # def test_dirty_string(self, session):
    #     """
    #     Test that the cached string representation of a Species object
    #     is invalidated when the object is modified or expired.
    #     """
    #     # Step 1: Create and commit initial species
    #     family = Family(epithet="family")
    #     genus = Genus(family=family, epithet="genus")
    #     sp = Species(genus=genus, epithet="sp")
    #     session.add_all([family, genus, sp])
    #     session.commit()

    #     # Step 2: Capture initial string representation
    #     str1 = sp.str()

    #     # Step 3: Modify the species and commit the changes
    #     sp.epithet = "sp2"
    #     session.commit()

    #     # Step 4: Refresh and reload the species from the database
    #     session.refresh(sp)
    #     sp = session.get(Species, sp.id)

    #     # Step 5: Verify that the string representation has changed
    #     assert sp.str() != str1, "String cache was not invalidated after modification."

    def test_vernacular_name(self, session) -> None:
        """Test the `Species.vernacular_name` property."""
        family = Family(epithet="family")
        genus = Genus(family=family, epithet="genus")
        sp = Species(genus=genus, epithet="sp")
        session.add_all([family, genus, sp])
        if session.in_transaction():
            session.commit()

        # Add a vernacular name
        vn = VernacularName(name="name")
        sp.vernacular_names.append(vn)
        if session.in_transaction():
            session.commit()
        assert vn in sp.vernacular_names

        # Remove vernacular name and verify orphan deletion
        sp.vernacular_names.remove(vn)
        if session.in_transaction():
            session.commit()
        with pytest.raises(NoResultFound):
            session.execute(
                select(VernacularName).where(VernacularName.species_id == sp.id)
            ).scalar_one()

    def test_default_vernacular_name(self, session) -> None:
        """Comprehensive test for Species.default_vernacular_name."""

        # Step 1: Create family, genus, species, and initial vernacular name
        family = Family(epithet="family")
        genus = Genus(family=family, epithet="genus")
        sp = Species(genus=genus, epithet="sp")
        vn = VernacularName(name="name")
        sp.vernacular_names.append(vn)
        session.add_all([family, genus, sp, vn])
        if session.in_transaction():
            session.commit()

        # Step 2: Set the default vernacular name
        default = VernacularName(name="default")
        sp.default_vernacular_name = default
        if session.in_transaction():
            session.commit()

        # Verify default vernacular name and relationship to species
        assert vn in sp.vernacular_names
        assert sp.default_vernacular_name == default

        # Step 3: Test `setattr` works for setting default vernacular name
        default_vn = VernacularName(name="default_vn")
        sp.default_vernacular_name = default_vn
        if session.in_transaction():
            session.commit()

        # Verify the updated default vernacular name
        assert vn in sp.vernacular_names
        assert sp.default_vernacular_name == default_vn

        # Step 4: Verify automatic addition of `default_vernacular_name`
        new_default = VernacularName(name="new_default")
        sp.default_vernacular_name = new_default
        if session.in_transaction():
            session.commit()

        # Verify `new_default` is added and set correctly
        assert new_default in sp.vernacular_names
        assert sp.default_vernacular_name == new_default

        # Step 5: Remove a vernacular name and check cascading effects
        dvid = sp._default_vernacular_name.id
        sp.vernacular_names.remove(new_default)
        if session.in_transaction():
            session.commit()

        # Verify the default vernacular name is unset and removed
        assert sp.default_vernacular_name is None
        with pytest.raises(NoResultFound):
            session.execute(
                select(DefaultVernacularName).where(
                    DefaultVernacularName.species_id == sp.id
                )
            ).scalars().one()
        with pytest.raises(NoResultFound):
            session.execute(
                select(DefaultVernacularName).where(DefaultVernacularName.id == dvid)
            ).scalars().one()

        # Step 6: Reset `default_vernacular_name` and verify orphan handling
        sp.vernacular_names.append(vn)
        sp.default_vernacular_name = vn
        if session.in_transaction():
            session.commit()
        dvid = sp._default_vernacular_name.id
        sp.default_vernacular_name = None
        if session.in_transaction():
            session.commit()

        # Verify orphaned objects are properly removed
        with pytest.raises(NoResultFound):
            session.execute(
                select(DefaultVernacularName).where(
                    DefaultVernacularName.species_id == sp.id
                )
            ).scalars().one()
        with pytest.raises(NoResultFound):
            session.execute(
                select(DefaultVernacularName).where(DefaultVernacularName.id == dvid)
            ).scalars().one()

        # Step 7: Use `__del__` to delete `default_vernacular_name`
        sp.default_vernacular_name = vn
        if session.in_transaction():
            session.commit()
        dvid = sp._default_vernacular_name.id
        del sp.default_vernacular_name
        if session.in_transaction():
            session.commit()
        # Verify the default vernacular name is unset and deleted
        assert sp.default_vernacular_name is None
        with pytest.raises(NoResultFound):
            session.execute(
                select(DefaultVernacularName).where(
                    DefaultVernacularName.species_id == sp.id
                )
            ).scalars().one()
        with pytest.raises(NoResultFound):
            session.execute(
                select(DefaultVernacularName).where(DefaultVernacularName.id == dvid)
            ).scalars().one()

        # Step 8: Test for regression in Launchpad Bug #123286
        vn1 = VernacularName(name="vn1")
        vn2 = VernacularName(name="vn2")
        sp.default_vernacular_name = vn1
        sp.default_vernacular_name = vn2
        if session.in_transaction():
            session.commit()

        # Verify the final default vernacular name
        assert sp.default_vernacular_name == vn2
        assert vn1 in sp.vernacular_names
        assert vn2 in sp.vernacular_names

    def test_synonyms_low_level(self):
        """
        Test the Species.synonyms property
        """

        def load_sp(id):
            return self.session.get(Species, id)

        def syn_str(id1, id2, isit="not"):
            sp1 = load_sp(id1)
            load_sp(id2)
            return "{}({}).synonyms: {}".format(
                sp1,
                sp1.id,
                str([f"{s}({s.id})" for s in sp1.synonyms]),
            )

        def synonym_of(id1, id2):
            sp1 = load_sp(id1)
            sp2 = load_sp(id2)
            return sp2 in sp1.synonyms

        # test that appending a synonym works using species.synonyms
        sp1 = load_sp(1)
        sp2 = load_sp(2)
        sp1.synonyms.append(sp2)
        self.session.flush()
        self.assertTrue(synonym_of(1, 2), syn_str(1, 2))

        # test that removing a synonyms works using species.synonyms
        sp1.synonyms.remove(sp2)
        self.session.flush()
        self.assertFalse(synonym_of(1, 2), syn_str(1, 2))

        self.session.expunge_all()

        # test that appending a synonym works using species._synonyms
        sp1 = load_sp(1)
        sp2 = load_sp(2)
        syn = SpeciesSynonym(sp2)
        sp1._synonyms.append(syn)
        self.session.flush()
        self.assertTrue(synonym_of(1, 2), syn_str(1, 2))

        # test that removing a synonyms works using species._synonyms
        sp1._synonyms.remove(syn)
        self.session.flush()
        self.assertFalse(synonym_of(1, 2), syn_str(1, 2))

        # test adding a species and then immediately remove it
        self.session.expunge_all()
        sp1 = load_sp(1)
        sp2 = load_sp(2)
        sp1.synonyms.append(sp2)
        sp1.synonyms.remove(sp2)
        # self.session.flush()
        if self.session.in_transaction():
            self.session.commit()
        assert sp2 not in sp1.synonyms

        # add a species and immediately add the same species
        sp2 = load_sp(2)
        sp1.synonyms.append(sp2)
        sp1.synonyms.remove(sp2)
        sp1.synonyms.append(sp2)
        # self.session.flush() # shouldn't raise an error
        if self.session.in_transaction():
            self.session.commit()
        assert sp2 in sp1.synonyms

        # test that deleting a species removes it from the synonyms list
        assert sp2 in sp1.synonyms
        self.session.delete(sp2)
        if self.session.in_transaction():
            self.session.commit()
        assert sp2 not in sp1.synonyms

        self.session.expunge_all()

    def test_no_synonyms_means_itself_accepted(self):
        def create_tmp_sp(id):
            sp = Species(id=id, epithet="sp%02d" % id, genus_id=1)
            self.session.add(sp)
            return sp

        sp1 = create_tmp_sp(51)
        sp2 = create_tmp_sp(52)
        sp3 = create_tmp_sp(53)
        sp4 = create_tmp_sp(54)
        if self.session.in_transaction():
            self.session.commit()
        self.assertEqual(sp1.accepted, None)
        self.assertEqual(sp2.accepted, None)
        self.assertEqual(sp3.accepted, None)
        self.assertEqual(sp4.accepted, None)

    def test_synonyms_and_accepted_properties(self):
        def create_tmp_sp(id):
            sp = Species(id=id, epithet="sp%02d" % id, genus_id=1)
            self.session.add(sp)
            return sp

        # equivalence classes after changes
        sp1 = create_tmp_sp(41)
        sp2 = create_tmp_sp(42)
        sp3 = create_tmp_sp(43)
        sp4 = create_tmp_sp(44)  # (1), (2), (3), (4)
        sp3.accepted = sp1  # (1 3), (2), (4)
        self.assertEqual([i.epithet for i in sp1.synonyms], [sp3.epithet])
        sp1.synonyms.append(sp2)  # (1 3 2), (4)
        self.session.flush()
        print(("synonyms of 1", [i.epithet[-1] for i in sp1.synonyms]))
        print(("synonyms of 4", [i.epithet[-1] for i in sp4.synonyms]))
        self.assertEqual(sp2.accepted.epithet, sp1.epithet)  # just added
        self.assertEqual(sp3.accepted.epithet, sp1.epithet)  # no change
        sp2.accepted = sp4  # (1 3), (4 2)
        self.session.flush()
        print(("synonyms of 1", [i.epithet[-1] for i in sp1.synonyms]))
        print(("synonyms of 4", [i.epithet[-1] for i in sp4.synonyms]))
        self.assertEqual([i.epithet for i in sp4.synonyms], [sp2.epithet])
        self.assertEqual([i.epithet for i in sp1.synonyms], [sp3.epithet])
        self.assertEqual(sp1.accepted, None)
        self.assertEqual(sp2.accepted, sp4)
        self.assertEqual(sp3.accepted, sp1)
        self.assertEqual(sp4.accepted, None)
        sp2.accepted = sp4  # does not change anything
        self.assertEqual(sp1.accepted, None)
        self.assertEqual(sp2.accepted, sp4)
        self.assertEqual(sp3.accepted, sp1)
        self.assertEqual(sp4.accepted, None)

    def test_remove_callback_no_accessions_no_confirm(self) -> None:
        # T_0
        caricaceae = Family(epithet="Caricaceae")
        f5 = Genus(epithet="Carica", family=caricaceae)
        sp = Species(epithet="papaya", genus=f5)
        self.session.add_all([caricaceae, f5, sp])
        self.session.flush()
        self.invoked = []

        # action
        utils.yes_no_dialog = partial(
            mockfunc, name="yes_no_dialog", caller=self, result=False
        )
        utils.message_details_dialog = partial(
            mockfunc, name="message_details_dialog", caller=self
        )
        from bauble.plugins.plants.species import remove_callback

        result = remove_callback([sp])
        self.session.flush()

        # effect
        self.assertFalse("message_details_dialog" in [f for (f, m) in self.invoked])
        print(self.invoked)
        self.assertTrue(
            (
                "yes_no_dialog",
                "Are you sure you want to remove the species <i>Carica \u200bpapaya</i>?",
            )
            in self.invoked
        )
        self.assertEqual(result, None)
        q = self.session.execute(select(Species).where(genus=f5, sp="papaya")).scalars()
        matching = q.all()
        self.assertEqual(matching, [sp])

    def test_remove_callback_no_accessions_confirm(self) -> None:
        # T_0
        caricaceae = Family(epithet="Caricaceae")
        f5 = Genus(epithet="Carica", family=caricaceae)
        sp = Species(epithet="papaya", genus=f5)
        self.session.add_all([caricaceae, f5, sp])
        self.session.flush()
        self.invoked = []

        # action
        utils.yes_no_dialog = partial(
            mockfunc, name="yes_no_dialog", caller=self, result=True
        )
        utils.message_details_dialog = partial(
            mockfunc, name="message_details_dialog", caller=self
        )
        from bauble.plugins.plants.species import remove_callback

        result = remove_callback([sp])
        self.session.flush()

        # effect
        print(self.invoked)
        self.assertFalse("message_details_dialog" in [f for (f, m) in self.invoked])
        self.assertTrue(
            (
                "yes_no_dialog",
                "Are you sure you want to remove the species <i>Carica \u200bpapaya</i>?",
            )
            in self.invoked
        )

        self.assertEqual(result, True)
        q = self.session.execute(select(Species).where(sp="Carica")).scalars()
        matching = q.all()
        self.assertEqual(matching, [])

    def test_remove_callback_with_accessions_cant_cascade(self) -> None:
        # T_0
        caricaceae = Family(epithet="Caricaceae")
        f5 = Genus(epithet="Carica", family=caricaceae)
        sp = Species(epithet="papaya", genus=f5)
        from bauble.plugins.garden.models import Accession

        acc = Accession(code="0123456", species=sp)
        self.session.add_all([caricaceae, f5, sp, acc])
        self.session.flush()
        self.invoked = []

        # action
        utils.yes_no_dialog = partial(
            mockfunc, name="yes_no_dialog", caller=self, result=True
        )
        utils.message_dialog = partial(
            mockfunc, name="message_dialog", caller=self, result=True
        )
        utils.message_details_dialog = partial(
            mockfunc, name="message_details_dialog", caller=self
        )
        from bauble.plugins.plants.species import remove_callback

        remove_callback([sp])
        self.session.flush()

        # effect
        print(self.invoked)
        self.assertFalse("message_details_dialog" in [f for (f, m) in self.invoked])
        self.assertTrue(
            (
                "message_dialog",
                "The species <i>Carica \u200bpapaya</i> has 1 accessions.\n\nYou cannot remove a species with accessions.",
            )
            in self.invoked
        )
        q = self.session.execute(select(Species).where(genus=f5, sp="papaya")).scalars()
        matching = q.all()
        self.assertEqual(matching, [sp])
        q = self.session.execute(select(Accession).where(species=sp)).scalars()
        matching = q.all()
        self.assertEqual(matching, [acc])



@pytest.mark.usefixtures("setup_plant_data")
class TestGeographicArea:
    """Tests for Geographic Area functionality."""

    session: Any
    family: Any
    genus: Any

    @pytest.fixture(autouse=True)
    def setup_class(self, session) -> None:
        """Setup for each test."""
        self.session = session
        self.family = Family(epithet="family")
        self.genus = Genus(epithet="genus", family=self.family)
        session.add_all([self.family, self.genus])
        session.flush()

        # Import default geographic area data
        with patch("bauble.paths.lib_dir", return_value="/mock/path/to/lib"):
            filename = "/mock/path/to/lib/plugins/plants/default/geographic_area.txt"
            importer = CSVImporter()
            importer.start([filename], force=True)
        if session.in_transaction():
            session.commit()

    def test_get_species(self) -> None:
        """Test fetching species by geographic area."""
        mexico_id = 53
        mexico_central_id = 267
        oaxaca_id = 665
        northern_america_id = 7
        western_canada_id = 45

        # Create species with distributions
        sp1 = Species(genus=self.genus, epithet="sp1")
        sp1.distribution.append(
            SpeciesDistribution(geographic_area_id=mexico_central_id)
        )

        sp2 = Species(genus=self.genus, epithet="sp2")
        sp2.distribution.append(SpeciesDistribution(geographic_area_id=oaxaca_id))

        sp3 = Species(genus=self.genus, epithet="sp3")
        sp3.distribution.append(
            SpeciesDistribution(geographic_area_id=western_canada_id)
        )

        if self.session.in_transaction():
            self.session.commit()

        # Test Oaxaca
        oaxaca = self.session.get(GeographicArea, oaxaca_id)
        species = get_species_in_geographic_area(oaxaca)
        assert [s.id for s in species] == [sp2.id], "Oaxaca species mismatch"

        # Test Mexico
        mexico = self.session.get(GeographicArea, mexico_id)
        species = get_species_in_geographic_area(mexico)
        assert [s.id for s in species] == [sp1.id, sp2.id], "Mexico species mismatch"

        # Test North America
        north_america = self.session.get(GeographicArea, northern_america_id)
        species = get_species_in_geographic_area(north_america)
        assert [s.id for s in species] == [
            sp1.id,
            sp2.id,
            sp3.id,
        ], "North America species mismatch"

    def test_species_distribution_str(self) -> None:
        """Test the string representation of species distribution."""
        sp1 = Species(genus=self.genus, epithet="sp1")
        dist_1 = SpeciesDistribution(geographic_area_id=267)  # Mexico Central
        sp1.distribution.append(dist_1)
        self.session.flush()
        assert (
            sp1.distribution_str() == "Mexico Central"
        ), "Distribution string mismatch for one area"

        dist_2 = SpeciesDistribution(geographic_area_id=45)  # Western Canada
        sp1.distribution.append(dist_2)
        self.session.flush()
        assert (
            sp1.distribution_str() == "Mexico Central, Western Canada"
        ), "Distribution string mismatch for multiple areas"


import pytest


@pytest.mark.usefixtures("setup_plant_data")
class TestFromAndToDict:
    """Tests for retrieve_or_create and as_dict methods."""

    def test_can_grab_existing_families(self, session) -> None:
        """Test retrieving existing families."""
        all_families = session.execute(select(Family)).scalars().all()
        orc = Family.retrieve_or_create(
            session, {"rank": "family", "epithet": "Orchidaceae"}
        )
        leg = Family.retrieve_or_create(
            session, {"rank": "family", "epithet": "Leguminosae"}
        )
        pol = Family.retrieve_or_create(
            session, {"rank": "family", "epithet": "Polypodiaceae"}
        )
        sol = Family.retrieve_or_create(
            session, {"rank": "family", "epithet": "Solanaceae"}
        )
        assert set(all_families) == {
            orc,
            pol,
            leg,
            sol,
        }, "Mismatch in retrieved families."

    def test_grabbing_same_params_same_output_existing(self, session) -> None:
        """Test that retrieving the same family parameters returns the same object."""
        orc1 = Family.retrieve_or_create(
            session, {"rank": "family", "epithet": "Orchidaceae"}
        )
        orc2 = Family.retrieve_or_create(
            session, {"rank": "family", "epithet": "Orchidaceae"}
        )
        assert orc1 is orc2, "Different objects returned for identical parameters."

    def test_can_create_family(self, session) -> None:
        """Test creating a new family."""
        all_families = session.execute(select(Family)).scalars().all()
        fab = Family.retrieve_or_create(
            session, {"rank": "family", "epithet": "Fabaceae"}
        )
        assert fab in session, "Family not in session after creation."
        assert fab not in all_families, "Family unexpectedly in initial families list."
        session_families = session.execute(select(Family)).scalars().all()
        assert fab in session_families, "Family not found in session after creation."

    @pytest.mark.skip(reason="Not Implemented")
    def test_where_can_object_be_found_before_commit(self, db_session) -> None:
        """Test visibility of created objects in other sessions before commit."""
        fab = Family.retrieve_or_create(
            db_session, {"rank": "family", "epithet": "Fabaceae"}
        )

        # Use a new session bound to same connection with SAVEPOINT
        nested_transaction = db_session.connection().begin_nested()
        other_session = db.Session(bind=db_session.connection())
        try:
            db_families = other_session.execute(select(Family)).scalars().all()
            Family.retrieve_or_create(
                other_session, {"rank": "family", "epithet": "Fabaceae"}
            )
            assert fab not in db_families, "Family unexpectedly found in other session."
        finally:
            if nested_transaction.in_transaction():
                nested_transaction.rollback()
            other_session.close()

    def test_where_can_object_be_found_after_commit(self, db_session) -> None:
        """Test visibility of created objects in other sessions after commit."""
        fab = Family.retrieve_or_create(
            db_session, {"rank": "family", "epithet": "Fabaceae"}
        )
        if db_session.in_transaction():
            db_session.commit()

        other_session = db.Session(bind=db.engine.connect())
        try:
            all_families = other_session.execute(select(Family)).scalars().all()
            Family.retrieve_or_create(
                other_session, {"rank": "family", "epithet": "Fabaceae"}
            )
            assert (
                fab in all_families
            ), "Family not found in other session after commit."
        finally:
            other_session.close()

    def test_grabbing_same_params_same_output_new(self, session) -> None:
        """Test that retrieving the same parameters returns the same new object."""
        fab1 = Family.retrieve_or_create(
            session, {"rank": "family", "epithet": "Fabaceae"}
        )
        fab2 = Family.retrieve_or_create(
            session, {"rank": "family", "epithet": "Fabaceae"}
        )
        assert fab1 is fab2, "Different objects returned for identical parameters."

    def test_can_grab_existing_genera(self, session) -> None:
        """Test retrieving existing genera under a specific family."""
        orc = Family.retrieve_or_create(
            session, {"rank": "family", "epithet": "Orchidaceae"}
        )
        all_genera_orc = (
            session.execute(select(Genus).where(Genus.family == orc)).scalars().all()
        )
        mxl = Genus.retrieve_or_create(
            session,
            {
                "ht-rank": "family",
                "ht-epithet": "Orchidaceae",
                "rank": "genus",
                "epithet": "Maxillaria",
            },
        )
        enc = Genus.retrieve_or_create(
            session,
            {
                "ht-rank": "family",
                "ht-epithet": "Orchidaceae",
                "rank": "genus",
                "epithet": "Encyclia",
            },
        )
        assert mxl in set(all_genera_orc), "Maxillaria not found in retrieved genera."
        assert enc in set(all_genera_orc), "Encyclia not found in retrieved genera."


import pytest
from bauble.plugins.plants.vernacular_name import VernacularName


def get_first_or_none(session, stmt):
    return session.execute(stmt).scalars().first()


@pytest.mark.usefixtures("setup_plant_data")
class TestFromAndToDictCreateUpdate:
    """Test the create and update fields in retrieve_or_create."""

    def test_family_nocreate_noupdate_noexisting(self, session) -> None:
        """Do not create a Family if it doesn't exist."""
        obj = Family.retrieve_or_create(
            session,
            {"object": "taxon", "rank": "familia", "epithet": "Arecaceae"},
            create=False,
        )
        assert obj is None

    def test_family_nocreate_noupdateeq_existing(self, session) -> None:
        """Retrieve the same Family object without creating or updating."""
        obj = Family.retrieve_or_create(
            session,
            {"object": "taxon", "rank": "familia", "epithet": "Leguminosae"},
            create=False,
            update=False,
        )
        assert obj is not None
        assert obj.qualifier == "s. str."

    def test_family_nocreate_noupdatediff_existing(self, session) -> None:
        """Do not update a Family object when create and update are disabled."""
        obj = Family.retrieve_or_create(
            session,
            {
                "object": "taxon",
                "rank": "familia",
                "epithet": "Leguminosae",
                "qualifier": "s. lat.",
            },
            create=False,
            update=False,
        )
        assert obj.qualifier == "s. str."

    def test_family_nocreate_updatediff_existing(self, session) -> None:
        """Update a Family object when update is enabled."""
        obj = Family.retrieve_or_create(
            session,
            {
                "object": "taxon",
                "rank": "familia",
                "epithet": "Leguminosae",
                "qualifier": "s. lat.",
            },
            create=False,
            update=True,
        )
        assert obj.qualifier == "s. lat."

    def test_genus_nocreate_noupdate_noexisting_impossible(self, session) -> None:
        """Do not create a Genus if it doesn't exist and is missing required data."""
        obj = Genus.retrieve_or_create(
            session,
            {"object": "taxon", "rank": "genus", "epithet": "Masdevallia"},
            create=False,
        )
        assert obj is None

    def test_genus_create_noupdate_noexisting_impossible(self, session) -> None:
        """Do not create a Genus if required data is missing."""
        obj = Genus.retrieve_or_create(
            session,
            {"object": "taxon", "rank": "genus", "epithet": "Masdevallia"},
            create=True,
        )
        assert obj is None

    def test_genus_nocreate_noupdate_noexisting_possible(self, session) -> None:
        """Do not create a Genus if it doesn't exist."""
        obj = Genus.retrieve_or_create(
            session,
            {
                "object": "taxon",
                "rank": "genus",
                "epithet": "Masdevallia",
                "ht-rank": "familia",
                "ht-epithet": "Orchidaceae",
            },
            create=False,
        )
        assert obj is None

    def test_genus_nocreate_noupdateeq_existing(self, session) -> None:
        """Retrieve the same Genus object without creating or updating."""
        obj = Genus.retrieve_or_create(
            session,
            {"object": "taxon", "rank": "genus", "epithet": "Maxillaria"},
            create=False,
            update=False,
        )
        assert obj is not None
        assert obj.author == ""

    def test_genus_nocreate_noupdatediff_existing(self, session) -> None:
        """Do not update a Genus object when create and update are disabled."""
        obj = Genus.retrieve_or_create(
            session,
            {
                "object": "taxon",
                "rank": "genus",
                "epithet": "Maxillaria",
                "author": "Schltr.",
            },
            create=False,
            update=False,
        )
        assert obj is not None
        assert obj.author == ""

    def test_genus_nocreate_updatediff_existing(self, session) -> None:
        """Update a Genus object when update is enabled."""
        obj = Genus.retrieve_or_create(
            session,
            {
                "object": "taxon",
                "rank": "genus",
                "epithet": "Maxillaria",
                "author": "Schltr.",
            },
            create=False,
            update=True,
        )
        assert obj is not None
        assert obj.author == "Schltr."

    def test_vernacular_name_as_dict(self, session) -> None:
        """Ensure VernacularName objects can be serialized to dictionaries."""
        bra = get_first_or_none(session, select(Species).where(Species.id == 21))
        assert bra is not None
        vn_bra = (
            session.execute(
                select(VernacularName).where(
                    VernacularName.language == "agr", VernacularName.species == bra
                )
            )
            .scalars()
            .all()
        )
        assert vn_bra[0].as_dict() == {
            "object": "vernacular_name",
            "name": "Toé",
            "language": "agr",
            "species": "Brugmansia arborea",
        }

        vn_bra = (
            session.execute(
                select(VernacularName).where(
                    VernacularName.language == "es", VernacularName.species == bra
                )
            )
            .scalars()
            .all()
        )
        assert vn_bra[0].as_dict() == {
            "object": "vernacular_name",
            "name": "Floripondio",
            "language": "es",
            "species": "Brugmansia arborea",
        }

    def test_vernacular_name_nocreate_noupdate_noexisting(self, session) -> None:
        """Do not create a VernacularName if it doesn't exist."""
        obj = VernacularName.retrieve_or_create(
            session,
            {
                "object": "vernacular_name",
                "language": "nap",
                "species": "Brugmansia arborea",
            },
            create=False,
        )
        assert obj is None

    def test_vernacular_name_nocreate_noupdateeq_existing(self, session) -> None:
        """Retrieve the same VernacularName object without creating or updating."""
        obj = VernacularName.retrieve_or_create(
            session,
            {
                "object": "vernacular_name",
                "language": "agr",
                "species": "Brugmansia arborea",
            },
            create=False,
            update=False,
        )
        assert obj is not None
        assert obj.name == "Toé"

    def test_vernacular_name_nocreate_noupdatediff_existing(self, session) -> None:
        """Do not update a VernacularName object when create and update are disabled."""
        obj = VernacularName.retrieve_or_create(
            session,
            {
                "object": "vernacular_name",
                "language": "agr",
                "name": "wrong",
                "species": "Brugmansia arborea",
            },
            create=False,
            update=False,
        )
        assert obj.name == "Toé"

    def test_vernacular_name_nocreate_updatediff_existing(self, session) -> None:
        """Update a VernacularName object when update is enabled."""
        obj = VernacularName.retrieve_or_create(
            session,
            {
                "object": "vernacular_name",
                "language": "agr",
                "name": "wrong",
                "species": "Brugmansia arborea",
            },
            create=False,
            update=True,
        )
        assert obj.name == "wrong"


import pytest


@pytest.mark.usefixtures("setup_plant_data")
class TestCitesStatus:
    """Tests for retrieving CITES status as defined in family-genus-species."""

    def test_cites_status(self, session) -> None:
        gen = Genus.retrieve_or_create(
            session,
            {"object": "taxon", "rank": "genus", "epithet": "Maxillaria"},
            create=False,
            update=False,
        )
        assert gen.cites == "II"

        gen = Genus.retrieve_or_create(
            session,
            {"object": "taxon", "rank": "genus", "epithet": "Laelia"},
            create=False,
            update=False,
        )
        assert gen.cites == "II"

        sp = Species.retrieve_or_create(
            session,
            {
                "object": "taxon",
                "ht-rank": "genus",
                "ht-epithet": "Paphiopedilum",
                "rank": "species",
                "epithet": "adductum",
            },
            create=False,
            update=False,
        )
        assert sp.cites == "I"

        sp = Species.retrieve_or_create(
            session,
            {
                "object": "taxon",
                "ht-rank": "genus",
                "ht-epithet": "Laelia",
                "rank": "species",
                "epithet": "lobata",
            },
            create=False,
            update=False,
        )
        assert sp.cites == "I"

        sp = Species.retrieve_or_create(
            session,
            {
                "object": "taxon",
                "ht-rank": "genus",
                "ht-epithet": "Laelia",
                "rank": "species",
                "epithet": "grandiflora",
            },
            create=False,
            update=False,
        )
        assert sp.cites == "II"


@pytest.mark.usefixtures("setup_plant_data")
class TestGenusHybridMarker:
    """Tests for identifying hybrid markers in Genus."""

    def test_intergeneric_hybrid_not_hybrid(self, session) -> None:
        gen = Genus.retrieve_or_create(
            session,
            {
                "ht-rank": "family",
                "ht-epithet": "Orchidaceae",
                "rank": "genus",
                "epithet": "Cattleya",
            },
        )
        assert gen.hybrid_marker == ""
        assert gen.hybrid_epithet == "Cattleya"

    def test_intergeneric_hybrid_mult(self, session) -> None:
        gen = Genus.retrieve_or_create(
            session,
            {
                "ht-rank": "family",
                "ht-epithet": "Orchidaceae",
                "rank": "genus",
                "epithet": "×Brassocattleya",
            },
        )
        assert gen.hybrid_marker == "×"
        assert gen.hybrid_epithet == "Brassocattleya"

    def test_intergeneric_hybrid_x_becomes_mult(self, session) -> None:
        gen = Genus.retrieve_or_create(
            session,
            {
                "ht-rank": "family",
                "ht-epithet": "Orchidaceae",
                "rank": "genus",
                "epithet": "xVascostylis",
            },
        )
        assert gen.hybrid_marker == "×"
        assert gen.hybrid_epithet == "Vascostylis"

    def test_hybrid_formula_h(self, session) -> None:
        gen = Genus.retrieve_or_create(
            session,
            {
                "ht-rank": "family",
                "ht-epithet": "Orchidaceae",
                "rank": "genus",
                "epithet": "Miltonia × Odontoglossum × Cochlioda",
            },
        )
        assert gen.hybrid_marker == "H"
        assert gen.hybrid_epithet == "Miltonia × Odontoglossum × Cochlioda"

    def test_intergeneric_graft_hybrid_plus(self, session) -> None:
        gen = Genus.retrieve_or_create(
            session,
            {
                "ht-rank": "family",
                "ht-epithet": "Rosaceae",
                "rank": "genus",
                "epithet": "+Crataegomespilus",
            },
        )
        assert gen.hybrid_marker == "+"
        assert gen.hybrid_epithet == "Crataegomespilus"


import pytest


@pytest.mark.usefixtures("setup_plant_data")
class TestSpeciesInfraspecificProp:
    """Tests for infraspecific properties and cultivar epithet in Species."""

    cinnamomum: Any
    cinnamomum_camphora: Any
    gleditsia: Any
    gleditsia_triacanthos: Any

    def test_cultivar_epithet_1(self, session) -> None:
        obj = Species.retrieve_or_create(
            session,
            {
                "object": "taxon",
                "ht-rank": "genus",
                "ht-epithet": "Paphiopedilum",
                "rank": "species",
                "epithet": "",
            },
        )
        obj.infrasp1 = "Eva Weigner"
        obj.infrasp1_rank = "cv."
        assert obj.cultivar_epithet == "Eva Weigner"

    def test_cultivar_epithet_2(self, session) -> None:
        obj = Species.retrieve_or_create(
            session,
            {
                "object": "taxon",
                "ht-rank": "genus",
                "ht-epithet": "Paphiopedilum",
                "rank": "species",
                "epithet": "",
            },
        )
        obj.infrasp2 = "Eva Weigner"
        obj.infrasp2_rank = "cv."
        assert obj.cultivar_epithet == "Eva Weigner"

    def test_infraspecific_1(self, session) -> None:
        self._include_cinnamomum_camphora(session)
        obj = Species(
            genus=self.cinnamomum,
            sp="camphora",
            infrasp1_rank="f.",
            infrasp1="linaloolifera",
            infrasp1_author="(Y.Fujita) Sugim.",
        )
        assert obj.infraspecific_rank == "f."
        assert obj.infraspecific_epithet == "linaloolifera"
        assert obj.infraspecific_author == "(Y.Fujita) Sugim."

    def test_infraspecific_2(self, session) -> None:
        self._include_cinnamomum_camphora(session)
        obj = Species(
            genus=self.cinnamomum,
            sp="camphora",
            infrasp2_rank="f.",
            infrasp2="linaloolifera",
            infrasp2_author="(Y.Fujita) Sugim.",
        )
        assert obj.infraspecific_rank == "f."
        assert obj.infraspecific_epithet == "linaloolifera"
        assert obj.infraspecific_author == "(Y.Fujita) Sugim."

    def test_variety_and_cultivar_1(self, session) -> None:
        self._include_gleditsia_triacanthos(session)
        obj = Species(
            genus=self.gleditsia,
            sp="triacanthos",
            infrasp1_rank="var.",
            infrasp1="inermis",
            infrasp2="Sunburst",
            infrasp2_rank="cv.",
        )
        assert obj.infraspecific_rank == "var."
        assert obj.infraspecific_epithet == "inermis"
        assert obj.infraspecific_author == ""
        assert obj.cultivar_epithet == "Sunburst"

    def test_variety_and_cultivar_2(self, session) -> None:
        self._include_gleditsia_triacanthos(session)
        obj = Species(
            genus=self.gleditsia,
            sp="triacanthos",
            infrasp2_rank="var.",
            infrasp2="inermis",
            infrasp1="Sunburst",
            infrasp1_rank="cv.",
        )
        assert obj.infraspecific_rank == "var."
        assert obj.infraspecific_epithet == "inermis"
        assert obj.infraspecific_author == ""
        assert obj.cultivar_epithet == "Sunburst"

    def test_infraspecific_props_is_lowest_ranked(self, session) -> None:
        Family.retrieve_or_create(
            session,
            {"object": "taxon", "rank": "family", "epithet": "Saxifragaceae"},
        )
        genus = Genus.retrieve_or_create(
            session,
            {
                "object": "taxon",
                "ht-rank": "family",
                "ht-epithet": "Saxifragaceae",
                "rank": "genus",
                "epithet": "Saxifraga",
            },
        )
        subvar = Species(
            genus=genus,
            sp="aizoon",
            infrasp1_rank="var.",
            infrasp1="aizoon",
            infrasp2_rank="subvar.",
            infrasp2="brevifolia",
        )
        subf = Species(
            genus=genus,
            sp="aizoon",
            infrasp2_rank="var.",
            infrasp2="aizoon",
            infrasp1_rank="subvar.",
            infrasp1="brevifolia",
            infrasp3_rank="f.",
            infrasp3="multicaulis",
            infrasp4_rank="subf.",
            infrasp4="surculosa",
        )
        assert subvar.infraspecific_rank == "subvar."
        assert subvar.infraspecific_epithet == "brevifolia"
        assert subvar.infraspecific_author == ""
        assert subvar.cultivar_epithet == ""
        assert subf.infraspecific_rank == "subf."
        assert subf.infraspecific_epithet == "surculosa"
        assert subf.infraspecific_author == ""
        assert subf.cultivar_epithet == ""

        cv = Species(
            genus=genus,
            sp="aizoon",
            infrasp4_rank="var.",
            infrasp4="aizoon",
            infrasp1_rank="subvar.",
            infrasp1="brevifolia",
            infrasp3_rank="f.",
            infrasp3="multicaulis",
            infrasp2_rank="cv.",
            infrasp2="Bellissima",
        )
        assert cv.infraspecific_rank == "f."
        assert cv.infraspecific_epithet == "multicaulis"
        assert cv.infraspecific_author == ""
        assert cv.cultivar_epithet == "Bellissima"

    def _include_cinnamomum_camphora(self, session) -> None:
        Family.retrieve_or_create(
            session,
            {"object": "taxon", "rank": "family", "epithet": "Lauraceae"},
        )
        self.cinnamomum = Genus.retrieve_or_create(
            session,
            {
                "object": "taxon",
                "ht-rank": "family",
                "ht-epithet": "Lauraceae",
                "rank": "genus",
                "epithet": "Cinnamomum",
            },
        )
        self.cinnamomum_camphora = Species.retrieve_or_create(
            session,
            {
                "object": "taxon",
                "ht-rank": "genus",
                "ht-epithet": "Cinnamomum",
                "rank": "species",
                "epithet": "camphora",
            },
        )

    def _include_gleditsia_triacanthos(self, session) -> None:
        Family.retrieve_or_create(
            session,
            {"object": "taxon", "rank": "family", "epithet": "Fabaceae"},
        )
        self.gleditsia = Genus.retrieve_or_create(
            session,
            {
                "object": "taxon",
                "ht-rank": "family",
                "ht-epithet": "Fabaceae",
                "rank": "genus",
                "epithet": "Gleditsia",
            },
        )
        self.gleditsia_triacanthos = Species.retrieve_or_create(
            session,
            {
                "object": "taxon",
                "ht-rank": "genus",
                "ht-epithet": "Gleditsia",
                "rank": "species",
                "epithet": "triacanthos",
            },
        )


@pytest.mark.usefixtures("setup_plant_data")
class TestSpeciesProperties:
    """Test retrieval of species_note objects given species and category."""

    def test_species_note_nocreate_noupdate_noexisting(self, session) -> None:
        obj = SpeciesNote.retrieve_or_create(
            session,
            {
                "object": "species_note",
                "category": "IUCN",
                "species": "Laelia grandiflora",
            },
            create=False,
        )
        assert obj is None

    def test_species_note_nocreate_noupdateeq_existing(self, session) -> None:
        obj = SpeciesNote.retrieve_or_create(
            session,
            {
                "object": "species_note",
                "category": "IUCN",
                "species": "Encyclia fragrans",
            },
            create=False,
            update=False,
        )
        assert obj is not None
        assert obj.note == "LC"

    def test_species_note_nocreate_noupdatediff_existing(self, session) -> None:
        obj = SpeciesNote.retrieve_or_create(
            session,
            {
                "object": "species_note",
                "category": "IUCN",
                "species": "Encyclia fragrans",
                "note": "EX",
            },
            create=False,
            update=False,
        )
        assert obj.note == "LC"

    def test_species_note_nocreate_updatediff_existing(self, session) -> None:
        obj = SpeciesNote.retrieve_or_create(
            session,
            {
                "object": "species_note",
                "category": "IUCN",
                "species": "Encyclia fragrans",
                "note": "EX",
            },
            create=False,
            update=True,
        )
        assert obj.note == "EX"


@pytest.mark.usefixtures("setup_plant_data")
class TestAttributesStoredInNotes:
    """Test parsing and retrieval of notes as attributes."""

    def test_proper_yaml_dictionary(self, session) -> None:
        obj = Species.retrieve_or_create(
            session,
            {
                "object": "taxon",
                "ht-rank": "genus",
                "rank": "species",
                "ht-epithet": "Laelia",
                "epithet": "lobata",
            },
            create=False,
            update=False,
        )
        note = SpeciesNote(category="<coords>", note="{1: 1, 2: 2}")
        note.species = obj
        if session.in_transaction():
            session.commit()
        assert obj.coords == {"1": 1, "2": 2}

    def test_very_sloppy_json_dictionary(self, session) -> None:
        obj = Species.retrieve_or_create(
            session,
            {
                "object": "taxon",
                "ht-rank": "genus",
                "rank": "species",
                "ht-epithet": "Laelia",
                "epithet": "lobata",
            },
            create=False,
            update=False,
        )
        note = SpeciesNote(category="<coords>", note="lat:8.3,lon:-80.1")
        note.species = obj
        if session.in_transaction():
            session.commit()
        assert obj.coords == {"lat": 8.3, "lon": -80.1}

    def test_atomic_value_interpreted(self, session) -> None:
        obj = Species.retrieve_or_create(
            session,
            {
                "object": "taxon",
                "ht-rank": "genus",
                "rank": "species",
                "ht-epithet": "Laelia",
                "epithet": "lobata",
            },
            create=False,
            update=False,
        )
        assert obj.price == 19.50

    def test_atomic_value_verbatim(self, session) -> None:
        obj = Species.retrieve_or_create(
            session,
            {
                "object": "taxon",
                "ht-rank": "genus",
                "rank": "species",
                "ht-epithet": "Laelia",
                "epithet": "lobata",
            },
            create=False,
            update=False,
        )
        assert obj.price_tag == "$19.50"

    def test_list_value(self, session) -> None:
        obj = Species.retrieve_or_create(
            session,
            {
                "object": "taxon",
                "ht-rank": "genus",
                "rank": "species",
                "ht-epithet": "Laelia",
                "epithet": "lobata",
            },
            create=False,
            update=False,
        )
        assert obj.list_var == ["abc", "def"]

    def test_dict_value(self, session) -> None:
        obj = Species.retrieve_or_create(
            session,
            {
                "object": "taxon",
                "ht-rank": "genus",
                "rank": "species",
                "ht-epithet": "Laelia",
                "epithet": "lobata",
            },
            create=False,
            update=False,
        )
        assert obj.dict_var == {"k": "abc", "l": "def", "m": "xyz"}


@pytest.mark.usefixtures("setup_plant_data")
class TestConservationStatus:
    """Test retrieval of IUCN conservation status."""

    def test(self, session) -> None:
        obj = Species.retrieve_or_create(
            session,
            {
                "object": "taxon",
                "ht-rank": "genus",
                "ht-epithet": "Encyclia",
                "rank": "species",
                "epithet": "fragrans",
            },
            create=False,
            update=False,
        )
        assert obj.conservation == "LC"


@pytest.mark.usefixtures("setup_plant_data")
class TestPresenter:
    def test_can_reedit_object(self, session) -> None:
        species = Species.retrieve_or_create(
            session,
            {
                "object": "taxon",
                "ht-rank": "genus",
                "ht-epithet": "Paphiopedilum",
                "rank": "species",
                "epithet": "adductum",
            },
            create=False,
            update=False,
        )
        presenter = GenericModelViewPresenterEditor(species, MockView())
        species.author = "wrong"
        presenter.commit_changes()
        species.author = "Asher"
        presenter.commit_changes()
        assert species.author == "Asher"

    @pytest.mark.skip(reason="Not Implemented: Presenter uses view internals")
    def test_cant_insert_same_twice(self, session) -> None:
        model = Species.retrieve_or_create(
            session,
            {
                "object": "taxon",
                "ht-rank": "genus",
                "ht-epithet": "Laelia",
                "rank": "species",
                "epithet": "lobata",
            },
            create=False,
            update=False,
        )
        presenter = SpeciesEditorPresenter(model, MockView())
        presenter.on_text_entry_changed("sp_species_entry", "grandiflora")

    @pytest.mark.skip(reason="Not Implemented: Presenter uses view internals")
    def test_cant_insert_same_twice_warn_once(self, session) -> None:
        # Implementation skipped
        pass


@pytest.mark.usefixtures("setup_plant_data")
class TestGlobalFunctions:
    def test_species_markup_func(self, session) -> None:
        eCo = Species.retrieve_or_create(
            session,
            {
                "object": "taxon",
                "ht-rank": "genus",
                "ht-epithet": "Maxillaria",
                "rank": "species",
                "epithet": "variabilis",
            },
            create=False,
            update=False,
        )
        model = Species.retrieve_or_create(
            session,
            {
                "object": "taxon",
                "ht-rank": "genus",
                "ht-epithet": "Laelia",
                "rank": "species",
                "epithet": "lobata",
            },
            create=False,
            update=False,
        )
        first, second = eCo.search_view_markup_pair()
        assert remove_zws(first).startswith("<i>Maxillaria</i> <i>variabilis</i>")
        expected = (
            '<i>Maxillaria</i> <i>variabilis</i> <span weight="light">'
            'Bateman ex Lindl.</span><span foreground="#555555" size="small" '
            'weight="light"> - synonym of <i>Encyclia</i> <i>cochleata</i> '
            "(L.) Lemée</span>"
        )
        assert remove_zws(first) == expected
        assert second == "Orchidaceae -- SomeName, SomeName 2"

        first, second = model.search_view_markup_pair()
        assert (
            remove_zws(first)
            == '<i>Laelia</i> <i>lobata</i> <span weight="light">H.J. Veitch</span>'
        )
        assert second == "Orchidaceae"

    def test_vername_markup_func(self, session) -> None:
        vName = session.execute(select(VernacularName).where(id=1)).scalars().one()
        first, second = vName.search_view_markup_pair()
        assert remove_zws(second) == "<i>Maxillaria</i> <i>variabilis</i>"
        assert first == "SomeName"

    def test_species_get_kids(self, session) -> None:
        mVa = session.execute(select(Species).where(id=1)).scalars().one()
        assert partial(db.natsort, "accessions")(mVa) == []

    def test_vernname_get_kids(self, session) -> None:
        vName = session.execute(select(VernacularName).where(id=1)).scalars().one()
        assert partial(db.natsort, "species.accessions")(vName) == []


@pytest.mark.usefixtures("setup_bauble_data")
class TestBaubleSearch:
    def test_search_uses_synonym_search(self, session, caplog) -> None:
        import bauble.plugins.garden.plant

        caplog.set_level(logging.DEBUG, logger="bauble.search")
        bauble.search.search("genus like %", session)
        assert 'SearchStrategy "genus like %"(SynonymSearch)' in caplog.text

        caplog.clear()
        bauble.search.search("12.11.13", session)
        assert 'SearchStrategy "12.11.13"(SynonymSearch)' in caplog.text

        caplog.clear()
        bauble.search.search("So ha", session)
        assert 'SearchStrategy "So ha"(SynonymSearch)' in caplog.text
