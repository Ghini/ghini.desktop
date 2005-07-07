#
# References table definition
#

from tables import *

# TODO: references should be a many-to-many relationship with
# plantnames since each plantname can have multiple references
# and each reference can refer to multiple plantnames

# TODO: should have references in families, genera, plantnames but
# if this is a multiple join i guess i would need to specify MultipleJoin
# columns for each

# TODO: should there be a reference type so we know if the references
# implies a book then we could look up extra information on amazon or
# something, probably better to just leave it as it is and if it is 
# URI then look it up, if not, then do nothing

class Reference(BaubleTable):

    # should only need either loc_id or site as long as whichever one is 
    # unique, probably site, there is already and internal id
    # what about subReferences, like if the References were the grounds
    # and the sublocation is the block number
    label = StringCol(length=60)
    reference = StringCol()
    #plantname = ForeignKey
    #plants = MultipleJoin("Plants", joinColumn="location_id")
    #plant = ForeignKey('Plants', notNull=True)
    
    def __str__(self): return self.label