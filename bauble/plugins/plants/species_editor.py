#
# Species table definition
#
import os
import xml.sax.saxutils as sax
import gtk, gobject
from sqlobject import *
from sqlobject.sqlbuilder import _LikeQuoted
from sqlobject.col import StringValidator
import bauble.utils as utils
import bauble.paths as paths
from bauble.plugins import tables, editors
from bauble.editor import *
from bauble.utils.log import log, debug
from bauble.plugins.plants.family import Family
from bauble.plugins.plants.genus import Genus
from bauble.plugins.plants.species_model import Species, SpeciesMeta, \
    SpeciesSynonym, VernacularName

# TODO: would be nice, but not necessary, to edit existing vernacular names
# instead of having to add new ones

# TODO: what about author string and cultivar groups

# TODO: ensure None is getting set in the model instead of empty strings, 
# UPDATE: i think i corrected most of these but i still need to double check


class StringOrNoneValidator(StringValidator):
    '''
    validator that returns None on an emptry string or calls the default 
    to_python method
    '''
    def __init__(self, name):
        StringValidator.__init__(self, name=name)
        
        
    def to_python(self, value, state):
        if value is '':
            return None
        else:
            return StringValidator.to_python(value, state)


class SpeciesEditorPresenter(GenericEditorPresenter):
    
    PROBLEM_INVALID_GENUS = 1
    
    widget_to_field_map = {'sp_genus_entry': 'genus',
                           'sp_species_entry': 'sp',
                           'sp_author_entry': 'sp_author',
                           'sp_infra_rank_combo': 'infrasp_rank',
                           'sp_hybrid_combo': 'sp_hybrid',
                           'sp_infra_entry': 'infrasp',
                           'sp_cvgroup_entry': 'cv_group',
                           'sp_infra_author_entry': 'infrasp_author',
                           'sp_idqual_combo': 'id_qual',
                           'sp_spqual_combo': 'sp_qual',
                           'sp_notes_textview': 'notes'}
    
    
    def __init__(self, model, view, defaults={}):
        GenericEditorPresenter.__init__(self, model, view)
        self.defaults = defaults
        self.defaults.pop('genusID', None) 
        self.model.update(defaults)        
        self.init_genus_entry()
        #self.init_infrasp_rank_combo()
        self.init_combos()
        self.init_fullname_widgets()
            
        vn_model = []    
        if self.model.vernacular_names is not None:
            vn_model = [SQLObjectProxy(vn) for vn in self.model.vernacular_names]
        self.vern_presenter = VernacularNamePresenter(vn_model, self.view, 
                                                      defaults=self.defaults.get('vernacular_names', {}))
        syn_model = []
        if self.model.synonyms is not None:        
            syn_model = [SQLObjectProxy(syn) for syn in self.model.synonyms]
        self.synonyms_presenter = SynonymsPresenter(syn_model, self.view, 
                                                    defaults=self.defaults.get('synonyms', {}))
        
        if self.model.species_meta:
            species_meta = SQLObjectProxy(self.model.species_meta)
        else:
            species_meta = SQLObjectProxy(tables['SpeciesMeta'])
        self.meta_presenter = SpeciesMetaPresenter(species_meta, self.view, 
                                                   defaults=self.defaults)
        
        self.sub_presenters = (self.vern_presenter, self.synonyms_presenter, self.meta_presenter)
        
        self.refresh_view()        
        
        #self.view.widgets.sp_infra_rank_combo.connect('changed', self.on_infra_rank_changed)
        
        self.assign_simple_handler('sp_species_entry', 'sp',
                                   StringOrNoneValidator('sp'))
        self.assign_simple_handler('sp_infra_rank_combo', 'infrasp_rank', 
                                   StringOrNoneValidator('infrasp_rank'))
        self.assign_simple_handler('sp_hybrid_combo', 'sp_hybrid', 
                                   StringOrNoneValidator('sp_hybrid'))
        self.assign_simple_handler('sp_infra_entry', 'infrasp', 
                                   StringOrNoneValidator('infrasp'))
        self.assign_simple_handler('sp_cvgroup_entry', 'cv_group')
        self.assign_simple_handler('sp_infra_author_entry', 'infrasp_author',
                                    StringOrNoneValidator('infrasp_author'))
        self.assign_simple_handler('sp_idqual_combo', 'id_qual', 
                                   StringOrNoneValidator('id_qual'))
        self.assign_simple_handler('sp_spqual_combo', 'sp_qual',
                                   StringOrNoneValidator('sp_qual'))
        self.assign_simple_handler('sp_author_entry', 'sp_author',
                                   StringOrNoneValidator('sp_author'))
        self.assign_simple_handler('sp_notes_textview', 'notes',
                                   StringOrNoneValidator('notes'))        
        
        self.init_change_notifier()
    
    
    def refresh_sensitivity(self):
        '''
        set the sensitivity on the widgets that make up the species name 
        according to values in the model
        '''
        sensitive = []
        notsensitive = []
        # states_dict:
        # { field: [widget(s) whose sensitivity == fields is not None] }
        # - if widgets is a tuple then at least one of the items has to not be None
        # - this assumes that when field is not None, if field is none then
        # sensitive widgets are set to false
        states_dict = {'sp_hybrid_combo': ['genus'],
                       'sp_species_entry': ['genus'],
                       'sp_author_entry': ['sp'],
                       'sp_infra_rank_combo': ['sp'],
                       'sp_infra_entry': [('infrasp_rank', 'sp_hybrid'), 'sp'],
                       'sp_infra_author_entry': [('infrasp_rank', 'sp_hybrid'), 'infrasp', 'sp']}
        for widget, fields in states_dict.iteritems():
#            debug('%s: %s' % (widget, fields))
            none_status = []
            for field in fields:                
                if isinstance(field, tuple):
                    none_list = [f for f in field if self.model[f] is not None]
                    if len(none_list) != 0:
                        none_status.extend(none_list)
                elif self.model[field] is not None:
                    none_status.append(field)
            
            if len(none_status) == len(states_dict[widget]):
                self.view.widgets[widget].set_sensitive(True)
            else:
                self.view.widgets[widget].set_sensitive(False)        
        
        # infraspecific rank has to be a cultivar for the cultivar group entry
        # to be sensitive
        if self.model.infrasp_rank == 'cv.':
            self.view.widgets.sp_cvgroup_entry.set_sensitive(True)
        else:
            self.view.widgets.sp_cvgroup_entry.set_sensitive(False)
            
        # turn off the infraspecific rank combo if the hybrid value in the model
        # is not None
        if self.model.sp_hybrid is not None:
            self.view.widgets.sp_infra_rank_combo.set_sensitive(False)
    
            
    def on_field_changed(self, field):
        '''
        rests the sensitivity on the ok buttons and the name widgets when 
        values change in the model
        '''
#        debug('on_field_changed: %s' % field)
#        debug('on_field_changed: %s = %s' % (field, self.model[field]))
        sensitive = True
        if len(self.problems) != 0 \
           or len(self.vern_presenter.problems) != 0 \
           or len(self.synonyms_presenter.problems) != 0 \
           or len(self.meta_presenter.problems) != 0:
            sensitive = False
        self.view.set_accept_buttons_sensitive(sensitive)
        self.refresh_sensitivity()
        
    
    def init_change_notifier(self):
        '''
        for each widget register a signal handler to be notified when the
        value in the widget changes, that way we can w things like sensitize
        the ok button
        '''
        for field in self.widget_to_field_map.values():            
            self.model.add_notifier(field, self.on_field_changed)
            
        #for field in self.synonyms_presenter.widget_to_field_map.values():            
        #    self.model.add_notifier(field, self.on_field_changed)
            
        #for field in self.vern_presenter.widget_to_field_map.values():
        #    self.model.add_notifier(field, self.on_field_changed)
            
        for field in self.meta_presenter.widget_to_field_map.values():
            self.meta_presenter.model.add_notifier(field, self.on_field_changed)
            #self.model.add_notifier(field, self.on_field_changed)
                
        self.vern_presenter.set_default_changed_notifier(self.on_field_changed)
        #self.model.dummy_model
            
            
    def init_genus_entry(self):
        '''
        initialize the genus entry
        '''
        genus_entry = self.view.widgets.sp_genus_entry
        completion = genus_entry.get_completion()
        completion.connect('match-selected', self.on_genus_match_selected)
        if self.model.genus is not None:
            self.idle_add_genus_completions(str(self.model.genus)[:2])
        self.insert_genus_sid = genus_entry.connect('insert-text', 
                                                self.on_genus_entry_insert)
        genus_entry.connect('delete-text', self.on_genus_entry_delete)
 
        
    def init_combos(self):
        '''
        initialize the infraspecific rank combo, the species hybrid combo,
        the species idqualifier combo and the species qualifier combo
        '''        
        combos = ['sp_infra_rank_combo', 'sp_hybrid_combo', 'sp_idqual_combo', 
                  'sp_spqual_combo']
        #combos = ['sp_idqual_combo', 'sp_spqual_combo']
        for combo_name in combos:
            combo = self.view.widgets[combo_name]
            combo.clear()
            r = gtk.CellRendererText()
            combo.pack_start(r, True)
            combo.add_attribute(r, 'text', 0)
            column = self.model.columns[self.widget_to_field_map[combo_name]]
            for enum in sorted(column.enumValues):
                if enum == None:
                    combo.append_text('')
                else:
                    combo.append_text(enum)
    
    
    def init_fullname_widgets(self):
        '''
        initialized the signal handlers on the widgets that are relative to
        building the fullname string in the sp_fullname_label widget
        '''
        def on_insert(entry, *args):
            self.refresh_fullname_label()                
        def on_delete(entry, *args):
            self.refresh_fullname_label()
        for widget_name in ['sp_genus_entry', 'sp_species_entry', 'sp_author_entry',
                            'sp_infra_entry', 'sp_cvgroup_entry', 
                            'sp_infra_author_entry']:
            w = self.view.widgets[widget_name]
            w.connect_after('insert-text', on_insert)
            w.connect_after('delete-text', on_delete)

        def on_changed(*args):
            self.refresh_fullname_label()
        for widget_name in ['sp_infra_rank_combo', 'sp_hybrid_combo', 
                            'sp_idqual_combo', 'sp_spqual_combo']:
            w = self.view.widgets[widget_name]
            w.connect_after('changed', on_changed)
                    
        
    def refresh_fullname_label(self):
        '''
        resets the fullname label according to values in the model
        '''
        if len(self.problems) > 0:
            s = '--'
        elif self.model.genus == None:
            s = '--'
        else:
            import copy
            values = copy.copy(self.model)
            values.pause_notifiers(True)
            for key, value in values.iteritems():
                if value is '':
                    values[key] = None                                        
            if values.sp_hybrid is not None:
                values.infrasp_rank = None
                values.cv_group = None
                values.sp_hybrid = values.sp_hybrid # so this is the last field on_field_changed is called on
            elif values.infrasp_rank is None:
                values.infrasp = None
                values.cv_group = None
                values.infrasp_author = None
            elif values.infrasp_rank != 'cv.':
                values.cv_group = None

            #s = '%s\n%s' % (self.model.genus.family, Species.str(values, authors=True, markup=True))
            s = '%s  -  %s' % (Family.str(self.model.genus.family, full_string=True),
                               Species.str(values, authors=True, markup=True))
            #s += '%s\n'\n%s' % self.model.genus.family
            values.pause_notifiers(False)
        self.view.widgets.sp_fullname_label.set_markup(s)
    
    
    def idle_add_genus_completions(self, text):
        '''
        adds completions to the genus entry according to text
        
        text -- the text to match against
        '''
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
        self.refresh_fullname_label()
#        debug('%s' % self.model)
        self.prev_text = str(genus)


    def on_genus_entry_delete(self, entry, start, end, data=None):
#        debug('on_species_delete: \'%s\'' % entry.get_text())        
#        debug(self.model.genus)
        text = entry.get_text()
        full_text = text[:start] + text[end:]
        if full_text == '' or (full_text == str(self.model.genus)):
            return
        self.add_problem(self.PROBLEM_INVALID_GENUS, 
                         self.view.widgets.sp_genus_entry)
        self.model.genus = None
        
    
    def on_genus_entry_insert(self, entry, new_text, new_text_length, position, 
                       data=None):
#        debug('on_species_insert_text: \'%s\'' % new_text)
#        debug('%s' % self.model)
        if new_text == '':
            # this is to workaround the problem of having a second 
            # insert-text signal called with new_text = '' when there is a 
            # custom renderer on the entry completion for this entry
            # block the signal from here since it will call this same
            # method again and resetting the species completions      
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
        self.refresh_sensitivity()
        self.vern_presenter.refresh_view(self.model.default_vernacular_name)
        self.synonyms_presenter.refresh_view()
        self.meta_presenter.refresh_view()
        
        
# TODO: what we should probably do is just create an interface that all
# presenters expects so as long as it implements the interface then it doesn't
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
            self.removed = []
            
                
        def __iter__(self):    
            self.next_iter = self.model.get_iter_root()
            return self
        
            
        def __len__(self):
            return len(self.model)
    
        current_iter = None
        next_iter = None
        def next(self):
            '''
            '''
            self.current_iter = self.next_iter
            if self.current_iter is None:
                raise StopIteration
            v = self.model[self.current_iter][0]
            self.next_iter = self.model.iter_next(self.current_iter)
            return v
                
                
        def remove(self, item):
            '''
            @param item: the value to remove from the model, if item is a 
                gtk.TreeModelIter then remove only the item that item points to,
                else remove all items in the model that are the same as item
            '''            
            # if item is a TreeIter then remove only that value
            if isinstance(item, gtk.TreeIter):
                value = self.model[item][0]
                self.model.remove(item)
                if isinstance(value, SQLObjectProxy) and value.isinstance:
                    self.removed.append(value)
                    self.dirty = True
            else:
                # search through the model for all occurences of item and 
                # remove them from the model and append them to self.removed    
                while 1:
                    row = utils.search_tree_model(self.model, item)
                    if row is None:
                        break
                    self.model.remove(row.iter)
                    # if is an instance then add to removed so we can delete it 
                    # from the database later
                    if isinstance(item, SQLObjectProxy) and item.isinstance:
                        self.removed.append(item)                    
                        self.dirty = True
            
            
        def append(self, item):
            '''
            @param item:
            '''
            self.dirty = True
            return self.model.append([item])
            


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
        self.view.widgets.sp_vern_add_button.connect('clicked', 
                                                  self.on_add_button_clicked)
        self.view.widgets.sp_vern_remove_button.connect('clicked', 
                                                  self.on_remove_button_clicked)
        lang_entry = self.view.widgets.vern_lang_entry
        lang_entry.connect('insert-text', self.on_entry_insert, 'vern_name_entry')
        lang_entry.connect('delete-text', self.on_entry_delete, 'vern_name_entry')
        
        name_entry = self.view.widgets.vern_name_entry
        name_entry.connect('insert-text', self.on_entry_insert, 'vern_lang_entry')
        name_entry.connect('delete-text', self.on_entry_delete, 'vern_lang_entry')        
        
    
    def on_entry_insert(self, entry, new_text, new_text_length, position, 
                        other_widget_name):
        '''
        ensures that the two vernacular name entries both have text and sets 
        the sensitivity of the add button if so
        '''
        entry_text = entry.get_text()                
        cursor = entry.get_position()
        full_text = entry_text[:cursor] + new_text + entry_text[cursor:]
        sensitive = False
        if full_text != '' and self.view.widgets[other_widget_name].get_text() != '':
            sensitive = True
        self.view.widgets.sp_vern_add_button.set_sensitive(sensitive)
        
        
    def on_entry_delete(self, entry, start, end, other_widget_name):
        '''
        ensures that the two vernacular name entries both have text and sets 
        the sensitivity of the add button if so
        '''
        text = entry.get_text()
        full_text = text[:start] + text[end:]
        sensitive = False
        if full_text != '' and self.view.widgets[other_widget_name].get_text() != '':
            sensitive = True
        self.view.widgets.sp_vern_add_button.set_sensitive(sensitive)
    
        
    def on_add_button_clicked(self, button, data=None):
        '''
        add the values in the entries to the model
        '''
        name = self.view.widgets.vern_name_entry.get_text()
        lang = self.view.widgets.vern_lang_entry.get_text()
        proxy = SQLObjectProxy(VernacularName)
        proxy.name = name
        proxy.language = lang
        it = self.model.append(proxy)
        if len(self.model) == 1:
            model = self.model.model
            self.default = gtk.TreeRowReference(model, model.get_path(it))
        self.view.widgets.sp_vern_add_button.set_sensitive(False)
        self.view.widgets.vern_name_entry.set_text('')
        self.view.widgets.vern_lang_entry.set_text('')
        self.view.set_accept_buttons_sensitive(True)
    
    
    def on_remove_button_clicked(self, button, data=None):
        '''
        removes the currently selected vernacular name from the view
        '''        
        # TODO: maybe we should only ask 'are you sure' if the selected value
        # is an instance, this means it will be deleted from the database        
        tree = self.view.widgets.vern_treeview
        path, col = tree.get_cursor()        
        model = tree.get_model()        
        value = model[model.get_iter(path)][0]
        # TODO: we need to do some some of 'unit of work' pattern in the model
        # decorator with a 'removed' list so we know which vernacular names
        # to delete from the database
        msg = 'Are you sure you want to remove the vernacular name %s?' % value.name
        if utils.yes_no_dialog(msg, parent=self.view.window):
            self.model.remove(model.get_iter(path))
            self.view.set_accept_buttons_sensitive(True)            
            # check if we removed the item designated as the default 
            # vernacular name and if so reset it to the first row in the model
            if not self.default.valid():
                path = self.model.model.get_path(self.model.model.get_iter_first())
                self.default = gtk.TreeRowReference(self.model.model, path)
        
        
    def set_default_changed_notifier(self, callback):    
        '''
        set the callback to call when the default toggles changes, will be
        called like C{callback('default_vernacular_name')}
        '''
        self.default_changed_callback = callback
        
        
    def on_default_toggled(self, cell, path, data=None):        
        '''
        default column callback
        '''
        active = cell.get_property('active')
        if not active:
            self.default = gtk.TreeRowReference(self.model.model, path)
            self.default_changed_callback('default_vernacular_name')
        
    
    def init_treeview(self, model):
        '''
        '''
        tree = self.view.widgets.vern_treeview
                
        def _name_data_func(column, cell, model, iter, data=None):
            v = model[iter][0]
            cell.set_property('text', v.name)
            # just added so change the background color to indicate its new
            if not v.isinstance:
                cell.set_property('foreground', 'blue')
            else:
                cell.set_property('foreground', None)
        cell = gtk.CellRendererText()
        col = gtk.TreeViewColumn('Name', cell)
        col.set_cell_data_func(cell, _name_data_func)
        #col.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        #col.set_min_width(150)
        col.set_fixed_width(150)
        col.set_min_width(50)
        col.set_resizable(True)
        tree.append_column(col)
        
        def _lang_data_func(column, cell, model, iter, data=None):
            v = model[iter][0]
            cell.set_property('text', v.language)
            # just added so change the background color to indicate its new
            if not v.isinstance:
                cell.set_property('foreground', 'blue')
            else:
                cell.set_property('foreground', None)
        cell = gtk.CellRendererText()
        col = gtk.TreeViewColumn('Language', cell)
        col.set_cell_data_func(cell, _lang_data_func)
        #col.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        col.set_resizable(True)
        #col.set_min_width(150)
        col.set_fixed_width(150)
        col.set_min_width(50)
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
        col.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        col.set_fixed_width(20)
        col.set_max_width(20)
        tree.append_column(col)
        
        tree.set_model(None)
        tree_model = gtk.ListStore(object)
        for vn in self.model:
#            debug(vn)
            tree_model.append([vn])
        tree.set_model(tree_model)
        
        tree.connect('cursor-changed', self.on_tree_cursor_changed)
        
    
    def on_tree_cursor_changed(self, tree, data=None):
        path, column = tree.get_cursor()
        self.view.widgets.sp_vern_remove_button.set_sensitive(True)
        
    
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
    
#
# TODO: you shouldn't be able to set a plant as a synonym of itself
#
class SynonymsPresenter(GenericEditorPresenter):
    
    PROBLEM_INVALID_SYNONYM = 1
    
    
    def __init__(self, model, view, defaults=[]):
        '''
        @param model: a list of SQLObject proxy objects
        @param view: see GenericEditorPresenter
        @param defaults: see GenericEditorPresenter
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
        self.view.widgets.sp_syn_remove_button.connect('clicked', 
                                                    self.on_remove_button_clicked)
        
    
    def init_treeview(self, model):        
        '''
        initialize the gtk.TreeView
        '''
        tree = self.view.widgets.sp_syn_treeview        
        def _syn_data_func(column, cell, model, iter, data=None):
            v = model[iter][0]
            cell.set_property('text', str(v.synonym))
            # just added so change the background color to indicate its new
            if not v.isinstance:
                cell.set_property('foreground', 'blue')
            else:
                cell.set_property('foreground', None)
        cell = gtk.CellRendererText()
        col = gtk.TreeViewColumn('Synonym', cell)
        col.set_cell_data_func(cell, _syn_data_func)
        tree.append_column(col)
        
        tree_model = gtk.ListStore(object)
        for syn in model:
            tree_model.append([syn])
        tree.set_model(tree_model)        
        tree.connect('cursor-changed', self.on_tree_cursor_changed)
    
    
    def on_tree_cursor_changed(self, tree, data=None):
        '''
        '''
        path, column = tree.get_cursor()
        self.view.widgets.sp_syn_remove_button.set_sensitive(True)

    
    def refresh_view(self):
        '''
        doesn't do anything
        '''
        return
        
        
    def init_syn_entry(self):
        '''
        initializes the synonym entry
        '''
        completion = self.view.widgets.sp_syn_entry.get_completion()
        completion.connect('match-selected', self.on_syn_match_selected)
        #if self.model.synonym is not None:
        #    genus = self.model.synonym.genus
        #    self.idle_add_species_completions(str(genus)[:2])
        
        
    def on_add_button_clicked(self, button, data=None):
        '''
        adds the synonym from the synonym entry to the list of synonyms for 
            this species
        '''
        syn = SQLObjectProxy(SpeciesSynonym)
        syn.synonym = self.selected
        self.model.append(syn)
        self.selected = None
        entry = self.view.widgets.sp_syn_entry
        entry.handler_block(self.insert_syn_sid)
        entry.set_text('')
        entry.set_position(-1)
        entry.handler_unblock(self.insert_syn_sid)
        self.view.widgets.sp_syn_add_button.set_sensitive(False)
        self.view.set_accept_buttons_sensitive(True)
        
        
    def on_remove_button_clicked(self, button, data=None):
        '''
        removes the currently selected synonym from the list of synonyms for
        this species
        '''
        # TODO: maybe we should only ask 'are you sure' if the selected value
        # is an instance, this means it will be deleted from the database        
        tree = self.view.widgets.sp_syn_treeview
        path, col = tree.get_cursor()
        model = tree.get_model()
        value = model[model.get_iter(path)][0]
        s = Species.str(value.synonym, markup=True)
        msg = 'Are you sure you want to remove %s as a synonym to the ' \
              'current species?\n\n<i>Note: This will not remove the species '\
              '%s from the database.</i>' % (s, s)
        if utils.yes_no_dialog(msg, parent=self.view.window):
            self.model.remove(model.get_iter(path))
            self.view.set_accept_buttons_sensitive(True)
    
    
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
        self.view.widgets.sp_syn_add_button.set_sensitive(True)
        self.selected = synonym
#        debug('%s' % self.model)
        self.prev_text = str(synonym)
        
        
    def on_syn_entry_delete(self, entry, start, end, data=None):
        '''
        '''
#        debug('on_species_delete: \'%s\'' % entry.get_text())        
#        debug(self.model.species)
        text = entry.get_text()
        full_text = text[:start] + text[end:]
        if full_text == '' or (full_text == str(self.selected)):
            self.remove_problem(self.PROBLEM_INVALID_SYNONYM, 
                                self.view.widgets.sp_syn_entry)
            return
        self.add_problem(self.PROBLEM_INVALID_SYNONYM, 
                         self.view.widgets.sp_syn_entry)
        self.view.widgets.sp_syn_add_button.set_sensitive(False)
        self.selected = None
        
    
    def on_syn_entry_insert(self, entry, new_text, new_text_length, position, 
                            data=None):
        '''
        '''
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
#            debug('new text is empty')
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
            self.view.widgets.sp_syn_add_button.set_sensitive(False)
            self.selected = None
#        debug('%s' % self.model)


    def idle_add_syn_completions(self, text):
        '''
        '''
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
    
    
    
# TODO: there is no way to set the check buttons to None once they
# have been set and the inconsistent state doesn't convey None that
# well, the only other option I know of is to use Yes/No/None combos
# instead of checks
        
class SpeciesMetaPresenter(GenericEditorPresenter):    
    
    widget_to_field_map = {'sp_dist_combo': 'distribution',
                           'sp_humanpoison_check': 'poison_humans',
                           'sp_animalpoison_check': 'poison_animals',
                           'sp_food_check': 'food_plant'}
        
    def __init__(self, model, view, defaults={}):
        '''
        @param model:
        @param view:
        @param defaults:
        '''
        GenericEditorPresenter.__init__(self, model, view)        
        self.init_distribution_combo()
        # we need to call refresh view here first before setting the signal
        # handlers b/c SpeciesEditorPresenter will call refresh_view after
        # these are assigned causing the the model to appear dirty
        self.refresh_view() 
        self.assign_simple_handler('sp_humanpoison_check', 'poison_humans')
        self.assign_simple_handler('sp_animalpoison_check', 'poison_animals')
        self.assign_simple_handler('sp_food_check', 'food_plant')
        
        
    def init_distribution_combo(self):        
        '''
        '''
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
            self.view.widgets.sp_dist_combo.set_sensitive(True)
            self.view.set_widget_value('sp_dist_combo', self.model.distribution,
                                       default=self.defaults.get('distribution', None))
            self.assign_simple_handler('sp_dist_combo', 'distribution')
        gobject.idle_add(_populate)
        
        
    def refresh_view(self):
        '''
        '''
#        debug('SpeciesMetaPresenter.refresh_view()')
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
        '''
        the constructor
        
        @param parent: the parent window
        '''
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
            if entry == 'sp_genus_entry':
                completion.set_cell_data_func(cell, self._genus_completion_cell_data_func)    
            else:
                completion.set_cell_data_func(cell, self._completion_cell_data_func)    
            completion.set_minimum_key_length(2)
            completion.set_popup_completion(True)        
            self.widgets[entry].set_completion(completion)    
        
        self.restore_state()
        self.connect_dialog_close(self.widgets.species_dialog)
        if sys.platform == 'win32':
            self.do_win32_fixes()
        
        
    def _get_window(self):
        '''
        '''
        return self.widgets.species_dialog    
    window = property(_get_window)
    
    
    def set_accept_buttons_sensitive(self, sensitive):        
        '''
        set the sensitivity of all the accept/ok buttons for the editor dialog
        '''
        self.widgets.sp_ok_button.set_sensitive(sensitive)
        self.widgets.sp_ok_and_add_button.set_sensitive(sensitive)
        self.widgets.sp_next_button.set_sensitive(sensitive)
        
        
    def _lower_completion_match_func(self, completion, key_string, iter, 
                                    data=None):
        '''
        the only thing this does different is it make the match case insensitve
        '''
        value = completion.get_model()[iter][0]
        return str(value).lower().startswith(key_string.lower())   
        
        
    def _genus_completion_cell_data_func(self, column, renderer, model, iter, 
                                         data=None):
        '''
        '''
        v = model[iter][0]
        renderer.set_property('text', '%s (%s)' % \
                              (Genus.str(v, full_string=True), 
                               Family.str(v.family, full_string=True)))
        
        
    def _completion_cell_data_func(self, column, renderer, model, iter, 
                                         data=None):
        '''
        '''
        v = model[iter][0]
        renderer.set_property('text', str(v))
        
        
    def do_win32_fixes(self):
        '''
        '''
        pass
        
        
    def save_state(self):        
        '''
        save the current state of the gui to the preferences
        '''
        for expander, pref in self.expanders_pref_map.iteritems():
            prefs[pref] = self.widgets[expander].get_expanded()
        
        
    def restore_state(self):
        '''
        restore the state of the gui from the preferences
        '''
        for expander, pref in self.expanders_pref_map.iteritems():
            expanded = prefs.get(pref, True)
            self.widgets[expander].set_expanded(expanded)

            
    def start(self):
        '''
        starts the views, essentially calls run() on the main dialog
        '''
        return self.widgets.species_dialog.run()    
    


class SpeciesEditor(GenericModelViewPresenterEditor):
    
    label = 'Species'
    # these have to correspond to the response values in the view
    RESPONSE_OK_AND_ADD = 11
    RESPONSE_NEXT = 22
    ok_responses = (RESPONSE_OK_AND_ADD, RESPONSE_NEXT)    
    
    def __init__(self, model=Species, defaults={}, parent=None, **kwargs):
        '''
        @param model: Species
        @param defaults: {}
        @param parent: None
        '''
        
        self.assert_args(model, Species, defaults)
        GenericModelViewPresenterEditor.__init__(self, model, defaults, parent)
        if parent is None: # should we even allow a change in parent
            parent = bauble.app.gui.window
        # keep parent and defaults around in case in start() we get
        # RESPONSE_NEXT or RESPONSE_OK_AND_ADD we can pass them to the new 
        # editor
        self.parent = parent
        self.defaults = defaults 
        
        
    def start(self, commit_transaction=True):    
        '''
        @param commit_transaction: where we should call 
            sqlhub.processConnection.commit() to commit our changes
        '''
        if tables['Genus'].select().count() == 0:
            msg = 'You must first add or import at least one genus into the '\
                  'database before you can add species.'
            utils.message_dialog(msg)
            return
        self.view = SpeciesEditorView(parent=self.parent)
        self.presenter = SpeciesEditorPresenter(self.model, self.view,
                                                self.defaults)
        not_ok_msg = 'Are you sure you want to lose your changes?'
        exc_msg = "Could not commit changes.\n"
        committed = None
        while True:
            response = self.presenter.start()
            self.view.save_state() # should view or presenter save state
            vernacular_dirty = self.presenter.vern_presenter is not None and \
                self.presenter.vern_presenter.model.dirty
            synonyms_dirty = self.presenter.synonyms_presenter is not None and \
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
                self.model.dirty = False
                break
            elif not (self.model.dirty or sub_presenters_dirty):
                break
            
        if commit_transaction:
            sqlhub.processConnection.commit()

        # respond to responses
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
                                           defaults={'species': committed})
            more_committed = e.start(commit_transaction)            
                    
        if more_committed is not None:
            committed = [committed]
            if isinstance(more_committed, list):
                committed.extend(more_committed)
            else:
                committed.append(more_committed)
                
        return committed
    
    
    def commit_changes(self):
        '''
        commit all changes to the species editor
        '''
#        debug(self.model)
        synonyms = self.model.pop('synonyms', None)
        vnames = self.model.pop('vernacular_names', None)
        meta = self.model.pop('species_meta', None)
        species = None
        if self.model.dirty:
            if self.model.sp_hybrid is not None:
                self.model.infrasp_rank = None
                self.model.cv_group = None
            elif self.model.infrasp_rank is None:
                self.model.infrasp = None
                self.model.infrasp_author = None
                self.model.cv_group = None
            elif self.model.infrasp_rank != 'cv.': 
                # no cv group if not a cultivar
                self.model.cv_group = None
            species = self._commit(self.model)        
        elif self.model.isinstance:
            species = self.model.so_object

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
        meta_model = self.presenter.meta_presenter.model 
        meta = None
        if meta_model.dirty:
            meta_model.species = species
            meta = commit_to_table(SpeciesMeta, meta_model)
        return meta
                        
        
    def commit_vernacular_name_changes(self, species):
        '''
        returns the vernacular name instance that was selected as the default
        '''
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
            
        # delete the items that need to be removed from the database    
        for item in vn_model.removed:
            item.destroySelf()

        return default
        
        
    def commit_synonyms_changes(self, species):
        '''
        commit changes in the synonyms presenter
        '''
        syn_model = self.presenter.synonyms_presenter.model 
        for item in syn_model:
            # if it has a species that means it's not a new synonym
            if item.species is None:
                item.species = species
                commit_to_table(SpeciesSynonym, item)
        
        for item in syn_model.removed:
            item.destroySelf()
        
    
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
    class VernacularExpander(InfoExpander):
        '''
        the constructor
        '''
        def __init__(self, glade_xml):
            InfoExpander.__init__(self, "Vernacular Names", glade_xml)
            vernacular_box = self.widgets.vernacular_box
            if vernacular_box.get_parent() is not None:
                vernacular_box.get_parent().remove(vernacular_box)                
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
                    if vn == row.default_vernacular_name:
                        names.insert(0, '%s - %s (default)' % \
                                     (vn.name, vn.language))
                    else:
                        names.append('%s - %s' % \
                                     (vn.name, vn.language))
                self.set_widget_value('vernacular_data', '\n'.join(names))
                self.set_sensitive(True)
                # TODO: get expanded state from prefs
                self.set_expanded(True) 
        
        
            
    class SynonymsExpander(InfoExpander):
        
        def __init__(self, glade_xml):
            InfoExpander.__init__(self, "Synonyms", glade_xml)
            synonyms_box = self.widgets.synonyms_box
            if synonyms_box.get_parent() is not None:
                synonyms_box.get_parent().remove(synonyms_box)                
            self.vbox.pack_start(synonyms_box)
            
            
        def update(self, row):
            '''
            update the expander
            
            @param row: the row to get thevalues from
            '''
            if len(row.synonyms) == 0:
                self.set_sensitive(False)
                self.set_expanded(False)
            else:
                synonyms = []
                for syn in row.synonyms:
                    s = Species.str(syn.synonym, markup=True, authors=True)
                    synonyms.append(s)
                self.widgets.synonyms_data.set_markup('\n'.join(synonyms))
                self.set_sensitive(True)
                # TODO: get expanded state from prefs
                self.set_expanded(True)
        
    
    
    class GeneralSpeciesExpander(InfoExpander):
        '''
        generic information about an accession like
        number of clones, provenance type, wild provenance type, speciess
        '''
    
        def __init__(self, glade_xml):
            '''
            the constructor
            '''
            InfoExpander.__init__(self, "General", glade_xml)
            general_box = self.widgets.general_box
            if general_box.get_parent() is not None:
                general_box.get_parent().remove(general_box)
                
            self.vbox.pack_start(general_box)
            
            # make the check buttons read only
            def on_enter(button, *args):
                button.emit_stop_by_name("enter-notify-event")
                return TRUE 
            self.widgets.food_check.connect('enter-notify-event', on_enter)
            self.widgets.phumans_check.connect('enter-notify-event', on_enter)
            self.widgets.panimals_check.connect('enter-notify-event', on_enter)

        
        def update(self, row):
            '''
            update the expander
            
            @param row: the row to get the values from
            '''
            self.set_widget_value('name_data', row.markup(True))
            self.set_widget_value('nacc_data', len(row.accessions))
            
            #nplants = 0
            #for acc in row.accessions:
            #    nplants += len(acc.plants)
            #nacc_data_str = '%s in %s plants' % (len(row.accessions), nplants)
            #self.set_widget_value('nacc_data', nacc_data_str)
            
            if row.id_qual is not None:
                self.widgets.idqual_label.set_sensitive(True)
                self.widgets.idqual_data.set_sensitive(True) 
                self.set_widget_value('idqual_data', row.id_qual)
            else:
                self.widgets.idqual_label.set_sensitive(False)
                self.widgets.idqual_data.set_sensitive(False)
            
            if row.species_meta is not None:
                meta = row.species_meta
                self.set_widget_value('dist_data', meta.distribution)
                self.set_widget_value('food_check', meta.food_plant)
                self.set_widget_value('phumans_check', meta.poison_humans)
                self.set_widget_value('panimals_check', meta.poison_animals)
            
            nplants = 0
            # TODO: could probably speed this up quite a bit with an sql query
            # and sql max function
            for acc in row.accessions:
                nplants += len(acc.plants)
            self.set_widget_value('nplants_data', nplants)    
    
    
    
    class SpeciesInfoBox(InfoBox):
        '''
        - general info, fullname, common name, num of accessions and clones
        - poisonous to humans
        - poisonous to animals
        - food plant
        - origin/distribution
        '''
        
        # others to consider: reference, images, redlist status
        
        def __init__(self):
            ''' 
            the constructor
            '''
            InfoBox.__init__(self)
            glade_file = os.path.join(paths.lib_dir(), 'plugins', 'plants', 
                                      'species_infobox.glade')            
            self.glade_xml = gtk.glade.XML(glade_file)
            
            self.general = GeneralSpeciesExpander(self.glade_xml)
            self.add_expander(self.general)
            self.vernacular = VernacularExpander(self.glade_xml)
            self.add_expander(self.vernacular)
            self.synonyms = SynonymsExpander(self.glade_xml)
            self.add_expander(self.synonyms)
            
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
            #self.ref.update(row.references)
            #self.ref.value = row.references
            #ref = self.get_expander("References")
            #ref.set_values(row.references)
        
