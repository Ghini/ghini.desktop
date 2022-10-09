#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright 2016,2017 Mario Frasca <mario@anche.no>.
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

import csv
import json
from . import staale

k = []
#header = ['No', 'NOMBRE CIENTIFICO', 'FAMILIA', 'Nombre común', 'Uso Actual y Potencial', 'Importancia ecológica', 'Ecosistema', 'Habito', 'Procedencia']
#header = ['code', 'vernacular', 'binomial', 'dap', 'altura', 'hábito', 'altitud', 'easting', 'northing', 'ecosistema', 'observaciones']
header = ["Item", "Species", "Fecha registro", "No.Plantas", "Locale", "Contacto", "N° De Autorización de Investigación:", "N° autorización de movilización", "Nombre del recolector", "Latitud", "Longitud"]
#header = ["Numeración", "Condición fitosanitaria", "Notas"]

note_defs = {
    'species': [
        {'key': 'Uso Actual y Potencial', 'category': 'use'},
        {'key': 'Importancia ecológica', 'category': 'relevance'},
        {'key': 'Ecosistema', 'category': 'ecosystem'},
        {'key': 'ecosistema', 'category': 'ecosystem'},
    ],
    'plant': [
        {'key': 'Condición fitosanitaria', 'category': 'state'},
#        {'key': 'observaciones', 'category': 'generic'},
#        {'key': 'dap', 'category': '{dap:2016-11}'},
#        {'key': 'altura', 'category': '{alt:2016-11}'},
    ],
}

formatted_note_defs = {
#    'plant': [ {'keys': [], 'value': "%(lat)s\t%(lon)s", 'category': '{coords}'}, ],
}

class_fields = {
    'species': {'key': 'Uso Actual y Potencial', 'category': 'use'},
}

binomial_key = 'Species'
habit_key = None
origin_key = None
easting_key, northing_key, altitude_key = None, None, None
utm_slice = None
plant_quantity_key = 'No.Plantas'

accession_code_def = "%(code)06d"

vernacular_keys = [
#    {'key': 'vernacular', 'lang': 'es'},
]


#input_file_name = '/tmp/species.csv'
input_file_name = '/tmp/plants.csv'

count = skipped = 0

species = {}
species_notes = {}

import re
binomial_with_authorship = re.compile(r'^([A-Z][a-z]+) (?:(cf|aff|cf\.|aff\.|\?) )?(×[ ]?)?([-a-z]+|sp\.?[ ]?[1-9]?)(?: (.*[A-Z].*))?( \?)?$')

family_hidden = []  # [vernacular_key, binomial_key]
family_name = re.compile(r'^[A-Z][a-z]*aceae$')

for r in csv.reader(open(input_file_name)):
    obj = dict(list(zip(header, [i.strip() for i in r])))
    for key in family_hidden:
        obj['family'] = ''
        if family_name.match(obj[key]):
            obj['family'] = obj[key]
            obj[key] = ''
            break
    if obj[binomial_key]:
        count += 1
        try:
            m = binomial_with_authorship.match(obj[binomial_key]).groups()
            obj['genus'], obj['qual'], obj['hybrid_flag'], obj['species-epithet'], obj['authorship'], obj['qual.2'] = m
        except:
            continue
    else:
        skipped += 1
        continue
    if easting_key in obj and northing_key in obj:
        if utm_slice:
            obj['lat'], obj['lon'] = staale.utm_to_latlon(utm_slice, float(obj[easting_key]), float(obj[northing_key]))
        else:
            obj['lat'], obj['lon'] = float(obj[northing_key]), float(obj[easting_key])
    k.append(obj)

print((count, skipped))

# first produce the taxomomy

for obj in k:
    sp_id = (obj['genus'], obj['species-epithet'], obj['authorship'])
    species[sp_id] = obj
    species_notes[sp_id] = []
    for d in note_defs['species']:
        if obj[d['key']]:
            for value in obj[d['key']].split('-'):
                species_notes[sp_id].append({"object": "species_note",
                                             "species": "%(genus)s %(species-epithet)s" % obj,
                                             'category': d['category'],
                                             'note': value.lower()})

result = []

for sp_id in sorted(species.keys()):
    orig = species[sp_id]
    obj = {'family': orig.get('family', ''),
           'ht-epithet': orig['genus'], 
           'epithet': orig['species-epithet'], 
           'author': orig['authorship'],
           'hybrid_flag': orig['hybrid_flag']}
    for key in ['hybrid_flag', 'family', 'author']:
        if key in orig and not orig[key]:
            del obj[key]
    obj['object'] = 'taxon'
    obj['rank'] = 'species'
    obj['ht-rank'] = 'genus'
    result.append(obj)
    for vernacular_def in vernacular_keys:
        if orig.get(vernacular_def['key']):
            result.append({'object': 'vernacular_name',
                           'species': "%(genus)s %(species-epithet)s" % orig,
                           'name': orig[vernacular_def['key']],
                           'language': vernacular_def['lang'],
                       })
    result.extend(species_notes[(orig['genus'], orig['species-epithet'], orig['authorship'])])

# now just a single fake location

location = {"code": "000", "description": "", "name": "lot 1", "object": "location"}
result.append(location)

def make_accession_code(obj):
    def smart_int(v):
        try:
            return int(v)
        except:
            return 0
    obj = dict((k, smart_int(v)) for (k, v) in list(obj.items()))
    return accession_code_def % obj

# now accessions, plants, and relative notes.

for obj in k:
    code = make_accession_code(obj)
    location_id = obj.get(location_key, '000')
    accession = {"code": code, "object": "accession", "species": "%(genus)s %(species-epithet)s" % obj}
    result.append(accession)
    plant = {"acc_type": "Plant", "accession": code, "code": "1", "location": location_id, "object": "plant", "quantity": 1}
    result.append(plant)
    for note_def in note_defs['plant']:
        pass
    if height_key in obj:
        note = {"category": "{alt:2016-11}", "note": obj['altura'], "object": "plant_note", "plant": code + ".1"}
        result.append(note)
    if dbh_key in obj:
        note = {"category": dbh_category, "note": obj[dbh_key], "object": "plant_note", "plant": code + ".1" % obj}
        result.append(note)
    if easting_key in obj and northing_key in obj:
        note =  {"category": "<coords>", "note": "%(lat)s\t%(lon)s" % obj, "object": "plant_note", "plant": code + ".1" % obj}
        result.append(note)

        
formatted_json = []

for i in result:
    formatted_json.append(' ' + json.dumps(i))

with open("/tmp/out.json", "w") as out:
    out.write('[\n ')
    out.write(',\n '.join(formatted_json))
    out.write(']')
