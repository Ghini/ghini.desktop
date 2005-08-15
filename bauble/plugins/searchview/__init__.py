#
# SearchView module
#

import sys
from bauble.plugins import BaublePlugin, plugins

class SearchViewPlugin(BaublePlugin):
    label = 'Search'
    description = ''    
        
    from search import SearchView
    views = [SearchView]
            
plugin = SearchViewPlugin