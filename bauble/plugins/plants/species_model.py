#
# species_model.py
#

import traceback
import gtk
import xml.sax.saxutils as sax
from sqlalchemy import *
from sqlalchemy.orm.session import object_session
import bauble
import bauble.utils as utils
from bauble.utils.log import log, debug
from bauble.types import Enum
from bauble.plugins.plants.geography import Geography, geography_table


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
# we can't support this without more infrasp and infrasp_rank fields,
# like BGRecorder

# ***** are these even valid
# Genus x sp sp_author
# Genus sp sp_athor x infrasp infrasp_author

# TODO: the callbacks on a vernacular name should be the same as for a species
# so that the two act more or less the same, they could even use the same 
# infobox if they don't already, and the same children expander, maybe the 
# markup for the search result should have be formatted like Name (Genus sp.)

def edit_callback(row):
    if isinstance(row, Species):
        value = row
    else: # TreeModelRow
        value = row[0]
    from bauble.plugins.plants.species_editor import SpeciesEditor
    e = SpeciesEditor(value)
    return e.start() != None


def add_accession_callback(row):
    from bauble.plugins.garden.accession import AccessionEditor
    if isinstance(row, Species):
        value = row
    else: # TreeModelRow
        value = row[0]
    e = AccessionEditor(Accession(species=value))
    return e.start() != None

def remove_callback(row):
    if isinstance(row, Species):
        value = row
    else: # TreeModelRow
        value = row[0]
    s = '%s: %s' % (value.__class__.__name__, str(value))
    msg = "Are you sure you want to remove %s?" % utils.xml_safe(s)
    if not utils.yes_no_dialog(msg):
        return    
    try:
        session = create_session()
        obj = session.load(value.__class__, value.id)
        session.delete(obj)
        session.flush()
    except Exception, e:
        msg = 'Could not delete.\n\n%s' % utils.xml_safe(e)        
        utils.message_details_dialog(msg, traceback.format_exc(), 
                                     type=gtk.MESSAGE_ERROR)
    return True
    
    

species_context_menu = [('Edit', edit_callback),
                       ('--', None),
                       ('Add accession', add_accession_callback),
                       ('--', None),
                       ('Remove', remove_callback)]

def call_on_species(func): 
    return lambda row: func(row[0].species)

vernname_context_menu = [('Edit', call_on_species(edit_callback)),
                          ('--', None),
                          ('Add accession',
                           call_on_species(add_accession_callback)),]
#                          ('--', None)]
#                          ('Remove', call_on_species(remove_callback))]

def species_markup_func(species):
    '''
    '''
    # TODO: add (syn) after species name if there are species synonyms that
    # refer to the id of this plant
    if len(species.vernacular_names) > 0:
        substring = '%s -- %s' % \
                    (species.genus.family, \
                     ', '.join([str(v) for v in species.vernacular_names]))
    else:
        substring = '%s' % species.genus.family    
    return species.markup(authors=False), substring


def vernname_get_children(vernname):
    '''
    '''
    return vernname.species.accessions


def vernname_markup_func(vernname):
    '''
    '''    
    return str(vernname), vernname.species.markup(authors=False)
    

''' 
Species table (species)

sp_hybrid
---------
H -- A hybrid formula for an Interspecific hybrid
x -- A Nothotaxon name for an Interspecific hybrid
+ -- An Interspecific graft hybrid or graft chimaera

sp_qual
-------
agg. -- An aggregate species
s. lat. -- aggregrate species (sensu lato)
s. str. -- segregate species (sensu stricto)

infrasp_rank
------------
subsp. -- subspecies
var. -- variety
subvar. -- sub variety
f. -- form
subf. -- subform
cv. -- cultivar

id_qual
---------
aff. -- Akin to or bordering
cf. -- compare with
Incorrect -- Incorrect
forsan -- Perhaps
near -- Close to
? -- Questionable

'''
        
# TODO: there is a trade_name column but there's no support yet for editing
# the trade_name or for using the trade_name when building the string
# for the species, for more information about trade_names see, 
# http://www.hortax.org.uk/gardenplantsnames.html

species_table = Table('species', 
                      Column('id', Integer, primary_key=True),
                      Column('sp', String(64), nullable=False, index=True),
                      Column('sp_author', Unicode(128)),
                      Column('sp_hybrid', Enum(values=['x', '+', 'H', None],
                                               empty_to_none=True)),
                      Column('sp_qual', Enum(values=['agg.', 's. lat.', 
                                                     's. str.', None], 
                                                     empty_to_none=True)),
                      Column('cv_group', Unicode(50)),
                      Column('trade_name', Unicode(64)), 
                      Column('infrasp', Unicode(50)),
                      Column('infrasp_author', Unicode(255)),
                      Column('infrasp_rank', Enum(values=['subsp.', 'var.', 
                                                          'subvar.', 'f.', 
                                                         'subf.', 'cv.', None],
                                                  empty_to_none=True)),
                      Column('notes', Unicode),
                      Column('genus_id', Integer, ForeignKey('genus.id'), 
                             nullable=False),
                      Column('_created', DateTime,
                             default=func.current_timestamp()),
                      Column('_last_updated', DateTime,
                             default=func.current_timestamp(), 
                             onupdate=func.current_timestamp()),
                      UniqueConstraint('sp', 'sp_author', 'sp_hybrid',
                                       'sp_qual', 'cv_group', 'trade_name',
                                       'infrasp', 'infrasp_author',
                                       'infrasp_rank', 'genus_id',
                                       name='species_index'))

class Species(bauble.BaubleMapper):    
            
    def __str__(self):
        '''
        returns a string representation of this speccies, 
        calls Species.str(self)
        '''
        # we'll cache the str(self) since building it is relatively heavy
        # TODO: we can't enable this until we can invalidated _cached_str in
        # cache self is changed
        #if self.__cached_str is None:
        #    self.__cached_str = Species.str(self)
        #return self.__cached_str        
        return Species.str(self)

##     def distribution_str(self):
##         if self.distribution is None:
##             return ''
##         else:
##             ','.join(self.distributon)
        

##     def _get_distribution(self):
##         debug('entered Species._get_distribution()')
##         dist = self._distribution
##         debug('dist: %s' % dist)
##         return [d.distribution for d in dist]
##     distribution = property(_get_distribution)

    
#    def _get_default_vernacular_name(self):
#        return object_session(self).query(VernacularName).get_by(id=self.default_vernacular_name_id)
#    def _set_default_vernacular_name(self, vn):
#        if not isinstance(vn, VernacularName):
#            raise AssertionError('_set_default_vernacular_name expects a '\
#                                 'VernacularName instance')
#        debug('_set_default_vernacular_name: %s' % vn)
#        self.default_vernacular_name_id = vn.id
#    default_vernacular_name = property(_get_default_vernacular_name,
#                                       _set_default_vernacular_name)
    
    def markup(self, authors=False):
        '''
        returns this object as a string with markup
        
        @param authors: flag to toggle whethe the author names should be
        included
        '''
        return Species.str(self, authors, True)
    
    
    @staticmethod
    def str(species, authors=False, markup=False):
        '''
        returns a string for species
        
        @param species: the species object to get the values from
        @param authors: flags to toggle whether the author names should be
        included
        @param markup: flags to toggle whether the returned text is marked up
        to show italics on the epithets
        '''
        #genus = str(species.genus)
        # TODO: the Genus->Species one_to_many relationship should have created
        # a backref to genus in species but it doesn't seem to work
        #genus = str(Genus.get_by(id=species.genus_id))
        genus = str(species.genus)
        sp = species.sp
        if markup:
            italic = "<i>%s</i>"            
            #genus = italic % species.genus
            genus = italic % genus
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
                                    species.infrasp, isp_author] \
                        if s is not None]
            else:
                name = [s for s in [genus, species.sp_hybrid, sp, author] \
                        if s is not None]
        else: # isn't a hybrid
            if species.cv_group:
                if species.infrasp is None:
                    cv = None
                    group = '%s Group' % species.cv_group
                else:
                    cv = "'%s'" % species.infrasp
                    group = '(%s Group)' % species.cv_group
                name = [s for s in [genus, sp, author, group, cv, isp_author] \
                        if s is not None]
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
                    
        if species.sp_qual is not None:
            name.append(species.sp_qual)
        return ' '.join(name)        
    


# TODO: deleting either of the species this synonym refers to makes
# this synonym irrelevant
species_synonym_table = Table('species_synonym',
                              Column('id', Integer, primary_key=True),
                              Column('species_id', Integer, 
                                     ForeignKey('species.id'), nullable=False),
                              Column('synonym_id', Integer, 
                                     ForeignKey('species.id'), nullable=False),
                              Column('_created', DateTime,
                                     default=func.current_timestamp()),
                              Column('_last_updated', DateTime,
                                     default=func.current_timestamp(), 
                                     onupdate=func.current_timestamp()),
                              UniqueConstraint('species_id', 'synonym_id',
                                               name='species_synonym_index'))
    
class SpeciesSynonym(bauble.BaubleMapper):
    
    def __str__(self):
        return str(self.synonym)
    
       
"""
Vernacular name table (vernacular_name)

name: the vernacular name
language: language is free text and could include something like UK or US to 
identify the origin of the name
species_id: key to the species this vernacular name refers to
"""
vernacular_name_table = Table('vernacular_name',
                              Column('id', Integer, primary_key=True),
                              Column('name', Unicode(128), nullable=False),
                              Column('language', Unicode(128)),
                              Column('species_id', Integer, 
                                     ForeignKey('species.id'), nullable=False),
                              Column('_created', DateTime,
                                     default=func.current_timestamp()),
                              Column('_last_updated', DateTime,
                                     default=func.current_timestamp(), 
                                     onupdate=func.current_timestamp()),
                              UniqueConstraint('name', 'language',
                                               'species_id', name='vn_index'))
                                     
class VernacularName(bauble.BaubleMapper):

    def __init__(self, species_or_id=None, name=None, language=None):
        #assert(species is not None and name is not None)
        if isinstance(species_or_id, int):
            self.species_id = species_or_id
        else:            
            self.species = species_or_id
        self.name = name
        self.language = language
        
    def __str__(self):
        return self.name


''' 
Default Vernacular Name table(default_vernacular_name)

species_id:
vernacular_name_id:
'''
default_vernacular_name_table = Table('default_vernacular_name',
                                      Column('id', Integer, primary_key=True),
                                      Column('species_id', Integer, 
                                             ForeignKey('species.id'),
                                             nullable=False),
                                      Column('vernacular_name_id', Integer, 
                                             ForeignKey('vernacular_name.id'),
                                             nullable=False),
                                      Column('_created', DateTime,
                                             default=func.current_timestamp()),
                                      Column('_last_updated', DateTime,
                                            default=func.current_timestamp(), 
                                            onupdate=func.current_timestamp()),
                                      UniqueConstraint('species_id',
                                                       'vernacular_name_id',
                                                      name='default_vn_index'))

class DefaultVernacularName(bauble.BaubleMapper):
    
    def __init__(self, species=None, vernacular_name=None):
        self.species = species
        self.vernacular_name = vernacular_name
        
    def __str__(self):
        # TODO: i can't decide which one of these i should stick with
        return str(self.vernacular_name)
        #return '%s (default)' % str(self.vernacular_name)


species_distribution_table = Table('species_distribution',
                                   Column('id', Integer, primary_key=True),
                                   Column('geography_id', Integer,
                                        ForeignKey('geography.id'),
                                          nullable=False),
                                   Column('species_id', Integer,
                                          ForeignKey('species.id'),
                                          nullable=False),
                                   Column('_created', DateTime,
                                          default=func.current_timestamp()),
                                   Column('_last_updated', DateTime,
                                          default=func.current_timestamp(), 
                                          onupdate=func.current_timestamp()))


class SpeciesDistribution(bauble.BaubleMapper):

    def __init__(self, geography):
        self.geography = geography

        
    def __str__(self):
        return str(self.geography)

##
## mappers
##


# map species synonym
mapper(SpeciesSynonym, species_synonym_table,
    properties = {'synonym':
                  relation(Species, uselist=False,
                           primaryjoin=species_synonym_table.c.synonym_id==species_table.c.id),
                  'species':
                  relation(Species, uselist=False, 
                           primaryjoin=species_synonym_table.c.species_id==species_table.c.id)
                  })

# map vernaculuar name 
mapper(VernacularName, vernacular_name_table)

# map default vernacular name
mapper(DefaultVernacularName, default_vernacular_name_table,
   properties = {'vernacular_name':
                 relation(VernacularName,
                          primaryjoin=default_vernacular_name_table.c.vernacular_name_id==vernacular_name_table.c.id,
                          uselist=False)
                 }
       )

# map species distribution
mapper(SpeciesDistribution, species_distribution_table,
   properties = {'geography':
                 relation(Geography,
                          primaryjoin=species_distribution_table.c.geography_id==geography_table.c.id,
                          uselist=False)})


# map species
species_mapper = mapper(Species, species_table, 
   properties = {'synonyms':
                 relation(SpeciesSynonym, 
                          primaryjoin=species_table.c.id==species_synonym_table.c.species_id,                                          
                          cascade='all, delete-orphan'),
                 'vernacular_names':
                 relation(VernacularName, 
                          primaryjoin=species_table.c.id==vernacular_name_table.c.species_id, 
                          cascade='all, delete-orphan',
                          backref=backref('species', uselist=False)),
                 'default_vernacular_name':
                 relation(DefaultVernacularName, uselist=False,
                          cascade='all, delete-orphan', lazy=False,
                          backref='species'),
                 'distribution':
                 relation(SpeciesDistribution,
                          cascade='all, delete-orphan'),
                          #backref=backref('species', uselist=False))
                 },
    order_by=[species_table.c.sp, species_table.c.sp_author, 
              species_table.c.infrasp_rank,species_table.c.infrasp])

try:
    # in case the garden plugin doesn't exist
    from bauble.plugins.garden.accession import Accession, accession_table
    species_mapper.add_property('accessions', 
        relation(Accession,
                 primaryjoin=species_table.c.id==accession_table.c.species_id,
                 backref=backref('species', uselist=False, lazy=False)))
except:
    debug(traceback.format_exc())
    debug('Could not add accessions relation to species mapper')
