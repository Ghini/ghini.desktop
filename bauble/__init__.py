#
# Copyright (c) 2005,2006,2007,2008,2009 Brett Adams <brett@belizebotanic.org>
# Copyright (c) 2012-2017 Mario Frasca <mario@anche.no>
# Copyright 2017 Jardín Botánico de Quito
# Copyright (c) 2016 Ross Demuth <rossdemuth123@gmail.com>
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
"""
The top level module for Ghini.
"""
import logging
import os
import sys
import traceback
from gettext import gettext as _
from typing import Any

# import bauble.db as db
# import bauble.error as err
# import bauble.paths as paths
# import bauble.pluginmgr as pluginmgr
# import bauble.utils as utils

# import debugpy
# from bauble.gtkinit import Gio, GLib, Gtk
# from bauble.prefs import use_sentry_client_pref
# from bauble.view import DefaultCommandHandler

zipfile: Any
default_icon: Any
import warnings

from sqlalchemy.exc import SAWarning

__all__ = ["version", "version_tuple", "app", "gtk_app"]

warnings.simplefilter("always", SAWarning)

from bauble import _version

version: Any = _version.__version__
version_tuple: Any = tuple(
    int(part) if part.isdigit() else part for part in version.split(".")
)

# extract release date (assuming setuptools_scm local_scheme='node-and-date')
import re

match: Any = re.search(r"\+g[0-9a-f]+\.d(\d{8})", version)
release_version: Any = None
release_date: Any = match.group(1) if match else None
installation_date: Any = os.environ.get("BUILD_DATE", "1970-01-01T00:00:00Z")


#from bauble.connmgr import start_connection_manager

# debugpy.breakpoint()

logger: Any = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
consoleLevel: Any = logging.INFO


try:
    import faulthandler

    faulthandler.enable()
except:
    pass


def pb_set_fraction(fraction) -> None:
    """set progressbar fraction safely

    provides a safe way to handle the progress bar if the gui isn't started,
    we use this in the tests where there is no gui
    """
    if gui is not None and gui.progressbar is not None:
        gui.progressbar.set_fraction(fraction)


def pb_grab() -> None:
    if gui is not None and gui.progressbar is not None:
        gui.set_busy(True)
        gui.progressbar.show()
        gui.progressbar.set_fraction(0)


def pb_release() -> None:
    if gui is not None and gui.progressbar is not None:
        gui.progressbar.hide()
        gui.set_busy(False)



# if not hasattr(Gtk.Widget, 'set_tooltip_markup'):
#     msg = _('Ghini requires GTK+ version 2.12 or greater')
#     utils.message_dialog(msg, Gtk.MessageType.ERROR)
#     sys.exit(1)



# if False:
#    sys.stderr.write('sys.path: %s\n' % sys.path)
#    sys.stderr.write('PATH: %s\n' % os.environ['PATH'])


# set SQLAlchemy logging level

logging.getLogger("sqlalchemy").setLevel(logging.WARNING)

gui: Any = None
"""bauble.gui is the instance :class:`bauble.ui.GUI`
"""



conn_name: Any = None
"""The name of the current connection.
"""


def save_state() -> None:
    """
    Save the gui state and preferences.
    """
    from bauble.prefs import prefs

    # in case we quit before the gui is created
    if gui is not None:
        gui.save_state()
    prefs.save()


def quit() -> None:
    """
    Stop all tasks and quit Ghini.
    """
    # from bauble.gtkinit import Gtk

    import bauble.utils as utils

    try:
        import bauble.task as task
    except Exception as e:
        logger.error(f"bauble.quit(): {utils.to_unicode(e)}")
    else:
        task.kill()
    try:
        save_state()
    except RuntimeError:
        pass
    sys.exit(1)


last_handler: Any = None


def command_handler(cmd, arg) -> None:
    """
    Call a command handler.

    :param cmd: The name of the command to call
    :type cmd: str

    :param arg: The arg to pass to the command handler
    :type arg: list
    """
    logger.debug(f"entering ui.command_handler {cmd} {arg}")
    # from bauble.gtkinit import Gtk

    import bauble.pluginmgr as pluginmgr
    import bauble.utils as utils

    global last_handler
    handler_cls = None
    try:
        handler_cls = pluginmgr.commands[cmd]
    except KeyError:
        if cmd is None:
            utils.message_dialog(_("No default handler registered"))
        else:
            utils.message_dialog(_("No command handler for %s") % cmd)
            return

    if not isinstance(last_handler, handler_cls):
        last_handler = handler_cls()
    handler_view = last_handler.get_view()
    old_view = gui.get_view()
    if type(old_view) != type(handler_view) and handler_view:
        # remove the accel_group from the window if the previous view
        # had one
        if hasattr(old_view, "accel_group"):
            gui.window.remove_accel_group(old_view.accel_group)
        # add the new view, and its accel_group if it has one
        gui.set_view(handler_view)
        if hasattr(handler_view, "accel_group"):
            gui.window.add_accel_group(handler_view.accel_group)
    try:
        last_handler(f"{cmd}", arg)
    except Exception as e:
        msg = utils.xml_safe(e)
        logger.error(f"bauble.command_handler(): {msg}")
        utils.message_details_dialog(msg, traceback.format_exc(), Gtk.MessageType.ERROR)


conn_default_pref: str = "conn.default"
conn_list_pref: str = "conn.list"



class GhiniApp:
    """Manages application logic without subclassing Gtk.Application."""

    gui: Any
    open_exc: Any
    conn_name: Any
    uri: Any
    gtk_app: Any

    def __init__(self) -> None:
        from bauble.gtkinit import Gio, Gtk
        self.Gio = Gio
        self.Gtk = Gtk
        self.gui = None
        self.open_exc = None
        self.conn_name = None
        self.uri = None
        self.gtk_app = Gtk.Application(
            application_id="com.ghini.app", flags=Gio.ApplicationFlags.FLAGS_NONE
        )

        # Connect signals for lifecycle events
        self.gtk_app.connect("startup", self.on_startup)
        self.gtk_app.connect("activate", self.on_activate)

        import bauble.paths as paths
        self.paths = paths

        if self.paths.main_is_frozen():  # main is frozen
            # put library.zip first in the path when using py2exe so libxml2
            # gets imported correctly,
            zipfile = sys.path[-1]
            sys.path.insert(0, zipfile)
            # put the bundled gtk at the beginning of the path to make it the
            # preferred version
            os.environ["PATH"] = "{}{}{}{}{}{}".format(
                os.pathsep,
                os.path.join(paths.main_dir(), "gtk", "bin"),
                os.pathsep,
                os.path.join(paths.main_dir(), "gtk", "lib"),
                os.pathsep,
                os.environ["PATH"],
            )
        # make sure we look in the lib path for modules
        sys.path.append(self.paths.lib_dir())

        global default_icon
        # Ensure the default icon path exists
        default_icon = os.path.join(paths.lib_dir(), "images", "icon.png")


        if not os.path.exists(default_icon):
            logger.warning("Default icon not found at %s", default_icon)
            default_icon = "/usr/share/icons/default-icon.png"  # Fallback to a system icon

        if not os.path.exists(default_icon):  # If fallback is also missing
            logger.error("No valid default icon found! UI may not display correctly.")
            default_icon = None  # Allow UI to handle missing icons gracefully


        # Ensure user directory exists
        self.create_user_directory()

        # Handle py2exe stdout and stderr redirection
        self.setup_py2exe_logging()

    def run(self, argv):
        """Run the GTK application."""
        return self.gtk_app.run(argv)

    def on_startup(self, app) -> None:
        """Runs initialization tasks before the UI is shown."""
        import bauble.pluginmgr as pluginmgr
        from bauble.prefs import prefs
        self.setup_logging()
        prefs.init()

        # Optional: configure Sentry
        self.setup_sentry()

        self.uri, self.open_exc = self.setup_database()
        pluginmgr.load()
        from bauble.db import ensure_relationships_wired
        ensure_relationships_wired()
        prefs.save()
        from bauble.view import DefaultCommandHandler
        pluginmgr.register_command(DefaultCommandHandler)

    def on_activate(self, app) -> None:
        """Runs when the application is launched (or brought to foreground)."""
        import bauble.ui as ui
        self.gui = self.create_gui()
        self.gui.show()
        self.handle_open_errors()

    def setup_logging(self) -> None:
        """Configures application logging."""
        filename = os.path.join(self.paths.appdata_dir(), "bauble.log")
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(thread)d - %(message)s"
        )

        fileHandler = logging.FileHandler(filename, "w+")
        consoleHandler = logging.StreamHandler()

        logging.getLogger().addHandler(fileHandler)
        logging.getLogger().addHandler(consoleHandler)

        fileHandler.setFormatter(formatter)
        consoleHandler.setFormatter(formatter)

        fileHandler.setLevel(logging.INFO)
        consoleHandler.setLevel(logging.WARNING)

    def setup_sentry(self) -> None:
        """Configures Sentry for error tracking if enabled in preferences."""
        try:
            from bauble.prefs import prefs, use_sentry_client_pref
            from raven import Client
            from raven.handlers.logging import SentryHandler
            if prefs[use_sentry_client_pref]:
                import logging
                logger.debug("Registering Sentry client")
                sentry_client = Client(
                    "https://59105d22a4ad49158796088c26bf8e4c:"
                    "00268114ed47460b94ce2b1b0b2a4a20@"
                    "app.getsentry.com/45704"
                )
                handler = SentryHandler(sentry_client)
                logging.getLogger().addHandler(handler)
                handler.setLevel(logging.WARNING)
            else:
                logger.debug("Sentry client not registered")
        except Exception as e:
            import logging
            logger.warning("Failed to configure Sentry client: %s", e)

    def setup_database(self):
        """Handles database connection and returns URI and any errors."""
        import bauble.db as db
        import bauble.error as err
        import bauble.utils as utils
        from bauble.connmgr import start_connection_manager
        from bauble.gtkinit import Gtk
        from bauble.prefs import prefs

        open_exc = None

        while True:
            conn_name, uri = (
                start_connection_manager()
                if not self.uri
                else (self.conn_name, self.uri)
            )
            if conn_name is None:
                quit()

            try:
                if db.open(uri, True, True):
                    self.conn_name = conn_name
                    self.uri = uri
                    prefs["conn_default_pref"] = conn_name
                    break
                else:
                    uri = conn_name = None
            except err.VersionError as e:
                logger.warning(f"{type(e)}({e})")
                db.open(uri, False)
                break
            except (
                err.EmptyDatabaseError,
                err.MetaTableError,
                err.VersionError,
                err.TimestampError,
                err.RegistryError,
            ) as e:
                logger.info(f"{type(e)}({e})")
                open_exc = e
                try:
                    # reopen without verification so that db.Session and
                    # db.engine, db.metadata will be bound to an engine
                    db.open(uri, False)
                    self.conn_name = conn_name
                    self.uri = uri
                    break
                except Exception as inner:
                    logger.error("Fallback open(uri, False) failed: %s", inner)
                    uri = conn_name = None
            except err.DatabaseError as e:
                logger.debug(f"{type(e)}({e})")
                # traceback.format_exc()
                open_exc = e
                # break
            except Exception as e:
                msg = _("Could not open connection.\n\n%s") % e
                utils.message_details_dialog(
                    msg, traceback.format_exc(), Gtk.MessageType.ERROR
                )
            uri = None

        return uri, open_exc

    def create_gui(self):
        """Creates and returns the GUI object."""
        import bauble.ui as ui

        gui = ui.GUI()
        import bauble

        bauble.gui = gui
        gui.window.set_application(self.gtk_app)
        return gui

    def handle_open_errors(self):
        """Handles any errors encountered when opening the database."""
        import bauble
        import bauble.db as db
        import bauble.pluginmgr as pluginmgr
        import bauble.utils as utils
        from bauble.gtkinit import GLib, Gtk
        from bauble.prefs import prefs
        if self.open_exc:
            msg = _(
                "Would you like to create a new Ghini database at "
                "the current connection?\n\n<i>Warning: If there is "
                "already a database at this connection, any existing "
                "data will be destroyed!</i>"
            )
            d = utils.create_yes_no_dialog(msg, buttons=Gtk.ButtonsType.NONE)
            d.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
            d.add_button(_("Create"), 24)
            d.add_button(_("Create and Initialize"), 42)

            def enable_buttons():
                """Enables buttons after a short delay to prevent accidental clicks."""
                if d.get_property("visible"):
                    d.set_response_sensitive(24, True)
                    d.set_response_sensitive(42, True)
                return False

            GLib.timeout_add(2000, enable_buttons)

            response = d.run()
            d.destroy()
            if response in (24, 42):
                try:
                    db.create(response == 42)
                    pluginmgr.init()
                    prefs["conn_default_pref"] = self.conn_name
                except Exception as e:
                    utils.message_details_dialog(
                        _("Error creating database: %s") % e,
                        traceback.format_exc(),
                        Gtk.MessageType.ERROR,
                    )
                    logger.error("Database creation failed: %s", e)
        else:
            pluginmgr.init()

        self.gui.get_view().update()

        # Log version information
        logger.info(
            "This version installed on: %s; "
            "This version installed at: %s; "
            "Latest published version: %s; "
            "Publication date: %s",
            installation_date,
            __file__,
            release_version,
            release_date,
        )

    def create_user_directory(self) -> None:
        """Ensures user directory exists for configuration and logging."""
        user_dir = self.paths.appdata_dir()
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)
            logger.info("Created user directory: %s", user_dir)

    def setup_py2exe_logging(self) -> None:
        """Redirects stdout and stderr to files when running in py2exe mode."""
        if self.paths.main_is_frozen():
            _stdout = os.path.join(self.paths.user_dir(), "stdout.log")
            _stderr = os.path.join(self.paths.user_dir(), "stderr.log")
            sys.stdout = open(_stdout, "w")
            sys.stderr = open(_stderr, "w")
            logger.info("Redirecting stdout and stderr to logs in frozen environment")


# Define app as a global variable
app: Any = GhiniApp()  # 🔹 Now accessible globally
gtk_app: Any = app.gtk_app  # Shortcut to access Gtk.Application if needed


def main():
    """Entry point for the application."""
    return app.run(sys.argv)
