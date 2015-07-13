# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Brett Adams
# Copyright 2012-2015 Mario Frasca <mario@anche.no>.
#
# This file is part of bauble.classic.
#
# bauble.classic is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# bauble.classic is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bauble.classic. If not, see <http://www.gnu.org/licenses/>.
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
import sys

import bauble
import bauble.db as db
import bauble.paths as paths
import bauble.pluginmgr as pluginmgr
from bauble.plugins.plants.family import (
    Familia, Family, FamilyInfoBox, FamilyEditor,
    family_context_menu, family_markup_func)
from bauble.plugins.plants.genus import (
    Genus, GenusEditor, GenusInfoBox,
    genus_context_menu, genus_markup_func,
    )
from bauble.plugins.plants.species import (
    Species, SpeciesEditor, SpeciesInfoBox,
    species_get_kids, species_markup_func,
    species_context_menu, add_accession_action,
    SynonymSearch, SpeciesDistribution,
    VernacularName, VernacularNameInfoBox, vernname_get_kids,
    vernname_context_menu, vernname_markup_func,
    )
from bauble.plugins.plants.geography import (
    Geography, get_species_in_geography)
import bauble.search as search
from bauble.view import SearchView
from bauble.i18n import _

## naming locally unused objects. will be imported by clients of the module
Familia, SpeciesDistribution,


class PlantsPlugin(pluginmgr.Plugin):

    @classmethod
    def init(cls):
        if 'GardenPlugin' in pluginmgr.plugins:
            species_context_menu.insert(1, add_accession_action)
            vernname_context_menu.insert(1, add_accession_action)

        mapper_search = search.get_strategy('MapperSearch')

        mapper_search.add_meta(('family', 'fam'), Family, ['family'])
        SearchView.view_meta[Family].set(children="genera",
                                         infobox=FamilyInfoBox,
                                         context_menu=family_context_menu,
                                         markup_func=family_markup_func)

        mapper_search.add_meta(('genus', 'gen'), Genus, ['genus'])
        SearchView.view_meta[Genus].set(children="species",
                                        infobox=GenusInfoBox,
                                        context_menu=genus_context_menu,
                                        markup_func=genus_markup_func)

        search.add_strategy(SynonymSearch)
        mapper_search.add_meta(('species', 'sp'), Species,
                               ['sp', 'sp2', 'infrasp1', 'infrasp2',
                                'infrasp3', 'infrasp4',
                                ((Genus, 'genus'), 'sp')])
        SearchView.view_meta[Species].set(children=species_get_kids,
                                          infobox=SpeciesInfoBox,
                                          context_menu=species_context_menu,
                                          markup_func=species_markup_func)

        mapper_search.add_meta(('vernacular', 'vern', 'common'),
                               VernacularName, ['name'])
        SearchView.view_meta[VernacularName].set(
            children=vernname_get_kids,
            infobox=VernacularNameInfoBox,
            context_menu=vernname_context_menu,
            markup_func=vernname_markup_func)

        mapper_search.add_meta(('geography', 'geo'), Geography, ['name'])
        SearchView.view_meta[Geography].set(children=get_species_in_geography)

        if bauble.gui is not None:
            bauble.gui.add_to_insert_menu(FamilyEditor, _('Family'))
            bauble.gui.add_to_insert_menu(GenusEditor, _('Genus'))
            bauble.gui.add_to_insert_menu(SpeciesEditor, _('Species'))

        if sys.platform == 'win32':
            # TODO: for some reason using the cross as the hybrid
            # character doesn't work on windows
            Species.hybrid_char = 'x'

    @classmethod
    def install(cls, import_defaults=True):
        """
        Do any setup and configuration required by this plugin like
        creating tables, etc...
        """
        if not import_defaults:
            return
        path = os.path.join(paths.lib_dir(), "plugins", "plants", "default")
        filenames = [os.path.join(path, f) for f in 'family.txt',
                     'genus.txt', 'genus_synonym.txt', 'geography.txt',
                     'habit.txt']

        from bauble.plugins.imex.csv_ import CSVImporter
        csv = CSVImporter()
        #import_error = False
        #import_exc = None
        csv.start(filenames, metadata=db.metadata, force=True)


plugin = PlantsPlugin
