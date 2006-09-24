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
    e = FamilyEditor(model=value)
    return e.start() != None


def add_genera_callback(row):
    value = row[0]
    e = GenusEditor(Genus(family=value))
    return e.start() != None


def remove_callback(row):
    value = row[0]    
    s = '%s: %s' % (value.__class__.__name__, str(value))
    msg = "Are you sure you want to remove %s?" % s
    if not utils.yes_no_dialog(msg):
        return    
    try:
        session = create_session()
        obj = session.load(value.__class__, value.id)
        session.delete(obj)
        session.flush()
    except Exception, e:
        msg = 'Could not delete.\nn%s' % str(e)        
        utils.message_details_dialog(msg, traceback.format_exc(), 
                                     type=gtk.MESSAGE_ERROR)
    return True




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
                           unique='family_index'),
                     Column('notes', Unicode))

family_synonym_table = Table('family_synonym',
                             Column('id', Integer, primary_key=True),
                             Column('family_id', Integer, 
                                    ForeignKey('family.id'), 
                                    nullable=False),
                             Column('synonym_id', Integer, 
                                    ForeignKey('family.id'), 
                                    nullable=False))

class Family(bauble.BaubleMapper):
    
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
        
from bauble.plugins.plants.genus import Genus, genus_table, GenusEditor
#from bauble.plugins.plants.genus import Species, species_table
from bauble.plugins.garden.accession import Accession, accession_table
from bauble.plugins.garden.plant import Plant, plant_table

mapper(Family, family_table,
       properties = {'synonyms': relation(FamilySynonym, 
                                          primaryjoin=family_synonym_table.c.family_id==family_table.c.id,
                                          backref='family'),
                     'genera': relation(Genus, backref='family')})
#                     'genera': relation(Genus, cascade='all, delete-orphan',
#                                        backref=backref('family', cascade='all'))})
mapper(FamilySynonym, family_synonym_table)
    
    
class FamilyEditorView(GenericEditorView):
    
    syn_expanded_pref = 'editor.family.synonyms.expanded'

    def __init__(self, parent=None):
        GenericEditorView.__init__(self, os.path.join(paths.lib_dir(), 
                                                      'plugins', 'plants', 
                                                      'editors.glade'),
                                   parent=parent)
        self.widgets.family_dialog.set_transient_for(parent)
        self.connect_dialog_close(self.widgets.family_dialog)

    def save_state(self):
        prefs[self.syn_expanded_pref] = \
            self.widgets.fam_syn_expander.get_expanded()    

        
    def restore_state(self):
        expanded = prefs.get(self.syn_expanded_pref, True)
        self.widgets.fam_syn_expander.set_expanded(expanded)        

            
    def start(self):
        return self.widgets.family_dialog.run()    
        

class FamilyEditorPresenter(GenericEditorPresenter):
    
    widget_to_field_map = {'fam_family_entry': 'family',
                           'fam_qualifier_combo': 'qualifier',
                           'fam_notes_textview': 'notes'}
    
    def __init__(self, model, view):
        '''
        @param model: should be an instance of class Accession
        @param view: should be an instance of AccessionEditorView
        '''
        GenericEditorPresenter.__init__(self, ModelDecorator(model), view)
        self.session = object_session(model)

        # initialize widgets
        self.init_enum_combo('fam_qualifier_combo', 'qualifier')

        self.refresh_view() # put model values in view            
        
        # connect signals
        self.assign_simple_handler('fam_family_entry', 'family')
        self.assign_simple_handler('fam_qualifier_combo', 'qualifier')
        self.assign_simple_handler('fam_notes_textview', 'notes')
        
        
    def refresh_view(self):
        for widget, field in self.widget_to_field_map.iteritems():
            value = self.model[field]
            self.view.set_widget_value(widget, value)
            
    
    def start(self):
        return self.view.start()
    
    
class FamilyEditor(GenericModelViewPresenterEditor):
    
    label = 'Family'
    
    # these have to correspond to the response values in the view
    RESPONSE_OK_AND_ADD = 11
    RESPONSE_NEXT = 22
    ok_responses = (RESPONSE_OK_AND_ADD, RESPONSE_NEXT)    
        
        
    def __init__(self, model=None, parent=None):
        '''
        @param model: Family instance or None
        @param parent: the parent window or None
        '''        
        if model is None:
            model = Family()

        GenericModelViewPresenterEditor.__init__(self, model, parent)
        if parent is None: # should we even allow a change in parent
            parent = bauble.app.gui.window
        self.parent = parent
        self._committed = []
    
    
    def handle_response(self, response):
        '''
        @return: return a list if we want to tell start() to close the editor, 
        the list should either be empty or the list of committed values, return 
        None if we want to keep editing
        '''
        not_ok_msg = 'Are you sure you want to lose your changes?'
        committed = []
        if response == gtk.RESPONSE_OK or response in self.ok_responses:
            try:
                self.commit_changes()
                committed.append(self.model)
            except SQLError, e:                
                msg = 'Error committing changes.\n\n%s' % e.orig
                utils.message_details_dialog(msg, str(e), gtk.MESSAGE_ERROR)
                return None
            except:
                msg = 'Unknown error when committing changes. See the details '\
                      'for more information.'
                utils.message_details_dialog(msg, traceback.format_exc(), 
                                             gtk.MESSAGE_ERROR)
                return None
        elif self.session.dirty and utils.yes_no_dialog(not_ok_msg) or not self.session.dirty:
            return []
        else:
            return None
                
        # respond to responses
        more_committed = None
        if response == self.RESPONSE_NEXT:
            e = FamilyEditor(parent=self.parent)
            more_committed = e.start()
        elif response == self.RESPONSE_OK_AND_ADD:
            e = GenusEditor(parent=self.parent, 
                            model_or_defaults={'family_id': committed[0].id})
            more_committed = e.start()
                      
        if more_committed is not None:
            if isinstance(more_committed, list):
                self._committed.extend(more_committed)
            else:
                self._committed.append(more_committed)                
        
        return committed            
        
    
    def start(self):
        self.view = FamilyEditorView(parent=self.parent)
        self.presenter = FamilyEditorPresenter(self.model, self.view)
        
        exc_msg = "Could not commit changes.\n"
        committed = None
        while True:
            response = self.presenter.start()
            self.view.save_state() # should view or presenter save state
            committed = self.handle_response(response)
            if committed is not None:
                break
            
        self.session.close() # cleanup session
        return committed

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
# Family infobox
#

# TODO: need to hook up the notes box

try:
    from bauble.plugins.searchview.infobox import InfoBox, InfoExpander    
except ImportError, e:    
    pass
else:    
    import bauble.paths as paths
    from bauble.plugins.plants.genus import Genus
    from bauble.plugins.plants.species_model import Species, species_table
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
            def get_unique_in_select(sel, col):
                return select([sel.c[col]], distinct=True).count().scalar()
            def count_select(sel):
                return sel.count().scalar()
                        
            self.set_widget_value('fam_name_data', str(row))
            
            # get the number of genera
            genus_ids = select([genus_table.c.id], genus_table.c.family_id==row.id)
            ngen = count_select(genus_ids)
            self.set_widget_value('fam_ngen_data', ngen)
            
            # get the number of species
            sp = species_table.select(species_table.c.genus_id.in_(genus_ids))
            nsp_str = str(count_select(sp))
            if nsp_str != '0': 
                ngen_with_species = get_unique_in_select(sp, 'genus_id')
                nsp_str = '%s in %s genera' % (nsp_str, ngen_with_species)            
            self.set_widget_value('fam_nsp_data', nsp_str)
            
            # get the number of accessions
            species_ids = select([sp.c.id])
            acc = accession_table.select(accession_table.c.species_id.in_(species_ids))
            nacc_str = str(count_select(acc))
            if nacc_str != '0':
                nsp_with_accessions = get_unique_in_select(acc, 'species_id')
                nacc_str = '%s in %s species' % (nacc_str, nsp_with_accessions)            
            self.set_widget_value('fam_nacc_data', nacc_str)
            
            # get the number of plants
            acc_ids = select([acc.c.id])
            plants = plant_table.select(plant_table.c.accession_id.in_(acc_ids))
            nplants_str = str(count_select(plants))
            if nplants_str != '0':
                nacc_with_plants = get_unique_in_select(plants, 'accession_id')
                nplants_str = '%s in %s accessions' % (nplants_str, nacc_with_plants)
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