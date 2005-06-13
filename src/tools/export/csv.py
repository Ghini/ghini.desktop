#
# CSV Exporter
#

from tools.export import *


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
               utils.are_you_sure("%s exists, do you want to continue?" % filename):
                return
        
        path = self.chooser_button.get_label()
        meta_file = file(path + os.sep + "tables.txt", "w")
        for table_name, table in tables.iteritems():
            meta = table_name + "=" + str(table.sqlmeta._columnDict.keys()) + "\n"
            meta_file.write(meta)
            filename = filename_template % table_name
            f = file(filename, "w")
            for row in table.select():
                values = []
                values.append(row.id)
                for col in table._columns:
                    if type(col) == ForeignKey:
                        name = col.name + "ID"
                    else: name = col.name
                    values.append(getattr(row, name))
                f.write(str(values)[1:-1]+"\n")
            f.close()
        meta_file.close()