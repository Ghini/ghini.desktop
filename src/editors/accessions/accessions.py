#
# accessions.py
#

import pygtk
pygtk.require("2.0")
import gtk

import editors
from tables import tables

#
# TODO: rather than having an accessions editor and a clones editor
# we should be able to just add clones to and accession in the same editor
# though it may take some custom code, maybe we could attach a children
# editor to any editor based on the clones name and just specify which editor
# would be the child and pop it up
#
class AccessionsEditor(editors.TableEditorDialog):

    visible_columns_pref = "editor.accessions.columns"

    def __init__(self, parent=None, select=None, defaults={}):

        self.sqlobj = tables.Accessions
        
        self.column_data = editors.createColumnMetaFromTable(self.sqlobj) #returns None?

        # set headers
        self.column_data["acc_id"].header = "Acc ID" 
        self.column_data["plantname"].header = "Name"
        self.column_data["prov_type"].header = "Provenance Type"
        self.column_data["wild_prov_status"].header = "Wild Provenance Status"
        self.column_data["ver_level"].header = "Verification Level"
        self.column_data["ver_name"].header = "Verifier's Name"
        self.column_data["ver_date"].header = "Verification Date"
        self.column_data["ver_lit"].header = "Verification Literature"
        

        # set default visible
        self.column_data["acc_id"].visible = True 
        self.column_data["plantname"].visible = True
    
        # set visible according to stored prefs
        self.set_visible_columns_from_prefs(self.visible_columns_pref)
            
        editors.TableEditorDialog.__init__(self, "Accessions Editor", select=select,
                                           defaults=defaults)
        

    def get_completions(self, text, colname):
        # get entry and determine from what has been input which
        # field is currently being edited and give completion
        # if this return None then the entry will never search for completions
        # TODO: finish this
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
                        #print s + ": " + str(p.id)
                        if len(s) > maxlen: maxlen = len(s)
                        model.append([s, p.id])
        return model, maxlen
    
        # split the text by spaces
        # if the last item is longer than say 3 then
        #    get completions 
    
    def commit_changes(self):
        editors.TableEditorDialog.commit_changes(self)
        msg  = "No Plants/Clones exist for this accession. Would you like \
        to add them now?"
        # TODO: if this accession didn't exist then ask the user if they want
        # to add clones
        #d = gtk.MessageDialog(None,
        #                      gtk.DIALOG_MODAL| gtk.DIALOG_DESTROY_WITH_PARENT,
        #                      gtk.MESSAGE_ERROR, gtk.BUTTONS_OK,
        #                      "%s does not exit in %s" % (value, name))
        #d.run()
        #d.destroy()