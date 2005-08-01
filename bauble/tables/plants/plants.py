#
# Plants table definition
#

from sqlobject import *
from tables import *

class Plants(BaubleTable):
    
    # add to end of accession id, e.g. 04-0002.05
    # these are only unique when combined with an accession_id
    values = {}
    plant_id = IntCol(notNull=True) 

    # accession type
    acc_type = StringCol(length=4, default=None)
    values['acc_type'] = [('P', 'Whole plant'),
                          ('S', 'Seed or Sport'),
                          ('V', 'Vegetative Part'),
                          ('T', 'Tissue culture'),
                          ('O', 'Other')]
                          
    # accession status
    acc_status = StringCol(length=6, default=None)
    values['acc_status'] = [('C', 'Current accession in living collection'),
                            ('D', 'Noncurrent accession due to Death'),
                            ('T', 'Noncurrent accession due to Transfer'),
                            ('S', 'Stored in dormant state'),
                            ('O', 'Other')]

    # foreign key and joins
    accession = ForeignKey('Accessions', notNull=True, cascade=True)
    location = ForeignKey("Locations", notNull=True)
    #location = MultipleJoin("Locations", joinColumn="locations_id")
    #mta_out = MultipleJoin("MaterialTransfers", joinColumn="genus_id")
    
    # these should only be at the accession level
#    ver_level = StringCol(length=2, default=None) # verification level
#    ver_name = StringCol(length=50, default=None) # verifier's name
#    ver_date = DateTimeCol(default=None) # verification data
#    ver_hist = StringCol(default=None)  # verification history
#    ver_lit = StringCol(default=None) # verification list

    # perrination flag, 2 letter code
#    perr_flag = StringCol(length=2, default=None) 
#    breed_sys = StringCol(length=3, default=None) # breeding system    
    
#    ADatePlant = DateTimeCol(default=None)
#    ADateInspected = DateTimeCol(default=None)    
    
    # unknowns
#    plantQual = IntCol(default=None)    # ?
#    plantHeld = StringCol(length=50, default=None)    
    #dater = DateTimeCol(default=None)
    #datep = DateTimeCol(default=None)
    #datei = DateTimeCol(default=None)
    #Seedp = StringCol(length=50, default=None)
    #Seedv = StringCol(length=1, default=None) # bool ?
    #Seedl = BoolCol(default=None)
    #ExchgM = StringCol(length=10, default=None)
    #Specc = StringCol(length=1, default=None) # bool?
    #MDate = DateTimeCol(default=None)
    #MInfo = StringCol(default=None)
    #culinf = StringCol(default=None)
    #proinf = StringCol(default=None)
    #PlantsComments = StringCol(default=None)
    #LabelInfo = StringCol(default=None)
    #PlantLifeForm = StringCol(length=50, default=None)
    #InsCode = StringCol(length=6, default=None)
    #ITFRec = BoolCol(default=None)
    #Source1 = IntCol(default=None)
    #Source2 = IntCol(default=None)

    def __str__(self): return "%s.%s" % (self.accession, self.plant_id)