#
# SearchView module
#

import sys
import bauble.pluginmgr as plugin

class SearchViewPlugin(plugin.Plugin):
    label = 'Search'
    description = ''
        
    from bauble.plugins.searchview.search import SearchView
    views = [SearchView]
            
plugin = SearchViewPlugin