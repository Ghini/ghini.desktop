#
# ABCD import/exporter
#

from bauble.tools.import_export import *
import csv
import sqlobject
#from tables import tables
import gtk.gdk

#from bauble import *

import abcd

# NOTE: see biocase provider software for reading and writing ABCD data
# files, already downloaded software to desktop

# TODO: should have a command line argument to create labels without starting the
# full bauble interface, after creating the labels it should automatically open
# the whatever ever view is associated with pdf files
# e.g bauble -labels "select string"
# bauble -labels "block=4"
# bauble -label "acc=1997"
#
# TODO: create label make in the tools that show a dialog with an entry
# the entry is for a search string that then returns a list of all the labels
# that'll be made with checkboxess next to them to de/select the ones you 
# don't want to print, could also have a check box to select plantnames or accessions
# so we can print labels for plants that don't have accessions, though this could
# be a problem b/c abcd data expects 'unitid' fields but we could have a special
# case just for generating labels
# 

class ABCDImporter(Importer):
    
    def __init__(self, dialog):
        Importer.__init__(self, dialog)
        self.create_gui()
    
    
    def create_gui(self):
        # create checkboxes for format paramater options used by csv modules
        pass
    
    
    def start(self, filenames=None):
        pass
        
    def run(self, filenames):
        pass
        
        
class ABCDExporter(Exporter):
    
    def __init__(self, dialog=None):
        Exporter.__init__(self, dialog)
        if dialog is not None:
            self.create_gui()
        
    def create_gui(self):
        label = gtk.Label("Export to: ")
        self.pack_start(label)
        
        #d = gtk.FileChooserDialog(action=gtk.FILE_CHOOSER_ACTION_SAVE)
        #self.chooser_button = gtk.FileChooserButton(d)
        #self.chooser_button = gtk.FileChooserButton('Select a new filename...')
        self.chooser_button = gtk.Button("Choose a filename...")
        self.chooser_button.connect("clicked", self.on_clicked_chooser_button)
        self.pack_start(self.chooser_button)        
        ok_button = self.dialog.action_area.get_children()[1]
        ok_button.set_sensitive(False)
        self.dialog.set_focus(ok_button)
        pass
    
    
    def on_clicked_chooser_button(self, button, data=None):
        d = gtk.FileChooserDialog("Select a directory", None,
                                   gtk.FILE_CHOOSER_ACTION_SAVE,
                                  #gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
                                  (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
                                  gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
        d.run()
        filename = d.get_filename()
        if filename is not None:
            ok_button = self.dialog.action_area.get_children()[1]
            ok_button.set_sensitive(True)
            button.set_label(filename)
            self.path = filename # set it so it's available in run
        d.destroy()
    
    
    def start(self):        
        self.run(self.path)
        
    
    def run(self, filename, plants=None):
        if filename == None:
            raise ValueError("filename can not be None")            
            
        # TODO: check if filename already exists give a message to the user
        
        # if plants is None then export all plants, this could be huge 
        if plants == None:            
            plants = tables.Plants.select()
        data = abcd.plants_to_abcd(plants)
        f = open(filename, "w")
        f.write(data)
        f.close()
            
            