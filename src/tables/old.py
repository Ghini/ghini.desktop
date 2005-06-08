
import sys
import os

from sqlobject import *  

#import bbl_utils
import utils

#TODO: all not editable columns should begin with a __

class Families(SQLObject):
    _cacheValue = False
    family = StringCol(length=45, notNull=True)
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

class Genera(SQLObject):
    _cacheValue = False
    
    genus = StringCol(length=30, notNull=True)    
    hybrid = StringCol(length=1, default=None) # generic hybrid code, H,x,+
    comments = StringCol(default=None)
    author = StringCol(length=50, default=None)
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
    

class Plantnames(SQLObject):
    _cacheValue = False
    values = {}
    
    sp_hybrid = StringCol(length=1, default=None)  # species hybrid, x, H,...
    values["sp_hybrid"] = [("H", "Hybrid formula"),
                           ("x", "Nothotaxon hybrid"),
                           ("+", "Graft hybrid/chimaera")]
    
    sp_qual = StringCol(length=10, default=None)  # species qualifier, agg., s. lat, s.str
    values["sp_qual"] = [("agg.", "Aggregate"),
                         ("s. lat.", "sensu lato"),
                         ("s. str.", "sensu stricto")]
                                                    
    sp = StringCol(length=40, notNull=True)          # specific epithet
    sp_author = StringCol(length=255, default=None)  # species author
        
    cv_group = StringCol(length=50, default=None)    # cultivar group
    cv = StringCol(length=30, default=None)          # cultivar epithet
    trades = StringCol(length=50, default=None)      # trades, e.g. "Sundance"

    # full name shouldn't be necessary
    full_name = StringCol(length=50, default=None)
    
    supfam = StringCol(length=30, default=None)  
        
    subgen = StringCol(length=50, default=None)
    subgen_rank = StringCol(length=12, default=None)
    values["subgen_rank"] = [("subgenus", "Subgenus"),
                             ("section", "Section"),
                             ("subsection", "Subsection"),
                             ("series", "Series"),
                             ("subseries", "Subseries")]
                             

    isp = StringCol(length=30, default=None)         # intraspecific epithet
    isp_author = StringCol(length=254, default=None) # intraspecific author
    isp_rank = StringCol(length=10, default=None)    # intraspecific rank
    values["isp_rank"] = [("subsp.", "Subspecies"),
                          ("var.", "Variety"),
                          ("subvar.", "Subvariety"),
                          ("f.", "Forma"),
                          ("subf.", "Subform")]

    isp2 = StringCol(length=30, default=None)
    isp2_author = StringCol(length=254, default=None)
    isp2_rank = StringCol(length=10, default=None)
    values["isp2_rank"] = [("subsp.", "Subspecies"),
                           ("var.", "Variety"),
                           ("subvar.", "Subvariety"),
                           ("f.", "Forma"),
                           ("subf.", "Subform")]


    isp3 = StringCol(length=30, default=None)
    isp3_author = StringCol(length=254, default=None)
    isp3_rank = StringCol(length=10, default=None)
    values["isp3_rank"] = [( "subsp.", "Subspecies"),
                           ("var.", "Variety"),
                           ("subvar.", "Subvariety"),
                           ("f.", "Forma"),
                           ("subf.", "Subform")]

    isp4 = StringCol(length=30, default=None)
    isp4_author = StringCol(length=254, default=None)
    isp4_rank = StringCol(length=10, default=None)
    values["isp4_rank"] = [( "subsp.", "Subspecies"),
                           ("var.", "Variety"),
                           ("subvar.", "Subvariety"),
                           ("f.", "Forma"),
                           ("subf.", "Subform")]

    # TODO: maybe the IUCN information should be looked up online
    # rather than being entered in the database or maybe there could
    # be an option to lookup the code online
    iucn23 = StringCol(length=5, default=None)  # iucn category version 2.3
    values["iucn23"] = [("EX", "Extinct"),
                        ("EW", "Extinct in the wild"),
                        ("CR", "Critically endangered"),
                        ("EN", "Endangered"),
                        ("VU", "Vulnerable"),
                        #("LR", "Low risk"),
                        ("CD", "Conservation dependent"), # low risk cat 1
                        ("NT", "Near threatened"), # low risk cat 2
                        ("LC", "Least consern"), # low risk cat 3
                        ("DD", "Data deficient"),
                        ("NE", "Not evaluated")]
    
    iucn31 = StringCol(length=50, default=None) # iucn category_version 3.1
    values["iucn31"] = [("EX", "Extinct"),
                        ("EW", "Extinct in the wild"),
                        ("CR", "Critically endangered"),
                        ("EN", "Endangered"),
                        ("VU", "Vulnerable"),
                        ("NT", "Near threatened"), 
                        ("LC", "Least consern"), 
                        ("DD", "Data deficient"),
                        ("NE", "Not evaluated")]
    
    #rank_qual = StringCol(length=1, default=None) # rank qualifier, a single character
    
    id_qual = StringCol(length=10, default=None)#id qualifier, aff., cf., etc...
    values["id_qual"] = [("aff.", "Akin to or bordering"),
                         ("cf.", "compare with"),
                         ("Incorrect", "Incorrect"),
                         ("forsan", "Perhaps"),
                         ("near", "Close to"),
                         ("?", "Quesionable")]
    
    vernac_name = StringCol(default=None)          # vernacular name

    synonym = StringCol(default=None)  # should really be an id into table \
                                       # or there should be a syn table
    #SynonynID = IntCol(, default=None) # ********* did i add this?
    poison_humans = BoolCol(default=None)
    poison_animals = BoolCol(default=None)
    food_plant = StringCol(length=50, default=None)

    # foreign key
    genus = ForeignKey('Genera', notNull=True)
    accessions = MultipleJoin('Accessions', joinColumn="plantname_id")
    
    ######## the rest? ##############    
    #Lifeform = StringCol(length=10)
    tuses = StringCol(default=None) # taxon uses?
    trange = StringCol(default=None)# taxon range?
    #pcomments = StringCol()
    #Source1 = IntCol()
    #Source2 = IntCol()
    #Initials1st = StringCol(length=50)
    #InitialsC = StringCol(length=50)

        
    # internal
    #Entered = DateTimeCol()
    #Updated = DateTimeCol()
    #Changed = DateTimeCol()

    def __str__(self):
        return utils.plantname2str(self)

    
class MaterialTransfers(SQLObject):
    _cacheValue = False
    # foreign keys
    plantname = ForeignKey('Plants', notNull=True)

    
class Accessions(SQLObject):
    _cacheValue = False
    values = {}
    acc_id = StringCol(length=20, notNull=True)
    #Field1 = IntCol(default=None)
    #nameid = IntCol(default=None)
    
    prov_type = StringCol(length=1,default=None) # provenance type
    values["prov_type"] = [("W", "W"),
                           ("Z", "Z"),
                           ("G", "G"),
                           ("U", "U")]
    
    acc = DateTimeCol(default=None) # ?
    acct = StringCol(length=50, default=None) #?

    # wild provenance status, wild native, wild non-native, cultivated native
    wild_prov_status = StringCol(length=50, default=None)

    # propagation history
    prop_history = StringCol(length=11, default=None)

    # accession lineage, parent garden code and acc id
    acc_lineage = StringCol(length=50, default=None)    
    acctxt = StringCol(default=None) # ???

    # donor type flag, a character, see ITF2
    donor_type = StringCol(length=1, default=None) 
    donor = StringCol(length=50, default=None)     # donor    
    donor_acc = StringCol(length=12, default=None) # donor's accession id    
    donor_txt = StringCol(default=None) # ???
    donor_id = IntCol(default=None)     # ???
    
    cultv_info = StringCol(default=None)      # cultivation information
    prop_info = StringCol(default=None)       # propogation information
    acc_uses = StringCol(default=None)        # accessions uses, why diff than taxon uses?
    
    ver_level = StringCol(length=2, default=None) # verification level
    ver_name = StringCol(length=50, default=None) # verifier's name
    ver_date = DateTimeCol(default=None) # verification data
    ver_hist = StringCol(default=None)  # verification history
    ver_lit = StringCol(default=None) # verification list
    vid = IntCol(default=None) # ??
    
    herb_id = StringCol(length=50, default=None) # herbarium id?

    
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
    coll_id = StringCol(length=50, default=None)    # collector's id
    coll_name2 = StringCol(length=50, default=None) # additional collectors name
    coll_date = DateTimeCol(default=None)         # collection data
    coll_notes = StringCol(default=None)          # collection notes
    colid = IntCol(default=None)
    lat_deg = IntCol(default=None) # latitude degrees
    lat_min = IntCol(default=None) # latitude minutes
    latsec = IntCol(default=None)  # latitude seconds
    latdir = StringCol(length=1, default=None) # latitude direction, N, S
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
    
    BGnot = StringCol(default=None) # ******** what is this?


    # material transfer, need to work on this
    MatTransIn = IntCol(default=None)
    MatTransOut = IntCol(default=None)
    MatTransOut2 = IntCol(default=None)
    MatTransOut3 = IntCol(default=None)
    
    # foreign keys
    plantname = ForeignKey('Plantnames', notNull=True)
    plants = MultipleJoin("Plants", joinColumn='accession_id')

    

    def __str__(self): return self.acc_id

    # internal
    #_entered = DateTimeCol()
    #_changed = DateTimeCol()
    #_updated = DateTimeCol()
    #_Initials1st = StringCol(length=50)
    #_InitialsC = StringCol(length=50)
    #_Source1 = IntCol()
    #_Source2 = IntCol()

class Plants(SQLObject):
    _cacheValue = False
    plant_id = IntCol(notNull=True)# add to end of accession id, e.g. 04-0002.05
    plantQual = IntCol(default=None)    # ?
    plantHeld = StringCol(length=50, default=None) 
    acct = StringCol(length=4, default=None)
    accsta = StringCol(length=6, default=None)

    ver_level = StringCol(length=2, default=None) # verification level
    ver_name = StringCol(length=50, default=None) # verifier's name
    ver_date = DateTimeCol(default=None) # verification data
    ver_hist = StringCol(default=None)  # verification history
    ver_lit = StringCol(default=None) # verification list

    # perrination flag, 2 letter code
    perr_flag = StringCol(length=2, default=None) 
    breed_sys = StringCol(length=3, default=None) # breeding system

    
    
    dater = DateTimeCol(default=None)
    datep = DateTimeCol(default=None)
    datei = DateTimeCol(default=None)
    Seedp = StringCol(length=50, default=None)
    Seedv = StringCol(length=1, default=None) # bool ?
    Seedl = BoolCol(default=None)
    ExchgM = StringCol(length=10, default=None)
    Specc = StringCol(length=1, default=None) # bool?
    MDate = DateTimeCol(default=None)
    MInfo = StringCol(default=None)
    culinf = StringCol(default=None)
    proinf = StringCol(default=None)
    PlantsComments = StringCol(default=None)
    LabelInfo = StringCol(default=None)
    PlantLifeForm = StringCol(length=50, default=None)
    InsCode = StringCol(length=6, default=None)
    ITFRec = BoolCol(default=None)
    Source1 = IntCol(default=None)
    Source2 = IntCol(default=None)
    
    ADatePlant = DateTimeCol(default=None)
    ADateInspected = DateTimeCol(default=None)

    # foreign key
    #accid1 = StringCol(length=50)
    # this is not the "accession id" but an
    # id into the accessions table
    accession = ForeignKey('Accessions', notNull=True)
    mta_out = MultipleJoin("MaterialTransfers", joinColumn="genus_id")
    

    def __str__(self): return "%s.%s" % (self.accession, self.plant_id)
    

    
class Locations(SQLObject):
    _cacheValue = False

    # don't need this as long as there's as long as the sites are 
    loc_id = StringCol(length=20) 
    site = StringCol(length=60)
    description = StringCol()

    plant = ForeignKey('Plants', notNull=True)

    # don't know why i would need a source in the locations
    #source_1 = IntCol() # id to source tables?
    #source_2 = IntCol()
    
    # other    
    # internal
    #_Updated = DateTimeCol()
    #_Changed = DateTimeCol()
    #_Initials1st = StringCol(length=50)
    #_InitialsC = StringCol(length=50)        
    #_Entered = DateTimeCol()
    #_Initials1st = StringCol(length=50)
    #_InitialsC = StringCol(length=50)

class Addresses_leave(SQLObject):
    _cacheValue = False    
    AddressID = StringCol(length=5)
    CompanyName = StringCol(length=40)
    MainContactName = StringCol(length=30)
    ContactTitle = StringCol(length=30)
    Address = StringCol(length=60)
    City = StringCol(length=15)
    Region = StringCol(length=15)
    PostalCode = StringCol(length=10)
    Country = StringCol(length=15)
    Phone = StringCol(length=24)
    Fax = StringCol(length=24)

class Contacts(SQLObject):
    _cacheValue = False
    ContactID = IntCol()
    FirstName = StringCol(length=50)
    LastName = StringCol(length=50)
    Dear = StringCol(length=50)
    Address = StringCol()
    City = StringCol(length=50)
    StateOrProvince = StringCol(length=20)
    PostalCode = StringCol(length=20)
    Region = StringCol(length=50)
    Country = StringCol(length=50)
    CompanyName = StringCol(length=50)
    Title = StringCol(length=50)
    WorkPhone = StringCol(length=30)
    WorkExtension = StringCol(length=20)
    MobilePhone = StringCol(length=30)
    FaxNumber = StringCol(length=30)
    EmailName = StringCol(length=50)
    WWW_Address = StringCol(length=50)
    LastMeetingDate = DateTimeCol()
    ContactTypeID = IntCol()
    ReferredBy = StringCol(length=50)
    Notes = StringCol()

class Sources(SQLObject):
    _cacheValue = False    
    #source_id = IntCol()
    sdesc = StringCol(length=50)
    s = DateTimeCol()
    sau = StringCol(length=50)
    stitle = StringCol()
    spub = StringCol(length=50)
    svol = StringCol()
    src_notes = StringCol()

    # other
    Entered = DateTimeCol()
    Updated = DateTimeCol()
    Changed = DateTimeCol()
    Initials1st = StringCol(length=10)
    InitialsC = StringCol(length=10)


class FlagGroup(SQLObject):
    _cacheValue = False
    #FlagGrpId = IntCol() # just use generated id
    FlagGrp = StringCol(length=20)
    FlagDesc = StringCol()


class Flags(SQLObject):
    _cacheValue = False
    #FlagId = IntCol() # just use generated id
    flag_abb = StringCol(length=50)
    flag_description = StringCol()
    
    flag_grp = ForeignKey("FlagGroup")
    #flag_grp_id = IntCol()


class ISOCountries(SQLObject):
    _cacheValue = False
    iso_code = StringCol(length=254)
    Country_Description = StringCol()
    Country_Comments = StringCol()
    Source1 = IntCol()
    Source2 = IntCol()
    Updated = DateTimeCol()
    Entered = DateTimeCol()
    Changed = DateTimeCol()
    Initials_1st = StringCol(length=50)
    InitialsC = StringCol(length=50)


class Lifeforms(SQLObject):
    _cacheValue = False
    LifeformCode = StringCol(length=10)
    PlantDescription = StringCol(length=50)
    Comments = StringCol()


class WGSContinent(SQLObject):
    _cacheValue = False
    #ID = IntCol()
    continent = StringCol(length=255)


class WGSGeographical(SQLObject):
    _cacheValue = False
    #ID = StringCol(length=255)
    Region = StringCol(length=255)
    iso = StringCol(length=255)
    #continent_id = IntCol()
    RegID = IntCol()
    BGCIentered = BoolCol()

    continent_id = ForeignKey("WGSContinent")


class WGSRegion(SQLObject):
    _cacheValue = False
    #ID = IntCol()
    region = StringCol(length=255)
    continent_id = ForeignKey("WGSContinent")
    #ContID = IntCol()
    #Continent = StringCol(length=255)


class Contacts_leave(SQLObject):
    _cacheValue = False
    Contact_ID = IntCol()
    Surname = StringCol(length=50)
    First_name = StringCol(length=50)
    Middle_Name = StringCol(length=50)
    Address = StringCol(length=50)
