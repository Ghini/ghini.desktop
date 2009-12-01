#
# species.py
#
import bauble.db as db
import bauble.pluginmgr as pluginmgr
from bauble.plugins.plants.species_editor import *
from bauble.plugins.plants.species_model import *
from bauble.view import SearchView, SearchStrategy, MapperSearch, \
     PropertiesExpander, Action
import bauble.view as view
import bauble.utils.desktop as desktop

# __all__ = ['Species', 'SpeciesSynonym', 'SpeciesNote', 'VernacularName',
#            'species_context_menu', 'species_markup_func', 'species_get_kids',
#            'vernname_get_kids', 'vernname_markup_func',
#            'vernname_context_menu', 'SpeciesEditor', 'SpeciesInfoBox',
#            'VernacularNameInfoBox', 'DefaultVernacularName',
#            'SpeciesDistribution', 'edit_action', 'remove_action',
#            'add_accession_action']

# TODO: we need to make sure that this will still work if the
# AccessionPlugin is not present, this means that we would have to
# change the species context menu, getting the children from the
# search view and what else

def edit_callback(values):
    from bauble.plugins.plants.species_editor import SpeciesEditor
    sp = values[0]
    if isinstance(sp, VernacularName):
        sp = sp.species
    e = SpeciesEditor(model=sp)
    return e.start() != None


def remove_callback(values):
    """
    The callback function to remove a species from the species context menu.
    """
    from bauble.plugins.garden.accession import Accession
    session = db.Session()
    species = values[0]
    if isinstance(species, VernacularName):
        species = species.species
    nacc = session.query(Accession).filter_by(species_id=species.id).count()
    safe_str = utils.xml_safe_utf8(str(species))
    if nacc > 0:
        msg = _('The species <i>%s</i> has %s accessions.  Are you sure '
                'you want remove it?') % (safe_str, nacc)
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
        msg = _('Could not delete.\n\n%s') % utils.xml_safe_utf8(e)
        utils.message_details_dialog(msg, traceback.format_exc(),
                                     type=gtk.MESSAGE_ERROR)
    finally:
        session.close()
    return True


def add_accession_callback(values):
    from bauble.plugins.garden.accession import Accession, AccessionEditor
    species = values[0]
    if isinstance(species, VernacularName):
        species = species.species
    e = AccessionEditor(model=Accession(species=species))
    return e.start() != None


edit_action = Action('species_edit', ('_Edit'), callback=edit_callback,
                     accelerator='<ctrl>e')
add_accession_action = Action('species_acc_add', ('_Add accession'),
                              callback=add_accession_callback,
                              accelerator='<ctrl>k')
remove_action = Action('species_remove', ('_Remove'), callback=remove_callback,
                       accelerator='<delete>', multiselect=True)

species_context_menu = [edit_action, remove_action]
vernname_context_menu = [edit_action]


def species_markup_func(species):
    '''
    '''
    # TODO: add (syn) after species name if there are species synonyms that
    # refer to the id of this plant
    if len(species.vernacular_names) > 0:
        substring = '%s -- %s' % \
                    (species.genus.family, \
                     ', '.join([str(v) for v in species.vernacular_names]))
    else:
        substring = '%s' % species.genus.family
    return species.markup(authors=False), substring


def species_get_kids(species):
    try:
        return sorted(species.accessions, key=utils.natsort_key)
    except Exception:
        return []

def vernname_get_kids(vernname):
    '''
    '''
    # TODO: should probably just create an accessions property on vername that
    # does the same thing as vername.species.accessions and might even make
    # it faster if we create the join directly instead of loading the species
    # first
    try:
        return sorted(vernname.species.accessions, key=utils.natsort_key)
    except Exception:
        return []


def vernname_markup_func(vernname):
    '''
    '''
    return str(vernname), vernname.species.markup(authors=False)


from bauble.view import InfoBox, InfoBoxPage, InfoExpander, \
    select_in_search_results

#
# Species infobox for SearchView
#
class VernacularExpander(InfoExpander):
    '''
    the constructor
    '''
    def __init__(self, widgets):
        InfoExpander.__init__(self, _("Vernacular Names"), widgets)
        vernacular_box = self.widgets.sp_vernacular_box
        self.widgets.remove_parent(vernacular_box)
        self.vbox.pack_start(vernacular_box)


    def update(self, row):
        '''
        update the expander

        @param row: the row to get thevalues from
        '''
        if len(row.vernacular_names) == 0:
            self.set_sensitive(False)
            self.set_expanded(False)
        else:
            names = []
            for vn in row.vernacular_names:
                if row.default_vernacular_name is not None \
                       and vn == row.default_vernacular_name:
                    names.insert(0, '%s - %s (default)' % \
                                 (vn.name, vn.language))
                else:
                    names.append('%s - %s' % \
                                 (vn.name, vn.language))
            self.set_widget_value('sp_vernacular_data', '\n'.join(names))
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

        @param row: the row to get thevalues from
        '''
        #debug(row.synonyms)
        if len(row.synonyms) == 0:
            self.set_sensitive(False)
            self.set_expanded(False)
        else:
            def on_label_clicked(label, event, syn):
                select_in_search_results(syn)
            syn_box = self.widgets.sp_synonyms_box
            # remove all the children
            syn_box.foreach(syn_box.remove)
            for syn in row.synonyms:
                # create clickable label that will select the synonym
                # in the search results
                box = gtk.EventBox()
                label = gtk.Label()
                label.set_alignment(0, .5)
                label.set_markup(Species.str(syn, markup=True, authors=True))
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
        self.widgets.sp_name_data.set_line_wrap(True)

        # make the check buttons read only
        def on_enter(button, *args):
            button.emit_stop_by_name("enter-notify-event")
            return True

        self.current_obj = None
        def on_nacc_clicked(*args):
            cmd = 'acc where species.id=%s' % self.current_obj.id
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

        @param row: the row to get the values from
        '''
        self.current_obj = row
        # TODO: how do we put the genus in a seperate label so it
        # can be clickable but still respect the text wrap to wrap
        # around and indent from the genus name instead of from the
        # species name
        session = db.Session()
        self.set_widget_value('sp_name_data', '<big>%s</big>' % \
                              row.markup(True))
        self.set_widget_value('sp_dist_data', row.distribution_str())

        # stop here if not GardenPluin
        if 'GardenPlugin' not in pluginmgr.plugins:
            return

        from bauble.plugins.garden.accession import Accession
        from bauble.plugins.garden.plant import Plant

        nacc = session.query(Accession).join('species').\
               filter_by(id=row.id).count()
        self.set_widget_value('sp_nacc_data', nacc)

        nplants = session.query(Plant).join(['accession', 'species']).\
                    filter_by(id=row.id).count()
        if nplants == 0:
            self.set_widget_value('sp_nplants_data', nplants)
        else:
            nacc_in_plants = session.query(Plant.accession_id).\
                    join(['accession', 'species']).\
                    filter_by(id=row.id).distinct().count()
            self.set_widget_value('sp_nplants_data', '%s in %s accessions' \
                                  % (nplants, nacc_in_plants))
        session.close()



class LinksExpander(view.LinksExpander):

    """
    A collection of link buttons to use for internet searches.
    """

    def __init__(self):
        super(LinksExpander, self).__init__("notes")
        buttons = []

        self.google_button = gtk.LinkButton("", _("Search Google"))
        self.google_button.set_tooltip_text(_("Search Google"))
        buttons.append(self.google_button)

        self.gbif_button = gtk.LinkButton("", _("Search GBIF"))
        tooltip = _("Search the Global Biodiversity Information Facility")
        self.gbif_button.set_tooltip_text(tooltip)
        buttons.append(self.gbif_button)

        self.itis_button = gtk.LinkButton("", _("Search ITIS"))
        tooltip = _("Search the Intergrated Taxonomic Information System")
        self.itis_button.set_tooltip_text(tooltip)
        buttons.append(self.itis_button)

        self.ipni_button = gtk.LinkButton("", _("Search IPNI"))
        tooltip = _("Search the International Plant Names Index")
        self.ipni_button.set_tooltip_text(tooltip)
        buttons.append(self.ipni_button)

        self.bgci_button = gtk.LinkButton("", _("Search BGCI"))
        tooltip = _("Search Botanic Gardens Conservation International")
        self.bgci_button.set_tooltip_text(tooltip)
        buttons.append(self.bgci_button)

        for b in buttons:
            b.set_alignment(0, -1)
            self.vbox.pack_start(b, expand=False, fill=False)


    def update(self, row):
        super(LinksExpander, self).update(row)
        s = str(row)
        self.gbif_button.set_uri("http://data.gbif.org/search/%s" % \
                                 s.replace(' ', '+'))
        itis_uri = "http://www.itis.gov/servlet/SingleRpt/SingleRpt?"\
                   "search_topic=Scientific_Name" \
                   "&search_value=%(search_value)s" \
                   "&search_kingdom=Plant" \
                   "&search_span=containing" \
                   "&categories=All&source=html&search_credRating=All" \
                   % {'search_value': s.replace(' ', '%20')}
        self.itis_button.set_uri(itis_uri)

        self.google_button.set_uri("http://www.google.com/search?q=%s" % \
                                   s.replace(' ', '+'))

        bgci_uri = "http://www.bgci.org/plant_search.php?action=Find"\
                   "&ftrGenus=%(genus)s&ftrRedList=&ftrSpecies=%(species)s"\
                   "&ftrRedList1997=&ftrEpithet=&ftrCWR=&x=0&y=0#results" % \
                   {'genus': str(row.genus), "species": str(row.sp) }
        self.bgci_button.set_uri(bgci_uri)

        ipni_uri = "http://www.ipni.org/ipni/advPlantNameSearch.do?"\
                   "find_genus=%(genus)s&find_species=%(species)s" \
                   "&find_isAPNIRecord=on& find_isGCIRecord=on" \
                   "&find_isIKRecord=on&output_format=normal" % \
                   {'genus': str(row.genus), 'species': str(row.sp)}
        self.ipni_button.set_uri(ipni_uri)



class SpeciesInfoBox(InfoBox):

    def __init__(self):
        super(SpeciesInfoBox, self).__init__(tabbed=True)
        page = SpeciesInfoPage()
        label = page.label
        if isinstance(label, basestring):
            label = gtk.Label(label)
        self.insert_page(page, label, 0)

        from bauble.plugins.picasa import PicasaInfoPage
        page = PicasaInfoPage()
        label = page.label
        if isinstance(label, basestring):
            label = gtk.Label(label)
        self.insert_page(page, label, 1)



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
        super(SpeciesInfoPage, self).__init__()
        filename = os.path.join(paths.lib_dir(), 'plugins', 'plants',
                                  'infoboxes.glade')
        self.widgets = utils.load_widgets(filename)
        self.general = GeneralSpeciesExpander(self.widgets)
        self.add_expander(self.general)
        self.vernacular = VernacularExpander(self.widgets)
        self.add_expander(self.vernacular)
        self.synonyms = SynonymsExpander(self.widgets)
        self.add_expander(self.synonyms)
        self.links = LinksExpander()
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

        @param row: the row to get the values from
        '''
        self.general.update(row)
        self.vernacular.update(row)
        self.synonyms.update(row)
        self.links.update(row)
        self.props.update(row)


# it's easier just to put this here instead of playing around with imports
class VernacularNameInfoBox(SpeciesInfoBox):

    def update(self, row):
        super(VernacularNameInfoBox, self).update(row.species)
        #self.props.update(row)


