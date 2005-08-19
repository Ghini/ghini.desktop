#
# csv import/export
#


import os, sys, csv, traceback, threading
import gtk.gdk
import sqlobject
#from bauble.tools.imex import *
import bauble
import bauble.utils as utils
from bauble.plugins import BaubleTool, BaublePlugin, plugins, tables

csv_format_params = {}


# TODO: how do i validate unicode ???
# TODO: i think we can do all of this easier using FormEncode
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


class CSVImporter:
    
    def start(self, filenames=None, block=False):
        """
        run the importer, if no filenames are are give then it will ask you
        for the files to import
        if there are any problems importing any of the files in filenames then
        then entire import is rolled back
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
                       
        bauble.app.gui.window.set_sensitive(False)
        bauble.app.gui.window.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))

        t = threading.Thread(target=self.run, args=(filenames, block))
        t.start()
        if block:
            t.join()
    
    
    def import_file(self, filename, table, connection):
        f = file(filename, "rb")
        reader = csv.DictReader(f, quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
                
        # create validator map
        validators = {} # TODO: look at formencode to do this
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
            
#        try:
        line = None
        for line in reader:
            for col in reader.fieldnames: # validate columns
                if line[col] == '': 
                    del line[col]
                else: line[col] = validators[col](line[col])
            table(connection=connection, **line) # add row to table
#        except Exception, e:
#            sys.stderr.write("CSVImporter.import_file() -- cold not import " \
#                             "table " + table.__name__)
#            traceback.print_exc()                 
#            raise ImportError(str(line))
        

    def run(self, filenames, block=False):
        """
        this should not be used directly but is used by start()
        
        """

        dialog = None
        # save the original connection
        old_conn = sqlobject.sqlhub.getConnection()        
        if not block: gtk.threads_enter()
        
        # TODO: connect to this cancel button so the user can stop the import
        # process and rollback any changes
        dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                          type=gtk.MESSAGE_INFO, buttons=gtk.BUTTONS_CANCEL, 
                          message_format='importing...')
        dialog.show()
        if not block: gtk.threads_leave()
        
        trans = old_conn.transaction()       
        sqlobject.sqlhub.threadConnection = trans
        
        try:
            for filename in filenames:                     
                path, base = os.path.split(filename)
                table_name, ext = os.path.splitext(base)
                # the name of the file has to match the name of the 
                # tables class
                if table_name not in tables:
                    msg = "%s table does not exist. Would you like to continue " \
                          "importing the rest of the tables?" % table_name
                    if not block: gtk.threads_enter()
                    keep_on = utils.yes_no_dialog(msg)
                    if not block: gtk.threads_leave()
                    if keep_on: continue
                    else: break            
    
                # TODO: could do something more with this to indicate progress
                # like a counter on the row number being imported
                if not block: gtk.threads_enter()
                dialog.set_markup('importing ' + table_name+ '...')
                dialog.queue_resize()
                if not block: gtk.threads_leave()
                                
                self.import_file(filename, tables[table_name], trans)
        except Exception, e:
            # TODO: should ask the user if they would like to import the 
            # rest of the tables or bail, should probably do all commits in 
            # one transaction so all data gets imported from all files 
            # successfully or nothing at all
            msg = "Error importing values from %s into table %s\n" % (filename, table_name)
            if not block: gtk.threads_enter()
            utils.message_details_dialog(msg, traceback.format_exc(), gtk.MESSAGE_ERROR)
            if not block: gtk.threads_leave()
            trans.rollback()
        else:
            trans.commit()
                
        sqlobject.sqlhub.threadConnection = old_conn
        if not block: gtk.threads_enter()
        if dialog is not None: 
            dialog.destroy()
        bauble.app.gui.window.set_sensitive(True)
        bauble.app.gui.window.window.set_cursor(None)
        if not block: gtk.threads_leave()
   
        
class CSVExporter:
        
    def start(self, path=None):
        if path == None:
            d = gtk.FileChooserDialog("Select a directory", None,
                                      gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
                                      (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
                                      gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
            response = d.run()
            path = d.get_filename()
            d.destroy()
            if response != gtk.RESPONSE_ACCEPT:
                return
        self.run(path)
        
    
    def run(self, path):
        if not os.path.exists(path):
            raise ValueError("CSVExporter: path does not exist.\n" + path) 

        #gtk.gdk.threads_enter()
        filename_template = path + os.sep +"%s.txt"
        for name in tables.keys():
            filename = filename_template % name
            if os.path.exists(filename) and not \
               utils.yes_no_dialog("%s exists, do you want to continue?" % filename):
                return
                
        #path = self.chooser_button.get_label()
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
                    if type(col) == sqlobject.ForeignKey:
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
            
#
# plugin classes
#

class CSVImportTool(BaubleTool):
    category = "Import"
    label = "Comma Separated Value"
    
    @classmethod
    def start(cls):
        c = CSVImporter()
        c.start()


class CSVExportTool(BaubleTool):
    category = "Export"
    label = "Comma Separated Value"
    
    @classmethod
    def start(cls):
        c = CSVExporter()
        c.start()

class CSVImexPlugin(BaublePlugin):
    tools = [CSVImportTool, CSVExportTool]

plugin = CSVImexPlugin