#
# accessions module
#

import os
import gtk
from sqlobject import * 
import bauble.utils as utils
import bauble.paths as paths
from bauble.plugins import BaubleTable, tables, editors
from bauble.editor import TreeViewEditorDialog, TableEditorDialog, \
    TableEditor, SQLObjectProxy
from bauble.utils.log import debug
from bauble.prefs import prefs


class Accession(BaubleTable):

    class sqlmeta(BaubleTable.sqlmeta):
	       defaultOrder = 'acc_id'

    values = {} # dictionary of values to restrict to columns
    acc_id = StringCol(length=20, notNull=True, alternateID=True)
    
    
    prov_type = EnumCol(enumValues=("Wild", # Wild,
                                    "Propagule of cultivated wild plant", # Propagule of wild plant in cultivation
                                    "Not of wild source", # Not of wild source
                                    "Insufficient Data", # Insufficient data
                                    "Unknown",
                                    "<not set>"),
                        default = "<not set>")

    # wild provenance status, wild native, wild non-native, cultivated native
    wild_prov_status = EnumCol(enumValues=("Wild native", # Endemic found within it indigineous range
                                           "Wild non-native", # Propagule of wild plant in cultivation
                                           "Cultivated native", # Not of wild source
                                           "Insufficient Data", # Insufficient data
                                           "Unknown",
                                           "<not set>"),
                               default="<not set>")
    
    # propagation history ???
    #prop_history = StringCol(length=11, default=None)

    # accession lineage, parent garden code and acc id ???
    #acc_lineage = StringCol(length=50, default=None)    
    #acctxt = StringCol(default=None) # ???
    
    #
    # verification, a verification table would probably be better and then
    # the accession could have a verification history with a previous
    # verification id which could create a chain for the history
    #
    #ver_level = StringCol(length=2, default=None) # verification level
    #ver_name = StringCol(length=50, default=None) # verifier's name
    #ver_date = DateTimeCol(default=None) # verification date
    #ver_hist = StringCol(default=None)  # verification history
    #ver_lit = StringCol(default=None) # verification lit
    #ver_id = IntCol(default=None) # ?? # verifier's ID??
    

    # i don't think this is the red list status but rather the status
    # of this accession in some sort of conservation program
    #consv_status = StringCol(default=None) # conservation status, free text
    
    # foreign keys and joins
    species = ForeignKey('Species', notNull=True, cascade=False)
    plants = MultipleJoin("Plant", joinColumn='accession_id')
    
    # these should probably be hidden then we can do some trickery
    # in the accession editor to choose where a collection or donation
    # source, the source will contain one of collection or donation
    # tables
    # 
    # holds the string 'Collection' or 'Donation' which indicates where
    # we should get the source information from either of those columns
    # TODO: it seems like it would make more sense just to make this and
    # EnumCol(enumValues='Collection, Donation') since that's essentially
    # what it is anyways
    source_type = StringCol(length=64, default=None)    
                            
    # the source type says whether we should be looking at the 
    # _collection or _donation joins for the source info
    #_collection = SingleJoin('Collection', joinColumn='accession_id', makeDefault=None)
    _collection = SingleJoin('Collection', joinColumn='accession_id')
    _donation = SingleJoin('Donation', joinColumn='accession_id', makeDefault=None)
        
    notes = UnicodeCol(default=None)
    
    # these probably belong in separate tables with a single join
    #cultv_info = StringCol(default=None)      # cultivation information
    #prop_info = StringCol(default=None)       # propogation information
    #acc_uses = StringCol(default=None)        # accessions uses, why diff than taxon uses?
    
    def __str__(self): 
        return self.acc_id
    
    def markup(self):
        return '%s (%s)' % (self.acc_id, self.species.markup())


#
# Accession editor
#

def get_source(row):
    # TODO: in one of the release prior to 0.4.5 we put the string 'NoneType'
    # into some of the accession.source_type columns, this can cause an error
    # here but it's not critical, but we should make sure this doesn't happen
    # again in the future, maybe incorporated into a test
    if row.source_type == None:
        return None
    elif row.source_type == tables['Donation'].__name__:
        # the __name__ should be 'Donation'
        return row._donation
    elif row.source_type == tables['Collection'].__name__:
        return row._collection
    else:
        raise ValueError('unknown source type: ' + str(row.source_type))
    

    

            
# Model View Presenter pattern
# see http://www.martinfowler.com/eaaDev/ModelViewPresenter.html
class GenericEditorView:
    
    class _widgets(dict):
        '''
        dictionary and attribute access for widgets
        '''
        # TODO: should i worry about making this more secure/read only

        def __init__(self, glade_xml):
            self.glade_xml = glade_xml
        
        def __getitem__(self, name):
            # TODO: raise a key error if there is no widget
            return self.glade_xml.get_widget(name)
    
        def __getattr__(self, name):
            return self.glade_xml.get_widget(name)
        
    def __init__(self, glade_xml_path, parent=None):
        self.glade_xml = gtk.glade.XML(glade_xml_path)
        self.parent = parent
        self.widgets = GenericEditorView._widgets(self.glade_xml)
    
    def set_widget_value(self, widget_name, value, markup=True, default=None):
        utils.set_widget_value(self.glade_xml, widget_name, value, markup, 
                               default)
        
class AccessionEditorView(GenericEditorView):
    
    # these have to correspond to the response values in the glade file
    RESPONSE_OK_AND_ADD = 11
    RESPONSE_NEXT = 22
    source_expanded_pref = 'editor.accesssion.source.expanded'

    def __init__(self, parent=None):
        GenericEditorView.__init__(self, os.path.join(paths.lib_dir(), 
                                                      'plugins', 'garden', 
                                                      'editors.glade'),
                                   parent=parent)
        self.dialog = self.widgets.acc_editor_dialog

        # configure species_entry
        completion = gtk.EntryCompletion()    
        completion.set_match_func(self.species_completion_match_func)        
#        r = gtk.CellRendererText() # set up the completion renderer
#        completion.pack_start(r)
#        completion.set_cell_data_func(r, self.name_cell_data_func)        
        completion.set_text_column(0)    
        completion.set_minimum_key_length(2)
        completion.set_inline_completion(True)
        completion.set_popup_completion(True)                 
        self.widgets.species_entry.set_completion(completion)
        self.restore_state()
        # TODO: set up automatic signal handling, all signals should be called
        # on the presenter
    
    
    def save_state(self):
        prefs[self.source_expanded_pref] = \
            self.widgets.source_expander.get_expanded()
        
        
    def restore_state(self):
        expanded = prefs.get(self.source_expanded_pref, True)
        self.widgets.source_expander.set_expanded(expanded)

            
    def start(self):
        return self.widgets.acc_editor_dialog.run()    
        
        
    def species_completion_match_func(self, completion, key_string, iter, data=None):        
        '''
        the only thing this does different is it make the match case insensitve
        '''
        value = completion.get_model()[iter][0]
        return str(value).lower().startswith(key_string.lower())         
    
        
#    def name_cell_data_func(self, column, renderer, model, iter, data=None):
#        '''
#        render the values in the completion popup model
#        '''
#        #species = model.get_value(iter, 0)        
#        value = model[iter][0]
#        renderer.set_property('text', str(value))
        

class GenericEditorPresenter:
    '''
    this class cannont be instantiated
    expects a self.model and self.view
    '''
    def __init__(self, model, view):
        '''
        model should be an instance of SQLObjectProxy
        view should be an instance of GenericEditorView
        '''
        widget_model_map = {}
        self.model = model
        self.view = view

    
    def bind_widget_to_model(self, widget_name, model_field):
        # TODO: this is just an idea stub, should we have a method like
        # this so to put the model values in the view we just
        # need a for loop over the keys of the widget_model_map
        pass
    
    
    def assign_simple_handler(self, widget_name, model_field):
        '''
        assign handlers to widgets to change fields in the model
        '''
        # TODO: this should validate the data, i.e. convert strings to
        # int, or does commit do that?
        widget = self.view.widgets[widget_name]
        if isinstance(widget, gtk.Entry):            
            def insert(entry, new_text, new_text_length, position):
                entry_text = entry.get_text()                
                pos = entry.get_position()
                full_text = entry_text[:pos] + new_text + entry_text[pos:]    
                self.model[model_field] = full_text
            widget.connect('insert-text', insert)
        elif isinstance(widget, gtk.TextView):
            def insert(buffer, iter, text, length, data=None):            
                text = buffer.get_text(buffer.get_start_iter(), 
                                       buffer.get_end_iter())
                self.model[model_field] = text
            widget.get_buffer().connect('insert-text', insert)
        else:
            raise ValueError('widget type not supported: %s' % type(widget))
    
    def start(self):
        raise NotImplentedError
    
# TODO: *******
# this is how this needs to go down:
# 1. we need to attach a listener on the widget, these listeners should be 
# methods of the presenter and should set the values in the model
# 2. the presenter should set the widget values from the view
# 3. if the model row is a ForeignKey then the value should be resolved
# and the foreign key should be set in the model while the resolved string 
# representation of the object should be put in the widget, this means that
# if the widgets are refreshed from the model we should again resolve the
# foreign key values from the foreign key id stored in the model
# 4. in general the model should be getting values from the 
class AccessionEditorPresenter(GenericEditorPresenter):
    
    def __init__(self, model, view, defaults={}):
        '''
        model: should be an instance of class Accession
        view: should be an instance of AccessionEditorView
        '''
        GenericEditorPresenter.__init__(self, model, view)
        self.defaults = defaults
        
        # add listeners to the view
        self.view.widgets.species_entry.connect('insert-text', 
                                             self.on_insert_text, 'speciesID')
        self.assign_simple_handler('acc_id_entry', 'acc_id')
        self.assign_simple_handler('notes_textview', 'notes')
        
        # TODO: should we set these to the default value or leave them
        # be and let the default be set when the row is created, i'm leaning
        # toward the second, its easier if it works this way
        
        self.init_prov_combo()
        self.init_wild_prov_combo()
        self.init_source_expander()
        
        self.view.dialog.connect('response', self.on_dialog_response)
        self.view.dialog.connect('close', self.on_dialog_close_or_delete)
        self.view.dialog.connect('delete-event', self.on_dialog_close_or_delete)    
        
        self.refresh_view() # put model values in view
    
    
    def on_source_expander_activate(self, expander):
        if not expander.get_expanded():
            # then add content before it gets expanded
            pass

    
    def init_source_expander(self):        
        # get collection or donation box depending on source_type
        if self.model.isinstance:
            debug(self.model.source_type)
        else:
            pass

        combo = self.view.widgets.source_type_combo
        model = gtk.ListStore(str)        
        model.append(['Collection'])
        model.append(['Donation'])
        combo.set_model(model)
        combo.set_active(0)
#        combo.append_text('Donation')
#        combo.append_text('Collection')

        box = self.view.widgets.collection_box
        old_window = self.view.widgets.collection_window
        box.get_parent().remove(box)
#        if box.get_parent() == old_window:
#            debug('removing box from window')
#            old_window.remove(box) # this could be removed already
        #source_box = self.view.widgets.source_box
        source_box = self.view.widgets.source_box
        source_box.pack_start(box)
        self.view.widgets.source_expander.connect('activate', 
                                           self.on_source_expander_activate)
        #box.set_visible(True)
        box.show_all()
        source_box.show_all()
        self.view.dialog.show_all()
        
    
    def init_prov_combo(self):
        combo = self.view.widgets.prov_combo
        model = gtk.ListStore(str)
        for enum in self.model.columns['prov_type'].enumValues:
            model.append([enum])
        combo.set_model(model)
        def changed(*args):
            self.model.prov_type = combo.get_active_text()
        combo.connect('changed', changed)
    
    
    def init_wild_prov_combo(self):
        combo = self.view.widgets.wild_prov_combo
        model = gtk.ListStore(str)
        for enum in self.model.columns['wild_prov_status'].enumValues:
            model.append([enum])
        combo.set_model(model)
        def changed(*args):
            self.model.prov_type = combo.get_active_text()
        combo.connect('changed', changed)


    def on_dialog_response(self, dialog, response, *args):
        # system-defined GtkDialog responses are always negative, in which
        # case we want to hide it
        if response < 0:
            dialog.hide()
            #self.dialog.emit_stop_by_name('response')
        #return response
    
    
    def on_dialog_close_or_delete(self, dialog, event=None):
        dialog.hide()
        return True


    widget_to_field_map = {'acc_id_entry': 'acc_id',
                           'prov_combo': 'prov_type',
                           'wild_prov_combo': 'wild_prov_status',
                           'species_entry': 'species',
                           'source_type_combo': 'source_type',}
#                           'collector_entry': 'collector',
#                           'colldate_entry': 'coll_date',
#                           'collid_entry': 'coll_id',
#                           'locale_entry': 'locale',
#                           'lat_entry': 'latitude',
#                           'lon_entry': 'longitude',
#                           'geoacc_entry': 'geo_accy',
#                           'alt_entry': 'elevation',
#                           'altacc_entry': 'elevation_accy',
#                           'habitat_entry': 'habitat',
#                           'notes_entry': 'notes'}

    widget_to_source_feild_map = {'collector_entry': 'collector',
                                  'colldate_entry': 'coll_date',
                                  'collid_entry': 'coll_id',
                                  'locale_entry': 'locale',
                                  'lat_entry': 'latitude',
                                  'lon_entry': 'longitude',
                                  'geoacc_entry': 'geo_accy',
                                  'alt_entry': 'elevation',
                                  'altacc_entry': 'elevation_accy',
                                  'habitat_entry': 'habitat',
                                  'notes_entry': 'notes'}

    def refresh_view(self):
        '''
        get the values from the model and put them in the view
        '''
        for widget, field in self.widget_to_field_map.iteritems():
            self.view.set_widget_value(widget, self.model[field],
                                       self.defaults.get(field, None))         
    
        
    def _set_species_completions(self, text, model_field):
        parts = text.split(" ")
        genus = parts[0]
        sr = tables["Genus"].select("genus LIKE '"+genus+"%'")
        
#        model = gtk.ListStore(object)
#        # TODO: this is _really_ slow, it may take a second or two to append
#        # 100 entries
#        for row in sr:
#            for species in row.species:
#                model.append([species])
        model = gtk.ListStore(str, int)
#        # TODO: this is _really_ slow, it may take a second or two to append
#        # 100 entries
        for row in sr:
            for species in row.species:
                model.append([str(species), species.id])
                        
        completion = self.view.widgets.species_entry.get_completion()
        completion.set_model(model)
        completion.connect('match-selected', self.on_species_match_selected, 
                           model_field)

        
    def on_species_match_selected(self, completion, compl_model, iter, 
                               model_field):
        '''
        put the selected value in the model
        '''                
        # TODO: i would rather just put the object in the column and get
        # the id from that but there is that funny bug when using custom 
        # renderers for a gtk.EntryCompletion
        
        # column 0 holds the name of the plant while column 1 holds the id         
        name = compl_model[iter][0]
        entry = self.view.widgets.species_entry
        entry.set_text(str(name))
        entry.set_position(-1)
        
        # for foreign keys put the id in the model
        # TODO: since this in from a completion will it always be from a 
        # foreign key. what about EnumCols, will they use a combobox
#        if model_field[-2:] == "ID":
#            self.model[model_field] = value.id
#        else:
#            debug('model[%s] = value' % model_field)
#            self.model[model_field] = value
        self.model[model_field] = compl_model[iter][1]
        debug(self.model)


    def on_insert_text(self, entry, new_text, new_text_length, position, 
                       model_field):
        # TODO: this is flawed since we can't get the index into the entry
        # where the text is being inserted so if the user inserts text into 
        # the middle of the string then this could break
        entry_text = entry.get_text()                
        cursor = entry.get_position()
        full_text = entry_text[:cursor] + new_text + entry_text[cursor:]
        # this funny logic is so that completions are reset if the user
        # paste multiple characters in the entry
        if len(new_text) == 1 and len(full_text) == 2:
            self._set_species_completions(full_text, model_field)
        elif new_text_length > 2:# and entry_text != '':
            self._set_species_completions(full_text[:2], model_field)
        
            
    def start(self):
        return self.view.start()
        
class SourceBoxPresenter:
    pass

class AccessionEditor(TableEditor):
    
    label = 'Accessions'
        
    # TODO: the kwargs is really only here to support the old editor 
    # constructor
    def __init__(self, model=Accession, defaults={}, **kwargs):
        '''
        model: either an Accession class or instance
        defaults: a dictionary of Accession field name keys with default
        values to enter in the model if none are give
        '''
        TableEditor.__init__(self, table=Accession, select=None, 
                             defaults=defaults)
        # assert that the model is some form of an Accession
        debug(repr(model))
        debug(defaults)
        if not isinstance(model, Accession):
            assert(issubclass(model, Accession)) 
            
        # can't have both defaults and a model instance
        assert(not isinstance(model, Accession) or len(defaults.keys()) == 0)
        self.model = SQLObjectProxy(model)
        self.view = AccessionEditorView()
        self.presenter = AccessionEditorPresenter(self.model, self.view,
                                                  defaults)
                                
    def start(self):    
        not_ok_msg = 'Are you sure you want to lose your changes?'
        exc_msg = "Could not commit changes.\n"
        committed = None
        while True:
            response = self.presenter.start()
            self.view.save_state() # should view or presenter save state
            if response == gtk.RESPONSE_OK or \
                    response == self.presenter.view.RESPONSE_NEXT or \
                    response == self.presenter.view.RESPONSE_OK_AND_ADD:
                try:
                    committed = self.commit_changes()                
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
            elif self.model.dirty and utils.yes_no_dialog(not_ok_msg):
                sqlhub.processConnection.rollback()
                sqlhub.processConnection.begin()
                self.model.dirty = False
                break
            elif not self.model.dirty:
                break
        return committed      
    
#        debug(self.model)        
#        if len(self.model.keys()) > 0:        
#            return self._commit(self.model)
#        else:
#            return None
        
    def commit_changes(self):
        self._commit(**self.model)
        

	    
#class old_AccessionEditor(TreeViewEditorDialog):
#
#    visible_columns_pref = "editor.accession.columns"
#    column_width_pref = "editor.accession.column_width"
#    default_visible_list = ['acc_id', 'species']
#
#    label = 'Accessions'
#
#    def __init__(self, parent=None, select=None, defaults={}):
#        
#        TreeViewEditorDialog.__init__(self, Accession, "Accession Editor", 
#                                      parent, select=select, defaults=defaults)
#        titles = {"acc_id": "Acc ID",
#                   "speciesID": "Name",
#                   "prov_type": "Provenance Type",
#                   "wild_prov_status": "Wild Provenance Status",
#                   'source_type': 'Source',
#                   'notes': 'Notes'
##                   "ver_level": "Verification Level",           
##                   "ver_name": "Verifier's Name",
##                   "ver_date": "Verification Date",
##                   "ver_lit": "Verification Literature",
#                   }
#
#        self.columns.titles = titles
#        self.columns['source_type'].meta.editor = editors["SourceEditor"]
#        self.columns['source_type'].meta.getter = get_source
#        
#        self.columns['speciesID'].meta.get_completions = \
#            self.get_species_completions
#        
#        # set the accession column of the table that will be in the 
#        # source_type columns returned from self.get_values_from view
#        # TODO: this is a little hoaky and could use some work, might be able
#        # to do this automatically if the value in the column is a table
#        # the the expected type is a single join
#        # could do these similar to the way we handle joins in 
#        # create_view_columns
#        #self.table_meta.foreign_keys = [('_collection', 'accession'),
#        #                                ('_donation', 'accession')]
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
#            for species in row.species:                
#                model.append((str(species), species))
#        return model
#    
#        
#    def _model_row_to_values(self, row):
#	'''
#	_model_row_to_values
#	row: iter from self.model
#	return None if you don't want to commit anything
#	'''    
#	values = super(AccessionEditor, self)._model_row_to_values(row)
#	if values is None:
#	    return None
#        if 'source_type' in values and values['source_type'] is not None:
#            source_class = values['source_type'].__class__.__name__
#            attribute_name = '_' + source_class.lower()
#            self.columns.joins.append(attribute_name)                
#            values[attribute_name] = values.pop('source_type')
#            values['source_type'] = source_class
#        return values
#    

#
# TODO: fix this so it asks if you want to adds plant when you're done
#
#
#    def commit_changes_old(self, commit_transaction=True):
#        committed_rows = TreeViewEditorDialog.commit_changes(self, 
#                                                            commit_transaction)
#        if not committed_rows:
#            return committed_rows
#                            
#        # TODO: here should we iterate over the response from 
#        # TreeViewEditorDialog.commit_changes or is the 'values' sufficient
#        for row in committed_rows:
#            pass
#            #debug(row)
#        return committed_rows
#    
#        #
#        # it would be nice to have this done later
#        #
#        for v in self.values:
#            acc_id = v["acc_id"]
#            sel = tables["Accession"].selectBy(acc_id=acc_id)
#            if sel.count() > 1:
#                raise Exception("AccessionEditor.commit_changes():  "\
#                                "more than one accession exists with id: " +
#                                acc_id)
#            msg  = "No Plants/Clones exist for this accession %s. Would you "\
#                   "like to add them now?"
#            if not utils.yes_no_dialog(msg % acc_id):
#                continue
#            e = editors['PlantEditor'](defaults={"accessionID":sel[0]},
#                                       connection=self._old_connection)
#            response = e.start()
#            #if response == gtk.RESPONSE_OK or response == gtk.RESPONSE_ACCEPT:
#            #    e.commit_changes()
#            #e.destroy()
#        return committed_rows
        
#
# infobox for searchview
#
try:
    import os
    import bauble.paths as paths
    from bauble.plugins.searchview.infobox import InfoBox, InfoExpander, \
        set_widget_value        
except ImportError:
    pass
else:
    class GeneralAccessionExpander(InfoExpander):
        """
        generic information about an accession like
        number of clones, provenance type, wild provenance type, speciess
        """
    
        def __init__(self, glade_xml):
            InfoExpander.__init__(self, "General", glade_xml)
            general_window = self.glade_xml.get_widget('general_window')
            w = self.glade_xml.get_widget('general_box')
            general_window.remove(w)
            self.vbox.pack_start(w)
        
        
        def update(self, row):
            set_widget_value(self.glade_xml, 'name_data', 
			     row.species.markup(True))
            set_widget_value(self.glade_xml, 'nplants_data', len(row.plants))
            set_widget_value(self.glade_xml, 'prov_data',row.prov_type, False)
            
            
    class NotesExpander(InfoExpander):
        """
        the accession's notes
        """
    
        def __init__(self, glade_xml):
            InfoExpander.__init__(self, "Notes", glade_xml)
            notes_window = self.glade_xml.get_widget('notes_window')
            w = self.glade_xml.get_widget('notes_box')
            notes_window.remove(w)
            self.vbox.pack_start(w)
        
        
        def update(self, row):
            set_widget_value(self.glade_xml, 'notes_data', row.notes)            
    
    
    class SourceExpander(InfoExpander):
        
        def __init__(self, glade_xml):
            InfoExpander.__init__(self, 'Source', glade_xml)
            self.curr_box = None
        
        
        def update_collections(self, collection):
            
            set_widget_value(self.glade_xml, 'loc_data', collection.locale)
            
            geo_accy = collection.geo_accy
            if geo_accy is None:
                geo_accy = ''
            else: geo_accy = '(+/-)' + geo_accy + 'm.'
            
            if collection.latitude is not None:
                set_widget_value(self.glade_xml, 'lat_data',
                                 '%.2f %s' %(collection.latitude, geo_accy))
            if collection.longitude is not None:
                set_widget_value(self.glade_xml, 'lon_data',
                                '%.2f %s' %(collection.longitude, geo_accy))                                
            
            v = collection.elevation
            if collection.elevation_accy is not None:
                v = '+/- ' + v + 'm.'
            set_widget_value(self.glade_xml, 'elev_data', v)
            
            set_widget_value(self.glade_xml, 'coll_data', collection.collector)
            set_widget_value(self.glade_xml, 'date_data', collection.coll_date)
            #set_widget_value(self.glade_xml,'date_data', collection.coll_date)
            set_widget_value(self.glade_xml, 'collid_data', collection.coll_id)
            set_widget_value(self.glade_xml,'habitat_data', collection.habitat)
            set_widget_value(self.glade_xml,'collnotes_data', collection.notes)
            
                
        def update_donations(self, donation):
            set_widget_value(self.glade_xml, 'donor_data', 
                             tables['Donor'].get(donation.donorID).name)
            set_widget_value(self.glade_xml, 'donid_data', donation.donor_acc)
            set_widget_value(self.glade_xml, 'donnotes_data', donation.notes)
        
        
        def update(self, value):        
            if self.curr_box is not None:
                self.vbox.remove(self.curr_box)
                    
            #assert value is not None
            if value is None:
                return
            
            if isinstance(value, tables["Collection"]):
                coll_window = self.glade_xml.get_widget('collections_window')
                w = self.glade_xml.get_widget('collections_box')
                coll_window.remove(w)
                self.curr_box = w
                self.update_collections(value)        
            elif isinstance(value, tables["Donation"]):
                don_window = self.glade_xml.get_widget('donations_window')
                w = self.glade_xml.get_widget('donations_box')
                don_window.remove(w)
                self.curr_box = w
                self.update_donations(value)            
            else:
                msg = "Unknown type for source: " + str(type(value))
                utils.message_dialog(msg, gtk.MESSAGE_ERROR)
            
            #if self.curr_box is not None:
            self.vbox.pack_start(self.curr_box)
            #self.set_expanded(False) # i think the infobox overrides this
            #self.set_sensitive(False)
            
    
    class AccessionInfoBox(InfoBox):
        """
        - general info
        - source
        """
        def __init__(self):
            InfoBox.__init__(self)
            path = os.path.join(paths.lib_dir(), "plugins", "garden")
            self.glade_xml = gtk.glade.XML(path + os.sep + "acc_infobox.glade")
            
            self.general = GeneralAccessionExpander(self.glade_xml)
            self.add_expander(self.general)
            
            self.source = SourceExpander(self.glade_xml)
            self.add_expander(self.source)
            
            self.notes = NotesExpander(self.glade_xml)
            self.add_expander(self.notes)
    
    
        def update(self, row):        
            self.general.update(row)
            
            if row.notes is None:
                self.notes.set_expanded(False)
                self.notes.set_sensitive(False)
            else:
                self.notes.set_expanded(True)
                self.notes.set_sensitive(True)
                self.notes.update(row)
            
            # TODO: should test if the source should be expanded from the prefs
            if row.source_type == None:
                self.source.set_expanded(False)
                self.source.set_sensitive(False)
            elif row.source_type == 'Collection':
                self.source.set_expanded(True)
                self.source.update(row._collection)
            elif row.source_type == 'Donation':
                self.source.set_expanded(True)
                self.source.update(row._donation)
