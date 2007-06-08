#
# garden plugin
#

import os, sys
import bauble
from bauble.i18n import *
import bauble.utils as utils
import bauble.pluginmgr as pluginmgr
from bauble.view import SearchView, SearchMeta
from bauble.plugins.garden.accession import accession_table, Accession, \
    AccessionEditor, AccessionInfoBox, acc_context_menu, acc_markup_func, \
    SourceInfoBox
from bauble.plugins.garden.location import location_table, Location, \
    LocationEditor, LocationInfoBox, loc_context_menu, loc_markup_func
from bauble.plugins.garden.plant import plant_table, Plant, \
    plant_history_table, PlantHistory, PlantEditor, PlantInfoBox, \
    plant_context_menu, plant_markup_func, plant_delimiter_key, \
    default_plant_delimiter
from bauble.plugins.garden.source import donation_table, Donation, \
    collection_table, Collection, source_markup_func
from bauble.plugins.garden.donor import donor_table, Donor, DonorEditor, \
    DonorInfoBox, donor_context_menu
import bauble.plugins.garden.institution
from bauble.utils.log import debug

# other ideas:
# - cultivation table
# - conservation table

def natsort_kids(kids):
    return lambda(parent): sorted(getattr(parent, kids),key=utils.natsort_key)



class GardenPlugin(pluginmgr.Plugin):

    tables = [accession_table, location_table, plant_table, donor_table,
              donation_table, collection_table, plant_history_table]


    @classmethod
    def init(cls):
        from bauble.plugins.plants import Species
        search_meta = SearchMeta(Accession, ["code"])
        SearchView.register_search_meta("accession", search_meta)
        SearchView.register_search_meta("acc", search_meta)
        SearchView.view_meta[Accession].set(children=natsort_kids("plants"),
                                            infobox=AccessionInfoBox,
                                            context_menu=acc_context_menu,
                                            markup_func=acc_markup_func)
        search_meta = SearchMeta(Location, ["site"])
        SearchView.register_search_meta("location", search_meta)
        SearchView.register_search_meta("loc", search_meta)
        SearchView.view_meta[Location].set(children=natsort_kids('plants'),
                                           infobox=LocationInfoBox,
                                           context_menu=loc_context_menu,
                                           markup_func=loc_markup_func)
        search_meta = SearchMeta(Plant, ["code"])
        SearchView.register_search_meta('plant', search_meta)
        SearchView.view_meta[Plant].set(infobox=PlantInfoBox,
                                        context_menu=plant_context_menu,
                                        markup_func=plant_markup_func)

        search_meta = SearchMeta(Donor, ['name'])
        SearchView.register_search_meta('donor', search_meta)
        SearchView.register_search_meta('don', search_meta)
        SearchView.view_meta[Donor].set(children=natsort_kids('donations'),
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


        # if the plant delimiter isn't in the bauble meta then add the default
        import bauble.meta as meta
        table = meta.bauble_meta_table
        row = table.select(table.c.name==plant_delimiter_key).execute().fetchone()
        if row is None:
            table.insert().execute(name=plant_delimiter_key,
                                   value=default_plant_delimiter)


    depends = ["PlantsPlugin"]

plugin = GardenPlugin
