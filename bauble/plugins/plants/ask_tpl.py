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

import threading


class AskTPL(threading.Thread):
    running = None

    def __init__(self, binomial, callback, threshold=0.8, timeout=4,
                 group=None, verbose=None, **kwargs):
        super(AskTPL, self).__init__(
            group=group, target=None, name=None, verbose=verbose)
        logger.info("%s %s", self.name, self.running and self.running.name)
        if self.running is not None:
            if self.running.binomial == binomial:
                binomial = None
            else:
                self.running.stop()
        if binomial:
            self.__class__.running = self
        self._stop = False
        self.binomial = binomial
        self.threshold = threshold
        self.callback = callback
        self.timeout = timeout

    def stop(self):
        self._stop = True

    def stopped(self):
        return self._stop

    def run(self):
        def ask_tpl(binomial):
            result = requests.get(
                'http://www.theplantlist.org/tpl1.1/search?q=' + binomial +
                '&csv=true',
                timeout=self.timeout)
            l = result.text[1:].split('\n')
            result = [row for row in csv.reader(k.encode('utf-8')
                                                for k in l if k)]
            header = result[0]
            result = result[1:]
            return [dict(zip(header, k)) for k in result]

        class ShouldStopNow(Exception):
            pass

        class NoResult(Exception):
            pass

        if self.binomial is None:
            logger.info("%s same value as %s, do not start", self.name, self.running.name)
            return

        try:
            synonym = None
            logger.info("%s before first query", self.name)
            candidates = ask_tpl(self.binomial)
            logger.info("%s after first query", self.name)
            if self.stopped():
                raise ShouldStopNow('after first query')
            if len(candidates) > 1:
                l = []
                for candidate in candidates:
                    g, s = candidate['Genus'], candidate['Species']
                    seq = difflib.SequenceMatcher(a=self.binomial,
                                                  b='%s %s' % (g, s))
                    l.append((seq.ratio(), candidate))

                score, candidate = sorted(l)[-1]
                if score < self.threshold:
                    score = 0
            elif candidates:
                candidate = candidates.pop()
            else:
                raise NoResult
            if candidate['Accepted ID']:
                synonym = candidate
                candidate = ask_tpl(candidate['Accepted ID'])[0]
                logger.info("%s after second query", self.name)
            if self.stopped():
                raise ShouldStopNow('after second query')
        except Exception, e:
            logger.info("%s (%s)%s -> do not invoke callback",
                        self.name, type(e).__name__, e)
            self.__class__.running = None
            return
        self.__class__.running = None
        logger.info("%s before invoking callback" % self.name)
        self.callback(candidate, synonym)


def citation(d):
    return "%(Genus hybrid marker)s%(Genus)s "\
        "%(Species hybrid marker)s%(Species)s "\
        "%(Authorship)s (%(Family)s)" % d


def what_to_do_with_it(accepted, synonym):
    if synonym is not None:
        logger.info("%s - synonym of:", citation(synonym))
    logger.info("%s", citation(accepted))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
    while True:
        binomial = raw_input()
        if not binomial:
            if AskTPL.running is not None:
                AskTPL.running.stop()
            break

        AskTPL(binomial, what_to_do_with_it, timeout=2).start()
