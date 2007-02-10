#
# Genera table module
#

import os, traceback
import xml
import gtk
from sqlalchemy import *
from sqlalchemy.orm.session import object_session
from sqlalchemy.exceptions import SQLError
import bauble
from bauble.editor import *
import bauble.utils as utils
import bauble.utils.sql as sql_utils
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
    e = GenusEditor(model=value)
    return e.start() != None


def add_species_callback(row):
    from bauble.plugins.plants.species_editor import SpeciesEditor
    value = row[0]
    e = SpeciesEditor(Species(genus=value))
    return e.start() != None


def remove_callback(row):
    # TODO: before removing we should get the object, find all the dependent 
    # objects for the class and then find all the child objects that refer
    # to the object to be removed and at least say something like, 
    # '522 species refer to this object, do you still want to remove it'
    value = row[0]    
    s = '%s: %s' % (value.__class__.__name__, str(value))
    msg = "Are you sure you want to remove %s?" % utils.xml_safe(s)
    if not utils.yes_no_dialog(msg):
        return    
    try:
        session = create_session()
        obj = session.load(value.__class__, value.id)
        session.delete(obj)
        session.flush()
    except Exception, e:
        msg = 'Could not delete.\n\n%s' % utils.xml_safe(e)        
        utils.message_details_dialog(msg, traceback.format_exc(), 
                                     type=gtk.MESSAGE_ERROR)
    return True


genus_context_menu = [('Edit', edit_callback),
                      ('--', None),
                      ('Add species', add_species_callback),
                      ('--', None),
                      ('Remove', remove_callback)]


def genus_markup_func(genus):
    '''
    '''
    return str(genus), str(genus.family)

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
                    # it is possible that there can be genera with the same name 
                    # but different authors and probably means that at different 
                    # points in literature this name was used but is now a 
                    # synonym even though it may not be a synonym for the same 
                    # species, this screws us up b/c you can now enter duplicate 
                    # genera, somehow
                    # NOTE: we should at least warn the user that a duplicate is 
                    # being entered
                    Column('genus', String(64), nullable=False, index=True),                
                    Column('hybrid', Enum(values=['H', 'x', '+', None], 
                                          empty_to_none=True)),
                    Column('author', Unicode(255)),
                    Column('qualifier', Enum(values=['s. lat.', 's. str', None],
                                             empty_to_none=True)),
                    Column('notes', Unicode),
                    Column('family_id', Integer, ForeignKey('family.id'), 
                           nullable=False),
                    Column('_created', DateTime, default=func.current_timestamp()),
                    Column('_last_updated', DateTime, default=func.current_timestamp(), 
                           onupdate=func.current_timestamp()),
                    UniqueConstraint('genus', 'hybrid', 'author', 'family_id', name='genus_index'))
    
class Genus(bauble.BaubleMapper):
        
    def __str__(self):
        return Genus.str(self)

    
    @staticmethod
    def str(genus, author=False):
        if genus.genus is None:
            return repr(genus)
        elif not author:
            return ' '.join([s for s in [genus.hybrid, genus.genus, genus.qualifier] if s is not None])
        else:
            return ' '.join([s for s in [genus.hybrid, genus.genus, 
                                         genus.qualifier, 
                                         xml.sax.saxutils.escape(genus.author)] if s is not None])

                
genus_synonym_table = Table('genus_synonym',
                            Column('id', Integer, primary_key=True),
                            Column('genus_id', Integer, ForeignKey('genus.id'), 
                                   nullable=False),
                            Column('synonym_id', Integer, ForeignKey('genus.id'), 
                                   nullable=False),
                            Column('_created', DateTime, default=func.current_timestamp()),
                            Column('_last_updated', DateTime, default=func.current_timestamp(), 
                                   onupdate=func.current_timestamp()),
                            UniqueConstraint('genus_id', 'synonym_id', name='genus_synonym_index'))


class GenusSynonym(bauble.BaubleMapper):
        
    def __str__(self):        
        return str(self.synonym)
        #return '(%s)' % self.synonym


from bauble.plugins.plants.family import Family
from bauble.plugins.plants.species_model import Species, species_table
from bauble.plugins.plants.species_editor import SpeciesEditor


genus_mapper = mapper(Genus, genus_table,       
       properties = {'species': relation(Species, 
                                         primaryjoin=genus_table.c.id==species_table.c.genus_id,
                                         cascade='all, delete-orphan',
                                         order_by=['sp', 'infrasp_rank', 'infrasp'],
                                         backref='genus'),
                     'synonyms': relation(GenusSynonym,
                                          primaryjoin=genus_table.c.id==genus_synonym_table.c.genus_id,
                                          cascade='all, delete-orphan',
                                          backref='genus')},
       order_by=['genus', 'author'])

mapper(GenusSynonym, genus_synonym_table,
       properties = {'synonym': relation(Genus, uselist=False,
                                         primaryjoin=genus_synonym_table.c.synonym_id==genus_table.c.id),
                     'genus': relation(Genus, uselist=False, 
                                        primaryjoin=genus_synonym_table.c.genus_id==genus_table.c.id)
                     })
            
    
class GenusEditorView(GenericEditorView):
    
    syn_expanded_pref = 'editor.genus.synonyms.expanded'
    expanders_pref_map = {'gen_syn_expander': 'editor.genus.synonyms.expanded', 
                          'gen_notes_expander': 'editor.genus.notes.expanded'}

    def __init__(self, parent=None):
        GenericEditorView.__init__(self, os.path.join(paths.lib_dir(), 
                                                      'plugins', 'plants', 
                                                      'editors.glade'),
                                   parent=parent)
        self.dialog = self.widgets.genus_dialog
        self.dialog.set_transient_for(parent)
        self.connect_dialog_close(self.dialog)
        self.attach_completion('gen_syn_entry')#, self.syn_cell_data_func)
        self.attach_completion('gen_family_entry')
        self.restore_state()


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
                        

    def _get_window(self):
        '''
        '''
        return self.widgets.family_dialog    
    window = property(_get_window)
    
    
    def set_accept_buttons_sensitive(self, sensitive):
        self.widgets.gen_ok_button.set_sensitive(sensitive)
        self.widgets.gen_ok_and_add_button.set_sensitive(sensitive)
        self.widgets.gen_next_button.set_sensitive(sensitive)
    
            
    def start(self):
        return self.dialog.run()    
        

class GenusEditorPresenter(GenericEditorPresenter):
    
    widget_to_field_map = {'gen_family_entry': 'family',
                           'gen_genus_entry': 'genus',
                           'gen_author_entry': 'author',
                           'gen_hybrid_combo': 'hybrid',
#                           'gen_qualifier_combo': 'qualifier'
                           'gen_notes_textview': 'notes'}

    
    def __init__(self, model, view):
        '''
        @model: should be an instance of class Genus
        @view: should be an instance of GenusEditorView
        '''
        GenericEditorPresenter.__init__(self, ModelDecorator(model), view)
        self.session = object_session(model)
        
        # initialize widgets
        self.init_enum_combo('gen_hybrid_combo', 'hybrid')
        self.synonyms_presenter = SynonymsPresenter(self.model, self.view, self.session)                
        self.refresh_view() # put model values in view
        
        # connect signals
        def fam_get_completions(text):            
            return self.session.query(Family).select(Family.c.family.like('%s%%' % text))
#        def set_in_model(self, field, value):
#            setattr(self.model, field, value.id)
#        self.assign_completions_handler('gen_family_entry', 'family_id', 
#                                        fam_get_completions, set_func=set_in_model)        
        def set_in_model(self, field, value):
            setattr(self.model, field, value)
        self.assign_completions_handler('gen_family_entry', 'family', 
                                        fam_get_completions, set_func=set_in_model)        
        self.assign_simple_handler('gen_genus_entry', 'genus')
        self.assign_simple_handler('gen_hybrid_combo', 'hybrid')
        self.assign_simple_handler('gen_author_entry', 'author')
        #self.assign_simple_handler('gen_qualifier_combo', 'qualifier')
        self.assign_simple_handler('gen_notes_textview', 'notes')
        
        # for each widget register a signal handler to be notified when the
        # value in the widget changes, that way we can do things like sensitize
        # the ok button
        for field in self.widget_to_field_map.values():
            self.model.add_notifier(field, self.on_field_changed)
    
    
    def on_field_changed(self, model, field):
        if self.model.family is not None:
            self.view.set_accept_buttons_sensitive(True)
        
        
    def dirty(self):
        return self.model.dirty or self.synonyms_presenter.dirty()
    
    
    def refresh_view(self):
        for widget, field in self.widget_to_field_map.iteritems():
            # TODO: it would be nice to have a generic way to accession the 
            # foreign table from the foreign key, UPDATE: what??? does this mean
#            if field.endswith('_id') and self.model.c[field].foreign_key is not None:                
#                value = self.model[]            
            if field == 'family_id':
                value = self.model.family
            else:
                value = self.model[field]
            self.view.set_widget_value(widget, value)        

    
    def start(self):
        # TODO: this should return true or false to determine whether we
        # need to commit our changes
#        
#        not_ok_msg = 'Are you sure you want to lose your changes?'
#        while True:        
#            response = self.view.start()
#            if response == gtk.RESPONSE_OK:
#                break
#            elif response == gtk.RESPONSE_CANCEL and self.model.dirty:
#                if utils.yes_no_dialog(not_ok_msg):
#                    continue
#                    
#                
#                
        return self.view.start()
    

#
# TODO: you shouldn't be able to set a family as a synonym of itself
#
class SynonymsPresenter(GenericEditorPresenter):
    
    PROBLEM_INVALID_SYNONYM = 1
    
    # TODO: if you add a species and then immediately remove then you get an
    # error, something about the synonym not being in the session
        
    def __init__(self, genus, view, session):
        '''
        @param model: Genus instance
        @param view: see GenericEditorPresenter
        @param session: 
        '''
        GenericEditorPresenter.__init__(self, ModelDecorator(genus), view)
        self.session = session
        self.init_treeview()
        
        # use completions_model as a dummy object for completions, we'll create
        # seperate SpeciesSynonym models on add
        completions_model = GenusSynonym()
        def gen_get_completions(text):           
            return self.session.query(Genus).select(genus_table.c.genus.like('%s%%' % text))
        def set_in_model(self, field, value):
            # don't set anything in the model, just set self.selected
            sensitive = True
            if value is None:
                sensitive = False
            self.view.widgets.gen_syn_add_button.set_sensitive(sensitive)
            self._added = value

        self.assign_completions_handler('gen_syn_entry', 'synonym',
                                        gen_get_completions, 
                                        set_func=set_in_model,
                                        model=completions_model)
#        self.selected = None
        self._added = None
        self.view.widgets.gen_syn_add_button.connect('clicked', 
                                                    self.on_add_button_clicked)
        self.view.widgets.gen_syn_remove_button.connect('clicked', 
                                                    self.on_remove_button_clicked)
        self.__dirty = False
        
        
    def dirty(self):
        return self.model.dirty or self.__dirty
    
    
    def init_treeview(self):        
        '''
        initialize the gtk.TreeView
        '''
        self.treeview = self.view.widgets.gen_syn_treeview        
        def _syn_data_func(column, cell, model, iter, data=None):
            v = model[iter][0]
            cell.set_property('text', str(v))
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
        for syn in self.model.synonyms:
            tree_model.append([syn])
        self.treeview.set_model(tree_model)        
        self.treeview.connect('cursor-changed', self.on_tree_cursor_changed)
    
    
    def on_tree_cursor_changed(self, tree, data=None):
        '''
        '''
        path, column = tree.get_cursor()
        self.view.widgets.gen_syn_remove_button.set_sensitive(True)

    
    def refresh_view(self):
        """
        doesn't do anything
        """
        return
        
        
    def on_add_button_clicked(self, button, data=None):
        '''
        adds the synonym from the synonym entry to the list of synonyms for 
            this species
        '''        
        syn = GenusSynonym()
        syn.synonym = self._added        
        #self.session.save(syn)
        self.model.synonyms.append(syn)
        tree_model = self.treeview.get_model()
        tree_model.append([syn])
        self._added = None
        entry = self.view.widgets.gen_syn_entry
        # sid generated from GenericEditorPresenter.assign_completion_handler
        entry.handler_block(self._insert_gen_syn_entry_sid) 
        entry.set_text('')
        entry.set_position(-1)        
        entry.handler_unblock(self._insert_gen_syn_entry_sid)
        self.view.widgets.gen_syn_add_button.set_sensitive(False)
        self.view.widgets.gen_syn_add_button.set_sensitive(False)
        #self.view.set_accept_buttons_sensitive(True)
        self.__dirty = True
        

    def on_remove_button_clicked(self, button, data=None):
        '''
        removes the currently selected synonym from the list of synonyms for
        this species
        '''
        # TODO: maybe we should only ask 'are you sure' if the selected value
        # is an instance, this means it will be deleted from the database        
        tree = self.view.widgets.gen_syn_treeview
        path, col = tree.get_cursor()
        tree_model = tree.get_model()
        value = tree_model[tree_model.get_iter(path)][0]      
#        debug('%s: %s' % (value, type(value)))
        s = Genus.str(value.synonym)
        msg = 'Are you sure you want to remove %s as a synonym to the ' \
              'current genus?\n\n<i>Note: This will not remove the genus '\
              '%s from the database.</i>' % (s, s)
        if utils.yes_no_dialog(msg, parent=self.view.window):            
            tree_model.remove(tree_model.get_iter(path))
            self.model.synonyms.remove(value)
#            delete_or_expunge(value)            
            #self.view.set_accept_buttons_sensitive(True)
            self.__dirty = True
            

class GenusEditor(GenericModelViewPresenterEditor):
    
    label = 'Genus'
    mnemonic_label = '_Genus'
    
    # these response values have to correspond to the response values in 
    # the view
    RESPONSE_OK_AND_ADD = 11
    RESPONSE_NEXT = 22
    ok_responses = (RESPONSE_OK_AND_ADD, RESPONSE_NEXT)    
        
        
    def __init__(self, model=None, parent=None):
        '''
        @param model: Genus instance or None
        @param parent: None
        '''         
        if model is None:
            model = Genus()
        GenericModelViewPresenterEditor.__init__(self, model, parent)
        
        if parent is None: # should we even allow a change in parent
            parent = bauble.gui.window
        self.parent = parent
        self._committed = []
        
    
    def handle_response(self, response):
        '''
        handle the response from self.presenter.start() in self.start()
        '''
        not_ok_msg = 'Are you sure you want to lose your changes?'
        if response == gtk.RESPONSE_OK or response in self.ok_responses:
            try:
                if self.presenter.dirty():
                    self.commit_changes()
                    self._committed.append(self.model)
            except SQLError, e:                
                msg = 'Error committing changes.\n\n%s' % utils.xml_safe(e.orig)
                utils.message_details_dialog(msg, str(e), gtk.MESSAGE_ERROR)
                return False
            except Exception, e:
                msg = 'Unknown error when committing changes. See the details '\
                      'for more information.\n\n%s' % utils.xml_safe(e)
                utils.message_details_dialog(msg, traceback.format_exc(), 
                                             gtk.MESSAGE_ERROR)
                return False
        elif self.presenter.dirty() and utils.yes_no_dialog(not_ok_msg) or not self.presenter.dirty():
            return True
        else:
            return False
                
        # respond to responses
        more_committed = None
        if response == self.RESPONSE_NEXT:
            model = Genus(family=self.model.family)
            e = GenusEditor(model=model, parent=self.parent)
            more_committed = e.start()
        elif response == self.RESPONSE_OK_AND_ADD:
            sp = Species(genus=self.model)
            e = SpeciesEditor(model=sp, parent=self.parent)
            more_committed = e.start()
             
        if more_committed is not None:
            if isinstance(more_committed, list):
                self._committed.extend(more_committed)
            else:
                self._committed.append(more_committed)                
        
        return True                

    
    def start(self):
        if self.session.query(Family).count() == 0:        
            msg = 'You must first add or import at least one Family into the '\
                  'database before you can add plants.'
            utils.message_dialog(msg)
            return
        self.view = GenusEditorView(parent=self.parent)
        self.presenter = GenusEditorPresenter(self.model, self.view)
        
        # add quick response keys
        dialog = self.view.dialog        
        self.attach_response(dialog, gtk.RESPONSE_OK, 'Return', gtk.gdk.CONTROL_MASK)
        self.attach_response(dialog, self.RESPONSE_OK_AND_ADD, 'k', gtk.gdk.CONTROL_MASK)
        self.attach_response(dialog, self.RESPONSE_NEXT, 'n', gtk.gdk.CONTROL_MASK)
    
        # set default focus
        if self.model.family is None:
            self.view.widgets.gen_family_entry.grab_focus()
        else:
            self.view.widgets.gen_genus_entry.grab_focus()
        
        exc_msg = "Could not commit changes.\n"
        while True:
            response = self.presenter.start()            
            self.view.save_state() # should view or presenter save state
            if self.handle_response(response):
                break                    
        self.session.close() # cleanup session
        return self._committed

    
        
#
# infobox
#
from bauble.view import InfoBox, InfoExpander
from sqlalchemy.orm.session import object_session
import bauble.paths as paths
from bauble.plugins.plants.species_model import Species, species_table
from bauble.plugins.garden.accession import Accession, accession_table
from bauble.plugins.garden.plant import Plant, plant_table

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
        self.set_widget_value('gen_name_data', Genus.str(row, author=True))

        # get the number of species
        species_ids = select([species_table.c.id], species_table.c.genus_id==row.id)
        nsp = sql_utils.count_select(species_ids)
        self.set_widget_value('gen_nsp_data', nsp)

        # get number of accessions
        acc_ids = select([accession_table.c.id], accession_table.c.species_id.in_(species_ids))        
        nacc_str = str(sql_utils.count_select(acc_ids))
        if nacc_str != '0':
            nsp_with_accessions = sql_utils.count_distinct_whereclause(accession_table.c.species_id, accession_table.c.species_id.in_(species_ids))
            nacc_str = '%s in %s species' % (nacc_str, nsp_with_accessions)
        self.set_widget_value('gen_nacc_data', nacc_str)

        # get number of plants
        plant_ids = select([plant_table.c.id], plant_table.c.accession_id.in_(acc_ids))
        nplants_str = str(sql_utils.count_select(plant_ids))
        if nplants_str != '0':
            nacc_with_plants = sql_utils.count_distinct_whereclause(plant_table.c.accession_id, plant_table.c.accession_id.in_(acc_ids))
            nplants_str = '%s in %s accessions' % (nplants_str, nacc_with_plants)            
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

__all__ = ['genus_table', 'Genus', 'genus_synonym_table', 'GenusSynonym', 
           'GenusEditor', 'GenusInfoBox', 'genus_context_menu', 
           'genus_markup_func']
