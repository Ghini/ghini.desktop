#
# species_model.py
#

import xml.sax.saxutils as sax
from sqlobject import *
from bauble.plugins import BaubleTable


#
# Species table
#
class Species(BaubleTable):

    class sqlmeta(BaubleTable.sqlmeta):
        defaultOrder = 'sp'
    
    def __init__(self, **kw):
        super(Species, self).__init__(**kw)
        self.__cached_str = None
        
    # TODO: create an index from sp_hybrid, sp_qual, sp, sp_author, cv_group, 
    # isp, isp_author, isp_rank, genus
    #species_index = DatabaseIndex('genus', 'sp', 'sp_author', 'sp_hybrid', 
    #                             'sp_qual', 'cv_group', 'infrasp', 
    #                             'infrasp_author', 'infrasp_rank')
    sp = StringCol(length=40, notNull=True)          # specific epithet
    sp_author = UnicodeCol(default=None)  # species author    
    sp_hybrid = EnumCol(enumValues=("H", "x", "+",None), default=None)     
    sp_qual = EnumCol(enumValues=("agg.", "s. lat.", "s. str.", None), 
                      default=None)                                                
    
    cv_group = StringCol(length=50, default=None)    # cultivar group                        
    infrasp = StringCol(length=30, default=None)         # intraspecific epithet
    infrasp_author = UnicodeCol(length=255, default=None) # intraspecific author
    '''
    infrasp_rank values:
    subsp. - subspecies
    var. - variety
    subvar. - sub variety
    f. - form
    subf. - subform
    cv. - cultivar
    '''
    infrasp_rank = EnumCol(enumValues=("subsp.", "var.", "subvar.", "f.", 
                                       "subf.",  "cv.", None), default=None)    
    '''
    "aff.", # Akin to or bordering
    "cf.", # compare with
    "Incorrect", # Incorrect
    "forsan", # Perhaps
    "near", # Close to
    "?", # Questionable
    '''
    id_qual = EnumCol(enumValues=("aff.", "cf.", "Incorrect", "forsan", "near", 
                                  "?", None), default=None)    
    notes = UnicodeCol(default=None)
    
    # foreign keys
    #
    default_vernacular_name = ForeignKey('VernacularName', default=None)#, 
                                         #cascade=True)
    genus = ForeignKey('Genus', notNull=True, cascade=False)
    

    # joins
    #
    # hold meta information about this plant
    species_meta = SingleJoin('SpeciesMeta', joinColumn='species_id')
    synonyms = MultipleJoin('SpeciesSynonym', joinColumn='species_id')
    # it would be best to display the vernacular names in a dropdown list
    # with a way to add to the list    
    # FIXME: what happens if to the value in default_vernacular_name if 
    # we delete the object that this foreign key points to, should somehow
    # get reset to None
    vernacular_names = MultipleJoin('VernacularName', joinColumn='species_id')
    #accessions = MultipleJoin('Accessions', joinColumn='species_id')
    #images = MultipleJoin('Images', joinColumn='species_id')
    #references = MultipleJoin('Reference', joinColumn='species_id')
    
    def __str__(self):
        # we'll cache the str(self) since building it is relatively heavy
        # TODO: we can't enable this until we can invalidated _cached_str in
        # cache self is changed
        #if self.__cached_str is None:
        #    self.__cached_str = Species.str(self)
        #return self.__cached_str        
        return Species.str(self)
    
    
    def markup(self, authors=False):
        return Species.str(self, authors, True)
    
    
    @staticmethod
    def str(species, authors=False, markup=False):
        """
        return the full plant name string        
        """    
        # TODO: how complete is this for the latest nomenclature code?        
        # TODO: create tests for all possible name combinations 
        #genus, sp_hybrid, id_qual, sp, sp_hybrid, infrasp, cv_group
        if markup:
            italic = "<i>%s</i>"
            escape = sax.escape
        else:
            italic = "%s"
            escape = lambda x: x
            
        name = []
        name.append(italic % str(species.genus))
        
        # id qualifier
        if species.id_qual:
            name.append(species.id_qual)
            
        # take care of species hybrid
        if species.sp_hybrid:
            # we don't have a second sp name for the hyrbid formula right now
            # so we'll just use the isp for now
            if species.infrasp is not None:
                name.extend([italic % species.sp, species.sp_hybrid,
                             italic % species.infrasp])
            else:                
                name.extend([species.sp_hybrid or '', species.sp])
        else:            
            name.append(italic % species.sp)
            
        # cultivar groups and cultivars
        if species.cv_group is not None:
            if species.infrasp_rank == "cv.":                
                name.extend(['(%s Group)' % species.cv_group, 
                             "'%s'" % italic % species.infrasp])
            else:                                 
                name.append('%s Group' % species.cv_group)
            return ' '.join(name)
        
        if species.sp_author is not None and authors is not False:
            name.append(escape(species.sp_author))
        
        if species.infrasp_rank:
            if species.infrasp_rank == "cv.":
                name.append("'%s'" % species.infrasp)
            else:
                name.extend([species.infrasp_rank, italic % species.infrasp])
                if species.infrasp_author is not None and authors is not False:
                    name.append(escape(species.infrasp_author))
                    
        return ' '.join(name)
    

    
class SpeciesSynonym(BaubleTable):
    # deleting either of the species this synonym refers to makes
    # this synonym irrelevant
    species = ForeignKey('Species', default=None, cascade=True)
    synonym = ForeignKey('Species', cascade=True)
    
    
    
class SpeciesMeta(BaubleTable):
    
    poison_humans = BoolCol(default=None)
    poison_animals = BoolCol(default=None)
    
    # poison_humans should imply food_plant false or whatever value
    # is meant to be in food_plant
    #food_plant = StringCol(length=50, default=None)
    food_plant = BoolCol(default=None)
    
    # TODO: create distribution table that holds one of each of the 
    # geography tables which will hold the plants distribution, this
    # distribution table could even be part of the geography module

    # UPDATE: it might be better to do something like the source_type in the 
    # the accessions, do we need the distribution table if we're only
    # going to be holding one of the value from continent/region/etc, the only
    # exception is that we also need to hold a cultivated value and possible
    # something like "tropical", we can probably still use the distribution
    # table as long as setting to and from the distribution is handled silently
    #distribution = SingleJoin('Distribution', joinColumn='species_id', 
    #                           makeDefault=None)
    # right now we'll just include the string from one of the tdwg 
    # plant distribution tables though in the future it would be good
    # to have a SingleJoin to a distribution table so we get the extra
    # benefit of things like iso codes and hierarchial data, e.g. get
    # all plants from africa
    distribution = UnicodeCol(default=None)
    
    # this should be set by the editor
    # FIXME: this could be dangerous and cause dangling meta information
    # - removing the species removes this meta info
    species = ForeignKey('Species', default=None, cascade=True)
    
    def __str__(self):
        v = []
        if self.distribution is not None:
            v.append(self.distribution)
        if self.food_plant is not None and self.food_plant:
            v.append('Food')
        if self.poison_humans is not None and self.poison_humans:
            v.append('Poisonous')
        if self.poison_animals is not None and self.poison_animals:
            v.append('Poisonous to animals')            
        return ','.join(v)
        
        
class VernacularName(BaubleTable):
    
    name = UnicodeCol(length=64)
    language = UnicodeCol(length=64)    
    
    # default=None b/c the VernacularNameEditor can only be invoked from the 
    # SpeciesEditor and it should set this on commit
    species = ForeignKey('Species', default=None, cascade=True)

    index = DatabaseIndex('name', 'language', 'species', unique=True)

    def __str__(self):
        return self.name