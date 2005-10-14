#
# Family table definition
#

#from tables import *
from sqlobject import *
from bauble.plugins import BaubleTable, tables
from bauble.plugins.editor import TreeViewEditorDialog
from datetime import datetime

class Family(BaubleTable):

    family = StringCol(length=45, notNull=True, alternateID="True")
    comments = StringCol(default=None)

    genera = MultipleJoin("Genus", joinColumn="family_id")
    
    
#    _created = DateTimeCol(default=datetime.now(), dbName='_created')
#    _updated = DateTimeCol(default=datetime.now(), dbName='_updated')
#    def _SO_setValue(self, name, value, from_python, to_python):
#        self.BaubleTable(name, value, from_python, to_python)
    # internal
    #_entered = DateTimeCol(default=None, forceDBName=True)
    #_changed = DateTimeCol(default=None, forceDBName=True)
    #_initials1st = StringCol(length=10, default=None, forceDBName=True)
    #_initials_c = StringCol(length=10, default=None, forceDBName=True)
    #_source_1 = IntCol(default=None, forceDBName=True)
    #_source_2 = IntCol(default=None, forceDBName=True)
    #_updated = DateTimeCol(default=None, forceDBName=True)

    def __str__(self): return self.family


# 
# editor
#
class FamilyEditor(TreeViewEditorDialog):

    visible_columns_pref = "editor.family.columns"
    column_width_pref = "editor.family.column_width"
    default_visible_list = ['family', 'comments']
    
    label = 'Families'
    
    def __init__(self, parent=None, select=None, defaults={}):
        
        TreeViewEditorDialog.__init__(self, tables["Family"], "Family Editor", 
                                      parent, select=select, defaults=defaults)
        titles = {'family': 'Family',
                  'comments': 'Comments'}               
        self.columns.titles = titles



#
# infobox for SearchView
# 
try:
    from bauble.plugins.searchview.infobox import InfoBox
except ImportError:
    pass
else:
    class FamiliesInfoBox(InfoBox):
        """
        - number of taxon in number of genera
        - references
        """
        def __init__(self):
            InfoBox.__init__(self)