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
from bauble.i18n import _
import bauble.utils as utils
import bauble.db as db
from bauble.plugins.plants import Familia, Genus, Species
from bauble.plugins.garden.plant import Plant
from bauble.plugins.garden.accession import Accession
from bauble.plugins.garden.location import Location
import bauble.task
import bauble.editor as editor
import bauble.paths as paths
import json
import bauble.pluginmgr as pluginmgr


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

    def __init__(self, parent=None):
        filename = os.path.join(paths.lib_dir(), 'plugins', 'imex',
                                'select_export.glade')
        super(ExportToJson, self).__init__(filename, parent=parent)

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

    def start(self, filenames):
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
        for i in objects:
            ## get class and remove reference
            try:
                klass = globals()[i['object'].capitalize()]
            except KeyError:
                klass = globals()[i['rank'].capitalize()]
                del i['rank']
            klass.retrieve_or_create(s, i)  # adds, too
            yield
        s.commit()


class JSONExporter(object):
    "Export taxonomy and plants in JSON format."

    def start(self, filename=None, objects=None):
        if filename is None or objects is None:  # need user intervention
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
