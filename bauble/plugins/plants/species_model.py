#
# species_model.py
#

import traceback
import xml.sax.saxutils as sax

import gtk
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.orm.session import object_session
from sqlalchemy.ext.associationproxy import association_proxy

import bauble
import bauble.db as db
import bauble.utils as utils
from bauble.i18n import *
from bauble.utils.log import log, debug
from bauble.types import Enum
from bauble.plugins.plants.geography import Geography#, geography_table


from sqlalchemy.orm.collections import collection

class VNList(list):
    """
    A Collection class for Species.vernacular_names

    This makes it possible to automatically remove a
    default_vernacular_name if the vernacular_name is removed from the
    list.
    """
    def remove(self, vn):
        super(VNList, self).remove(vn)
        try:
            if vn.species.default_vernacular_name == vn:
                del vn.species.default_vernacular_name
        except Exception, e:
            debug(e)

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



# TODO: there is a trade_name column but there's no support yet for editing
# the trade_name or for using the trade_name when building the string
# for the species, for more information about trade_names see,
# http://www.hortax.org.uk/gardenplantsnames.html



class Species(db.Base):
    """
    :Table name: species

    :Columns:
        *sp_hybrid*:
            Hybrid flag

            Possible values:
                H: A hybrid formula for an Interspecific hybrid

                x: A Nothotaxon name for an Interspecific hybrid

                +: An Interspecific graft hybrid or graft chimaera

        *sp_qual*:
            Species qualifier

            Possible values:
                *agg.*: An aggregate species

                *s. lat.*: aggregrate species (sensu lato)

                *s. str.*: segregate species (sensu stricto)

        *infrasp_rank*:
            The infraspecific rank

            Possible values:
                *subsp.*: subspecies

                *variety.*: variety

                *subvar.*: sub variety

                *f.*: form

                *subf.*: subform

                *cv.*: cultivar

        *infrasp*:
            The infraspecific epithet


    :Properties:
        *accessions*:

        *vernacular_names*:

        *default_vernacular_name*:

        *synonyms*:

        *distribution*:

    :Constraints:
        The combination of sp, sp_author, sp_hybrid, sp_qual,
        cv_group, trade_name, infrasp, infrasp_author, infrasp_rank,
        genus_id
    """
    __tablename__ = 'species'
    __table_args__ = (UniqueConstraint('sp', 'sp_author', 'sp_hybrid',
                                        'sp_qual', 'cv_group', 'trade_name',
                                        'infrasp', 'infrasp_author',
                                        'infrasp_rank', 'genus_id',
                                        name='species_index'))
    _mapper_args__ = {'order_by': ['sp', 'sp_author', 'infrasp_rank',
                                   'infrasp']}

    # columns
    sp = Column(Unicode(64), nullable=False, index=True)
    sp_author = Column(Unicode(128))
    sp_hybrid = Column(Enum(values=['x', '+', 'H', '']), default=u'')
    sp_qual = Column(Enum(values=['agg.', 's. lat.', 's. str.', '']),
                     default=u'')
    cv_group = Column(Unicode(50))
    trade_name = Column(Unicode(64))
    infrasp = Column(Unicode(50))
    infrasp_author = Column(Unicode(255))
    infrasp_rank = Column(Enum(values=['subsp.', 'var.', 'subvar.', 'f.',
                                       'subf.', 'cv.', '']), default=u'')
    notes = Column(UnicodeText)
    genus_id = Column(Integer, ForeignKey('genus.id'), nullable=False)

    # relations
    synonyms = association_proxy('_synonyms', 'synonym')
    _synonyms = relation('SpeciesSynonym',
                         primaryjoin='Species.id==SpeciesSynonym.species_id',
                         cascade='all, delete-orphan', uselist=True,
                         backref='species')
    vernacular_names = relation('VernacularName', cascade='all, delete-orphan',
                                 collection_class=VNList,
                                backref=backref('species', uselist=False))
    _default_vernacular_name = relation('DefaultVernacularName', uselist=False,
                                         cascade='all, delete-orphan',
                                         backref=backref('species',
                                                         uselist=False))
    distribution = relation('SpeciesDistribution',
                            cascade='all, delete-orphan',
                            backref=backref('species', uselist=False))


    def __init__(self, *args, **kwargs):
        super(Species, self).__init__(*args, **kwargs)
        self.__cached_str = {}


    @reconstructor
    def init_on_load(self):
        """
        Called instead of __init__() when an Species is loaded from
        the database.
        """
        self.__cached_str = {}


    def __str__(self):
        '''
        returns a string representation of this species,
        calls Species.str(self)
        '''
        return Species.str(self)


    def _get_default_vernacular_name(self):
        if self._default_vernacular_name is None:
            return None
        return self._default_vernacular_name.vernacular_name
    def _set_default_vernacular_name(self, vn):
        if vn is None:
            del self.default_vernacular_name
            return
        if vn not in self.vernacular_names:
            self.vernacular_names.append(vn)
        d = DefaultVernacularName()
        d.vernacular_name = vn
        self._default_vernacular_name = d
    def _del_default_vernacular_name(self):
        utils.delete_or_expunge(self._default_vernacular_name)
        del self._default_vernacular_name
    default_vernacular_name = property(_get_default_vernacular_name,
                                       _set_default_vernacular_name,
                                       _del_default_vernacular_name)

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
    def str(species, authors=False, markup=False, use_cache=True):
        '''
        returns a string for species

        @param species: the species object to get the values from
        @param authors: flags to toggle whether the author names should be
        included
        @param markup: flags to toggle whether the returned text is marked up
        to show italics on the epithets
        '''
        if use_cache:
            try:
                cached = species.__cached_str[(markup, authors)]
            except KeyError:
                species.__cached_str[(markup, authors)] = None
                cached = None
            session = object_session(species)
            if cached is not None and species not in session.dirty:
                return cached

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
                                if s not in (None, '')]
                else:
                    name = [s for s in [genus, species.sp_hybrid, sp, author,
                                        species.infrasp_rank, infrasp,
                                        isp_author] \
                                if s not in (None, '')]
            else:
                name = [s for s in [genus, species.sp_hybrid, sp, author] \
                        if s not in (None, '')]
        else: # isn't a hybrid
            if species.cv_group:
                if species.infrasp is None:
                    cv = None
                    group = '%s Group' % species.cv_group
                else:
                    cv = "'%s'" % infrasp
                    group = '(%s Group)' % species.cv_group
                name = [s for s in [genus, sp, author, group, cv, isp_author] \
                        if s not in (None, '')]
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
                                    isp_author] if s not in (None, '')]

        if species.sp_qual not in (None, ''):
            name.append(species.sp_qual)

        s = u' '.join(name)
        species.__cached_str[(markup, authors)] = s
        return s


# TODO: deleting either of the species this synonym refers to makes
# this synonym irrelevant
class SpeciesSynonym(db.Base):
    """
    :Table name: species_synonym
    """
    __tablename__ = 'species_synonym'
    __table_args__ = (UniqueConstraint('species_id', 'synonym_id',
                                       name='species_synonym_index'))

    # columns
    species_id = Column(Integer, ForeignKey('species.id'),
                        nullable=False)
    synonym_id = Column(Integer, ForeignKey('species.id'),
                        nullable=False)

    # relations
    synonym = relation('Species', uselist=False,
                           primaryjoin='SpeciesSynonym.synonym_id==Species.id')

    def __init__(self, synonym=None, **kwargs):
        # it is necessary that the first argument here be synonym for
        # the Species.synonyms association_proxy to work
        self.synonym = synonym
        super(SpeciesSynonym, self).__init__(**kwargs)

    def __str__(self):
        return str(self.synonym)



class VernacularName(db.Base):
    """
    :Table name: vernacular_name

    :Columns:
        *name*:
            the vernacular name

        *language*:
            language is free text and could include something like UK
            or US to identify the origin of the name

        *species_id*:
            key to the species this vernacular name refers to

    :Properties:

    :Constraints:
    """
    __tablename__ = 'vernacular_name'
    name = Column(Unicode(128), nullable=False)
    language = Column(Unicode(128))
    species_id = Column(Integer, ForeignKey('species.id'), nullable=False)
    __table_args__ = ((UniqueConstraint('name', 'language',
                                        'species_id', name='vn_index')))

    def __str__(self):
        return self.name



class DefaultVernacularName(db.Base):
    """
    :Table name: default_vernacular_name

    DefaultVernacularName is not meant to be instantiated directly.
    Usually the default vernacular name is set on a species by setting
    the default_vernacular_name property on Species to a
    VernacularName instance

    :Columns:
        *id*:
            Integer, primary_key

        *species_id*:
            foreign key to species.id, nullable=False

        *vernacular_name_id*:

    :Properties:

    :Constraints:
    """
    __tablename__ = 'default_vernacular_name'
    __table_args__ = (UniqueConstraint('species_id', 'vernacular_name_id',
                                       name='default_vn_index'),
                      {})

    # columns
    species_id = Column(Integer, ForeignKey('species.id'), nullable=False)
    vernacular_name_id = Column(Integer, ForeignKey('vernacular_name.id'),
                                nullable=False)

    # relations
    vernacular_name = relation(VernacularName, uselist=False)

    def __str__(self):
        return str(self.vernacular_name)


class SpeciesDistribution(db.Base):
    """
    :Table name: species_distribution

    :Columns:

    :Properties:

    :Constraints:
    """
    __tablename__ = 'species_distribution'

    # columns
    geography_id = Column(Integer, ForeignKey('geography.id'), nullable=False)
    species_id = Column(Integer, ForeignKey('species.id'), nullable=False)

    def __str__(self):
        return str(self.geography)

# late bindings
SpeciesDistribution.geography = relation('Geography',
                primaryjoin='SpeciesDistribution.geography_id==Geography.id',
                                         uselist=False)

