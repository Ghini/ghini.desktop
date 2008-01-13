#
# bauble module
#
"""
The top level module for Bauble.
"""

import imp, os, sys
import bauble.paths as paths

# major, minor, revision version tuple
version = (0, 8, '0b1')
version_str = '.'.join([str(v) for v in version])

def main_is_frozen():
    """
    Return True if we are running in a py2exe environment, else
    return False
    """
    return (hasattr(sys, "frozen") or # new py2exe
            hasattr(sys, "importers") or # old py2exe
            imp.is_frozen("__main__")) # tools/freeze

import pygtk
if not main_is_frozen():
    pygtk.require("2.0")
else: # main is frozen
    # put library.zip first in the path when using py2exe so libxml2
    # gets imported correctly,
    zipfile = sys.path[-1]
    sys.path.insert(0, zipfile)
    # put the bundled gtk at the beginning of the path to make it the
    # preferred version
    os.environ['PATH'] = '%s%s%s%s%s%s' \
                % (os.pathsep, os.path.join(paths.main_dir(), 'gtk', 'bin'),
                   os.pathsep, os.path.join(paths.main_dir(), 'gtk', 'lib'),
                   os.pathsep, os.environ['PATH'])

import gtk, gobject

# make sure we look in the lib path for modules
sys.path.append(paths.lib_dir())

#sys.stderr.write('sys.path: %s\n' % sys.path)
#sys.stderr.write('PATH: %s\n' % os.environ['PATH'])

# create the user directory
if not os.path.exists(paths.user_dir()):
    os.makedirs(paths.user_dir())

from bauble.i18n import _

import bauble.utils as utils

try:
    import sqlalchemy
    parts = sqlalchemy.__version__.split('.')
    if int(parts[1]) < 4:
        msg = _('This version of Bauble requires SQLAlchemy 0.4.0 or greater.'\
                'Please download and install a newer version of SQLAlchemy ' \
                'from http://www.sqlalchemy.org or contact your system '
                'administrator.')
        utils.message_dialog(msg, gtk.MESSAGE_ERROR)
        sys.exit(1)
except ImportError:
    msg = _('SQLAlchemy not installed. Please install SQLAlchemy from ' \
            'http://www.sqlalchemy.org')
    utils.message_dialog(msg, gtk.MESSAGE_ERROR)
    raise

try:
    import simplejson
    # TODO: check simplejson version
except ImportError:
    msg = _('SimpleJSON not installed. Please install SimpleJSON from ' \
              'http://cheeseshop.python.org/pypi/simplejson')
    utils.message_dialog(msg, gtk.MESSAGE_ERROR)
    raise


# set SQLAlchemy logging level
import logging
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)

#
# global database handler
#
engine = None
metadata = sqlalchemy.MetaData()
Session = None

import datetime
class DateTimeDecorator(sqlalchemy.types.TypeDecorator):

    """
    A DateTime type that converts Python's datetime.datetime to an
    SQLAlchemy DateTime type.
    """

    impl = sqlalchemy.types.DateTime

    def __init__(self, *args, **kwargs):
        super(DateTimeDecorator, self).__init__(*args, **kwargs)

    def convert_bind_param(self, value, engine):
        if isinstance(value, (basestring)):
            format = '%Y-%m-%d %H:%M:%S'
            value = datetime.datetime.strptime(value, format)
        return super(DateTimeDecorator, self).convert_bind_param(value, engine)

    def convert_result_value(self, value, engine):
        return super(DateTimeDecorator, self).convert_result_value(value,
                                                                   engine)

_now = sqlalchemy.func.current_timestamp(type_=sqlalchemy.DateTime)

class Table(sqlalchemy.Table):

    """
    All tables create created for use in Bauble should inherit from
    this Table class.
    """

    def __init__(self, *args, **kwargs):
        super(Table, self).__init__(*args, **kwargs)
        self.append_column(sqlalchemy.Column('_created',
                                             DateTimeDecorator(True),
                                             default=_now))
        self.append_column(sqlalchemy.Column('_last_updated',
                                             DateTimeDecorator(True),
                                             default=_now, onupdate=_now))



class BaubleMapper(object):

    """
    All mappers created for use with Bauble should inherit from this class.
    """

    def __init__(self, **kwargs):
        for attr, value in kwargs.iteritems():
            setattr(self, attr, value)


import traceback
from bauble.utils.log import debug, warning
import bauble.pluginmgr as pluginmgr
from bauble.prefs import prefs
import bauble.error as error


def save_state():
    """
    Save the gui state and preferences.
    """
    # in case we quit before the gui is created
    global gui, prefs
    if gui is not None:
        gui.save_state()
    prefs.save()


def quit():
    """
    Stop all  tasks and quite Bauble.
    """
    import bauble.task as task
    global _quitting
    _quitting = True
    save_state()
    try:
        task._quit()
        gtk.main_quit()
    except RuntimeError: # in case main_quit is called before main
        sys.exit(1)

def _verify_connection(engine, show_error_dialogs=False):
    """
    Test whether a connection to an engine is a valid Bauble database. This
    method will raise an error for the first problem it finds with the
    database.
    @param engine: the engine to test
    @param show_error_dialogs: flag for whether or not to show message dialogs
    detailing the error, default=False
    """
    if show_error_dialogs:
        try:
            return _verify_connection(engine, False)
        except error.MetaTableError:
            msg = _('The database you have connected to does not have the '
                    'bauble meta table.  This usually means that the database '
                    'is either corrupt or it was created with an old version '
                    'of Bauble')
            raise
        except error.TimestampError:
            msg = _('The database you have connected to does not have a '\
                    'timestamp for when it was created. This usually means '\
                    'that there was a problem when you created the '\
                    'database or the database you connected to wasn\'t '\
                    'created with Bauble.')
            utils.message_dialog(msg, gtk.MESSAGE_ERROR)
            raise
        except error.VersionError, e:
            msg = _('You are using Bauble version %(version)s while the '\
                    'database you have connected to was created with '\
                    'version %(db_version)s\n\nSome things might not work as '\
                    'or some of your data may become unexpectedly '\
                    'corrupted.') % \
                    {'version': version_str,
                     'db_version':'%s.%s.%s' % eval(e.version)}
            utils.message_dialog(msg, gtk.MESSAGE_ERROR)
            raise

    import bauble.meta as meta
    # make sure the version information matches or if the bauble
    # table doesn't exists then this may not be a bauble created
    # database
    warning = _('\n\n<i>Warning: If a database does already exists at ' \
                'this connection, creating a new database could corrupt '\
                'it.</i>')
    session = Session()
    query = session.query(meta.BaubleMeta)

    # check that the database we connected to has the bauble meta table
    if not engine.has_table(meta.bauble_meta_table.name):
        raise error.MetaTableError()

    # check that the database we connected to has a "created" timestamp
    # in the bauble meta table
    result = query.filter_by(name = meta.CREATED_KEY).first()
    if result is None:
        raise error.TimestampError()

    # check that the database we connected to has a "version" in the bauble
    # meta table and the the major and minor version are the same
    global version
    result = query.filter_by(name = meta.VERSION_KEY).first()
    if result is None:
        raise error.VersionError(None)
    elif eval(result.value)[0:2] != version[0:2]:
        raise error.VersionError(result.value)

    return True


def open_database(uri, verify=True, show_error_dialogs=False):
    '''
    open a database connection
    '''
##   debug('bauble.open_database(%s)' % uri) # ** WARNING: this can print your passwd
    from sqlalchemy.orm import sessionmaker
    global engine
    global metadata
    global Session
    global version, version_str

    try:
        engine = sqlalchemy.create_engine(uri)
        engine.connect()
        metadata.bind = engine # make engine implicit for metadata
        import bauble.meta as meta
        Session = sessionmaker(bind=engine,autoflush=False, transactional=True)
    except Exception, e:
        msg = _("Could not open connection.\n\n%s") % utils.xml_safe_utf8(e)
        utils.message_details_dialog(msg, traceback.format_exc(),
                                     gtk.MESSAGE_ERROR)
        raise

    if engine is None or not verify:
        return engine

    _verify_connection(engine, show_error_dialogs)

    return engine


def create_database(import_defaults=True):
    '''
    create new Bauble database at the current connection
    '''
    # TODO: when creating a database there shouldn't be any errors
    # on import since we are importing from the default values, we should
    # just force the import and send everything in the database at once
    # instead of using slices, this would make it alot faster but it may
    # make it more difficult to make the interface more responsive,
    # maybe we can use a dialog without the progress bar to show the status,
    # should probably work on the status bar to display this

    # TODO: we create a transaction here and the csv import creates another
    # nested transaction, we need to verify that if we rollback here then all
    # of the changes made by csv import are rolled back as well
    import bauble.meta
    from bauble.task import TaskQuitting
    conn = bauble.engine.connect()
    transaction = conn.begin()
    try:
        # TODO: here we are creating all the tables in the metadata whether
        # they are in the registry or not, we should really only be creating
        # those tables in the registry
        bauble.metadata.drop_all()
        bauble.metadata.create_all()
        # TODO: clearing the insert menu probably shouldn't be here and should
        # probably be pushed into bauble.create_database, the problem is at the
        # moment the data is imported in the pluginmgr.init method so we would
        # have to separate table creations from the init menu

        # clear the insert menu
        if bauble.gui is not None and hasattr(bauble.gui, 'insert_menu'):
            menu = bauble.gui.insert_menu
            submenu = menu.get_submenu()
            for c in submenu.get_children():
                submenu.remove(c)
            menu.show()

        # create the plugin registry and import the default data
        pluginmgr.install('all', import_defaults, force=True)
        meta.bauble_meta_table.insert().execute(name=meta.VERSION_KEY,
                                                value=unicode(bauble.version))
        meta.bauble_meta_table.insert().execute(name=meta.CREATED_KEY,
                                        value=unicode(datetime.datetime.now()))
    except (GeneratorExit, TaskQuitting), e:
        # this is here in case the main windows is closed in the middle
        # of a task
        transaction.rollback()
        conn.close()
        raise
    except Exception, e:
        transaction.rollback()
        conn.close()
        msg = _('Error creating tables. Your database may be corrupt.'\
                '\n\n%s') % utils.xml_safe_utf8(e)
        debug(traceback.format_exc())
        utils.message_details_dialog(msg, traceback.format_exc(),
                                     gtk.MESSAGE_ERROR)
        raise
    else:
        transaction.commit()
        conn.close()


def set_busy(busy):
    """
    Set the interface to appear busy.
    """
    global gui
    if gui is None or gui.widgets.main_box is None:
        return
    # main_box is everything but the statusbar
    gui.widgets.main_box.set_sensitive(not busy)
    if busy:
        gui.window.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
    else:
        gui.window.window.set_cursor(None)


last_handler = None

def command_handler(cmd, arg):
    """
    Call a command handler.

    @param cmd: the name of the command to call
    @param arg: the arg to pass to the command handler
    """
    global last_handler
    handler_cls = None
    try:
        handler_cls = pluginmgr.commands[cmd]
    except KeyError, e:
        if cmd is None:
            utils.message_dialog(_('No default handler registered'))
        else:
            utils.message_dialog(_('No command handler for %s' % cmd))
            return

    if not isinstance(last_handler, handler_cls):
        last_handler = handler_cls()
    handler_view = last_handler.get_view()
    if type(gui.get_view()) != type(handler_view):
        gui.set_view(handler_view)
    try:
        last_handler(arg)
    except Exception, e:
        utils.message_details_dialog(str(e), traceback.format_exc(),
                                              gtk.MESSAGE_ERROR)


try:
    # TODO: this should really only be set once but for some reason its being
    # reset,
    gui
except NameError:
    gui=None


conn_default_pref = "conn.default"
conn_list_pref = "conn.list"

def main(uri=None):
    """
    Initialize Bauble and start the main Bauble interface.
    """
    # initialize threading
    gtk.gdk.threads_init()
    gtk.gdk.threads_enter()

    # declare module level variables
    global prefs, conn_name, db_engine, gui, default_icon
    gui = conn_name = db_engine = None

    default_icon = os.path.join(paths.lib_dir(), "images", "icon.svg")

    # intialize the user preferences
    prefs.init()

    import bauble.pluginmgr as pluginmgr

    open_exc = None
    # open default database
    if uri is None:
        from bauble.connmgr import ConnectionManager
        default_conn = prefs[conn_default_pref]
        while True:
            if uri is None or conn_name is None:
                cm = ConnectionManager(default_conn)
                conn_name, uri = cm.start()
                if conn_name is None:
                    quit()
            try:
                if open_database(uri, conn_name, True):
                    prefs[conn_default_pref] = conn_name
                    break
                else:
                    uri = conn_name = None
            except error.VersionError, e:
                warning(e)
                break
            except error.DatabaseError, e:
                debug(e)
                traceback.format_exc()
                open_exc = e
                break
    else:
        open_database(uri, None, True)

    # load the plugins
    pluginmgr.load()

    # save any changes made in the conn manager before anything else has
    # chance to crash
    prefs.save()

    # set the default command handler
    import bauble.view as view
    pluginmgr.commands[None] = view.DefaultCommandHandler

    # now that we have a connection create the gui, start before the plugins
    # are initialized in case they have to do anything like add a menu
    import bauble._gui as _gui
    gui = _gui.GUI()

    def _post_loop():
##      debug('__post_loop')
        gtk.gdk.threads_enter()
        ok_to_init_plugins = True
        try:
            if isinstance(open_exc, error.DatabaseError):
                ok_to_init_plugins = False
                msg = _('Would you like to create a new Bauble database at ' \
                        'the current connection?\n\n<i>Warning: If there is '\
                        'already a database at this connection any existing '\
                        'data will be destroyed!</i>')
                if utils.yes_no_dialog(msg, yes_delay=2):
                    create_database()
                    ok_to_init_plugins = True
        except Exception, e:
            debug(e)
            pass
            #utils.message_dialog('create failed', gtk.ERROR_MESSAGE)
        else:
            # create_database creates all tables registered with the default
            # metadata so the pluginmgr should be loaded after the database
            # is created so we don't inadvertantly create tables from the
            # plugins
            if ok_to_init_plugins:
                pluginmgr.init()
            # set the default connection
            prefs[conn_default_pref] = conn_name

        gtk.gdk.threads_leave()

    gobject.idle_add(_post_loop)

    gui.show()
    gtk.main()
    gtk.gdk.threads_leave()
