#
# infobox.py
#

import gtk
from tables import tables

# TODO: need some way to handle multiple join, maybe display some 
# number automatically but after that then a scrollbar should appear

class InfoExpander(gtk.Expander):
    """
    a generic expander with a vbox
    """
    # TODO: we should be able to make this alot more generic
    # and get information from sources other than table columns
    def __init__(self, label):
        gtk.Expander.__init__(self, label)
        self.vbox = gtk.VBox(False)
        self.add(self.vbox)

    def update(self):
        raise NotImplementedError("InfoExpander.update(): not implemented")
   

class TableExpander(InfoExpander): 
    """
    an InfoExpander to represent columns in a table
    """
    
    def __init__(self, label, columns):
        """
        columns is a dictionary of {column: name}
        """
        InfoExpander.__init__(self, label)
        self.labels = {}
        
    
        
    # this is intended to be overidden, this could be a list
    # or a list of items, the class which extends TableExpander
    # will know what to do with it
    def _set_value(self, value):
        self._value = value
        self.update()
    value = property(fset=_set_value)
            

class LocationsExpander(TableExpander):
    """
    TableExpander for the Locations table
    """
    
    def __init__(self, label="Locations", columns={"site": "Site"}):
        TableExpander.__init__(self, label, columns)


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

class ImagesExpander(TableExpander):
    def __init(self, label="Images", columns={'label': 'Label',
                                              'uri': 'URI'}):
        TableExpander.__init__(self, label, columns)
                                                            
    def create_gui(self):
        pass
        
    def update(self, values):
        pass
        
        
class InfoBoxFactory:
    def createInfoBox(type):
        pass

        
class InfoBox(gtk.VBox):
    """
    a VBox with a bunch of InfoExpanders
    """
    
    def __init__(self):
        gtk.VBox.__init__(self, False)
        self.expanders = {}
        
    def add_expander(self, expander):
        self.pack_start(expander, False, False)
        self.expanders[expander.get_property("label")] = expander
    
    def get_expander(self, label):
        if self.expanders.has_key(label): 
            return self.expanders[label]
        else: return None
    
    def remove_expander(self, label):
        if self.expanders.has_key(label): 
            self.remove(self.expanders[label])
    
    def update(self, row):
        raise NotImplementedError
        

class ReferencesExpander(TableExpander):
    def __init__(self):
        InfoExpander.__init__(self, 'References')
        
        
    def update(self, values):
        if type(values) is not list:
            raise ValueError('ReferencesExpander.update(): expected a list')
            
        for v in values:
            print v.reference
        
        
class SourceExpander(InfoExpander):
    def __init__(self):
        InfoExpander.__init__(self, 'Source')
        self.create_gui()
    
    type_prefix = 'Type: '
    alt_prefix = 'Altitude: '
    gps_prefix = '' # should just do a 'long lat' string
    
    
    def create_gui(self):
        #vbox = gtk.VBox(False)
        self.type_label = gtk.Label('Type: ')
        self.type_label.set_alignment(0.0, 0.5)
        self.vbox.pack_start(self.type_label)
        self.name_label = gtk.Label('Name:')
        self.name_label.set_alignment(0.0, 0.5)
        self.vbox.pack_start(self.name_label)
        #self.add(vbox)
        
    def update(self, value):
        #print 'SourceExpander._set_row:' + value
        #self._row = value
        if type(value) == tables.Collections:
            self.type_label.set_text('Collection')
        elif type(value) == tables.Donations:
            self.type_label.set_text('Donation')
        self.name_label.set_text(str(value))
        #self.type_label.set_text(str(value.__class__.__name)
        #self.name_label.set_text(str(value))
    
    
class AccessionsExpander(InfoExpander):
    """
    generic information about an accession like
    number of clones, provenance type, wild provenance type, plantnames
    """
    pass
    
    
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
        
            
class AccessionsInfoBox(InfoBox):
    """
    - general info
    - source
    """
    def __init__(self):
        InfoBox.__init__(self)
        self.source = SourceExpander()
        self.add_expander(self.source)
        self.source.set_expanded(True)


    def update(self, row):        
        if row.source_type == 'Collections':
            self.source.row = row._collection
        if row.source_type == 'Donations':
            self.source.row = row._donation
        
        
        
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
        loc.set_values(row.location)