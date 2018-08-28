# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Brett Adams
# Copyright 2012-2017 Mario Frasca <mario@anche.no>.
# Copyright 2017 Jardín Botánico de Quito
# Copyright 2017 Ross Demuth
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
# __init__.py
#
# Description : report plugin
#
import os
import traceback

import logging
logger = logging.getLogger(__name__)

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import GObject

from sqlalchemy import union

import bauble

from bauble.error import BaubleError
import bauble.utils as utils
import bauble.paths as paths
from bauble.prefs import prefs
import bauble.pluginmgr as pluginmgr
from bauble.plugins.plants import Family, Genus, Species, VernacularName
from bauble.plugins.garden import Accession, Plant, Location, Source, Contact
from bauble.plugins.tag import Tag

from bauble.editor import (
    GenericEditorView, GenericEditorPresenter)

from .flat_export import FlatFileExportTool

# name: formatter_class, formatter_kwargs
config_list_pref = 'report.configs'

# the default report generator to select on start
default_config_pref = 'report.xsl'
formatter_settings_expanded_pref = 'report.settings.expanded'

# to be populated by the dialog box, with fields mentioned in the template
options = {}


def _get_pertinent_objects(cls, get_query_func, objs, session):
    """
    :param cls:
    :param get_query_func:
    :param objs:
    :param session:
    """
    if session is None:
        import bauble.db as db
        session = db.Session()
    if not isinstance(objs, (tuple, list)):
        objs = [objs]
    queries = [get_query_func(o, session) for o in objs]
    # TODO: what is the problem with the following form?
    # results = session.query(cls).order_by(None).union(*queries)
    unions = union(*[q.statement for q in queries])
    results = session.query(cls).from_statement(unions)
    return results


def get_plant_query(obj, session):
    """
    """
    # as of sqlalchemy 0.5.0 we have to have the order_by(None) here
    # so that if we want to union() the statements together later it
    # will work properly
    q = session.query(Plant).order_by(None)
    if isinstance(obj, Family):
        return q.join('accession', 'species', 'genus', 'family').\
            filter_by(id=obj.id)
    elif isinstance(obj, Genus):
        return q.join('accession', 'species', 'genus').filter_by(id=obj.id)
    elif isinstance(obj, Species):
        return q.join('accession', 'species').filter_by(id=obj.id)
    elif isinstance(obj, VernacularName):
        return q.join('accession', 'species', 'vernacular_names').\
            filter_by(id=obj.id)
    elif isinstance(obj, Plant):
        return q.filter_by(id=obj.id)
    elif isinstance(obj, Accession):
        return q.join('accession').filter_by(id=obj.id)
    elif isinstance(obj, Location):
        return q.filter_by(location_id=obj.id)
    elif isinstance(obj, Contact):
        return q.join('accession', 'source', 'source_detail').\
                filter_by(id=obj.id)
    elif isinstance(obj, Tag):
        plants = get_plants_pertinent_to(obj.objects, session)
        return q.filter(Plant.id.in_([p.id for p in plants]))
    else:
        raise BaubleError(_("Can't get plants from a %s") % type(obj).__name__)


def get_plants_pertinent_to(objs, session=None):
    """
    :param objs: an instance of a mapped object
    :param session: the session to use for the queries

    Return all the plants found in objs.
    """
    return _get_pertinent_objects(Plant, get_plant_query, objs, session)


def get_accession_query(obj, session):
    """
    """
    q = session.query(Accession).order_by(None)
    if isinstance(obj, Family):
        return q.join('species', 'genus', 'family').\
            filter_by(id=obj.id)
    elif isinstance(obj, Genus):
        return q.join('species', 'genus').filter_by(id=obj.id)
    elif isinstance(obj, Species):
        return q.join('species').filter_by(id=obj.id)
    elif isinstance(obj, VernacularName):
        return q.join('species', 'vernacular_names').\
            filter_by(id=obj.id)
    elif isinstance(obj, Plant):
        return q.join('plants').filter_by(id=obj.id)
    elif isinstance(obj, Accession):
        return q.filter_by(id=obj.id)
    elif isinstance(obj, Location):
        return q.join('plants').filter_by(location_id=obj.id)
    elif isinstance(obj, Contact):
        return q.join('source', 'source_detail').filter_by(id=obj.id)
    elif isinstance(obj, Tag):
        acc = get_accessions_pertinent_to(obj.objects, session)
        return q.filter(Accession.id.in_([a.id for a in acc]))
    else:
        raise BaubleError(_("Can't get accessions from a %s") %
                          type(obj).__name__)


def get_accessions_pertinent_to(objs, session=None):
    """
    :param objs: an instance of a mapped object
    :param session: the session to use for the queries

    Return all the accessions found in objs.
    """
    return _get_pertinent_objects(
        Accession, get_accession_query, objs, session)


def get_species_query(obj, session):
    """
    """
    q = session.query(Species).order_by(None)
    if isinstance(obj, Family):
        return q.join('genus', 'family').\
            filter_by(id=obj.id)
    elif isinstance(obj, Genus):
        return q.join('genus').filter_by(id=obj.id)
    elif isinstance(obj, Species):
        return q.filter_by(id=obj.id)
    elif isinstance(obj, VernacularName):
        return q.join('vernacular_names').\
            filter_by(id=obj.id)
    elif isinstance(obj, Plant):
        return q.join('accessions', 'plants').filter_by(id=obj.id)
    elif isinstance(obj, Accession):
        return q.join('accessions').filter_by(id=obj.id)
    elif isinstance(obj, Location):
        return q.join('accessions', 'plants', 'location').\
            filter_by(id=obj.id)
    elif isinstance(obj, Contact):
        return q.join('accessions', 'source', 'source_detail').\
                filter_by(id=obj.id)
    elif isinstance(obj, Tag):
        acc = get_species_pertinent_to(obj.objects, session)
        return q.filter(Species.id.in_([a.id for a in acc]))
    else:
        raise BaubleError(_("Can't get species from a %s") %
                          type(obj).__name__)


def get_species_pertinent_to(objs, session=None):
    """
    :param objs: an instance of a mapped object
    :param session: the session to use for the queries

    Return all the species found in objs.
    """
    return sorted(
        _get_pertinent_objects(Species, get_species_query, objs, session),
        key=lambda x: "%s" % x)


def get_location_query(obj, session):
    """
    """
    q = session.query(Location).order_by(None)
    if isinstance(obj, Location):
        return q.filter_by(id=obj.id)
    elif isinstance(obj, Plant):
        return q.join('plants').filter_by(id=obj.id)
    elif isinstance(obj, Accession):
        return q.join('plants', 'accession').filter_by(id=obj.id)
    elif isinstance(obj, Family):
        return q.join('plants', 'accession', 'species', 'genus', 'family').\
            filter_by(id=obj.id)
    elif isinstance(obj, Genus):
        return q.join('plants', 'accession', 'species', 'genus').\
            filter_by(id=obj.id)
    elif isinstance(obj, Species):
        return q.join('plants', 'accession', 'species').\
            filter_by(id=obj.id)
    elif isinstance(obj, VernacularName):
        return q.join('plants', 'accession', 'species', 'vernacular_names').\
            filter_by(id=obj.id)
    elif isinstance(obj, Contact):
        return q.join('plants', 'accession', 'source', 'source_detail').\
                filter_by(id=obj.id)
    elif isinstance(obj, Tag):
        locs = get_locations_pertinent_to(obj.objects, session)
        return q.filter(Location.id.in_([l.id for l in locs]))
    else:
        raise BaubleError(_("Can't get Location from a %s") %
                          type(obj).__name__)


def get_locations_pertinent_to(objs, session=None):
    """
    :param objs: an instance of a mapped object
    :param session: the session to use for the queries

    Return all the locations found in objs.
    """
    return sorted(
        _get_pertinent_objects(Location, get_location_query, objs, session),
        key=str)


class SettingsBox(Gtk.VBox):
    """
    the interface to use for the settings box, formatters should
    implement this interface and return it from the formatters's get_settings
    method
    """
    def __init__(self):
        super().__init__()

    def get_settings(self):
        raise NotImplementedError

    def update(self, settings):
        raise NotImplementedError


class FormatterPlugin(pluginmgr.Plugin):
    '''
    an interface class that a plugin should implement if it wants to generate
    reports with the ReportToolPlugin

    NOTE: the title class attribute must be a unique string
    '''

    title = ''

    @staticmethod
    def get_settings_box():
        '''
        return a class the implement Gtk.Box that should hold the gui for
        the formatter
        '''
        raise NotImplementedError

    @staticmethod
    def format(selfobjs, **kwargs):
        '''
        called when the use clicks on OK, this is the worker
        '''
        raise NotImplementedError


class ReportToolDialogPresenter(GenericEditorPresenter):

    formatter_class_map = {}  # title->class map

    def __init__(self, view):
        super().__init__(model=self, view=view, refresh_view=False)
        self.populate_names_combo()

        self.view.widget_set_sensitive('ok_button', False)

        # set the names combo to the default. this activates
        # on_names_combo_changes, which does the rest of the work
        combo = self.view.widgets.names_combo
        default = prefs[default_config_pref]
        self.view.widget_set_value('names_combo', default)

    def set_prefs_for(self, name, template, settings):
        '''
        This will overwrite any other report settings with name
        '''
        activated_templates = prefs[config_list_pref]
        if activated_templates is None:
            activated_templates = {}
        activated_templates[name] = template, settings
        prefs[config_list_pref] = activated_templates

    def on_new_button_clicked(self, *args):
        d = Gtk.Dialog(_("Activate Formatter Template"), self.view.get_window(),
                       Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                       buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.REJECT,
                                Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT))
        d.vbox.set_spacing(10)
        d.set_default_response(Gtk.ResponseType.ACCEPT)

        # label
        text = '<b>%s</b>' % _('Enter a Name and choose a Formatter Template')
        label = Gtk.Label()
        label.set_markup(text)
        label.set_xalign(0)
        d.vbox.pack_start(label, True, True, 0)

        # entry
        entry = Gtk.Entry()
        entry.set_activates_default(True)
        d.vbox.pack_start(entry, True, True, 0)

        # file_chooser_widget
        chooser = Gtk.FileChooserWidget(0)
        d.vbox.pack_start(chooser, True, True, 0)

        # action
        d.show_all()
        names = set(prefs[config_list_pref].keys())
        templates = dict([(v[0], k) for (k, v) in prefs[config_list_pref].items()])
        while True:
            if d.run() != Gtk.ResponseType.ACCEPT:
                break
            name = entry.get_text()
            template = chooser.get_filename()
            if name == '' or template is None:
                # ignore action on emtpy choice
                continue
            elif name in names:
                utils.message_dialog(_('%s already exists') % name)
                continue
            elif template in templates:
                utils.message_dialog(_('already activated as %s') % templates[template])
                continue
            else:
                self.set_prefs_for(name, template, {})
                self.populate_names_combo()
                self.view.widget_set_value('names_combo', name)
                break
        d.destroy()

    def on_remove_button_clicked(self, *args):
        activated_templates = prefs[config_list_pref]
        name = self.view.widget_get_value('names_combo')
        self.view.widgets.names_combo.set_active(-1)
        self.view.widgets.names_combo.get_child().text = ''
        activated_templates.pop(name)
        prefs[config_list_pref] = activated_templates
        self.populate_names_combo()

    def on_names_combo_changed(self, combo, *args):
        name = self.view.widget_get_value('names_combo')
        activated_templates = prefs[config_list_pref]
        self.view.widget_set_sensitive('details_box', name is not None)
        prefs[default_config_pref] = name  # set the default to the new name
        try:
            template, settings = activated_templates[name]
        except (KeyError, TypeError) as e:
            # TODO: show a dialog saying that you can't find whatever
            # you're looking for in the settings
            logger.debug(e)
            return

        self.view.widget_set_sensitive('details_box', True)

    def populate_names_combo(self):
        '''copy configuration names from prefs into names_ls

        '''
        activated_templates = prefs[config_list_pref]
        self.view.widgets.names_ls.clear()
        for name in list(activated_templates.keys()):
            self.view.widgets.names_ls.append((name, ))

    def save_formatter_settings(self):
        name = self.view.widget_get_value('names_combo')
        title, dummy = prefs[config_list_pref][name]
        box = self.view.widgets.settings_expander.get_child()
        activated_templates = prefs[config_list_pref]
        activated_templates[name] = template, box.get_settings()
        prefs[config_list_pref] = activated_templates

    def start(self):
        formatter = None
        settings = None
        while True:
            response = self.view.start()
            if response == Gtk.ResponseType.OK:
                # get format method
                # save default
                name = self.view.widget_get_value('names_combo')
                prefs[default_config_pref] = name
                self.save_formatter_settings()
                title, settings = prefs[config_list_pref][name]
                formatter = self.formatter_class_map[title]
                break
            else:
                break
        self.view.disconnect_all()
        return formatter, settings


class ReportToolDialog(object):

    def __init__(self):
        filename = os.path.join(paths.lib_dir(), "plugins", "report", 'report.glade')
        self.view = GenericEditorView(filename, root_widget_name='report_dialog')
        self.presenter = ReportToolDialogPresenter(self.view)

    def start(self):
        return self.presenter.start()


class ReportTool(pluginmgr.Tool):
    category = (_('Report'), "plugins/report/tool-report.png")
    label = _("From Template")
    icon_file_name = "report/from-template.png"

    @classmethod
    def start(self):
        '''
        '''
        # get the select results from the search view
        model = bauble.gui.get_results_model()

        bauble.gui.set_busy(True)
        ok = False
        try:
            while True:
                dialog = ReportToolDialog()
                formatter, settings = dialog.start()
                if formatter is None:
                    break
                ok = formatter.format([row[0] for row in model], **settings)
                if ok:
                    break
        except AssertionError as e:
            logger.debug(e)
            logger.debug(traceback.format_exc())
            parent = None
            if hasattr(self, 'view') and hasattr(self.view, 'dialog'):
                parent = self.view.get_window()

            utils.message_details_dialog(str(e), traceback.format_exc(),
                                         Gtk.MessageType.ERROR, parent=parent)
        except Exception as e:
            logger.debug(traceback.format_exc())
            utils.message_details_dialog(_('Formatting Error\n\n'
                                           '%(exception)s') %
                                         {"exception": utils.utf8(e)},
                                         traceback.format_exc(),
                                         Gtk.MessageType.ERROR)
        bauble.gui.set_busy(False)
        return


class ReportToolPlugin(pluginmgr.Plugin):
    '''
    '''
    tools = [ReportTool, FlatFileExportTool, ]


try:
    import lxml.etree as etree
    import lxml._elementpath  # put this here so py2exe picks it up
except ImportError:
    utils.message_dialog('The <i>lxml</i> package is required for the '
                         'Report plugin')
else:
    def plugin():
        from bauble.plugins.report.xsl import XSLFormatterPlugin
        from bauble.plugins.report.mako import MakoFormatterPlugin
        return [ReportToolPlugin, XSLFormatterPlugin,
                MakoFormatterPlugin]

## compatibility aliases:
get_all_plants = get_plants_pertinent_to
get_all_accessions = get_accessions_pertinent_to
get_all_species = get_species_pertinent_to
