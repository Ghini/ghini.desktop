# -*- coding: utf-8 -*-
#
# Copyright 2015 Mario Frasca <mario@anche.no>.
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

import gtk

import logging
logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)

import bauble.utils as utils


class PicturesView(gtk.HBox):
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
        logger.debug("entering PicturesView.__init__(parent=%s, fake=%s)"
                     % (parent, fake))
        super(PicturesView, self).__init__()
        if fake:
            self.fake = True
            return
        self.fake = False
        import os
        from bauble import paths
        glade_file = os.path.join(
            paths.lib_dir(), 'pictures_view.glade')
        self.widgets = utils.BuilderWidgets(glade_file)
        self.widgets.remove_parent(self.widgets.scrolledwindow2)
        parent.add(self.widgets.scrolledwindow2)
        parent.show_all()
        self.widgets.scrolledwindow2.show()

    def set_selection(self, selection):
        logger.debug("PicturesView.set_selection(%s)" % selection)
        if self.fake:
            return
        self.box = self.widgets.pictures_box
        for k in self.box.children():
            k.destroy()

        for o in selection:
            try:
                pics = o.pictures
            except AttributeError:
                logger.debug('object %s does not know of pictures' % o)
                pics = []
            for p in pics:
                logger.debug('object %s has picture %s' % (o, p))
                expander = gtk.HBox()
                expander.add(p)
                self.box.pack_end(expander, expand=False, fill=False)
                self.box.reorder_child(expander, 0)
                expander.show_all()
                p.show()

        self.box.show_all()

    def add_picture(self, picture=None):
        """
        Add a new picture to the model.
        """
        expander = self.ContentBox(self, picture)
        self.box.pack_start(expander, expand=False, fill=False)
        expander.show_all()
        return expander

floating_window = None


def show_pictures_callback(selection):
    """activate a modal window showing plant pictures.

    the current selection defines what pictures should be shown. it
    makes sense for plant, accession and species.

    plants: show the pictures directly associated to them;

    accessions: show all pictures for the plants in the selected
    accessions.

    species: show the voucher.
    """

    floating_window.set_selection(selection)
