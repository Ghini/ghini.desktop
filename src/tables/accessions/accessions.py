#
# Accessions table definition
#

#import tables
#from sqlobject import *
from tables import *

class Accessions(BaubleTable):
    #_cacheValue = False
    #name = "Accessions"
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
    #acc_lineage = StringCol(length=50, default=None)    
    #acctxt = StringCol(default=None) # ???

    # the source type is the name of the table and determines which
    # one of donor or collection is valid, if the source type changes,
    # which really it should never do, then it should remove the row 
    # from the table that the type was before it was changed
    #source_type = StrinCol(length=32)
    #donor = SingleJoin('Donor', joinColumn='accession')
    #collection = SingleJoin('Collection', joinColumn='accession')
    
    #
    # verification, a verification table would probably be better and then
    # the accession could have a verification history with a previous
    # verification id which could create a chain for the history
    #ver_level = StringCol(length=2, default=None) # verification level
    #ver_name = StringCol(length=50, default=None) # verifier's name
    #ver_date = DateTimeCol(default=None) # verification date
    #ver_hist = StringCol(default=None)  # verification history
    #ver_lit = StringCol(default=None) # verification lit
    #ver_id = IntCol(default=None) # ?? # verifier's ID??
    

    # i don't think this is the red list status but rather the status
    # of this accession in some sort of conservation program
    consv_status = StringCol(default=None) # conservation status, free text
    
    # foreign keys and joins
    plantname = ForeignKey('Plantnames', notNull=True)
    plants = MultipleJoin("Plants", joinColumn='accession_id')
    
    # these should probably be hidden then we can do some trickery
    # in the accession editor to choose where a collection or donation
    # source
    #collection = SingleJoin('Collections', joinColumn='accession_id')
    #donation = SingleJoin('Donation', joinColumn='accession_id')

    # these probably belong in separate tables with a single join
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
    
