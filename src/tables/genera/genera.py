#
# Genera table module
#

from tables import *

class Genera(BaubleTable):
    #name = "Genera"
    _cacheValue = False
    
    genus = StringCol(length=30, notNull=True, alternateID=True)    
    hybrid = StringCol(length=1, default=None) # generic hybrid code, H,x,+
    comments = StringCol(default=None)
    author = UnicodeCol(length=255, default=None)
    synonym_id = IntCol(default=None) # an id into this table
    
    # foreign key    
    family = ForeignKey('Families', notNull=True)
    plantnames = MultipleJoin("Plantnames", joinColumn="genus_id")

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
