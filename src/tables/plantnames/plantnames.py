#
# Plantnames table definition
#

import utils
from tables import *

class Plantnames(BaubleTable):
    
    def __init__(self, **kw):
        super(Plantnames, self).__init__(**kw)
        
        self.values = {"sp_hybrid": [("H", "Hybrid formula"),
                                     ("x", "Nothotaxon hybrid"),
                                     ("+", "Graft hybrid/chimaera")],
                       "sp_qual": [("agg.", "Aggregate"),
                                   ("s. lat.", "sensu lato"),
                                   ("s. str.", "sensu stricto")],

                                     
                      }
        
        
    sp_hybrid = StringCol(length=1, default=None)  # species hybrid, x, H,...
    
    
    sp_qual = StringCol(length=10, default=None)  # species qualifier, agg., s. lat, s.str
#    values["sp_qual"] = [("agg.", "Aggregate"),
#                         ("s. lat.", "sensu lato"),
#                         ("s. str.", "sensu stricto")]
                                                    
    sp = StringCol(length=40, notNull=True)          # specific epithet
    #sp_author = StringCol(length=255, default=None)  # species author
    sp_author = UnicodeCol(dbEncoding='latin-1', default=None)  # species author
        
    cv_group = StringCol(length=50, default=None)    # cultivar group
    cv = StringCol(length=30, default=None)          # cultivar epithet
    trades = StringCol(length=50, default=None)      # trades, e.g. "Sundance"

    # full name shouldn't be necessary
    #full_name = StringCol(length=50, default=None)
    
    supfam = StringCol(length=30, default=None)  
        
    subgen = StringCol(length=50, default=None)
    subgen_rank = StringCol(length=12, default=None)
#    values["subgen_rank"] = [("subgenus", "Subgenus"),
#                             ("section", "Section"),
#                             ("subsection", "Subsection"),
#                             ("series", "Series"),
#                             ("subseries", "Subseries")]
                             

    isp = StringCol(length=30, default=None)         # intraspecific epithet
    #isp_author = StringCol(length=254, default=None) # intraspecific author
    isp_author = UnicodeCol(length=255, dbEncoding="latin-1", default=None) # intraspecific author
    isp_rank = StringCol(length=10, default=None)    # intraspecific rank
#    values["isp_rank"] = [("subsp.", "Subspecies"),
#                          ("var.", "Variety"),
#                          ("subvar.", "Subvariety"),
#                          ("f.", "Forma"),
#                          ("subf.", "Subform")]

    isp2 = StringCol(length=30, default=None)
    isp2_author = UnicodeCol(length=254, default=None)
    isp2_rank = StringCol(length=10, default=None)
#    values["isp2_rank"] = [("subsp.", "Subspecies"),
#                           ("var.", "Variety"),
#                           ("subvar.", "Subvariety"),
#                           ("f.", "Forma"),
#                           ("subf.", "Subform")]


    isp3 = StringCol(length=30, default=None)
    isp3_author = UnicodeCol(length=254, default=None)
    isp3_rank = StringCol(length=10, default=None)
#    values["isp3_rank"] = [( "subsp.", "Subspecies"),
#                           ("var.", "Variety"),
#                           ("subvar.", "Subvariety"),
#                           ("f.", "Forma"),
#                           ("subf.", "Subform")]

    isp4 = StringCol(length=30, default=None)
    isp4_author = UnicodeCol(length=254, default=None)
    isp4_rank = StringCol(length=10, default=None)
#    values["isp4_rank"] = [( "subsp.", "Subspecies"),
#                           ("var.", "Variety"),
#                           ("subvar.", "Subvariety"),
#                           ("f.", "Forma"),
#                           ("subf.", "Subform")]

    # TODO: maybe the IUCN information should be looked up online
    # rather than being entered in the database or maybe there could
    # be an option to lookup the code online
    iucn23 = StringCol(length=5, default=None)  # iucn category version 2.3
#    values["iucn23"] = [("EX", "Extinct"),
#                        ("EW", "Extinct in the wild"),
#                        ("CR", "Critically endangered"),
#                        ("EN", "Endangered"),
#                        ("VU", "Vulnerable"),
#                        #("LR", "Low risk"),
#                        ("CD", "Conservation dependent"), # low risk cat 1
#                        ("NT", "Near threatened"), # low risk cat 2
#                        ("LC", "Least consern"), # low risk cat 3
#                        ("DD", "Data deficient"),
#                        ("NE", "Not evaluated")]
    
    iucn31 = StringCol(length=50, default=None) # iucn category_version 3.1
#    values["iucn31"] = [("EX", "Extinct"),
#                        ("EW", "Extinct in the wild"),
#                        ("CR", "Critically endangered"),
#                        ("EN", "Endangered"),
#                        ("VU", "Vulnerable"),
#                        ("NT", "Near threatened"), 
#                        ("LC", "Least consern"), 
#                        ("DD", "Data deficient"),
#                        ("NE", "Not evaluated")]
    
    #rank_qual = StringCol(length=1, default=None) # rank qualifier, a single character
    
    id_qual = StringCol(length=10, default=None)#id qualifier, aff., cf., etc...
#    values["id_qual"] = [("aff.", "Akin to or bordering"),
#                         ("cf.", "compare with"),
#                         ("Incorrect", "Incorrect"),
#                         ("forsan", "Perhaps"),
#                         ("near", "Close to"),
#                         ("?", "Quesionable")]
    
    vernac_name = StringCol(default=None)          # vernacular name

#    synonym = StringCol(default=None)  # should really be an id into table \
#                                       # or there should be a syn table
    

    poison_humans = BoolCol(default=None)
    poison_animals = BoolCol(default=None)
    food_plant = StringCol(length=50, default=None)

    # origin, should be value from one of the country
    # tables, i think the values of the country tables can be combined
    # into a string to give more specific information, either that or
    # maybe an index into one of the tables with the value being chosen
    # from a combo
    origin = StringCol(default=None)

    # foreign keys and joins
    genus = ForeignKey('Genera', notNull=True)
    accessions = MultipleJoin('Accessions', joinColumn='plantname_id')
    images = MultipleJoin('Images', joinColumn='plantname_id')
    #references = MultipleJoin('References', joinColumn='plantname_id')
    ######## the rest? ##############    
    #Lifeform = StringCol(length=10)
#    tuses = StringCol(default=None) # taxon uses?
#    trange = StringCol(default=None)# taxon range?
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