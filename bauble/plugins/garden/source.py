# 
# source tables module
#

from sqlobject import * 
from bauble.plugins import BaubleTable


class Donation(BaubleTable):
    values = {}
    
    donor = ForeignKey('Donor', notNull=True)                        
    donor_acc = StringCol(length=12, default=None) # donor's accession id    
    notes = StringCol(default=None) # ??? random text, memo
    
    # we'll have to set a default to none here because of the way our editors
    # are set up have to commit this table and then set the foreign key later,
    # we have to be careful we don't get dangling tables without an accession
    accession = ForeignKey('Accession', default=None)
    
    def __str__(self):
        # i don't know why this has to be donorID instead of donor
        return Donors.get(self.donorID).name # 

        
    #herb_id = StringCol(length=50, default=None) # herbarium id?
    
    
class Collection(BaubleTable):
    
    _cacheValue = False
    
    collector = StringCol(length=50, default=None)  # primary collector's name
    collector2 = StringCol(length=50, default=None) # additional collectors name
    coll_id = StringCol(length=50, default=None)    # collector's/collection id
    coll_date = DateTimeCol(default=None)         # collection date
    
    locale = StringCol() # text of where collected
    
    # this could also just be a float and we could convert back and 
    # forth to deg, min, sec with a utility function
    latitude = FloatCol(default=None)
    longitude = FloatCol(default=None)
    geo_accy = IntCol(default=None) # geo accuracy in meters
    
    # should altitude be a plus or minus and get rid of depth
    elevation = FloatCol(default=None) # altitude
    elevation_accy = FloatCol(default=None) # altitude accuracy
    #altitude_max = IntCol(default=None) # maximum altitude
    #altitude_mac_accy = IntCol(default=None) # maximum altitude accuracy
    
    # depth under water, same as minus altitude
    #depth = FloatCol(default=None) 
    
    habitat = StringCol(default=None) # habitat, free text
    notes = StringCol(default=None)
    
    # we'll have to set a default to none here because of the way our editors
    # are set up have to commit this table and then set the foreign key later,
    # we have to be careful we don't get dangling tables without an accession
    #
    # these are only for recording plant distribution and should
    # be put in a distribution table so the plantnames can do a single join
    # on them, the only thing we need here is the country name
    #area = ForeignKey('Areas', default=None)
    #region = ForeignKey('Regions', default=None)
    #place = ForeignKey('Places', default=None)
    #state = ForeignKey('States', default=None)
    country = ForeignKey('Country', default=None) # where collected
    accession = ForeignKey('Accessions', default=None)
    
    def __str__(self):
        #if self.label == None: 
        #    return self.locale
        #return self.label
        return self.locale 


