#
# source editor module
#

import os, re
import editors
import bauble
import gtk
import gtk.glade
import utils
from tables import tables
import sqlobject

label = 'Source'
description = 'Source'

def setComboModelFromSelect(combo, select):
    model = gtk.ListStore(str, object)
    for value in select:
        model.append([str(value), value])
    combo.set_model(model)
    
    if combo.get_text_column() == -1:
        combo.set_text_column(0)
        
    if len(model) == 1: # only one to choose from
        combo.set_active(0)
    
    
class SourceEditor(editors.TableEditor):
    def __init__(self, select=None, defaults={}):
        editors.TableEditor.__init__(self, tables.Source,
                                     select=select, defaults=defaults)
        self._dirty = False
        self.create_gui()
 
        
    def create_gui(self):
        self.curr_box = None
        
        # TODO: change this, the main_dir and the locaition of the
        # plugins may not be the same
        path = utils.get_main_dir() + os.sep + 'editors' + os.sep + 'source' + os.sep
        self.glade_xml = gtk.glade.XML(path + 'source_editor.glade')
        self.dialog = self.glade_xml.get_widget('source_dialog')
        self.source_box = self.glade_xml.get_widget('source_box')
        handlers = {'on_response': self.on_response,
                    'on_type_combo_changed': self.on_type_combo_changed,
                    'on_lon_entry_changed': self.on_coord_entry_changed,
                    'on_lat_entry_changed': self.on_coord_entry_changed,
                    'on_region_combo_changed': self.on_region_combo_changed,
                    'on_area_combo_changed': self.on_area_combo_changed,
                    'on_state_combo_changed': self.on_state_combo_changed,
                    'on_place_combo_changed': self.on_place_combo_changed}
        self.glade_xml.signal_autoconnect(handlers)
        
        # set everything to their default states
        self.type_combo = self.glade_xml.get_widget('type_combo')
        self.type_combo.set_active(0)
        
        # set combo models
        self.region_combo = self.glade_xml.get_widget('region_combo')
        self.region_combo.child.set_property('editable', False)
        setComboModelFromSelect(self.region_combo, 
                                tables.Regions.select(orderBy='region'))
        
        self.area_combo = self.glade_xml.get_widget('area_combo')
        self.area_combo.child.set_property('editable', False)
        
        self.state_combo = self.glade_xml.get_widget('state_combo')
        self.state_combo.child.set_property('editable', False)
            
        self.place_combo = self.glade_xml.get_widget('place_combo')
        self.place_combo.child.set_property('editable', False)
        
        
        
    def on_coord_entry_changed(self):
        pass
        
        
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
        
        
    def save_state(self):
        # save the current width, height of the dialogs
        # so that each source type can have different dialog dimensions
        pass
    
            
    def get_donation_values(self):
        # donor_combo
        # get the donor id from the model
        self.glade_xml.get_widget('donor_combo')
        # donid_entry
        self.glade_xml.get_widget('donid_combo')
        # donnotes_entry
        self.glade_xml.get_widget('donnotes_combo')
        return None
        
        
    def set_value_from_widget(self, name, key, dic, validator=lambda x: x):
        w = self.glade_xml.get_widget(name)
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
        elif type(w) == gtk.ComboBoxEntry:
            v = w.get_active_text()
            if v == '': v = None
        else:
            raise ValueError("SourceEditor.set_value_from_widget: " \
                             " ** unknown widget type: " + str(type(w)))
            
        if v is not None: 
            v = validator(v)
            dic[key] = v

    
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

    
    def get_collection_values(self):
        values = {}
        # collector_entry, should be a combo entry with an id in the model
        self.set_value_from_widget('collector_entry', 'coll_name', values)

        # colldate_entry, dd/mm/yy
        self.set_value_from_widget('colldate_entry', 'coll_date', values)
        # collid_entry
        self.set_value_from_widget('collid_entry', 'coll_id', values)
        # locale_entry
        self.set_value_from_widget('locale_entry', 'locale', values)
        
        # lon_entry
        # parse the entry and turn it into deg, min, sec or 
        # maybe just a float, could also automatically put a 
        # negative at the front if south_radio is selected
        lon, lat = self.get_coords()
        if lon is not None and lat is not None:
            values['longitude'] = lon
            values['latitude'] = lat

        # geoacc_entry
        self.set_value_from_widget('geoacc_entry', 'geo_accy', values)
        
        # alt_entry
        try:
            self.set_value_from_widget('alt_entry', 'altitude', values, float)
        except TypeError, e:
            msg = 'Error setting the altitude: \nValue must be a number'
            utils.message_dialog(msg, gtk.MESSAGE_ERROR)
            
        # altacc_entry
        try:
            self.set_value_from_widget('altacc_entry', 'altitude_accy', values, float)
        except TypeError, e:
            msg = 'Error setting the altitude accuracy: \nValue must be a number'
            utils.message_dialog(msg, gtk.MESSAGE_ERROR)
        
        # habitat_entry
        self.set_value_from_widget('habitat_entry', 'habitat', values)
        # country_combo
        self.set_value_from_widget('region_combo', 'region', values)
        # primary_combo
        self.set_value_from_widget('area_combo', 'area', values)
        # secondary_combo
        self.set_value_from_widget('state_combo', 'state', values)
        # geounit_combo
        self.set_value_from_widget('place_combo', 'place', values)
        # notes_entry
        self.set_value_from_widget('notes_entry', 'notes', values)
        return values
    
    
    def get_values(self, type):
        if type == 'Donation':
            values = self.get_donation_values()
            table = tables.Donations
        elif type == 'Collection':
            values = self.get_collection_values()
            table = tables.Collections
            #return get_donation_values())
        else: 
            raise ValueError("SourceEditor.get_values() " \
                             "-- unknown table type: + " + tyye)
        return table, values
    
    committed = None
    def commit_changes(self):
        # TODO: since the source is a single join and is only relevant
        # to its parent(accession) then we should allow a way to get
        # the values so that wherever the values are returned then the
        # accession foreign key can be set there and commited
        active = self.type_combo.get_active_text()
        table, values = self.get_values(active)
        print values
        if values is None: 
            return
        conn = sqlobject.sqlhub.getConnection()
        trans = conn.transaction()        
        #self.commited = None
        try:
            print 'create table'
            # i guess the connection is inherant
            t = table(connection=trans, **values)
        except Exception, e:
            print 'SourceEditor.commited: could not commit'
            print e
            trans.rollback()
            return False
        else:
            trans.commit()
            print 'self.commited'
            print t
            print str(t)
            self.committed = t
        return True
        
        
    def on_type_combo_changed(self, combo, data=None):
        if self.curr_box is not None:
            self.source_box.remove(self.curr_box)
        
        active = combo.get_active_text()    
        if active == 'Donation':
            box_name = 'donation_box'
        elif active == 'Collection':
            box_name = 'collection_box'
        else: 
            raise Exception('SourceEditor.on_type_combo_changed: unknown source type')

        box = self.glade_xml.get_widget(box_name)
        if box is None:
            msg = 'could not get box with name' + box_name
            raise Exception('SourceEditor.on_type_combo_changed: ' + msg)
        # to edit the box in glade it needs a parent but we want the change
        # the parent on pack
        box.unparent() 
        self.source_box.pack_start(box)
        self.curr_box = box
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
        editors.TableEditor.start(self)
        #self.commit_on_response = commit_on_response        
        self.dialog.run() # blocks
        #print 'start: get_values'
        #t, v = self.get_values(self.type_combo.get_active_text())
        #self.dialog.destroy()
        return self.committed


editor = SourceEditor
