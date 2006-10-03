#
# csv import/export
#

import os, sys, csv, traceback, itertools
import gtk.gdk, gobject
from sqlalchemy import *
import bauble
import bauble.utils as utils
from bauble.plugins import BaubleTool, BaublePlugin, plugins, tables
from bauble.utils.log import log, debug
import bauble.utils.gtasklet as gtasklet
from bauble.utils.progressdialog import ProgressDialog

# TODO: ****** important *****
# right now exporting will only export those tables that are registered through
# plugins and won't *see* the other tables that aren't part of any plugin 
# or attached to and SA metadata object, we really should try to get all the
# tables and dump everything
# *****************************


# TODO: is there a way to validate that the unicode is unicode or has the 
# proper encoding?
# TODO: i think we can do all of this easier using FormEncode
# TODO: DateTimeCol and DateTime i guess should convert to a datetime object
#column_type_validators = {sqlobject.SOForeignKey: lambda x: int(x),
#                          sqlobject.SOIntCol: lambda x: int(x),
#                          sqlobject.SOFloatCol: lambda x: float(x),
#                          sqlobject.SOBoolCol: lambda x: bool(x),
#                          sqlobject.SOStringCol: lambda x: str(x),
#                          sqlobject.SOEnumCol: lambda x: x,
#                          #sqlobject.SOUnicodeCol: lambda x: unicode(x,'utf-8'),
#                          sqlobject.SOUnicodeCol: lambda x: x,
#                          sqlobject.SODateTimeCol: lambda x: x,
#                          sqlobject.SODateCol: lambda x: x}


QUOTE_STYLE = csv.QUOTE_MINIMAL
QUOTE_CHAR = '"'

class CSVImporter:

    def __init__(self):
        self.__error = False  # flag to indicate error on import
        self.__cancel = False # flag to cancel importing
        self.__pause = False  # flag to pause importing

#    @staticmethod
#    def sort_filenames(filenames):
#        '''
#        this is a mega hack so to to sort a list of filenames by
#        the order they should be imported, ideally we would have
#        a way to sort by dependency but that's more work, hopefully at some 
#        time we'll get around to it
#        '''
#        sortlist = ['Continent.txt',"Country.txt","Region.txt", 
#                    "BotanicalCountry.txt",
#                    "BasicUnit.txt", "Place.txt",
#                    "Location.txt","Family.txt","FamilySynonym.txt","Genus.txt",
#                    "GenusSynonym.txt","Species.txt","SpeciesMeta.txt",
#                    "SpeciesSynonym.txt","VernacularName.txt","Accession.txt",
#                    "Donor.txt","Donation.txt","Collection.txt","Plant.txt",
#                    'PlantHistory.txt', "Tag.txt","TaggedObj.txt"]
#
#        import copy
#        sorted_filenames = copy.copy(sortlist)
#        def compare_files(one, two):
#            one_file = os.path.basename(one)
#            two_file = os.path.basename(two)
#            return cmp(sortlist.index(one_file), sortlist.index(two_file))
#        return sorted(filenames, cmp=compare_files)


    def _task_import_files(self, filenames, force, monitor_tasklet):
        '''
        a tasklet that import data into a Bauble database, this method should
        be run as a gtasklet task, see http://www.gnome.org/~gjc/gtasklet/gtasklets.html
        
        filenames -- the list of files names t
        force -- causes the data to be imported regardless if there already 
        the table already has something in it (TODO: this doesn't do anything yet)
        monitor_tasklet -- the tasklet that monitors the progress of this task
        and update the interface
        '''
        session = create_session()
        timeout = gtasklet.WaitForTimeout(12)
        
        def chunk(iterable, n):
            '''
            return iterable in chunks of size n
            '''
            chunk = []
            ctr = 0
            for it in iterable:
                chunk.append(it)            
                ctr += 1
                if ctr >= n:
                    yield chunk
                    chunk = []
                    ctr = 0
            yield chunk
        
 
        # sort the tables and filenames by dependency so we can import
        filename_dict = {}
        for f in filenames:            
            path, base = os.path.split(f)
            table_name, ext = os.path.splitext(base)        
            filename_dict[table_name] = f

        sorted_tables = []
        for table in default_metadata.table_iterator():
            try:
                sorted_tables.append((table, filename_dict.pop(table.name)))
            except KeyError, e: # table.name in list of filenames
                pass
            
        if len(filename_dict) > 0:
            msg = 'Could not match all filenames to table names.\n\n%s' % filename_dict
            d = utils.create_yes_no_dialog(msg)
            yield (gtasklet.WaitForSignal(d, "response"),
                   gtasklet.WaitForSignal(d, "close"))   
            response = gtasklet.get_event().signal_args[0]        
            d.destroy()
            
        for table, filename in sorted_tables:
            log.info('importing %s table from %s' % (table.name, filename))                
            yield gtasklet.Message('update_filename', dest=monitor_tasklet, value=(filename, table.name))
            yield timeout
            gtasklet.get_event()
            f = file(filename, "rb")
            reader = csv.DictReader(f, quotechar=QUOTE_CHAR, quoting=QUOTE_STYLE)
            if table.count().scalar() and not force:
                msg = "The %s table already contains some data. If two rows "\
                      "have the same id in the import file and the database "\
                      "then the file will not import "\
                      "correctly.\n\n<i>Would you like to drop the table in the "\
                      "database first. You will lose the data in your database "\
                      "if you do this?</i>" % table.name                    
                d = utils.create_yes_no_dialog(msg)
                yield (gtasklet.WaitForSignal(d, "response"),
                       gtasklet.WaitForSignal(d, "close"))   
                response = gtasklet.get_event().signal_args[0]        
                d.destroy()
                if force or response == gtk.RESPONSE_YES:
                    table.drop()
                    table.create()
            
            insert = table.insert()
            # chop the lines from reader into chunks
            for slice in chunk(reader, 127): 
                while self.__pause:
                    yield timeout
                    gtasklet.get_event()
                if self.__cancel:
                    break  
                def do(insert, values):
                    try:
                        # make a copy of each item in values, removing
                        # all the empty strings                  
                        # TODO: we should be able to speed this up
                        def cleanup(row):
                            clean = {}
                            for key, val in row.iteritems():
                                if val is not '':
                                    clean[key] = val
                            return clean
                        insert.execute(map(cleanup, values))
                    except Exception, e:
                        debug(values)
                        self.__error = True
                        self.__error_exc = e
                        self.__error_traceback_str = traceback.format_exc()
                        self.__cancel = True
                if len(slice) > 0:
                    gobject.idle_add(do, insert, slice)                    
                yield gtasklet.Message('update_progress', 
                                       dest=monitor_tasklet, value=len(slice))
                yield timeout
                gtasklet.get_event()

        if self.__error:
            debug(str(self.__error_exc))
            debug(self.__error_traceback_str)
            if hasattr(self.__error_exc, 'orig'):
                msg = self.__error_exc.orig
            else:
                msg = self.__error_exc
            d = utils.create_message_details_dialog('Error:  %s' % msg,
                                                    self.__error_traceback_str,
                                                    type=gtk.MESSAGE_ERROR,
                                                    parent=self.__progress_dialog)
            yield (gtasklet.WaitForSignal(d, "response"),
                   gtasklet.WaitForSignal(d, "close"))
            gtasklet.get_event()
            d.destroy()
        elif not self.__error and not self.__cancel:
            session.flush()

        session.close()
        yield gtasklet.Message('quit', dest=monitor_tasklet)
    
    
    def _cancel_import(self, *args):
        '''
        called by the progress dialog to cancel the current import
        '''
        msg = 'Are you sure you want to cancel importing?\n\n<i>All changes so '\
              'far will be rolled back.</i>'
        self.__pause = True
        if utils.yes_no_dialog(msg, parent=self.__progress_dialog):
            self.__cancel = True
        self.__pause = False
                            

    def _task_monitor_progress(self, total_lines):
        '''
        monitors the progress of CSVImporter._task_import_files and updates the
        interface accordingly
        
        import_task -- the task that this is monitoring
        total_lines -- the total number of lines in all the files we're importing
        '''
        print('_task_monitor_progress')
        self.__progress_dialog = ProgressDialog(title='Importing...')
        self.__progress_dialog.show_all()
        self.__progress_dialog.connect_cancel(self._cancel_import)
        bauble.app.set_busy(True)
        msgwait = gtasklet.WaitForMessages(accept=("quit", "update_progress", 
                                                   'update_filename'))
        print('_task_monitor_progress 2')
        nsteps = 0
        while True:
          yield msgwait
          msg = gtasklet.get_event()
          if msg.name == "quit":
              bauble.app.set_busy(False) 
              self.__progress_dialog.destroy()
          elif msg.name == 'update_progress':
              nsteps += msg.value
              percent = float(nsteps)/float(total_lines)
              self.__progress_dialog.pb.set_fraction(percent)
              self.__progress_dialog.pb.set_text('%s of %s records' % (nsteps, total_lines))
          elif msg.name == 'update_filename':
              filename, table_name = msg.value  
              msg = 'Importing data into %s table from\n%s' % (table_name, filename)
              self.__progress_dialog.set_message(msg)
          elif msg.name == 'insert_error':
              CSVImporter.__cancel = True
              utils.message_dialog('insert error')
              
                          
#    @staticmethod
#    def _get_validators(table_class):
#        '''        
#        return a validator dictionary by looking up the column types from 
#        table_class getting the validators from column_type_validators, the
#        dictionary is of the format {colname: validator}
#        
#        table_class -- the class of the table to get the validators from
#        '''
#        validators = {} # TODO: look at formencode to do this
#        for col in table_class.sqlmeta.columnList:
##            if type(col) not in column_type_validators:
##                raise Exception("no validator for col " + col.name + \
##                                " with type " + str(col.__class__))           
#            if col.name.endswith('ID'):
#                validators['%s_id' % col.name[:-2]] = column_type_validators[type(col)]
#            else:
#                validators[col.name] = column_type_validators[type(col)]
#        validators['id'] = int        
#        return validators
        
        
    def start(self, filenames=None, force=False, block=False):
        """
        the simplest way to import, no threads, nothing
        
        filenames -- the list of filenames to import from
        force -- import regardless if the table already has data
        block -- TODO: don't return until importing is finished
        """        
        error = False # return value
        bauble.app.set_busy(True)
                
        if filenames is None:
            filenames = self._get_filenames()
        if filenames is None:
            bauble.app.set_busy(False)
            return        
        
        #filenames = CSVImporter.sort_filenames(filenames)
        #filename = None   # these two are here in case we get an exception
        #table_name = None
        
        # TODO: use gobject main loop to block
#        if block:
#            gobject.mainloop()
            
        # TODO: block doesn't work at all    
        if block:
            self.import_all_files(filenames)
        else:
            total_lines = 0
            for filename in filenames:
                # get the total number of lines for all the files
                total_lines += len(file(filename).readlines())            
            monitor_task = gtasklet.run(self._task_monitor_progress(total_lines))
            gtasklet.run(self._task_import_files(filenames, force, monitor_task))
      
        
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
        replace = lambda s: s.replace('\n', '\\n')



        for table_name, table in default_metadata.tables.iteritems():
            log.info("exporting %s" % table_name)
            rows = []
            # TODO: probably don't need to write out column names or even
            # create the file if it contains no data, could be an option
            rows.append(table.c.keys()) # write col names
            for row in table.select().execute():
                values = map(replace, row.values())
                rows.append(values)
            f = file(filename_template % table_name, "wb")
            #writer = csv.writer(f, quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
            writer = csv.writer(f, quotechar=QUOTE_CHAR, quoting=QUOTE_STYLE)
            writer.writerows(rows)
            f.close()

        bauble.app.set_busy(False)
        
        
        
#    def run(self, path):        
#        if not os.path.exists(path):
#            raise ValueError("CSVExporter: path does not exist.\n" + path) 
#
#        filename_template = path + os.sep +"%s.txt"
#        for name in tables.keys():
#            filename = filename_template % name
#            if os.path.exists(filename) and not \
#               utils.yes_no_dialog("%s exists, do you want to continue?" % filename):
#                return                
#        bauble.app.set_busy(True)
#        #rows = []
#        #rows_append = rows.append
#        for table_name, table in tables.iteritems():
#            print "exporting " + table_name
#            #progress.pulse()
#            col_dict = {}
#            header = ['id']
#            for name, col in table.sqlmeta.columns.iteritems():
#                if name.endswith('ID'):
#                    header.append('%s_id' % name[:-2])
#                else:
#                    header.append(name)
#
#            col_dict = table.sqlmeta.columns
#            
#            rows = []
#            # TODO: probably don't need to write out column names or even
#            # create the file if it contains no data, could be an option
#            # TODO: this is slow as dirt
#            #rows.append(["id"] + col_dict.keys()[:]) # write col names
#            rows.append(header) # write col names
#            rows_append = rows.append
#            for row in table.select():                                
#                values = []
#                values.append(row.id) # id is always first
#                map(lambda col: values.append(getattr(row, col)), col_dict)
#                rows_append(values)
#            f = file(filename_template % table_name, "wb")
#            writer = csv.writer(f, quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
#            writer.writerows(rows)
#        f.close()
#        bauble.app.set_busy(False)
#        #bauble.app.gui.window.window.set_cursor(None)
#        #progress.destroy()
            
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

