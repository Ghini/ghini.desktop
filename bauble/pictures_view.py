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
import logging
from typing import Any, Optional

import bauble.utils as utils
from bauble.db import Session
from bauble.gtkinit import Gtk
from sqlalchemy.orm.exc import DetachedInstanceError

logger: Any = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class PicturesView:
    """Displays pictures corresponding to selection."""

    fake: Any
    widgets: Any
    pictures_box: Any
    ghini_box: Any

    def __init__(self, parent: Optional[Any] = None, fake: bool = False) -> None:
        logger.debug(f"entering PicturesView.__init__(parent={parent}, fake={fake})")
        self.fake = fake

        if self.fake:
            return

        import os

        from bauble import paths

        glade_file = os.path.join(paths.lib_dir(), "pictures_view.glade")
        self.widgets = utils.BuilderWidgets(glade_file)

        # Use Gtk.Box for layout composition
        self.pictures_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        # Remove parent reference from builder and add to the new parent
        self.widgets.remove_parent(self.widgets.scrolledwindow2)
        parent.add(self.widgets.scrolledwindow2)
        parent.show_all()
        self.widgets.scrolledwindow2.show()

    def set_selection(self, selection) -> None:
        """
        Updates the view based on the current selection.
        If an object in the selection contains a `pictures` property,
        its pictures will be displayed.
        """
        logger.debug(f"Setting selection: {selection}")
        if self.fake:
            return

        self.ghini_box = self.widgets.pictures_box

        # Clear existing children
        for child in self.ghini_box.get_children():
            child.destroy()

        for obj in selection or []:
            pics = []
            try:
                # first attempt — will fail if obj is detached
                pics = getattr(obj, "pictures")
            except AttributeError:
                logger.debug(f"Object {obj} does not define 'pictures' attribute")
                continue
            except DetachedInstanceError:
                # Reattach to a short-lived session and retry once
                with Session() as s:
                    try:
                        obj = s.merge(obj, load=False)  # cheap reattach
                        pics = getattr(obj, "pictures")
                    except Exception as e:
                        logger.warning("Could not load pictures for %r after merge: %s", obj, e)
                        pics = []

            for pic in pics or []:
                logger.debug(f"Object {obj} has picture {pic}")
                self.add_picture(pic)

        self.ghini_box.show_all()

    def add_picture(self, picture: Optional[Any] = None):
        """
        Adds a new picture to the model.
        """
        if picture is None:
            logger.warning("add_picture() called with no picture provided.")
            return None

        # Create a picture container box
        picture_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        picture_box.add(picture)

        # Add the picture box to the container
        self.ghini_box.pack_start(picture_box, False, False, 0)
        picture_box.show_all()

        return picture_box

    def get_widget(self):
        """Returns the main widget (Gtk.Box) containing the pictures."""
        return self.pictures_box


floating_window: Any = None


def show_pictures_callback(selection) -> None:
    """activate a modal window showing plant pictures.

    the current selection defines what pictures should be shown. it
    makes sense for plant, accession and species.

    plants: show the pictures directly associated to them;

    accessions: show all pictures for the plants in the selected
    accessions.

    species: show the voucher.
    """
    if floating_window is not None:
        floating_window.set_selection(selection)
