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
#


from bauble.editor import GenericEditorView
from bauble.i18n import _


import logging
logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)


class PicturesView(GenericEditorView):
    """shows pictures corresponding to selection.

    at any time, no more than one PicturesView object will exist.

    when activated, the PicturesView object will be informed of changes
    to the selection and whatever the selection contains, the
    PicturesView object will ask each object in the selection to please
    return pictures, so that the PicturesView object can display them.

    if an object in the selection does not know of pictures (like it
    raises an exception because it does not define the 'pictures'
    property), the PicturesView object will silently accept the failure.

    """

    def __init__(self, parent=None, fake=False):
        if fake:
            self.fake = True
            return
        self.fake = False
        logger.debug("entering PicturesView.__init__")
        import os
        from bauble import paths
        glade_file = os.path.join(
            paths.lib_dir(), 'pictures_view.glade')
        super(PicturesView, self).__init__(glade_file, parent=parent)
        pass

    def get_window(self):
        return self.widgets.pictures_view_dialog

    def set_selection(self, selection):
        if self.fake:
            return
        logger.debug("PicturesView.set_selection(%s)" % selection)
        for o in selection:
            try:
                for p in o.pictures:
                    logger.debug('object %s has picture %s' % (o, p))
            except AttributeError:
                logger.debug('object %s does not know of pictures' % o)

floating_window = PicturesView(fake=True)


def show_pictures_callback(selection):
    """activate a modal window showing plant pictures.

    the current selection defines what pictures should be shown. it
    makes sense for plant, accession and species.

    plants: show the pictures directly associated to them;

    accessions: show all pictures for the plants in the selected
    accessions.

    species: show the voucher.
    """

    global floating_window
    floating_window = PicturesView()
    floating_window.set_selection(selection)
    floating_window.start()
    floating_window.get_window().set_keep_above(True)

    return floating_window
