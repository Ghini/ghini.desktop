# -*- coding: utf-8 -*-
#
# Copyright 2015 Mario Frasca <mario@anche.no>.
#
# This file is part of bauble.classic.
#
# bauble.classic is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# bauble.classic is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bauble.classic. If not, see <http://www.gnu.org/licenses/>.

import os
import logging
logger = logging.getLogger(__name__)
from bauble import db, paths, pluginmgr
from bauble.i18n import _


from bauble.editor import (
    GenericEditorView, GenericEditorPresenter)


def start_taxonomy_check():
    '''run the batch taxonomy check (BTC)
    '''

    view = GenericEditorView(
        os.path.join(paths.lib_dir(), 'plugins', 'plants',
                     'taxonomy_check.glade'),
        parent=None,
        root_widget_name='dialog1')
    model = type('BTCStatus', (object,), {})()
    model.page = 1
    model.selection = view.get_selection()
    model.tick_off = None
    model.report = None
    model.file_path = '/home/mario/Downloads/tnrs_results.txt'

    if model.selection is None:
        return
    presenter = BatchTaxonomicCheckPresenter(model, view, refresh_view=True)
    error_state = presenter.start()
    if error_state:
        presenter.session.rollback()
    else:
        presenter.commit_changes()
    presenter.session.close()
    presenter.cleanup()
    return error_state


class BatchTaxonomicCheckPresenter(GenericEditorPresenter):
    '''
    the batch taxonomy check (BTC) can run if you have an equal rank
    selection of taxa in your search results. The BTC exports the names
    to the clipboard and opens the browser on the
    http://tnrs.iplantcollaborative.org/TNRSapp.html page.

    the user will run the service on the remote site, then save the results to
    a file. then back to Bauble's BTC, the user will open the file and finally
    interact with the BTC view.

    the Model of the BTC is a list of tuples.

    '''

    widget_to_field_map = {'file_path_entry': 'file_path'}

    def __init__(self, *args, **kwargs):
        super(BatchTaxonomicCheckPresenter, self).__init__(*args, **kwargs)
        self.refresh_visible_frame()
        self.tick_off_list = self.view.widgets.liststore2
        self.tick_off_view = self.view.widgets.treeview2
        from bauble.plugins.plants import Species
        self.binomials = [item.str(item, remove_zws=True)
                          for item in self.model.selection
                          if isinstance(item, Species) and item.sp != '']

    def refresh_visible_frame(self):
        for i in range(1, 4):
            frame_id = 'frame%d' % i
            self.view.widget_set_visible(frame_id, i == self.model.page)

    def on_frame1_next(self, *args):
        'parse the results into the liststore2 and move to frame 2'
        responses = []
        self.tick_off_list.clear()
        import codecs
        with codecs.open(self.model.file_path, 'r', 'utf16') as f:
            keys = f.readline().strip().split('\t')
            for l in f.readlines():
                l = l.strip()
                values = [i.strip() for i in l.split("\t")]
                responses.append(dict(zip(keys, values)))
        for binomial, response in zip(self.binomials, responses):
            row = [response['Name_matched_rank'] == u'species'
                   and 'gtk-yes' or 'gtk-no',
                   binomial]
            for key in ['Name_matched', 'Name_matched_author',
                        'Taxonomic_status']:
                row.append(response[key])
            self.tick_off_list.append(row)
            if response['Taxonomic_status'] == 'Synonym':
                row = ['gtk-yes', '', response['Accepted_name'],
                       response['Accepted_name_author'], 'Accepted']
                self.tick_off_list.append(row)
        self.on_frame_next(*args)

    def on_frame2_next(self, *args):
        'execute all that is selected in liststore2 and move to frame 3'
        self.on_frame_next(*args)

    def on_frame_next(self, *args):
        self.model.page += 1
        self.refresh_visible_frame()

    def on_frame_previous(self, *args):
        self.model.page -= 1
        self.refresh_visible_frame()

    def on_copy_to_clipboard_button_clicked(self, *args):
        text = '\n'.join(self.binomials)
        import gtk
        clipboard = gtk.Clipboard()
        clipboard.set_text(text)

    def on_tnrs_browse_button_clicked(self, *args):
        from bauble.utils import desktop
        desktop.open('http://tnrs.iplantcollaborative.org/TNRSapp.html')

    def on_tick_off_view_row_activated(self, view, path, column, data=None):
        iter = self.tick_off_list.get_iter(path)
        value = self.tick_off_list[path][0]
        value = (value == 'gtk-yes') and 'gtk-no' or 'gtk-yes'
        self.tick_off_list.set_value(iter, 0, value)
        pass


class TaxonomyCheckTool(pluginmgr.Tool):
    label = _('Taxonomy check')

    @classmethod
    def start(self):
        start_taxonomy_check()
