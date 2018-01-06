# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Brett Adams
# Copyright 2014-2017 Mario Frasca <mario@anche.no>.
# Copyright 2016 Ross Demuth <rossdemuth123@gmail.com>
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

import logging
logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)

import bauble.utils.desktop as desktop



def _open_link(data=None, *args, **kwargs):
    """Open a web link"""
    # windows generates odd characters in the uri unless its in ascii
    logger.debug("_open_link received data=%s, args=%s, kwargs=%s" % (data, args, kwargs))
    import sys
    if sys.platform == 'win32':
        udata = data.decode("utf-8")
        asciidata = udata.encode("ascii", "ignore")
        desktop.open(asciidata)
    else:
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
