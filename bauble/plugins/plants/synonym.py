
from sqlobject import *
from bauble.plugins import BaubleTable, tables
#from bauble.editor import TreeViewEditorDialog

class Synonyms(BaubleTable):
    """
    a synonym table can be a synonym for multiple plant names
    """
    
    # look up in the botanical nomenclature about the rules for synonyms
    
    # the valid name
    species = ForeignKey('Species', notNull=True)
    
    # unambiguous synonym, maybe this should be a single join to one speciess
    synonym = ForeignKey('Species')
    #synonym = SingleJoin('Species', joinColumn='id')
        
#    def __str__(self): 
#        pass