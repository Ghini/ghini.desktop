#!/usr/bin/python
# -*- coding: utf-8 -*-

import csv
import json
import staale

k = []
header = ['code', 'vernacular', 'binomial', 'dap', 'altura', 'hábito', 'altitud', 'easting', 'northing', 'ecosistema', 'observaciones']

second = set()
count = skipped = 0

species = set()

import re
binomial_with_authorship = re.compile(r'^([A-Z][a-z]+) (?:(cf|aff|cf\.|aff\.|\?) )?([-a-z]+|sp\.?[ ]?[1-9]?)(?: (.*[A-Z].*))?( \?)?$')
family_name = re.compile(r'^[A-Z][a-z]*aceae$')

for r in csv.reader(open('/home/mario/Dropbox/SharedWithMario/La Macarena/plants.csv')):
    obj = dict(zip(header, [i.strip() for i in r]))
    second.add((obj['binomial'].split(' ') + [''])[1])
    obj['family'] = ''
    if family_name.match(obj['vernacular']):
        obj['family'] = obj['vernacular']
        obj['vernacular'] = ''
    elif family_name.match(obj['binomial']):
        obj['family'] = obj['binomial']
        obj['binomial'] = ''
    if obj['binomial']:
        count += 1
        try:
            m = binomial_with_authorship.match(obj['binomial']).groups()
            obj['genus'], obj['qual'], obj['species-epithet'], obj['authorship'], obj['qual.2'] = m
        except:
            continue
    else:
        skipped += 1
        continue
    k.append(obj)

print count, skipped

for obj in k:
    species.add((obj.get('family', ''), obj['genus'], obj['species-epithet'], obj['authorship']))

result = []

for obj in sorted(species):
    obj = dict(zip(['family', 'ht-epithet', 'epithet', 'author'], obj))
    if not obj['family']:
        del obj['family']
    if not obj['author']:
        del obj['author']
    obj['object'] = 'taxon'
    obj['rank'] = 'species'
    obj['ht-rank'] = 'genus'
    result.append(obj)

location = {"code": "000", "description": "", "name": "lot 1", "object": "location"}
result.append(location)

for obj in k:
    obj['lat'], obj['lon'] = staale.utm_to_latlon(18, float(obj['easting']), float(obj['northing']))
    accession = {"code": "%(code)s" % obj, "object": "accession", "species": "%(genus)s %(species-epithet)s" % obj}
    result.append(accession)
    plant = {"acc_type": "Plant", "accession": "%(code)s" % obj, "code": "1", "location": "000", "object": "plant", "quantity": 1}
    result.append(plant)
    note = {"category": "{alt:2016-11}", "note": obj['altura'], "object": "plant_note", "plant": "%(code)s.1" % obj}
    result.append(note)
    note = {"category": "{dap:2016-11}", "note": obj['dap'], "object": "plant_note", "plant": "%(code)s.1" % obj}
    result.append(note)
    note =  {"category": "{coords}", "note": "%(lat)s\t%(lon)s" % obj, "object": "plant_note", "plant": "%(code)s.1" % obj}
    result.append(note)

formatted_json = []

for i in result:
    formatted_json.append(' ' + json.dumps(i))

with open("/tmp/out.json", "w") as out:
    out.write('[\n ')
    out.write(',\n '.join(formatted_json))
    out.write(']')
