#
# CSV Exporter
#

import csv
from threading import Thread

from tools.export import *


#class CSVWorker(Thread):
#    def __init__(self):
#        pass
#        
#    def run(self):
#        pass


class CSVExporter(Exporter):
    def __init__(self, dialog):
        Exporter.__init__(self, dialog)
        self.create_gui()
        
    def create_gui(self):
        label = gtk.Label("Export to: ")
        self.pack_start(label)
        self.chooser_button = gtk.Button("Select a directory...")
        self.chooser_button.connect("clicked", self.on_clicked_chooser_button)
        self.pack_start(self.chooser_button)
        ok_button = self.dialog.action_area.get_children()[1]
        ok_button.set_sensitive(False)
        self.dialog.set_focus(ok_button)
    

    def on_clicked_chooser_button(self, button, data=None):
        d = gtk.FileChooserDialog("Select a directory", None,
                                  gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
                                  (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
                                  gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
        d.run()
        filename = d.get_filename()
        if filename is not None:
            ok_button = self.dialog.action_area.get_children()[1]
            ok_button.set_sensitive(True)
            button.set_label(filename)
        d.destroy()
    
    
    def export(self):
        path = self.chooser_button.get_label()
        filename_template = path + os.sep +"%s.txt"
        for name in tables.keys():
            filename = filename_template % name
            if os.path.exists(filename) and not \
               utils.yes_no_dialog("%s exists, do you want to continue?" % filename):
                return
                
        path = self.chooser_button.get_label()
        #progress = utils.ProgressDialog()
        #progress.show_all()
    
        for table_name, table in tables.iteritems():
            #progress.pulse()
            col_dict = table.sqlmeta._columnDict
            rows = []
            # TODO: probably don't need to write out column names or even
            # create the file if it contains no data, could be an option
            rows.append(["id"] + col_dict.keys()[:]) # write col names
            for row in table.select():
                values = []
                values.append(row.id)
                #values[0] = row.id
                for name, col in col_dict.iteritems():
                    if type(col) == ForeignKey:
                        name = name+"ID"
                    v = getattr(row, name)
                    values.append(v)
                rows.append(values)
            f = file(filename_template % table_name, "wb")
            writer = csv.writer(f, quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
            writer.writerows(rows)
        f.close()
        #progress.destroy()
            
        
    def exportOLD(self):        
        path = self.chooser_button.get_label()
        filename_template = path + os.sep +"%s.txt"
        for name in tables.keys():
            filename = filename_template % name
            if os.path.exists(filename) and not \
               utils.yes_no_dialog("%s exists, do you want to continue?" % filename):
                return
        
        path = self.chooser_button.get_label()
        progress = utils.ProgressDialog()
        progress.show_all()
        for table_name, table in tables.iteritems():
            progress.pulse()
            filename = filename_template % table_name
            f = file(filename, "w")
            col_dict = table.sqlmeta._columnDict
            names = ["id"] + col_dict.keys()[:] # id not in the dict
            f.write(str(names) + "\n")
            for row in table.select():
                values_str = '%s' % row.id
                for name, col in col_dict.iteritems():
                    values_str += "|" # delimeter
                    if type(col) == ForeignKey:
                        name = name + "ID"
                    v = getattr(row, name)
                    if type(v) == str:
                        values_str += '"%s"' % v
                    elif v is not None: values_str += '%s' % v
                f.write(values_str + "\n")
            f.close()
        progress.destroy()