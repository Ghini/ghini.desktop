# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Brett Adams
# Copyright 2012-2016 Mario Frasca <mario@anche.no>.
# Copyright 2017 Jardín Botánico de Quito
#
# This file is part of ghini.desktop.
#
# ghini.desktop is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ghini.desktop is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ghini.desktop. If not, see <http://www.gnu.org/licenses/>.

from itertools import chain

import logging
logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)

from sqlalchemy.ext.associationproxy import association_proxy

from sqlalchemy import Column, Boolean, Unicode, Integer, ForeignKey, \
    UnicodeText, func, UniqueConstraint
from sqlalchemy.orm import relation, backref, synonym
import bauble.db as db
import bauble.error as error
import bauble.utils as utils
import bauble.btypes as types



def _remove_zws(s):
    "remove_zero_width_space"
    if s:
        return s.replace(u'\u200b', '')
    return s


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
            logger.debug(e)


infrasp_rank_values = {u'subsp.': _('subsp.'),
                       u'var.': _('var.'),
                       u'subvar.': _('subvar'),
                       u'f.': _('f.'),
                       u'subf.': _('subf.'),
                       u'cv.': _('cv.'),
                       None: ''}


# TODO: there is a trade_name column but there's no support yet for editing
# the trade_name or for using the trade_name when building the string
# for the species, for more information about trade_names see,
# http://www.hortax.org.uk/gardenplantsnames.html

# TODO: the specific epithet should not be non-nullable but instead
# make sure that at least one of the specific epithet, cultivar name
# or cultivar group is specificed


def compare_rank(rank1, rank2):
    'implement the binary comparison operation needed for sorting'

    ordering = [u'familia', u'subfamilia', u'tribus', u'subtribus',
                u'genus', u'subgenus', u'species', None, u'subsp.',
                u'var.', u'subvar.', u'f.', u'subf.', u'cv.']
    return ordering.index(rank1).__cmp__(ordering.index(rank2))


class Species(db.Base, db.Serializable, db.DefiningPictures, db.WithNotes):
    """
    :Table name: species

    :Columns:
        *sp*:
        *sp2*:
        *sp_author*:

        *hybrid*:
            Hybrid flag

        *infrasp1*:
        *infrasp1_rank*:
        *infrasp1_author*:

        *infrasp2*:
        *infrasp2_rank*:
        *infrasp2_author*:

        *infrasp3*:
        *infrasp3_rank*:
        *infrasp3_author*:

        *infrasp4*:
        *infrasp4_rank*:
        *infrasp4_author*:

        *cv_group*:
        *trade_name*:

        *sp_qual*:
            Species qualifier

            Possible values:
                *agg.*: An aggregate species

                *s. lat.*: aggregrate species (sensu lato)

                *s. str.*: segregate species (sensu stricto)

        *label_distribution*:
            UnicodeText
            This field is optional and can be used for the label in case
            str(self.distribution) is too long to fit on the label.

    :Properties:
        *accessions*:

        *vernacular_names*:

        *default_vernacular_name*:

        *synonyms*:

        *distribution*:

    :Constraints:
        The combination of sp, sp_author, hybrid, sp_qual,
        cv_group, trade_name, genus_id
    """
    __tablename__ = 'species'
    __mapper_args__ = {'order_by': ['sp', 'sp_author']}

    rank = 'species'
    link_keys = ['accepted']

    def search_view_markup_pair(self):
        '''provide the two lines describing object for SearchView row.
        '''
        try:
            if len(self.vernacular_names) > 0:
                substring = (
                    '%s -- %s' %
                    (self.genus.family,
                     ', '.join([str(v) for v in self.vernacular_names])))
            else:
                substring = '%s' % self.genus.family
            trail = ''
            if self.accepted:
                trail += ('<span foreground="#555555" size="small" '
                          'weight="light"> - ' + _("synonym of %s") + "</span>"
                          ) % self.accepted.markup(authors=True)
            citation = self.markup(authors=True)
            authorship_text = utils.xml_safe(self.sp_author)
            if authorship_text:
                citation = citation.replace(authorship_text, '<span weight="light">' + authorship_text + '</span>')
            return citation + trail, substring
        except:
            return u'...', u'...'

    @property
    def cites(self):
        '''the cites status of this taxon, or None

        cites appendix number, one of I, II, or III.
        not enforced by the software in v1.0.x
        '''

        cites_notes = [i.note for i in self.notes
                       if i.category and i.category.upper() == u'CITES']
        if not cites_notes:
            return self.genus.cites
        return cites_notes[0]

    @property
    def conservation(self):
        '''the IUCN conservation status of this taxon, or DD

        one of: EX, RE, CR, EN, VU, NT, LC, DD
        not enforced by the software in v1.0.x
        '''

        {'EX': _('Extinct (EX)'),
         'EW': _('Extinct Wild (EW)'),
         'RE': _('Regionally Extinct (RE)'),
         'CR': _('Critically Endangered (CR)'),
         'EN': _('Endangered (EN)'),
         'VU': _('Vulnerable (VU)'),
         'NT': _('Near Threatened (NT)'),
         'LV': _('Least Concern (LC)'),
         'DD': _('Data Deficient (DD)'),
         'NE': _('Not Evaluated (NE)')}

        notes = [i.note for i in self.notes
                 if i.category and i.category.upper() == u'IUCN']
        return (notes + ['DD'])[0]

    @property
    def condition(self):
        '''the condition of this taxon, or None

        this is referred to what the garden conservator considers the
        area of interest. it is really an interpretation, not a fact.
        '''
        # one of, but not forcibly so:
        [_('endemic'), _('indigenous'), _('native'), _('introduced')]

        notes = [i.note for i in self.notes
                 if i.category.lower() == u'condition']
        return (notes + [None])[0]

    def __lowest_infraspecific(self):
        infrasp = [(self.infrasp1_rank, self.infrasp1,
                    self.infrasp1_author),
                   (self.infrasp2_rank, self.infrasp2,
                    self.infrasp2_author),
                   (self.infrasp3_rank, self.infrasp3,
                    self.infrasp3_author),
                   (self.infrasp4_rank, self.infrasp4,
                    self.infrasp4_author)]
        infrasp = [i for i in infrasp if i[0] not in [u'cv.', '', None]]
        if infrasp == []:
            return (u'', u'', u'')
        return sorted(infrasp, cmp=lambda a, b: compare_rank(a[0], b[0]))[-1]

    @property
    def infraspecific_rank(self):
        return self.__lowest_infraspecific()[0] or u''

    @property
    def infraspecific_epithet(self):
        return self.__lowest_infraspecific()[1] or u''

    @property
    def infraspecific_author(self):
        return self.__lowest_infraspecific()[2] or u''

    @property
    def cultivar_epithet(self):
        infrasp = ((self.infrasp1_rank, self.infrasp1,
                    self.infrasp1_author),
                   (self.infrasp2_rank, self.infrasp2,
                    self.infrasp2_author),
                   (self.infrasp3_rank, self.infrasp3,
                    self.infrasp3_author),
                   (self.infrasp4_rank, self.infrasp4,
                    self.infrasp4_author))
        for rank, epithet, author in infrasp:
            if rank == u'cv.':
                return epithet
        return u''

    # columns
    sp = Column(Unicode(64), index=True)
    epithet = synonym('sp')
    sp2 = Column(Unicode(64), index=True)  # in case hybrid=True
    sp_author = Column(Unicode(128))
    hybrid = Column(Boolean, default=False)
    sp_qual = Column(types.Enum(values=['agg.', 's. lat.', 's. str.', None]),
                     default=None)
    cv_group = Column(Unicode(50))
    trade_name = Column(Unicode(64))

    infrasp1 = Column(Unicode(64))
    infrasp1_rank = Column(types.Enum(values=infrasp_rank_values.keys(),
                                      translations=infrasp_rank_values))
    infrasp1_author = Column(Unicode(64))

    infrasp2 = Column(Unicode(64))
    infrasp2_rank = Column(types.Enum(values=infrasp_rank_values.keys(),
                                      translations=infrasp_rank_values))
    infrasp2_author = Column(Unicode(64))

    infrasp3 = Column(Unicode(64))
    infrasp3_rank = Column(types.Enum(values=infrasp_rank_values.keys(),
                                      translations=infrasp_rank_values))
    infrasp3_author = Column(Unicode(64))

    infrasp4 = Column(Unicode(64))
    infrasp4_rank = Column(types.Enum(values=infrasp_rank_values.keys(),
                                      translations=infrasp_rank_values))
    infrasp4_author = Column(Unicode(64))

    genus_id = Column(Integer, ForeignKey('genus.id'), nullable=False)
    ## the Species.genus property is defined as backref in Genus.species

    label_distribution = Column(UnicodeText)
    bc_distribution = Column(UnicodeText)

    # relations
    synonyms = association_proxy('_synonyms', 'synonym')
    _synonyms = relation('SpeciesSynonym',
                         primaryjoin='Species.id==SpeciesSynonym.species_id',
                         cascade='all, delete-orphan', uselist=True,
                         backref='species')

    # this is a dummy relation, it is only here to make cascading work
    # correctly and to ensure that all synonyms related to this genus
    # get deleted if this genus gets deleted
    _syn = relation('SpeciesSynonym',
                    primaryjoin='Species.id==SpeciesSynonym.synonym_id',
                    cascade='all, delete-orphan', uselist=True)

    ## VernacularName.species gets defined here too.
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

    habit_id = Column(Integer, ForeignKey('habit.id'), default=None)
    habit = relation('Habit', uselist=False, backref='species')

    flower_color_id = Column(Integer, ForeignKey('color.id'), default=None)
    flower_color = relation('Color', uselist=False, backref='species')

    #hardiness_zone = Column(Unicode(4))

    awards = Column(UnicodeText)

    def __init__(self, *args, **kwargs):
        super(Species, self).__init__(*args, **kwargs)

    def __str__(self):
        'return the default string representation for self.'
        return self.str()

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

    def markup(self, authors=False, genus=True):
        '''returns this object as a string with markup

        :param authors: whether the authorship should be included
        :param genus: whether the genus name should be included

        '''
        return self.str(authors, markup=True, genus=genus)

    # in PlantPlugins.init() we set this to 'x' for win32
    hybrid_char = u'×'

    def str(self, authors=False, markup=False, remove_zws=False, genus=True,
            qualification=None):
        '''
        returns a string for species

        :param authors: flag to toggle whether authorship should be included
        :param markup: flag to toggle whether the returned text is marked up
        to show italics on the epithets
        :param remove_zws: flag to toggle zero width spaces, helping
        semantically correct lexicographic order.
        :param genus: flag to toggle leading genus name.
        :param qualification: pair or None. if specified, first is the
        qualified rank, second is the qualification.
        '''
        # TODO: this method will raise an error if the session is none
        # since it won't be able to look up the genus....we could
        # probably try to query the genus directly with the genus_id
        if genus is True:
            genus = str(self.genus)
        else:
            genus = ''
        if self.sp and not remove_zws:
            sp = u'\u200b' + self.sp  # prepend with zero_width_space
        else:
            sp = self.sp
        sp2 = self.sp2
        if markup:
            escape = utils.xml_safe
            italicize = lambda s: (  # all but the multiplication signs
                u'<i>%s</i>' % escape(s).replace(u'×', u'</i>×<i>'))
            genus = italicize(genus)
            if sp is not None:
                sp = italicize(sp)
            if sp2 is not None:
                sp2 = italicize(sp2)
        else:
            italicize = escape = lambda x: x

        author = None
        if authors and self.sp_author:
            author = escape(self.sp_author)

        infrasp = ((self.infrasp1_rank, self.infrasp1,
                    self.infrasp1_author),
                   (self.infrasp2_rank, self.infrasp2,
                    self.infrasp2_author),
                   (self.infrasp3_rank, self.infrasp3,
                    self.infrasp3_author),
                   (self.infrasp4_rank, self.infrasp4,
                    self.infrasp4_author))

        infrasp_parts = []
        group_added = False
        for rank, epithet, iauthor in infrasp:
            if rank == 'cv.' and epithet:
                if self.cv_group and not group_added:
                    group_added = True
                    infrasp_parts.append(_("(%(group)s Group)") %
                                         dict(group=self.cv_group))
                infrasp_parts.append("'%s'" % escape(epithet))
            else:
                if rank:
                    infrasp_parts.append(rank)
                if epithet and rank:
                    infrasp_parts.append(italicize(epithet))
                elif epithet:
                    infrasp_parts.append(escape(epithet))

            if authors and iauthor:
                infrasp_parts.append(escape(iauthor))
        if self.cv_group and not group_added:
            infrasp_parts.append(_("%(group)s Group") %
                                 dict(group=self.cv_group))

        # create the binomial part
        binomial = [genus, self.hybrid and self.hybrid_char, sp, author]

        # create the tail, ie: anything to add on to the end
        tail = []
        if self.sp_qual:
            tail = [self.sp_qual]

        if qualification is not None:
            rank, qual = qualification
            if qual in ['incorrect']:
                rank = None
            if rank == 'sp':
                binomial.insert(2, qual)
            elif not rank:
                binomial[2] += ' (' + qual + ')'
            elif rank == 'genus':
                binomial.insert(0, qual)
            elif rank == 'infrasp':
                if infrasp_parts:
                    infrasp_parts.insert(0, qual)
            else:
                for r, e, a in infrasp:
                    if r == 'cv.':
                        e = "'%s'" % e
                    if rank == r:
                        pos = infrasp_parts.index(e)
                        infrasp_parts.insert(pos, qual)
                else:
                    logger.info('cannot find specified rank %s' % e)

        parts = chain(binomial, infrasp_parts, tail)
        s = utils.utf8(' '.join(i for i in parts if i))
        if self.hybrid:
            s = s.replace('%s ' % self.hybrid_char, self.hybrid_char)
        return s

    @property
    def accepted(self):
        'Name that should be used if name of self should be rejected'
        from sqlalchemy.orm.session import object_session
        session = object_session(self)
        if not session:
            logger.warn('species:accepted - object not in session')
            return None
        syn = session.query(SpeciesSynonym).filter(
            SpeciesSynonym.synonym_id == self.id).first()
        accepted = syn and syn.species
        return accepted

    @accepted.setter
    def accepted(self, value):
        'Name that should be used if name of self should be rejected'
        logger.debug("Accepted taxon: %s %s" % (type(value), value))
        assert isinstance(value, self.__class__)
        if self in value.synonyms:
            return
        # remove any previous `accepted` link
        from sqlalchemy.orm.session import object_session
        session = object_session(self)
        if not session:
            logger.warn('species:accepted.setter - object not in session')
            return
        previous_synonymy_link = session.query(SpeciesSynonym).filter(
            SpeciesSynonym.synonym_id == self.id).first()
        if previous_synonymy_link:
            a = session.query(Species).filter(Species.id==previous_synonymy_link.species_id).one()
            a.synonyms.remove(self)
        session.flush()
        if value != self:
            value.synonyms.append(self)
        session.flush()

    def has_accessions(self):
        '''true if species is linked to at least one accession
        '''

        return False

    infrasp_attr = {1: {'rank': 'infrasp1_rank',
                        'epithet': 'infrasp1',
                        'author': 'infrasp1_author'},
                    2: {'rank': 'infrasp2_rank',
                        'epithet': 'infrasp2',
                        'author': 'infrasp2_author'},
                    3: {'rank': 'infrasp3_rank',
                        'epithet': 'infrasp3',
                        'author': 'infrasp3_author'},
                    4: {'rank': 'infrasp4_rank',
                        'epithet': 'infrasp4',
                        'author': 'infrasp4_author'}}

    def get_infrasp(self, level):
        """
        level should be 1-4
        """
        return getattr(self, self.infrasp_attr[level]['rank']), \
            getattr(self, self.infrasp_attr[level]['epithet']), \
            getattr(self, self.infrasp_attr[level]['author'])

    def set_infrasp(self, level, rank, epithet, author=None):
        """
        level should be 1-4
        """
        setattr(self, self.infrasp_attr[level]['rank'], rank)
        setattr(self, self.infrasp_attr[level]['epithet'], epithet)
        setattr(self, self.infrasp_attr[level]['author'], author)

    def as_dict(self, recurse=True):
        result = dict((col, getattr(self, col))
                      for col in self.__table__.columns.keys()
                      if col not in ['id', 'sp']
                      and col[0] != '_'
                      and getattr(self, col) is not None
                      and not col.endswith('_id'))
        result['object'] = 'taxon'
        result['rank'] = 'species'
        result['epithet'] = self.sp
        result['ht-rank'] = 'genus'
        result['ht-epithet'] = self.genus.genus
        if recurse and self.accepted is not None:
            result['accepted'] = self.accepted.as_dict(recurse=False)
        return result

    @classmethod
    def correct_field_names(cls, keys):
        for internal, exchange in [('sp_author', 'author'),
                                   ('sp', 'epithet')]:
            if exchange in keys:
                keys[internal] = keys[exchange]
                del keys[exchange]

    @classmethod
    def retrieve(cls, session, keys):
        from genus import Genus
        try:
            return session.query(cls).filter(
                cls.sp == keys['epithet']).join(Genus).filter(
                Genus.genus == keys['ht-epithet']).one()
        except:
            return None

    @classmethod
    def compute_serializable_fields(cls, session, keys):
        from genus import Genus
        result = {'genus': None}
        ## retrieve genus object
        specifies_family = keys.get('familia')
        result['genus'] = Genus.retrieve_or_create(
            session, {'epithet': keys['ht-epithet'],
                      'ht-epithet': specifies_family},
            create=(specifies_family is not None))
        if result['genus'] is None:
            raise error.NoResultException()
        return result

    def top_level_count(self):
        plants = [p for a in self.accessions for p in a.plants]
        return {(1, 'Species'): 1,
                (2, 'Genera'): set([self.genus.id]),
                (3, 'Families'): set([self.genus.family.id]),
                (4, 'Accessions'): len(self.accessions),
                (5, 'Plantings'): len(plants),
                (6, 'Living plants'): sum(p.quantity for p in plants),
                (7, 'Locations'): set(p.location.id for p in plants),
                (8, 'Sources'): set([a.source.source_detail.id
                                     for a in self.accessions
                                     if a.source and a.source.source_detail])}


def as_dict(self):
    result = db.Serializable.as_dict(self)
    result['species'] = self.species.str(self.species, remove_zws=True)
    return result

def compute_serializable_fields(cls, session, keys):
    logger.debug('compute_serializable_fields(session, %s)' % keys)
    result = {}
    genus_name, epithet = keys['species'].split(' ', 1)
    sp_dict = {'ht-epithet': genus_name,
               'epithet': epithet}
    result['species'] = Species.retrieve_or_create(
        session, sp_dict, create=False)
    return result

def retrieve(cls, session, keys):
    from genus import Genus
    genus, epithet = keys['species'].split(' ', 1)
    try:
        return session.query(cls).filter(
            cls.category == keys['category']).join(Species).filter(
            Species.sp == epithet).join(Genus).filter(
            Genus.genus == genus).one()
    except:
        return None

SpeciesNote = db.make_note_class('Species', compute_serializable_fields, as_dict, retrieve)


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


class VernacularName(db.Base, db.Serializable):
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
    __table_args__ = (UniqueConstraint('name', 'language',
                                       'species_id', name='vn_index'), {})

    def search_view_markup_pair(self):
        """provide the two lines describing object for SearchView row.
        """
        return str(self), self.species.markup(authors=False)

    def __str__(self):
        if self.name:
            return self.name
        else:
            return ''

    def replacement(self):
        'user wants the species, not just the name'
        return self.species

    def as_dict(self):
        result = db.Serializable.as_dict(self)
        result['species'] = self.species.str(self.species, remove_zws=True)
        return result

    @classmethod
    def compute_serializable_fields(cls, session, keys):
        logger.debug('compute_serializable_fields(session, %s)' % keys)
        result = {'species': None}
        if 'species' in keys:
            ## now we must connect the name to the species it refers to
            genus_name, epithet = keys['species'].split(' ', 1)
            sp_dict = {'ht-epithet': genus_name,
                       'epithet': epithet}
            result['species'] = Species.retrieve_or_create(
                session, sp_dict, create=False)
        return result

    @classmethod
    def retrieve(cls, session, keys):
        from genus import Genus
        g_epithet, s_epithet = keys['species'].split(' ', 1)
        sp = session.query(Species).filter(
            Species.sp == s_epithet).join(Genus).filter(
            Genus.genus == g_epithet).first()
        try:
            return session.query(cls).filter(
                cls.species == sp,
                cls.language == keys['language']).one()
        except:
            return None

    @property
    def pictures(self):
        return self.species.pictures


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
                                       name='default_vn_index'), {})

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
SpeciesDistribution.geography = relation(
    'Geography',
    primaryjoin='SpeciesDistribution.geography_id==Geography.id',
    uselist=False)


class Habit(db.Base):
    __tablename__ = 'habit'

    name = Column(Unicode(64))
    code = Column(Unicode(8), unique=True)

    def __str__(self):
        if self.name:
            return '%s (%s)' % (self.name, self.code)
        else:
            return str(self.code)


class Color(db.Base):
    __tablename__ = 'color'

    name = Column(Unicode(32))
    code = Column(Unicode(8), unique=True)

    def __str__(self):
        if self.name:
            return '%s (%s)' % (self.name, self.code)
        else:
            return str(self.code)


db.Species = Species
db.SpeciesNote = SpeciesNote
db.VernacularName = VernacularName
