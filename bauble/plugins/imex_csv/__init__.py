#
# csv import/export
#

import os, sys, csv, traceback
import gtk.gdk
import sqlobject
from sqlobject.sqlbuilder import *
import bauble
import bauble.utils as utils
from bauble.plugins import BaubleTool, BaublePlugin, plugins, tables
from bauble.utils.log import log, debug
import bauble.utils.gtasklet as gtasklet
from bauble.utils.progressdialog import ProgressDialog

# TODO: is there a way to validate that the unicode is unicode or has the 
# proper encoding?
# TODO: i think we can do all of this easier using FormEncode
# TODO: DateTimeCol and DateTime i guess should convert to a datetime object
column_type_validators = {sqlobject.SOForeignKey: lambda x: int(x),
                          sqlobject.SOIntCol: lambda x: int(x),
                          sqlobject.SOFloatCol: lambda x: float(x),
                          sqlobject.SOBoolCol: lambda x: bool(x),
                          sqlobject.SOStringCol: lambda x: str(x),
                          sqlobject.SOEnumCol: lambda x: x,
                          #sqlobject.SOUnicodeCol: lambda x: unicode(x,'utf-8'),
                          sqlobject.SOUnicodeCol: lambda x: x,
                          sqlobject.SODateTimeCol: lambda x: x,
                          sqlobject.SODateCol: lambda x: x}


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
                    'PlantHistory.txt', "Tag.txt","TaggedObj.txt"]

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
        # TODO: how can we do batch inserts???
        # TODO: what is the best number for this the timout, we want the 
        # smallest number so that the gui is still responsive and the progress
        # dialog can updates but not too slow for inserts
        # TODO: instead of timeout on every insert maybe we should only timeout
        # every other one or something like that
        timeout = gtasklet.WaitForTimeout(8)
        for filename in filenames:
            line = None # dummy for exception handler
            try:
                path, base = os.path.split(filename)
                table_class_name, ext = os.path.splitext(base)
                table = tables[table_class_name]
                table_name = table.sqlmeta.table
                log.info('importing %s table from %s' % (table.__name__, filename))                
                yield gtasklet.Message('update_filename', dest=monitor_tasklet, value=(filename, table_class_name))
                yield timeout
                gtasklet.get_event()
                f = file(filename, "rb")
                reader = csv.DictReader(f, quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
                validators = CSVImporter._get_validators(table)
                t = table.select()
                if t.count() > 0 and not force:
                    msg = "The %s table already contains some data. If two rows "\
                          "have the same id in the import file and the database "\
                          "then the file will not import "\
                          "correctly.\n\n<i>Would you like to drop the table in the "\
                          "database first. You will lose the data in your database "\
                          "if you do this?</i>" % table_name                    
                    d = utils.create_yes_no_dialog(msg)
                    yield (gtasklet.WaitForSignal(d, "response"),
                           gtasklet.WaitForSignal(d, "close"))   
                    response = gtasklet.get_event().signal_args[0]        
                    d.destroy()
                    if force or response == gtk.RESPONSE_YES:
                        table.dropTable(ifExists=True, dropJoinTables=True, 
                                        cascade=True)
                        table.createTable()
                values = []
                lineno = 0
                for line in reader:
                    while CSVImporter.__pause:
                        yield timeout
                        gtasklet.get_event()
                    if CSVImporter.__cancel:
                        break                
                    values = {}
                    def __validate_col(col):
                        if line[col] is not '':
                            values[col] = validators[col](line[col])
                    map(__validate_col, reader.fieldnames)
                    conn = sqlobject.sqlhub.processConnection                     
                    sql = conn.sqlrepr(Insert(table_name, values=values))
                    conn.query(sql)
                    yield gtasklet.Message('update_progress', 
                                           dest=monitor_tasklet, value=1)
                    yield timeout
                    gtasklet.get_event()
                    lineno += 1
                if CSVImporter.__cancel:
                    break
            except Exception, e:
                msg = "Error importing values from %s into table %s\n\n%s\n" \
                       % (filename, table_name, line or '')   
                debug(traceback.format_exc())
                debug(msg)
                d= utils.create_message_details_dialog(msg, traceback.format_exc(), 
                                                       gtk.MESSAGE_ERROR)
                yield (gtasklet.WaitForSignal(d, "response"),
                       gtasklet.WaitForSignal(d, "close"))
                gtasklet.get_event()
                d.destroy()
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
    
        # reset flags
        CSVImporter.__cancel = False 
        error = False # this shouldn't be static no?

    
    __cancel = False # flag to cancel importing
    __pause = False  # flag to pause importing
    
    @classmethod
    def _cancel_import(klass, *args):
        msg = 'Are you sure you want to cancel importing?\n\n<i>All changes so '\
              'far will be rolled back.</i>'
        CSVImporter.__pause = True
        if utils.yes_no_dialog(msg, parent=klass.__progress_dialog):
            CSVImporter.__cancel = True
        CSVImporter.__pause = False
                            
    
    @classmethod
    def _task_monitor_progress(klass, total_lines):
        '''
        monitors the progress of CSVImporter._task_import_files and updates the
        interface accordingly
        
        import_task -- the task that this is monitoring
        total_lines -- the total number of lines in all the files we're importing
        '''
        klass.__progress_dialog = ProgressDialog(title='Importing...')
        klass.__progress_dialog.show_all()
        klass.__progress_dialog.connect_cancel(CSVImporter._cancel_import)
        bauble.app.set_busy(True)
        msgwait = gtasklet.WaitForMessages(accept=("quit", "update_progress", 
                                                   'update_filename'))
        nsteps = 0
        while True:
          yield msgwait
          msg = gtasklet.get_event()
          if msg.name == "quit":
              bauble.app.set_busy(False) 
              klass.__progress_dialog.destroy()
          elif msg.name == 'update_progress':
              nsteps += msg.value
              percent = float(nsteps)/float(total_lines)
              klass.__progress_dialog.pb.set_fraction(percent)
              klass.__progress_dialog.pb.set_text('%s of %s records' % (nsteps, total_lines))
          elif msg.name == 'update_filename':
              filename, table_name = msg.value  
              msg = 'Importing data into %s table from\n%s' % (table_name, filename)
              klass.__progress_dialog.set_message(msg)

            
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
#            if type(col) not in column_type_validators:
#                raise Exception("no validator for col " + col.name + \
#                                " with type " + str(col.__class__))           
            if col.name.upper().endswith('ID'):
                validators['%s_id' % col.name[:-2]] = column_type_validators[type(col)]
            else:
                validators[col.name] = column_type_validators[type(col)]
        validators['id'] = int        
        return validators
        
    
#    @classmethod
#    def import_file(klass, filename, table_class, force=False):        
#        '''
#        import data into a bauble database 
#        
#        filename -- the name of the file to get the data from
#        table_class -- the class of the table to import to
#        force -- import data into table regardless if the table already has
#        data in it
#        '''
#        log.info('import_file(%s, %s)' % (filename, table_class))
#        #debug('imex_csv.import_file(%s, %s)' % (filename, table))
#        f = file(filename, "rb")
#        nlines = len(file(filename).readlines())
#        reader = csv.DictReader(f, quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
#        validators = CSVImporter._get_validators()
#        t = table_class.select()
#        if t.count() > 0 and not force:
#            msg = "The %s table already contains some data. If two rows "\
#                  "have the same id in the import file and the database "\
#                  "then the file will not import "\
#                  "correctly.\n\n<i>Would you like to drop the table in the "\
#                  "database first. You will lose the data in your database "\
#                  "if you do this?</i>" % table_class.sqlmeta.table
#            if force or utils.yes_no_dialog(msg):
#                table_class.dropTable(ifExists=True, dropJoinTables=True, 
#                                cascade=True)
#                table_class.createTable()
#
#        for line in reader:
##            debug(line)
#            def __validate_col(col):
#                if line[col] == '': 
#                    line.pop(col) # pop seems to be slightly faster than del
#                else:
#                    # convert to proper type from str
#                    line[col] = validators[col](line[col])                    
#            map(__validate_col, reader.fieldnames)
#            try:                
#                table_class(**line) # add row to table
#            except Exception, e:
#                raise bauble.BaubleError("%s\n%s" % (str(e), line))
        
        
    def start(self, filenames=None, force=False, block=False):
        """
        the simplest way to import, no threads, nothing
        
        filenames -- the list of filenames to import from
        force -- import regardless if the table already has data
        block -- don't return until importing is finished
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
            monitor_task = gtasklet.run(CSVImporter._task_monitor_progress(total_lines))
            gtasklet.run(CSVImporter._task_import_files(filenames, force, monitor_task))
      
        
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
        bauble.app.set_busy(True)
        #rows = []
        #rows_append = rows.append
        for table_name, table in tables.iteritems():
            print "exporting " + table_name
            #progress.pulse()
            col_dict = {}
            header = ['id']
            for name, col in table.sqlmeta.columns.iteritems():
                if name.upper().endswith('ID'):
                    header.append('%s_id' % name[:-2])
                else:
                    header.append(name)

            col_dict = table.sqlmeta.columns
            
            rows = []
            # TODO: probably don't need to write out column names or even
            # create the file if it contains no data, could be an option
            # TODO: this is slow as dirt
            #rows.append(["id"] + col_dict.keys()[:]) # write col names
            rows.append(header) # write col names
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

# TODO: importing from the command line isn't finished, i think the only thing
# that really need to be done for it to work is to create a gobject.mainloop()
# or implement blocking in the importer to have it's own mainloop

def main():
    # should allow you to export or import from a database from the
    # command line, you would just have to pass the connection uri
    # and the name of the directory to export to
    # TODO: allow -i for import, -e for export
    # TODO: need to pass in a database connection string
    # postgres://bbg:garden@ceiba.test

    # TODO: ****** i think the only reason this isn't working is because of using the 
    # connection manager so we can either 1. figure out how to use the connection 
    # manager from a tasklet or 2. don't use the connection manager and get 
    # connection paramaters from the command line including the passwd
    
    import sys
    from sqlobject import sqlhub, connectionForURI
    from bauble.conn_mgr import ConnectionManager#Dialog
    from bauble.prefs import prefs
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option('--force', dest='force', action='store_true', 
                      default=False, help='force import')
    parser.add_option('-c', '--connection', dest='conn',
                      help='named connection from prefs')
    options, args = parser.parse_args()
        
    if len(args) == 0:
        print '** Error: need a list of files to import'
        return
    
    prefs.init() # intialize the preferences

    if options.conn is None:
        default_conn = prefs[prefs.conn_default_pref]
        cm = ConnectionManager(default_conn)
        conn_name, uri = cm.start()
        if conn_name is None: return
    else:
        params = prefs[prefs.conn_list_pref][options.conn]            
        uri = ConnectionManager().parameters_to_uri(params)
    
    sqlhub.processConnection = connectionForURI(uri)    
    sqlhub.processConnection.getConnection()
    sqlhub.processConnection = sqlhub.processConnection.transaction()    
    
    if not options.force:
        msg = 'Importing to this connection (%s) will destroy any existing data '\
              ' in the database. Are you sure this is what you want to do? ' % uri
        response = raw_input(msg)
        if response not in ('Y', 'y'):
            return
#        if not utils.yes_no_dialog(msg):
#            return
        
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
    gtasklet.run(main())
    gtk.main()
