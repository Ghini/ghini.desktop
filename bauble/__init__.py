#  Copyright (c) 2005,2006,2007,2008,2009
#  Brett Adams <brett@belizebotanic.org>
#  This is free software, see GNU General Public License v2 for details.
"""
The top level module for Bauble.
"""

import imp, os, sys
import bauble.paths as paths
import bauble.i18n

# major, minor, revision version tuple
version = '1.0.0b4' # :bump
"""The Bauble version.
"""
version_tuple = version.split('.')

def main_is_frozen():
    """
    Return True if we are running in a py2exe environment, else
    return False
    """
    return (hasattr(sys, "frozen") or # new py2exe
            hasattr(sys, "importers") or # old py2exe
            imp.is_frozen("__main__")) # tools/freeze


if main_is_frozen(): # main is frozen
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


# if not hasattr(gtk.Widget, 'set_tooltip_markup'):
#     msg = _('Bauble requires GTK+ version 2.12 or greater')
#     utils.message_dialog(msg, gtk.MESSAGE_ERROR)
#     sys.exit(1)

# make sure we look in the lib path for modules
sys.path.append(paths.lib_dir())

#sys.stderr.write('sys.path: %s\n' % sys.path)
#sys.stderr.write('PATH: %s\n' % os.environ['PATH'])


# set SQLAlchemy logging level
import logging
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)

gui = None
"""bauble.gui is the instance :class:`bauble.ui.GUI`
"""

default_icon = None
"""The default icon.
"""

conn_name = None
"""The name of the current connection.
"""

import traceback
import bauble.error as err


def save_state():
    """
    Save the gui state and preferences.
    """
    from bauble.prefs import prefs
    # in case we quit before the gui is created
    if gui is not None:
        gui.save_state()
    prefs.save()


def quit():
    """
    Stop all tasks and quit Bauble.
    """
    import gtk
    import bauble.utils as utils
    from bauble.utils.log import error
    try:
        import bauble.task as task
    except Exception, e:
        error('bauble.quit(): %s' % utils.utf8(e))
    else:
        task.kill()
    try:
        save_state()
        gtk.main_quit()
    except RuntimeError, e:
        # in case main_quit is called before main, e.g. before
        # bauble.main() is called
        sys.exit(1)


# TODO: this functions seems redundant when we already have
# bauble.gui.set_busy
def set_busy(busy):
    """
    Set the interface to appear busy.
    """
    import gtk.gdk
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

    :param cmd: The name of the command to call
    :type cmd: str

    :param arg: The arg to pass to the command handler
    :type arg: list
    """
    import gtk
    from bauble.utils.log import error
    import bauble.utils as utils
    import bauble.pluginmgr as pluginmgr
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
    old_view = gui.get_view()
    if type(old_view) != type(handler_view) and handler_view:
        # remove the accel_group from the window if the previous view
        # had one
        if hasattr(old_view, 'accel_group'):
            gui.window.remove_accel_group(old_view.accel_group)
        # add the new view and its accel_group if it has one
        gui.set_view(handler_view)
        if hasattr(handler_view, 'accel_group'):
            gui.window.add_accel_group(handler_view.accel_group)
    try:
        last_handler(cmd, arg)
    except Exception, e:
        msg = utils.xml_safe_utf8(e)
        error('bauble.command_handler(): %s' % msg)
        utils.message_details_dialog(msg, traceback.format_exc(),
                                     gtk.MESSAGE_ERROR)


conn_default_pref = "conn.default"
conn_list_pref = "conn.list"

def main(uri=None):
    """
    Run the main Bauble application.
    """
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
    import pygtk
    if not main_is_frozen():
        pygtk.require("2.0")

    display = gtk.gdk.display_get_default()
    if display is None:
        print _("**Error: Bauble must be run in a windowed environment.")
        sys.exit(1)

    import bauble.pluginmgr as pluginmgr
    from bauble.prefs import prefs
    import bauble.utils as utils
    from bauble.utils.log import debug, warning, error

    # create the user directory
    if not os.path.exists(paths.user_dir()):
        os.makedirs(paths.user_dir())

    # initialize threading
    gtk.gdk.threads_init()
    gtk.gdk.threads_enter()

    try:
        import bauble.db as db
    except Exception, e:
        utils.message_dialog(utils.xml_safe_utf8(e), gtk.MESSAGE_ERROR)
        sys.exit(1)

    # declare module level variables
    global gui, default_icon, conn_name

    default_icon = os.path.join(paths.lib_dir(), "images", "icon.svg")

    # intialize the user preferences
    prefs.init()

    open_exc = None
    # open default database
    if uri is None:
        from bauble.connmgr import ConnectionManager
        default_conn = prefs[conn_default_pref]
        while True:
            if not uri or not conn_name:
                cm = ConnectionManager(default_conn)
                conn_name, uri = cm.start()
                if conn_name is None:
                    quit()
            try:
                if db.open(uri, True, True):
                    prefs[conn_default_pref] = conn_name
                    break
                else:
                    uri = conn_name = None
            except err.VersionError, e:
                warning(e)
                db.open(uri, False)
                break
            except (err.EmptyDatabaseError, err.MetaTableError,
                    err.VersionError, err.TimestampError,
                    err.RegistryError), e:
                warning(e)
                open_exc = e
                # reopen without verification so that db.Session and
                # db.engine, db.metadata will be bound to an engine
                db.open(uri, False)
                break
            except err.DatabaseError, e:
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
        db.open(uri, True, True)


    # make session available as a convenience to other modules
    #Session = db.Session

    # load the plugins
    pluginmgr.load()

    # save any changes made in the conn manager before anything else has
    # chance to crash
    prefs.save()

    # set the default command handler
    import bauble.view as view
    pluginmgr.register_command(view.DefaultCommandHandler)

    # now that we have a connection create the gui, start before the plugins
    # are initialized in case they have to do anything like add a menu
    #import bauble._gui as _gui
    import bauble.ui as ui
    gui = ui.GUI()

    def _post_loop():
        gtk.gdk.threads_enter()
        try:
            if isinstance(open_exc, err.DatabaseError):
                msg = _('Would you like to create a new Bauble database at ' \
                        'the current connection?\n\n<i>Warning: If there is '\
                        'already a database at this connection any existing '\
                        'data will be destroyed!</i>')
                if utils.yes_no_dialog(msg, yes_delay=2):
                    try:
                        db.create()
                        # db.create() creates all tables registered with
                        # the default metadata so the pluginmgr should be
                        # loaded after the database is created so we don't
                        # inadvertantly create tables from the plugins
                        pluginmgr.init()
                        # set the default connection
                        prefs[conn_default_pref] = conn_name
                    except Exception, e:
                        utils.message_details_dialog(utils.xml_safe_utf8(e),
                                                     traceback.format_exc(),
                                                     gtk.MESSAGE_ERROR)
                        error(e)
            else:
                pluginmgr.init()
        except Exception, e:
            warning(traceback.format_exc())
            warning(e)
            utils.message_dialog(utils.utf8(e), gtk.MESSAGE_WARNING)
        gtk.gdk.threads_leave()

    gobject.idle_add(_post_loop)

    gui.show()
    gtk.main()
    gtk.gdk.threads_leave()
