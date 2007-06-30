#
# species.py
#

from species_editor import *
from species_model import *
from bauble.view import SearchView, SearchStrategy, MapperSearch

__all__ = ['species_table', 'Species', 'species_synonym_table',
           'SpeciesSynonym', 'vernacular_name_table', 'VernacularName',
           'species_context_menu', 'species_markup_func', 'vernname_get_kids',
           'vernname_markup_func', 'vernname_context_menu', 'SpeciesEditor',
           'SpeciesInfoBox', 'VernacularNameInfoBox',
           'species_distribution_table', 'SpeciesDistribution']


def edit_callback(value):
    from bauble.plugins.plants.species_editor import SpeciesEditor
    e = SpeciesEditor(value)
    return e.start() != None


def add_accession_callback(value):
    from bauble.plugins.garden.accession import AccessionEditor
    e = AccessionEditor(Accession(species=value))
    return e.start() != None


def remove_callback(value):
    s = '%s: %s' % (value.__class__.__name__, str(value))
    msg = _("Are you sure you want to remove %s?") % \
              utils.xml_safe_utf8(s)
    if not utils.yes_no_dialog(msg):
        return
    try:
        session = create_session()
        obj = session.load(value.__class__, value.id)
        session.delete(obj)
        session.flush()
    except Exception, e:
        msg = _('Could not delete.\n\n%s') % utils.xml_safe_utf8(e)
        utils.message_details_dialog(msg, traceback.format_exc(),
                                     type=gtk.MESSAGE_ERROR)
    return True



species_context_menu = [('Edit', edit_callback),
                       ('--', None),
                       ('Add accession', add_accession_callback),
                       ('--', None),
                       ('Remove', remove_callback)]


def call_on_species(func):
    return lambda value : func(value.species)

vernname_context_menu = [('Edit', call_on_species(edit_callback)),
                          ('--', None),
                          ('Add accession',
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


from bauble.view import InfoBox, InfoExpander
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
        InfoExpander.__init__(self, "Vernacular Names", widgets)
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
        InfoExpander.__init__(self, "Synonyms", widgets)
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
                s = Species.str(syn.synonym, markup=True, authors=True)
                synonyms.append(s)
            self.widgets.sp_synonyms_data.set_markup('\n'.join(synonyms))
            self.set_sensitive(True)
            # TODO: get expanded state from prefs
            self.set_expanded(True)



class NotesExpander(InfoExpander):

    def __init__(self, widgets):
        InfoExpander.__init__(self, "Notes", widgets)
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
        InfoExpander.__init__(self, "General", widgets)
        general_box = self.widgets.sp_general_box
        self.widgets.remove_parent(general_box)
        self.vbox.pack_start(general_box)

        # make the check buttons read only
        def on_enter(button, *args):
            button.emit_stop_by_name("enter-notify-event")
            return True


    def update(self, row):
        '''
        update the expander

        @param row: the row to get the values from
        '''
        self.set_widget_value('sp_name_data', row.markup(True))
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

        #self.ref = ReferenceExpander()
        #self.ref.set_expanded(True)
        #self.add_expander(self.ref)

        #img = ImagesExpander()
        #img.set_expanded(True)
        #self.add_expander(img)


    def update(self, row):
        '''
        update the expanders in this infobox

        @param row: the row to get the values from
        '''
        self.general.update(row)
        self.vernacular.update(row)
        self.synonyms.update(row)
        self.notes.update(row)
        #self.ref.update(row.references)
        #self.ref.value = row.references
        #ref = self.get_expander("References")
        #ref.set_values(row.references)


# it's easier just to put this here instead of playing around with imports
class VernacularNameInfoBox(SpeciesInfoBox):
    def update(self, row):
        super(VernacularNameInfoBox, self).update(row.species)


