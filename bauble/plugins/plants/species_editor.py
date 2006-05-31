#
# Species table definition
#
import os
import gtk, gobject
from sqlobject import *
from sqlobject.sqlbuilder import _LikeQuoted
#import bauble
import bauble.utils as utils
import bauble.paths as paths
from bauble.plugins import tables, editors
#from bauble.treevieweditor import TreeViewEditorDialog, ComboColumn, TextColumn
from bauble.editor import *
from bauble.utils.log import log, debug
import xml.sax.saxutils as sax
from bauble.plugins.plants.species_model import Species, SpeciesMeta, \
    SpeciesSynonym, VernacularName

# TODO: need to make sure that unicode values are being stored properly from
# the entry, e.g. species_author should store unicode

class SpeciesEditorPresenter(GenericEditorPresenter):
    
    PROBLEM_INVALID_GENUS = 1
    
    widget_to_field_map = {'sp_genus_entry': 'genus',
                           'sp_species_entry': 'sp',
                           'sp_author_entry': 'sp_author',
                           'sp_infra_rank_combo': 'infrasp_rank',
                           'sp_infra_entry': 'infrasp',
                           'sp_cvgroup_entry': 'cv_group',
                           'sp_infra_author_entry': 'infrasp_author',
                           'sp_idqual_combo': 'id_qual',
                           'sp_spqual_combo': 'sp_qual',
                           'sp_notes_textview': 'notes'}
    
    
    def __init__(self, model, view, defaults={}):
        GenericEditorPresenter.__init__(self, model, view)
        self.defaults = defaults
        self.init_genus_entry()
        self.init_combos()
                
        if self.model.vernacular_names is not None:
            vn_model = [SQLObjectProxy(vn) for vn in self.model.vernacular_names]
        else:            
            vn_model = []
        self.vern_presenter = VernacularNamePresenter(vn_model, self.view, 
                                                      defaults=self.defaults.get('vernacular_names', {}))
        if self.model.synonyms is not None:        
            syn_model = [SQLObjectProxy(syn) for syn in self.model.synonyms]
        else:
            syn_model = []
        self.synonyms_presenter = SynonymsPresenter(syn_model, self.view, 
                                                    defaults=self.defaults.get('synonyms', {}))        
        self.meta_presenter = SpeciesMetaPresenter(SQLObjectProxy(tables['SpeciesMeta']), 
                                                   self.view, 
                                                   defaults=self.defaults)
        self.sub_presenters = (self.vern_presenter, self.synonyms_presenter, self.meta_presenter)
        
        self.refresh_view()        
        self.assign_simple_handler('sp_species_entry', 'sp')
        self.assign_simple_handler('sp_infra_rank_combo', 'infrasp_rank')
        self.assign_simple_handler('sp_infra_entry', 'infrasp')
        self.assign_simple_handler('sp_cvgroup_entry', 'cv_group')
        self.assign_simple_handler('sp_infra_author_entry', 'infrasp_author')
        self.assign_simple_handler('sp_idqual_combo', 'id_qual')
        self.assign_simple_handler('sp_spqual_combo', 'sp_qual')
        self.assign_simple_handler('sp_author_entry', 'sp_author')
        self.assign_simple_handler('sp_notes_textview', 'notes')        
    
    
    def init_genus_entry(self):
        genus_entry = self.view.widgets.sp_genus_entry
        completion = genus_entry.get_completion()
        completion.connect('match-selected', self.on_genus_match_selected)
        if self.model.genus is not None:
            self.idle_add_genus_completions(str(self.model.genus)[:2])
        self.insert_genus_sid = genus_entry.connect('insert-text', 
                                                self.on_genus_entry_insert)
        genus_entry.connect('delete-text', self.on_genus_entry_delete)
    
    
    def init_combos(self):
        combos = ['sp_infra_rank_combo', 'sp_idqual_combo', 'sp_spqual_combo']
        for combo_name in combos:
            combo = self.view.widgets[combo_name]
            combo.clear()
            r = gtk.CellRendererText()
            combo.pack_start(r, True)
            combo.add_attribute(r, 'text', 0)            
            model = gtk.ListStore(str)
            column = self.model.columns[self.widget_to_field_map[combo_name]]
            for enum in sorted(column.enumValues):
                if enum == None:
                    combo.append_text('')
                else:
                    combo.append_text(enum)
          
        
    def idle_add_genus_completions(self, text):
#        debug('idle_add_genus_competions: %s' % text)        
        like_genus = sqlhub.processConnection.sqlrepr(_LikeQuoted('%s%%' % text))
        sr = tables["Genus"].select('genus LIKE %s' % like_genus)
        def _add_completion_callback(select):
            model = gtk.ListStore(object)
            for genus in select:  
                model.append([genus])  
            completion = self.view.widgets.sp_genus_entry.get_completion()
            completion.set_model(model)
        gobject.idle_add(_add_completion_callback, sr)
    
    
    def on_genus_match_selected(self, completion, compl_model, iter):
        '''
        put the selected value in the model
        '''                
        genus = compl_model[iter][0]
#        debug('selected: %s' % str(species))
        entry = self.view.widgets.sp_genus_entry
        entry.handler_block(self.insert_genus_sid)
        entry.set_text(str(genus))
        entry.handler_unblock(self.insert_genus_sid)
        entry.set_position(-1)
        self.remove_problem(self.PROBLEM_INVALID_GENUS, 
                            self.view.widgets.sp_genus_entry)
        self.model.genus = genus
#        debug('%s' % self.model)
        self.prev_text = str(genus)


    def on_genus_entry_delete(self, entry, start, end, data=None):
#        debug('on_species_delete: \'%s\'' % entry.get_text())        
#        debug(self.model.species)
        text = entry.get_text()
        full_text = text[:start] + text[end:]
        if full_text == '' or (full_text == str(self.model.genus)):
            return
        self.add_problem(self.PROBLEM_INVALID_GENUS, 
                         self.view.widgets.species_entry)
        self.model.species = None
        
    
    def on_genus_entry_insert(self, entry, new_text, new_text_length, position, 
                       data=None):
        # TODO: this is flawed since we can't get the index into the entry
        # where the text is being inserted so if the user inserts text into 
        # the middle of the string then this could break
#        debug('on_species_insert_text: \'%s\'' % new_text)
#        debug('%s' % self.model)
        if new_text == '':
            # this is to workaround the problem of having a second 
            # insert-text signal called with new_text = '' when there is a 
            # custom renderer on the entry completion for this entry
            # block the signal from here since it will call this same
            # method again and resetting the species completions      
            debug('nex text == 0')      
            entry.handler_block(self.insert_genus_sid)
            entry.set_text(self.prev_text)
            entry.handler_unblock(self.insert_genus_sid)
            return False # is this 'False' necessary, does it do anything?
            
        entry_text = entry.get_text()                
        cursor = entry.get_position()
        full_text = entry_text[:cursor] + new_text + entry_text[cursor:]
        # this funny logic is so that completions are reset if the user
        # paste multiple characters in the entry    
        if len(new_text) == 1 and len(full_text) == 2:
            self.idle_add_genus_completions(full_text)
        elif new_text_length > 2:# and entry_text != '':
            self.idle_add_genus_completions(full_text[:2])
        self.prev_text = full_text
        
        if full_text != str(self.model.genus):
            self.add_problem(self.PROBLEM_INVALID_GENUS, 
                             self.view.widgets.sp_genus_entry)
            self.model.genus = None
#        debug('%s' % self.model)
    
    def start(self):
        return self.view.start()
        
        
    def refresh_view(self):
        for widget, field in self.widget_to_field_map.iteritems():            
            if field[-2:] == "ID":
                field = field[:-2]
            value = self.model[field]
#            debug('%s, %s, %s' % (widget, field, value))
            self.view.set_widget_value(widget, value, 
                                       default=self.defaults.get(field, None))
        #for presenter in self.sub_presenters:
        #    presenter.refresh_view()
        self.vern_presenter.refresh_view(self.model.default_vernacular_name)
        self.synonyms_presenter.refresh_view()
        self.meta_presenter.refresh_view()
        
        
        
# TODO: what we should probably do is just create an interface that the 
# presenter expects so as long as it implements the interface then it doesn't
# matter what the back looks like
# NOTES: what about if the model is a list of items, then __get??__ doesn't
# make sense
#class ModelInterface:
#    dirty = False
#    def __getitem__(self, item):
#        raise NotImplementedError()
#    def __getattr__(self, item):
#        raise NotImplementedError()
# NOTES: this basically makes a gtk.ListStore act like a cross between a 
# ListStore and a SQLObjectProxy
class ModelDecorator:
        # could use this to provide __iter__ and .dirty but that still doesn't 
        # solve the problem of how we determine what's dirty unless we set dirty
        # whenever add or remove is clicked
         
        def __init__(self, model, dirty=False):
            '''
            model: a tree view model
            '''
            self.model = model
            self.dirty = dirty
            
                
        def __iter__(self):    
            self.next_iter = self.model.get_iter_root()
            #self.iter = iter(self.model)
            return self
            #return iter(self.model)
            #return self.model.get_iter_root()
            
        
        current_iter = None
        next_iter = None
        def next(self):
#            debug(self.iter)
            self.current_iter = self.next_iter
            if self.current_iter is None:
                raise StopIteration
            debug(self.model[self.current_iter][0])
            v = self.model[self.current_iter][0]
            #self.iter = self.model.iter_next(self.iter)
            self.next_iter = self.model.iter_next(self.current_iter)
            #self.iter = self.model.iter_next(self.iter)
            return v
                
                
        def remove(self, item):
            # TODO: this need to be finished,  i guess we'll need to iterate
            # through the model and remove ALL matches though in reality there
            # should be only once since each item should have a unique id,
            # but then how do we know we should delete the object from the
            # database just because it was removed from the tree model, unless
            # we mark it here as deleted same as we do with dirty
            
            # search through the model for all occurences of item and remove
            # them from the model and append them to self.removed
            while 1:
                result = utils.search_tree_model(item)
                debug(Results)
                if results is None:
                    break
                self.model.remove(result)
                debug(result)                        
                self.removed.append(item)
                self.dirty = True
            
            
        def append(self, item):
            debug(item)
            debug(type(item))
            self.dirty = True
            self.model.append([item])
            
        
class VernacularNamePresenter(GenericEditorPresenter):
    
    def __init__(self, model, view, defaults={}):
        '''
        model: a list of SQLObject proxy objects
        view: see GenericEditorPresenter
        defaults: see GenericEditorPresenter
        '''
        GenericEditorPresenter.__init__(self, model, view, defaults)
        self.default = None
        self.init_treeview(model)
        self.model = ModelDecorator(self.view.widgets.vern_treeview.get_model()) 
        self.view.widgets.vern_add_button.connect('clicked', 
                                                  self.on_add_button_clicked)
        
        
    def on_add_button_clicked(self, button, data=None):
        name = self.view.widgets.vern_name_entry.get_text()
        lang = self.view.widgets.vern_lang_entry.get_text()
        proxy = SQLObjectProxy(VernacularName)
        proxy.name = name
        proxy.language = lang
        self.model.append(proxy)
        
    
        
    def on_default_toggled(self, cell, path, data=None):        
        active = cell.get_property('active')
#        debug('%s: %s' % (path, type(path)))
#        debug('on_default_toggled: %s' % active)                
        if not active:
            self.default = gtk.TreeRowReference(self.model.model, path)
            #self.default = path
        #cell.set_property('active', not_active)
#        debug(self.default)
        
    
    def init_treeview(self, model):
        tree = self.view.widgets.vern_treeview
                
        def _name_data_func(column, cell, model, iter, data=None):
            v = model[iter][0]
            cell.set_property('text', v.name)
        cell = gtk.CellRendererText()
        col = gtk.TreeViewColumn('Name', cell)
        col.set_cell_data_func(cell, _name_data_func)
        #col.set_resizable(True)
        tree.append_column(col)
        
        def _lang_data_func(column, cell, model, iter, data=None):
            v = model[iter][0]
            cell.set_property('text', v.language)
        cell = gtk.CellRendererText()
        col = gtk.TreeViewColumn('Language', cell)
        col.set_cell_data_func(cell, _lang_data_func)
        #col.set_resizable(True)
        tree.append_column(col)
        
        def _default_data_func(column, cell, model, iter, data=None):
            if self.default is None:
                return
            active = False
            # [0] on the path since this is a liststore
            if self.default.get_path() == model.get_path(iter):
                active = True
            cell.set_property('active', active)
            
        cell = gtk.CellRendererToggle()
        cell.connect('toggled', self.on_default_toggled)
        col = gtk.TreeViewColumn('Default', cell)
        col.set_cell_data_func(cell, _default_data_func)
        #col.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        tree.append_column(col)
        
        tree.set_model(None)
        tree_model = gtk.ListStore(object)
        for vn in self.model:
            debug(vn)
            tree_model.append([vn])
        tree.set_model(tree_model)
    
    
    def refresh_view(self, default_vernacular_name):
#        debug(default_vernacular_name)        
        if default_vernacular_name is None:
            return
        for vn in self.model:
            if vn.id == default_vernacular_name.id:
                path  = self.model.model.get_path(self.model.current_iter)
                self.default = gtk.TreeRowReference(self.model.model, path)
        if self.default is None:
            raise ValueError('couldn\'t set the default name: %s' % 
                             default_vernacular_name)
#        tree = self.view.widgets.vern_treeview
#        tree.set_model(None)
#        model = gtk.ListStore(object)
#        debug(self.model)
#        for vn in self.model:
#            debug(vn)
#            model.append([vn])
#        tree.set_model(model)
    

    
class SynonymsPresenter(GenericEditorPresenter):
    
    PROBLEM_INVALID_SYNONYM = 1
    
    
    def __init__(self, model, view, defaults=[]):
        '''
        model: a list of SQLObject proxy objects
        view: see GenericEditorPresenter
        defaults: see GenericEditorPresenter
        '''
        GenericEditorPresenter.__init__(self, model, view, defaults)     
        
        self.init_treeview(model)
        self.model = ModelDecorator(self.view.widgets.sp_syn_treeview.get_model())   
        self.init_syn_entry()
        self.insert_syn_sid = self.view.widgets.sp_syn_entry.connect('insert-text', 
                                                self.on_syn_entry_insert)
        self.view.widgets.sp_syn_entry.connect('delete-text', 
                                                self.on_syn_entry_delete)
        self.selected = None
        self.view.widgets.sp_syn_add_button.connect('clicked', 
                                                    self.on_add_button_clicked)
        #self.refresh_view()
        
    
    def init_treeview(self, model):        
        tree = self.view.widgets.sp_syn_treeview        
        def _syn_data_func(column, cell, model, iter, data=None):
            v = model[iter][0]
            cell.set_property('text', str(v.synonym))
        cell = gtk.CellRendererText()
        col = gtk.TreeViewColumn('Synonym', cell)
        col.set_cell_data_func(cell, _syn_data_func)
        tree.append_column(col)
        
        tree_model = gtk.ListStore(object)
        for syn in model:
            tree_model.append([syn])
        tree.set_model(tree_model)
    
    
    def refresh_view(self):
        return
#        tree = self.view.widgets.vern_treeview
#        tree.set_model(None)
#        model = gtk.ListStore(object)
#        debug(self.model)
#        for syn in self.model:
#            debug(syn)
#            model.append([syn])
#        tree.set_model(model)
        
        
    def init_syn_entry(self):
        completion = self.view.widgets.sp_syn_entry.get_completion()
        completion.connect('match-selected', self.on_syn_match_selected)
        #if self.model.synonym is not None:
        #    genus = self.model.synonym.genus
        #    self.idle_add_species_completions(str(genus)[:2])
        
        
    def on_add_button_clicked(self, button, data=None):
        syn = SQLObjectProxy(SpeciesSynonym)
        syn.synonym = self.selected
        self.model.append(syn)
        self.selected = None
        entry = self.view.widgets.sp_syn_entry
        entry.handler_block(self.insert_syn_sid)
        entry.set_text('')
        entry.set_position(-1)
        entry.handler_unblock(self.insert_syn_sid)
        
        
    def on_syn_match_selected(self, completion, compl_model, iter):
        '''
        put the selected value in the model
        '''                
        synonym = compl_model[iter][0]
#        debug('selected: %s' % str(species))
        entry = self.view.widgets.sp_syn_entry
        entry.handler_block(self.insert_syn_sid)
        entry.set_text(str(synonym))
        entry.handler_unblock(self.insert_syn_sid)
        entry.set_position(-1)
        self.remove_problem(self.PROBLEM_INVALID_SYNONYM, 
                            self.view.widgets.sp_syn_entry)
        self.selected = synonym
#        debug('%s' % self.model)
        self.prev_text = str(synonym)
        
        
    def on_syn_entry_delete(self, entry, start, end, data=None):
#        debug('on_species_delete: \'%s\'' % entry.get_text())        
#        debug(self.model.species)
        text = entry.get_text()
        full_text = text[:start] + text[end:]
        if full_text == '' or (full_text == str(self.selected)):
            return
        self.add_problem(self.PROBLEM_INVALID_SYNONYM, 
                         self.view.widgets.sp_syn_entry)
        self.selected = None
        
    
    def on_syn_entry_insert(self, entry, new_text, new_text_length, position, 
                       data=None):
        # TODO: this is flawed since we can't get the index into the entry
        # where the text is being inserted so if the user inserts text into 
        # the middle of the string then this could break
#        debug('on_species_insert_text: \'%s\'' % new_text)
#        debug('%s' % self.model)
        if new_text == '':
            # this is to workaround the problem of having a second 
            # insert-text signal called with new_text = '' when there is a 
            # custom renderer on the entry completion for this entry
            # block the signal from here since it will call this same
            # method again and resetting the species completions            
            debug('new text is empty')
            entry.handler_block(self.insert_syn_sid)
            entry.set_text(self.prev_text)
            entry.handler_unblock(self.insert_syn_sid)
            return False # is this 'False' necessary, does it do anything?
            
        entry_text = entry.get_text()                
        cursor = entry.get_position()
        full_text = entry_text[:cursor] + new_text + entry_text[cursor:]
        # this funny logic is so that completions are reset if the user
        # paste multiple characters in the entry    
        if len(new_text) == 1 and len(full_text) == 2:
            self.idle_add_syn_completions(full_text)
        elif new_text_length > 2:# and entry_text != '':
            self.idle_add_syn_completions(full_text[:2])
        self.prev_text = full_text
        
        if full_text != str(self.selected):
            self.add_problem(self.PROBLEM_INVALID_SYNONYM, 
                             self.view.widgets.sp_syn_entry)
            self.selected = None
#        debug('%s' % self.model)


    def idle_add_syn_completions(self, text):
#        debug('idle_add_species_competions: %s' % text)
        parts = text.split(" ")
        genus = parts[0]
        like_genus = sqlhub.processConnection.sqlrepr(_LikeQuoted('%s%%' % genus))
        sr = tables["Genus"].select('genus LIKE %s' % like_genus)
        def _add_completion_callback(select):
            n_gen = sr.count()
            n_sp = 0
            model = gtk.ListStore(object)
            for row in sr:    
                if len(row.species) == 0: # give a bit of a speed up
                    continue
                n_sp += len(row.species)
                for species in row.species:                
                    model.append([species])
            completion = self.view.widgets.sp_syn_entry.get_completion()
            completion.set_model(model)
        gobject.idle_add(_add_completion_callback, sr)
    
    
    
    
    
class SpeciesMetaPresenter(GenericEditorPresenter):    
    
    widget_to_field_map = {'sp_dist_combo': 'distribution',
                           'sp_humanpoison_check': 'poison_humans',
                           'sp_animalpoison_check': 'poison_animals',
                           'sp_food_check': 'food_plant'}
    def __init__(self, model, view, defaults={}):
        GenericEditorPresenter.__init__(self, model, view)        
        self.init_distribution_combo()
        self.refresh_view()
        
        # TODO: there is no way to set the check buttons to None once they
        # have been set and the inconsistent state doesn't convey None that
        # well, the only other option I know of is to use Yes/No/None combos
        # instead of checks
        self.assign_simple_handler('sp_dist_combo', 'distribution')
        self.assign_simple_handler('sp_humanpoison_check', 'poison_humans')
        self.assign_simple_handler('sp_animalpoison_check', 'poison_animals')
        self.assign_simple_handler('sp_food_check', 'food_plant')
        
        
    def init_distribution_combo(self):        
        def _populate():            
            model = gtk.TreeStore(str)
            model.append(None, ["Cultivated"])
            for continent in tables['Continent'].select():
                p1 = model.append(None, [str(continent)])
                for region in continent.regions:
                    p2 = model.append(p1, [str(region)])
                    for country in region.botanical_countries:
                        p3 = model.append(p2, [str(country)])
                        for unit in country.units:
                            if str(unit) != str(country):
                                model.append(p3, [str(unit)])            
            self.view.widgets.sp_dist_combo.set_model(model)
        gobject.idle_add(_populate)
        
        
    def refresh_view(self):
        for widget, field in self.widget_to_field_map.iteritems():            
            if field[-2:] == "ID":
                field = field[:-2]
            value = self.model[field]
#            debug('%s, %s, %s' % (widget, field, value))
#            debug('default: %s' % self.defaults.get(field, None))
            self.view.set_widget_value(widget, value, 
                                       default=self.defaults.get(field, None))
    
    

class SpeciesEditorView(GenericEditorView):
    
    expanders_pref_map = {'sp_infra_expander': 'editor.species.infra.expanded', 
                          'sp_qual_expander': 'editor.species.qual.expanded',
                          'sp_meta_expander': 'editor.species.meta.expanded'}
    
    
    def __init__(self, parent=None):
        GenericEditorView.__init__(self, os.path.join(paths.lib_dir(), 
                                                      'plugins', 'plants', 
                                                      'editors.glade'),
                                   parent=parent)
        self.dialog = self.widgets.species_dialog
        self.dialog.set_transient_for(parent)
        
        for entry in ('sp_genus_entry', 'sp_syn_entry'):        
            completion = gtk.EntryCompletion()    
            completion.set_match_func(self._lower_completion_match_func)        
            cell = gtk.CellRendererText() # set up the completion renderer
            completion.pack_start(cell)
            completion.set_cell_data_func(cell, self._completion_cell_data_func)
            completion.set_minimum_key_length(2)
            completion.set_popup_completion(True)        
            self.widgets[entry].set_completion(completion)
    
        
        self.restore_state()
        # TODO: set up automatic signal handling, all signals should be called
        # on the presenter
        self.connect_dialog_close(self.widgets.species_dialog)
        if sys.platform == 'win32':
            self.do_win32_fixes()
            
                    
    def _lower_completion_match_func(self, completion, key_string, iter, 
                                    data=None):
        '''
        the only thing this does different is it make the match case insensitve
        '''
        value = completion.get_model()[iter][0]
        return str(value).lower().startswith(key_string.lower())   
        
        
    def _completion_cell_data_func(self, column, renderer, model, iter, 
                                         data=None):
        v = model[iter][0]
        renderer.set_property('text', str(v))
        
        
    def do_win32_fixes(self):
        pass
        
        
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
        # TODO: somehow we need to get the default vernacular name from the list
        # after it is commited and set species.default_vernacular to the id, 
        # maybe commit_changes can return the default for us and we can
        debug(self.model)
        synonyms = self.model.pop('synonyms', None)
        vnames = self.model.pop('vernacular_names', None)
        species = None
        if self.model.dirty:
            species = self._commit(self.model)        
        elif self.model.isinstance:
            species = self.model.so_object
        debug(species)
        if species is not None:
            self.commit_meta_changes(species)            
            vn = self.commit_vernacular_name_changes(species)
            species.default_vernacular_name = vn
            self.commit_synonyms_changes(species)
        return species
    
    
    def commit_meta_changes(self, species):
        '''
        if this returns none then it means that nothing was commited
        '''
#        debug('commit_meta_changes')
        meta_model = self.presenter.meta_presenter.model 
#        debug(meta_model)
        meta = None
        if meta_model.dirty:
#            debug('committing dirty meta')
            meta_model.species = species
            #meta_model.speciesID = species.id
            meta = commit_to_table(SpeciesSynonym, meta_model)
            #self._commit(meta_model)            
        return meta
            
            
        
    def commit_vernacular_name_changes(self, species):
        '''
        returns the vernacular name instance that was selected as the default
        '''
#        debug('commit_vernacular_name_changes')
        vn_model = self.presenter.vern_presenter.model 
        default = None
        for item in vn_model:
            if item.species is None: # then it's a new entry
                item.species = species
                vn = commit_to_table(VernacularName, item)
            else: # item should be an instance of VernacularName
                vn = item.so_object
            if self.presenter.vern_presenter.default.get_path() == vn_model.model.get_path(vn_model.current_iter):
                default = vn
        return default
        
        
    def commit_synonyms_changes(self, species):
        '''
        '''
#        debug('commit_synonyms_changes')
        syn_model = self.presenter.synonyms_presenter.model 
        # TODO: need to also check model.removed and delete any items in the
        # list from the database
        for item in syn_model:
            debug(item)
            debug(type(item))
            #if item.dirty:                
            # if it has a species that means it's not a new synonym
            if item.species is None:
                item.species = species
                commit_to_table(SpeciesSynonym, item)
        

#class VernacularNameColumn(TextColumn):
#        
#    def __init__(self, tree_view_editor, header):
#        # this is silly to have the get the join this way
#        vern_join = None
#        for j in Species.sqlmeta.joins: 
#            if j.joinMethodName == 'vernacular_names':
#                vern_join = j
#                break
#        assert vern_join is not None
#        super(VernacularNameColumn, self).__init__(tree_view_editor, header,
#               so_col=vern_join)
#        self.meta.editor = editors['VernacularNameEditor']
#
#    
#    def _start_editor(self, path):        
#        model = self.table_editor.view.get_model()
#        row = model[model.get_iter(path)][0]
#        existing = row[self.name]
#        old_committed = []
#        select = None    
#        if isinstance(existing, tuple): # existing/pending pair
#            existing, old_committed = existing
#            if existing is None: # nothing already exist
#                select = old_committed
#            else:
#                select = existing+old_committed
#        else:
#            select = existing
#        e = self.meta.editor(select=select,
#                             default_name=row['default_vernacular_nameID'])
#        returned = e.start(False)
#        if returned is None:
#            return
#        default_name, committed_names = returned # unpack
#        if default_name is not None and committed_names is not None:
#            model = self.table_editor.view.get_model()
#            i = model.get_iter(path)
#            row = model.get_value(i, 0)
#            row['default_vernacular_nameID'] = default_name
#            if committed_names is not None and len(committed_names) > 0:
#                row['vernacular_names'] = (existing, 
#                                           old_committed+committed_names)
#            # why do we emit edited? to set the values in the model
#            self.renderer.emit('edited', path, default_name) 
#            self.dirty = True
#
#
#    def cell_data_func(self, column, renderer, model, iter, data=None):
#        row = model.get_value(iter, 0)
#        all_names = row[self.name]
#        if row.committed:
#            renderer.set_property('sensitive', False)
#            renderer.set_property('editable', False)
#        else:
#            renderer.set_property('sensitive', True)
#            renderer.set_property('editable', True)        
#
#        if all_names is not None:
#            default_name = row['default_vernacular_nameID']            
#            #debug(default_name)
#            if isinstance(all_names, tuple): 
#                existing, pending = all_names
#                if existing is None:
#                    renderer.set_property('text', '%s (%s pending)' \
#                                      % (default_name, len(pending)))
#                else:
#                    renderer.set_property('text', '%s (%s names, %s pending)' \
#                                          % (default_name, len(existing), 
#                                             len(pending)))
#            else:
#                renderer.set_property('text', '%s (%s names)' \
#                                      % (default_name, len(all_names)))                                      
#        else:
#            renderer.set_property('text', None)
#
#
##
## Species editor
##
#class SpeciesEditor_old(TreeViewEditorDialog):
#    
#    visible_columns_pref = "editor.species.columns"
#    column_width_pref = "editor.species.column_width"
#    default_visible_list = ['genus', 'sp']
#    
#    label = 'Species'
#    
#    def __init__(self, parent=None, select=None, defaults={}, **kwargs):  
#        TreeViewEditorDialog.__init__(self, tables["Species"],
#                                      "Species Editor", parent,
#                                      select=select, defaults=defaults, 
#                                      **kwargs)
#        titles = {"genusID": "Genus",
#		  "sp": "Species",
#		  "sp_hybrid": "Sp. hybrid",
#		  "sp_qual": "Sp. qualifier",
#		  "sp_author": "Sp. author",
#		  "cv_group": "Cv. group",
##                   "cv": "Cultivar",
##                   "trades": "Trade name",
##                   "supfam": 'Super family',
##                   'subgen': 'Subgenus',
##                   'subgen_rank': 'Subgeneric rank',
#		  'infrasp': 'Isp. epithet',
#		  'infrasp_rank': 'Isp. rank',
#		  'infrasp_author': 'Isp. author',
##                   'iucn23': 'IUCN 2.3\nCategory',
##                   'iucn31': 'IUCN 3.1\nCategory',
#		  'id_qual': 'ID qualifier',
##                   'distribution': 'Distribution'
#		  'species_meta': 'Meta Info',
#		  'notes': 'Notes',
##                    'default_vernacular_nameID': 'Vernacular Names',
#		  'synonyms': 'Synonyms',
#		  'vernacular_names': 'Vernacular Names',
#		  }
#
#        # make a custom distribution column
##        self.columns.pop('distribution') # this probably isn't necessary     
##        dist_column = ComboColumn(self.view, 'Distribution',
##                           so_col = Species.sqlmeta.columns['distribution'])
##        dist_column.model = self.make_model()
##        self.columns['distribution'] = dist_column                    
#        #self.columns['species_meta'] = \
#        #    TextColumn(self.view, 'Species Meta', so_col=Species.sqlmeta.joins['species_meta'])
#        #self.columns['default_vernacular_nameID'] = \
#        
#        # remove the default vernacular name column have this set
#        # by the VernacularNameColumn, but we have to make sure that the
#        # default vernacular name is listed in the foreign keys or we'll 
#        # commit_changes won't know to set it
#        
#        self.columns.pop('default_vernacular_nameID')
#        #self.columns.foreign_keys.append('default_vernacular_nameID')
#        self.columns['vernacular_names'] = \
#            VernacularNameColumn(self, 'Vernacular Names')
#        
#        self.columns['species_meta'].meta.editor = editors["SpeciesMetaEditor"]
#        self.columns.titles = titles                     
#                     
#        # set completions
#        self.columns["genusID"].meta.get_completions= self.get_genus_completions
#        self.columns['synonyms'].meta.editor = editors["SpeciesSynonymEditor"]
#    
#        
##    def commit_changes_NO(self):
##        # TODO: speciess are a complex typle where more than one field
##        # make the plant unique, write a custom commit_changes to get the value
##        # from the table as a dictionary, convert this dictionary to 
##        # an object that can be accessed by attributes so it mimic a 
##        # Species object, pass the dict to species2str and test
##        # that a species with the same name doesn't already exist in the 
##        # database, if it does exist then ask the use what they want to do
##        #super(SpeciesEditor, self).commit_changes()
##        values = self.get_values_from_view()
#    
#          
#    def _model_row_to_values(self, row):    
#        # need to test each of the values that make up the species
#        # against the database, not just the string, i guess we need to
#        # check each of the keys in values, check if they are name components
#        # use each of these values in a query to speciess
#	values = super(SpeciesEditor, self)._model_row_to_values(row)
#	if values is None:
#	    return values
#
#        if values.has_key('id'):
#            return values
#        exists = False
#        select_values = {}
#        try:
#            select_values['genusID'] = values['genusID'].id
#            select_values['sp'] = values['sp']        
#        except KeyError, e:
#            raise bauble.BaubleError('You must enter the required field %s' %e)
#            
#        sel = Species.selectBy(**select_values)
#        names = ""
#        for s in sel:
#            exists = True
#            names += "%d: %s\n" % (s.id, s)
#        msg  = "The following plant names are similiar to the plant name you "\
#               "are trying to create. Are your sure this is what you want to "\
#               "do?\n\n" + names
#        if exists and not utils.yes_no_dialog(msg):
#            return None
#        return values
#
#
#    def get_genus_completions(self, text):
#        model = gtk.ListStore(str, object)
#        sr = tables["Genus"].select("genus LIKE '"+text+"%'")        
#        for row in sr: 
#            model.append([str(row), row])
#        return model
#                
#    
#    def on_genus_completion_match_selected(self, completion, model, 
#                                           iter, path):
#        """
#        all foreign keys should use entry completion so you can't type in
#        values that don't already exists in the database, therefore, allthough
#        i don't like it the view.model.row is set here for foreign key columns
#        and in self.on_renderer_edited for other column types                
#        """        
#        genus = model.get_value(iter, 1)
#        self.set_view_model_value(path, "genusID", genus)        
#        
#                                    
##    def make_model(self):
##        model = gtk.TreeStore(str)
##        model.append(None, ["Cultivated"])
##        for continent in tables['Continent'].select(orderBy='continent'):
##            p1 = model.append(None, [str(continent)])
##            for region in continent.regions:
##                p2 = model.append(p1, [str(region)])
##                for country in region.botanical_countries:
##                    p3 = model.append(p2, [str(country)])
##                    for unit in country.units:
##                        if str(unit) != str(country):
##                            model.append(p3, [str(unit)])    
##        return model
#                            
#      
#    def foreign_does_not_exist(self, name, value):
#        self.add_genus(value)    
#
#
#    def add_genus(self, name):
#        msg = "The Genus %s does not exist. Would you like to add it?" % name
#        if utils.yes_no_dialog(msg):
#            print "add genus"
#
#        
#
## 
## SpeciesSynonymEditor
##
#class SpeciesSynonymEditor(TreeViewEditorDialog):
#
#    visible_columns_pref = "editor.species_syn.columns"
#    column_width_pref = "editor.species_syn.column_width"
#    default_visible_list = ['synonym']
#    
#    standalone = False
#    label = 'Species Synonym'
#    
#    def __init__(self, parent=None, select=None, defaults={}, **kwargs):        
#        TreeViewEditorDialog.__init__(self, tables["SpeciesSynonym"], \
#                                      "Species Synonym Editor", 
#                                      parent, select=select, 
#                                      defaults=defaults, *kwargs)
#        titles = {'synonymID': 'Synonym of Species'}
#                  
#        # can't be edited as a standalone so the species should only be set by
#        # the parent editor
#        self.columns.pop('speciesID')
#        
#        self.columns.titles = titles
#        self.columns["synonymID"].meta.get_completions = \
#            self.get_species_completions
#
#
#    def get_species_completions(self, text):
#        # get entry and determine from what has been input which
#        # field is currently being edited and give completion
#        # if this return None then the entry will never search for completions
#        # TODO: finish this, it would be good if we could just stick
#        # the table row in the model and tell the renderer how to get the
#        # string to match on, though maybe not as fast, and then to get
#        # the value we would only have to do a row.id instead of storing
#        # these tuples in the model
#        # UPDATE: the only problem with sticking the table row in the column
#        # is how many queries would it take to screw in a lightbulb, this
#        # would be easy to test it just needs to be done
#        # TODO: there should be a better/faster way to do this 
#        # using a join or something
#        parts = text.split(" ")
#        genus = parts[0]
#        sr = tables["Genus"].select("genus LIKE '"+genus+"%'")
#        model = gtk.ListStore(str, object) 
#        for row in sr:
##            debug(str(row))
#            for species in row.species:                
#                model.append((str(species), species))
#        return model
#    
#    
    
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
        
