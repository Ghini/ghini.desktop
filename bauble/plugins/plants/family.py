#
# Family table definition
#

import os, traceback
import gtk
from sqlalchemy import *
from sqlalchemy.orm.session import object_session
from sqlalchemy.exceptions import SQLError
import bauble
from bauble.editor import *
from datetime import datetime
import bauble.utils as utils
from bauble.utils.log import debug
from bauble.types import Enum


def edit_callback(row):
    value = row[0]    
    # TODO: the select paramater can go away when we move FamilyEditor to the 
    # new style editors    
    e = FamilyEditor(select=[value], model=value)
    return e.start() != None


def add_genera_callback(row):
    from bauble.plugins.plants.genus import GenusEditor    
    value = row[0]
    e = GenusEditor(defaults={'familyID': value})
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


family_context_menu = [('Edit', edit_callback),
                       ('--', None),
                       ('Add genera', add_genera_callback),
                       ('--', None),
                       ('Remove', remove_callback)]

        
def family_markup_func(family):
    '''
    '''
    return str(family)



#
# Family
#
family_table = Table('family',
                     Column('id', Integer, primary_key=True),
                     Column('family', String(45), unique='family_index', 
                            nullable=False),
                     Column('qualifier', Enum(values=['s. lat.', 's. str.', None],
                                              empty_to_none=True),
                           unique='family_index'))

family_synonym_table = Table('family_synonym',
                             Column('id', Integer, primary_key=True),
                             Column('family_id', Integer, 
                                    ForeignKey('family.id'), 
                                    nullable=False),
                             Column('synonym_id', Integer, 
                                    ForeignKey('family.id'), 
                                    nullable=False))

class Family(bauble.BaubleMapper):
#    def __init__(self, family, qualifier):
#        self.family = family
#        self.qualifier = qualifier
    
    def __str__(self): 
        # TODO: need ability to include the qualifier as part of the name, 
        # maybe as a keyworkd argument flag
        return Family.str(self)

    @staticmethod
    def str(family, full_string=False):
        if full_string and family.qualifier is not None:
            return '%s (%s)' % (family.family, family.qualifier)
        else:
            return family.family            
    
class FamilySynonym(bauble.BaubleMapper):
    
    # - deleting either of the families that this synonym refers to 
    # makes this synonym irrelevant
    # - here default=None b/c this can only be edited as a sub editor of,
    # Family, thoughwe have to be careful this doesn't create a dangling record
    # with no parent
    def __init__(self, family_id, synonym_id):
        self.family_id
        self.synonym_id
        
from bauble.plugins.plants.genus import Genus, genus_table
from bauble.plugins.plants.genus import Species, species_table
from bauble.plugins.garden.accession import Accession, accession_table
from bauble.plugins.garden.plant import Plant, plant_table

mapper(Family, family_table,
       properties = {'synonyms': relation(FamilySynonym, 
                                          primaryjoin=family_synonym_table.c.family_id==family_table.c.id,
                                          backref='family'),
                     'genera': relation(Genus, backref='family')})
mapper(FamilySynonym, family_synonym_table)
    
    
class FamilyEditorView(GenericEditorView):
    
    #source_expanded_pref = 'editor.accesssion.source.expanded'

    def __init__(self, parent=None):
        GenericEditorView.__init__(self, os.path.join(paths.lib_dir(), 
                                                      'plugins', 'plants', 
                                                      'editors.glade'),
                                   parent=parent)
        self.widgets.family_dialog.set_transient_for(parent)
        self.connect_dialog_close(self.widgets.family_dialog)

        
    def save_state(self):
#        prefs[self.source_expanded_pref] = \
#            self.widgets.source_expander.get_expanded()
        pass
    
        
    def restore_state(self):
#        expanded = prefs.get(self.source_expanded_pref, True)
#        self.widgets.source_expander.set_expanded(expanded)
        pass

            
    def start(self):
        return self.widgets.family_dialog.run()    
        

class FamilyEditorPresenter(GenericEditorPresenter):
    
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
        model: should be an instance of class Accession
        view: should be an instance of AccessionEditorView
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
    
    
class FamilyEditor(GenericModelViewPresenterEditor):
    
    label = 'Family'
    
    # these have to correspond to the response values in the view
    RESPONSE_OK_AND_ADD = 11
    RESPONSE_NEXT = 22
    ok_responses = (RESPONSE_OK_AND_ADD, RESPONSE_NEXT)    
        
        
    def __init__(self, model_or_defaults=None, parent=None):
        '''
        @param model_or_defaults: Plant instance or default values
        @param defaults: {}
        @param parent: None
        '''        
        if isinstance(model_or_defaults, dict):
            model = Family(**model_or_defaults)
        elif model_or_defaults is None:
            model = Family()
        elif isinstance(model_or_defaults, Family):
            model = model_or_defaults
        else:
            raise ValueError('model_or_defaults argument must either be a '\
                             'dictionary or Family instance')
        GenericModelViewPresenterEditor.__init__(self, model, parent)
        if parent is None: # should we even allow a change in parent
            parent = bauble.app.gui.window
        self.parent = parent
        
    
    _committed = [] # TODO: shouldn't be class level
    
    def handle_response(self, response):
        return True    
    
    def start(self):
        self.view = FamilyEditorView(parent=self.parent)
        self.presenter = FamilyEditorPresenter(self.model, self.view)
        
        exc_msg = "Could not commit changes.\n"
        committed = None
        while True:
            response = self.presenter.start()
            self.view.save_state() # should view or presenter save state
            if self.handle_response(response):
                break
            
        self.session.close() # cleanup session
        return self._committed

#class SO_Family(BaubleTable):
#
#    class sqlmeta(BaubleTable.sqlmeta):
#        defaultOrder = 'family'
#
#    family = StringCol(length=45, notNull=True)#, alternateID="True")
#    
#    '''    
#    The qualifier field designates the botanical status of the family.
#    Possible values:
#        s. lat. - aggregrate family (sensu lato)
#        s. str. segregate family (sensu stricto)
#    '''
#    qualifier = EnumCol(enumValues=('s. lat.', 's. str.', None), default=None)
#    notes = UnicodeCol(default=None)
#    
#    # indices
#    family_index = DatabaseIndex('family', 'qualifier', unique=True)    
#    
#    # joins
#    synonyms = MultipleJoin('FamilySynonym', joinColumn='family_id')    
#    genera = MultipleJoin("Genus", joinColumn="family_id")
#    
#        
#    def __str__(self): 
#        # TODO: need ability to include the qualifier as part of the name, 
#        # maybe as a keyworkd argument flag        
#        return self.family
#    
#    @staticmethod
#    def str(family, full_string=False):
#        if full_string and family.qualifier is not None:
#            return '%s (%s)' % (family.family, family.qualifier)
#        else:
#            return family.family
    
    
    
#class SO_FamilySynonym(BaubleTable):
#    
#    # - deleting either of the families that this synonym refers to makes this
#    # synonym irrelevant
#    # - here default=None b/c this can only be edited as a sub editor of,
#    # Family, thoughwe have to be careful this doesn't create a dangling record
#    # with no parent
#    family = ForeignKey('Family', default=None, cascade=True)
#    synonym = ForeignKey('Family', cascade=True)
#    
#    def __str__(self): 
#        return self.synonym


# 
# editor
#
#class FamilyEditor(TreeViewEditorDialog):
#
#    visible_columns_pref = "editor.family.columns"
#    column_width_pref = "editor.family.column_width"
#    default_visible_list = ['family', 'comments']
#    
#    label = 'Families'
#    
#    def __init__(self, parent=None, select=None, defaults={}, **kwargs):
#        
#        TreeViewEditorDialog.__init__(self, tables["Family"], "Family Editor", 
#                                      parent, select=select, defaults=defaults, 
#                                      **kwargs)
#        titles = {'family': 'Family',
#                  'notes': 'Notes',
#                  'qualifier': 'Qualifier',
#                  'synonyms': 'Synonyms'}
#        self.columns.titles = titles
#        self.columns['synonyms'].meta.editor = editors["FamilySynonymEditor"]
#
#
#
## 
## FamilySynonymEditor
##
#class FamilySynonymEditor(TreeViewEditorDialog):
#
#    visible_columns_pref = "editor.family_syn.columns"
#    column_width_pref = "editor.family_syn.column_width"
#    default_visible_list = ['synonym']
#    
#    standalone = False
#    label = 'Family Synonym'
#    
#    def __init__(self, parent=None, select=None, defaults={}, **kwargs):        
#        TreeViewEditorDialog.__init__(self, tables["FamilySynonym"],
#                                      "Family Synonym Editor", 
#                                      parent, select=select, 
#                                      defaults=defaults, **kwargs)
#        titles = {'synonymID': 'Synonym of Family'}
#                  
#        # can't be edited as a standalone so the family should only be set by
#        # the parent editor
#        self.columns.pop('familyID')
#        
#        self.columns.titles = titles
#        self.columns["synonymID"].meta.get_completions = self.get_family_completions
#
#        
#    def get_family_completions(self, text):
#        model = gtk.ListStore(str, object)
#        sr = tables["Family"].select("family LIKE '"+text+"%'")
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
    import bauble.paths as paths
    from bauble.plugins.plants.genus import Genus
    from bauble.plugins.plants.species_model import Species
    from bauble.plugins.garden.accession import Accession
    from bauble.plugins.garden.plant import Plant
    
    class GeneralFamilyExpander(InfoExpander):
        '''
        generic information about an family like number of genus, species,
        accessions and plants
        '''
    
        def __init__(self, widgets):
            '''
            the constructor
            '''
            InfoExpander.__init__(self, "General", widgets)
            general_box = self.widgets.fam_general_box
            self.widgets.remove_parent(general_box)                
            self.vbox.pack_start(general_box)
            
            
        def update(self, row):
            '''
            update the expander
            
            @param row: the row to get the values from
            '''            
            # TODO: see the way this is done in the GenusInfobox, i think it
            # cleaner and probably a bit faster            
            session = object_session(row)
            self.set_widget_value('fam_name_data', str(row))
            
            ngen = session.query(Genus).count_by(family_id=row.id) 
            self.set_widget_value('fam_ngen_data', ngen)
                   
            # get the number of species
            genus_ids = select([genus_table.c.id], genus_table.c.family_id==row.id)
            nsp = session.query(Species).count_by(species_table.c.genus_id.in_(genus_ids))              
            nsp_str = str(nsp)
            
            # get the unique genera from the species
            if nsp > 0:                
                all_species = select([species_table], species_table.c.genus_id.in_(genus_ids))
                
                # TODO: can these two lines be combined
                gen_ids_in_sp = select([genus_table.c.id], genus_table.c.id==all_species.c.genus_id)
                ngen_with_species = session.query(Genus).count_by(gen_ids_in_sp)        
                nsp_str = '%s in %s genera' % (nsp_str, ngen_with_species)            
                                             
            # get the number of accessions
            species_ids = select([species_table.c.id], 
                                 species_table.c.genus_id.in_(genus_ids))
            nacc = session.query(Accession).count_by(accession_table.c.species_id.in_(species_ids))
            nacc_str = str(nacc)
            if nacc > 0:
                # get the unique species from the accessions
                all_acc = select([accession_table], accession_table.c.species_id.in_(species_ids))            
                sp_ids_in_acc = select([species_table.c.id], species_table.c.id==all_acc.c.species_id)
                nsp_with_accessions = session.query(Species).count_by(sp_ids_in_acc)
                nacc_str = '%s in %s species' % (nacc_str, nsp_with_accessions)            
            
            # get the number of plants
            acc_ids = select([accession_table.c.id],
                             accession_table.c.species_id.in_(species_ids))
            nplants = session.query(Plant).count_by(plant_table.c.accession_id.in_(acc_ids))
            nplants_str = str(nplants)
            if nplants > 0:            
                # get the unique accession from the plants
                all_plants = select([plant_table], plant_table.c.accession_id.in_(acc_ids))
                acc_ids_in_plants = select([accession_table.c.id], accession_table.c.id==all_plants.c.accession_id)
                nacc_with_plants = session.query(Accession).count_by(acc_ids_in_plants)
                nplants_str = '%s in %s accessions' % (nplants_str, nacc_with_plants)            
                        
            self.set_widget_value('fam_nsp_data', nsp_str)
            self.set_widget_value('fam_nacc_data', nacc_str)
            self.set_widget_value('fam_nplants_data', nplants_str)
                
                
    class FamilyInfoBox(InfoBox):
        '''
        '''
        
        def __init__(self):
            '''
            '''
            InfoBox.__init__(self)
            glade_file = os.path.join(paths.lib_dir(), 'plugins', 'plants', 
                                      'infoboxes.glade')            
            self.widgets = utils.GladeWidgets(gtk.glade.XML(glade_file))
            self.general = GeneralFamilyExpander(self.widgets)
            self.add_expander(self.general)
        
        def update(self, row):
            '''
            '''
            self.general.update(row)