# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Brett Adams
# Copyright 2015-2016 Mario Frasca <mario@anche.no>.
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
#
# accessions module
#

import datetime
from decimal import Decimal, ROUND_DOWN
import os
from random import random
import sys
import traceback
import weakref

import logging
logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)

import gtk


import lxml.etree as etree
import pango
from sqlalchemy import and_, or_, func
from sqlalchemy import ForeignKey, Column, Unicode, Integer, Boolean, \
    UnicodeText
from sqlalchemy.orm import EXT_CONTINUE, MapperExtension, \
    backref, relation, reconstructor, validates
from sqlalchemy.orm.session import object_session
from sqlalchemy.exc import DBAPIError

import bauble
import bauble.db as db
import bauble.editor as editor
from bauble import meta
from bauble.error import check
import bauble.paths as paths
from bauble.plugins.garden.propagation import SourcePropagationPresenter, \
    Propagation
from bauble.plugins.garden.source import Contact, create_contact, \
    Source, Collection, CollectionPresenter, PropagationChooserPresenter
import bauble.prefs as prefs
import bauble.btypes as types
import bauble.utils as utils
from bauble.view import InfoBox, InfoExpander, PropertiesExpander, \
    select_in_search_results, Action
import bauble.view as view
from bauble.search import SearchStrategy
from types import StringTypes
from bauble.utils import safe_int

# TODO: underneath the species entry create a label that shows information
# about the family of the genus of the species selected as well as more
# info about the genus so we know exactly what plant is being selected
# e.g. Malvaceae (sensu lato), Hibiscus (senso stricto)


def longitude_to_dms(decimal):
    return decimal_to_dms(Decimal(decimal), 'long')


def latitude_to_dms(decimal):
    return decimal_to_dms(Decimal(decimal), 'lat')


def decimal_to_dms(decimal, long_or_lat):
    '''
    :param decimal: the value to convert
    :param long_or_lat: should be either "long" or "lat"

    @returns dir, degrees, minutes seconds, seconds rounded to two
    decimal places
    '''
    if long_or_lat == 'long':
        check(abs(decimal) <= 180)
    else:
        check(abs(decimal) <= 90)
    dir_map = {'long': ['E', 'W'],
               'lat':  ['N', 'S']}
    direction = dir_map[long_or_lat][0]
    if decimal < 0:
        direction = dir_map[long_or_lat][1]
    dec = Decimal(str(abs(decimal)))
    d = Decimal(str(dec)).to_integral(rounding=ROUND_DOWN)
    m = Decimal(abs((dec-d)*60)).to_integral(rounding=ROUND_DOWN)
    m2 = Decimal(abs((dec-d)*60))
    places = 2
    q = Decimal((0, (1,), -places))
    s = Decimal(abs((m2-m) * 60)).quantize(q)
    return direction, d, m, s


def dms_to_decimal(dir, deg, min, sec, precision=6):
    '''
    convert degrees, minutes, seconds to decimal
    return a decimal.Decimal
    '''
    nplaces = Decimal(10) ** -precision
    if dir in ('E', 'W'):  # longitude
        check(abs(deg) <= 180)
    else:
        check(abs(deg) <= 90)
    check(abs(min) < 60)
    check(abs(sec) < 60)
    deg = Decimal(str(abs(deg)))
    min = Decimal(str(min))
    sec = Decimal(str(sec))
    dec = abs(sec/Decimal('3600')) + abs(min/Decimal('60.0')) + deg
    if dir in ('W', 'S'):
        dec = -dec
    return dec.quantize(nplaces)


def generic_taxon_add_action(model, view, presenter, top_presenter,
                             button, taxon_entry):
    """user hit click on taxon add button

    new taxon goes into model.species;
    its string representation into taxon_entry.
    """

    from bauble.plugins.plants.species import edit_species
    committed = edit_species(parent_view=view.get_window(), is_dependent_window=True)
    if committed:
        if isinstance(committed, list):
            committed = committed[0]
        logger.debug('new taxon added from within AccessionEditor')
        # add the new taxon to the session and start using it
        presenter.session.add(committed)
        taxon_entry.set_text("%s" % committed)
        presenter.remove_problem(
            hash(gtk.Buildable.get_name(taxon_entry)), None)
        setattr(model, 'species', committed)
        presenter._dirty = True
        top_presenter.refresh_sensitivity()
    else:
        logger.debug('new taxon not added after request from AccessionEditor')


def edit_callback(accessions):
    e = AccessionEditor(model=accessions[0])
    return e.start()


def add_plants_callback(accessions):
    # create a temporary session so that the temporary plant doesn't
    # get added to the accession
    session = db.Session()
    acc = session.merge(accessions[0])
    e = PlantEditor(model=Plant(accession=acc))
    session.close()
    return e.start()


def remove_callback(accessions):
    acc = accessions[0]
    if len(acc.plants) > 0:
        safe = utils.xml_safe
        plants = [str(plant) for plant in acc.plants]
        values = dict(num_plants=len(acc.plants),
                      plant_codes=safe(', '.join(plants)))
        msg = (_('%(num_plants)s plants depend on this accession: '
                 '<b>%(plant_codes)s</b>\n\n') % values +
               _('You cannot remove an accession with plants.'))
        utils.message_dialog(msg, type=gtk.MESSAGE_WARNING)
        return
    else:
        msg = _("Are you sure you want to remove accession <b>%s</b>?") % \
            utils.xml_safe(unicode(acc))
    if not utils.yes_no_dialog(msg):
        return
    try:
        session = db.Session()
        obj = session.query(Accession).get(acc.id)
        session.delete(obj)
        session.commit()
    except Exception, e:
        msg = _('Could not delete.\n\n%s') % utils.xml_safe(unicode(e))
        utils.message_details_dialog(msg, traceback.format_exc(),
                                     type=gtk.MESSAGE_ERROR)
    finally:
        session.close()
    return True


edit_action = Action('acc_edit', _('_Edit'),
                     callback=edit_callback,
                     accelerator='<ctrl>e')
add_plant_action = Action('acc_add', _('_Add plants'),
                          callback=add_plants_callback,
                          accelerator='<ctrl>k')
remove_action = Action('acc_remove', _('_Delete'),
                       callback=remove_callback,
                       accelerator='<ctrl>Delete')

acc_context_menu = [edit_action, add_plant_action, remove_action]


# TODO: accession should have a one-to-many relationship on verifications
    #ver_level = StringCol(length=2, default=None) # verification level
    #ver_name = StringCol(length=50, default=None) # verifier's name
    #ver_date = DateTimeCol(default=None) # verification date
    #ver_hist = StringCol(default=None)  # verification history
    #ver_lit = StringCol(default=None) # verification lit
    #ver_id = IntCol(default=None) # ?? # verifier's ID??


ver_level_descriptions = \
    {0: _('The name of the record has not been checked by any authority.'),
     1: _('The name of the record determined by comparison with other '
          'named plants.'),
     2: _('The name of the record determined by a taxonomist or by other '
          'competent persons using herbarium and/or library and/or '
          'documented living material.'),
     3: _('The name of the plant determined by taxonomist engaged in '
          'systematic revision of the group.'),
     4: _('The record is part of type gathering or propagated from type '
          'material by asexual methods.')}


class Verification(db.Base):
    """
    :Table name: verification

    :Columns:
      verifier: :class:`sqlalchemy.types.Unicode`
        The name of the person that made the verification.
      date: :class:`sqlalchemy.types.Date`
        The date of the verification
      reference: :class:`sqlalchemy.types.UnicodeText`
        The reference material used to make this verification
      level: :class:`sqlalchemy.types.Integer`
        Determines the level or authority of the verifier. If it is
        not known whether the name of the record has been verified by
        an authority, then this field should be None.

        Possible values:
            - 0: The name of the record has not been checked by any authority.
            - 1: The name of the record determined by comparison with
              other named plants.
            - 2: The name of the record determined by a taxonomist or by
              other competent persons using herbarium and/or library and/or
              documented living material.
            - 3: The name of the plant determined by taxonomist engaged in
              systematic revision of the group.
            - 4: The record is part of type gathering or propagated from
              type material by asexual methods

      notes: :class:`sqlalchemy.types.UnicodeText`
        Notes about this verification.
      accession_id: :class:`sqlalchemy.types.Integer`
        Foreign Key to the :class:`Accession` table.
      species_id: :class:`sqlalchemy.types.Integer`
        Foreign Key to the :class:`~bauble.plugins.plants.Species` table.
      prev_species_id: :class:`~sqlalchemy.types.Integer`
        Foreign key to the :class:`~bauble.plugins.plants.Species`
        table. What it was verified from.

    """
    __tablename__ = 'verification'
    __mapper_args__ = {'order_by': 'verification.date'}

    # columns
    verifier = Column(Unicode(64), nullable=False)
    date = Column(types.Date, nullable=False)
    reference = Column(UnicodeText)
    accession_id = Column(Integer, ForeignKey('accession.id'), nullable=False)

    # the level of assurance of this verification
    level = Column(Integer, nullable=False, autoincrement=False)

    # what it was verified as
    species_id = Column(Integer, ForeignKey('species.id'), nullable=False)

    # what it was verified from
    prev_species_id = Column(Integer, ForeignKey('species.id'), nullable=False)

    species = relation(
        'Species', primaryjoin='Verification.species_id==Species.id')
    prev_species = relation(
        'Species', primaryjoin='Verification.prev_species_id==Species.id')

    notes = Column(UnicodeText)


# TODO: I have no internet, so I write this here. please remove this note
# and add the text as new issues as soon as possible.
#
# First of all a ghini-1.1 issue: being 'Accession' an abstract concept, you
# don't make a Voucher of an Accession, you make a Voucher of a Plant. As
# with Photos, in the Accession Infobox you want to see all Vouchers of all
# Plantings belonging to the Accession.
#
# 2: imagine you go on expedition and collect vouchers as well as seeds, or
# stekken:nl. You will have vouchers of the parent plant plant, but the
# parent plant will not be in your collection. This justifies requiring the
# ability to add a Voucher to a Plant and mark it as Voucher of its parent
# plant. On the other hand though, if the parent plant *is* in your
# collection and the link is correctly represented in a Propagation, any
# 'parent plant voucher' will conflict with the vouchers associated to the
# parent plant. Maybe this can be solved by disabling the whole
# parent_voucher panel in the case of plants resulting of a garden
# propagation.
#
# 3: Infobox (Accession AND Plant) are to show parent plant information as a
# link to the parent plant, or as the name of the parent plant voucher. At
# the moment this is only partially the case for


herbarium_codes = {}


class Voucher(db.Base):
    """
    :Table name: voucher

    :Columns:
      herbarium: :class:`sqlalchemy.types.Unicode`
        The name of the herbarium.
      code: :class:`sqlalchemy.types.Unicode`
        The herbarium code for the voucher.
      parent_material: :class:`sqlalchemy.types.Boolean`
        Is this voucher relative to the parent material of the accession.
      accession_id: :class:`sqlalchemy.types.Integer`
        Foreign key to the :class:`Accession` .


    """
    __tablename__ = 'voucher'
    herbarium = Column(Unicode(5), nullable=False)
    code = Column(Unicode(32), nullable=False)
    parent_material = Column(Boolean, default=False)
    accession_id = Column(Integer, ForeignKey('accession.id'), nullable=False)

    # accession  = relation('Accession', uselist=False,
    #                       backref=backref('vouchers',
    #                                       cascade='all, delete-orphan'))


# invalidate an accessions string cache after it has been updated
class AccessionMapperExtension(MapperExtension):

    def after_update(self, mapper, conn, instance):
        instance.invalidate_str_cache()
        return EXT_CONTINUE


# ITF2 - E.1; Provenance Type Flag; Transfer code: prot
prov_type_values = [
    (u'Wild', _('Accession of wild source')),  # W
    (u'Cultivated', _('Propagule(s) from a wild source plant')),  # Z
    (u'NotWild', _("Accession not of wild source")),  # G
    (u'Purchase', _('Purchase or gift')),  # COLLAPSE INTO G
    (u'InsufficientData', _("Insufficient Data")),  # U
    (u'Unknown', _("Unknown")),  # COLLAPSE INTO U
    (None, ''),  # do not transfer this field
    ]

# ITF2 - E.3; Wild Provenance Status Flag; Transfer code: wpst
#  - further specifies the W and Z prov type flag
#
# according to the ITF2, the keys should literally be one of: 'Wild native',
# 'Wild non-native', 'Cultivated native', 'Cultivated non-native'.  In
# practice the standard just requires we note whether a wild (a cultivated
# propagule Z or the one directly collected W) plant is native or not to the
# place where it was found. a boolean should suffice, exporting will expand
# to and importing will collapse from the standard value. Giving all four
# options after the user has already selected W or Z works only confusing to
# user not familiar with ITF2 standard.
wild_prov_status_values = [
    # Endemic found within indigenous range
    (u'WildNative', _("Wild native")),
    # found outside indigenous range
    (u'WildNonNative', _("Wild non-native")),
    # Endemic, cultivated, reintroduced or translocated within its
    # indigenous range
    (u'CultivatedNative', _("Cultivated native")),

    # MISSING cultivated, found outside its indigenous range
    # (u'CultivatedNonNative', _("Cultivated non-native"))

    # TO REMOVE:
    (u'Impound', _("Impound")),
    (u'Collection', _("Collection")),
    (u'Rescue', _("Rescue")),
    (u'InsufficientData', _("Insufficient Data")),
    (u'Unknown', _("Unknown")),

    # Not transferred
    (None, '')]

# not ITF2
# - further specifies the Z prov type flag value
cultivated_prov_status_values = [
    (u'InVitro', _("In vitro")),
    (u'Division', _("Division")),
    (u'Seed', _("Seed")),
    (u'Unknown', _("Unknown")),
    (None, '')]

# not ITF2
# - further specifies the G prov type flag value
purchase_prov_status_values = [
    (u'National', _("National")),
    (u'Imported', _("Imported")),
    (u'Unknown', _("Unknown")),
    (None, '')]

# not ITF2
recvd_type_values = {
    u'ALAY': _('Air layer'),
    U'BBPL': _('Balled & burlapped plant'),
    u'BRPL': _('Bare root plant'),
    u'BUDC': _('Bud cutting'),
    u'BUDD': _('Budded'),
    u'BULB': _('Bulb'),
    u'CLUM': _('Clump'),
    u'CORM': _('Corm'),
    u'DIVI': _('Division'),
    u'GRAF': _('Graft'),
    u'LAYE': _('Layer'),
    u'PLNT': _('Planting'),
    u'PSBU': _('Pseudobulb'),
    u'RCUT': _('Rooted cutting'),
    u'RHIZ': _('Rhizome'),
    u'ROOC': _('Root cutting'),
    u'ROOT': _('Root'),
    u'SCIO': _('Scion'),
    u'SEDL': _('Seedling'),
    u'SEED': _('Seed'),
    u'SPOR': _('Spore'),
    u'SPRL': _('Sporeling'),
    u'TUBE': _('Tuber'),
    u'UNKN': _('Unknown'),
    u'URCU': _('Unrooted cutting'),
    u'BBIL': _('Bulbil'),
    u'VEGS': _('Vegetative spreading'),
    u'SCKR': _('Root sucker'),
    None: ''
    }

accession_type_to_plant_material = {
    #u'Plant': _('Planting'),
    U'BBPL': u'Plant',
    u'BRPL': u'Plant',
    u'PLNT': u'Plant',
    u'SEDL': u'Plant',
    #u'Seed': _('Seed/Spore'),
    u'SEED': u'Seed',
    u'SPOR': u'Seed',
    u'SPRL': u'Seed',
    #u'Vegetative': _('Vegetative Part'),
    u'BUDC': u'Vegetative',
    u'BUDD': u'Vegetative',
    u'BULB': u'Vegetative',
    u'CLUM': u'Vegetative',
    u'CORM': u'Vegetative',
    u'DIVI': u'Vegetative',
    u'GRAF': u'Vegetative',
    u'LAYE': u'Vegetative',
    u'PSBU': u'Vegetative',
    u'RCUT': u'Vegetative',
    u'RHIZ': u'Vegetative',
    u'ROOC': u'Vegetative',
    u'ROOT': u'Vegetative',
    u'SCIO': u'Vegetative',
    u'TUBE': u'Vegetative',
    u'URCU': u'Vegetative',
    u'BBIL': u'Vegetative',
    u'VEGS': u'Vegetative',
    u'SCKR': u'Vegetative',
    #u'Tissue': _('Tissue Culture'),
    u'ALAY': u'Tissue',
    #u'Other': _('Other'),
    u'UNKN': u'Other',
    None: None
    }


def compute_serializable_fields(cls, session, keys):
    result = {'accession': None}

    acc_keys = {}
    acc_keys.update(keys)
    acc_keys['code'] = keys['accession']
    accession = Accession.retrieve_or_create(
        session, acc_keys, create=(
            'taxon' in acc_keys and 'rank' in acc_keys))

    result['accession'] = accession

    return result

AccessionNote = db.make_note_class('Accession', compute_serializable_fields)


class Accession(db.Base, db.Serializable, db.WithNotes):
    """
    :Table name: accession

    :Columns:
        *code*: :class:`sqlalchemy.types.Unicode`
            the accession code

        *prov_type*: :class:`bauble.types.Enum`
            the provenance type

            Possible values:
                * first column of prov_type_values

        *wild_prov_status*:  :class:`bauble.types.Enum`
            this column can be used to give more provenance
            information

            Possible values:
                * union of first columns of wild_prov_status_values,
                * purchase_prov_status_values,
                * cultivated_prov_status_values

        *date_accd*: :class:`bauble.types.Date`
            the date this accession was accessioned

        *id_qual*: :class:`bauble.types.Enum`
            The id qualifier is used to indicate uncertainty in the
            identification of this accession

            Possible values:
                * aff. - affinity with
                * cf. - compare with
                * forsan - perhaps
                * near - close to
                * ? - questionable
                * incorrect

        *id_qual_rank*: :class:`sqlalchemy.types.Unicode`
            The rank of the species that the id_qaul refers to.

        *private*: :class:`sqlalchemy.types.Boolean`
            Flag to indicate where this information is sensitive and
            should be kept private

        *species_id*: :class:`sqlalchemy.types.Integer()`
            foreign key to the species table

    :Properties:
        *species*:
            the species this accession refers to

        *source*:
            source is a relation to a Source instance

        *plants*:
            a list of plants related to this accession

        *verifications*:
            a list of verifications on the identification of this accession

    :Constraints:

    """
    __tablename__ = 'accession'
    __mapper_args__ = {'order_by': 'accession.code',
                       'extension': AccessionMapperExtension()}

    # columns
    #: the accession code
    code = Column(Unicode(20), nullable=False, unique=True)
    code_format = u'%Y%PD####'

    @validates('code')
    def validate_stripping(self, key, value):
        if value is None:
            return None
        return value.strip()

    prov_type = Column(types.Enum(values=[i[0] for i in prov_type_values],
                                  translations=dict(prov_type_values)),
                       default=None)

    wild_prov_status = Column(
        types.Enum(values=[i[0] for i in wild_prov_status_values],
                   translations=dict(wild_prov_status_values)),
        default=None)

    date_accd = Column(types.Date)
    date_recvd = Column(types.Date)
    quantity_recvd = Column(Integer, autoincrement=False)
    recvd_type = Column(types.Enum(values=recvd_type_values.keys(),
                                   translations=recvd_type_values),
                        default=None)

    # ITF2 - C24 - Rank Qualified Flag - Transfer code: rkql
    ## B: Below Family; F: Family; G: Genus; S: Species; I: first
    ## Infraspecific Epithet; J: second Infraspecific Epithet; C: Cultivar;
    id_qual_rank = Column(Unicode(10))

    # ITF2 - C25 - Identification Qualifier - Transfer code: idql
    id_qual = Column(types.Enum(values=['aff.', 'cf.', 'incorrect',
                                        'forsan', 'near', '?', None]),
                     default=None)

    # "private" new in 0.8b2
    private = Column(Boolean, default=False)
    species_id = Column(Integer, ForeignKey('species.id'), nullable=False)

    # intended location
    intended_location_id = Column(Integer, ForeignKey('location.id'))
    intended2_location_id = Column(Integer, ForeignKey('location.id'))

    # the source of the accession
    source = relation('Source', uselist=False, cascade='all, delete-orphan',
                      backref=backref('accession', uselist=False))

    # relations
    species = relation('Species', uselist=False,
                       backref=backref('accessions',
                                       cascade='all, delete-orphan'))

    # use Plant.code for the order_by to avoid ambiguous column names
    plants = relation('Plant', cascade='all, delete-orphan',
                      #order_by='plant.code',
                      backref=backref('accession', uselist=False))
    verifications = relation('Verification',  # order_by='date',
                             cascade='all, delete-orphan',
                             backref=backref('accession', uselist=False))
    vouchers = relation('Voucher', cascade='all, delete-orphan',
                        backref=backref('accession', uselist=False))
    intended_location = relation(
        'Location', primaryjoin='Accession.intended_location_id==Location.id')
    intended2_location = relation(
        'Location', primaryjoin='Accession.intended2_location_id==Location.id')

    @classmethod
    def get_next_code(cls, code_format=None):
        """
        Return the next available accession code.

        the format is stored in the `bauble` table.
        the format may contain a %PD, replaced by the plant delimiter.
        date formatting is applied.

        If there is an error getting the next code the None is returned.
        """
        # auto generate/increment the accession code
        session = db.Session()
        if code_format is None:
            code_format = cls.code_format
        format = code_format.replace('%PD', Plant.get_delimiter())
        today = datetime.date.today()
        format = today.strftime(format)
        if format.find('%{Y-1}') >= 0:
            format = format.replace('%{Y-1}', str(today.year - 1))
        start = unicode(format.rstrip('#'))
        if start == format:
            # fixed value
            return start
        digits = len(format) - len(start)
        format = start + '%%0%dd' % digits
        q = session.query(Accession.code).\
            filter(Accession.code.startswith(start))
        next = None
        try:
            if q.count() > 0:
                codes = [safe_int(row[0][len(start):]) for row in q]
                next = format % (max(codes)+1)
            else:
                next = format % 1
        except Exception, e:
            logger.debug(e)
            pass
        finally:
            session.close()
        return unicode(next)

    def search_view_markup_pair(self):
        """provide the two lines describing object for SearchView row.

        """
        first, second = (utils.xml_safe(unicode(self)),
                         self.species_str(markup=True))
        suffix = _("%(1)s plant groups in %(2)s location(s)") % {
            '1': len(set(self.plants)),
            '2': len(set(p.location for p in self.plants))}
        suffix = ('<span foreground="#555555" size="small" '
                  'weight="light"> - %s</span>') % suffix
        return first + suffix, second

    @property
    def parent_plant(self):
        try:
            return self.source.plant_propagation.plant
        except AttributeError:
            return None

    @property
    def propagations(self):
        import operator
        return reduce(operator.add, [p.propagations for p in self.plants], [])

    @property
    def pictures(self):
        import operator
        return reduce(operator.add, [p.pictures for p in self.plants], [])

    def __init__(self, *args, **kwargs):
        super(Accession, self).__init__(*args, **kwargs)
        self.__cached_species_str = {}

    @reconstructor
    def init_on_load(self):
        """
        Called instead of __init__() when an Accession is loaded from
        the database.
        """
        self.__cached_species_str = {}

    def invalidate_str_cache(self):
        self.__cached_species_str = {}

    def __str__(self):
        return self.code

    def species_str(self, authors=False, markup=False):
        """
        Return the string of the species with the id qualifier(id_qual)
        injected into the proper place.

        If the species isn't part of a session of if the species is dirty,
        i.e. in object_session(species).dirty, then a new string will be
        built even if the species hasn't been changeq since the last call
        to this method.
        """
        # WARNING: don't use session.is_modified() here because it
        # will query lots of dependencies
        try:
            cached = self.__cached_species_str[(markup, authors)]
        except KeyError:
            self.__cached_species_str[(markup, authors)] = None
            cached = None
        session = object_session(self.species)
        if session:
            # if not part of a session or if the species is dirty then
            # build a new string
            if cached is not None and self.species not in session.dirty:
                return cached
        if not self.species:
            return None

        # show a warning if the id_qual is aff. or cf. but the
        # id_qual_rank is None, but only show it once
        try:
            self.__warned_about_id_qual
        except AttributeError:
            self.__warned_about_id_qual = False
        if self.id_qual in ('aff.', 'cf.') and not self.id_qual_rank \
                and not self.__warned_about_id_qual:
            msg = _('If the id_qual is aff. or cf. '
                    'then id_qual_rank is required. %s ') % self.code
            logger.warning(msg)
            self.__warned_about_id_qual = True

        if self.id_qual:
            sp_str = self.species.str(
                authors, markup, remove_zws=True,
                qualification=(self.id_qual_rank, self.id_qual))
        else:
            sp_str = self.species.str(authors, markup, remove_zws=True)

        self.__cached_species_str[(markup, authors)] = sp_str
        return sp_str

    def markup(self):
        return '%s (%s)' % (self.code, self.species.markup())

    def as_dict(self):
        result = db.Serializable.as_dict(self)
        result['species'] = self.species.str(remove_zws=True, authors=False)
        if self.source and self.source.source_detail:
            result['contact'] = self.source.source_detail.name
        return result

    @classmethod
    def correct_field_names(cls, keys):
        for internal, exchange in [('species', 'taxon')]:
            if exchange in keys:
                keys[internal] = keys[exchange]
                del keys[exchange]

    @classmethod
    def compute_serializable_fields(cls, session, keys):
        logger.debug('compute_serializable_fields(session, %s)' % keys)
        result = {'species': None}
        keys = dict(keys)  # make copy
        if 'species' in keys:
            keys['taxon'] = keys['species']
            keys['rank'] = 'species'
        if 'rank' in keys and 'taxon' in keys:
            ## now we must connect the accession to the species it refers to
            if keys['rank'] == 'species':
                genus_name, epithet = keys['taxon'].split(' ', 1)
                sp_dict = {'ht-epithet': genus_name,
                           'epithet': epithet}
                result['species'] = Species.retrieve_or_create(
                    session, sp_dict, create=False)
            elif keys['rank'] == 'genus':
                result['species'] = Species.retrieve_or_create(
                    session, {'ht-epithet': keys['taxon'],
                              'epithet': u'sp'})
            elif keys['rank'] == 'familia':
                unknown_genus = 'Zzz-' + keys['taxon'][:-1]
                Genus.retrieve_or_create(
                    session, {'ht-epithet': keys['taxon'],
                              'epithet': unknown_genus})
                result['species'] = Species.retrieve_or_create(
                    session, {'ht-epithet': unknown_genus,
                              'epithet': u'sp'})
        return result

    @classmethod
    def retrieve(cls, session, keys):
        try:
            return session.query(cls).filter(
                cls.code == keys['code']).one()
        except:
            return None

    def top_level_count(self):
        sd = self.source and self.source.source_detail
        return {(1, 'Accessions'): 1,
                (2, 'Species'): set([self.species.id]),
                (3, 'Genera'): set([self.species.genus.id]),
                (4, 'Families'): set([self.species.genus.family.id]),
                (5, 'Plantings'): len(self.plants),
                (6, 'Living plants'): sum(p.quantity for p in self.plants),
                (7, 'Locations'): set([p.location.id for p in self.plants]),
                (8, 'Sources'): set(sd and [sd.id] or [])}


from bauble.plugins.garden.plant import Plant, PlantEditor


class AccessionEditorView(editor.GenericEditorView):
    """
    AccessionEditorView provide the view part of the
    model/view/presenter paradigm.  It also acts as the view for any
    child presenter contained within the AccessionEditorPresenter.

    The primary function of the view is setup an parts of the
    interface that don't chage due to user interaction.  Although it
    also provides some utility methods for changing widget states.
    """
    expanders_pref_map = {
        # 'acc_notes_expander': 'editor.accession.notes.expanded',
        # 'acc_source_expander': 'editor.accession.source.expanded'
        }

    _tooltips = {
        'acc_species_entry': _(
            "The species must be selected from the list of completions. "
            "To add a species use the Species editor."),
        'acc_code_entry': _("The accession ID must be a unique code"),
        'acc_id_qual_combo': (_("The ID Qualifier\n\n"
                                "Possible values: %s")
                              % utils.enum_values_str('accession.id_qual')),
        'acc_id_qual_rank_combo': _('The part of the taxon name that the id '
                                    'qualifier refers to.'),
        'acc_date_accd_entry': _('The date this species was accessioned.'),
        'acc_date_recvd_entry': _('The date this species was received.'),
        'acc_recvd_type_comboentry': _(
            'The type of the accessioned material.'),
        'acc_quantity_recvd_entry': _('The amount of plant material at the '
                                      'time it was accessioned.'),
        'intended_loc_comboentry': _('The intended location for plant '
                                     'material being accessioned.'),
        'intended2_loc_comboentry': _('The intended location for plant '
                                      'material being accessioned.'),
        'intended_loc_create_plant_checkbutton': _('Immediately create a plant at this location, using all plant material.'),

        'acc_prov_combo': (_('The origin or source of this accession.\n\n'
                             'Possible values: %s') %
                           ', '.join(i[1] for i in prov_type_values)),
        'acc_wild_prov_combo': (_('The wild status is used to clarify the '
                                  'provenance.\n\nPossible values: %s') %
                                ', '.join(i[1]
                                          for i in wild_prov_status_values)),
        'acc_private_check': _('Indicates whether this accession record '
                               'should be considered private.'),
        'acc_cancel_button': _('Cancel your changes.'),
        'acc_ok_button': _('Save your changes.'),
        'acc_ok_and_add_button': _('Save your changes and add a '
                                   'plant to this accession.'),
        'acc_next_button': _('Save your changes and add another '
                             'accession.'),

        'sources_code_entry': "ITF2 - E7 - Donor's Accession Identifier - donacc",
        }

    def __init__(self, parent=None):
        """

        """
        super(AccessionEditorView, self).\
            __init__(os.path.join(paths.lib_dir(), 'plugins', 'garden',
                                  'acc_editor.glade'),
                     parent=parent)
        self.attach_completion('acc_species_entry',
                               cell_data_func=self.species_cell_data_func,
                               match_func=self.species_match_func)
        self.set_accept_buttons_sensitive(False)
        self.restore_state()

        # TODO: at the moment this also sets up some of the view parts
        # of child presenters like the CollectionPresenter, etc.

        # datum completions
        completion = self.attach_completion('datum_entry',
                                            minimum_key_length=1,
                                            match_func=self.datum_match,
                                            text_column=0)
        model = gtk.ListStore(str)
        for abbr in sorted(datums.keys()):
            # TODO: should create a marked up string with the datum description
            model.append([abbr])
        completion.set_model(model)

        self.init_translatable_combo('acc_prov_combo', prov_type_values)
        self.init_translatable_combo('acc_wild_prov_combo',
                                     wild_prov_status_values)
        self.init_translatable_combo('acc_recvd_type_comboentry',
                                     recvd_type_values)
        adjustment = self.widgets.source_sw.get_vadjustment()
        adjustment.props.value = 0.0
        self.widgets.source_sw.set_vadjustment(adjustment)

        # set current page so we don't open the last one that was open
        self.widgets.notebook.set_current_page(0)

    def get_window(self):
        return self.widgets.accession_dialog

    def set_accept_buttons_sensitive(self, sensitive):
        '''
        set the sensitivity of all the accept/ok buttons for the editor dialog
        '''
        self.widgets.acc_ok_button.set_sensitive(sensitive)
        self.widgets.acc_ok_and_add_button.set_sensitive(sensitive)
        self.widgets.acc_next_button.set_sensitive(sensitive)

    def save_state(self):
        '''
        save the current state of the gui to the preferences
        '''
        for expander, pref in self.expanders_pref_map.iteritems():
            prefs.prefs[pref] = self.widgets[expander].get_expanded()

    def restore_state(self):
        '''
        restore the state of the gui from the preferences
        '''
        for expander, pref in self.expanders_pref_map.iteritems():
            expanded = prefs.prefs.get(pref, True)
            self.widgets[expander].set_expanded(expanded)

    def start(self):
        return self.get_window().run()

    @staticmethod
    # staticmethod ensures the AccessionEditorView gets garbage collected.
    def datum_match(completion, key, treeiter, data=None):
        datum = completion.get_model()[treeiter][0]
        words = datum.split(' ')
        for w in words:
            if w.lower().startswith(key.lower()):
                return True
        return False

    @staticmethod
    # staticmethod ensures the AccessionEditorView gets garbage collected.
    def species_match_func(completion, key, treeiter, data=None):
        species = completion.get_model()[treeiter][0]
        epg, eps = (species.str(remove_zws=True).lower() + ' ').split(' ')[:2]
        key_epg, key_eps = (key.lower() + ' ').split(' ')[:2]
        if not epg:
            epg = str(species.genus.epithet).lower()
        if (epg.startswith(key_epg) and eps.startswith(key_eps)):
            return True
        return False

    @staticmethod
    # staticmethod ensures the AccessionEditorView gets garbage collected.
    def species_cell_data_func(column, renderer, model, treeiter, data=None):
        v = model[treeiter][0]
        renderer.set_property(
            'text', '%s (%s)' % (v.str(authors=True), v.genus.family))


class VoucherPresenter(editor.GenericEditorPresenter):

    def __init__(self, parent, model, view, session):
        super(VoucherPresenter, self).__init__(model, view)
        self.parent_ref = weakref.ref(parent)
        self.session = session
        self._dirty = False
        #self.refresh_view()
        self.view.connect('voucher_add_button', 'clicked', self.on_add_clicked)
        self.view.connect('voucher_remove_button', 'clicked',
                          self.on_remove_clicked)
        self.view.connect('parent_voucher_add_button', 'clicked',
                          self.on_add_clicked, True)
        self.view.connect('parent_voucher_remove_button', 'clicked',
                          self.on_remove_clicked, True)

        def _voucher_data_func(column, cell, model, treeiter, prop):
            v = model[treeiter][0]
            cell.set_property('text', getattr(v, prop))

        def setup_column(tree, column, cell, prop):
            column = self.view.widgets[column]
            cell = self.view.widgets[cell]
            column.clear_attributes(cell)  # get rid of some warnings
            cell.props.editable = True
            self.view.connect(
                cell, 'edited', self.on_cell_edited, (tree, prop))
            column.set_cell_data_func(cell, _voucher_data_func, prop)

        setup_column('voucher_treeview', 'voucher_herb_column',
                     'voucher_herb_cell', 'herbarium')
        setup_column('voucher_treeview', 'voucher_code_column',
                     'voucher_code_cell', 'code')

        setup_column('parent_voucher_treeview', 'parent_voucher_herb_column',
                     'parent_voucher_herb_cell', 'herbarium')
        setup_column('parent_voucher_treeview', 'parent_voucher_code_column',
                     'parent_voucher_code_cell', 'code')

        # intialize vouchers treeview
        treeview = self.view.widgets.voucher_treeview
        utils.clear_model(treeview)
        model = gtk.ListStore(object)
        for voucher in self.model.vouchers:
            if not voucher.parent_material:
                model.append([voucher])
        treeview.set_model(model)

        # initialize parent vouchers treeview
        treeview = self.view.widgets.parent_voucher_treeview
        utils.clear_model(treeview)
        model = gtk.ListStore(object)
        for voucher in self.model.vouchers:
            if voucher.parent_material:
                model.append([voucher])
        treeview.set_model(model)

    def is_dirty(self):
        return self._dirty

    def on_cell_edited(self, cell, path, new_text, data):
        treeview, prop = data
        treemodel = self.view.widgets[treeview].get_model()
        voucher = treemodel[path][0]
        if getattr(voucher, prop) == new_text:
            return  # didn't change
        setattr(voucher, prop, utils.utf8(new_text))
        self._dirty = True
        self.parent_ref().refresh_sensitivity()

    def on_remove_clicked(self, button, parent=False):
        if parent:
            treeview = self.view.widgets.parent_voucher_treeview
        else:
            treeview = self.view.widgets.voucher_treeview
        model, treeiter = treeview.get_selection().get_selected()
        voucher = model[treeiter][0]
        voucher.accession = None
        model.remove(treeiter)
        self._dirty = True
        self.parent_ref().refresh_sensitivity()

    def on_add_clicked(self, button, parent=False):
        """
        """
        if parent:
            treeview = self.view.widgets.parent_voucher_treeview
        else:
            treeview = self.view.widgets.voucher_treeview
        voucher = Voucher()
        voucher.accession = self.model
        voucher.parent_material = parent
        model = treeview.get_model()
        treeiter = model.insert(0, [voucher])
        path = model.get_path(treeiter)
        column = treeview.get_column(0)
        treeview.set_cursor(path, column, start_editing=True)


class VerificationPresenter(editor.GenericEditorPresenter):

    """
    VerificationPresenter

    :param parent:
    :param model:
    :param view:
    :param session:
    """
    PROBLEM_INVALID_DATE = random()

    def __init__(self, parent, model, view, session):
        super(VerificationPresenter, self).__init__(model, view)
        self.parent_ref = weakref.ref(parent)
        self.session = session
        self.view.connect('ver_add_button', 'clicked', self.on_add_clicked)

        # remove any verification boxes that would have been added to
        # the widget in a previous run
        box = self.view.widgets.verifications_parent_box
        map(box.remove, box.get_children())

        # order by date of the existing verifications
        for ver in model.verifications:
            expander = self.add_verification_box(model=ver)
            expander.set_expanded(False)  # all are collapsed to start

        # if no verifications were added then add an empty VerificationBox
        if len(self.view.widgets.verifications_parent_box.get_children()) < 1:
            self.add_verification_box()

        # expand the first verification expander
        self.view.widgets.verifications_parent_box.get_children()[0].\
            set_expanded(True)
        self._dirty = False

    def is_dirty(self):
        return self._dirty

    def refresh_view(self):
        pass

    def on_add_clicked(self, *args):
        self.add_verification_box()

    def add_verification_box(self, model=None):
        """
        :param model:
        """
        box = VerificationPresenter.VerificationBox(self, model)
        self.view.widgets.verifications_parent_box.pack_start(
            box, expand=False, fill=False)
        self.view.widgets.verifications_parent_box.reorder_child(box, 0)
        box.show_all()
        return box

    class VerificationBox(gtk.HBox):

        def __init__(self, parent, model):
            super(VerificationPresenter.VerificationBox, self).__init__(self)
            check(not model or isinstance(model, Verification))

            self.presenter = weakref.ref(parent)
            self.model = model
            if not self.model:
                self.model = Verification()
                self.model.prev_species = self.presenter().model.species

            # copy UI definitions from the accession editor glade file
            filename = os.path.join(paths.lib_dir(), "plugins", "garden",
                                    "acc_editor.glade")
            xml = etree.parse(filename)
            el = xml.find("//object[@id='ver_box']")
            builder = gtk.Builder()
            s = '<interface>%s</interface>' % etree.tostring(el)
            if sys.platform == 'win32':
                # NOTE: PyGTK for Win32 is broken so we have to include
                # this little hack
                #
                # TODO: is this only a specific set of version of
                # PyGTK/GTK...it was only tested with PyGTK 2.12
                builder.add_from_string(s, -1)
            else:
                builder.add_from_string(s)
            self.widgets = utils.BuilderWidgets(builder)

            ver_box = self.widgets.ver_box
            self.widgets.remove_parent(ver_box)
            self.pack_start(ver_box, expand=True, fill=True)

            # verifier entry
            entry = self.widgets.ver_verifier_entry
            if self.model.verifier:
                entry.props.text = self.model.verifier
            self.presenter().view.connect(
                entry, 'changed', self.on_entry_changed, 'verifier')

            # date entry
            self.date_entry = self.widgets.ver_date_entry
            if self.model.date:
                utils.set_widget_value(self.date_entry, self.model.date)
            else:
                self.date_entry.props.text = utils.today_str()
            self.presenter().view.connect(
                self.date_entry, 'changed', self.on_date_entry_changed)

            # reference entry
            ref_entry = self.widgets.ver_ref_entry
            if self.model.reference:
                ref_entry.props.text = self.model.reference
            self.presenter().view.connect(
                ref_entry, 'changed', self.on_entry_changed, 'reference')

            # species entries
            def sp_get_completions(text):
                query = self.presenter().session.query(Species).join('genus').\
                    filter(utils.ilike(Genus.genus, '%s%%' % text)).\
                    filter(Species.id != self.model.id).\
                    order_by(Species.sp)
                return query

            def sp_cell_data_func(col, cell, model, treeiter, data=None):
                v = model[treeiter][0]
                cell.set_property('text', '%s (%s)' %
                                  (v.str(authors=True),
                                   v.genus.family))

            ver_prev_taxon_entry = self.widgets.ver_prev_taxon_entry

            def on_prevsp_select(value):
                self.set_model_attr('prev_species', value)

            self.presenter().view.attach_completion(
                ver_prev_taxon_entry, sp_cell_data_func)
            if self.model.prev_species:
                ver_prev_taxon_entry.props.text = self.model.prev_species
            self.presenter().assign_completions_handler(
                ver_prev_taxon_entry, sp_get_completions, on_prevsp_select)

            ver_new_taxon_entry = self.widgets.ver_new_taxon_entry

            def on_sp_select(value):
                self.set_model_attr('species', value)

            self.presenter().view.attach_completion(
                ver_new_taxon_entry, sp_cell_data_func)
            if self.model.species:
                ver_new_taxon_entry.props.text = self.model.species
            self.presenter().assign_completions_handler(
                ver_new_taxon_entry, sp_get_completions, on_sp_select)

            ## add a taxon implies setting the ver_new_taxon_entry
            self.presenter().view.connect(
                self.widgets.ver_taxon_add_button, 'clicked',
                self.on_taxon_add_button_clicked,
                ver_new_taxon_entry)

            combo = self.widgets.ver_level_combo
            renderer = gtk.CellRendererText()
            renderer.props.wrap_mode = pango.WRAP_WORD
            # TODO: should auto calculate the wrap width with a
            # on_size_allocation callback
            renderer.props.wrap_width = 400
            combo.pack_start(renderer, True)

            def cell_data_func(col, cell, model, treeiter):
                level = model[treeiter][0]
                descr = model[treeiter][1]
                cell.set_property('markup', '<b>%s</b>  :  %s'
                                  % (level, descr))
            combo.set_cell_data_func(renderer, cell_data_func)
            model = gtk.ListStore(int, str)
            for level, descr in ver_level_descriptions.iteritems():
                model.append([level, descr])
            combo.set_model(model)
            if self.model.level:
                utils.set_widget_value(combo, self.model.level)
            self.presenter().view.connect(combo, 'changed',
                                          self.on_level_combo_changed)

            # notes text view
            textview = self.widgets.ver_notes_textview
            textview.set_border_width(1)
            buff = gtk.TextBuffer()
            if self.model.notes:
                buff.props.text = self.model.notes
            textview.set_buffer(buff)
            self.presenter().view.connect(buff, 'changed',
                                          self.on_entry_changed, 'notes')

            # remove button
            button = self.widgets.ver_remove_button
            self._sid = self.presenter().view.connect(
                button, 'clicked', self.on_remove_button_clicked)

            # copy to general tab
            button = self.widgets.ver_copy_to_taxon_general
            self._sid = self.presenter().view.connect(
                button, 'clicked', self.on_copy_to_taxon_general_clicked)

            self.update_label()

        def on_date_entry_changed(self, entry, data=None):
            from bauble.editor import ValidatorError
            value = None
            PROBLEM = 'INVALID_DATE'
            try:
                value = editor.DateValidator().to_python(entry.props.text)
            except ValidatorError, e:
                logger.debug(e)
                self.presenter().add_problem(PROBLEM, entry)
            else:
                self.presenter().remove_problem(PROBLEM, entry)
            self.set_model_attr('date', value)

        def on_copy_to_taxon_general_clicked(self, button):
            if self.model.species is None:
                return
            parent = self.get_parent()
            msg = _("Are you sure you want to copy this verification to the general taxon?")
            if not utils.yes_no_dialog(msg):
                return
            # copy verification species to general tab
            if self.model.accession:
                self.presenter().parent_ref().view.widgets.acc_species_entry.\
                    set_text(utils.utf8(self.model.species))
                self.presenter()._dirty = True
                self.presenter().parent_ref().refresh_sensitivity()

        def on_remove_button_clicked(self, button):
            parent = self.get_parent()
            msg = _("Are you sure you want to remove this verification?")
            if not utils.yes_no_dialog(msg):
                return
            if parent:
                parent.remove(self)

            # disconnect clicked signal to make garbage collecting work
            button.disconnect(self._sid)

            # remove verification from accession
            if self.model.accession:
                self.model.accession.verifications.remove(self.model)
            self.presenter()._dirty = True
            self.presenter().parent_ref().refresh_sensitivity()

        def on_entry_changed(self, entry, attr):
            text = entry.props.text
            if not text:
                self.set_model_attr(attr, None)
            else:
                self.set_model_attr(attr, utils.utf8(text))

        def on_level_combo_changed(self, combo, *args):
            i = combo.get_active_iter()
            level = combo.get_model()[i][0]
            self.set_model_attr('level', level)

        def set_model_attr(self, attr, value):
            setattr(self.model, attr, value)
            if attr != 'date' and not self.model.date:
                # When we create a new verification box we set today's date
                # in the GtkEntry but not in the model so the presenter
                # doesn't appear dirty.  Now that the user is setting
                # something, we trigger the 'changed' signal on the 'date'
                # entry as well, by first clearing the entry then setting it
                # to its intended value.
                tmp = self.date_entry.props.text
                self.date_entry.props.text = ''
                self.date_entry.props.text = tmp
            # if the verification isn't yet associated with an accession
            # then set the accession when we start changing values, this way
            # we can setup a dummy verification in the interface
            if not self.model.accession:
                self.presenter().model.verifications.append(self.model)
            self.presenter()._dirty = True
            self.update_label()
            self.presenter().parent_ref().refresh_sensitivity()

        def update_label(self):
            parts = []
            # TODO: the parts string isn't being translated
            if self.model.date:
                parts.append('<b>%(date)s</b> : ')
            if self.model.species:
                parts.append(_('verified as %(species)s '))
            if self.model.verifier:
                parts.append(_('by %(verifier)s'))
            label = ' '.join(parts) % dict(date=self.model.date,
                                           species=self.model.species,
                                           verifier=self.model.verifier)
            self.widgets.ver_expander_label.props.use_markup = True
            self.widgets.ver_expander_label.props.label = label

        def set_expanded(self, expanded):
            self.widgets.ver_expander.props.expanded = expanded

        def on_taxon_add_button_clicked(self, button, taxon_entry):
            ## we come here when we are adding a Verification, and the
            ## Verification wants to refer to a new taxon.

            generic_taxon_add_action(
                self.model, self.presenter().view, self.presenter(),
                self.presenter().parent_ref(),
                button, taxon_entry)


class SourcePresenter(editor.GenericEditorPresenter):
    """
    SourcePresenter
    :param parent:
    :param model:
    :param view:
    :param session:
    """

    garden_prop_str = _('Garden Propagation')

    def __init__(self, parent, model, view, session):
        super(SourcePresenter, self).__init__(model, view)
        self.parent_ref = weakref.ref(parent)
        self.session = session
        self._dirty = False

        self.view.connect('new_source_button', 'clicked',
                          self.on_new_source_button_clicked)

        self.view.widgets.source_garden_prop_box.props.visible = False
        self.view.widgets.source_sw.props.visible = False
        self.view.widgets.source_none_label.props.visible = True

        # populate the source combo
        def on_select(source):
            if not source:
                self.model.source = None
            elif isinstance(source, Contact):
                self.model.source = self.source
                self.model.source.source_detail = source
            elif source == self.garden_prop_str:
                self.model.source = self.source
                self.model.source.source_detail = None
            else:
                logger.warning('unknown source: %s' % source)
            #self.model.source = self.source
            #self.model.source.source_detail = source_detail

        self.init_source_comboentry(on_select)

        if self.model.source:
            self.source = self.model.source
            self.view.widgets.sources_code_entry.props.text = \
                self.source.sources_code
        else:
            self.source = Source()
            # self.model.source will be reset the None if the source
            # combo value is None in commit_changes()
            self.model.source = self.source
            self.view.widgets.sources_code_entry.props.text = ''

        if self.source.collection:
            self.collection = self.source.collection
            enabled = True
        else:
            self.collection = Collection()
            self.session.add(self.collection)
            enabled = False
        self.view.widgets.source_coll_add_button.props.sensitive = not enabled
        self.view.widgets.source_coll_remove_button.props.sensitive = enabled
        self.view.widgets.source_coll_expander.props.expanded = enabled
        self.view.widgets.source_coll_expander.props.sensitive = enabled

        if self.source.propagation:
            self.propagation = self.source.propagation
            enabled = True
        else:
            self.propagation = Propagation()
            self.session.add(self.propagation)
            enabled = False
        self.view.widgets.source_prop_add_button.props.sensitive = not enabled
        self.view.widgets.source_prop_remove_button.props.sensitive = enabled
        self.view.widgets.source_prop_expander.props.expanded = enabled
        self.view.widgets.source_prop_expander.props.sensitive = enabled

        # TODO: all the sub presenters here take the
        # AccessionEditorPresenter as their parent though their real
        # parent is this SourcePresenter....having the
        # AccessionEditorPresenter is easier since what we really need
        # access to is refresh_sensitivity() and possible
        # set_model_attr() but having the SourcePresenter would be
        # more "correct"

        # presenter that allows us to create a new Propagation that is
        # specific to this Source and not attached to any Plant
        self.source_prop_presenter = SourcePropagationPresenter(
            self.parent_ref(), self.propagation, view, session)
        self.source_prop_presenter.register_clipboard()

        # presenter that allows us to select an existing propagation
        self.prop_chooser_presenter = PropagationChooserPresenter(
            self.parent_ref(), self.source, view, session)

        # collection data
        self.collection_presenter = CollectionPresenter(
            self.parent_ref(), self.collection, view, session)
        self.collection_presenter.register_clipboard()

        def on_changed(entry, *args):
            text = entry.props.text
            if text.strip():
                self.source.sources_code = utils.utf8(text)
            else:
                self.source.sources_code = None
            self._dirty = True
            self.refresh_sensitivity()
        self.view.connect('sources_code_entry', 'changed', on_changed)

        self.view.connect('source_coll_add_button', 'clicked',
                          self.on_coll_add_button_clicked)
        self.view.connect('source_coll_remove_button', 'clicked',
                          self.on_coll_remove_button_clicked)
        self.view.connect('source_prop_add_button', 'clicked',
                          self.on_prop_add_button_clicked)
        self.view.connect('source_prop_remove_button', 'clicked',
                          self.on_prop_remove_button_clicked)

    def all_problems(self):
        """
        Return a union of all the problems from this presenter and
        child presenters
        """
        return (self.problems | self.collection_presenter.problems |
                self.prop_chooser_presenter.problems |
                self.source_prop_presenter.problems)

    def cleanup(self):
        super(SourcePresenter, self).cleanup()
        self.collection_presenter.cleanup()
        self.prop_chooser_presenter.cleanup()
        self.source_prop_presenter.cleanup()

    def start(self):
        active = None
        if self.model.source:
            if self.model.source.source_detail:
                active = self.model.source.source_detail
            elif self.model.source.plant_propagation:
                active = self.garden_prop_str
        self.populate_source_combo(active)

    def is_dirty(self):
        return self._dirty or self.source_prop_presenter.is_dirty() or \
            self.prop_chooser_presenter.is_dirty() or \
            self.collection_presenter.is_dirty()

    def refresh_sensitivity(self):
        logger.warning('refresh_sensitivity: %s' % str(self.problems))
        self.parent_ref().refresh_sensitivity()

    def on_coll_add_button_clicked(self, *args):
        self.model.source.collection = self.collection
        self.view.widgets.source_coll_expander.props.expanded = True
        self.view.widgets.source_coll_expander.props.sensitive = True
        self.view.widgets.source_coll_add_button.props.sensitive = False
        self.view.widgets.source_coll_remove_button.props.sensitive = True
        self._dirty = True
        self.refresh_sensitivity()

    def on_coll_remove_button_clicked(self, *args):
        self.model.source.collection = None
        self.view.widgets.source_coll_expander.props.expanded = False
        self.view.widgets.source_coll_expander.props.sensitive = False
        self.view.widgets.source_coll_add_button.props.sensitive = True
        self.view.widgets.source_coll_remove_button.props.sensitive = False
        self._dirty = True
        self.refresh_sensitivity()

    def on_prop_add_button_clicked(self, *args):
        self.model.source.propagation = self.propagation
        self.view.widgets.source_prop_expander.props.expanded = True
        self.view.widgets.source_prop_expander.props.sensitive = True
        self.view.widgets.source_prop_add_button.props.sensitive = False
        self.view.widgets.source_prop_remove_button.props.sensitive = True
        self._dirty = True
        self.refresh_sensitivity()

    def on_prop_remove_button_clicked(self, *args):
        self.model.source.propagation = None
        self.view.widgets.source_prop_expander.props.expanded = False
        self.view.widgets.source_prop_expander.props.sensitive = False
        self.view.widgets.source_prop_add_button.props.sensitive = True
        self.view.widgets.source_prop_remove_button.props.sensitive = False
        self._dirty = True
        self.refresh_sensitivity()

    def on_new_source_button_clicked(self, *args):
        """
        Opens a new ContactEditor when clicked and repopulates the
        source combo if a new Contact is created.
        """
        committed = create_contact(parent=self.view.get_window())
        new_detail = None
        if committed:
            new_detail = committed[0]
            self.session.add(new_detail)
            self.populate_source_combo(new_detail)

    def populate_source_combo(self, active=None):
        """
        If active=None then set whatever was previously active before
        repopulating the combo.
        """
        combo = self.view.widgets.acc_source_comboentry
        if not active:
            treeiter = combo.get_active_iter()
            if treeiter:
                active = combo.get_model()[treeiter][0]
        combo.set_model(None)
        model = gtk.ListStore(object)
        none_iter = model.append([''])
        model.append([self.garden_prop_str])
        map(lambda x: model.append([x]), self.session.query(Contact))
        combo.set_model(model)
        combo.child.get_completion().set_model(model)

        combo._populate = True
        if active:
            results = utils.search_tree_model(model, active)
            if results:
                combo.set_active_iter(results[0])
        else:
            combo.set_active_iter(none_iter)
        combo._populate = False

    def init_source_comboentry(self, on_select):
        """
        A comboentry that allows the location to be entered requires
        more custom setup than view.attach_completion and
        self.assign_simple_handler can provides.  This method allows us to
        have completions on the location entry based on the location code,
        location name and location string as well as selecting a location
        from a combo drop down.

        :param on_select: called when an item is selected
        """
        PROBLEM = 'unknown_source'

        def cell_data_func(col, cell, model, treeiter, data=None):
            cell.props.text = utils.utf8(model[treeiter][0])

        combo = self.view.widgets.acc_source_comboentry
        combo.clear()
        cell = gtk.CellRendererText()
        combo.pack_start(cell)
        combo.set_cell_data_func(cell, cell_data_func)

        completion = gtk.EntryCompletion()
        cell = gtk.CellRendererText()  # set up the completion renderer
        completion.pack_start(cell)
        completion.set_cell_data_func(cell, cell_data_func)

        def match_func(completion, key, treeiter, data=None):
            model = completion.get_model()
            value = model[treeiter][0]
            # allows completions of source details by their ID
            if utils.utf8(value).lower().startswith(key.lower()) or \
                    (isinstance(value, Contact) and
                     str(value.id).startswith(key)):
                return True
            return False
        completion.set_match_func(match_func)

        entry = combo.child
        entry.set_completion(completion)

        def update_visible():
            widget_visibility = dict(source_sw=False,
                                     source_garden_prop_box=False,
                                     source_none_label=False)
            if entry.props.text == self.garden_prop_str:
                widget_visibility['source_garden_prop_box'] = True
            elif not self.model.source or not self.model.source.source_detail:
                widget_visibility['source_none_label'] = True
            else:
                #self.model.source.source_detail = value
                widget_visibility['source_sw'] = True
            for widget, value in widget_visibility.iteritems():
                self.view.widgets[widget].props.visible = value
            self.view.widgets.source_alignment.props.sensitive = True

        def on_match_select(completion, model, treeiter):
            value = model[treeiter][0]
            # TODO: should we reset/store the entry values if the
            # source is changed and restore them if they are switched
            # back
            if not value:
                combo.child.props.text = ''
                on_select(None)
            else:
                combo.child.props.text = utils.utf8(value)
                on_select(value)

            # don't set the model as dirty if this is called during
            # populate_source_combo
            if not combo._populate:
                self._dirty = True
                self.refresh_sensitivity()
            return True
        self.view.connect(completion, 'match-selected', on_match_select)

        def on_entry_changed(entry, data=None):
            text = utils.utf8(entry.props.text)
            # see if the text matches a completion string
            comp = entry.get_completion()

            def _cmp(row, data):
                val = row[0]
                if (utils.utf8(val) == data or
                        (isinstance(val, Contact) and val.id == data)):
                    return True
                else:
                    return False

            found = utils.search_tree_model(comp.get_model(), text, _cmp)
            if len(found) == 1:
                # the model and iter here should technically be the tree
                comp.emit('match-selected', comp.get_model(), found[0])
                self.remove_problem(PROBLEM, entry)
            else:
                self.add_problem(PROBLEM, entry)
            update_visible()
            return True
        self.view.connect(entry, 'changed', on_entry_changed)

        def on_combo_changed(combo, *args):
            active = combo.get_active_iter()
            if active:
                detail = combo.get_model()[active][0]
                # set the text value on the entry since it does all the
                # validation
                if not detail:
                    combo.child.props.text = ''
                else:
                    combo.child.props.text = utils.utf8(detail)
            update_visible()
            return True

        self.view.connect(combo, 'changed', on_combo_changed)


class AccessionEditorPresenter(editor.GenericEditorPresenter):

    widget_to_field_map = {'acc_code_entry': 'code',
                           'acc_id_qual_combo': 'id_qual',
                           'acc_date_accd_entry': 'date_accd',
                           'acc_date_recvd_entry': 'date_recvd',
                           'acc_recvd_type_comboentry': 'recvd_type',
                           'acc_quantity_recvd_entry': 'quantity_recvd',
                           'intended_loc_comboentry': 'intended_location',
                           'intended2_loc_comboentry': 'intended2_location',
                           'acc_prov_combo': 'prov_type',
                           'acc_wild_prov_combo': 'wild_prov_status',
                           'acc_species_entry': 'species',
                           'acc_private_check': 'private',
                           'intended_loc_create_plant_checkbutton': 'create_plant',
                           }

    PROBLEM_INVALID_DATE = random()
    PROBLEM_DUPLICATE_ACCESSION = random()
    PROBLEM_ID_QUAL_RANK_REQUIRED = random()

    def __init__(self, model, view):
        '''
        :param model: an instance of class Accession
        ;param view: an instance of AccessionEditorView
        '''
        super(AccessionEditorPresenter, self).__init__(model, view)
        self.create_toolbar()
        self._dirty = False
        self.session = object_session(model)
        self._original_code = self.model.code
        self.current_source_box = None
        model.create_plant = False

        # set the default code and add it to the top of the code formats
        self.populate_code_formats(model.code or '')
        self.view.widget_set_value('acc_code_format_comboentry',
                                   model.code or '')
        if not model.code:
            model.code = model.get_next_code()
            if self.model.species:
                self._dirty = True

        self.ver_presenter = VerificationPresenter(self, self.model, self.view,
                                                   self.session)
        self.voucher_presenter = VoucherPresenter(self, self.model, self.view,
                                                  self.session)
        self.source_presenter = SourcePresenter(self, self.model, self.view,
                                                self.session)

        notes_parent = self.view.widgets.notes_parent_box
        notes_parent.foreach(notes_parent.remove)
        self.notes_presenter = \
            editor.NotesPresenter(self, 'notes', notes_parent)

        self.init_enum_combo('acc_id_qual_combo', 'id_qual')

        # init id_qual_rank
        utils.setup_text_combobox(self.view.widgets.acc_id_qual_rank_combo)
        self.refresh_id_qual_rank_combo()

        def on_changed(combo, *args):
            it = combo.get_active_iter()
            if not it:
                self.model.id_qual_rank = None
                return
            text, col = combo.get_model()[it]
            self.set_model_attr('id_qual_rank', utils.utf8(col))
        self.view.connect('acc_id_qual_rank_combo', 'changed', on_changed)

        # TODO: refresh_view() will fire signal handlers for any
        # connected widgets and can be tricky with resetting values
        # that already exist in the model.  Although this usually
        # isn't a problem, it is sloppy.  We need a better way to update
        # the widgets without firing signal handlers.

        # put model values in view before any handlers are connected
        self.refresh_view()

        # connect signals
        def sp_get_completions(text):
            query = self.session.query(Species)
            genus = ''
            try:
                genus = text.split(' ')[0]
            except Exception:
                pass
            from utils import ilike
            return query.filter(
                and_(Species.genus_id == Genus.id,
                     or_(ilike(Genus.genus, '%s%%' % text),
                         ilike(Genus.genus, '%s%%' % genus)))).\
                order_by(Species.sp)

        def on_select(value):
            logger.debug('on select: %s' % value)
            if isinstance(value, StringTypes):
                value = Species.retrieve(
                    self.session, {'species': value})
            def set_model(v):
                self.set_model_attr('species', v)
                self.refresh_id_qual_rank_combo()
            for kid in self.view.widgets.message_box_parent.get_children():
                self.view.widgets.remove_parent(kid)
            set_model(value)
            if not value:
                return
            syn = self.session.query(SpeciesSynonym).\
                filter(SpeciesSynonym.synonym_id == value.id).first()
            if not syn:
                set_model(value)
                return
            msg = _('The species <b>%(synonym)s</b> is a synonym of '
                    '<b>%(species)s</b>.\n\nWould you like to choose '
                    '<b>%(species)s</b> instead?') % \
                {'synonym': syn.synonym, 'species': syn.species}
            box = None

            def on_response(button, response):
                self.view.widgets.remove_parent(box)
                box.destroy()
                if response:
                    completion = self.view.widgets.acc_species_entry.\
                        get_completion()
                    utils.clear_model(completion)
                    model = gtk.ListStore(object)
                    model.append([syn.species])
                    completion.set_model(model)
                    self.view.widgets.acc_species_entry.\
                        set_text(utils.utf8(syn.species))
                    set_model(syn.species)
            box = self.view.add_message_box(utils.MESSAGE_BOX_YESNO)
            box.message = msg
            box.on_response = on_response
            box.show()

        self.assign_completions_handler('acc_species_entry',
                                        sp_get_completions,
                                        on_select=on_select)
        self.assign_simple_handler('acc_prov_combo', 'prov_type')
        self.assign_simple_handler('acc_wild_prov_combo', 'wild_prov_status')

        # connect recvd_type comboentry widget and child entry
        self.view.connect('acc_recvd_type_comboentry', 'changed',
                          self.on_recvd_type_comboentry_changed)
        self.view.connect(self.view.widgets.acc_recvd_type_comboentry.child,
                          'changed', self.on_recvd_type_entry_changed)

        self.view.connect('acc_code_entry', 'changed',
                          self.on_acc_code_entry_changed)

        # date received
        self.view.connect('acc_date_recvd_entry', 'changed',
                          self.on_date_entry_changed, 'date_recvd')
        utils.setup_date_button(self.view, 'acc_date_recvd_entry',
                                'acc_date_recvd_button')

        # date accessioned
        self.view.connect('acc_date_accd_entry', 'changed',
                          self.on_date_entry_changed, 'date_accd')
        utils.setup_date_button(self.view, 'acc_date_accd_entry',
                                'acc_date_accd_button')

        self.view.connect(
            self.view.widgets.intended_loc_add_button,
            'clicked',
            self.on_loc_button_clicked,
            self.view.widgets.intended_loc_comboentry,
            'intended_location')

        self.view.connect(
            self.view.widgets.intended2_loc_add_button,
            'clicked',
            self.on_loc_button_clicked,
            self.view.widgets.intended2_loc_comboentry,
            'intended2_location')

        ## add a taxon implies setting the acc_species_entry
        self.view.connect(
            self.view.widgets.acc_taxon_add_button, 'clicked',
            lambda b, w: generic_taxon_add_action(
                self.model, self.view, self, self, b, w),
            self.view.widgets.acc_species_entry)

        self.has_plants = len(model.plants) > 0
        view.widget_set_sensitive('intended_loc_create_plant_checkbutton', not self.has_plants)
        def refresh_create_plant_checkbutton_sensitivity(*args):
            if self.has_plants:
                view.widget_set_sensitive('intended_loc_create_plant_checkbutton', False)
                return
            location_chosen = bool(self.model.intended_location)
            has_quantity = self.model.quantity_recvd and bool(int(self.model.quantity_recvd)) or False
            view.widget_set_sensitive('intended_loc_create_plant_checkbutton', has_quantity and location_chosen)

        self.assign_simple_handler(
            'acc_quantity_recvd_entry', 'quantity_recvd')
        self.view.connect_after('acc_quantity_recvd_entry', 'changed',
                                refresh_create_plant_checkbutton_sensitivity)
        self.assign_simple_handler('acc_id_qual_combo', 'id_qual',
                                   editor.UnicodeOrNoneValidator())
        self.assign_simple_handler('acc_private_check', 'private')

        from bauble.plugins.garden import init_location_comboentry
        def on_loc1_select(value):
            self.set_model_attr('intended_location', value)
            refresh_create_plant_checkbutton_sensitivity()

        init_location_comboentry(
            self, self.view.widgets.intended_loc_comboentry,
            on_loc1_select, required=False)

        def on_loc2_select(value):
            self.set_model_attr('intended2_location', value)
        init_location_comboentry(
            self, self.view.widgets.intended2_loc_comboentry,
            on_loc2_select, required=False)

        self.refresh_sensitivity()
        refresh_create_plant_checkbutton_sensitivity()

        if self.model not in self.session.new:
            self.view.widgets.acc_ok_and_add_button.set_sensitive(True)

    def populate_code_formats(self, entry_one=None, values=None):
        logger.debug('populate_code_formats %s %s' % (entry_one, values))
        ls = self.view.widgets.acc_code_format_liststore
        if entry_one is None:
            entry_one = ls.get_value(ls.get_iter_first(), 0)
        ls.clear()
        ls.append([entry_one])
        if values is None:
            query = self.session.\
                query(meta.BaubleMeta).\
                filter(meta.BaubleMeta.name.like(u'acidf_%')).\
                order_by(meta.BaubleMeta.name)
            if query.count():
                Accession.code_format = query.first().value
            values = [r.value for r in query]
        for v in values:
            ls.append([v])

    def on_acc_code_format_comboentry_changed(self, widget, *args):
        code_format = self.view.widget_get_value(widget)
        code = Accession.get_next_code(code_format)
        self.view.widget_set_value('acc_code_entry', code)

    def on_acc_code_format_edit_btn_clicked(self, widget, *args):
        view = editor.GenericEditorView(
            os.path.join(paths.lib_dir(), 'plugins', 'garden',
                         'acc_editor.glade'),
            root_widget_name='acc_codes_dialog')
        ls = view.widgets.acc_codes_liststore
        ls.clear()
        query = self.session.\
            query(meta.BaubleMeta).\
            filter(meta.BaubleMeta.name.like(u'acidf_%')).\
            order_by(meta.BaubleMeta.name)
        for i, row in enumerate(query):
            ls.append([i+1, row.value])
        ls.append([len(ls)+1, ''])

        class Presenter(editor.GenericEditorPresenter):
            def on_acc_cf_renderer_edited(self, widget, iter, value):
                i = ls.get_iter_from_string(str(iter))
                ls.set_value(i, 1, value)
                if ls.iter_next(i) is None:
                    if value:
                        ls.append([len(ls)+1, ''])
                elif value == '':
                    ls.remove(i)
                    while i:
                        ls.set_value(i, 0, ls.get_value(i, 0)-1)
                        i = ls.iter_next(i)

        presenter = Presenter(ls, view, session=db.Session())
        if presenter.start() > 0:
            presenter.session.\
                query(meta.BaubleMeta).\
                filter(meta.BaubleMeta.name.like(u'acidf_%')).\
                delete(synchronize_session=False)
            i = 1
            iter = ls.get_iter_first()
            values = []
            while iter:
                value = ls.get_value(iter, 1)
                iter = ls.iter_next(iter)
                i += 1
                if not value:
                    continue
                obj = meta.BaubleMeta(name=u'acidf_%02d' % i,
                                      value=value)
                values.append(value)
                presenter.session.add(obj)
            self.populate_code_formats(values=values)
            presenter.session.commit()
        presenter.session.close()

    def refresh_id_qual_rank_combo(self):
        """
        Populate the id_qual_rank_combo with the parts of the species string
        """
        combo = self.view.widgets.acc_id_qual_rank_combo
        utils.clear_model(combo)
        if not self.model.species:
            return
        model = gtk.ListStore(str, str)
        species = self.model.species
        it = model.append([str(species.genus), 'genus'])
        active = None
        if self.model.id_qual_rank == 'genus':
            active = it
        it = model.append([str(species.sp), u'sp'])
        if self.model.id_qual_rank == u'sp':
            active = it

        infrasp_parts = []
        for level in (1, 2, 3, 4):
            infrasp = [s for s in species.get_infrasp(level) if s is not None]
            if infrasp:
                infrasp_parts.append(' '.join(infrasp))
        if infrasp_parts:
            it = model.append([' '.join(infrasp_parts), 'infrasp'])
            if self.model.id_qual_rank == 'infrasp':
                active = it

        # if species.infrasp:
        #     s = ' '.join([str(isp) for isp in species.infrasp])
        #     if len(s) > 32:
        #         s = '%s...' % s[:29]
        #     it = model.append([s, 'infrasp'])
        #     if self.model.id_qual_rank == 'infrasp':
        #         active = it

        it = model.append(('', None))
        if not active:
            active = it
        combo.set_model(model)
        combo.set_active_iter(active)

    def on_loc_button_clicked(self, button, target_widget, target_field):
        logger.debug('on_loc_button_clicked %s, %s, %s, %s' %
                     (self, button, target_widget, target_field))
        from bauble.plugins.garden.location import LocationEditor
        editor = LocationEditor(parent=self.view.get_window())
        if editor.start():
            location = editor.presenter.model
            self.session.add(location)
            self.remove_problem(None, target_widget)
            self.view.widget_set_value(target_widget, location)
            self.set_model_attr(target_field, location)

    def is_dirty(self):
        presenters = [self.ver_presenter, self.voucher_presenter,
                      self.notes_presenter, self.source_presenter]
        dirty_kids = [p.is_dirty() for p in presenters]
        return self._dirty or True in dirty_kids

    def on_recvd_type_comboentry_changed(self, combo, *args):
        """
        """
        value = None
        treeiter = combo.get_active_iter()
        if treeiter:
            value = combo.get_model()[treeiter][0]
        else:
            # the changed handler is fired again after the
            # combo.child.props.text with the activer iter set to None
            return True
        # the entry change handler does the validation of the model
        combo.child.props.text = recvd_type_values[value]

    def on_recvd_type_entry_changed(self, entry, *args):
        """
        """
        problem = 'BAD_RECVD_TYPE'
        text = entry.props.text
        if not text.strip():
            self.remove_problem(problem, entry)
            self.set_model_attr('recvd_type', None)
            return
        model = entry.get_parent().get_model()

        def match_func(row, data):
            return str(row[0]).lower() == str(data).lower() or \
                str(row[1]).lower() == str(data).lower()
        results = utils.search_tree_model(model, text, match_func)
        if results and len(results) == 1:  # is match is unique
            self.remove_problem(problem, entry)
            self.set_model_attr('recvd_type', model[results[0]][0])
        else:
            self.add_problem(problem, entry)
            self.set_model_attr('recvd_type', None)

    def on_acc_code_entry_changed(self, entry, data=None):
        text = entry.get_text()
        query = self.session.query(Accession)
        if text != self._original_code \
                and query.filter_by(code=unicode(text)).count() > 0:
            self.add_problem(self.PROBLEM_DUPLICATE_ACCESSION,
                             self.view.widgets.acc_code_entry)
            self.set_model_attr('code', None)
            return
        self.remove_problem(self.PROBLEM_DUPLICATE_ACCESSION,
                            self.view.widgets.acc_code_entry)
        if text is '':
            self.set_model_attr('code', None)
        else:
            self.set_model_attr('code', utils.utf8(text))

    def on_date_entry_changed(self, entry, prop):
        """handle changed signal.

        used by acc_date_recvd_entry and acc_date_accd_entry

        :param prop: the model property to change, should be
          date_recvd or date_accd
        """
        from bauble.editor import ValidatorError
        value = None
        PROBLEM = 'INVALID_DATE'
        try:
            value = editor.DateValidator().to_python(entry.props.text)
        except ValidatorError, e:
            logger.debug(e)
            self.add_problem(PROBLEM, entry)
        else:
            self.remove_problem(PROBLEM, entry)
        self.set_model_attr(prop, value)

    def set_model_attr(self, field, value, validator=None):
        """
        Set attributes on the model and update the GUI as expected.
        """
        #debug('set_model_attr(%s, %s)' % (field, value))
        super(AccessionEditorPresenter, self).set_model_attr(field, value,
                                                             validator)
        self._dirty = True
        # TODO: add a test to make sure that the change notifiers are
        # called in the expected order
        prov_sensitive = True
        wild_prov_combo = self.view.widgets.acc_wild_prov_combo
        if field == 'prov_type':
            if self.model.prov_type == 'Wild':
                self.model.wild_prov_status = wild_prov_combo.get_active_text()
            else:
                # remove the value in the model from the wild_prov_combo
                prov_sensitive = False
                self.model.wild_prov_status = None
            wild_prov_combo.set_sensitive(prov_sensitive)
            self.view.widgets.acc_wild_prov_combo.set_sensitive(prov_sensitive)

        if field == 'id_qual' and not self.model.id_qual_rank:
            self.add_problem(self.PROBLEM_ID_QUAL_RANK_REQUIRED,
                             self.view.widgets.acc_id_qual_rank_combo)
        else:
            self.remove_problem(self.PROBLEM_ID_QUAL_RANK_REQUIRED)

        self.refresh_sensitivity()

    def validate(self, add_problems=False):
        """
        Validate the self.model
        """
        # TODO: if add_problems=True then we should add problems to
        # all the required widgets that don't have values

        if not self.model.code or not self.model.species:
            return False

        for ver in self.model.verifications:
            ignore = ('id', 'accession_id', 'species_id', 'prev_species_id')
            if utils.get_invalid_columns(ver, ignore_columns=ignore) or \
                    not ver.species or not ver.prev_species:
                return False

        for voucher in self.model.vouchers:
            ignore = ('id', 'accession_id')
            if utils.get_invalid_columns(voucher, ignore_columns=ignore):
                return False

        # validate the source if there is one
        if self.model.source:
            if utils.get_invalid_columns(self.model.source.collection):
                return False
            if utils.get_invalid_columns(self.model.source.propagation):
                return False

            if not self.model.source.propagation:
                return True

            prop = self.model.source.propagation
            prop_ignore = ['id', 'propagation_id']
            prop_model = None
            if prop and prop.prop_type == u'Seed':
                prop_model = prop._seed
            elif prop and prop.prop_type == 'UnrootedCutting':
                prop_model = prop._cutting
            else:
                logger.debug('AccessionEditorPresenter.validate(): unknown prop_type')
                return True  # let user save it anyway

            if utils.get_invalid_columns(prop_model, prop_ignore):
                return False

        return True

    def refresh_sensitivity(self):
        """
        Refresh the sensitivity of the fields and accept buttons according
        to the current values in the model.
        """
        if self.model.species and self.model.id_qual:
            self.view.widgets.acc_id_qual_rank_combo.set_sensitive(True)
        else:
            self.view.widgets.acc_id_qual_rank_combo.set_sensitive(False)

        sensitive = self.is_dirty() and self.validate() \
            and not self.problems \
            and not self.source_presenter.all_problems() \
            and not self.ver_presenter.problems \
            and not self.voucher_presenter.problems
        self.view.set_accept_buttons_sensitive(sensitive)

    def refresh_view(self):
        '''
        get the values from the model and put them in the view
        '''
        date_format = prefs.prefs[prefs.date_format_pref]
        for widget, field in self.widget_to_field_map.iteritems():
            if field == 'species_id':
                value = self.model.species
            else:
                value = getattr(self.model, field)
            self.view.widget_set_value(widget, value)

        self.view.widget_set_value(
            'acc_wild_prov_combo',
            dict(wild_prov_status_values)[self.model.wild_prov_status],
            index=1)
        self.view.widget_set_value(
            'acc_prov_combo',
            dict(prov_type_values)[self.model.prov_type],
            index=1)
        self.view.widget_set_value(
            'acc_recvd_type_comboentry',
            recvd_type_values[self.model.recvd_type],
            index=1)

        self.view.widgets.acc_private_check.set_inconsistent(False)
        self.view.widgets.acc_private_check.\
            set_active(self.model.private is True)

        sensitive = self.model.prov_type == 'Wild'
        self.view.widgets.acc_wild_prov_combo.set_sensitive(sensitive)
        self.view.widgets.acc_wild_prov_combo.set_sensitive(sensitive)

    def cleanup(self):
        super(AccessionEditorPresenter, self).cleanup()
        self.ver_presenter.cleanup()
        self.voucher_presenter.cleanup()
        self.source_presenter.cleanup()

    def start(self):
        self.source_presenter.start()
        r = self.view.start()
        return r


class AccessionEditor(editor.GenericModelViewPresenterEditor):

    # these have to correspond to the response values in the view
    RESPONSE_OK_AND_ADD = 11
    RESPONSE_NEXT = 22
    ok_responses = (RESPONSE_OK_AND_ADD, RESPONSE_NEXT)

    def __init__(self, model=None, parent=None):
        '''
        :param model: Accession instance or None
        :param parent: the parent widget
        '''
        if model is None:
            model = Accession()

        super(AccessionEditor, self).__init__(model, parent)
        self.parent = parent
        self._committed = []

        view = AccessionEditorView(parent=parent)
        self.presenter = AccessionEditorPresenter(self.model, view)

        # set the default focus
        if self.model.species is None:
            view.widgets.acc_species_entry.grab_focus()
        else:
            view.widgets.acc_code_entry.grab_focus()

    def handle_response(self, response):
        '''
        handle the response from self.presenter.start() in self.start()
        '''
        not_ok_msg = _('Are you sure you want to lose your changes?')
        if response == gtk.RESPONSE_OK or response in self.ok_responses:
            try:
                if not self.presenter.validate():
                    # TODO: ideally the accept buttons wouldn't have
                    # been sensitive until validation had already
                    # succeeded but we'll put this here either way and
                    # show a message about filling in the fields
                    #
                    # msg = _('Some required fields have not been completed')
                    return False
                if self.presenter.is_dirty():
                    self.commit_changes()
                    self._committed.append(self.model)
            except DBAPIError, e:
                msg = _('Error committing changes.\n\n%s') % \
                    utils.xml_safe(unicode(e.orig))
                utils.message_details_dialog(msg, str(e), gtk.MESSAGE_ERROR)
                return False
            except Exception, e:
                msg = _('Unknown error when committing changes. See the '
                        'details for more information.\n\n%s') \
                    % utils.xml_safe(e)
                utils.message_details_dialog(msg, traceback.format_exc(),
                                             gtk.MESSAGE_ERROR)
                return False
        elif self.presenter.is_dirty() and utils.yes_no_dialog(not_ok_msg) \
                or not self.presenter.is_dirty():
            self.session.rollback()
            return True
        else:
            return False

        # respond to responses
        more_committed = None
        if response == self.RESPONSE_NEXT:
            self.presenter.cleanup()
            e = AccessionEditor(parent=self.parent)
            more_committed = e.start()
        elif response == self.RESPONSE_OK_AND_ADD:
            e = PlantEditor(Plant(accession=self.model), self.parent)
            more_committed = e.start()

        if more_committed is not None:
            if isinstance(more_committed, list):
                self._committed.extend(more_committed)
            else:
                self._committed.append(more_committed)

        return True

    def start(self):
        from bauble.plugins.plants.species_model import Species
        if self.session.query(Species).count() == 0:
            msg = _('You must first add or import at least one species into '
                    'the database before you can add accessions.')
            utils.message_dialog(msg)
            return

        while True:
            #debug(self.presenter.source_presenter.source)
            #debug(self.presenter.source_presenter.source.collection)
            response = self.presenter.start()
            self.presenter.view.save_state()
            if self.handle_response(response):
                break

        self.session.close()  # cleanup session
        self.presenter.cleanup()
        return self._committed

    @staticmethod
    def _cleanup_collection(model):
        '''
        '''
        if not model:
            return
        # TODO: we should raise something besides commit ValueError
        # so we can give a meaningful response
        if model.latitude is not None or model.longitude is not None:
            if (model.latitude is not None and model.longitude is None) or \
                    (model.longitude is not None and model.latitude is None):
                msg = _('model must have both latitude and longitude or '
                        'neither')
                raise ValueError(msg)
            elif model.latitude is None and model.longitude is None:
                model.geo_accy = None  # don't save
        else:
            model.geo_accy = None  # don't save

        # reset the elevation accuracy if the elevation is None
        if model.elevation is None:
            model.elevation_accy = None
        return model

    def commit_changes(self):
        if self.model.source:

            if not self.model.source.collection:
                utils.delete_or_expunge(
                    self.presenter.source_presenter.collection)

            if self.model.source.propagation:
                self.model.source.propagation.clean()
            else:
                utils.delete_or_expunge(
                    self.presenter.source_presenter.propagation)
        else:
            utils.delete_or_expunge(
                self.presenter.source_presenter.source)
            utils.delete_or_expunge(
                self.presenter.source_presenter.collection)
            utils.delete_or_expunge(
                self.presenter.source_presenter.propagation)

        if self.model.id_qual is None:
            self.model.id_qual_rank = None

        # should we also add a plant for this accession?
        if self.model.create_plant:
            logger.debug('creating plant for new accession')
            accession = self.model
            location = accession.intended_location
            plant = Plant(accession=accession, code=u'1', quantity=accession.quantity_recvd, location=location,
                          acc_type=accession_type_to_plant_material.get(self.model.recvd_type))
            self.session.add(plant)
            
        return super(AccessionEditor, self).commit_changes()


# import at the bottom to avoid circular dependencies
from bauble.plugins.plants.genus import Genus
from bauble.plugins.plants.species_model import Species, SpeciesSynonym


#
# infobox for searchview
#

# TODO: i don't think this shows all field of an accession, like the
# accuracy values
class GeneralAccessionExpander(InfoExpander):
    """
    generic information about an accession like
    number of clones, provenance type, wild provenance type, speciess
    """

    def __init__(self, widgets):
        '''
        '''
        super(GeneralAccessionExpander, self).__init__(_("General"), widgets)
        general_box = self.widgets.general_box
        self.widgets.general_window.remove(general_box)
        self.vbox.pack_start(general_box)
        self.current_obj = None
        self.private_image = self.widgets.acc_private_data

        def on_species_clicked(*args):
            select_in_search_results(self.current_obj.species)
        utils.make_label_clickable(self.widgets.name_data, on_species_clicked)

        def on_parent_plant_clicked(*args):
            select_in_search_results(self.current_obj.source.plant_propagation.plant)
        utils.make_label_clickable(self.widgets.parent_plant_data,
                                   on_parent_plant_clicked)

        def on_nplants_clicked(*args):
            cmd = 'plant where accession.code="%s"' % self.current_obj.code
            bauble.gui.send_command(cmd)
        utils.make_label_clickable(self.widgets.nplants_data,
                                   on_nplants_clicked)

    def update(self, row):
        '''
        '''
        self.current_obj = row
        self.widget_set_value('acc_code_data', '<big>%s</big>' %
                              utils.xml_safe(unicode(row.code)),
                              markup=True)

        # TODO: i don't know why we can't just set the visible
        # property to False here
        acc_private = self.widgets.acc_private_data
        if row.private:
            if acc_private.parent != self.widgets.acc_code_box:
                self.widgets.acc_code_box.pack_start(acc_private)
        else:
            self.widgets.remove_parent(acc_private)

        self.widget_set_value('name_data', row.species_str(markup=True),
                              markup=True)

        session = object_session(row)
        plant_locations = {}
        for plant in row.plants:
            if plant.quantity == 0:
                continue
            q = plant_locations.setdefault(plant.location, 0)
            plant_locations[plant.location] = q + plant.quantity
        if plant_locations:
            strs = []
            for location, quantity in plant_locations.iteritems():
                strs.append(_('%(quantity)s in %(location)s')
                            % dict(location=str(location), quantity=quantity))
            s = '\n'.join(strs)
        else:
            s = '0'
        self.widget_set_value('living_plants_data', s)

        nplants = session.query(Plant).filter_by(accession_id=row.id).count()
        self.widget_set_value('nplants_data', nplants)
        self.widget_set_value('date_recvd_data', row.date_recvd)
        self.widget_set_value('date_accd_data', row.date_accd)

        type_str = ''
        if row.recvd_type:
            type_str = recvd_type_values[row.recvd_type]
        self.widget_set_value('recvd_type_data', type_str)
        quantity_str = ''
        if row.quantity_recvd:
            quantity_str = row.quantity_recvd
        self.widget_set_value('quantity_recvd_data', quantity_str)

        prov_str = dict(prov_type_values)[row.prov_type]
        if row.prov_type == u'Wild' and row.wild_prov_status:
            prov_str = '%s (%s)' % \
                (prov_str, dict(wild_prov_status_values)[row.wild_prov_status])
        self.widget_set_value('prov_data', prov_str, False)

        image_size = gtk.ICON_SIZE_MENU
        stock = gtk.STOCK_NO
        if row.private:
            stock = gtk.STOCK_YES
        self.widgets.private_image.set_from_stock(stock, image_size)

        loc_map = (('intended_loc_data', 'intended_location'),
                   ('intended2_loc_data', 'intended2_location'))

        for label, attr in loc_map:
            location_str = ''
            location = getattr(row, attr)
            if location:
                if location.name and location.code:
                    location_str = '%s (%s)' % (location.name,
                                                location.code)
                elif location.name and not location.code:
                    location_str = '%s' % location.name
                elif not location.name and location.code:
                    location_str = '(%s)' % location.code
            self.widget_set_value(label, location_str)


class SourceExpander(InfoExpander):
    def __init__(self, widgets):
        super(SourceExpander, self).__init__(_('Source'), widgets)
        source_box = self.widgets.source_box
        self.widgets.source_window.remove(source_box)
        self.vbox.pack_start(source_box)

    def update_collection(self, collection):
        self.widget_set_value('loc_data', collection.locale)
        self.widget_set_value('datum_data', collection.gps_datum)

        geo_accy = collection.geo_accy
        if not geo_accy:
            geo_accy = ''
        else:
            geo_accy = '(+/- %sm)' % geo_accy

        lat_str = ''
        if collection.latitude is not None:
            dir, deg, min, sec = latitude_to_dms(collection.latitude)
            lat_str = '%s (%s %s\302\260%s\'%.2f") %s' % \
                (collection.latitude, dir, deg, min, sec, geo_accy)
        self.widget_set_value('lat_data', lat_str)

        long_str = ''
        if collection.longitude is not None:
            dir, deg, min, sec = longitude_to_dms(collection.longitude)
            long_str = '%s (%s %s\302\260%s\'%.2f") %s' % \
                (collection.longitude, dir, deg, min, sec, geo_accy)
        self.widget_set_value('lon_data', long_str)

        elevation = ''
        if collection.elevation:
            elevation = '%sm' % collection.elevation
            if collection.elevation_accy:
                elevation += ' (+/- %sm)' % collection.elevation_accy
        self.widget_set_value('elev_data', elevation)

        self.widget_set_value('coll_data', collection.collector)
        self.widget_set_value('date_data', collection.date)
        self.widget_set_value('collid_data', collection.collectors_code)
        self.widget_set_value('habitat_data', collection.habitat)
        self.widget_set_value('collnotes_data', collection.notes)

    def update(self, row):
        if not row.source:
            self.props.expanded = False
            self.props.sensitive = False
            return

        if row.source.source_detail:
            self.widgets.source_name_label.props.visible = True
            self.widgets.source_name_data.props.visible = True
            self.widget_set_value('source_name_data',
                                  utils.utf8(row.source.source_detail))

            def on_source_clicked(w, e, x):
                select_in_search_results(x)
            utils.make_label_clickable(self.widgets.source_name_data,
                                       on_source_clicked,
                                       row.source.source_detail)
        else:
            self.widgets.source_name_label.props.visible = False
            self.widgets.source_name_data.props.visible = False

        sources_code = ''
        if row.source.sources_code:
            sources_code = row.source.sources_code
        self.widget_set_value('sources_code_data', utils.utf8(sources_code))

        if row.source.plant_propagation:
            self.widgets.parent_plant_label.props.visible = True
            self.widgets.parent_plant_eventbox.props.visible = True
            self.widget_set_value('parent_plant_data',
                                  str(row.source.plant_propagation.plant))
            self.widget_set_value('propagation_data',
                                  row.source.plant_propagation.get_summary())
        else:
            self.widgets.parent_plant_label.props.visible = False
            self.widgets.parent_plant_eventbox.props.visible = False

        prop_str = ''
        if row.source.propagation:
            prop_str = row.source.propagation.get_summary()
        self.widget_set_value('propagation_data', prop_str)

        if row.source.collection:
            self.widgets.collection_expander.props.expanded = True
            self.widgets.collection_expander.props.sensitive = True
            self.update_collection(row.source.collection)
        else:
            self.widgets.collection_expander.props.expanded = False
            self.widgets.collection_expander.props.sensitive = False


class VerificationsExpander(InfoExpander):
    """
    the accession's notes
    """

    def __init__(self, widgets):
        super(VerificationsExpander, self).__init__(
            _("Verifications"), widgets)
        # notes_box = self.widgets.notes_box
        # self.widgets.notes_window.remove(notes_box)
        # self.vbox.pack_start(notes_box)

    def update(self, row):
        pass
        #self.widget_set_value('notes_data', row.notes)


class VouchersExpander(InfoExpander):
    """
    the accession's notes
    """

    def __init__(self, widgets):
        super(VouchersExpander, self).__init__(_("Vouchers"), widgets)

    def update(self, row):
        for kid in self.vbox.get_children():
            self.vbox.remove(kid)

        if not row.vouchers:
            self.set_expanded(False)
            self.set_sensitive(False)
            return

        # TODO: should save/restore the expanded state of the vouchers
        self.set_expanded(True)
        self.set_sensitive(True)

        parents = filter(lambda v: v.parent_material, row.vouchers)
        for voucher in parents:
            s = '%s %s (parent)' % (voucher.herbarium, voucher.code)
            label = gtk.Label(s)
            label.set_alignment(0.0, 0.5)
            self.vbox.pack_start(label)
            label.show()

        not_parents = filter(lambda v: not v.parent_material, row.vouchers)
        for voucher in not_parents:
            s = '%s %s' % (voucher.herbarium, voucher.code)
            label = gtk.Label(s)
            label.set_alignment(0.0, 0.5)
            self.vbox.pack_start(label)
            label.show()


class AccessionInfoBox(InfoBox):
    """
    - general info
    - source
    """
    def __init__(self):
        super(AccessionInfoBox, self).__init__()
        filename = os.path.join(paths.lib_dir(), "plugins", "garden",
                                "acc_infobox.glade")
        self.widgets = utils.load_widgets(filename)
        self.general = GeneralAccessionExpander(self.widgets)
        self.add_expander(self.general)
        self.source = SourceExpander(self.widgets)
        self.add_expander(self.source)

        # self.vouchers = VouchersExpander(self.widgets)
        # self.add_expander(self.vouchers)
        # self.verifications = VerificationsExpander(self.widgets)
        # self.add_expander(self.verifications)

        self.links = view.LinksExpander('notes')
        self.add_expander(self.links)

        self.props = PropertiesExpander()
        self.add_expander(self.props)

        #self.show_all()

    def update(self, row):
        if isinstance(row, Collection):
            row = row.source.accession

        self.general.update(row)
        self.props.update(row)

        # if row.verifications:
        #     self.verifications.update(row)
        # self.verifications.set_expanded(row.verifications != None)
        # self.verifications.set_sensitive(row.verifications != None)

        # self.vouchers.update(row)

        urls = filter(lambda x: x != [],
                      [utils.get_urls(note.note) for note in row.notes])
        if not urls:
            self.links.props.visible = False
            self.links._sep.props.visible = False
        else:
            self.links.props.visible = True
            self.links._sep.props.visible = True
            self.links.update(row)

        # TODO: should test if the source should be expanded from the prefs
        expanded = prefs.prefs.get('acc_source_expander', True)
        self.source.props.expanded = expanded
        self.source.props.sensitive = True
        self.source.update(row)


#
# Map Datum List - this list should be available as a list of completions for
# the datum text entry....the best way is that is to show the abbreviation
# with the long string in parenthesis or with different markup but selecting
# the completion will enter the abbreviation....though the entry should be
# free text....this list complements of:
# http://www8.garmin.com/support/faqs/MapDatumList.pdf
#
# Abbreviation: Name
datums = {"Adindan": "Adindan- Ethiopia, Mali, Senegal, Sudan",
          "Afgooye": "Afgooye- Somalia",
          "AIN EL ABD": "'70 AIN EL ANBD 1970- Bahrain Island, Saudi Arabia",
          "Anna 1 Ast '65": "Anna 1 Astro '65- Cocos I.",
          "ARC 1950": "ARC 1950- Botswana, Lesotho, Malawi, Swaziland, Zaire, Zambia",
          "ARC 1960": "Kenya, Tanzania",
          "Ascnsn Isld '58": "Ascension Island '58- Ascension Island",
          "Astro Dos 71/4": "Astro Dos 71/4- St. Helena",
          "Astro B4 Sorol": "Sorol Atoll- Tern Island",
          "Astro Bcn \"E\"": "Astro Beacon \"E\"- Iwo Jima",
          "Astr Stn '52": "Astronomic Stn '52- Marcus Island",
          "Aus Geod '66": "Australian Geod '66- Australia, Tasmania Island",
          "Aus Geod '84": "Australian Geod '84- Australia, Tasmania Island",
          "Austria": "Austria",
          "Bellevue (IGN)": "Efate and Erromango Islands",
          "Bermuda 1957": "Bermuda 1957- Bermuda Islands",
          "Bogota Observ": "Bogata Obsrvatry- Colombia",
          "Campo Inchspe": "Campo Inchauspe- Argentina",
          "Canton Ast '66": "Canton Astro 1966- Phoenix Islands",
          "Cape": "Cape- South Africa",
          "Cape Canavrl": "Cape Canaveral- Florida, Bahama Islands",
          "Carthage": "Carthage- Tunisia",
          "CH-1903": "CH 1903- Switzerland",
          "Chatham 1971": "Chatham 1971- Chatham Island (New Zealand)",
          "Chua Astro": "Chua Astro- Paraguay",
          "Corrego Alegr": "Corrego Alegre- Brazil",
          "Croatia": "Croatia",
          "Djakarta": "Djakarta (Batavia)- Sumatra Island (Indonesia)",
          "Dos 1968": "Dos 1968- Gizo Island (New Georgia Islands)",
          "Dutch": "Dutch",
          "Easter Isld 67": "Easter Island 1967",
          "European 1950": "European 1950- Austria, Belgium, Denmark, Finland, France, Germany, Gibraltar, Greece, Italy, Luxembourg, Netherlands, Norway, Portugal, Spain, Sweden, Switzerland",
          "European 1979": "European 1979- Austria, Finland, Netherlands, Norway, Spain, Sweden, Switzerland",
          "Finland Hayfrd": "Finland Hayford- Finland",
          "Gandajika Base": "Gandajika Base- Republic of Maldives",
          "GDA": "Geocentric Datum of Australia",
          "Geod Datm '49": "Geodetic Datum '49- New Zealand",
          "Guam 1963": "Guam 1963- Guam Island",
          "Gux 1 Astro": "Guadalcanal Island",
          "Hjorsey 1955": "Hjorsey 1955- Iceland",
          "Hong Kong '63": "Hong Kong",
          "Hu-Tzu-Shan": "Taiwan",
          "Indian Bngldsh": "Indian- Bangladesh, India, Nepal",
          "Indian Thailand": "Indian- Thailand, Vietnam",
          "Indonesia 74": "Indonesia 1974- Indonesia",
          "Ireland 1965": "Ireland 1965- Ireland",
          "ISTS 073 Astro": "ISTS 073 ASTRO '69- Diego Garcia",
          "Johnston Island": "Johnston Island NAD27 Central",
          "Kandawala": "Kandawala- Sri Lanka",
          "Kergueln Islnd": "Kerguelen Island",
          "Kertau 1948": "West Malaysia, Singapore",
          "L.C. 5 Astro": "Cayman Brac Island",
          "Liberia 1964": "Liberia 1964- Liberia",
          "Luzon Mindanao": "Luzon- Mindanao Island",
          "Luzon Philippine": "Luzon- Philippines (excluding Mindanao Isl.)",
          "Mahe 1971": "Mahe 1971- Mahe Island",
          "Marco Astro": "Marco Astro- Salvage Isl.",
          "Massawa": "Massawa- Eritrea (Ethiopia)",
          "Merchich": "Merchich- Morocco",
          "Midway Ast '61": "Midway Astro '61- Midway",
          "Minna": "Minna- Nigeria",
          "NAD27 Alaska": "North American 1927- Alaska",
          "NAD27 Bahamas": "North American 1927- Bahamas",
          "NAD27 Canada": "North American 1927- Canada and Newfoundland",
          "NAD27 Canal Zn": "North American 1927- Canal Zone",
          "NAD27 Caribbn": "North American 1927- Caribbean (Barbados, Caicos Islands, Cuba, Dominican Repuplic, Grand Cayman, Jamaica, Leeward and Turks Islands)",
          "NAD27 Central": "North American 1927- Central America (Belize, Costa Rica, El Salvador, Guatemala, Honduras, Nicaragua)",
          "NAD27 CONUS": "North American 1927- Mean Value (CONUS)",
          "NAD27 Cuba": "North American 1927- Cuba",
          "NAD27 Grnland": "North American 1927- Greenland (Hayes Peninsula)",
          "NAD27 Mexico": "North American 1927- Mexico",
          "NAD27 San Sal": "North American 1927- San Salvador Island",
          "NAD83": "North American 1983- Alaska, Canada, Central America, CONUS, Mexico",
          "Naparima BWI": "Naparima BWI- Trinidad and Tobago",
          "Nhrwn Masirah": "Nahrwn- Masirah Island (Oman)",
          "Nhrwn Saudi A": "Nahrwn- Saudi Arabia",
          "Nhrwn United A": "Nahrwn- United Arab Emirates",
          "Obsrvtorio '66": "Observatorio 1966- Corvo and Flores Islands (Azores)",
          "Old Egyptian": "Old Egyptian- Egypt",
          "Old Hawaiian": "Old Hawaiian- Mean Value",
          "Oman": "Oman- Oman",
          "Old Srvy GB": "Old Survey Great Britain- England, Isle of Man, Scotland, Shetland Isl., Wales",
          "Pico De Las Nv": "Canary Islands",
          "Potsdam": "Potsdam-Germany",
          "Prov S Am '56": "Prov  Amricn '56- Bolivia, Chile,Colombia, Ecuador, Guyana, Peru, Venezuela",
          "Prov S Chln '63": "So. Chilean '63- S. Chile",
          "Ptcairn Ast '67": "Pitcairn Astro '67- Pitcairn",
          "Puerto Rico": "Puerto Rico & Virgin Isl.",
          "Qatar National": "Qatar National- Qatar South Greenland",
          "Qornoq": "Qornoq- South Greenland",
          "Reunion": "Reunion- Mascarene Island",
          "Rome 1940": "Rome 1940- Sardinia Isl.",
          "RT 90": "Sweden",
          "Santo (Dos)": "Santo (Dos)- Espirito Santo",
          "Sao Braz": "Sao Braz- Sao Miguel, Santa Maria Islands",
          "Sapper Hill '43": "Sapper Hill 1943- East Falkland Island",
          "Schwarzeck": "Schwarzeck- Namibia",
          "SE Base": "Southeast Base- Porto Santo and Madiera Islands",
          "South Asia": "South Asia- Singapore",
          "Sth Amrcn '69": "S. American '69- Argentina, Bolivia, Brazil, Chile, Colombia, Ecuador, Guyana, Paraguay, Peru, Venezuela, Trin/Tobago",
          "SW Base": "Southwest Base- Faial, Graciosa, Pico, Sao Jorge and Terceira",
          "Taiwan": "Taiwan",
          "Timbalai 1948": "Timbalai 1948- Brunei and E. Malaysia (Sarawak and Sabah)",
          "Tokyo": "Tokyo- Japan, Korea, Okinawa",
          "Tristan Ast '68": "Tristan Astro 1968- Tristan da Cunha",
          "Viti Levu 1916": "Viti Levu 1916- Viti Levu/Fiji Islands",
          "Wake-Eniwetok": "Wake-Eniwetok- Marshall",
          "WGS 72": "World Geodetic System 72",
          "WGS 84": "World Geodetic System 84",
          "Zanderij": "Zanderij- Surinam (excluding San Salvador Island)",
          "User": "User-defined custom datum"}
