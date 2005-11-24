#
# accessions module
#

import os
import gtk
from sqlobject import * 
import bauble.paths as paths
import bauble.utils as utils
from bauble.plugins import BaubleTable, tables, editors
from bauble.plugins.editor import TreeViewEditorDialog
from bauble.utils.log import debug


class Accession(BaubleTable):

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
    species = ForeignKey('Species', notNull=True)
    plants = MultipleJoin("Plant", joinColumn='accession_id')
    
    # these should probably be hidden then we can do some trickery
    # in the accession editor to choose where a collection or donation
    # source, the source will contain one of collection or donation
    # tables
    # 
    # holds the string 'Collection' or 'Donation' which indicates where
    # we should get the source information from either of those columns
    source_type = StringCol(length=64, default=None)    
                            
    # the source type says whether we should be looking at the 
    # _collection or _donation joins for the source info
    #_collection = SingleJoin('Collection', joinColumn='accession_id', makeDefault=None)
    _collection = SingleJoin('Collection', joinColumn='accession_id')
    _donation = SingleJoin('Donation', joinColumn='accession_id', makeDefault=None)
        
    #notes = UnicodeCol()
    
    # these probably belong in separate tables with a single join
    #cultv_info = StringCol(default=None)      # cultivation information
    #prop_info = StringCol(default=None)       # propogation information
    #acc_uses = StringCol(default=None)        # accessions uses, why diff than taxon uses?

    # these are the unknowns
#    acc = DateTimeCol(default=None) # ?
#    acct = StringCol(length=50, default=None) #?
#    BGnot = StringCol(default=None) # ******** what is this?

    def __str__(self): 
        return self.acc_id


#
# Accession editor
#

def get_source(row):
#    debug('get_source: ' + str(row.source_type))
    if row.source_type == None:
        return None
    elif row.source_type == tables['Donation'].__name__:
        # the __name__ should be 'Donation'
        return row._donation
    elif row.source_type == tables['Collection'].__name__:
        return row._collection
    else:
        raise ValueError('unknown source type: ' + str(row.source_type))
    
    
class AccessionEditor(TreeViewEditorDialog):

    visible_columns_pref = "editor.accession.columns"
    column_width_pref = "editor.accession.column_width"
    default_visible_list = ['acc_id', 'species']

    label = 'Accessions'

    def __init__(self, parent=None, select=None, defaults={}, connection=None):
        
        TreeViewEditorDialog.__init__(self, Accession, "Accession Editor", 
                                      parent, select=select, defaults=defaults,
                                      connection=connection)
        titles = {"acc_id": "Acc ID",
                   "speciesID": "Name",
                   "prov_type": "Provenance Type",
                   "wild_prov_status": "Wild Provenance Status",
                   'source_type': 'Source'
#                   "ver_level": "Verification Level",           
#                   "ver_name": "Verifier's Name",
#                   "ver_date": "Verification Date",
#                   "ver_lit": "Verification Literature",
#                   'donor_type': 'Donor Type',
#                   'donor': 'Donor Name',
#                   'donor_acc': 'Donor\'s Accession'
                   #,
#                   "wgs": "World Geographical Scheme"
                   }

        self.columns.titles = titles
        self.columns['source_type'].meta.editor = editors["SourceEditor"]
        self.columns['source_type'].meta.getter = get_source
        
        self.columns['speciesID'].meta.get_completions = \
            self.get_species_completions
        
        # set the accession column of the table that will be in the 
        # source_type columns returned from self.get_values_from view
        # TODO: this is a little hoaky and could use some work, might be able
        # to do this automatically if the value in the column is a table
        # the the expected type is a single join
        # could do these similar to the way we handle joins in 
        # create_view_columns
        #self.table_meta.foreign_keys = [('_collection', 'accession'),
        #                                ('_donation', 'accession')]
        
        
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
        sr = tables["Genus"].select("genus LIKE '"+genus+"%'",
                                    connection=self.transaction)
        model = gtk.ListStore(str, object) 
        debug(sr.count())
        for row in sr:
            for species in row.species:                
                model.append((str(species), species))
        return model
    
        
    # TODO:  we should have to reproduce this entire method just for this 
    # editor, somehow we need a good way to get so that when we get the values
    # from the editor we know now to change source_type into an id, etc.s        
    def _set_values_from_widgets(self):
        super(AccessionEditor, self)._set_values_from_widgets()
        
        for v in self._values:
            if v.has_key('source_type'):
                source_class = v['source_type'].__class__.__name__
                attribute_name = '_' + source_class.lower()
                self.columns.joins.append(attribute_name)                
                v[attribute_name] = v.pop('source_type')
                v['source_type'] = source_class
    
    
    def commit_changes(self):
        committed_rows = TreeViewEditorDialog.commit_changes(self)
        if not committed_rows:
            return committed_rows
                            
        # TODO: here should we iterate over the response from 
        # TreeViewEditorDialog.commit_changes or is the 'values' sufficient
        for row in committed_rows:
            pass
            #debug(row)
        return committed_rows
        for v in self.values:
            acc_id = v["acc_id"]
            sel = tables["Accession"].selectBy(acc_id=acc_id)
            if sel.count() > 1:
                raise Exception("AccessionEditor.commit_changes():  "\
                                "more than one accession exists with id: " +
                                acc_id)
            msg  = "No Plants/Clones exist for this accession %s. Would you "\
                   "like to add them now?"
            if not utils.yes_no_dialog(msg % acc_id):
                continue
            e = editors['PlantEditor'](defaults={"accessionID":sel[0]},
                                       connection=self._old_connection)
            response = e.start()
            if response == gtk.RESPONSE_OK or response == gtk.RESPONSE_ACCEPT:
                e.commit_changes()
            e.destroy()
        return committed_rows
        
#
# infobox for searchview
#
try:
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
            w = self.glade_xml.get_widget('general_box')
            w.unparent()
            self.vbox.pack_start(w)
        
        
        def update(self, row):
            set_widget_value(self.glade_xml, 'name_data', row.species)
            set_widget_value(self.glade_xml, 'nplants_data', len(row.plants))
    
    
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
            set_widget_value(self.glade_xml, 'data_data', collection.coll_date)
            set_widget_value(self.glade_xml, 'collid_data', collection.coll_id)
            set_widget_value(self.glade_xml, 'habitat_data', collection.habitat)
            
            # NOTE: if the widget is named notes_data then it doesn't update,
            # should probably file a bug with glade
            # UPDATE: i think this may actually have been b/c i had two widgets
            # with different parent windows but both named notes_data in the 
            # glade xml
            set_widget_value(self.glade_xml, 'collnotes_data', collection.notes)
            
                
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
                w = self.glade_xml.get_widget('collections_box')
                w.unparent()
                self.curr_box = w
                self.update_collections(value)        
            elif isinstance(value, tables["Donation"]):
                w = self.glade_xml.get_widget('donations_box')
                w.unparent()
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
            #path = utils.get_main_dir() + os.sep + 'views' + os.sep + 'search' + os.sep
            #path = paths.main_dir() + os.sep + 'views' + os.sep + 'search' + os.sep
            #path = os.path.dirname(__file__) + os.sep
            #path = paths.lib_dir() + os.sep + 'acc_infobox.glade'            
            path = os.path.join(paths.lib_dir(), "plugins", "garden")
            self.glade_xml = gtk.glade.XML(path + os.sep + "acc_infobox.glade")
            
            self.general = GeneralAccessionExpander(self.glade_xml)
            self.add_expander(self.general)
            
            self.source = SourceExpander(self.glade_xml)
            self.add_expander(self.source)
    
    
        def update(self, row):        
            self.general.update(row)
                            
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
