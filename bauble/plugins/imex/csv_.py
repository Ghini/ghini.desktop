# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Brett Adams
# Copyright 2012-2015 Mario Frasca <mario@anche.no>.
# Copyright 2017 Jardín Botánico de Quito
#
# This file is part of ghini.desktop.
#
# ghini.desktop is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ghini.desktop is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ghini.desktop. If not, see <http://www.gnu.org/licenses/>.
#
# csv import/export
#
# Description: have to name this module csv_ in order to avoid conflict
# with the system csv module
#

import os
import csv
import traceback

import logging
logger = logging.getLogger(__name__)

import gtk

from sqlalchemy import ColumnDefault, Boolean

import bauble
import bauble.db as db

from bauble.error import BaubleError
import bauble.utils as utils
import bauble.pluginmgr as pluginmgr
import bauble.task
from bauble import pb_set_fraction

# TODO: i've also had a problem with bad insert statements, e.g. importing a
# geography table after creating a new database and it doesn't use the
# 'name' column in the insert so there is an error, if  you then import the
# same table immediately after then everything seems to work fine

# TODO: should check that if we're dropping a table because of a
# dependency that we expect that data to be imported in this same
# task, or at least let the user know that the table is empty

# TODO: don't ask if we want to drop empty tables
# https://bugs.launchpad.net/bauble/+bug/103923

# TODO: allow the user set the unicode encoding on import, exports should
# always us UTF-8, import, exports should always use UTF-8, need to figure
# out how to extend the file open dialog,
# http://evanjones.ca/python-utf8.html
# import codecs
# fileObj = codecs.open( "someFile", "r", "utf-8" )
# u = fileObj.read() # Returns a Unicode string from the UTF-8 bytes in
# the file

# TODO: what happens when you export from one database type and try
# and import into a different database, e.g. postgres->sqlite

QUOTE_STYLE = csv.QUOTE_MINIMAL
QUOTE_CHAR = '"'


class UnicodeReader(object):

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        self.reader = csv.DictReader(f, dialect=dialect, **kwds)
        self.encoding = encoding

    def next(self):
        row = self.reader.next()
        t = {}
        for k, v in row.iteritems():
            if v == '':
                t[k] = None
            else:
                t[k] = utils.to_unicode(v, self.encoding)

        return t

    def __iter__(self):
        return self


# TODO: UnicodeWriter needs to be more thoroughly needs to be more
# tested, i came across a small problem once when createing a tempory
# geography table from _topsort_file and it exported the numbers in
# some strange format
class UnicodeWriter(object):

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        self.writer = csv.writer(f, dialect=dialect, **kwds)
        self.encoding = encoding

    def writerow(self, row):
        """
        Write a row.  If row is a dict then row.values() is written
        and therefore care should be taken to ensure that row.values()
        returns a consisten order.
        """
        if isinstance(row, dict):
            row = row.values()
        t = []
        for s in row:
            if s is None:
                t.append(None)
            else:
                t.append(utils.to_unicode(s, self.encoding))
        self.writer.writerow(t)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


class Importer(object):

    def start(self, **kwargs):
        '''
        start the import process, this is a non blocking method, queue the
        process as a bauble task
        '''
        return bauble.task.queue(self.run, **kwargs)

    def run(self, **kwargs):
        '''
        where all the action happens
        '''
        raise NotImplementedError


class CSVImporter(Importer):

    """imports comma separated value files into a Ghini database.

    It imports multiple files, each of them equally named as the bauble
    database tables. The bauble tables dependency graph defines the correct
    import order, each file being imported will completely replace any
    existing data in the corresponding table.

    The CSVImporter imports the rows of the CSV file in chunks rather than
    one row at a time.  The non-server side column defaults are determined
    before the INSERT statement is generated instead of getting new defaults
    for each row.  This shouldn't be a problem but it also means that your
    column default should change depending on the value of previously
    inserted rows.

    """

    def __init__(self):
        super(CSVImporter, self).__init__()
        self.__error = False   # flag to indicate error on import
        self.__cancel = False  # flag to cancel importing
        self.__pause = False   # flag to pause importing
        self.__error_exc = False

    def start(self, filenames=None, metadata=None, force=False):
        '''start the import process. this is a non blocking method: we queue
        the process as a bauble task. there is no callback informing whether
        it is successfully completed or not.

        '''
        if metadata is None:
            metadata = db.metadata  # use the default metadata

        if filenames is None:
            filenames = self._get_filenames()
        if filenames is None:
            return

        bauble.task.queue(self.run(filenames, metadata, force))

    @staticmethod
    def _toposort_file(filename, key_pairs):
        """
        filename: the csv file to sort

        key_pairs: tuples of the form (parent, child) where for each
        line in the file the line[parent] needs to be sorted before
        any of the line[child].  parent is usually the name of the
        foreign_key column and child is usually the column that the
        foreign key points to, e.g ('parent_id', 'id')
        """
        f = open(filename, 'rb')
        reader = UnicodeReader(f, quotechar=QUOTE_CHAR,
                               quoting=QUOTE_STYLE)

        # create a dictionary of the lines mapped to the child field
        bychild = {}
        for line in reader:
            for parent, child in key_pairs:
                bychild[line[child]] = line
        f.close()
        fields = reader.reader.fieldnames
        del reader

        # create pairs from the values in the lines where pair[0]
        # should come before pair[1] when the lines are sorted
        pairs = []
        for line in bychild.values():
            for parent, child in key_pairs:
                if line[parent] and line[child]:
                    pairs.append((line[parent], line[child]))

        # sort the keys and flatten the lines back into a list
        sorted_keys = utils.topological_sort(bychild.keys(), pairs)
        sorted_lines = []
        for key in sorted_keys:
            sorted_lines.append(bychild[key])

        # write a temporary file of the sorted lines
        import tempfile
        tmppath = tempfile.mkdtemp()
        head, tail = os.path.split(filename)
        filename = os.path.join(tmppath, tail)
        tmpfile = open(filename, 'wb')
        tmpfile.write('%s\n' % ','.join(fields))
        #writer = UnicodeWriter(tmpfile, fields, quotechar=QUOTE_CHAR,
        writer = csv.DictWriter(tmpfile, fields, quotechar=QUOTE_CHAR,
                                quoting=QUOTE_STYLE)
        writer.writerows(sorted_lines)
        tmpfile.flush()
        tmpfile.close()
        del writer
        return filename

    def run(self, filenames, metadata, force=False):
        '''
        A generator method for importing filenames into the database.
        This method periodically yields control so that the GUI can
        update.

        :param filenames:
        :param metadata:
        :param force: default=False
        '''
        transaction = None
        connection = None
        self.__error_exc = BaubleError(_('Unknown Error.'))

        try:
            # user a contextual connect in case whoever called this
            # method called it inside a transaction then we can pick
            # up the parent connection and the transaction
            connection = metadata.bind.connect()
            transaction = connection.begin()
        except Exception, e:
            msg = _('Error connecting to database.\n\n%s') % \
                utils.xml_safe(e)
            utils.message_dialog(msg, gtk.MESSAGE_ERROR)
            return

        # create a mapping of table names to filenames
        filename_dict = {}
        for f in filenames:
            path, base = os.path.split(f)
            table_name, ext = os.path.splitext(base)
            if table_name in filename_dict:
                safe = utils.xml_safe
                values = dict(table_name=safe(table_name),
                              file_name=safe(filename_dict[table_name]),
                              file_name2=safe(f))
                msg = _('More than one file given to import into table '
                        '<b>%(table_name)s</b>: %(file_name)s, '
                        '(file_name2)s') % values
                utils.message_dialog(msg, gtk.MESSAGE_ERROR)
                return
            filename_dict[table_name] = f

        # resolve filenames to table names and return them in sorted order
        sorted_tables = []
        for table in metadata.sorted_tables:
            try:
                sorted_tables.insert(0, (table, filename_dict.pop(table.name)))
            except KeyError, e:
                # table.name not in list of filenames
                pass

        if len(filename_dict) > 0:
            msg = _('Could not match all filenames to table names.\n\n%s') \
                % filename_dict
            utils.message_dialog(msg, gtk.MESSAGE_ERROR)
            return

        total_lines = 0
        filesizes = {}
        for filename in filenames:
            #get the total number of lines for all the files
            nlines = len(open(filename).readlines())
            filesizes[filename] = nlines
            total_lines += nlines

        created_tables = []

        def create_table(table):
            table.create(bind=connection)
            if table.name not in created_tables:
                created_tables.append(table.name)

        steps_so_far = 0
        cleaned = None
        insert = None
        depends = set()  # the type will be changed to a [] later
        try:
            ## get all the dependencies
            for table, filename in sorted_tables:
                logger.debug(table.name)
                d = utils.find_dependent_tables(table)
                depends.update(list(d))
                del d

            ## drop all of the dependencies together
            if len(depends) > 0:
                if not force:
                    msg = _('In order to import the files the following '
                            'tables will need to be dropped:'
                            '\n\n<b>%s</b>\n\n'
                            'Would you like to continue?') % \
                        ', '.join(sorted([d.name for d in depends]))
                    response = utils.yes_no_dialog(msg)
                else:
                    response = True

                if response and len(depends) > 0:
                    logger.debug('dropping: %s'
                                 % ', '.join([d.name for d in depends]))
                    metadata.drop_all(bind=connection, tables=depends)
                else:
                    # user doesn't want to drop dependencies so we just quit
                    return

            # commit the dependency drops
            transaction.commit()
            transaction = connection.begin()

            # update_every determines how many rows we will insert at
            # a time and consequently how often we update the gui
            update_every = 127

            # import the tables one at a time, breaking every so often
            # so the GUI can update
            for table, filename in reversed(sorted_tables):
                if self.__cancel or self.__error:
                    break
                msg = _('importing %(table)s table from %(filename)s') \
                    % {'table': table.name, 'filename': filename}
                #log.info(msg)
                bauble.task.set_message(msg)
                yield  # allow progress bar update

                # don't do anything if the file is empty:
                if filesizes[filename] <= 1:
                    if not table.exists():
                        create_table(table)
                    continue
                # check if the table was in the depends because they
                # could have been dropped whereas table.exists() can
                # return true for a dropped table if the transaction
                # hasn't been committed
                if table in depends or not table.exists():
                    logger.info('%s does not exist. creating.' % table.name)
                    logger.debug('%s does not exist. creating.' % table.name)
                    create_table(table)
                elif table.name not in created_tables and table not in depends:
                    # we get here if the table wasn't previously
                    # dropped because it was a dependency of another
                    # table
                    if not force:
                        msg = _('The <b>%s</b> table already exists in the '
                                'database and may contain some data. If a '
                                'row the import file has the same id as a '
                                'row in the database then the file will not '
                                'import correctly.\n\n<i>Would you like to '
                                'drop the table in the database first. You '
                                'will lose the data in your database if you '
                                'do this?</i>') % table.name
                        response = utils.yes_no_dialog(msg)
                    else:
                        response = True
                    if response:
                        table.drop(bind=connection)
                        create_table(table)

                if self.__cancel or self.__error:
                    break

                # commit the drop of the table we're importing
                transaction.commit()
                transaction = connection.begin()

                # open a temporary reader to get the column keys so we
                # can later precompile our insert statement
                f = open(filename, "rb")
                tmp = UnicodeReader(f, quotechar=QUOTE_CHAR,
                                    quoting=QUOTE_STYLE)
                tmp.next()
                csv_columns = set(tmp.reader.fieldnames)
                del tmp
                f.close()

                # precompute the defaults...this assumes that the
                # default function doesn't depend on state after each
                # row...it shouldn't anyways since we do an insert
                # many instead of each row at a time
                defaults = {}
                for column in table.c:
                    if isinstance(column.default, ColumnDefault):
                        defaults[column.name] = column.default.execute()
                column_names = table.c.keys()

                # check if there are any foreign keys to on the table
                # that refer to itself, if so create a new file with
                # the lines sorted in order of dependency so that we
                # don't get errors about importing values into a
                # foreign_key that don't reference and existin row
                self_keys = filter(lambda f: f.column.table == table,
                                   table.foreign_keys)
                if self_keys:
                    key_pairs = map(lambda x: (x.parent.name, x.column.name),
                                    self_keys)
                    filename = self._toposort_file(filename, key_pairs)

                # the column keys for the insert are a union of the
                # columns in the CSV file and the columns with
                # defaults
                column_keys = list(csv_columns.union(defaults.keys()))
                insert = table.insert(bind=connection).\
                    compile(column_keys=column_keys)

                values = []

                def do_insert():
                    if values:
                        connection.execute(insert, *values)
                    del values[:]
                    percent = float(steps_so_far)/float(total_lines)
                    if 0 < percent < 1.0:
                        pb_set_fraction(percent)

                isempty = lambda v: v in ('', None)

                f = open(filename, "rb")
                reader = UnicodeReader(f, quotechar=QUOTE_CHAR,
                                       quoting=QUOTE_STYLE)
                # NOTE: we shouldn't get this far if the file doesn't
                # have any rows to import but if so there is a chance
                # that this loop could cause problems
                for line in reader:
                    while self.__pause:
                        yield
                    if self.__cancel or self.__error:
                        break

                    # fill in default values and None for "empty"
                    # columns in line
                    for column in table.c.keys():
                        if column in defaults \
                                and (column not in line
                                     or isempty(line[column])):
                            line[column] = defaults[column]
                        elif column in line and isempty(line[column]):
                            line[column] = None
                        elif column in line and line[column] == 'False' and \
                                isinstance(table.c[column].type, Boolean):
                            # need bool value, not 'False' string
                            line[column] = False
                        elif column in line and line[column] == 'True' and \
                                isinstance(table.c[column].type, Boolean):
                            # need bool value, not 'True' string
                            line[column] = True
                            # in SA 0.5.5 and only on an SQLite
                            # database the 'False' will import as True
                            # for some reason whereas True will import
                            # as True automatically...probably because
                            # bool('False') == True
                    values.append(line)
                    steps_so_far += 1
                    if steps_so_far % update_every == 0:
                        do_insert()
                        yield

                if self.__error or self.__cancel:
                    break

                # insert the remainder that were less than update every
                do_insert()

                # we have commit after create after each table is imported
                # or Postgres will complain if two tables that are
                # being imported have a foreign key relationship
                transaction.commit()
                logger.debug('%s: %s' % (
                    table.name,
                    table.select().alias().count().execute().fetchone()[0]))
                transaction = connection.begin()

            logger.debug('creating: %s' % ', '.join([d.name for d in depends]))
            # TODO: need to get those tables from depends that need to
            # be created but weren't created already
            metadata.create_all(connection, depends, checkfirst=True)
        except GeneratorExit, e:
            transaction.rollback()
            raise
        except Exception, e:
            logger.error(e)
            logger.error(traceback.format_exc())
            transaction.rollback()
            self.__error = True
            self.__error_exc = e
            raise
        else:
            transaction.commit()

        # unfortunately inserting an explicit value into a column that
        # has a sequence doesn't update the sequence, we shortcut this
        # by setting the sequence manually to the max(column)+1
        col = None
        try:
            for table, filename in sorted_tables:
                for col in table.c:
                    utils.reset_sequence(col)
        except Exception, e:
            col_name = None
            try:
                col_name = col.name
            except Exception:
                pass
            msg = _('Error: Could not set the sequence for column: %s') \
                % col_name
            utils.message_details_dialog(utils.xml_safe(msg),
                                         traceback.format_exc(),
                                         type=gtk.MESSAGE_ERROR)

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
        fc = gtk.FileChooserDialog(_("Choose file(s) to import…"),
                                   None,
                                   gtk.FILE_CHOOSER_ACTION_OPEN,
                                   (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
                                    gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT))
        fc.set_select_multiple(True)
        fc.connect("selection-changed", on_selection_changed)
        filenames = None
        if fc.run() == gtk.RESPONSE_ACCEPT:
            filenames = fc.get_filenames()
        fc.destroy()
        return filenames

    def on_response(self, widget, response, data=None):
        logger.debug('on_response')
        logger.debug(response)


# TODO: add support for exporting only specific tables

class CSVExporter(object):

    def start(self, path=None):
        if path is None:
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
            raise ValueError(_("CSVExporter: path does not exist.\n%s") % path)

        try:
            # TODO: should we support exporting other metadata
            # besides db.metadata
            bauble.task.queue(self.__export_task(path))
        except Exception, e:
            logger.debug(e)

    def __export_task(self, path):
        filename_template = os.path.join(path, "%s.txt")
        steps_so_far = 0
        ntables = 0
        for table in db.metadata.sorted_tables:
            ntables += 1
            filename = filename_template % table.name
            if os.path.exists(filename):
                msg = _('Export file <b>%(filename)s</b> for '
                        '<b>%(table)s</b> table already exists.\n\n<i>Would '
                        'you like to continue?</i>')\
                    % {'filename': filename, 'table': table.name}
                if utils.yes_no_dialog(msg):
                    return

        def replace(s):
            if isinstance(s, (str, unicode)):
                s.replace('\n', '\\n')
            return s

        def write_csv(filename, rows):
            f = open(filename, 'wb')
            writer = UnicodeWriter(f, quotechar=QUOTE_CHAR,
                                   quoting=QUOTE_STYLE)
            writer.writerows(rows)
            f.close()

        update_every = 30
        for table in db.metadata.sorted_tables:
            filename = filename_template % table.name
            steps_so_far += 1
            fraction = float(steps_so_far)/float(ntables)
            pb_set_fraction(fraction)
            msg = _('exporting %(table)s table to %(filename)s')\
                % {'table': table.name, 'filename': filename}
            bauble.task.set_message(msg)
            logger.info("exporting %s" % table.name)

            # get the data
            results = table.select().execute().fetchall()

            # create empty files with only the column names
            if len(results) == 0:
                write_csv(filename, [table.c.keys()])
                yield
                continue

            rows = []
            rows.append(table.c.keys())  # append col names
            ctr = 0
            for row in results:
                values = map(replace, row.values())
                rows.append(values)
                if ctr == update_every:
                    yield
                    ctr = 0
                ctr += 1
            write_csv(filename, rows)


class CSVImportCommandHandler(pluginmgr.CommandHandler):

    command = 'imcsv'

    def __call__(self, cmd, arg):
        importer = CSVImporter()
        importer.start(arg)


class CSVExportCommandHandler(pluginmgr.CommandHandler):

    command = 'excsv'

    def __call__(self, cmd, arg):
        exporter = CSVExporter()
        exporter.start(arg)


#
# plugin classes
#

class CSVImportTool(pluginmgr.Tool):
    category = _('Import')
    label = _('Comma Separated Value')

    @classmethod
    def start(cls):
        """
        Start the CSV importer.  This tool will also reinitialize the
        plugins after importing.
        """
        msg = _('It is possible that importing data into this database could '
                'destroy or corrupt your existing data.\n\n<i>Would you '
                'like to continue?</i>')
        if utils.yes_no_dialog(msg):
            c = CSVImporter()
            c.start()


class CSVExportTool(pluginmgr.Tool):
    category = _('Export')
    label = _('Comma Separated Value')

    @classmethod
    def start(cls):
        c = CSVExporter()
        c.start()


# TODO: add support to import from the command line
