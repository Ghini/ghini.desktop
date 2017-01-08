#!/usr/bin/python
# -*- coding: utf-8 -*-

import csv
import json
import staale

k = []
#header = ['No', 'NOMBRE CIENTIFICO', 'FAMILIA', 'Nombre común', 'Uso Actual y Potencial', 'Importancia ecológica', 'Ecosistema', 'Habito', 'Procedencia']
header = ['code', 'vernacular', 'binomial', 'dap', 'altura', 'hábito', 'altitud', 'easting', 'northing', 'ecosistema', 'observaciones']

vernacular_key = 'vernacular'
vernacular_lang = 'es'
binomial_key = 'binomial'
habit_key = 'hábito'
origin_key = 'Procedencia'
easting_key, northing_key, altitude_key = 'easting', 'northing', 'altitud'
code_key = 'code'
height_key = 'altura'
dbh_key = 'dap'
dbh_category = "{dap:2016-11}"

note_keys = [
#    {'key': 'Uso Actual y Potencial', 'category': 'use', 'applies_to': 'species'},
#    {'key': 'Importancia ecológica', 'category': 'relevance', 'applies_to': 'species'},
#    {'key': 'Ecosistema', 'category': 'ecosystem', 'applies_to': 'species'},
    {'key': 'ecosistema', 'category': 'ecosystem', 'applies_to': 'species'},
    {'key': 'observaciones', 'category': 'generic', 'applies_to': 'plant'},
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
    obj = dict(zip(header, [i.strip() for i in r]))
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
    if code_key != 'code':
        obj['code'] = obj[code_key]
        del obj[code_key]
    k.append(obj)

print count, skipped

for obj in k:
    sp_id = (obj['genus'], obj['species-epithet'], obj['authorship'])
    species[sp_id] = obj
    species_notes[sp_id] = []
    for d in note_keys:
        if d['applies_to'] == 'species' and obj[d['key']]:
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
    if orig.get(vernacular_key):
        result.append({'object': 'vernacular_name',
                       'species': "%(genus)s %(species-epithet)s" % orig,
                       'name': orig[vernacular_key],
                       'language': vernacular_lang,
                       })
    result.extend(species_notes[(orig['genus'], orig['species-epithet'], orig['authorship'])])

location = {"code": "000", "description": "", "name": "lot 1", "object": "location"}
result.append(location)

def accession_code(obj):
    code = '%(code)s' % obj
    code_len = len(code)
    return "2016.0000"[:-code_len] + code

for obj in k:
    code = accession_code(obj)
    accession = {"code": code, "object": "accession", "species": "%(genus)s %(species-epithet)s" % obj}
    result.append(accession)
    plant = {"acc_type": "Plant", "accession": code, "code": "1", "location": "000", "object": "plant", "quantity": 1}
    result.append(plant)
    if height_key in obj:
        note = {"category": "{alt:2016-11}", "note": obj['altura'], "object": "plant_note", "plant": code + ".1"}
        result.append(note)
    if dbh_key in obj:
        note = {"category": dbh_category, "note": obj[dbh_key], "object": "plant_note", "plant": code + ".1" % obj}
        result.append(note)
    if easting_key in obj and northing_key in obj:
        obj['lat'], obj['lon'] = staale.utm_to_latlon(18, float(obj[easting_key]), float(obj[northing_key]))
        note =  {"category": "{coords}", "note": "%(lat)s\t%(lon)s" % obj, "object": "plant_note", "plant": code + ".1" % obj}
        result.append(note)

        
formatted_json = []

for i in result:
    formatted_json.append(' ' + json.dumps(i))

with open("/tmp/out.json", "w") as out:
    out.write('[\n ')
    out.write(',\n '.join(formatted_json))
    out.write(']')
