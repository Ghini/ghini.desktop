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
from bauble.utils.log import log, debug

csv_format_params = {}

# TODO: some sort of asynchronous io, see gobject.io_add_watch, 
# http://www.async.com.br/faq/pygtk/index.py?req=show&file=faq20.016.htp

# TODO: how do i validate unicode ???
# TODO: i think we can do all of this easier using FormEncode
# TODO: DateTimeCol and DateTime i guess should convert to a datetime object
column_type_validators = {sqlobject.SOForeignKey: lambda x: int(x),
                          sqlobject.SOIntCol: lambda x: int(x),
                          sqlobject.SOFloatCol: lambda x: float(x),
                          sqlobject.SOBoolCol: lambda x: bool(x),
                          sqlobject.SOStringCol: lambda x: str(x),
                          sqlobject.SOEnumCol: lambda x: x,
                          sqlobject.SOUnicodeCol: lambda x: unicode(x,'utf-8'),
                          sqlobject.SODateTimeCol: lambda x: x,
                          sqlobject.SODateCol: lambda x: x}

class CSVImporter:

    
    def start(self, filenames=None):
        """
        the simplest way to import, no threads, nothing
        """        
        
        error = False # return value
        bauble.app.set_busy(True)
                
        if filenames is None:
            filenames = self._get_filenames()
        if filenames is None:
            bauble.app.set_busy(False)
            return        
        
        filename = None   # these two are here in case we get an exception
        table_name = None
        for filename in filenames:
            try:
                path, base = os.path.split(filename)
                table_class_name, ext = os.path.splitext(base)
                table = tables[table_class_name]
                table_name = table.sqlmeta.table
#                import time
#                t = time.clock()
                self.import_file(filename, table)
#                debug(time.clock() - t)
            except Exception, e:
                msg = "Error importing values from %s into table %s\n" \
                       % (filename, table_name)
                utils.message_details_dialog(msg, traceback.format_exc(), 
                                             gtk.MESSAGE_ERROR)            
                error = True
                break
            else:
                # this gets pass some problem when import tables with id's
                # into postgres, the table_name_id_seq doesn't get set to the
                # max value so subsequent inserts to the table won't give
                # unique id numbers
                if sqlobject.sqlhub.processConnection.dbName == "postgres":
                    sql = "SELECT max(id) FROM %s" % table_name
                    max = sqlobject.sqlhub.processConnection.queryOne(sql)[0]                    
                    if max is not None:
                        sql = "SELECT setval('%s_id_seq', %d);" % \
                              (table_name, max+1)
                        sqlobject.sqlhub.processConnection.query(sql)    
                
        bauble.app.set_busy(False)
        if not error:
            sqlobject.sqlhub.processConnection.commit()
        else:
            sqlobject.sqlhub.processConnection.rollback()
            sqlobject.sqlhub.processConnection.begin()
        return not error
        
        
    def import_file(self, filename, table_class):
#        debug('imex_csv.import_file(%s, %s)' % (filename, table))
        f = file(filename, "rb")
        reader = csv.DictReader(f, quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
        # create validator map
        validators = {} # TODO: look at formencode to do this
        for col in table_class.sqlmeta.columnList:
            if type(col) not in column_type_validators:
                raise Exception("no validator for col " + col.name + \
                                " with type " + str(col.__class__))                
            validators[col.name] = column_type_validators[type(col)]
        validators['id'] = int
        
        t = table_class.select()
        if t.count() > 0:
            msg = "The %s table already contains some data. If two rows "\
                  "have the same id in the import file and the database "\
                  "then the file will not import "\
                  "correctly.\n\n<i>Would you like to drop the table in the "\
                  "database first. You will lose the data in your database "\
                  "if you do this?</i>" % table_class.sqlmeta.table
            if utils.yes_no_dialog(msg):
                table_class.dropTable(ifExists=True, dropJoinTables=True, 
                                cascade=True)
                table_class.createTable()

        
        # testing a  couple of different implementations here, the 
        # considerations here are
        # 1. does map() help here...not really
        # 2. the line[col] = validators[col](line[col]) is hardly any 
        # overhead
        # 3. most the of the time is spent in creating the table row so
        # there might not be much for me to do here
        # 4. might be worthwhile to put this code in a standalone script
        # and test it with profile to see where the time is really spent        
        # 5. i don't know if there's any penalties with the way we pass  the 
        # arguments using **line, this would be something worthile to check
        # in a script
        if True:
            # this is me playing around
            for line in reader:
                def __validate_col(col):
                    if line[col] == '': 
                        line.pop(col) # pop seems to be slightly faster than del
                    else:
                        # convert to proper type from str
                        line[col] = validators[col](line[col])                    
                map(__validate_col, reader.fieldnames)
                try:
                    table_class(**line) # add row to table
                except Exception, e:
                    raise bauble.BaubleError("%s\n%s" % (str(e), line))
        else:
            # this is the original implementation
            for line in reader:
                for col in reader.fieldnames:
                    if line[col] == '': 
                        line.pop(col) # pop seems to be slightly faster than del
                    else:
                        # convert to proper type from str
                        line[col] = validators[col](line[col])                    
                try:
                    table_class(**line) # add row to table
                except Exception, e:
                    raise bauble.BaubleError("%s\n%s" % (str(e), line))
            
            
    def _get_filenames(self):
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
            return None        
        filenames = fc.get_filenames()
        fc.destroy()
        return filenames

        
    def on_response(self, widget, response, data=None):
        debug('on_response')
        debug(response)
        
                
# TODO: should use sqlobject.fromDatabase() to create the schema
# incase  you want to export a database with a different version 
# than the version of bauble you are using
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
    
        #bauble.app.gui.window.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
        bauble.app.set_busy(True)
        #rows = []
        #rows_append = rows.append
        for table_name, table in tables.iteritems():
            print "exporting " + table_name
            #progress.pulse()
            col_dict = table.sqlmeta.columns
            rows = []
            # TODO: probably don't need to write out column names or even
            # create the file if it contains no data, could be an option
            # TODO: this is slow as dirt
            rows.append(["id"] + col_dict.keys()[:]) # write col names
            rows_append = rows.append
            for row in table.select():                                
                values = []
                values.append(row.id) # id is always first
                map(lambda col: values.append(getattr(row, col)), col_dict)
                rows_append(values)
            f = file(filename_template % table_name, "wb")
            writer = csv.writer(f, quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
            writer.writerows(rows)
        f.close()
        bauble.app.set_busy(False)
        #bauble.app.gui.window.window.set_cursor(None)
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


if __name__ == "__main__":
    # should allow you to export or import from a database from the
    # command line, you would just have to pass the connection uri
    # and the name of the directory to export to
    pass
