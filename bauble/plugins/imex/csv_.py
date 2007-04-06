#
# csv import/export
#
# Description: have to name this module csv_ in order to avoid conflict
# with the system csv module
#

import os, csv, traceback
import gtk, gobject
from sqlalchemy import *
import bauble
from bauble.i18n import *
import bauble.utils as utils
import bauble.pluginmgr as plugin
import bauble.task
from bauble.utils.log import log, debug
import bauble.utils.tasklet as tasklet
import Queue

# TODO: ****** important *****
# right now exporting will only export those tables that are registered through
# plugins and won't *see* the other tables that aren't part of any plugin
# or attached to and SA metadata object, we really should try to get all the
# tables and dump everything
# *****************************

# # TODO: ****** important *****
# there is still a bug where bauble locks up if you try to import twice in a
# row

# TODO: i've also had a problem with bad insert statements, e.g. importing a
# geography table after creating a new database and it doesn't use the
# 'name' column in the insert so there is an error, if  you then import the
# same table immediately after then everything seems to work fine

# TODO: in _task_import_files we should really only be dropping tables if the
# tables exist and not showing up warning dialogs if we don't really need
# to drop anything anyway

# TODO: after import we should clear the search results, and maybe
# warn the user we are doing so

# TODO: it might be way faster to transform the csv to a format that
# the database connection understands and use the databases import file statements

# TODO: allow importing/exporting to be customizable, ability to set quoting

# TODO: implement exporting csv from a select statement

# TODO: need better error handling on import, right now it catches the
# exception and shows a dialog but when you close the dialog the task
# bar isn't cleared

# seems like it would make way more sense to just use the database specific
# file loader than deal with all this crap

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



class Importer(object):

    def start(self, **kwargs):
        '''
        start the import process, this is a non blocking method queue the
        process as a bauble task
        '''
        return bauble.task.queue(self.run, **kwargs)


    def run(self, **kwargs):
        '''
        where all the action happens
        '''
        raise NotImplementedError


class CSVImporter(object):

    def __init__(self):
        pass


    def start(self, filenames=None, metadata=None, force=False):
        '''
        start the import process, this is a non blocking method queue the
        process as a bauble task
        '''
        if metadata is None:
            metadata = default_metadata
        bauble.task.queue(self.run, None, filenames, metadata, force)



    def run(self, filenames, metadata, force=False):
        '''
        where all the action happens

        @params filesnames
        @param metadata
        @param force: default=False
        '''
        engine = metadata.engine
        transaction = None
        connection = None
        try:
            connection = engine.contextual_connect()
            transaction = connection.begin()
        except Exception, e:
            msg = 'Error connecting to database.\n\n%s' % utils.xml_safe(e)
            utils.message_dialog(msg, gtk.MESSAGE_ERROR)
            return

        # sort the tables and filenames by dependency so we can
        # drop/create/import them in the proper order
        filename_dict = {}
        for f in filenames:
            path, base = os.path.split(f)
            table_name, ext = os.path.splitext(base)
            if table_name in filename_dict:
                msg = 'More than one file given to import into table '\
                      '<b>%s</b>: %s, %s' % filename_dict[table_name], f
                utils.message_dialog(msg, gtk.MESSAGE_ERROR)
                return
            filename_dict[table_name] = f

        sorted_tables = []
        for table in metadata.table_iterator():
            try:
                sorted_tables.insert(0, (table, filename_dict.pop(table.name)))
            except KeyError, e: # ---> table.naeme not in list of filenames
                # we handle this below
                pass

        if len(filename_dict) > 0:
            msg = 'Could not match all filenames to table names.\n\n%s' % \
                  filename_dict
            utils.message_dialog(msg, gtk.MESSAGE_ERROR)
            return

        total_lines = 0
        for filename in filenames:
            #get the total number of lines for all the files
            total_lines += len(file(filename).readlines())

        # TODO: should check that if we're dropping a table because of a
        # dependency that we expect that data to be imported in this same
        # task, or at least let the user know that the table is empty

        # TODO: if table exists but doesn't have anything in it then we don't
        # drop/create it. this can be a problem if the table was created with
        # a different schema, in theory this shouldn't happend but it's
        # possible, would probably be better to just recreate the table anyway
        # since it's empty

        # TODO: checking the number of rows in a database locks up when in a
        # transaction and causes the import the hang, i would rather only ask
        # the user if they want drop the table if it isn't empty but i haven't
        # figured out a way to do this in a transaction. the problem seems to
        # be when table is in an inbetween state b/c it's been dropped in
        # transaction as a dependency of another table so when we go to check
        # if it has rows it seems like the database is waiting for the
        # transaction to finish and....LOCK
        self.__error_traceback_str = ''
        self.__error_exc = 'Unknown Error.'

        created_tables = []
        def add_to_created(names):
           created_tables.extend([n for n in names if n not in created_tables])
        total_lines = 0
        for table, filename in sorted_tables:
            #get the total number of lines for all the files
            total_lines += len(file(filename).readlines())
        steps_so_far = 0

        try:
            # first do all the table creation/dropping
            for table, filename in sorted_tables:
                inner_trans = connection.begin()
#                if self.__cancel or self.__error:
#                    debug('break')
#                    break
                msg = 'importing %s table from %s' % (table.name, filename)
                log.info(msg)
                bauble.task.set_message(msg)
                yield # allow update
                if not table.exists():#connectable=engine):
                    log.info('%s does not exist. creating.' % table.name)
                    debug('%s does not exist. creating.' % table.name)
                    table.create()#connectable=connection)
                    add_to_created(table.name)
                    #elif table.count().scalar(connectable=connection) > 0 and not force:
                elif table.name not in created_tables:# or \
                    #(table.count().scalar() > 0 and not force):
                    if not force:
                        msg = _('The <b>%s</b> table already exists in the '\
                                'database and may contain some data. If a '\
                                'row the import file has the same id as a '
                                'row in the database then the file will not '\
                                'import correctly.\n\n<i>Would you like to '
                                'drop the table in the database first. You '\
                                'will lose the data in your database if you '\
                                'do this?</i>') % table.name
                        d = utils.create_yes_no_dialog(msg)
                        yield
#                        yield (tasklet.WaitForSignal(d, "response"),
#                               tasklet.WaitForSignal(d, "close"))
##                        response = tasklet.get_event().signal_args[0]
                        d.destroy()
                    else:
                        response = gtk.RESPONSE_YES

                    if response == gtk.RESPONSE_YES:
                        deps = utils.find_dependent_tables(table)
                        dep_names = [t.name for t in deps]
                        if len(dep_names) > 0 and not force:
                            msg = _('The following tables depend on the %s ' \
                                    'table. These tables will need to be '\
                                    'dropped as well.\n\n<b>%s</b>\n\n' \
                                    '<i>Would you like to continue?</i>') \
                                    % (table.name, ', '.join(dep_names))
                            d = utils.create_yes_no_dialog(msg)
                            yield
#                            yield (tasklet.WaitForSignal(d, "response"),
#                                   tasklet.WaitForSignal(d, "close"))
##                            response = tasklet.get_event().signal_args[0]
                            d.destroy()
                            if response != gtk.RESPONSE_YES:
                                self.__cancel = True
                                break
                                # TODO: there is a bug here when importing the same
                                # table back to back,
                                # see https://launchpad.net/products/bauble/+bug/70309
                                # drop the deps in reverse order
                                for d in reversed(deps):
                                    debug('dropping dep %s' % d)
                                    d.drop(checkfirst=True)#, connectable=connection)
                            debug('dropping %s' % table)
                            table.drop(checkfirst=True)#, connectable=connection)
                            debug('creating %s' % table)
                            table.create()#connectable=connection)

                            add_to_created([table.name])
                            for d in deps: # recreate the deps
                                debug('creating dep %s' % d)
                                d.create()#connectable=connection)
                                add_to_created(dep_names)

                if self.__cancel or self.__error:
                    break

                insert = table.insert()
                f = file(filename, "rb")
                reader = csv.DictReader(f, quotechar=QUOTE_CHAR,
                                        quoting=QUOTE_STYLE)
                update_every = 11
                # TODO: maybe to speed this up we could build all the inserts
                # and then do an execute_many
#                debug('slice it')
                for slice in reader:
                    while self.__pause:
                        yield
                    if self.__cancel or self.__error:
                        break
                    if len(slice) > 0:
                        cleaned = dict([(k, v) for k,v in \
                                        slice.iteritems() if v is not ''])
#                        debug('%s: %s' % (insert.table, cleaned['id']))
                        connection.execute(insert, cleaned)
                    steps_so_far += 1
                    if steps_so_far % update_every == 0:
                        percent = float(steps_so_far)/float(total_lines)
                        if 0 < percent < 1.0: # avoid warning
                            if bauble.gui is not None:
                                bauble.gui.progressbar.set_fraction(percent)
                    yield

                if self.__error or self.__cancel:
                    break

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
            d = utils.create_message_details_dialog('Error:  %s' % \
                                                    utils.xml_safe(msg),
                                                    self.__error_traceback_str,
                                                    type=gtk.MESSAGE_ERROR)
            yield
##            yield (tasklet.WaitForSignal(d, "response"),
##                   tasklet.WaitForSignal(d, "close"))
##            tasklet.get_event()
            d.destroy()

        if self.__error or self.__cancel:
            log.info('rolling back import')
            transaction.rollback()
        else:
            log.info('commiting import')
            transaction.commit()
            # set the sequence on a table to the max value
            if engine.name == 'postgres':
                try:
                    for table, filename in sorted_tables:
                    # TOD0: maybe something like
    #                for col in table.c:
    #                    if col.type == Integer:
    #                        - get the max
    #                        try:
    #                            - set the sequence
    #                        except:
    #                            pass

                        sequence_name = '%s_id_seq' % table.name
                        stmt = "SELECT max(id) FROM %s" % table.name
                        max = connection.execute(stmt).fetchone()[0]
                        if max is not None:
                            stmt = "SELECT setval('%s', %d);" % \
                                   (sequence_name, max+1)
                            connection.execute(stmt)
                except Exception, e:
                    debug(e)
                    msg = 'Error: Could not set the value the for the '\
                          'sequence: %s' % sequence_name
                    d = utils.create_message_details_dialog('Error:  %s' \
                                                        % utils.xml_safe(msg),
                                                        str(e),
                                                        type=gtk.MESSAGE_ERROR)
                    yield
##                    yield (tasklet.WaitForSignal(d, "response"),
##                           tasklet.WaitForSignal(d, "close"))
##                    tasklet.get_event()
                    d.destroy()
        debug('leaving CSVImporter._run()')


## class CSVImporter2:

    def __init__(self):
        self.__error = False  # flag to indicate error on import
        self.__cancel = False # flag to cancel importing
        self.__pause = False  # flag to pause importing


##     def import_files(self, filenames, metadata, force=False, callback=None):
##         transaction = None
##         connection = None
##         try:
##             connection = metadata.engine.contextual_connect()
##             #transaction = connection.begin()
##         except Exception, e:
##             msg = 'Error connecting to database.\n\n%s' % utils.xml_safe(e)
##             utils.message_dialog(msg, gtk.MESSAGE_ERROR)
##             return

##         # sort the tables and filenames by dependency so we can
##         # drop/create/import them in the proper order
##         filename_dict = {}
##         for f in filenames:
##             path, base = os.path.split(f)
##             table_name, ext = os.path.splitext(base)
##             if table_name in filename_dict:
##                 msg = 'More than one file given to import into table '\
##                       '<b>%s</b>: %s, %s' % filename_dict[table_name], f
##                 utils.message_dialog(msg, gtk.MESSAGE_ERROR)
##                 return
##             filename_dict[table_name] = f

##         sorted_tables = []
##         for table in metadata.table_iterator():
##             try:
##                 sorted_tables.insert(0, (table, filename_dict.pop(table.name)))
##             except KeyError, e: # ---> table.naeme not in list of filenames
##                 # we handle this below
##                 pass

##         if len(filename_dict) > 0:
##             msg = 'Could not match all filenames to table names.\n\n%s' % \
##                   filename_dict
##             utils.message_dialog(msg, gtk.MESSAGE_ERROR)
##             return

##         total_lines = 0
##         for filename in filenames:
##             #get the total number of lines for all the files
##             total_lines += len(file(filename).readlines())

##         bauble.task.queue(self.__import_task, callback, connection,
##                           sorted_tables, force)

## #        from bauble.plugins.imex.sqlite import import_csv
## #        for table, filename in sorted_tables:
## #            import_csv(connection, filename, table)


##     def __import_task(self, connection, sorted_tables, force):
##         """
##         a tasklet that import data into a Bauble database, this method should
##         be run as a tasklet task,
##         see http://www.gnome.org/~gjc/tasklet/tasklets.html

##         this method takes an all or nothing approach, either we import
##         everything in filesnames of we bail out

##         @param filenames: the list of files names t
##         @param force: causes the data to be imported regardless if the table
##         already has something in it (TODO: this doesn't do anything yet)
##         @param monitor_tasklet: the tasklet that monitors the progress of
##         this task and update the interface
##         """
##         transaction = connection.begin()
##         #connection = transaction.connection
##         engine = connection.engine
##         # TODO: should check that if we're dropping a table because of a
##         # dependency that we expect that data to be imported in this same
##         # task, or at least let the user know that the table is empty

##         # TODO: if table exists but doesn't have anything in it then we don't
##         # drop/create it. this can be a problem if the table was created with
##         # a different schema, in theory this shouldn't happend but it's
##         # possible, would probably be better to just recreate the table anyway
##         # since it's empty

##         # TODO: checking the number of rows in a database locks up when in a
##         # transaction and causes the import the hang, i would rather only ask
##         # the user if they want drop the table if it isn't empty but i haven't
##         # figured out a way to do this in a transaction. the problem seems to
##         # be when table is in an inbetween state b/c it's been dropped in
##         # transaction as a dependency of another table so when we go to check
##         # if it has rows it seems like the database is waiting for the
##         # transaction to finish and....LOCK

##         timeout = tasklet.WaitForTimeout(3)
##         self.__error_traceback_str = ''
##         self.__error_exc = 'Unknown Error.'

##         created_tables = []
##         def add_to_created(names):
##            created_tables.extend([n for n in names if n not in created_tables])
##         que = Queue.Queue(0)
##         total_lines = 0
##         for table, filename in sorted_tables:
##             #get the total number of lines for all the files
##             total_lines += len(file(filename).readlines())
##         steps_so_far = 0

##         try:
##             # first do all the table creation/dropping
##             for table, filename in sorted_tables:
##                 inner_trans = connection.begin()
## #                if self.__cancel or self.__error:
## #                    debug('break')
## #                    break
##                 msg = 'importing %s table from %s' % (table.name, filename)
##                 log.info(msg)
##                 bauble.task.set_message(msg)
##                 yield timeout
##                 tasklet.get_event()

##                 inner_trans = connection.begin()
##                 if not table.exists():#connectable=engine):
##                     log.info('%s does not exist. creating.' % table.name)
##                     debug('%s does not exist. creating.' % table.name)
##                     table.create()#connectable=connection)
##                     add_to_created(table.name)
##                     #elif table.count().scalar(connectable=connection) > 0 and not force:
##                 elif table.name not in created_tables:# or \
##                     #(table.count().scalar() > 0 and not force):
##                     if not force:
##                         msg = _('The <b>%s</b> table already exists in the '\
##                                 'database and may contain some data. If a '\
##                                 'row the import file has the same id as a '
##                                 'row in the database then the file will not '\
##                                 'import correctly.\n\n<i>Would you like to '
##                                 'drop the table in the database first. You '\
##                                 'will lose the data in your database if you '\
##                                 'do this?</i>') % table.name
##                         d = utils.create_yes_no_dialog(msg)
##                         yield (tasklet.WaitForSignal(d, "response"),
##                                tasklet.WaitForSignal(d, "close"))
##                         response = tasklet.get_event().signal_args[0]
##                         d.destroy()
##                     else:
##                         response = gtk.RESPONSE_YES

##                     if response == gtk.RESPONSE_YES:
##                         deps = utils.find_dependent_tables(table)
##                         dep_names = [t.name for t in deps]
##                         if len(dep_names) > 0 and not force:
##                             msg = _('The following tables depend on the %s ' \
##                                     'table. These tables will need to be '\
##                                     'dropped as well.\n\n<b>%s</b>\n\n' \
##                                     '<i>Would you like to continue?</i>') \
##                                     % (table.name, ', '.join(dep_names))
##                             d = utils.create_yes_no_dialog(msg)
##                             yield (tasklet.WaitForSignal(d, "response"),
##                                    tasklet.WaitForSignal(d, "close"))
##                             response = tasklet.get_event().signal_args[0]
##                             d.destroy()
##                             if response != gtk.RESPONSE_YES:
##                                 self.__cancel = True
##                                 break
##                                 # TODO: there is a bug here when importing the same
##                                 # table back to back,
##                                 # see https://launchpad.net/products/bauble/+bug/70309
##                                 # drop the deps in reverse order
##                                 for d in reversed(deps):
##                                     debug('dropping dep %s' % d)
##                                     d.drop(checkfirst=True)#, connectable=connection)

##                             debug('dropping %s' % table)
##                             table.drop(checkfirst=True)#, connectable=connection)
##                             debug('creating %s' % table)
##                             table.create()#connectable=connection)

##                             #debug(e)
##                             #debug(traceback.format_exc())
##                             #inner_trans.rollback()
##                             #inner_trans.commit()
##                             add_to_created([table.name])
##                             for d in deps: # recreate the deps
##                                 debug('creating dep %s' % d)
##                                 d.create()#connectable=connection)
##                                 add_to_created(dep_names)

##                 if self.__cancel or self.__error:
##                     break

##                 insert = table.insert()
##                 def do_import():
##                     try:
##                         # this should never block since we add the value to
##                         # the queue before we ever call this method but just
##                         # in case, the two scenarios are 1. values are added
##                         # to the queue but we get here and don't see anything
##                         # and keep going and effectively lose data, or 2. we
##                         # block and we stay
##                         # here forever and the app would stop responding, the
##                         # second one sounds better since at least it doesn't
##                         # lose data, maybe we could add a timeout to get and
##                         # if we get here and don't get anything from the
##                         # queue we can at least rollback all our changes
##                         insert, values = que.get(block=True)
##                         # this is how to do this for list of dictionaries for
##                         # the values, e.g. when using chunk()
##                         #cleaned = [dict([(k, v) for k,v in d.iteritems() if v is not '']) for d in [row for row in values]]
##                         cleaned = dict([(k, v) for k,v in values.iteritems() if v is not ''])
## #                        debug('cleaned: %s' % cleaned)
##                         connection.execute(insert, cleaned)
##                     #insert.execute(map(cleanup, values))
##                     except Queue.Empty, e:
##     #                        debug('empty')
##                         pass
##                     except Exception, e:
##                         debug(e)
##                         self.__error = True
##                         self.__cancel = True
##                         self.__error_exc = utils.xml_safe(e)
##                         self.__error_traceback_str = traceback.format_exc()

##                 f = file(filename, "rb")
##                 reader = csv.DictReader(f, quotechar=QUOTE_CHAR,
##                                         quoting=QUOTE_STYLE)
##                 update_every = 11
##                 # TODO: maybe to speed this up we could build all the inserts
##                 # and then do an execute_many
## #                debug('slice it')
##                 for slice in reader:
##                     while self.__pause:
##                         yield timeout
##                         tasklet.get_event()
##                     if self.__cancel:
##                         break
##                     if len(slice) > 0:
##                         que.put((insert, slice), block=False)
##                         gobject.idle_add(do_import)
##                     steps_so_far += 1
##                     if steps_so_far % update_every == 0:
##                         percent = float(steps_so_far)/float(total_lines)
##                         if 0 < percent < 1.0: # avoid warning
##                             bauble.gui.progressbar.set_fraction(percent)
##                     yield timeout
##                     tasklet.get_event()

##                 if self.__error or self.__cancel:
##                     break

##             # loop till everything has been committed, is it possible
##             # for this to go on forever?
##             while not que.empty():
##                 yield timeout
##                 tasklet.get_event()

##         except Exception, e:
##             debug(e)
##             self.__error = True
##             self.__error_exc = utils.xml_safe(e)
##             self.__error_traceback_str = traceback.format_exc()
##             self.__cancel = True

##         if self.__error:
##             try:
##                 msg = self.__error_exc.orig
##             except AttributeError, e: # no attribute orig
##                 msg = self.__error_exc
##             d = utils.create_message_details_dialog('Error:  %s' % \
##                                                     utils.xml_safe(msg),
##                                                     self.__error_traceback_str,
##                                                     type=gtk.MESSAGE_ERROR)
##             yield (tasklet.WaitForSignal(d, "response"),
##                    tasklet.WaitForSignal(d, "close"))
##             tasklet.get_event()
##             d.destroy()

##         if self.__error or self.__cancel:
##             log.info('rolling back import')
##             transaction.rollback()
##         else:
##             log.info('commiting import')
##             transaction.commit()
##             # set the sequence on a table to the max value
##             if engine.name == 'postgres':
##                 try:
##                     for table, filename in sorted_tables:
##                     # TOD0: maybe something like
##     #                for col in table.c:
##     #                    if col.type == Integer:
##     #                        - get the max
##     #                        try:
##     #                            - set the sequence
##     #                        except:
##     #                            pass

##                         sequence_name = '%s_id_seq' % table.name
##                         stmt = "SELECT max(id) FROM %s" % table.name
##                         max = connection.execute(stmt).fetchone()[0]
##                         if max is not None:
##                             stmt = "SELECT setval('%s', %d);" % \
##                                    (sequence_name, max+1)
##                             connection.execute(stmt)
##                 except Exception, e:
##                     debug(e)
##                     msg = 'Error: Could not set the value the for the '\
##                           'sequence: %s' % sequence_name
##                     d = utils.create_message_details_dialog('Error:  %s' \
##                                                         % utils.xml_safe(msg),
##                                                         str(e),
##                                                         type=gtk.MESSAGE_ERROR)
##                     yield (tasklet.WaitForSignal(d, "response"),
##                            tasklet.WaitForSignal(d, "close"))
##                     tasklet.get_event()
##                     d.destroy()


    def _cancel_import(self, *args):
        '''
        called by the progress dialog to cancel the current import
        '''
        msg = 'Are you sure you want to cancel importing?\n\n<i>All changes '\
              'so far will be rolled back.</i>'
        self.__pause = True
        if utils.yes_no_dialog(msg, parent=self.__progress_dialog):
            self.__cancel = True
        self.__pause = False


##     def start(self, filenames=None, force=False, callback=None):
##         """
##         the simplest way to import, no threads, nothing

##         filenames -- the list of filenames to import from
##         force -- import regardless if the table already has data
##         """
##         # TODO: possibly implement a block argument that would allow us
##         # to import from the command line
##         error = False # return value
##         if filenames is None:
##             filenames = self._get_filenames()
##         if filenames is None: # no filenames selected
##             return
##         if bauble.db_engine.name not in  ['sqlite', 'postgres']:
##             msg = 'The CSV Import plugin has not been tested with %s '\
##                   'databases. It\'s possible that it may work fine but we '\
##                   'can\'t offer an guarantees.  If you need this to work '\
##                   'then please contact the developers of Bauble.  '\
##                   'http://bauble.belizebotanic.org\n\n<i>Would you like to '\
##                   'continue?</i>'
##             if not utils.yes_no_dialog(msg):
##                 return
##         self.import_files(filenames, default_metadata, force, callback)


    def _get_filenames(self):
        def on_selection_changed(filechooser, data=None):
            """
            only make the ok button sensitive if the selection is a file
            """
            f = filechooser.get_preview_filename()
            if f is None:
                return
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


# TODO: right now only tables that are registered with the metadata are
# registered, we need to make sure that all the tables are exported and not
# just the ones that we know about at the time of export...need to get a list
# of tables from postgres, mysql and sqlite
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

        if not os.path.exists(path):
            raise ValueError("CSVExporter: path does not exist.\n" + path)
        bauble.task.queue(self.__export_task, None, path)

    def __export_task(self, path):
#        if not os.path.exists(path):
#            raise ValueError("CSVExporter: path does not exist.\n" + path)
        filename_template = os.path.join(path, "%s.txt")
        tables = default_metadata.tables
        timeout = tasklet.WaitForTimeout(12)
        ntables = len(tables.keys())
        steps_so_far = 0
        for name in tables.keys():
            filename = filename_template % name
            if os.path.exists(filename):
                msg = 'Export file <b>%s</b> for <b>%s</b> table already '\
                      'exists.\n\n<i>Would you like to continue?</i>' % \
                      (filename, name)
                d = utils.create_yes_no_dialog(msg)
                yield (tasklet.WaitForSignal(d, "response"),
                       tasklet.WaitForSignal(d, "close"))
                response = tasklet.get_event().signal_args[0]
                d.destroy()
                if response != gtk.RESPONSE_YES:
                    debug('return')
                    return

        def replace(s):
            if isinstance(s, (str, unicode)):
                s.replace('\n', '\\n')
            return s

        def write_csv(filename, rows):
            f = file(filename, 'wb')
            writer = csv.writer(f, quotechar=QUOTE_CHAR, quoting=QUOTE_STYLE)
            writer.writerows(rows)
            f.close()

        update_every = 30
        for table_name, table in tables.iteritems():
            filename = filename_template % table_name
            steps_so_far+=1
            fraction = float(steps_so_far)/float(ntables)
            bauble.gui.progressbar.set_fraction(fraction)
            msg = 'exporting %s table to %s' % (table_name, filename)
            bauble.task.set_message(msg)
            log.info("exporting %s" % table_name)

            # get the data
            results = table.select().execute().fetchall()

            # create empty files with only the column names
            if len(results) == 0:
                write_csv(filename, [table.c.keys()])
                yield timeout
                tasklet.get_event()
                continue

            rows = []
            rows.append(table.c.keys()) # append col names
            ctr = 0
            for row in results:
                values = map(replace, row.values())
                rows.append(values)
                if ctr == update_every:
                    yield timeout
                    tasklet.get_event()
                    ctr=0
                ctr += 1
            write_csv(filename, rows)


class CSVImportCommandHandler(plugin.CommandHandler):

    command = 'imcsv'

    def __call__(self, arg):
        debug('CSVImportCommandHandler(%s)' % arg)
        importer = CSVImporter()
        importer.start(arg)


class CSVExportCommandHandler(plugin.CommandHandler):

    command = 'excsv'

    def __call__(self, arg):
        debug('CSVExportCommandHandler(%s)' % arg)
        exporter = CSVExporter()
        debug('starting')
        exporter.start(arg)
        debug('started')

#
# plugin classes
#

class CSVImportTool(plugin.Tool):
    category = "Import"
    label = "Comma Separated Value"

    @classmethod
    def start(cls):
        msg = 'It is possible that importing data into this database could '\
        'destroy or corrupt your existing data.\n\n<i>Would you like to '\
        'continue?</i>'
        if utils.yes_no_dialog(msg):
            c = CSVImporter()
            c.start()


class CSVExportTool(plugin.Tool):
    category = "Export"
    label = "Comma Separated Value"

    @classmethod
    def start(cls):
        c = CSVExporter()
        c.start()

## class CSVImexPlugin(plugin.Plugin):
##     tools = [CSVImportTool, CSVExportTool]
##     commands = [CSVExportCommandHandler, CSVImportCommandHandler]

## plugin = CSVImexPlugin

# TODO: importing from the command line isn't finished, i think the only thing
# that really need to be done for it to work is to create a gobject.mainloop()
# or implement blocking in the importer to have it's own mainloop

#def main():
#    # should allow you to export or import from a database from the
#    # command line, you would just have to pass the connection uri
#    # and the name of the directory to export to
#    # TODO: allow -i for import, -e for export
#    # TODO: need to pass in a database connection string
#    # postgres://bbg:garden@ceiba.test
#
#    # TODO: ****** i think the only reason this isn't working is because of using the
#    # connection manager so we can either 1. figure out how to use the connection
#    # manager from a tasklet or 2. don't use the connection manager and get
#    # connection paramaters from the command line including the passwd
#
#    import sys
#    from sqlobject import sqlhub, connectionForURI
#    from bauble.conn_mgr import ConnectionManager#Dialog
#    from bauble.prefs import prefs
#    from optparse import OptionParser
#    parser = OptionParser()
#    parser.add_option('--force', dest='force', action='store_true',
#                      default=False, help='force import')
#    parser.add_option('-c', '--connection', dest='conn',
#                      help='named connection from prefs')
#    options, args = parser.parse_args()
#
#    if len(args) == 0:
#        print '** Error: need a list of files to import'
#        return
#
#    prefs.init() # intialize the preferences
#
#    if options.conn is None:
#        default_conn = prefs[prefs.conn_default_pref]
#        cm = ConnectionManager(default_conn)
#        conn_name, uri = cm.start()
#        if conn_name is None: return
#    else:
#        params = prefs[prefs.conn_list_pref][options.conn]
#        uri = ConnectionManager().parameters_to_uri(params)
#
#    sqlhub.processConnection = connectionForURI(uri)
#    sqlhub.processConnection.getConnection()
#    sqlhub.processConnection = sqlhub.processConnection.transaction()
#
#    if not options.force:
#        msg = 'Importing to this connection (%s) will destroy any existing data '\
#              ' in the database. Are you sure this is what you want to do? ' % uri
#        response = raw_input(msg)
#        if response not in ('Y', 'y'):
#            return
##        if not utils.yes_no_dialog(msg):
##            return
#
#    # check that the database version are the same
#    from bauble._app import BaubleApp
#    BaubleApp.open_database(uri)
#
#    bauble.plugins.load()
#    importer = CSVImporter()
#    print 'importing....'
#    importer.start(args, force=options.force)
#    sqlhub.processConnection.commit()
#    print '...finished importing'


#if __name__ == "__main__":
#    tasklet.run(main())
#    gtk.main()

