#
# accessions module
#

from sqlobject import * 
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
    plantname = ForeignKey('Plantnames', notNull=True)
    plants = MultipleJoin("Plants", joinColumn='accession_id')
    
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
    _collection = SingleJoin('Collections', joinColumn='accession_id', makeDefault=None)
    _donation = SingleJoin('Donations', joinColumn='accession_id', makeDefault=None)
    

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
        
        TreeViewEditorDialog.__init__(self, tables["Accession"], 
                                      "Accession Editor", parent, 
                                      select=select, defaults=defaults)
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
                if source_class == 'Collections':
                    v['_collection'] = v.pop('source_type')
                    v['source_type'] = source_class
                elif source_class == 'Donations':
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
            sel = tables["Accessions"].selectBy(acc_id=acc_id)
            accession = sel[0]
            if sel.count() > 1:
                raise Exception("AccessionEditor.commit_changes():  "\
                                "more than one accession exists with id: " + acc_id)
            
            if not utils.yes_no_dialog(msg % acc_id):
                continue
            e = editors['PlantsEditor'](defaults={"accession":sel[0]})
            e.start()
        return True