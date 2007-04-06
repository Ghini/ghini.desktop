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

# TODO: i've also had a problem with bad insert statements, e.g. importing a
# geography table after creating a new database and it doesn't use the
# 'name' column in the insert so there is an error, if  you then import the
# same table immediately after then everything seems to work fine

# TODO: should check that if we're dropping a table because of a
# dependency that we expect that data to be imported in this same
# task, or at least let the user know that the table is empty

# TODO: checking the number of rows in a database locks up when in a
# transaction and causes the import the hang, i would rather only ask
# the user if they want drop the table if it isn't empty but i haven't
# figured out a way to do this in a transaction. the problem seems to
# be when table is in an inbetween state b/c it's been dropped in
# transaction as a dependency of another table so when we go to check
# if it has rows it seems like the database is waiting for the
# transaction to finish and....LOCK

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
        return bauble.task.queue(self.run, self.on_quit, self.on_error,
                                 **kwargs)


    def on_quit(self):
        pass


    def on_error(self, exc):
        pass


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

        def on_error(exc):
            utils.message_details_dialog(str(exc), traceback.format_exc())

        if filenames is None:
            filenames = self._get_filenames()

        bauble.task.queue(self.run, None, on_error, filenames, metadata, force)



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
            msg = _('Error connecting to database.\n\n%s') % utils.xml_safe(e)
            utils.message_dialog(msg, gtk.MESSAGE_ERROR)
            return

        # sort the tables and filenames by dependency so we can
        # drop/create/import them in the proper order
        filename_dict = {}
        for f in filenames:
            path, base = os.path.split(f)
            table_name, ext = os.path.splitext(base)
            if table_name in filename_dict:
                msg = _('More than one file given to import into table '\
                        '<b>%s</b>: %s, %s') % (table_name,
                                                filename_dict[table_name], f)
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
            msg = _('Could not match all filenames to table names.\n\n%s') \
                  % filename_dict
            utils.message_dialog(msg, gtk.MESSAGE_ERROR)
            return

        total_lines = 0
        for filename in filenames:
            #get the total number of lines for all the files
            total_lines += len(file(filename).readlines())

        self.__error_traceback_str = ''
        self.__error_exc = _('Unknown Error.')

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
                if self.__cancel or self.__error:
                    break
                inner_trans = connection.begin()
#                if self.__cancel or self.__error:
#                    debug('break')
#                    break
                msg = _('importing %(table)s table from %(filename)s') \
                        % {'table': table.name, 'filename': filename}
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
                        response = utils.yes_no_dialog(msg)
                    else:
                        response = True

                    if response:
                        deps = utils.find_dependent_tables(table)
                        dep_names = [t.name for t in deps]
                        if len(dep_names) > 0 and not force:
                            msg = _('The following tables depend on the '
                                    '%(table)s table. These tables will need '
                                    'to be dropped as well.\n\n' \
                                    '<b>%(other_tables)s</b>\n\n' \
                                    '<i>Would you like to continue?</i>' \
                                    % {'table': table.name,
                                       'other_tables': ', '.join(dep_names)})

                            if not utils.yes_no_dialog(msg):
                                self.__cancel = True
                                continue

                            # drop the deps in reverse order
                            for d in reversed(deps):
                                debug('dropping dep %s' % d)
                                d.drop(checkfirst=True)

                            # TODO: there is a bug here when importing the same
                            # table back to back,
                            # see https://launchpad.net/products/bauble/+bug/70309
                            debug('dropping %s' % table)
                            table.drop(checkfirst=True)
                            debug('creating %s' % table)
                            table.create()

                            add_to_created([table.name])
                            for d in deps: # recreate the deps
                                debug('creating dep %s' % d)
                                d.create()
                                add_to_created(dep_names)

                if self.__cancel or self.__error:
                    debug('canceled')
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
            utils.message_details_dialog(_('Error:  %s') % \
                                         utils.xml_safe(msg),
                                         self.__error_traceback_str,
                                         type=gtk.MESSAGE_ERROR)

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
                    msg = _('Error: Could not set the value the for the '\
                            'sequence: %s') % sequence_name
                    utils.message_details_dialog(_('Error:  %s' \
                                                   % utils.xml_safe(msg)),
                                                 str(e),
                                                 type=gtk.MESSAGE_ERROR)


    def __init__(self):
        self.__error = False  # flag to indicate error on import
        self.__cancel = False # flag to cancel importing
        self.__pause = False  # flag to pause importing



    def _cancel_import(self, *args):
        '''
        called by the progress dialog to cancel the current import
        '''
        msg = _('Are you sure you want to cancel importing?\n\n<i>All '
                'changes so far will be rolled back.</i>')
        self.__pause = True
        if utils.yes_no_dialog(msg, parent=self.__progress_dialog):
            self.__cancel = True
        self.__pause = False



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
        fc = gtk.FileChooserDialog(_("Choose file(s) to import..."),
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



class CSVExporter:

    def start(self, path=None):
        if path == None:
            d = gtk.FileChooserDialog(_("Select a directory"), None,
                                      gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
                                      (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
                                      gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
            response = d.run()
            path = d.get_filename()
            d.destroy()
            if response != gtk.RESPONSE_ACCEPT:
                return

        if not os.path.exists(path):
            raise ValueError(_("CSVExporter: path does not exist.\n%s" % path))

        def on_error(exc):
            utils.message_dialog(str(exc))

        try:
            bauble.task.queue(self.__export_task, None, on_error, path)
        except Exception, e:
            debug(e)


    def __export_task(self, path):
#        if not os.path.exists(path):
#            raise ValueError("CSVExporter: path does not exist.\n" + path)
        filename_template = os.path.join(path, "%s.txt")
        tables = default_metadata.tables
#        timeout = tasklet.WaitForTimeout(12)
        ntables = len(tables.keys())
        steps_so_far = 0
        for name in tables.keys():
            filename = filename_template % name
            if os.path.exists(filename):
                msg = _('Export file <b>%(filename)s</b> for '\
                        '<b>%(table)s</b> table already exists.\n\n<i>Would '\
                        'you like to continue?</i>') \
                        % {'filename': filename, 'table': name}
                if utils.yes_no_dialog(msg):
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
            msg = _('exporting %(table)s table to %(filename)s') \
                    % {'table': table_name, 'filename': filename}
            bauble.task.set_message(msg)
            log.info("exporting %s" % table_name)

            # get the data
            results = table.select().execute().fetchall()

            # create empty files with only the column names
            if len(results) == 0:
                write_csv(filename, [table.c.keys()])
                yield
                #yield timeout
                #tasklet.get_event()
                continue

            rows = []
            rows.append(table.c.keys()) # append col names
            ctr = 0
            for row in results:
                values = map(replace, row.values())
                rows.append(values)
                if ctr == update_every:
                    yield
                    #yield timeout
                    #tasklet.get_event()
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
    category = _('Import')
    label = _('Comma Separated Value')

    @classmethod
    def start(cls):
        msg = _('It is possible that importing data into this database could '\
                'destroyed or corrupt your existing data.\n\n<i>Would you '\
                'like to continue?</i>')
        if utils.yes_no_dialog(msg):
            c = CSVImporter()
            c.start()


class CSVExportTool(plugin.Tool):
    category = _('Export')
    label = _('Comma Separated Value')

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

