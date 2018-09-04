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
#
# implements the xmlrcp server for the p2d and d2p streams
#

import logging
logger = logging.getLogger(__name__)

import os.path

from bauble import paths
from bauble import pluginmgr
from bauble.editor import (
    GenericEditorView, GenericEditorPresenter)


class PocketServerPresenter(GenericEditorPresenter):
    '''manage the xmlrpc server for pocket communication

    '''

    def __init__(self, view):
        super().__init__(model=self, view=view, refresh_view=False)


class PocketServerTool(pluginmgr.Tool):
    label = _('Pocket Server…')
    icon_name = "server"

    @classmethod
    def start(cls):
        filename = os.path.join(paths.lib_dir(), "plugins", "imex", 'select_export.glade')
        view = GenericEditorView(filename, root_widget_name='pocket_server_dialog')
        c = PocketServerPresenter(view)
        c.start()
