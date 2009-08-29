#
# species_model.py
#

import traceback
import xml.sax.saxutils as sax
from itertools import chain

import gtk
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.orm.session import object_session
from sqlalchemy.ext.associationproxy import association_proxy

import bauble
import bauble.db as db
import bauble.utils as utils
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


# TODO: there is a trade_name column but there's no support yet for editing
# the trade_name or for using the trade_name when building the string
# for the species, for more information about trade_names see,
# http://www.hortax.org.uk/gardenplantsnames.html

# TODO: the specific epithet should not be non-nullable but instead
# make sure that at least one of the specific epithet, cultivar name
# or cultivar group is specificed

class SpeciesMapperExtension(MapperExtension):

    def after_update(self, mapper, conn, instance):
        instance.invalidate_str_cache()
        return EXT_CONTINUE



class Species(db.Base):
    """
    :Table name: species

    :Columns:
        *hybrid*:
            Hybrid flag

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
        The combination of sp, sp_author, hybrid, sp_qual,
        cv_group, trade_name, infrasp, infrasp_author, infrasp_rank,
        genus_id
    """
    __tablename__ = 'species'
    __table_args__ = (UniqueConstraint('sp', 'sp_author', 'hybrid',
                                        'sp_qual', 'cv_group', 'trade_name',
                                        'infrasp', 'infrasp_author',
                                        'infrasp_rank', 'genus_id',
                                        name='species_index'))
    __mapper_args__ = {'order_by': ['sp', 'sp_author', 'infrasp_rank',
                                   'infrasp'],
                       'extension': SpeciesMapperExtension()}

    # columns
    sp = Column(Unicode(64), index=True)
    sp_author = Column(Unicode(128))
    hybrid = Column(Boolean, default=False)
    sp_qual = Column(Enum(values=['agg.', 's. lat.', 's. str.', '']),
                     default=u'')
    cv_group = Column(Unicode(50))
    trade_name = Column(Unicode(64))

    # first infraspecific rank
    infrasp = Column(Unicode(50))
    infrasp_author = Column(Unicode(255))
    infrasp_rank = Column(Enum(values=['subsp.', 'var.', 'subvar.', 'f.',
                                       'subf.', 'cv.', '']), default=u'')

    # second infraspecific rank
    infrasp2 = Column(Unicode(50))
    infrasp2_author = Column(Unicode(255))
    infrasp2_rank = Column(Enum(values=['subsp.', 'var.', 'subvar.', 'f.',
                                        'subf.', 'cv.', '']), default=u'')

    notes = Column(UnicodeText)
    genus_id = Column(Integer, ForeignKey('genus.id'), nullable=False)

    # relations
    synonyms = association_proxy('_synonyms', 'synonym')
    _synonyms = relation('SpeciesSynonym',
                         primaryjoin='Species.id==SpeciesSynonym.species_id',
                         cascade='all, delete-orphan', uselist=True,
                         backref='species')

    # this is a dummy relation, it is only here to make cascading work
    # correctly and to ensure that all synonyms related to this genus
    # get deleted if this genus gets deleted
    __syn = relation('SpeciesSynonym',
                     primaryjoin='Species.id==SpeciesSynonym.synonym_id',
                     cascade='all, delete-orphan', uselist=True)

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


    def invalidate_str_cache(self):
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


    hybrid_char = '\xe2\xa8\x89'

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
        # TODO: this method will raise an error if the session is none
        # since it won't be able to look up the genus....we could
        # probably try to query the genus directly with the genus_id
        session = object_session(species)
        if session and use_cache and not session.is_modified(species):
            try:
                return species.__cached_str[(markup, authors)]
            except KeyError:
                species.__cached_str[(markup, authors)] = None

        genus = str(species.genus)
        sp = species.sp
        isp = species.infrasp
        isp2 = species.infrasp2
        if markup:
            escape = utils.xml_safe_utf8
            italicize = lambda s: u'<i>%s</i>' % escape(s)
            genus = italicize(genus)
            if sp is not None:
                sp = italicize(species.sp)
            if species.infrasp_rank != 'cv.':
                isp = italicize(species.infrasp)
            else:
                isp = escape(species.infrasp)

            if species.infrasp2_rank != 'cv.':
                isp2 = italicize(species.infrasp2)
            else:
                isp2 = escape(species.infrasp2)
        else:
            italicize = lambda s: u'%s' % s
            escape = lambda x: x

        author = None
        isp_author = None
        isp2_author = None
        if authors:
            if species.sp_author:
                author = escape(species.sp_author)
            if species.infrasp_author:
                isp_author = escape(species.infrasp_author)
            if species.infrasp2_author:
                isp2_author = escape(species.infrasp2_author)

        # create the first infraspecific part
        infrasp = []
        if species.infrasp:
            if species.infrasp_rank == 'cv.':
                group = None
                if species.cv_group:
                    group = "(%s Group)" % species.cv_group
                if authors:
                    infrasp = [group, "'%s'" % isp, isp_author]
                else:
                    infrasp = [group, "'%s'" % isp]
            else:
                group = None
                if species.cv_group:
                    group = "%s Group" % species.cv_group
                if authors:
                    infrasp = [species.infrasp_rank, isp, group,
                               isp_author]
                else:
                    infrasp = [species.infrasp_rank, isp, group]

        # create the second infraspecific part
        infrasp2 = []
        if species.infrasp2:
            if species.infrasp2_rank == 'cv.':
                group = None
                if species.cv_group and not species.infrasp:
                    group = "(%s Group)" % species.cv_group
                if authors:
                    infrasp2 = [group, "'%s'" % isp2, isp2_author]
                else:
                    infrasp2 = [group, "'%s'" % isp2, group]
            else:
                group = None
                if species.cv_group:
                    group = "%s Group" % species.cv_group
                if authors:
                    infrasp2 = [species.infrasp2_rank, isp2, group,isp2_author]
                else:
                    infrasp2 = [species.infrasp2_rank, isp2, group]

        # create the binomial part
        binomial = []
        if species.hybrid:
            if species.infrasp_rank is None:
                binomial = [genus, sp, species.hybrid_char]
            else:
                binomial = [genus, species.hybrid_char, sp, author]
        else:
            binomial = [genus, sp, author]

        # create the group part if there are not infraspecific parts
        group = []
        if not (species.infrasp or species.infrasp2) and species.cv_group:
            group = [species.cv_group, 'Group']

        # create the tail a.k.a think to add on to the end
        tail = []
        if species.sp_qual:
            tail = [species.sp_qual]

        parts = chain(binomial, group, infrasp, infrasp2, tail)
        s = utils.utf8(' '.join(filter(lambda x: x not in ('', None), parts)))
        species.__cached_str[(markup, authors)] = s
        return s



class SpeciesSynonym(db.Base):
    """
    :Table name: species_synonym
    """
    __tablename__ = 'species_synonym'

    # columns
    species_id = Column(Integer, ForeignKey('species.id'),
                        nullable=False)
    synonym_id = Column(Integer, ForeignKey('species.id'),
                        nullable=False, unique=True)

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
        if self.name:
            return self.name
        else:
            return ''



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

