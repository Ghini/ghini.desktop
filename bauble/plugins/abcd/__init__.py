#
# ABCD import/exporter
#

from bauble.plugins import BaublePlugin, BaubleTool, plugins
#from bauble.tools.imex import *
import csv
import gtk.gdk
import bauble.plugins.imex_abcd.abcd

# NOTE: see biocase provider software for reading and writing ABCD data
# files, already downloaded software to desktop

# TODO: should have a command line argument to create labels without starting 
# the full bauble interface, after creating the labels it should automatically 
# open the whatever ever view is associated with pdf files
# e.g bauble -labels "select string"
# bauble -labels "block=4"
# bauble -label "acc=1997"
#
# TODO: create label make in the tools that show a dialog with an entry
# the entry is for a search string that then returns a list of all the labels
# that'll be made with checkboxess next to them to de/select the ones you 
# don't want to print, could also have a check box to select species or 
# accessions so we can print labels for plants that don't have accessions, 
# though this could be a problem b/c abcd data expects 'unitid' fields but 
# we could have a special case just for generating labels
# 

class ABCDImporter:

    def start(self, filenames=None):
        pass
        
    def run(self, filenames):
        pass
        
    
class ABCDExporter:
    
    def start(self, filename=None, plants=None):
        if filename == None: # no filename, ask the user
            d = gtk.FileChooserDialog("Choose a file to export to...", None,
                                      gtk.FILE_CHOOSER_ACTION_SAVE,
                                      (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
                                       gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
            response = d.run()
            filename = d.get_filename()
            d.destroy()
            if response != gtk.RESPONSE_ACCEPT or filename == None:
                return
        self.run(filename, plants)
        
    
    def run(self, filename, plants=None):
        if filename == None:
            raise ValueError("filename can not be None")            
            
        # TODO: check if filename already exists give a message to the user
        
        # if plants is None then export all plants, this could be huge 
        if plants == None:            
            plants = plugins.tables["Plant"].select()
        data = abcd.plants_to_abcd(plants)
        f = open(filename, "w")
        f.write(data)
        f.close()
        
        
class ABCDImportTool(BaubleTool):
    category = "Import"
    label = "ABCD"

    @classmethod
    def start(cls):
        ABCDImporter().start()
    
    
class ABCDExportTool(BaubleTool):
    category = "Export"
    label = "ABCD"
    
    @classmethod
    def start(cls):
        ABCDExporter().start()
    

class ABCDImexPlugin(BaublePlugin):
    #tools = [ABCDImportTool, ABCDExportTool]
    tools = [ABCDExportTool]
    depends = ["PlantsPlugin"]
plugin = ABCDImexPlugin
            
            
