# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Brett Adams
# Copyright 2012-2018 Mario Frasca <mario@anche.no>.
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
from gi.repository import Gdk
from gi.repository import GObject

from threading import Thread

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
        plants = get_pertinent_objects(Plant, obj.objects)
        return q.filter(Plant.id.in_([p.id for p in plants]))
    else:
        raise BaubleError(_("Can't get plants from a %s") % type(obj).__name__)


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
        acc = get_pertinent_objects(Accession, obj.objects)
        return q.filter(Accession.id.in_([a.id for a in acc]))
    else:
        raise BaubleError(_("Can't get accessions from a %s") %
                          type(obj).__name__)


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
        acc = get_pertinent_objects(Species, obj.objects)
        return q.filter(Species.id.in_([a.id for a in acc]))
    else:
        raise BaubleError(_("Can't get species from a %s") %
                          type(obj).__name__)


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
        locs = get_pertinent_objects(Location, obj.objects)
        return q.filter(Location.id.in_([l.id for l in locs]))
    else:
        raise BaubleError(_("Can't get Location from a %s") %
                          type(obj).__name__)


def get_pertinent_objects(cls, objs):
    """return a query containing all `csl` objects reachable from `objs`

    :param cls:
    :param objs:
    """
    if not isinstance(objs, (list, tuple)):
        objs = [objs]
    from sqlalchemy.orm import object_session
    session = object_session(objs[0])

    get_query_func = {
        Plant: get_plant_query,
        Accession: get_accession_query,
        Species: get_species_query,
        Location: get_location_query,
    }[cls]

    queries = [get_query_func(o, session) for o in objs]
    unions = union(*[q.statement for q in queries])
    return session.query(cls).from_statement(unions)


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

    @classmethod
    def init(cls):
        '''inform report presenter that this plugin is available

        (extend in derived classes)
        '''
        cls.install()  # plugins still not versioned...
        ReportToolDialogPresenter.formatter_class_map[cls.title] = cls

    @staticmethod
    def format(objs, **kwargs):
        '''
        called when the use clicks on OK, this is the worker
        '''
        raise NotImplementedError

    @classmethod
    def can_handle(cls, template):
        '''tell whether plugin can handle template
        '''
        return cls.get_iteration_domain(template) != ''

    @classmethod
    def get_options(cls, template):
        '''return template options list

        an element in the options list is a 4-tuple of strings, describing a
        field: (name, type, default, tooltip)

        '''
        try:
            with open(template) as f:
                option_lines = [m for m in [cls.option_pattern.match(i.strip())
                                            for i in f.readlines()]
                                if m is not None]
        except IOError:
            option_lines = []

        return [i.groups() for i in option_lines]

    @classmethod
    def get_iteration_domain(cls, template):
        '''return template iteration domain

        a template that does not declare its iteration domain is not
        considered valid.

        '''
        try:
            with open(template) as f:
                domains = [m.group(1) for m in [cls.domain_pattern.match(line.strip())
                                                for line in f.readlines()]
                           if m is not None]
                try:
                    domain = domains[0]
                except IndexError as e:
                    logger.debug("template %s contains no DOMAIN declarations" % (template, ))
                    domain = ''
        except:
            logger.debug("template %s can't be read" % template)
            domain = ''

        return domain


class ReportToolDialogPresenter(GenericEditorPresenter):
    '''presenter, and at same time model.

    Let user set parameters for report production, return them to invoking
    function, and die.

    '''

    # to be populated by template plugins
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
        self.hard_coded_option = set(self.view.widgets.options_box.get_children())

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
                utils.message_dialog(_('Already activated as %s') % templates[template])
                continue
            else:
                for plugin in self.formatter_class_map.values():
                    if plugin.can_handle(template):
                        break
                else:
                    utils.message_dialog(_('Not a template, or no valid formatter installed.'))
                    continue

            self.set_prefs_for(name, template, {})
            self.populate_names_combo()
            self.view.widget_set_value('names_combo', name)
            break
        d.destroy()

    def on_remove_button_clicked(self, *args):
        activated_templates = prefs[config_list_pref]
        name = self.view.widget_get_value('names_combo')
        self.view.widgets.names_combo.set_active(-1)
        self.view.widgets.names_combo.get_child().set_text('')
        self.view.widget_set_value('dirname_entry', '')
        self.view.widget_set_value('basename_entry', '')
        self.view.widget_set_value('formatter_entry', '')
        self.view.widget_set_value('domain_entry', '')
        activated_templates.pop(name)
        prefs[config_list_pref] = activated_templates
        self.populate_names_combo()

    def on_names_combo_changed(self, combo, *args):
        self.options = {}
        name = self.view.widget_get_value('names_combo')
        activated_templates = prefs[config_list_pref]
        self.view.widget_set_sensitive('details_box', (name or '') != '')
        prefs[default_config_pref] = name  # set the default to the new name
        GObject.idle_add(self._names_combo_changed_idle, combo)

    def _names_combo_changed_idle(self, combo):
        name = self.view.widget_get_value('names_combo')
        try:
            template, settings = prefs[config_list_pref][name]
        except KeyError as e:
            logger.debug(e)
            return

        self.view.widget_set_sensitive('ok_button', False)
        self.view.widget_set_value('dirname_entry', '')
        self.view.widget_set_value('basename_entry', '')
        self.view.widget_set_value('formatter_entry', '')
        self.view.widget_set_value('domain_entry', '')
        for formatter, plugin in self.formatter_class_map.items():
            domain = plugin.get_iteration_domain(template)
            if domain != '':
                if domain == 'raw':
                    model = bauble.gui.get_results_model()
                    top_left_content = model[0][0]
                    domain = '(%s)' % top_left_content.__class__.__name__.lower()
                dirname = os.path.dirname(template)
                basename = os.path.basename(template)
                self.view.widget_set_value('dirname_entry', dirname)
                self.view.widget_set_value('basename_entry', basename)
                self.view.widget_set_value('formatter_entry', formatter)
                self.view.widget_set_value('domain_entry', domain)
                self.view.widget_set_sensitive('ok_button', True)
                break
        else:
            utils.message_dialog('this should NOT happen.\nan invalid template at this stage.')
            return

        self.set_prefs_for(name, template, settings)

        self.defaults = []
        options_box = self.view.widgets.options_box
        # empty the options box
        for child in options_box.get_children():
            if child in self.hard_coded_option:
                continue
            options_box.remove(child)
        # which options does the template accept? (can be None)
        option_fields = plugin.get_options(template)
        current_row = 1  # should not be hard coded
        # populate the options box
        for fname, ftype, fdefault, ftooltip in option_fields:
            row = Gtk.HBox()
            label = Gtk.Label(fname.replace('_', ' ') + _(':'))
            label.set_alignment(0, 0.5)
            ftype = ftype.lower()
            if ftype == 'bool':
                fdefault = fdefault.lower() not in ['false', '0']
                self.options.setdefault(fname, fdefault)
                entry = Gtk.CheckButton()
                entry.set_margin_left(4)
                entry.set_active(self.options[fname])
                entry.connect('toggled', self.set_bool_option, fname)
            else:
                self.options.setdefault(fname, fdefault)
                entry = Gtk.Entry()
                entry.set_text(self.options[fname])
                entry.connect('changed', self.set_option, fname)
            entry.set_tooltip_text(ftooltip)
            # entry updates the corresponding item in report.options
            self.defaults.append((entry, fdefault))
            options_box.attach(label, 0, current_row, 1, 1)
            options_box.attach(entry, 1, current_row, 2, 1)
            current_row += 1
        if self.defaults:
            button = Gtk.Button(_('Reset to defaults'))
            button.connect('clicked', self.reset_options)
            options_box.attach(button, 3, current_row - 1, 2, 1)
        options_box.show_all()

    def reset_options(self, widget):
        for entry, value in self.defaults:
            if isinstance(value, bool):
                entry.set_active(value)
            else:
                entry.set_text(value)

    def set_option(self, widget, fname):
        self.options[fname] = widget.get_text()

    def set_bool_option(self, widget, fname):
            self.options[fname] = widget.get_active()

    def populate_names_combo(self):
        '''copy configuration names from prefs into names_ls

        '''
        activated_templates = prefs[config_list_pref]
        self.view.widgets.names_ls.clear()
        for name in list(activated_templates.keys()):
            self.view.widgets.names_ls.append((name, ))

    def save_formatter_settings(self):
        activated_templates = prefs[config_list_pref]
        name = self.view.widget_get_value('names_combo')
        title, dummy = activated_templates[name]
        activated_templates[name] = title, self.options
        prefs[config_list_pref] = activated_templates

    def selection_to_domain(self, domain):
        '''convert the selection to the corresponding domain

        if domain is one of species, accession, plant, location, then
        retrieve all objects in the domain that are associated to the
        selected objects.

        if domain looks like `(domain)`, then it is an implicit domain,
        i.e.: it was inferred from the selection itself, so the selection
        itself is what we need.

        if the domain is `raw`, also that tells us to return the raw
        selection (the template will handle it).

        '''
        try:
            cls = {
                'plant': Plant,
                'accession': Accession,
                'species': Species,
                'location': Location,
            }[domain]
            return sorted(get_pertinent_objects(cls, self.selection),
                          key=utils.natsort_key)
        except KeyError:
            return self.selection

    def start(self):
        '''collect user choices, invokes formatter, repeat.

        '''
        results_model = bauble.gui.get_results_model()  # guaranteed not empty
        self.selection = [row[0] for row in results_model]  # only top level selected
        from sqlalchemy.orm import object_session
        self.session = object_session(self.selection[0])  # reuse the same session

        formatter = None
        settings = None
        while True:
            response = self.view.start()
            if response != Gtk.ResponseType.OK:
                break

            name = self.view.widget_get_value('names_combo')
            prefs[default_config_pref] = name
            self.save_formatter_settings()
            template, settings = prefs[config_list_pref][name]
            settings['template'] = template
            domain = self.view.widget_get_value('domain_entry')
            title = self.view.widget_get_value('formatter_entry')
            formatter = self.formatter_class_map[title]
            todo = self.selection_to_domain(domain)
            if todo:
                self.work_thread = Thread(target=self.run_thread, args=[formatter, todo, settings])
                self.running = True
                GObject.timeout_add(200, self.update_progress)
                self.view.widgets.main_grid.set_sensitive(False)
                self.view.widget_set_sensitive('ok_button', False)
                self.view.widget_set_sensitive('cancel_button', False)
                self.work_thread.start()
            else:
                translated_name = {
                    'plant': _('plants/clones'),
                    'accession': _('accessions'),
                    'species': _('species'),
                    'location': _('locations'),
                }[domain]
                utils.message_dialog(_('There are no %s in the search results.\n'
                                       'Please try another search.') % translated_name)

        self.view.disconnect_all()

    def update_progress(self):
        if self.running:
            self.view.widgets.progressbar.pulse()
        return self.running

    def run_thread(self, formatter, todo, settings):
        from bauble import db
        session = db.Session()
        todo = [session.merge(i) for i in todo]
        try:
            formatter.format(todo, **settings)
        except Exception as e:
            utils.idle_message("formatting %s objects of type %s\n%s(%s)\n%s" % (len(todo), type((todo+[None])[0]).__name__, type(e).__name__, e, traceback.format_exc()), type=Gtk.MessageType.ERROR)
                             
        session.close()
        GObject.idle_add(self.stop_progress)

    def stop_progress(self):
        self.running = False
        self.work_thread.join()
        self.view.widgets.main_grid.set_sensitive(True)
        self.view.widget_set_sensitive('ok_button', True)
        self.view.widget_set_sensitive('cancel_button', True)
        self.view.widgets.progressbar.set_fraction(0)
        

class ReportTool(pluginmgr.Tool):
    category = (_('Report'), "plugins/report/tool-report.png")
    label = _("From Template")
    icon_name = "text-x-generic-template"

    @classmethod
    def start(self):
        '''
        '''
        # is anything selected?  if not, refuse even considering
        if not bauble.gui.get_results_model():
            return

        bauble.gui.set_busy(True)
        ok = False
        try:
            filename = os.path.join(paths.lib_dir(), "plugins", "report", 'report.glade')
            view = GenericEditorView(filename, root_widget_name='report_dialog')
            presenter = ReportToolDialogPresenter(view)
            presenter.start()
        except AssertionError as e:
            logger.debug(e)
            logger.debug(traceback.format_exc())
            parent = None
            if hasattr(self, 'view') and hasattr(self.view, 'dialog'):
                parent = self.view.get_window()

            utils.message_details_dialog("AssertionError(%s)" % e, traceback.format_exc(),
                                         Gtk.MessageType.ERROR, parent=parent)
        except Exception as e:
            logger.debug(traceback.format_exc())
            utils.message_details_dialog(_('Formatting Error\n\n'
                                           '%s(%s)') % (type(e).__name__, utils.utf8(e)),
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
