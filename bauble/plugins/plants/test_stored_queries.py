# Copyright 2016 Mario Frasca <mario@anche.no>.
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
from bauble import prefs
from bauble.editor import MockView

# Enable testing mode
from bauble.plugins.plants.stored_queries import (
    StoredQueriesModel as StoredQueriesModel,
)
from bauble.plugins.plants.stored_queries import (
    StoredQueriesPresenter as StoredQueriesPresenter,
)

prefs.testing = True


@pytest.mark.usefixtures("db_session")
class TestStoredQueriesInitialize:
    def test_initialize_model(self) -> None:
        model = StoredQueriesModel()
        for i in range(1, 9):
            assert (
                model[i] == "::"
            ), f"Expected default empty value for model[{i}], but got: {model[i]}"

    def test_initialize_has_defaults(self) -> None:
        model = StoredQueriesModel()
        for i in range(1, 9):
            assert (
                model[i] == "::"
            ), f"Expected default empty value for model[{i}], but got: {model[i]}"


@pytest.mark.usefixtures("db_session")
class TestStoredQueries:
    def test_define_label(self) -> None:
        model = StoredQueriesModel()
        model.label = "n=1"
        assert model.label == "n=1"
        model.page = 2
        assert model.label == ""
        model.label = "n=2"
        assert model.label == "n=2"
        model.page = 1
        assert model.label == "n=1"

    def test_define_tooltip(self) -> None:
        model = StoredQueriesModel()
        model.tooltip = "n=1"
        assert model.tooltip == "n=1"
        model.page = 2
        assert model.tooltip == ""
        model.tooltip = "n=2"
        assert model.tooltip == "n=2"
        model.page = 1
        assert model.tooltip == "n=1"

    def test_define_query(self) -> None:
        model = StoredQueriesModel()
        model.query = "n=1"
        assert model.query == "n=1"
        model.page = 2
        assert model.query == ""
        model.query = "n=2"
        assert model.query == "n=2"
        model.page = 1
        assert model.query == "n=1"

    def test_loop(self) -> None:
        model = StoredQueriesModel()
        before = [i for i in model]

        model.page = 1
        model.label = "l=1"
        model.tooltip = "t=1"
        model.query = "q=1"
        model.page = 2
        model.label = "l=2"
        model.tooltip = "t=2"
        model.query = "q=2"

        after = before.copy()
        after[0] = "l=1:t=1:q=1"
        after[1] = "l=2:t=2:q=2"
        assert model[1] == after[0]
        assert model[2] == after[1]
        assert model[3] == "::"
        assert [i for i in model] == after

    def test_setgetitem(self) -> None:
        model = StoredQueriesModel()
        before = [i for i in model]
        model[1] = "l:t:q"
        model[4] = "l:t:q"
        after = [i for i in model]
        for i, _v in enumerate(after):
            if i in [0, 3]:
                assert after[i] == "l:t:q"
            else:
                assert after[i] == before[i]

    def test_save(self) -> None:
        model = StoredQueriesModel()
        model[1] = "l:t:q"
        model[4] = "l:t:q"
        model.save()
        new_model = StoredQueriesModel()
        assert [i for i in new_model] == [k for k in model]
        assert id(new_model) != id(model)

    def test_save_overwrite(self) -> None:
        model = StoredQueriesModel()
        model[1] = "l:t:q"
        model[4] = "l:t:q"
        model.save()
        new_model = StoredQueriesModel()
        new_model[5] = "l:t:q"
        new_model.save()
        reloaded_model = StoredQueriesModel()
        assert [i for i in new_model] == [k for k in reloaded_model]
        assert id(new_model) != id(reloaded_model)


@pytest.mark.usefixtures("db_session")
class TestStoredQueriesPresenter:
    def test_create_presenter(self) -> None:
        view = MockView()
        model = StoredQueriesModel()
        presenter = StoredQueriesPresenter(model, view)
        assert presenter.view == view
        assert id(presenter.model) == id(model)

    def test_change_page(self) -> None:
        view = MockView()
        model = StoredQueriesModel()
        presenter = StoredQueriesPresenter(model, view)
        model.page = 2
        presenter.refresh_view()
        for i in range(1, 11):
            bname = f"stqr_{i:02d}_button"
            assert (
                "widget_set_active",
                (bname, i == model.page),
            ) in presenter.view.invoked_detailed
            lname = f"stqr_{i:02d}_label"
            assert (
                "widget_set_attributes",
                (lname, presenter.weight[i == model.page]),
            ) in presenter.view.invoked_detailed

    def test_next_page(self) -> None:
        view = MockView()
        model = StoredQueriesModel()
        presenter = StoredQueriesPresenter(model, view)
        assert model.page == 1
        presenter.on_next_button_clicked(None)
        assert model.page == 2
        presenter.on_next_button_clicked(None)
        assert model.page == 3

    def test_prev_page(self) -> None:
        view = MockView()
        model = StoredQueriesModel()
        presenter = StoredQueriesPresenter(model, view)
        assert model.page == 1
        presenter.on_prev_button_clicked(None)
        assert model.page == 10
        presenter.on_prev_button_clicked(None)
        assert model.page == 9

    def test_select_page(self) -> None:
        view = MockView()
        model = StoredQueriesModel()
        presenter = StoredQueriesPresenter(model, view)
        assert model.page == 1
        bname = "stqr_05_button"
        presenter.on_button_clicked(bname)
        assert model.page == 5
        assert ("widget_set_active", (bname, True)) in presenter.view.invoked_detailed
        assert (
            "widget_set_active",
            ("stqr_01_button", False),
        ) in presenter.view.invoked_detailed

    def test_label_entry_change(self) -> None:
        view = MockView()
        model = StoredQueriesModel()
        presenter = StoredQueriesPresenter(model, view)
        bname = "stqr_04_button"
        presenter.on_button_clicked(bname)
        assert model.page == 4
        presenter.view.values["stqr_label_entry"] = "abc"
        presenter.on_label_entry_changed("stqr_label_entry")
        assert model.label == "abc"
        assert (
            "widget_set_text",
            ("stqr_04_label", "abc"),
        ) in presenter.view.invoked_detailed
        presenter.view.values["stqr_label_entry"] = ""
        presenter.on_label_entry_changed("stqr_label_entry")
        assert model.label == ""
        assert (
            "widget_set_text",
            ("stqr_04_label", "<empty>"),
        ) in presenter.view.invoked_detailed
