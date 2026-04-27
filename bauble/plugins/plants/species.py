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
import logging
import os
import traceback
from gettext import gettext as _
from typing import Any, Optional, Set

import bauble
import bauble.paths as paths
import bauble.pluginmgr as pluginmgr
import bauble.search as search
import bauble.utils as utils
import bauble.view as view
from bauble.db import Session
from bauble.gtkinit import Gtk
from bauble.plugins.plants.genus import Genus, GenusSynonym
from bauble.plugins.plants.species_editor import (
    SpeciesDistribution as SpeciesDistribution,
)
from bauble.plugins.plants.species_editor import SpeciesEditor as SpeciesEditor
from bauble.plugins.plants.species_editor import (
    SpeciesEditorPresenter as SpeciesEditorPresenter,
)
from bauble.plugins.plants.species_editor import SpeciesEditorView as SpeciesEditorView
from bauble.plugins.plants.species_editor import edit_species as edit_species
from bauble.plugins.plants.species_model import (
    DefaultVernacularName as DefaultVernacularName,
)
from bauble.plugins.plants.species_model import Species as Species
from bauble.plugins.plants.species_model import SpeciesNote as SpeciesNote
from bauble.plugins.plants.species_model import SpeciesSynonym as SpeciesSynonym
from bauble.plugins.plants.species_model import VernacularName as VernacularName
from bauble.prefs import prefs
from bauble.shared import InfoExpander
from bauble.view import Action, InfoBox, PropertiesExpander, select_in_search_results
from sqlalchemy import distinct, select
from sqlalchemy.orm.session import object_session

logger: Any = logging.getLogger(__name__)

logger.setLevel(logging.INFO)


SpeciesDistribution  # will be imported by clients of this module
SpeciesEditorPresenter, SpeciesEditorView, SpeciesEditor, edit_species,
DefaultVernacularName
SpeciesNote


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
    from bauble.plugins.garden.models import Accession

    species = values[0]
    session = object_session(species)
    if isinstance(species, VernacularName):
        species = species.species
    from sqlalchemy import func

    nacc = session.execute(
        select(func.count()).select_from(Accession).where(species_id=species.id)
    )
    safe_str = utils.xml_safe(species)
    if nacc > 0:
        msg = _("The species <i>%(1)s</i> has %(2)s accessions." "\n\n") % {
            "1": safe_str,
            "2": nacc,
        } + _("You cannot remove a species with accessions.")
        utils.message_dialog(msg, type=Gtk.MessageType.WARNING)
        return
    else:
        msg = _("Are you sure you want to remove the species <i>%s</i>?") % safe_str
    if not utils.yes_no_dialog(msg):
        return
    try:
        obj = session.get(Species, species.id)
        session.delete(obj)
        if session.in_transaction():
            session.commit()
    except Exception as e:
        msg = _("Could not delete.\n\n%s") % utils.xml_safe(e)
        utils.message_details_dialog(
            msg, traceback.format_exc(), type=Gtk.MessageType.ERROR
        )
    return True


def add_accession_callback(values):
    from bauble.plugins.garden.accession_editor import AccessionEditor
    from bauble.plugins.garden.models import Accession

    session = Session()
    species = session.merge(values[0])
    if isinstance(species, VernacularName):
        species = species.species
    e = AccessionEditor(model=Accession(species=species))
    # session creates unbound object.  editor decides what to do with it.
    session.close()
    return e.start() is not None


edit_action: Any = Action(
    "species_edit", _("_Edit"), callback=edit_callback, accelerator="<ctrl>e"
)
add_accession_action: Any = Action(
    "species_acc_add",
    _("_Add accession"),
    callback=add_accession_callback,
    accelerator="<ctrl>k",
)
remove_action: Any = Action(
    "species_remove",
    _("_Delete"),
    callback=remove_callback,
    accelerator="<ctrl>Delete",
    multiselect=True,
)

species_context_menu: Any = [edit_action, remove_action]
vernname_context_menu: Any = [edit_action]

class SynonymSearch(search.SearchStrategy):
    return_synonyms_pref: str = "bauble.search.return_synonyms"

    def __init__(self) -> None:
        super().__init__()
        if self.return_synonyms_pref not in prefs:
            prefs[self.return_synonyms_pref] = True
            prefs.save()

    def search(self, text, session, seed: Optional[Set[Any]] = None, **_):
        super().search(text, session)
        if not session or not prefs[self.return_synonyms_pref]:
            return set()

        # use the provided base if available to avoid re-running MapperSearch
        if seed is not None:
            base = set(seed)
        else:
            # fallback if called directly
            mapper_search = search.get_strategy("MapperSearch")
            base = set(mapper_search.search(text, session))

        if not base:
            return set()

        # adjust imports to where your synonym ORM classes actually are
        from bauble.plugins.plants.species_model import SpeciesSynonym
        from sqlalchemy import select

        # Build synonyms only (let the dispatcher union with base)
        synonyms: Set[Any] = set()

        # Optional micro-optimization: batch synonym lookups
        species_ids = [o.id for o in base if isinstance(o, Species)]
        genus_ids   = [o.id for o in base if isinstance(o, Genus)]
        vname_sids  = [o.species.id for o in base if isinstance(o, VernacularName)]

        if species_ids:
            syns = session.scalars(
                select(SpeciesSynonym).where(SpeciesSynonym.synonym_id.in_(species_ids))
            ).all()
            synonyms.update(syn.species for syn in syns if syn.species is not None)

        if genus_ids:
            syns = session.scalars(
                select(GenusSynonym).where(GenusSynonym.synonym_id.in_(genus_ids))
            ).all()
            synonyms.update(syn.genus for syn in syns if syn.genus is not None)

        if vname_sids:
            syns = session.scalars(
                select(SpeciesSynonym).where(SpeciesSynonym.synonym_id.in_(vname_sids))
            ).all()
            synonyms.update(syn.species for syn in syns if syn.species is not None)

        return synonyms - base

#
# Species infobox for SearchView
#
class VernacularExpander(InfoExpander):
    """
    VernacularExpander

    :param widgets:
    """

    def __init__(self, widgets) -> None:
        InfoExpander.__init__(self, _("Vernacular names"), widgets)
        vernacular_box = self.widgets.sp_vernacular_box
        self.widgets.remove_parent(vernacular_box)
        self.vbox.pack_start(vernacular_box, True, True, 0)

    def update(self, row) -> None:
        """
        update the expander

        :param row: the row to get thevalues from
        """
        if len(row.vernacular_names) == 0:
            self.set_sensitive(False)
            self.set_expanded(False)
        else:
            names = []
            for vn in row.vernacular_names:
                if (
                    row.default_vernacular_name is not None
                    and vn == row.default_vernacular_name
                ):
                    names.insert(0, f"{vn.name} - {vn.language} (default)")
                else:
                    names.append(f"{vn.name} - {vn.language}")
            self.widget_set_value("sp_vernacular_data", "\n".join(names))
            self.set_sensitive(True)
            # TODO: get expanded state from prefs
            self.set_expanded(True)


class SynonymsExpander(InfoExpander):

    def __init__(self, widgets) -> None:
        InfoExpander.__init__(self, _("Synonyms"), widgets)
        synonyms_box = self.widgets.sp_synonyms_box
        self.widgets.remove_parent(synonyms_box)
        self.vbox.pack_start(synonyms_box, True, True, 0)

    def update(self, row):
        """
        update the expander

        :param row: the row to get thevalues from
        """
        syn_box = self.widgets.sp_synonyms_box
        # remove old labels
        syn_box.foreach(syn_box.remove)
        logger.debug(row.synonyms)
        session = object_session(row)
        syn = (
            session.execute(
                select(SpeciesSynonym).where(SpeciesSynonym.synonym_id == row.id)
            )
            .scalars()
            .first()
        )
        accepted = syn and syn.species
        logger.debug(
            f"species {row} is synonym of {accepted} and has synonyms {row.synonyms}"
        )
        self.set_label(_("Synonyms"))  # reset default value

        def on_label_clicked(l, e, syn):
            return select_in_search_results(syn)

        if accepted is not None:
            self.set_label(_("Accepted name"))
            # create clickable label that will select the synonym
            # in the search results
            box = Gtk.EventBox()
            label = Gtk.Label()
            label.set_alignment(0, 0.5)
            label.set_markup(accepted.str(markup=True, authors=True))
            box.add(label)
            utils.make_label_clickable(label, on_label_clicked, accepted)
            syn_box.pack_start(box, False, False, 0)
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
                box = Gtk.EventBox()
                label = Gtk.Label()
                label.set_alignment(0, 0.5)
                label.set_markup(syn.str(markup=True, authors=True))
                box.add(label)
                utils.make_label_clickable(label, on_label_clicked, syn)
                syn_box.pack_start(box, False, False, 0)
            self.show_all()
            self.set_sensitive(True)
            # TODO: get expanded state from prefs
            self.set_expanded(True)


class GeneralSpeciesExpander(InfoExpander):
    """
    expander to present general information about a species
    """

    current_obj: Any

    def __init__(self, widgets) -> None:
        """
        the constructor
        """
        InfoExpander.__init__(self, _("General"), widgets)
        general_box = self.widgets.sp_general_box
        self.widgets.remove_parent(general_box)
        self.vbox.pack_start(general_box, True, True, 0)
        self.widgets.sp_epithet_data.set_property("wrap", True)

        # make the check buttons read only
        def on_enter(button, *args):
            button.emit_stop_by_name("enter-notify-event")
            return True

        self.current_obj = None

        def on_nacc_clicked(*args):
            cmd = f"accession where species.id={self.current_obj.id}"
            bauble.gui.send_command(cmd)

        utils.make_label_clickable(self.widgets.sp_nacc_data, on_nacc_clicked)

        def on_nplants_clicked(*args):
            cmd = f"plant where accession.species.id={self.current_obj.id}"
            bauble.gui.send_command(cmd)

        utils.make_label_clickable(self.widgets.sp_nplants_data, on_nplants_clicked)

    def update(self, row):
        """
        update the expander

        :param row: the row to get the values from
        """
        self.current_obj = row
        session = object_session(row)

        # link function
        def on_label_clicked(l, e, x):
            return select_in_search_results(x)

        # Link to family
        self.widget_set_value(
            "sp_fam_data",
            f"<small>({row.genus.family.epithet})</small>",
            markup=True,
        )
        utils.make_label_clickable(
            self.widgets.sp_fam_data, on_label_clicked, row.genus.family
        )
        # link to genus
        self.widget_set_value(
            "sp_gen_data",
            f"<big><i>{row.genus.genus}</i></big>",
            markup=True,
        )
        utils.make_label_clickable(
            self.widgets.sp_gen_data, on_label_clicked, row.genus
        )
        # epithet (full binomial but missing genus)
        self.widget_set_value(
            "sp_epithet_data",
            f"<big>{row.markup(authors=True, genus=False)}</big>",
            markup=True,
        )

        awards = ""
        if row.awards:
            awards = utils.to_unicode(row.awards)
        self.widget_set_value("sp_awards_data", awards)

        logger.debug(f"setting cites data from row {row}")
        cites = ""
        if row.cites:
            cites = utils.to_unicode(row.cites)
        self.widget_set_value("sp_cites_data", cites)

        # zone = ''
        # if row.hardiness_zone:
        #     awards = utils.to_unicode(row.hardiness_zone)
        # self.widget_set_value('sp_hardiness_data', zone)

        habit = ""
        if row.habit:
            habit = utils.to_unicode(row.habit)
        self.widget_set_value("sp_habit_data", habit)

        dist = ""
        if row.distribution:
            dist = utils.to_unicode(row.distribution_str())
        self.widget_set_value("sp_dist_data", dist)

        dist = ""
        if row.label_distribution:
            dist = row.label_distribution
        self.widget_set_value("sp_labeldist_data", dist)

        # stop here if not GardenPluin
        if "GardenPlugin" not in pluginmgr.plugins:
            return

        from bauble.plugins.garden.models import Accession, Plant

        nacc = (
            session.execute(
                select(Accession)
                .join(Species, Accession.species_id == Species.id)
                .where(Species.id == row.id)
            )
            .scalars()
            .count()
        )
        self.widget_set_value("sp_nacc_data", nacc)

        nplants = (
            session.execute(
                select(Plant)
                .join(Accession, Plant.accession_id == Accession.id)
                .join(Species, Accession.species_id == Species.id)
                .where(Species.id == row.id)
            )
            .scalars()
            .count()
        )
        if nplants == 0:
            self.widget_set_value("sp_nplants_data", nplants)
        else:
            nacc_in_plants = len(
                session.execute(
                    select(distinct(Plant.accession_id))
                    .join(Accession, Plant.accession_id == Accession.id)
                    .join(Species, Accession.species_id == Species.id)
                    .where(Species.id == row.id)
                )
                .scalars()
                .all()
            )
            self.widget_set_value(
                "sp_nplants_data",
                f"{nplants} in {nacc_in_plants} accessions",
            )

        living_plants = sum(
            i.quantity
            for i in session.execute(
                select(Plant)
                .join(Accession, Plant.accession_id == Accession.id)
                .join(Species, Accession.species_id == Species.id)
                .where(Species.id == row.id)
            )
            .scalars()
            .all()
        )
        self.widget_set_value("living_plants_count", living_plants)


class SpeciesInfoBox(InfoBox):
    """
    general info, fullname, common name, num of accessions and clones,
    distribution
    """

    # others to consider: reference, images, redlist status

    widgets: Any
    general: Any
    vernacular: Any
    synonyms: Any
    links: Any
    properties_expander: Any
    label: Any

    def __init__(self) -> None:
        """
        the constructor
        """
        button_defs = [
            {
                "name": "GoogleButton",
                "_base_uri": "https://www.google.com/search?q=%s",
                "_space": "+",
                "title": "Search Google",
                "tooltip": None,
            },
            {
                "name": "GBIFButton",
                "_base_uri": "https://www.gbif.org/species/search?q=%s",
                "_space": "+",
                "title": _("Search GBIF"),
                "tooltip": _("Search the Global Biodiversity Information Facility"),
            },
            {
                "name": "ITISButton",
                "_base_uri": "https://www.itis.gov/servlet/SingleRpt/SingleRpt?search_topic=Scientific_Name&search_value=%s&search_kingdom=Plant&search_span=containing&categories=All&source=html&search_credRating=All",
                "_space": "%20",
                "title": _("Search ITIS"),
                "tooltip": _("Search the Intergrated Taxonomic Information System"),
            },
            {
                "name": "GRINButton",
                "_base_uri": "https://npgsweb.ars-grin.gov/gringlobal/search=%s",
                "_space": "+",
                "title": _("Search NPGS/GRIN"),
                "tooltip": _("Search National Plant Germplasm System"),
            },
            {
                "name": "ALAButton",
                "_base_uri": "https://bie.ala.org.au/search?q=%s",
                "_space": "+",
                "title": _("Search ALA"),
                "tooltip": _("Search the Atlas of Living Australia"),
            },
            {
                "name": "WikipediaButton",
                "_base_uri": "http://en.wikipedia.org/wiki/%(genus.genus)s_%(sp)s",
                "_space": "+",
                "title": _("Search Wikipedia"),
                "tooltip": _("open the wikipedia page about this species"),
            },
            {
                "name": "IPNIButton",
                "_base_uri": "https://www.ipni.org/ipni/advPlantNameSearch.do?find_genus=%(genus.genus)s&find_species=%(sp)s&find_isAPNIRecord=on& find_isGCIRecord=on&find_isIKRecord=on&output_format=normal",
                "_space": " ",
                "title": _("Search IPNI"),
                "tooltip": _("Search the International Plant Names Index"),
            },
            {
                "name": "BGCIButton",
                "_base_uri": "https://plantsearch.bgci.org/search?filter[genus]=%(genus.genus)s&filter[specific_epithet]=%(sp)s&sort=name",
                "_space": " ",
                "title": _("Search BGCI"),
                "tooltip": _("Search Botanic Gardens Conservation International"),
            },
            {
                "name": "WFOButton",
                "_base_uri": "https://www.worldfloraonline.org/search?query=%(genus.genus)s+%(sp)s",
                "_space": "+",
                "title": _("Search WFO"),
                "tooltip": _("Search The World Flora Online database"),
            },
            {
                "name": "TropicosButton",
                "_base_uri": "https://tropicos.org/name/Search?name=%(genus.genus)s+%(sp)s",
                "_space": "+",
                "title": _("Search Tropicos"),
                "tooltip": _("Search Tropicos (MissouriBG) online database"),
            },
        ]
        super().__init__()
        filename = os.path.join(paths.lib_dir(), "plugins", "plants", "infoboxes.glade")
        # load the widgets directly instead of using BuilderWidgets()
        # because the caching that BuilderWidgets() does can mess up
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
        self.links = view.LinksExpander("notes", links=button_defs)
        self.add_expander(self.links)
        self.properties_expander = PropertiesExpander()
        self.add_expander(self.properties_expander)
        self.label = _("General")

        if "GardenPlugin" not in pluginmgr.plugins:
            self.widgets.remove_parent("sp_nacc_label")
            self.widgets.remove_parent("sp_nacc_data")
            self.widgets.remove_parent("sp_nplants_label")
            self.widgets.remove_parent("sp_nplants_data")

    def update(self, row) -> None:
        """
        update the expanders in this infobox

        :param row: the row to get the values from
        """
        self.general.update(row)
        self.vernacular.update(row)
        self.synonyms.update(row)
        self.links.update(row)
        self.properties_expander.update(row)


# it's easier just to put this here instead of playing around with imports
class VernacularNameInfoBox(SpeciesInfoBox):

    def update(self, row) -> None:
        logger.info(f"VernacularNameInfoBox.update {row.__class__.__name__}({row})")
        if isinstance(row, VernacularName):
            super().update(row.species)
            super().update(row.species)
