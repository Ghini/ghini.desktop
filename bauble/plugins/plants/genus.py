#
# Genera table module
#

from sqlobject import *
from bauble.plugins import BaubleTable, tables
from bauble.plugins.editor import TreeViewEditorDialog

# TODO: should be a higher_taxon column that holds values into 
# subgen, subfam, tribes etc, maybe this should be included in Genus

#
# Genus table
#
class Genus(BaubleTable):

    _cacheValue = False
    
    #genus = StringCol(length=30, notNull=True, alternateID=True)    
    # it is possible that there can be genera with the same name but 
    # different authors and probably means that at different points in literature
    # this name was used but is now a synonym even though it may not be a
    # synonym for the same species,
    # this screws us up b/c you can now enter duplicate genera, somehow
    # NOTE: we should at least warn the user that a duplicate is being entered
    genus = StringCol(length=32)#, notNull=True, alternateID=True)    
    
    hybrid = StringCol(length=1, default=None) # generic hybrid code, H,x,+
    comments = StringCol(default=None)
    author = UnicodeCol(length=255, default=None)
    #synonym_id = IntCol(default=None) # an id into this table
    synonym = ForeignKey('Genus', default=None)#IntCol(default=None) # an id into this table
    
    # foreign key    
    family = ForeignKey('Family', notNull=True)
    plantnames = MultipleJoin("Plantname", joinColumn="genus_id")

    # internal
    #_entered = DateTimeCol(default=None)
    #_changed = DateTimeCol(default=None)
    #_initials1st = StringCol(length=50, default=None)
    #_initials_c = StringCol(length=50, default=None)
    #_source_1 = IntCol(default=None)
    #_source_2 = IntCol(default=None)
    #_updated = DateTimeCol(default=None)

    def __str__(self):
        return self.genus # should include the hybrid sign
        
        
#
# editor
#
class GenusEditor(TreeViewEditorDialog):

    visible_columns_pref = "editor.genus.columns"
    column_width_pref = "editor.genus.column_width"
    default_visible_list = ['family', 'genus']
    
    label = 'Genus'
    
    def __init__(self, parent=None, select=None, defaults={}):
        TreeViewEditorDialog.__init__(self, tables["Genus"], "Genus Editor", 
                                      parent, select=select, defaults=defaults)        
        headers = {'genus': 'Genus',
                   'author': 'Author',
                   'hybrid': 'Hybrid',
                   'family': 'Family'}
        self.column_meta.headers = headers


    def get_completions(self, text, colname):
        maxlen = -1
        model = None
        if colname == "family":
            model = gtk.ListStore(str, int)
            if len(text) > 2:
                sr = tables["Family"].select("family LIKE '"+text+"%'")
                for row in sr:
                    model.append([str(row), row.id])
        return model, maxlen # not setting maxlen but maybe we should
        

#
# infobox
#
