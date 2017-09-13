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

import sys

with open("/tmp/genera.txt") as f:
    for text in f.readlines():
        sys.stdout.flush()
        text = unicode(text.strip())
        if not text:
            continue  # skip any empty lines

        try:
            genus_name, location = text.split(',')
            genus = session.query(Genus).filter(Genus.epithet == genus_name).one()
            try:
                species = session.query(Species).filter(Species.infrasp1 == u'sp').one()
                sys.stdout.write('+')
            except:
                species = Species(genus=genus, sp=u'', infrasp1=u'sp')
                session.add(species)
                sys.stdout.write('*')
                session.flush()
            continue  # we used the line, let's continue with the accession codes
        except:
            pass

        # `species` is the fictive identification for all following acc. codes.

        try:
            accession = session.query(Accession).filter(Accession.code == text).one()
        except:
            sys.stdout.write('?')
            continue

        if accession.species == zzz:
            accession.species = species
            sys.stdout.write('.')
        else:
            sys.stdout.write('!')
            
        session.flush()

print
session.commit()
