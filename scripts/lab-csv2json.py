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
import staale

k = []
#header = ['No', 'NOMBRE CIENTIFICO', 'FAMILIA', 'Nombre común', 'Uso Actual y Potencial', 'Importancia ecológica', 'Ecosistema', 'Habito', 'Procedencia']
#header = ['code', 'vernacular', 'binomial', 'dap', 'altura', 'hábito', 'altitud', 'easting', 'northing', 'ecosistema', 'observaciones']
#header = ["Item", "Species", "Fecha registro", "No.Plantas", "Locale", "Contacto", "N° De Autorización de Investigación:", "N° autorización de movilización", "Nombre del recolector", "Latitud", "Longitud"]
#header = ["Numeración", "Condición fitosanitaria", "Notas"]
#header = ['Nombre', 'N°Frascos', 'total', 'int_ppf']
header = ['ID accesión', 'Nombre', 'var.', 'Ubicación']

# list of formats once data lines are read
sp_format = ',\n{"object": "taxon", "rank": "species", "epithet": "%(sp_epit)s", "ht-rank": "genus", "ht-epithet": "%(gn_epit)s"}'
acc_format = ',\n{"object": "accession", "code": "%(acc_code)s", "species": "%(binomial)s"}'
plt_format = ',\n{"object": "plant", "accession": "%(acc_code)s", "code": "%(plt_code)s", "quantity": "%(plt_qty)s", "location": "%(loc)s"}'

# correspondence header → fields
fields = {
    'ID accesión': 'acc_code',
    'Ubicación': 'loc',
    'Nombre': 'binomial'}

#input_file_name = '/tmp/species.csv'
input_file_name = '/home/mario/Documents/JBQ-2017/inv2.csv'

count = skipped = 0

species_collected = set()

with open("/tmp/out.json", "w") as out:
    out.write('[ {}')
    for line_no, r in enumerate(csv.reader(open(input_file_name))):
        if line_no == 0:
            continue
        obj = dict(zip(header, [i.strip() for i in r]))
        if obj['var.']:
            break
        for k1, k2 in fields.items():
            obj[k2] = obj.get(k1)
        if not obj['binomial'].strip():
            obj['binomial'] = 'Zzz sp'
        try:
            obj['gn_epit'], obj['sp_epit'] = obj['binomial'].split(' ')
        except:
            obj['gn_epit'], obj['sp_epit'] = ('Zzz', 'sp')
        if obj['binomial'] not in species_collected:
            out.write(sp_format % obj)
            species_collected.add(obj['binomial'])
        out.write(acc_format % obj)
        obj['plt_code'] = 1
        obj['plt_qty'] = 1
        out.write(plt_format % obj)
    out.write(']')
