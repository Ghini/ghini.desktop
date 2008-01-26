#
# species_model.py
#

import traceback
import gtk
import xml.sax.saxutils as sax
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.orm.session import object_session
from sqlalchemy.ext.associationproxy import association_proxy
import bauble
import bauble.utils as utils
from bauble.i18n import *
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

species_table = \
    bauble.Table('species', bauble.metadata,
          Column('id', Integer, primary_key=True),
          Column('sp', String(64), nullable=False, index=True),
          Column('sp_author', Unicode(128)),
          Column('sp_hybrid', Enum(values=['x', '+', 'H', None],
                                   empty_to_none=True)),
          Column('sp_qual', Enum(values=['agg.', 's. lat.', 's. str.', None],
                                 empty_to_none=True)),
          Column('cv_group', Unicode(50)),
          Column('trade_name', Unicode(64)),
          Column('infrasp', Unicode(50)),
          Column('infrasp_author', Unicode(255)),
          Column('infrasp_rank', Enum(values=['subsp.', 'var.',
                                              'subvar.', 'f.',
                                              'subf.', 'cv.', None],
                                      empty_to_none=True)),
          Column('notes', UnicodeText),
          Column('genus_id', Integer, ForeignKey('genus.id'), nullable=False),
          UniqueConstraint('sp', 'sp_author', 'sp_hybrid', 'sp_qual',
                           'cv_group', 'trade_name', 'infrasp',
                           'infrasp_author', 'infrasp_rank', 'genus_id',
                           name='species_index'))



class Species(bauble.BaubleMapper):

    synonyms = association_proxy('_synonyms', 'synonym')

    def __str__(self):
        '''
        returns a string representation of this species,
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
        if self._default_vernacular_name is None:
            return None
        return self._default_vernacular_name.vernacular_name
    def _set_default_vernacular_name(self, vn):
        if vn not in self.vernacular_names:
            self.names.append(vn)
        if self._default_vernacular_name is not None:
            utils.delete_or_expunge(self._default_vernacular_name)

        d = DefaultVernacularName()
        d.vernacular_name = vn
        self._default_vernacular_name = d
##     def _del_default_vernacular_name(self):
##         """
##         deleting the default vernacular name only removes the vernacular as
##         the default and doesn't do anything to the vernacular name was the
##         default
##         """
##         del self._default_vernacular_name
    default_vernacular_name = property(_get_default_vernacular_name,
                                       _set_default_vernacular_name)
#                                       _del_default_vernacular_name)


    def distribution_str(self):
        if self.distribution is None:
            return ''
        else:
            dist = ['%s' % d for d in self.distribution]
            return unicode(', ').join(sorted(dist))


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
        infrasp = species.infrasp
        if markup:
            italic = u'<i>%s</i>'
            #genus = italic % species.genus
            genus = italic % utils.xml_safe_utf8(genus)
            if sp is not None: # shouldn't really be allowed
                sp = italic % species.sp
            # the infrasp italic is handled below
            #escape = sax.escape
            escape = utils.xml_safe_utf8
            if species.infrasp_rank not in (u'cv.', 'cv.'):
                infrasp = italic % species.infrasp
        else:
            italic = u'%s'
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
                if species.infrasp_rank is None:
                    name = [s for s in [genus, sp, author, species.sp_hybrid,
                                        infrasp, isp_author] \
                                if s is not None]
                elif species.infrasp_rank in (u'cv.', 'cv.'):
                    if species.cv_group:
                        cv = "(%s Group) '%s'" % \
                            (species.cv_group, infrasp)
                    else:
                        cv = "'%s'" % infrasp
                    name = [s for s in [genus, species.sp_hybrid, sp, author,
                                        cv, isp_author] \
                                if s is not None]
                else:
                    name = [s for s in [genus, species.sp_hybrid, sp, author,
                                        species.infrasp_rank, infrasp,
                                        isp_author] \
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
                    cv = "'%s'" % infrasp
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
                        #isp = italic % species.infrasp
                        isp = infrasp
                name = [s for s in [genus, sp, author, isp_rank, isp,
                                    isp_author] if s is not None]

        if species.sp_qual is not None:
            name.append(species.sp_qual)
#        print name
        return u' '.join(name)




# TODO: deleting either of the species this synonym refers to makes
# this synonym irrelevant
species_synonym_table = \
    bauble.Table('species_synonym', bauble.metadata,
          Column('id', Integer, primary_key=True),
          Column('species_id', Integer, ForeignKey('species.id'),
                 nullable=False),
          Column('synonym_id', Integer, ForeignKey('species.id'),
                 nullable=False),
          UniqueConstraint('species_id', 'synonym_id',
                           name='species_synonym_index'))



class SpeciesSynonym(bauble.BaubleMapper):

    def __init__(self, species=None):
        """
        @param species: a Species object that will be used as the synonym
        """
        self.synonym = species


    def __str__(self):
        return str(self.synonym)


"""
Vernacular name table (vernacular_name)

name: the vernacular name
language: language is free text and could include something like UK or US to
identify the origin of the name
species_id: key to the species this vernacular name refers to
"""
vernacular_name_table = bauble.Table('vernacular_name', bauble.metadata,
                              Column('id', Integer, primary_key=True),
                              Column('name', Unicode(128), nullable=False),
                              Column('language', Unicode(128)),
                              Column('species_id', Integer,
                                     ForeignKey('species.id'), nullable=False),
                              UniqueConstraint('name', 'language',
                                               'species_id', name='vn_index'))

class VernacularName(bauble.BaubleMapper):

    def __init__(self, species_or_id=None, name=None, language=None):
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
default_vernacular_name_table = bauble.Table('default_vernacular_name',
                                             bauble.metadata,
                                      Column('id', Integer, primary_key=True),
                                      Column('species_id', Integer,
                                             ForeignKey('species.id'),
                                             nullable=False),
                                      Column('vernacular_name_id', Integer,
                                             ForeignKey('vernacular_name.id'),
                                             nullable=False),
                                      UniqueConstraint('species_id',
                                                       'vernacular_name_id',
                                                      name='default_vn_index'))


class DefaultVernacularName(bauble.BaubleMapper):

    def __init__(self, species=None, vernacular_name=None):
        self.species = species
        self.vernacular_name = vernacular_name


    def __str__(self):
        return str(self.vernacular_name)



species_distribution_table = \
    bauble.Table('species_distribution', bauble.metadata,
          Column('id', Integer, primary_key=True),
          Column('geography_id', Integer, ForeignKey('geography.id'),
                 nullable=False),
          Column('species_id', Integer, ForeignKey('species.id'),
                 nullable=False))


class SpeciesDistribution(bauble.BaubleMapper):

    def __init__(self, geography):
        self.geography = geography


    def __str__(self):
        return str(self.geography)



# map species synonym
mapper(SpeciesSynonym, species_synonym_table,
    properties = \
       {'synonym':
        relation(Species, uselist=False,
            primaryjoin=species_synonym_table.c.synonym_id==species_table.c.id),
                  })

# map vernaculuar name
mapper(VernacularName, vernacular_name_table)


# map default vernacular name
mapper(DefaultVernacularName, default_vernacular_name_table,
     properties = \
        {'vernacular_name':
         relation(VernacularName, uselist=False,
                  backref=backref('__defaults', cascade='all, delete-orphan')
                  )})


# map species distribution
mapper(SpeciesDistribution, species_distribution_table,
    properties = \
       {'geography':
        relation(Geography,
                 primaryjoin=species_distribution_table.c.geography_id==geography_table.c.id,
                 uselist=False)})


# map species
species_mapper = mapper(Species, species_table,
    properties = \
        {'_synonyms':
         relation(SpeciesSynonym,
            primaryjoin=species_table.c.id==species_synonym_table.c.species_id,
            cascade='all, delete-orphan', uselist=True, backref='species'),
         'vernacular_names':
         relation(VernacularName, cascade='all, delete-orphan',
                  backref=backref('species', uselist=False)),
         '_default_vernacular_name':
         relation(DefaultVernacularName, uselist=False,
                  cascade='all, delete-orphan',
                  backref=backref('species', uselist=False)),
         'distribution':
         relation(SpeciesDistribution,
                  cascade='all, delete-orphan',
                  backref=backref('species', uselist=False))
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
