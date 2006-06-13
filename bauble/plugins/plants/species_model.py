#
# species_model.py
#

import xml.sax.saxutils as sax
from sqlobject import *
from bauble.plugins import BaubleTable
from bauble.utils.log import log, debug

# TODO: need to incorporate the species qualifier and id qualifier string
# into the name string

# ***** supported names
# Genus sp
# Genus sp sp_author
# Genus sp_hybrid (cv.) 'infrasp' # not supported any more?
# Genus sp_hybrid sp
# Genus sp sp_hybrid infrasp
# Genus sp infrasp_rank infrasp
# Genus sp (cv.) 'infrasp'
# Genus sp cv_group
# Genus sp (cv.) (cv_group) 'infrasp' 

# ***** names we don't support
# Genux sp x sp2 [infrasp_rank] infrasp
# Genus sp infrasp_rank infrasp 'cv' 
# eg Rudbeckia fulgida var. sullivantii 'Goldsturm',
# we can't support this without more infrasp and infrasp_rank fields, like BGRecorder

# ***** are these even valid
# Genus x sp sp_author
# Genus sp sp_athor x infrasp infrasp_author


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
    
    # TODO: add trade_name for better support for cultivated plants
    # see http://www.hortax.org.uk/gardenplantsnames.html
    #trade_name = StringCol(length=50, default=None)    # cultivar group                        
    
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
        '''
        returns this object as a string with markup
        
        authors -- falgs to toggle whethe the author names should be included
        '''
        return Species.str(self, authors, True)
    
    
    @staticmethod
    def str(species, authors=False, markup=False):
        '''
        returns a string for species
        
        species -- the species object to get the values from
        authors -- flags to toggle whether the author names should be included
        markup - flags to toggle whether the returned text is marked up to show
        italics on the epithets
        '''
        genus = str(species.genus)
        sp = species.sp
        if markup:
            italic = "<i>%s</i>"            
            genus = italic % species.genus
            if sp is not None: # shouldn't really be allowed
                sp = italic % species.sp
            # the infrasp italic is handled below
            escape = sax.escape
        else:
            italic = "%s"
            escape = lambda x: x
            
        author = None
        isp_author = None                        
        if authors:
            if species.sp_author:
                author = escape(species.sp_author)
            if species.infrasp_author:            
                isp_author = escape(species.infrasp_author)
                    
        if species.sp_hybrid: # is a hybrid
            if species.infrasp is not None:                    
                name = [s for s in [genus, sp, author, species.sp_hybrid, 
                                    species.infrasp, isp_author] if s is not None]
            else:
                name = [s for s in [genus, species.sp_hybrid, sp, author] if s is not None]
        else: # isn't a hybrid
            if species.cv_group:
                if species.infrasp is None:
                    cv = None
                    group = '%s Group' % species.cv_group
                else:
                    cv = "'%s'" % species.infrasp
                    group = '(%s Group)' % species.cv_group
                name = [s for s in [genus, sp, author, group, cv, isp_author] if s is not None]
            else:
                if species.infrasp is None:
                    isp = None
                    isp_rank = None
                else:
                    if species.infrasp_rank == 'cv.':
                        isp_rank = None                    
                        isp = "'%s'" % (species.infrasp or '')
                    else:
                        isp_rank = species.infrasp_rank
                        isp = italic % species.infrasp
                name = [s for s in [genus, sp, author, 
                                    isp_rank, isp, isp_author] if s is not None]
            
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