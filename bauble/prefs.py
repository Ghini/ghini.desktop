# -*- coding: utf-8 -*-
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

import os
from gi.repository import Gtk

import logging
logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)

import bauble

import bauble.db as db
import bauble.paths as paths
import bauble.pluginmgr as pluginmgr

testing = False  # set this to True when testing

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

default_filename = 'config'
default_prefs_file = os.path.join(paths.appdata_dir(), default_filename)
"""
The default file for the preference settings file.
"""

config_version_pref = 'bauble.config.version'
"""
The preferences key for the bauble version of the preferences file.
"""

config_version = bauble.version_tuple[0], bauble.version_tuple[1]

date_format_pref = 'bauble.default_date_format'
"""
The preferences key for the default data format.
"""

picture_root_pref = 'bauble.picture_root'
"""
The preferences key for the default data format.
"""

parse_dayfirst_pref = 'bauble.parse_dayfirst'
"""
The preferences key for to determine whether the date should come
first when parsing date string.  For more information see the
:meth:`dateutil.parser.parse` method.

Values: True, False
"""

parse_yearfirst_pref = 'bauble.parse_yearfirst'
"""
The preferences key for to determine whether the date should come
first when parsing date string.  For more information see the
:meth:`dateutil.parser.parse` method.

Values: True, False
"""

units_pref = 'bauble.units'
"""
The preferences key for the default units for Ghini.

Values: metric, imperial
"""

use_sentry_client_pref = 'bauble.use_sentry_client'
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


from configparser import RawConfigParser


class _prefs(dict):

    def __init__(self, filename=default_prefs_file):
        self._filename = filename

    def init(self):
        '''
        initialize the preferences, should only be called from app.main
        '''
        # create directory tree of filename if it doesn't yet exist
        head, tail = os.path.split(self._filename)
        if not os.path.exists(head):
            os.makedirs(head)

        self.config = RawConfigParser()

        # set the version if the file doesn't exist
        if not os.path.exists(self._filename):
            self[config_version_pref] = config_version
        else:
            self.config.read(self._filename)
        version = self[config_version_pref]
        if version is None:
            logger.warning('%s has no config version pref' % self._filename)
            logger.warning('setting the config version to %s.%s'
                           % (config_version))
            self[config_version_pref] = config_version

        # set some defaults if they don't exist
        if use_sentry_client_pref not in self:
            self[use_sentry_client_pref] = False
        if picture_root_pref not in self:
            self[picture_root_pref] = ''
        if date_format_pref not in self:
            self[date_format_pref] = '%d-%m-%Y'
        if parse_dayfirst_pref not in self:
            format = self[date_format_pref]
            if format.find('%d') < format.find('%m'):
                self[parse_dayfirst_pref] = True
            else:
                self[parse_dayfirst_pref] = False
        if parse_yearfirst_pref not in self:
            format = self[date_format_pref]
            if format.find('%Y') == 0 or format.find('%y') == 0:
                self[parse_yearfirst_pref] = True
            else:
                self[parse_yearfirst_pref] = False

        if units_pref not in self:
            self[units_pref] = 'metric'

    @staticmethod
    def _parse_key(name):
        index = name.rfind(".")
        return name[:index], name[index+1:]

    def get(self, key, default):
        '''
        get value for key else return default
        '''
        value = self[key]
        if value is None:
            return default
        return value

    def __getitem__(self, key):
        section, option = _prefs._parse_key(key)
        # this doesn't allow None values for preferences
        if not self.config.has_section(section) or \
                not self.config.has_option(section, option):
            return None
        else:
            i = self.config.get(section, option)
            eval_chars = '{[('
            if i == '':
                return i
            elif i[0] in eval_chars:  # then the value is a dict, list or tuple
                return eval(i)
            elif i == 'True' or i == 'False':
                return eval(i)
            return i

    def iteritems(self):
        return [('%s.%s' % (section, name), value)
                for section in sorted(prefs.config.sections())
                for name, value in prefs.config.items(section)]

    def __setitem__(self, key, value):
        section, option = _prefs._parse_key(key)
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, option, str(value))

    def __contains__(self, key):
        section, option = _prefs._parse_key(key)
        if self.config.has_section(section) and \
           self.config.has_option(section, option):
            return True
        return False

    def save(self, force=False):
        if testing and not force:
            return
        try:
            f = open(self._filename, "w+")
            self.config.write(f)
            f.close()
        except Exception:
            msg = _("Ghini can't save your user preferences. \n\nPlease "
                    "check the file permissions of your config file:\n %s") \
                % self._filename
            if bauble.gui is not None and bauble.gui.window is not None:
                import bauble.utils as utils
                utils.message_dialog(msg, type=Gtk.MessageType.ERROR,
                                     parent=bauble.gui.window)
            else:
                logger.error(msg)


class PrefsView(pluginmgr.View):
    """
    The PrefsView displays the values of in the preferences and the registry.
    """

    pane_size_pref = 'bauble.prefs.pane_position'

    def __init__(self):
        logger.debug('PrefsView::__init__')
        super().__init__(
            filename=os.path.join(paths.lib_dir(), 'bauble.glade'),
            root_widget_name='prefs_window')
        self.view.connect_signals(self)
        self.prefs_ls = self.view.widgets.prefs_prefs_ls
        self.plugins_ls = self.view.widgets.prefs_plugins_ls
        self.update()

    def on_prefs_prefs_tv_row_activated(self, tv, path, column):
        global prefs
        modified = False
        key, repr_str, type_str = self.prefs_ls[path]
        if type_str == 'bool':
            self.prefs_ls[path][1] = prefs[key] = not prefs[key]
            modified = True
        if modified:
            prefs.save()

    def update(self):
        self.widgets.prefs_prefs_ls.clear()
        global prefs
        for key, value in sorted(prefs.items()):
            self.widgets.prefs_prefs_ls.append(
                (key, value, prefs[key].__class__.__name__))

        self.widgets.prefs_plugins_ls.clear()
        from bauble.pluginmgr import PluginRegistry
        session = db.Session()
        plugins = session.query(PluginRegistry.name, PluginRegistry.version)
        for item in plugins:
            self.widgets.prefs_plugins_ls.append(item)
        session.close()
        pass


class PrefsCommandHandler(pluginmgr.CommandHandler):

    command = ('prefs', 'config')
    view = None

    def __call__(self, cmd, arg):
        pass

    def get_view(self):
        if self.view is None:
            self.__class__.view = PrefsView()
        return self.view


pluginmgr.register_command(PrefsCommandHandler)

prefs = _prefs()
