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
header = ['timestamp', 'loc', 'acc_code', 'binomial']

# list of formats once data lines are read
sp_format = ',\n{"object": "taxon", "rank": "species", "epithet": "%(sp_epit)s", "ht-rank": "genus", "ht-epithet": "%(gn_epit)s"}'
acc_format = ',\n{"object": "accession", "code": "%(acc_code)s", "species": "%(binomial)s"}'
plt_format = ',\n{"object": "plant", "accession": "%(acc_code)s", "code": "%(plt_code)s", %(plt_qty)s"location": "%(loc)s"}'

input_file_name = '/tmp/searches.txt'

count = skipped = 0

species_collected = set(['Zzz sp'])
old_accessions = set()

with open("/tmp/out.json", "w") as out:
    out.write('[ {}')
    lastloc = None
    for line_no, r in enumerate(csv.reader(open(input_file_name), delimiter=':')):
        obj = dict(zip(header, [i.strip() for i in r]))
        if len(obj) == 1:
            break
        obj.setdefault('binomial', 'Zzz sp')
        try:
            obj['gn_epit'], obj['sp_epit'] = obj['binomial'].split(' ')
        except:
            obj['gn_epit'], obj['sp_epit'] = ('Zzz', 'sp')
        if obj['binomial'] not in species_collected:
            out.write(sp_format % obj)
            species_collected.add(obj['binomial'])
        if obj['acc_code'] not in old_accessions:
            out.write(acc_format % obj)
            obj['plt_qty'] = '"quantity": 1, '
        else:
            obj['plt_qty'] = ''
        if not obj['loc']:
            obj['loc'] = lastloc
        lastloc = obj['loc']
        obj['plt_code'] = 1
        out.write(plt_format % obj)
    out.write(']')
