#
# source.py
#
import os
import sys
import traceback
import weakref
from random import random

import gtk
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.orm.session import object_session

import bauble
import bauble.db as db
import bauble.editor as editor
from bauble.plugins.plants.geography import Geography
import bauble.types as types
from bauble.view import Action


def source_markup_func(source):
    from bauble.plugins.garden.accession import acc_markup_func
    return '%s - <small>%s</small>' % \
        (source.accession, source.accession.species_str()), source

def edit_callback(source):
    from bauble.plugins.garden.accession import edit_callback
    return edit_callback([source[0].accession])

def add_plants_callback(source):
    from bauble.plugins.garden.accession import add_plants_callback
    return add_plants_callback([source[0].accession])

def remove_callback(source):
    from bauble.plugins.garden.accession import remove_callback
    return remove_callback([source[0].accession])

edit_action = Action('source_edit', ('_Edit'), callback=edit_callback,
                        accelerator='<ctrl>e')
add_plant_action = Action('source_add', ('_Add plants'),
                          callback=add_plants_callback, accelerator='<ctrl>k')
remove_action = Action('source_remove', ('_Remove'), callback=remove_callback,
                       accelerator='<delete>')#, multiselect=True)

source_context_menu = [edit_action, add_plant_action, remove_action]

class Donation(db.Base):
    """
    :Table name: donation

    :Columns:
        *donor_id*: :class:`sqlalchemy.types.Integer(ForeignKey('donor.id'), nullable=False)`

        *donor_acc*: :class:`sqlalchemy.types.Unicode(32)`

        *notes*: :class:`sqlalchemy.types.UnicodeText`

        *date*: :class:`bauble.types..Date`

        *accession_id*: :class:`sqlalchemy.types.Integer(ForeignKey('accession.id'), nullable=False)`


    :Properties:

      donor:
        created as a backref from the Donor mapper

      _accession:
        created as a backref from the Accession mapper _donation property
    """
    __tablename__ = 'donation'

    donor_id = Column(Integer, ForeignKey('donor.id'), nullable=False)
    donor_acc = Column(Unicode(32)) # donor's accession id
    notes = Column(UnicodeText)
    date = Column(types.Date)
    accession_id = Column(Integer, ForeignKey('accession.id'), nullable=False)


    def _set_accession(self, accession):
        accession.source = self
    def _get_accession(self):
        # self._accession is created as a backref on the accession's
        # _donation property
        return self._accession
    accession = property(_get_accession, _set_accession)


    def __str__(self):
        if self.donor:
            return 'Donation from %s' % self.donor
        else:
            return repr(self)


# TODO: is there anyway to get this date format from BaubleMeta, also
#    i don't know why setting dateFormat here give me an error about getting
#    the date in unicode instead of a DateTimeCol eventhough i set this
#    column using a datetime object
# TODO: deleting this foreign accession deletes this collection

# TODO: collector combined with collectors_code should be a unique key, need to
# also indicate this in the UI

# TODO: should provide a collection type: alcohol, bark, boxed,
# cytological, fruit, illustration, image, other, packet, pollen,
# print, reference, seed, sheet, slide, transparency, vertical,
# wood.....see HISPID standard, in general need to be more herbarium
# aware

# TODO: create a DMS column type to hold latitude and longitude,
# should probably store the DMS data as a string in decimal degrees
class Collection(db.Base):
    """
    :Table name: collection

    :Columns:
            *collector*: :class:`sqlalchemy.types.Unicode(64)`

            *collectors_code*: :class:`sqlalchemy.types.Unicode(50)`

            *date*: :class:`sqlalchemy.types.Date`

            *locale*: :class:`sqlalchemy.types.UnicodeText(nullable=False)`

            *latitude*: :class:`sqlalchemy.types.Float`

            *longitude*: :class:`sqlalchemy.types.Float`

            *gps_datum*: :class:`sqlalchemy.types.Unicode(32)`

            *geo_accy*: :class:`sqlalchemy.types.Float`

            *elevation*: :class:`sqlalchemy.types.Float`

            *elevation_accy*: :class:`sqlalchemy.types.Float`

            *habitat*: :class:`sqlalchemy.types.UnicodeText`

            *geography_id*: :class:`sqlalchemy.types.Integer(ForeignKey('geography.id'))`

            *notes*: :class:`sqlalchemy.types.UnicodeText`

            *accession_id*: :class:`sqlalchemy.types.Integer(ForeignKey('accession.id'), nullable=False)`


    :Properties:

    Also contains an _accession property that was created as a backref
    from the Accession mapper

    :Constraints:
    """
    __tablename__ = 'collection'

    # columns
    collector = Column(Unicode(64))
    collectors_code = Column(Unicode(50))

    # TODO: make sure the country names are translatable, maybe store
    # the ISO country code, e.g es for Spain, en_US for US or
    # something similar so that we can use the translated country
    # names for completions but the same database can be opened with
    # different locales and show the localized names....might in this
    # case be better to create a country table instead of just the
    # string column...google countrytransl.map

    #Column(Unicode(64)) # ISO country name

    date = Column(types.Date)
    locale = Column(UnicodeText, nullable=False)
    latitude = Column(Float)
    longitude = Column(Float)
    gps_datum = Column(Unicode(32))
    geo_accy = Column(Float)
    elevation = Column(Float)
    elevation_accy = Column(Float)
    habitat = Column(UnicodeText)
    geography_id = Column(Integer, ForeignKey('geography.id'))
    notes = Column(UnicodeText)
    accession_id = Column(Integer, ForeignKey('accession.id'), nullable=False)


    def _set_accession(self, accession):
        accession.source = self
    def _get_accession(self):
        # self._accession is created as a backref on the accession's
        # _donation property
        return self._accession
    accession = property(_get_accession, _set_accession)


    def __str__(self):
        return 'Collection at %s' % (self.locale or repr(self))



# TODO: should have a label next to lat/lon entry to show what value will be
# stored in the database, might be good to include both DMS and the float
# so the user can see both no matter what is in the entry. it could change in
# time as the user enters data in the entry
# TODO: shouldn't allow entering altitude accuracy without entering altitude,
# same for geographic accuracy
# TODO: should show an error if something other than a number is entered in
# the altitude entry
class CollectionPresenter(editor.GenericEditorPresenter):

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
    PROBLEM_BAD_LATITUDE = str(random())
    PROBLEM_BAD_LONGITUDE = str(random())
    PROBLEM_INVALID_DATE = str(random())
    PROBLEM_INVALID_LOCALE = str(random())

    def __init__(self, parent, model, view, session):
        super(CollectionPresenter, self).__init__(model, view)
        self.parent_ref = weakref.ref(parent)
        self.session = session
        self.refresh_view()

        self.assign_simple_handler('collector_entry', 'collector',
                                   editor.UnicodeOrNoneValidator())
        self.assign_simple_handler('locale_entry', 'locale',
                                   editor.UnicodeOrNoneValidator())
        self.assign_simple_handler('collid_entry', 'collectors_code',
                                   editor.UnicodeOrNoneValidator())
        self.assign_simple_handler('geoacc_entry', 'geo_accy',
                                   editor.IntOrNoneStringValidator())
        self.assign_simple_handler('alt_entry', 'elevation',
                                   editor.FloatOrNoneStringValidator())
        self.assign_simple_handler('altacc_entry', 'elevation_accy',
                                   editor.FloatOrNoneStringValidator())
        self.assign_simple_handler('habitat_textview', 'habitat',
                                   editor.UnicodeOrNoneValidator())
        self.assign_simple_handler('coll_notes_textview', 'notes',
                                   editor.UnicodeOrNoneValidator())
        # the list of completions are added in AccessionEditorView.__init__
        def on_match(completion, model, iter, data=None):
            value = model[iter][0]
            validator = editor.UnicodeOrNoneValidator()
            self.set_model_attr('gps_data', value, validator)
            completion.get_entry().set_text(value)
        completion = self.view.widgets.datum_entry.get_completion()
        self.view.connect(completion, 'match-selected', on_match)
        self.assign_simple_handler('datum_entry', 'gps_datum',
                                   editor.UnicodeOrNoneValidator())

        self.view.connect('lat_entry', 'changed', self.on_lat_entry_changed)
        self.view.connect('lon_entry', 'changed', self.on_lon_entry_changed)

        self.view.connect('coll_date_entry', 'changed',
                          self.on_date_entry_changed)

        utils.setup_date_button(self.view.widgets.coll_date_entry,
                                self.view.widgets.coll_date_button)

        # don't need to connection to south/west since they are in the same
        # groups as north/east
        self.north_toggle_signal_id = \
            self.view.connect('north_radio', 'toggled',
                              self.on_north_south_radio_toggled)
        self.east_toggle_signal_id = \
            self.view.connect('east_radio', 'toggled',
                              self.on_east_west_radio_toggled)

        if self.model.locale is None or self.model.locale in ('', u''):
            self.add_problem(self.PROBLEM_INVALID_LOCALE)
        self.__dirty = False


    def set_model_attr(self, field, value, validator=None):
        """
        Validates the fields when a field changes.
        """
        super(CollectionPresenter, self).set_model_attr(field, value,validator)
        self.__dirty = True
        if self.model.locale is None or self.model.locale in ('', u''):
            self.add_problem(self.PROBLEM_INVALID_LOCALE)
        else:
            self.remove_problem(self.PROBLEM_INVALID_LOCALE)

        if field in ('longitude', 'latitude'):
            sensitive = self.model.latitude is not None \
                        and self.model.longitude is not None
            self.view.widgets.geoacc_entry.set_sensitive(sensitive)
            self.view.widgets.datum_entry.set_sensitive(sensitive)

        if field == 'elevation':
            sensitive = self.model.elevation is not None
            self.view.widgets.altacc_entry.set_sensitive(sensitive)

        self.parent_ref().refresh_sensitivity()


    def start(self):
        raise Exception('CollectionPresenter cannot be started')


    def dirty(self):
        return self.__dirty


    def refresh_view(self):
        for widget, field in self.widget_to_field_map.iteritems():
            value = getattr(self.model, field)
##            debug('%s, %s, %s' % (widget, field, value))
            if value is not None and field == 'date':
                value = '%s/%s/%s' % (value.day, value.month,
                                      '%04d' % value.year)
            self.view.set_widget_value(widget, value)

        latitude = self.model.latitude
        if latitude is not None:
            dms_string ='%s %s\302\260%s\'%s"' % latitude_to_dms(latitude)
            self.view.widgets.lat_dms_label.set_text(dms_string)
            if latitude < 0:
                self.view.widgets.south_radio.set_active(True)
            else:
                self.view.widgets.north_radio.set_active(True)
        longitude = self.model.longitude
        if longitude is not None:
            dms_string ='%s %s\302\260%s\'%s"' % longitude_to_dms(longitude)
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


    def on_date_entry_changed(self, entry, data=None):
        text = entry.get_text()
        if text == '':
            self.set_model_attr('date', None)
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
            except Exception:
                self.add_problem(self.PROBLEM_INVALID_DATE,
                                    self.view.widgets.coll_date_entry)
        self.set_model_attr('date', dt)


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


    def on_lat_entry_changed(self, entry, date=None):
        '''
        set the latitude value from text
        '''
        text = entry.get_text()
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
                dms_string ='%s %s\302\260%s\'%s"' % latitude_to_dms(latitude)
        except Exception:
#            debug(traceback.format_exc())
            bg_color = gtk.gdk.color_parse("red")
            self.add_problem(self.PROBLEM_BAD_LATITUDE,
                             self.view.widgets.lat_entry)
        else:
            self.remove_problem(self.PROBLEM_BAD_LATITUDE,
                             self.view.widgets.lat_entry)

        self.set_model_attr('latitude', latitude)
        self.view.widgets.lat_dms_label.set_text(dms_string)


    def on_lon_entry_changed(self, entry, data=None):
        text = entry.get_text()
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
                dms_string ='%s %s\302\260%s\'%s"' % longitude_to_dms(longitude)
        except Exception:
#            debug(traceback.format_exc())
            bg_color = gtk.gdk.color_parse("red")
            self.add_problem(self.PROBLEM_BAD_LONGITUDE,
                              self.view.widgets.lon_entry)
        else:
            self.remove_problem(self.PROBLEM_BAD_LONGITUDE,
                              self.view.widgets.lon_entry)

        self.set_model_attr('longitude', longitude)
        self.view.widgets.lon_dms_label.set_text(dms_string)


# TODO: make the donor_combo insensitive if the model is empty
class DonationPresenter(editor.GenericEditorPresenter):

    widget_to_field_map = {'donor_combo': 'donor',
                           'donid_entry': 'donor_acc',
                           'donnotes_entry': 'notes',
                           'don_date_entry': 'date'}
    PROBLEM_INVALID_DATE = random()
    PROBLEM_INVALID_DONOR = random()

    def __init__(self, parent, model, view, session):
        """
        @param parent: the parent AccessionEditorPresenter
        """
        super(DonationPresenter, self).__init__(model, view)
        self.parent_ref = weakref.ref(parent)
        self.session = session

        # set up donor_combo
        donor_combo = self.view.widgets.donor_combo
        donor_combo.clear() # avoid gchararry/PyObject warning
        r = gtk.CellRendererText()
        donor_combo.pack_start(r)
        donor_combo.set_cell_data_func(r, self.combo_cell_data_func)

        # set the values in the view before setting any signal handlers
        self.refresh_view()

        # assign handlers
        self.view.connect('donor_combo', 'changed',
                          self.on_donor_combo_changed)
        self.assign_simple_handler('donid_entry', 'donor_acc',
                                   editor.UnicodeOrNoneValidator())
        self.assign_simple_handler('donnotes_entry', 'notes',
                                   editor.UnicodeOrNoneValidator())
        self.view.connect('don_date_entry', 'changed',
                          self.on_date_entry_changed)

        utils.setup_date_button(self.view.widgets.don_date_entry,
                                self.view.widgets.don_date_button)
        self.view.connect('don_new_button', 'clicked', self.on_don_new_clicked)
        self.view.connect('don_edit_button', 'clicked',
                          self.on_don_edit_clicked)

        # if there is no donor and only one donor in the donor combo model
        # then set it as the active donor
        if self.model.donor is None and len(donor_combo.get_model()) == 1:
            donor_combo.set_active(0)

        if self.model.donor is None:
            self.add_problem(self.PROBLEM_INVALID_DONOR)
        self.__dirty = False


    def set_model_attr(self, field, value, validator=None):
#        debug('DonationPresenter.set_model_attr(%s, %s)' % (field, value))
        super(DonationPresenter, self).set_model_attr(field, value, validator)
        self.__dirty = True
        if self.model.donor is None:
            self.add_problem(self.PROBLEM_INVALID_DONOR)
        else:
            self.remove_problem(self.PROBLEM_INVALID_DONOR)
        self.parent_ref().refresh_sensitivity()


    def start(self):
        raise Exception('DonationPresenter cannot be started')


    def dirty(self):
        return self.__dirty


    def on_donor_combo_changed(self, combo, data=None):
        """
        Changed the sensitivity of the don_edit_button if the
        selected item in the donor_combo is an instance of Donor
        """
        from bauble.plugins.garden.donor import Donor
#        debug('on_donor_combo_changed')
        it = combo.get_active_iter()
        if not it:
            return
        value = combo.get_model()[it][0]
        self.set_model_attr('donor', value)
        sensitive = False
        if isinstance(value, Donor):
            sensitive = True
        self.view.widgets.don_edit_button.set_sensitive(sensitive)


    def on_date_entry_changed(self, entry):
        text = entry.get_text()
        if text == '':
            self.set_model_attr('date', None)
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
        except Exception:
            self.add_problem(self.PROBLEM_INVALID_DATE,
                             self.view.widgets.don_date_entry)
        self.set_model_attr('date', dt)


    def on_don_new_clicked(self, button, data=None):
        '''
        create a new donor, setting the current donor on donor_combo
        to the new donor
        '''
        from bauble.plugins.garden.donor import DonorEditor
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
        from bauble.plugins.garden.donor import DonorEditor
        e = DonorEditor(model=donor, parent=self.view.widgets.accession_dialog)
        edited = e.start()
        if edited is not None:
            self.refresh_view()


    @staticmethod
    def combo_cell_data_func(cell, renderer, model, iter):
        """
        This method is static to make sure this object gets garbage collected.
        """
        v = model[iter][0]
        renderer.set_property('text', str(v))


    def refresh_view(self):
#        debug('DonationPresenter.refresh_view')

        # populate the donor combo
        model = gtk.ListStore(object)
        from bauble.plugins.garden.donor import Donor
        for value in self.session.query(Donor):
#            debug(value)
            model.append([value])
        donor_combo = self.view.widgets.donor_combo
        donor_combo.set_model(model)

        for widget, field in self.widget_to_field_map.iteritems():
            value = getattr(self.model, field)
#            debug('%s, %s, %s' % (widget, field, value))
            if value is not None and field == 'date':
                value = '%s/%s/%s' % (value.day, value.month,
                                      '%04d' % value.year)
            self.view.set_widget_value(widget, value)

        if self.model.donor is None:
            self.view.widgets.don_edit_button.set_sensitive(False)
        else:
            self.view.widgets.don_edit_button.set_sensitive(True)

