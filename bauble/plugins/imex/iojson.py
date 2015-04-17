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
from json import load, dump
import bauble.utils as utils
import bauble.db as db
from bauble.plugins.plants import Family, Genus, Species
from bauble.plugins.garden.plant import Plant
from bauble.plugins.garden.accession import Accession
from bauble.plugins.garden.location import Location
import bauble.task
import json


def serializedatetime(obj):
    """Default JSON serializer."""
    import calendar, datetime

    if isinstance(obj, (Family, Genus, Species)):
        return str(obj)
    elif isinstance(obj, datetime.datetime):
        if obj.utcoffset() is not None:
            obj = obj - obj.utcoffset()
    millis = int(
        calendar.timegm(obj.timetuple()) * 1000 +
        obj.microsecond / 1000
    )
    return {'__class__': 'datetime', 'millis': millis}


def saobj2dict(obj):
    def process_field(i):
        'remove trailing _id from field names'

        if i.endswith('_id'):
            return i[:-3]
        return i

    result = dict((col, getattr(obj, col)) 
                  for col in [process_field(i) 
                              for i in obj.__table__.columns.keys()
                              if i != 'id' and i[0] != '_']
                  if getattr(obj, col) is not None)
    result['__class__'] = obj.__class__.__name__
    return result


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

    def start(self, filenames, force=None):
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
            klass = globals()[i['__class__']]
            del i['__class__']
            obj = klass.retrieve_or_create(s, i)
            s.add(obj)
            yield
        s.commit()


class JSONExporter(object):
    "Export taxonomy and plants in JSON format."

    def start(self, filename=None, objects=None):
        if filename is None: # no filename, ask the user
            d = gtk.FileChooserDialog(_("Choose a file to export to..."), None,
                                      gtk.FILE_CHOOSER_ACTION_SAVE,
                                      (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
                                       gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
            response = d.run()
            filename = d.get_filename()
            d.destroy()
            if response != gtk.RESPONSE_ACCEPT or filename == None:
                return
        self.run(filename, objects)


    def run(self, filename, objects=None):
        if filename == None:
            raise ValueError("filename can not be None")

        if os.path.exists(filename) and not os.path.isfile(filename):
            raise ValueError("%s exists and is not a a regular file" \
                                 % filename)

        # if objects is None then export all objects under classes Family,
        # Genus, Species, Accession, Plant, Location.
        if objects == None:
            s = db.Session()
            objects = s.query(Family).all()
            objects.extend(s.query(Genus).all())
            objects.extend(s.query(Species).all())
            objects.extend(s.query(Accession).all())
            objects.extend(s.query(Plant).all())
            objects.extend(s.query(Location).all())

        count = len(objects)
        if count > 3000:
            msg = _('You are exporting %(nplants)s objects to JSON format.  ' \
                    'Exporting this many objects may take several minutes.  '\
                    '\n\n<i>Would you like to continue?</i>') \
                    % ({'nplants': count})
            if not utils.yes_no_dialog(msg):
                return

        import codecs
        with codecs.open(filename, "wb", "utf-8") as output:
            dump([saobj2dict(obj) for obj in objects], output, 
                 default=serializedatetime, sort_keys=True, indent=4)
