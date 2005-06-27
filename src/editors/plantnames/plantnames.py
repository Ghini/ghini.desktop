#
# plantnames.py
#

import gtk

import editors
from tables import tables

class PlantnamesEditor(editors.TableEditorDialog):
    
    visible_columns_pref = "editor.plantnames.columns"

    
    def __init__(self, parent=None, select=None, defaults={}):

        self.sqlobj = tables.Plantnames

        self.column_data = editors.createColumnMetaFromTable(self.sqlobj)

        # set headers
        headers = {"genus": "Genus",
                   "sp": "Species",
                   "sp_hybrid": "Sp. hybrid",
                   "sp_qual": "Sp. qualifier",
                   "sp_author": "Sp. author",
                   "cv_group": "Cv. group",
                   "cv": "Cultivar",
                   "trades": "Trade name",
                   "supfam": 'Super family',
                   'subgen': 'Subgenus',
                   'subgen_rank': 'Subgeneric rank',
                   'isp': 'Intraspecific\nepithet',
                   'isp_rank': 'Isp. rank',
                   'isp_author': 'Isp. author',
                   'isp2': 'Isp. 2',
                   'isp2_rank': 'Isp. 2 rank',
                   'isp2_author': 'Isp. 2 author',
                   'isp3': 'Isp. 3',
                   'isp3_rank': 'Isp. 3 rank',
                   'isp3_author': 'Isp. 3 author',
                   'isp4': 'Isp. 4',
                   'isp4_rank': 'Isp. 4 rank',
                   'isp4_author': 'Isp. 4 author',
                   'iucn23': 'IUCN 2.3\nCategory',
                   'iucn31': 'IUCN 3.1\nCategory',
                   'id_qual': 'ID qualifier',
                   'vernac_name': 'Common Name',
                   'poison_humans': 'Poisonious\nto humans',
                   'poison_animals': 'Poisonious\nto animals',
                   'food_plant': 'Food plant'
                   }
        self.column_data.set_headers(headers)
        #self.column_data["genus"].header = "Genus"

        # set default visible
        self.column_data["genus"].visible = True

        # set visible from stored prefs
        self.set_visible_columns_from_prefs(self.visible_columns_pref)
                        
        editors.TableEditorDialog.__init__(self, "Plantnames Editor",
                                           select=select, defaults=defaults)

        
    def foreign_does_not_exist(self, name, value):
        self.add_genus(value)    


    def add_genus(self, name):
        msg = "The Genus %s does not exist. Would you like to add it?" % name
        if utils.yes_no_dialog(msg):
            print "add genus"

    def get_completions(self, text, colname):
        maxlen = -1
        model = None
        if colname == "genus":
            model = gtk.ListStore(str, int)
            if len(text) > 2:
                sr = tables.Genera.select("genus LIKE '"+text+"%'")
                for row in sr: model.append([str(row), row.id])
        return model, maxlen
