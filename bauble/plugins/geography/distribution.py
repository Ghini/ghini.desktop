#
# distribution.py
# 
# Description: schema for the TDWG World Geographical Scheme for Recording Plant 
#    Distributions, Edition 2
#
import os
import gtk
from sqlalchemy import *
import bauble


# FIXME: there are lots of problems with these tables
# 1. in some tables there is a row with no real values, i think this means
# from a cultivated source with no know origin but it should be verified and
# more intuitive
# 2. some row values that have default=None shouldn't, they are only set that
# way so that the mystery row with no values will import correctly
# 3. other stuff...


# TODO: don't allow continent to be deleted if region exists, in general
# fix cascading

# TODO: i wonder if it would be possible to store this in one table
# and remove some of the data we're not using

# level: the rank, this combined with the parent_id would give it's 
# exact place in the combo, e.g. level=0 would be the top level so
# we could do 
#for one in distribution_table.select(level=0):
#    for two in distribution_table.select(level=0):
# actually this way we really only need to know what is the top level
# and everything else can follow from the parent
#class GeographyMapper(bauble.BaubleMapper):
#    
#    _subdivisions_field = None
#    def _get_subdivisions(self):
#        '''
#        return all objects considered inside this geographic region
#        according to self._subdivisions_field
#        '''    
#        if self._subdivisions_field is None:
#            return None
#        
#        # select and return the subvisions
#        return []
#        
#    subdivisions = property(_get_subdivisions)
    

#
# place table (the gazetteer)
#
# TODO: if this is None then i think it means cultivated, should really do
        # something about this, like change the None to cultivated
        # NOTE: these two don't have names for some reason
        # ID*Gazetteer*L1 code*L2 code*L3 code*L4 code*Kew region code*Kew region subdivision*Kew region*Synonym*Notes
        #331**2,00*24,00*SOC*SOC-OO*10,00*C*North East Tropical Africa**
        #333**3,00*33,00*TCS*TCS-AB*2,00*A*Orient**
# TODO: should synonym be a key into this table
# NOTE: Mansel I. and Manu'a don't have continents ???

def region_markup_func(region):
    if region.continent is None:
        return region
    else:
        return region, region.continent

def botanicalcountry_markup_func(bc):
    if bc.region is None:
        return bc
    else:
        return bc, bc.region


def basicunit_markup_func(bu):
    if bu.botanical_country is None:
        return bu
    else:
        return bu, bu.botanical_country


def place_markup_func(place):
    if place.basic_unit is None:
        return place
    else:
        return place, place.basic_unit


place_table = Table('place',
                    Column('id', Integer, primary_key=True),
                    Column('place', Unicode(64)),
                    Column('code', String(4), unique=True, nullable=False),
                    Column('synonym', Unicode(255)),
                    Column('notes', Unicode),
                    Column('continent_id', Integer, ForeignKey('continent.id')),
                    Column('region_id', Integer, ForeignKey('region.id')),
                    Column('botanical_country_id', Integer, 
                           ForeignKey('botanical_country.id')),
                    Column('basic_unit_id', Integer, ForeignKey('basic_unit.id')),
                    Column('_created', DateTime, default=func.current_timestamp()),
                    Column('_last_updated', DateTime, default=func.current_timestamp(), 
                           onupdate=func.current_timestamp()))

class Place(object):

    def __str__(self): 
        return self.place or ''

mapper(Place, place_table, order_by='place')


#
# kew_region table
#
# TODO: one column in the data has none, i don't know why, i think it means
        # that its cultivated and its origin is unknown, neother code or region
        # should really be None
kew_region_table = Table('kew_region',
                         Column('id', Integer, primary_key=True),
                         Column('code', Integer, unique=True, nullable=False),
                         Column('region', Unicode(64)),
                         Column('subdiv', String(1)),
                         Column('_created', DateTime, default=func.current_timestamp()),
                         Column('_last_updated', DateTime, default=func.current_timestamp(), 
                                onupdate=func.current_timestamp()))

class KewRegion(object):
    
    def __str__(self):         
        if self.region is None: 
            return "" # **** TODO: don't do it
        if self.subdiv is not None:
            return "%s - %s" % (self.region, self.subdiv)
        return self.region
    
mapper(KewRegion, kew_region_table,
#       properties={'places': relation(Place, backref='kew_region')},
       order_by='region')


#
# state table
#
state_table = Table('state',
                    Column('id', Integer, primary_key=True),
                    Column('state', Unicode(64), unique=True, nullable=False),
                    Column('code', String(8), unique=True, nullable=False),
                    Column('iso_code', String(8)),
                    Column('ed2_status', Unicode(64)),
                    Column('notes', Unicode),
                    Column('area_id', Integer, ForeignKey('area.id')),
                    Column('_created', DateTime, default=func.current_timestamp()),
                    Column('_last_updated', DateTime, default=func.current_timestamp(), 
                           onupdate=func.current_timestamp()))

class State(object):

    def __str__(self): 
        return self.state

mapper(State, state_table,
#       properties={'places': relation(Place, backref='state')},
       order_by='state')


#
# area table
#
area_table = Table('area',
                   Column('id', Integer, primary_key=True),
                   Column('area', Unicode(64), unique=True, nullable=False),
                   Column('code', String(5), unique=True, nullable=False),
                   Column('iso_code', String(4)),
                   Column('ed2_status', Unicode(64)),
                   Column('notes', Unicode),
                   Column('region_id', Integer, ForeignKey('region.id')),
                   Column('_created', DateTime, default=func.current_timestamp()),
                   Column('_last_updated', DateTime, default=func.current_timestamp(), 
                          onupdate=func.current_timestamp()))

class Area(object):
    
    def __str__(self): 
        return self.area
    
mapper(Area, area_table,
       properties={'states': relation(State, cascade='all, delete-orphan',
                                      backref='area')},
       order_by='area')


# 
# basic_unit table
# 
basic_unit_table = Table('basic_unit',
                         Column('id', Integer, primary_key=True),
                         Column('name', Unicode(64)),
                         Column('code', String(8), unique=True, nullable=False),
                         Column('iso_code', String(8)),
                         Column('ed2_status', Unicode(64)),
                         Column('notes', Unicode),
                         Column('botanical_country_id', Integer, 
                                ForeignKey('botanical_country.id')),
                         Column('_created', DateTime, default=func.current_timestamp()),
                         Column('_last_updated', DateTime, default=func.current_timestamp(), 
                                onupdate=func.current_timestamp()))

class BasicUnit(object):
        
    def __str__(self): 
        return self.name

mapper(BasicUnit, basic_unit_table,
       properties = {'places': relation(Place, cascade='all, delete-orphan',
                                        backref='basic_unit')},
       order_by='name')


#
# botanical_country table
#
botanical_country_table = Table('botanical_country',
                                Column('id', Integer, primary_key=True),
                                Column('name', Unicode(64), nullable=False, unique=True),
                                Column('code', String(5), nullable=False, unique=True),
                                Column('iso_code', String(4)),
                                Column('ed2_status', Unicode(64)),
                                Column('notes', Unicode),
                                Column('region_id', Integer, ForeignKey('region.id')),
                                Column('_created', DateTime, default=func.current_timestamp()),
                                Column('_last_updated', DateTime, default=func.current_timestamp(), 
                                       onupdate=func.current_timestamp()))

class BotanicalCountry(object):
    
    def __str__(self): 
        return self.name
    
mapper(BotanicalCountry, botanical_country_table,       
       properties={'basic_units':
                   relation(BasicUnit, cascade='all, delete-orphan',
                            backref='botanical_country')},
       order_by='name')


# 
# region table
#
# TODO: iso_code isn't even used, remove it
region_table = Table('region',
                     Column('id', Integer, primary_key=True),
                     Column('region', Unicode(64), nullable=False, unique=True),
                     Column('code', Integer, nullable=False, unique=True),
                     Column('iso_code', String(1)),
                     Column('continent_id', Integer, ForeignKey('continent.id')),
                     Column('_created', DateTime, default=func.current_timestamp()),
                     Column('_last_updated', DateTime, default=func.current_timestamp(), 
                            onupdate=func.current_timestamp()))
            
class Region(object):
    
    def __str__(self): 
        return self.region

mapper(Region, region_table,
       properties={'botanical_countries': 
                   relation(BotanicalCountry, cascade='all, delete-orphan',
                            backref='region')},
       order_by='region')


# 
# continent table
#
continent_table = Table('continent',
                        Column('id', Integer, primary_key=True),
                        Column('continent', Unicode(24), nullable=False, unique=True) ,       
                        Column('code', Integer, nullable=False, unique=True),
                        Column('_created', DateTime, default=func.current_timestamp()),
                        Column('_last_updated', DateTime, default=func.current_timestamp(), 
                               onupdate=func.current_timestamp()))

class Continent(object):
    
    def __str__(self): 
        return self.continent
    
mapper(Continent, continent_table,
       properties = {'regions': relation(Region, cascade='all, delete-orphan',
                                         backref='continent')},
       order_by='continent')


#class Distribution(BaubleTable):
#    """
#    this class holds a possible plant distribution, a species row should
#    have a SingleJoin to a distribution, there is no DistributionEditor,
#    the distribution are added from the SpeciesEditor
#    """
#    continent = ForeignKey("Continent", cascade=False)
#    area = ForeignKey("Area", default=None, cascade=False)
#    region = ForeignKey("Region", default=None, cascade=False)
#    state = ForeignKey("State", default=None, cascade=False)    
#    place = ForeignKey("Place", default=None, cascade=False)
#    #kew_region = ForeignKey("KewRegion", default=None)
#    
#    # means that the distribution is unknown but is widely
#    # cultivated
#    cultivated = BoolCol(default=False)
#    
#    species = ForeignKey("Species")
#        
#    def __str__(self):
#        # this might not be a good idea to choose the string like this
#        # since unique objects might return the same __str__
#        if self.cultivated: 
#            return self.cultivated
#        elif self.place is not None:
#            return str(self.place)
#        elif self.state is not None:
#            return str(self.state)
#        elif self.region is not None:
#            return str(self.region)
#        elif self.area is not None:
#            return str(self.area)
#        else: 
#            return str(self.continent)

##
## Distribution Editor
##
#
#class DistributionEditor(TableEditor):
#    
#    label = "Distribution"
#    
#    widget_to_column_name_map = {'cont_combo': 'continentID',
#                                 'area_combo': 'areaID',
#                                 'region_combo': 'regionID',
#                                 'state_combo': 'stateID',
#                                 'place_combo': 'placeID',
#                                 'kew_combo': 'kew_regionID',
#                                 'cult_check': 'cultivated',
#                                 'species_label': 'speciesID'
#                                }
#
#    
#    def __init__(self, select=None, default={}):
#        super(DistributionEditor, self).__init__(Distribution, select, default)
#        path = os.path.dirname(__file__) + os.sep
#        self.glade_xml = gtk.glade.XML(path + 'distribution_editor.glade')
#        handlers = {'on_cult_check_toggled': self.on_cult_check_toggled,
#                    'on_distribution_dialog_response': self.on_response,
#                    'on_cont_combo_button_press_event': self.on_cont_combo_button_press_event,
##                    'on_cont_combo_show': self.on_cont_combo_show,
#                    'on_dist_combo_changed': self.on_dist_combo_changed,
##                    'on_cont_combo_editing_done': self.on_cont_combo_editing_done
##                    'on_cont_clear_clicked': self.on_cont_clear_clicked,
##                    'on_region_clear_clicked': self.on_region_clear_clicked,
##                    'on_country_clear_clicked': self.on_country_clear_clicked,
##                    'on_unit_clear_clicked': self.on_unit_clear_clicked,
##                    'on_place_clear_clicked': self.on_place_clear_clicked,
#                    }
#        self.glade_xml.signal_autoconnect(handlers)
#        
#        self.dist_combo = self.glade_xml.get_widget("dist_combo")
#        #self.cont_combo.connect("changed", self.on_cont_changed)
#        #cont_combo.connect("focus-in-event", self.on_combo_focus_in)
#        #cont_combo.connect("focus-out-event", self.on_combo_focus_out)
#    
#    def on_dist_combo_changed(self, widget, data=None):
#        value = self.get_active_dist()
#        self.set_labels(value)
#        
#               
#    def cell_data_method(self, layout, cell, model, iter, data=None):
#        v = model.get_value(iter, 0)
#        cell.set_property("text", str(v))
#        
#        
#    def set_labels(self, value):
#        #dist_data = self.glade_xml.get_widget('cont_data')
#        cont_data = self.glade_xml.get_widget('cont_data')
#        region_data = self.glade_xml.get_widget('region_data')
#        #region_data.set_label(value.region)
#        country_data = self.glade_xml.get_widget('country_data')
#        unit_data = self.glade_xml.get_widget('unit_data')
#        place_data = self.glade_xml.get_widget('place_data')
#        if isinstance(value, Continent):
#            cont_data.set_text(value.continent)
#        elif isinstance(value, Region):
#            region_data.set_text(value.region)
#        elif isinstance(value, BotanicalCountry):
#            country_data.set_text(value.name)
#        
#        
#    def start(self):
#        model = gtk.TreeStore(object)
#        for continent in Continent.select(orderBy='continent'):
#            p1 = model.append(None, [continent])
#            for region in continent.regions:
#                p2 = model.append(p1, [region])
#                for country in region.botanical_countries:
#                    p3 = model.append(p2, [country])
#                    for unit in country.units:
#                        if unit.name != country.name: # no reason to have these
#                            model.append(p3, [unit])
#                    
#                    
#        #combo = self.glade_xml.get_widget("cont_combo")
#        combo = self.glade_xml.get_widget("dist_combo")
#        combo.set_model(model)
#        cell = gtk.CellRendererText()
#        combo.pack_start(cell, True)
#        combo.set_cell_data_func(cell, self.cell_data_method, None)
#        #combo.set_text_column(0)        
#        #self.set_completion_on_combo(combo, model)    
#
#
#    def populate_model(self, model, parent, select):
#        for row in select:
#            model.append(parent, row)
#    
#    def start_old(self):                
#        self.init_combo("cont_combo", Continent.select(orderBy='continent'))
#        self.init_combo("region_combo", Region.select(orderBy='region'))
#        self.init_combo("country_combo", BotanicalCountry.select(orderBy='name'))
#        self.init_combo("unit_combo", BasicUnit.select(orderBy='name'))
#        self.init_combo("place_combo", Place.select(orderBy='place'))
#        #self.init_combo("kew_combo", KewRegion.select(orderBy='region'))
#        
#                    
#    def init_combo(self, combo_name, select):        
#        #model = gtk.ListStore(str, int)
#        model = gtk.TreeStore(str, int)
#        for row in select:
#            #model.append([str(row), row.id])
#            p = model.append(None, [str(row), row.id])
#            model.append(p, ["_dummy", 0])
#        combo = self.glade_xml.get_widget(combo_name)
#        combo.set_model(model)
#        cell = gtk.CellRendererText()
#        combo.pack_start(cell, True)
#        #combo.set_cell_data_func(cell, self.cell_data_method, None)
#        combo.set_text_column(0)        
#        self.set_completion_on_combo(combo, model)
#        
#        
#    def set_completion_on_combo(self, combo, model):
#        """
#        model = [str, i]
#        """
#        completion = gtk.EntryCompletion()
#        cell = gtk.CellRendererText()        
#        completion.pack_start(cell)
#        completion.set_inline_completion(True)
#        completion.set_text_column(0)
#        combo.child.set_completion(completion)
#        completion.set_model(model)
#        
#
#    def on_cont_combo_editing_done(self, widget, data=None):
#        print 'editing done'
#
#        
#        
#    def on_cont_combo_changed(self, widget, data=None):
#        print "cont changed"
#        #print widget.get_active_iterm()
#        #pass
#        #active = widget.get_active()
#        #if active == -1:
#        #    widget.set_text("")                
#        i = widget.get_active_iter()        
#        if i is not None:
#            v = widget.get_model().get_value(i, 0)            
#            print v
#            widget.child.set_text(str(v))
#                
#        
#    def on_cont_combo_button_press_event(self, widget, data=None):
#        print 'on_cont_combo_button_press_event'
#        #model = widget.get_model()
#        #for row in Continent.select():
#        #    print "append " + row
#        #    model.append(row)
#        
#        
#    def on_cult_check_toggled(self, widget, data=None):
#        active = widget.get_active()
#        table = self.glade_xml.get_widget("dist_table")
#        table.set_sensitive(not active)
#
#
#    def on_response(self, widget, response):        
#        if response == gtk.RESPONSE_OK:
#            self.commit_changes()
#        widget.destroy()            
#        
#    def get_active_dist(self):
#        model = self.dist_combo.get_model()
#        i = self.dist_combo.get_active_iter()
#        return model.get_value(i, 0)
#        
#    def get_values_from_widgets(self):
#        values = {}
#        species = get_widget_value(self.glade_xml, "species_label")
#        if isinstance(species, BaubleTable):
#            values['speciesID'] = species.id    
#        else: 
#            values['speciesID'] = species
#            #raise ValueError()
#            
#        if get_widget_value(self.glade_xml, "cult_check"):
#            values["cultivated"] = True
#            return values
#
#        dist = self.get_active_dist()
#        print dist
#        #set_dict_value_from_wdiget(values, )
#        #set_dict_value_from_widget(values, "continentID", self.glade_xml, "cont_combo", 1)
#        #set_dict_value_from_widget(values, "regionID", self.glade_xml, "region_combo", 1)
#        #set_dict_value_from_widget(values, "areaID", self.glade_xml, "area_combo", 1)
#        #set_dict_value_from_widget(values, "stateID", self.glade_xml, "state_combo", 1)
#        #set_dict_value_from_widget(values, "placeID", self.glade_xml, "place_combo", 1)
#        #set_dict_value_from_widget(values, "kew_regionID", self.glade_xml, "kew_combo", 1)        
#        #return values
#        return {}
#            
#        
#    def commit_changes(self):
#        values = self.get_values_from_widgets()
#        print values
#        


## level 1
#class Continent(BaubleTable):
#
#    class sqlmeta(BaubleTable.sqlmeta):
#        defaultOrder = "continent"
#
#    #continent = StringCol(length=24, alternateID=True)
#    continent = UnicodeCol(length=24, alternateID=True)
#    code = IntCol(alternateID=True)
#    
#    regions = MultipleJoin('Region', joinColumn='continent_id')
#    
#    def __str__(self): 
#        return self.continent
#    
#    
## level2
#class Region(BaubleTable):
#
#    class sqlmeta(BaubleTable.sqlmeta):
#        defaultOrder = "region"
#    
#    region = UnicodeCol(length=64, alternateID=True)
#    code = IntCol(alternateID=True)
#    
#    # i don't think this is used
#    iso_code = StringCol(default=None)
#    
#    continent = ForeignKey('Continent', cascade=False)
#    botanical_countries = MultipleJoin('BotanicalCountry', joinColumn='region_id')
#    
#    def __str__(self): 
#        return self.region
#    
## level3
#class BotanicalCountry(BaubleTable):
#
##    class sqlmeta(BaubleTable.sqlmeta):
##	defaultOrder = "name"
#    class sqlmeta:
#        defaultOrder = "name"
#    
#    name = UnicodeCol(length=64, alternateID=True)
#    code = StringCol(length=5, alternateID=True)
#    #area = StringCol(length=64)
#
#    iso_code = StringCol(length=4, default=None)
#    ed2_status = UnicodeCol(length=64, default=None)
#    notes = StringCol(default=None)
#    
#    region = ForeignKey('Region', cascade=False)
#    units = MultipleJoin('BasicUnit', joinColumn='botanical_country_id')
#    
#    def __str__(self): 
#        #return self.area
#        return self.name
#     
## level 3     
#class BasicUnit(BaubleTable):
#
#    class sqlmeta(BaubleTable.sqlmeta):
#        defaultOrder = "name"
#    
#    name = UnicodeCol(length=64)
#    code = StringCol(length=8, alternateID=True)
#    iso_code = StringCol(length=8)
#    ed2_status = UnicodeCol(length=64, default=None)
#    notes = UnicodeCol(default=None)
#    
#    botanical_country = ForeignKey('BotanicalCountry', cascade=False)
#    places = MultipleJoin('Place', joinColumn='state_id')
#    
#    def __str__(self): 
#        return self.name
#          
## level3
#class Area(BaubleTable):
#
#    class sqlmeta(BaubleTable.sqlmeta):
#	defaultOrder = "area"
#	    
#    area = UnicodeCol(length=64, alternateID=True)
#    code = StringCol(length=5, alternateID=True)
#    
#    iso_code = StringCol(length=4, default=None)
#    ed2_status = UnicodeCol(length=64, default=None)
#    notes = UnicodeCol(default=None)
#    
#    region = ForeignKey('Region', cascade=False)
#    states = MultipleJoin('State', joinColumn='area_id')
#    
#    def __str__(self): 
#        return self.area
#    
#
#        
## level4
#class State(BaubleTable):
#
#    class sqlmeta(BaubleTable.sqlmeta):
#        defaultOrder = "state"
#    
#    state = UnicodeCol(length=64, alternateID=True)
#    code = StringCol(length=8, alternateID=True)
#    iso_code = StringCol(length=8)
#    ed2_status = UnicodeCol(length=64, default=None)
#    notes = UnicodeCol(default=None)
#    
#    area = ForeignKey('Area', cascade=False)
#    places = MultipleJoin('Place', joinColumn='state_id')
#    
#    def __str__(self): 
#        return self.state
#    
#    
## gazetteer
#class Place(BaubleTable):
#
#    class sqlmeta(BaubleTable.sqlmeta):
#        defaultOrder = "place"
#    
#    # TODO: if this is None then i think it means cultivated, should really do
#    # something about this
#    
#    # NOTE: these two don't have names for some reason
#    # ID*Gazetteer*L1 code*L2 code*L3 code*L4 code*Kew region code*Kew region subdivision*Kew region*Synonym*Notes
#    #331**2,00*24,00*SOC*SOC-OO*10,00*C*North East Tropical Africa**
#    #333**3,00*33,00*TCS*TCS-AB*2,00*A*Orient**
#    place = UnicodeCol(length=64, default=None)
#    code = StringCol(length=4, alternateID=True)
#
#    #name = UnicodeCol(length=64)
#    synonym = UnicodeCol(length=250, default=None)
#    notes = UnicodeCol(default=None)
#
#    # NOTE: Mansel I. and Manu'a don't have continents ???
#    continent = ForeignKey('Continent', default=None, cascade=False) 
#    region = ForeignKey('Region', default=None, cascade=False)
#    #area = ForeignKey('Area', default=None)
#    botanical_country = ForeignKey('BotanicalCountry', default=None, 
#                                   cascade=False)
#    basic_unit = ForeignKey('BasicUnit', default=None, cascade=False)
#    #state = ForeignKey('State', default=None)
#    #kew_region = ForeignKey('KewRegion', default=None)
#
#    def __str__(self): 
#        if self.place is None:
#            return ""
#        return self.place
#
#
#class KewRegion(BaubleTable):
#
#    class sqlmeta(BaubleTable.sqlmeta):
#	defaultOrder = "region"
#    
#    # TODO: one column in the data has none, i don't know why, i think it means
#    # that its cultivated and its origin is unknown, neother code or region
#    # should really be None
#    code = IntCol(default=None, alternateID=True)
#    region = UnicodeCol(length=64, default=None)
#    subdiv = StringCol(length=1, default=None)
#    
#    places = MultipleJoin('Place', joinColumn='kew_region_id')
#    
#    def __str__(self):         
#        if self.region is None: return "" # **** TODO: don't do it
#        if self.subdiv is not None:
#            return "%s - %s" % (self.region, self.subdiv)
#        return self.region
#
#
#class Distribution(BaubleTable):
#    """
#    this class holds a possible plant distribution, a species row should
#    have a SingleJoin to a distribution, there is no DistributionEditor,
#    the distribution are added from the SpeciesEditor
#    """
#    continent = ForeignKey("Continent", cascade=False)
#    area = ForeignKey("Area", default=None, cascade=False)
#    region = ForeignKey("Region", default=None, cascade=False)
#    state = ForeignKey("State", default=None, cascade=False)    
#    place = ForeignKey("Place", default=None, cascade=False)
#    #kew_region = ForeignKey("KewRegion", default=None)
#    
#    # means that the distribution is unknown but is widely
#    # cultivated
#    cultivated = BoolCol(default=False)
#    
#    species = ForeignKey("Species")
#        
#    def __str__(self):
#        # this might not be a good idea to choose the string like this
#        # since unique objects might return the same __str__
#        if self.cultivated: 
#            return self.cultivated
#        elif self.place is not None:
#            return str(self.place)
#        elif self.state is not None:
#            return str(self.state)
#        elif self.region is not None:
#            return str(self.region)
#        elif self.area is not None:
#            return str(self.area)
#        else: 
#            return str(self.continent)

