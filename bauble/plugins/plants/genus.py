#
# Genera table module
#

import os, traceback
import gtk
from sqlalchemy import *
from sqlalchemy.orm.session import object_session
from sqlalchemy.exceptions import SQLError
import bauble
from bauble.editor import *
import bauble.utils as utils
from bauble.types import Enum
from bauble.utils.log import debug


# TODO: should be a higher_taxon column that holds values into 
# subgen, subfam, tribes etc, maybe this should be included in Genus

# TODO: since there can be more than one genus with the same name but
# different authors we need to show the Genus author in the result search
# and at least give the Genus it's own infobox, we should also check if
# when entering a plantname with a chosen genus if that genus has an author
# ask the user if they want to use the accepted name and show the author of
# the genus then so they aren't using the wrong version of the Genus,
# e.g. Cananga

def edit_callback(row):
    value = row[0]
    
    # TODO: the select paramater can go away when we move FamilyEditor to the 
    # new style editors    
    e = GenusEditor(select=[value], model=value)
    return e.start() != None


def add_species_callback(row):
    from bauble.plugins.plants.species_editor import SpeciesEditor
    value = row[0]
    # call with genus_id instead of genus so the new species doesn't get bound
    # to the same session as genus
    # TODO: i wish there was a better way around this
    e = SpeciesEditor(model_or_defaults={'genus_id': value.id})
    return e.start() != None


def remove_callback(row):
    value = row[0]
    s = '%s: %s' % (value.__class__.__name__, str(value))
    msg = "Are you sure you want to remove %s?" % s
        
    if utils.yes_no_dialog(msg):
        from sqlobject.main import SQLObjectIntegrityError
        try:
            value.destroySelf()
            # since we are doing everything in a transaction, commit it
            sqlhub.processConnection.commit() 
            return True
        except SQLObjectIntegrityError, e:
            msg = "Could not delete '%s'. It is probably because '%s' "\
                  "still has children that refer to it.  See the Details for "\
                  " more information." % (s, s)
            utils.message_details_dialog(msg, str(e))
        except:
            msg = "Could not delete '%s'. It is probably because '%s' "\
                  "still has children that refer to it.  See the Details for "\
                  " more information." % (s, s)
            utils.message_details_dialog(msg, traceback.format_exc())


genus_context_menu = [('Edit', edit_callback),
                       ('--', None),
                       ('Add species', add_species_callback),
                       ('--', None),
                       ('Remove', remove_callback)]


def genus_markup_func(genus):
    '''
    '''
    return '%s (%s)' % (str(genus), str(genus.family))

    '''
    hybrid: indicates whether the name in the Genus Name field refers to an 
    Intergeneric hybrid or an Intergeneric graft chimaera.
    Content of genhyb   Nature of Name in gen
    H        An intergeneric hybrid collective name
    x        An Intergeneric Hybrid
    +        An Intergeneric Graft Hybrid or Graft Chimaera
    
    qualifier field designates the botanical status of the genus.
    Possible values:
    s. lat. - aggregrate family (sensu lato)
    s. str. segregate family (sensu stricto)
    '''
    
    # TODO: we should at least warn the user that a duplicate genus name is being 
    # entered
    
genus_table = Table('genus',
                    Column('id', Integer, primary_key=True),
    
                    # it is possible that there can be genera with the same name but 
                    # different authors and probably means that at different points in literature
                    # this name was used but is now a synonym even though it may not be a
                    # synonym for the same species,
                    # this screws us up b/c you can now enter duplicate genera, somehow
                    # NOTE: we should at least warn the user that a duplicate is being entered
                    #genus = StringCol(length=50)    
                    Column('genus', String(64), unique='genus_index'),                
                    Column('hybrid', String(1), unique='genus_index'),                         
                    Column('author', Unicode(255), unique='genus_index'),
                    Column('qualifier', Enum(values=['s. lat.', 's. str', None],
                                             empty_to_none=True)),
                    Column('notes', Unicode),
                    #family = ForeignKey('Family', notNull=True, cascade=False)                    
                    Column('family_id', Integer, ForeignKey('family.id'), 
                           nullable=False, unique='genus_index'))
    
class Genus(bauble.BaubleMapper):
    
#    def __init__(self, genus, hybrid, author, qualifier, notes=None):
#        self.genus = genus
#        self.hybrid = hybrid
#        self.author = author
#        self.qualifier = qualifier
#        self.notes = qualifier
        
    def __str__(self):
        if self.hybrid:
            return '%s %s' % (self.hybrid, self.genus)
        else:
            return self.genus
    
    @staticmethod
    def str(genus, full_string=False):
        # TODO: should the qualifier be a standard part of the string, is it
        # standard as part of botanical nomenclature
        if full_string and genus.qualifier is not None:
            return '%s (%s)' % (str(genus), genus.qualifier)
        else:
            return str(genus)
        
genus_synonym_table = Table('genus_synonym',
                            Column('id', Integer, primary_key=True),
                            Column('genus_id', Integer, ForeignKey('genus.id'), 
                                   nullable=False),
                            Column('synonym_id', Integer, 
                                   ForeignKey('genus.id'), nullable=False))

class GenusSynonym(bauble.BaubleMapper):
    
#    def __init__(self, genus_id, synonym_id):
#        self.genus_id = genus_id
#        self.synonym_id = synonym_id
        
    def __str__(self):        
        return '(%s)' % self.synonym

from bauble.plugins.plants.species_model import Species

mapper(Genus, genus_table,
       properties = {'species': relation(Species, backref=backref('genus', lazy=False),
                                         order_by=['sp', 'infrasp_rank', 'infrasp']),
                     'synonyms': relation(GenusSynonym, backref='genus',
                                          primaryjoin=genus_synonym_table.c.genus_id==genus_table.c.id,
                                          order_by=['sp', 'infrasp_rank', 'infrasp'])},
       order_by=['genus', 'author'])

mapper(GenusSynonym, genus_synonym_table)
            
    
class GenusEditorView(GenericEditorView):
    
    #source_expanded_pref = 'editor.accesssion.source.expanded'

    def __init__(self, parent=None):
        GenericEditorView.__init__(self, os.path.join(paths.lib_dir(), 
                                                      'plugins', 'plants', 
                                                      'editors.glade'),
                                   parent=parent)
        self.widgets.genus_dialog.set_transient_for(parent)
        self.connect_dialog_close(self.widgets.genus_dialog)

        
    def save_state(self):
#        prefs[self.source_expanded_pref] = \
#            self.widgets.source_expander.get_expanded()
        pass
    
        
    def restore_state(self):
#        expanded = prefs.get(self.source_expanded_pref, True)
#        self.widgets.source_expander.set_expanded(expanded)
        pass

            
    def start(self):
        return self.widgets.genus_dialog.run()    
        

class GenusEditorPresenter(GenericEditorPresenter):
    
#    widget_to_field_map = {'acc_id_entry': 'acc_id',
#                           'acc_date_entry': 'date',
#                           'prov_combo': 'prov_type',
#                           'wild_prov_combo': 'wild_prov_status',
#                           'species_entry': 'species',
#                           'source_type_combo': 'source_type',
#                           'acc_notes_textview': 'notes'}
    
#    PROBLEM_INVALID_DATE = 3
#    PROBLEM_INVALID_SPECIES = 4
#    PROBLEM_DUPLICATE_ACCESSION = 5
    
    def __init__(self, model, view):
        '''
        @model: should be an instance of class Genus
        @view: should be an instance of GenusEditorView
        '''
        GenericEditorPresenter.__init__(self, ModelDecorator(model), view)
        self.session = object_session(model)

        # TODO: should we set these to the default value or leave them
        # be and let the default be set when the row is created, i'm leaning
        # toward the second, its easier if it works this way

        # initialize widgets

        self.refresh_view() # put model values in view            
        
        # connect signals
    def refresh_view(self):
        pass
    
    def start(self):
        return self.view.start()
    
    
class GenusEditor(GenericModelViewPresenterEditor):
    
    label = 'Genus'
    
    # these have to correspond to the response values in the view
    RESPONSE_OK_AND_ADD = 11
    RESPONSE_NEXT = 22
    ok_responses = (RESPONSE_OK_AND_ADD, RESPONSE_NEXT)    
        
        
    def __init__(self, model_or_defaults=None, parent=None):
        '''
        @param model_or_defaults: Genus instance or default values
        @param parent: None
        '''        
        if isinstance(model_or_defaults, dict):
            model = Genus(**model_or_defaults)
        elif model_or_defaults is None:
            model = Genus()
        elif isinstance(model_or_defaults, Genus):
            model = model_or_defaults
        else:
            raise ValueError('model_or_defaults argument must either be a '\
                             'dictionary or Genus instance')
        GenericModelViewPresenterEditor.__init__(self, model, parent)
        if parent is None: # should we even allow a change in parent
            parent = bauble.app.gui.window
        self.parent = parent
        
    
    _committed = [] # TODO: shouldn't be class level
    
    def handle_response(self, response):
        return True    
    
    def start(self):
        from bauble.plugins.plants.family import Family
        if self.session.query(Accession).count() == 0:        
            msg = 'You must first add or import at least one Family into the '\
                  'database before you can add plants.'
            utils.message_dialog(msg)
            return
        self.view = GenusEditorView(parent=self.parent)
        self.presenter = GenusEditorPresenter(self.model, self.view)
        
        exc_msg = "Could not commit changes.\n"
        committed = None
        while True:
            response = self.presenter.start()
            self.view.save_state() # should view or presenter save state
            if self.handle_response(response):
                break
            
        self.session.close() # cleanup session
        return self._committed
        
    #class Genus(BaubleTable):
    #
    #    class sqlmeta(BaubleTable.sqlmeta):
    #        defaultOrder = 'genus'
    #    
    #    # it is possible that there can be genera with the same name but 
    #    # different authors and probably means that at different points in literature
    #    # this name was used but is now a synonym even though it may not be a
    #    # synonym for the same species,
    #    # this screws us up b/c you can now enter duplicate genera, somehow
    #    # NOTE: we should at least warn the user that a duplicate is being entered
    #    genus = StringCol(length=50)    
    #            
    #    '''
    #    hybrid: indicates whether the name in the Genus Name field refers to an 
    #    Intergeneric hybrid or an Intergeneric graft chimaera.
    #    Content of genhyb   Nature of Name in gen
    #     H        An intergeneric hybrid collective name
    #     x        An Intergeneric Hybrid
    #     +        An Intergeneric Graft Hybrid or Graft Chimaera
    #    '''
    #    hybrid = EnumCol(enumValues=("H", "x", "+", None), default=None) 
    #    '''    
    #    The qualifier field designates the botanical status of the genus.
    #    Possible values:
    #        s. lat. - aggregrate family (sensu lato)
    #        s. str. segregate family (sensu stricto)
    #    '''
    #    qualifier = EnumCol(enumValues=('s. lat.', 's. str.', None), default=None)
    #    author = UnicodeCol(length=255, default=None)
    #    notes = UnicodeCol(default=None)
    #    
    #    # indices
    #    # we can't do this right now unless we do more work on 
    #    # the synonyms table, see 
    #    # {'author': 'Raf.', 'synonymID': 13361, 'familyID': 214, 'genus': 'Trisiola', 'id': 15845}
    #    # in Genus.txt
    #    genus_index = DatabaseIndex('genus', 'author', 'family', unique=True)
    #    
    #    # foreign keys
    #    family = ForeignKey('Family', notNull=True, cascade=False)
    #    
    #    # joins
    #    species = MultipleJoin("Species", joinColumn="genus_id")
    #    synonyms = MultipleJoin('GenusSynonym', joinColumn='genus_id')    
    #
    #
    #    def __str__(self):
    #        if self.hybrid:
    #            return '%s %s' % (self.hybrid, self.genus)
    #        else:
    #            return self.genus
    #    
    #    @staticmethod
    #    def str(genus, full_string=False):
    #        # TODO: should the qualifier be a standard part of the string, is it
    #        # standard as part of botanical nomenclature
    #        if full_string and genus.qualifier is not None:
    #            return '%s (%s)' % (str(genus), genus.qualifier)
    #        else:
    #            return str(genus)
    
            
    #class GenusSynonym(BaubleTable):
    #    
    #    # deleting either of the genera this synonym refers to makes this 
    #    # synonym irrelevant
    #    genus = ForeignKey('Genus', default=None, cascade=True)
    #    synonym = ForeignKey('Genus', cascade=True)
    #    
    #    def __str__(self):
    #        return self. synonym
    #
    #    def markup(self):
    #        return '%s (syn. of %f)' % (self.synonym, self.genus)
    
#
# editor
#
#class GenusEditor(TreeViewEditorDialog):
#
#    visible_columns_pref = "editor.genus.columns"
#    column_width_pref = "editor.genus.column_width"
#    default_visible_list = ['family', 'genus']
#    
#    label = 'Genus'
#    
#    def __init__(self, parent=None, select=None, defaults={}, **kwargs):
#        TreeViewEditorDialog.__init__(self, tables["Genus"], "Genus Editor", 
#                                      parent, select=select, defaults=defaults,
#                                      **kwargs)
#        titles = {'genus': 'Genus',
#                  'author': 'Author',
#                  'hybrid': 'Hybrid',
#                  'familyID': 'Family',
#                  'qualifier': 'Qualifier',
#                  'notes': 'Notes',
#                  'synonyms': 'Synonyms'}
#        self.columns.titles = titles
#        self.columns["familyID"].meta.get_completions = self.get_family_completions
#        self.columns['synonyms'].meta.editor = editors["GenusSynonymEditor"]
#
#
#    def get_family_completions(self, text):
#        model = gtk.ListStore(str, object)
#        sr = tables["Family"].select("family LIKE '"+text+"%'")
#        for row in sr:            
#            model.append([str(row), row])
#        return model
#
#
## 
## GenusSynonymEditor
##
#class GenusSynonymEditor(TreeViewEditorDialog):
#
#    visible_columns_pref = "editor.genus_syn.columns"
#    column_width_pref = "editor.genus_syn.column_width"
#    default_visible_list = ['synonym']
#    
#    standalone = False
#    label = 'Genus Synonym'
#    
#    def __init__(self, parent=None, select=None, defaults={}):
#        TreeViewEditorDialog.__init__(self, tables["GenusSynonym"],
#                                      "Genus Synonym Editor", 
#                                      parent, select=select, defaults=defaults, 
#                                      **kwargs)
#        titles = {'synonymID': 'Synonym of Genus'}
#                  
#        # can't be edited as a standalone so the family should only be set by
#        # the parent editor
#        self.columns.pop('genusID')
#        
#        self.columns.titles = titles
#        self.columns["synonymID"].meta.get_completions = self.get_genus_completions
#
#        
#    def get_genus_completions(self, text):
#        model = gtk.ListStore(str, object)
#        sr = tables["Genus"].select("genus LIKE '"+text+"%'")
#        for row in sr:
#            model.append([str(row), row])
#        return model
        
#
# infobox
#
try:
    from bauble.plugins.searchview.infobox import InfoBox, InfoExpander
except ImportError:
    pass
else:    
    from sqlalchemy.orm.session import object_session
    import bauble.paths as paths
    from bauble.plugins.plants.species_model import Species, species_table
    from bauble.plugins.garden.accession import Accession
    from bauble.plugins.garden.plant import Plant
    
    class GeneralGenusExpander(InfoExpander):
        '''
        expander to present general information about a genus
        '''
    
        def __init__(self, widgets):
            '''
            the constructor
            '''
            InfoExpander.__init__(self, "General", widgets)
            general_box = self.widgets.gen_general_box
            self.widgets.remove_parent(general_box)
            self.vbox.pack_start(general_box)
            
            
        def update(self, row):
            '''
            update the expander
            
            @param row: the row to get the values from
            '''
            self.set_widget_value('gen_name_data', str(row))
            session = object_session(row)
            
            species_query = session.query(Species)            
            species = species_query.table            
            nsp = species_query.count_by(genus_id = row.id)
            self.set_widget_value('gen_nsp_data', nsp)
            
            def get_unique_in_select(sel, col):
                return select([sel.c[col]], distinct=True).count().scalar()
            
            acc_query = session.query(Accession)
            accession = acc_query.table                     
            sp = select([species.c.id], species.c.genus_id==row.id)
            acc = accession.select(accession.c.species_id.in_(sp))     
            nacc = acc.count().scalar()
            nacc_str = str(nacc)
            if nacc > 0:
                nsp_with_accessions = get_unique_in_select(acc, 'species_id')
                nacc_str = '%s in %s species' % (nacc_str, nsp_with_accessions)
            
            plant_query = session.query(Plant)
            plant = plant_query.table
            acc_ids = select([acc.c.id])
            plants = plant.select(plant.c.accession_id.in_(acc_ids))
            nplants = plants.count().scalar()
            nplants_str = str(nplants)
            if nplants > 0:
                nacc_with_plants = get_unique_in_select(plants, 'accession_id')
                nplants_str = '%s in %s accessions' % (nplants_str, nacc_with_plants)                        
                
            self.set_widget_value('gen_nacc_data', nacc_str)
            self.set_widget_value('gen_nplants_data', nplants_str)
                
                
    class GenusInfoBox(InfoBox):
        """
        - number of taxon in number of accessions
        - references
        """
        def __init__(self):
            InfoBox.__init__(self)
            glade_file = os.path.join(paths.lib_dir(), 'plugins', 'plants', 
                                      'infoboxes.glade')            
            self.widgets = utils.GladeWidgets(gtk.glade.XML(glade_file))
            self.general = GeneralGenusExpander(self.widgets)
            self.add_expander(self.general)
        
        def update(self, row):
            self.general.update(row)
