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


import logging
logger = logging.getLogger(__name__)

import gtk
import threading
import glib
import re
import os.path
from bauble import pluginmgr

from bauble.editor import (GenericEditorView, GenericEditorPresenter)

accno_re = re.compile(r'([12][0-9][0-9][0-9]\.[0-9][0-9][0-9][0-9])(?:\.([0-9]+))?')
species_re = re.compile(r'([A-Z][a-z]+(?: [a-z-]*)?)')
picname_re = re.compile(r'([A-Z]+[0-9]+)')
number_re = re.compile(r'([0-9]+)')

def decode_parts(name, acc_format=None):
    """return the dictionary of parts in name

    name is matched against the basic concepts in a plant description, like
    its accession or species.  all matching parts are used to construct a
    dictionary, which is then returned.

    accession, defaults to None,
    plant, defaults to 1,
    seq, defaults to 1,
    species, defaults to Zzz

    """

    # look for anything looking like (and remove it), in turn: species name,
    # accession number with optional plant number, original picture name,
    # some other number overruling the original picture name.

    #only scan name part, ignore location
    path, name = os.path.split(name)

    result = {'accession': None,
              'plant': '1',
              'seq': '1',
              'species': 'Zzz'}

    if acc_format is None:
        use_accno_re = accno_re
    else:
        exp_str = acc_format.replace('.', '\.').replace('#', "[0-9]")
        exp_str = "(%s)(?:\.([0-9]+))?" % exp_str
        use_accno_re = re.compile(exp_str)
    for key, exp in [('accession', use_accno_re),
                     ('species', species_re),
                     ('seq', picname_re),
                     ('seq', number_re)]:
        match = exp.search(name)
        if match:
            value = match.group(1)
            if not value:
                continue
            if key == 'seq':
                value = re.sub(r'([A-Z]+0*)', '', value)
            result[key] = value
            if key == 'accession' and match.group(2):
                result['plant'] = match.groups()[1]
            name = name.replace(match.group(0), '')
    if result['accession'] is None:
        return None
    return result


class TextBufferHandler(logging.Handler):
    def __init__(self, textbuffer, *args, **kwargs):
        super(TextBufferHandler, self).__init__(*args, **kwargs)
        self.textbuffer = textbuffer

    def emit(self, record):
        msg = self.format(record)
        self.textbuffer.insert(self.textbuffer.get_end_iter(), msg)
        self.textbuffer.insert(self.textbuffer.get_end_iter(), "\n")


class PictureImporterPresenter(GenericEditorPresenter):
    widget_to_field_map = {
        'accno_entry': 'accno_format',
        'filepath_entry': 'filepath',
        'recurse_checkbutton': 'recurse'}

    use_me_col = 0
    filename_col = 1
    accno_col = 2
    binomial_col = 3
    thumbnail_col = 4
    iseditable_col = 5
    orig_accno_col = 6
    edited_accno_col = 7
    full_filename_col = 8
    orig_binomial = 9
    edited_binomial_col = 10
    def __init__(self, model, view, **kwargs):
        kwargs['refresh_view'] = True
        super(PictureImporterPresenter, self).__init__(model, view, **kwargs)
        self.panes = [getattr(self.view.widgets, 'box_define'),
                      getattr(self.view.widgets, 'box_review'),
                      getattr(self.view.widgets, 'box_log'),]
        self.review_rows = self.view.widgets.review_liststore
        self.show_visible_pane()
        self.view.widgets.use_tvc.set_sort_column_id(0)
        self.view.widgets.filename_tvc.set_sort_column_id(1)
        self.view.widgets.accno_tvc.set_sort_column_id(2)
        self.view.widgets.binomial_tvc.set_sort_column_id(3)
        self.view.widgets.iseditable_tvc.set_sort_column_id(5)
        self.running = None

    def show_visible_pane(self):
        for n, i in enumerate(self.panes):
            i.set_visible(n == self.model.visible_pane)
        self.view.widgets.button_prev.set_sensitive(self.model.visible_pane > 0)
        self.view.widgets.button_next.set_sensitive(self.model.visible_pane < len(self.panes) - 1)
        self.view.widgets.button_ok.set_sensitive(self.model.visible_pane == len(self.panes) - 1)
        if self.model.visible_pane != 1:
            self.running = None

    def load_pixbufs(self):
        # to be run in different thread - or you're blocking the gui
        for fname, path in self.pixbufs_to_load:
            if self.running is None:
                return
            pixbuf = gtk.gdk.pixbuf_new_from_file(fname)
            try:
                pixbuf = pixbuf.apply_embedded_orientation()
                scale_x = pixbuf.get_width() / 144
                scale_y = pixbuf.get_height() / 144
                scale = max(scale_x, scale_y, 1)
                x = int(pixbuf.get_width() / scale)
                y = int(pixbuf.get_height() / scale)
                self.review_rows[path][thumbnail_col] = pixbuf.scale_simple(x, y, gtk.gdk.INTERP_BILINEAR)
            except glib.GError, e:
                logger.debug("picture %s caused glib.GError %s" %
                             (fname, e))
            except Exception, e:
                logger.warning("picture %s caused Exception %s:%s" %
                               (fname, type(e), e))

    def add_rows(self, arg, dirname, fnames):
        for name in fnames:
            d = decode_parts(name, self.model.accno_format)
            if d is None:
                continue
            row = [True, name, d['accession'], d['species'], None, False, d['accession'], d['accession'],
                   os.path.join(dirname, name), d['species'], d['species']]
            self.pixbufs_to_load.append((os.path.join(dirname, name), (len(self.review_rows), )))
            self.review_rows.append(row)

    def on_cellrenderertext_edited(self, widget, path, new_text, *args, **kwargs):
        if widget == self.view.widgets.accno_crtext:
            self.review_rows[path][accno_col] = self.review_rows[path][edited_accno_col] = new_text
        elif widget == self.view.widgets.binomial_crtext:
            self.review_rows[path][binomial_col] = self.review_rows[path][edited_binomial_col] = new_text

    def on_use_crtoggle_toggled(self, column_widget, path):
        self.review_rows[path][use_me_col] = not self.review_rows[path][use_me_col]

    def on_edit_crtoggle_toggled(self, column_widget, path):
        self.review_rows[path][iseditable_col] = not self.review_rows[path][iseditable_col]
        if not self.review_rows[path][iseditable_col]:  # let's restore original
            self.review_rows[path][accno_col] = self.review_rows[path][orig_accno_col]
            self.review_rows[path][binomial_col] = self.review_rows[path][orig_binomial_col]
        else:  # otherwise: restore last edit
            self.review_rows[path][accno_col] = self.review_rows[path][edited_accno_col]
            self.review_rows[path][binomial_col] = self.review_rows[path][edited_binomial_col]

    def on_picture_importer_dialog_response(self, widget, response, **kwargs):
        self.running = None

    def on_action_prev_activate(self, *args, **kwargs):
        self.model.visible_pane -= 1
        self.show_visible_pane()

    def do_import(self):  # step 2
        handler = TextBufferHandler(self.view.widgets.log_buffer)
        logger.addHandler(handler)

    def on_action_next_activate(self, *args, **kwargs):
        self.model.visible_pane += 1
        if self.model.visible_pane == 1:  # let user review import
            self.review_rows.clear()
            self.pixbufs_to_load = []
            os.path.walk(self.model.filepath, self.add_rows, None)
            self.running = True
            threading.Thread(target=self.load_pixbufs).start()
        elif self.model.visible_pane == 2:  # import as specified
            self.do_import()
        self.show_visible_pane()

    def on_action_cancel_activate(self, *args, **kwargs):
        self.view.get_window().emit('response', gtk.RESPONSE_DELETE_EVENT)

    def on_action_ok_activate(self, *args, **kwargs):
        self.view.get_window().emit('response', gtk.RESPONSE_OK)

    def on_action_browse_activate(self, *args, **kwargs):
        text = _('Select pictures source directory')
        parent = None
        action = gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER
        buttons = (_('Cancel'), gtk.RESPONSE_CANCEL, _('Ok'), gtk.RESPONSE_ACCEPT, )
        last_folder = self.model.filepath
        target = 'filepath_entry'
        self.view.run_file_chooser_dialog(text, parent, action, buttons, last_folder, target)

class PictureImporterTool(pluginmgr.Tool):
    category = _('Import')
    label = _('Picture Collection')
    model = type('Model', (object,),
                 {'visible_pane': 0,
                  'filepath': '',
                  'accno_format': '####.####',
                  'recurse': False,
                  'default_location': 'imported',
                  'rows': [],
                  'log': []})
    import os.path
    from bauble import paths
    glade_path = os.path.join(paths.lib_dir(), "plugins", "garden",
                              "picture_importer.glade")

    @classmethod
    def start(cls):
        cls.model.visible_pane = 0
        view = GenericEditorView(
            cls.glade_path,
            parent=None,
            root_widget_name='picture_importer_dialog')
        presenter = PictureImporterPresenter(cls.model, view)
        result = presenter.start()
        if result == gtk.RESPONSE_OK:
            presenter.session.commit()
        else:
            presenter.session.rollback()
        return True
