#
# exporter module
#

import gtk
import sys, os
from sqlobject import *
from tables import tables
import utils

# TODO: load a list of all exporters, or require the exporters to register
# themselves with us, right now just hard code them in
#
# TODO: convert this to use threading, could just include the threading
# in the exporter class and have the Exporter subclasses be the workers,
# then the progress dialog could be done one time

class ExportDialog(gtk.Dialog):
    def __init__(self, title="Export", parent=None,
                 flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                 buttons=(gtk.STOCK_OK, gtk.RESPONSE_OK,
                          gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)):
        gtk.Dialog.__init__(self, title, parent, flags, buttons)
        self.current_exporter = None
        self.create_gui()
        self.connect("response", self.on_response)
        

    def create_gui(self):
        self.vbox.set_spacing(10)
        export_type_combo = gtk.combo_box_new_text()
        export_type_combo.append_text("Comma Separated Values")
        export_type_combo.connect("changed", self.on_changed_export_type_combo)
        self.vbox.pack_start(export_type_combo)
        
        sep = gtk.HSeparator()
        self.vbox.pack_start(sep, False, False)
        
        # now that everything is created set the active exporter
        export_type_combo.set_active(0)
        
        self.show_all()

    
    def on_changed_export_type_combo(self, combo, data=None):        
        if self.current_exporter is not None:
            self.vbox.remove(self.current_expoter)
        self.current_exporter = ExporterFactory.createExporter(combo.get_active_text(), self)
        self.vbox.pack_start(self.current_exporter)
        self.show_all()


    def on_response(self, dialog, response, data=None):
        if response == gtk.RESPONSE_OK:
            self.current_exporter.export()
        

class ExporterFactory:
    
    def createExporter(exporter_type, dialog):
        if exporter_type == "Comma Separated Values":
            import csvexporter
            return csvexporter.CSVExporter(dialog)
    createExporter = staticmethod(createExporter)
        

class Exporter(gtk.VBox):
    def __init__(self, dialog):
        gtk.VBox.__init__(self)
        self.dialog = dialog
    
    def export(self):
        raise NotImplented()
                    
        
# for testing, though you can export without a connection to
# a database
if __name__ == "__main__":
    d = ExportDialog()
    d.run()
    d.destroy()
    