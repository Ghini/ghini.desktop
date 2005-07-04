#
# Images table definition
#

from tables import *

class Images(BaubleTable):

    # not unique but if a duplicate uri is entered the user
    # should be asked if this is what they want
    uri = StringCol()
    label = StringCol(length=50)
    
    # copyright ?
    # owner ?
    
    # should accessions also have a images in case an accession
    # differs from a plant slightly or should it just have a different
    # plantname
    #plant = MultipleJoin("Plantnames", joinColumn="image_id")
    plantname = ForeignKey('Plantnames')
    
    
    def __str__(self): return self.label