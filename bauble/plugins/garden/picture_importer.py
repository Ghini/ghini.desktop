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


import gtk
import re
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
    for key, exp in [('species', species_re),
                     ('accession', use_accno_re),
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


class PictureImporterPresenter(GenericEditorPresenter):
    widget_to_field_map = {
        'accno_entry': 'accno_format',
        'filepath_entry': 'filepath',
        'recurse_checkbox': 'recurse'}

    def __init__(self, *args, **kwargs):
        super(PictureImporterPresenter, self).__init__(*args, **kwargs)
        self.panes = [getattr(self.view.widgets, 'box_define'),
                      getattr(self.view.widgets, 'box_review'),
                      getattr(self.view.widgets, 'box_log'),]
        self.show_visible_pane()

    def show_visible_pane(self):
        for n, i in enumerate(self.panes):
            i.set_visible(n == self.model.visible_pane)
        self.view.widgets.button_prev.set_sensitive(self.model.visible_pane > 0)
        self.view.widgets.button_next.set_sensitive(self.model.visible_pane < len(self.panes) - 1)
    
    def start(self, *args, **kwargs):
        super(PictureImporterPresenter, self).start(*args, **kwargs)

    def on_picture_importer_dialog_close(self, *args, **kwargs):
        print 'close', args, kwargs

    def on_picture_importer_dialog_response(self, *args, **kwargs):
        print 'response', args, kwargs

    def on_action_prev_activate(self, *args, **kwargs):
        self.model.visible_pane -= 1
        self.show_visible_pane()

    def on_action_next_activate(self, *args, **kwargs):
        self.model.visible_pane += 1
        self.show_visible_pane()

    def on_action_cancel_activate(self, *args, **kwargs):
        self.view.get_window().emit('response', gtk.RESPONSE_DELETE_EVENT)

    def on_action_ok_activate(self, *args, **kwargs):
        self.view.get_window().emit('response', gtk.RESPONSE_OK)

    def on_action_browse_activate(self, *args, **kwargs):
        print 'next', args, kwargs



class PictureImporterTool(pluginmgr.Tool):
    category = _('Import')
    label = _('Picture Collection')

    @classmethod
    def start(self):
        import os.path
        from bauble import paths
        glade_path = os.path.join(paths.lib_dir(), "plugins", "garden",
                                  "picture_importer.glade")
        view = GenericEditorView(
            glade_path,
            parent=None,
            root_widget_name='picture_importer_dialog')
        model = type('Model', (object,),
                     {'visible_pane': 0,
                      'filepath': '',
                      'accno_format': '####.####',
                      'recurse': False,
                      'default_location': None,
                      'rows': [],
                      'log': []})
        presenter = PictureImporterPresenter(model, view)
        result = presenter.start()
        return result is not None

