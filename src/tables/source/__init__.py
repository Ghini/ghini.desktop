# 
# source tables module
#

from tables import *

class Donors(BaubleTable):
    
    values = {}
    # herbarium, garden, individual, etc...
    donor_type = StringCol(length=1)
    values["donor_type"] = [("E", "Expedition"),
                            ("G", "Gene bank"),
                            ("B", "Botanic Garden or Arboretum"),
                            ("R", "Other research, field or experimental station"),
                            ("S", "Staff of the botanic garden to which record system applies"),
                            ("U", "University Department"),
                            ("H", "Horticultural Association or Garden Club"),
                            ("M", "Municipal department"),
                            ("N", "Nursery or other commercial establishment"),
                            ("I", "Individual"),
                            ("O", "Other"),
                            ("U", "Unknown")]
                            
    name = StringCol(length=72)
    donations = MultipleJoin('Donations', joinColumn='donor_id')
    
    # contact information
    address = StringCol(default=None)
    email = StringCol(default=None)
    fax = StringCol(default=None)
    tel = StringCol(default=None)
    
    def __str__(self):
        return self.name


class Donations(BaubleTable):
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
    
    
class Collections(BaubleTable):
    
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
    altitude = FloatCol(default=None) # altitude
    altutude_accy = FloatCol(default=None) # altitude accuracy
    #altitude_max = IntCol(default=None) # maximum altitude
    #altitude_mac_accy = IntCol(default=None) # maximum altitude accuracy
    
    # depth under water, same as minus altitude
    #depth = FloatCol(default=None) 
    
    habitat = StringCol(default=None) # habitat, free text
    notes = StringCol(default=None)
    
    # we'll have to set a default to none here because of the way our editors
    # are set up have to commit this table and then set the foreign key later,
    # we have to be careful we don't get dangling tables without an accession
    area = ForeignKey('Areas', default=None)
    region = ForeignKey('Region', default=None)
    place = ForeignKey('Place', default=None)
    accession = ForeignKey('Accessions', default=None)
    
    def __str__(self):
        #if self.label == None: 
        #    return self.locale
        #return self.label
        return self.locale 
    
    
tables = [Donors, Donations, Collections]
