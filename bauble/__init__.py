#
# bauble module
#

import imp, os, sys
import bauble.paths as paths

# major, minor, revision 
# should be updated for each release of bauble

# this is from the python docs, we should probably have something similar
# for bauble so we can do release candidate and beta releases
# version_info 
# A tuple containing the five components of the version number: 
# major, minor, micro, releaselevel, and serial. All values except 
# releaselevel are integers; the release level is 'alpha', 'beta', 
# 'candidate', or 'final'. The version_info value corresponding to the Python 
# version 2.0 is (2, 0, 0, 'final', 0). New in version 2.0. 
version = (0,7,0)
version_str = '%s.%s.%s' % (version)

def main_is_frozen():
   return (hasattr(sys, "frozen") or # new py2exe
           hasattr(sys, "importers") or # old py2exe
           imp.is_frozen("__main__")) # tools/freeze

import pygtk
if not main_is_frozen():
   pygtk.require("2.0")     
else: # main is frozen
   # put library.zip first in the path when using py2exe so libxml2 gets 
   # imported correctly, 
   zipfile = sys.path[-1]
   sys.path.insert(0,zipfile)
   # put the bundled gtk at the beginning of the path to make it the 
   # preferred version
   os.environ['PATH'] = '%s%s%s%s%s%s' % (os.pathsep, os.path.join(paths.main_dir(), 'gtk', 'bin'),
                                          os.pathsep, os.path.join(paths.main_dir(), 'gtk', 'lib'),
                                          os.pathsep, os.environ['PATH'])
   
import gtk
import bauble.utils as utils

# make sure we look in the lib path for modules
sys.path.append(paths.lib_dir())

# create the user directory
if not os.path.exists(paths.user_dir()):
    os.makedirs(paths.user_dir())

from bauble.i18n import *
try:
    from sqlalchemy import *
    # TODO: check sqlalchemy version
except ImportError:
    msg = _('SQLAlchemy not installed. Please install SQAlchemy from ' \
            'http://www.sqlalchemy.org')
    utils.message_dialog(msg, gtk.MESSAGE_ERROR)    
    raise


# set SQLAlchemy logging level
import logging
#logging.getLogger('sqlalchemy').setLevel(logging.DEBUG)
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)

# TODO: make this work, we get strange errors when using this, probably because
# of the way table is implemented, with a singleton metaclass
#
#class BaubleTable(Table):
#    
#    def __init__(self, *args, **kwargs):
#        # TODO: add _created
#        super(BaubleTable, self).__init__(*args, **kwargs)
#        super(BaubleTable, self).append_column(Column('_last_updated', DateTime, 
#                                                      onupdate=func.current_timestamp()))

class BaubleMapper(object):
    
    def __init__(self, **kwargs):
        for attr, value in kwargs.iteritems():
            setattr(self, attr, value)


import traceback
from bauble.utils.log import debug
from bauble.i18n import *
from bauble.error import *
import bauble.pluginmgr
#from bauble._app import BaubleApp
#app = BaubleApp()

from bauble.prefs import prefs


def save_state():
    # in case we quit before the gui is created
    global gui, prefs    
    if gui is not None:
        gui.save_state()
    prefs.save()


def quit():
    save_state()
    try:
        gtk.main_quit()
    except RuntimeError: # in case main_quit is called before main
        sys.exit(1)


def open_database(uri, name=None):    
    '''
    open a database connection
    '''
#    debug(uri) # ** WARNING: this can print your passwd
    import bauble.db as db
    global db_engine

    warning = _('\n\n<i>Warning: If a database does already exists at ' \
                'this connection, creating a new database could corrupt '\
                'it.</i>')
    try:
        db_engine = db.open(uri)    
    except db.MetaTableError, e:
        msg = _('The database you connected to connected to wasn\'t created '\
                'with Bauble.')
        utils.message_dialog(msg, gtk.MESSAGE_ERROR)
        raise
    except db.VersionError, e:
        msg = _('You are using Bauble version %(version)s while the '\
                'database you have connected to was created with '\
                'version %(db_version)s\n\nSome things might not work as '\
                'or some of your data may become unexpectedly '\
                'corrupted.') % {'version': bauble.version_str, 
                                 'db_version': '%s' % (e.version)}
        utils.message_dialog(msg, gtk.MESSAGE_WARNING)
        raise
    except db.RegistryError:
        msg = _('Could not get the plugin registry from the database. '\
                'Most likely this is because the database you have '\
                'connected to wasn\'t created with Bauble.')
        utils.message_dialog(msg, gtk.MESSAGE_ERROR)
        raise
    except db.TimestampError:
        msg = _('The database you have connected to does not have a '\
                'timestamp for when it was created. This usually means '\
                'that there was a problem when you created the '\
                'database or the database you connected to wasn\'t'\
                'created with Bauble.')
        utils.message_dialog(msg, gtk.MESSAGE_ERROR)
        raise
    except Exception, e:
        msg = _('There was an error connecting to the database.\n\n ** %s' % \
                str(utils.xml_safe(e)))
        utils.message_dialog(msg, gtk.MESSAGE_ERROR)
        raise
        
    return db_engine


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
    # TODO: *** important ***
    # this work should be done in a transaction, i think the best way to do
    # this would be to pass a metadata or engine or connection object to
    # the importer that holds the transaction we should work in
    
    import bauble.db as db
#    bauble.app.set_busy(True)
    try:
        db.create()
        # create for each of the plugins
#        if import_defaults:
#            for p in plugins.values():
#                default_filenames.extend(p.default_filenames())                
#            default_basenames = [os.path.basename(f) for f in default_filenames]                        
#            # import default data
#            if len(default_filenames) > 0:
#                from bauble.plugins.imex_csv import CSVImporter
#                csv = CSVImporter()    
#                csv.start(default_filenames)
    except Exception, e:
        msg = _('Error creating tables. Your database may be corrupt.'\
                '\n\n%s"') % utils.xml_safe(e)
        debug(traceback.format_exc())
        utils.message_details_dialog(msg, traceback.format_exc(),
                                     gtk.MESSAGE_ERROR)
        # TODO: should be do a rollback here so that we return to the previous
        # database state, we would first need a begiin at the beginning of 
        # this method for it to work correction i think
        # UPDATE: this wouldn't work since csv.start() doesn't block, need 
        # another way to handle the transaction, maybe pass it the csv start
        # and tell it to commit when it's done. that not good though.    
#    bauble.app.set_busy(False)
        

def set_busy(busy):
    global gui
    if gui is None:
        return
    gui.window.set_sensitive(not busy)
    if busy:
        gui.window.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
    else:
        gui.window.window.set_cursor(None)



def main():
    
    # initialize threading
    gtk.gdk.threads_init() 
    gtk.gdk.threads_enter()
    
    # declare module level variables
    global prefs, conn_name, db_engine, gui, default_icon
    gui = None
    
    default_icon = os.path.join(paths.lib_dir(), "images", "icon.svg")
    
    # intialize the user preferences
    prefs.init() 
            
    # open default database
    from bauble.conn_mgr import ConnectionManager
    default_conn = prefs[prefs.conn_default_pref]
    uri = None
    while True:                    
        if uri is None or conn_name is None:
            cm = ConnectionManager(default_conn)            
            conn_name, uri = cm.start()
        if conn_name is None:
            quit()
        try:
            open_database(uri, conn_name)
            break
        except db.DatabaseError, e:
            msg = _('Would you like to create a new Bauble database at the '
                    'current connection?\n\n<i>Warning: If there is already a '
                    'database at this connection any existing data will be '
                    'destroyed!</i>')
            if utils.yes_no_dialog(msg):
                create_database()
                
    
    # create_database creates all tables registered with the default metadata
    # so the pluginmgr should be loaded after the database is created so
    # we don't inadvertantly create tables from the plugins
    bauble.pluginmgr.load()
    bauble.pluginmgr.init()
        
    # set the default connection
    prefs[prefs.conn_default_pref] = conn_name
        
    # now that we have a connection create the gui
    import bauble._gui as _gui
    gui = _gui.GUI()
    gui.window.show()
    gtk.main()
    gtk.gdk.threads_leave()
