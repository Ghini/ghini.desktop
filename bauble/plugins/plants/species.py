#
# Species table definition
#
import os
import gtk
from sqlobject import *
import bauble.utils as utils
import bauble.paths as paths
import bauble
from bauble.plugins import BaubleTable, tables, editors
from bauble.treevieweditor import TreeViewEditorDialog, ComboColumn, TextColumn
from bauble.utils.log import log, debug
import xml.sax.saxutils as sax
#from speciesmeta import SpeciesMeta

# TODO: SpeciesMetaEditor isn't modal on the SpeciesEditor
    
#
# Species table
#
class Species(BaubleTable):

    class sqlmeta(BaubleTable.sqlmeta):
        defaultOrder = 'sp'
    
    def __init__(self, **kw):
        super(Species, self).__init__(**kw)
        self.__cached_str = None
        
    # TODO: create an index from sp_hybrid, sp_qual, sp, sp_author, cv_group, 
    # isp, isp_author, isp_rank, genus
    #species_index = DatabaseIndex('genus', 'sp', 'sp_author', 'sp_hybrid', 
    #                             'sp_qual', 'cv_group', 'infrasp', 
    #                             'infrasp_author', 'infrasp_rank')
    sp = StringCol(length=40, notNull=True)          # specific epithet
    sp_author = UnicodeCol(default=None)  # species author    
    sp_hybrid = EnumCol(enumValues=("H", "x", "+",None), default=None) 
    
    
    sp_qual = EnumCol(enumValues=("agg.", "s.lat.", "s. str.", None), 
                      default=None)                                                
    cv_group = StringCol(length=50, default=None)    # cultivar group                        
    infrasp = StringCol(length=30, default=None)         # intraspecific epithet
    infrasp_author = UnicodeCol(length=255, default=None) # intraspecific author
    '''
    subsp. - subspecies
    var. - variety
    subvar. - sub variety
    f. - form
    subf. - subform
    cv. - cultivar
    '''
    infrasp_rank = EnumCol(enumValues=("subsp.", "var.", "subvar.", "f.", 
                                       "subf.",  "cv.", None), default=None)
#    isp = StringCol(length=30, default=None)         # intraspecific epithet
#    isp_author = UnicodeCol(length=255, default=None) # intraspecific author
#    # intraspecific rank
#    isp_rank = EnumCol(enumValues=("subsp.", # subspecies
#                                   "var.",   # variety
#                                   "subvar.", # sub variety
#                                   "f.",     # form
#                                   "subf.",  # subform
#                                   "cv.",    # cultivar
#                                   None), 
#                       default=None)

    
    #rank_qual = StringCol(length=1, default=None) # rank qualifier, a single
    # character
    '''
    "aff.", # Akin to or bordering
    "cf.", # compare with
    "Incorrect", # Incorrect
    "forsan", # Perhaps
    "near", # Close to
    "?", # Quesionable
    '''
    id_qual = EnumCol(enumValues=("aff.", "cf.", "Incorrect", "forsan", "near", 
                                  "?", None), default=None)    
    notes = UnicodeCol(default=None)
    
    # foreign keys
    default_vernacular_name = ForeignKey('VernacularName', default=None)#, 
                                         #cascade=True)
    genus = ForeignKey('Genus', notNull=True, cascade=False)
    #
    # joins
    #
    # hold meta information about this plant
    species_meta = SingleJoin('SpeciesMeta', joinColumn='species_id')
    synonyms = MultipleJoin('SpeciesSynonym', joinColumn='species_id')
    # it would be best to display the vernacular names in a dropdown list
    # with a way to add to the list    
    # FIXME: what happens if to the value in default_vernacular_name if 
    # we delete the object that this foreign key points to, should somehow
    # get reset to None
    vernacular_names = MultipleJoin('VernacularName', joinColumn='species_id')
    #accessions = MultipleJoin('Accessions', joinColumn='species_id')
    #images = MultipleJoin('Images', joinColumn='species_id')
    #references = MultipleJoin('Reference', joinColumn='species_id')
    
    def __str__(self):
        # we'll cache the str(self) since building it is relatively heavy
        # TODO: we can't enable this until we can invalidated _cached_str in
        # cache self is changed
        #if self.__cached_str is None:
        #    self.__cached_str = Species.str(self)
        #return self.__cached_str        
        return Species.str(self)
    
    
    def markup(self, authors=False):
        return Species.str(self, authors, True)
    
    
    @staticmethod
    def str(species, authors=False, markup=False):
        """
        return the full plant name string
        NOTE: it may be better to create a separate method for the markup
        since substituting into the italic make slow things down, should do 
        some benchmarks. also, which is faster, doing substitution this way or
        by using concatenation
        """    
        # TODO: should do a translation table for any entities that might
        # be in the author strings and use translate, what else besided 
        # ampersand could be in the author name
        # TODO: how complete is this for the latest nomenclature code?
        # TODO: optimize: (1) be sure to use % substitution in instead of +=, 
        # (2) maybe create the name in parts and return them all combined in 
        # the end
        # TODO: create tests for all possible name combinations 
        #genus, sp_hybrid, id_qual, sp, sp_hybrid, infrasp, cv_group
        if markup:
            italic = "<i>%s</i>"
	    escape = sax.escape
        else:
            italic = "%s"
	    escape = lambda x: x        
        name = italic % str(species.genus)

        # id qualifier
        if species.id_qual:
            name += " %s" % species.id_qual
            
        # take care of species hybrid
        if species.sp_hybrid:
            # we don't have a second sp name for the hyrbid formula right now
            # so we'll just use the isp for now
            if species.infrasp is not None:
                name += " %s %s %s " % (italic % species.sp, 
                                        species.sp_hybrid,
                                        italic % species.infrasp)
            else:
                name += ' %s %s' % (species.sp_hybrid or '', species.sp)
        else:
            name = ' '.join([name, italic % species.sp])
            
        # cultivar groups and cultivars
        if species.cv_group is not None:
            if species.infrasp_rank == "cv.":
                name += ' (' + species.cv_group + " Group) '" + \
                italic % species.infrasp + "'"
            else: 
                name += ' ' + species.cv_group + ' Group'
            return name
        
        if species.sp_author is not None and authors is not False:
            #name += ' ' + species.sp_author.replace('&', '&amp;')
            name += ' ' + escape(species.sp_author)
        
        if species.infrasp_rank:
            if species.infrasp_rank == "cv.":
                name += " '" + species.infrasp + "'"
            else:
                name = '%s %s %s' % (name, species.infrasp_rank, 
                                     italic % species.infrasp)
                if species.infrasp_author is not None and authors is not False:
                    name += ' ' + escape(species.infrasp_author)
        return name
    

    
class SpeciesSynonym(BaubleTable):
    # deleting either of the species this synonym refers to makes
    # this synonym irrelevant
    species = ForeignKey('Species', default=None, cascade=True)
    synonym = ForeignKey('Species', cascade=True)
    


class VernacularNameColumn(TextColumn):
        
    def __init__(self, tree_view_editor, header):
        # this is silly to have the get the join this way
        vern_join = None
        for j in Species.sqlmeta.joins: 
            if j.joinMethodName == 'vernacular_names':
                vern_join = j
                break
        assert vern_join is not None
        super(VernacularNameColumn, self).__init__(tree_view_editor, header,
               so_col=vern_join)
        self.meta.editor = editors['VernacularNameEditor']

    
    def _start_editor(self, path):        
        model = self.table_editor.view.get_model()
        row = model[model.get_iter(path)][0]
        existing = row[self.name]
        old_committed = []
        select = None    
        if isinstance(existing, tuple): # existing/pending pair
            existing, old_committed = existing
            if existing is None: # nothing already exist
                select = old_committed
            else:
                select = existing+old_committed
        else:
            select = existing
        e = self.meta.editor(select=select,
                             default_name=row['default_vernacular_nameID'])
        returned = e.start(False)
        if returned is None:
            return
        default_name, committed_names = returned # unpack
        if default_name is not None and committed_names is not None:
            model = self.table_editor.view.get_model()
            i = model.get_iter(path)
            row = model.get_value(i, 0)
            row['default_vernacular_nameID'] = default_name
            if committed_names is not None and len(committed_names) > 0:
                row['vernacular_names'] = (existing, 
                                           old_committed+committed_names)
            # why do we emit edited? to set the values in the model
            self.renderer.emit('edited', path, default_name) 
            self.dirty = True


    def cell_data_func(self, column, renderer, model, iter, data=None):
        row = model.get_value(iter, 0)
        all_names = row[self.name]
        if row.committed:
            renderer.set_property('sensitive', False)
            renderer.set_property('editable', False)
        else:
            renderer.set_property('sensitive', True)
            renderer.set_property('editable', True)        

        if all_names is not None:
            default_name = row['default_vernacular_nameID']            
            #debug(default_name)
            if isinstance(all_names, tuple): 
                existing, pending = all_names
                if existing is None:
                    renderer.set_property('text', '%s (%s pending)' \
                                      % (default_name, len(pending)))
                else:
                    renderer.set_property('text', '%s (%s names, %s pending)' \
                                          % (default_name, len(existing), 
                                             len(pending)))
            else:
                renderer.set_property('text', '%s (%s names)' \
                                      % (default_name, len(all_names)))                                      
        else:
            renderer.set_property('text', None)


#
# Species editor
#
class SpeciesEditor(TreeViewEditorDialog):
    
    visible_columns_pref = "editor.species.columns"
    column_width_pref = "editor.species.column_width"
    default_visible_list = ['genus', 'sp']
    
    label = 'Species'
    
    def __init__(self, parent=None, select=None, defaults={}):  
        TreeViewEditorDialog.__init__(self, tables["Species"],
                                      "Species Editor", parent,
                                      select=select, defaults=defaults)
        titles = {"genusID": "Genus",
		  "sp": "Species",
		  "sp_hybrid": "Sp. hybrid",
		  "sp_qual": "Sp. qualifier",
		  "sp_author": "Sp. author",
		  "cv_group": "Cv. group",
#                   "cv": "Cultivar",
#                   "trades": "Trade name",
#                   "supfam": 'Super family',
#                   'subgen': 'Subgenus',
#                   'subgen_rank': 'Subgeneric rank',
		  'infrasp': 'Isp. epithet',
		  'infrasp_rank': 'Isp. rank',
		  'infrasp_author': 'Isp. author',
#                   'iucn23': 'IUCN 2.3\nCategory',
#                   'iucn31': 'IUCN 3.1\nCategory',
		  'id_qual': 'ID qualifier',
#                   'distribution': 'Distribution'
		  'species_meta': 'Meta Info',
		  'notes': 'Notes',
#                    'default_vernacular_nameID': 'Vernacular Names',
		  'synonyms': 'Synonyms',
		  'vernacular_names': 'Vernacular Names',
		  }

        # make a custom distribution column
#        self.columns.pop('distribution') # this probably isn't necessary     
#        dist_column = ComboColumn(self.view, 'Distribution',
#                           so_col = Species.sqlmeta.columns['distribution'])
#        dist_column.model = self.make_model()
#        self.columns['distribution'] = dist_column                    
        #self.columns['species_meta'] = \
        #    TextColumn(self.view, 'Species Meta', so_col=Species.sqlmeta.joins['species_meta'])
        #self.columns['default_vernacular_nameID'] = \
        
        # remove the default vernacular name column have this set
        # by the VernacularNameColumn, but we have to make sure that the
        # default vernacular name is listed in the foreign keys or we'll 
        # commit_changes won't know to set it
        
        self.columns.pop('default_vernacular_nameID')
        #self.columns.foreign_keys.append('default_vernacular_nameID')
        self.columns['vernacular_names'] = \
            VernacularNameColumn(self, 'Vernacular Names')
        
        self.columns['species_meta'].meta.editor = editors["SpeciesMetaEditor"]
        self.columns.titles = titles                     
                     
        # set completions
        self.columns["genusID"].meta.get_completions= self.get_genus_completions
        self.columns['synonyms'].meta.editor = editors["SpeciesSynonymEditor"]
    
        
#    def commit_changes_NO(self):
#        # TODO: speciess are a complex typle where more than one field
#        # make the plant unique, write a custom commit_changes to get the value
#        # from the table as a dictionary, convert this dictionary to 
#        # an object that can be accessed by attributes so it mimic a 
#        # Species object, pass the dict to species2str and test
#        # that a species with the same name doesn't already exist in the 
#        # database, if it does exist then ask the use what they want to do
#        #super(SpeciesEditor, self).commit_changes()
#        values = self.get_values_from_view()
    
          
    def _model_row_to_values(self, row):    
        # need to test each of the values that make up the species
        # against the database, not just the string, i guess we need to
        # check each of the keys in values, check if they are name components
        # use each of these values in a query to speciess
	values = super(SpeciesEditor, self)._model_row_to_values(row)
	if values is None:
	    return values

        if values.has_key('id'):
            return values
        exists = False
        select_values = {}
        try:
            select_values['genusID'] = values['genusID'].id
            select_values['sp'] = values['sp']        
        except KeyError, e:
            raise bauble.BaubleError('You must enter the required field %s' %e)
            
        sel = Species.selectBy(**select_values)
        names = ""
        for s in sel:
            exists = True
            names += "%d: %s\n" % (s.id, s)
        msg  = "The following plant names are similiar to the plant name you "\
               "are trying to create. Are your sure this is what you want to "\
               "do?\n\n" + names
        if exists and not utils.yes_no_dialog(msg):
            return None
        return values


    def get_genus_completions(self, text):
        model = gtk.ListStore(str, object)
        sr = tables["Genus"].select("genus LIKE '"+text+"%'")        
        for row in sr: 
            model.append([str(row), row])
        return model
                
    
    def on_genus_completion_match_selected(self, completion, model, 
                                           iter, path):
        """
        all foreign keys should use entry completion so you can't type in
        values that don't already exists in the database, therefore, allthough
        i don't like it the view.model.row is set here for foreign key columns
        and in self.on_renderer_edited for other column types                
        """        
        genus = model.get_value(iter, 1)
        self.set_view_model_value(path, "genusID", genus)        
        
                                    
#    def make_model(self):
#        model = gtk.TreeStore(str)
#        model.append(None, ["Cultivated"])
#        for continent in tables['Continent'].select(orderBy='continent'):
#            p1 = model.append(None, [str(continent)])
#            for region in continent.regions:
#                p2 = model.append(p1, [str(region)])
#                for country in region.botanical_countries:
#                    p3 = model.append(p2, [str(country)])
#                    for unit in country.units:
#                        if str(unit) != str(country):
#                            model.append(p3, [str(unit)])    
#        return model
                            
      
    def foreign_does_not_exist(self, name, value):
        self.add_genus(value)    


    def add_genus(self, name):
        msg = "The Genus %s does not exist. Would you like to add it?" % name
        if utils.yes_no_dialog(msg):
            print "add genus"

        

# 
# SpeciesSynonymEditor
#
class SpeciesSynonymEditor(TreeViewEditorDialog):

    visible_columns_pref = "editor.species_syn.columns"
    column_width_pref = "editor.species_syn.column_width"
    default_visible_list = ['synonym']
    
    standalone = False
    label = 'Species Synonym'
    
    def __init__(self, parent=None, select=None, defaults={}):        
        TreeViewEditorDialog.__init__(self, tables["SpeciesSynonym"], \
                                      "Species Synonym Editor", 
                                      parent, select=select, 
                                      defaults=defaults)
        titles = {'synonymID': 'Synonym of Species'}
                  
        # can't be edited as a standalone so the species should only be set by
        # the parent editor
        self.columns.pop('speciesID')
        
        self.columns.titles = titles
        self.columns["synonymID"].meta.get_completions = \
            self.get_species_completions


    def get_species_completions(self, text):
        # get entry and determine from what has been input which
        # field is currently being edited and give completion
        # if this return None then the entry will never search for completions
        # TODO: finish this, it would be good if we could just stick
        # the table row in the model and tell the renderer how to get the
        # string to match on, though maybe not as fast, and then to get
        # the value we would only have to do a row.id instead of storing
        # these tuples in the model
        # UPDATE: the only problem with sticking the table row in the column
        # is how many queries would it take to screw in a lightbulb, this
        # would be easy to test it just needs to be done
        # TODO: there should be a better/faster way to do this 
        # using a join or something
        parts = text.split(" ")
        genus = parts[0]
        sr = tables["Genus"].select("genus LIKE '"+genus+"%'")
        model = gtk.ListStore(str, object) 
        for row in sr:
#            debug(str(row))
            for species in row.species:                
                model.append((str(species), species))
        return model
    
    
    
try:
    from bauble.plugins.searchview.infobox import InfoBox, InfoExpander, \
        set_widget_value
except ImportError:
    pass
else:

# TODO: add the vernacular names to the species infobox, maybe like
# English: name1, name2
# Spanish: name1
# or
# name1 (English), name2 (English), name3 (English), etc
    
#    
# Species infobox for SearchView
#
    class GeneralSpeciesExpander(InfoExpander):
        """
        generic information about an accession like
        number of clones, provenance type, wild provenance type, speciess
        """
    
        def __init__(self, glade_xml):
            InfoExpander.__init__(self, "General", glade_xml)
            w = self.glade_xml.get_widget('general_box')
            main_window = self.glade_xml.get_widget('main_window')
            main_window.remove(w)            
            self.vbox.pack_start(w)
        
        
        def update(self, row):
            set_widget_value(self.glade_xml, 'name_data', row.markup(True))
            set_widget_value(self.glade_xml, 'nacc_data', len(row.accessions))
            
            nplants = 0
            for acc in row.accessions:
                nplants += len(acc.plants)
            set_widget_value(self.glade_xml, 'nplants_data', nplants)    
    
    
    class SpeciesInfoBox(InfoBox):
        """
        - general info, fullname, common name, num of accessions and clones
        - reference
        - images
        - redlist status
        - poisonous to humans
        - poisonous to animals
        - food plant
        - origin/distrobution
        """
        def __init__(self):
            """ 
            fullname, synonyms, ...
            """
            InfoBox.__init__(self)
            path = os.path.join(paths.lib_dir(), "plugins", "plants")
            self.glade_xml = gtk.glade.XML(path + os.sep + 
					   "species_infobox.glade")
            
            self.general = GeneralSpeciesExpander(self.glade_xml)
            self.add_expander(self.general)
            
            #self.ref = ReferenceExpander()
            #self.ref.set_expanded(True)
            #self.add_expander(self.ref)
            
            #img = ImagesExpander()
            #img.set_expanded(True)
            #self.add_expander(img)
            
            
        def update(self, row):
            self.general.update(row)
            #self.ref.update(row.references)
            #self.ref.value = row.references
            #ref = self.get_expander("References")
            #ref.set_values(row.references)
        
