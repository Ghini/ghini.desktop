#
# Accessions table definition
#

from sqlobject import *

class Accessions(SQLObject):
    _cacheValue = False
    name = "Accessions"
    values = {}
    acc_id = StringCol(length=20, notNull=True, alternateID=True)
    
    prov_type = StringCol(length=1, default=None) # provenance type
    values["prov_type"] = [("W", "Wild"),
                           ("Z", "Propagule of wild plant in cultivation"),
                           ("G", "Not of wild source"),
                           ("U", "Insufficient data")]
    
    

    # wild provenance status, wild native, wild non-native, cultivated native
    wild_prov_status = StringCol(length=50, default=None)
    values["wild_prov_status"] = [("Wild native", "Endemic found within it indigineous range"),
                                  ("Wild non-native", "Propagule of wild plant in cultivation"),
                                  ("Cultivated native", "Not of wild source"),
                                  ("U", "Insufficient data")]
                                 
    # propagation history ???
    prop_history = StringCol(length=11, default=None)

    # accession lineage, parent garden code and acc id ???
    acc_lineage = StringCol(length=50, default=None)    
    acctxt = StringCol(default=None) # ???

    # donor type flag, a character, see ITF2, it would probably
    # be better to have a donor table since multiple accessions can have
    # the same donor and only the donor's id, data
    donor_type = StringCol(length=1, default=None) 
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
                            
    donor = StringCol(length=50, default=None)     # donor    
    donor_acc = StringCol(length=12, default=None) # donor's accession id    
    donor_txt = StringCol(default=None) # ???
    donor_id = IntCol(default=None)     # ???
    
    #
    # verification, a verification table would probably be better and then
    # the accession could have a verification history
    ver_level = StringCol(length=2, default=None) # verification level
    ver_name = StringCol(length=50, default=None) # verifier's name
    ver_date = DateTimeCol(default=None) # verification date
    ver_hist = StringCol(default=None)  # verification history
    ver_lit = StringCol(default=None) # verification lit
    vid = IntCol(default=None) # ??
    
    herb_id = StringCol(length=50, default=None) # herbarium id?

    # collection information
    country = StringCol(length=50, default=None) # country of origin, full name 
    country_iso = StringCol(length=4, default=None)  # ISO code for country
    wgs = StringCol(length=50, default=None)         # world geographic scheme
    # primary subdivision of country
    country_pri_sub = StringCol(default=None)      
    # secondary subdivision of country
    country_sec_sub = StringCol(length=50, default=None)
    # specific geographic unit of country
    country_sp_unit = StringCol(length=50, default=None) 
    locality = StringCol(default=None)            # full text of where collected
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
    
    
    consv_status = StringCol(default=None) # conservation status, free text
    
    
    
    
    
    # foreign keys
    plantname = ForeignKey('Plantnames', notNull=True)
    plants = MultipleJoin("Plants", joinColumn='accession_id')

    # these probably belong in 
    cultv_info = StringCol(default=None)      # cultivation information
    prop_info = StringCol(default=None)       # propogation information
    acc_uses = StringCol(default=None)        # accessions uses, why diff than taxon uses?


    # these are the unknowns
    acc = DateTimeCol(default=None) # ?
    acct = StringCol(length=50, default=None) #?
    BGnot = StringCol(default=None) # ******** what is this?

    def __str__(self): return self.acc_id

    # internal
    #_entered = DateTimeCol()
    #_changed = DateTimeCol()
    #_updated = DateTimeCol()
    #_Initials1st = StringCol(length=50)
    #_InitialsC = StringCol(length=50)
    #_Source1 = IntCol()
    #_Source2 = IntCol()