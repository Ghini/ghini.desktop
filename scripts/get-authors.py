#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2012-2015 Mario Frasca <mario@anche.no>.
#
# This file is part of bauble.classic.
#
# bauble.classic is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# bauble.classic is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bauble.classic. If not, see <http://www.gnu.org/licenses/>.

# tropicos-to-json is a filter.
#
# pass it a json export (piping, or giving the name as parameter). the json
# file should contain species for which you miss the author, this script
# will query tropicos and generate a json file for the same species, but
# with authorship. pipe the output to a different json file.

from __future__ import print_function

import sys
import json
import fileinput

import gettropicos

result = []
json_to_import = "\n".join(fileinput.input())
values = json.loads(json_to_import)
for i in values:
    query = i['ht-epithet'] + ' ' + i['epithet']
    sys.stderr.write("querying tropicos for %s ... " % query)
    i = gettropicos.getTropicos(query)
    if i['FullNameWithAuthors'] == '':
        sys.stderr.write("can't find it.\n")
        continue
    author = i['FullNameWithAuthors'][len(i['Query']) + 1:]
    if author.find(')') != -1:
        author = author[author.find(')') + 2:]
    obj = {'genus': i['Query'].split()[0],
           'species': i['Query'].split()[1],
           'author': author
           }
    result.append('{"object": "taxon", "ht-epithet": "%(genus)s", '
                  '"epithet": "%(species)s", "author": "%(author)s", '
                  '"ht-rank": "genus", "rank": "species"}' % obj)
    sys.stderr.write('ok\n')

print("[" + ",\n  ".join(result) + "]")
