#
# geography plugin
#

import os
import bauble.paths as paths
from bauble.plugins import plugins, BaublePlugin
from bauble.plugins.geography.country import Country
from bauble.plugins.geography.distribution import Continent, Region, Area, \
    State, Place, KewRegion, BotanicalCountry, BasicUnit, region_markup_func,\
    botanicalcountry_markup_func, basicunit_markup_func, place_markup_func
from bauble.utils.log import log, debug


class GeographyPlugin(BaublePlugin):
    
    tables = [Country, Continent, Region, BotanicalCountry, BasicUnit, Place]#, \
    
    @classmethod
    def init(cls):
        if "SearchViewPlugin" in plugins:
            from bauble.plugins.searchview.search import SearchMeta
            from bauble.plugins.searchview.search import SearchView
            
            search_meta = SearchMeta("Country", ["country"], "country")
            SearchView.register_search_meta("country", search_meta)
            
            search_meta = SearchMeta("Continent", ["continent"], "continent")
            SearchView.register_search_meta("continent", search_meta)                    

            search_meta = SearchMeta("Region", ["region"], "region")
            SearchView.register_search_meta("region", search_meta)
            SearchView.view_meta["Region"].set(markup_func=region_markup_func)
            
#            search_meta = SearchMeta("Area", ["area"], "area")
#            SearchView.register_search_meta("area", search_meta)
#                                
#            search_meta = SearchMeta("State", ["state"], "state")
#            SearchView.register_search_meta("state", search_meta)

            search_meta = SearchMeta("BotanicalCountry", ["name"], "name")
            SearchView.register_search_meta("bot_country", search_meta)
            SearchView.view_meta["BotanicalCountry"].set(botanicalcountry_markup_func)
                                            
            search_meta = SearchMeta("BasicUnit", ["name"], "name")
            SearchView.register_search_meta("basic", search_meta)
            SearchView.view_meta["BasicUnit"].set(markup_func=basicunit_markup_func)        
            
            search_meta = SearchMeta("Place", ["place"], "place")
            SearchView.register_search_meta("place", search_meta)
            SearchView.view_meta["Place"].set(place_markup_func)
            
#            search_meta = SearchMeta("KewRegion", ["region"], "region")
#            SearchView.register_search_meta("kewregion", search_meta)
                        
            
    @classmethod
    def create_tables(cls):
        super(GeographyPlugin, cls).create_tables()

    @staticmethod
    def default_filenames():
        path = os.path.join(paths.lib_dir(), "plugins", "geography", "default")
        files = ['country.txt', 'continent.txt', 'region.txt', 
                 'botanical_country.txt', 'basic_unit.txt', 'place.txt']        
        return [os.path.join(path, f) for f in files]
        
    

plugin = GeographyPlugin