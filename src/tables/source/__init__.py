# 
# source tables module
#
# TODO: this module should contain more than one table, for now just
# a donor and a collections table, what other sources could there be?
# herbarium? garden? individual? but these are really just differen't
# types of donor's with differen't donor id's but then we would probably
# need a separate donor_id table

# TODO: the editor could be a dialog but not a treeview that has a combobox
# which determines the source type and the entry fields change depending
# on the type, in the accession editor the source column could just be 
# a button when clicked it brings up the but how do we indicate that it 
# should be button rather than a text entry if it's not a different 
# column type

# NOTE: the only problem with this is that we have to do manual joins
# but since isnt's a single join it shouldn't be too much trouble. things
# just won't be automatic like other types but this is a special one off
# exception, in the attribute setter could we set change the type of 
# the join, this is probably bad database design, the other option is 
# to have two joins, one for donor and one for collection and only
# one can be valid at a time depending on the source type

from tables import *

class Source(BaubleTable):
    
    accession = ForeignKey('Accessions', notNull=True, cascade=True)
    
    # an arbitrary string we can use a shorthand to refer to this
    # source, is this really necessary, though being able to include
    # a label like 'expedition 2004' would be kinda nice but typing
    # expedition 2004 for every collection record wouldn't
    label = StringCol(length=72, default=None) 
    
    values = {}
    # collection or donation
    type = StringCol(length=32)
    values['type'] = [('Collection', ''),
                      ('Donation', '')]
    # do we need to have a type id as an id into either donation 
    # or collections or can the type be the value that determines which
    # value we look up in the table and the id's will be the same
    #type_id = 
    
    def __str__(self): return self.label


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
    
    def __str__(self):
        return self.name


 # donor type flag, a character, see ITF2, it would probably
    # be better to have a donor table since multiple accessions can have
    # the same donor and only the donor's id, data
class Donations(Source):
    values = {}
                            
    #donor = StringCol(length=50, default=None)     # donor    
    donor_acc = StringCol(length=12, default=None) # donor's accession id    
    donor_txt = StringCol(default=None) # ??? random text, memo
    
    donor = ForeignKey('Donor', notNull=True)
    
    def __str__(self):
        if self.label == None: 
            return self.donor
        return self.label
        
    #herb_id = StringCol(length=50, default=None) # herbarium id?
    
class Collections(Source):
    name = "Collections"
    _cacheValue = False
    
    coll_name = StringCol(length=50, default=None)  # primary collector's name
    coll_name2 = StringCol(length=50, default=None) # additional collectors name
    coll_id = StringCol(length=50, default=None)    # collector's/collection id
    coll_date = DateTimeCol(default=None)         # collection date
    #coll_notes = StringCol(default=None)          # collection notes
    
    locale = StringCol(default=None) # text of where collected
    
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
    #depth = FloatCol(default=None) # depth under water
    
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
    
    notes = StringCol(default=None)
    
    def __str__(self):
        if self.label == None: 
            return self.locale
        return self.label
    
    
tables = [Donors, Source, Donations, Collections]