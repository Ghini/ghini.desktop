#
# garden plugin 
#

import os, sys
import bauble
from bauble.i18n import *
import bauble.pluginmgr as pluginmgr
from bauble.view import SearchView, SearchMeta
from bauble.plugins.garden.accession import accession_table, Accession, \
    AccessionEditor, AccessionInfoBox, acc_context_menu, acc_markup_func, \
    SourceInfoBox
from bauble.plugins.garden.location import location_table, Location, \
    LocationEditor, LocationInfoBox, loc_context_menu, loc_markup_func
from bauble.plugins.garden.plant import plant_table, Plant, \
    plant_history_table, PlantHistory, PlantEditor, PlantInfoBox, \
    plant_context_menu, plant_markup_func
#from reference import Reference, ReferenceEditor
from bauble.plugins.garden.source import donation_table, Donation, \
    collection_table, Collection, source_markup_func
from bauble.plugins.garden.donor import donor_table, Donor, DonorEditor, \
    DonorInfoBox, donor_context_menu

# other ideas:
# - cultivation table
# - conservation table

class GardenPlugin(pluginmgr.Plugin):

    tables = [accession_table, location_table, plant_table, donor_table,
              donation_table, collection_table, plant_history_table]
    
    @classmethod
    def init(cls):
        from bauble.plugins.plants import Species
        search_meta = SearchMeta(Accession, ["code"], "code")
        SearchView.register_search_meta("accession", search_meta)
        SearchView.register_search_meta("acc", search_meta)      
        SearchView.view_meta[Accession].set(children="plants",
                                            infobox=AccessionInfoBox,
                                            context_menu=acc_context_menu,
                                            markup_func=acc_markup_func)
        search_meta = SearchMeta(Location, ["site"], "site")
        SearchView.register_search_meta("location", search_meta)
        SearchView.register_search_meta("loc", search_meta)            
        SearchView.view_meta[Location].set(children="plants",
                                           infobox=LocationInfoBox,
                                           context_menu=loc_context_menu,
                                           markup_func=loc_markup_func)        
        search_meta = SearchMeta(Plant, ["code"], "code")
        SearchView.register_search_meta('plant', search_meta)
        SearchView.view_meta[Plant].set(infobox=PlantInfoBox,
                                        context_menu=plant_context_menu,
                                        markup_func=plant_markup_func)
            
        search_meta = SearchMeta(Donor, ['name'])
        SearchView.register_search_meta('donor', search_meta)
        SearchView.register_search_meta('don', search_meta)
        SearchView.view_meta[Donor].set(children="donations", 
                                        infobox=DonorInfoBox,
                                        context_menu=donor_context_menu)
        
        SearchView.view_meta[Donation].set(infobox=SourceInfoBox,
                                           markup_func=source_markup_func)
        SearchView.view_meta[Collection].set(infobox=SourceInfoBox,
                                             markup_func=source_markup_func)

        # done here b/c the Species table is not part of this plugin
        SearchView.view_meta[Species].child = "accessions"

        if bauble.gui is not None:
            bauble.gui.add_to_insert_menu(AccessionEditor, _('Accession'))
            bauble.gui.add_to_insert_menu(PlantEditor, _('Plant'))
            bauble.gui.add_to_insert_menu(LocationEditor, _('Location'))
            #bauble.gui.add_to_insert_menu(DonorEditor, _('Donor'))
    
    
    depends = ["PlantsPlugin"]

plugin = GardenPlugin
