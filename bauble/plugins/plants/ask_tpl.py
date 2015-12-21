# -*- coding: utf-8 -*-
#
# Copyright 2015 Mario Frasca <mario@anche.no>.
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

import difflib
import requests
import csv

header = None


def ask_tpl(s):
    result = requests.get(
        'http://www.theplantlist.org/tpl1.1/search?q=' + s + '&csv=true',
        timeout=5)
    l = result.text[1:].split('\n')
    result = [row for row in csv.reader(k.encode('utf-8') for k in l if k)]
    global header
    header = result[0]
    result = result[1:]
    return result


def citation(l):
    d = dict(zip(header, l))
    return "%(Genus)s %(Species hybrid marker)s%(Species)s "\
        "%(Authorship)s (%(Family)s)" % d


def best_tpl_match(binomial, threshold=0.8):
    l = []
    for row in ask_tpl(binomial):
        g, s = row[4], row[6]
        seq = difflib.SequenceMatcher(a=binomial, b='%s %s' % (g, s))
        l.append((seq.ratio(), row))

    score, candidate = sorted(l)[-1]
    if score < threshold:
        score = 0
    return score, candidate


while True:
    binomial = raw_input()
    if not binomial:
        break

    score, candidate = best_tpl_match(binomial)

    print {1: 'your match is',
           0: 'do you really mean'}.get(score, 'you probably mean')
    print citation(candidate)
    if candidate[-1]:
        print 'synonym of'
        print citation(ask_tpl(candidate[-1])[0])
