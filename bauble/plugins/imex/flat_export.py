# -*- coding: utf-8 -*-
#
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


class FlatFileExporter(GenericEditorPresenter):

    view_accept_buttons = ['cancel_button', 'confirm_button']

    def __init__(self, view=None):
        super().__init__(model=self, view=view, refresh_view=False)

    def set_model_fields(output_file=None, iteration_domain=None,
                         exported_fields=None, 
                         **kwargs):
        pass


class FlatFileExportTool(pluginmgr.Tool):
    category = _('Export')
    label = _('Flat file (csv)')

    @classmethod
    def start(cls):
        gladefilepath = os.path.join(paths.lib_dir(), "flat_file.glade")
        view = GenericEditorView(
            gladefilepath,
            parent=None,
            root_widget_name='main_dialog')
        qb = FlatFileExporter(view)
        qb.set_model_fields(output_file='/tmp/test.csv', iteration_domain='Plant',
                            exported_fields=['accession.code', 'code', 'accession.species.genus.epithet', 'accession.species.epithet'])
        response = qb.start()
        if response == Gtk.ResponseType.OK:
            query = qb.do_export()
        qb.cleanup()

