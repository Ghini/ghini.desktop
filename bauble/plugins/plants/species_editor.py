#
# Species table definition
#
import os
import xml.sax.saxutils as sax
import gtk, gobject
from sqlalchemy import *
from sqlalchemy.orm.session import object_session
from sqlalchemy.exceptions import SQLError
import formencode.validators as validators
import bauble.utils as utils
import bauble.paths as paths
from bauble.plugins import tables, editors
from bauble.editor import *
from bauble.utils.log import log, debug
from bauble.plugins.plants.family import Family
from bauble.plugins.plants.genus import Genus
from bauble.plugins.plants.species_model import Species, SpeciesMeta, \
    SpeciesSynonym, VernacularName
from bauble.plugins.garden.accession import AccessionEditor

# TODO: would be nice, but not necessary, to edit existing vernacular names
# instead of having to add new ones

# TODO: what about author string and cultivar groups

# TODO: ensure None is getting set in the model instead of empty strings, 
# UPDATE: i think i corrected most of these but i still need to double check

def expunge_or_delete(session, instance):
    print instance in session.new
    if instance.id is None:
        session.expunge(instance)
    else:
        session.delete(instance)
            

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
    
    
    def __init__(self, model, view):                
        GenericEditorPresenter.__init__(self, ModelDecorator(model), view)
        self.session = object_session(model)
        self.init_genus_entry()
        #self.init_infrasp_rank_combo()
        self.init_combos()
        self.init_fullname_widgets()

        self.vern_presenter = VernacularNamePresenter(self.model.vernacular_names, 
                                                      self.view, self.session)        
        self.synonyms_presenter = SynonymsPresenter(self.model.synonyms, 
                                                    self.view, self.session)
        self.meta_presenter = SpeciesMetaPresenter(self.model.species_meta, 
                                                   self.view, self.session)
        
        self.sub_presenters = (self.vern_presenter, self.synonyms_presenter, self.meta_presenter)
        
        self.refresh_view()        
        
        #self.view.widgets.sp_infra_rank_combo.connect('changed', self.on_infra_rank_changed)

        self.assign_simple_handler('sp_species_entry', 'sp', StringOrNoneValidator())
        self.assign_simple_handler('sp_infra_rank_combo', 'infrasp_rank', StringOrNoneValidator())
        self.assign_simple_handler('sp_hybrid_combo', 'sp_hybrid', StringOrNoneValidator())
        self.assign_simple_handler('sp_infra_entry', 'infrasp', StringOrNoneValidator())
        self.assign_simple_handler('sp_cvgroup_entry', 'cv_group', UnicodeOrNoneValidator())
        self.assign_simple_handler('sp_infra_author_entry', 'infrasp_author', UnicodeOrNoneValidator())
        self.assign_simple_handler('sp_idqual_combo', 'id_qual', StringOrNoneValidator()) 
        self.assign_simple_handler('sp_spqual_combo', 'sp_qual', StringOrNoneValidator())
        self.assign_simple_handler('sp_author_entry', 'sp_author', UnicodeOrNoneValidator())
        self.assign_simple_handler('sp_notes_textview', 'notes', UnicodeOrNoneValidator())
        
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
#                    debug(none_list)
                    if len(none_list) != 0:
                        none_status.append(none_list)
                elif getattr(self.model, field) is not None:
                    none_status.append(field)
            
#            debug(none_status)
#            debug(len(none_status))
#            debug(len(states_dict[widget]))
            if len(none_status) == len(states_dict[widget]):
                self.view.widgets[widget].set_sensitive(True)
            else:
                self.view.widgets[widget].set_sensitive(False)        
        
        # turn off the infraspecific rank combo if the hybrid value in the model
        # is not None, this has to be called before the conditional that
        # sets the sp_cvgroup_entry
        if self.model.sp_hybrid is not None:
            self.view.widgets.sp_infra_rank_combo.set_sensitive(False)
        
        # infraspecific rank has to be a cultivar for the cultivar group entry
        # to be sensitive
        if self.model.infrasp_rank == 'cv.' and self.view.widgets['sp_infra_rank_combo'].get_property('sensitive'):
            self.view.widgets.sp_cvgroup_entry.set_sensitive(True)
        else:
            self.view.widgets.sp_cvgroup_entry.set_sensitive(False)
            
        
    
            
    def on_field_changed(self, model, field):
        '''
        rests the sensitivity on the ok buttons and the name widgets when 
        values change in the model
        '''
#        debug('on_field_changed: %s' % field)
#        debug('on_field_changed: %s = %s' % (field, getattr(model, field)))
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
            #debug(field)               
            self.model.add_notifier(field, self.on_field_changed)
            #add_notifier(self.model, field, self.on_field_changed)
                        
        #for field in self.synonyms_presenter.widget_to_field_map.values():            
        #    self.model.add_notifier(field, self.on_field_changed)
            
        #for field in self.vern_presenter.widget_to_field_map.values():
        #    self.model.add_notifier(field, self.on_field_changed)
            
        for field in self.meta_presenter.widget_to_field_map.values():
            #pass
            self.meta_presenter.model.add_notifier(field, self.on_field_changed)
          
        #self.vern_presenter.set_default_changed_notifier(self.on_field_changed)
        self.vern_presenter.set_default_changed_notifier(self.on_default_changed)
        
            
    def on_default_changed(self, obj):
        self.model.default_vernacular_name = obj
        self.on_field_changed(self.model, 'default_vernacular_name')
        
            
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
            column = self.model.c[self.widget_to_field_map[combo_name]]            
            for enum in sorted(column.type.values):
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
            # create an object that behaves like a Species and pass it to 
            # Species.str
            d = {}
            d.update(zip(self.model.c.keys(), 
                          [getattr(self.model, k) for k in self.model.c.keys()]))            
            
            class attr_dict(object):
                def __init__(self, d):
                    attr_dict.__setattr__(self, '__dict', d)                
                def __getattr__(self, item):
                    d = self.__getattribute__('__dict')
                    if item is '__dict':
                        return d
                    elif item in d:
                        return d[item]
                    else:
                        return getattr(d, item)
                def __setattr__(self, item, value):
                    if item is '__dict':                    
                        super(attr_dict, self).__setattr__(item , value)
                    d = self.__getattribute__('__dict')
                    d[item] = value                    
                def iteritems(self):
                    d = self.__getattribute__('__dict')
                    return d.iteritems()
                
            values = attr_dict(d)
            values.genus = self.model.genus
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

            s = '%s  -  %s' % (Family.str(self.model.genus.family, full_string=True),
                               Species.str(values, authors=True, markup=True))
        self.view.widgets.sp_fullname_label.set_markup(s)
    
    
    def idle_add_genus_completions(self, text):
        '''
        adds completions to the genus entry according to text
        
        text -- the text to match against
        '''
        # TODO: it would be nice if we put the genus completions in a separate
        # session so if we have to do anything like loop through the objects in 
        # the session then it won't slow things down too much
#        debug('idle_add_genus_competions: %s' % text)            
        sr = self.session.query(Genus).select(Genus.c.genus.like('%s%%' % text))        
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
        debug('selected: %s' % str(genus))
        entry = self.view.widgets.sp_genus_entry
        entry.handler_block(self.insert_genus_sid)
        entry.set_text(str(genus))
        entry.handler_unblock(self.insert_genus_sid)
        entry.set_position(-1)
        self.remove_problem(self.PROBLEM_INVALID_GENUS, 
                            self.view.widgets.sp_genus_entry)
        self.session.save(genus)
        self.model.genus = genus
        self.refresh_fullname_label()
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
            value = getattr(self.model, field)
#            debug('%s, %s, %s' % (widget, field, value))            
#            self.view.set_widget_value(widget, value, 
#                                       default=self.defaults.get(field, None))             
            self.view.set_widget_value(widget, value)
        self.refresh_sensitivity()
        debug(self.model.default_vernacular_name)
        debug(self.model.default_vernacular_name_id)
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


#class ModelDecorator_OLD:
#        # could use this to provide __iter__ and .dirty but that still doesn't 
#        # solve the problem of how we determine what's dirty unless we set dirty
#        # whenever add or remove is clicked
#         
#        def __init__(self, model, dirty=False):
#            '''
#            model: a tree view model
#            '''
#            self.model = model
#            self.dirty = dirty
#            self.removed = []
#            self.session = object_session(model)
#                
#        def __iter__(self):    
#            self.next_iter = self.model.get_iter_root()
#            return self
#        
#            
#        def __len__(self):
#            return len(self.model)
#    
#        current_iter = None
#        next_iter = None
#        def next(self):
#            '''
#            '''
#            self.current_iter = self.next_iter
#            if self.current_iter is None:
#                raise StopIteration
#            v = self.model[self.current_iter][0]
#            self.next_iter = self.model.iter_next(self.current_iter)
#            return v
#                
#                
#        def remove(self, item):
#            '''
#            @param item: the value to remove from the model, if item is a 
#                gtk.TreeModelIter then remove only the item that item points to,
#                else remove all items in the model that are the same as item
#            '''            
#            # if item is a TreeIter then remove only that value
#            if isinstance(item, gtk.TreeIter):
#                value = self.model[item][0]
#                self.model.remove(item)
#                #if isinstance(value, SQLObjectProxy) and value.isinstance:
#                #    self.removed.append(value)
#                #    self.dirty = True
#                
#            else:
#                # search through the model for all occurences of item and 
#                # remove them from the model and append them to self.removed    
#                while 1:
#                    row = utils.search_tree_model(self.model, item)
#                    if row is None:
#                        break
#                    self.model.remove(row.iter)
#                    # if is an instance then add to removed so we can delete it 
#                    # from the database later
#                    if isinstance(item, SQLObjectProxy) and item.isinstance:
#                        self.removed.append(item)                    
#                        self.dirty = True
#            
#            
#        def append(self, item):
#            '''
#            @param item:
#            '''
#            self.dirty = True
#            return self.model.append([item])
            


class VernacularNamePresenter(GenericEditorPresenter):
    # TODO: change the background of the entries and desensitize the 
    # name/lang entries if the name conflicts with an existing vernacular
    # name for this species
    
    def __init__(self, model, view, session):
        '''
        @param model: a list of VernacularName objects
        @param view: see GenericEditorPresenter
        '''
        GenericEditorPresenter.__init__(self, model, view)
        self.session = session
        self.default = None
        self.init_treeview(model)
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
        vn = VernacularName(name=name, language=lang)
        self.session.save(vn)
        tree_model = self.treeview.get_model()
        it = tree_model.append([vn])        
        if len(tree_model) == 1:            
            self.default = gtk.TreeRowReference(tree_model, tree_model.get_path(it))
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
            model.remove(model.get_iter(path))
            debug('delete value: %s' % value)
            expunge_or_delete(self.session, value)
            self.view.set_accept_buttons_sensitive(True)            
            # check if we removed the item designated as the default 
            # vernacular name and if so reset it to the first row in the model
            if not self.default.valid():
                #path = self.model.model.get_path(self.model.model.get_iter_first())
                first = model.get_iter_first()
                if first is not None:
                    path = model.get_path(model.get_iter_first())
                    self.default = gtk.TreeRowReference(model, path)
                else:
                    self.default = None
        
        
    def set_default_changed_notifier(self, callback):    
        '''
        set the callback to call when the default toggles changes, will be
        called like C{callback('vernacular_name_obj')}
        '''
        self.default_changed_callback = callback
        
        
    def on_default_toggled(self, cell, path, data=None):        
        '''
        default column callback
        '''
        # TODO: there is a bug here that if the object set as the default
        # is a pending object without an id then the default_vernacular_name_id
        # will get reset to None since the object doesn't have an idea, the 
        # correct way to fix this is to make default_vernacular_name_id a proper
        # ForeignKey but right now SQLAlchemy complains about circular 
        # references
        active = cell.get_property('active')        
        if not active:
            tree_model = self.treeview.get_model()
            self.default = gtk.TreeRowReference(tree_model, path)
            it = tree_model.get_iter(self.default.get_path())
            debug(tree_model[it][0])
            self.default_changed_callback(tree_model[it][0])
        
    
    def init_treeview(self, model):
        '''
        '''
        self.treeview = self.view.widgets.vern_treeview
                
        def _name_data_func(column, cell, model, iter, data=None):
            v = model[iter][0]
            cell.set_property('text', v.name)
            # just added so change the background color to indicate its new
#            if not v.isinstance:
            if v.id is None: # hasn't been committed
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
        self.treeview.append_column(col)
        
        def _lang_data_func(column, cell, model, iter, data=None):
            v = model[iter][0]
            cell.set_property('text', v.language)
            # just added so change the background color to indicate its new
            #if not v.isinstance:` 
            if v.id is None: # hasn't been committed
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
        self.treeview.append_column(col)
        
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
        self.treeview.append_column(col)
        
        self.treeview.set_model(None)
        
        # TODO: why am i setting self.treeview.model and why does this work
        self.treeview.model = gtk.ListStore(object)
        for vn in self.model:
            debug(vn)
            self.treeview.model.append([vn])
        self.treeview.set_model(self.treeview.model)
        
        self.treeview.connect('cursor-changed', self.on_tree_cursor_changed)
        
    
    def on_tree_cursor_changed(self, tree, data=None):
        path, column = tree.get_cursor()
        self.view.widgets.sp_vern_remove_button.set_sensitive(True)
        
    
    def refresh_view(self, default_vernacular_name):        
        tree_model = self.treeview.get_model()
        if len(self.model) > 0 and default_vernacular_name is None:
            msg = 'This species has vernacular names but none of them are '\
                  'selected as the default. The first vernacular name in the '\
                  'list has been automatically selected.'
            utils.message_dialog(msg)
            first = tree_model.get_iter_first()
            value = tree_model[first][0]
            path = tree_model.get_path(first)
            self.default = gtk.TreeRowReference(tree_model, path)
            value.species.default_vernacular_name = value
            self.view.set_accept_buttons_sensitive(True)
            return
        elif default_vernacular_name is None:
            return
        
        # select the default_vernacular_name
        for row in tree_model:
            vn = row[0]
            if vn.id == default_vernacular_name.id:
                path  = tree_model.get_path(row.iter)
                self.default = gtk.TreeRowReference(tree_model, path)
        if self.default is None:
            raise ValueError('couldn\'t set the default name: %s' % 
                             default_vernacular_name)
    
#
# TODO: you shouldn't be able to set a plant as a synonym of itself
#
class SynonymsPresenter(GenericEditorPresenter):
    
    PROBLEM_INVALID_SYNONYM = 1
    
    
    def __init__(self, model, view, session):
        '''
        @param model: a list of SQLObject proxy objects
        @param view: see GenericEditorPresenter
        @param defaults: see GenericEditorPresenter
        '''
        GenericEditorPresenter.__init__(self, model, view)
        self.session = session
        self.init_treeview(model)
        #self.model = ModelDecorator(self.view.widgets.sp_syn_treeview.get_model())   
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
        self.treeview = self.view.widgets.sp_syn_treeview        
        def _syn_data_func(column, cell, model, iter, data=None):
            v = model[iter][0]
            cell.set_property('text', str(v.synonym))
            # just added so change the background color to indicate its new
            if v.id is None:
                cell.set_property('foreground', 'blue')
            else:
                cell.set_property('foreground', None)
        cell = gtk.CellRendererText()
        col = gtk.TreeViewColumn('Synonym', cell)
        col.set_cell_data_func(cell, _syn_data_func)
        self.treeview.append_column(col)
        
        tree_model = gtk.ListStore(object)
        for syn in model:
            tree_model.append([syn])
        self.treeview.set_model(tree_model)        
        self.treeview.connect('cursor-changed', self.on_tree_cursor_changed)
    
    
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
        syn = SpeciesSynonym()
        self.session.save(syn)
        syn.synonym = self.selected
        tree_model = self.treeview.get_model()
        tree_model.append([syn])
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
        tree_model = tree.get_model()
        value = tree_model[tree_model.get_iter(path)][0]      
        debug('%s: %s' % (value, type(value)))
        s = Species.str(value.synonym, markup=True)
        msg = 'Are you sure you want to remove %s as a synonym to the ' \
              'current species?\n\n<i>Note: This will not remove the species '\
              '%s from the database.</i>' % (s, s)
        if utils.yes_no_dialog(msg, parent=self.view.window):
            tree_model.remove(tree_model.get_iter(path))
            #self.session.delete(value)            
            debug('%s: %s' % (value, type(value)))
            expunge_or_delete(self.session, value)            
            self.view.set_accept_buttons_sensitive(True)
        debug(value in self.session)
    
    
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
        #like_genus = sqlhub.processConnection.sqlrepr(_LikeQuoted('%s%%' % genus))
        #sr = tables["Genus"].select('genus LIKE %s' % like_genus)
        sr = self.session.query(Genus).select(Genus.c.genus.like('%s%%' % text))
        def _add_completion_callback(select):        
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
        
    def __init__(self, model, view, session):
        '''
        @param model:
        @param view:
        @param session: the session to save the model to, can be different than 
        that session the model is bound to
        '''        
        if model is None:
            assert(session is not None), 'you must pass either a session or model'
            sp_meta = SpeciesMeta()
            #session.save(sp_meta)
        else:
            sp_meta = model                        
        
        GenericEditorPresenter.__init__(self, ModelDecorator(sp_meta), view)        
        self.session = session
        debug(self.model)
        self.init_distribution_combo()
        # we need to call refresh view here first before setting the signal
        # handlers b/c SpeciesEditorPresenter will call refresh_view after
        # these are assigned causing the the model to appear dirty
        self.refresh_view() 
        self.assign_simple_handler('sp_humanpoison_check', 'poison_humans')
        self.assign_simple_handler('sp_animalpoison_check', 'poison_animals')
        self.assign_simple_handler('sp_food_check', 'food_plant')
                
        for field in self.widget_to_field_map.values():         
            self.model.add_notifier(field, self.on_field_changed)
    
    
    def on_field_changed(self, model, field):
        # if any field changed then attach the current model to the sesion
        # if it hasn't been
        if not model in self.session:
            self.session.save(model)
        
        
    def init_distribution_combo(self):        
        '''
        '''
        def _populate():
            self.view.widgets.sp_dist_combo.set_model(None)
            model = gtk.TreeStore(str)
            model.append(None, ["Cultivated"])            
            from bauble.plugins.geography.distribution import continent_table, \
                region_table, botanical_country_table, basic_unit_table
            region_select = select([region_table.c.id, region_table.c.region], 
                                   region_table.c.continent_id==bindparam('continent_id')).compile()
            country_select = select([botanical_country_table.c.id, botanical_country_table.c.name], 
                                    botanical_country_table.c.region_id==bindparam('region_id')).compile()
            unit_select = select([basic_unit_table.c.name, basic_unit_table.c.id], 
                                 basic_unit_table.c.botanical_country_id==bindparam('country_id')).compile()                        
            for continent_id, continent in select([continent_table.c.id, continent_table.c.continent]).execute():
                p1 = model.append(None, [continent])
                for region_id, region in region_select.execute(continent_id=continent_id):
                    p2 = model.append(p1, [region])
                    for country_id, country in country_select.execute(region_id=region_id):
                        p3 = model.append(p2, [country])
                        for unit, dummy in unit_select.execute(country_id=country_id):
                            if unit != country:
                                model.append(p3, [unit])
            self.view.widgets.sp_dist_combo.set_model(model)
            self.view.widgets.sp_dist_combo.set_sensitive(True)
            self.view.set_widget_value('sp_dist_combo', self.model.distribution)
            self.assign_simple_handler('sp_dist_combo', 'distribution')
        gobject.idle_add(_populate)
    
        
        
    def refresh_view(self):
        '''
        '''

        for widget, field in self.widget_to_field_map.iteritems():
            value = getattr(self.model, field)
            self.view.set_widget_value(widget, value)
            
    

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
        
        self.attach_completion('sp_genus_entry', self.genus_completion_cell_data_func)
        self.attach_completion('sp_syn_entry', self.syn_cell_data_func)
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
        
        
    def genus_completion_cell_data_func(self, column, renderer, model, iter, 
                                         data=None):
        '''
        '''
        v = model[iter][0]
        renderer.set_property('text', '%s (%s)' % \
                              (Genus.str(v, full_string=True), 
                               Family.str(v.family, full_string=True)))
        
        
    def syn_cell_data_func(self, column, renderer, model, iter, 
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
    

# If a a mapped object that is attached to a session is passed into the 
# SpeciesEditor the we will use the same session that the mapped object is 
# attached to. This could mean that we make changes the the object but if the 
# editor is cancelled or closed then the changes will stay on the object without
# being rolled back. If someone else using the same session at some point 
# flushes the session then the changes that had earlier been cancelled would
# then be committed.
class SpeciesEditor(GenericModelViewPresenterEditor):
    
    label = 'Species'
    # these have to correspond to the response values in the view
    RESPONSE_OK_AND_ADD = 11
    RESPONSE_NEXT = 22
    ok_responses = (RESPONSE_OK_AND_ADD, RESPONSE_NEXT)    
    
    def __init__(self, model_or_defaults=None, parent=None):
        '''
        @param model_or_defaults: Species or dictionary of values for Species
        @param parent: None
        '''        
        if isinstance(model_or_defaults, dict):
            model = Species(**model_or_defaults)
        elif model_or_defaults is None:
            model = Species()            
        elif isinstance(model_or_defaults, Species):
            model = model_or_defaults
        else:
            raise ValueError('model_or_defaults argument must either be a '\
                             'dictionary or Species instance')

        debug(model)
        GenericModelViewPresenterEditor.__init__(self, model, parent)
        debug('%s: %s' % (type(self.model), self.model))
        if parent is None: # should we even allow a change in parent
            parent = bauble.app.gui.window
        # keep parent and defaults around in case in start() we get
        # RESPONSE_NEXT or RESPONSE_OK_AND_ADD we can pass them to the new 
        # editor
        self.parent = parent
        
        
    _committed = None
    def handle_response(self, response):
        not_ok_msg = 'Are you sure you want to lose your changes?'
        if response == gtk.RESPONSE_OK or response in self.ok_responses:
#                debug('session dirty, committing')
            try:
                self.commit_changes()
                self._committed = self.model
            except SQLError, e:                
                exc = traceback.format_exc()
                msg = 'Error committing changes.\n\n%s' % e.orig
                utils.message_details_dialog(msg, str(e), gtk.MESSAGE_ERROR)
                return False
            except:
                msg = 'Unknown error when committing changes. See the details '\
                      'for more information.'
                utils.message_details_dialog(msg, traceback.format_exc(), 
                                             gtk.MESSAGE_ERROR)
                return False
        elif self.session.dirty and utils.yes_no_dialog(not_ok_msg):                
            return True
        elif not self.session.dirty:
            return True
        else:
            return False
        
        
#        # respond to responses
        more_committed = None
        if response == self.RESPONSE_NEXT:
            e = SpeciesEditor(parent=self.parent)
            more_committed = e.start()
        elif response == self.RESPONSE_OK_AND_ADD:
            e = AccessionEditor(model_or_defaults={'species_id': self._committed.id},
                                parent=self.parent)
            more_committed = e.start()
                    
        if more_committed is not None:
            self._committed = [self._committed]
            if isinstance(more_committed, list):
                self._ommitted.extend(more_committed)
            else:
                self._committed.append(more_committed)                
        
        return True

        
    def start(self):
        if self.session.query(Genus).count() == 0:        
            msg = 'You must first add or import at least one genus into the '\
                  'database before you can add species.'
            utils.message_dialog(msg)
            return
        self.view = SpeciesEditorView(parent=self.parent)
        self.presenter = SpeciesEditorPresenter(self.model, self.view)
        
        exc_msg = "Could not commit changes.\n"
        committed = None
        while True:
            response = self.presenter.start()
            self.view.save_state() # should view or presenter save state
            if self.handle_response(response):
                break
            
        self.session.close() # cleanup session
        return self._committed
    
    
    def commit_changes(self):
        # TODO: the 'obj not in self.session.deleted' part is to work around
        # a bug in SA, i reckon this will get fixed at some point
        for obj in self.session.new:
            if isinstance(obj, (VernacularName, SpeciesMeta, SpeciesSynonym)) \
              and obj not in self.session.deleted:
                obj.species = self.model
        return super(SpeciesEditor, self).commit_changes()

        
    
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
                    if vn == row.default_vernacular_name:
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
            self.widgets.sp_food_check.connect('enter-notify-event', on_enter)
            self.widgets.sp_phumans_check.connect('enter-notify-event', on_enter)
            self.widgets.sp_panimals_check.connect('enter-notify-event', on_enter)

        
        def update(self, row):
            '''
            update the expander
            
            @param row: the row to get the values from
            '''
            self.set_widget_value('sp_name_data', row.markup(True))
            self.set_widget_value('sp_nacc_data', len(row.accessions))
            
            #nplants = 0
            #for acc in row.accessions:
            #    nplants += len(acc.plants)
            #nacc_data_str = '%s in %s plants' % (len(row.accessions), nplants)
            #self.set_widget_value('nacc_data', nacc_data_str)
            
            if row.id_qual is not None:
                self.widgets.sp_idqual_label.set_sensitive(True)
                self.widgets.sp_idqual_data.set_sensitive(True) 
                self.set_widget_value('sp_idqual_data', row.id_qual)
            else:
                self.widgets.sp_idqual_label.set_sensitive(False)
                self.widgets.sp_idqual_data.set_sensitive(False)
            
            if row.species_meta is not None:
                meta = row.species_meta
                self.set_widget_value('sp_dist_data', meta.distribution)
                self.set_widget_value('sp_food_check', meta.food_plant)
                self.set_widget_value('sp_phumans_check', meta.poison_humans)
                self.set_widget_value('sp_panimals_check', meta.poison_animals)
            
            nplants = 0
            # TODO: could probably speed this up quite a bit with an sql query
            # and sql max function
            nacc_with_plants = 0
            for acc in row.accessions:
                if len(acc.plants) > 0:
                    nacc_with_plants += 1
                    nplants += len(acc.plants)
                    
            nplants_str = 0
            if nacc_with_plants > 0:
                nplants_str = '%s in %s accessions' % (nplants, nacc_with_plants)
            self.set_widget_value('sp_nplants_data', nplants_str)    
    
    
    
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
                                      'infoboxes.glade')            
            self.widgets = utils.GladeWidgets(gtk.glade.XML(glade_file))
            self.general = GeneralSpeciesExpander(self.widgets)
            self.add_expander(self.general)
            self.vernacular = VernacularExpander(self.widgets)
            self.add_expander(self.vernacular)
            self.synonyms = SynonymsExpander(self.widgets)
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
        
