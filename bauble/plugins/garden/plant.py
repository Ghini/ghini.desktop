#
# Plants table definition
#

import gtk
from sqlobject import * 
from bauble.plugins import BaubleTable, tables, editors
from bauble.treevieweditor import TreeViewEditorDialog
import bauble.utils as utils
from bauble.utils.log import debug

# TODO: do a magic attribute on plant_id that checks if a plant id
# already exists with the accession number, this probably won't work though
# sense the acc_id may not be set when setting the plant_id

# TODO: should probably make acc_status required since whether a plant is 
# living or dead is pretty important

# TODO: need a way to search plants by the full accession number, 
# e.g. 2004.0011.02 would return a specific plant, probably need to be
# able to set a callback function like the children field of the view meta

def edit_callback(row):
    value = row[0]    
    # TODO: the select paramater can go away when we move FamilyEditor to the 
    # new style editors    
    e = PlantEditor(select=[value], model=value)
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


plant_context_menu = [('Edit', edit_callback),
                      ('--', None),
                      ('Remove', remove_callback)]


def plant_markup_func(plant):
    '''
    '''
    return '%s (%s)' % (str(plant), 
                        plant.accession.species.markup(authors=False))


class PlantHistory(BaubleTable):
    class sqlmeta(BaubleTable.sqlmeta):
        defaultOrder = 'date'
    date = DateCol(notNull=True)
    description = UnicodeCol()
    plant = ForeignKey('Plant', notNull=True, cascade=True)
    
    
class Plant(BaubleTable):

    class sqlmeta(BaubleTable.sqlmeta):
	       defaultOrder = 'plant_id'

    # add to end of accession id, e.g. 04-0002.05
    # these are only unique when combined with an accession_id, see the 
    # id_index index    
    #plant_id = IntCol(notNull=True) 
    # makes sense that it should be an int but we won't restrict it that way,
    # if the editor wants to ensure that it is int then it should attach
    # a formencode.Validator on it
    plant_id = UnicodeCol(notNull=True)


    # Plant: Whole plant
    # Seed/Spore: Seed or Spore
    # Vegetative Part: Vegetative Part
    # Tissue Culture: Tissue culture
    # Other: Other, probably see notes for more information
    # None: no information, unknown
    acc_type = EnumCol(enumValues=('Plant', 'Seed/Spore', 'Vegetative Part', 
                                   'Tissue Culture', 'Other', None),
                       default=None)
                          
    # Accession Status
    # Living accession: Current accession in living collection
    # Dead: Noncurrent accession due to Death
    # Transfered: Noncurrent accession due to Transfer
    # Stored in dormant state: Stored in dormant state
    # Other: Other, possible see notes for more information
    # None: no information, unknown)
    acc_status = EnumCol(enumValues=('Living accession', 'Dead', 'Transfered', 
                                     'Stored in dormant state', 'Other', None),
                         default=None)
    
    notes = UnicodeCol(default=None)

    # indices
    #
    id_index = DatabaseIndex('plant_id', 'accession', unique=True)
    
    # foreign key
    # 
    accession = ForeignKey('Accession', notNull=True, cascade=False)
    
    # TODO: change the "location" field to "site" and then add specific 
    # locations fields like geographic coordinates
    location = ForeignKey("Location", notNull=True, cascade=False)
    
    # joins
    #
    history = MultipleJoin('PlantHistory', joinColumn='plant_id')
    

    def __str__(self): 
        return "%s.%s" % (self.accession, self.plant_id)
    
    
    def markup(self):
        #return "%s.%s" % (self.accession, self.plant_id)
        # FIXME: this makes expanding accessions look ugly with too many
        # plant names around but makes expanding the location essential
        # or you don't know what plants you are looking at
        return "%s.%s (%s)" % (self.accession, self.plant_id, 
                               self.accession.species.markup())
    
#
# Plant editor
#
class PlantEditor(TreeViewEditorDialog):

    visible_columns_pref = "editor.plant.columns"
    column_width_pref = "editor.plant.column_width"
    default_visible_list = ['accession', 'plant_id'] 

    label = 'Plants\\Clones'

    def __init__(self, parent=None, select=None, defaults={}, **kwargs):
        TreeViewEditorDialog.__init__(self, Plant, "Plants/Clones Editor", 
                                      parent, select=select, defaults=defaults,
                                      **kwargs)
        # set headers
        titles = {'plant_id': 'Plant ID',
                   'accessionID': 'Accession ID',
                   'locationID': 'Location',
                   'acc_type': 'Accession Type',
                   'acc_status': 'Accession Status',
                   'notes': 'Notes'
                   }
        self.columns.titles = titles
        self.columns['accessionID'].meta.get_completions = \
            self.get_accession_completions
        self.columns['locationID'].meta.get_completions = \
            self.get_location_completions


    def start(self, commit_transaction=True):
        '''
        '''
        accessions = tables["Accession"].select()
        if accessions.count() < 1:
            msg = "You can't add plants/clones to the database without first " \
                  "adding accessions.\n" \
                  "Would you like to add accessions now?"
            if utils.yes_no_dialog(msg):
                acc_editor = editors["AccessionEditor"]()
                acc_editor.start() # use the same transaction but commit
                    
        accessions = tables["Accession"].select()
        if accessions.count() < 1:   # no accessions were added
            return
        
        locations = tables["Location"].select()
        # keep location committed b/c locations.select might return 1 since
        # the location is just in the cache
        loc_committed = [] 
        if locations.count() < 1:
            msg = "You are trying to add plants to the database but no " \
                  "locations exists.\n" \
                  "Would you like to add some locations now?"
            if utils.yes_no_dialog(msg):
                loc_editor = editors["LocationEditor"]()
                loc_editor.start() # use the same transaction but commit
        
        locations = tables["Location"].select()
        if locations.count() < 1:
            return
            
        return super(PlantEditor, self).start(commit_transaction)


    def get_accession_completions(self, text):
        model = gtk.ListStore(str, object)
        sr = tables["Accession"].select("acc_id LIKE '"+text+"%'")
        for row in sr:
            s = str(row) + " - " + str(row.species)
            model.append([s, row])
        return model
            
            
    def get_location_completions(self, text):
        model = gtk.ListStore(str, object)
        sr = tables["Location"].select("site LIKE '" + text + "%'")
        for row in sr:
            model.append([str(row), row])
        return model
        
        
#    # extending this so we can have different value that show for the completions
#    # than what is stored in the model on selection
#    def on_completion_match_selected(self, completion, model, iter, 
#                                     path, colname):
#        """
#        all foreign keys should use entry completion so you can't type in
#        values that don't already exists in the database, therefore, allthough
#        i don't like it the view.model.row is set here for foreign key columns
#        and in self.on_edited for other column types                
#        """
#        if colname == "accession":
#            name = model.get_value(iter, 1)
#            id = model.get_value(iter, 2)
#            model = self.view.get_model()
#            i = model.get_iter(path)
#            row = model.get_value(i, 0)
#            row[colname] = [id, name]
#        else:
#            name = model.get_value(iter, 0)
#            id = model.get_value(iter, 1)
#            model = self.view.get_model()
#            i = model.get_iter(path)
#            row = model.get_value(i, 0)
#            row[colname] = [id, name]

        
#    def get_completions(self, text, colname):
#        maxlen = -1
#        model = None        
#        if colname == "accession":
#            model = gtk.ListStore(str, str, int)
#            if len(text) > 2:
#                sr = tables["Accession"].select("acc_id LIKE '"+text+"%'")
#                for row in sr:
#                    s = str(row) + " - " + str(row.species)
#                    model.append([s, str(row), row.id])
#        elif colname == "location":
#            model = gtk.ListStore(str, int)
#            sr = tables["Location"].select()
#            for row in sr:
#                model.append([str(row), row.id])
#        return model, maxlen
        
        
try:
    import os
#    from xml.sax.saxutils import escape
    import bauble.paths as paths
    from bauble.plugins.searchview.infobox import InfoBox, InfoExpander

except ImportError:
    pass
else:
    
    class GeneralPlantExpander(InfoExpander):
        """
        general expander for the PlantInfoBox        
        """
        
        def __init__(self, glade_xml):
            InfoExpander.__init__(self, "General", glade_xml)
            general_window = self.glade_xml.get_widget('general_window')
            w = self.glade_xml.get_widget('general_box')
            general_window.remove(w)
            self.vbox.pack_start(w)
        
        
        def update(self, row):
            utils.set_widget_value(self.glade_xml, 'name_data', 
                 '%s\n%s' % (row.accession.species.markup(True), str(row)))
            
            utils.set_widget_value(self.glade_xml, 'location_data',row.location.site)
            utils.set_widget_value(self.glade_xml, 'status_data',
                             row.acc_status, False)
            utils.set_widget_value(self.glade_xml, 'type_data',
                             row.acc_type, False)
            
            
    class NotesExpander(InfoExpander):
        """
        the plants notes
        """
            
        def __init__(self, glade_xml):
            InfoExpander.__init__(self, "Notes", glade_xml)
            w = self.glade_xml.get_widget('notes_box')
            notes_window = self.glade_xml.get_widget('notes_window')
            notes_window.remove(w)
            self.vbox.pack_start(w)
        
        
        def update(self, row):
#            debug(row.notes)
            utils.set_widget_value(self.glade_xml, 'notes_data', row.notes)
        

    class PlantInfoBox(InfoBox):
        """
        an InfoBox for a Plants table row
        """
        def __init__(self):
            InfoBox.__init__(self)
            #loc = LocationExpander()
            #loc.set_expanded(True)
            path = os.path.join(paths.lib_dir(), "plugins", "garden")
            self.glade_xml = gtk.glade.XML(path + os.sep + "plant_infobox.glade")            
            self.general = GeneralPlantExpander(self.glade_xml)
            self.add_expander(self.general)                    
            
            self.notes = NotesExpander(self.glade_xml)
            self.add_expander(self.notes)
            
        
        def update(self, row):
            # TODO: don't really need a location expander, could just
            # use a label in the general section
            #loc = self.get_expander("Location")
            #loc.update(row.location)
            self.general.update(row)
            
            if row.notes is None:
                self.notes.set_expanded(False)
                self.notes.set_sensitive(False)
            else:
                self.notes.set_expanded(True)
                self.notes.set_sensitive(True)
                self.notes.update(row)
