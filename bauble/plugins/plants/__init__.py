#
# plant plugin
#

# TODO: there is going to be problem with the accessions MultipleJoin
# in Species, plants should really have to depend on garden unless
# plants is contained within garden, but what about herbaria, they would
# also need to depend on plants, what we could do is have another class
# with the same name as the other table that defines new columns/joins
# for that class or probably not add new columns but add new joins 
# dynamically

# TODO: should create the table the first time this plugin is loaded, if a new 
# database is created there should be a way to recreate everything from scratch

import os
import bauble
from bauble.i18n import *
import bauble.utils as utils
import bauble.paths as paths
import bauble.pluginmgr as pluginmgr
from bauble.plugins.plants.family import *
from bauble.plugins.plants.genus import *
from bauble.plugins.plants.species import *
from bauble.plugins.plants.geography import *
from bauble.view import SearchView, SearchMeta


class PlantsPlugin(pluginmgr.Plugin):
    
    tables = [family_table, family_synonym_table, genus_table, 
              genus_synonym_table, species_table, species_synonym_table, 
              vernacular_name_table, geography_table]
    
    @classmethod
    def init(cls):            
        search_meta = SearchMeta(Family, ["family"], "family")
        SearchView.register_search_meta("family", search_meta)
        SearchView.register_search_meta("fam", search_meta)            
        SearchView.view_meta[Family].set(children="genera",
                                         infobox=FamilyInfoBox,
                                         context_menu=family_context_menu,
                                         markup_func=family_markup_func)
        
        search_meta = SearchMeta(Genus, ["genus"], "genus")
        SearchView.register_search_meta("genus", search_meta)
        SearchView.register_search_meta("gen", search_meta)
        SearchView.view_meta[Genus].set(children="species", 
                                        infobox=GenusInfoBox,
                                        context_menu=genus_context_menu,
                                        markup_func=genus_markup_func)
        
        search_meta = SearchMeta(Species, ["sp", "infrasp"], "sp")
        SearchView.register_search_meta("species", search_meta)
        SearchView.register_search_meta("sp", search_meta)
        SearchView.view_meta[Species].set(children='accessions',
                                          infobox=SpeciesInfoBox,
                                          context_menu=species_context_menu,
                                          markup_func=species_markup_func)
                                                        
        search_meta = SearchMeta(VernacularName, ['name'], "name")
        SearchView.register_search_meta("vernacular", search_meta)
        SearchView.register_search_meta("vern", search_meta)
        SearchView.register_search_meta("common", search_meta)
        SearchView.view_meta[VernacularName].set(children=vernname_get_children,
                                                 infobox=VernacularNameInfoBox,
                                                 context_menu=vernname_context_menu,
                                                 markup_func=vernname_markup_func)
        # TODO: this needs some work, what should we be able to do
        # when a vernacular name is returned, should we just return the 
        # species
        # TODO: for the infobox somehow we need to show the species infobox
##         SearchView.view_meta["VernacularName"].set(context_menu=vern_context_menu, 
##                                                    markup_func=vern_markup_func)        
        bauble.gui.add_to_insert_menu(SpeciesEditor, _('Species'))
        bauble.gui.add_to_insert_menu(GenusEditor, _('Genus'))
        bauble.gui.add_to_insert_menu(FamilyEditor, _('Family'))
        
            
            
    @classmethod
    def create_tables(cls):
        super(PlantsPlugin, cls).create_tables()


    @staticmethod
    def default_filenames():
        path = os.path.join(paths.lib_dir(), "plugins", "plants", "default")
        files = ['family.txt', 'family_synonym.txt', 'genus.txt',
                 'genus_synonym.txt', 'geography.txt']
        return [os.path.join(path, f) for f in files]


    def install(cls):
        """
        do any setup and configuration required bt this plugin like
        creating tables, etc...
        """
        cls.create_tables()
        
plugin = PlantsPlugin
