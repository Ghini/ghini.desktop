#
# species.py
#

from bauble.plugins.plants.species_editor import *
from bauble.plugins.plants.species_model import *
from bauble.view import SearchView, SearchStrategy, MapperSearch, \
     PropertiesExpander
from bauble.i18n import _
import bauble.utils.desktop as desktop

__all__ = ['species_table', 'Species', 'species_synonym_table',
           'SpeciesSynonym', 'vernacular_name_table', 'VernacularName',
           'species_context_menu', 'species_markup_func', 'vernname_get_kids',
           'vernname_markup_func', 'vernname_context_menu', 'SpeciesEditor',
           'SpeciesInfoBox', 'VernacularNameInfoBox',
           'species_distribution_table', 'SpeciesDistribution']


def edit_callback(value):
    from bauble.plugins.plants.species_editor import SpeciesEditor
    session = bauble.Session()
    e = SpeciesEditor(model=session.merge(value))
    return e.start() != None


def add_accession_callback(value):
    from bauble.plugins.garden.accession import AccessionEditor
    session = bauble.Session()
    e = AccessionEditor(model=Accession(species=session.merge(value)))
    return e.start() != None


def remove_callback(value):
    s = '%s: %s' % (value.__class__.__name__, str(value))
    msg = _("Are you sure you want to remove %s?") % \
              utils.xml_safe_utf8(s)
    if not utils.yes_no_dialog(msg):
        return
    try:
        session = bauble.Session()
        obj = session.load(value.__class__, value.id)
        session.delete(obj)
        session.commit()
    except Exception, e:
        msg = _('Could not delete.\n\n%s') % utils.xml_safe_utf8(e)
        utils.message_details_dialog(msg, traceback.format_exc(),
                                     type=gtk.MESSAGE_ERROR)
    return True



species_context_menu = [(_('Edit'), edit_callback),
                        ('--', None),
                        (_('Add accession'), add_accession_callback),
                        ('--', None),
                        (_('Remove'), remove_callback)]


def call_on_species(func):
    return lambda value : func(value.species)

vernname_context_menu = [(_('Edit'), call_on_species(edit_callback)),
                         ('--', None),
                         (_('Add accession'),
                          call_on_species(add_accession_callback))]

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


def vernname_get_kids(vernname):
    '''
    '''
    # TODO: should probably just create an accessions property on vername that
    # does the same thing as vername.species.accessions and might even make
    # it faster if we create the join directly instead of loading the species
    # first
    return sorted(vernname.species.accessions, key=utils.natsort_key)


def vernname_markup_func(vernname):
    '''
    '''
    return str(vernname), vernname.species.markup(authors=False)


from bauble.view import InfoBox, InfoExpander, select_in_search_results
from bauble.plugins.garden.accession import Accession, accession_table
from bauble.plugins.garden.plant import Plant, plant_table

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
            synonyms = []
            for syn in row.synonyms:
                s = Species.str(syn, markup=True, authors=True)
                synonyms.append(s)
            self.widgets.sp_synonyms_data.set_markup('\n'.join(synonyms))
            self.set_sensitive(True)
            # TODO: get expanded state from prefs
            self.set_expanded(True)



class NotesExpander(InfoExpander):

    def __init__(self, widgets):
        InfoExpander.__init__(self, _("Notes"), widgets)
        notes_box = self.widgets.sp_notes_box
        self.widgets.remove_parent(notes_box)
        self.vbox.pack_start(notes_box)


    def update(self, row):
        if row.notes is None:
            self.set_expanded(False)
            self.set_sensitive(False)
        else:
            self.set_expanded(True)
            self.set_sensitive(True)
            self.set_widget_value('sp_notes_data', row.notes)


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

        # make the check buttons read only
        def on_enter(button, *args):
            button.emit_stop_by_name("enter-notify-event")
            return True

        self.current_obj = None
#         def on_genus_clicked(*args):
#             select_in_search_results(self.current_obj.genus)
#         utils.make_label_clickable(self.widgets.sp_genus_data, on_genus_clicked)


    def update(self, row):
        '''
        update the expander

        @param row: the row to get the values from
        '''
        # TODO: how do we put the genus is a seperate label so so it
        # can be clickable but still respect the text wrap to wrap
        # around and indent from the genus name instead of from the
        # species name
        sp_str = row.markup(True)
        from textwrap import TextWrapper
        wrapper = TextWrapper(width=50, subsequent_indent='  ')
        new_str = wrapper.fill(sp_str)
        self.set_widget_value('sp_name_data', '<big>%s</big>' % new_str)
        nacc = sql_utils.count(accession_table,
                               accession_table.c.species_id==row.id)
        self.set_widget_value('sp_nacc_data', nacc)

        acc_ids = select([accession_table.c.id],
                         accession_table.c.species_id==row.id)
        nplants_str = str(sql_utils.count(plant_table,
                                    plant_table.c.accession_id.in_(acc_ids)))
        if nplants_str != '0':
            nacc_with_plants = sql_utils.count_distinct_whereclause(plant_table.c.accession_id, plant_table.c.accession_id.in_(acc_ids))
            nplants_str = '%s in %s accessions' % \
                          (nplants_str, nacc_with_plants)
        self.set_widget_value('sp_nplants_data', nplants_str)

        self.set_widget_value('sp_dist_data', row.distribution_str())



class LinksExpander(InfoExpander):

    """
    A collection of link buttons to use for internet searches.
    """

    def __init__(self):
        InfoExpander.__init__(self, _("Links"))
        self.tooltips = gtk.Tooltips()
        buttons = []

        self.google_button = gtk.LinkButton("", _("Search Google"))
        self.tooltips.set_tip(self.google_button, _("Search Google"))
        buttons.append(self.google_button)

        self.gbif_button = gtk.LinkButton("", _("Search GBIF"))
        self.tooltips.set_tip(self.gbif_button,
                         _("Search the Global Biodiversity Information "\
                           "Facility"))
        buttons.append(self.gbif_button)

        self.itis_button = gtk.LinkButton("", _("Search ITIS"))
        self.tooltips.set_tip(self.itis_button,
                              _("Search the Intergrated Taxonomic "\
                                "Information System"))
        buttons.append(self.itis_button)

        self.ipni_button = gtk.LinkButton("", _("Search IPNI"))
        self.tooltips.set_tip(self.ipni_button,
                              _("Search the International Plant Names Index"))
        buttons.append(self.ipni_button)

        self.bgci_button = gtk.LinkButton("", _("Search BGCI"))
        self.tooltips.set_tip(self.bgci_button,
                              _("Search Botanic Gardens Conservation " \
                                "International"))
        buttons.append(self.bgci_button)

        for b in buttons:
            b.set_alignment(0, -1)
            b.connect("clicked", self.on_click)
            self.vbox.pack_start(b)


    def on_click(self, button):
        desktop.open(button.get_uri())


    def update(self, row):
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
    '''
    general info, fullname, common name, num of accessions and clones,
    distribution
    '''

    # others to consider: reference, images, redlist status

    def __init__(self):
        '''
        the constructor
        '''
        InfoBox.__init__(self)
        glade_file = os.path.join(paths.lib_dir(), 'plugins', 'plants',
                                  'infoboxes.glade')
        self.widgets = utils.GladeWidgets(gtk.glade.XML(glade_file))
        self.general = GeneralSpeciesExpander(self.widgets)
        self.add_expander(self.general)
        self.vernacular = VernacularExpander(self.widgets)
        self.add_expander(self.vernacular)
        self.synonyms = SynonymsExpander(self.widgets)
        self.add_expander(self.synonyms)
        self.notes = NotesExpander(self.widgets)
        self.add_expander(self.notes)
        self.links = LinksExpander()
        self.add_expander(self.links)
        self.props = PropertiesExpander()
        self.add_expander(self.props)


    def update(self, row):
        '''
        update the expanders in this infobox

        @param row: the row to get the values from
        '''
        self.general.update(row)
        self.vernacular.update(row)
        self.synonyms.update(row)
        self.notes.update(row)
        self.links.update(row)
        self.props.update(row)


# it's easier just to put this here instead of playing around with imports
class VernacularNameInfoBox(SpeciesInfoBox):

    def update(self, row):
        super(VernacularNameInfoBox, self).update(row.species)
        self.props.update(row)


