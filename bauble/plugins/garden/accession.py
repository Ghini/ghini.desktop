#
# accessions module
#

import os, traceback, math
from datetime import datetime
import xml.sax.saxutils as saxutils
import gtk, gobject
from sqlalchemy import *
from sqlalchemy.orm.session import object_session
from sqlalchemy.exceptions import SQLError
import formencode.validators as validators
import bauble
import bauble.utils as utils
import bauble.paths as paths
from bauble.editor import *
from bauble.utils.log import debug
from bauble.prefs import prefs
from bauble.error import CommitException
from bauble.types import Enum

# TODO: underneath the species entry create a label that shows information
# about the family of the genus of the species selected as well as more
# info about the genus so we know exactly what plant is being selected
# e.g. Malvaceae (sensu lato), Hibiscus (senso stricto)

# FIXME: time.mktime can't handle dates before 1970 on win32

# TODO: there is a bug if you edit an existing accession and change the 
# accession number but change it back to the original then it indicates the
# number is invalid b/c it's a duplicate


def longitude_to_dms(decimal):
    return decimal_to_dms(decimal, 'long')
    
def latitude_to_dms(decimal):
    return decimal_to_dms(decimal, 'lat')

# TODO: should get the precision from the values passed in, 
# e.g. if seconds was passed in as an integer there is no reason
# to keep 6 decimal places for precision
def dms_to_decimal(dir, deg, min, sec):
    '''
    convert degrees, minutes, seconds to decimal
    return float rounded to 5 decimal points
    '''
    if dir in ('E', 'W'): # longitude
        assert(abs(deg) > 0 and abs(deg) <= 180)
    else:
        assert(abs(deg) > 0 and abs(deg) <= 90)
    assert(abs(min) > 0 and abs(min) < 60)
    assert(abs(sec) > 0 and abs(sec) < 60)    
    dec = (abs(sec)/3600.0) + (abs(min)/60.0) + abs(deg)
    #dec = (((abs(sec)/60.0) + abs(min)) /60.0) + abs(deg)
    if dir in ('W', 'S'):
        dec = -dec
    return dec
    

def decimal_to_dms(decimal, long_or_lat):
    '''
    long_or_lat: should be either "long" or "lat"
    
    returns dir, degrees, minutes seconds
    seconds rounded to two decimal points
    '''
    
    dir_map = {'long': ['E', 'W'],
               'lat':  ['N', 'S']}
    dir = dir_map[long_or_lat][0]
    if decimal < 0:
        dir = dir_map[long_or_lat][1]
    
    dec = abs(decimal)
    d = abs(int(dec))
    m = abs((dec-d)*60)        
    s = abs((int(m)-m) * 60)    
    ROUND_TO=2
    #return dir, int(d), int(m), round(s,ROUND_TO)
    return dir, int(d), int(m), s


def edit_callback(row):
    value = row[0]
    e = AccessionEditor(value)
    return e.start() != None


def add_plants_callback(row):
    from bauble.plugins.garden.plant import PlantEditor
    value = row[0]
    e = PlantEditor(Plant(accession=value))
    return e.start() != None


def remove_callback(row):
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


acc_context_menu = [('Edit', edit_callback),
                    ('--', None),
                    ('Add plants', add_plants_callback),
                    ('--', None),
                    ('Remove', remove_callback)]

def acc_markup_func(acc):
    '''
    '''
    return str(acc), acc.species.markup(authors=False)




'''
prov_type:
----------
"Wild", # Wild,
"Propagule of cultivated wild plant", # Propagule of wild plant in cultivation
"Not of wild source", # Not of wild source
"Insufficient Data", # Insufficient data
"Unknown"

wild_prov_status:
-----------------
"Wild native", # Endemic found within it indigineous range
"Wild non-native", # Propagule of wild plant in cultivation
"Cultivated native", # Not of wild source
"Insufficient Data", # Insufficient data
"Unknown",

date: date accessioned

'''

# TODO: accession should have a one-to-many relationship on verifications
    #ver_level = StringCol(length=2, default=None) # verification level
    #ver_name = StringCol(length=50, default=None) # verifier's name
    #ver_date = DateTimeCol(default=None) # verification date
    #ver_hist = StringCol(default=None)  # verification history
    #ver_lit = StringCol(default=None) # verification lit
    #ver_id = IntCol(default=None) # ?? # verifier's ID??
verification_table = Table('verification',
                           Column('id', Integer, primary_key=True),
                           Column('verifier', Unicode(64)),
                           Column('date', Date),
                           Column('literature', Unicode),
                           Column('level', String), # i don't know what this is
                           Column('accession_id', Integer, 
                                  ForeignKey('accession.id')),
                           Column('_created', DateTime, default=func.current_timestamp()),
                           Column('_last_updated', DateTime, default=func.current_timestamp(),
                                  onupdate=func.current_timestamp()))


class Verification(bauble.BaubleMapper):
    pass


accession_table = Table('accession',
                Column('id', Integer, primary_key=True),                            
                Column('code', Unicode(20), nullable=False, unique=True),
                Column('prov_type', Enum(values=['Wild', 
                                                 "Propagule of cultivated wild plant", 
                                                 "Not of wild source",
                                                 "Insufficient Data", 
                                                 "Unknown",
                                                 None],
                                         empty_to_none=True)),
                Column('wild_prov_status', Enum(values=["Wild native",
                                                        "Wild non-native",
                                                        "Cultivated native",
                                                        "Insufficient Data",
                                                        "Unknown",
                                                        None],
                                                empty_to_none=True)),
                Column('date', Date),
                #Column('source_type', String(10)), # Collection, Donation, None
                Column('source_type', Enum(values=['Collection', 'Donation', None], empty_to_none=True)),
                Column('notes', Unicode),
                Column('species_id', Integer, ForeignKey('species.id'), nullable=False),
                Column('_created', DateTime, default=func.current_timestamp()),
                Column('_last_updated', DateTime, default=func.current_timestamp(), 
                       onupdate=func.current_timestamp()))



def delete_or_expunge(obj):
    session = object_session(obj)
#    debug('delete_or_expunge: %s' % obj)
    if obj in session.new:
#        debug('expunge obj: %s -- %s' % (obj, repr(obj)))
        session.expunge(obj)
        del obj
    else:
#        debug('delete obj: %s -- %s' % (obj, repr(obj)))        
        session.delete(obj)        


class Accession(bauble.BaubleMapper):
    
    def __str__(self): 
        return self.code
    
    def _get_source(self):
        if self.source_type is None:
            return None
        elif self.source_type == 'Collection':
            return self._collection
        elif self.source_type == 'Donation':
            return self._donation
        raise AssertionError('unknown source_type in accession: %s' % self.source_type)    
    
    def _set_source(self, source):
        del self.source
        if source is None:
            self.source_type = None
        else:
            self.source_type = source.__class__.__name__
            source.accession = self
        
    def _del_source(self):   
#        debug('_del_source(%s)' % repr(self.source))
        source = self.source        
        if source is not None:
            source.accession = None
            delete_or_expunge(source)
        self.source_type = None        
                    
    source = property(_get_source, _set_source, _del_source)

        
    def markup(self):
        return '%s (%s)' % (self.code, self.species.markup())


from bauble.plugins.garden.source import Donation, donation_table, \
    Collection, collection_table
from bauble.plugins.garden.plant import Plant, PlantEditor, plant_table    

mapper(Accession, accession_table,
       properties = {
                     '_collection': relation(Collection, 
                                             primaryjoin=accession_table.c.id==collection_table.c.accession_id,
                                             private=True, uselist=False, backref='accession'),
                     '_donation': relation(Donation, 
                                           primaryjoin=accession_table.c.id==donation_table.c.accession_id,
                                           private=True, uselist=False,
                                           backref='accession'),
                     'plants': relation(Plant, cascade='all, delete-orphan', 
                                        order_by=plant_table.c.code,
                                        backref='accession', ),
                     'verifications': relation(Verification, order_by='date',
                                               private=True, 
                                               backref='accession', )},
       order_by='code')
                               
mapper(Verification, verification_table)

    # these probably belong in separate tables with a single join
    #cultv_info = StringCol(default=None)      # cultivation information
    #prop_info = StringCol(default=None)       # propogation information
    #acc_uses = StringCol(default=None)        # accessions uses, why diff than taxon uses?
       # propagation history ???
    #prop_history = StringCol(length=11, default=None)

    # accession lineage, parent garden code and acc id ???
    #acc_lineage = StringCol(length=50, default=None)    
    #acctxt = StringCol(default=None) # ???
    

    # i don't think this is the red list status but rather the status
    # of this accession in some sort of conservation program
    #consv_status = StringCol(default=None) # conservation status, free text
    
    

    
#class Accession(BaubleTable):
#
#    class sqlmeta(BaubleTable.sqlmeta):
#	       defaultOrder = 'acc_id'
#
#    acc_id = UnicodeCol(length=20, notNull=True, alternateID=True)
#        
#    prov_type = EnumCol(enumValues=("Wild", # Wild,
#                                    "Propagule of cultivated wild plant", # Propagule of wild plant in cultivation
#                                    "Not of wild source", # Not of wild source
#                                    "Insufficient Data", # Insufficient data
#                                    "Unknown",
#                                    None),
#                        default=None)
#
#    # wild provenance status, wild native, wild non-native, cultivated native
#    wild_prov_status = EnumCol(enumValues=("Wild native", # Endemic found within it indigineous range
#                                           "Wild non-native", # Propagule of wild plant in cultivation
#                                           "Cultivated native", # Not of wild source
#                                           "Insufficient Data", # Insufficient data
#                                           "Unknown",
#                                           None),
#                               default=None)
#    
#    # date accessioned
#    date = DateCol(notNull=True)
#    
#    # indicates wherewe should get the source information from either of those 
#    # columns
#    source_type = EnumCol(enumValues=('Collection', 'Donation', None),
#                          default=None)                   
#    notes = UnicodeCol(default=None)    
#    
#    # foriegn keys
#    #
#    species = ForeignKey('Species', notNull=True, cascade=False)    
#    
#    # joins
#    #
#    _collection = SingleJoin('Collection', joinColumn='accession_id')
#    _donation = SingleJoin('Donation', joinColumn='accession_id', makeDefault=None)
#    plants = MultipleJoin("Plant", joinColumn='accession_id')    
#    
#    
#    # these probably belong in separate tables with a single join
#    #cultv_info = StringCol(default=None)      # cultivation information
#    #prop_info = StringCol(default=None)       # propogation information
#    #acc_uses = StringCol(default=None)        # accessions uses, why diff than taxon uses?
#       # propagation history ???
#    #prop_history = StringCol(length=11, default=None)
#
#    # accession lineage, parent garden code and acc id ???
#    #acc_lineage = StringCol(length=50, default=None)    
#    #acctxt = StringCol(default=None) # ???
#    
#    #
#    # verification, a verification table would probably be better and then
#    # the accession could have a verification history with a previous
#    # verification id which could create a chain for the history,
#    # this would be necessary especially for herbarium records
#    #
#    #ver_level = StringCol(length=2, default=None) # verification level
#    #ver_name = StringCol(length=50, default=None) # verifier's name
#    #ver_date = DateTimeCol(default=None) # verification date
#    #ver_hist = StringCol(default=None)  # verification history
#    #ver_lit = StringCol(default=None) # verification lit
#    #ver_id = IntCol(default=None) # ?? # verifier's ID??
#    
#
#    # i don't think this is the red list status but rather the status
#    # of this accession in some sort of conservation program
#    #consv_status = StringCol(default=None) # conservation status, free text
#    
#    
#    def __str__(self): 
#        return self.acc_id
#    
#    def markup(self):
#        return '%s (%s)' % (self.acc_id, self.species.markup())



def get_source(row):
    # TODO: in one of the release prior to 0.4.5 we put the string 'NoneType'
    # into some of the accession.source_type columns, this can cause an error
    # here but it's not critical, but we should make sure this doesn't happen
    # again in the future, maybe incorporated into a test
    if row.source_type == None:
        return None
    elif row.source_type == tables['Donation'].__name__:
        # the __name__ should be 'Donation'
        return row._donation
    elif row.source_type == tables['Collection'].__name__:
        return row._collection
    else:
        raise ValueError('unknown source type: ' + str(row.source_type))
    

        
class AccessionEditorView(GenericEditorView):
    
    expanders_pref_map = {'acc_notes_expander': 'editor.accession.notes.expanded', 
                          'acc_source_expander': 'editor.accession.source.expanded'}
    

    def __init__(self, parent=None):
        GenericEditorView.__init__(self, os.path.join(paths.lib_dir(), 
                                                      'plugins', 'garden', 
                                                      'editors.glade'),
                                   parent=parent)
        self.dialog = self.widgets.accession_dialog
        self.dialog.set_transient_for(parent)
        self.attach_completion('acc_species_entry')
        self.restore_state()
        self.connect_dialog_close(self.widgets.accession_dialog)
        if sys.platform == 'win32':
            self.do_win32_fixes()
    
    
    def do_win32_fixes(self):
        import pango
        def get_char_width(widget):
            context = widget.get_pango_context()        
            font_metrics = context.get_metrics(context.get_font_description(), 
                                               context.get_language())        
            width = font_metrics.get_approximate_char_width()            
            return pango.PIXELS(width)

        species_entry = self.widgets.acc_species_entry
        species_entry.set_size_request(get_char_width(species_entry)*20, -1)
        prov_combo = self.widgets.acc_prov_combo
        prov_combo.set_size_request(get_char_width(prov_combo)*20, -1)
        wild_prov_combo = self.widgets.acc_wild_prov_combo
        wild_prov_combo.set_size_request(get_char_width(wild_prov_combo)*12, -1)
        source_combo = self.widgets.acc_source_type_combo
        source_combo.set_size_request(get_char_width(source_combo)*10, -1)
                
        # TODO: we really don't need to do the rest of these until we know the 
        # which source box is going to be opened, could connect to the boxes 
        # realized or focused signals or something along those lines
        
        # fix the widgets in the collection editor
        lat_entry = self.widgets.lat_entry
        lat_entry.set_size_request(get_char_width(lat_entry)*8, -1)
        lon_entry = self.widgets.lon_entry
        lon_entry.set_size_request(get_char_width(lon_entry)*8, -1)
        locale_entry = self.widgets.locale_entry
        locale_entry.set_size_request(get_char_width(locale_entry)*30, -1)
        
        lat_dms_label = self.widgets.lat_dms_label
        lat_dms_label.set_size_request(get_char_width(lat_dms_label)*7, -1)
        lon_dms_label = self.widgets.lon_dms_label
        lon_dms_label.set_size_request(get_char_width(lon_dms_label)*7, -1)
        
        # fixes for donation editor        

        
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
            
#    def save_state(self):
#        prefs[self.source_expanded_pref] = \
#            self.widgets.source_expander.get_expanded()
#        
#        
#    def restore_state(self):
#        expanded = prefs.get(self.source_expanded_pref, True)
#        self.widgets.source_expander.set_expanded(expanded)

            
    def start(self):
        return self.widgets.accession_dialog.run()    
        
        
    def species_completion_match_func(self, completion, key_string, iter, data=None):        
        '''
        the only thing this does different is it make the match case insensitve
        '''
        value = completion.get_model()[iter][0]
        return str(value).lower().startswith(key_string.lower())         


    def species_cell_data_func(self, column, renderer, model, iter, data=None):
        v = model[iter][0]
        renderer.set_property('text', str(v))
        


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
                           'coll_notes_textview': 'notes'}
    
    # TODO: could make the problems be tuples of an id and description to
    # be displayed in a dialog or on a label ala eclipse
    PROBLEM_BAD_LATITUDE = 1
    PROBLEM_BAD_LONGITUDE = 2
    PROBLEM_INVALID_DATE = 3
            
            
    def __init__(self, model, view, session):
        GenericEditorPresenter.__init__(self, ModelDecorator(model), view)
        self.session = session
        self.refresh_view()    
        
        self.assign_simple_handler('collector_entry', 'collector')
        self.assign_simple_handler('locale_entry', 'locale')
        self.assign_simple_handler('collid_entry', 'coll_id')
        self.assign_simple_handler('geoacc_entry', 'geo_accy',
                                   IntOrNoneStringValidator())
        self.assign_simple_handler('alt_entry', 'elevation', 
                                   FloatOrNoneStringValidator())
        self.assign_simple_handler('altacc_entry', 'elevation_accy',
                                   FloatOrNoneStringValidator())
        self.assign_simple_handler('habitat_textview', 'habitat')
        self.assign_simple_handler('coll_notes_textview', 'notes')
        
        lat_entry = self.view.widgets.lat_entry
        lat_entry.connect('insert-text', self.on_lat_entry_insert)
        lat_entry.connect('delete-text', self.on_lat_entry_delete)
        
        lon_entry = self.view.widgets.lon_entry
        lon_entry.connect('insert-text', self.on_lon_entry_insert)
        lon_entry.connect('delete-text', self.on_lon_entry_delete)
        
        coll_date_entry = self.view.widgets.coll_date_entry
        coll_date_entry.connect('insert-text', self.on_date_entry_insert)
        coll_date_entry.connect('delete-text', self.on_date_entry_delete)

        # don't need to connection to south/west since they are in the same
        # groups as north/east
        north_radio = self.view.widgets.north_radio
        self.north_toggle_signal_id = north_radio.connect('toggled', 
                                                          self.on_north_south_radio_toggled)        
        east_radio = self.view.widgets.east_radio        
        self.east_toggle_signal_id = east_radio.connect('toggled', 
                                                   self.on_east_west_radio_toggled)

    def dirty(self):
        return self.model.dirty
    
    
    def refresh_view(self):
        for widget, field in self.widget_to_field_map.iteritems():
            value = self.model[field]
#            debug('%s, %s, %s' % (widget, field, value))
            if value is not None and field == 'date':                
                value = '%s/%s/%s' % (value.day, value.month, value.year)
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
        

    _date_regex = re.compile('(?P<day>\d?\d)/(?P<month>\d?\d)/(?P<year>\d\d\d\d)')
    
    def _set_date_from_text(self, text):
        if text == '':
            self.model.date = None
            self.remove_problem(self.PROBLEM_INVALID_DATE, 
                                self.view.widgets.coll_date_entry)
            return
        
        dt = None # datetime
        m = self._date_regex.match(text)
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
    

    # TODO: need to write a test for this method
    @staticmethod
    def _parse_lat_lon(direction, text):
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
            raise ValueError('_parse_lat_lon -- incorrect format: %s' % \
                             text)
        return dec


    def _get_lat_direction(self):
        if self.view.widgets.north_radio.get_active():
            return 'N'
        elif self.view.widgets.south_radio.get_active():
            return 'S'
        raise ValueError('North/South radio buttons in a confused state')
            
            
    def _get_lon_direction(self):
        if self.view.widgets.east_radio.get_active():
            return 'E'
        elif self.view.widgets.west_radio.get_active():
            return 'W'
        raise ValueError('East/West radio buttons in a confused state')
    
    
    def on_lat_entry_insert(self, entry, new_text, new_text_length, position, 
                            data=None):
        entry_text = entry.get_text()                
        cursor = entry.get_position()
        full_text = entry_text[:cursor] + new_text + entry_text[cursor:]       
        self._set_latitude_from_text(full_text)
        

    def on_lat_entry_delete(self, entry, start, end, data=None):
        text = entry.get_text()
        full_text = text[:start] + text[end:]
        self._set_latitude_from_text(full_text)
            
            
    def _set_latitude_from_text(self, text):
        latitude = None
        dms_string = ''
        try:
            if text != '' and text is not None:
                self.view.widgets.north_radio.handler_block(self.north_toggle_signal_id)
                if text[0] == '-':
                    self.view.widgets.south_radio.set_active(True)
                else:
                    self.view.widgets.north_radio.set_active(True)
                self.view.widgets.north_radio.handler_unblock(self.north_toggle_signal_id)
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
                self.view.widgets.east_radio.handler_block(self.east_toggle_signal_id)
                if text[0] == '-':
                    self.view.widgets.west_radio.set_active(True)
                else:
                    self.view.widgets.east_radio.set_active(True)
                self.view.widgets.east_radio.handler_unblock(self.east_toggle_signal_id)
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
    PROBLEM_INVALID_DATE = 3
    
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
        self.assign_simple_handler('donid_entry', 'donor_acc')
        self.assign_simple_handler('donnotes_entry', 'notes')       
        don_date_entry = self.view.widgets.don_date_entry
        don_date_entry.connect('insert-text', self.on_date_entry_insert)
        don_date_entry.connect('delete-text', self.on_date_entry_delete)
        self.view.widgets.don_new_button.connect('clicked', 
                                                 self.on_don_new_clicked)
        self.view.widgets.don_edit_button.connect('clicked',
                                                  self.on_don_edit_clicked)
        
        # if there is only one donor in the donor combo model and 
        if self.model.donor is None and len(donor_combo.get_model()) == 1:
            donor_combo.set_active(0)
    
            
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
        if isinstance(value, tables['Donor']):
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
        

    _date_regex = re.compile('(?P<day>\d?\d)/(?P<month>\d?\d)/(?P<year>\d\d\d\d)')
    def _set_date_from_text(self, text):        
        if text == '':
            self.model.date = None
            self.remove_problem(self.PROBLEM_INVALID_DATE, 
                                self.view.widgets.don_date_entry)
            return
        
        m = self._date_regex.match(text)
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
        model = gtk.ListStore(object)        
        for value in self.session.query(Donor).select():
            model.append([value])
        donor_combo = self.view.widgets.donor_combo
        donor_combo.set_model(model)        
        
        for widget, field in self.widget_to_field_map.iteritems():            
            value = self.model[field]
#            debug('%s, %s, %s' % (widget, field, value))
            if value is not None and field == 'date':
                value = '%s/%s/%s' % (value.day, value.month, value.year)
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
        raise ValueError('unknown source type: %s' % source_type)


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
                           'acc_date_entry': 'date',
                           'acc_prov_combo': 'prov_type',
                           'acc_wild_prov_combo': 'wild_prov_status',
                           'acc_species_entry': 'species_id',
                           'acc_source_type_combo': 'source_type',
                           'acc_notes_textview': 'notes'}
    
    
    PROBLEM_INVALID_DATE = 3
    PROBLEM_DUPLICATE_ACCESSION = 5
    
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
        self.init_enum_combo('acc_prov_combo', 'prov_type')
        self.init_enum_combo('acc_wild_prov_combo', 'wild_prov_status')
        self.init_source_expander()             
        self.refresh_view() # put model values in view    

        # connect signals
        def sp_get_completions(text):           
            genus_ids = select([genus_table.c.id], genus_table.c.genus.like('%s%%' % text))
            sql = species_table.select(species_table.c.genus_id.in_(genus_ids))
            return self.session.query(Species).select(sql) 
        def set_in_model(self, field, value):
#            debug('set_in_model(%s, %s)' % (field, value))
            setattr(self.model, field, value)
        self.assign_completions_handler('acc_species_entry', 'species', 
                                        sp_get_completions, 
                                        set_func=set_in_model)
        self.view.widgets.acc_prov_combo.connect('changed', self.on_combo_changed, 
                                                 'prov_type')
        self.view.widgets.acc_wild_prov_combo.connect('changed', 
                                                      self.on_combo_changed,
                                                      'wild_prov_status')
        # TODO: could probably replace this by just passing a valdator
        # to assign_simple_handler...UPDATE: but can the validator handle
        # adding a problem to the widget
        self.view.widgets.acc_code_entry.connect('insert-text', 
                                               self.on_acc_code_entry_insert)
        self.view.widgets.acc_code_entry.connect('delete-text', 
                                               self.on_acc_code_entry_delete)
        self.assign_simple_handler('acc_notes_textview', 'notes')
        
        acc_date_entry = self.view.widgets.acc_date_entry
        acc_date_entry.connect('insert-text', self.on_acc_date_entry_insert)
        acc_date_entry.connect('delete-text', self.on_acc_date_entry_delete)
        self.init_change_notifier()
    
    
    def dirty(self):
        if self.source_presenter is None:
            return self.model.dirty
        return self.source_presenter.dirty() or self.model.dirty
    
    
    def on_acc_code_entry_insert(self, entry, new_text, new_text_length, position, 
                            data=None):
        entry_text = entry.get_text()                
        cursor = entry.get_position()
        full_text = entry_text[:cursor] + new_text + entry_text[cursor:]
        self._set_acc_code_from_text(full_text)

        
    def on_acc_code_entry_delete(self, entry, start, end, data=None):
        text = entry.get_text()
        full_text = text[:start] + text[end:]
        self._set_acc_code_from_text(full_text)
                
        
    def _set_acc_code_from_text(self, text):
        if text != self._original_code and self.session.query(Accession).count_by(code=text) > 0:            
            self.add_problem(self.PROBLEM_DUPLICATE_ACCESSION,
                             self.view.widgets.acc_code_entry)
            self.model.code = None            
            return        
        self.remove_problem(self.PROBLEM_DUPLICATE_ACCESSION,
                            self.view.widgets.acc_code_entry)
        if text is '':
            self.model.code = None
        self.model.code = text
            
        
    def on_acc_date_entry_insert(self, entry, new_text, new_text_length, position, 
                            data=None):        
        entry_text = entry.get_text()                
        cursor = entry.get_position()
        full_text = entry_text[:cursor] + new_text + entry_text[cursor:]
#        debug('acc:date_insert: %s' % full_text)
        self._set_acc_date_from_text(full_text)
        

    def on_acc_date_entry_delete(self, entry, start, end, data=None):
        text = entry.get_text()
        full_text = text[:start] + text[end:]
        self._set_acc_date_from_text(full_text)
        

    # TODO: there is a funny bug here if you enter the date 1/1/1900
    _date_regex = re.compile('(?P<day>\d?\d)/(?P<month>\d?\d)/(?P<year>\d\d\d\d)')
    
    def _set_acc_date_from_text(self, text):
        m = self._date_regex.match(text)
        dt = None # datetime
        if text == '':
            # accession date can't be None
            self.add_problem(self.PROBLEM_INVALID_DATE,
                             self.view.widgets.acc_date_entry)
            self.model.date = dt
        try:
            ymd = [int(x) for x in [m.group('year'), m.group('month'), \
                                    m.group('day')]]
            dt = datetime(*ymd).date()
            self.remove_problem(self.PROBLEM_INVALID_DATE, 
                                self.view.widgets.acc_date_entry)
        except:
#            debug(traceback.format_exc())
            self.add_problem(self.PROBLEM_INVALID_DATE,
                             self.view.widgets.acc_date_entry)
                        
        self.model.date = dt
        
    
    def on_field_changed(self, model, field):
#        debug('on field changed: %s = %s' % (field, getattr(model, field)))
        # TODO: we could have problems here if we are monitoring more than
        # one model change and the two models have a field with the same name,
        # e.g. date, then if we do 'if date == something' we won't know
        # which model changed
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
            if model.latitude is not None and model.longitude is not None:
                self.view.widgets.geoacc_entry.set_sensitive(True)
            else:
                self.view.widgets.geoacc_entry.set_sensitive(False)
            
        if field == 'elevation':
            if model.elevation is not None:            
                self.view.widgets.altacc_entry.set_sensitive(True)
            else: 
                self.view.widgets.altacc_entry.set_sensitive(False)
                
        # refresh the sensitivity of the accept buttons
        sensitive = True
        if len(self.problems) != 0:
            sensitive = False
        elif self.source_presenter is not None:
            if len(self.source_presenter.problems) != 0:
                sensitive = False
        elif self.model.code is None or self.model.species is None:
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
        # FIXME: Donation and Collection shouldn't be hardcoded so that it 
        # can be translated
        # this helps keep a reference to the widgets so they don't get destroyed
        box_map = {'Donation': self.view.widgets.donation_box, 
                   'Collection': self.view.widgets.collection_box}
        
        # the source_type has changed
        if source_type != self.model.source_type:
            source_type_changed = True
            if source_type is None:
                self.model.source = None
            elif isinstance(self._original_source, tables[source_type]):
                self.model.source = self._original_source
            else:              
                self.model.source = tables[source_type]()
                                
        # replace source box contents with our new box
        #source_box = self.view.widgets.source_box
        source_box_parent = self.view.widgets.source_box_parent
        if self.current_source_box is not None:
            self.view.widgets.remove_parent(self.current_source_box)
        if source_type is not None:
#            debug(source_type)
            self.current_source_box = box_map[source_type]
            self.view.widgets.remove_parent(self.current_source_box)
            #source_box.pack_start(self.current_source_box, expand=False, 
            #                      fill=True)
            source_box_parent.add(self.current_source_box)
        else:
            self.current_source_box = None
        
        if self.model.source is not None:
            self.source_presenter = \
                SourcePresenterFactory(self.model.source, self.view, self.session)
            # initialize model change notifiers    
            for field in self.source_presenter.widget_to_field_map.values():            
                self.source_presenter.model.add_notifier(field, self.on_field_changed)
#            debug(self.model.source in self.session.dirty)
#        if self.model.source is None:
#            # turn the accept buttons on here b/c i don't know a better place to 
#            # do it
#            #self.set_accept_buttons_sensitive(True)
#            self.on_field_changed(self.model, 'source_type')
#            pass
        if source_type_changed:
            self.on_field_changed(self.model, 'source_type')
        #source_box.show_all()
        

        
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
#        self.view.dialog.show_all()
        
        
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
#            debug('%s, model[%s] = %s' % (widget,field, value))
            if value is not None and field == 'date':
                value = '%s/%s/%s' % (value.day, value.month, value.year)
            
            self.view.set_widget_value(widget, value)

        if self.model.prov_type == 'Wild':
            self.view.widgets.acc_wild_prov_combo.set_sensitive(True)
            self.view.widgets.acc_wild_prov_frame.set_sensitive(True)
        else:
            self.view.widgets.acc_wild_prov_combo.set_sensitive(False)
            self.view.widgets.acc_wild_prov_frame.set_sensitive(False)

                
    def start(self):
        return self.view.start()
        
        

class AccessionEditor(GenericModelViewPresenterEditor):
    
    label = 'Accession'
    mnemonic_label = '_Accession'
    
    # these have to correspond to the response values in the view
    RESPONSE_OK_AND_ADD = 11
    RESPONSE_NEXT = 22
    ok_responses = (RESPONSE_OK_AND_ADD, RESPONSE_NEXT)    
        
        
    def __init__(self, model=None, parent=None):
        '''
        @param model: Accession instance or None
        @param parent: the parent widget
        '''        
        if model is None:
            model = Accession()
        GenericModelViewPresenterEditor.__init__(self, model, parent)
        if parent is None: # should we even allow a change in parent
            parent = bauble.app.gui.window
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
                msg = 'Error committing changes.\n\n%s' % utils.xml_safe(e.orig)
                utils.message_details_dialog(msg, str(e), gtk.MESSAGE_ERROR)
                return False
            except Exception, e:
                msg = 'Unknown error when committing changes. See the details '\
                      'for more information.\n\n%s' % utils.xml_safe(e)
                debug(traceback.format_exc())
                utils.message_details_dialog(msg, traceback.format_exc(), 
                                             gtk.MESSAGE_ERROR)
                return False
        elif self.presenter.dirty() and utils.yes_no_dialog(not_ok_msg) or not self.presenter.dirty():
            return True
        else:
            return False
                
        # respond to responses
        more_committed = None
        if response == self.RESPONSE_NEXT:
            e = AccessionEditor(parent=self.parent)
            more_committed = e.start()
        elif response == self.RESPONSE_OK_AND_ADD:
#            e = PlantEditor(parent=self.parent, 
#                            model_or_defaults={'accession_id': self._committed[0].id})
            e = PlantEditor(Plant(accession=self.model), self.parent)
            more_committed = e.start()
                    
        if more_committed is not None:
            committed = [self._committed]
            if isinstance(more_committed, list):
                self._committed.extend(more_committed)
            else:
                self._committed.append(more_committed)                
        
        return True        

    
    def start(self):
        from bauble.plugins.plants.species_model import Species
        if self.session.query(Species).count() == 0:        
            msg = 'You must first add or import at least one species into the '\
                  'database before you can add accessions.'
            utils.message_dialog(msg)
            return
        self.view = AccessionEditorView(parent=self.parent)
        self.presenter = AccessionEditorPresenter(self.model, self.view)
        
        # add quick response keys
        dialog = self.view.dialog        
        self.attach_response(dialog, gtk.RESPONSE_OK, 'Return', gtk.gdk.CONTROL_MASK)
        self.attach_response(dialog, self.RESPONSE_OK_AND_ADD, 'a', gtk.gdk.CONTROL_MASK)
        self.attach_response(dialog, self.RESPONSE_NEXT, 'n', gtk.gdk.CONTROL_MASK)        
        
        exc_msg = "Could not commit changes.\n"
        committed = None
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
                msg = 'model must have both latitude and longitude or neither'
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
try:
    from bauble.plugins.searchview.infobox import InfoBox, InfoExpander
except ImportError:    
    pass
else:
    import os
    import bauble.paths as paths
    from bauble.plugins.garden.plant import Plant
    
    
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
            InfoExpander.__init__(self, "General", widgets)
            general_box = self.widgets.general_box
            self.widgets.general_window.remove(general_box)
            self.vbox.pack_start(general_box)
        
        
        def update(self, row):
            '''
            '''
            self.set_widget_value('name_data', 
                                  '%s\n%s' % (row.species.markup(True), row.code))
            session = object_session(row)
            # TODO: it would be nice if we did something like 13 Living, 2 Dead,
            # 6 Unknown, etc
            # TODO: could this be sped up, does it matter?            
            nplants = session.query(Plant).count_by(accession_id=row.id)
            self.set_widget_value('nplants_data', nplants)
            self.set_widget_value('prov_data', row.prov_type, False)
            
            
    class NotesExpander(InfoExpander):
        """
        the accession's notes
        """
    
        def __init__(self, widgets):
            InfoExpander.__init__(self, "Notes", widgets)            
            notes_box = self.widgets.notes_box
            self.widgets.notes_window.remove(notes_box)
            self.vbox.pack_start(notes_box)
        
        
        def update(self, row):
            self.set_widget_value('notes_data', row.notes)            
    
    
    class SourceExpander(InfoExpander):
        
        def __init__(self, widgets):
            InfoExpander.__init__(self, 'Source', widgets)
            self.curr_box = None
        
        
        def update_collections(self, collection):
            
            self.set_widget_value('loc_data', collection.locale)
            
            geo_accy = collection.geo_accy
            if geo_accy is None:
                geo_accy = ''
            else: 
                geo_accy = '(+/- %sm)' % geo_accy
            
            if collection.latitude is not None:
                dir, deg, min, sec = latitude_to_dms(collection.latitude)
                s = '%.2f (%s %s\302\260%s"%.3f\') %s' % \
                    (collection.latitude, dir, deg, min, sec, geo_accy)
                self.set_widget_value('lat_data', s)

            if collection.longitude is not None:
                dir, deg, min, sec = longitude_to_dms(collection.longitude)
                s = '%.2f (%s %s\302\260%s"%.3f\') %s' % \
                    (collection.longitude, dir, deg, min, sec, geo_accy)
                self.set_widget_value('lon_data', s)                                
            
            v = collection.elevation

            if collection.elevation_accy is not None:
                v = '%s (+/- %sm)' % (v, collection.elevation_accy)
            self.set_widget_value('elev_data', v)
            
            self.set_widget_value('coll_data', collection.collector)
            self.set_widget_value('date_data', collection.date)
            self.set_widget_value('collid_data', collection.collectors_code)
            self.set_widget_value('habitat_data', collection.habitat)
            self.set_widget_value('collnotes_data', collection.notes)
            
                
        def update_donations(self, donation):
            #self.set_widget_value('donor_data', donation.donor)
            session = object_session(donation)
            self.set_widget_value('donor_data', session.load(Donor, donation.donor_id))
            self.set_widget_value('donid_data', donation.donor_acc)
            self.set_widget_value('donnotes_data', donation.notes)
        
        
        def update(self, value):        
            if self.curr_box is not None:
                self.vbox.remove(self.curr_box)
                    
            if value is None:
                self.set_expanded(False)
                self.set_sensitive(False)
                return
                    
            # TODO: i guess we are losing the references here to box map
            # and so the widgets are getting destroyed, somehow we need to make
            # this persistent, maybe make it class level
            box_map = {Collection: (self.widgets.collections_box, 
                                    self.update_collections),
                       Donation: (self.widgets.donations_box, 
                                  self.update_donations)}
            box, update = box_map[value.__class__]
            self.widgets.remove_parent(box)
            self.curr_box = box
            update(value)        
#            if isinstance(value, Collection):            
#                #box = self.widgets.collections_box
#                self.widgets.remove_parent(box)
#                self.curr_box = box
#                self.update_collections(value)        
#            elif isinstance(value, Donation):
#                box = self.widgets.donations_box
#                self.widgets.remove_parent(box)
#                self.curr_box = box
#                self.update_donations(value)            
#            else:
#                msg = "Unknown type for source: " + str(type(value))
#                utils.message_dialog(msg, gtk.MESSAGE_ERROR)
            
            self.vbox.pack_start(self.curr_box)            
            self.set_expanded(True)
            self.set_sensitive(True)
            
    
    class AccessionInfoBox(InfoBox):
        """
        - general info
        - source
        """
        def __init__(self):
            InfoBox.__init__(self)
            glade_file = os.path.join(paths.lib_dir(), "plugins", "garden", 
                                "acc_infobox.glade")
            self.widgets = utils.GladeWidgets(gtk.glade.XML(glade_file))
            
            self.general = GeneralAccessionExpander(self.widgets)
            self.add_expander(self.general)
            
            self.source = SourceExpander(self.widgets)
            self.add_expander(self.source)
            
            self.notes = NotesExpander(self.widgets)
            self.add_expander(self.notes)
    
    
        def update(self, row):
            self.general.update(row)
            
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
            super(SourceInfoBox, self).update(row.accession)

