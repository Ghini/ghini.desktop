#
# Species table definition
#
import os
import gtk
from sqlobject import *
import bauble.utils as utils
import bauble.paths as paths
import bauble
from bauble.plugins import tables, editors
from bauble.treevieweditor import TreeViewEditorDialog, ComboColumn, TextColumn
from bauble.editor import *
from bauble.utils.log import log, debug
import xml.sax.saxutils as sax
from bauble.plugins.plants.species_model import Species, SpeciesMeta, \
    SpeciesSynonym, VernacularName

# TODO: SpeciesMetaEditor isn't modal on the SpeciesEditor    

class SpeciesEditorPresenter(GenericEditorPresenter):
    
    
    def __init__(self, model, view, defaults={}):
        GenericEditorPresenter.__init__(self, model, view)
        self.defaults = defaults
        
        self.vern_presenter = None #VernacularNamePresenter()
        self.synonyms_presenter = None #SynonymsPresenter()
        self.meta_presenter = None #SpeciesMetaPresenter()
        self.sub_presenters = (self.vern_presenter, self.synonyms_presenter, self.meta_presenter)
    
    def init_genus_entry(self):
        pass
        
    def start(self):
        return self.view.start()
        
        
    def refresh_view(self):
        for presenter in self.sub_presenters:
            presenter.refresh_view()
        
    
        
class VernacularNamePresenter(GenericEditorPresenter):
    
    def __init__(self, model, view, defaults={}):
        GenericEditorPresenter.__init__(self, model, view)        
    
    
    def refresh_view(self):
        pass
    
    
    
class SynonymsPresenter(GenericEditorPresenter):
    
    def __init__(self, model, view, defaults={}):
        GenericEditorPresenter.__init__(self, model, view)        
        
        
    def refresh_view(self):
        pass
    
    
class SpeciesMetaPresenter(GenericEditorPresenter):    
    
    def __init__(self, model, view, defaults={}):
        GenericEditorPresenter.__init__(self, model, view)        
        
        
    def refresh_view(self):
        pass
    
    

class SpeciesEditorView(GenericEditorView):
    def __init__(self, parent=None):
        GenericEditorView.__init__(self, os.path.join(paths.lib_dir(), 
                                                      'plugins', 'plants', 
                                                      'editors.glade'),
                                   parent=parent)
        self.dialog = self.widgets.species_dialog
        self.dialog.set_transient_for(parent)
        
        # configure genus_entry
        completion = gtk.EntryCompletion()    
        completion.set_match_func(self.genus_completion_match_func)        
        r = gtk.CellRendererText() # set up the completion renderer
        completion.pack_start(r)
        completion.set_cell_data_func(r, self.genus_cell_data_func)        
        #completion.set_text_column(0)    
        completion.set_minimum_key_length(2)
        completion.set_popup_completion(True)                 
        self.widgets.sp_genus_entry.set_completion(completion)
        self.restore_state()
        # TODO: set up automatic signal handling, all signals should be called
        # on the presenter
        self.connect_dialog_close(self.widgets.species_dialog)
        if sys.platform == 'win32':
            self.do_win32_fixes()
            
    def genus_completion_match_func(self, completion, key_string, iter, 
                                    data=None):
        '''
        the only thing this does different is it make the match case insensitve
        '''
        value = completion.get_model()[iter][0]
        return str(value).lower().startswith(key_string.lower())   
        
    def genus_cell_data_func(self, column, renderer, model, iter, data=None):
        v = model[iter][0]
        renderer.set_property('text', str(v))
        
    def do_win32_fixes(self):
        pass
        
    expanders_pref_map = {'sp_infra_expander': 'editor.species.infra.expanded', 
                          'sp_qual_expander': 'editor.species.qual.expanded',
                          'sp_meta_expander': 'editor.species.meta.expanded'}
    def save_state(self):        
        for expander, pref in self.expanders_pref_map.iteritems():
            prefs[pref] = self.widgets[expander].get_expanded()
        
        
    def restore_state(self):
        for expander, pref in self.expanders_pref_map.iteritems():
            expanded = prefs.get(pref, True)
            self.widgets[expander].set_expanded(expanded)

            
    def start(self):
        return self.widgets.species_dialog.run()    
    

class SpeciesEditor(GenericModelViewPresenterEditor):
    
    label = 'Species'
    # these have to correspond to the response values in the view
    RESPONSE_OK_AND_ADD = 11
    RESPONSE_NEXT = 22
    ok_responses = (RESPONSE_OK_AND_ADD, RESPONSE_NEXT)    
    
    def __init__(self, model=Species, defaults={}, parent=None, **kwargs):
        self.assert_args(model, Species, defaults)
        GenericModelViewPresenterEditor.__init__(self, model, defaults, parent)
        if parent is None: # should we even allow a change in parent
            parent = bauble.app.gui.window
        # keep parent and defaults around in case in start() we get
        # RESPONSE_NEXT or RESPONSE_OK_AND_ADD we can pass them to the new 
        # editor
        self.parent = parent
        self.defaults = defaults 
        self.view = SpeciesEditorView(parent=parent)
        self.presenter = SpeciesEditorPresenter(self.model, self.view,
                                                self.defaults)
        
    def start(self, commit_transaction=True):    
        not_ok_msg = 'Are you sure you want to lose your changes?'
        exc_msg = "Could not commit changes.\n"
        committed = None
        while True:
            response = self.presenter.start()
            self.view.save_state() # should view or presenter save state
            vernacular_dirty = self.presenter.vern_presenter is not None and \
                self.presenter.vern_presenter.model.dirty
            synonyms_dirty = self.presenter.synonyms_presenter is not None and\
                self.presenter.synonyms_presenter.model.dirty
            meta_dirty = self.presenter.meta_presenter is not None and\
                self.presenter.meta_presenter.model.dirty
            sub_presenters_dirty = vernacular_dirty or synonyms_dirty or meta_dirty
            if response == gtk.RESPONSE_OK or response in self.ok_responses:
                try:
                    committed = self.commit_changes()                
                except DontCommitException:
                    continue
                except BadValue, e:
                    utils.message_dialog(saxutils.escape(str(e)),
                                         gtk.MESSAGE_ERROR)
                except CommitException, e:
                    debug(traceback.format_exc())
                    exc_msg + ' \n %s\n%s' % (str(e), e.row)
                    utils.message_details_dialog(saxutils.escape(exc_msg), 
                                 traceback.format_exc(), gtk.MESSAGE_ERROR)
                    sqlhub.processConnection.rollback()
                    sqlhub.processConnection.begin()
                except Exception, e:
                    debug(traceback.format_exc())
                    exc_msg + ' \n %s' % str(e)
                    utils.message_details_dialog(saxutils.escape(exc_msg), 
                                                 traceback.format_exc(),
                                                 gtk.MESSAGE_ERROR)
                    sqlhub.processConnection.rollback()
                    sqlhub.processConnection.begin()
                else:
                    break
            elif (self.model.dirty or sub_presenters_dirty) and utils.yes_no_dialog(not_ok_msg):
                sqlhub.processConnection.rollback()
                sqlhub.processConnection.begin()
                self.model.dirty = False
                break
            elif not (self.model.dirty or sub_presenters_dirty):
                break
            
        if commit_transaction:
            sqlhub.processConnection.commit()

        # TODO: if we could get the response from the view
        # then we could just call GenericModelViewPresenterEditor.start()
        # and then add this code but GenericModelViewPresenterEditor doesn't
        # know anything about it's presenter though maybe it should
        more_committed = None
        if response == self.RESPONSE_NEXT:
            if self.model.isinstance:
                model = self.model.so_object.__class__
            else:
                model = self.model.so_object
            e = SpeciesEditor(model, self.defaults, self.parent)
            more_committed = e.start(commit_transaction)
        elif response == self.RESPONSE_OK_AND_ADD:
            # TODO: when the plant editor gets it's own glade implementation
            # we should change accessionID to accession
            e = editors['AccessionEditor'](parent=self.parent, 
                                       defaults={'speciesID': committed})
            more_committed = e.start(commit_transaction)            
                    
        if more_committed is not None:
            committed = [committed]
            if isinstance(more_committed, list):
                committed.extend(more_committed)
            else:
                committed.append(more_committed)
                
        return committed
    
    
    def commit_changes(self):
        pass
    def commit_meta_changes(self):
        pass
    def comit_vernacular_name_changes(self):
        pass
    def commit_synonyms_changes(self):
        pass

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
class SpeciesEditor_old(TreeViewEditorDialog):
    
    visible_columns_pref = "editor.species.columns"
    column_width_pref = "editor.species.column_width"
    default_visible_list = ['genus', 'sp']
    
    label = 'Species'
    
    def __init__(self, parent=None, select=None, defaults={}, **kwargs):  
        TreeViewEditorDialog.__init__(self, tables["Species"],
                                      "Species Editor", parent,
                                      select=select, defaults=defaults, 
                                      **kwargs)
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
    
    def __init__(self, parent=None, select=None, defaults={}, **kwargs):        
        TreeViewEditorDialog.__init__(self, tables["SpeciesSynonym"], \
                                      "Species Synonym Editor", 
                                      parent, select=select, 
                                      defaults=defaults, *kwargs)
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
    from bauble.plugins.searchview.infobox import InfoBox, InfoExpander
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
            utils.set_widget_value(self.glade_xml, 'name_data', 
                                   row.markup(True))
            utils.set_widget_value(self.glade_xml, 'nacc_data', 
                                   len(row.accessions))
            
            nplants = 0
            for acc in row.accessions:
                nplants += len(acc.plants)
            utils.set_widget_value(self.glade_xml, 'nplants_data', nplants)    
    
    
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
        
