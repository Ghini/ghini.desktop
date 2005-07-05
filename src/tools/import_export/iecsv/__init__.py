


from tools.import_export import *
import csv
import sqlobject
from tables import tables
import gtk.gdk

from bauble import *

#import bauble
#importer = CSVImporter
#exporter = CSVExporter

csv_format_params = {}

class CSVImporter(Importer):
    
    def __init__(self, dialog):
        Importer.__init__(self, dialog)
        self.create_gui()
    
    
    def create_gui(self):
        # create checkboxes for format paramater options used by csv modules
        pass
    
    
    def start(self):
        def on_selection_changed(filechooser, data=None):
            """
            only make the ok button sensitive if the selection is a file
            """
            f = filechooser.get_preview_filename()
            if f is None: return
            ok = filechooser.action_area.get_children()[1]
            ok.set_sensitive(os.path.isfile(f))
        fc = gtk.FileChooserDialog("Choose file(s) to import...",
                                  None,    
                                  gtk.FILE_CHOOSER_ACTION_OPEN,
                                  (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
                                   gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT))
        fc.set_select_multiple(True)
        fc.connect("selection-changed", on_selection_changed)
        r = fc.run()
        if r != gtk.RESPONSE_ACCEPT:
            fc.destroy()
            return
        bauble.gui.window.set_sensitive(False)
        bauble.gui.window.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
        filenames = fc.get_filenames()
        fc.destroy()
        t = threading.Thread(target=self.run, args=(filenames,))
        t.start()
    
    
    def run(self, filenames):
        print "CSVImporter.run()"
        # save the original connection
        old_conn = sqlobject.sqlhub.getConnection()
        for filename in filenames:
            # create a new transaction/connection for each table
            trans = old_conn.transaction()
            sqlobject.sqlhub.threadConnection = trans
            path, base = os.path.split(filename)
            table_name, ext = os.path.splitext(base)
            table = tables[table_name]
            print "importing table: " + table_name + "..."
            f = file(filename, "rb")
            reader = csv.DictReader(f, quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
            try:
                for line in reader:
                    # convert int columns to integer types
                    for col in table.sqlmeta._columns:
                        if col.__class__ == sqlobject.SOIntCol:
                            line[col.name] = int(line[col.name])
                    # add row to table
                    table(connection=trans, **line)
            except Exception, e:
                # TODO: should ask the user if they would like to import the 
                # rest of the tables or bail, should probably do all commits in 
                # one transaction so all data gets imported from all files 
                # successfully or nothing at all
                msg = "Error importing values from %s into table %s" % (filename, table_name)
                print line
                print e
                utils.message_dialog(msg)
                trans.rollback()
            else:
                # everything ok for this table, commit
                trans.commit()
        sqlobject.sqlhub.threadConnection = old_conn
        gtk.gdk.threads_enter()
        bauble.gui.window.set_sensitive(True)
        bauble.gui.window.window.set_cursor(None)
        gtk.gdk.threads_leave()
        
        
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
            self.path = filename # set it so it's available in run
        d.destroy()
    
    def start(self):
        self.run()
        
    
    def run(self):
        if self.path == None:
            return
        #gtk.gdk.threads_enter()
        filename_template = self.path + os.sep +"%s.txt"
        for name in tables.keys():
            filename = filename_template % name
            if os.path.exists(filename) and not \
               utils.yes_no_dialog("%s exists, do you want to continue?" % filename):
                return
                
        path = self.chooser_button.get_label()
        #gtk.gdk.threads_leave()
        #progress = utils.ProgressDialog()
        #progress.show_all()
    
        for table_name, table in tables.iteritems():
            print "exporting " + table_name
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
        print 'exporting completed.'
        #progress.destroy()
            