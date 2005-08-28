#
# Plants table definition
#

import gtk
from sqlobject import * 
from bauble.plugins import BaubleTable, tables
from bauble.plugins.editor import TreeViewEditorDialog


class Plant(BaubleTable):
    
    # add to end of accession id, e.g. 04-0002.05
    # these are only unique when combined with an accession_id
    values = {}
    plant_id = IntCol(notNull=True) 

    # accession type
    acc_type = StringCol(length=4, default=None)
    values['acc_type'] = [('P', 'Whole plant'),
                          ('S', 'Seed or Sport'),
                          ('V', 'Vegetative Part'),
                          ('T', 'Tissue culture'),
                          ('O', 'Other')]
                          
    # accession status
    acc_status = StringCol(length=6, default=None)
    values['acc_status'] = [('C', 'Current accession in living collection'),
                            ('D', 'Noncurrent accession due to Death'),
                            ('T', 'Noncurrent accession due to Transfer'),
                            ('S', 'Stored in dormant state'),
                            ('O', 'Other')]

    # foreign key and joins
    accession = ForeignKey('Accession', notNull=True, cascade=True)
    location = ForeignKey("Location", notNull=True)
    #location = MultipleJoin("Locations", joinColumn="locations_id")
    #mta_out = MultipleJoin("MaterialTransfers", joinColumn="genus_id")
    
    # these should only be at the accession level
#    ver_level = StringCol(length=2, default=None) # verification level
#    ver_name = StringCol(length=50, default=None) # verifier's name
#    ver_date = DateTimeCol(default=None) # verification data
#    ver_hist = StringCol(default=None)  # verification history
#    ver_lit = StringCol(default=None) # verification list

    # perrination flag, 2 letter code
#    perr_flag = StringCol(length=2, default=None) 
#    breed_sys = StringCol(length=3, default=None) # breeding system    
    
#    ADatePlant = DateTimeCol(default=None)
#    ADateInspected = DateTimeCol(default=None)    
    
    # unknowns
#    plantQual = IntCol(default=None)    # ?
#    plantHeld = StringCol(length=50, default=None)    
    #dater = DateTimeCol(default=None)
    #datep = DateTimeCol(default=None)
    #datei = DateTimeCol(default=None)
    #Seedp = StringCol(length=50, default=None)
    #Seedv = StringCol(length=1, default=None) # bool ?
    #Seedl = BoolCol(default=None)
    #ExchgM = StringCol(length=10, default=None)
    #Specc = StringCol(length=1, default=None) # bool?
    #MDate = DateTimeCol(default=None)
    #MInfo = StringCol(default=None)
    #culinf = StringCol(default=None)
    #proinf = StringCol(default=None)
    #PlantsComments = StringCol(default=None)
    #LabelInfo = StringCol(default=None)
    #PlantLifeForm = StringCol(length=50, default=None)
    #InsCode = StringCol(length=6, default=None)
    #ITFRec = BoolCol(default=None)
    #Source1 = IntCol(default=None)
    #Source2 = IntCol(default=None)

    def __str__(self): return "%s.%s" % (self.accession, self.plant_id)
    
#
# Plant editor
#
class PlantEditor(TreeViewEditorDialog):

    visible_columns_pref = "editor.plant.columns"
    column_width_pref = "editor.plant.column_width"
    default_visible_list = ['accession', 'plant_id'] 

    label = 'Plants\\Clones'

    def __init__(self, parent=None, select=None, defaults={}):        
        TreeViewEditorDialog.__init__(self, Plant, "Plants/Clones Editor", 
                                      parent, select=select, defaults=defaults)
        # set headers
        titles = {'plant_id': 'Plant ID',
                   'accessionID': 'Accession ID',
                   'locationID': 'Location',
                   'acc_type': 'Accession Type',
                   'acc_status': 'Accession Status'}
        self.columns.titles = titles
        self.columns['accessionID'].meta.get_completions = \
            self.get_accession_completions
        self.columns['locationID'].meta.get_completions = \
            self.get_location_completions


    def get_accession_completions(self, text):
        model = gtk.ListStore(str, object)
        sr = tables["Accession"].select("acc_id LIKE '"+text+"%'")
        for row in sr:
            s = str(row) + " - " + str(row.plantname)
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
#                    s = str(row) + " - " + str(row.plantname)
#                    model.append([s, str(row), row.id])
#        elif colname == "location":
#            model = gtk.ListStore(str, int)
#            sr = tables["Location"].select()
#            for row in sr:
#                model.append([str(row), row.id])
#        return model, maxlen
        
        
try:
    from bauble.plugins.searchview.infobox import InfoBox, InfoExpander, \
        set_widget_value
except ImportError:
    pass
else:
    
    class LocationExpander(InfoExpander):
        """
        TableExpander for the Locations table
        """
        
        def __init__(self, label="Location"):
            InfoExpander.__init__(self, label)
    
        def update(self, value):
            pass
        

    class PlantInfoBox(InfoBox):
        """
        an InfoBox for a Plants table row
        """
        def __init__(self):
            InfoBox.__init__(self)
            loc = LocationExpander()
            loc.set_expanded(True)
            self.add_expander(loc)
        
        def update(self, row):
            # TODO: don't really need a location expander, could just
            # use a label in the general section
            loc = self.get_expander("Location")
            loc.update(row.location)