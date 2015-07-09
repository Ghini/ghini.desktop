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

import bauble.utils.desktop as desktop
from bauble.i18n import _


def _open_link(func, data=None):
    desktop.open(data)

gtk.link_button_set_uri_hook(_open_link)


class StringLinkButton(gtk.LinkButton):

    _base_uri = "%s"
    _space = "_"

    def __init__(self, title=_("Search"), tooltip=None):
        super(StringLinkButton, self).__init__("", title)
        if not tooltip:
            self.set_tooltip_text(title)
        else:
            self.set_tooltip_text(tooltip)

    def set_string(self, search):
        s = str(search)  # just in case an object is passed in
        self.set_uri(self._base_uri % s.replace(' ', self._space))


class KeywordsLinkButton(gtk.LinkButton):

    _base_uri = ""
    _space = "_"

    def __init__(self, title=_("Search"), tooltip=None):
        super(KeywordsLinkButton, self).__init__("", title)
        if not tooltip:
            self.set_tooltip_text(title)
        else:
            self.set_tooltip_text(tooltip)

    def set_string(self, search):
        # s = str(search)  # just in case an object is passed in
        # self.set_uri(self._base_uri % s.replace(' ', self._space))
        # self.set_keywords(s=search)
        raise NotImplementedError

    def set_keywords(self, **kwargs):
        self.set_uri(self._base_uri % kwargs)


class GoogleButton(StringLinkButton):

    _base_uri = "http://www.google.com/search?q=%s"
    _space = '+'

    def __init__(self, title=_("Search Google"), tooltip=None):
        super(GoogleButton, self).__init__(title, tooltip)


class GBIFButton(StringLinkButton):

    _base_uri = "http://www.gbif.org/species/search?q=%s"
    _space = '+'

    def __init__(self, title=_("Search GBIF"), tooltip=_(
            "Search the Global Biodiversity Information Facility")):
        super(GBIFButton, self).__init__(title, tooltip)


class TPLButton(KeywordsLinkButton):

    _base_uri = "http://www.theplantlist.org/tpl1.1/search?" + \
        "q=%(genus)s+%(species)s"
    _space = '+'

    def __init__(self, title=_("Search TPL"), tooltip=_(
            "Search The Plant List online database")):
        super(TPLButton, self).__init__(title, tooltip)


class TropicosButton(KeywordsLinkButton):

    _base_uri = "http://tropicos.org/NameSearch.aspx?" + \
        "name=%(genus)s+%(species)s"
    _space = '+'

    def __init__(self, title=_("Search Tropicos"), tooltip=_(
            "Search Tropicos (MissouriBG) online database")):
        super(TropicosButton, self).__init__(title, tooltip)


class WikipediaButton(KeywordsLinkButton):

    _base_uri = "http://en.wikipedia.org/wiki/%(genus)s_%(species)s"
    _space = '+'

    def __init__(self, title=_("Search the Wikipedia"), tooltip=_(
            "open the wikipedia page about this species")):
        super(WikipediaButton, self).__init__(title, tooltip)


class ITISButton(StringLinkButton):

    _base_uri = "http://www.itis.gov/servlet/SingleRpt/SingleRpt?"\
        "search_topic=Scientific_Name" \
        "&search_value=%s" \
        "&search_kingdom=Plant" \
        "&search_span=containing" \
        "&categories=All&source=html&search_credRating=All"

    _space = '%20'

    def __init__(self, title=_("Search ITIS"), tooltip=_(
            "Search the Intergrated Taxonomic Information System")):
        super(ITISButton, self).__init__(title, tooltip)


class BGCIButton(KeywordsLinkButton):

    _base_uri = "http://www.bgci.org/plant_search.php?action=Find"\
        "&ftrGenus=%(genus)s&ftrRedList=&ftrSpecies=%(species)s"\
        "&ftrRedList1997=&ftrEpithet=&ftrCWR=&x=0&y=0#results"

    _space = ' '

    def __init__(self, title=_("Search BGCI"), tooltip=_(
            "Search Botanic Gardens Conservation International")):
        super(BGCIButton, self).__init__(title, tooltip)


class IPNIButton(KeywordsLinkButton):

    _base_uri = "http://www.ipni.org/ipni/advPlantNameSearch.do?"\
                "find_genus=%(genus)s&find_species=%(species)s" \
                "&find_isAPNIRecord=on& find_isGCIRecord=on" \
                "&find_isIKRecord=on&output_format=normal"

    _space = ' '

    def __init__(self, title=_("Search IPNI"), tooltip=_(
            "Search the International Plant Names Index")):
        super(IPNIButton, self).__init__(title, tooltip)


class GRINButton(StringLinkButton):

    _base_uri = "http://www.ars-grin.gov/cgi-bin/npgs/swish/accboth?"\
                "query=%s&submit=Submit+Text+Query&si=0"
    _space = '+'

    def __init__(self, title=_("Search NPGS/GRIN"),
                 tooltip=_('Search National Plant Germplasm System')):
        super(GRINButton, self).__init__(title, tooltip)
