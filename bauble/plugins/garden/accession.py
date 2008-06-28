# -*- coding: utf-8 -*-

#
# accessions module
#

import sys
import re
import os
import traceback
from random import random
from datetime import datetime
import xml.sax.saxutils as saxutils
from decimal import Decimal, ROUND_DOWN

import gtk
import gobject
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.orm.session import object_session
from sqlalchemy.exceptions import SQLError

import bauble
from bauble.error import check
import bauble.utils as utils
import bauble.paths as paths
from bauble.i18n import *
from bauble.editor import *
from bauble.utils.log import debug
from bauble.prefs import prefs
from bauble.error import CommitException
from bauble.types import Enum
from bauble.view import InfoBox, InfoExpander, PropertiesExpander, \
     select_in_search_results
from bauble.plugins.garden.donor import Donor


# TODO: underneath the species entry create a label that shows information
# about the family of the genus of the species selected as well as more
# info about the genus so we know exactly what plant is being selected
# e.g. Malvaceae (sensu lato), Hibiscus (senso stricto)

# FIXME: time.mktime can't handle dates before 1970 on win32

# TODO: there is a bug if you edit an existing accession and change the
# accession number but change it back to the original then it indicates the
# number is invalid b/c it's a duplicate

# TODO: make sure an accessions source record is being deleted when the
# accession is being deleted, and create a test for the same thing

# date regular expression for date entry fields
_date_regex = re.compile('(?P<day>\d?\d)/(?P<month>\d?\d)/(?P<year>\d\d\d\d)')

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
    #dec = Decimal((abs(Decimal(str(sec)))/Decimal('3600.0')) + \
    #      (abs(Decimal(str(min)))/Decimal('60.0')) + \
    #       Decimal(abs(deg)), 5)
    if dir in ('W', 'S'):
        dec = -dec

    return dec.quantize(nplaces)



def edit_callback(value):
    session = bauble.Session()
    e = AccessionEditor(model=session.merge(value))
    return e.start() != None


def add_plants_callback(value):
    session = bauble.Session()
    e = PlantEditor(model=Plant(accession=session.merge(value)))
    return e.start() != None


def remove_callback(value):
    if len(value.plants) > 0:
        msg = _('%s plants depend on this accession: <b>%s</b>\n\n'\
                'Are you sure you want to remove accession <b>%s</b>?') % \
                (len(value.plants),
                 utils.xml_safe_utf8(', '.join(map(utils.utf8, value.plants))),
                 utils.xml_safe_utf8(unicode(value)))
    else:
        msg = _("Are you sure you want to remove accession <b>%s</b>?") % \
                  utils.xml_safe_utf8(unicode(value))
    if not utils.yes_no_dialog(msg):
        return
    try:
        session = bauble.Session()
        obj = session.load(value.__class__, value.id)
        session.delete(obj)
        session.commit()
    except Exception, e:
        msg = _('Could not delete.\n\n%s') % utils.xml_safe_utf8(unicode(e))
        utils.message_details_dialog(msg, traceback.format_exc(),
                                     type=gtk.MESSAGE_ERROR)
    return True


acc_context_menu = [('Edit', edit_callback),
                    ('--', None),
                    ('Add plants', add_plants_callback),
                    ('--', None),
                    ('Remove', remove_callback)]

def acc_markup_func(acc):
    '''
    '''
    if acc.id_qual is None:
        sp_str = acc.species.markup(authors=False)
    else:
        sp_str = '%s %s' % (acc.species.markup(authors=False),
                            acc.id_qual)
    return utils.xml_safe_utf8(unicode(acc)), sp_str




# prov_type:
# ----------
# "Wild", # Wild,
# "Propagule of cultivated wild plant", # Propagule of wild plant in cultivation
# "Not of wild source", # Not of wild source
# "Insufficient Data", # Insufficient data
# "Unknown"

# wild_prov_status:
# -----------------
# "Wild native", # Endemic found within it indigineous range
# "Wild non-native", # Propagule of wild plant in cultivation
# "Cultivated native", # Not of wild source
# "Insufficient Data", # Insufficient data
# "Unknown",

# date: date accessioned

# TODO: accession should have a one-to-many relationship on verifications
    #ver_level = StringCol(length=2, default=None) # verification level
    #ver_name = StringCol(length=50, default=None) # verifier's name
    #ver_date = DateTimeCol(default=None) # verification date
    #ver_hist = StringCol(default=None)  # verification history
    #ver_lit = StringCol(default=None) # verification lit
    #ver_id = IntCol(default=None) # ?? # verifier's ID??

# TODO: see HISPID for a good explanation of what should be included
# in the verification data
verification_table = bauble.Table('verification', bauble.metadata,
                           Column('id', Integer, primary_key=True),
                           Column('verifier', Unicode(64)),
                           Column('date', Date),
                           Column('literature', UnicodeText),
                           Column('level', Text),# i don't know what this is
                           Column('accession_id', Integer,
                                  ForeignKey('accession.id')))


class Verification(bauble.BaubleMapper):
    pass


accession_table = bauble.Table('accession', bauble.metadata,
                        Column('id', Integer, primary_key=True),
                        Column('code', Unicode(20), nullable=False,
                               unique=True),
                        Column('prov_type',
                               Enum(values=['Wild',
                                          'Propagule of cultivated wild plant',
                                            "Not of wild source",
                                            "Insufficient Data",
                                            "Unknown",
                                            None],
                                    empty_to_none=True)),
                        Column('wild_prov_status',
                               Enum(values=["Wild native",
                                            "Wild non-native",
                                            "Cultivated native",
                                            "Insufficient Data",
                                            "Unknown",
                                            None],
                                    empty_to_none=True)),
                        Column('date', Date),
                        Column('source_type',
                               Enum(values=['Collection', 'Donation',
                                            None], empty_to_none=True)),
                        Column('notes', UnicodeText),
                        # "id_qual" new in 0.7
                        Column('id_qual',
                               Enum(values=['aff.', 'cf.', 'Incorrect',
                                            'forsan', 'near', '?', None],
                                    empty_to_none=True)),
                        # "private" new in 0.8b2
                        Column('private', Boolean, default=False),
                        Column('species_id', Integer, ForeignKey('species.id'),
                               nullable=False))


class Accession(bauble.BaubleMapper):

    def __str__(self):
        return self.code


    def _get_source(self):
        if self.source_type is None:
            return None
        elif self.source_type == u'Collection':
            return self._collection
        elif self.source_type == u'Donation':
            return self._donation
        raise ValueError(_('unknown source_type in accession: %s') % \
                             self.source_type)
    def _set_source(self, source):
        if self.source is not None:
            obj = self.source
            obj._accession = None
            utils.delete_or_expunge(obj)
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


from bauble.plugins.garden.source import Donation, donation_table, \
    Collection, collection_table
from bauble.plugins.garden.plant import Plant, PlantEditor, plant_table


# NOTES: be careful with the _accession property on the Collection and
# Donation tables, if you try to set the accession for one of these objects
# using the _accession property you will have problems using Accession.source
# because the Accession.source_type property won't be set
mapper(Accession, accession_table,
    properties = {\
        '_collection':
        relation(Collection, cascade='all, delete-orphan', uselist=False,
                 backref=backref('_accession', uselist=False)),
        '_donation':
        relation(Donation, cascade='all, delete-orphan', uselist=False,
                 backref=backref('_accession', uselist=False)),
        'plants':
        relation(Plant, cascade='all, delete-orphan',
                 order_by=plant_table.c.code, backref='accession'),
        'verifications':
        relation(Verification, order_by='date', cascade='all, delete-orphan',
                 backref='accession')},
       )

mapper(Verification, verification_table)


# TODO: we don't use this anymore i don't think and its broken
# anyways, remove it?
#
# def get_source(row):
#     # TODO: in one of the release prior to 0.4.5 we put the string 'NoneType'
#     # into some of the accession.source_type columns, this can cause an error
#     # here but it's not critical, but we should make sure this doesn't happen
#     # again in the future, maybe incorporated into a test
#     if row.source_type == None:
#         return None
#     elif row.source_type == tables['Donation'].__name__:
#         # the __name__ should be 'Donation'
#         return row._donation
#     elif row.source_type == tables['Collection'].__name__:
#         return row._collection
#     else:
#         raise ValueError(_('unknown source type: %s') % str(row.source_type))


def _val_str(col):
    values = [str(v) for v in col.type.values if v is not None]
    if None in col.type.values:
        if hasattr(gtk.Widget, 'set_tooltip_markup'):
            values.append('&lt;None&gt;')
        else:
            values.append('<None>')
    return ', '.join(values)


class AccessionEditorView(GenericEditorView):

    expanders_pref_map = {'acc_notes_expander':
                          'editor.accession.notes.expanded',
                          'acc_source_expander':
                          'editor.accession.source.expanded'}

    _tooltips = {
        'acc_species_entry': _("The species must be selected from the list "\
                               "of completions. To add a species use the "\
                               "Species editor."),
        'acc_code_entry': _("The accession ID must be a unique code"),
        'acc_id_qual_combo': _("The ID Qualifier\n\n"
                               "Possible values: %s" %
                               _val_str(accession_table.c.id_qual)),
        'acc_date_entry': _('The date this species was accessioned.'),
        'acc_prov_combo': _('The origin or source of this accession.\n\n'
                            'Possible values: %s' %
                            _val_str(accession_table.c.prov_type)),
        'acc_wild_prov_combo': _('The wild status is used to clarify the '
                                 'provenance\n\nPossible values: %s' %
                                 _val_str(accession_table.c.wild_prov_status)),
        'acc_source_type_combo': _('The source type is in what way this '
                                   'accession was obtained'),
        'acc_notes_textview': _('Miscelleanous notes about this accession.'),
        'acc_private_check': _('Indicates whether this accession record ' \
                               'should be considered private.')
        }


    def __init__(self, parent=None):
        GenericEditorView.__init__(self, os.path.join(paths.lib_dir(),
                                                      'plugins', 'garden',
                                                      'editors.glade'),
                                   parent=parent)
        self.dialog = self.widgets.accession_dialog
        self.dialog.set_transient_for(parent)
        self.attach_completion('acc_species_entry',
                               cell_data_func=self.species_cell_data_func,
                               match_func=self.species_match_func)
        self.restore_state()
        self.connect_dialog_close(self.widgets.accession_dialog)

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


    def save_state(self):
        '''
        save the current state of the gui to the preferences
        '''
        for expander, pref in self.expanders_pref_map.iteritems():
            prefs[pref] = self.widgets[expander].get_expanded()


    def restore_state(self):
        '''
        restore the state of the gui from the preferences
        '''
        for expander, pref in self.expanders_pref_map.iteritems():
            expanded = prefs.get(pref, True)
            self.widgets[expander].set_expanded(expanded)


    def start(self):
        return self.widgets.accession_dialog.run()


    def datum_match(self, completion, key, iter, data=None):
        datum = completion.get_model()[iter][0]
        words = datum.split(' ')
        for w in words:
            if w.lower().startswith(key.lower()):
                return True
        return False


    def species_match_func(self, completion, key, iter, data=None):
        species = completion.get_model()[iter][0]
        if str(species).lower().startswith(key.lower()) \
               or str(species.genus.genus).lower().startswith(key.lower()):
            return True
        return False


    def species_cell_data_func(self, column, renderer, model, iter, data=None):
        v = model[iter][0]
        renderer.set_property('text', '%s (%s)' % (str(v), v.genus.family))



# TODO: should have a label next to lat/lon entry to show what value will be
# stored in the database, might be good to include both DMS and the float
# so the user can see both no matter what is in the entry. it could change in
# time as the user enters data in the entry
# TODO: shouldn't allow entering altitude accuracy without entering altitude,
# same for geographic accuracy
# TODO: should show an error if something other than a number is entered in
# the altitude entry
class CollectionPresenter(GenericEditorPresenter):

    widget_to_field_map = {'collector_entry': 'collector',
                           'coll_date_entry': 'date',
                           'collid_entry': 'collectors_code',
                           'locale_entry': 'locale',
                           'lat_entry': 'latitude',
                           'lon_entry': 'longitude',
                           'geoacc_entry': 'geo_accy',
                           'alt_entry': 'elevation',
                           'altacc_entry': 'elevation_accy',
                           'habitat_textview': 'habitat',
                           'coll_notes_textview': 'notes',
                           'datum_entry': 'gps_datum'
                           }

    # TODO: could make the problems be tuples of an id and description to
    # be displayed in a dialog or on a label ala eclipse
    PROBLEM_BAD_LATITUDE = random()
    PROBLEM_BAD_LONGITUDE = random()
    PROBLEM_INVALID_DATE = random()
    PROBLEM_INVALID_LOCALE = random()


    def __init__(self, model, view, session):
        GenericEditorPresenter.__init__(self, ModelDecorator(model), view)
        self.session = session
        self.refresh_view()

        self.assign_simple_handler('collector_entry', 'collector',
                                   UnicodeOrNoneValidator())
        self.assign_simple_handler('locale_entry', 'locale',
                                   UnicodeOrNoneValidator())
        self.assign_simple_handler('collid_entry', 'collectors_code',
                                   UnicodeOrNoneValidator())
        self.assign_simple_handler('geoacc_entry', 'geo_accy',
                                   IntOrNoneStringValidator())
        self.assign_simple_handler('alt_entry', 'elevation',
                                   FloatOrNoneStringValidator())
        self.assign_simple_handler('altacc_entry', 'elevation_accy',
                                   FloatOrNoneStringValidator())
        self.assign_simple_handler('habitat_textview', 'habitat',
                                   UnicodeOrNoneValidator())
        self.assign_simple_handler('coll_notes_textview', 'notes',
                                   UnicodeOrNoneValidator())
        # the list of completions are added in AccessionEditorView.__init__
        def on_match(completion, model, iter, data=None):
            value = model[iter][0]
            validator = UnicodeOrNoneValidator()
            self.model.gps_datum = validator.to_python(value)
            completion.get_entry().set_text(value)
        completion = self.view.widgets.datum_entry.get_completion()
        completion.connect('match-selected', on_match)
        self.assign_simple_handler('datum_entry', 'gps_datum',
                                   UnicodeOrNoneValidator())

        lat_entry = self.view.widgets.lat_entry
        lat_entry.connect('insert-text', self.on_lat_entry_insert)
        lat_entry.connect('delete-text', self.on_lat_entry_delete)

        lon_entry = self.view.widgets.lon_entry
        lon_entry.connect('insert-text', self.on_lon_entry_insert)
        lon_entry.connect('delete-text', self.on_lon_entry_delete)

        coll_date_entry = self.view.widgets.coll_date_entry
        coll_date_entry.connect('insert-text', self.on_date_entry_insert)
        coll_date_entry.connect('delete-text', self.on_date_entry_delete)

        utils.setup_date_button(coll_date_entry,
                                self.view.widgets.coll_date_button)

        # don't need to connection to south/west since they are in the same
        # groups as north/east
        north_radio = self.view.widgets.north_radio
        self.north_toggle_signal_id = north_radio.connect('toggled',
                                            self.on_north_south_radio_toggled)
        east_radio = self.view.widgets.east_radio
        self.east_toggle_signal_id = east_radio.connect('toggled',
                                            self.on_east_west_radio_toggled)

        for field in self.widget_to_field_map.values():
            self.model.add_notifier(field, self.on_field_changed)
        if self.model.locale is None or self.model.locale in ('', u''):
            self.add_problem(self.PROBLEM_INVALID_LOCALE)


    def on_field_changed(self, model, field):
        """
        Validates the fields when a field changes.
        """
        if self.model.locale is None or self.model.locale in ('', u''):
            self.add_problem(self.PROBLEM_INVALID_LOCALE)
        else:
            self.remove_problem(self.PROBLEM_INVALID_LOCALE)


    def start(self):
        raise Exception('CollectionEditorPresenter cannot be started')


    def dirty(self):
        return self.model.dirty


    def refresh_view(self):
        for widget, field in self.widget_to_field_map.iteritems():
            value = self.model[field]
##            debug('%s, %s, %s' % (widget, field, value))
            if value is not None and field == 'date':
                value = '%s/%s/%s' % (value.day, value.month,
                                      '%04d' % value.year)
            self.view.set_widget_value(widget, value)

        latitude = self.model.latitude
        if latitude is not None:
            dms_string ='%s %s\302\260%s"%s\'' % latitude_to_dms(latitude)
            self.view.widgets.lat_dms_label.set_text(dms_string)
            if latitude < 0:
                self.view.widgets.south_radio.set_active(True)
            else:
                self.view.widgets.north_radio.set_active(True)
        longitude = self.model.longitude
        if longitude is not None:
            dms_string ='%s %s\302\260%s"%s\'' % longitude_to_dms(longitude)
            self.view.widgets.lon_dms_label.set_text(dms_string)
            if longitude < 0:
                self.view.widgets.west_radio.set_active(True)
            else:
                self.view.widgets.east_radio.set_active(True)

        if self.model.elevation == None:
            self.view.widgets.altacc_entry.set_sensitive(False)

        if self.model.latitude is None or self.model.longitude is None:
            self.view.widgets.geoacc_entry.set_sensitive(False)
            self.view.widgets.datum_entry.set_sensitive(False)


    def on_date_entry_insert(self, entry, new_text, new_text_length, position,
                            data=None):
        entry_text = entry.get_text()
        cursor = entry.get_position()
        full_text = entry_text[:cursor] + new_text + entry_text[cursor:]
        self._set_date_from_text(full_text)


    def on_date_entry_delete(self, entry, start, end, data=None):
        text = entry.get_text()
        full_text = text[:start] + text[end:]
        self._set_date_from_text(full_text)


    def _set_date_from_text(self, text):
        if text == '':
            self.model.date = None
            self.remove_problem(self.PROBLEM_INVALID_DATE,
                                self.view.widgets.coll_date_entry)
            return

        dt = None # datetime
        m = _date_regex.match(text)
        if m is None:
            self.add_problem(self.PROBLEM_INVALID_DATE,
                             self.view.widgets.coll_date_entry)
        else:
#            debug('%s.%s.%s' % (m.group('year'), m.group('month'), \
#                                    m.group('day')))
            try:
                ymd = [int(x) for x in [m.group('year'), m.group('month'), \
                                        m.group('day')]]
                dt = datetime(*ymd).date()
                self.remove_problem(self.PROBLEM_INVALID_DATE,
                                    self.view.widgets.coll_date_entry)
            except:
                self.add_problem(self.PROBLEM_INVALID_DATE,
                                    self.view.widgets.coll_date_entry)
        self.model.date = dt


    def on_east_west_radio_toggled(self, button, data=None):
        direction = self._get_lon_direction()
        entry = self.view.widgets.lon_entry
        lon_text = entry.get_text()
        if lon_text == '':
            return
        if direction == 'W' and lon_text[0] != '-'  and len(lon_text) > 2:
            entry.set_text('-%s' % lon_text)
        elif direction == 'E' and lon_text[0] == '-' and len(lon_text) > 2:
            entry.set_text(lon_text[1:])


    def on_north_south_radio_toggled(self, button, data=None):
        direction = self._get_lat_direction()
        entry = self.view.widgets.lat_entry
        lat_text = entry.get_text()
        if lat_text == '':
            return
        if direction == 'S' and lat_text[0] != '-' and len(lat_text) > 2:
            entry.set_text('-%s' % lat_text)
        elif direction == 'N' and lat_text[0] == '-' and len(lat_text) > 2:
            entry.set_text(lat_text[1:])


    @staticmethod
    def _parse_lat_lon(direction, text):
        '''
        parse a latitude or longitude in a variety of formats
        '''
        bits = re.split(':| ', text.strip())
#        debug('%s: %s' % (direction, bits))
        if len(bits) == 1:
            dec = abs(float(text))
            if dec > 0 and direction in ('W', 'S'):
                dec = -dec
        elif len(bits) == 2:
            deg, tmp = map(float, bits)
            sec = tmp/60
            min = tmp-60
            dec = dms_to_decimal(direction, deg, min, sec)
        elif len(bits) == 3:
#            debug(bits)
            dec = dms_to_decimal(direction, *map(float, bits))
        else:
            raise ValueError(_('_parse_lat_lon() -- incorrect format: %s') % \
                             text)
        return dec


    def _get_lat_direction(self):
        '''
        return N or S from the radio
        '''
        if self.view.widgets.north_radio.get_active():
            return 'N'
        elif self.view.widgets.south_radio.get_active():
            return 'S'
        raise ValueError(_('North/South radio buttons in a confused state'))


    def _get_lon_direction(self):
        '''
        return E or W from the radio
        '''
        if self.view.widgets.east_radio.get_active():
            return 'E'
        elif self.view.widgets.west_radio.get_active():
            return 'W'
        raise ValueError(_('East/West radio buttons in a confused state'))


    def on_lat_entry_insert(self, entry, new_text, new_text_length, position,
                            data=None):
        '''
        insert handler for lat_entry
        '''
        entry_text = entry.get_text()
        cursor = entry.get_position()
        full_text = entry_text[:cursor] + new_text + entry_text[cursor:]
        self._set_latitude_from_text(full_text)


    def on_lat_entry_delete(self, entry, start, end, data=None):
        '''
        delete handler for lat_entry
        '''
        text = entry.get_text()
        full_text = text[:start] + text[end:]
        self._set_latitude_from_text(full_text)


    def _set_latitude_from_text(self, text):
        '''
        set the latitude value from text
        '''
        latitude = None
        dms_string = ''
        try:
            if text != '' and text is not None:
                north_radio = self.view.widgets.north_radio
                north_radio.handler_block(self.north_toggle_signal_id)
                if text[0] == '-':
                    self.view.widgets.south_radio.set_active(True)
                else:
                    north_radio.set_active(True)
                north_radio.handler_unblock(self.north_toggle_signal_id)
                direction = self._get_lat_direction()
                latitude = CollectionPresenter._parse_lat_lon(direction, text)
                #u"\N{DEGREE SIGN}"
                dms_string ='%s %s\302\260%s"%s\'' % latitude_to_dms(latitude)
        except:
#            debug(traceback.format_exc())
            bg_color = gtk.gdk.color_parse("red")
            self.add_problem(self.PROBLEM_BAD_LATITUDE,
                             self.view.widgets.lat_entry)
        else:
            self.remove_problem(self.PROBLEM_BAD_LATITUDE,
                             self.view.widgets.lat_entry)

        self.model['latitude'] = latitude
        self.view.widgets.lat_dms_label.set_text(dms_string)


    def on_lon_entry_insert(self, entry, new_text, new_text_length, position,
                            data=None):
        entry_text = entry.get_text()
        cursor = entry.get_position()
        full_text = entry_text[:cursor] + new_text + entry_text[cursor:]
        self._set_longitude_from_text(full_text)


    def on_lon_entry_delete(self, entry, start, end, data=None):
        text = entry.get_text()
        full_text = text[:start] + text[end:]
        self._set_longitude_from_text(full_text)


    def _set_longitude_from_text(self, text):
        longitude = None
        dms_string = ''
        try:
            if text != '' and text is not None:
                east_radio = self.view.widgets.east_radio
                east_radio.handler_block(self.east_toggle_signal_id)
                if text[0] == '-':
                    self.view.widgets.west_radio.set_active(True)
                else:
                    self.view.widgets.east_radio.set_active(True)
                east_radio.handler_unblock(self.east_toggle_signal_id)
                direction = self._get_lon_direction()
                longitude = CollectionPresenter._parse_lat_lon(direction, text)
                dms_string ='%s %s\302\260%s"%s\'' % longitude_to_dms(longitude)
        except:
#            debug(traceback.format_exc())
            bg_color = gtk.gdk.color_parse("red")
            self.add_problem(self.PROBLEM_BAD_LONGITUDE,
                              self.view.widgets.lon_entry)
        else:
            self.remove_problem(self.PROBLEM_BAD_LONGITUDE,
                              self.view.widgets.lon_entry)

        self.model['longitude'] = longitude
        self.view.widgets.lon_dms_label.set_text(dms_string)


# TODO: make the donor_combo insensitive if the model is empty
class DonationPresenter(GenericEditorPresenter):

    widget_to_field_map = {'donor_combo': 'donor',
                           'donid_entry': 'donor_acc',
                           'donnotes_entry': 'notes',
                           'don_date_entry': 'date'}
    PROBLEM_INVALID_DATE = random()
    PROBLEM_INVALID_DONOR = random()

    def __init__(self, model, view, session):
        GenericEditorPresenter.__init__(self, ModelDecorator(model), view)
        self.session = session

        # set up donor_combo
        donor_combo = self.view.widgets.donor_combo
        donor_combo.clear() # avoid gchararry/PyObject warning
        r = gtk.CellRendererText()
        donor_combo.pack_start(r)
        donor_combo.set_cell_data_func(r, self.combo_cell_data_func)

        self.refresh_view()

        # assign handlers
        donor_combo.connect('changed', self.on_donor_combo_changed)
        self.assign_simple_handler('donid_entry', 'donor_acc',
                                   UnicodeOrNoneValidator())
        self.assign_simple_handler('donnotes_entry', 'notes',
                                   UnicodeOrNoneValidator())
        don_date_entry = self.view.widgets.don_date_entry
        don_date_entry.connect('insert-text', self.on_date_entry_insert)
        don_date_entry.connect('delete-text', self.on_date_entry_delete)
        utils.setup_date_button(don_date_entry,
                                self.view.widgets.don_date_button)
        self.view.widgets.don_new_button.connect('clicked',
                                                 self.on_don_new_clicked)
        self.view.widgets.don_edit_button.connect('clicked',
                                                  self.on_don_edit_clicked)

        # if there is only one donor in the donor combo model and
        if self.model.donor is None and len(donor_combo.get_model()) == 1:
#           donor('set_active(0)')
            donor_combo.set_active(0)

        for field in self.widget_to_field_map.values():
            self.model.add_notifier(field, self.on_field_changed)
        if self.model.donor is None:
            self.add_problem(self.PROBLEM_INVALID_DONOR)


    def on_field_changed(self, model, field):
        if self.model.donor is None:
            self.add_problem(self.PROBLEM_INVALID_DONOR)
        else:
            self.remove_problem(self.PROBLEM_INVALID_DONOR)


    def start(self):
        raise Exception('CollectionEditorPresenter cannot be started')


    def dirty(self):
        return self.model.dirty


    def on_donor_combo_changed(self, combo, data=None):
        '''
        changed the sensitivity of the don_edit_button if the
        selected item in the donor_combo is an instance of Donor
        '''
#        debug('on_donor_combo_changed')
        i = combo.get_active_iter()
        if i is None:
            return
        value = combo.get_model()[i][0]
        self.model.donor = value
        if isinstance(value, Donor):
            self.view.widgets.don_edit_button.set_sensitive(True)
        else:
            self.view.widgets.don_edit_button.set_sensitive(False)


    def on_date_entry_insert(self, entry, new_text, new_text_length, position,
                            data=None):
        entry_text = entry.get_text()
        cursor = entry.get_position()
        full_text = entry_text[:cursor] + new_text + entry_text[cursor:]
        self._set_date_from_text(full_text)


    def on_date_entry_delete(self, entry, start, end, data=None):
        text = entry.get_text()
        full_text = text[:start] + text[end:]
        self._set_date_from_text(full_text)


    def _set_date_from_text(self, text):
        if text == '':
            self.model.date = None
            self.remove_problem(self.PROBLEM_INVALID_DATE,
                                self.view.widgets.don_date_entry)
            return

        m = _date_regex.match(text)
        dt = None # datetime
        try:
            ymd = [int(x) for x in [m.group('year'), m.group('month'), \
                                    m.group('day')]]
            dt = datetime(*ymd).date()
            self.remove_problem(self.PROBLEM_INVALID_DATE,
                                self.view.widgets.don_date_entry)
        except:
            self.add_problem(self.PROBLEM_INVALID_DATE,
                             self.view.widgets.don_date_entry)
        self.model.date = dt



    def on_don_new_clicked(self, button, data=None):
        '''
        create a new donor, setting the current donor on donor_combo
        to the new donor
        '''
        donor = DonorEditor().start()
        if donor is not None:
            self.refresh_view()
            self.view.set_widget_value('donor_combo', donor)


    def on_don_edit_clicked(self, button, data=None):
        '''
        edit currently selected donor
        '''
        donor_combo = self.view.widgets.donor_combo
        i = donor_combo.get_active_iter()
        donor = donor_combo.get_model()[i][0]
        e = DonorEditor(model=donor, parent=self.view.widgets.accession_dialog)
        edited = e.start()
        if edited is not None:
            self.refresh_view()


    def combo_cell_data_func(self, cell, renderer, model, iter):
        v = model[iter][0]
        renderer.set_property('text', str(v))


    def refresh_view(self):
#        debug('DonationPresenter.refresh_view')

        # populate the donor combo
        model = gtk.ListStore(object)
        for value in self.session.query(Donor):
#            debug(value)
            model.append([value])
        donor_combo = self.view.widgets.donor_combo
        donor_combo.set_model(model)

        for widget, field in self.widget_to_field_map.iteritems():
            value = self.model[field]
#            debug('%s, %s, %s' % (widget, field, value))
            if value is not None and field == 'date':
                value = '%s/%s/%s' % (value.day, value.month,
                                      '%04d' % value.year)
            self.view.set_widget_value(widget, value)

        if self.model.donor is None:
            self.view.widgets.don_edit_button.set_sensitive(False)
        else:
            self.view.widgets.don_edit_button.set_sensitive(True)


def SourcePresenterFactory(model, view, session):
    if isinstance(model, Collection):
        return CollectionPresenter(model, view, session)
    elif isinstance(model, Donation):
        return DonationPresenter(model, view, session)
    else:
        raise ValueError('unknown source type: %s' % type(model))


# TODO: pick one or a combination of the following
# 1. the ok, next and whatever buttons shouldn't be made sensitive until
# all required field are valid, or all field are valid
# 2. implement eclipse style label at the top of the editor that give
# information about context, whether a field is invalid or whatever
# 3. change color around widget with an invalid value so the user knows there's
# a problem
# TODO: the accession editor presenter should give an error if no species exist
# in fact it should give a message dialog and ask if you would like
# to enter some species now, or maybe import some
class AccessionEditorPresenter(GenericEditorPresenter):

    widget_to_field_map = {'acc_code_entry': 'code',
                           'acc_id_qual_combo': 'id_qual',
                           'acc_date_entry': 'date',
                           'acc_prov_combo': 'prov_type',
                           'acc_wild_prov_combo': 'wild_prov_status',
                           'acc_species_entry': 'species',
                           'acc_source_type_combo': 'source_type',
                           'acc_notes_textview': 'notes',
                           'acc_private_check': 'private'}

    PROBLEM_INVALID_DATE = random()
    PROBLEM_DUPLICATE_ACCESSION = random()

    def __init__(self, model, view):
        '''
        @param model: an instance of class Accession
        @param view: an instance of AccessionEditorView
        '''
        GenericEditorPresenter.__init__(self, ModelDecorator(model), view)
        self.session = object_session(model)
        self._original_source = self.model.source
        self._original_code = self.model.code
        self.current_source_box = None
        self.source_presenter = None
        self._source_box_map = {'Donation': self.view.widgets.donation_box,
                                'Collection': self.view.widgets.collection_box}
        self.init_enum_combo('acc_prov_combo', 'prov_type')
        self.init_enum_combo('acc_wild_prov_combo', 'wild_prov_status')
        self.init_enum_combo('acc_id_qual_combo', 'id_qual')
        self.init_source_expander()
        self.refresh_view() # put model values in view


        # connect signals
        def sp_get_completions(text):
            query = self.session.query(Species)
            return query.filter(and_(species_table.c.genus_id == \
                                     genus_table.c.id,
                                or_(genus_table.c.genus.like('%s%%' % text),
                                    genus_table.c.hybrid==utils.utf8(text))))
        def set_in_model(self, field, value):
            setattr(self.model, field, value)
        self.assign_completions_handler('acc_species_entry', 'species',
                                        sp_get_completions,
                                        set_func=set_in_model)
        self.view.widgets.acc_prov_combo.connect('changed',
                                                 self.on_combo_changed,
                                                 'prov_type')
        self.view.widgets.acc_wild_prov_combo.connect('changed',
                                                      self.on_combo_changed,
                                                      'wild_prov_status')
        # TODO: could probably replace this by just passing a valdator
        # to assign_simple_handler...UPDATE: but can the validator handle
        # adding a problem to the widget...if we passed it the widget it
        # could
        self.view.widgets.acc_code_entry.connect('insert-text',
                                               self.on_acc_code_entry_insert)
        self.view.widgets.acc_code_entry.connect('delete-text',
                                               self.on_acc_code_entry_delete)
        self.assign_simple_handler('acc_notes_textview', 'notes',
                                   UnicodeOrNoneValidator())

        acc_date_entry = self.view.widgets.acc_date_entry
        acc_date_entry.connect('insert-text', self.on_acc_date_entry_insert)
        acc_date_entry.connect('delete-text', self.on_acc_date_entry_delete)

        utils.setup_date_button(acc_date_entry,
                                self.view.widgets.acc_date_button)

        self.assign_simple_handler('acc_id_qual_combo', 'id_qual',
                                   UnicodeOrNoneValidator())
        self.assign_simple_handler('acc_private_check', 'private')
        self.init_change_notifier()


    def dirty(self):
        if self.source_presenter is None:
            return self.model.dirty
        return self.source_presenter.dirty() or self.model.dirty


    def on_acc_code_entry_insert(self, entry, new_text, new_text_length,
                                 position, data=None):
        """
        insert-text callback for acc_code widget
        """
        entry_text = entry.get_text()
        cursor = entry.get_position()
        full_text = entry_text[:cursor] + new_text + entry_text[cursor:]
        self._set_acc_code_from_text(full_text)


    def on_acc_code_entry_delete(self, entry, start, end, data=None):
        """
        delete-text callback for acc_code widget
        """
        text = entry.get_text()
        full_text = text[:start] + text[end:]
        self._set_acc_code_from_text(full_text)


    def _set_acc_code_from_text(self, text):
        query = self.session.query(Accession)
        if text != self._original_code \
               and query.filter_by(code=unicode(text)).count()>0:
            self.add_problem(self.PROBLEM_DUPLICATE_ACCESSION,
                             self.view.widgets.acc_code_entry)
            self.model.code = None
            return
        self.remove_problem(self.PROBLEM_DUPLICATE_ACCESSION,
                            self.view.widgets.acc_code_entry)
        if text is '':
            self.model.code = None
        else:
            # TODO: even though utf-8 is pretty much standard throughout
            # Bauble we shouldn't hardcode the encoding here...probably best
            # to store the default encoding in the bauble.meta
            self.model.code = unicode(text, encoding='utf-8')


    def on_acc_date_entry_insert(self, entry, new_text, new_text_length,
                                 position, data=None):
        """
        insert-text call back for acc_date widget
        """
        entry_text = entry.get_text()
        cursor = entry.get_position()
        full_text = entry_text[:cursor] + new_text + entry_text[cursor:]
        self._set_acc_date_from_text(full_text)


    def on_acc_date_entry_delete(self, entry, start, end, data=None):
        """
        delete-text call back for acc_date_widget
        """
        text = entry.get_text()
        full_text = text[:start] + text[end:]
        self._set_acc_date_from_text(full_text)


    def _set_acc_date_from_text(self, text):
        """
        """
        if text == '':
            self.model.date = None
            self.remove_problem(self.PROBLEM_INVALID_DATE,
                                self.view.widgets.acc_date_entry)
            return

        m = _date_regex.match(text)
        dt = None # datetime
        try:
            ymd = [int(x) for x in [m.group('year'), m.group('month'), \
                                    m.group('day')]]
            dt = datetime(*ymd).date()
            self.remove_problem(self.PROBLEM_INVALID_DATE,
                                self.view.widgets.acc_date_entry)
        except Exception:
#            debug(traceback.format_exc())
            self.add_problem(self.PROBLEM_INVALID_DATE,
                             self.view.widgets.acc_date_entry)

        self.model.date = dt


    def on_field_changed(self, model, field):
        """
        This method works on the assumption that
        source_presenter.on_field_changed is called before this method
        and adds and removes problems as necessary, if for some reason
        this isn't the case then this method would work as expected
        """
##        debug('on field changed: %s = %s' % (field, getattr(model, field)))
        # TODO: we could have problems here if we are monitoring more than
        # one model change and the two models have a field with the same name,
        # e.g. date, then if we do 'if date == something' we won't know
        # which model changed

        # TODO: add a test to make sure that the change notifiers are
        # called in the expected order
        prov_sensitive = True
        wild_prov_combo = self.view.widgets.acc_wild_prov_combo
        if field == 'prov_type':
            if model.prov_type == 'Wild':
                model.wild_prov_status = wild_prov_combo.get_active_text()
            else:
                # remove the value in the model from the wild_prov_combo
                prov_sensitive = False
                model.wild_prov_status = None
            wild_prov_combo.set_sensitive(prov_sensitive)
            self.view.widgets.acc_wild_prov_frame.set_sensitive(prov_sensitive)

        if field == 'longitude' or field == 'latitude':
            sensitive = model.latitude is not None and \
                            model.longitude is not None
            self.view.widgets.geoacc_entry.set_sensitive(sensitive)
            self.view.widgets.datum_entry.set_sensitive(sensitive)

        if field == 'elevation':
            sensitive = model.elevation is not None
            self.view.widgets.altacc_entry.set_sensitive(sensitive)

        # refresh the sensitivity of the accept buttons
        sensitive = True
        if len(self.problems) != 0:
            sensitive = False
        elif self.source_presenter is not None and \
                len(self.source_presenter.problems) != 0:
            sensitive = False
        elif (self.model.code is None) or (self.model.species is None):
            sensitive = False
        elif field == 'source_type':
            sensitive = False

        self.set_accept_buttons_sensitive(sensitive)


    def init_change_notifier(self):
        '''
        for each widget register a signal handler to be notified when the
        value in the widget changes, that way we can do things like sensitize
        the ok button
        '''
        for field in self.widget_to_field_map.values():
            self.model.add_notifier(field, self.on_field_changed)


    def on_source_type_combo_changed(self, combo, data=None):
        '''
        change which one of donation_box/collection_box is packed into
        source box and setup the appropriate presenter
        '''
        source_type = combo.get_active_text()
        source_type_changed = False
        if source_type is None:
            if self.model.source is not None:
                self.model.source = None
                if self.current_source_box is not None:
                    self.view.widgets.remove_parent(self.current_source_box)
                    self.current_source_box = None
                self.on_field_changed(self.model, 'source_type')
            return

        # FIXME: Donation and Collection shouldn't be hardcoded so that it
        # can be translated
        #
        # TODO: if source_type is set and self.model.source is None then create
        # a new empty source object and attach it to the model

        source_class_map = {'Donation': Donation,
                            'Collection': Collection}

        # the source_type has changed from what it originally was
        if source_type != self.model.source_type:
#            debug('source_type != model.source_type')
            source_type_changed = True
            new_source = None
            try:
                new_source = source_class_map[source_type]()
            except KeyError, e:
                debug('unknown source type: %s' % e)
                raise
            if isinstance(new_source, type(self._original_source)):
                self.model.source = self._original_source
            else:
                self.model.source = new_source
        elif source_type is not None and self.model.source is None:
            # the source type is set but there is no corresponding model.source
            try:
                self.model.source = source_class_map[source_type]()
            except KeyError, e:
                debug('unknown source type: %s' % e)
                raise


        # replace source box contents with our new box
        #source_box = self.view.widgets.source_box
        source_box_parent = self.view.widgets.source_box_parent
        if self.current_source_box is not None:
            self.view.widgets.remove_parent(self.current_source_box)
        if source_type is not None:
            self.current_source_box = self._source_box_map[source_type]
            self.view.widgets.remove_parent(self.current_source_box)
            source_box_parent.add(self.current_source_box)
        else:
            self.current_source_box = None

        if self.model.source is not None:
            self.source_presenter = \
                           SourcePresenterFactory(self.model.source, self.view,
                                                  self.session)
            # initialize model change notifiers
            for field in self.source_presenter.widget_to_field_map.values():
                self.source_presenter.model.add_notifier(field,
                                                         self.on_field_changed)

        if source_type_changed:
            self.on_field_changed(self.model, 'source_type')


    def set_accept_buttons_sensitive(self, sensitive):
        '''
        set the sensitivity of all the accept/ok buttons for the editor dialog
        '''
        self.view.widgets.acc_ok_button.set_sensitive(sensitive)
        self.view.widgets.acc_ok_and_add_button.set_sensitive(sensitive)
        self.view.widgets.acc_next_button.set_sensitive(sensitive)


    def init_source_expander(self):
        '''
        initialized the source expander contents
        '''
        combo = self.view.widgets.acc_source_type_combo
        model = gtk.ListStore(str)
        model.append(['Collection'])
        model.append(['Donation'])
        model.append([None])
        combo.set_model(model)
        combo.set_active(-1)
        self.view.widgets.acc_source_type_combo.connect('changed',
                                            self.on_source_type_combo_changed)


    def on_combo_changed(self, combo, field):
        self.model[field] = combo.get_active_text()


    def refresh_view(self):
        '''
        get the values from the model and put them in the view
        '''
        for widget, field in self.widget_to_field_map.iteritems():
            if field == 'species_id':
                value = self.model.species
            else:
                value = self.model[field]
            if value is not None and field == 'date':
                value = '%s/%s/%s' % (value.day, value.month,
                                      '%04d' % value.year)
            self.view.set_widget_value(widget, value)

        if self.model.private is None:
            self.view.widgets.acc_private_check.set_inconsistent(False)
            self.view.widgets.acc_private_check.set_active(False)

        sensitive = self.model.prov_type == 'Wild'
        self.view.widgets.acc_wild_prov_combo.set_sensitive(sensitive)
        self.view.widgets.acc_wild_prov_frame.set_sensitive(sensitive)


    def start(self):
        return self.view.start()



class AccessionEditor(GenericModelViewPresenterEditor):

    label = _('Accession')
    mnemonic_label = _('_Accession')

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
        GenericModelViewPresenterEditor.__init__(self, model, parent)
        if parent is None: # should we even allow a change in parent
            parent = bauble.gui.window
        self.parent = parent
        self._committed = []


    def handle_response(self, response):
        '''
        handle the response from self.presenter.start() in self.start()
        '''
        not_ok_msg = 'Are you sure you want to lose your changes?'
        if response == gtk.RESPONSE_OK or response in self.ok_responses:
            try:
                if self.presenter.dirty():
                    self.commit_changes()
                    self._committed.append(self.model)
            except SQLError, e:
                msg = _('Error committing changes.\n\n%s') % \
                      utils.xml_safe_utf8(unicode(e.orig))
                utils.message_details_dialog(msg, str(e), gtk.MESSAGE_ERROR)
                self.session.rollback()
                return False
            except Exception, e:
                msg = _('Unknown error when committing changes. See the '\
                        'details for more information.\n\n%s') \
                        % utils.xml_safe_utf8(e)
                debug(traceback.format_exc())
                utils.message_details_dialog(msg, traceback.format_exc(),
                                             gtk.MESSAGE_ERROR)
                self.session.rollback()
                return False
        elif self.presenter.dirty() \
                 and utils.yes_no_dialog(not_ok_msg) \
                 or not self.presenter.dirty():
            self.session.rollback()
            return True
        else:
            return False

        # respond to responses
        more_committed = None
        if response == self.RESPONSE_NEXT:
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
        self.view = AccessionEditorView(parent=self.parent)
        self.presenter = AccessionEditorPresenter(self.model, self.view)

        # add quick response keys
        dialog = self.view.dialog
        self.attach_response(dialog, gtk.RESPONSE_OK, 'Return',
                             gtk.gdk.CONTROL_MASK)
        self.attach_response(dialog, self.RESPONSE_OK_AND_ADD, 'k',
                             gtk.gdk.CONTROL_MASK)
        self.attach_response(dialog, self.RESPONSE_NEXT, 'n',
                             gtk.gdk.CONTROL_MASK)

        # set the default focus
        if self.model.species is None:
            self.view.widgets.acc_species_entry.grab_focus()
        else:
            self.view.widgets.acc_code_entry.grab_focus()

        while True:
            response = self.presenter.start()
            self.view.save_state() # should view or presenter save state
            if self.handle_response(response):
                break

        self.session.close() # cleanup session
        return self._committed



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
        return super(AccessionEditor, self).commit_changes()



# import at the bottom to avoid circular dependencies
from bauble.plugins.plants.genus import Genus, genus_table
from bauble.plugins.plants.species_model import Species, species_table
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

        self.set_widget_value('name_data', '%s %s' % \
                              (row.species.markup(True), row.id_qual or '',))

        session = object_session(row)
        # TODO: it would be nice if we did something like 13 Living,
        # 2 Dead, 6 Unknown, etc
        # TODO: could this be sped up, does it matter?
        nplants = session.query(Plant).filter_by(accession_id=row.id).count()
        self.set_widget_value('nplants_data', nplants)
        self.set_widget_value('prov_data', row.prov_type, False)


class NotesExpander(InfoExpander):
    """
    the accession's notes
    """

    def __init__(self, widgets):
        InfoExpander.__init__(self, _("Notes"), widgets)
        notes_box = self.widgets.notes_box
        self.widgets.notes_window.remove(notes_box)
        self.vbox.pack_start(notes_box)


    def update(self, row):
        self.set_widget_value('notes_data', row.notes)


class SourceExpander(InfoExpander):

    def __init__(self, widgets):
        InfoExpander.__init__(self, _('Source'), widgets)
        self.curr_box = None
        self.box_map = {Collection: (self.widgets.collections_box,
                                     self.update_collections),
                        Donation: (self.widgets.donations_box,
                                   self.update_donations)}
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
            lat_str = '%.2f (%s %s\302\260%s"%.2f\') %s' % \
                (collection.latitude, dir, deg, min, sec, geo_accy)
            self.set_widget_value('lat_data', lat_str)

        if collection.longitude:
            dir, deg, min, sec = longitude_to_dms(collection.longitude)
            long_str = '%.2f (%s %s\302\260%s"%.2f\') %s' % \
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
        donor_str = utils.xml_safe(unicode(session.load(Donor,
                                                        donation.donor_id)))
        self.set_widget_value('donor_data', donor_str)
        self.set_widget_value('donid_data', donation.donor_acc)
        self.set_widget_value('donnotes_data', donation.notes)


    def update(self, value):
        if self.curr_box is not None:
            self.vbox.remove(self.curr_box)

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


class AccessionInfoBox(InfoBox):
    """
    - general info
    - source
    """
    def __init__(self):
        super(AccessionInfoBox, self).__init__()
        glade_file = os.path.join(paths.lib_dir(), "plugins", "garden",
                            "acc_infobox.glade")
        self.widgets = utils.GladeWidgets(gtk.glade.XML(glade_file))

        self.general = GeneralAccessionExpander(self.widgets)
        self.add_expander(self.general)
        self.source = SourceExpander(self.widgets)
        self.add_expander(self.source)
        self.notes = NotesExpander(self.widgets)
        self.add_expander(self.notes)
        self.props = PropertiesExpander()
        self.add_expander(self.props)


    def update(self, row):
        self.general.update(row)
        self.props.update(row)
        if row.notes is None:
            self.notes.set_expanded(False)
            self.notes.set_sensitive(False)
        else:
            self.notes.set_expanded(True)
            self.notes.set_sensitive(True)
            self.notes.update(row)

        # TODO: should test if the source should be expanded from the prefs
        self.source.update(row.source)


# it's easier just to put this here instead of playing around with imports
class SourceInfoBox(AccessionInfoBox):
    def update(self, row):
        super(SourceInfoBox, self).update(row._accession)



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
