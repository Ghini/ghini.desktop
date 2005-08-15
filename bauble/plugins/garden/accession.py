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


class Accession(BaubleTable):

    values = {} # dictionary of values to restrict to columns
    acc_id = StringCol(length=20, notNull=True, alternateID=True)
    
    prov_type = StringCol(length=1, default=None) # provenance type
    values["prov_type"] = [("W", "Wild"),
                           ("Z", "Propagule of wild plant in cultivation"),
                           ("G", "Not of wild source"),
                           ("U", "Insufficient data")]

    # wild provenance status, wild native, wild non-native, cultivated native
    wild_prov_status = StringCol(length=50, default=None)
    values["wild_prov_status"] = [("Wild native", "Endemic found within it indigineous range"),
                                  ("Wild non-native", "Propagule of wild plant in cultivation"),
                                  ("Cultivated native", "Not of wild source"),
                                  ("U", "Insufficient data")]
                                 
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
    plantname = ForeignKey('Plantname', notNull=True)
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
    # collection or _donation join
    _collection = SingleJoin('Collection', joinColumn='accession_id', makeDefault=None)
    _donation = SingleJoin('Donation', joinColumn='accession_id', makeDefault=None)
    

    # these probably belong in separate tables with a single join
    #cultv_info = StringCol(default=None)      # cultivation information
    #prop_info = StringCol(default=None)       # propogation information
    #acc_uses = StringCol(default=None)        # accessions uses, why diff than taxon uses?


    # these are the unknowns
#    acc = DateTimeCol(default=None) # ?
#    acct = StringCol(length=50, default=None) #?
#    BGnot = StringCol(default=None) # ******** what is this?

    def __str__(self): return self.acc_id


#
# Accession editor
#
    
def get_source(row):    
    if row._collection is not None and row._donation is not None:
        raise Exception('tables.Accessions.get_source(): only one of '\
                        'donation or _collection should be set but '\
                        'both seem to be set')
    if row._collection is not None:
        return row._collection
    elif row._donation is not None:
        return row._donation
    return None
    
    
class AccessionEditor(TreeViewEditorDialog):

    visible_columns_pref = "editor.accession.columns"
    column_width_pref = "editor.accession.column_width"
    default_visible_list = ['acc_id', 'plantname']

    label = 'Accessions'

    def __init__(self, parent=None, select=None, defaults={}):
        
        TreeViewEditorDialog.__init__(self, Accession, "Accession Editor", 
                                      parent, select=select, defaults=defaults)
        headers = {"acc_id": "Acc ID",
                   "plantname": "Name",
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
        self.column_meta.headers = headers
        self.column_meta['source_type'].editor = editors["SourceEditor"]
        self.column_meta['source_type'].getter = get_source
        
        # set the accession column of the table that will be in the 
        # source_type columns returned from self.get_values_from view
        # TODO: this is a little hoaky and could use some work, might be able
        # to do this automatically if the value in the column is a table
        # the the expected type is a single join
        self.table_meta.foreign_keys = [('_collection', 'accession'),
                                        ('_donation', 'accession')]
        
        
    def get_completions(self, text, colname):
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
        parts = text.split(" ")
        genus = parts[0]
        results = []
        model = None
        maxlen = 0
        if colname == "plantname": #and len(genus) > 2:            
            model = gtk.ListStore(str, int)
            if len(genus) > 2:
                sr = tables["Genus"].select("genus LIKE '"+genus+"%'")
                # this is a foreign key so store the the string and id
                model = gtk.ListStore(str, int) 
                for row in sr:
                    for p in row.plantnames:
                        s = str(p)
                        if len(s) > maxlen: maxlen = len(s)
                        model.append((s, p.id))
                        #model.append(row)
        return model, maxlen
    
        # split the text by spaces
        # if the last item is longer than say 3 then
        #    get completions 
    
    
    def get_values_from_view(self):
        values = TreeViewEditorDialog.get_values_from_view(self)
        for v in values:
            if v.has_key('source_type'):
                source_class = v['source_type'].__class__.__name__[:]
                if source_class == 'Collection':
                    v['_collection'] = v.pop('source_type')
                    v['source_type'] = source_class
                elif source_class == 'Donation':
                    v['_donation'] = v.pop('source_type')
                    v['source_type'] = source_class
                else:
                    raise ValueError('AccessionsEditor.get_values_from_view:'\
                                     'bad value for source type')
        return values
    
    
    def commit_changes(self):
        if not TreeViewEditorDialog.commit_changes(self):
            return
            
        msg  = "No Plants/Clones exist for this accession %s. Would you like " \
        "to add them now?"
        
        values = self.get_values_from_view()
        for v in values:
            acc_id = v["acc_id"]
            sel = tables["Accession"].selectBy(acc_id=acc_id)
            accession = sel[0]
            if sel.count() > 1:
                raise Exception("AccessionEditor.commit_changes():  "\
                                "more than one accession exists with id: " + acc_id)
            
            if not utils.yes_no_dialog(msg % acc_id):
                continue
            e = editors['PlantEditor'](defaults={"accession":sel[0]})
            e.start()
        return True
        
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
        number of clones, provenance type, wild provenance type, plantnames
        """
    
        def __init__(self, glade_xml):
            InfoExpander.__init__(self, "General", glade_xml)
            w = self.glade_xml.get_widget('general_box')
            w.unparent()
            self.vbox.pack_start(w)
        
        def update(self, row):
            set_widget_value(self.glade_xml, 'name_data', row.plantname)
            set_widget_value(self.glade_xml, 'nplants_data', len(row.plants))
            #w = self.glade_xml.get_widget('nplants_data')
            #pass
    
    
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
                set_widget_value(self.glade_xml, 'lat_data', collection.latitude + geo_accy)
            if collection.longitude is not None:
                set_widget_value(self.glade_xml, 'lon_data', collection.longitude + geo_accy)
            
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
            set_widget_value(self.glade_xml, 'donor_data', tables.Donors.get(donation.donorID).name)
            set_widget_value(self.glade_xml, 'donid_data', donation.donor_acc)
            set_widget_value(self.glade_xml, 'donnotes_data', donation.notes)
            pass
        
        
        def update(self, value):        
            if self.curr_box is not None:
                self.vbox.remove(self.curr_box)
                            
            if type(value) == tables.Collections:
                w = self.glade_xml.get_widget('collections_box')
                w.unparent()
                self.curr_box = w
                self.update_collections(value)
            elif type(value) == tables.Donations:
                w = self.glade_xml.get_widget('donations_box')
                w.unparent()
                self.curr_box = w
                self.update_donations(value)
            
            self.vbox.pack_start(self.curr_box)
            
    
    class AccessionInfoBox(InfoBox):
        """
        - general info
        - source
        """
        def __init__(self):
            InfoBox.__init__(self)
            #path = utils.get_main_dir() + os.sep + 'views' + os.sep + 'search' + os.sep
            #path = paths.main_dir() + os.sep + 'views' + os.sep + 'search' + os.sep
            path = os.path.dirname(__file__) + os.sep
            print path
            self.glade_xml = gtk.glade.XML(path + 'acc_infobox.glade')
            
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
            elif row.source_type == 'Collections':
                self.source.set_expanded(True)
                self.source.update(row._collection)
            elif row.source_type == 'Donations':
                self.source.set_expanded(True)
                self.source.update(row._donation)