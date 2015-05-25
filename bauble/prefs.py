# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Brett Adams
# Copyright 2015 Mario Frasca <mario@anche.no>.
#
# This file is part of bauble.classic.
#
# bauble.classic is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# bauble.classic is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bauble.classic. If not, see <http://www.gnu.org/licenses/>.

import os
import gtk

import logging
logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)

import bauble
from bauble.i18n import _
import bauble.db as db
import bauble.paths as paths
import bauble.pluginmgr as pluginmgr

"""
The prefs module exposes an API for getting and setting user
preferences in the Bauble config file.

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
default_prefs_file = os.path.join(paths.user_dir(), default_filename)
"""
The default file for the preference settings file.
"""

# TODO: i don't think we use these icons anymore - issue #58
prefs_icon_dir = os.path.join(paths.lib_dir(), 'images')
general_prefs_icon = os.path.join(prefs_icon_dir, 'prefs_general.png')
security_prefs_icon = os.path.join(prefs_icon_dir, 'prefs_security.png')

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
The preferences key for the default units for Bauble.

Values: metric, imperial
"""


from ConfigParser import RawConfigParser


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
            #return self.config.get(section, option)

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

    def save(self):
        try:
            f = open(self._filename, "w+")
            self.config.write(f)
            f.close()
        except Exception:
            msg = _("Bauble can't save your user preferences. \n\nPlease "
                    "check the file permissions of your config file:\n %s"
                    % self._filename)
            if bauble.gui is not None and bauble.gui.window is not None:
                import bauble.utils as utils
                utils.message_dialog(msg, type=gtk.MESSAGE_ERROR,
                                     parent=bauble.gui.window)


# TODO: remember pane sizes

# TODO: we need to include the meta table in the pref view

class PrefsView(pluginmgr.View):
    """
    The PrefsView displays the values of in the preferences and the registry.
    """

    pane_size_pref = 'bauble.prefs.pane_position'

    def __init__(self):
        super(PrefsView, self).__init__()
        self.create_gui()

#     def create_registry_view(self):
#         pass

    def create_meta_view(self):
        pass

    def create_gui(self):
        pane = gtk.VPaned()
        self.pack_start(pane)
        pane.set_border_width(5)
        width, height = pane.size_request()

        # TODO: check-resize and move_handle are not the correct
        # signals when the pane is resized....so right now the size is
        # not getting saved in the prefs

        def on_move_handle(paned, data=None):
            print paned.get_position()
            prefs[self.pane_size_pref] = paned.get_position()
        pane.connect('check-resize', on_move_handle)

        if prefs.get(self.pane_size_pref, None) is not None:
            pane.set_position(prefs[self.pane_size_pref])
        else:
            # setting the default to half the height of the window is
            # close enough to the middle even though the top pane will
            # be a little larger
            rect = bauble.gui.window.get_allocation()
            pane.set_position(int(rect.height/2))

        label = gtk.Label()
        label.set_markup(_('<b>Preferences</b>'))
        label.set_padding(5, 0)
        frame = gtk.Frame()
        frame.set_label_widget(label)
        view = self.create_prefs_view()
        frame.add(view)
        pane.pack1(frame)

        label = gtk.Label()
        label.set_markup(_('<b>Plugins</b>'))
        label.set_padding(5, 0)
        frame = gtk.Frame()
        frame.set_label_widget(label)
        view = self.create_registry_view()
        frame.add(view)
        pane.pack2(frame)

    def create_tree(self, columns, itemsiter):
        treeview = gtk.TreeView()
        treeview.set_rules_hint(True)

        i = 0
        model_cols = []
        for c in columns:
            renderer = gtk.CellRendererText()
            column = gtk.TreeViewColumn(c, renderer, text=i)
            treeview.append_column(column)
            i += 1
            model_cols.append(str)

        model = gtk.ListStore(*model_cols)
        for item in itemsiter:
            model.append(item)
        treeview.set_model(model)

        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.add(treeview)
        return sw

    def create_prefs_view(self):
        global prefs
        tree = self.create_tree([_('Names'), _('Values')], prefs.iteritems())
        return tree

    def create_registry_view(self):
        #from bauble.pluginmgr import Registry
        from bauble.pluginmgr import PluginRegistry
        session = db.Session()
        plugins = session.query(PluginRegistry.name, PluginRegistry.version)
        tree = self.create_tree([_('Name'), _('Version')],
                                plugins)
        session.close()
        return tree


class PrefsCommandHandler(pluginmgr.CommandHandler):

    command = ('prefs', 'config')
    view = None

    def __call__(self, cmd, arg):
        pass

    def get_view(self):
        if self.view is None:
            self.view = PrefsView()
        return self.view


pluginmgr.register_command(PrefsCommandHandler)

prefs = _prefs()
