#
# bauble module
#
"""
The top level module for Bauble.
"""

import imp, os, sys
import bauble.paths as paths
from bauble.i18n import _


# major, minor, revision version tuple
version = (0, 9, '0b1')
version_str = '.'.join([str(v) for v in version])
#from bauble.version import *

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

# TODO: it would be nice to show a Tk dialog here saying we can't
# import gtk...but then we would have to include all of the Tk libs in
# with the win32 batteries-included installer
try:
    import gtk, gobject
except ImportError, e:
    print _('** Error: could not import gtk and/or gobject')
    print e
    if sys.platform == 'win32':
        print _('Please make sure that GTK_ROOT\\bin is in your PATH.')
    sys.exit(1)


import gtk.gdk
display = gtk.gdk.display_get_default()
if display is None:
    print _("**Error: Bauble must be run in a windowed environment.")
    sys.exit(1)

# setup glade internationalization
import gtk.glade
gtk.glade.bindtextdomain('bauble', paths.locale_dir())
gtk.glade.textdomain('bauble')

import bauble.utils as utils

# if not hasattr(gtk.Widget, 'set_tooltip_markup'):
#     msg = _('Bauble requires GTK+ version 2.12 or greater')
#     utils.message_dialog(msg, gtk.MESSAGE_ERROR)
#     sys.exit(1)

# make sure we look in the lib path for modules
sys.path.append(paths.lib_dir())

#sys.stderr.write('sys.path: %s\n' % sys.path)
#sys.stderr.write('PATH: %s\n' % os.environ['PATH'])

# create the user directory
if not os.path.exists(paths.user_dir()):
    os.makedirs(paths.user_dir())

try:
    import sqlalchemy as sa
    parts = sa.__version__.split('.')
    if int(parts[1]) < 5:
        msg = _('This version of Bauble requires SQLAlchemy 0.5.0 or greater.'\
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
    # TODO: check simplejson version....why, do we require a specific version?
except ImportError:
    msg = _('SimpleJSON not installed. Please install SimpleJSON from ' \
            'http://cheeseshop.python.org/pypi/simplejson')
    utils.message_dialog(msg, gtk.MESSAGE_ERROR)
    raise


# set SQLAlchemy logging level
import logging
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)

import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta
import sqlalchemy.types as types
from datetime import datetime

# TODO: should we allow custom formats?
# TODO: do formats depend on locale
class DateTime(types.TypeDecorator):
    """
    A DateTime type that allows strings
    """
    impl = types.DateTime

    def process_bind_param(self, value, dialect):
        from datetime import datetime
        # TODO: what about microseconds
        if isinstance(value, basestring):
            date, time = value.split(' ')
            y, mo, d = date.split('-')
            h, mi, s = time.split(':')
            return datetime(*map(int, (y, mo, d, h, mi, s)))

        return value

    def process_result_value(self, value, dialect):
        return value

    def copy(self):
        return DateTime()


class Date(types.TypeDecorator):
    """
    A Date type that allows Date strings
    """
    impl = types.Date

    def process_bind_param(self, value, dialect):
        if isinstance(value, basestring):
            if ' ' in value:
                date, time = value.split(' ')
                warning('bauble.Date.process_bind_param: truncating %s to %s' \
                        % (value, date))
            else:
                date = value
            y, mo, d = date.split('-')
            return datetime(*map(int, (y, mo, d)))
        return value

    def process_result_value(self, value, dialect):
        return value

    def copy(self):
        return Date()


class MapperBase(DeclarativeMeta):
    """
    MapperBase adds the id, _created and _last_updated columns to all tables.
    """

    def __init__(cls, classname, bases, dict_):
        #print >>sys.stderr, dict_
        if '__tablename__' in dict_:
            seqname = '%s_seq_id' % dict_['__tablename__']
            dict_['id'] = sa.Column('id', sa.Integer, sa.Sequence(seqname),
                                    primary_key=True)
            dict_['_created'] = sa.Column('_created', DateTime(True),
                                          default=sa.func.now())
            dict_['_last_updated'] = sa.Column('_last_updated',
                                               DateTime(True),
                                               default=sa.func.now())
        super(MapperBase, cls).__init__(classname, bases, dict_)


#
# global database variables
#
engine = None
Base = declarative_base(metaclass=MapperBase)
metadata = Base.metadata
Session = None
gui = None
default_icon = None
conn_name = None

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
    if gui is not None:
        gui.save_state()
    prefs.save()


def quit():
    """
    Stop all  tasks and quite Bauble.
    """
    import bauble.task as task
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
##    debug('entered _verify_connection(%s)' % show_error_dialogs)
    if show_error_dialogs:
        try:
            return _verify_connection(engine, False)
        except error.EmptyDatabaseError:
            msg = _('The database you have connected to is empty.')
            utils.message_dialog(msg, gtk.MESSAGE_ERROR)
            raise
        except error.MetaTableError:
            msg = _('The database you have connected to does not have the '
                    'bauble meta table.  This usually means that the database '
                    'is either corrupt or it was created with an old version '
                    'of Bauble')
            utils.message_dialog(msg, gtk.MESSAGE_ERROR)
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
        except pluginmgr.RegistryEmptyError, e:
            msg = _('The database you have connected to does not have a '\
                    'valid plugin registry.  This means that the ' \
                    'database could be corrupt or was interrupted while ' \
                    'creating a new database at this connection.')
            utils.message_dialog(msg, gtk.MESSAGE_ERROR)
            raise

    if len(engine.table_names()) == 0:
        raise error.EmptyDatabaseError()

    import bauble.meta as meta
    # check that the database we connected to has the bauble meta table
    if not engine.has_table(meta.BaubleMeta.__tablename__):
        raise error.MetaTableError()

    from sqlalchemy.orm import sessionmaker
    # if we don't close this session before raising an exception then we
    # will probably get deadlocks....i'm not really sure why
    session = sessionmaker(bind=engine)()
    query = session.query#(meta.BaubleMeta)

    # check that the database we connected to has a "created" timestamp
    # in the bauble meta table
    result = query(meta.BaubleMeta).filter_by(name = meta.CREATED_KEY).first()
    if not result:
        session.close()
        raise error.TimestampError()

    # check that the database we connected to has a "version" in the bauble
    # meta table and the the major and minor version are the same
    result = query(meta.BaubleMeta).filter_by(name = meta.VERSION_KEY).first()
    if not result:
        session.close()
        raise error.VersionError(None)
    elif eval(result.value)[0:2] != version[0:2]:
        session.close()
        raise error.VersionError(result.value)

    # will raise RegistryEmptyError if the plugin registry does not exist in
    # the meta table
    try:
        pluginmgr.Registry(session=session)
    except:
        session.close()
        raise

    return True


def open_database(uri, verify=True, show_error_dialogs=False):
    '''
    open a database connection

    @returns: On a successful connection a new engine is returned
    which is the same as bauble.engine, on failure None is returned
    and bauble.engine remains as it was previously
    '''
    # ** WARNING: this can print your passwd
##    debug('bauble.open_database(%s)' % uri)
    from sqlalchemy.orm import sessionmaker
    global engine
    new_engine = None
    new_engine = sa.create_engine(uri)
    new_engine.contextual_connect()
    def _bind():
        """bind metadata to engine and create sessionmaker """
        global Session, engine
        engine = new_engine
        metadata.bind = engine # make engine implicit for metadata
        Session = sessionmaker(bind=engine, autoflush=False)

    if new_engine is not None and not verify:
        _bind()
        return engine
    elif new_engine is None:
        return None

    _verify_connection(new_engine, show_error_dialogs)
    _bind()
    return engine


def create_database(import_defaults=True):
    '''
    Create new Bauble database at the current connection
    @param import_defaults: default=True
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
##    debug('entered bauble.create_database()')
    import bauble.meta as meta
    from bauble.task import TaskQuitting
    import datetime
    #transaction = engine.contextual_connect().begin()
    session = Session()
    try:
        # TODO: here we are creating all the tables in the metadata whether
        # they are in the registry or not, we should really only be creating
        # those tables in the registry
        metadata.drop_all(checkfirst=True)
        metadata.create_all()
##       debug('dropped and created')
        # TODO: clearing the insert menu probably shouldn't be here and should
        # probably be pushed into bauble.create_database, the problem is at the
        # moment the data is imported in the pluginmgr.init method so we would
        # have to separate table creations from the init menu

        # clear the insert menu
        if gui is not None and hasattr(gui, 'insert_menu'):
            menu = gui.insert_menu
            submenu = menu.get_submenu()
            for c in submenu.get_children():
                submenu.remove(c)
            menu.show()

        # create the plugin registry and import the default data
        meta_table = meta.BaubleMeta.__table__
        meta_table.insert().execute(name=meta.VERSION_KEY,
                                    value=unicode(version))
        meta_table.insert().execute(name=meta.CREATED_KEY,
                                        value=unicode(datetime.datetime.now()))
        pluginmgr.install('all', import_defaults, force=True)
    except (GeneratorExit, TaskQuitting), e:
        # this is here in case the main windows is closed in the middle
        # of a task
        debug(e)
#        debug('bauble.create_database(): rollback')
        #transaction.rollback()
        session.rollback()
        raise
    except Exception, e:
        debug(e)
        #debug('bauble.create_database(): rollback')
        #transaction.rollback()
        session.rollback()
        msg = _('Error creating tables.\n\n%s') % utils.xml_safe_utf8(e)
        debug(traceback.format_exc())
        utils.message_details_dialog(msg, traceback.format_exc(),
                                     gtk.MESSAGE_ERROR)
        raise
    else:
##        debug('bauble.create_database(): committing')
        session.commit()
        #transaction.commit()


def set_busy(busy):
    """
    Set the interface to appear busy.
    """
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
    global prefs, gui, default_icon, conn_name

    default_icon = os.path.join(paths.lib_dir(), "images", "icon.svg")

    # intialize the user preferences
    prefs.init()

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
                if open_database(uri, True, True):
                    prefs[conn_default_pref] = conn_name
                    break
                else:
                    uri = conn_name = None
            except error.VersionError, e:
                warning(e)
                open_database(uri, False)
                break
            except (error.EmptyDatabaseError, error.MetaTableError,
                    pluginmgr.RegistryEmptyError, error.VersionError,
                    error.TimestampError), e:
                warning(e)
                open_exc = e
                # reopen without verification so that bauble.Session and
                # bauble.engine, bauble.metadata will be bound to an engine
                open_database(uri, False)
                break
            except error.DatabaseError, e:
                debug(e)
                #traceback.format_exc()
                open_exc = e
                #break
            except Exception, e:
                msg = _("Could not open connection.\n\n%s") % \
                      utils.xml_safe_utf8(e)
                utils.message_details_dialog(msg, traceback.format_exc(),
                                             gtk.MESSAGE_ERROR)
                uri = None
    else:
        open_database(uri, True, True)

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
        gtk.gdk.threads_enter()
        try:
            if isinstance(open_exc, error.DatabaseError):
                msg = _('Would you like to create a new Bauble database at ' \
                        'the current connection?\n\n<i>Warning: If there is '\
                        'already a database at this connection any existing '\
                        'data will be destroyed!</i>')
                if utils.yes_no_dialog(msg, yes_delay=2):
                    try:
                        create_database()
                        # create_database creates all tables registered with
                        # the default metadata so the pluginmgr should be
                        # loaded after the database is created so we don't
                        # inadvertantly create tables from the plugins
                        pluginmgr.init()
                        # set the default connection
                        prefs[conn_default_pref] = conn_name
                    except Exception, e:
                        debug(e)
            else:
                pluginmgr.init()
        except Exception, e:
            debug(e)
            #utils.message_dialog('create failed', gtk.ERROR_MESSAGE)
        gtk.gdk.threads_leave()

    gobject.idle_add(_post_loop)

    gui.show()
    gtk.main()
    gtk.gdk.threads_leave()
