#
# Collections table definition
#

from tables import *
from sqlobject import *    

class Collections(tables.BaubleTable):
    #name = "Collections"
    _cacheValue = False
    
    coll_name = StringCol(length=50, default=None)  # primary collector's name
    coll_name2 = StringCol(length=50, default=None) # additional collectors name
    coll_id = StringCol(length=50, default=None)    # collector's/collection id
    coll_date = DateTimeCol(default=None)         # collection data
    coll_notes = StringCol(default=None)          # collection notes
    lat_deg = IntCol(default=None) # latitude degrees
    lat_min = IntCol(default=None) # latitude minutes
    lat_sec = IntCol(default=None)  # latitude seconds
    lat_dir = StringCol(length=1, default=None) # latitude direction, N, S
    lon_deg = IntCol(default=None) # longitude degrees
    lon_min = IntCol(default=None) # longiture minutes
    lon_sec = IntCol(default=None) # longitude seconds
    lon_dir = StringCol(length=1, default=None) # longitude direction, E, W
    geo_accy = IntCol(default=None) # geo accuracy in meters
    altitude = IntCol(default=None) # altitude
    altutude_accy = IntCol(default=None) # altitude accuracy
    altitude_max = IntCol(default=None) # maximum altitude
    altitude_mac_accy = IntCol(default=None) # maximum altitude accuracy
    depth = IntCol(default=None) # depth under water
    habitat = StringCol(default=None) # habitat, free text
 
    # country where collected or origi, full name
    country = StringCol(length=50, default=None) 
    country_iso = StringCol(length=4, default=None)  # ISO code for country
    wgs = StringCol(length=50, default=None)         # world geographic scheme
    # primary subdivision of country
    country_pri_sub = StringCol(default=None)
    # secondary subdivision of country
    country_sec_sub = StringCol(length=50, default=None)
    # specific geographic unit of country
    country_sp_unit = StringCol(length=50, default=None) 
    locality = StringCol(default=None)            # full text of where collected
    
    accession = ForeignKey('Accessions', notNull=True, cascade=True)
    
    def __str__(self): return self.label