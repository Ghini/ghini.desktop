#
# csv import/export
#


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


# TODO: how do i validate unicode ???
column_type_validators = {sqlobject.SOForeignKey: lambda x: int(x),
                          sqlobject.SOIntCol: lambda x: int(x),
                          sqlobject.SOBoolCol: lambda x: bool(x),
                          sqlobject.SOStringCol: lambda x: str(x),
                          sqlobject.SOUnicodeCol: lambda x: x
#                          sqlobject.SOUnicodeCol: lambda x: unicode(x)
                          }
                             
type_validators = {int: lambda x: int(x),
                   str: lambda x: str(x),
                   bool: lambda x: bool(x),
                   unicode: lambda x: x}
                   #unicode: lambda x: unicode(x, 'latin-1')}
                   #unicode: lambda x: unicode(x, 'utf-8')}

# TODO: it would be easier to create this gui in glade

class CSVImporter(Importer):
    
    def __init__(self, dialog):
        Importer.__init__(self, dialog)
        self.create_gui()
    
    
    def create_gui(self):
        # create checkboxes for format paramater options used by csv modules
        pass
    
    
    def start(self, filenames=None):
        """
        run the importer, if no filenames are are give then it will ask you
        for the files to import
        """
        # TODO: this could be part of the gui rather so that the file are choses
        # before 'OK' is clicked, we could have a table with two columns with
        # the left side the filenames and the right side the 'guessed' table name
        # but with a drop down to change the table, each row could also have an
        # expand arrow that when expanded peeks at the file for the columns and 
        # shows the column mapping and if there are any errors
        # mapping 
        if filenames is None:
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
            filenames = fc.get_filenames()
            fc.destroy()
                
        bauble.gui.window.set_sensitive(False)
        bauble.gui.window.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
        t = threading.Thread(target=self.run, args=(filenames,))
        t.start()
    
    
    def import_file(self, filename, table, connection):
        f = file(filename, "rb")
        reader = csv.DictReader(f, quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
                
        # create validator map
        validators = {}
        #for col in table.sqlmeta._columns:
        for col in table.sqlmeta.columnList:
            if type(col) not in column_type_validators:
                raise Exception("no validator for col" + col.name + \
                                " with type " + str(col.__class__))                
            validators[col.name] = column_type_validators[type(col)]
#            if type(col) == sqlobject.SOForeignKey or \
#               type(col) == sqlobject.SOIntCol:
#                validators[col.name] = type_validators[int]
#            elif type(col) == sqlobject.SOStringCol:                    
#                validators[col.name] = type_validators[str]
#            elif type(col) == sqlobject.SOUnicodeCol:
#                validators[col.name] = type_validators[unicode]       
#            elif type(col) == sqlobject.SOUnicodeCol:
#                validators[col.name] = type_validators[unicode]       
#            else:
#                raise Exception("no validator for col" + col.name + \
#                                " with type " + str(col.__class__))
        validators['id'] = type_validators[int]
            
        try:
            line = None
            for line in reader:
                for col in reader.fieldnames: # validate columns
                    if line[col] == '': 
                        del line[col]
                    else: line[col] = validators[col](line[col])
                table(connection=connection, **line) # add row to table
        except Exception, e:
            sys.stderr.write("CSVImporter.import_file() -- cold not import table" + table)
            raise ImportError(str(line))
        
            
    def run(self, filenames):
        """
        this should not be used directly but is used by start()
        """                
        # save the original connection
        old_conn = sqlobject.sqlhub.getConnection()        
        gtk.threads_enter()
        
        # TODO: connect to this cancel button so the user can stop the import
        # process and rollback any changes
        dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                          type=gtk.MESSAGE_INFO, buttons=gtk.BUTTONS_CANCEL, 
                          message_format='importing...')
        dialog.show()
        gtk.threads_leave()
        
        trans = old_conn.transaction()       
        sqlobject.sqlhub.threadConnection = trans
        
        for filename in filenames:     
            # create a new transaction/connection for each table
            
            path, base = os.path.split(filename)
            table_name, ext = os.path.splitext(base)
            # the name of the file has to match the name of the 
            # tables class
            if table_name not in tables:
                msg = "%s table does not exist. Would you like to continue " \
                      "importing the rest of the tables?" % table_name
                gtk.threads_enter()
                keep_on = utils.yes_no_dialog(msg)
                gtk.threads_leave()
                if keep_on: continue
                else: break            

            # TODO: could do something more with this to indicate progress
            # like a counter on the row number being imported
            gtk.threads_enter()
            dialog.set_markup('importing ' + table_name+ '...')
            dialog.queue_resize()
            gtk.threads_leave()
                            
            try:
                self.import_file(filename, tables[table_name], trans)
            except Exception, e:
                # TODO: should ask the user if they would like to import the 
                # rest of the tables or bail, should probably do all commits in 
                # one transaction so all data gets imported from all files 
                # successfully or nothing at all
                msg = "Error importing values from %s into table %s\n" % (filename, table_name)
                
                sys.stderr.write(msg)
                sys.stderr.write(str(e) + '\n')
                trans.rollback()
            else:
                trans.commit()
                
        sqlobject.sqlhub.threadConnection = old_conn
        gtk.gdk.threads_enter()
        dialog.destroy()
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
            col_dict = table.sqlmeta.columns
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
            