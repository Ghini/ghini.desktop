# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Brett Adams
# Copyright 2012-2015 Mario Frasca <mario@anche.no>.
#
# This file is part of ghini.desktop.
#
# ghini.desktop is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ghini.desktop is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ghini.desktop. If not, see <http://www.gnu.org/licenses/>.
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
from gi.repository import Gtk

import logging
logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)

from functools import partial

import bauble
import bauble.db as db
import bauble.paths as paths
import bauble.pluginmgr as pluginmgr
from bauble.plugins.plants.family import (
    Familia, Family, FamilyInfoBox, FamilyEditor, FamilyNote,
    family_context_menu)
from bauble.plugins.plants.genus import (
    Genus, GenusEditor, GenusInfoBox, GenusNote,
    genus_context_menu,
    )
from bauble.plugins.plants.species import (
    Species, SpeciesEditorMenuItem, SpeciesInfoBox, SpeciesNote,
    species_context_menu, add_accession_action,
    SynonymSearch, SpeciesDistribution,
    VernacularName, VernacularNameInfoBox,
    vernname_context_menu,
    )
from bauble.plugins.plants.geography import (
    GeographicArea, get_species_in_geographic_area)
from .taxonomy_check import (
    TaxonomyCheckTool)
from .stored_queries import (
    StoredQueryEditorTool)
import bauble.search as search
from bauble.view import SearchView
from bauble.ui import DefaultView
from bauble import utils


## naming locally unused objects. will be imported by clients of the module
Familia, SpeciesDistribution,

from threading import Thread
from gi.repository import GObject


class LabelUpdater(Thread):
    def __init__(self, widget, query, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.query = query
        self.widget = widget

    def run(self):
        ssn = db.Session()
        value, = ssn.execute(self.query).first()
        GObject.idle_add(lambda x: self.widget.set_text(str(x)), value)
        ssn.close()


class SplashInfoBox(pluginmgr.View):
    '''info box shown in the initial splash screen.

    '''

    def __init__(self):
        '''
        '''
        logger.debug('SplashInfoBox::__init__')
        super().__init__()
        filename = os.path.join(paths.lib_dir(), 'plugins', 'plants',
                                'infoboxes.glade')
        self.widgets = utils.BuilderWidgets(filename)
        self.widgets.remove_parent(self.widgets.splash_vbox)
        self.pack_start(self.widgets.splash_vbox, True, False, 8)

        utils.make_label_clickable(
            self.widgets.splash_nfamuse,
            lambda *a: bauble.gui.send_command(
                'family where genera.species.id != 0'))

        utils.make_label_clickable(
            self.widgets.splash_ngenuse,
            lambda *a: bauble.gui.send_command(
                'genus where species.accessions.id!=0'))

        utils.make_label_clickable(
            self.widgets.splash_nspctot,
            lambda *a: bauble.gui.send_command(
                'species like %'))

        utils.make_label_clickable(
            self.widgets.splash_nspcuse,
            lambda *a: bauble.gui.send_command(
                'species where not accessions = Empty'))

        utils.make_label_clickable(
            self.widgets.splash_nspcnot,
            lambda *a: bauble.gui.send_command(
                'species where accessions = Empty'))

        utils.make_label_clickable(
            self.widgets.splash_nacctot,
            lambda *a: bauble.gui.send_command(
                'accession like %'))

        utils.make_label_clickable(
            self.widgets.splash_naccuse,
            lambda *a: bauble.gui.send_command(
                'accession where sum(plants.quantity)>0'))

        utils.make_label_clickable(
            self.widgets.splash_naccnot,
            lambda *a: bauble.gui.send_command(
                'accession where plants = Empty or sum(plants.quantity)=0'))

        utils.make_label_clickable(
            self.widgets.splash_nplttot,
            lambda *a: bauble.gui.send_command(
                'plant like %'))

        utils.make_label_clickable(
            self.widgets.splash_npltuse,
            lambda *a: bauble.gui.send_command(
                'plant where sum(quantity)>0'))

        utils.make_label_clickable(
            self.widgets.splash_npltnot,
            lambda *a: bauble.gui.send_command(
                'plant where sum(quantity)=0'))

        utils.make_label_clickable(
            self.widgets.splash_nloctot,
            lambda *a: bauble.gui.send_command(
                'location like %'))

        utils.make_label_clickable(
            self.widgets.splash_nlocuse,
            lambda *a: bauble.gui.send_command(
                'location where sum(plants.quantity)>0'))

        utils.make_label_clickable(
            self.widgets.splash_nlocnot,
            lambda *a: bauble.gui.send_command(
                'location where plants is Empty or sum(plants.quantity)=0'))

        for i in range(1, 11):
            wname = "stqr_%02d_button" % i
            widget = getattr(self.widgets, wname)
            widget.connect('clicked', partial(self.on_sqb_clicked, i))
        wname = "splash_stqr_button"
        widget = getattr(self.widgets, wname)
        widget.connect('clicked', self.on_splash_stqr_button_clicked)

    def update(self):
        '''
        '''
        logger.debug('SplashInfoBox::update')
        statusbar = bauble.gui.widgets.statusbar
        sbcontext_id = statusbar.get_context_id('searchview.nresults')
        statusbar.pop(sbcontext_id)
        bauble.gui.widgets.main_comboentry.get_child().set_text('')

        ssn = db.Session()
        q = ssn.query(bauble.meta.BaubleMeta)
        q = q.filter(bauble.meta.BaubleMeta.name.startswith('stqr'))
        name_tooltip_query = dict(
            (int(i.name[5:]), (i.value.split(':', 2)))
            for i in q.all())
        ssn.close()

        for i in range(1, 11):
            wname = "stqr_%02d_button" % i
            widget = getattr(self.widgets, wname)
            name, tooltip, query = name_tooltip_query.get(
                i, (_('<empty>'), '', ''))
            widget.set_label(name)
            widget.set_tooltip_text(tooltip)

        self.name_tooltip_query = name_tooltip_query

        # LabelUpdater objects **can** run in a thread.
        if 'GardenPlugin' in pluginmgr.plugins:
            self.start_thread(
                LabelUpdater(self.widgets.splash_nplttot,
                             "select count(*) from plant"))
            self.start_thread(
                LabelUpdater(self.widgets.splash_npltuse,
                             "select count(*) from plant where quantity>0"))
            self.start_thread(
                LabelUpdater(self.widgets.splash_npltnot,
                             "select count(*) from plant where quantity=0"))
            self.start_thread(
                LabelUpdater(self.widgets.splash_nacctot,
                             "select count(*) from accession"))
            self.start_thread(
                LabelUpdater(self.widgets.splash_naccuse,
                             "select count(distinct accession.id) "
                             "from accession "
                             "join plant on plant.accession_id=accession.id "
                             "where plant.quantity>0"))
            self.start_thread(
                LabelUpdater(self.widgets.splash_naccnot,
                             "select count(id) "
                             "from accession "
                             "where id not in "
                             "(select accession_id from plant "
                             " where plant.quantity>0)"))
            self.start_thread(
                LabelUpdater(self.widgets.splash_nloctot,
                             "select count(*) from location"))
            self.start_thread(
                LabelUpdater(self.widgets.splash_nlocuse,
                             "select count(distinct location.id) "
                             "from location "
                             "join plant on plant.location_id=location.id "
                             "where plant.quantity>0"))
            self.start_thread(
                LabelUpdater(self.widgets.splash_nlocnot,
                             "select count(id) "
                             "from location "
                             "where id not in "
                             "(select location_id from plant "
                             " where plant.quantity>0)"))

        self.start_thread(
            LabelUpdater(self.widgets.splash_nspcuse,
                         "select count(distinct species.id) "
                         "from species join accession "
                         "on accession.species_id=species.id"))
        self.start_thread(
            LabelUpdater(self.widgets.splash_ngenuse,
                         "select count(distinct species.genus_id) "
                         "from species join accession "
                         "on accession.species_id=species.id"))
        self.start_thread(
            LabelUpdater(self.widgets.splash_nfamuse,
                         "select count(distinct genus.family_id) from genus "
                         "join species on species.genus_id=genus.id "
                         "join accession on accession.species_id=species.id "))
        self.start_thread(
            LabelUpdater(self.widgets.splash_nspctot,
                         "select count(*) from species"))
        self.start_thread(
            LabelUpdater(self.widgets.splash_ngentot,
                         "select count(*) from genus"))
        self.start_thread(
            LabelUpdater(self.widgets.splash_nfamtot,
                         "select count(*) from family"))
        self.start_thread(
            LabelUpdater(self.widgets.splash_nspcnot,
                         "select count(id) from species "
                         "where id not in "
                         "(select distinct species.id "
                         " from species join accession "
                         " on accession.species_id=species.id)"))
        self.start_thread(
            LabelUpdater(self.widgets.splash_ngennot,
                         "select count(id) from genus "
                         "where id not in "
                         "(select distinct species.genus_id "
                         " from species join accession "
                         " on accession.species_id=species.id)"))
        self.start_thread(
            LabelUpdater(self.widgets.splash_nfamnot,
                         "select count(id) from family "
                         "where id not in "
                         "(select distinct genus.family_id from genus "
                         "join species on species.genus_id=genus.id "
                         "join accession on accession.species_id=species.id)"))

    def on_sqb_clicked(self, btn_no, *args):
        try:
            query = self.name_tooltip_query[btn_no][2]
            bauble.gui.widgets.main_comboentry.get_child().set_text(query)
            bauble.gui.widgets.go_button.emit("clicked")
        except:
            pass

    def on_splash_stqr_button_clicked(self, *args):
        from .stored_queries import edit_callback
        edit_callback()


class PlantsPlugin(pluginmgr.Plugin):
    tools = [TaxonomyCheckTool, StoredQueryEditorTool]
    provides = {'Family': Family,
                'FamilyNote': FamilyNote,
                'Genus': Genus,
                'GenusNote': GenusNote,
                'Species': Species,
                'SpeciesNote': SpeciesNote,
                'VernacularName': VernacularName,
                'GeographicArea': GeographicArea, }

    @classmethod
    def init(cls):
        pluginmgr.provided.update(cls.provides)
        if 'GardenPlugin' in pluginmgr.plugins:
            species_context_menu.insert(1, add_accession_action)
            vernname_context_menu.insert(1, add_accession_action)

        mapper_search = search.get_strategy('MapperSearch')

        mapper_search.add_meta(('family', 'fam'), Family, ['family'])
        SearchView.row_meta[Family].set(children="genera",
                                        infobox=FamilyInfoBox,
                                        context_menu=family_context_menu)

        mapper_search.add_meta(('genus', 'gen'), Genus, ['genus'])
        SearchView.row_meta[Genus].set(children="species",
                                       infobox=GenusInfoBox,
                                       context_menu=genus_context_menu)

        from functools import partial
        search.add_strategy(SynonymSearch)
        mapper_search.add_meta(('species', 'sp'), Species,
                               ['sp', 'sp2', 'infrasp1', 'infrasp2',
                                'infrasp3', 'infrasp4'])
        SearchView.row_meta[Species].set(
            children=partial(db.natsort, 'accessions'),
            infobox=SpeciesInfoBox,
            context_menu=species_context_menu)

        mapper_search.add_meta(('vernacular', 'vern', 'common'),
                               VernacularName, ['name'])
        SearchView.row_meta[VernacularName].set(
            children=partial(db.natsort, 'species.accessions'),
            infobox=VernacularNameInfoBox,
            context_menu=vernname_context_menu)

        mapper_search.add_meta(('geography', 'geo'), GeographicArea, ['name'])
        SearchView.row_meta[GeographicArea].set(children=get_species_in_geographic_area)

        ## now it's the turn of the DefaultView
        logger.debug('PlantsPlugin::init, registering splash info box')
        DefaultView.infoboxclass = SplashInfoBox

        if bauble.gui is not None:
            bauble.gui.add_to_insert_menu(FamilyEditor, _('Family'))
            bauble.gui.add_to_insert_menu(GenusEditor, _('Genus'))
            bauble.gui.add_to_insert_menu(SpeciesEditorMenuItem, _('Species'))

        # suggest some useful defaults for stored queries
        import bauble.meta as meta
        session = db.Session()
        default = 'false'
        q = session.query(bauble.meta.BaubleMeta).filter(bauble.meta.BaubleMeta.name.startswith('stqr-'))
        for i in q.all():
            default = i.name
            session.delete(i)
            session.commit()
        init_marker = meta.get_default('stqv_initialized', default, session)
        if init_marker.value == 'false':
            init_marker.value = 'true'
            for index, name, tooltip, query in [
                    (9, _('history'), _('the history in this database'), ':history'),
                    (10, _('preferences'), _('your user preferences'), ':prefs')]:
                meta.get_default('stqr_%02d' % index,
                                 "%s:%s:%s" % (name, tooltip, query),
                                 session)
            session.commit()
        session.close()

    @classmethod
    def install(cls, import_defaults=True):
        """
        Do any setup and configuration required by this plugin like
        creating tables, etc...
        """
        if not import_defaults:
            return
        path = os.path.join(paths.lib_dir(), "plugins", "plants", "default")
        filenames = [os.path.join(path, f) for f in ('family.txt',
                     'family_synonym.txt',
                     'genus.txt', 'genus_synonym.txt', 'geographic_area.txt',
                     'habit.txt')]

        from bauble.plugins.imex.csv_ import CSVImporter
        csv = CSVImporter()
        csv.start(filenames, metadata=db.metadata, force=True)


plugin = PlantsPlugin
