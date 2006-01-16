 #
# source editor module
#

import os, re, traceback
from datetime import datetime
import gtk
import gtk.glade
from sqlobject import * 
from bauble import BaubleError
import bauble.utils as utils
import bauble.paths as paths
from bauble.plugins import BaubleTable, tables, editors
from bauble.plugins.editor import TableEditorDialog
from bauble.utils.log import debug


def text_coord_to_decimal(dir, text):
    bits = re.split(':| ', text)
#    debug(bits)
    if len(bits) == 3:
#        debug(bits)
        dec = utils.dms_to_decimal(dir, *map(float, bits))
    else:
        try:
            dec = abs(float(text))
            if dec > 0 and dir == 'W' or dir == 'S':
                dec = -dec
        except:
            raise Exception("get_latitude: float()")
    return dec


def set_dict_value_from_widget(glade_xml, name, key, dic,
                               validator=lambda x: x):
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
    return utils.set_widget_value(glade_xml, widget_name, value)

#     debug('set_widget_value(%s, %s)' % (widget_name, value))
#     if value is None: 
#         return
#     w = glade_xml.get_widget(widget_name)
#     if w is None:
#         raise ValueError("set_widget_value: no widget by the name "+\
#                          widget_name)
# #    debug(type(value))
#     if type(value) == ForeignKey:
#         pass
#     if isinstance(value, datetime):
#         # TODO: get the date format from BaubleMeta
#         s = "%s/%s/%s" % (value.day, value.month, value.year)
#         w.set_text(s)
#     elif isinstance(w, gtk.Entry):
#         w.set_text(value)
#     else:
# 	raise TypeError('unknown widget type (%s) in glade file named %s' \
# 			% (type(w), widget_name))


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
    

class CollectionEditor:
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
                    'on_lat_entry_changed': self.on_coord_entry_changed}
        self.glade_xml.signal_autoconnect(handlers)
        
        self.box = self.glade_xml.get_widget('collection_box')
        old_window = self.glade_xml.get_widget('collection_window')
        if self.box.get_parent() == old_window:
            old_window.remove(self.box) # this could be removed already
            
        self._collection_box_inited = True

        self.row = row
        if self.row is not None:
            #debug('CollectionsEditor.initalized - refreshing')
            self.refresh_widgets_from_row()
    
    
    def on_coord_entry_changed(self, widget):
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
        
        return text_coord_to_decimal(dir, text)
        
        
    def get_latitude(self):
        text = self.glade_xml.get_widget('lat_entry').get_text()
        if text == '' or text is None:
            return None
        
        east = self.glade_xml.get_widget('east_radio')
        west = self.glade_xml.get_widget('west_radio')
        if east.get_active(): dir = 'E'
        elif west.get_active(): dir = 'W'
        else: raise Exception('east/west radio in inconsistent state')
            
        return text_coord_to_decimal(dir, text)
        
        
    def get_coords(self):
        lon = self.get_longitude()
        lat = self.get_latitude()
        return lon, lat


    def refresh_widgets_from_row(self):
        """
        set all values from the collection object
        """
        for widget_name,col_name in self.widget_to_column_name_map.iteritems():
            set_widget_value(self.glade_xml, widget_name,
                             getattr(self.row, col_name))
        
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
                                 'notes_entry': 'notes'}
        
    def get_values(self):
        values = {}
        # collector_entry, should be a combo entry with an id in the model
        set_dict_value_from_widget(self.glade_xml, 'collector_entry',
                                   'collector', values)

        # colldate_entry
        set_dict_value_from_widget(self.glade_xml, 'colldate_entry',
                                   'coll_date', values)
        # collid_entry
        set_dict_value_from_widget(self.glade_xml, 'collid_entry', 'coll_id',
                                   values)
        # locale_entry
        set_dict_value_from_widget(self.glade_xml, 'locale_entry', 'locale',
                                   values)
        
        # lon_entry
        # parse the entry and turn it into deg, min, sec or 
        # maybe just a float, could also automatically put a 
        # negative at the front if south_radio is selected
        lon, lat = self.get_coords()
        if lon is not None and lat is not None:
            values['longitude'] = lon
            values['latitude'] = lat

        # geoacc_entry
        set_dict_value_from_widget(self.glade_xml, 'geoacc_entry', 'geo_accy',
                                   values)
        
        # alt_entry
        try:
            set_dict_value_from_widget(self.glade_xml, 'alt_entry',
                                       'elevation', values, float)
        except TypeError, e:
            msg = 'Error setting the altitude: \nValue must be a number'
            utils.message_dialog(msg, gtk.MESSAGE_ERROR)
            
        # altacc_entry
        try:
            set_dict_value_from_widget(self.glade_xml, 'altacc_entry',
                                       'elevation_accy', values, float)
        except TypeError, e:
            msg = 'Error setting the altitude accuracy: \n'\
                  'Value must be a number'
            utils.message_dialog(msg, gtk.MESSAGE_ERROR)
        
        # habitat_entry
        set_dict_value_from_widget(self.glade_xml, 'habitat_entry', 'habitat',
                                   values)
        set_dict_value_from_widget(self.glade_xml, 'notes_entry', 'notes',
                                   values)
        return values
        
        
class DonationEditor:

    initialized = False
    
    def __init__(self, glade_xml, row=None):            
        self.table = tables["Donation"]
        if not self.initialized:
            self.initialize(glade_xml, row)
            self.initialized = True

        
    def initialize(self, glade_xml, row=None):    
        self.glade_xml = glade_xml
        handlers = {'on_don_new_button_clicked':self.on_don_new_button_clicked,
                    'on_don_edit_button_clicked':
                    self.on_don_edit_button_clicked,
                    'on_donor_combo_changed': self.on_donor_combo_changed}
        self.glade_xml.signal_autoconnect(handlers)

        old_window = self.glade_xml.get_widget('donation_window')
        self.box = self.glade_xml.get_widget('donation_box')
        if self.box.get_parent() == old_window:
            old_window.remove(self.box)
        
        self.donor_combo = self.glade_xml.get_widget('donor_combo')
        sel = tables["Donor"].select()
        r = gtk.CellRendererText()
        self.donor_combo.pack_start(r)
        self.donor_combo.set_cell_data_func(r, combo_cell_data_func, None)
        setComboModelFromSelect(self.donor_combo, sel)


    def get_values(self):

        # donor_combo
        # get the donor id from the model
        values = {}
        set_dict_value_from_widget(self.glade_xml, 'donor_combo', 'donor',
                                   values)
        set_dict_value_from_widget(self.glade_xml, 'donid_entry', 'donor_acc',
                                   values)
        set_dict_value_from_widget(self.glade_xml, 'donnotes_entry', 'notes',
                                   values)
        return values
    
    
    def on_don_new_button_clicked(self, button, data=None):
        #self.dialog.set_sensitive(False)
        e = editors['DonorEditor']()
        response = e.start()
        #editor_class().start()
        #self.dialog.set_sensitive(True)
        #model = gtk.ListStore(obj)
        #self.init_donations()
        donor_combo = self.glade_xml.get_widget('donor_combo')
        setComboModelFromSelect(donor_combo, tables["Donor"].select())
        
        
    def on_don_edit_button_clicked(self, button, data=None):
        # get the current value
        pass
        
        
    def on_donor_combo_changed(self, combo, data=None):
        #set the sensitivity of the edit button
        pass
    
    
class SourceEditor(TableEditorDialog):
    
    label = 'Acession Sources'
    standalone = False
    show_in_toolbar = False
    
    def __init__(self, select=None, defaults={}):
        super(SourceEditor, self).__init__(None, None, None, select, defaults)
        if select is not None and not isinstance(select, BaubleTable):
            raise ValueError("SourceEditor.__init__: select should be a "\
                             "single row in the table")
                             
        #self.committed = None
        self._dirty = False
        self.source_editor_map = (('Collection', CollectionEditor),
                                  ('Donation', DonationEditor))   
        self.create_gui()       
    
        
    def create_gui(self):
        self.curr_editor = None    
        path = os.path.join(paths.lib_dir(), "plugins", "garden")
        self.glade_xml = gtk.glade.XML(path + os.sep + 'source_editor.glade')
        self.dialog = self.glade_xml.get_widget('source_dialog')
        self.source_box = self.glade_xml.get_widget('source_box')
#        handlers = {'on_response': self.on_response,
#                    'on_type_combo_changed': self.on_type_combo_changed,}
        handlers = {'on_type_combo_changed': self.on_type_combo_changed,}
        self.glade_xml.signal_autoconnect(handlers)
        
        # set everything to their default states
        self.type_combo = self.glade_xml.get_widget('type_combo')
        for name, editor in self.source_editor_map:
            self.type_combo.append_text(name)
            
        # TODO: the indexes shouldn't be hardcoded like this
        if self.select is not None:
            if isinstance(self.select, tables["Collection"]):
                self.type_combo.set_active(0)
            elif isinstance(self.select, tables["Donations"]):
                self.type_combo.set_active(1)
            else:
                raise Exception('SourceEditor: unknown row type')
        else: 
            self.type_combo.set_active(0)
    
        
    def save_state(self):
        # save the current width, height of the dialogs
        # so that each source type can have different dialog dimensions
        pass
    
    
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
                editor = e(self.glade_xml, self.select)
                continue                
        if editor is None:
            raise Exception('SourceEditor.on_type_combo_changed: '\
                            'unknown source type')
        self.curr_editor = editor                
        self.source_box.pack_start(editor.box)
        editor.box.show_all()
        
    def _transform_row(self, row):
        # TODO: we need a much better way to define the date format for the 
        # database, possible having a wizard when creating a new database to 
        # select the global date format at database creation and store the 
        # date format in BuableMeta, really we shouldn't have to set it
        # in BaubleMeta since we store datatime objects in the database, we 
        # just have to be able to convert the value at entry time, lets just
        # do this conversion in _transform_row
#        date_str = sel
#        colldate_entry = self.glade_xml.get_widget('colldate_entry')
#        date_str = colldate_entry.get_text()

#        values[coll_date] = date
        if 'coll_date' in row:
            # should get the date format from somewhere, most likely
            # from BaubleMeta, should also validate the date but i think
            # datetime actually does this, e.g. month < 12
            date_str = row['coll_date']
            rx = re.compile('(?P<day>\d?\d)/(?P<month>\d?\d)/(?P<year>\d\d\d\d)')
            m = rx.match(date_str)
            if m is None:
                raise BaubleError("Collection date not in dd/mm/yyyy format")
            ymd = [int(x) for x in [m.group('year'), m.group('month'), \
                                    m.group('day')]]
            dt = datetime(*ymd)
            row['coll_date'] = dt
            
            
            
            
    def commit_changes(self):
        # TODO: since the source is a single join and is only relevant
        # to its parent(accession) then we should allow a way to get
        # the values so that wherever the values are returned then the
        # accession foreign key can be set there and commited
        active = self.type_combo.get_active_text()
        #table, values = self.get_values(active)
        
        table = self.curr_editor.table
        values = self.curr_editor.get_values()
        
        if values is None: 
            return None

        self._transform_row(values)

        table_instance = None
        if self.select is None: # create a new table row
            table_instance = table(**values)
        else: # update the table row passed in
            # TODO: if select and table aren't the same we should
            # ask the user if they want to change the type source
            if not isinstance(self.select, self.curr_editor.table):
                msg = 'SourceEditor.commit_changes: Bauble does not ' \
                      'currently support changing the source type'
                raise ValueError(msg)
            self.select.set(**values)
            table_instance = self.select # TODO: does this work????
            #raise NotImplementedError("TODO: updating a collection "\
            #                          "hasn't been implemented")
        return table_instance
        
        
    def start(self, commit_transaction=True):   
         committed = self._run()
         if commit_transaction:
             sqlhub.processConnection.commit()
         return committed
         
         
    def _set_values_from_widgets(self):
         '''
         we get the values from the other editor so we don't worry about
         this method
         '''
         pass
     
#    def start(self):
#        # this ensures that the visibility is set properly in the meta before
#        # before everything is created
#
#        while True:
#            msg = 'Are you sure you want to lose your changes?'
#            response = self.dialog.run()
#            if response == gtk.RESPONSE_OK:
#                    break
#            elif self._dirty and utils.yes_no_dialog(msg):
#                break      
#            elif not dirty:
#                break
#        return response
    
    
#    def destroy(self):
#        super(SourceEditor, self).destroy()
#        self.dialog.destroy()
