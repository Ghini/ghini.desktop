#
# geography plugin
#

import os
import bauble.paths as paths
from bauble.plugins import plugins, BaublePlugin
from country import Country
from distribution import Continent, Region, Area, State, Place, KewRegion, \
    Distribution, BotanicalCountry, BasicUnit
from bauble.utils.log import log, debug


class GeographyPlugin(BaublePlugin):
    
#    tables = [Country, Continent, Region, Area, State, Place, KewRegion, \
#        Distribution]
    #editors = [DistributionEditor]
    tables = [Country, Continent, Region, BotanicalCountry, BasicUnit, Place]#, \
#        Distribution]
    
    @classmethod
    def init(cls):
        if "SearchViewPlugin" in plugins:
            from bauble.plugins.searchview.search import SearchMeta
            from bauble.plugins.searchview.search import ResultsMeta
            from bauble.plugins.searchview.search import SearchView
            
            search_meta = SearchMeta("Country", ["country"], "country")
            SearchView.register_search_meta("country", search_meta)
            
            search_meta = SearchMeta("Continent", ["continent"], "continent")
            SearchView.register_search_meta("continent", search_meta)
            
            search_meta = SearchMeta("Region", ["region"], "region")
            SearchView.register_search_meta("region", search_meta)
            
#            search_meta = SearchMeta("Area", ["area"], "area")
#            SearchView.register_search_meta("area", search_meta)
#                                
#            search_meta = SearchMeta("State", ["state"], "state")
#            SearchView.register_search_meta("state", search_meta)
            
            search_meta = SearchMeta("BotanicalCountry", ["name"], "name")
            SearchView.register_search_meta("bot_country", search_meta)
                                
            search_meta = SearchMeta("BasicUnit", ["name"], "name")
            SearchView.register_search_meta("basic", search_meta)
            
            search_meta = SearchMeta("Place", ["place"], "place")
            SearchView.register_search_meta("place", search_meta)
            
#            search_meta = SearchMeta("KewRegion", ["region"], "region")
#            SearchView.register_search_meta("kewregion", search_meta)
                        
            
    @classmethod
    def create_tables(cls):
        super(GeographyPlugin, cls).create_tables()
        from bauble.plugins.imex_csv import CSVImporter
        csv = CSVImporter()        
        #path = os.path.dirname(__file__) + os.sep + 'default'
        path = os.path.join(paths.lib_dir(), "plugins", "geography", "default")
        files = ['Country.txt', 'Continent.txt', 'Region.txt', 
                 'BotanicalCountry.txt', 'BasicUnit.txt', 'Place.txt']

        csv.start([path+os.sep+f for f in files])

        
    

plugin = GeographyPlugin