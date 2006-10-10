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
import Queue

# TODO: ****** important *****
# right now exporting will only export those tables that are registered through
# plugins and won't *see* the other tables that aren't part of any plugin 
# or attached to and SA metadata object, we really should try to get all the
# tables and dump everything
# *****************************

# TODO: in _task_import_files we should really only be dropping tables if the 
# tables exist and not showing up warning dialogs if we don't really need
# to drop anything anyway

# TODO: after import we should clear the search results, and maybe
# warn the user we are doing so

# TODO: it might be way faster to transform the csv to a format that 
# the database connection understands and use the databases import file statements

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


class CSVImporter:

    def __init__(self):
        self.__error = False  # flag to indicate error on import
        self.__cancel = False # flag to cancel importing
        self.__pause = False  # flag to pause importing

        
    def _task_import_files(self, filenames, force, metadata, monitor_tasklet):        
        '''
        a tasklet that import data into a Bauble database, this method should
        be run as a gtasklet task, see http://www.gnome.org/~gjc/gtasklet/gtasklets.html
        
        this method takes an all or nothing approach, either we import 
        everything in filesnames of we bail out
        
        @param filenames: the list of files names t
        @param force: causes the data to be imported regardless if there already 
        the table already has something in it (TODO: this doesn't do anything yet)
        @param monitor_tasklet: the tasklet that monitors the progress of this task
        and update the interface
        '''
        # TODO: should check that if we're dropping a table because of a dependency
        # that we expect that data to be imported in this same task, or at least
        # let the user know that the table is empty

        # TODO: if table exists but doesn't have anything in it then we don't
        # drop/create it. this can be a problem if the table was created with
        # a different schema, in theory this shouldn't happend but it's possible,
        # would probably be better to just recreate the table anyway since it's 
        # empty
        
        # TODO: checking the number of rows in a database locks up when in a 
        # transaction and causes the import the hang, i would rather only ask
        # the user if they want drop the table if it isn't empty but i haven't
        # figured out a way to do this in a transaction. the problem seems to
        # be when table is in an inbetween state b/c it's been dropped in
        # transaction as a dependency of another table so when we go to check if 
        # it has rows it seems like the database is waiting for the transaction
        # to finish and....LOCK
        
        # TODO: any dialogs opened in this method should have the progress
        # dialog as it's parent
        engine = metadata.engine
        connection = engine.connect()
        transaction = connection.begin()
        #timeout = gtasklet.WaitForTimeout(12)
        timeout = gtasklet.WaitForTimeout(12)
        
        self.__error_traceback_str = ''
        self.__error_exc = 'Unknown Error.'

        def cleanup(row):
            clean = {}
            for key, val in row.iteritems():
                if val is not '':
                    clean[key] = val
            return clean

        # sort the tables and filenames by dependency so we can import
        filename_dict = {}
        for f in filenames:            
            path, base = os.path.split(f)
            table_name, ext = os.path.splitext(base)        
            filename_dict[table_name] = f

        sorted_tables = []
        for table in metadata.table_iterator():
            try:
                sorted_tables.insert(0, (table, filename_dict.pop(table.name)))
            except KeyError, e: # ---> table.name not in list of filenames
                pass
            
        if len(filename_dict) > 0:
            msg = 'Could not match all filenames to table names.\n\n%s' % filename_dict
            d = utils.create_message_dialog(msg)
            yield (gtasklet.WaitForSignal(d, "response"),
                   gtasklet.WaitForSignal(d, "close"))   
            response = gtasklet.get_event().signal_args[0]        
            d.destroy()
        
        created_tables = []
        def add_to_created(names):
            created_tables.extend([n for n in names if n not in created_tables])
        
        que = Queue.Queue(0)    
        try:
            # first do all the table creation/dropping
            for table, filename in sorted_tables:
               
#                if self.__cancel or self.__error:
#                    debug('break')
#                    break
                
                log.info('importing %s table from %s' % (table.name, filename))                
                yield gtasklet.Message('update_filename', dest=monitor_tasklet, value=(filename, table.name))
                yield timeout
                gtasklet.get_event()
                
                if not table.exists(engine=engine):
                    debug('%s does not exist. creating.' % table.name)                
                    table.create(connectable=connection)
                    add_to_created(table.name)
                #elif table.count().scalar(connectable=connection) > 0 and not force:
                elif table.name not in created_tables:
                    msg = 'The <b>%s</b> table already exists in the database and may '\
                          'contain some data. If a row in the import file has '\
                          'the same id as a row in the databse then the file '\
                          'will not import correctly.\n\n<i>Would you like to '\
                          'drop the table in the database first. You will lose '\
                          'the data in your database if you do this?</i>' % table.name                                              
                    d = utils.create_yes_no_dialog(msg)
                    yield (gtasklet.WaitForSignal(d, "response"),
                           gtasklet.WaitForSignal(d, "close"))   
                    response = gtasklet.get_event().signal_args[0]        
                    d.destroy()
                    if force or response == gtk.RESPONSE_YES:
                        deps = utils.find_dependent_tables(table)
                        dep_names = [t.name for t in deps]
                        if len(dep_names) > 0 and not force:
                            msg = 'The following tables depend on the %s table. '\
                                  'These tables will need to be dropped as well. '\
                                  '\n\n<b>%s</b>\n\n' \
                                  '<i>Would you like to continue?</i>' % (table.name, ', '.join(dep_names))
                            d = utils.create_yes_no_dialog(msg)
                            yield (gtasklet.WaitForSignal(d, "response"),
                                   gtasklet.WaitForSignal(d, "close"))   
                            response = gtasklet.get_event().signal_args[0]        
                            d.destroy()
                            if response != gtk.RESPONSE_YES:
                                self.__cancel = True
                                break
                                                
                            for d in reversed(deps):
                                # drop the deps in reverse order
                                d.drop(checkfirst=True, connectable=connection)                            

                        table.drop(checkfirst=True, connectable=connection)
                        table.create(connectable=connection)
                        add_to_created([table.name])
                        for d in deps: # recreate the deps
                            d.create(connectable=connection)
                        add_to_created(dep_names)

                if self.__cancel or self.__error:
                    break
                
                insert = table.insert()    
                def do_import():
                    try:                        
                        # TODO: maybe we chould further chunk up the slice
                        # to make it more responsive
                        
                        # this should never block since we add the value to the 
                        # queue before we ever call this method but just in case,
                        # the two scenarios are 1. values are added to the queue
                        # but we get here and don't see anything and keep going
                        # and effectively lose data, or 2. we block and we stay 
                        # here forever and the app would stop responding, the 
                        # second one sounds better since at least it doesn't lose 
                        # data, maybe we could add a timeout to get and if we 
                        # get here and don't get anything from the queue we can
                        # at least rollback all our changes
                        insert, values = que.get(block=True)
                        connection.execute(insert, map(cleanup, values))
                    #insert.execute(map(cleanup, values))
                    except Queue.Empty, e:
    #                        debug('empty')
                        pass
                    except Exception, e:
                        debug(e)
                        raise
                
                f = file(filename, "rb")
                reader = csv.DictReader(f, quotechar=QUOTE_CHAR, quoting=QUOTE_STYLE)
                for slice in chunk(reader, 173):
                    while self.__pause:
                        yield timeout
                        gtasklet.get_event()
                    if self.__cancel:
                        break  
                    if len(slice) > 0:
                        if False:                
                            connection.execute(insert, map(cleanup, slice))
                            v = ''
#                            for v in map(cleanup, slice):
#                                debug(v)
#                                connection.execute(insert, v)
                        else:
                            que.put((insert, slice), block=False)
                            gobject.idle_add(do_import)
                    yield gtasklet.Message('update_progress', 
                                           dest=monitor_tasklet, value=len(slice))
                    yield timeout
                    gtasklet.get_event()
                            
                if self.__error or self.__cancel:
                    break            
                
                # set the sequence on a table to the max value            
                if engine.name in ['sqlite']: # don't need to do anything
                    pass
                elif engine.name is 'postgres':
                    # TOD0: maybe something like
    #                for col in table.c:
    #                    if col.type == Integer:
    #                        - get the max
    #                        try:
    #                            - set the sequence
    #                        except:
    #                            pass
                    try:
                        stmt = "SELECT max(id) FROM %s" % table.name
                        #max = bauble.app.db_engine.execute(stmt).fetchone()[0]
                        max = connection.execute(stmt).fetchone()[0]
                        if max is not None:
                            stmt = "SELECT setval('%s_id_seq', %d);" % (table.name, max+1)
                            connection.execute(stmt)
                            #bauble.app.db_engine.execute(stmt)
                    except Exception, e:
                        debug(e)
                else:
                    msg = 'Could not set the next sequence value for the primary '\
                    'key on the "%s" table.  Importing into %s databases is not '\
                    'fully supported.  If you need this to work then please contact '\
                    'the developers of Bauble.  http://bauble.belizebotanic.org'
                    debug(msg)
                    self.__error = True
                    self.__error_exc = msg
                    self.__cancel = True
        except Exception, e:
            debug(e)
            self.__error = True            
            self.__error_exc = utils.xml_safe(e)
            self.__error_traceback_str = traceback.format_exc()            
            self.__cancel = True            
            
                
        if self.__error:
            try:
                msg = self.__error_exc.orig
            except AttributeError, e: # no attribute orig
                msg = self.__error_exc
            d = utils.create_message_details_dialog('Error:  %s' % utils.xml_safe(msg),
                                                    self.__error_traceback_str,
                                                    type=gtk.MESSAGE_ERROR,
                                                    parent=self.__progress_dialog)
            yield (gtasklet.WaitForSignal(d, "response"),
                   gtasklet.WaitForSignal(d, "close"))
            gtasklet.get_event()
            d.destroy()
            
        if self.__error or self.__cancel:
#            debug('rolling back')
            transaction.rollback()
        else:
#            debug('committing')
            transaction.commit()
        connection.close()        
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
#        debug('_task_monitor_progress')
        self.__progress_dialog = ProgressDialog(title='Importing...')
        self.__progress_dialog.show_all()
        self.__progress_dialog.connect_cancel(self._cancel_import)
        bauble.app.set_busy(True)
        msgwait = gtasklet.WaitForMessages(accept=("quit", "update_progress", 
                                                   'update_filename'))
#        debug('_task_monitor_progress 2')
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
            gtasklet.run(self._task_import_files(filenames, force, default_metadata, monitor_task))
      
        
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
        msg = 'It is possible that importing data into this database could '\
        'destroy or corrupt your existing data.\n\n<i>Would you like to '\
        'continue?</i>'
        if utils.yes_no_dialog(msg) == gtk.RESPONSE_YES:        
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

