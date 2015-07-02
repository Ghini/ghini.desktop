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
from bauble.plugins.plants import Familia, Genus, Species, VernacularName
from bauble.plugins.garden.plant import Plant
from bauble.plugins.garden.accession import Accession, AccessionNote
from bauble.plugins.garden.location import Location
import bauble.task
import bauble.editor as editor
import bauble.paths as paths
import json
import bauble.pluginmgr as pluginmgr
from bauble import pb_set_fraction


def class_of_object(o):
    """what class implements object o

    >>> class_of_object("genus")
    <class 'bauble.plugins.plants.genus.Genus'>
    >>> class_of_object("accession_note")
    <class 'bauble.plugins.garden.accession.AccessionNote'>
    >>> class_of_object("not_existing")
    >>>
    """

    name = ''.join(p.capitalize() for p in o.split('_'))
    return globals().get(name)


def serializedatetime(obj):
    """Default JSON serializer."""
    import calendar
    import datetime

    if isinstance(obj, (Familia, Genus, Species)):
        return str(obj)
    elif isinstance(obj, datetime.datetime):
        if obj.utcoffset() is not None:
            obj = obj - obj.utcoffset()
    millis = int(
        calendar.timegm(obj.timetuple()) * 1000 +
        obj.microsecond / 1000
    )
    return {'__class__': 'datetime', 'millis': millis}


class ExportToJson(editor.GenericEditorView):

    _tooltips = {}
    _choices = {'based_on': 'selection',
                'includes': 'referred',
                }

    def radio_button_pushed(self, widget, group):
        name = gtk.Buildable.get_name(widget).split('_')[1]
        self._choices[group] = name
        print self._choices

    def __init__(self, parent=None):
        filename = os.path.join(paths.lib_dir(), 'plugins', 'imex',
                                'select_export.glade')
        super(ExportToJson, self).__init__(filename, parent=parent)
        for wn in ['selection', 'taxa', 'accessions', 'plants']:
            self.connect('sbo_' + wn, 'toggled',
                         self.radio_button_pushed, "based_on")
        for wn in ['referred', 'referring']:
            self.connect('ei_' + wn, 'toggled',
                         self.radio_button_pushed, "includes")

    def get_window(self):
        return self.widgets.select_export_dialog

    def start(self):
        return self.get_window().run() == gtk.RESPONSE_OK

    def get_filename(self):
        return self.widgets.filename.get_text()

    def get_objects(self):
        return []


class JSONImporter(object):
    '''The import process will be queued as a bauble task. there is no callback
    informing whether it is successfully completed or not.

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
        s = db.Session()
        n = len(objects)
        for i, obj in enumerate(objects):
            ## get class and remove reference
            klass = None
            if 'object' in obj:
                klass = class_of_object(obj['object'])
            if klass is None and 'rank' in obj:
                klass = globals().get(obj['rank'].capitalize())
                del obj['rank']
            try:
                klass.retrieve_or_create(s, obj, create=self.create)
            except Exception as e:
                logger.warning("could not import %s (%s: %s)" %
                               (obj, type(e).__name__, e.args))
            pb_set_fraction(float(i) / n)
            yield
        s.commit()


class JSONExporter(object):
    "Export taxonomy and plants in JSON format."

    def start(self, filename=None, objects=None):
        if filename is None:  # need user intervention
            d = ExportToJson()
            response = d.start()
            filename = d.get_filename()
            objects = d.get_objects()
            if response != gtk.RESPONSE_OK or filename is None:
                return
        self.run(filename, objects)

    def run(self, filename, objects=None):
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
            json.dump([obj.as_dict() for obj in objects], output,
                      default=serializedatetime, sort_keys=True, indent=4)


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
        c = JSONExporter()
        c.start()
