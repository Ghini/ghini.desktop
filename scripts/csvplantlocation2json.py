#!/usr/bin/python
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

# This is just yet another example. The given input was of such a simple
# format that it felt excessive, adapting the generic script to handle it.

import csv
import json

header = ["Numeración", "Condición fitosanitaria", "Notas"]
input_file_name = '/tmp/plants.csv'

result = []

for r in csv.reader(open(input_file_name)):
    obj = dict(list(zip(header, [i.strip() for i in r])))
    code = obj['Numeración']
    plant = {"accession": code, "code": "1", "location": "INV4", "object": "plant"}
    if obj['Condición fitosanitaria'] == 'Muerta':
        plant['quantity'] = 0
    result.append(plant)

formatted_json = [json.dumps(plant) for plant in result]

with open("/tmp/out.json", "w") as out:
    out.write('[\n ')
    out.write(',\n '.join(formatted_json))
    out.write(']')
    
