#
# Copyright 2008-2010 Brett Adams
# Copyright 2015 Mario Frasca <mario@anche.no>.
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
import logging
import os
from configparser import RawConfigParser
from gettext import gettext as _
from typing import Any, Optional

import bauble.db as db
import bauble.paths as paths
import bauble.pluginmgr as pluginmgr
from bauble._version import version as _bauble_version
from bauble._version import version_tuple as _bauble_version_tuple

default_filename: str
import copy

from bauble.gtkinit import Gtk
from sqlalchemy import select

logger: Any = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


testing: bool = False  # set this to True when testing

"""
The prefs module exposes an API for getting and setting user
preferences in the Ghini config file.

To use the preferences import bauble.prefs and access the prefs object
using a dictionary like interface. e.g. ::

    import bauble.prefs
    prefs.prefs[key] = value
"""

# TODO: maybe we should have a create method that creates the preferences
# todo a one time thing if the files doesn't exist

# TODO: Consider using ConfigObj since it does validation, type
# conversion and unicode automatically...the cons are that it adds
# another dependency and we would have to change the prefs interface
# throughout bauble

default_filename = "config"
default_prefs_file: Any = os.path.join(paths.appdata_dir(), default_filename)
"""
The default file for the preference settings file.
"""

config_version_pref: str = "bauble.config.version"
"""
The preferences key for the bauble version of the preferences file.
"""
config_version: Any = (_bauble_version_tuple[0], _bauble_version_tuple[1])

date_format_pref: str = "bauble.default_date_format"
"""
The preferences key for the default data format.
"""

picture_root_pref: str = "bauble.picture_root"
"""
The preferences key for the default data format.
"""

ask_timeout_pref: str = "bauble.network_timeout"
"""
The preferences key for remote server querying timeout.
"""

parse_dayfirst_pref: str = "bauble.parse_dayfirst"
"""
The preferences key for to determine whether the date should come
first when parsing date string.  For more information see the
:meth:`dateutil.parser.parse` method.

Values: True, False
"""

parse_yearfirst_pref: str = "bauble.parse_yearfirst"
"""
The preferences key for to determine whether the date should come
first when parsing date string.  For more information see the
:meth:`dateutil.parser.parse` method.

Values: True, False
"""

units_pref: str = "bauble.units"
"""
The preferences key for the default units for Ghini.

Values: metric, imperial
"""

use_sentry_client_pref: str = "bauble.use_sentry_client"
"""
During normal usage, Ghini produces a log file which contains
invaluable information for tracking down errors. This information is
normally saved in a file on the local workstation.

This preference key controls the option of sending exceptional
conditions (WARNING and ERROR, normally related to software problems)
to a central logging server, and developers will be notified by email
of the fact that you encountered a problem.

Logging messages at the levels Warning and Error do not contain personal
information. If you have completed the registration steps, a developer
might contact you to ask for further details, as it could be the
complete content of your log file.

Values: True, False (Default: False)
"""
testing_pref: str = "bauble.testing"


class _prefs(dict):

    _filename: Any
    config: Any

    def __init__(self, filename=default_prefs_file) -> None:
        self._filename = filename
        self.config = None

        # Populate attributes for module-level _pref constants
        for name, value in globals().items():
            if name.endswith("_pref") and isinstance(value, str):
                if name == "date_format_pref":
                    print(f"Date_format_pref = {date_format_pref}")
                setattr(self, name, value)

    def __getattr__(self, name):
        """Allow attributes to refer to module-level constants (keys)."""
        if name in globals():
            return globals()[name]
        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{name}'"
        )

    def __deepcopy__(self, memo):
        """
        Custom deepcopy implementation for `_prefs`.
        Ensures `config` and `_filename` are appropriately handled.
        """
        # Create a new instance of `_prefs`
        new_prefs = _prefs(self._filename)

        # Copy additional attributes
        new_prefs._filename = copy.deepcopy(self._filename, memo)
        new_prefs.config = copy.deepcopy(self.config, memo) if self.config else None

        # Deepcopy the dictionary items
        for key, value in self.items():
            new_prefs[key] = copy.deepcopy(value, memo)

        return new_prefs

    def _strip_prefix(self, key: str) -> str:
        """
        Strip the 'bauble.' prefix from a key if present.
        """
        if key.startswith("bauble."):
            return key[len("bauble.") :]
        return key

    @property
    def prefs(self):
        # Mimic the old behavior by returning self
        return self

    def __setattr__(self, name, value) -> None:
        """
        Allow setting keys as attributes, e.g., prefs.parse_dayfirst_pref = value.
        """
        if name in ["_filename", "config"]:
            super().__setattr__(name, value)
        else:
            key = f"bauble.{name}"
            super().__setitem__(key, value)

    def init(self, prefs: Optional[Any] = None) -> None:
        """
        initialize the preferences, should only be called from app.main
        """
        # create directory tree of filename if it doesn't yet exist
        head, tail = os.path.split(self._filename)
        if not os.path.exists(head):
            os.makedirs(head)

        # also make sure the templates and resources directories exists
        if not os.path.exists(os.path.join(head, "res", "templates")):
            os.makedirs(os.path.join(head, "res", "templates"))

        self.config = RawConfigParser()

        # set the version if the file doesn't exist
        if not os.path.exists(self._filename):
            self[config_version_pref] = config_version
        else:
            self.config.read(self._filename)
        version = self[config_version_pref]
        if version is None:
            logger.warning(f"{self._filename} has no config version pref")
            logger.warning(
                "setting the config version to {}.{}".format(*config_version)
            )
            self[config_version_pref] = config_version

        # set some defaults if they don't exist
        self.setdefault(use_sentry_client_pref, False)
        self.setdefault(picture_root_pref, "")
        self.setdefault(date_format_pref, "%d-%m-%Y")
        self.setdefault(units_pref, "metric")
        self.setdefault(ask_timeout_pref, 4)
        self.setdefault(testing_pref, False)
        if parse_dayfirst_pref not in self:
            format = self[date_format_pref]
            if format.find("%d") < format.find("%m"):
                self[parse_dayfirst_pref] = True
            else:
                self[parse_dayfirst_pref] = False
        if parse_yearfirst_pref not in self:
            format = self[date_format_pref]
            if format.find("%Y") == 0 or format.find("%y") == 0:
                self[parse_yearfirst_pref] = True
            else:
                self[parse_yearfirst_pref] = False

    @staticmethod
    def _parse_key(name: str) -> tuple[str, str]:
        index = name.rfind(".")
        return name[:index], name[index + 1 :]

    def get(self, key: str, default: Optional[Any]) -> Optional[Any]:
        """
        get value for key else return default
        """
        value = self[key]
        if value is None:
            return default
        return value

    def __getitem__(self, key):
        section, option = _prefs._parse_key(key)
        key = self._strip_prefix(key)
        # this doesn't allow None values for preferences
        if not self.config.has_section(section) or not self.config.has_option(
            section, option
        ):
            return None
        else:
            i = self.config.get(section, option)
            eval_chars = "{[("
            if i == "":
                return i
            elif i[0] in eval_chars:  # then the value is a dict, list or tuple
                return eval(i)
            elif i == "True" or i == "False":
                return eval(i)
            return i

    def items(self):
        return [
            (f"{section}.{name}", value)
            for section in sorted(prefs.config.sections())
            for name, value in prefs.config.items(section)
        ]

    def setdefault(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        if key not in self:
            self.__setitem__(key, default)
        return self[key]

    def __setitem__(self, key, value) -> None:
        section, option = _prefs._parse_key(key)
        key = self._strip_prefix(key)
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, option, str(value))

    def __contains__(self, key) -> bool:
        section, option = _prefs._parse_key(key)
        key = self._strip_prefix(key)
        if self.config.has_section(section) and self.config.has_option(section, option):
            return True
        return False

    def save(self, force: bool = False) -> None:
        if testing and not force:
            return
        try:
            f = open(self._filename, "w+")
            self.config.write(f)
            f.close()
        except Exception:
            msg = (
                _(
                    "Ghini can't save your user preferences. \n\nPlease "
                    "check the file permissions of your config file:\n %s"
                )
                % self._filename
            )
            if bauble.gui is not None and bauble.gui.window is not None:
                import bauble.utils as utils

                utils.message_dialog(
                    msg, type=Gtk.MessageType.ERROR, parent=bauble.gui.window
                )
            else:
                logger.error(msg)


prefs: Any = _prefs()


class PrefsView(pluginmgr.View):
    """
    The PrefsView displays the values of in the preferences and the registry.
    """

    prefs_ls: Any
    plugins_ls: Any
    pane_size_pref: str = "bauble.prefs.pane_position"

    def __init__(self) -> None:
        logger.debug("PrefsView::__init__")
        super().__init__(
            filename=os.path.join(paths.lib_dir(), "bauble.glade"),
            root_widget_name="prefs_window",
        )
        self.view.connect_signals(self)
        self.prefs_ls = self.view.widgets.prefs_prefs_ls
        self.plugins_ls = self.view.widgets.prefs_plugins_ls
        self.update()

    def on_prefs_prefs_tv_row_activated(self, tv, path, column) -> None:
        key, repr_str, type_str = self.prefs_ls[path]
        if type_str == "bool":
            prefs[key] = not prefs[key]
            self.prefs_ls[path][1] = str(prefs[key])
            prefs.save()

    def update(self) -> None:
        self.prefs_ls.clear()
        for key, value in sorted(prefs.items()):
            self.prefs_ls.append((key, value, prefs[key].__class__.__name__))

        self.plugins_ls.clear()
        from bauble.pluginmgr import PluginRegistry

        with db.Session() as session:
            stmt = PluginRegistry.query_with_default_order()
            plugins = session.scalars(stmt).all()

        for plugin in plugins:
            name, version = plugin
            self.plugins_ls.append((name, version))
        session.close()


class PrefsCommandHandler(pluginmgr.CommandHandler):

    command: Any = ("prefs", "config")
    view: Any = None

    def __call__(self, cmd, arg) -> None:
        pass

    def get_view(self):
        if self.view is None:
            self.__class__.view = PrefsView()
        return self.view


pluginmgr.register_command(PrefsCommandHandler)

# prefs = _prefs()
