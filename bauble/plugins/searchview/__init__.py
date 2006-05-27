#
# SearchView module
#

import sys
from bauble.plugins import BaublePlugin, plugins

class SearchViewPlugin(BaublePlugin):
    label = 'Search'
    description = ''    
        
    from bauble.plugins.searchview.search import SearchView
    views = [SearchView]
            
plugin = SearchViewPlugin