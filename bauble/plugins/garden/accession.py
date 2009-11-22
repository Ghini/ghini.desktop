# -*- coding: utf-8 -*-

#
# accessions module
#
import datetime
from decimal import Decimal, ROUND_DOWN
import os
import re
from random import random
import sys
import traceback
import weakref
import xml.sax.saxutils as saxutils

import gtk
import gobject
import lxml.etree as etree
import pango
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.orm.session import object_session
from sqlalchemy.exc import SQLError

import bauble
import bauble.db as db
import bauble.editor as editor
from bauble.error import check, CommitException
import bauble.paths as paths
from bauble.plugins.garden.donor import Donor
from bauble.plugins.garden.source import CollectionPresenter, \
    DonationPresenter, SourcePropagationPresenter
import bauble.prefs as prefs
import bauble.types as types
import bauble.utils as utils
from bauble.utils.log import debug
from bauble.view import InfoBox, InfoExpander, PropertiesExpander, \
     select_in_search_results, Action
import bauble.view as view

# TODO: underneath the species entry create a label that shows information
# about the family of the genus of the species selected as well as more
# info about the genus so we know exactly what plant is being selected
# e.g. Malvaceae (sensu lato), Hibiscus (senso stricto)

def longitude_to_dms(decimal):
    return decimal_to_dms(decimal, 'long')

def latitude_to_dms(decimal):
    return decimal_to_dms(decimal, 'lat')


def decimal_to_dms(decimal, long_or_lat):
    '''
    @param decimal: the value to convert
    @param long_or_lat: should be either "long" or "lat"

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
    if dir in ('E', 'W'): # longitude
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


def get_next_code():
    """
    Return the next available accession code.  This function should be
    specific to the institution.

    At the moment it assumes that you are using an accession code of
    the format: YYYY.CCCC where YYYY is the four digit year and CCCC
    is the four digit code left filled with zeroes

    If there is an error getting the next code the None is returned.
    """
    # auto generate/increment the accession code
    session = db.Session()
    year = str(datetime.date.today().year)
    start = '%s%s' % (year, Plant.get_delimiter())
    q = session.query(Accession.code).\
        filter(Accession.code.startswith(start))
    next = None
    try:
        if q.count() > 0:
            codes = [int(code[0][len(start):]) for code in q]
            next = '%s%s' % (start, str(max(codes)+1).zfill(4))
        else:
            next = '%s%s0001' % (datetime.date.today().year,
                                 Plant.get_delimiter())
    except Exception, e:
        debug('exception')
        debug(e)
        pass
    finally:
        session.close()
    return next

def edit_callback(accessions):
    e = AccessionEditor(model=accessions[0])
    return e.start()


def add_plants_callback(accessions):
    e = PlantEditor(model=Plant(accession=accessions[0]))
    return e.start()


def remove_callback(accessions):
    # TODO: allow this method to remove multiple accessions
    acc = accessions[0]
    if len(acc.plants) > 0:
        safe = utils.xml_safe_utf8
        plants = [str(plant) for plant in acc.plants]
        values = dict(num_plants=len(acc.plants),
                      plant_codes = safe(', '.join(plants)),
                      acc_code = safe(acc))
        msg = _('%(num_plants)s plants depend on this accession: ' \
                '<b>%(plant_codes)s</b>\n\n'\
                'Are you sure you want to remove accession ' \
                '<b>%(acc_code)s</b>?' % values)
    else:
        msg = _("Are you sure you want to remove accession <b>%s</b>?") % \
                  utils.xml_safe_utf8(unicode(acc))
    if not utils.yes_no_dialog(msg):
        return False
    try:
        session = db.Session()
        obj = session.query(Accession).get(acc.id)
        session.delete(obj)
        session.commit()
    except Exception, e:
        msg = _('Could not delete.\n\n%s') % utils.xml_safe_utf8(unicode(e))
        utils.message_details_dialog(msg, traceback.format_exc(),
                                     type=gtk.MESSAGE_ERROR)
    finally:
        session.close()
    return True


edit_action = Action('acc_edit', ('_Edit'), callback=edit_callback,
                        accelerator='<ctrl>e')
add_plant_action = Action('acc_add', ('_Add plants'),
                          callback=add_plants_callback, accelerator='<ctrl>k')
remove_action = Action('acc_remove', ('_Remove'), callback=remove_callback,
                       accelerator='<delete>')#, multiselect=True)

acc_context_menu = [edit_action, add_plant_action, remove_action]


def acc_markup_func(acc):
    """
    Returns str(acc), acc.species_str()
    """
    return utils.xml_safe_utf8(unicode(acc)), acc.species_str(markup=True)



# TODO: accession should have a one-to-many relationship on verifications
    #ver_level = StringCol(length=2, default=None) # verification level
    #ver_name = StringCol(length=50, default=None) # verifier's name
    #ver_date = DateTimeCol(default=None) # verification date
    #ver_hist = StringCol(default=None)  # verification history
    #ver_lit = StringCol(default=None) # verification lit
    #ver_id = IntCol(default=None) # ?? # verifier's ID??

ver_level_descriptions = \
    {0: _('The name of the record has not been checked by any authority.'),
     1: _('The name of the record determined by comparison with other '\
              'named plants.'),
     2: _('The name of the record determined by a taxonomist or by other '\
              'competent persons using herbarium and/or library and/or '\
              ' documented living material.'),
     3: _('The name of the plant determined by taxonomist engaged in ' \
              'systematic revision of the group.'),
     4: _('The record is part of type gathering or propagated from type '\
              'material by asexual methods.')}

class Verification(db.Base):
    """Verification table (verification)

    level: If it is not known whether the name of the record has been
    verified by an authority, then this field must not be filled.
      0: The name of the record has not been checked by any authority
      1: The name of the record determined by comparison with other
         named plants
      2: The name of the record determined by a taxonomist or by other
         competent persons using herbarium and/or library and/or
         documented living material
      3: The name of the plant determined by taxonomist engaged in
         systematic revision of the group
      4: The record is part of type gathering or propagated from type
         material by asexual methods

    """
    __tablename__ = 'verification'
    __mapper_args__ = {'order_by': 'date'}

    # columns
    verifier = Column(Unicode(64), nullable=False)
    date = Column(types.Date, nullable=False)
    reference = Column(UnicodeText)
    accession_id = Column(Integer, ForeignKey('accession.id'), nullable=False)

    # the level of assurance of this verification
    level = Column(Integer, nullable=False)

    # what it was verified as
    species_id = Column(Integer, ForeignKey('species.id'), nullable=False)

    # what it was verified from
    prev_species_id = Column(Integer, ForeignKey('species.id'), nullable=False)

    species = relation('Species',
                       primaryjoin='Verification.species_id==Species.id')
    prev_species = relation('Species',
                        primaryjoin='Verification.prev_species_id==Species.id')

    notes = Column(UnicodeText)



# TODO: auto add parent voucher if accession is a propagule of an
# existing accession and that parent accession has vouchers...or at
# least display them in the Voucher tab and Infobox
herbarium_codes = {}

class Voucher(db.Base):
    """
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


prov_type_values = {u'Wild': _('Wild'),
                    u'Cultivated': _('Propagule of cultivated wild plant'),
                    u'NotWild': _("Not of wild source"),
                    u'InsufficientData': _("Insufficient Data"),
                    u'Unknown': _("Unknown"),
                    None: _('')}


wild_prov_status_values = {u'WildNative': _("Wild native"),
                           u'WildNonNative': _("Wild non-native"),
                           u'CultivatedNative': _("Cultivated native"),
                           u'InsufficientData': _("Insufficient Data"),
                           u'Unknown': _("Unknown"),
                           None: _('')}


source_type_values = {u'Collection': _('Collection'),
                      u'Donation': _('Donation'),
                      u'SourcePropagation': _('Garden Propagation'),
                      None: _('')}

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
    u'PLNT': _('Plant'),
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
    u'SCKR': _('Root sucker')
    }

class AccessionNote(db.Base):
    """
    Notes for the accession table
    """
    __tablename__ = 'accession_note'
    __mapper_args__ = {'order_by': 'accession_note.date'}

    date = Column(types.DateTime, nullable=False)
    user = Column(Unicode(64))
    category = Column(Unicode(32))
    note = Column(UnicodeText, nullable=False)
    accession_id = Column(Integer, ForeignKey('accession.id'), nullable=False)
    accession = relation('Accession', uselist=False,
                       backref=backref('notes', cascade='all, delete-orphan'))


class Accession(db.Base):
    """
    :Table name: accession

    :Columns:
        *code*: :class:`sqlalchemy.types.Unicode`
            the accession code

        *prov_type*: :class:`bauble.types.Enum`
            the provenance type

            Possible values:
                * Wild:
                * Propagule of cultivated wild plant
                * Not of wild source
                * Insufficient Data
                * Unknown

        *wild_prov_status*:  :class:`bauble.types.Enum`
            wild provenance status, if prov_type is
            Wild then this column can be used to give more provenance
            information

            Possible values:
                * Wild native
                * Cultivated native
                * Insufficient Data
                * Unknown

        *date*: :class:`bauble.types.Date`
            the date this accession was accessioned

        *source_type*: :class:`bauble.types.Enum`
            The type of the source of this accession

            Possible values:

                * Collection: indicates that self.source points to a
                  :class:`bauble.plugins.garden.Collection`

                * Donation: indicates that self.source points to a
                  :class:`bauble.plugins.garden.Donation`

                * SourcePropagation: indicates that self.source points to a
                  :class:`bauble.plugins.garden.PropagationSource`

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

        *species_id*: :class:`sqlalchemy.types.ForeignKey`
            foreign key to the species table

    :Properties:
        *species*:
            the species this accession refers to

        *_collection*:
            this relation should never be used directly, use the
            source property instead

        *_donation*:
            this relations should never be used directly, use
            the source property instead

        *source*:
            source cancel either be a Donation, Collection or None
            depending on the value of the source_type

        *plants*:
            a list of plants related to this accession

        *verifications*:
            a list of verifications on the identification of this accession

    :Constraints:

    """
    __tablename__ = 'accession'
    __mapper_args__ = {'order_by': 'code',
                       'extension': AccessionMapperExtension()}

    # columns
    #: the accession code
    code = Column(Unicode(20), nullable=False, unique=True)

    prov_type = Column(types.Enum(values=prov_type_values.keys()),default=None)

    wild_prov_status =Column(types.Enum(values=wild_prov_status_values.keys()),
                             default=None)

    date_accd = Column(types.Date)
    date_recvd = Column(types.Date)
    quantity_recvd = Column(Integer)
    recvd_type = Column(types.Enum(values=recvd_type_values.keys()))

    date = Column(types.Date)
    source_type = Column(types.Enum(values=source_type_values.keys()),
                         default=None)

    # "id_qual" new in 0.7
    id_qual = Column(types.Enum(values=['aff.', 'cf.', 'incorrect',
                                        'forsan', 'near', '?', None]),
                     default=None)

    # new in 0.9, this column should contain the name of the column in
    # the species table that the id_qual refers to, e.g. genus, sp, etc.
    id_qual_rank = Column(Unicode(10))

    # "private" new in 0.8b2
    private = Column(Boolean, default=False)
    species_id = Column(Integer, ForeignKey('species.id'), nullable=False)

    # intended location
    intended_location_id = Column(Integer, ForeignKey('location.id'))
    intended2_location_id = Column(Integer, ForeignKey('location.id'))

    # relations
    species = relation('Species', uselist=False, backref=backref('accessions',
                                                cascade='all, delete-orphan'))

    # TODO: the _accession property on the Collection and Donation
    # tables, if you try to set the accession for one of these objects
    # using the _accession property you will have problems using
    # Accession.source because the Accession.source_type property
    # won't be set...previously (0.8) the property was _accession, we
    # should probably change it back and make accession a property
    # that properly sets the source type or just the source
    _collection = relation('Collection', cascade='all, delete-orphan',
                           uselist=False, backref=backref('_accession',
                                                          uselist=False))
    _donation = relation('Donation',
                         cascade='all, delete-orphan', uselist=False,
                         backref=backref('_accession', uselist=False))

    _source_prop = relation('SourcePropagation',
                            cascade='all, delete-orphan', uselist=False,
                            backref=backref('_accession', uselist=False))

    # use Plant.code for the order_by to avoid ambiguous column names
    plants = relation('Plant', cascade='all, delete-orphan',
                      order_by='Plant.code',
                      backref=backref('accession', uselist=False))
    verifications = relation('Verification', #order_by='date',
                             cascade='all, delete-orphan',
                             backref=backref('accession', uselist=False))
    vouchers = relation('Voucher', cascade='all, delete-orphan',
                        backref=backref('accession', uselist=False))


    # *** UBC specific
    pisbg = Column(Boolean, default=False)
    memorial = Column(Boolean, default=False)

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
                    'then id_qual_rank is required. %s ' % self.code)
            warning(msg)
            self.__warned_about_id_qual = True

        # copy the species so we don't affect the original
        session = db.Session()
        species = session.merge(self.species)#, dont_load=True)

        # generate the string
        if self.id_qual in ('aff.', 'cf.'):
            if self.id_qual_rank=='infrasp':
                species.sp = '%s %s' % (species.sp, self.id_qual)
            elif self.id_qual_rank:
                setattr(species, self.id_qual_rank,
                        '%s %s' % (self.id_qual,
                                   getattr(species, self.id_qual_rank)))
            sp_str = Species.str(species, authors, markup)
        elif self.id_qual:
            sp_str = '%s(%s)' % (Species.str(species, authors, markup),
                                 self.id_qual)
        else:
            sp_str = Species.str(species, authors, markup)

        # clean up and return the string
        del species
        session.close()
        self.__cached_species_str[(markup, authors)] = sp_str
        return sp_str


    def is_source_type(self, source_type):
        """
        Return True/False if the source_type of the Accession matches.

        Arguments:
        - `source_type`: a string or class
        """
        if isinstance(source_type, basestring):
            return source_type == self.source_type
        elif isinstance(self.source_type, source_type):
            return True
        return False


    def _get_source(self):
        if self.source_type is None:
            return None
        elif self.source_type == u'Collection':
            return self._collection
        elif self.source_type == u'Donation':
            return self._donation
        elif self.source_type == u'SourcePropagation':
            return self._source_prop
        raise ValueError(_('unknown source_type in accession: %s') % \
                             self.source_type)
    def _set_source(self, source):
        if self.source is not None:
            obj = self.source
            obj._accession = None
            # we don't need to delete the old source since it will be
            # orphaned and should get automatically deleted
            #utils.delete_or_expunge(obj)
            self.source_type = None
        if source is None:
            self.source_type = None
        else:
            self.source_type = unicode(source.__class__.__name__)
            source._accession = self
    def _del_source(self):
        self.source = None

    source = property(_get_source, _set_source, _del_source)


    def markup(self):
        return '%s (%s)' % (self.code, self.species.markup())


from bauble.plugins.garden.source import Donation, Collection, \
    SourcePropagation
from bauble.plugins.garden.plant import Plant, PlantStatusEditor, PlantEditor


class AccessionEditorView(editor.GenericEditorView):

    expanders_pref_map = {#'acc_notes_expander':
                          #'editor.accession.notes.expanded',
#                           'acc_source_expander':
#                           'editor.accession.source.expanded'
                          }

    _tooltips = {
        'acc_species_entry': _("The species must be selected from the list "\
                               "of completions. To add a species use the "\
                               "Species editor."),
        'acc_code_entry': _("The accession ID must be a unique code"),
        'acc_id_qual_combo': _("The ID Qualifier\n\n" \
                               "Possible values: %s") \
                               % utils.enum_values_str('accession.id_qual'),
        'acc_date_accd_entry': _('The date this species was accessioned.'),
        'acc_date_recvd_entry': _('The date this species was received.'),
        'acc_prov_combo': _('The origin or source of this accession.\n\n' \
                            'Possible values: %s') % \
                            ', '.join(prov_type_values.values()),
        'acc_wild_prov_combo': _('The wild status is used to clarify the ' \
                                 'provenance\n\nPossible values: %s') % \
                                 ', '.join(wild_prov_status_values.values()),
        'acc_source_type_combo': _('The source type is in what way this ' \
                                   'accession was obtained'),
        'acc_private_check': _('Indicates whether this accession record ' \
                               'should be considered private.')
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
    def datum_match(completion, key, treeiter, data=None):
        """
        This method is static to ensure the AccessionEditorView gets
        garbage collected.
        """
        datum = completion.get_model()[treeiter][0]
        words = datum.split(' ')
        for w in words:
            if w.lower().startswith(key.lower()):
                return True
        return False


    @staticmethod
    def species_match_func(completion, key, treeiter, data=None):
        """
        This method is static to ensure the AccessionEditorView gets
        garbage collected.
        """
        species = completion.get_model()[treeiter][0]
        if str(species).lower().startswith(key.lower()) \
               or str(species.genus.genus).lower().startswith(key.lower()):
            return True
        return False


    @staticmethod
    def species_cell_data_func(column, renderer, model, treeiter, data=None):
        """
        This method is static to ensure the AccessionEditorView gets
        garbage collected.
        """
        v = model[treeiter][0]
        renderer.set_property('text', '%s (%s)' % (str(v), v.genus.family))



class VoucherPresenter(editor.GenericEditorPresenter):

    def __init__(self, parent, model, view, session):
        super(VoucherPresenter, self).__init__(model, view)
        self.parent_ref = weakref.ref(parent)
        self.session = session
        self.__dirty = False
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
            column.clear_attributes(cell) # get rid of some warnings
            cell.props.editable = True
            self.view.connect(cell, 'edited', self.on_cell_edited, (tree,prop))
            column.set_cell_data_func(cell, _voucher_data_func, prop)

        setup_column('voucher_treeview', 'voucher_herb_column',
                     'voucher_herb_cell', 'herbarium')
        setup_column('voucher_treeview', 'voucher_code_column',
                     'voucher_code_cell', 'code')

        setup_column('parent_voucher_treeview', 'parent_voucher_herb_column',
                     'parent_voucher_herb_cell', 'herbarium')
        setup_column('parent_voucher_treeview','parent_voucher_code_column',
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


    def dirty(self):
        return self.__dirty


    def on_cell_edited(self, cell, path, new_text, data):
        treeview, prop = data
        treemodel = self.view.widgets[treeview].get_model()
        rooted = treemodel[path][0]
        if getattr(rooted, prop) == new_text:
            return  # didn't change
        setattr(rooted, prop, utils.utf8(new_text))
        self.__dirty = True
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
        self.__dirty = True
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
            expander.set_expanded(False) # all are collapsed to start

        # if no verifications were added then add an empty VerificationBox
        if len(self.view.widgets.verifications_parent_box.get_children()) < 1:
            self.add_verification_box()

        # expand the first verification expander
        self.view.widgets.verifications_parent_box.get_children()[0].\
            set_expanded(True)
        self._dirty = False


    def dirty(self):
        return self._dirty

    def refresh_view(self):
        pass


    def on_add_clicked(self, *args):
        self.add_verification_box()


    def add_verification_box(self, model=None):
        box = VerificationPresenter.VerificationBox(self, model)
        self.view.widgets.\
            verifications_parent_box.pack_start(box, expand=False, fill=False)
        self.view.widgets.verifications_parent_box.reorder_child(box, 0)
        box.show_all()
        return box


    class VerificationBox(gtk.HBox):

        def __init__(self, parent, model):
            super(VerificationPresenter.VerificationBox,
                  self).__init__(self)
            check(not model or isinstance(model, Verification))

            self.dirty = False
            self.presenter = parent
            self.model = model
            if not self.model:
                self.model = Verification()

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
            self.presenter.view.connect(entry, 'changed',
                                        self.on_entry_changed, 'verifier')

            # date entry
            self.date_entry = self.widgets.ver_date_entry
            if self.model.date:
                format = prefs.prefs[prefs.date_format_pref]
                safe = utils.xml_safe(self.model.date.strftime(format))
                self.date_entry.props.text = safe
            else:
                self.date_entry.props.text = utils.xml_safe(utils.today_str())
            self.presenter.view.connect(self.date_entry, 'changed',
                                        self.on_date_entry_changed)

            # reference entry
            ref_entry = self.widgets.ver_ref_entry
            if self.model.reference:
                ref_entry.props.text = self.model.reference
            self.presenter.view.connect(ref_entry, 'changed',
                                        self.on_entry_changed, 'reference')

            # species entries
            def sp_get_completions(text):
                query = self.presenter.session.query(Species).join('genus').\
                    filter(utils.ilike(Genus.genus, '%s%%' % text)).\
                    filter(Species.id != self.model.id)
                return query
            def sp_cell_data_func(col, cell, model, treeiter, data=None):
                cell.set_property('text', str(model[treeiter][0]))

            entry = self.widgets.ver_prev_taxon_entry
            def on_prevsp_select(value):
                self.set_model_attr('prev_species', value)
            self.presenter.view.attach_completion(entry, sp_cell_data_func)
            if self.model.prev_species:
                entry.props.text = self.model.prev_species
            self.presenter.assign_completions_handler(entry,sp_get_completions,
                                                      on_prevsp_select)

            entry = self.widgets.ver_new_taxon_entry
            def on_sp_select(value):
                self.set_model_attr('species', value)
            self.presenter.view.attach_completion(entry, sp_cell_data_func)
            if self.model.species:
                entry.props.text = self.model.species
            self.presenter.assign_completions_handler(entry,sp_get_completions,
                                                      on_sp_select)

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
                cell.set_property('markup', '<b>%s</b>  :  %s' \
                                      % (level, descr))
            combo.set_cell_data_func(renderer, cell_data_func)
            model = gtk.ListStore(int, str)
            for level, descr in ver_level_descriptions.iteritems():
                model.append([level, descr])
            combo.set_model(model)
            if self.model.level:
                utils.set_widget_value(combo, self.model.level)
            self.presenter.view.connect(combo, 'changed',
                                        self.on_level_combo_changed)

            # notes text view
            buff = gtk.TextBuffer()
            if self.model.notes:
                buff.props.text = self.model.notes
            self.presenter.view.connect(buff, 'changed', self.on_entry_changed,
                                        'notes')
            textview = self.widgets.ver_notes_textview
            textview.set_border_width(1)

            # remove button
            button = self.widgets.ver_remove_button
            #self._sid = button.connect('clicked',self.on_remove_button_clicked)
            self._sid = self.presenter.view.connect(button, 'clicked',
                                          self.on_remove_button_clicked)

            self.update_label()


        def on_date_entry_changed(self, entry, data=None):
            from bauble.editor import ValidatorError
            value = None
            PROBLEM = 'INVALID_DATE'
            try:
                value = editor.DateValidator().to_python(entry.props.text)
            except ValidatorError, e:
                self.presenter.add_problem(PROBLEM, entry)
            else:
                self.presenter.remove_problem(PROBLEM, entry)
            self.set_model_attr('date', value)


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
            self.presenter._dirty = True
            self.presenter.parent_ref().refresh_sensitivity()


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
                # this is a little voodoo to set the date on the model
                # since when we create a new verification box we add
                # today's date to the entry but we don't set the model
                # so the presenter doesn't appear dirty...we have to
                # use a tmp variable since the changed signal won't
                # fire if the new value is the same as the old
                tmp = self.date_entry.props.text
                self.date_entry.props.text = ''
                self.date_entry.props.text = tmp
                # if the verification is new and isn't yet associated
                # with an accession then set the accession when we
                # start changing values, this way we can setup a dummy
                # verification in the interface
                if not self.model.accession:
                    self.presenter.model.verifications.append(self.model)
            self.presenter._dirty = True
            self.update_label()
            self.presenter.parent_ref().refresh_sensitivity()


        def update_label(self):
            parts = []
            if self.model.date:
                parts.append('<b>%(date)s</b> : ')
            if self.model.species:
                parts.append('verified as %(species)s ')
            if self.model.verifier:
                parts.append('by %(verifier)s')
            label = ' '.join(parts) % dict(date=self.model.date,
                                           species=self.model.species,
                                           verifier=self.model.verifier)
            self.widgets.ver_expander_label.props.use_markup = True
            self.widgets.ver_expander_label.props.label = label


        def set_expanded(self, expanded):
            self.widgets.ver_expander.props.expanded = expanded






class AccessionEditorPresenter(editor.GenericEditorPresenter):

    widget_to_field_map = {'acc_code_entry': 'code',
                           'acc_id_qual_combo': 'id_qual',
                           'acc_date_accd_entry': 'date_accd',
                           'acc_date_recvd_entry': 'date_recvd',
                           'acc_prov_combo': 'prov_type',
                           'acc_wild_prov_combo': 'wild_prov_status',
                           'acc_species_entry': 'species',
                           'acc_source_type_combo': 'source_type',
                           'acc_private_check': 'private'}

    PROBLEM_INVALID_DATE = random()
    PROBLEM_DUPLICATE_ACCESSION = random()
    PROBLEM_ID_QUAL_RANK_REQUIRED = random()

    # keep references to donation and collection box so they don't get
    # destroyed when we reparent them
    _source_box_map = {}

    def __init__(self, model, view):
        '''
        @param model: an instance of class Accession
        @param view: an instance of AccessionEditorView
        '''
        super(AccessionEditorPresenter, self).__init__(model, view)
        self.__dirty = False
        self.session = object_session(model)
        self._original_source = self.model.source
        self._original_code = self.model.code
        self.current_source_box = None
        self.source_presenter = None
        self._source_box_map[Donation] = self.view.widgets.donation_box
        self._source_box_map[Collection] = self.view.widgets.collection_box
        self._source_box_map[SourcePropagation] = \
            self.view.widgets.source_prop_box

        if not model.code:
            model.code = get_next_code()
            #self.__dirty = True

        # reset the source_box_parent in case it still has a child
        # from a previous run of the accession editor
        map(self.view.widgets.source_box_parent.remove,
            self.view.widgets.source_box_parent.get_children())

        self.ver_presenter = VerificationPresenter(self, self.model, self.view,
                                                   self.session)
        self.voucher_presenter = VoucherPresenter(self, self.model, self.view,
                                                  self.session)

        notes_parent = self.view.widgets.notes_parent_box
        notes_parent.foreach(notes_parent.remove)
        self.notes_presenter = \
            editor.NotesPresenter(self, 'notes', notes_parent)

        # set current page so we don't open the last one that was open
        self.view.widgets.acc_notebook.set_current_page(0)

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

        self.init_source_tab()

        # TODO: refresh_view() will fire signal handlers for any
        # connected widgets and can be tricky with resetting values
        # that already exist in the model.  Although this usually
        # isn't a problem its sloppy.  We need a better way to update
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
            return query.filter(and_(Species.genus_id == Genus.id,
                                     or_(ilike(Genus.genus, '%s%%' % text),
                                         ilike(Genus.genus, '%s%%' % genus))))

        def on_select(value):
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
            msg = _('The species <b>%(synonym)s</b> is a synonym of '\
                        '<b>%(species)s</b>.\n\nWould you like to choose '\
                        '<b>%(species)s</b> instead?' \
                        % {'synonym': syn.synonym, 'species': syn.species})
            box = None
            def on_response(button, response):
                self.view.widgets.remove_parent(box)
                box.destroy()
                if response:
                    self.view.widgets.acc_species_entry.\
                        set_text(utils.utf8(syn.species))
                    set_model(syn.species)
                else:
                    set_model(value)
            box = utils.add_message_box(self.view.widgets.message_box_parent,
                                        utils.MESSAGE_BOX_YESNO)
            box.message = msg
            box.on_response = on_response
            box.show()


        self.assign_completions_handler('acc_species_entry',
                                        sp_get_completions,
                                        on_select=on_select)
        self.assign_simple_handler('acc_prov_combo', 'prov_type')
        self.assign_simple_handler('acc_wild_prov_combo', 'wild_prov_status')
        self.assign_simple_handler('acc_recvd_type_comboentry', 'recvd_type')

        # TODO: could probably replace this by just passing a valdator
        # to assign_simple_handler...UPDATE: but can the validator handle
        # adding a problem to the widget...if we passed it the widget it
        # could
        self.view.connect('acc_code_entry', 'changed',
                          self.on_acc_code_entry_changed)

        # date received
        self.view.connect('acc_date_recvd_entry', 'changed',
                          self.on_date_entry_changed, 'date_recvd')
        utils.setup_date_button(self.view.widgets.acc_date_recvd_entry,
                               self.view.widgets.acc_date_recvd_button)

        # date accessioned
        self.view.connect('acc_date_accd_entry', 'changed',
                          self.on_date_entry_changed, 'date_accd')
        utils.setup_date_button(self.view.widgets.acc_date_accd_entry,
                               self.view.widgets.acc_date_accd_button)

        self.assign_simple_handler('acc_id_qual_combo', 'id_qual',
                                   editor.UnicodeOrNoneValidator())
        self.assign_simple_handler('acc_private_check', 'private')
        self.assign_simple_handler('acc_memorial_check', 'memorial')
        self.assign_simple_handler('acc_pisbg_check', 'pisbg')

        from bauble.plugins.garden import init_location_comboentry
        def on_loc1_select(value):
            self.set_model_attr('intended_location_id')
        init_location_comboentry(self,
                                 self.view.widgets.intended_loc_comboentry,
                                 on_loc1_select)
        def on_loc2_select(value):
            self.set_model_attr('intended2_location_id')
        init_location_comboentry(self,
                                 self.view.widgets.intended2_loc_comboentry,
                                 on_loc2_select)

        self.refresh_sensitivity()



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
        it = model.append([str(species.sp), 'sp'])
        if self.model.id_qual_rank == 'sp':
            active = it

        infrasp_parts = []
        for level in (1,2,3,4):
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


    def dirty(self):
        presenters = [self.ver_presenter, self.voucher_presenter,
                      self.notes_presenter]
        dirty_kids = [p.dirty() for p in presenters]
        if self.source_presenter is None:
            return self.__dirty or True in dirty_kids
        return self.source_presenter.dirty() or self.__dirty or \
            True in dirty_kids


    def on_acc_code_entry_changed(self, entry, data=None):
        text = entry.get_text()
        query = self.session.query(Accession)
        if text != self._original_code \
               and query.filter_by(code=unicode(text)).count()>0:
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
        """
        Changed signal handdler for acc_date_recvd_entry and acc_date_accd_entry

        :param prop: the model property to change, should be
          date_recvd or date_accd
        """
        from bauble.editor import ValidatorError
        value = None
        PROBLEM = 'INVALID_DATE'
        try:
            value = editor.DateValidator().to_python(entry.props.text)
        except ValidatorError, e:
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
        self.__dirty = True
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


    def refresh_sensitivity(self):
        """
        Refresh the sensitivity of the fields and accept buttons according
        to the current values in the model.
        """
        if self.model.species and self.model.id_qual:
            self.view.widgets.acc_id_qual_rank_combo.set_sensitive(True)
        else:
            self.view.widgets.acc_id_qual_rank_combo.set_sensitive(False)

        sensitive = self.dirty()
        # if not source_type is None and self._original_source is None
        if len(self.problems) != 0:
            sensitive = False
        elif self.model.source_type and self.source_presenter \
                and len(self.source_presenter.problems) != 0:
            sensitive = False
        elif not self.model.code or not self.model.species:
            sensitive = False
        self.view.set_accept_buttons_sensitive(sensitive)


    def on_source_type_combo_changed(self, combo, data=None):
        '''
        Change which one of donation_box/collection_box is packed into
        source box and setup the appropriate presenter.
        '''
        treeiter = combo.get_active_iter()
        if not treeiter:
            return
        presenter_class = combo.get_model()[treeiter][2]
        source_class = combo.get_model()[treeiter][1]
        source_type_changed = False

        # if the source type is None then set the model.source as None
        # and remove the source box
        if not source_class:
            if self.model.source is not None:
                self.set_model_attr('source', None)
                if self.current_source_box is not None:
                    self.view.widgets.remove_parent(self.current_source_box)
                    self.current_source_box = None
            return

        # TODO: if source_type is set and self.model.source is None then create
        # a new empty source object and attach it to the model

        # the source_type has changed from what it originally was
        new_source = None
        if not self.model.is_source_type(source_class):
            source_type_changed = True
            try:
                new_source = source_class()
            except KeyError, e:
                debug('unknown source type: %s' % e)
                raise
            if isinstance(new_source, type(self._original_source)):
                new_source = self._original_source
        elif source_class is not None and self.model.source is None:
            # the source type is set but there is no corresponding model.source
            try:
                new_source = source_class()
            except KeyError, e:
                debug('Source type is set but the source attribute None: %s' \
                          % e)
                raise

        # replace source box contents with our new box
        #source_box = self.view.widgets.source_box
        source_box_parent = self.view.widgets.source_box_parent
        if self.current_source_box is not None:
            self.view.widgets.remove_parent(self.current_source_box)
        if source_class is not None:
            self.current_source_box = self._source_box_map[source_class]
            self.view.widgets.remove_parent(self.current_source_box)
            source_box_parent.add(self.current_source_box)
        else:
            self.current_source_box = None

        if new_source is not None:
            self.source_presenter = presenter_class(self, new_source,
                                                    self.view, self.session)
            if new_source != self.model.source:
                # don't set the source if it hasn't changed
                self.set_model_attr('source', new_source)
        elif self.model.source is not None:
            # didn't create a new source but we need to create a
            # source presenter
            self.source_presenter = presenter_class(self, self.model.source,
                                                    self.view, self.session)


    def init_source_tab(self):
        '''
        initialized the source expander contents
        '''
        combo = self.view.widgets.acc_source_type_combo
        combo.clear()
        model = gtk.ListStore(str, object, object)
        values = [[source_type_values[u'Collection'], Collection,
                   CollectionPresenter],
                  [source_type_values[u'Donation'], Donation,
                   DonationPresenter],
                  [source_type_values[u'SourcePropagation'], SourcePropagation,
                   SourcePropagationPresenter],
                  [None, None, None]]
        for v in values:
            model.append(v)
        combo.set_model(model)
        combo.set_active(-1)
        renderer = gtk.CellRendererText()
        combo.pack_start(renderer, True)
        combo.add_attribute(renderer, 'text', 0)
        self.view.connect('acc_source_type_combo', 'changed',
                          self.on_source_type_combo_changed)


    def refresh_view(self):
        '''
        get the values from the model and put them in the view
        '''
        for widget, field in self.widget_to_field_map.iteritems():
            if field == 'species_id':
                value = self.model.species
            else:
                value = getattr(self.model, field)
            if value is not None and field == 'date':
                value = '%s/%s/%s' % (value.day, value.month,
                                      '%04d' % value.year)
            self.view.set_widget_value(widget, value)


        # set the source_type combo to the translated source type
        # string, not the source_type value
        self.view.set_widget_value('acc_source_type_combo',
                                   source_type_values[self.model.source_type])

        self.view.set_widget_value('acc_wild_prov_combo',
                          wild_prov_status_values[self.model.wild_prov_status],
                                   index=1)
        self.view.set_widget_value('acc_prov_combo',
                                   prov_type_values[self.model.prov_type],
                                   index=1)

        if self.model.private is None:
            self.view.widgets.acc_private_check.set_inconsistent(False)
            self.view.widgets.acc_private_check.set_active(False)

        sensitive = self.model.prov_type == 'Wild'
        self.view.widgets.acc_wild_prov_combo.set_sensitive(sensitive)
        self.view.widgets.acc_wild_prov_combo.set_sensitive(sensitive)


    def start(self):
        r = self.view.start()
        return r



class AccessionEditor(editor.GenericModelViewPresenterEditor):

    # these have to correspond to the response values in the view
    RESPONSE_OK_AND_ADD = 11
    RESPONSE_NEXT = 22
    ok_responses = (RESPONSE_OK_AND_ADD, RESPONSE_NEXT)


    def __init__(self, model=None, parent=None):
        '''
        @param model: Accession instance or None
        @param parent: the parent widget
        '''
        # the view and presenter are created in self.start()
        self.view = None
        self.presenter = None
        if model is None:
            model = Accession()

        super(AccessionEditor, self).__init__(model, parent)
        if not parent and bauble.gui:
            parent = bauble.gui.window
        self.parent = parent
        self._committed = []

        view = AccessionEditorView(parent=self.parent)
        self.presenter = AccessionEditorPresenter(self.model, view)

        # add quick response keys
        self.attach_response(view.get_window(), gtk.RESPONSE_OK, 'Return',
                             gtk.gdk.CONTROL_MASK)
        self.attach_response(view.get_window(), self.RESPONSE_OK_AND_ADD, 'k',
                             gtk.gdk.CONTROL_MASK)
        self.attach_response(view.get_window(), self.RESPONSE_NEXT, 'n',
                             gtk.gdk.CONTROL_MASK)

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
                if self.presenter.dirty():
                    self.commit_changes()
                    self._committed.append(self.model)
            except SQLError, e:
                msg = _('Error committing changes.\n\n%s') % \
                      utils.xml_safe_utf8(unicode(e.orig))
                utils.message_details_dialog(msg, str(e), gtk.MESSAGE_ERROR)
                return False
            except Exception, e:
                msg = _('Unknown error when committing changes. See the '\
                        'details for more information.\n\n%s') \
                        % utils.xml_safe_utf8(e)
                utils.message_details_dialog(msg, traceback.format_exc(),
                                             gtk.MESSAGE_ERROR)
                return False
        elif self.presenter.dirty() and utils.yes_no_dialog(not_ok_msg) \
                 or not self.presenter.dirty():
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
            msg = _('You must first add or import at least one species into '\
                        'the database before you can add accessions.')
            utils.message_dialog(msg)
            return

        while True:
            response = self.presenter.start()
            self.presenter.view.save_state()
            if self.handle_response(response):
                break

        self.session.close() # cleanup session
        self.presenter.cleanup()
        return self._committed


    @staticmethod
    def __cleanup_source_prop_model(model):
        '''
        '''
        return model


    @staticmethod
    def __cleanup_donation_model(model):
        '''
        '''
        return model


    @staticmethod
    def __cleanup_collection_model(model):
        '''
        '''
        # TODO: we should raise something besides commit ValueError
        # so we can give a meaningful response
        if model.latitude is not None or model.longitude is not None:
            if (model.latitude is not None and model.longitude is None) or \
                (model.longitude is not None and model.latitude is None):
                msg = _('model must have both latitude and longitude or '\
                        'neither')
                raise ValueError(msg)
            elif model.latitude is None and model.longitude is None:
                model.geo_accy = None # don't save
        else:
            model.geo_accy = None # don't save

        # reset the elevation accuracy if the elevation is None
        if model.elevation is None:
            model.elevation_accy = None
        return model


    def commit_changes(self):
        if isinstance(self.model.source, Collection):
            self.__cleanup_collection_model(self.model.source)
        elif isinstance(self.model.source, Donation):
            self.__cleanup_donation_model(self.model.source)
        elif isinstance(self.model.source, SourcePropagation):
            self.__cleanup_source_prop_model(self.model.source)
        if self.model.id_qual is None:
            self.model.id_qual_rank = None
        return super(AccessionEditor, self).commit_changes()



# import at the bottom to avoid circular dependencies
from bauble.plugins.plants.genus import Genus
from bauble.plugins.plants.species_model import Species, SpeciesSynonym
from bauble.plugins.garden.donor import Donor, DonorEditor

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
        InfoExpander.__init__(self, _("General"), widgets)
        general_box = self.widgets.general_box
        self.widgets.general_window.remove(general_box)
        self.vbox.pack_start(general_box)
        self.current_obj = None
        self.private_image = self.widgets.acc_private_data

        def on_species_clicked(*args):
            select_in_search_results(self.current_obj.species)
        utils.make_label_clickable(self.widgets.name_data, on_species_clicked)

        def on_nplants_clicked(*args):
            cmd = 'plant where accession.code="%s"' % self.current_obj.code
            bauble.gui.send_command(cmd)
        utils.make_label_clickable(self.widgets.nplants_data,
                                   on_nplants_clicked)


    def update(self, row):
        '''
        '''
        self.current_obj = row
        self.set_widget_value('acc_code_data', '<big>%s</big>' % \
                              utils.xml_safe(unicode(row.code)))

        # TODO: i don't know why we can't just set the visible
        # property to False here
        acc_private = self.widgets.acc_private_data
        if row.private:
            if acc_private.parent != self.widgets.acc_code_box:
                self.widgets.acc_code_box.pack_start(acc_private)
        else:
            self.widgets.remove_parent(acc_private)

        #self.set_widget_value('name_data', '%s %s' % \
        #                      (row.species.markup(True), row.id_qual or '',))
        self.set_widget_value('name_data', row.species_str(markup=True))

        session = object_session(row)
        # TODO: it would be nice if we did something like 13 Living,
        # 2 Dead, 6 Unknown, etc

        nplants = session.query(Plant).filter_by(accession_id=row.id).count()
        self.set_widget_value('nplants_data', nplants)
        self.set_widget_value('prov_data', prov_type_values[row.prov_type],
                              False)


class SourceExpander(InfoExpander):

    def __init__(self, widgets):
        InfoExpander.__init__(self, _('Source'), widgets)
        self.curr_box = None
        self.box_map = {Collection: (self.widgets.collections_box,
                                     self.update_collections),
                        Donation: (self.widgets.donations_box,
                                   self.update_donations),
                        SourcePropagation: (self.widgets.source_prop_box,
                                            self.update_source_prop)
                        }

        self.current_obj = None
        def on_donor_clicked(*args):
            select_in_search_results(self.current_obj.donor)
        utils.make_label_clickable(self.widgets.donor_data, on_donor_clicked)


    def update_collections(self, collection):

        self.set_widget_value('loc_data', collection.locale)
        self.set_widget_value('datum_data', collection.gps_datum)

        geo_accy = collection.geo_accy
        if not geo_accy:
            geo_accy = ''
        else:
            geo_accy = '(+/- %sm)' % geo_accy

        if collection.latitude:
            dir, deg, min, sec = latitude_to_dms(collection.latitude)
            lat_str = '%.2f (%s %s\302\260%s\'%.2f") %s' % \
                (collection.latitude, dir, deg, min, sec, geo_accy)
            self.set_widget_value('lat_data', lat_str)

        if collection.longitude:
            dir, deg, min, sec = longitude_to_dms(collection.longitude)
            long_str = '%.2f (%s %s\302\260%s\'%.2f") %s' % \
                (collection.longitude, dir, deg, min, sec, geo_accy)
            self.set_widget_value('lon_data', long_str)

        if collection.elevation_accy:
            elevation = '%sm (+/- %sm)' % (collection.elevation,
                                           collection.elevation_accy)
            self.set_widget_value('elev_data', elevation)


        self.set_widget_value('coll_data', collection.collector)
        self.set_widget_value('date_data', collection.date)
        self.set_widget_value('collid_data', collection.collectors_code)
        self.set_widget_value('habitat_data', collection.habitat)
        self.set_widget_value('collnotes_data', collection.notes)


    def update_donations(self, donation):
        self.current_obj = donation
        session = object_session(donation)
        donor = session.query(Donor).get(donation.donor_id)
        donor_str = utils.xml_safe(utils.utf8(donor))
        self.set_widget_value('donor_data', donor_str)
        self.set_widget_value('donid_data', donation.donor_acc)
        self.set_widget_value('donnotes_data', donation.notes)


    def update_source_prop(self, source_prop):
        # TODO: implement this
        pass


    def update(self, value):
        if self.curr_box is not None:
            parent = self.curr_box.get_parent()
            if parent:
                parent.remove(self.curr_box)

        if value is None:
            self.set_expanded(False)
            self.set_sensitive(False)
            return

        box, update = self.box_map[value.__class__]
        self.widgets.remove_parent(box)
        self.curr_box = box
        update(value)
        self.vbox.pack_start(self.curr_box)
        self.set_expanded(True)
        self.set_sensitive(True)



class VerificationsExpander(InfoExpander):
    """
    the accession's notes
    """

    def __init__(self, widgets):
        super(VerificationsExpander, self).__init__(_("Verifications"),widgets)
        # notes_box = self.widgets.notes_box
        # self.widgets.notes_window.remove(notes_box)
        # self.vbox.pack_start(notes_box)


    def update(self, row):
        pass
        #self.set_widget_value('notes_data', row.notes)


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
        self.vouchers = VouchersExpander(self.widgets)
        self.add_expander(self.vouchers)
        self.verifications = VerificationsExpander(self.widgets)
        self.add_expander(self.verifications)

        self.links = view.LinksExpander('notes')
        self.add_expander(self.links)

        self.props = PropertiesExpander()
        self.add_expander(self.props)


    def update(self, row):
        self.general.update(row)
        self.props.update(row)

        if row.verifications:
            self.verifications.update(row)
        self.verifications.set_expanded(row.verifications != None)
        self.verifications.set_sensitive(row.verifications != None)

        self.vouchers.update(row)

        urls = filter(lambda x: x!=[], \
                          [utils.get_urls(note.note) for note in row.notes])
        if not urls:
            self.links.props.visible = False
            self.links._sep.props.visible = False
        else:
            self.links.props.visible = True
            self.links._sep.props.visible = True
            self.links.update(row)

        # TODO: should test if the source should be expanded from the prefs
        self.source.update(row.source)


# it's easier just to put this here instead of source.py to avoid
# playing around with imports for AccessionInfoBox
class SourceInfoBox(AccessionInfoBox):
    def update(self, row):
        super(SourceInfoBox, self).update(row.accession)


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
          "Bermuda 1957" : "Bermuda 1957- Bermuda Islands",
          "Bogota Observ": "Bogata Obsrvatry- Colombia",
          "Campo Inchspe": "Campo Inchauspe- Argentina",
          "Canton Ast '66": "Canton Astro 1966- Phoenix Islands",
          "Cape": "Cape- South Africa",
          "Cape Canavrl": "Cape Canaveral- Florida, Bahama Islands",
          "Carthage": "Carthage- Tunisia",
          "CH-1903": "CH 1903- Switzerland",
          "Chatham 1971" : "Chatham 1971- Chatham Island (New Zealand)",
          "Chua Astro": "Chua Astro- Paraguay",
          "Corrego Alegr" : "Corrego Alegre- Brazil",
          "Croatia" : "Croatia",
          "Djakarta" : "Djakarta (Batavia)- Sumatra Island (Indonesia)",
          "Dos 1968" : "Dos 1968- Gizo Island (New Georgia Islands)",
          "Dutch" : "Dutch",
          "Easter Isld 67" : "Easter Island 1967",
          "European 1950" : "European 1950- Austria, Belgium, Denmark, Finland, France, Germany, Gibraltar, Greece, Italy, Luxembourg, Netherlands, Norway, Portugal, Spain, Sweden, Switzerland",
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
          "Indian Bngldsh" : "Indian- Bangladesh, India, Nepal",
          "Indian Thailand" : "Indian- Thailand, Vietnam",
          "Indonesia 74" : "Indonesia 1974- Indonesia",
          "Ireland 1965" : "Ireland 1965- Ireland",
          "ISTS 073 Astro": "ISTS 073 ASTRO '69- Diego Garcia",
          "Johnston Island" : "Johnston Island NAD27 Central",
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
