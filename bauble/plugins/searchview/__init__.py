#
# SearchView module
#

import sys
from bauble.plugins import BaublePlugin, plugins

class SearchViewPlugin(BaublePlugin):
    label = 'Search'
    description = ''    
    
    def init(cls):
        print "SearchViewPlugin.init()"
    init = classmethod(init)
    
    from search import SearchView
    views = [SearchView]
            
plugin = SearchViewPlugin