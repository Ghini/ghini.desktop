#
# plants.py
#

import gtk

import editors
from tables import tables
import bauble
#from prefs import Preferences

class PlantsEditor(editors.TreeViewEditorDialog):

    visible_columns_pref = "editor.plants.columns"
    column_width_pref = "editor.plants.column_width"

    def __init__(self, parent=None, select=None, defaults={}):

        self.sqlobj = tables.Plants

        self.column_meta = editors.createColumnMetaFromTable(self.sqlobj)

        # set headers
        headers = {'plant_id': 'Plant ID',
                   'accession': 'Accession ID',
                   'location': 'Location',
                   'acc_type': 'Accession Type',
                   'acc_status': 'Accession Status'}
        self.column_meta.set_headers(headers)
        
        # validators
        self.column_meta["plant_id"].validate = editors.validate_int

        # set default visible
        default_visible_list = ['accession', 'plant_id'] 
        
        # set visible from stored prefs
        if not bauble.prefs.has_key(self.visible_columns_pref):
            bauble.prefs[self.visible_columns_pref] = default_visible_list
        self.set_visible_columns_from_prefs(self.visible_columns_pref)

        editors.TreeViewEditorDialog.__init__(self, "Plants/Clones Editor",
                                              select=select, defaults=defaults)

    # extending this so we can have different value that show for the completions
    # than what is stored in the model on selection
    def on_completion_match_selected(self, completion, model, iter, 
                                     path, colname):
        """
        all foreign keys should use entry completion so you can't type in
        values that don't already exists in the database, therefore, allthough
        i don't like it the view.model.row is set here for foreign key columns
        and in self.on_edited for other column types                
        """
        if colname == "accession":
            name = model.get_value(iter, 1)
            id = model.get_value(iter, 2)
            model = self.view.get_model()
            i = model.get_iter(path)
            row = model.get_value(i, 0)
            row[colname] = [id, name]
        else:
            name = model.get_value(iter, 0)
            id = model.get_value(iter, 1)
            model = self.view.get_model()
            i = model.get_iter(path)
            row = model.get_value(i, 0)
            row[colname] = [id, name]

    def get_completions(self, text, colname):
        maxlen = -1
        model = None        
        if colname == "accession":
            model = gtk.ListStore(str, str, int)
            if len(text) > 2:
                sr = tables.Accessions.select("acc_id LIKE '"+text+"%'")
                for row in sr:
                    s = str(row) + " - " + str(row.plantname)
                    model.append([s, str(row), row.id])
        elif colname == "location":
            model = gtk.ListStore(str, int)
            sr = tables.Locations.select()
            for row in sr:
                model.append([str(row), row.id])
        return model, maxlen

        
