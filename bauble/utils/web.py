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
    pt = re.compile(ur'%\(([a-z_]*)\)s')

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
                value = getattr(row, key, '-')
                values[key] = (value == str(value)) and value or ''
            self.set_uri(self._base_uri % values)

    set_keywords = set_string


GoogleButton = type(
    'GoogleButton', (BaubleLinkButton, ),
    {'_base_uri': "http://www.google.com/search?q=%s",
     '_space': '+',
     'title': _("Search Google"),
     'tooltip': None, })


GBIFButton = type(
    'GBIFButton', (BaubleLinkButton, ),
    {'_base_uri': "http://www.gbif.org/species/search?q=%s",
     '_space': '+',
     'title': _("Search GBIF"),
     'tooltip': _("Search the Global Biodiversity Information Facility"), })


TPLButton = type(
    'TPLButton', (BaubleLinkButton, ),
    {'_base_uri': "http://www.theplantlist.org/tpl1.1/search?" +
                  "q=%(genus)s+%(sp)s",
     '_space': '+',
     'title': _("Search TPL"),
     'tooltip': _("Search The Plant List online database"), })


TropicosButton = type(
    'TropicosButton', (BaubleLinkButton, ),
    {'_base_uri': "http://tropicos.org/NameSearch.aspx?" +
        "name=%(genus)s+%(sp)s",
     '_space': '+',
     'title': _("Search Tropicos"),
     'tooltip': _("Search Tropicos (MissouriBG) online database"), })


WikipediaButton = type(
    'WikipediaButton', (BaubleLinkButton, ),
    {'_base_uri': "http://en.wikipedia.org/wiki/%(genus)s_%(sp)s",
     '_space': '+',
     'title': _("Search Wikipedia"),
     'tooltip': _("open the wikipedia page about this species"), })


ITISButton = type(
    'ITISButton', (BaubleLinkButton, ),
    {'_base_uri': "http://www.itis.gov/servlet/SingleRpt/SingleRpt?"
        "search_topic=Scientific_Name"
        "&search_value=%s"
        "&search_kingdom=Plant"
        "&search_span=containing"
        "&categories=All&source=html&search_credRating=All",
     '_space': '%20',
     'title': _("Search ITIS"),
     'tooltip': _("Search the Intergrated Taxonomic Information System"), })


BGCIButton = type(
    'BGCIButton', (BaubleLinkButton, ),
    {'_base_uri': "http://www.bgci.org/plant_search.php?action=Find"
        "&ftrGenus=%(genus)s&ftrRedList=&ftrSpecies=%(sp)s"
        "&ftrRedList1997=&ftrEpithet=&ftrCWR=&x=0&y=0#results",
     '_space': ' ',
     'title': _("Search BGCI"),
     'tooltip': _("Search Botanic Gardens Conservation International"), })


IPNIButton = type(
    'IPNIButton', (BaubleLinkButton, ),
    {'_base_uri': "http://www.ipni.org/ipni/advPlantNameSearch.do?"
        "find_genus=%(genus)s&find_species=%(sp)s&"
        "find_isAPNIRecord=on& find_isGCIRecord=on&"
        "find_isIKRecord=on&output_format=normal",
     '_space': ' ',
     'title': _("Search IPNI"),
     'tooltip': _("Search the International Plant Names Index"), })


GRINButton = type(
    'GRINButton', (BaubleLinkButton, ),
    {'_base_uri': "http://www.ars-grin.gov/cgi-bin/npgs/swish/accboth?"
        "query=%s&submit=Submit+Text+Query&si=0",
     '_space': '+',
     'title': _("Search NPGS/GRIN"),
     'tooltip': _('Search National Plant Germplasm System'), })


ALAButton = type(
    'ALAButton', (BaubleLinkButton, ),
    {'_base_uri': "http://bie.ala.org.au/search?q=%s",
     '_space': '+',
     'title': _("Search ALA"),
     'tooltip': _("Search the Atlas of Living Australia"), })
