#
# garden plugin 
#

import os, sys
from accession import *
from bauble.plugins import BaublePlugin, plugins, tables
from accession import Accession, AccessionEditor
from location import Location, LocationEditor
from plant import Plant, PlantEditor, PlantInfoBox
from reference import Reference, ReferenceEditor
from source import Donation, Collection
from source_editor import SourceEditor
from donor import Donor, DonorEditor


# other ideas:
# - cultivation table
# - conservation table    

class GardenPlugin(BaublePlugin):

    editors = [AccessionEditor, LocationEditor, PlantEditor, DonorEditor, 
               SourceEditor, ReferenceEditor]
            #ReferenceEditor,DonorEditor, SourceEditor]

    tables = [Accession, Location, Plant, Reference, Donor, Donation, Collection]
    
    @classmethod
    def init(cls):
        # add joins        
        acc_join = MultipleJoin('Accession', joinMethodName="accessions", 
                                joinColumn='plantname_id')    
        tables["Plantname"].sqlmeta.addJoin(acc_join)
        
        if "SearchViewPlugin" in plugins:
            from bauble.plugins.searchview.search import SearchMeta
            from bauble.plugins.searchview.search import ResultsMeta
            from bauble.plugins.searchview.search import SearchView
            
            search_meta = SearchMeta("Accession", ["acc_id"])
            SearchView.register_search_meta("accession", search_meta)
            SearchView.register_search_meta("acc", search_meta)      
            SearchView.view_meta["Accession"].set("plants", AccessionEditor, 
                                                   AccessionInfoBox)
            
            search_meta = SearchMeta("Location", ["site"])
            SearchView.register_search_meta("location", search_meta)
            SearchView.register_search_meta("loc", search_meta)            
            SearchView.view_meta["Location"].set("plants", LocationEditor)

            SearchView.view_meta["Plant"].set(None, PlantEditor, PlantInfoBox)

            # done here b/c the Plantname table is not part of this plugin
            SearchView.view_meta["Plantname"].child = "accessions"
    
    
    depends = ("PlantsPlugin","GeographyPlugin")

plugin = GardenPlugin