# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Brett Adams
# Copyright 2012-2015 Mario Frasca <mario@anche.no>.
# Copyright 2017 Jardín Botánico de Quito
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

import gtk

import logging
logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)

import os
import traceback

from sqlalchemy.orm.session import object_session

import bauble
import bauble.paths as paths
import bauble.db as db

import bauble.pluginmgr as pluginmgr
from bauble.prefs import prefs
import bauble.utils as utils
from bauble.plugins.plants.species_editor import (
    SpeciesDistribution, SpeciesEditorPresenter, SpeciesEditorView,
    SpeciesEditorMenuItem, edit_species)
from bauble.plugins.plants.species_model import (
    Species, SpeciesNote, VernacularName, SpeciesSynonym,
    DefaultVernacularName)
import bauble.search as search
from bauble.view import PropertiesExpander, Action
import bauble.view as view

SpeciesDistribution  # will be imported by clients of this module
SpeciesEditorPresenter, SpeciesEditorView, SpeciesEditorMenuItem, edit_species,
DefaultVernacularName
SpeciesNote

# TODO: we need to make sure that this will still work if the
# AccessionPlugin is not present, this means that we would have to
# change the species context menu, getting the children from the
# search view and what else


def edit_callback(values):
    from bauble.plugins.plants.species_editor import edit_species
    sp = values[0]
    if isinstance(sp, VernacularName):
        sp = sp.species
    return edit_species(model=sp) is not None


def remove_callback(values):
    """
    The callback function to remove a species from the species context menu.
    """
    from bauble.plugins.garden.accession import Accession
    species = values[0]
    session = object_session(species)
    if isinstance(species, VernacularName):
        species = species.species
    nacc = session.query(Accession).filter_by(species_id=species.id).count()
    safe_str = utils.xml_safe(str(species))
    if nacc > 0:
        msg = (_('The species <i>%(1)s</i> has %(2)s accessions.'
                 '\n\n') % {'1': safe_str, '2': nacc} +
               _('You cannot remove a species with accessions.'))
        utils.message_dialog(msg, type=gtk.MESSAGE_WARNING)
        return
    else:
        msg = _("Are you sure you want to remove the species <i>%s</i>?") \
            % safe_str
    if not utils.yes_no_dialog(msg):
        return
    try:
        obj = session.query(Species).get(species.id)
        session.delete(obj)
        session.commit()
    except Exception, e:
        msg = _('Could not delete.\n\n%s') % utils.xml_safe(e)
        utils.message_details_dialog(msg, traceback.format_exc(),
                                     type=gtk.MESSAGE_ERROR)
    return True


def add_accession_callback(values):
    from bauble.plugins.garden.accession import Accession, AccessionEditor
    session = db.Session()
    species = session.merge(values[0])
    if isinstance(species, VernacularName):
        species = species.species
    e = AccessionEditor(model=Accession(species=species))
    session.close()
    return e.start() is not None


edit_action = Action('species_edit', _('_Edit'),
                     callback=edit_callback,
                     accelerator='<ctrl>e')
add_accession_action = Action('species_acc_add', _('_Add accession'),
                              callback=add_accession_callback,
                              accelerator='<ctrl>k')
remove_action = Action('species_remove', _('_Delete'),
                       callback=remove_callback,
                       accelerator='<ctrl>Delete', multiselect=True)

species_context_menu = [edit_action, remove_action]
vernname_context_menu = [edit_action]


from bauble.view import InfoBox, InfoBoxPage, InfoExpander, \
    select_in_search_results


class SynonymSearch(search.SearchStrategy):
    """
    Return any synonyms for matching species.

    bauble.search.return_synonyms in the prefs toggles this.
    """
    return_synonyms_pref = 'bauble.search.return_synonyms'

    def __init__(self):
        super(SynonymSearch, self).__init__()
        if self.return_synonyms_pref not in prefs:
            prefs[self.return_synonyms_pref] = True
            prefs.save()

    def search(self, text, session):
        from genus import Genus, GenusSynonym
        super(SynonymSearch, self).search(text, session)
        if not prefs[self.return_synonyms_pref]:
            return []
        mapper_search = search.get_strategy('MapperSearch')
        r1 = mapper_search.search(text, session)
        if not r1:
            return []
        results = []
        for result in r1:
            # iterate through the results and for all objects considered
            # synonym of something else, include that something else. that
            # is, the accepted name.
            if isinstance(result, Species):
                q = session.query(SpeciesSynonym).\
                    filter_by(synonym_id=result.id)
                results.extend([syn.species for syn in q])
            elif isinstance(result, Genus):
                q = session.query(GenusSynonym).\
                    filter_by(synonym_id=result.id)
                results.extend([syn.genus for syn in q])
            elif isinstance(results, VernacularName):
                q = session.query(SpeciesSynonym).\
                    filter_by(synonym_id=result.species.id)
                results.extend([syn.species for syn in q])
        return results


#
# Species infobox for SearchView
#
class VernacularExpander(InfoExpander):
    '''
    VernacularExpander

    :param widgets:
    '''
    def __init__(self, widgets):
        InfoExpander.__init__(self, _("Vernacular names"), widgets)
        vernacular_box = self.widgets.sp_vernacular_box
        self.widgets.remove_parent(vernacular_box)
        self.vbox.pack_start(vernacular_box)

    def update(self, row):
        '''
        update the expander

        :param row: the row to get thevalues from
        '''
        if len(row.vernacular_names) == 0:
            self.set_sensitive(False)
            self.set_expanded(False)
        else:
            names = []
            for vn in row.vernacular_names:
                if row.default_vernacular_name is not None \
                        and vn == row.default_vernacular_name:
                    names.insert(0, '%s - %s (default)' %
                                 (vn.name, vn.language))
                else:
                    names.append('%s - %s' %
                                 (vn.name, vn.language))
            self.widget_set_value('sp_vernacular_data', '\n'.join(names))
            self.set_sensitive(True)
            # TODO: get expanded state from prefs
            self.set_expanded(True)


class SynonymsExpander(InfoExpander):

    def __init__(self, widgets):
        InfoExpander.__init__(self, _("Synonyms"), widgets)
        synonyms_box = self.widgets.sp_synonyms_box
        self.widgets.remove_parent(synonyms_box)
        self.vbox.pack_start(synonyms_box)

    def update(self, row):
        '''
        update the expander

        :param row: the row to get thevalues from
        '''
        syn_box = self.widgets.sp_synonyms_box
        # remove old labels
        syn_box.foreach(syn_box.remove)
        logger.debug(row.synonyms)
        session = object_session(row)
        syn = session.query(SpeciesSynonym).filter(
            SpeciesSynonym.synonym_id == row.id).first()
        accepted = syn and syn.species
        logger.debug("species %s is synonym of %s and has synonyms %s" %
                     (row, accepted, row.synonyms))
        self.set_label(_("Synonyms"))  # reset default value
        on_label_clicked = lambda l, e, syn: select_in_search_results(syn)
        if accepted is not None:
            self.set_label(_("Accepted name"))
            # create clickable label that will select the synonym
            # in the search results
            box = gtk.EventBox()
            label = gtk.Label()
            label.set_alignment(0, .5)
            label.set_markup(accepted.str(markup=True, authors=True))
            box.add(label)
            utils.make_label_clickable(label, on_label_clicked, accepted)
            syn_box.pack_start(box, expand=False, fill=False)
            self.show_all()
            self.set_sensitive(True)
            self.set_expanded(True)
        elif len(row.synonyms) == 0:
            self.set_sensitive(False)
            self.set_expanded(False)
        else:
            # remove all the children
            syn_box.foreach(syn_box.remove)
            for syn in row.synonyms:
                # create clickable label that will select the synonym
                # in the search results
                box = gtk.EventBox()
                label = gtk.Label()
                label.set_alignment(0, .5)
                label.set_markup(syn.str(markup=True, authors=True))
                box.add(label)
                utils.make_label_clickable(label, on_label_clicked, syn)
                syn_box.pack_start(box, expand=False, fill=False)
            self.show_all()
            self.set_sensitive(True)
            # TODO: get expanded state from prefs
            self.set_expanded(True)


class GeneralSpeciesExpander(InfoExpander):
    '''
    expander to present general information about a species
    '''

    def __init__(self, widgets):
        '''
        the constructor
        '''
        InfoExpander.__init__(self, _("General"), widgets)
        general_box = self.widgets.sp_general_box
        self.widgets.remove_parent(general_box)
        self.vbox.pack_start(general_box)
        self.widgets.sp_epithet_data.set_line_wrap(True)

        # make the check buttons read only
        def on_enter(button, *args):
            button.emit_stop_by_name("enter-notify-event")
            return True

        self.current_obj = None

        def on_nacc_clicked(*args):
            cmd = 'accession where species.id=%s' % self.current_obj.id
            bauble.gui.send_command(cmd)

        utils.make_label_clickable(self.widgets.sp_nacc_data,
                                   on_nacc_clicked)

        def on_nplants_clicked(*args):
            cmd = 'plant where accession.species.id=%s' % self.current_obj.id
            bauble.gui.send_command(cmd)
        utils.make_label_clickable(self.widgets.sp_nplants_data,
                                   on_nplants_clicked)

    def update(self, row):
        '''
        update the expander

        :param row: the row to get the values from
        '''
        self.current_obj = row
        session = object_session(row)
        # link function
        on_label_clicked = lambda l, e, x: select_in_search_results(x)
        # Link to family
        self.widget_set_value('sp_fam_data', '<small>(%s)</small>' %
                              row.genus.family.family, markup=True)
        utils.make_label_clickable(
            self.widgets.sp_fam_data, on_label_clicked, row.genus.family)
        # link to genus
        self.widget_set_value('sp_gen_data', '<big><i>%s</i></big>' %
                              row.genus.genus, markup=True)
        utils.make_label_clickable(
            self.widgets.sp_gen_data, on_label_clicked, row.genus)
        # epithet (full binomial but missing genus)
        self.widget_set_value('sp_epithet_data', '<big>%s</big>' %
                              row.markup(authors=True, genus=False),
                              markup=True)

        awards = ''
        if row.awards:
            awards = utils.utf8(row.awards)
        self.widget_set_value('sp_awards_data', awards)

        logger.debug('setting cites data from row %s' % row)
        cites = ''
        if row.cites:
            cites = utils.utf8(row.cites)
        self.widget_set_value('sp_cites_data', cites)

        # zone = ''
        # if row.hardiness_zone:
        #     awards = utils.utf8(row.hardiness_zone)
        # self.widget_set_value('sp_hardiness_data', zone)

        habit = ''
        if row.habit:
            habit = utils.utf8(row.habit)
        self.widget_set_value('sp_habit_data', habit)

        dist = ''
        if row.distribution:
            dist = utils.utf8(row.distribution_str())
        self.widget_set_value('sp_dist_data', dist)

        dist = ''
        if row.label_distribution:
            dist = row.label_distribution
        self.widget_set_value('sp_labeldist_data', dist)

        # stop here if not GardenPluin
        if 'GardenPlugin' not in pluginmgr.plugins:
            return

        from bauble.plugins.garden.accession import Accession
        from bauble.plugins.garden.plant import Plant

        nacc = session.query(Accession).join('species').\
            filter_by(id=row.id).count()
        self.widget_set_value('sp_nacc_data', nacc)

        nplants = session.query(Plant).join('accession', 'species').\
            filter_by(id=row.id).count()
        if nplants == 0:
            self.widget_set_value('sp_nplants_data', nplants)
        else:
            nacc_in_plants = session.query(Plant.accession_id).\
                join('accession', 'species').\
                filter_by(id=row.id).distinct().count()
            self.widget_set_value('sp_nplants_data', '%s in %s accessions'
                                  % (nplants, nacc_in_plants))

        living_plants = sum(i.quantity for i in session.query(Plant).join('accession', 'species').\
                            filter_by(id=row.id).all())
        self.widget_set_value('living_plants_count', living_plants)


class SpeciesInfoBox(InfoBox):

    def __init__(self):
        super(SpeciesInfoBox, self).__init__(tabbed=True)
        page = SpeciesInfoPage()
        label = page.label
        if isinstance(label, basestring):
            label = gtk.Label(label)
        self.insert_page(page, label, 0)


class SpeciesInfoPage(InfoBoxPage):
    '''
    general info, fullname, common name, num of accessions and clones,
    distribution
    '''

    # others to consider: reference, images, redlist status

    def __init__(self):
        '''
        the constructor
        '''
        button_defs = [
            {'name': 'GoogleButton', '_base_uri': "http://www.google.com/search?q=%s", '_space': '+', 'title': "Search Google", 'tooltip': None, },
            {'name': 'GBIFButton', '_base_uri': "http://www.gbif.org/species/search?q=%s", '_space': '+', 'title': _("Search GBIF"), 'tooltip': _("Search the Global Biodiversity Information Facility"), },
            {'name': 'ITISButton', '_base_uri': "http://www.itis.gov/servlet/SingleRpt/SingleRpt?search_topic=Scientific_Name&search_value=%s&search_kingdom=Plant&search_span=containing&categories=All&source=html&search_credRating=All", '_space': '%20', 'title': _("Search ITIS"), 'tooltip': _("Search the Intergrated Taxonomic Information System"), },
            {'name': 'GRINButton', '_base_uri': "http://www.ars-grin.gov/cgi-bin/npgs/swish/accboth?query=%s&submit=Submit+Text+Query&si=0", '_space': '+', 'title': _("Search NPGS/GRIN"), 'tooltip': _('Search National Plant Germplasm System'), },
            {'name': 'ALAButton', '_base_uri': "http://bie.ala.org.au/search?q=%s", '_space': '+', 'title': _("Search ALA"), 'tooltip': _("Search the Atlas of Living Australia"), },
            {'name': 'WikipediaButton', '_base_uri': "http://en.wikipedia.org/wiki/%(genus.genus)s_%(sp)s", '_space': '+', 'title': _("Search Wikipedia"), 'tooltip': _("open the wikipedia page about this species"), },
            {'name': 'IPNIButton', '_base_uri': "http://www.ipni.org/ipni/advPlantNameSearch.do?find_genus=%(genus.genus)s&find_species=%(sp)s&find_isAPNIRecord=on& find_isGCIRecord=on&find_isIKRecord=on&output_format=normal", '_space': ' ', 'title': _("Search IPNI"), 'tooltip': _("Search the International Plant Names Index"), },
            {'name': 'BGCIButton', '_base_uri': "http://www.bgci.org/plant_search.php?action=Find&ftrGenus=%(genus.genus)s&ftrRedList=&ftrSpecies=%(sp)s&ftrRedList1997=&ftrEpithet=&ftrCWR=&x=0&y=0#results", '_space': ' ', 'title': _("Search BGCI"), 'tooltip': _("Search Botanic Gardens Conservation International"), },
            {'name': 'TPLButton', '_base_uri': "http://www.theplantlist.org/tpl1.1/search?q=%(genus.genus)s+%(sp)s", '_space': '+', 'title': _("Search TPL"), 'tooltip': _("Search The Plant List online database"), },
            {'name': 'TropicosButton', '_base_uri': "http://tropicos.org/NameSearch.aspx?name=%(genus.genus)s+%(sp)s", '_space': '+', 'title': _("Search Tropicos"), 'tooltip': _("Search Tropicos (MissouriBG) online database"), },
            ]
        super(SpeciesInfoPage, self).__init__()
        filename = os.path.join(paths.lib_dir(), 'plugins', 'plants',
                                'infoboxes.glade')
        # load the widgets directly instead of using load_widgets()
        # because the caching that load_widgets() does can mess up
        # displaying the SpeciesInfoBox sometimes if you try to show
        # the infobox while having a vernacular names selected in
        # the search results and then a species name
        self.widgets = utils.BuilderWidgets(filename)
        self.general = GeneralSpeciesExpander(self.widgets)
        self.add_expander(self.general)
        self.vernacular = VernacularExpander(self.widgets)
        self.add_expander(self.vernacular)
        self.synonyms = SynonymsExpander(self.widgets)
        self.add_expander(self.synonyms)
        self.links = view.LinksExpander('notes', links=button_defs)
        self.add_expander(self.links)
        self.props = PropertiesExpander()
        self.add_expander(self.props)
        self.label = _('General')

        if 'GardenPlugin' not in pluginmgr.plugins:
            self.widgets.remove_parent('sp_nacc_label')
            self.widgets.remove_parent('sp_nacc_data')
            self.widgets.remove_parent('sp_nplants_label')
            self.widgets.remove_parent('sp_nplants_data')

    def update(self, row):
        '''
        update the expanders in this infobox

        :param row: the row to get the values from
        '''
        self.general.update(row)
        self.vernacular.update(row)
        self.synonyms.update(row)
        self.links.update(row)
        self.props.update(row)


# it's easier just to put this here instead of playing around with imports
class VernacularNameInfoBox(SpeciesInfoBox):

    def update(self, row):
        logger.info("VernacularNameInfoBox.update %s(%s)" % (
            row.__class__.__name__, row))
        if isinstance(row, VernacularName):
            super(VernacularNameInfoBox, self).update(row.species)
