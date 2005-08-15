
from sqlobject import *
from bauble.plugins import BaubleTable, tables
#from bauble.plugins.editor import TreeViewEditorDialog

class Synonyms(BaubleTable):
    """
    a synonym table can be a synonym for multiple plant names
    """
    
    # look up in the botanical nomenclature about the rules for synonyms
    
    # the valid name
    plantname = ForeignKey('Plantname', notNull=True)
    
    # unambiguous synonym, maybe this should be a single join to one plantnames
    #synonym = ForeignKey('Plantnames')
    synonym = SingleJoin('Plantname', joinColumn='id')
        
#    def __str__(self): 
#        pass