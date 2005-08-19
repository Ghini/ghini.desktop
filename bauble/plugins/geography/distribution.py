#
# distribution.py
# 
# Description: the TDWG database for plant distributions version 2
#
import os
import gtk
from sqlobject import *
import bauble.utils as utils
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
    
    def __str__(self): return self.continent
    
    
# level2
class Region(BaubleTable):
    region = UnicodeCol(length=64)
    code = IntCol()
    
    # i don't think this is used
    iso_code = StringCol(default=None)
    
    continent = ForeignKey('Continent')
    areas = MultipleJoin('Area', joinColumn='region_id')
    
    def __str__(self): return self.region
    
    
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
    
    def __str__(self): return self.region


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

    
    def __init__(self):        
        super(DistributionEditor, self).__init__(Distribution)
    
    
    def start(self):
        path = os.path.dirname(__file__) + os.sep
        self.glade_xml = gtk.glade.XML(path + 'distribution_editor.glade')
        handlers = {'on_cult_check_toggled': self.on_cult_check_toggled,
                    'on_distribution_dialog_response': self.on_response,
                    }
        self.glade_xml.signal_autoconnect(handlers)
        
        
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
        for widget, col in self.widget_to_column_name_map.iteritems():
            print widget
            print col
            utils.set_dict_value_from_widget(self.glade_xml, widget, col, values)
        return values
            
        
    def commit_changes(self):
        values = self.get_values_from_widgets()
        print values
        