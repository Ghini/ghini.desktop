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
# pluginmgr.py
#
"""
Manage plugin registry, loading, initialization and installation.  The
plugin manager should be started in the following order:

1. load the plugins: search the plugin directory for plugins,
populates the plugins dict (happens in load())

2. install the plugins if not in the registry, add properly
installed plugins in to the registry (happens in load())

3. initialize the plugins (happens in init())
"""
import logging
import os
import re
import sys
import traceback
from gettext import gettext as _
from typing import Any, Optional

import bauble
import bauble.paths as paths
import bauble.utils as utils
import sqlalchemy.orm.exc as orm_exc
from bauble.db import Base, Session
from bauble.error import BaubleError
from bauble.gtkinit import GLib, Gtk
from sqlalchemy import Integer, Unicode, select
from sqlalchemy.orm import Mapped, mapped_column

logger: Any = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


plugins: Any = {}
commands: Any = {}
provided: Any = {}


def register_command(handler) -> None:
    """
    Register command handlers.  If a command is a duplicate then it
    will overwrite the old command of the same name.

    :param handler:  A class which extends pluginmgr.CommandHandler
    """
    logger.debug(f"registering command handler {str(handler.command)}")
    if isinstance(handler.command, str):
        if handler.command in commands:
            logger.info(f"overwriting command {handler.command}")
        commands[handler.command] = handler
    else:
        for cmd in handler.command:
            if cmd in commands:
                logger.info(f"overwriting command {cmd}")
            commands[cmd] = handler


def _create_dependency_pairs(plugs):
    """calculate plugin dependencies, met and unmet

    plugs is an iterable of plugins.

    returned value is a pair, the first item is the dependency pairs that
    can be passed to utils.topological_sort.  The second item is a
    dictionary associating plugin names (from plugs) with the list of unmet
    dependencies.

    """
    depends = []
    unmet = {}
    for p in plugs:
        for dep in p.depends:
            try:
                depends.append((plugins[dep], p))
            except KeyError:
                logger.debug(f"no dependency {dep} for {p.__name__}")
                u = unmet.setdefault(p.__name__, [])
                u.append(dep)
    return depends, unmet


def load(path: Optional[Any] = None) -> None:
    """
    Search the plugin path for modules that provide a plugin. If path
    is a directory then search the directory for plugins. If path is
    None then use the default plugins path, bauble.plugins.

    This method populates the pluginmgr.plugins dict and imports the
    plugins but doesn't do any plugin initialization.

    :param path: the path where to look for the plugins
    :type path: str
    """

    if path is None:
        if paths.main_is_frozen():
            path = os.path.join(paths.main_dir(), "library.zip")
        else:
            path = os.path.join(paths.lib_dir(), "plugins")
    logger.debug(f"pluginmgr.load({path})")
    found, errors = _find_plugins(path)
    logger.debug(f"found={found}, errors={errors}")

    # show error dialog for plugins that couldn't be loaded...we only
    # give details for the first error and assume the others are the
    # same...and if not then it doesn't really help anyways
    if errors:
        name = ", ".join(sorted(errors.keys()))
        exc_info = list(errors.values())[0]
        exc_str = utils.xml_safe(exc_info[1])
        tb_str = "".join(traceback.format_tb(exc_info[2]))
        utils.message_details_dialog(
            "Could not load plugin: " f"\n\n<i>{name}</i>\n\n{exc_str}",
            tb_str,
            type=Gtk.MessageType.ERROR,
        )

    if len(found) == 0:
        logger.debug(f"No plugins found at path: {path}")

    for plugin in found:
        # issue #27: should we include the module name of the plugin to
        # allow for plugin namespaces or just assume that the plugin class
        # name is unique?
        if isinstance(plugin, type):
            plugins[plugin.__name__] = plugin
            logger.debug(f"registering plugin {plugin.__name__}: {plugin}")
        else:
            plugins[plugin.__class__.__name__] = plugin
            logger.debug(f"registering plugin {plugin.__class__.__name__}: {plugin}")


def init(force: bool = False) -> None:
    """
    Initialize the plugin manager.

    1. Check for and install any plugins in the plugins dict that
    aren't in the registry.
    2. Call each init() for each plugin the registry in order of dependency
    3. Register the command handlers in the plugin's commands[]

    NOTE: This is called after after Ghini has created the GUI and
    established a connection to a database with db.open()

    """
    logger.debug("bauble.pluginmgr.init()")
    # ******
    # NOTE: Be careful not to keep any references to
    # PluginRegistry open here as it will cause a deadlock if you try
    # to create a new database. For example, don't query the
    # PluginRegistry with a session without closing the session.
    # ******

    # search for plugins that are in the plugins dict but not in the registry
    registered = list(plugins.values())
    logger.debug(f"registered plugins: {plugins}")
    try:
        # try to access the plugin registry, if the table does not exist
        # then it might mean that we are opening a pre 0.9 database, in this
        # case we just assume all the plugins have been installed and
        # registered, this might be the right thing to do but at least it
        # allows you to connect to a pre bauble 0.9 database and use it to
        # upgrade to a >=0.9 database
        registered_names = PluginRegistry.names()
        not_installed = [
            p for n, p in list(plugins.items()) if n not in registered_names
        ]
        if len(not_installed) > 0:
            msg = _(
                "The following plugins were not found in the plugin "
                "registry:\n\n<b>%s</b>\n\n"
                "<i>Would you like to install them now?</i>"
            ) % ", ".join([p.__class__.__name__ for p in not_installed])
            if force or utils.yes_no_dialog(msg):
                # Ensure mappers are configured
                from bauble.db import MapperBase
                from sqlalchemy.orm import configure_mappers

                print(
                    "Mapped class names seen so far:",
                    sorted(MapperBase._class_registry.keys()),
                )
                # Ensure all mappers are configured before creating tables
                import bauble.plugins.garden.models.accession as acc
                import bauble.plugins.garden.models.plant as pl
                from bauble.db import MapperBase, metadata

                print("accession in shared metadata? ", "accession" in metadata.tables)
                print(
                    "Accession uses shared metadata? ",
                    acc.Accession.__table__.metadata is metadata,
                )
                print(
                    "Plant uses shared metadata? ",
                    pl.Plant.__table__.metadata is metadata,
                )
                print(
                    "Mapped class names seen so far:",
                    sorted(MapperBase._class_registry.keys()),
                )

                import inspect as pyinspect
                import sys

                import bauble.plugins.garden.models.accession as acc
                import bauble.plugins.garden.models.plant as pl
                from bauble.db import Base

                metadata = Base.metadata

                dbmod = sys.modules[
                    __name__
                ]  # since this code is running inside bauble.db
                print("db module path:", pyinspect.getfile(dbmod), "id:", id(dbmod))
                print(
                    "Garden model modules loaded:",
                    [k for k in sys.modules if "bauble.plugins.garden.models" in k],
                )

                print("db module path:", pyinspect.getfile(dbmod), "id:", id(dbmod))
                print("Accession Base is db.Base? ", acc.Base is dbmod.Base)
                # if plant.py still uses "from bauble.db import Base", this will exist:
                print("Plant module has 'db' alias? ", hasattr(pl, "db"))
                if hasattr(pl, "db"):
                    print("pl.db is dbmod? ", pl.db is dbmod)

                print(
                    "Accession uses shared metadata? ",
                    acc.Accession.__table__.metadata is metadata,
                )
                print(
                    "Plant uses shared metadata? ",
                    pl.Plant.__table__.metadata is metadata,
                )
                print("Tables in shared metadata:", sorted(metadata.tables.keys()))
                print("accession in shared metadata? ", "accession" in metadata.tables)
                print("plant in shared metadata? ", "plant" in metadata.tables)
                configure_mappers()
                install([p for p in not_installed], import_defaults=force)

        # sort plugins in the registry by their dependencies
        not_registered = []
        for name in PluginRegistry.names():
            try:
                registered.append(plugins[name])
            except KeyError as e:
                logger.debug(f"could not find '{e}' plugin. " "removing from database")
                not_registered.append(utils.to_unicode(name))
                PluginRegistry.remove(name=name)

        if not_registered:
            msg = _(
                "The following plugins are in the registry but "
                "could not be loaded:\n\n%(plugins)s"
            ) % {"plugins": utils.to_unicode(", ".join(sorted(not_registered)))}
            utils.message_dialog(utils.xml_safe(msg), type=Gtk.MessageType.WARNING)

    except Exception as e:
        logger.warning(f"unhandled exception {e}")
        raise

    if not registered:
        # no plugins to initialize
        return

    deps, unmet = _create_dependency_pairs(registered)
    ordered = utils.topological_sort(registered, deps)
    if not ordered:
        raise BaubleError(
            _(
                "The plugins contain a dependency loop. This "
                "can happen if two plugins directly or "
                "indirectly rely on each other"
            )
        )

    # Ensure mappers are configured
    from bauble.db import MapperBase
    from sqlalchemy.orm import configure_mappers

    print("Mapped class names seen so far:", sorted(MapperBase._class_registry.keys()))
    configure_mappers()

    # call init() for each ofthe plugins
    for plugin in ordered:
        logger.debug(f"about to invoke init on: {plugin}")
        try:
            plugin.init()
            logger.debug(f"plugin {plugin} initialized")
        except KeyError:
            # keep the plugin in the registry so if we find it again we do
            # not offer the user the option to reinstall it, something which
            # could overwrite data
            ordered.remove(plugin)
            msg = _(
                "The %(plugin_name)s plugin is listed in the registry "
                "but isn't wasn't found in the plugin directory"
            ) % dict(plugin_name=plugin.__class__.__name__)
            logger.warning(msg)
        except Exception as e:
            logger.error(f"{type(e)}: {e}")
            ordered.remove(plugin)
            logger.debug(traceback.print_exc())
            safe = utils.xml_safe
            values = dict(entry_name=plugin.__class__.__name__, exception=safe(e))
            utils.message_details_dialog(
                _("Error: Couldn't initialize %(entry_name)s\n\n" "%(exception)s.")
                % values,
                traceback.format_exc(),
                Gtk.MessageType.ERROR,
            )

    # register the plugin commands separately from the plugin initialization
    for plugin in ordered:
        if plugin.commands in (None, []):
            continue
        for cmd in plugin.commands:
            try:
                register_command(cmd)
            except Exception as e:
                logger.debug(f"exception {e} while registering command {cmd}")
                msg = f"Error: Could not register command handler.\n\n{utils.xml_safe(str(e))}"
                utils.message_dialog(msg, Gtk.MessageType.ERROR)

    # don't build the tools menu if we're running from the tests and
    # we don't have a gui
    if type(bauble.gui).__name__ == "GUI":
        bauble.gui.build_tools_menu()


def install(
    plugins_to_install, import_defaults: bool = True, force: bool = False
) -> None:
    """
    :param plugins_to_install: A list of plugins to install. If the
        string "all" is passed then install all plugins listed in the
        bauble.pluginmgr.plugins dict that aren't already listed in
        the plugin registry.

    :param import_defaults: Flag passed to the plugin's install()
        method to indicate whether it should import its default data.
    :type import_defaults: bool

    :param force:  Force, don't ask questions.
    :type force: book
    """
    # pluginmgr.py - top of `install()` or right before the install loop
    from bauble.db import MapperBase
    from sqlalchemy.orm import configure_mappers

    print("Mapped class names seen so far:", sorted(MapperBase._class_registry.keys()))
    configure_mappers()

    logger.debug(f"pluginmgr.install({str(plugins_to_install)})")
    if plugins_to_install == "all":
        to_install = list(plugins.values())
    else:
        to_install = plugins_to_install

    if len(to_install) == 0:
        # no plugins to install
        return

    # sort the plugins by their dependency
    depends, unmet = _create_dependency_pairs(list(plugins.values()))
    logger.debug(f"{str(depends)} - the dependencies pairs")
    if unmet != {}:
        logger.debug(unmet)
        raise BaubleError("unmet dependencies")
    to_install = utils.topological_sort(to_install, depends)
    logger.debug(f"{str(to_install)} - this is after topological sort")
    if not to_install:
        raise BaubleError(
            _(
                "The plugins contain a dependency loop. This "
                "means that two plugins "
                "(possibly indirectly) rely on each other"
            )
        )

    try:
        for p in to_install:
            logger.debug(f"install: {p}")
            p.install(import_defaults=import_defaults)
            # issue #28: here we make sure we don't add the plugin to the
            # registry twice but we should really update the version number
            # in the future when we accept versioned plugins (if ever)
            if not PluginRegistry.exists(p):
                logger.debug(f"{p} - adding to registry")
                PluginRegistry.add(p)
    except Exception as e:
        logger.warning(f"bauble.pluginmgr.install(): {utils.to_unicode(e)}")
        logger.debug(traceback.print_exc())
        raise


class PluginRegistry(Base):
    """
    The PluginRegistry contains a list of plugins that have been installed
    in a particular instance of a Ghini database.  At the moment it only
    includes the name and version of the plugin but this is likely to change
    in future versions.
    """

    __tablename__: str = "plugin"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Unicode(64), unique=True)
    version: Mapped[str] = mapped_column(Unicode(12))

    @staticmethod
    def add(plugin) -> None:
        """
        Add a plugin to the registry.

        Warning: Adding a plugin to the registry does not install it.  It
        should be installed before adding.
        """

        p = PluginRegistry(
            name=plugin.__class__.__name__,
            version=plugin.version,
        )
        with Session() as session:
            session.add(p)
            if session.in_transaction():
                session.commit()

    @staticmethod
    def remove(plugin: Optional[Any] = None, name: Optional[Any] = None) -> None:
        """
        Remove a plugin from the registry by name.
        """
        # debug('PluginRegistry.remove()')
        if name is None:
            if plugin is None:
                raise ValueError("Either 'plugin' or 'name' must be provided.")
            name = plugin.__class__.__name__

        # Decode name if it's in bytes
        decoded_name = name.decode() if isinstance(name, bytes) else name

        with Session() as session:
            stmt = PluginRegistry.query_with_default_order().where(PluginRegistry.name == decoded_name)
            p = session.execute(stmt).scalar_one_or_none()
            if p:
                session.delete(p)
                if session.in_transaction():
                    session.commit()

    @staticmethod
    def all(session=None) -> list[str]:
        with Session() as local_session:
            session = session or local_session
            stmt = PluginRegistry.query_with_default_order()
            return session.scalars(stmt).all()

    @staticmethod
    def names() -> list[str]:
        t = PluginRegistry.__table__
        stmt = select(t.c.name)
        with Session() as session:
            return session.execute(stmt).scalars().all()

    @staticmethod
    def exists(plugin):
        """
        Check if plugin exists in the plugin registry.
        """

        if isinstance(plugin, str):
            name = plugin
            version = None
        else:
            name = plugin.__class__.__name__
            version = plugin.version

        # Decode name if it's in bytes
        name.decode() if isinstance(name, bytes) else name

        with Session() as session:
            try:
                logger.debug(f"not using value of version ({version}).")
                # Apply the where clause to the select object
                stmt = PluginRegistry.query_with_default_order().where(PluginRegistry.name == name)
                session.execute(stmt).scalar_one()
                return True
            except orm_exc.NoResultFound as e:
                logger.debug(e)
                return False


class Plugin:
    """
    commands:
      a map of commands this plugin handled with callbacks,
      e.g dict('cmd', lambda x: handler)
    tools:
      a list of BaubleTool classes that this plugin provides, the
      tools' category and label will be used in Ghini's "Tool" menu
    depends:
      a list of names classes that inherit from BaublePlugin that this
      plugin depends on
    provides:
      a dictionary name->class exported by this plugin
    description:
      a short description of the plugin
    """

    commands: Any = []
    tools: Any = []
    depends: Any = []
    provides: Any = {}
    description: str = ""
    version: str = "0.0"

    @classmethod
    def __init__(cls) -> None:
        pass

    @classmethod
    def init(cls) -> None:
        """
        init() is run when Ghini is first started
        """

    @classmethod
    def install(cls, import_defaults: bool = True) -> None:
        """
        install() is run when a new plugin is installed, it is usually
        only run once for the lifetime of the plugin
        """


class EditorPlugin(Plugin):
    """
    a plugin that provides one or more editors, the editors should
    implement the Editor interface
    """

    editors: Any = []


class Tool:
    category: Any = None
    label: Any = None
    enabled: bool = True
    icon_dir: Any = None

    @classmethod
    def start(cls) -> None:
        pass


class View(Gtk.Box):
    """
    A generic view class that uses Gtk.VBox for layout and supports threading for async tasks.
    It is designed to be extended with custom UI logic and widgets.

    If a class extends this View and provides its own __init__ it *must* call its parent (this) __init__.
    """

    widgets: Any
    view: Any
    running_threads: Any

    def __init__(self, *args, **kwargs) -> None:
        """
        Initializes the view, optionally loading a UI from a .glade file.

        :param filename: Path to the .glade file (optional).
        :param root_widget_name: The root widget's name in the .glade file (optional).
        """
        filename = kwargs.get("filename")
        if filename is not None:
            del kwargs["filename"]
            root_widget_name = kwargs.get("root_widget_name")
            del kwargs["root_widget_name"]

        # Initialize Gtk.Box with the parent constructor
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        if filename is not None:
            from bauble import editor, utils

            self.widgets = utils.BuilderWidgets(filename)
            self.view = editor.GenericEditorView(
                filename, root_widget_name=root_widget_name
            )
            root_widget = getattr(self.view.widgets, root_widget_name)
            widget = root_widget.get_children()[0]
            self.view.widgets.remove_parent(widget)
            self.pack_start(widget, True, True, 0)

        self.running_threads = []

    def cancel_threads(self) -> None:
        """Cancel and join all running threads."""
        for k in self.running_threads:
            k.cancel()
        for k in self.running_threads:
            k.join()
        self.running_threads = []

    def start_thread(self, thread):
        """Start a new thread and add it to the list of running threads."""
        self.running_threads.append(thread)
        thread.start()
        return thread

    def idle_start_thread(self, cls, *args, **kwargs) -> None:
        """Start a thread after the main loop yields control."""

        def create_and_start(cls, args, kwargs):
            thread = cls(*args, **kwargs)
            self.running_threads.append(thread)
            thread.start()

        GLib.idle_add(create_and_start, cls, args, kwargs)

    def update(self) -> None:
        """Override this method in a subclass to update the view."""
        pass

    def get_widget(self):
        """Returns the main widget (Gtk.Box) containing the view's UI."""
        return self

    def add(self, widget) -> None:
        """Add a widget to the vbox container."""
        self.pack_start(widget, True, True, 0)


class CommandHandler:

    command: Any = None

    def get_view(self) -> None:
        """
        return the  view for this command handler
        """
        return None

    def __call__(self, cmd, arg) -> None:
        """
        do what this command handler does

        :param arg:
        """
        raise NotImplementedError


def _find_module_names(path):
    """
    :param path: where to look for modules
    """
    modules = []
    if path.find("library.zip") != -1:  # using py2exe
        from zipfile import ZipFile

        z = ZipFile(path)
        filenames = z.namelist()
        rx = re.compile("(.+)\\__init__.py[oc]")
        for f in filenames:
            m = rx.match(f)
            if m is not None:
                modules.append(m.group(1).replace("/", ".")[:-1])
        z.close()
    else:
        for dir, _subdir, files in os.walk(path):
            if dir != path and "__init__.py" in files:
                modules.append(dir[len(path) + 1 :].replace(os.sep, "."))
    return modules


def _find_plugins(path):
    """
    Return the plugins at path.
    """
    plugins = []
    import bauble.plugins

    bauble.plugins
    errors = {}

    if path.find("library.zip") != -1:
        plugin_names = [
            m for m in _find_module_names(path) if m.startswith("bauble.plugins")
        ]
    else:
        plugin_names = [f"bauble.plugins.{m}" for m in _find_module_names(path)]

    import importlib

    import bauble.plugins

    for name in plugin_names:
        mod = None
        # Fast path: see if the module has already been imported.

        if name in sys.modules:
            mod = sys.modules[name]
        else:
            try:
                print("DEBUG: bauble =", bauble)
                print("DEBUG: type(bauble) =", type(bauble))
                mod = importlib.import_module(name, package="bauble.plugins")
            except Exception as e:
                msg = _("Could not import the %(module)s module.\n\n" "%(error)s") % {
                    "module": name,
                    "error": e,
                }
                logger.debug(msg)
                errors[name] = sys.exc_info()
        if not hasattr(mod, "plugin"):
            continue

        # if mod.plugin is a function it should return a plugin or list of
        # plugins
        try:
            mod_plugin = mod.plugin()
            logger.debug(f"module {mod} contains callable plugin: {mod_plugin}")
        except:
            mod_plugin = mod.plugin
            logger.debug(f"module {mod} contains non callable plugin: {mod_plugin}")

        def is_plugin_class(p):
            return isinstance(p, type) and issubclass(p, Plugin)

        def is_plugin_instance(p):
            return isinstance(p, Plugin)

        if isinstance(mod_plugin, (list, tuple)):
            for p in mod_plugin:
                if is_plugin_class(p):
                    logger.debug(f"append plugin class {name}:{p}")
                    plugins.append(p())
                elif is_plugin_instance(p):
                    logger.debug(f"append plugin instance {name}:{p}")
                    plugins.append(p)
        elif is_plugin_class(mod_plugin):
            logger.debug(f"append plugin class {name}:{mod_plugin}")
            plugins.append(mod_plugin())
        elif is_plugin_instance(mod_plugin):
            logger.debug(f"append plugin instance {name}:{mod_plugin}")
            plugins.append(mod_plugin)
        else:
            logger.warning(
                _("%s.plugin is not an instance of pluginmgr.Plugin") % mod.__name__
            )
    return plugins, errors
