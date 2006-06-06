#
# accessions module
#

import os, traceback, math
from datetime import datetime
import xml.sax.saxutils as saxutils
import gtk, gobject
from sqlobject import * 
from sqlobject.constraints import BadValue, notNull
from sqlobject.sqlbuilder import _LikeQuoted
from sqlobject.col import FloatValidator, IntValidator
from formencode import *
import bauble
import bauble.utils as utils
import bauble.paths as paths
from bauble.plugins import BaubleTable, tables, editors
from bauble.editor import *
from bauble.utils.log import debug
from bauble.prefs import prefs
from bauble.error import CommitException

# TODO: underneath the species entry create a label that shows information
# about the family of the genus of the species selected as well as more
# info about the genus so we know exactly what plant is being selected
# e.g. Malvaceae (sensu lato), Hibiscus (senso stricto)

# TODO: colors on the event boxes around some of the entries don't change color 
# on win32, is this my problem or a gtk+ bug

# FIXME: time.mktime can't handle dates before 1970 on win32

#def utm_wgs84_to_dms():
#    pass
#
#def dms_to_utm_wgs84():
#    pass

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



class Accession(BaubleTable):

    class sqlmeta(BaubleTable.sqlmeta):
	       defaultOrder = 'acc_id'

    acc_id = UnicodeCol(length=20, notNull=True, alternateID=True)
        
    prov_type = EnumCol(enumValues=("Wild", # Wild,
                                    "Propagule of cultivated wild plant", # Propagule of wild plant in cultivation
                                    "Not of wild source", # Not of wild source
                                    "Insufficient Data", # Insufficient data
                                    "Unknown",
                                    None),
                        default=None)

    # wild provenance status, wild native, wild non-native, cultivated native
    wild_prov_status = EnumCol(enumValues=("Wild native", # Endemic found within it indigineous range
                                           "Wild non-native", # Propagule of wild plant in cultivation
                                           "Cultivated native", # Not of wild source
                                           "Insufficient Data", # Insufficient data
                                           "Unknown",
                                           None),
                               default=None)
    
    # date accessioned
    date = DateCol(notNull=True)
    
    # indicates wherewe should get the source information from either of those 
    # columns
    source_type = EnumCol(enumValues=('Collection', 'Donation', None),
                          default=None)                   
    notes = UnicodeCol(default=None)    
    
    # foriegn keys
    #
    species = ForeignKey('Species', notNull=True, cascade=False)    
    
    # joins
    #
    _collection = SingleJoin('Collection', joinColumn='accession_id')
    _donation = SingleJoin('Donation', joinColumn='accession_id', makeDefault=None)
    plants = MultipleJoin("Plant", joinColumn='accession_id')    
    
    
    # these probably belong in separate tables with a single join
    #cultv_info = StringCol(default=None)      # cultivation information
    #prop_info = StringCol(default=None)       # propogation information
    #acc_uses = StringCol(default=None)        # accessions uses, why diff than taxon uses?
       # propagation history ???
    #prop_history = StringCol(length=11, default=None)

    # accession lineage, parent garden code and acc id ???
    #acc_lineage = StringCol(length=50, default=None)    
    #acctxt = StringCol(default=None) # ???
    
    #
    # verification, a verification table would probably be better and then
    # the accession could have a verification history with a previous
    # verification id which could create a chain for the history,
    # this would be necessary especially for herbarium records
    #
    #ver_level = StringCol(length=2, default=None) # verification level
    #ver_name = StringCol(length=50, default=None) # verifier's name
    #ver_date = DateTimeCol(default=None) # verification date
    #ver_hist = StringCol(default=None)  # verification history
    #ver_lit = StringCol(default=None) # verification lit
    #ver_id = IntCol(default=None) # ?? # verifier's ID??
    

    # i don't think this is the red list status but rather the status
    # of this accession in some sort of conservation program
    #consv_status = StringCol(default=None) # conservation status, free text
    
    
    def __str__(self): 
        return self.acc_id
    
    def markup(self):
        return '%s (%s)' % (self.acc_id, self.species.markup())



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
    
    source_expanded_pref = 'editor.accesssion.source.expanded'

    def __init__(self, parent=None):
        GenericEditorView.__init__(self, os.path.join(paths.lib_dir(), 
                                                      'plugins', 'garden', 
                                                      'editors.glade'),
                                   parent=parent)
        self.dialog = self.widgets.accession_dialog
        self.dialog.set_transient_for(parent)
        # configure species_entry
        completion = gtk.EntryCompletion()    
        completion.set_match_func(self.species_completion_match_func)        
        r = gtk.CellRendererText() # set up the completion renderer
        completion.pack_start(r)
        completion.set_cell_data_func(r, self.species_cell_data_func)        
        #completion.set_text_column(0)    
        completion.set_minimum_key_length(2)
        # DONT DO INLINE COMPLETION, it can cause insert text to look up 
        # new and unneccessary completions and doesn't put the species id
        # in the model any way since on_species_selected isn't called
        #completion.set_inline_completion(True) 
        completion.set_popup_completion(True)                 
        self.widgets.species_entry.set_completion(completion)
        self.restore_state()
        # TODO: set up automatic signal handling, all signals should be called
        # on the presenter
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

        species_entry = self.widgets.species_entry
        species_entry.set_size_request(get_char_width(species_entry)*20, -1)
        prov_combo = self.widgets.prov_combo
        prov_combo.set_size_request(get_char_width(prov_combo)*20, -1)
        wild_prov_combo = self.widgets.wild_prov_combo
        wild_prov_combo.set_size_request(get_char_width(wild_prov_combo)*12, -1)
        source_combo = self.widgets.source_type_combo
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
        prefs[self.source_expanded_pref] = \
            self.widgets.source_expander.get_expanded()
        
        
    def restore_state(self):
        expanded = prefs.get(self.source_expanded_pref, True)
        self.widgets.source_expander.set_expanded(expanded)

            
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
        


class IntOrEmptyStringValidator(IntValidator):
        
    def __init__(self, name):
        IntValidator.__init__(self, name=name)
        
        
    def to_python(self, value, state):
        if value is None:
            return None
        if isinstance(value, (int, long, sqlbuilder.SQLExpression)):
            return value        
        elif isinstance(value, str) and value == '':
            return None
        try:
            return int(value)
        except:
            raise validators.Invalid("expected a int in the FloatCol '%s', got %s instead" % \
                (self.name, type(value)), value, state)



class FloatOrEmptyStringValidator(FloatValidator):
        
    def __init__(self, name):
        FloatValidator.__init__(self, name=name)
        
        
    def to_python(self, value, state):
        if value is None:
            return None
        if isinstance(value, (int, long, float, sqlbuilder.SQLExpression)):
            return value        
        elif isinstance(value, str) and value == '':
            return None
        try:
            return float(value)
        except:
            raise validators.Invalid("expected a float in the FloatCol '%s', got %s instead" % \
                (self.name, type(value)), value, state)
                


# TODO: should have a label next to lat/lon entry to show what value will be 
# stored in the database, might be good to include both DMS and the float
# so the user can see both no matter what is in the entry. it could change in
# time as the user enters data in the entry
# TODO: shouldn't allow entering altitude accuracy without entering accuracy,
# same for geographic accuracy
# TODO: should show an error if something other than a number is entered in
# the altitude entry
class CollectionPresenter(GenericEditorPresenter):
    
    widget_to_field_map = {'collector_entry': 'collector',                           
                           'coll_date_entry': 'coll_date',
                           'collid_entry': 'coll_id',
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
            
    def _get_column_validator(self, column):
        return self.model.columns[column].validator
                
        
    def __init__(self, model, view, defaults={}):
        GenericEditorPresenter.__init__(self, model, view)
        self.defaults = defaults
        self.refresh_view()    
        
        self.assign_simple_handler('collector_entry', 'collector')
        self.assign_simple_handler('locale_entry', 'locale')
        self.assign_simple_handler('collid_entry', 'coll_id')
        self.assign_simple_handler('geoacc_entry', 'geo_accy',
                                   IntOrEmptyStringValidator('geo_accy'))
        self.assign_simple_handler('alt_entry', 'elevation', 
                                   FloatOrEmptyStringValidator('elevation'))
        self.assign_simple_handler('altacc_entry', 'elevation_accy',
                                   FloatOrEmptyStringValidator('elevation_accy'))
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


    def refresh_view(self):
        for widget, field in self.widget_to_field_map.iteritems():
            if field[-2:] == "ID":
                field = field[:-2]
            value = self.model[field]
#            debug('%s, %s, %s' % (widget, field, value))
            if value is not None and field == 'coll_date':
                value = '%s/%s/%s' % (value.day, value.month, value.year)
            self.view.set_widget_value(widget, value,
                                       default=self.defaults.get(field, None))         
        #lat_dms_label
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
            self.model.coll_date = None
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
        self.model.coll_date = dt
        
        
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
    
    def __init__(self, model, view, defaults={}):
        GenericEditorPresenter.__init__(self, model, view)        
        self.defaults = defaults
        donor_combo = self.view.widgets.donor_combo
        donor_combo.clear() # avoid gchararry/PyObject warning
        donor_combo.connect('changed', self.on_donor_combo_changed)
        r = gtk.CellRendererText()                    
        donor_combo.pack_start(r)
        donor_combo.set_cell_data_func(r, self.combo_cell_data_func)
       
        self.refresh_view()        
        self.assign_simple_handler('donid_entry', 'donor_acc')
        self.assign_simple_handler('donnotes_entry', 'notes')
        self.assign_simple_handler('donor_combo', 'donor')
        don_date_entry = self.view.widgets.don_date_entry
        don_date_entry.connect('insert-text', self.on_date_entry_insert)
        don_date_entry.connect('delete-text', self.on_date_entry_delete)
        self.view.widgets.don_new_button.connect('clicked', 
                                                 self.on_don_new_clicked)
        self.view.widgets.don_edit_button.connect('clicked',
                                                  self.on_don_edit_clicked)
        
        
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
#        if m is None:
#            self.add_problem(self.PROBLEM_INVALID_DATE, 
#                             self.view.widgets.don_date_entry)
#        else:
#            try:
#                ymd = [int(x) for x in [m.group('year'), m.group('month'), \
#                                        m.group('day')]]            
#                dt = datetime(*ymd).date()
#                self.remove_problem(self.PROBLEM_INVALID_DATE, 
#                                 gets.don_date_entry)
#            except:
#                self.add_problem(self.PROBLEM_INVALID_DATE, 
#                                 self.view.widgets.don_date_entry)
                
        self.model.date = dt

        
        
    def on_don_new_clicked(self, button, data=None):
        '''
        create a new donor, setting the current donor on donor_combo
        to the new donor
        '''
        e = editors['DonorEditor']()
        donor = e.start()
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
        e = editors['DonorEditor'](model=donor, 
                                   parent=self.view.widgets.accession_dialog)
        edited = e.start()
        if edited is not None:
            self.refresh_view()


    def on_donor_combo_changed(self, combo, data=None):
        '''
        changed the sensitivity of the don_edit_button if the
        selected item in the donor_combo is an instance of Donor
        '''
        i = combo.get_active_iter()
        if i is None:
            return
        value = combo.get_model()[i][0]
        if isinstance(value, tables['Donor']):
            self.view.widgets.don_edit_button.set_sensitive(True)
        else:
            self.view.widgets.don_edit_button.set_sensitive(False)

            
    def combo_cell_data_func(self, cell, renderer, model, iter):
        v = model[iter][0]
        renderer.set_property('text', str(v))        
                
           
    def refresh_view(self):
        model = gtk.ListStore(object)        
        for value in tables['Donor'].select():
            model.append([value])
        donor_combo = self.view.widgets.donor_combo
        donor_combo.set_model(model)        
        if len(model) == 1: # only one to choose from
            donor_combo.set_active(0)
        
        # TODO: what if there is a donor id in the source but the donor
        # doesn't exist        
        for widget, field in self.widget_to_field_map.iteritems():
            if field[-2:] == "ID":
                field = field[:-2]
            value = self.model[field]
#            debug('%s, %s, %s' % (widget, field, value))
            if value is not None and field == 'date':
                value = '%s/%s/%s' % (value.day, value.month, value.year)
            default = self.defaults.get(field, None)
            self.view.set_widget_value(widget, value, default=default)
        
        
        if self.model.donor is None:
            self.view.widgets.don_edit_button.set_sensitive(False)
        else:
            self.view.widgets.don_edit_button.set_sensitive(True)


class SourcePresenterFactory:
    
    def __init__(self):
        raise NotImplementedError('SourcePresenterFactor should not be '\
                                  'instantiated')
        
    @staticmethod
    def createSourcePresenter(source_type, model, view, defaults={}):
        if source_type == 'Collection':
            return CollectionPresenter(model, view, defaults)
        elif source_type == 'Donation':
            return DonationPresenter(model, view, defaults)
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
    
    widget_to_field_map = {'acc_id_entry': 'acc_id',
                           'acc_date_entry': 'date',
                           'prov_combo': 'prov_type',
                           'wild_prov_combo': 'wild_prov_status',
                           'species_entry': 'species',
                           'source_type_combo': 'source_type',
                           'acc_notes_textview': 'notes'}
    
    PROBLEM_INVALID_DATE = 3
    PROBLEM_INVALID_SPECIES = 4
    PROBLEM_DUPLICATE_ACCESSION = 5
    
    def __init__(self, model, view, defaults={}):
        '''
        model: should be an instance of class Accession
        view: should be an instance of AccessionEditorView
        '''
        GenericEditorPresenter.__init__(self, model, view)
        self.defaults = defaults
        # defaults probably has both speciesID and species, see 
        # SearchView.on_view_button_release
        self.defaults.pop('speciesID', None) 
        self.model.update(defaults)
#        debug(model)
        self.current_source_box = None
        self.source_presenter = None  
        # TODO: should we set these to the default value or leave them
        # be and let the default be set when the row is created, i'm leaning
        # toward the second, its easier if it works this way
        self.init_species_entry()
        self.init_prov_combo()
        self.init_wild_prov_combo()
        self.init_source_expander()        
        self.refresh_view() # put model values in view    
        # connect methods that watch for change now that we have 
        # refreshed the view
        #
        # TODO: need alot of work on species entry, should change colors if
        # a species isn't selected and one is selected but then if something
        # changes then it should invalidate again
        #
        self.insert_species_sid = self.view.widgets.species_entry.connect('insert-text', 
                                                self.on_species_entry_insert)
        self.view.widgets.species_entry.connect('delete-text', 
                                                self.on_species_entry_delete)
        self.view.widgets.prov_combo.connect('changed', self.on_combo_changed, 
                                             'prov_type')
        self.view.widgets.wild_prov_combo.connect('changed', 
                                                  self.on_combo_changed,
                                                  'wild_prov_status')
        #self.assign_simple_handler('acc_id_entry', 'acc_id')
        self.view.widgets.acc_id_entry.connect('insert-text', 
                                               self.on_acc_id_entry_insert)
        self.view.widgets.acc_id_entry.connect('delete-text', 
                                               self.on_acc_id_entry_delete)
        self.assign_simple_handler('acc_notes_textview', 'notes')
        
        acc_date_entry = self.view.widgets.acc_date_entry
        acc_date_entry.connect('insert-text', self.on_acc_date_entry_insert)
        acc_date_entry.connect('delete-text', self.on_acc_date_entry_delete)
        
        self.init_change_notifier()
    
    
    def on_acc_id_entry_insert(self, entry, new_text, new_text_length, position, 
                            data=None):
        entry_text = entry.get_text()                
        cursor = entry.get_position()
        full_text = entry_text[:cursor] + new_text + entry_text[cursor:]
        self._set_acc_id_from_text(full_text)

        
    def on_acc_id_entry_delete(self, entry, start, end, data=None):
        text = entry.get_text()
        full_text = text[:start] + text[end:]
        self._set_acc_id_from_text(full_text)
                
        
    def _set_acc_id_from_text(self, text):
        sr = Accession.selectBy(acc_id=text)
        if sr.count() > 0:
            self.add_problem(self.PROBLEM_DUPLICATE_ACCESSION,
                             self.view.widgets.acc_id_entry)
            self.model.acc_id = None            
            return
        
        self.remove_problem(self.PROBLEM_DUPLICATE_ACCESSION,
                            self.view.widgets.acc_id_entry)
        self.model.acc_id = text
            
        
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
        
        
    # the previous value that was in the species entry, this is for a 
    # workaround for how entry completion works
    prev_species_text = ''
        
    def on_species_match_selected(self, completion, compl_model, iter):
        '''
        put the selected value in the model
        '''                
        species = compl_model[iter][0]
#        debug('selected: %s' % str(species))
        entry = self.view.widgets.species_entry
        entry.handler_block(self.insert_species_sid)
        entry.set_text(str(species))
        entry.handler_unblock(self.insert_species_sid)
        entry.set_position(-1)
        self.remove_problem(self.PROBLEM_INVALID_SPECIES, 
                            self.view.widgets.species_entry)
        self.model.species = species
#        debug('%s' % self.model)
        self.prev_text = str(species)


    def on_species_entry_delete(self, entry, start, end, data=None):
#        debug('on_species_delete: \'%s\'' % entry.get_text())        
#        debug(self.model.species)
        text = entry.get_text()
        full_text = text[:start] + text[end:]
        if full_text == '' or (full_text == str(self.model.species)):
            return
        self.add_problem(self.PROBLEM_INVALID_SPECIES, 
                         self.view.widgets.species_entry)
        self.model.species = None
        
    
    def on_species_entry_insert(self, entry, new_text, new_text_length, position, 
                       data=None):
        # TODO: this is flawed since we can't get the index into the entry
        # where the text is being inserted so if the user inserts text into 
        # the middle of the string then this could break
#        debug('on_species_insert_text: \'%s\'' % new_text)
#        debug('%s' % self.model)
        if new_text == '':
            # this is to workaround the problem of having a second 
            # insert-text signal called with new_text = '' when there is a 
            # custom renderer on the entry completion for this entry
            # block the signal from here since it will call this same
            # method again and resetting the species completions            
            entry.handler_block(self.insert_species_sid)
            entry.set_text(self.prev_text)
            entry.handler_unblock(self.insert_species_sid)
            return False # is this 'False' necessary, does it do anything?
            
        entry_text = entry.get_text()                
        cursor = entry.get_position()
        full_text = entry_text[:cursor] + new_text + entry_text[cursor:]
        # this funny logic is so that completions are reset if the user
        # paste multiple characters in the entry    
        if len(new_text) == 1 and len(full_text) == 2:
            self.idle_add_species_completions(full_text)
        elif new_text_length > 2:# and entry_text != '':
            self.idle_add_species_completions(full_text[:2])
        self.prev_text = full_text
        
        if full_text != str(self.model.species):
            self.add_problem(self.PROBLEM_INVALID_SPECIES, 
                             self.view.widgets.species_entry)
            self.model.species = None
#        debug('%s' % self.model)
            
            
    def init_species_entry(self):
        completion = self.view.widgets.species_entry.get_completion()
        completion.connect('match-selected', self.on_species_match_selected)
        if self.model.species is not None:
            genus = self.model['species'].genus
            self.idle_add_species_completions(str(genus)[:2])
        
        
    def idle_add_species_completions(self, text):
#        debug('idle_add_species_competions: %s' % text)
        parts = text.split(" ")
        genus = parts[0]
        like_genus = sqlhub.processConnection.sqlrepr(_LikeQuoted('%s%%' % genus))
        sr = tables["Genus"].select('genus LIKE %s' % like_genus)
        def _add_completion_callback(select):
            n_gen = sr.count()
            n_sp = 0
            model = gtk.ListStore(object)
            for row in sr:    
                if len(row.species) == 0: # give a bit of a speed up
                    continue
                n_sp += len(row.species)
                for species in row.species:                
                    model.append([species])
            completion = self.view.widgets.species_entry.get_completion()
            completion.set_model(model)
        gobject.idle_add(_add_completion_callback, sr)
        
    
    def on_field_changed(self, field):
        #debug('on field changed: %s = %s' % (field, self.model[field]))
#        debug('on field changed: %s' % field)
#        debug(self.problems)        
        # TODO: we could have problems here if we are monitoring more than
        # one model change and the two models have a field with the same name,
        # e.g. date, then if we do 'if date == something' we won't know
        # which model changed
        prov_sensitive = True                    
        wild_prov_combo = self.view.widgets.wild_prov_combo
        if field == 'prov_type':
            if self.model.prov_type in ['Wild']:
                self.model.wild_prov_status = wild_prov_combo.get_active_text()
            else:
                # remove the value in the model from the wild_prov_combo                
                prov_sensitive = False
                self.model.wild_prov_status = None
        wild_prov_combo.set_sensitive(prov_sensitive)
        self.view.widgets.wild_prov_label.set_sensitive(prov_sensitive)
        
        if field == 'longitude' or field == 'latitude':
            source_model = self.source_presenter.model
            if source_model.latitude is not None and source_model.longitude is not None:
                self.view.widgets.geoacc_entry.set_sensitive(True)
            else:
                self.view.widgets.geoacc_entry.set_sensitive(False)
            
        if field == 'elevation':
            if self.source_presenter.model.elevation is not None:            
                self.view.widgets.altacc_entry.set_sensitive(True)
            else: 
                self.view.widgets.altacc_entry.set_sensitive(False)
                
        sensitive = True
        if len(self.problems) != 0:
            sensitive = False
        elif self.source_presenter is not None:
            if len(self.source_presenter.problems) != 0:
                sensitive = False
        self.view.widgets.acc_ok_button.set_sensitive(sensitive)
        self.view.widgets.acc_ok_and_add_button.set_sensitive(sensitive)
        self.view.widgets.acc_next_button.set_sensitive(sensitive)
            
    
    def init_change_notifier(self):
        '''
        for each widget register a signal handler to be notified when the
        value in the widget changes, that way we can w things like sensitize
        the ok button
        '''
        for widget, field in self.widget_to_field_map.iteritems():            
            w = self.view.widgets[widget]
            self.model.add_notifier(field, self.on_field_changed)
        
    
    def on_source_type_combo_changed(self, combo, data=None):
        '''
        change which one of donation_box/collection_box is packed into
        source box and setup the appropriate presenter
        '''
        source_type = combo.get_active_text()
        box = None
        # FIXME: Donation and Collection shouldn't be hardcoded so that it 
        # can be translated
        source = None
        source_model = None
        if source_type is not None:
            if self.model.isinstance:
                source = get_source(self.model.so_object)
                if source is not None and source.__class__.__name__ == source_type:
                    source_model = SQLObjectProxy(source)
            if source_model is None:
                source_model = SQLObjectProxy(tables[source_type])
            
        
        box_map = {'Donation': 'donation_box', 'Collection': 'collection_box'}

        def remove_parent(widget):
            p = widget.get_parent()
            if p is not None:
                p.remove(widget)
                                
        # replace source box contents with our new box
        source_box = self.view.widgets.source_box
        if self.current_source_box is not None:
#            debug(self.current_source_box)
            remove_parent(self.current_source_box)
        if source_type is not None:
#            debug(source_type)
            self.current_source_box = self.view.widgets[box_map[source_type]]
            # FIXME: there seems to be a bug here if you change to source type 
            # too many times or too fast then self.current.source_box can 
            # be None
#            debug(self.current_source_box)
            remove_parent(self.current_source_box)
            source_box.pack_start(self.current_source_box, expand=False, 
                                  fill=True)
        else:
            self.current_source_box = None
        
        if source_model is not None:
            self.source_presenter = SourcePresenterFactory.\
                createSourcePresenter(source_type, source_model, self.view,
                                      self.defaults)
            # initialize model change notifiers    
            for field in self.source_presenter.widget_to_field_map.values():
                self.source_presenter.model.add_notifier(field, 
                                                         self.on_field_changed)
        self.model.source_type = source_type
        source_box.show_all()
        
        
    def init_source_expander(self):        
        '''
        initialized the source expander contents
        '''
        combo = self.view.widgets.source_type_combo
        model = gtk.ListStore(str)        
        model.append(['Collection'])
        model.append(['Donation'])
        model.append([None])
        combo.set_model(model)
        combo.set_active(-1)
        self.view.widgets.source_type_combo.connect('changed', 
                                            self.on_source_type_combo_changed)            
#        self.view.dialog.show_all()
        
    
    def init_prov_combo(self):
        combo = self.view.widgets.prov_combo
        model = gtk.ListStore(str)
        for enum in self.model.columns['prov_type'].enumValues:
            model.append([enum])
        combo.set_model(model)        
    
    
    def init_wild_prov_combo(self):
        # TODO: the wild_prov_combo should only be set sensitive if
        # prov_type == 'Wild' or maybe 'Propagule of wild cultivated plant'
        combo = self.view.widgets.wild_prov_combo        
        model = gtk.ListStore(str)
        for enum in self.model.columns['wild_prov_status'].enumValues:
            model.append([enum])
        combo.set_model(model)        


    def on_combo_changed(self, combo, field):
        self.model[field] = combo.get_active_text()


    def refresh_view(self):
        '''
        get the values from the model and put them in the view
        '''
        for widget, field in self.widget_to_field_map.iteritems():            
            if field[-2:] == "ID":
                field = field[:-2]
            value = self.model[field]
#            debug('%s, %s, %s' % (widget, field, value))
#            debug('default: %s' % self.defaults.get(field, None))
            if value is not None and field == 'date':
                value = '%s/%s/%s' % (value.day, value.month, value.year)
            self.view.set_widget_value(widget, value, 
                                       default=self.defaults.get(field, None))
            
        if self.model.prov_type in ['Wild']:
            self.view.widgets.wild_prov_combo.set_sensitive(True)
            self.view.widgets.wild_prov_label.set_sensitive(True)
        else:
            self.view.widgets.wild_prov_combo.set_sensitive(False)
            self.view.widgets.wild_prov_label.set_sensitive(False)

                
    def start(self):
        return self.view.start()
        
        

class AccessionEditor(GenericModelViewPresenterEditor):
    
    label = 'Accessions'
    
    # these have to correspond to the response values in the view
    RESPONSE_OK_AND_ADD = 11
    RESPONSE_NEXT = 22
    ok_responses = (RESPONSE_OK_AND_ADD, RESPONSE_NEXT)    
        
    # TODO: the kwargs is really only here to support the old editor 
    # constructor
    def __init__(self, model=Accession, defaults={}, parent=None, **kwargs):
        '''
        model: either an Accession class or instance
        defaults: a dictionary of Accession field name keys with default
        values to enter in the model if none are give
        '''
        self.assert_args(model, Accession, defaults)
        GenericModelViewPresenterEditor.__init__(self, model, defaults, parent)
        if parent is None: # should we even allow a change in parent
            parent = bauble.app.gui.window
        # keep parent and defaults around in case in start() we get
        # RESPONSE_NEXT or RESPONSE_OK_AND_ADD we can pass them to the new 
        # editor
        self.parent = parent
        self.defaults = defaults 
        self.view = AccessionEditorView(parent=parent)
        self.presenter = AccessionEditorPresenter(self.model, self.view,
                                                  self.defaults)


    def handle_response(self, response):
        '''
        handle the response from self.presenter.start() in self.start()
        '''
        # TODO: use this method to factor out some of the code from self.start
        pass
    
    
    def start(self, commit_transaction=True):    
        not_ok_msg = 'Are you sure you want to lose your changes?'
        exc_msg = "Could not commit changes.\n"
        committed = None
        while True:
            response = self.presenter.start()
            self.view.save_state() # should view or presenter save state
            source_dirty = self.presenter.source_presenter is not None and \
                self.presenter.source_presenter.model.dirty
            if response == gtk.RESPONSE_OK or response in self.ok_responses:
                try:
                    committed = self.commit_changes()                
                except DontCommitException:
                    continue
                except BadValue, e:
                    utils.message_dialog(saxutils.escape(str(e)),
                                         gtk.MESSAGE_ERROR)
                except CommitException, e:
                    debug(traceback.format_exc())
                    exc_msg + ' \n %s\n%s' % (str(e), e.row)
                    utils.message_details_dialog(saxutils.escape(exc_msg), 
                                 traceback.format_exc(), gtk.MESSAGE_ERROR)
                    sqlhub.processConnection.rollback()
                    sqlhub.processConnection.begin()
                except Exception, e:
                    debug(traceback.format_exc())
                    exc_msg + ' \n %s' % str(e)
                    utils.message_details_dialog(saxutils.escape(exc_msg), 
                                                 traceback.format_exc(),
                                                 gtk.MESSAGE_ERROR)
                    sqlhub.processConnection.rollback()
                    sqlhub.processConnection.begin()
                else:
                    break
            elif (self.model.dirty or source_dirty) and utils.yes_no_dialog(not_ok_msg):
                self.model.dirty = False
                break
            elif not (self.model.dirty or source_dirty):
                break
            
        if commit_transaction:
            sqlhub.processConnection.commit()

        # TODO: if we could get the response from the view
        # then we could just call GenericModelViewPresenterEditor.start()
        # and then add this code but GenericModelViewPresenterEditor doesn't
        # know anything about it's presenter though maybe it should
        more_committed = None
        if response == self.RESPONSE_NEXT:
            if self.model.isinstance:
                model = self.model.so_object.__class__
            else:
                model = self.model.so_object
            e = AccessionEditor(model, self.defaults, self.parent)
            more_committed = e.start(commit_transaction)
        elif response == self.RESPONSE_OK_AND_ADD:
            # TODO: when the plant editor gets it's own glade implementation
            # we should change accessionID to accession
            e = editors['PlantEditor'](parent=self.parent, 
                                       defaults={'accessionID': committed})
            more_committed = e.start(commit_transaction)            
                    
        if more_committed is not None:
            committed = [committed]
            if isinstance(more_committed, list):
                committed.extend(more_committed)
            else:
                committed.append(more_committed)
                
        return committed
    
    
    def commit_source_changes(self, accession):
        source_model = None
        if self.presenter.source_presenter is not None \
          and self.presenter.source_presenter.model.dirty:
            source_model = self.presenter.source_presenter.model
            if source_model.isinstance:
                source_table = tables[source_model.so_object.__class__.__name__]
            else:
                source_table = tables[source_model.so_object.__name__]
                
        if source_model is None:
            return
        
        if 'latitude' in source_model or 'longitude' in source_model:
            if (source_model.latitude is not None and source_model.longitude is None) or \
                (source_model.longitude is not None and source_model.latitude is None):
                msg = 'model must have both latitude and longitude or neither'
                raise ValueError(msg)
            elif source_model.latitude is None and source_model.longitude is None:
                source_model.geo_accy = None # don't save 
        else:
            source_model.geo_accy = None # don't save 
                
#        if 'latitude' in source_model and source_model.latitude is not None:
#            if 'longitude' in source_model and source_model.longitude is None:
#                msg = 'model must have both latitude and longitude or neither'
#                raise ValueError(msg)
#            else:
#                source_model.geo_accy = None # don't save 
#        else:
#                source_model.geo_accy = None
            
        # reset the elevation accuracy if the elevation is None
        if 'elevation' in source_model and source_model.elevation is None:
            source_model.elevation_accy = None
            
        source_model['accession'] = accession.id
        new_source = commit_to_table(source_table, source_model)
        
        
    def commit_changes(self):
#        debug('commit_changes: %s' % self.model)
        # if source_type changes and the original source type wasn't none
        # warn the user
        if self.model.isinstance:
            orig_source_type = self.model.so_object.source_type
            if orig_source_type is not None \
              and self.model.source_type != orig_source_type:
                msg = 'You are about to change the type of the accession\'s '\
                       'source data. All previous source data will be '\
                       'deleted. Are you sure this is what you want to do?'
                if utils.yes_no_dialog(msg):
                    # change source, destroying old one
                    source = get_source(self.model.so_object)
                    if source is not None:
                        source.destroySelf()    
                else:
                    raise DontCommitException
                
        accession = None        
        if self.model.dirty:
            accession = self._commit(self.model)
        elif self.presenter.source_presenter is not None \
          and self.presenter.source_presenter.model.dirty \
          and not self.model.dirty:
            if self.model.isinstance:
                accession = self.model.so_object
            else: # commit it anyway to make sure error get thrown
                accession = self._commit(self.model)
        
        # reset self.model and self.presenter.model in case 
        # commit_source_changes fails we won't commit the same accession again
        #self.model = SQLObject(accession)
        new_model = SQLObjectProxy(accession)
        self.model = new_model
        self.presenter.model = new_model
        self.commit_source_changes(accession)
        return accession
    
    
       
#
# infobox for searchview
#
try:
    import os
    import bauble.paths as paths
    from bauble.plugins.searchview.infobox import InfoBox, InfoExpander
except ImportError:
    pass
else:
    # TODO: i don't think this shows all field of an accession, like the 
    # accuracy values
    class GeneralAccessionExpander(InfoExpander):
        """
        generic information about an accession like
        number of clones, provenance type, wild provenance type, speciess
        """
    
        def __init__(self, glade_xml):
            InfoExpander.__init__(self, "General", glade_xml)
            general_window = self.glade_xml.get_widget('general_window')
            w = self.glade_xml.get_widget('general_box')
            general_window.remove(w)
            self.vbox.pack_start(w)
        
        
        def update(self, row):
            utils.set_widget_value(self.glade_xml, 'name_data', 
			     row.species.markup(True))
            utils.set_widget_value(self.glade_xml, 'nplants_data', len(row.plants))
            utils.set_widget_value(self.glade_xml, 'prov_data',row.prov_type, False)
            
            
    class NotesExpander(InfoExpander):
        """
        the accession's notes
        """
    
        def __init__(self, glade_xml):
            InfoExpander.__init__(self, "Notes", glade_xml)
            notes_window = self.glade_xml.get_widget('notes_window')
            w = self.glade_xml.get_widget('notes_box')
            notes_window.remove(w)
            self.vbox.pack_start(w)
        
        
        def update(self, row):
            utils.set_widget_value(self.glade_xml, 'notes_data', row.notes)            
    
    
    class SourceExpander(InfoExpander):
        
        def __init__(self, glade_xml):
            InfoExpander.__init__(self, 'Source', glade_xml)
            self.curr_box = None
        
        
        def update_collections(self, collection):
            
            utils.set_widget_value(self.glade_xml, 'loc_data', collection.locale)
            
            geo_accy = collection.geo_accy
            if geo_accy is None:
                geo_accy = ''
            else: 
                geo_accy = '(+/- %sm)' % geo_accy
            
            if collection.latitude is not None:
                dir, deg, min, sec = latitude_to_dms(collection.latitude)
                s = '%.2f (%s %s\302\260%s"%.3f\') %s' % \
                    (collection.latitude, dir, deg, min, sec, geo_accy)
                utils.set_widget_value(self.glade_xml, 'lat_data', s)

            if collection.longitude is not None:
                dir, deg, min, sec = longitude_to_dms(collection.longitude)
                s = '%.2f (%s %s\302\260%s"%.3f\') %s' % \
                    (collection.longitude, dir, deg, min, sec, geo_accy)
                utils.set_widget_value(self.glade_xml, 'lon_data', s)                                
            
            v = collection.elevation

            if collection.elevation_accy is not None:
                v = '%s (+/- %sm)' % (v, collection.elevation_accy)
            utils.set_widget_value(self.glade_xml, 'elev_data', v)
            
            utils.set_widget_value(self.glade_xml, 'coll_data', collection.collector)
            utils.set_widget_value(self.glade_xml, 'date_data', collection.coll_date)
            utils.set_widget_value(self.glade_xml, 'collid_data', collection.coll_id)
            utils.set_widget_value(self.glade_xml,'habitat_data', collection.habitat)
            utils.set_widget_value(self.glade_xml,'collnotes_data', collection.notes)
            
                
        def update_donations(self, donation):
            utils.set_widget_value(self.glade_xml, 'donor_data', 
                             tables['Donor'].get(donation.donorID).name)
            utils.set_widget_value(self.glade_xml, 'donid_data', donation.donor_acc)
            utils.set_widget_value(self.glade_xml, 'donnotes_data', donation.notes)
        
        
        def update(self, value):        
            if self.curr_box is not None:
                self.vbox.remove(self.curr_box)
                    
            #assert value is not None
            if value is None:
                return
            
            if isinstance(value, tables["Collection"]):
                coll_window = self.glade_xml.get_widget('collections_window')
                w = self.glade_xml.get_widget('collections_box')
                coll_window.remove(w)
                self.curr_box = w
                self.update_collections(value)        
            elif isinstance(value, tables["Donation"]):
                don_window = self.glade_xml.get_widget('donations_window')
                w = self.glade_xml.get_widget('donations_box')
                don_window.remove(w)
                self.curr_box = w
                self.update_donations(value)            
            else:
                msg = "Unknown type for source: " + str(type(value))
                utils.message_dialog(msg, gtk.MESSAGE_ERROR)
            
            #if self.curr_box is not None:
            self.vbox.pack_start(self.curr_box)
            #self.set_expanded(False) # i think the infobox overrides this
            #self.set_sensitive(False)
            
    
    class AccessionInfoBox(InfoBox):
        """
        - general info
        - source
        """
        def __init__(self):
            InfoBox.__init__(self)
            path = os.path.join(paths.lib_dir(), "plugins", "garden")
            self.glade_xml = gtk.glade.XML(path + os.sep + "acc_infobox.glade")
            
            self.general = GeneralAccessionExpander(self.glade_xml)
            self.add_expander(self.general)
            
            self.source = SourceExpander(self.glade_xml)
            self.add_expander(self.source)
            
            self.notes = NotesExpander(self.glade_xml)
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
            if row.source_type == None:
                self.source.set_expanded(False)
                self.source.set_sensitive(False)
            elif row.source_type == 'Collection':
                self.source.set_expanded(True)
                self.source.update(row._collection)
            elif row.source_type == 'Donation':
                self.source.set_expanded(True)
                self.source.update(row._donation)
