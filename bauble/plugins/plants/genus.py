#
# Genera table module
#

#from tables import *
from sqlobject import *

from bauble.plugins import BaubleTable

# TODO: should be a higher_taxon column that holds values into 
# subgen, subfam, tribes etc, maybe this should be included in Genus

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
    synonym = ForeignKey('Genera', default=None)#IntCol(default=None) # an id into this table
    
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
