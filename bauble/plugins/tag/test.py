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

import glob
import os
from collections.abc import Generator
from functools import partial
from typing import Any, Optional

import bauble.plugins.tag as tag_plugin
import bauble.utils as utils
import pytest
from bauble.editor import GenericEditorView, MockView
from bauble.gtkinit import Gtk
from bauble.plugins.plants import Family
from bauble.plugins.tag import Tag as Tag
from bauble.plugins.tag import TagEditorPresenter as TagEditorPresenter
from bauble.plugins.tag import create_named_empty_tag as create_named_empty_tag
from bauble.plugins.tag import remove_callback as remove_callback
from bauble.plugins.tag import tag_objects as tag_objects
from bauble.plugins.tag import tags_menu_manager as tags_menu_manager
from bauble.plugins.tag import untag_objects as untag_objects
from bauble.test import check_dupids, mockfunc
from sqlalchemy import delete, select


@pytest.fixture
def setup_tags(session) -> None:
    """Fixture to clear all tags before each test."""
    session.execute(delete(Tag))
    if session.in_transaction():
        session.commit()


def test_duplicate_ids() -> None:
    """
    Test for duplicate IDs for all .glade files in the tag plugin.
    """
    import bauble.plugins.tag as mod

    head, _ = os.path.split(mod.__file__)
    files = glob.glob(os.path.join(head, "*.glade"))
    for file in files:
        assert not check_dupids(file), f"Duplicate IDs found in {file}"


@pytest.mark.usefixtures("setup_tags")
class TestTagMenu:
    def test_no_tags(self) -> None:
        """Test menu creation when no tags are present."""
        menu = tags_menu_manager.build_menu()
        assert isinstance(menu, Gtk.Menu)
        assert len(menu.get_children()) == 1
        assert menu.get_children()[0].get_label() == "Tag Selection"

    def test_one_tag(self, session) -> None:
        """Test menu creation with one tag."""
        tag_name = "some_tag"
        tag = Tag(tag=tag_name, description="description")
        session.add(tag)
        if session.in_transaction():
            session.commit()

        menu = tags_menu_manager.build_menu()
        assert isinstance(menu, Gtk.Menu)
        assert len(menu.get_children()) == 6
        assert isinstance(menu.get_children()[1], Gtk.SeparatorMenuItem)
        assert menu.get_children()[2].get_label() == tag_name
        assert isinstance(menu.get_children()[3], Gtk.SeparatorMenuItem)

    def test_more_tags(self, session) -> None:
        """Test menu creation with multiple tags."""
        tag_name_template = "%s-some_tag"
        tags = [
            Tag(tag=tag_name_template % i, description="description") for i in range(5)
        ]
        session.add_all(tags)
        if session.in_transaction():
            session.commit()

        menu = tags_menu_manager.build_menu()
        assert isinstance(menu, Gtk.Menu)
        assert len(menu.get_children()) == 10

        for i in range(5):
            assert menu.get_children()[i + 2].get_label() == tag_name_template % i


@pytest.fixture
def setup_family_and_tags(session) -> Generator[Any, None, None]:
    """Fixture to add a default family and clear tags before each test."""
    family = Family(family="family")
    session.add(family)
    if session.in_transaction():
        session.commit()
    yield family
    session.execute(delete(Tag))  # <-- direct delete
    if session.in_transaction():
        session.commit()


@pytest.mark.usefixtures("setup_family_and_tags")
class TestTag:
    def test_str(self) -> None:
        """Test `Tag.__str__` method."""
        tag_name = "test"
        tag = Tag(tag=tag_name)
        assert str(tag) == tag_name

    def test_create_named_empty_tag(self, session) -> None:
        """Test creating a named empty tag."""
        tag_name = "name123"
        result = session.execute(select(Tag).where(Tag.tag == tag_name)).scalars().all()
        assert len(result) == 0

        create_named_empty_tag(tag_name)
        result = session.execute(select(Tag).where(Tag.tag == tag_name)).scalars().all()
        assert len(result) == 1
        assert result[0].tag == tag_name

        create_named_empty_tag(tag_name)
        tag_retrieved = (
            session.execute(select(Tag).where(Tag.tag == tag_name)).scalars().one()
        )
        assert tag_retrieved == result[0]

    def test_tag_nothing(self, session) -> None:
        """Test tagging nothing."""
        tag = Tag(tag="some_tag", description="description")
        session.add(tag)
        if session.in_transaction():
            session.commit()

        tag.tag_objects([])
        assert tag.objects == []
        assert tag.search_view_markup_pair() == (
            'some_tag - <span weight="light">tagging nothing</span>',
            '(Tag) - <span weight="light">description</span>',
        )

    def test_tag_objects(self, session, setup_family_and_tags) -> None:
        """Test tagging objects."""
        family2 = Family(family="family2")
        session.add(family2)
        if session.in_transaction():
            session.commit()

        tag_objects("test", [setup_family_and_tags, family2])

        tag = session.execute(select(Tag).where(Tag.tag == "test")).scalars().one()
        tagged_objs = tag.objects
        sorted_pairs = sorted([(type(obj), obj.id) for obj in tagged_objs])

        assert sorted_pairs == sorted(
            [(Family, setup_family_and_tags.id), (Family, family2.id)]
        )

        # Test untagging one object
        untag_objects("test", [setup_family_and_tags])
        tag = session.execute(select(Tag).where(Tag.tag == "test")).scalars().one()
        assert tag.objects == [family2]

        # Test untagging all objects
        untag_objects("test", [setup_family_and_tags, family2])
        tag = session.execute(select(Tag).where(Tag.tag == "test")).scalars().one()
        assert tag.objects == []

    def test_is_tagging(self, session, setup_family_and_tags) -> None:
        """Test checking if a tag is tagging an object."""
        family2 = Family(family="family2")
        tag = Tag(tag="test1")
        session.add_all([family2, tag])
        if session.in_transaction():
            session.commit()

        assert not tag.is_tagging(family2)
        assert not tag.is_tagging(setup_family_and_tags)

        tag.tag_objects([setup_family_and_tags])
        if session.in_transaction():
            session.commit()

        assert not tag.is_tagging(family2)
        assert tag.is_tagging(setup_family_and_tags)

    def test_search_view_markup_pair(self, session, setup_family_and_tags) -> None:
        """Test the search view markup for tagged objects."""
        family2 = Family(family="family2")
        tag1 = Tag(tag="test1")
        tag2 = Tag(tag="test2")
        session.add_all([family2, tag1, tag2])
        if session.in_transaction():
            session.commit()

        tag1.tag_objects([setup_family_and_tags, family2])
        tag2.tag_objects([setup_family_and_tags])
        if session.in_transaction():
            session.commit()

        assert tag1.search_view_markup_pair() == (
            'test1 - <span weight="light">tagging 2 objects of type Family</span>',
            '(Tag) - <span weight="light"></span>',
        )
        assert tag2.search_view_markup_pair() == (
            'test2 - <span weight="light">tagging 1 objects of type Family</span>',
            '(Tag) - <span weight="light"></span>',
        )

        # Add an additional tag to tag2
        tag2.tag_objects([tag1])
        if session.in_transaction():
            session.commit()

        assert tag2.search_view_markup_pair() == (
            'test2 - <span weight="light">tagging 2 objects of 2 different types: Family, Tag</span>',
            '(Tag) - <span weight="light"></span>',
        )

    def test_remove_callback_no_confirm(self, session) -> None:
        """Test remove callback without confirmation."""
        tag = Tag(tag="Arecaceae")
        session.add(tag)
        if session.in_transaction():
            session.commit()

        invoked = []
        partial(mockfunc, name="yes_no_dialog", caller=invoked, result=False)
        partial(mockfunc, name="message_details_dialog", caller=invoked)

        result = remove_callback([tag])
        if session.in_transaction():
            session.commit()

        # Assertions
        assert "message_details_dialog" not in [func for func, _ in invoked]
        assert (
            "yes_no_dialog",
            "Are you sure you want to remove Tag: Arecaceae?",
        ) in invoked
        assert result is None

        matching = (
            session.execute(select(Tag).where(Tag.tag == "Arecaceae")).scalars().all()
        )
        assert matching == [tag]

    def test_remove_callback_confirm(self, session) -> None:
        """Test remove callback with confirmation."""
        tag = Tag(tag="Arecaceae")
        session.add(tag)
        if session.in_transaction():
            session.commit()

        invoked = []
        save_reset = tag_plugin.tags_menu_manager.reset
        partial(mockfunc, name="yes_no_dialog", caller=invoked, result=True)
        tag_plugin.tags_menu_manager.reset = partial(
            mockfunc, name="_reset_tags_menu", caller=invoked
        )

        result = remove_callback([tag])
        tag_plugin.tags_menu_manager.reset = save_reset
        if session.in_transaction():
            session.commit()

        # Assertions
        assert "_reset_tags_menu" in [func for func, _ in invoked]
        assert (
            "yes_no_dialog",
            "Are you sure you want to remove Tag: Arecaceae?",
        ) in invoked
        assert result is True

        matching = (
            session.execute(select(Tag).where(Tag.tag == "Arecaceae")).scalars().all()
        )
        assert matching == []


@pytest.mark.usefixtures("setup_session")
class TestGetTagIds:
    fam1: Any
    fam2: Any
    fam3: Any
    fam4: Any

    @pytest.fixture(autouse=True)
    def setup_families_and_tags(self, session) -> Generator[None, None, None]:
        """Setup fixture for families and tags."""
        self.fam1 = Family(family="Fabaceae")
        self.fam2 = Family(family="Poaceae")
        self.fam3 = Family(family="Solanaceae")
        self.fam4 = Family(family="Caricaceae")
        session.add_all([self.fam1, self.fam2, self.fam3, self.fam4])
        if session.in_transaction():
            session.commit()

        tag_plugin.tag_objects("test1", [self.fam1, self.fam2])
        tag_plugin.tag_objects("test2", [self.fam1])
        tag_plugin.tag_objects("test3", [self.fam2, self.fam3])
        if session.in_transaction():
            session.commit()

        yield

        # Cleanup after tests
        session.execute(delete(Family))
        session.execute(delete(Tag))

        if session.in_transaction():
            session.commit()

    def test_get_tag_ids1(self, session) -> None:
        s_all, s_some, s_none = tag_plugin.get_tag_ids([self.fam1, self.fam2])
        assert s_all == {1}
        assert s_some == {2, 3}

    def test_get_tag_ids2(self, session) -> None:
        s_all, s_some, s_none = tag_plugin.get_tag_ids([self.fam1])
        assert s_all == {1, 2}
        assert s_some == set()

    def test_get_tag_ids3(self, session) -> None:
        s_all, s_some, s_none = tag_plugin.get_tag_ids([self.fam2])
        test_id = {1, 3}
        assert s_all == test_id
        assert s_some == set()

    def test_get_tag_ids4(self, session) -> None:
        s_all, s_some, s_none = tag_plugin.get_tag_ids([self.fam3])
        test_id = {3}
        assert s_all == test_id
        assert s_some == set()

    def test_get_tag_ids5(self, session) -> None:
        s_all, s_some, s_none = tag_plugin.get_tag_ids([self.fam1, self.fam3])
        assert s_all == set()
        assert s_some == {1, 2, 3}

    def test_get_tag_ids6(self, session) -> None:
        s_all, s_some, s_none = tag_plugin.get_tag_ids([self.fam1, self.fam4])
        assert s_all == set()
        assert s_some == {1, 2}

    def test_get_tag_ids7(self, session) -> None:
        # Cleanup existing tags and create new ones
        session.execute(delete(Tag))

        if session.in_transaction():
            session.commit()

        tag_plugin.tag_objects("test1", [self.fam1, self.fam4])
        tag_plugin.tag_objects("test2", [self.fam1])
        tag_plugin.tag_objects("test3", [self.fam2, self.fam4])
        if session.in_transaction():
            session.commit()

        s_all, s_some, s_none = tag_plugin.get_tag_ids(
            [self.fam1, self.fam2, self.fam3, self.fam4]
        )
        assert s_all == set()
        assert s_some == {1, 2, 3}


class MockTagView(GenericEditorView):
    _dirty: bool
    sensitive: bool
    dict: Any
    widgets: Any
    window: Any

    def __init__(self) -> None:
        self._dirty = False
        self.sensitive = False
        self.dict = {}
        self.widgets = None
        self.window = Gtk.Dialog()

    def get_window(self):
        return self.window

    def is_dirty(self):
        return self._dirty

    def connect_signals(self, *args) -> None:
        pass

    def set_accept_buttons_sensitive(self, value) -> None:
        self.sensitive = value

    def mark_problem(self, widget_name) -> None:
        pass

    def widget_set_value(
        self,
        widget,
        value,
        markup: bool = False,
        default: Optional[Any] = None,
        index: int = 0,
    ) -> None:
        self.dict[widget] = value

    def widget_get_value(self, widget, index: int = 0):
        return self.dict.get(widget)


@pytest.mark.usefixtures("setup_session")
class TestTagPresenter:
    def test_when_user_edits_name_name_is_memorized(self) -> None:
        model = Tag()
        view = MockTagView()
        presenter = TagEditorPresenter(model, view)

        view.widget_set_value("tag_name_entry", "1234")
        presenter.on_text_entry_changed("tag_name_entry")

        assert presenter.model.tag == "1234"

    def test_when_user_inserts_existing_name_warning_ok_deactivated(
        self, session
    ) -> None:
        # Prepare data in the database
        obj = Tag(tag="1234")
        session.add(obj)
        if session.in_transaction():
            session.commit()

        # Test with a new scratch object
        obj = Tag()
        session.add(obj)
        view = MockTagView()
        presenter = TagEditorPresenter(obj, view)

        assert not view.sensitive  # Initially not sensitive
        presenter.on_unique_text_entry_changed("tag_name_entry", "1234")

        assert obj.tag == "1234"
        assert view.is_dirty()
        assert not view.sensitive  # Unacceptable change
        assert presenter.has_problems()

    def test_widget_names_and_field_names(self) -> None:
        model = Tag()
        view = MockTagView()
        presenter = TagEditorPresenter(model, view)

        for widget, field in presenter.widget_to_field_map.items():
            assert hasattr(model, field)
            view.widget_get_value(widget)  # Test widget-to-field mapping

    def test_when_user_edits_fields_ok_active(self) -> None:
        model = Tag()
        view = MockTagView()
        presenter = TagEditorPresenter(model, view)

        assert not view.sensitive  # Initially not sensitive
        view.widget_set_value("tag_name_entry", "1234")
        presenter.on_text_entry_changed("tag_name_entry")

        assert presenter.model.tag == "1234"
        assert view.sensitive  # Sensitive after change

    def test_when_user_edits_description_description_is_memorized(self) -> None:
        # This is a placeholder test
        pass

    def test_presenter_does_not_initialize_view(self, session) -> None:
        # Prepare data in the database
        obj = Tag(tag="1234")
        session.add(obj)

        # Test with the presenter and the view
        view = MockTagView()
        presenter = TagEditorPresenter(obj, view)

        assert not view.widget_get_value("tag_name_entry")  # Initially not set
        presenter.refresh_view()
        assert view.widget_get_value("tag_name_entry") == "1234"

    def test_if_asked_presenter_initializes_view(self, session) -> None:
        # Prepare data in the database
        obj = Tag(tag="1234")
        session.add(obj)

        # Test with `refresh_view=True`
        view = MockTagView()
        TagEditorPresenter(obj, view, refresh_view=True)

        assert view.widget_get_value("tag_name_entry") == "1234"


@pytest.mark.usefixtures("setup_session")
class TestAttachedTo:
    @pytest.fixture(autouse=True)
    def setup(self, session) -> None:
        obj1 = Tag(tag="medicinal")
        obj2 = Tag(tag="maderable")
        obj3 = Tag(tag="frutal")
        fam = Family(family="Solanaceae")
        session.add_all([obj1, obj2, obj3, fam])
        if session.in_transaction():
            session.commit()

    def test_attached_tags_empty(self, session) -> None:
        fam = session.execute(select(Family)).scalars().one()
        assert Tag.attached_to(fam) == []

    def test_attached_tags_singleton(self, session) -> None:
        fam = session.execute(select(Family)).scalars().one()
        obj2 = (
            session.execute(select(Tag).where(Tag.tag == "maderable")).scalars().one()
        )
        tag_plugin.tag_objects(obj2, [fam])
        assert Tag.attached_to(fam) == [obj2]

    def test_attached_tags_many(self, session) -> None:
        fam = session.execute(select(Family)).scalars().one()
        tags = session.execute(select(Tag)).scalars().all()
        for t in tags:
            tag_plugin.tag_objects(t, [fam])
        assert Tag.attached_to(fam) == tags


class FakeGui:
    invoked: Any
    window: Any

    def __init__(self) -> None:
        self.invoked = []
        self.window = self

    def get_view(self):
        return MockView(selection=[])

    def show_message_box(self, *args, **kwargs) -> None:
        self.invoked.append((args, kwargs))

    def add_accel_group(self, *args, **kwargs) -> None:
        self.invoked.append(("window.add_accel_group", args, kwargs))

    def add_to_insert_menu(self, *args, **kwargs) -> None:
        self.invoked.append(("add_to_insert_menu", args, kwargs))

    def add_menu(self, *args, **kwargs) -> None:
        self.invoked.append(("add_menu", args, kwargs))


@pytest.fixture
def fake_gui(monkeypatch):
    local_gui = FakeGui()
    monkeypatch.setattr("bauble.gui", local_gui)
    return local_gui


def test_on_add_tag_activated_wrong_view(fake_gui, monkeypatch) -> None:
    import bauble

    # Use monkeypatch to inject the FakeGui instance into the bauble module
    monkeypatch.setattr(bauble, "gui", fake_gui)

    # Invoke the actual method being tested
    tag_plugin._on_add_tag_activated()

    # Verify the expected behavior
    assert fake_gui.invoked[0] == (
        (
            "In order to tag an item you must first search for something and select one of the results.",
        ),
        {},
    )


def test_on_add_tag_activated_search_view_empty_selection(fake_gui, monkeypatch):
    import bauble

    # Use monkeypatch to inject the FakeGui instance into the bauble module
    monkeypatch.setattr(bauble, "gui", fake_gui)

    # Replace utils.message_dialog with FakeGui's method
    monkeypatch.setattr(utils, "message_dialog", fake_gui.show_message_box)

    # Modify the MockView to simulate no selected values
    def mock_get_selected_values():
        return []

    monkeypatch.setattr(MockView, "get_selected_values", mock_get_selected_values)

    # Invoke the actual method being tested
    tag_plugin._on_add_tag_activated()

    # Verify the expected behavior
    assert fake_gui.invoked[0] == (("Nothing selected",), {})
