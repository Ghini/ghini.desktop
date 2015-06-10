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
#
# Description: edit and store information about the institution in the bauble
# meta
#

import os

import gtk

import bauble.editor as editor
import bauble.meta as meta
import bauble.paths as paths
import bauble.pluginmgr as pluginmgr
import bauble.utils as utils
from bauble.i18n import _


class Institution(object):
    '''
    Institution is a "live" object. When properties are changed the changes
    are immediately reflected in the database.

    Institution values are stored in the Bauble meta database and not in
    its own table
    '''
    __properties = ('inst_name', 'inst_abbreviation', 'inst_code',
                    'inst_contact', 'inst_technical_contact', 'inst_email',
                    'inst_tel', 'inst_fax', 'inst_address')

    table = meta.BaubleMeta.__table__

    def __init__(self):
        # initialize properties to None
        map(lambda p: setattr(self, p, None), self.__properties)

        for prop in self.__properties:
            prop = utils.utf8(prop)
            result = self.table.select(self.table.c.name == prop).execute()
            row = result.fetchone()
            if row:
                setattr(self, prop, row['value'])
            result.close()

    def write(self):
        for prop in self.__properties:
            value = getattr(self, prop)
            prop = utils.utf8(prop)
            value = utils.utf8(value)
            result = self.table.select(self.table.c.name == prop).\
                execute()
            row = result.fetchone()
            result.close()
            # have to check if the property exists first because sqlite doesn't
            # raise an error if you try to update a value that doesn't exist
            # and do an insert and then catching the exception if it exists
            # and then updating the value is too slow
            if not row:
                #debug('insert: %s = %s' % (prop, value))
                self.table.insert().execute(name=prop, value=value)
            else:
                #debug('update: %s = %s' % (prop, value))
                self.table.update(
                    self.table.c.name == prop).execute(value=value)


class InstitutionEditorView(editor.GenericEditorView):

    _tooltips = {'inst_name': _('The full name of the institution.'),
                 'inst_abbr': _('The standard abbreviation of the '
                                'institution.'),
                 'inst_code': _('The intitution code should be unique among '
                                'all institions.'),
                 'inst_contact': _('The name of the person to contact for '
                                   'information related to the institution.'),
                 'inst_tech': _('The email address or phone number of the '
                                'person to contact for technical '
                                'information related to the institution.'),
                 'inst_email': _('The email address of the institution.'),
                 'inst_tel': _('The telephone number of the institution.'),
                 'inst_fax': _('The fax number of the institution.'),
                 'inst_addr': _('The mailing address of the institition.')
                 }

    def __init__(self, parent=None):
        filename = os.path.join(paths.lib_dir(), 'plugins', 'garden',
                                'institution.glade')
        super(InstitutionEditorView, self).__init__(filename, parent=parent)

    def get_window(self):
        return self.widgets.inst_dialog

    def start(self):
        return self.get_window().run()


class InstitutionEditorPresenter(editor.GenericEditorPresenter):

    widget_to_field_map = {'inst_name': 'inst_name',
                           'inst_abbr': 'inst_abbreviation',
                           'inst_code': 'inst_code',
                           'inst_contact': 'inst_contact',
                           'inst_tech': 'inst_technical_contact',
                           'inst_email': 'inst_email',
                           'inst_tel': 'inst_tel',
                           'inst_fax': 'inst_fax',
                           'inst_addr': 'inst_address'
                           }

    def __init__(self, model, view):
        super(InstitutionEditorPresenter, self).__init__(model, view)
        self.refresh_view()
        for widget, field in self.widget_to_field_map.iteritems():
            self.assign_simple_handler(widget, field)
        self._dirty = False

    def set_model_attr(self, attr, value, validator):
        super(InstitutionEditorPresenter, self).set_model_attr(attr, value,
                                                               validator)
        self._dirty = True

    def dirty(self):
        return self._dirty

    def refresh_view(self):
        for widget, field in self.widget_to_field_map.iteritems():
            self.view.set_widget_value(widget, getattr(self.model, field))

    def start(self, commit_transaction=True):
        return self.view.start()


class InstitutionEditor(object):

    def __init__(self, parent=None):
        self.model = Institution()
        self.view = InstitutionEditorView(parent=parent)
        self.presenter = InstitutionEditorPresenter(self.model, self.view)

    def start(self):
        response = self.presenter.start()
        if response == gtk.RESPONSE_OK:
            self.model.write()


class InstitutionCommand(pluginmgr.CommandHandler):
    command = ('inst', 'institution')
    view = None

    def __call__(self, cmd, arg):
        InstitutionTool.start()


class InstitutionTool(pluginmgr.Tool):
    label = _('Institution')

    @classmethod
    def start(cls):
        e = InstitutionEditor()
        e.start()
