#
# Accessions table definition
#

from sqlobject import *

class Accessions(SQLObject):
    _cacheValue = False
    name = "Accessions"
    values = {} # dictionary of values to restrict to columns
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
    #prop_history = StringCol(length=11, default=None)

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
    ver_id = IntCol(default=None) # ?? # verifier's ID??
    
    herb_id = StringCol(length=50, default=None) # herbarium id?

    # i don't think this is the red list status but rather the status
    # of this accession in some sort of conservation program
    consv_status = StringCol(default=None) # conservation status, free text
    
    # foreign keys and joins
    plantname = ForeignKey('Plantnames', notNull=True)
    plants = MultipleJoin("Plants", joinColumn='accession_id')
    collection = SingleJoin('Collections', joinColumn='accession_id')

    # these probably belong in 
    cultv_info = StringCol(default=None)      # cultivation information
    prop_info = StringCol(default=None)       # propogation information
    acc_uses = StringCol(default=None)        # accessions uses, why diff than taxon uses?


    # these are the unknowns
#    acc = DateTimeCol(default=None) # ?
#    acct = StringCol(length=50, default=None) #?
#    BGnot = StringCol(default=None) # ******** what is this?

    def __str__(self): return self.acc_id

    # internal
    #_entered = DateTimeCol()
    #_changed = DateTimeCol()
    #_updated = DateTimeCol()
    #_Initials1st = StringCol(length=50)
    #_InitialsC = StringCol(length=50)
    #_Source1 = IntCol()
    #_Source2 = IntCol()
    
