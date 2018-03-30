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

import gtk
import gobject

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

# TODO: this module should depend on PlantPlugin, GardenPlugin,
# TagPlugin and should also allow other plugins to register between
# two type of objects

# TODO: should be able to drop a new formatter plugin and have it
# automatically detected, right now we to return it in this modules
# plugin() function

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
    queries = map(lambda o: get_query_func(o, session), objs)
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
        key=str)


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


class SettingsBox(gtk.VBox):
    """
    the interface to use for the settings box, formatters should
    implement this interface and return it from the formatters's get_settings
    method
    """
    def __init__(self):
        super(SettingsBox, self).__init__()

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
        return a class the implement gtk.Box that should hold the gui for
        the formatter
        '''
        raise NotImplementedError

    @staticmethod
    def format(selfobjs, **kwargs):
        '''
        called when the use clicks on OK, this is the worker
        '''
        raise NotImplementedError


class ReportToolDialogView(object):

    def __init__(self):
        self.widgets = utils.load_widgets(
            os.path.join(paths.lib_dir(), "plugins", "report", 'report.glade'))
        self.dialog = self.widgets.report_dialog
        self.dialog.set_transient_for(bauble.gui.window)
        self.builder = self.widgets.builder
        utils.setup_text_combobox(self.widgets.names_combo)
        utils.setup_text_combobox(self.widgets.formatter_combo)

        self._delete_sid = self.dialog.connect(
            'delete-event', self.on_dialog_close_or_delete)
        self._close_sid = self.dialog.connect(
            'close', self.on_dialog_close_or_delete)
        self._response_sid = self.dialog.connect(
            'response', self.on_dialog_response)

    def on_dialog_response(self, dialog, response, *args):
        '''
        Called if self.get_window() is a gtk.Dialog and it receives
        the response signal.
        '''
        dialog.hide()
        self.response = response
        return response

    def on_dialog_close_or_delete(self, dialog, event=None):
        """
        Called if self.get_window() is a gtk.Dialog and it receives
        the close signal.
        """
        dialog.hide()
        return False

    def disconnect_all(self):
        self.dialog.disconnect(self._delete_sid)
        self.dialog.disconnect(self._close_sid)
        self.dialog.disconnect(self._response_sid)

    def start(self):
        return self.dialog.run()

    def set_sensitive(self, name, sensitivity):
        try:
            self.builder.get_object(name).set_sensitive(sensitivity)
        except:
            logger.debug("can't set sensitivity of %s" % name)


class ReportToolDialogPresenter(object):

    formatter_class_map = {}  # title->class map

    def __init__(self, view):
        self.view = view
        self.init_names_combo()
        self.init_formatter_combo()

        self.view.builder.connect_signals(self)

        self.view.set_sensitive('ok_button', False)

        # set the names combo to the default, on_names_combo_changes should
        # do the rest of the work
        combo = self.view.widgets.names_combo
        default = prefs[default_config_pref]
        try:
            self.set_names_combo(default)
        except Exception, e:
            logger.debug(e)
            self.set_names_combo(0)

    def set_names_combo(self, val):
        """
        Set the names combo to val and emit the 'changed' signal,
        :param val: either an integer index or a string value in the combo

        If the model on the combo is None then this method will return
        and not emit the changed signal
        """
        combo = self.view.widgets.names_combo
        if combo.get_model() is None:
            self.view.set_sensitive('details_box', False)
            return
        if val is None:
            combo.set_active(-1)
        elif isinstance(val, int):
            combo.set_active(val)
        else:
            utils.combo_set_active_text(combo, val)

    def set_formatter_combo(self, val):
        """
        Set the formatter combo to val and emit the 'changed' signal.

        :param val: either an integer index or a string value in the
          combo combo = self.view.widgets.formatter_combo
        """
        combo = self.view.widgets.formatter_combo
        if val is None:
            combo.set_active(-1)
        elif isinstance(val, int):
            combo.set_active(val)
        else:
            utils.combo_set_active_text(combo, val)

    def set_prefs_for(self, name, formatter_title, settings):
        '''
        This will overwrite any other report settings with name
        '''
        formatters = prefs[config_list_pref]
        if formatters is None:
            formatters = {}
        formatters[name] = formatter_title, settings
        prefs[config_list_pref] = formatters

    def on_new_button_clicked(self, *args):
        # TODO: don't set the OK button as sensitive in the name dialog
        # if the name already exists
        # TODO: make "Enter" in the entry fire the default response
        d = gtk.Dialog(_("Formatter Name"), self.view.dialog,
                       gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                       buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                                gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        d.vbox.set_spacing(10)
        d.set_default_response(gtk.RESPONSE_ACCEPT)
        text = '<b>%s</b>' % _('Enter a name for the new formatter')
        label = gtk.Label()
        label.set_markup(text)
        label.set_padding(10, 10)
        d.vbox.pack_start(label)
        entry = gtk.Entry()
        entry.set_activates_default(True)
        d.vbox.pack_start(entry)
        d.show_all()
        names_model = self.view.widgets.names_combo.get_model()
        while True:
            if d.run() == gtk.RESPONSE_ACCEPT:
                name = entry.get_text()
                if name == '':
                    continue
                elif names_model is not None \
                        and utils.tree_model_has(names_model, name):
                    utils.message_dialog(_('%s already exists') % name)
                    continue
                else:
                    self.set_prefs_for(entry.get_text(), None, {})
                    self.populate_names_combo()
                    utils.combo_set_active_text(self.view.widgets.names_combo,
                                                name)
                    break
            else:
                break
        d.destroy()

    def on_remove_button_clicked(self, *args):
        formatters = prefs[config_list_pref]
        names_combo = self.view.widgets.names_combo
        name = names_combo.get_active_text()
        formatters.pop(name)
        prefs[config_list_pref] = formatters
        self.populate_names_combo()
        names_combo.set_active(0)

    def on_names_combo_changed(self, combo, *args):
        if combo.get_model() is None:
            self.view.set_sensitive('details_box', False)
            return

        name = combo.get_active_text()
        formatters = prefs[config_list_pref]
        self.view.set_sensitive('details_box', name is not None)
        prefs[default_config_pref] = name  # set the default to the new name
        try:
            title, settings = formatters[name]
        except (KeyError, TypeError), e:
            # TODO: show a dialog saying that you can't find whatever
            # you're looking for in the settings
            logger.debug(e)
            return

        try:
            self.set_formatter_combo(title)
        except Exception, e:
            # TODO: show a dialog saying that you can't find whatever
            # you're looking for in the settings
            logger.debug(e)
            self.set_formatter_combo(-1)
        self.view.set_sensitive('details_box', True)

    def on_formatter_combo_changed(self, combo, *args):
        '''
        formatter_combo changed signal handler
        '''
        self.view.set_sensitive('ok_button', False)
        gobject.idle_add(self._formatter_combo_changed_idle, combo)

    def _formatter_combo_changed_idle(self, combo):
        formatter = combo.get_active_text()
        name = self.view.widgets.names_combo.get_active_text()
        try:
            saved_name, settings = prefs[config_list_pref][name]
        except KeyError, e:
            logger.debug(e)
            return

        expander = self.view.widgets.settings_expander
        child = expander.get_child()
        if child:
            expander.remove(child)

        #self.widgets.ok_button.set_sensitive(title is not None)
        self.view.set_sensitive('ok_button', formatter is not None)
        if not formatter:
            return
        try:
            cls = self.formatter_class_map[formatter]
        except KeyError:
            return
        box = cls.get_settings_box()
        if box:
            box.update(settings)
            expander.add(box)
            box.show_all()
        expander.set_sensitive(box is not None)
        # TODO: should probably remember expanded state,
        # see formatter_settings_expander_pref
        expander.set_expanded(box is not None)
        #formatter = combo.get_active_text()
        self.set_prefs_for(name, formatter, settings)
        self.view.set_sensitive('ok_button', True)

    def init_formatter_combo(self):
        plugins = []
        for p in pluginmgr.plugins.values():
            if isinstance(p, FormatterPlugin):
                logger.debug('recognized %s as a FormatterPlugin', p)
                plugins.append(p)
            else:
                logger.debug('discarded %s: not a FormatterPlugin', p)

        # we should always have at least the default formatter
        model = gtk.ListStore(str)
        if len(plugins) == 0:
            utils.message_dialog(_('No formatter plugins defined'),
                                 gtk.MESSAGE_WARNING)
            return

        for item in plugins:
            title = item.title
            self.formatter_class_map[title] = item
            model.append([item.title])
        self.view.widgets.formatter_combo.set_model(model)

    def populate_names_combo(self):
        '''
        populates the combo with the list of configuration names
        from the prefs
        '''
        configs = prefs[config_list_pref]
        combo = self.view.widgets.names_combo
        if configs is None:
            self.view.set_sensitive('details_box', False)
            utils.clear_model(combo)
            return
        try:
            model = gtk.ListStore(str)
            for cfg in configs.keys():
                model.append([cfg])
            combo.set_model(model)
        except AttributeError, e:
            # no formatters
            logger.debug(e)
            pass

    def init_names_combo(self):
        formatters = prefs[config_list_pref]
        if formatters is None or len(formatters) == 0:
            msg = _('No formatters found. To create a new formatter click '
                    'the "New" button.')
            utils.message_dialog(msg, parent=self.view.dialog)
            self.view.widgets.names_combo.set_model(None)
        self.populate_names_combo()

    def save_formatter_settings(self):
        name = self.view.widgets.names_combo.get_active_text()
        title, dummy = prefs[config_list_pref][name]
        box = self.view.widgets.settings_expander.get_child()
        formatters = prefs[config_list_pref]
        formatters[name] = title, box.get_settings()
        prefs[config_list_pref] = formatters

    def start(self):
        formatter = None
        settings = None
        while True:
            response = self.view.start()
            if response == gtk.RESPONSE_OK:
                # get format method
                # save default
                prefs[default_config_pref] = \
                    self.view.widgets.names_combo.get_active_text()
                self.save_formatter_settings()
                name = self.view.widgets.names_combo.get_active_text()
                title, settings = prefs[config_list_pref][name]
                formatter = self.formatter_class_map[title]
                break
            else:
                break
        self.view.disconnect_all()
        return formatter, settings


class ReportToolDialog(object):

    def __init__(self):
        self.view = ReportToolDialogView()
        self.presenter = ReportToolDialogPresenter(self.view)

    def start(self):
        return self.presenter.start()


class ReportTool(pluginmgr.Tool):

    label = _("Report")

    @classmethod
    def start(self):
        '''
        '''
        # get the select results from the search view
        from bauble.view import SearchView
        view = bauble.gui.get_view()
        if not isinstance(view, SearchView):
            utils.message_dialog(_('Search for something first.'))
            return

        model = view.results_view.get_model()
        if model is None:
            utils.message_dialog(_('Search for something first.'))
            return

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
        except AssertionError, e:
            logger.debug(e)
            logger.debug(traceback.format_exc())
            parent = None
            if hasattr(self, 'view') and hasattr(self.view, 'dialog'):
                parent = self.view.dialog

            utils.message_details_dialog(str(e), traceback.format_exc(),
                                         gtk.MESSAGE_ERROR, parent=parent)
        except Exception, e:
            logger.debug(traceback.format_exc())
            utils.message_details_dialog(_('Formatting Error\n\n'
                                           '%(exception)s') %
                                         {"exception": utils.utf8(e)},
                                         traceback.format_exc(),
                                         gtk.MESSAGE_ERROR)
        bauble.gui.set_busy(False)
        return


class ReportToolPlugin(pluginmgr.Plugin):
    '''
    '''
    tools = [ReportTool]


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
