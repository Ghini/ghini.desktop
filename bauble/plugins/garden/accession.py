#
# accessions module
#

import os, traceback, math
from datetime import datetime
import xml.sax.saxutils as saxutils
import gtk
import gobject
from sqlobject import * 
from sqlobject.constraints import BadValue, notNull
from sqlobject.sqlbuilder import _LikeQuoted
import bauble
import bauble.utils as utils
import bauble.paths as paths
from bauble.plugins import BaubleTable, tables, editors
from bauble.editor import *
#from bauble.editor import TableEditor, SQLObjectProxy, commit_to_table, \
#    check_constraints, GenericModelViewPresenterEditor, \
#    GenericEditorPresenter, GenericEditorView, DontCommitException
from bauble.utils.log import debug
from bauble.prefs import prefs
from bauble.error import CommitException


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
    #dec = (sec/3600.0) + (min/60.0) + deg
    dec = (float(sec)/3600.0) + (float(min)/60.0) + float(deg)
    if dir in ('W', 'S'):
        dec = -dec
    ROUND_TO = 5
    return round(dec, ROUND_TO)
    
        
def decimal_to_dms(decimal, long_or_lat):
    '''
    long_or_lat: should be either "long" or "lat"
    
    returns dir, degrees, minutes seconds
    seconds rounded to two decimal points
    '''
    
    dir_map = { 'long': ['E', 'W'],
                'lat':  ['N', 'S']}
    dir = dir_map[long_or_lat][0]
    if decimal < 0:
        dir = dir_map[long_or_lat][1]
    
    dec = abs(decimal)
    d = int(dec)
    m = abs((dec-d)*60)        
    s = abs((int(m)-m) * 60)    
    ROUND_TO=2
    return dir, int(d), int(m), round(s,ROUND_TO)

class Accession(BaubleTable):

    class sqlmeta(BaubleTable.sqlmeta):
	       defaultOrder = 'acc_id'

    values = {} # dictionary of values to restrict to columns
    acc_id = StringCol(length=20, notNull=True, alternateID=True)
    
    
    prov_type = EnumCol(enumValues=("Wild", # Wild,
                                    "Propagule of cultivated wild plant", # Propagule of wild plant in cultivation
                                    "Not of wild source", # Not of wild source
                                    "Insufficient Data", # Insufficient data
                                    "Unknown",
                                    "<not set>"),
                        default = "<not set>")

    # wild provenance status, wild native, wild non-native, cultivated native
    wild_prov_status = EnumCol(enumValues=("Wild native", # Endemic found within it indigineous range
                                           "Wild non-native", # Propagule of wild plant in cultivation
                                           "Cultivated native", # Not of wild source
                                           "Insufficient Data", # Insufficient data
                                           "Unknown",
                                           "<not set>"),
                               default="<not set>")
    
    #TODO: need to provide a date field for when the accession was accessioned
    #acc_date = DateCol())
    
    
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
    
    # foreign keys and joins
    species = ForeignKey('Species', notNull=True, cascade=False)
    plants = MultipleJoin("Plant", joinColumn='accession_id')
    
    # these should probably be hidden then we can do some trickery
    # in the accession editor to choose where a collection or donation
    # source, the source will contain one of collection or donation
    # tables
    # 
    # holds the string 'Collection' or 'Donation' which indicates where
    # we should get the source information from either of those columns
    # TODO: it seems like it would make more sense just to make this and
    # EnumCol(enumValues='Collection, Donation') since that's essentially
    # what it is anyways
    # should also allow None values so that we can effectively delete the 
    # source information though we have to be careful we don't mess anything
    # up here
    #source_type = StringCol(length=64, default=None)    
    source_type = EnumCol(enumValues=('Collection', 'Donation', None),
                          default=None)
                            
    # the source type says whether we should be looking at the 
    # _collection or _donation joins for the source info
    #_collection = SingleJoin('Collection', joinColumn='accession_id', makeDefault=None)
    _collection = SingleJoin('Collection', joinColumn='accession_id')
    _donation = SingleJoin('Donation', joinColumn='accession_id', makeDefault=None)
        
    notes = UnicodeCol(default=None)
    
    # these probably belong in separate tables with a single join
    #cultv_info = StringCol(default=None)      # cultivation information
    #prop_info = StringCol(default=None)       # propogation information
    #acc_uses = StringCol(default=None)        # accessions uses, why diff than taxon uses?
    
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
#        r = gtk.CellRendererText() # set up the completion renderer
#        completion.pack_start(r)
#        completion.set_cell_data_func(r, self.name_cell_data_func)        
        completion.set_text_column(0)    
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
    
        
#    def name_cell_data_func(self, column, renderer, model, iter, data=None):
#        '''
#        render the values in the completion popup model
#        '''
#        #species = model.get_value(iter, 0)        
#        value = model[iter][0]
#        renderer.set_property('text', str(value))
        

class Problems:
        
        _problems = []
        
        def add(self, problem):
            self._problems.append(problem)
            
        def remove(self, problem):
            # TODO: nothing happens if problem does not exist in self.problems
            # should we ignore it or do..
            # if problem not in self.problems
            #   raise KeyError()
            while 1:
                try:
                    self._problems.remove(problem)
                except:
                    break
            
        def __len__(self):
            return len(self._problems)
            
        def __str__(self):
            return str(self._problems)

# TODO: should have a label next to lat/lon entry to show what value will be 
# stored in the database, might be good to include both DMS and the float
# so the user can see both no matter what is in the entry. it could change in
# time as the user enters data in the entry
# TODO: shouldn't allow entering altitude accuracy without entering accuracy,
# same for geographic accuracy
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
                           'habitat_entry': 'habitat',
                           'notes_entry': 'notes'}
    
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
        self.problems = Problems()
        
        self.assign_simple_handler('collector_entry', 'collector')
        self.assign_simple_handler('locale_entry', 'locale')
        self.assign_simple_handler('coll_date_entry', 'coll_date')
        self.assign_simple_handler('collid_entry', 'coll_id')
        self.assign_simple_handler('geoacc_entry', 'geo_accy',
                                   self._get_column_validator('geo_accy'))
        self.assign_simple_handler('alt_entry', 'elevation', 
                                   self._get_column_validator('elevation'))
        self.assign_simple_handler('altacc_entry', 'elevation_accy',
                                   self._get_column_validator('elevation'))
        self.assign_simple_handler('habitat_entry', 'habitat')
        self.assign_simple_handler('notes_entry', 'notes')
        
        lat_entry = self.view.widgets.lat_entry
        lat_entry.connect('insert-text', self.on_lat_entry_insert)
        lat_entry.connect('delete-text', self.on_lat_entry_delete)
        
        lon_entry = self.view.widgets.lon_entry
        lon_entry.connect('insert-text', self.on_lon_entry_insert)
        lon_entry.connect('delete-text', self.on_lon_entry_delete)
        
        coll_date_entry = self.view.widgets.coll_date_entry
        coll_date_entry.connect('insert-text', self.on_date_entry_insert)
        coll_date_entry.connect('delete-text', self.on_date_entry_delete)

        # TODO: maybe i should only be checking on one of these since they
        # have to one or the other, it works with both connected since
        # the one being untoggled is called first and the one be toggled
        # on is called last
        north_radio = self.view.widgets.north_radio
        north_radio.connect('toggled', self.on_north_south_radio_toggled)
        south_radio = self.view.widgets.north_radio
        south_radio.connect('toggled', self.on_north_south_radio_toggled)
        
        east_radio = self.view.widgets.east_radio
        east_radio.connect('toggled', self.on_east_west_radio_toggled)
        west_radio = self.view.widgets.west_radio
        west_radio.connect('toggled', self.on_east_west_radio_toggled)


    def refresh_view(self):
        for widget, field in self.widget_to_field_map.iteritems():
            if field[-2:] == "ID":
                field = field[:-2]
            self.view.set_widget_value(widget, self.model[field],
                                       self.defaults.get(field, None))         
            
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
        bg_color = None
        m = self._date_regex.match(text)
        dt = None # datetime
        if m is None:
            self.problems.add(self.PROBLEM_INVALID_DATE)            
            bg_color = gtk.gdk.color_parse("red")
        else:
#            debug('%s.%s.%s' % (m.group('year'), m.group('month'), \
#                                    m.group('day')))
            try:
                ymd = [int(x) for x in [m.group('year'), m.group('month'), \
                                        m.group('day')]]            
                dt = datetime(*ymd)            
                self.problems.remove(self.PROBLEM_INVALID_DATE)
            except:
                self.problems.add(self.PROBLEM_INVALID_DATE)
                
        self.model.coll_date = dt
        e = self.view.widgets.coll_date_eventbox
        e.modify_bg(gtk.STATE_NORMAL, bg_color)
        e.queue_draw()
        

    def on_north_south_radio_toggled(self, button, data=None):
        direction = self._get_lon_direction()
        lon_text = self.view.widgets.lon_entry.get_text()
        if lon_text != '':
            self._set_longitude_from_text(lon_text)
        
        
    def on_east_west_radio_toggled(self, button, data=None):
        direction = self._get_lat_direction()
        lat_text = self.view.widgets.lat_entry.get_text()
        if lat_text != '':
            self._set_latitude_from_text(lat_text)
    

    # TODO: need to write a test for this method
    # TODO: still need to support degrees minutes seconds,
    # decimal degrees, and degrees with decimal minutes
    @staticmethod
    def _parse_lat_lon(direction, text):
        bits = re.split(':| ', text)
#        debug('%s: %s' % (direction, bits))
        if len(bits) == 3:
            dec = dms_to_decimal(dir, *map(float, bits))
        else:
            try:
                dec = abs(float(text))
                if dec > 0 and direction in ('W', 'S'):
                    dec = -dec
            except:
                # TODO: or parse error? does it matter?
                raise ValueError('_parse_lat_lon -- incorrect format: %s' % \
                                 text)
        return dec


    def _get_lon_direction(self):
        if self.view.widgets.north_radio.get_active():
            return 'N'
        elif self.view.widgets.south_radio.get_active():
            return 'S'
        raise ValueError('North/South radio buttons in a confused state')
            
            
    def _get_lat_direction(self):
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
        bg_color = None
        longitude = None
        try:
            if text != '' and text is not None:
                direction = self._get_lat_direction()
                latitude = CollectionPresenter._parse_lat_lon(direction, text)
        except:         
            bg_color = gtk.gdk.color_parse("red")
            self.problems.add(self.PROBLEM_BAD_LATITUDE)
            self.model['latitude'] = None
        else:
            self.problems.remove(self.PROBLEM_BAD_LATITUDE)
            self.model['latitude'] = latitude            
                
        e = self.view.widgets.lat_event_box    
        e.modify_bg(gtk.STATE_NORMAL, bg_color)
        e.queue_draw()
        
        
    def on_lon_entry_insert(self, entry, new_text, new_text_length, position, 
                            data=None):
#        e = self.view.widgets.lon_event_box
#        e.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("red"))
        entry_text = entry.get_text()                
        cursor = entry.get_position()
        full_text = entry_text[:cursor] + new_text + entry_text[cursor:]
        self._set_longitude_from_text(full_text)
 
 
    def on_lon_entry_delete(self, entry, start, end, data=None):
        text = entry.get_text()
        full_text = text[:start] + text[end:]
        self._set_longitude_from_text(full_text)


    def _set_longitude_from_text(self, text):
        bg_color = None
        longitude = None
        try:
            if text != '' and text is not None:
                direction = self._get_lon_direction()
                longitude = CollectionPresenter._parse_lat_lon(direction, text)            
        except:
            bg_color = gtk.gdk.color_parse("red")            
            self.problems.add(self.PROBLEM_BAD_LONGITUDE)
            # set the model so that the ok buttons will be reset
            #self.model['longitude'] = None 
        else:
            self.problems.remove(self.PROBLEM_BAD_LONGITUDE)
            #self.model['longitude'] = longitude            
            
        self.model['longitude'] = longitude
        e = self.view.widgets.lon_event_box    
        e.modify_bg(gtk.STATE_NORMAL, bg_color)
        e.queue_draw()
    
    
    
    
class DonationPresenter(GenericEditorPresenter):
    
    widget_to_field_map = {'donor_combo': 'donor',
                           'donid_entry': 'donor_acc',
                           'donnotes_entry': 'notes'}    
    
    
    def __init__(self, model, view, defaults={}):
        GenericEditorPresenter.__init__(self, model, view)        
        self.defaults = defaults        
        self.problems = Problems()
        donor_combo = self.view.widgets.donor_combo
        donor_combo.connect('changed', self.on_donor_combo_changed)
        r = gtk.CellRendererText()            
        donor_combo.pack_start(r)
        donor_combo.set_cell_data_func(r, self.combo_cell_data_func)
       
        self.refresh_view()        
        self.assign_simple_handler('donid_entry', 'donor_acc')
        self.assign_simple_handler('donnotes_entry', 'notes')
        self.assign_simple_handler('donor_combo', 'donor')
        self.view.widgets.don_new_button.connect('clicked', 
                                                 self.on_don_new_clicked)
        self.view.widgets.don_edit_button.connect('clicked',
                                                  self.on_don_edit_clicked)
        
        
        
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
        self.view.widgets.donor_combo.set_model(model)
        
        if len(model) == 1: # only one to choose from
            donor_combo.set_active(0)    
        
        # TODO: what if there is a donor id in the source but the donor
        # doesn't exist        
        for widget, field in self.widget_to_field_map.iteritems():
            if field[-2:] == "ID":
                field = field[:-2]
#            debug("%s: %s = %s" % (widget, field, self.model[field]))
            default = self.defaults.get(field, None)
            self.view.set_widget_value(widget, self.model[field], default)
        


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
    
    def __init__(self, model, view, defaults={}):
        '''
        model: should be an instance of class Accession
        view: should be an instance of AccessionEditorView
        '''
        GenericEditorPresenter.__init__(self, model, view)
        self.defaults = defaults
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
        self.view.widgets.species_entry.connect('insert-text', 
                                                self.on_insert_text, 'species')
        self.view.widgets.prov_combo.connect('changed', self.on_combo_changed, 
                                             'prov_type')
        self.view.widgets.wild_prov_combo.connect('changed', 
                                                  self.on_combo_changed,
                                                  'wild_prov_status')
        self.assign_simple_handler('acc_id_entry', 'acc_id')
        self.assign_simple_handler('notes_textview', 'notes')
        self.init_change_notifier()
    
        
    def on_species_match_selected(self, completion, compl_model, iter):
        '''
        put the selected value in the model
        '''                
        # TODO: i would rather just put the object in the column and get
        # the id from that but there is that funny bug when using custom 
        # renderers for a gtk.EntryCompletion, the only downside with this
        # is calling Species.str() over and over from cell_data_func, but 
        # would these get cached?
        
        # column 0 holds the name of the plant while column 1 holds the id         
        name = compl_model[iter][0]
        entry = self.view.widgets.species_entry
        entry.set_text(str(name))
        entry.set_position(-1)
        self.model.species = compl_model[iter][1]


    def on_insert_text(self, entry, new_text, new_text_length, position, 
                       data=None):
        # TODO: this is flawed since we can't get the index into the entry
        # where the text is being inserted so if the user inserts text into 
        # the middle of the string then this could break
        entry_text = entry.get_text()                
        cursor = entry.get_position()
        full_text = entry_text[:cursor] + new_text + entry_text[cursor:]
        # this funny logic is so that completions are reset if the user
        # paste multiple characters in the entry    
        if len(new_text) == 1 and len(full_text) == 2:
            self.idle_add_species_completions(full_text)
        elif new_text_length > 2:# and entry_text != '':
            self.idle_add_species_completions(full_text[:2])
            
            
    def init_species_entry(self):
        completion = self.view.widgets.species_entry.get_completion()
        completion.connect('match-selected', self.on_species_match_selected)
        if self.model.isinstance:
#            debug(self.model['species'].genus)
            genus = self.model['species'].genus
            self.idle_add_species_completions(str(genus)[:2])
        
        
    def idle_add_species_completions(self, text):
#        debug('idle_add_competions')
        parts = text.split(" ")
        genus = parts[0]
        like_genus = sqlhub.processConnection.sqlrepr(_LikeQuoted('%s%%' % genus))
        sr = tables["Genus"].select('genus LIKE %s' % like_genus)
        #debug(like_genus)        
        def _add_completion_callback(select):
            #self.view.widgets.accession_dialog.set_sensitive(False)
            n_gen = sr.count()
            n_sp = 0
            model = gtk.ListStore(str, int)
            for row in sr:    
                if len(row.species) == 0: # give a bit of a speed up
                    continue
                n_sp += len(row.species)
                for species in row.species:                
                    model.append([str(species), species.id])
#            debug('%s species in %s genera' % (n_sp, n_gen))
            completion = self.view.widgets.species_entry.get_completion()
            completion.set_model(model)
            #self.view.widgets.accession_dialog.set_sensitive(True)
        gobject.idle_add(_add_completion_callback, sr)
        
    
    
    def on_field_changed(self, field):
#        debug('on field changed: %s' % field)
        sensitive = True
        if self.source_presenter is not None:
            if len(self.source_presenter.problems) == 0:
                sensitive = True
            else:
                sensitive = False
        self.view.widgets.acc_ok_button.set_sensitive(sensitive)
        self.view.widgets.acc_ok_and_add_button.set_sensitive(sensitive)
        self.view.widgets.acc_next_button.set_sensitive(sensitive)
        
    
    def init_change_notifier(self):
        '''
        for each widget register a signal handler to be notified when the
        value in the widget changes, that way we can do things like sensitize
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
            remove_parent(self.current_source_box)
        if source_type is not None:
            self.current_source_box = self.view.widgets[box_map[source_type]]
            remove_parent(self.current_source_box)
            source_box.pack_start(self.current_source_box)
        else:
            self.current_source_box = None
        
        if source_model is not None:
            self.source_presenter = SourcePresenterFactory.\
                createSourcePresenter(source_type, source_model, self.view,
                                      self.defaults)
            # initialize model change notifiers    
            for widget, field in self.source_presenter.widget_to_field_map.iteritems():
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
        self.view.dialog.show_all()
        
    
    # TODO: should i combine these two init_(wild)_prov_combo methods
    
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


    widget_to_field_map = {'acc_id_entry': 'acc_id',
                           'prov_combo': 'prov_type',
                           'wild_prov_combo': 'wild_prov_status',
                           'species_entry': 'species',
                           'source_type_combo': 'source_type',}
    

    def refresh_view(self):
        '''
        get the values from the model and put them in the view
        '''
        for widget, field in self.widget_to_field_map.iteritems():            
            if field[-2:] == "ID":
                field = field[:-2]
#            debug('refresh(%s, %s=%s)' % (widget, field, self.model[field]))
            self.view.set_widget_value(widget, self.model[field],
                                       self.defaults.get(field, None))         
    
                
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


    def start(self, commit_transaction=True):    
        not_ok_msg = 'Are you sure you want to lose your changes?'
        exc_msg = "Could not commit changes.\n"
        committed = None
        while True:
            response = self.presenter.start()
            self.view.save_state() # should view or presenter save state
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
            elif self.model.dirty and utils.yes_no_dialog(not_ok_msg):
#                debug(self.model.dirty)
                sqlhub.processConnection.rollback()
                sqlhub.processConnection.begin()
                self.model.dirty = False
                break
            elif not self.model.dirty:
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
        
        if self.presenter.source_presenter is not None \
          and self.presenter.source_presenter.model.dirty:
            source_model = self.presenter.source_presenter.model
#            debug(source_model)                 
            if source_model.isinstance:
                source_table = tables[source_model.so_object.__class__.__name__]
            else:
                source_table = tables[source_model.so_object.__name__]
                
#        debug(source_model)                
        if source_model is None:
            return
#        debug(source_model)
        if 'latitude' in source_model and source_model.latitude is not None:
            if 'longitude' in source_model and source_model.longitude is None:
                msg = 'model must have both latitude and longitude or neither'
                raise ValueError(msg)
                    
        source_model['accession'] = accession.id
        new_source = commit_to_table(source_table, source_model)
        
        
        
    def commit_changes(self):
    
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
    from bauble.plugins.searchview.infobox import InfoBox, InfoExpander, \
        set_widget_value        
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
            set_widget_value(self.glade_xml, 'name_data', 
			     row.species.markup(True))
            set_widget_value(self.glade_xml, 'nplants_data', len(row.plants))
            set_widget_value(self.glade_xml, 'prov_data',row.prov_type, False)
            
            
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
            set_widget_value(self.glade_xml, 'notes_data', row.notes)            
    
    
    class SourceExpander(InfoExpander):
        
        def __init__(self, glade_xml):
            InfoExpander.__init__(self, 'Source', glade_xml)
            self.curr_box = None
        
        
        def update_collections(self, collection):
            
            set_widget_value(self.glade_xml, 'loc_data', collection.locale)
            
            geo_accy = collection.geo_accy
            if geo_accy is None:
                geo_accy = ''
            else: 
                geo_accy = '(+/- %sm)' % geo_accy
            
            if collection.latitude is not None:
                set_widget_value(self.glade_xml, 'lat_data',
                                 '%.2f %s' %(collection.latitude, geo_accy))
            if collection.longitude is not None:
                set_widget_value(self.glade_xml, 'lon_data',
                                '%.2f %s' %(collection.longitude, geo_accy))                                
            
            v = collection.elevation

            if collection.elevation_accy is not None:
                v = '%s (+/- %sm)' % (v, collection.elevation_accy)
            set_widget_value(self.glade_xml, 'elev_data', v)
            
            set_widget_value(self.glade_xml, 'coll_data', collection.collector)
            set_widget_value(self.glade_xml, 'date_data', collection.coll_date)
            set_widget_value(self.glade_xml, 'collid_data', collection.coll_id)
            set_widget_value(self.glade_xml,'habitat_data', collection.habitat)
            set_widget_value(self.glade_xml,'collnotes_data', collection.notes)
            
                
        def update_donations(self, donation):
            set_widget_value(self.glade_xml, 'donor_data', 
                             tables['Donor'].get(donation.donorID).name)
            set_widget_value(self.glade_xml, 'donid_data', donation.donor_acc)
            set_widget_value(self.glade_xml, 'donnotes_data', donation.notes)
        
        
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
