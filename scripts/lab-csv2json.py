#!/usr/bin/python2
# -*- coding: utf-8 -*-
#
# Copyright 2016,2017 Mario Frasca <mario@anche.no>.
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

import csv
import json
import staale
import re

k = []
#header = ['No', 'NOMBRE CIENTIFICO', 'FAMILIA', 'Nombre común', 'Uso Actual y Potencial', 'Importancia ecológica', 'Ecosistema', 'Habito', 'Procedencia']
#header = ['code', 'vernacular', 'binomial', 'dap', 'altura', 'hábito', 'altitud', 'easting', 'northing', 'ecosistema', 'observaciones']
#header = ["Item", "Species", "Fecha registro", "No.Plantas", "Locale", "Contacto", "N° De Autorización de Investigación:", "N° autorización de movilización", "Nombre del recolector", "Latitud", "Longitud"]
#header = ["Numeración", "Condición fitosanitaria", "Notas"]
#header = ['Nombre', 'N°Frascos', 'total', 'int_ppf']
#header = ['ID accesión', 'Nombre', 'var.', 'Ubicación']
#header = ['Item', 'Genero', 'Especie', 'Fecha registro']
header = ['número', 'ubicación', 'fecha', 'species']

# list of formats once data lines are read
sp_format = ',\n{"object": "taxon", "rank": "species", "epithet": "%(sp_epit)s", "ht-rank": "genus", "ht-epithet": "%(gn_epit)s"}'
acc_format = ',\n{"object": "accession", "code": "%(acc_code)s", "species": "%(binomial)s"}'
plt_format = ',\n{"object": "plant", "accession": "%(acc_code)s", "code": "%(plt_code)s", "quantity": "%(plt_qty)s", "location": "%(loc)s"}'
plt_coordinates_format = ',\n {"category": "<UTM>", "note": "easting:%(easting)s;northing:%(northing)s", "object": "plant_note", "plant": "%(acc_code)s.%(plt_code)s"}'
plt_sex_format = ',\n {"category": "sex", "note": "%(sex)s", "object": "plant_note", "plant": "%(acc_code)s.%(plt_code)s"}'

# correspondence header → fields
fields = {
    'plant': 'accession-plant',
    'species': 'binomial',
    'x': 'easting',
    'y': 'northing',
}

#input_file_name = '/tmp/species.csv'
input_file_name = '/home/mario/to-import.csv'

count = skipped = 0

species_collected = set()
old_accessions = set()

subspecies_re = re.compile(r'^(.*) subsp\. ([a-z]*)(.*)$')
varietas_re = re.compile(r'^(.*) var\. ([a-z]*)(.*)$')
forma_re = re.compile(r'^(.*) f\. ([a-z]*)(.*)$')
cultivar_re = re.compile(r"^(.*) '(.*)'(.*)$")
sex_re = re.compile(r'^(.*)\(([fm])\)(.*)$')
previous_accession_code = None

with open("/tmp/out.json", "w") as out:
    out.write('[ {}')
    for line_no, r in enumerate(csv.reader(open(input_file_name))):
        if line_no == 0:
            header = [i.strip() for i in r]
            continue
        obj = dict(zip(header, [i.strip() for i in r]))
        if len(obj) == 1:
            break
        for k1, k2 in fields.items():
            obj[k2] = obj.get(k1)
        for field, expression in [('subspecies', subspecies_re),
                                  ('varietas', varietas_re),
                                  ('forma', forma_re),
                                  ('cultivar', cultivar_re),
                                  ('sex', sex_re)]:
            m = expression.match(obj['binomial'])
            if m:
                obj['binomial'] = m.group(1) + m.group(3)
                obj[field] = m.group(2)
        obj['binomial'] = obj['binomial'].strip()
        if not obj['binomial']:
            obj['binomial'] = 'Zzz sp'
        try:
            obj['gn_epit'], obj['sp_epit'] = obj['binomial'].split(' ')
        except:
            obj['gn_epit'], obj['sp_epit'] = (obj['binomial'], 'sp')
        #obj['acc_code'], obj['plt_code'] = obj.get('accession-plant').split('.')
        obj['acc_code'] = obj.get('accession-plant')
        if obj['acc_code'] == previous_accession_code:
            plant_code += 1
        else:
            plant_code = 1
        obj['plt_code'] = plant_code
        obj['loc'] = 1
        print(obj)
        if obj['binomial'] not in species_collected:
            out.write(sp_format % obj)
            species_collected.add(obj['binomial'])
        if obj['acc_code'] not in old_accessions:
            out.write(acc_format % obj)
        obj['plt_qty'] = 1
        out.write(plt_format % obj)
        if obj.get('x') and obj.get('y'):
            out.write(plt_coordinates_format % obj)
        previous_accession_code = obj['acc_code']
    out.write(']')
