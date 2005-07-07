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

label = 'Source'
description = 'Source'


class SourceEditor(editors.TableEditor):
    def __init__(self, select=None, defaults={}):
        print tables
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
                    'on_lat_entry_changed': self.on_coord_entry_changed}
        self.glade_xml.signal_autoconnect(handlers)
        
        # set everything to their default states
        self.type_combo = self.glade_xml.get_widget('type_combo')
        self.type_combo.set_active(0)
        
        self.dialog.show_all()
        
    def on_coord_entry_changed(self):
        pass
        
    def save_state(self):
        # save the current width, height of the dialogs
        # so that each source type can have different dialog dimensions
        pass
    
    
    def get_values(self, type):
        if type == 'Donation':
            values = self.get_donation_values()
            table = tables.Donations
        elif type == 'Collection':
            values = self.get_collection_values()
            table = tables.Collections
            #return get_donation_values())
        return table, values
            
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
        print key
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
        else:
            raise Exception("SourceEditor.set_value_from_widget: " \
                            " ** unknown widget type")
            
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
        self.set_value_from_widget('collector_entry', 'collector', values)
        
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
        self.set_value_from_widget('country_combo', 'country', values)
        # primary_combo
        self.set_value_from_widget('primary_combo', 'country_pri_sub', values)
        # secondary_combo
        self.set_value_from_widget('secondary_combo', 'country_sec_sub', values)
        # geounit_combo
        self.set_value_from_widget('geounit_combo', 'country_sp_unit', values)
        # notes_entry
        self.set_value_from_widget('notes_entry', 'notes', values)
        return values
        
    def commit_changes(self):
        active = self.type_combo.get_active_text()
        table, values = self.get_values(active)
        print table
        print values
        return
        if values is None: 
            return
        conn = sqlobject.sqlhub.getConnection()
        trans = con.transaction()
        try:
            table(conn=trans, **values)
        except:
            trans.rollback()
        else:
            trans.commit()
        
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
        print "SourceEditor.on_response"
        if response == gtk.RESPONSE_OK:
            print "response ok"
            #if self._dirty:
            self.commit_changes()
        else:
            msg = 'Are you sure? You will lose your changes'
            if self._dirty and utils.yes_no_dialog(msg):
                return
            
        self.dialog.destroy()

    
    def start(self):
        editors.TableEditor.start(self)
    #    pass


editor = SourceEditor
