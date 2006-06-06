#
# infobox.py
#

import sys, os
import gtk
import bauble.utils as utils
import bauble.paths as paths
from bauble.utils.log import debug
from bauble.plugins import tables

# TODO: at some point all files using this method should use the one from
# utils instead, we need to set some type of deprecation warning on using this
# method and move it completely by 0.5.0
def set_widget_value(glade_xml, widget_name, value, markup=True):
    debug('DeprecationWarning: use set_widget_value from the utils modules')
    utils.set_widget_value(glade_xml, widget_name, value, markup, default='--')

# TODO: need some way to handle multiple join, maybe display some 
# number automatically but after that then a scrollbar should appear

# TODO: reset expander data on expand

# what to display if the value in the database is None
DEFAULT_VALUE='--'

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
        self.widgets = InfoExpander._widgets(glade_xml)
        
        
    class _widgets(dict):
        '''
        dictionary and attribute access for widgets
        '''
        # TODO: should i worry about making this more secure/read only

        def __init__(self, glade_xml):
            self.glade_xml = glade_xml
        
        def __getitem__(self, name):
            # TODO: raise a key error if there is no widget
            return self.glade_xml.get_widget(name)
    
        def __getattr__(self, name):
            return self.glade_xml.get_widget(name)
        
        
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
        
        sep = gtk.HSeparator()
        self.vbox.pack_start(sep, False, False)
    
    
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
        # TODO: should we just iter over the expanders and update them all
        raise NotImplementedError


# TODO: references expander should also show references to any
# foreign key defined in the table, e.g. if a species is being
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

        
