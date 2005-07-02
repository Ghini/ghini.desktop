 #
# MySQL Importer/Exporter
#

from bauble import *
from tools.import_export import *
import sqlobject
from tables import tables

#importer = MySQLImporter
#exporter = None

class MySQLImporter(Importer):
    def __init__(self, dialog):
        Importer.__init__(self, dialog)
        self.create_gui()
    
    def create_gui(self):
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
            
        fc = gtk.FileChooserDialog("Choose file to import...",
                                  None,
                                  gtk.FILE_CHOOSER_ACTION_OPEN,
                                  (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
                                   gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT))
        fc.connect("selection-changed", on_selection_changed)
        fc.set_select_multiple(True)
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
        """
        choose a file to import, the filename should be table_name.txt
        to import to table table_name
        """
        
        #old_conn = sqlobject.sqlhub.getConnection()
        conn = sqlobject.sqlhub.getConnection()
        #old_auto = conn.autoCommit
        #conn.autoCommit = True
        for filename in filenames:
            # TODO: should probably check first that there is a table with 
            # the same name as the file in the database
                
            # read the first row of the file as the column names
            head, tail = os.path.split(filename)
            table, ext = os.path.splitext(tail)
            columns = file(filename).readline().strip()
            
            sql = "LOAD DATA LOCAL INFILE '%(file)s' " + \
                "INTO TABLE %(table)s " + \
                "FIELDS " + \
                "TERMINATED BY ',' "  + \
                "OPTIONALLY ENCLOSED BY '\"' "  + \
                'IGNORE 1 LINES '  + \
                '(%(columns)s);'
    
            filename = filename.replace('\\', '\\\\')
            q = sql % {"file": filename, 
                       "table": table, 
                       "columns": columns}
            print q
            try:
                # NOTE: if autocommit is 0 then all of this will be lost
                # if we don't sync the tables on exit
                conn.query(q)
            except Exception, e:
                # TODO: we need to do something here, if not
                # then autocommit, sensitivity and the cursor will not be reset
                print e
                raise
       
        
        #conn.autoCommit = old_auto
        # TODO: popup a message dialog that says "Success." or something
        # to indicate everything was imported without problems
        gtk.gdk.threads_enter()
        bauble.gui.window.set_sensitive(True)
        bauble.gui.window.window.set_cursor(None)
        gtk.gdk.threads_leave()