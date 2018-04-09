#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2018 Mario Frasca <mario@anche.no>.
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
# implements the desktop→web (d2w) data stream
#
# You invoke this temporary script from the command line, it reads your
# connection configuration from a 'settings.json' file in the same scripts
# directory.
#

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

consoleHandler = logging.StreamHandler()
logging.getLogger().addHandler(consoleHandler)
consoleHandler.setLevel(logging.DEBUG)
logging.getLogger().setLevel(logging.DEBUG)

import os.path
import datetime
import json
import codecs
import os
import uuid
import math

import bauble.db
import bauble.utils

from bauble.plugins.garden import Institution
from bauble.plugins.garden import Location
from bauble.plugins.garden import Plant
from bauble.plugins.garden import Accession
from bauble.plugins.plants import Species
from bauble.plugins.plants import Genus


def shorten(x):
    import re
    x = x.lower()  # ignore case
    x = x.replace('-', '')  # remove hyphen
    x = re.sub('c([ie])', r'z\1', x)  # palatal c sounds like z
    x = re.sub('g([ie])', r'j\1', x)  # palatal g sounds like j
    x = x.replace('ph', 'f')  # ph sounds like f
    x = x.replace('v', 'f')  # v sounds like f // fricative (voiced or not)
    x = x.replace('h', '')  # h sounds like nothing
    x = re.sub('[gcq]', 'k', x)  # g, c, q sound like k // guttural
    x = re.sub('[xz]', 's', x)  # x, z sound like s
    x = x.replace('ae', 'e')  # ae sounds like e
    x = re.sub('[ye]', 'i', x)  # y, e sound like i
    x = re.sub('[ou]', 'u', x)  # o, u sound like u // so we only have a, i, u
    x = re.sub(r'(.)\1', r'\1', x)  # doubled letters sound like single
    return x;


def get_genus(session, keys):
    try:
        keys['gn_epit'], keys['sp_epit'] = keys['species'].split(' ')
    except:
        keys['gn_epit'], keys['sp_epit'] = (u'Zzz', u'sp')

    genus = session.query(Genus).filter(Genus.epithet == keys['gn_epit']).one()
    return genus


def get_species(session, keys):
    if keys['sp_epit'] == u'sp':
        keys['infrasp1'], keys['sp_epit'] = u'sp', u''
    else:
        keys['infrasp1'] = u''

    if keys['sp_epit'] == u'sp':
        try:
            species = session.query(Species).filter(
                Species.genus == genus).filter(
                Species.infrasp1 == u'sp').one()
            if species != zzz:  # no hace falta mencionarlo
                sys.stdout.write('+')  # encontramos
        except:
            species = Species(genus=genus, sp=u'', infrasp1=u'sp')
            session.add(species)
            session.flush()
            sys.stdout.write('*')  # tuvimos que crear
    else:
        try:
            species = session.query(Species).filter(
                Species.genus == genus).filter(
                Species.epithet == keys['sp_epit']).one()
            sys.stdout.write('+')  # encontramos
        except:
            species = Species(genus=genus, sp=u'', epithet=keys['sp_epit'])
            session.add(species)
            session.flush()
            sys.stdout.write('*')  # tuvimos que crear
    return species


def get_location(session, keys):
    try:
        loc = session.query(Location).filter(bauble.utils.ilike(Location.code, unicode(keys['location']))).one()
    except:
        loc = Location(code=keys['location'].upper())
        session.add(loc)
        session.flush()
    return loc


# allow user invoke this script from any location

path = os.path.dirname(os.path.realpath(__file__))

# read settings from file

with open(os.path.join(path, 'settings.json'), 'r') as f:
    (user, pw, filename, imei2user, dburi, pic_path) = json.load(f)

bauble.db.open(dburi, True, True)
session = bauble.db.Session()

result = []

insti = Institution()
d = {'name': insti.name,
     'lat': float(insti.geo_latitude),
     'lon': float(insti.geo_longitude),
     'zoom': int(26 - (math.log(float(insti.geo_diameter)) / math.log(2))),
     'uuid': insti.uuid,
}
contact = insti.contact or insti.technical_contact
if contact:
    d['contact'] = contact
if insti.email:
    d['email'] = insti.email
if insti.tel:
    d['phone'] = insti.tel
result.append(d)

species = {}

for i in session.query(Plant).all():
    if i.accession.private:
        continue
    try:
        if not isinstance(i.coords, dict):
            continue
    except:
        continue

    s = i.accession.species
    try:
        vernacular = s.default_vernacular_name.name
    except:
        vernacular = ''
    species.setdefault((s.str(authors=False, markup=False, remove_zws=True),
                        s.sp_author,
                        s.genus.family.epithet,
                        vernacular), []).append(i)

for k in species:
    d = {'name': k[0],
         'family': k[2],
         'phonetic': shorten(k[0])}
    if k[1]:
        d['authorship'] = k[1]
    if k[3]:
        d['vernacular'] = k[3]

    result.append(d)

for k, plants in species.items():
    for v in plants:
        p = {'species': k[0],
             'garden': insti.name,
             'code': v.accession.code + '.' + v.code,
             'lat': v.coords['lat'],
             'lon': v.coords['lon']}
        result.append(p)

print json.dumps(result)
