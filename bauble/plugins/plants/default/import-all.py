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

import json
f = open('family.txt', 'r')
lines = [i.strip() for i in f.readlines()]
family = dict([(eval(i.split(',')[0]), eval(i.split(',')[1]))
               for i in lines[1:]])
family_no = dict([(eval(i.split(',')[1]), eval(i.split(',')[0]))
                  for i in lines[1:]])

genera = json.load(open('genera-conservanda.json'))

enumerated_genera = [
    (n + 1, g) for n, g in enumerate(
        g for g in genera
        if g['ht-epithet'] not in ['Undetermined',
                                   'Undetermined-Virus'])]

genus = dict((n, (g['epithet'], g['author'], family_no[g['ht-epithet']]))
             for n, g in enumerated_genera)
genus_no = dict(((g['epithet'], g['author']), n)
                for n, g in enumerated_genera)

gtxt = '\n'.join(['%d,"%s","%s",%d' % (n, t[0], t[1], t[2])
                  for n, t in genus.items()])
import codecs
o = codecs.open("genus.txt", "w", "UTF8")
o.write('"id","genus","author","family_id"\n')
o.write(gtxt)
o.close()

stxt = '\n'.join(["%d,%d" % (
    n, genus_no[(g['accepted']['epithet'], g['accepted']['author'])])
    for n, g in enumerated_genera
    if 'accepted' in g])

o = codecs.open("genus_synonym.txt", "w", "UTF8")
o.write('"synonym_id","genus_id"\n')
o.write(stxt)
o.close()
