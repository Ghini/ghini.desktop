#
# Synonyms table definition
#

from tables import *

class Synonyms(BaubleTable):
    """
    a synonym table can be a synonym for multiple plant names
    """
    
    # look up in the botanical nomenclature about the rules for synonyms
    
    # the valid name
    plantname = ForeignKey('Plantnames', notNull=True)
    
    # unambiguous synonym, maybe this should be a single join to one plantnames
    #synonym = ForeignKey('Plantnames')
    synonym = SingleJoin('Plantnames', joinColumn='id')
        
    def __str__(self): return self.site