#
# infobox.py
#

import gtk

# TODO: need some way to handle multiple join, maybe display some 
# number automatically but after that then a scrollbar should appea

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
        for column, name in columns.iteritems():
            label = gtk.Label()
            label.set_alignment(0.0, 0.5)
            self.vbox.pack_start(label, False, False)
            self.labels[column] = (name, label)
        
    
    def set_values(self, values):
        """
        populate the labels according to the values in result, should
        only be a single row
        """
        for col in self.labels.keys():
            value = eval("str(values.%s)" % col)
            name, label = self.labels[col] 
            label.set_text("%s: %s" % (name, value))
            

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
class ReferencesExpander(TableExpander):
    def __init__(self, label="References", columns={'label': 'Label',
                                                    'reference': 'References'}):
        TableExpander.__init__(self, label, columns)

class ImagesExpander(TableExpander):
    def __init(self, label="Images", columns={'label': 'Label',
                                              'uri': 'URI'}):
        TableExpander.__init__(self, label, columns)
                                                            
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
    
    def set_values_from_row(self, row):
        raise NotImplementedError
        
#class AccessionsInfoBox(InfoBox):
#    def __init__(self):
#        InfoBox.__init__(self)
            
class PlantnamesInfoBox(InfoBox):
    def __init__(self):
        InfoBox.__init__(self)
        #ref = ReferenfencesExpander()
        #ref.set_expanded(True)
        #self.add_expander(ref)
        
        #img = ImagesExpander()
        #img.set_expanded(True)
        #self.add_expander(img)
        
        
    def set_values_from_row(self, row):
        pass
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
    
    def set_values_from_row(self, row):
        loc = self.get_expander("Locations")
        loc.set_values(row.location)