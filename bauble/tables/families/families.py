#
# Family table definition
#

from tables import *

class Family(BaubleTable):

    family = StringCol(length=45, notNull=True, alternateID="True")
    comments = StringCol(default=None)

    genus = MultipleJoin("Genera", joinColumn="family_id")
    
    # internal
    #_entered = DateTimeCol(default=None, forceDBName=True)
    #_changed = DateTimeCol(default=None, forceDBName=True)
    #_initials1st = StringCol(length=10, default=None, forceDBName=True)
    #_initials_c = StringCol(length=10, default=None, forceDBName=True)
    #_source_1 = IntCol(default=None, forceDBName=True)
    #_source_2 = IntCol(default=None, forceDBName=True)
    #_updated = DateTimeCol(default=None, forceDBName=True)

    def __str__(self): return self.family