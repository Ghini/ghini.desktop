#
# SearchView module
#

import sys
import search
from bauble.plugins import BaublePlugin

class SearchViewPlugin(BaublePlugin):
    label = 'Search'
    description = ''
    views = [search.SearchView]

plugin = SearchViewPlugin