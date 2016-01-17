#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2015 Mario Frasca <mario@anche.no>
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
synonym = {}

with open("genus_synonym.txt") as f:
    f.readline()
    spamreader = csv.reader(f, delimiter=',', quotechar='"')
    for syn, gen in spamreader:
        synonym[int(syn)] = int(gen)

family = {}
with open("family.txt") as f:
    f.readline()
    spamreader = csv.reader(f, delimiter=',', quotechar='"')
    for famid, famname in spamreader:
        family[int(famid)] = famname

genus = {}
with open("genus.txt") as f:
    f.readline()
    spamreader = csv.reader(f, delimiter=',', quotechar='"')
    for genid, name, author, famid in spamreader:
        genid = int(genid)
        genus[genid] = name

with open("genus.txt") as f:
    f.readline()
    spamreader = csv.reader(f, delimiter=',', quotechar='"')
    for genid, name, author, famid in spamreader:
        genid = int(genid)
        famid = int(famid)
        if genid in synonym:
            acc_part = ', "accepted": "%s"' % genus[synonym[genid]]
        else:
            acc_part = ''
        print ' {"object": "taxon", "rank": "genus", "epithet": "%s", '\
            '"author": "%s", "ht-rank": "familia", "ht-epithet": "%s"%s},' \
            % (name, author, family[famid], acc_part)
