#
# species_model.py
#

import traceback
import xml.sax.saxutils as sax
from sqlalchemy import *
from sqlalchemy.orm.session import object_session
import bauble
import bauble.utils as utils
from bauble.utils.log import log, debug
from bauble.types import Enum

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

# TODO: the callbacks on a vernacular name should be the same as for a species
# so that the two act more or less the same, they could even use the same 
# infobox if they don't already, and the same children expander, maybe the 
# markup for the search result should have be formatted like Name (Genus sp.)

def edit_callback(row):
    value = row[0]
    from bauble.plugins.plants.species_editor import SpeciesEditor
    # TODO: the select paramater can go away when we move FamilyEditor to the 
    # new style editors    
    #e = SpeciesEditor(select=[value], model=value)
    e = SpeciesEditor(value)
    return e.start() != None


def add_accession_callback(row):
    from bauble.plugins.garden.accession import AccessionEditor
    value = row[0]
    e = AccessionEditor(model_or_defaults={'species_id': value.id})
    return e.start() != None


def remove_callback(row):
    value = row[0]
    s = '%s: %s' % (value.__class__.__name__, str(value))
    msg = "Are you sure you want to remove %s?" % s

    try:
        bauble.app.db_engine.echo=True
        species_table.delete(species_table.c.id==value.id).execute()
        bauble.app.db_engine.echo=False
    except:
        debug(traceback.format_exc())
    return True
#    if utils.yes_no_dialog(msg):
#        from sqlobject.main import SQLObjectIntegrityError
#        try:
#            value.destroySelf()
#            # since we are doing everything in a transaction, commit it
#            sqlhub.processConnection.commit() 
#            return True
#            #self.refresh_search()                
#        except SQLObjectIntegrityError, e:
#            msg = "Could not delete '%s'. It is probably because '%s' "\
#                  "still has children that refer to it.  See the Details for "\
#                  " more information." % (s, s)
#            utils.message_details_dialog(msg, str(e))
#        except:
#            msg = "Could not delete '%s'. It is probably because '%s' "\
#                  "still has children that refer to it.  See the Details for "\
#                  " more information." % (s, s)
#            utils.message_details_dialog(msg, traceback.format_exc())
    

species_context_menu = [('Edit', edit_callback),
                       ('--', None),
                       ('Add accession', add_accession_callback),
                       ('--', None),
                       ('Remove', remove_callback)]


def species_markup_func(species):
    '''
    '''    
    return species.markup(authors=False)
    debug(repr(species))
    #debug(species.genus)
    debug(species.relations)
    debug(species.c)    
    #return '%s %s' % (species.genus_id, species.sp)
    #debug(Genus.get_by(id=species.genus_id))
    return '%s %s' % (Genus.get_by(id=species.genus_id), species.sp)


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
# TODO: create an index from sp_hybrid, sp_qual, sp, sp_author, cv_group, 
        # isp, isp_author, isp_rank, genus
        #species_index = DatabaseIndex('genus', 'sp', 'sp_author', 'sp_hybrid', 
        #                             'sp_qual', 'cv_group', 'infrasp', 
        #                             'infrasp_author', 'infrasp_rank')
# TODO: add trade_name for better support for cultivated plants
        # see http://www.hortax.org.uk/gardenplantsnames.html
        #trade_name = StringCol(length=50, default=None)    # cultivar group                        
        #trade_name = column(Unicode(64))
# FIXME: what happens to the value in default_vernacular_name if 
        # we delete the object that this foreign key points to, should somehow
        # get reset to None....in general we need to fix cascading
species_table = Table('species', 
                      Column('id', Integer, primary_key=True),
                      Column('sp', String(64), nullable=False, 
                             unique='species_index'),
                      Column('sp_author', Unicode(128), unique='species_index'),
                      Column('sp_hybrid', Enum(values=['x', '+', 'H', None],
                                               empty_to_none=True), 
                             unique='species_index'),
                      Column('sp_qual', Enum(values=['agg.', 's. lat.', 
                                                     's. str.', None]), 
                             unique='species_index'),
                      Column('cv_group', Unicode(50), unique='species_index'),
                      Column('infrasp', Unicode(50), unique='species_index'),
                      Column('infrasp_author', Unicode(255), 
                             unique='species_index'),
                      #Column('infrasp_rank', String(8), unique='species_index'),
                      Column('infrasp_rank', Enum(values=['subsp.', 'var.', 
                                                          'subvar.', 'f.', 
                                                          'subf.', 'cv.', None],
                                                  empty_to_none=True), 
                                                  unique='species_index'),
                      Column('id_qual', Enum(values=['aff.', 'cf.', 'Incorrect', 
                                             'forsan', 'near', '?', None],
                                             empty_to_none=True)),
                      Column('notes', Unicode),
                      Column('genus_id', Integer, ForeignKey('genus.id'), 
                             nullable=False),
                      Column('default_vernacular_name_id', Integer))#, ForeignKey('vernacular_name.id')))
#                      ForeignKeyConstraint(['default_vernacular_name_id'],
#                                           ['vernacular_name.id']))
#                      Column('default_vernacular_name_id', Integer, 
#                             ForeignKey('vernacular_name.id')))
    
#class Species(object):
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
    
    def _get_default_vernacular_name(self):
        return object_session(self).query(VernacularName).get_by(id=self.default_vernacular_name_id)
    def _set_default_vernacular_name(self, vn):
        if not isinstance(vn, VernacularName):
            raise AssertionError('_set_default_vernacular_name expects a '\
                                 'VernacularName instance')
        self.default_vernacular_name_id = vn.id
    default_vernacular_name = property(_get_default_vernacular_name,
                                       _set_default_vernacular_name)

    
    def markup(self, authors=False):
        '''
        returns this object as a string with markup
        
        @param authors: flag to toggle whethe the author names should be included
        '''
        return Species.str(self, authors, True)
    
    
    @staticmethod
    def str(species, authors=False, markup=False):
        '''
        returns a string for species
        
        @param species: the species object to get the values from
        @param authors: flags to toggle whether the author names should be included
        @param markup: flags to toggle whether the returned text is marked up to show
            italics on the epithets
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
                                     ForeignKey('species.id'), nullable=False))
    
class SpeciesSynonym(object):
    
    def __str__(self):
        #return '(%s)' % object_session(Species.get_by(id=self.species)
        return str(self.species)
    


'''
a table to hold meta information abot a species, such as it's distributions
and where it is edible or poisonous

poison_humans: whether this plant is poisonous to humans
poison_animals: whether this plant is poisonous to animals    
edible: whether this plant is considered edible
distribution: the natural distribution of this plant, string from TDWG WGS...
species_id: the species this meta information refers to
'''
# TODO: poison_humans should imply food_plant false or whatever value
#     is meant to be in food_plant
# TODO: create distribution table that holds one of each of the 
#     geography tables which will hold the plants distribution, this
#     distribution table could even be part of the geography module

# UPDATE: it might be better to do something like the source_type in the 
#     the accessions, do we need the distribution table if we're only
#     going to be holding one of the value from continent/region/etc, the only
#     exception is that we also need to hold a cultivated value and possible
#     something like "tropical", we can probably still use the distribution
#     table as long as setting to and from the distribution is handled silently
#distribution = SingleJoin('Distribution', joinColumn='species_id', 
#                           makeDefault=None)
#     right now we'll just include the string from one of the tdwg 
#     plant distribution tables though in the future it would be good
#     to have a SingleJoin to a distribution table so we get the extra
#     benefit of things like iso codes and hierarchial data, e.g. get
#     all plants from africa
# TODO: fix cascading
#     species = ForeignKey('Species', default=None, cascade=True)
species_meta_table = Table('species_meta',
                           Column('id', Integer, primary_key=True),
                           Column('poison_humans', Boolean),
                           Column('poison_animals', Boolean),
                           Column('food_plant', Boolean),
                           Column('distribution', Unicode(255)),
                           Column('species_id', Integer, 
                                  ForeignKey('species.id'), nullable=False))
                           
class SpeciesMeta(object):    
        
    def __str__(self):
        '''
        @returns: the string the representation of this meta info,
            e.g. Cultivated, Food, Poisonous, Poisonous to animals
        '''
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
       
'''
Vernacular name table (vernacular_name)

name: the vernacular name
language: language is free text and could include something like UK or US to 
identify the origin of the name
species_id: key to the species this vernacular name refers to
''' 
vernacular_name_table = Table('vernacular_name',
                              Column('id', Integer, primary_key=True),
                              Column('name', Unicode(128), unique='vn_index', nullable=False),
                              Column('language', Unicode(128), unique='vn_index'),
#                              Column('species_id', Integer, ForeignKey('species.id')),
#                              ForeignKeyConstraint(['species_id'], ['species.id']))
                              Column('species_id', Integer, 
                                     ForeignKey('species.id'), unique='vn_index', nullable=False))
                                     
class VernacularName(object):

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


mapper(SpeciesSynonym, species_synonym_table,
       properties = {'synonym': relation(Species, uselist=False,
                                         primaryjoin = species_synonym_table.c.synonym_id==species_table.c.id)})
mapper(VernacularName, vernacular_name_table)
mapper(SpeciesMeta, species_meta_table)

species_mapper = mapper(Species, species_table, 
       properties = {'species_meta': relation(SpeciesMeta, backref='species', 
                                              uselist=False, cascade='all, delete-orphan'),
                     'synonyms': relation(SpeciesSynonym, 
                                          primaryjoin = species_synonym_table.c.species_id==species_table.c.id,
                                          backref='species', 
                                          cascade='all, delete-orphan'),
                     'vernacular_names': relation(VernacularName, 
                                                  primaryjoin=vernacular_name_table.c.species_id==species_table.c.id, 
                                                  backref='species', 
                                                  cascade='all, delete-orphan'),
#                     'default_vernacular_name': relation(VernacularName, 
#                                                         primaryjoin=species_table.c.default_vernacular_name_id==vernacular_name_table.c.id,
#                                                         cascade='all, delete-orphan',
#                                                         uselist=False),
                     },

       order_by=[species_table.c.sp, species_table.c.sp_author, 
                 species_table.c.infrasp_rank,species_table.c.infrasp])

#species_mapper.add_property('synonyms', relation(SpeciesSynonym, 
#         primaryjoin = species_synonym_table.c.species_id==species_table.c.id,
#         backref='species'))


try:
    from bauble.plugins.garden.accession import Accession
    species_mapper.add_property('accessions', relation(Accession, 
                        backref=backref('species', uselist=False, lazy=False)))
except:
    debug('Could not add accessions relation to species mapper')


       
##
## Species table
##
#class Species2(BaubleTable):
#    
#    def __init__(self, **kw):
#        super(Species, self).__init__(**kw)
#        self.__cached_str = None
#
#    class mapping:
#        #defaultOrder = 'sp'
#        id = column(Integer, primary_key=True)
#        # TODO: create an index from sp_hybrid, sp_qual, sp, sp_author, cv_group, 
#        # isp, isp_author, isp_rank, genus
#        #species_index = DatabaseIndex('genus', 'sp', 'sp_author', 'sp_hybrid', 
#        #                             'sp_qual', 'cv_group', 'infrasp', 
#        #                             'infrasp_author', 'infrasp_rank')
#        sp = column(Unicode(40), nullable=False) # specific epithet
#        #sp = StringCol(length=40, notNull=True)          
#        
#        sp_author = column(Unicode)
#        #sp_author = UnicodeCol(default=None)  # species author    
#        
#        ''' 
#        sp_hybrid
#        ---------
#        H -- A hybrid formula for an Interspecific hybrid
#        x -- A Nothotaxon name for an Interspecific hybrid
#        + -- An Interspecific graft hybrid or graft chimaera
#        '''
#        sp_hybrid = column(String)
#        #sp_hybrid = EnumCol(enumValues=("H", "x", "+",None), default=None)     
#        
#        '''
#        sp_qual
#        -------
#        agg. -- An aggregate species
#        s. lat. -- aggregrate species (sensu lato)
#        s. str. -- segregate species (sensu stricto)
#        '''
#        sp_qual = column(String)
##        sp_qual = EnumCol(enumValues=("agg.", "s. lat.", "s. str.", None), 
##                          default=None)                                    
#        
#        # TODO: add trade_name for better support for cultivated plants
#        # see http://www.hortax.org.uk/gardenplantsnames.html
#        #trade_name = StringCol(length=50, default=None)    # cultivar group                        
#        #trade_name = column(Unicode(64))
#
#    
#        cv_group = column(Unicode(50))
#        infrasp = column(Unicode(50))
#        infrasp_author = column(Unicode(255))
##        cv_group = StringCol(length=50, default=None)    # cultivar group                        
##        infrasp = StringCol(length=30, default=None)         # intraspecific epithet
##        infrasp_author = UnicodeCol(length=255, default=None) # intraspecific author
#        '''
#        infrasp_rank
#        ------------
#        subsp. -- subspecies
#        var. -- variety
#        subvar. -- sub variety
#        f. -- form
#        subf. -- subform
#        cv. -- cultivar
#        '''
#        infrasp_rank = column(String)
##        infrasp_rank = EnumCol(enumValues=("subsp.", "var.", "subvar.", "f.", 
##                                           "subf.",  "cv.", None), default=None)    
#        '''
#        id_qual
#        ---------
#        aff. -- Akin to or bordering
#        cf. -- compare with
#        Incorrect -- Incorrect
#        forsan -- Perhaps
#        near -- Close to
#        ? -- Questionable
#        '''
#        id_qual = column(String)
##        id_qual = EnumCol(enumValues=("aff.", "cf.", "Incorrect", "forsan", "near", 
##                                      "?", None), default=None)    
#
#        notes = column(Unicode)
##        notes = UnicodeCol(default=None)
#        
#        # foreign keys
#        #
#        default_vernacular_name_id = column(Integer, foreign_key=ForeignKey('vernacular_name.id'))
#        #default_vernacular_name = ForeignKey('VernacularName', default=None, cascade='null')
#
#        genus_id = column(Integer, foreign_key=ForeignKey('genus.id'), 
#                          nullable=False)        
#        #genus = ForeignKey('Genus', notNull=True, cascade=False)
#        
#    
#        # joins
#        #
#        # hold meta information about this plant
#        species_meta = one_to_one('SpeciesMeta', colname='species_id', 
#                                  backref='species')
#        #species_meta = SingleJoin('SpeciesMeta', joinColumn='species_id')
#        
#        synonyms = one_to_many('SpeciesSynonym', colname='species_id',
#                               backref='species')
#        #synonyms = MultipleJoin('SpeciesSynonym', joinColumn='species_id')
#        # it would be best to display the vernacular names in a dropdown list
#        # with a way to add to the list    
#        # FIXME: what happens to the value in default_vernacular_name if 
#        # we delete the object that this foreign key points to, should somehow
#        # get reset to None        
#        vernacular_names = one_to_many('VernacularName', colname='species_id', 
#                                       backref='species')
#        #vernacular_names = MultipleJoin('VernacularName', joinColumn='species_id')
#        #accessions = MultipleJoin('Accessions', joinColumn='species_id')
#        #images = MultipleJoin('Images', joinColumn='species_id')
#        #references = MultipleJoin('Reference', joinColumn='species_id')
#
#        # TODO: this requires the accession table which is in a different 
#        # plugin, will this cause a problem        
#        accessions = one_to_many('Accession', colname='species_id', 
#                                 backref='species')
#                
#    
#    def __str__(self):
#        '''
#        returns a string representation of this speccies, 
#        calls Species.str(self)
#        '''
#        # we'll cache the str(self) since building it is relatively heavy
#        # TODO: we can't enable this until we can invalidated _cached_str in
#        # cache self is changed
#        #if self.__cached_str is None:
#        #    self.__cached_str = Species.str(self)
#        #return self.__cached_str        
#        return Species.str(self)
#    
#    
#    def markup(self, authors=False):
#        '''
#        returns this object as a string with markup
#        
#        @param authors: flag to toggle whethe the author names should be included
#        '''
#        return Species.str(self, authors, True)
#    
#    
#    @staticmethod
#    def str(species, authors=False, markup=False):
#        '''
#        returns a string for species
#        
#        @param species: the species object to get the values from
#        @param authors: flags to toggle whether the author names should be included
#        @param markup: flags to toggle whether the returned text is marked up to show
#            italics on the epithets
#        '''
#        #genus = str(species.genus)
#        # TODO: the Genus->Species one_to_many relationship should have created
#        # a backref to genus in species but it doesn't seem to work
#        genus = str(Genus.get_by(id=species.genus_id))
#        sp = species.sp
#        if markup:
#            italic = "<i>%s</i>"            
#            #genus = italic % species.genus
#            genus = italic % genus
#            if sp is not None: # shouldn't really be allowed
#                sp = italic % species.sp
#            # the infrasp italic is handled below
#            escape = sax.escape
#        else:
#            italic = "%s"
#            escape = lambda x: x
#            
#        author = None
#        isp_author = None                        
#        if authors:
#            if species.sp_author:
#                author = escape(species.sp_author)
#            if species.infrasp_author:            
#                isp_author = escape(species.infrasp_author)
#                    
#        if species.sp_hybrid: # is a hybrid
#            if species.infrasp is not None:                    
#                name = [s for s in [genus, sp, author, species.sp_hybrid, 
#                                    species.infrasp, isp_author] if s is not None]
#            else:
#                name = [s for s in [genus, species.sp_hybrid, sp, author] if s is not None]
#        else: # isn't a hybrid
#            if species.cv_group:
#                if species.infrasp is None:
#                    cv = None
#                    group = '%s Group' % species.cv_group
#                else:
#                    cv = "'%s'" % species.infrasp
#                    group = '(%s Group)' % species.cv_group
#                name = [s for s in [genus, sp, author, group, cv, isp_author] if s is not None]
#            else:
#                if species.infrasp is None:
#                    isp = None
#                    isp_rank = None
#                else:
#                    if species.infrasp_rank == 'cv.':
#                        isp_rank = None                    
#                        isp = "'%s'" % (species.infrasp or '')
#                    else:
#                        isp_rank = species.infrasp_rank
#                        isp = italic % species.infrasp
#                name = [s for s in [genus, sp, author, 
#                                    isp_rank, isp, isp_author] if s is not None]
#            
#        
#        if species.sp_qual is not None:
#            name.append(species.sp_qual)
#        return ' '.join(name)        
#            
#
#
#class SpeciesSynonym(BaubleTable):
#    '''
#    a table to hold species synonyms
#    '''
#    # deleting either of the species this synonym refers to makes
#    # this synonym irrelevant
#    species_id = column(Integer, foreign_key=ForeignKey('species.id'))
#    synonym_id = column(Integer, foreign_key=ForeignKey('species.id'))
##    species = ForeignKey('Species', default=None, cascade=True)
##    synonym = ForeignKey('Species', cascade=True)
#    
#    
#    
#class SpeciesMeta(BaubleTable):
#    '''
#    a table to hold meta information abot a species, such as it's distributions
#    and where it is edible or poisonous
#    '''
#    
#    '''
#    whether this plant is poisonous to humans
#    '''
#    poison_humans = unicode(Boolean)
##    poison_humans = BoolCol(default=None)
#    
#    
#    '''
#    whether this plant is poisonous to animals
#    '''
#    poison_animals = unicode(Boolean)
##    poison_animals = BoolCol(default=None)
#    
#    # TODO: poison_humans should imply food_plant false or whatever value
#    # is meant to be in food_plant
#    '''
#    whether this plant is poisonous to considered edible
#    '''
#    food_plant = unicode(Boolean)
##    food_plant = BoolCol(default=None)
#    
#    # TODO: create distribution table that holds one of each of the 
#    # geography tables which will hold the plants distribution, this
#    # distribution table could even be part of the geography module
#
#    # UPDATE: it might be better to do something like the source_type in the 
#    # the accessions, do we need the distribution table if we're only
#    # going to be holding one of the value from continent/region/etc, the only
#    # exception is that we also need to hold a cultivated value and possible
#    # something like "tropical", we can probably still use the distribution
#    # table as long as setting to and from the distribution is handled silently
#    #distribution = SingleJoin('Distribution', joinColumn='species_id', 
#    #                           makeDefault=None)
#    # right now we'll just include the string from one of the tdwg 
#    # plant distribution tables though in the future it would be good
#    # to have a SingleJoin to a distribution table so we get the extra
#    # benefit of things like iso codes and hierarchial data, e.g. get
#    # all plants from africa
#    '''
#    the plants natural distribution
#    '''
##    distribution = UnicodeCol(default=None)
#    distribution = column(Unicode(255))
#    
#    # this should be set by the editor
#    # FIXME: this could be dangerous and cause dangling meta information
#    # - removing the species removes this meta info
#    '''
#    the species this meta information refers to
#    '''    
#    #species = ForeignKey('Species', default=None, cascade=True)
#    species_id = column(Integer, foreign_key=ForeignKey('species.id'))
#    
#    
#    def __str__(self):
#        '''
#        @returns: the string the representation of this meta info,
#            e.g. Cultivated, Food, Poisonous, Poisonous to animals
#        '''
#        v = []
#        if self.distribution is not None:
#            v.append(self.distribution)
#        if self.food_plant is not None and self.food_plant:
#            v.append('Food')
#        if self.poison_humans is not None and self.poison_humans:
#            v.append('Poisonous')
#        if self.poison_animals is not None and self.poison_animals:
#            v.append('Poisonous to animals')            
#        return ','.join(v)
#        
#        
#        
#class VernacularName(BaubleTable):
#    '''
#    a vernacular name for a species
#    '''
#    
#    '''
#    the vernacular name
#    '''
#    name = column(Unicode(64), index='vernname_index')
##    name = UnicodeCol(length=64)
#    
#    '''
#    language is free text and could include something like UK or US to identify
#    the origin of the name
#    '''
#    language = column(Unicode(64), index='vernname_index')
#    #language = UnicodeCol(length=64)    
#    
#    
#    # default=None b/c the VernacularNameEditor can only be invoked from the 
#    # SpeciesEditor and it should set this on commit
#    '''
#    a key to the species this vernacular name refers to
#    '''
#    #species = ForeignKey('Species', default=None, cascade=True)
#    species_id = column(Integer, foreign_key=ForeignKey('species.id'), index='vernname_index')
#
##    index = DatabaseIndex('name', 'language', 'species', unique=True)
#
#    def __str__(self):
#        return self.name

#class Species(BaubleTable):
#
#    class sqlmeta(BaubleTable.sqlmeta):
#        defaultOrder = 'sp'
#    
#    def __init__(self, **kw):
#        super(Species, self).__init__(**kw)
#        self.__cached_str = None
#        
#    # TODO: create an index from sp_hybrid, sp_qual, sp, sp_author, cv_group, 
#    # isp, isp_author, isp_rank, genus
#    #species_index = DatabaseIndex('genus', 'sp', 'sp_author', 'sp_hybrid', 
#    #                             'sp_qual', 'cv_group', 'infrasp', 
#    #                             'infrasp_author', 'infrasp_rank')
#    sp = StringCol(length=40, notNull=True)          # specific epithet
#    sp_author = UnicodeCol(default=None)  # species author    
#    
#    ''' 
#    sp_hybrid
#    ---------
#    H -- A hybrid formula for an Interspecific hybrid
#    x -- A Nothotaxon name for an Interspecific hybrid
#    + -- An Interspecific graft hybrid or graft chimaera
#    '''
#    sp_hybrid = EnumCol(enumValues=("H", "x", "+",None), default=None)     
#    
#    '''
#    sp_qual
#    -------
#    agg. -- An aggregate species
#    s. lat. -- aggregrate species (sensu lato)
#    s. str. -- segregate species (sensu stricto)
#    '''
#    sp_qual = EnumCol(enumValues=("agg.", "s. lat.", "s. str.", None), 
#                      default=None)                                                
#    
#    # TODO: add trade_name for better support for cultivated plants
#    # see http://www.hortax.org.uk/gardenplantsnames.html
#    #trade_name = StringCol(length=50, default=None)    # cultivar group                        
#    
#    cv_group = StringCol(length=50, default=None)    # cultivar group                        
#    infrasp = StringCol(length=30, default=None)         # intraspecific epithet
#    infrasp_author = UnicodeCol(length=255, default=None) # intraspecific author
#    '''
#    infrasp_rank
#    ------------
#    subsp. -- subspecies
#    var. -- variety
#    subvar. -- sub variety
#    f. -- form
#    subf. -- subform
#    cv. -- cultivar
#    '''
#    infrasp_rank = EnumCol(enumValues=("subsp.", "var.", "subvar.", "f.", 
#                                       "subf.",  "cv.", None), default=None)    
#    '''
#    id_qual
#    ---------
#    aff. -- Akin to or bordering
#    cf. -- compare with
#    Incorrect -- Incorrect
#    forsan -- Perhaps
#    near -- Close to
#    ? -- Questionable
#    '''
#    id_qual = EnumCol(enumValues=("aff.", "cf.", "Incorrect", "forsan", "near", 
#                                  "?", None), default=None)    
#    notes = UnicodeCol(default=None)
#    
#    # foreign keys
#    #
#    default_vernacular_name = ForeignKey('VernacularName', default=None, cascade='null')
#    genus = ForeignKey('Genus', notNull=True, cascade=False)
#    
#
#    # joins
#    #
#    # hold meta information about this plant
#    species_meta = SingleJoin('SpeciesMeta', joinColumn='species_id')
#    synonyms = MultipleJoin('SpeciesSynonym', joinColumn='species_id')
#    # it would be best to display the vernacular names in a dropdown list
#    # with a way to add to the list    
#    # FIXME: what happens to the value in default_vernacular_name if 
#    # we delete the object that this foreign key points to, should somehow
#    # get reset to None
#    vernacular_names = MultipleJoin('VernacularName', joinColumn='species_id')
#    #accessions = MultipleJoin('Accessions', joinColumn='species_id')
#    #images = MultipleJoin('Images', joinColumn='species_id')
#    #references = MultipleJoin('Reference', joinColumn='species_id')
#    
#    def __str__(self):
#        '''
#        returns a string representation of this speccies, 
#        calls Species.str(self)
#        '''
#        # we'll cache the str(self) since building it is relatively heavy
#        # TODO: we can't enable this until we can invalidated _cached_str in
#        # cache self is changed
#        #if self.__cached_str is None:
#        #    self.__cached_str = Species.str(self)
#        #return self.__cached_str        
#        return Species.str(self)
#    
#    
#    def markup(self, authors=False):
#        '''
#        returns this object as a string with markup
#        
#        @param authors: flag to toggle whethe the author names should be included
#        '''
#        return Species.str(self, authors, True)
#    
#    
#    @staticmethod
#    def str(species, authors=False, markup=False):
#        '''
#        returns a string for species
#        
#        @param species: the species object to get the values from
#        @param authors: flags to toggle whether the author names should be included
#        @param markup: flags to toggle whether the returned text is marked up to show
#            italics on the epithets
#        '''
#        genus = str(species.genus)
#        sp = species.sp
#        if markup:
#            italic = "<i>%s</i>"            
#            genus = italic % species.genus
#            if sp is not None: # shouldn't really be allowed
#                sp = italic % species.sp
#            # the infrasp italic is handled below
#            escape = sax.escape
#        else:
#            italic = "%s"
#            escape = lambda x: x
#            
#        author = None
#        isp_author = None                        
#        if authors:
#            if species.sp_author:
#                author = escape(species.sp_author)
#            if species.infrasp_author:            
#                isp_author = escape(species.infrasp_author)
#                    
#        if species.sp_hybrid: # is a hybrid
#            if species.infrasp is not None:                    
#                name = [s for s in [genus, sp, author, species.sp_hybrid, 
#                                    species.infrasp, isp_author] if s is not None]
#            else:
#                name = [s for s in [genus, species.sp_hybrid, sp, author] if s is not None]
#        else: # isn't a hybrid
#            if species.cv_group:
#                if species.infrasp is None:
#                    cv = None
#                    group = '%s Group' % species.cv_group
#                else:
#                    cv = "'%s'" % species.infrasp
#                    group = '(%s Group)' % species.cv_group
#                name = [s for s in [genus, sp, author, group, cv, isp_author] if s is not None]
#            else:
#                if species.infrasp is None:
#                    isp = None
#                    isp_rank = None
#                else:
#                    if species.infrasp_rank == 'cv.':
#                        isp_rank = None                    
#                        isp = "'%s'" % (species.infrasp or '')
#                    else:
#                        isp_rank = species.infrasp_rank
#                        isp = italic % species.infrasp
#                name = [s for s in [genus, sp, author, 
#                                    isp_rank, isp, isp_author] if s is not None]
#            
#        
#        if species.sp_qual is not None:
#            name.append(species.sp_qual)
#        return ' '.join(name)        
#            
#
#
#class SpeciesSynonym(BaubleTable):
#    '''
#    a table to hold species synonyms
#    '''
#    # deleting either of the species this synonym refers to makes
#    # this synonym irrelevant
#    species = ForeignKey('Species', default=None, cascade=True)
#    synonym = ForeignKey('Species', cascade=True)
#    
#    
#    
#class SpeciesMeta(BaubleTable):
#    '''
#    a table to hold meta information abot a species, such as it's distributions
#    and where it is edible or poisonous
#    '''
#    
#    '''
#    whether this plant is poisonous to humans
#    '''
#    poison_humans = BoolCol(default=None)
#    
#    '''
#    whether this plant is poisonous to animals
#    '''
#    poison_animals = BoolCol(default=None)
#    
#    # TODO: poison_humans should imply food_plant false or whatever value
#    # is meant to be in food_plant
#    '''
#    whether this plant is poisonous to considered edible
#    '''
#    food_plant = BoolCol(default=None)
#    
#    # TODO: create distribution table that holds one of each of the 
#    # geography tables which will hold the plants distribution, this
#    # distribution table could even be part of the geography module
#
#    # UPDATE: it might be better to do something like the source_type in the 
#    # the accessions, do we need the distribution table if we're only
#    # going to be holding one of the value from continent/region/etc, the only
#    # exception is that we also need to hold a cultivated value and possible
#    # something like "tropical", we can probably still use the distribution
#    # table as long as setting to and from the distribution is handled silently
#    #distribution = SingleJoin('Distribution', joinColumn='species_id', 
#    #                           makeDefault=None)
#    # right now we'll just include the string from one of the tdwg 
#    # plant distribution tables though in the future it would be good
#    # to have a SingleJoin to a distribution table so we get the extra
#    # benefit of things like iso codes and hierarchial data, e.g. get
#    # all plants from africa
#    '''
#    the plants natural distribution
#    '''
#    distribution = UnicodeCol(default=None)
#    
#    # this should be set by the editor
#    # FIXME: this could be dangerous and cause dangling meta information
#    # - removing the species removes this meta info
#    '''
#    the species this meta information refers to
#    '''    
#    species = ForeignKey('Species', default=None, cascade=True)
#    
#    
#    def __str__(self):
#        '''
#        @returns: the string the representation of this meta info,
#            e.g. Cultivated, Food, Poisonous, Poisonous to animals
#        '''
#        v = []
#        if self.distribution is not None:
#            v.append(self.distribution)
#        if self.food_plant is not None and self.food_plant:
#            v.append('Food')
#        if self.poison_humans is not None and self.poison_humans:
#            v.append('Poisonous')
#        if self.poison_animals is not None and self.poison_animals:
#            v.append('Poisonous to animals')            
#        return ','.join(v)
#        
#        
#        
#class VernacularName(BaubleTable):
#    '''
#    a vernacular name for a species
#    '''
#    
#    '''
#    the vernacular name
#    '''
#    name = UnicodeCol(length=64)
#    
#    '''
#    language is free text and could include something like UK or US to identify
#    the origin of the name
#    '''
#    language = UnicodeCol(length=64)    
#    
#    # default=None b/c the VernacularNameEditor can only be invoked from the 
#    # SpeciesEditor and it should set this on commit
#    '''
#    a key to the species this vernacular name refers to
#    '''
#    species = ForeignKey('Species', default=None, cascade=True)
#
#    index = DatabaseIndex('name', 'language', 'species', unique=True)
#
#    def __str__(self):
#        return self.name
    
