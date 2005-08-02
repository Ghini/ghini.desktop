#
# infobox.py
#

import sys, os
import gtk
from tables import tables
import utils

# TODO: need some way to handle multiple join, maybe display some 
# number automatically but after that then a scrollbar should appear

# TODO: reset expander data on expand

# what to display if the value in the database is None
DEFAULT_VALUE='--'

def set_widget_value(glade_xml, widget_name, value):
    w = glade_xml.get_widget(widget_name)
    if value is None: 
        value = DEFAULT_VALUE
        
    if isinstance(w, gtk.Label):
        w.set_text(str(value))
    if isinstance(w, gtk.TextView):
        w.get_buffer().set_text(value)
    

class InfoExpander(gtk.Expander):
    """
    a generic expander with a vbox
    """
    # TODO: we should be able to make this alot more generic
    # and get information from sources other than table columns
    def __init__(self, label, glade_xml=None):
        gtk.Expander.__init__(self, label)
        self.vbox = gtk.VBox(False)
        self.add(self.vbox)
        self.glade_xml = glade_xml
        self.set_expanded(True)
        
        
    def update(self, value):
        raise NotImplementedError("InfoExpander.update(): not implemented")
   
# should we have a specific expander for those that use glade
class GladeInfoExpander(gtk.Expander):
    pass
    
    
class InfoBox(gtk.ScrolledWindow):
    """
    a VBox with a bunch of InfoExpanders
    """
    
    def __init__(self):
        gtk.ScrolledWindow.__init__(self)
        self.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.vbox = gtk.VBox()
        self.vbox.set_spacing(10)
        viewport = gtk.Viewport()
        viewport.add(self.vbox)
        self.add(viewport)
        
        self.expanders = {}
    
    
    def add_expander(self, expander):
        self.vbox.pack_start(expander, False, False)
        self.expanders[expander.get_property("label")] = expander
    
    
    def get_expander(self, label):
        #if self.expanders.has_key(label): 
        if label in self.expanders:
            return self.expanders[label]
        else: return None
    
    
    def remove_expander(self, label):
        #if self.expanders.has_key(label): 
        if label in self.expanders:
            self.vbox.remove(self.expanders[label])
    
    
    def update(self, row):
        raise NotImplementedError


#class TableExpander(InfoExpander): 
#    """
#    an InfoExpander to represent columns in a table
#    """
#    
#    def __init__(self, label, columns):
#        """
#        columns is a dictionary of {column: name}
#        """
#        InfoExpander.__init__(self, label)
#        self.labels = {}
#        
#        
#    # this is intended to be overidden, this could be a list
#    # or a list of items, the class which extends TableExpander
#    # will know what to do with it
#    def _set_value(self, value):
#        self._value = value
#        self.update()
#    value = property(fset=_set_value)
            

class LocationsExpander(InfoExpander):
    """
    TableExpander for the Locations table
    """
    
    def __init__(self, label="Locations"):
        InfoExpander.__init__(self, label)

    def update(self, value):
        pass

# TODO: references expander should also show references to any
# foreign key defined in the table, e.g. if a plantname is being
# display it should also show the references associated with
# the family and genera

# TODO: it would be uber-cool to look up book references on amazon, 
# is there a python api for amazon or should it just defer to the browser
#class ReferencesExpander(TableExpander):
#    def __init__(self, label="References", columns={'label': 'Label',
#                                                    'reference': 'References'}):
#        TableExpander.__init__(self, label, columns)

class ImagesExpander(InfoExpander):
    def __init(self, label="Images"):#, columns={'label': 'Label',
                                    #          'uri': 'URI'}):
        InfoExpander.__init__(self, label)
                                                            
    def create_gui(self):
        pass
        
    def update(self, values):
        pass
        
        
class ReferencesExpander(InfoExpander):
    def __init__(self):
        InfoExpander.__init__(self, 'References', None)
        
        
    def update(self, values):
        if type(values) is not list:
            raise ValueError('ReferencesExpander.update(): expected a list')
            
        for v in values:
            print v.reference
        
        
class SourceExpander(InfoExpander):
    def __init__(self, glade_xml):
        InfoExpander.__init__(self, 'Source', glade_xml)
        self.curr_box = None
    
    def update_collections(self, collection):
        
        set_widget_value(self.glade_xml, 'loc_data', collection.locale)
        
        geo_accy = collection.geo_accy
        if geo_accy is None:
            geo_accy = ''
        else: geo_accy = '(+/-)' + geo_accy + 'm.'
        
        if collection.latitude is not None:
            set_widget_value(self.glade_xml, 'lat_data', collection.latitude + geo_accy)
        if collection.longitude is not None:
            set_widget_value(self.glade_xml, 'lon_data', collection.longitude + geo_accy)
        
        v = collection.elevation
        if collection.elevation_accy is not None:
            v = '+/- ' + v + 'm.'
        set_widget_value(self.glade_xml, 'elev_data', v)
        
        set_widget_value(self.glade_xml, 'coll_data', collection.collector)
        set_widget_value(self.glade_xml, 'data_data', collection.coll_date)
        set_widget_value(self.glade_xml, 'collid_data', collection.coll_id)
        
        set_widget_value(self.glade_xml, 'habitat_data', collection.habitat)
        
        # NOTE: if the widget is named notes_data then it doesn't update,
        # should probably file a bug with glade
        # UPDATE: i think this may actually have been b/c i had two widgets
        # with different parent windows but both named notes_data in the 
        # glade xml
        set_widget_value(self.glade_xml, 'collnotes_data', collection.notes)
        
            
    def update_donations(self, donation):
        set_widget_value(self.glade_xml, 'donor_data', tables.Donors.get(donation.donorID).name)
        set_widget_value(self.glade_xml, 'donid_data', donation.donor_acc)
        set_widget_value(self.glade_xml, 'donnotes_data', donation.notes)
        pass
    
    
    def update(self, value):        
        if self.curr_box is not None:
            self.vbox.remove(self.curr_box)
                        
        if type(value) == tables.Collections:
            w = self.glade_xml.get_widget('collections_box')
            w.unparent()
            self.curr_box = w
            self.update_collections(value)
        elif type(value) == tables.Donations:
            w = self.glade_xml.get_widget('donations_box')
            w.unparent()
            self.curr_box = w
            self.update_donations(value)
        
        self.vbox.pack_start(self.curr_box)
        
    
class GeneralAccessionExpander(InfoExpander):
    """
    generic information about an accession like
    number of clones, provenance type, wild provenance type, plantnames
    """

    def __init__(self, glade_xml):
        InfoExpander.__init__(self, "General", glade_xml)
        w = self.glade_xml.get_widget('general_box')
        w.unparent()
        self.vbox.pack_start(w)
    
    def update(self, row):
        set_widget_value(self.glade_xml, 'name_data', row.plantname)
        set_widget_value(self.glade_xml, 'nplants_data', len(row.plants))
        #w = self.glade_xml.get_widget('nplants_data')
        #pass


class AccessionsInfoBox(InfoBox):
    """
    - general info
    - source
    """
    def __init__(self):
        InfoBox.__init__(self)
        path = utils.get_main_dir() + os.sep + 'views' + os.sep + 'search' + os.sep
        self.glade_xml = gtk.glade.XML(path + 'acc_infobox.glade')
        
        self.general = GeneralAccessionExpander(self.glade_xml)
        self.add_expander(self.general)
        
        self.source = SourceExpander(self.glade_xml)
        self.add_expander(self.source)


    def update(self, row):        
        self.general.update(row)
                        
        # TODO: should test if the source should be expanded from the prefs
        if row.source_type == None:
            self.source.set_expanded(False)
            self.source.set_sensitive(False)
        elif row.source_type == 'Collections':
            self.source.set_expanded(True)
            self.source.update(row._collection)
        elif row.source_type == 'Donations':
            self.source.set_expanded(True)
            self.source.update(row._donation)
    
    
class FamiliesInfoBox(InfoBox):
    """
    - number of taxon in number of genera
    - references
    """
    def __init__(self):
        InfoBox.__init__(self)
        
        
class GeneraInfoBox(InfoBox):
    """
    - number of taxon in number of accessions
    - references
    """
    def __init__(self):
        InfoBox.__init__(self)
        

class PlantnamesInfoBox(InfoBox):
    """
    - general info, fullname, common name, num of accessions and clones
    - reference
    - images
    - redlist status
    - poisonous to humans
    - poisonous to animals
    - food plant
    - origin
    """
    def __init__(self):
        """ 
        fullname, synonyms, ...
        """
        InfoBox.__init__(self)
        self.ref = ReferencesExpander()
        self.ref.set_expanded(True)
        self.add_expander(self.ref)
        
        #img = ImagesExpander()
        #img.set_expanded(True)
        #self.add_expander(img)
        
        
    def update(self, row):
        self.ref.update(row.references)
        #self.ref.value = row.references
        #ref = self.get_expander("References")
        #ref.set_values(row.references)
        

class PlantsInfoBox(InfoBox):
    """
    an InfoBox for a Plants table row
    """
    def __init__(self):
        InfoBox.__init__(self)
        loc = LocationsExpander()
        loc.set_expanded(True)
        self.add_expander(loc)
    
    def update(self, row):
        loc = self.get_expander("Locations")
        loc.update(row.location)