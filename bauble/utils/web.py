# -*- coding: utf-8 -*-
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


import gtk
import re

import logging
logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)

import bauble.utils.desktop as desktop
from bauble.i18n import _


def _open_link(func, data=None):
    desktop.open(data)

gtk.link_button_set_uri_hook(_open_link)


class BaubleLinkButton(gtk.LinkButton):

    _base_uri = "%s"
    _space = "_"
    title = _("Search")
    tooltip = None
    pt = re.compile(ur'%\(([a-z_\.]*)\)s')

    def __init__(self, title=_("Search"), tooltip=None):
        super(BaubleLinkButton, self).__init__("", self.title)
        self.set_tooltip_text(self.tooltip or self.title)
        self.__class__.fields = self.pt.findall(self._base_uri)

    def set_string(self, row):
        if self.fields == []:
            s = str(row)
            self.set_uri(self._base_uri % s.replace(' ', self._space))
        else:
            values = {}
            for key in self.fields:
                value = row
                for step in key.split('.'):
                    value = getattr(value, step, '-')
                values[key] = (value == str(value)) and value or ''
            self.set_uri(self._base_uri % values)
