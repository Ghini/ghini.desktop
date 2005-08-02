#
# accessions.py
#

import gtk

import editors
from tables import tables
import utils
import bauble

#
# TODO: rather than having an accessions editor and a clones editor
# we should be able to just add clones to and accession in the same editor
# though it may take some custom code, maybe we could attach a children
# editor to any editor based on the clones name and just specify which editor
# would be the child and pop it up
#

# TODO: should have a source_id and a source_type or table that says
# that the id is an index into the some table then the source could
# be either a donor, a collection, etc...this could screw things
# up if the source_type was changed but the source_id wasn't then the 
# id would point to a row in the wrong table, could we restrict it
# somehow that if source_table is edited then source_id is reset, could
# do it through some sort of attribute access

#class AccessionsEditor(editors.TableEditorDialog):
    
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
    
    
class AccessionsEditor(editors.TreeViewEditorDialog):

    visible_columns_pref = "editor.accessions.columns"
    column_width_pref = "editor.accessions.column_width"
    default_visible_list = ['acc_id', 'plantname']

    label = 'Accessions'

    def __init__(self, parent=None, select=None, defaults={}):
        
        editors.TreeViewEditorDialog.__init__(self, tables.Accessions,
                                              "Accessions Editor", parent, 
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
        print editors.editors._by_name
        print editors.editors[tables.Plants]
        #print editors.editorForTable(tables.Plants)
        #print editors
        #print editorForTable(tables.Plants)
        
        
        self.column_meta['source_type'].editor = editors.source.SourceEditor
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
                sr = tables.Genera.select("genus LIKE '"+genus+"%'")
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
        values = editors.TreeViewEditorDialog.get_values_from_view(self)
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
        print 'entered Accessions.commit_changes()'        
        if not editors.TreeViewEditorDialog.commit_changes(self):
            return
            
        msg  = "No Plants/Clones exist for this accession %s. Would you like " \
        "to add them now?"
        
        values = self.get_values_from_view()
        print 'values: ' 
        print values
        for v in values:
            acc_id = v["acc_id"]
            sel = tables.Accessions.selectBy(acc_id=acc_id)
            accession = sel[0]
            if sel.count() > 1:
                raise Exception("AccessionEditor.commit_changes():  "\
                                "more than one accession exists with id: " + acc_id)
            
            if not utils.yes_no_dialog(msg % acc_id):
                continue
            #e = editors.editors.Plants(defaults={"accession":sel[0]})    
            print editors.editors._by_table
            #e = editors.editors['Plants'](defaults={"accession":sel[0]})
            e = editors.editors['Plants'](defaults={"accession":sel[0]})
            e.start()
            #e.show_all()
        return True
    