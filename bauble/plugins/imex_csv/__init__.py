#
# csv import/export
#

import os, sys, csv, traceback
import gtk.gdk
import sqlobject
import bauble
import bauble.utils as utils
from bauble.plugins import BaubleTool, BaublePlugin, plugins, tables
from bauble.utils.log import log, debug
import bauble.utils.gtasklet as gtasklet
from bauble.utils.progressdialog import ProgressDialog

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


class ImportTasklet:        
                
    def run(self, filenames, force, monitor_tasklet):
        gtasklet.run(ImportTasklet._real_run(filenams, force, monitor_tasklet))
    
    @staticmethod
    def _real_run(self, filenames, force, monitor_tasklet):
        filenames, force, monitor_tasklet = args
        '''
        a tasklet that import data into a Bauble database, this method should
        be run as a gtasklet task, see http://www.gnome.org/~gjc/gtasklet/gtasklets.html
        
        filenames -- the list of files names t
        force -- causes the data to be imported regardless if there already 
        the table already has something in it (TODO: this doesn't do anything yet)
        monitor_tasklet -- the tasklet that monitors the progress of this task
        and update the interface
        '''
        error = False        
        # TODO: what is the best number for this the timout, we want the 
        # smallest number so that the gui is still responsive and the progress
        # dialog can updates
        timeout = gtasklet.WaitForTimeout(5)
        for filename in filenames:
            line = None # dummy for exception handler
            try:
                path, base = os.path.split(filename)
                table_class_name, ext = os.path.splitext(base)
                table = tables[table_class_name]
                table_name = table.sqlmeta.table
                log.info('importing %s table from %s' % (table.__name__, filename))                
                yield gtasklet.Message('update_filename', dest=monitor_tasklet, value=(filename, table_class_name))
                #//////////////
                f = file(filename, "rb")
                reader = csv.DictReader(f, quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
                validators = CSVImporter._get_validators(table)
                t = table.select()
                if t.count() > 0:
                    msg = "The %s table already contains some data. If two rows "\
                          "have the same id in the import file and the database "\
                          "then the file will not import "\
                          "correctly.\n\n<i>Would you like to drop the table in the "\
                          "database first. You will lose the data in your database "\
                          "if you do this?</i>" % table_class.sqlmeta.table
                    if force or utils.yes_no_dialog(msg):
                        table_class.dropTable(ifExists=True, dropJoinTables=True, 
                                        cascade=True)
                        table_class.createTable()
        
                for line in reader:
                    if CSVImporter.__cancel:
                        break
                    def __validate_col(col):
                        if line[col] == '': 
                            line.pop(col) # pop seems to be slightly faster than del
                        else:
                            # convert to proper type from str
                            line[col] = validators[col](line[col])                    
                    map(__validate_col, reader.fieldnames)                             
                    lineno = 1
                    yield gtasklet.Message('update_progress', 
                                           dest=monitor_tasklet, value=lineno)

                    table(**line) # create row in table
                    yield timeout
                    gtasklet.get_event()
                    lineno += 1

            except Exception, e:
                msg = "Error importing values from %s into table %s\n\n%s\n" \
                       % (filename, table_name, line or '')
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
                
        if not error and not CSVImporter.__cancel:
            sqlobject.sqlhub.processConnection.commit()
        else:
            sqlobject.sqlhub.processConnection.rollback()
            sqlobject.sqlhub.processConnection.begin()
        yield gtasklet.Message('quit', dest=monitor_tasklet)



class ImportMonitorTasklet(gtasklet.Tasklet):
    
    def run(self, total_lines, import_task):
        gtasklet.run(ImportMonitorTasklet._real_run(total_lines, import_task))
        
    @staticmethod
    def run(total_lines, import_task):
        '''
        monitors the progress of CSVImporter._task_import_files and updates the
        interface accordingly
        
        import_task -- the task that this is monitoring
        total_lines -- the total number of lines in all the files we're importing
        '''
        dialog = ProgressDialog(title='Importing...')
        dialog.show_all()
        dialog.connect_cancel(CSVImporter._cancel_import, import_task)
        bauble.app.set_busy(True)
        msgwait = gtasklet.WaitForMessages(accept=("quit", "update_progress", 'update_filename'))
        lines_so_far = 0
        while True:
          yield msgwait
          msg = gtasklet.get_event()
          if msg.name == "quit":
              bauble.app.set_busy(False) 
              dialog.destroy()          
          elif msg.name == 'update_progress':
              lines_so_far += msg.value
              percent = float(lines_so_far)/float(total_lines)
              #debug('%s of %s: %.2f' % (lines_so_far, total_lines, percent))
              dialog.pb.set_fraction(percent)
          elif msg.name == 'update_filename':
              filename, table_name = msg.value  
              msg = 'Importing data into %s table from\n%s' % (table_name, filename)
              dialog.set_message(msg)
              #dialog.pb.set_text(filename)
              dialog.pb.set_text('importing %s...' % table_name)        


class CSVImporter:

    @staticmethod
    def sort_filenames(filenames):
        '''
        this is a mega hack so to to sort a list of filenames by
        the order they should be imported, ideally we would have
        a way to sort by dependency but that's more work, hopefully at some 
        time we'll get around to it
        '''
        sortlist = ['Continent.txt',"Country.txt","Region.txt", 
                    "BotanicalCountry.txt",
                    "BasicUnit.txt", "Place.txt",
                    "Location.txt","Family.txt","FamilySynonym.txt","Genus.txt",
                    "GenusSynonym.txt","Species.txt","SpeciesMeta.txt",
                    "SpeciesSynonym.txt","VernacularName.txt","Accession.txt",
                    "Donor.txt","Donation.txt","Collection.txt","Plant.txt",
                    "Tag.txt","TaggedObj.txt"]

        import copy
        sorted_filenames = copy.copy(sortlist)
        def compare_files(one, two):
            one_file = os.path.basename(one)
            two_file = os.path.basename(two)
            return cmp(sortlist.index(one_file), sortlist.index(two_file))
        return sorted(filenames, cmp=compare_files)


    @staticmethod
    def _task_import_files(filenames, force, monitor_tasklet):
        '''
        a tasklet that import data into a Bauble database, this method should
        be run as a gtasklet task, see http://www.gnome.org/~gjc/gtasklet/gtasklets.html
        
        filenames -- the list of files names t
        force -- causes the data to be imported regardless if there already 
        the table already has something in it (TODO: this doesn't do anything yet)
        monitor_tasklet -- the tasklet that monitors the progress of this task
        and update the interface
        '''
        error = False        
        # TODO: what is the best number for this the timout, we want the 
        # smallest number so that the gui is still responsive and the progress
        # dialog can updates
        timeout = gtasklet.WaitForTimeout(5)
        for filename in filenames:
            line = None # dummy for exception handler
            try:
                path, base = os.path.split(filename)
                table_class_name, ext = os.path.splitext(base)
                table = tables[table_class_name]
                table_name = table.sqlmeta.table
                log.info('importing %s table from %s' % (table.__name__, filename))                
                yield gtasklet.Message('update_filename', dest=monitor_tasklet, value=(filename, table_class_name))
                #//////////////
                f = file(filename, "rb")
                reader = csv.DictReader(f, quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
                validators = CSVImporter._get_validators(table)
                t = table.select()
                if t.count() > 0:
                    msg = "The %s table already contains some data. If two rows "\
                          "have the same id in the import file and the database "\
                          "then the file will not import "\
                          "correctly.\n\n<i>Would you like to drop the table in the "\
                          "database first. You will lose the data in your database "\
                          "if you do this?</i>" % table_class.sqlmeta.table
                    if force or utils.yes_no_dialog(msg):
                        table_class.dropTable(ifExists=True, dropJoinTables=True, 
                                        cascade=True)
                        table_class.createTable()
        
                for line in reader:
                    if CSVImporter.__cancel:
                        break
                    def __validate_col(col):
                        if line[col] == '': 
                            line.pop(col) # pop seems to be slightly faster than del
                        else:
                            # convert to proper type from str
                            line[col] = validators[col](line[col])                    
                    map(__validate_col, reader.fieldnames)                             
                    lineno = 1
                    yield gtasklet.Message('update_progress', 
                                           dest=monitor_tasklet, value=lineno)

                    table(**line) # create row in table
                    yield timeout
                    gtasklet.get_event()
                    lineno += 1

            except Exception, e:
                msg = "Error importing values from %s into table %s\n\n%s\n" \
                       % (filename, table_name, line or '')
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
                
        if not error and not CSVImporter.__cancel:
            sqlobject.sqlhub.processConnection.commit()
        else:
            sqlobject.sqlhub.processConnection.rollback()
            sqlobject.sqlhub.processConnection.begin()
        yield gtasklet.Message('quit', dest=monitor_tasklet)

    
    __cancel = False
    @staticmethod
    def _cancel_import(*args):
        msg = 'Are you sure you want to quit importing?\n\n<i>All changes so '\
              'far will be rolled back</i>'
        Tasklet.STATE_SUSPENDED
        if utils.yes_no_dialog(msg):
            CSVImporter.__cancel = True
              
              
        
    @staticmethod
    def _task_monitor_progress(import_task, total_lines):
        '''
        monitors the progress of CSVImporter._task_import_files and updates the
        interface accordingly
        
        import_task -- the task that this is monitoring
        total_lines -- the total number of lines in all the files we're importing
        '''
        dialog = ProgressDialog(title='Importing...')
        dialog.show_all()
        dialog.connect_cancel(CSVImporter._cancel_import, import_task)
        bauble.app.set_busy(True)
        msgwait = gtasklet.WaitForMessages(accept=("quit", "update_progress", 'update_filename'))
        lines_so_far = 0
        while True:
          yield msgwait
          msg = gtasklet.get_event()
          if msg.name == "quit":
              bauble.app.set_busy(False) 
              dialog.destroy()          
          elif msg.name == 'update_progress':
              lines_so_far += msg.value
              percent = float(lines_so_far)/float(total_lines)
              #debug('%s of %s: %.2f' % (lines_so_far, total_lines, percent))
              dialog.pb.set_fraction(percent)
          elif msg.name == 'update_filename':
              filename, table_name = msg.value  
              msg = 'Importing data into %s table from\n%s' % (table_name, filename)
              dialog.set_message(msg)
              #dialog.pb.set_text(filename)
              dialog.pb.set_text('importing %s...' % table_name)

            
    @staticmethod
    def _get_validators(table_class):
        '''        
        return a validator dictionary by looking up the column types from 
        table_class getting the validators from column_type_validators, the
        dictionary is of the format {colname: validator}
        
        table_class -- the class of the table to get the validators from
        '''
        validators = {} # TODO: look at formencode to do this
        for col in table_class.sqlmeta.columnList:
            if type(col) not in column_type_validators:
                raise Exception("no validator for col " + col.name + \
                                " with type " + str(col.__class__))                
            validators[col.name] = column_type_validators[type(col)]
        validators['id'] = int        
        return validators
        
    
    @classmethod
    def import_file(klass, filename, table_class, force=False):        
        '''
        import data into a bauble database 
        
        filename --
        table_class --
        force --
        '''
        log.info('import_file(%s, %s)' % (filename, table_class))
        #debug('imex_csv.import_file(%s, %s)' % (filename, table))
        f = file(filename, "rb")
        nlines = len(file(filename).readlines())
        reader = csv.DictReader(f, quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
        validators = CSVImporter._get_validators()
        t = table_class.select()
        if t.count() > 0:
            msg = "The %s table already contains some data. If two rows "\
                  "have the same id in the import file and the database "\
                  "then the file will not import "\
                  "correctly.\n\n<i>Would you like to drop the table in the "\
                  "database first. You will lose the data in your database "\
                  "if you do this?</i>" % table_class.sqlmeta.table
            if force or utils.yes_no_dialog(msg):
                table_class.dropTable(ifExists=True, dropJoinTables=True, 
                                cascade=True)
                table_class.createTable()

        for line in reader:
#            debug(line)
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
        
        
    def start(self, filenames=None, force=False, block=False):
        """
        the simplest way to import, no threads, nothing
        
        filenames --
        force --
        block --
        """        
        error = False # return value
        bauble.app.set_busy(True)
                
        if filenames is None:
            filenames = self._get_filenames()
        if filenames is None:
            bauble.app.set_busy(False)
            return        
        
        filenames = CSVImporter.sort_filenames(filenames)
        filename = None   # these two are here in case we get an exception
        table_name = None
        
        # TODO: use gobject main loop to block
#        if block:
#            gobject.mainloop()
                
        if block:
            self.import_all_files(filenames)
        else:
            total_lines = 0
            for filename in filenames:
                # get the total number of lines for all the files
                total_lines += len(file(filename).readlines())
            
            monitor_tasklet = ImportMonitorTasklet()
            import_tasklet = ImportTasklet()
            monitor_tasklet.run(total_lines, import_tasklet)
            import_tasklet.run(filenames, force, monitor_task)
            #monitor_task = gtasklet.run(CSVImporter._task_monitor_progress(total_lines))
            #gtasklet.run(CSVImporter._task_import_files(filenames, force, monitor_task))
      
        
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

        filename_template = path + os.sep +"%s.txt"
        for name in tables.keys():
            filename = filename_template % name
            if os.path.exists(filename) and not \
               utils.yes_no_dialog("%s exists, do you want to continue?" % filename):
                return
                
        #path = self.chooser_button.get_label()
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




def main():
    # should allow you to export or import from a database from the
    # command line, you would just have to pass the connection uri
    # and the name of the directory to export to
    # TODO: allow -i for import, -e for export
    # TODO: need to pass in a database connection string
    # postgres://bbg:garden@ceiba.test
    # TODO: if not connection is passed on the command line the open the 
    # connection manager
    import sys
    from sqlobject import sqlhub, connectionForURI
    from bauble.conn_mgr import ConnectionManager#Dialog
    from bauble.prefs import prefs
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option('--force', dest='force', action='store_true', 
                      default=False, help='force import')
    options, args = parser.parse_args()
    prefs.init() # intialize the preferences

    default_conn = prefs[prefs.conn_default_pref]
    cm = ConnectionManager(default_conn)
    conn_name, uri = cm.start()
    if conn_name is None:
        return
    
    sqlhub.processConnection = connectionForURI(uri)    
    sqlhub.processConnection.getConnection()
    sqlhub.processConnection = sqlhub.processConnection.transaction()    
    
    if not options.force:
        msg = 'Importing to this connection (%s) will destroy any existing data '\
              ' in the database. Are you sure this is what you want to do? ' % uri
        #response = raw_input(msg)
        #if response not in ('Y', 'y'):
        #    return
        if not utils.yes_no_dialog(msg):
            return
        
    # check that the database version are the same
    from bauble._app import BaubleApp
    BaubleApp.open_database(uri)
        
    bauble.plugins.load()
    importer = CSVImporter()
    print 'importing....'
    importer.start(args, force=options.force)
    sqlhub.processConnection.commit()
    print '...finished importing'

if __name__ == "__main__":
    main()