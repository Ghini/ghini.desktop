# -*- coding: utf-8 -*-
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

from gi.repository import Gtk
from gi.repository import Pango

import logging
logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)

import bauble
from bauble import db, meta, editor, paths, pluginmgr

import os.path


class StoredQueriesModel(object):
    def __init__(self):
        self.__label = [''] * 11
        self.__tooltip = [''] * 11
        self.__query = [''] * 11
        ssn = db.Session()
        q = ssn.query(meta.BaubleMeta)
        stqrq = q.filter(meta.BaubleMeta.name.startswith('stqr_'))
        for item in stqrq:
            if item.name[4] != '_':
                continue
            index = int(item.name[5:])
            self[index] = item.value
        ssn.close()
        self.page = 1

    def __repr__(self):
        return '[p:%d; l:%s; t:%s; q:%s' % (
            self.page, self.__label[1:], self.__tooltip[1:], self.__query[1:])

    def save(self):
        ssn = db.Session()
        for index in range(1, 11):
            if self.__label[index] == '':
                ssn.query(meta.BaubleMeta).\
                    filter_by(name='stqr_%02d' % index).\
                    delete()
            else:
                obj = db.get_or_create(ssn, meta.BaubleMeta,
                                       name='stqr_%02d' % index)
                if obj.value != self[index]:
                    obj.value = self[index]
        ssn.commit()
        ssn.close()

    def __getitem__(self, index):
        return '%s:%s:%s' % (self.__label[index],
                              self.__tooltip[index],
                              self.__query[index])

    def __setitem__(self, index, value):
        self.page = index
        self.label, self.tooltip, self.query = value.split(':', 2)

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
    def label(self):
        return self.__label[self.page]

    @label.setter
    def label(self, value):
        self.__label[self.page] = value

    @property
    def tooltip(self):
        return self.__tooltip[self.page]

    @tooltip.setter
    def tooltip(self, value):
        self.__tooltip[self.page] = value

    @property
    def query(self):
        return self.__query[self.page]

    @query.setter
    def query(self, value):
        self.__query[self.page] = value


class StoredQueriesPresenter(editor.GenericEditorPresenter):

    widget_to_field_map = {
        'stqr_label_entry': 'label',
        'stqr_tooltip_entry': 'tooltip',
        'stqr_query_textbuffer': 'query'}

    weight = {False: Pango.AttrList(),
              True: Pango.AttrList()}
    #weight[True].insert(Pango.AttrFontDesc(Pango.Weight.HEAVY, 0, 50))

    view_accept_buttons = ['stqr_ok_button', ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for self.model.page in range(1, 11):
            name = 'stqr_%02d_label' % self.model.page
            self.view.widget_set_text(name, self.model.label or _('<empty>'))
        self.model.page = 1

    def refresh_toggles(self):
        for i in range(1, 11):
            bname = 'stqr_%02d_button' % i
            lname = 'stqr_%02d_label' % i
            self.view.widget_set_active(bname, i == self.model.page)
            self.view.widget_set_attributes(lname,
                                            self.weight[i == self.model.page])

    def refresh_view(self):
        super().refresh_view()
        self.refresh_toggles()

    def on_button_clicked(self, widget, *args):
        if self.view.widget_get_active(widget) is False:
            return
        widget_name = self.widget_get_name(widget)
        self.model.page = int(widget_name[5:7])
        self.refresh_view()

    def on_next_button_clicked(self, widget, *args):
        self.model.page = self.model.page % 10 + 1
        self.refresh_view()

    def on_prev_button_clicked(self, widget, *args):
        self.model.page = (self.model.page - 2) % 10 + 1
        self.refresh_view()

    def on_label_entry_changed(self, widget, *args):
        self.on_text_entry_changed(widget, *args)
        page_label_name = 'stqr_%02d_label' % self.model.page
        value = self.view.widget_get_text(widget)
        self.view.widget_set_text(
            page_label_name, value or _('<empty>'))

    def on_stqr_query_textbuffer_changed(self, widget, value=None, attr=None):
        return self.on_textbuffer_changed(widget, value, attr='query')


def edit_callback():
    session = db.Session()
    view = editor.GenericEditorView(
        os.path.join(paths.lib_dir(),
                     'plugins', 'plants', 'stored_queries.glade'),
        parent=None,
        root_widget_name='stqr_dialog')
    stored_queries = StoredQueriesModel()
    presenter = StoredQueriesPresenter(
        stored_queries, view, session=session, refresh_view=True)
    error_state = presenter.start()
    if error_state > 0:
        stored_queries.save()
        bauble.gui.get_view().update()
    session.close()
    return error_state


class StoredQueryEditorTool(pluginmgr.Tool):
    label = _('Edit stored queries')

    @classmethod
    def start(self):
        edit_callback()
