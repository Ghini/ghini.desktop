# -*- coding: utf-8 -*-
#
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

from bauble.i18n import _
import bauble.utils as utils
import bauble.db as db
from bauble.plugins.plants import (Familia, Genus, Species, VernacularName)
from bauble.plugins.garden.plant import (Plant, PlantNote)
from bauble.plugins.garden.accession import (Accession, AccessionNote)
from bauble.plugins.garden.location import (Location)
import bauble.task
import bauble.editor as editor
from bauble.error import check, CheckConditionError
import bauble.paths as paths
import json
import bauble.pluginmgr as pluginmgr
from bauble import pb_set_fraction



def serializedatetime(obj):
    """Default JSON serializer."""
    import calendar
    import datetime

    if isinstance(obj, (Familia, Genus, Species)):
        return str(obj)
    elif isinstance(obj, datetime.datetime):
        if obj.utcoffset() is not None:
            obj = obj - obj.utcoffset()
    millis = calendar.timegm(obj.timetuple()) * 1000
    try:
        millis += int(obj.microsecond / 1000)
    except AttributeError:
        pass
    return {'__class__': 'datetime', 'millis': millis}


class TreeStoreFlattener(object):

    def __call__(self, model):
        self.result = []
        return self.flatten(model, model.iter_children(None))

    def flatten(self, model, iter):
        while iter:
            self.result.append(model.get_value(iter, 0))
            self.flatten(model, model.iter_children(iter))
            iter = model.iter_next(iter)
        return self.result

tree_store_flatten = TreeStoreFlattener()


class ExportToJson(editor.GenericEditorView):
    "the View ((M)VP)"

    _tooltips = {}
    _choices = {'based_on': 'selection',
                'includes': 'referred',
                }

    last_folder = ''

    def radio_button_pushed(self, widget, group):
        name = gtk.Buildable.get_name(widget).split('_')[1]
        self._choices[group] = name
        logger.debug("selected %s for group %s" % (name, group))

    def __init__(self, session, parent=None):
        self.session = session
        filename = os.path.join(paths.lib_dir(), 'plugins', 'imex',
                                'select_export.glade')
        super(ExportToJson, self).__init__(filename, parent=parent)
        self.builder.connect_signals(self)
        for wn in ['selection', 'taxa', 'accessions', 'plants']:
            self.connect('sbo_' + wn, 'toggled',
                         self.radio_button_pushed, "based_on")
        for wn in ['referred', 'referring']:
            self.connect('ei_' + wn, 'toggled',
                         self.radio_button_pushed, "includes")

    def on_btnbrowse_clicked(self, button):
        chooser = gtk.FileChooserDialog(
            _("Choose a file..."), None,
            buttons=(gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
                     gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
        #chooser.set_do_overwrite_confirmation(True)
        #chooser.connect("confirm-overwrite", confirm_overwrite_callback)
        try:
            if self.last_folder:
                chooser.set_current_folder(self.last_folder)
            if chooser.run() == gtk.RESPONSE_ACCEPT:
                filename = chooser.get_filename()
                if filename:
                    ExportToJson.last_folder, bn = os.path.split(filename)
                    self.widgets.filename.set_text(filename)
        except Exception, e:
            logger.warning("unhandled exception in iojson.py: %s" % e)
        chooser.destroy()

    def get_window(self):
        return self.widgets.select_export_dialog

    def start(self):
        return self.get_window().run()

    def get_filename(self):
        return self.widgets.filename.get_text()

    def popup_message(self, message):
        'show message and return'
        utils.message_dialog(message)

    def get_objects(self):
        '''return the list of objects to be exported

        if "based_on" is "selection", return the top level selection only.

        if "based_on" is something else, return all that is needed to create
        a complete export.
        '''
        if self._choices['based_on'] == 'selection':
            class EmptySelectionException(Exception):
                pass
            from bauble.view import SearchView
            view = bauble.gui.get_view()
            try:
                check(isinstance(view, SearchView))
                tree_view = view.results_view.get_model()
                check(tree_view is not None)
            except CheckConditionError:
                utils.message_dialog(_('Search for something first.'))
                return

            return [row[0] for row in tree_view]

        ## export disregarding selection
        result = []
        if self._choices['based_on'] == 'plants':
            plants = self.session.query(Plant).order_by(Plant.code).join(
                Accession).order_by(Accession.code).all()
            plantnotes = self.session.query(PlantNote).all()
            ## only used locations and accessions
            locations = self.session.query(Location).filter(
                Location.id.in_([j.location_id for j in plants])).all()
            accessions = self.session.query(Accession).filter(
                Accession.id.in_([j.accession_id for j in plants])).order_by(
                Accession.code).all()
            ## notes are linked in opposite direction
            accessionnotes = self.session.query(AccessionNote).filter(
                AccessionNote.accession_id.in_(
                    [j.id for j in accessions])).all()
            # extend results with things not further used
            result.extend(locations)
            result.extend(plants)
            result.extend(plantnotes)
        elif self._choices['based_on'] == 'accessions':
            accessions = self.session.query(Accession).order_by(
                Accession.code).all()
            accessionnotes = self.session.query(AccessionNote).all()

        ## now the taxonomy, based either on all species or on the ones used
        if self._choices['based_on'] == 'taxa':
            species = self.session.query(Species).order_by(
                Species.sp).all()
        else:
            # prepend results with accession data
            result = accessions + accessionnotes + result

            species = self.session.query(Species).filter(
                Species.id.in_([j.species_id for j in accessions])).order_by(
                Species.sp).all()

        ## and all used genera and families
        genera = self.session.query(Genus).filter(
            Genus.id.in_([j.genus_id for j in species])).order_by(
            Genus.genus).all()
        families = self.session.query(Familia).filter(
            Familia.id.in_([j.family_id for j in genera])).order_by(
            Familia.family).all()

        ## prepend the result with the taxonomic information
        result = families + genera + species + result

        ## done, return the result
        return result


class JSONImporter(object):
    '''The import process will be queued as a bauble task. there is no callback
    informing whether it is successfully completed or not.

    the Presenter ((M)VP)
    '''

    def __init__(self):
        super(JSONImporter, self).__init__()
        self.__error = False   # flag to indicate error on import
        self.__cancel = False  # flag to cancel importing
        self.__pause = False   # flag to pause importing
        self.__error_exc = False
        self.create = True     # should be an option

    def start(self, filenames=None):
        if filenames is None:
            d = gtk.FileChooserDialog(
                _("Choose a file to import from..."), None,
                gtk.FILE_CHOOSER_ACTION_SAVE,
                (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
                 gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
            response = d.run()
            filename = d.get_filename()
            d.destroy()
            if response != gtk.RESPONSE_ACCEPT or filename is None:
                return
            filenames = [filename]
        objects = [json.load(open(fn)) for fn in filenames]
        a = []
        for i in objects:
            if isinstance(i, list):
                a.extend(i)
            else:
                a.append(i)
        bauble.task.queue(self.run(a))

    def run(self, objects):
        ## generator function. will be run as a task.
        session = db.Session()
        n = len(objects)
        for i, obj in enumerate(objects):
            try:
                db.construct_from_dict(session, obj, self.create)
            except Exception as e:
                logger.warning("could not import %s (%s: %s)" %
                               (obj, type(e).__name__, e.args))
            pb_set_fraction(float(i) / n)
            yield
        session.commit()


class JSONExporter(object):
    '''Export taxonomy and plants in JSON format.

    the Presenter ((M)VP)'''

    def __init__(self, view):
        self.view = view

    def start(self, filename=None, objects=None):
        "interact with user to establish what to do"
        if filename is None:  # need user intervention
            response = gtk.RESPONSE_NONE
            while response != gtk.RESPONSE_OK:
                response = self.view.start()
                if response in[gtk.RESPONSE_CANCEL, gtk.RESPONSE_DELETE_EVENT]:
                    return
                filename = self.view.get_filename()
                if filename == '':
                    self.view.popup_message(_('Please first choose a file.'))
                    response = gtk.RESPONSE_NONE
            objects = self.view.get_objects()
        logger.debug("will run with filename and objects: %s %s" %
                     (filename, objects))
        self.run(filename, objects)

    def run(self, filename, objects=None):
        "perform the export"
        if filename is None:
            raise ValueError("filename can not be None")

        if os.path.exists(filename) and not os.path.isfile(filename):
            raise ValueError("%s exists and is not a a regular file"
                             % filename)

        # if objects is None then export all objects under classes Familia,
        # Genus, Species, Accession, Plant, Location.
        if objects is None:
            s = db.Session()
            objects = s.query(Familia).all()
            objects.extend(s.query(Genus).all())
            objects.extend(s.query(Species).all())
            objects.extend(s.query(VernacularName).all())
            objects.extend(s.query(Accession).all())
            objects.extend(s.query(Plant).all())
            objects.extend(s.query(Location).all())

        count = len(objects)
        if count > 3000:
            msg = _('You are exporting %(nplants)s objects to JSON format.  '
                    'Exporting this many objects may take several minutes.  '
                    '\n\n<i>Would you like to continue?</i>') \
                % ({'nplants': count})
            if not utils.yes_no_dialog(msg):
                return

        import codecs
        with codecs.open(filename, "wb", "utf-8") as output:
            output.write('[')
            output.write(',\n '.join(
                [json.dumps(obj.as_dict(),
                            default=serializedatetime, sort_keys=True)
                 for obj in objects]))
            output.write(']')


#
# plugin classes
#

class JSONImportTool(pluginmgr.Tool):
    category = _('Import')
    label = _('JSON')

    @classmethod
    def start(cls):
        """
        Start the JSON importer.  This tool will also reinitialize the
        plugins after importing.
        """
        c = JSONImporter()
        c.start()


class JSONExportTool(pluginmgr.Tool):
    category = _('Export')
    label = _('JSON')

    @classmethod
    def start(cls):
        # the presenter uses the view to interact with user then
        # performs the export, if this is the case.
        s = db.Session()
        presenter = JSONExporter(view=ExportToJson(s))
        presenter.start()  # interact && run
        s.close()
