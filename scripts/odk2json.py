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

path = os.path.dirname(os.path.realpath(__file__))

with open(os.path.join(path, 'settings.json'), 'r') as f:
    (user, pw, filename, imei2user, dburi, pic_path) = json.load(f)

try:
    with open(os.path.join(path, 'odk-seen.json'), 'r') as f:
        to_skip = json.load(f)
except:
    to_skip = []

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
        # correct location codes according to ILIKE matches,
        db_loc = session.query(Location).filter(bauble.utils.ilike(Location.code, unicode(item['location']))).first()
        if db_loc:
            plant['location'] = db_loc.code
        else:
            plant['location'] = item['location'].upper()
            locations_needed[plant['location']] = {'object': 'location', 'code': plant['location']}
            
    if item['species']:
        item['species'] = item['species'].replace('.', '')

        genus_epithet, species_epithet = (unicode(item['species']).split(u' ') + [u''])[:2]
        if species_epithet == '':
            species_epithet = u'sp'

        accession['species'] = item['species'] = u"%s %s" % (genus_epithet, species_epithet)

    # add a default quantity=1 for plants relative to new accessions,
    # add a default species=Zzz sp for new accessions,
    # ignore species=Zzz sp for already existing accessions.
    need_species = False
    db_accession = session.query(Accession).filter(Accession.code == unicode(accession['code'])).first()

    if db_accession is None:  # this is a new accession
        plant['quantity'] = 1
        item['species'] = item.get('species') or u'Zzz sp'
        accession['species'] = item['species']
        genus_epithet, species_epithet = (unicode(item['species']).split(u' ') + [u''])[:2]
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
        except Exception, e:
            print type(e), e
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

for i in species_needed.values() + locations_needed.values():
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
