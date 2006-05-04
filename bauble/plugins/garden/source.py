# 
# source tables module
#

from sqlobject import * 
from bauble.plugins import BaubleTable
from bauble.plugins import tables


class Donation(BaubleTable):
    values = {}
    
    # don't allow donor to be deleted if donor still has donations
    donor = ForeignKey('Donor', notNull=True, cascade=False)                        
    # TODO: need to add the data for 0.5.0 and need to update the donation
    # editor and donation infobox to support it
    # date = DateCol()

    donor_acc = StringCol(length=12, default=None) # donor's accession id    
    notes = UnicodeCol(default=None) # ??? random text, memo
    
    # we'll have to set a default to none here because of the way our editors
    # are set up have to commit this table and then set the foreign key later,
    # we have to be careful we don't get dangling tables without an accession
    #
    # deleting the foreign accession deleted this donation
    accession = ForeignKey('Accession', default=None, cascade=True)
        
    def __str__(self):
        # i don't know why this has to be donorID instead of donor
        return tables['Donor'].get(self.donorID).name
        
    #herb_id = StringCol(length=50, default=None) # herbarium id?
    
    
class Collection(BaubleTable):
    
    _cacheValue = False
    
    collector = UnicodeCol(length=50, default=None)  # primary collector's name
    collector2 = UnicodeCol(length=50, default=None) # additional collectors name
    coll_id = UnicodeCol(length=50, default=None)    # collector's/collection id
    
    
    # collection date
    # TODO: is there anyway to get this date format from BaubleMeta, also
    # i don't know why setting dateFormat here give me an error about getting
    # the date in unicode instead of a DateTimeCol eventhough i set this
    # column using a datetime object    
    #coll_date = DateCol(default=None, dateFormat='%d/%m/%Y')    
    coll_date = DateCol(default=None)
    
    locale = UnicodeCol() # text of where collected
    
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
    
    habitat = UnicodeCol(default=None) # habitat, free text
    notes = UnicodeCol(default=None)
    
    # we'll have to set a default to none here because of the way our editors
    # are set up have to commit this table and then set the foreign key later,
    # we have to be careful we don't get dangling tables without an accession
    #
    # these are only for recording plant distribution and should
    # be put in a distribution table so the species can do a single join
    # on them, the only thing we need here is the country name
    #area = ForeignKey('Areas', default=None)
    #region = ForeignKey('Regions', default=None)
    #place = ForeignKey('Places', default=None)
    #state = ForeignKey('States', default=None)    
    country = ForeignKey('Country', default=None) # where collected
    
    # deleting this foreign accession deletes this collection
    # TODO: this shouldn't be allowed to be None
    accession = ForeignKey('Accession', default=None, cascade=True)
    
    def __str__(self):
        #if self.label == None: 
        #    return self.locale
        #return self.label
        return self.locale 


