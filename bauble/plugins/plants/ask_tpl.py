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

import logging
logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)

header = None

import threading


class AskTPL(threading.Thread):
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        threading.Thread.__init__(self, group=group, target=target, name=name,
                                  verbose=verbose)
        self.args = args
        self.kwargs = kwargs
        return

    def run(self):
        def ask_tpl(binomial):
            result = requests.get(
                'http://www.theplantlist.org/tpl1.1/search?q=' + binomial +
                '&csv=true',
                timeout=4)
            l = result.text[1:].split('\n')
            result = [row for row in csv.reader(k.encode('utf-8')
                                                for k in l if k)]
            header = result[0]
            result = result[1:]
            return [dict(zip(header, k)) for k in result]

        logger.info('running with %s and %s', self.args, self.kwargs)

        s, threshold = self.args[:2]
        candidates = ask_tpl(s)
        if len(candidates) > 1:
            l = []
            for candidate in candidates:
                g, s = candidate['Genus'], candidate['Species']
                seq = difflib.SequenceMatcher(a=binomial, b='%s %s' % (g, s))
                l.append((seq.ratio(), candidate))

            score, candidate = sorted(l)[-1]
            if score < threshold:
                score = 0
        else:
            candidate = candidates.pop()
        logger.info("%(Genus)s %(Species hybrid marker)s%(Species)s %(Authorship)s (%(Family)s)", candidate)
        if candidate['Accepted ID']:
            candidate = ask_tpl(candidate['Accepted ID'])[0]
        logger.info("%(Genus)s %(Species hybrid marker)s%(Species)s %(Authorship)s (%(Family)s)", candidate)

        return


def citation(l):
    d = dict(zip(header, l))
    return "%(Genus)s %(Species hybrid marker)s%(Species)s "\
        "%(Authorship)s (%(Family)s)" % d


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    while True:
        binomial = raw_input()
        if not binomial:
            break

        t = AskTPL(args=(binomial, 0.8))
        t.run()
