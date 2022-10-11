#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2017 Mario Frasca <mario@anche.no>.
# Copyright 2017 Jardín Botánico de Quito
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

from bauble.plugins.garden import Plant
from bauble.plugins.garden import Accession
from bauble.plugins.plants import Species
from bauble.plugins.plants import Genus

bauble.db.open(dburi, True, True)
session = bauble.db.Session()

q = session.query(Species).filter(Species.infrasp1 == 'sp')
q = q.join(Genus).filter(Genus.epithet == 'Zzz')
zzz = q.one()

q = session.query(Species).filter(Species.epithet == 'sp')
q = q.join(Genus).filter(Genus.epithet == 'Zzz')
zzzsp = q.one()

import sys
conflicting = {}
unknown = []

import fileinput, re
for line in fileinput.input():
    sys.stdout.flush()
    text = str(line.strip())
    if not text:
        continue  # skip any empty lines

    try:
        genus_name, location = re.split('[ ,]+', text)
    except:
        genus_name = location = None

    if genus_name:
        genus = session.query(Genus).filter(Genus.epithet == genus_name).one()
        try:
            species = session.query(Species).filter(Species.genus == genus).filter(Species.infrasp1 == 'sp').first()
            if species is None:
                raise Exception
            sys.stdout.write('+')
        except:
            species = Species(genus=genus, sp='', infrasp1='sp')
            session.add(species)
            sys.stdout.write('*')
            session.flush()
        continue  # we used the line, let's continue with the accession codes

    # `species` is the fictive identification for all following acc. codes.

    try:
        accession = session.query(Accession).filter(Accession.code == text).one()
    except:
        unknown.append(text)
        sys.stdout.write('?')
        continue

    if accession.species in [zzz, zzzsp]:
        accession.species = species
        sys.stdout.write(':')
        session.flush()
    elif accession.species == species:
        sys.stdout.write('.')
    else:
        conflicting.setdefault(species.str(), []).append((accession.code, accession.species.str()))
        sys.stdout.write('!')

print()
session.commit()
print(conflicting)
print(unknown)
