# -*- coding: utf-8 -*-
#
# Copyright (c) 2005,2006,2007,2008,2009 Brett Adams <brett@belizebotanic.org>
# Copyright (c) 2012-2015 Mario Frasca <mario@anche.no>
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
# test_bauble.py
#

import os

from bauble.editor import GenericEditorView
import bauble.prefs as prefs
import bauble.paths as paths
import bauble.utils as utils

from bauble.test import BaubleTestCase


class BaubleTests(BaubleTestCase):

    def test_create_generic_view(self):
        filename = os.path.join(paths.lib_dir(), 'bauble.glade')
        view = GenericEditorView(filename)
        print type(view.widgets)
        self.assertTrue(type(view.widgets) is utils.BuilderWidgets)

    def test_set_title_ok(self):
        filename = os.path.join(paths.lib_dir(), 'bauble.glade')
        view = GenericEditorView(filename, root_widget_name='main_window')
        title = 'testing'
        view.set_title(title)
        self.assertEquals(view.get_window().get_title(), title)

    def test_set_title_no_root(self):
        filename = os.path.join(paths.lib_dir(), 'bauble.glade')
        view = GenericEditorView(filename)
        title = 'testing'
        self.assertRaises(NotImplementedError, view.set_title, title)
        self.assertRaises(NotImplementedError, view.get_window)

    def test_set_icon_no_root(self):
        filename = os.path.join(paths.lib_dir(), 'bauble.glade')
        view = GenericEditorView(filename)
        title = 'testing'
        self.assertRaises(NotImplementedError, view.set_icon, title)

    def test_add_widget(self):
        import gtk
        filename = os.path.join(paths.lib_dir(), 'bauble.glade')
        view = GenericEditorView(filename)
        label = gtk.Label('testing')
        view.widget_add('statusbar', label)


class PleaseIgnoreMe:
    '''these cannot be tested in a non-windowed environment
    '''

    def test_set_accept_buttons_sensitive_not_set(self):
        'it is a task of the presenter to indicate the accept buttons'
        filename = os.path.join(paths.lib_dir(), 'connmgr.glade')
        view = GenericEditorView(filename, root_widget_name='main_dialog')
        self.assertRaises(AttributeError,
                          view.set_accept_buttons_sensitive, True)

    def test_set_sensitive(self):
        filename = os.path.join(paths.lib_dir(), 'connmgr.glade')
        view = GenericEditorView(filename, root_widget_name='main_dialog')
        view.widget_set_sensitive('cancel_button', True)
        self.assertTrue(view.widgets.cancel_button.get_sensitive())
        view.widget_set_sensitive('cancel_button', False)
        self.assertFalse(view.widgets.cancel_button.get_sensitive())

    def test_set_visible_get_visible(self):
        filename = os.path.join(paths.lib_dir(), 'connmgr.glade')
        view = GenericEditorView(filename, root_widget_name='main_dialog')
        view.widget_set_visible('noconnectionlabel', True)
        self.assertTrue(view.widget_get_visible('noconnectionlabel'))
        self.assertTrue(view.widgets.noconnectionlabel.get_visible())
        view.widget_set_visible('noconnectionlabel', False)
        self.assertFalse(view.widget_get_visible('noconnectionlabel'))
        self.assertFalse(view.widgets.noconnectionlabel.get_visible())
