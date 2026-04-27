#
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
#
import logging
import os.path
from gettext import gettext as _
from typing import Any, Optional

import bauble
from bauble import db, editor, meta, paths, pluginmgr
from bauble.gtkinit import Pango
from sqlalchemy import select

logger: Any = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class StoredQueriesModel:
    _label: Any
    _tooltip: Any
    _query: Any
    page: int
    __index: int

    def __init__(self) -> None:
        self._label = [""] * 11
        self._tooltip = [""] * 11
        self._query = [""] * 11

        # Use a context manager to ensure session cleanup
        with db.Session() as session:
            if session.in_transaction():
                session.commit()  # Ensure session if fully initialized before querying
            query = select(meta.BaubleMeta).filter(
                meta.BaubleMeta.name.startswith("stqr_")
            )
            for item in session.scalars(query):
                if str(item.name)[4] != "_":
                    continue
                index = int(str(item.name)[5:])
                self[index] = item.value

        self.page = 1

    def __repr__(self) -> str:
        return "[p:%d; l:%s; t:%s; q:%s" % (
            self.page,
            self._label[1:],
            self._tooltip[1:],
            self._query[1:],
        )

    def save(self) -> None:
        """
        Save the current state of stored queries to the database.
        """
        try:
            with db.Session() as session:
                for index in range(1, 11):
                    query_name = f"stqr_{index:02d}"

                    # If the label is empty, remove the corresponding record
                    if self._label[index] == "":
                        stmt = select(meta.BaubleMeta).filter_by(name=query_name)
                        obj = (
                            session.execute(stmt).scalars().first()
                        )  # Retrieve the model instance
                        if obj:
                            session.delete(obj)
                    else:
                        # Use get_or_create to retrieve or create the object
                        obj, created = db.get_or_create(
                            session, meta.BaubleMeta, name=query_name
                        )

                        # Update the object's value if it differs
                        if obj.value != self[index]:
                            obj.value = self[index]

                # Commit the changes
                if session.in_transaction():
                    session.commit()
        except Exception as e:
            logger.error(f"Error during save: {e}")
            raise

    def __getitem__(self, index):
        return f"{self._label[index]}:{self._tooltip[index]}:{self._query[index]}"

    def __setitem__(self, index, value) -> None:
        self.page = index
        self.label, self.tooltip, self.query = value.split(":", 2)

    def __iter__(self):
        self.__index = 0
        return self

    def __next__(self):
        if self.__index == 10:
            raise StopIteration
        else:
            self.__index += 1
            return self[self.__index]

    @property
    def label(self) -> str:
        return self._label[self.page]

    @label.setter
    def label(self, value):
        self._label[self.page] = value

    @property
    def tooltip(self) -> str:
        return self._tooltip[self.page]

    @tooltip.setter
    def tooltip(self, value):
        self._tooltip[self.page] = value

    @property
    def query(self) -> str:
        return self._query[self.page]

    @query.setter
    def query(self, value):
        self._query[self.page] = value


class StoredQueriesPresenter(editor.GenericEditorPresenter):

    view_accept_buttons: Any
    widget_to_field_map: Any = {
        "stqr_label_entry": "label",
        "stqr_tooltip_entry": "tooltip",
        "stqr_query_textbuffer": "query",
    }

    weight: Any = {False: Pango.AttrList(), True: Pango.AttrList()}
    # weight[True].insert(Pango.AttrFontDesc(Pango.Weight.HEAVY, 0, 50))

    view_accept_buttons = [
        "stqr_ok_button",
    ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        for self.model.page in range(1, 11):
            name = "stqr_%02d_label" % self.model.page
            self.view.widget_set_text(name, self.model.label or _("<empty>"))
        self.model.page = 1

    def refresh_toggles(self) -> None:
        for i in range(1, 11):
            bname = "stqr_%02d_button" % i
            lname = "stqr_%02d_label" % i
            self.view.widget_set_active(bname, i == self.model.page)
            self.view.widget_set_attributes(lname, self.weight[i == self.model.page])

    def refresh_view(self) -> None:
        super().refresh_view()
        self.refresh_toggles()

    def on_button_clicked(self, widget, *args) -> None:
        if self.view.widget_get_active(widget) is False:
            return
        widget_name = self.widget_get_name(widget)
        self.model.page = int(widget_name[5:7])
        self.refresh_view()

    def on_next_button_clicked(self, widget, *args) -> None:
        self.model.page = self.model.page % 10 + 1
        self.refresh_view()

    def on_prev_button_clicked(self, widget, *args) -> None:
        self.model.page = (self.model.page - 2) % 10 + 1
        self.refresh_view()

    def on_label_entry_changed(self, widget, *args) -> None:
        self.on_text_entry_changed(widget, *args)
        page_label_name = "stqr_%02d_label" % self.model.page
        value = self.view.widget_get_text(widget)
        self.view.widget_set_text(page_label_name, value or _("<empty>"))

    def on_stqr_query_textbuffer_changed(
        self, widget, value: Optional[Any] = None, attr: Optional[Any] = None
    ):
        return self.on_textbuffer_changed(widget, value, attr="query")


def edit_callback():
    with db.Session() as session:
        view = editor.GenericEditorView(
            os.path.join(paths.lib_dir(), "plugins", "plants", "stored_queries.glade"),
            parent=None,
            root_widget_name="stqr_dialog",
        )
        stored_queries = StoredQueriesModel()
        presenter = StoredQueriesPresenter(
            stored_queries, view, session=session, refresh_view=True
        )
        error_state = presenter.start()
        if error_state > 0:
            stored_queries.save()
            bauble.gui.get_view().update()
        return error_state


class StoredQueryEditorTool(pluginmgr.Tool):
    item_position: int = 20
    label: Any = _("Edit stored queries")
    icon_name: str = "x-office-spreadsheet"

    @classmethod
    def start(cls) -> None:
        edit_callback()
