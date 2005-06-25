#
# MySQL Importer/Exporter
#

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
    
    def run(self):
        """
        choose a file to import, the filename should be table_name.txt
        to import to table table_name
        """
        
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
        fc.set_select_multiple(False)
        r = fc.run()
        filename = fc.get_filename()
        fc.destroy()
        if r == gtk.RESPONSE_CANCEL: 
            return
            
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

        print sql % {"file": filename, "table": table, "columns": columns}
        
        conn = sqlobject.sqlhub.threadConnection.getConnection()
        conn.query(sql % {"file": filename, 
                          "table": table, 
                          "columns": columns})
                                      
        # TODO: popup a message dialog that says "Success." or something
        # to indicate everything was imported without problems
        pass