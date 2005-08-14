 #
# source editor module
#

import os, re
import gtk
import gtk.glade
from sqlobject import * 
import bauble
import bauble.utils as utils
import bauble.paths as paths
from bauble.plugins import BaubleTable, tables
from bauble.plugins.editor import TableEditor
#import donor

# FIXME: there is a bug that if  you open the source editor window, close
# it and then open it again then the widgets don't show on the donations
# box and sometimes the collections


def text_coord_to_decimal(self, dir, text):
    bits = re.split(':| ', text)
    print bits
    if len(bits) == 3:
        print bits
        dec = utils.dms_to_decimal(dir, *map(float, bits))
    else:
        try:
            dec = abs(float(text))
            if dec > 0 and dir == 'W' or dir == 'S':
                dec = -dec
        except:
            raise Exception("get_latitude: float()")
    return dec


def set_dict_value_from_widget(glade_xml, name, key, dic, validator=lambda x: x):
    w = glade_xml.get_widget(name)
    v = None
    if type(w) == gtk.Entry:
        v = w.get_text()
        if v == "": v = None
    elif type(w) == gtk.TextView:
        buffer = w.get_buffer()
        start = buffer.get_start_iter()
        end = buffer.get_end_iter()
        v = buffer.get_text(start, end)
        if v == "": v = None
    elif type(w) == gtk.ComboBoxEntry or type(w) == gtk.ComboBox:
        it = w.get_active_iter()
        if it is None: 
            v = None
        else: 
            model = w.get_model()
            v = model.get_value(it, 0)
            if isinstance(v, BaubleTable): v = v.id
            else: v
    else:
        raise ValueError("SourceEditor.set_dict_value_from_widget: " \
                         " ** unknown widget type: " + str(type(w)))
            
    if v is not None: 
        v = validator(v)
        dic[key] = v


def set_widget_value(glade_xml, widget_name, value):
    print 'set_widget_value: ' + widget_name
    if value is None: return
    w = glade_xml.get_widget(widget_name)
    if w is None:
        raise ValueError("set_widget_value: no widget by the name "+\
                         widget_name)
    print type(value)
    if type(value) == ForeignKey:
        pass
    elif isinstance(w, gtk.Entry):
        w.set_text(value)


def combo_cell_data_func(cell, renderer, model, iter, data):
    v = model.get_value(iter, 0)
    renderer.set_property('text', str(v))
    
    
def setComboModelFromSelect(combo, select):
    model = gtk.ListStore(object)
    for value in select:
        model.append([value])
    combo.set_model(model)

    if len(model) == 1: # only one to choose from
        combo.set_active(0)
    
    
class Singleton(object):
        _instance = None
        def __new__(cls, *args, **kwargs):
            if not cls._instance:
                cls._instance = super(Singleton, cls).__new__(
                                   cls, *args, **kwargs)
            return cls._instance
    
            
class CollectionEditor(Singleton):
    
    # TODO: region combos should start with all possible values so that
    # you don't have to set them in any particular order, it takes a
    # while to open the dialog if everthing is added at once so we 
    # could 1) initialize them on first click or 2) set them insensitive
    # and setup a thread to populate them and set them sensitive when
    # the thread exits, this could be a problem when porting to windows
    # or 3) set up an idle function to do something similar to the thread
    # solution
    # 
    # TODO: somehow figure out how to set the dirty flag if anything has
    # changed, this is a bit of a pain in the ass and a scalability problem
    # if we have to add an edit notify on every widget, but maybe not as 
    # long as we have the widget in a map and can just loop through
    # them to add the handlers
    #
    # TODO: the OK button should start off insensitive until the dirty
    # flag is set to indicate something has changed, and possible change
    # the border of the widget when the changed handler is called to
    # indicate what has changed
    
    initialized = False
    
    def __init__(self, glade_xml, row=None):
        self.table = tables["Collection"]
        if not self.initialized:
            self.initialize(glade_xml, row)
            self.initialized = True

        
    def initialize(self, glade_xml, row=None):    
        self.glade_xml = glade_xml
        handlers = {'on_lon_entry_changed': self.on_coord_entry_changed,
                    'on_lat_entry_changed': self.on_coord_entry_changed,
                    'on_region_combo_changed': self.on_region_combo_changed,
                    'on_area_combo_changed': self.on_area_combo_changed,
                    'on_state_combo_changed': self.on_state_combo_changed,
                    'on_place_combo_changed': self.on_place_combo_changed}
        self.glade_xml.signal_autoconnect(handlers)
        
        self.box = self.glade_xml.get_widget('collection_box')
        
        # set combo models
#        self.region_combo = self.glade_xml.get_widget('region_combo')
#        self.region_combo.child.set_property('editable', False)
#        r = gtk.CellRendererText()
#        self.region_combo.pack_start(r)
#        self.region_combo.set_cell_data_func(r, combo_cell_data_func, None)
#        setComboModelFromSelect(self.region_combo, 
#                                tables.Regions.select(orderBy='region'))
#        
#        self.area_combo = self.glade_xml.get_widget('area_combo')
#        self.area_combo.child.set_property('editable', False)
#        
#        self.state_combo = self.glade_xml.get_widget('state_combo')
#        self.state_combo.child.set_property('editable', False)
#            
#        self.place_combo = self.glade_xml.get_widget('place_combo')
#        self.place_combo.child.set_property('editable', False)
        self._collection_box_inited = True

        self.row = row
        if self.row is not None:
            print 'CollectionsEditor.initalized - refreshing'
            self.refresh_widgets_from_row()


    def on_region_combo_changed(self, combo, data=None):
         # TODO: if we can't catch the clicked signal then we have to
         # set the models with all possible values
         # TODO: if this is set to None or the entry is cleared we should
         # reset all the models
            
         self.place_combo.set_active(-1)
         self.place_combo.child.set_text('')
         self.place_combo.set_model(None)
            
         self.state_combo.set_active(-1)
         self.state_combo.child.set_text('')
         self.state_combo.set_model(None)
            
         self.area_combo.set_active(-1)
         self.area_combo.child.set_text('')
         model = combo.get_model()
         it = combo.get_active_iter()
         row = model.get_value(it, 1)
         setComboModelFromSelect(self.area_combo, row.areas)
        
        
    def on_area_combo_changed(self, combo, data=None):
        self.place_combo.set_active(-1)
        self.place_combo.child.set_text('')
        self.place_combo.set_model(None)
        
        self.state_combo.set_active(-1)
        self.state_combo.child.set_text('')
        self.state_combo.set_model(None)
        
        model = combo.get_model()
        if model is not None:
            it = combo.get_active_iter()
            if it is not None:
                row = model.get_value(it, 1)
                setComboModelFromSelect(self.state_combo, row.states)
        
        
    def on_state_combo_changed(self, combo, data=None):
        self.place_combo.set_active(-1)
        self.place_combo.child.set_text('')
        
        model = combo.get_model()
        if model is not None:
            it = combo.get_active_iter()
            if it is not None:
                row = model.get_value(it, 1)
                select = row.places
                if len(select) == 0:
                    self.place_combo.set_sensitive(False)
                else:
                    setComboModelFromSelect(self.place_combo, select)
                    self.place_combo.set_sensitive(True)
        
        
    def on_place_combo_changed(self, combo, data=None):
        pass
    
    
    def on_coord_entry_changed(self):
        pass
        
        
    def get_longitude(self):

        text = self.glade_xml.get_widget('lon_entry').get_text()
        if text == '' or text is None:
            return None
        
        north = self.glade_xml.get_widget('north_radio')
        south = self.glade_xml.get_widget('south_radio')
        if north.get_active(): dir = 'N'
        elif south.get_active(): dir = 'S'
        else: raise Exception('north south radio in inconsistent state')
        
        return self.text_coord_to_decimal(dir, text)
        
        
    def get_latitude(self):
        text = self.glade_xml.get_widget('lat_entry').get_text()
        if text == '' or text is None:
            return None
        
        east = self.glade_xml.get_widget('east_radio')
        west = self.glade_xml.get_widget('west_radio')
        if east.get_active(): dir = 'E'
        elif west.get_active(): dir = 'W'
        else: raise Exception('east/west radio in inconsistent state')
            
        return self.text_coord_to_decimal(dir, text)
        
        
    def get_coords(self):
        lon = self.get_longitude()
        lat = self.get_latitude()
        return lon, lat


    def refresh_widgets_from_row(self):
        """
        set all values from the collection object
        """
        #set_widget_value(self.glade_xml, 'collector_entry', self.row.collector)
        #set_widget_value(self.glade_xml, 'colldate_entry', self.row.coll_date)
        #set_widget_value(self.glade_xml, 'collid_entry', self.row.coll_date)
        #set_widget_value(self.glade_xml, 'collector_entry', self.row.collector)
        #set_widget_value(self.glade_xml, 'locale_entry', self.row.locale)
        print 'range'
        
        print '---------'
        for widget_name, col_name in self.widget_to_column_name_map.iteritems():
            attr = getattr(self.row, col_name)
            print type(attr)
            if type(attr) == ForeignKey:
                # TODO, implement this in a global function since we have 
                # to do it for at least the four location combos
                # if type(widget) == combobox
                #   for each value in combo model
                #      if row.id == value 
                #        set active row
                #        return
                pass
            set_widget_value(self.glade_xml, widget_name, getattr(self.row, col_name))
        
    widget_to_column_name_map = {'collector_entry': 'collector',
                                 'colldate_entry': 'coll_date',
                                 'collid_entry': 'coll_id',
                                 'locale_entry': 'locale',
                                 'lat_entry': 'latitude',
                                 'lon_entry': 'longitude',
                                 'geoacc_entry': 'geo_accy',
                                 'alt_entry': 'elevation',
                                 'altacc_entry': 'elevation_accy',
                                 'habitat_entry': 'habitat',
#                                 'region_combo': 'regionID',
#                                 'area_combo': 'areaID',
#                                 'state_combo': 'state',
#                                 'place_combo': 'placeID',
                                 'notes_entry': 'notes'}
        
    def get_values(self):
        values = {}
        # collector_entry, should be a combo entry with an id in the model
        set_dict_value_from_widget(self.glade_xml, 'collector_entry', 'collector', values)

        # colldate_entry, dd/mm/yy
        set_dict_value_from_widget(self.glade_xml, 'colldate_entry', 'coll_date', values)
        # collid_entry
        set_dict_value_from_widget(self.glade_xml, 'collid_entry', 'coll_id', values)
        # locale_entry
        set_dict_value_from_widget(self.glade_xml, 'locale_entry', 'locale', values)
        
        # lon_entry
        # parse the entry and turn it into deg, min, sec or 
        # maybe just a float, could also automatically put a 
        # negative at the front if south_radio is selected
        lon, lat = self.get_coords()
        if lon is not None and lat is not None:
            values['longitude'] = lon
            values['latitude'] = lat

        # geoacc_entry
        set_dict_value_from_widget(self.glade_xml, 'geoacc_entry', 'geo_accy', values)
        
        # alt_entry
        try:
            set_dict_value_from_widget(self.glade_xml, 'alt_entry', 'elevation', values, float)
        except TypeError, e:
            msg = 'Error setting the altitude: \nValue must be a number'
            utils.message_dialog(msg, gtk.MESSAGE_ERROR)
            
        # altacc_entry
        try:
            set_dict_value_from_widget(self.glade_xml, 'altacc_entry', 'elevation_accy', values, float)
        except TypeError, e:
            msg = 'Error setting the altitude accuracy: \nValue must be a number'
            utils.message_dialog(msg, gtk.MESSAGE_ERROR)
        
        # habitat_entry
        set_dict_value_from_widget(self.glade_xml, 'habitat_entry', 'habitat', values)
#        # country_combo
#        set_dict_value_from_widget(self.glade_xml, 'region_combo', 'region', values)
#        # primary_combo
#        set_dict_value_from_widget(self.glade_xml, 'area_combo', 'area', values)
#        # secondary_combo
#        set_dict_value_from_widget(self.glade_xml, 'state_combo', 'state', values)
#        # geounit_combo
#        set_dict_value_from_widget(self.glade_xml, 'place_combo', 'place', values)
        # notes_entry
        set_dict_value_from_widget(self.glade_xml, 'notes_entry', 'notes', values)
        return values
        
        
class DonationEditor(Singleton):

    initialized = False
    
    def __init__(self, glade_xml, row=None):
        self.table = tables["Donation"]
        if not self.initialized:
            self.initialize(glade_xml, row)
            self.initialized = True
        
        
    def initialize(self, glade_xml, row=None):    
        self.glade_xml = glade_xml
        handlers = {'on_don_new_button_clicked': self.on_don_new_button_clicked,
                    'on_don_edit_button_clicked': self.on_don_edit_button_clicked,
                    'on_donor_combo_changed': self.on_donor_combo_changed}
        self.glade_xml.signal_autoconnect(handlers)

        self.box = self.glade_xml.get_widget('donation_box')
        
        self.donor_combo = self.glade_xml.get_widget('donor_combo')
        sel = tables["Donor"].select()
        print 'init_donations'
        print sel
        for s in sel:
            print s
        print '---------'
        r = gtk.CellRendererText()
        self.donor_combo.pack_start(r)
        self.donor_combo.set_cell_data_func(r, combo_cell_data_func, None)
        setComboModelFromSelect(self.donor_combo, sel)


    def set_values(self, values):
        pass
        

    def get_values(self):
        # donor_combo
        # get the donor id from the model
        values = {}
        set_dict_value_from_widget(self.glade_xml, 'donor_combo', 'donor', values)
        set_dict_value_from_widget(self.glade_xml, 'donid_entry', 'donor_acc', values)
        set_dict_value_from_widget(self.glade_xml, 'donnotes_entry', 'notes', values)
        print 'get_values: ' + str(values)
        return values
    
    
    def on_don_new_button_clicked(self, button, data=None):
        #self.dialog.set_sensitive(False)
        e = editors["DonorEditor"]
        #e = donor.DonorEditor()
        print 'starting donor editor'
        e.start(True)
        print 'done with donor editor'
        #self.dialog.set_sensitive(True)
        #model = gtk.ListStore(obj)
        #self.init_donations()
        donor_combo = self.glade_xml.get_widget('donor_combo')
        print 'setting table'
        setComboModelFromSelect(donor_combo, tables["Donor"].select())
        
        
    def on_don_edit_button_clicked(self, button, data=None):
        # get the current value
        pass
        
        
    def on_donor_combo_changed(self, combo, data=None):
        #set the sensitivity of the edit button
        pass
    
    
class SourceEditor(TableEditor):
    
    label = 'Acession Sources'
    standalone = False
    show_in_toolbar = False
    
    def __init__(self, select=None, defaults={}):
        if select is not None and not isinstance(select, BaubleTable):
            raise ValueError("SourceEditor.__init__: select should be a "\
                             "single row in the table")
        TableEditor.__init__(self, None, #tables.SourceEditor,
                             select=select, defaults=defaults)
        self.committed = None
        self._dirty = False
        self.source_editor_map = (('Collection', CollectionEditor),
                                  ('Donation', DonationEditor))   
        self.create_gui()       
    
        
    def create_gui(self):
        self.curr_editor = None
        
        # TODO: change this, the main_dir and the locaition of the
        # plugins may not be the same
        #path = utils.get_main_dir() + os.sep + 'editors' + os.sep + 'source' + os.sep
        #path = paths.main_dir() + os.sep + 'editors' + os.sep + 'source' + os.sep
        path = os.path.dirname(__file__)
        self.glade_xml = gtk.glade.XML(path + os.sep + 'source_editor.glade')
        self.dialog = self.glade_xml.get_widget('source_dialog')
        self.source_box = self.glade_xml.get_widget('source_box')
        handlers = {'on_response': self.on_response,
                    'on_type_combo_changed': self.on_type_combo_changed,}
        self.glade_xml.signal_autoconnect(handlers)
        
        # set everything to their default states
        self.type_combo = self.glade_xml.get_widget('type_combo')
        for name, editor in self.source_editor_map:
            self.type_combo.append_text(name)
            
        # TODO: the indexes shouldn't be hardcoded like this
        if self.select is not None:
            print type(self.select)
            if type(self.select) == tables["Collections"]:
                self.type_combo.set_active(0)
            elif type(self.select) == tables["Donations"]:
                self.type_combo.set_active(1)
            else:
                raise Exception('SourceEditor: unknown row type')
        else: 
            self.type_combo.set_active(0)
    
        
    def save_state(self):
        # save the current width, height of the dialogs
        # so that each source type can have different dialog dimensions
        pass
    
    
    def commit_changes(self):
        # TODO: since the source is a single join and is only relevant
        # to its parent(accession) then we should allow a way to get
        # the values so that wherever the values are returned then the
        # accession foreign key can be set there and commited
        active = self.type_combo.get_active_text()
        #table, values = self.get_values(active)
        
        table = self.curr_editor.table
        values = self.curr_editor.get_values()
        
        print values
        if values is None: 
            return
        conn = sqlhub.getConnection()
        trans = conn.transaction()        
        #self.commited = None
        t = None
        try:
            print 'create table'
            # i guess the connection is inherant
            if self.select is None: # create a new table row
                t = table(connection=trans, **values)
            else: # update the table row passed in
                # TODO: if select and table aren't the same we should
                # ask the user if they want to change the type source
                if not isinstance(self.select, self.curr_editor.table):
                    msg = 'SourceEditor.commit_changes: the type has changed'
                    raise ValueError(msg)
                self.select.set(**values)
                t = self.select
                #raise NotImplementedError("TODO: updating a collection "\
                #                          "hasn't been implemented")
                #pass
                
        except Exception, e:
            print 'SourceEditor.commited: could not commit'
            print e
            trans.rollback()
            return False
        else:
            trans.commit()
            print 'commited'
            if t is None:
                raise ValueError("SourceEditor.commit_changes: t is None")
            self.committed = t
        
        return True
        
        
    def on_type_combo_changed(self, combo, data=None):
        if self.curr_editor is not None:
            self.source_box.remove(self.curr_editor.box)
            #self.curr_box.destroy()
        
        # TODO: check that nothing has been changed and ask the use if 
        # they want to save if something has changed, would probably have
        # to get this from the editors
        
        active = combo.get_active_text()    
        editor = None
        for label, e in self.source_editor_map:
            if label == active:
                print label
                editor = e(self.glade_xml, self.select)
                continue
                
        if editor is None:
            raise Exception('SourceEditor.on_type_combo_changed: unknown source type')

        #box = self.glade_xml.get_widget(box_name)
        #if box is None:
        #    msg = 'could not get box with name ' + box_name
        #    raise Exception('SourceEditor.on_type_combo_changed: ' + msg)
        # to edit the box in glade it needs a parent but we want the change
        # the parent on pack
        
        self.curr_editor = editor
        editor.box.unparent()
        self.source_box.pack_start(editor.box)
        #editor.se(self.select)
        #self.curr_box = box
        self.dialog.show_all()
    
        
    def on_response(self, dialog, response, data=None):
        #print "SourceEditor.on_response"
        
        if response == gtk.RESPONSE_OK:
            print "response ok"
            #if self._dirty:
            if not self.commit_changes():
                print 'SourceEditor.on_response: could not commited changes'
                return
        else:
            msg = 'Are you sure? You will lose your changes'
            if self._dirty and utils.yes_no_dialog(msg):
                return
        self.dialog.destroy()

    
    def start(self):
        """
        this blocks
        """
        # TODO: if commit_on_response is False we could return
        # from here since it blocks anyways
        TableEditor.start(self)
        #self.commit_on_response = commit_on_response        
        self.dialog.run() # blocks
        #print 'start: get_values'
        #t, v = self.get_values(self.type_combo.get_active_text())
        #self.dialog.destroy()
        return self.committed


