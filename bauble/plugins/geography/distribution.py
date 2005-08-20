#
# distribution.py
# 
# Description: the TDWG database for plant distributions version 2
#
import os
import gtk
from sqlobject import *
#import bauble.utils as utils
from bauble.plugins.editor import set_dict_value_from_widget, get_widget_value
from bauble.plugins import BaubleTable, tables
from bauble.plugins.editor import TableEditor


# FIXME: there are lots of problems with these tables
# 1. in some tables there is a row with no real values, i think this means
# from a cultivated source with no know origin but it should be verified and
# more intuitive
# 2. some row values that have default=None shouldn't, they are only set that
# way so that the mystery row with no values will import correctly
# 3. other stuff...


# level 1
class Continent(BaubleTable):
    continent = StringCol(length=24)
    code = IntCol()
    
    regions = MultipleJoin('Region', joinColumn='continent_id')
    
    def __str__(self): 
        return self.continent
    
    
# level2
class Region(BaubleTable):
    region = UnicodeCol(length=64)
    code = IntCol()
    
    # i don't think this is used
    iso_code = StringCol(default=None)
    
    continent = ForeignKey('Continent')
    areas = MultipleJoin('Area', joinColumn='region_id')
    
    def __str__(self): 
        return self.region
    
    
# level3
class Area(BaubleTable):
    code = StringCol(length=5)
    #area = StringCol(length=64)
    area = UnicodeCol(length=64)
    iso_code = StringCol(length=4, default=None)
    ed2_status = StringCol(length=64, default=None)
    notes = StringCol(default=None)
    
    region = ForeignKey('Region')
    states = MultipleJoin('State', joinColumn='area_id')
    
    def __str__(self): 
        return self.area
    
    
# level4
class State(BaubleTable):
    state = UnicodeCol(length=64)
    code = StringCol(length=8)
    iso_code = StringCol(length=8)
    ed2_status = StringCol(length=64, default=None)
    notes = UnicodeCol(default=None)
    
    area = ForeignKey('Area')
    places = MultipleJoin('Place', joinColumn='state_id')
    
    def __str__(self): 
        return self.state
    
    
# gazetteer
class Place(BaubleTable):
    
    # TODO: if this is None then i think it means cultivated, should really do
    # something about this
    place = UnicodeCol(length=64, default=None)
    #name = UnicodeCol(length=64)
    synonym = UnicodeCol(length=64, default=None)
    notes = UnicodeCol(default=None)
    
    #continent = ForeignKey('Continent')
    region = ForeignKey('Region', default=None)
    area = ForeignKey('Area', default=None)
    state = ForeignKey('State', default=None)
    kew_region = ForeignKey('KewRegion', default=None)

    def __str__(self): 
        if self.place is None:
            return ""
        return self.place


class KewRegion(BaubleTable):
    
    # TODO: one column in the data has none, i don't know why, i think it means
    # that its cultivated and its origin is unknown, neother code or region
    # should really be None
    code = IntCol(default=None)
    region = StringCol(length=64, default=None)
    subdiv = StringCol(length=1, default=None)
    
    places = MultipleJoin('Place', joinColumn='kew_region_id')
    
    def __str__(self):         
        if self.region is None: return "" # **** TODO: don't do it
        if self.subdiv is not None:
            return "%s - %s" % (self.region, self.subdiv)
        return self.region


class Distribution(BaubleTable):
    """
    this class holds a possible plant distribution, a plantname row should
    have a single to a distribution
    """
    continent = ForeignKey("Continent")
    area = ForeignKey("Area", default=None)
    region = ForeignKey("Region", default=None)
    state = ForeignKey("State", default=None)    
    place = ForeignKey("Place", default=None)
    kew_region = ForeignKey("KewRegion", default=None)
    
    # means that the distribution is unknown but is widely
    # cultivated
    cultivated = BoolCol(default=False)
    
    plantname = ForeignKey("Plantname")
        
    def __str__(self):
        # this might not be a good idea to choose the string like this
        # since unique objects might return the same __str__
        if self.cultivated: 
            return self.cultivated
        elif self.place is not None:
            return str(self.place)
        elif self.state is not None:
            return str(self.state)
        elif self.region is not None:
            return str(self.region)
        elif self.area is not None:
            return str(self.area)
        else: 
            return str(self.continent)

#
# Distribution Editor
#

class DistributionEditor(TableEditor):
    
    label = "Distribution"
    
    widget_to_column_name_map = {'cont_combo': 'continentID',
                                 'area_combo': 'areaID',
                                 'region_combo': 'regionID',
                                 'state_combo': 'stateID',
                                 'place_combo': 'placeID',
                                 'kew_combo': 'kew_regionID',
                                 'cult_check': 'cultivated',
                                 'plantname_label': 'plantnameID'
                                }

    
    def __init__(self, select=None, default={}):
        super(DistributionEditor, self).__init__(Distribution, select, default)
        path = os.path.dirname(__file__) + os.sep
        self.glade_xml = gtk.glade.XML(path + 'distribution_editor.glade')
        handlers = {'on_cult_check_toggled': self.on_cult_check_toggled,
                    'on_distribution_dialog_response': self.on_response,
#                    'on_cont_combo_button_press_event': self.on_cont_combo_button_press_event,
#                    'on_cont_combo_show': self.on_cont_combo_show,
#                    'on_cont_combo_changed': self.on_cont_combo_changed,
#                    'on_cont_combo_editing_done': self.on_cont_combo_editing_done
                    }
        self.glade_xml.signal_autoconnect(handlers)
    
    
    def start(self):                
        self.init_combo("cont_combo", Continent.select(orderBy='continent'))
        self.init_combo("region_combo", Region.select(orderBy='region'))
        self.init_combo("area_combo", Area.select(orderBy='area'))
        self.init_combo("state_combo", State.select(orderBy='state'))
        self.init_combo("place_combo", Place.select(orderBy='place'))
        self.init_combo("kew_combo", KewRegion.select(orderBy='region'))
        
            
    def init_combo(self, combo_name, select):        
        model = gtk.ListStore(str, int)
        for row in select:
            model.append([str(row), row.id])
        combo = self.glade_xml.get_widget(combo_name)
        combo.set_model(model)
        cell = gtk.CellRendererText()
        combo.pack_start(cell, True)
        combo.set_text_column(0)
        
        self.set_completion_on_combo(combo, model)
        
    def set_completion_on_combo(self, combo, model):
        """
        model = [str, i]
        """
        completion = gtk.EntryCompletion()
        cell = gtk.CellRendererText()        
        completion.pack_start(cell)
        completion.set_inline_completion(True)
        completion.set_text_column(0)
        combo.child.set_completion(completion)
        completion.set_model(model)
        

    def on_cont_combo_editing_done(self, widget, data=None):
        print 'editing done'
        pass
        
        
    def on_cont_combo_changed(self, widget, data=None):
        print "cont changed"
        print widget.get_active()
        i = widget.get_active_iter()
        v = widget.get_model().get_value(i, 0)
        print v
        #widget.set_text(str(v))
        
        
    def on_cont_combo_show(self, widget, data=None):
        print 'cont show'
        
        
    def on_cont_combo_button_press_event(self, widget, data=None):
        print 'on_cont_combo_button_press_event'
        model = widget.get_model()
        for row in Continent.select():
            print "append " + row
            model.append(row)
        
        
    def on_cult_check_toggled(self, widget, data=None):
        active = widget.get_active()
        table = self.glade_xml.get_widget("dist_table")
        table.set_sensitive(not active)
        box = self.glade_xml.get_widget("kew_box")
        box.set_sensitive(not active)


    def on_response(self, widget, response):        
        if response == gtk.RESPONSE_OK:
            self.commit_changes()
        widget.destroy()            
        
        
    def get_values_from_widgets(self):
        values = {}
        plantname = get_widget_value(self.glade_xml, "plantname_label")
        if isinstance(plantname, BaubleTable):
            values['plantnameID'] = plantname.id    
        else: 
            values['plantnameID'] = plantname
            #raise ValueError()
            
        if get_widget_value(self.glade_xml, "cult_check"):
            values["cultivated"] = True
            return values
            
        set_dict_value_from_widget(values, "continentID", self.glade_xml, "cont_combo", 1)
        set_dict_value_from_widget(values, "regionID", self.glade_xml, "region_combo", 1)
        set_dict_value_from_widget(values, "areaID", self.glade_xml, "area_combo", 1)
        set_dict_value_from_widget(values, "stateID", self.glade_xml, "state_combo", 1)
        set_dict_value_from_widget(values, "placeID", self.glade_xml, "place_combo", 1)
        set_dict_value_from_widget(values, "kew_regionID", self.glade_xml, "kew_combo", 1)        
        return values
            
        
    def commit_changes(self):
        values = self.get_values_from_widgets()
        print values
        