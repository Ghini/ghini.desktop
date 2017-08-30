#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2004-2010 Brett Adams <brett@bauble.io>
# Copyright 2015 Mario Frasca <mario@anche.no>.
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

import bauble.plugins.garden.aggregateclient
import os.path
import datetime
import json
import codecs

import os
path = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(path, 'settings.json'), 'r') as f:
    user, pw, filename, imei2user = json.load(f)

r = bauble.plugins.garden.aggregateclient.get_submissions(user, pw, 'ghini-collect.appspot.com', 'plant_form_r')
objects = []

for item in r:
    accession = {"object": "accession"}
    plant = {"object": "plant", "code": "1"}
    accession['code'] = item['acc_no_scan'] or item['acc_no_typed']
    plant['accession'] = accession['code']
    if item['location']:
        plant['location'] = item['location']
    if item['species']:
        accession['species'] = item['species']
    # should create a change object, just like the Accession Editor:
    if True:
        author = imei2user[item['deviceid']]
        timestamp = datetime.datetime.strptime(item['end'][:19], '%Y-%m-%dT%H:%M:%S')
        if author != 'Denisse':
            logger.info("skipping user %s" % author)
            continue
    # should import pictures:
    if False:
        for p in item['photo']:
            url, md5 = r[0]['media'][i]
            path = os.path.join('home', 'mario', 'tmp', 'PlantPictures', p)
            bauble.plugins.garden.aggregateclient.get_image(user, pw, url, path)
    objects.append(accession)
    objects.append(plant)

with codecs.open(filename, "wb", "utf-8") as output:
    output.write('[')
    output.write(',\n '.join(
        [json.dumps(obj, sort_keys=True)
         for obj in objects]))
    output.write(']')
