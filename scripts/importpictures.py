#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2017 Mario Frasca <mario@anche.no>.
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

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

consoleHandler = logging.StreamHandler()
logging.getLogger().addHandler(consoleHandler)
consoleHandler.setLevel(logging.DEBUG)
logging.getLogger().setLevel(logging.DEBUG)

import os.path
path = os.path.dirname(os.path.realpath(__file__))

import json

with open(os.path.join(path, 'settings.json'), 'r') as f:
    (user, pw, filename, imei2user, dburi, pic_path) = json.load(f)

import bauble.db
import bauble.utils

from bauble.plugins.garden import Location
from bauble.plugins.garden import Plant, PlantNote
from bauble.plugins.garden import Accession
from bauble.plugins.plants import Species
from bauble.plugins.plants import Genus

bauble.db.open(dburi, True, True)
session = bauble.db.Session()

q = session.query(Species).filter(Species.infrasp1 == u'sp')
q = q.join(Genus).filter(Genus.epithet == u'Zzz')
zzz = q.one()

loc = session.query(Location).filter(Location.code == u'desconocid').one()
import sys

with open("/tmp/plant-pictures.txt") as f:
    for text in f.readlines():
        text = unicode(text.strip())
        acc_no = text[:6]
        
        q = session.query(Plant)
        q = q.join(Accession).filter(Accession.code == acc_no)
        if q.count() == 0:
            # we need to add accession and plant first.
            try:
                accession = session.query(Accession).filter(Accession.code == acc_no).one()
            except:
                accession = Accession(species=zzz, code=acc_no)
                session.add(accession)
                sys.stdout.write('a')
            plant = Plant(accession=accession, location=loc, quantity=1, code=u'1')
            session.add(plant)
            sys.stdout.write('p')
            session.flush()
        else:
            plant = q.first()

        # `plant` is the object to receive pictures, and it is in the session.

        q = session.query(Plant)
        q = q.join(Accession).filter(Accession.code == acc_no)
        q = q.join(PlantNote).filter(PlantNote.category == u'<picture>')
        q = q.filter(PlantNote.note == text)
        if q.count() == 0:
            # we need to add this note to the plant
            note = PlantNote(plant=plant, category=u'<picture>', note=text)
            session.add(note)
            sys.stdout.write('f')
        else:
            sys.stdout.write('.')
        sys.stdout.flush()
session.commit()
print
