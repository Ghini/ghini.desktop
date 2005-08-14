#
# garden plugin 
#

import os, sys
from accession import *
from bauble.plugins import BaublePlugin, plugins, tables
from accession import Accession, AccessionEditor
from location import Location, LocationEditor
from plant import Plant, PlantEditor
from reference import Reference# #ReferenceEditor
from source import Donation, Collection
from source_editor import SourceEditor
from donor import Donor, DonorEditor


class GardenPlugin(BaublePlugin):

    editors = [AccessionEditor, LocationEditor, PlantEditor, DonorEditor, 
               SourceEditor]
            #ReferenceEditor,DonorEditor, SourceEditor]

    tables = [Accession, Location, Plant, Reference, Donor, Donation, Collection]
    
    def init(cls):
        # add joins        
        acc_join = MultipleJoin('Accession', joinMethodName="accession", 
                                joinColumn='plantname_id')    
        tables["Plantname"].sqlmeta.addJoin(acc_join)
        
        if "SearchViewPlugin" in plugins:
            from bauble.plugins.searchview.search import SearchMeta
            from bauble.plugins.searchview.search import ResultsMeta
            from bauble.plugins.searchview.search import SearchView
            search_meta = SearchMeta("Accession", ["acc_id"])
            SearchView.register_search_meta("accession", search_meta)
            SearchView.register_search_meta("acc", search_meta)            
            results_meta = ResultsMeta("plants", "AccessionEditor", None)
            SearchView.register_results_meta("Accession", results_meta)
            
            search_meta = SearchMeta("Location", ["site"])
            SearchView.register_search_meta("location", search_meta)
            SearchView.register_search_meta("loc", search_meta)            
            results_meta = ResultsMeta("plants", "LocationEditor", None)
            SearchView.register_results_meta("Location", results_meta)
    init = classmethod(init)
    
    
    depends = ("PlantsPlugin","GeographyPlugin")

plugin = GardenPlugin