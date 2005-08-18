#
# geography plugin
#

import os
from bauble.plugins import plugins, BaublePlugin
from country import Country
from distribution import Continent, Region, Area, State, Place, KewRegion, \
    Distribution

class GeographyPlugin(BaublePlugin):
    
    tables = [Country, Continent, Region, Area, State, Place, KewRegion, \
        Distribution]
    
    @classmethod
    def init(cls):
        if "SearchViewPlugin" in plugins:
            from bauble.plugins.searchview.search import SearchMeta
            from bauble.plugins.searchview.search import ResultsMeta
            from bauble.plugins.searchview.search import SearchView
            
            search_meta = SearchMeta("Country", ["country"], "country")
            SearchView.register_search_meta("country", search_meta)
            
            
    @classmethod
    def create_tables(cls):
        super(GeographyPlugin, cls).create_tables()
        from bauble.plugins.imex_csv import CSVImporter
        csv = CSVImporter()    
        path = os.path.dirname(__file__) + os.sep + 'default'
        #files = ['Country.txt', 'Continent.txt', 'Region.txt', 'Area.txt',
        #          'State.txt', 'Place.txt', 'KewRegion.txt']
        files=['Country.txt']
        csv.start([path+os.sep+f for f in files], True)
        
    

plugin = GeographyPlugin