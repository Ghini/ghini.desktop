#
# garden plugin
#

import os, sys
import bauble
from bauble.i18n import *
import bauble.utils as utils
import bauble.pluginmgr as pluginmgr
from bauble.view import SearchView
from bauble.plugins.garden.accession import Accession, \
    AccessionEditor, AccessionInfoBox, acc_context_menu, acc_markup_func, \
    SourceInfoBox
from bauble.plugins.garden.location import Location, \
    LocationEditor, LocationInfoBox, loc_context_menu, loc_markup_func
from bauble.plugins.garden.plant import Plant, \
    PlantHistory, PlantEditor, PlantInfoBox, \
    plant_context_menu, plant_markup_func, plant_delimiter_key, \
    default_plant_delimiter, PlantSearch
from bauble.plugins.garden.source import Donation, \
    Collection, source_markup_func
from bauble.plugins.garden.donor import Donor, DonorEditor, \
    DonorInfoBox, donor_context_menu
import bauble.plugins.garden.institution
from bauble.utils.log import debug

# other ideas:
# - cultivation table
# - conservation table

def natsort_kids(kids):
    return lambda(parent): sorted(getattr(parent, kids),key=utils.natsort_key)


class GardenPlugin(pluginmgr.Plugin):

    depends = ["PlantsPlugin"]

    @classmethod
    def install(cls, *args, **kwargs):
        pass


    @classmethod
    def init(cls):
        from bauble.plugins.plants import Species
        mapper_search = SearchView.get_search_strategy('MapperSearch')

        mapper_search.add_meta(('accession', 'acc'), Accession, ['code'])
        SearchView.view_meta[Accession].set(children=natsort_kids("plants"),
                                            infobox=AccessionInfoBox,
                                            context_menu=acc_context_menu,
                                            markup_func=acc_markup_func)

        mapper_search.add_meta(('location', 'loc'), Location, ['site'])
        SearchView.view_meta[Location].set(children=natsort_kids('plants'),
                                           infobox=LocationInfoBox,
                                           context_menu=loc_context_menu,
                                           markup_func=loc_markup_func)

        mapper_search.add_meta(('plant', 'plants'), Plant, ['code'])
        SearchView.add_search_strategy(PlantSearch)
        SearchView.view_meta[Plant].set(infobox=PlantInfoBox,
                                        context_menu=plant_context_menu,
                                        markup_func=plant_markup_func)

        mapper_search.add_meta(('donor', 'don'), Donor, ['name'])
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
        table = meta.BaubleMeta.__table__
        sel = table.select(table.c.name==plant_delimiter_key).execute()
        if sel.fetchone() is None:
            table.insert().execute(name=plant_delimiter_key,
                                   value=default_plant_delimiter)



plugin = GardenPlugin
