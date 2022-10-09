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
#
# This file is a first start for importing data from your ODK aggregator.
#
# You invoke this temporary script from the command line, it reads your
# connection configuration from a 'settings.json' file in the same scripts
# directory.
#
# Data from the ODK aggregator is written to the database, inconditionally.
#

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

consoleHandler = logging.StreamHandler()
logging.getLogger().addHandler(consoleHandler)
consoleHandler.setLevel(logging.DEBUG)
logging.getLogger().setLevel(logging.DEBUG)

from bauble.plugins.garden.aggregateclient import get_submissions, get_image
import os.path
import datetime
import json
import codecs
import os
import uuid

import bauble.db
import bauble.utils

from bauble.plugins.garden import Location
from bauble.plugins.garden import Plant
from bauble.plugins.garden import Accession
from bauble.plugins.plants import Species
from bauble.plugins.plants import Genus


def get_genus(session, keys):
    try:
        keys['gn_epit'], keys['sp_epit'] = keys['species'].split(' ')
    except:
        keys['gn_epit'], keys['sp_epit'] = ('Zzz', 'sp')

    genus = session.query(Genus).filter(Genus.epithet == keys['gn_epit']).one()
    return genus


def get_species(session, keys):
    if keys['sp_epit'] == 'sp':
        keys['infrasp1'], keys['sp_epit'] = 'sp', ''
    else:
        keys['infrasp1'] = ''

    if keys['sp_epit'] == 'sp':
        try:
            species = session.query(Species).filter(
                Species.genus == genus).filter(
                Species.infrasp1 == 'sp').one()
            if species != zzz:  # no hace falta mencionarlo
                sys.stdout.write('+')  # encontramos
        except:
            species = Species(genus=genus, sp='', infrasp1='sp')
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
            species = Species(genus=genus, sp='', epithet=keys['sp_epit'])
            session.add(species)
            session.flush()
            sys.stdout.write('*')  # tuvimos que crear
    return species


def get_location(session, keys):
    try:
        loc = session.query(Location).filter(bauble.utils.ilike(Location.code, str(keys['location']))).one()
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

# avoid querying already seen submitted forms: 'to_skip' is a list of uuids.

try:
    with open(os.path.join(path, 'odk-seen.json'), 'r') as f:
        to_skip = json.load(f)
except:
    to_skip = []

# get submissions from all known form definitions

r = get_submissions(user, pw, 'ghini-collect.appspot.com', 'plant_form_r', to_skip)
s = get_submissions(user, pw, 'ghini-collect.appspot.com', 'plant_form_s', to_skip)
items = r + s

objects = []
species_needed = {}
locations_needed = {}

bauble.db.open(dburi, True, True)
session = bauble.db.Session()

# loop over the submissions, sorted by accession number
for item in sorted(items, key=lambda x: x['acc_no_scan'] or x['acc_no_typed']):

    # each submission is either altering or adding an accession and a plant.
    # If these objects are not in the session, we should first add them.
    # Next we can and alter them, according to the submitted form.

    # A submission can additionally refer to a location and a species, both
    # of which might be in the session, or not.  It's not the idea that we
    # alter existing locations and species, but we might need adding them to
    # the session.  Ghini should know that these objects have been added
    # automatically.

    # keep track of seen submissions, do not retrieve twice.
    to_skip.append(item['meta:uuid'])

    accession = {"object": "accession"}
    plant = {"object": "plant", "code": "1"}
    accession['code'] = item['acc_no_scan'] or item['acc_no_typed']
    if not accession['code']:
        logger.warn("can't handle submission %s without accession code" % str(item))
        continue
    # if the plant code contains a plant code, separate it from accession code.
    plant['accession'] = accession['code']
    if item['location']:
        # case insensitive match on location code (use bauble.utils.ilike).
        db_loc = session.query(Location).filter(bauble.utils.ilike(Location.code, str(item['location']))).first()
        if db_loc:
            plant['location'] = db_loc.code
        else:
            plant['location'] = item['location'].upper()
            locations_needed[plant['location']] = {'object': 'location', 'code': plant['location']}

    if item['species']:
        # TODO: retrieve species from session, or add one to it.
        item['species'] = item['species'].replace('.', '')

        genus_epithet, species_epithet = (str(item['species']).split(' ') + [''])[:2]
        if species_epithet == '':
            species_epithet = 'sp'

        accession['species'] = item['species'] = "%s %s" % (genus_epithet, species_epithet)

    # add a default quantity=1 for plants relative to new accessions,
    # add a default species=Zzz sp for new accessions,
    # ignore species=Zzz sp for already existing accessions.
    need_species = False
    db_accession = session.query(Accession).filter(Accession.code == str(accession['code'])).first()

    if db_accession is None:  # this is a new accession
        plant['quantity'] = 1
        item['species'] = item.get('species') or 'Zzz sp'
        accession['species'] = item['species']
        genus_epithet, species_epithet = (str(item['species']).split(' ') + [''])[:2]
        need_species = True

    else:                     # this is an existing accession
        # if not specifying species or this species is already set, don't alter anything.
        if not item['species'] or db_accession.species.str(remove_zws=True) == item['species']:
            accession = {}

    if item['species']:
        db_genus = session.query(Genus).filter(Genus.epithet == genus_epithet).first()
        if db_genus is None:
            logger.debug("com'è possibile? %s" % item['species'])
        else:
            db_species = session.query(Species).filter(
                Species.genus_id == db_genus.id).filter(
                Species.epithet == species_epithet).first()
            if db_species is None:
                species = {'object': 'taxon',
                           'rank': 'species', 'epithet': species_epithet,
                           'ht-rank': 'genus', 'ht-epithet': genus_epithet, }
                species_needed[(genus_epithet, species_epithet)] = species

    # needed for plant_notes and the change object
    author = imei2user[item['deviceid']]
    timestamp = datetime.datetime.strptime(item['end'][:19], '%Y-%m-%dT%H:%M:%S')

    # should do something with alive or dead status (put quantity to zero).
    if item.get('alive', '1') == '0':
        plant['quantity'] = '0'

    if accession:
        objects.append(accession)
    objects.append(plant)

    # should import pictures:
    for pic_name in item.get('photo', []):
        try:
            url, md5 = item['media'][pic_name]
        except Exception as e:
            print((type(e), e))
            continue
        pic_name = (item['acc_no_scan'] or item['acc_no_typed']) + ' ' + pic_name
        pic_full_name = os.path.join(pic_path, pic_name)
        get_image(user, pw, url, pic_full_name)
        note = {'object': 'plant_note', 'plant': '%(accession)s.%(code)s' % plant, 'category': '<picture>', 'note': pic_name}
        objects.append(note)

    # should import notes
    pass

    # should create a change object, just like the Accession Editor
    pass

for i in list(species_needed.values()) + list(locations_needed.values()):
    objects.insert(0, i)

with codecs.open(filename, "wb", "utf-8") as output:
    output.write('[')
    output.write(',\n '.join(
        [json.dumps(obj, sort_keys=True)
         for obj in objects]))
    output.write(']')

with open(os.path.join(path, 'odk-seen.json'), 'w') as output:
    output.write('[')
    output.write(',\n '.join(
        [json.dumps(obj) for obj in to_skip]))
    output.write(']')
