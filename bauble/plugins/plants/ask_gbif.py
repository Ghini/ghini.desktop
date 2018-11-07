# -*- coding: utf-8 -*-
#
# Copyright 2015,2018 Mario Frasca <mario@anche.no>.
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

import difflib
import requests
import json

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

import threading


class AskGBIF(threading.Thread):
    running = None

    def __init__(self, binomial, callback, threshold=0.8, timeout=4, gui=False,
                 group=None, verbose=None, **kwargs):
        super().__init__(
            group=group, target=None, name=None)
        logger.debug("new %s, already running %s.",
                     self.name, self.running and self.running.name)
        if self.running is not None:
            if self.running.binomial == binomial:
                logger.debug('already requesting %s, ignoring repeated request', binomial)
                binomial = None
            else:
                logger.debug("running different request (%s), stopping it, starting %s",
                             self.running.binomial, binomial)
                self.running.stop()
        if binomial:
            self.__class__.running = self
        self._stop = False
        self.binomial = binomial
        self.threshold = threshold
        self.callback = callback
        self.timeout = timeout
        self.gui = gui

    def stop(self):
        self._stop = True

    def stopped(self):
        return self._stop

    def run(self):
        def ask_gbif(binomial):
            result = requests.get(
                'http://api.gbif.org/v1/species/match?verbose=false&name=' + binomial,
                timeout=self.timeout)
            logger.debug(result.text)
            result = json.loads(result.text)
            return result

        class ShouldStopNow(Exception):
            pass

        class NoResult(Exception):
            pass

        if self.binomial is None:
            return

        try:
            accepted = None
            logger.debug("%s before first query", self.name)
            candidate = ask_gbif(self.binomial)
            logger.debug("%s after first query", self.name)
            if self.stopped():
                raise ShouldStopNow('after first query')
            if candidate['matchType'] in ['NONE', 'HIGHERRANK']:
                raise NoResult
            else:
                found = candidate
            logger.debug("found this: %s", str(found))
            if found['status'] == 'SYNONYM':
                accepted = ask_gbif(found['species'])
                logger.debug("ask_gbif on the Accepted ID returns %s", accepted)
                logger.debug("%s after second query", self.name)
            if self.stopped():
                raise ShouldStopNow('after second query')
        except ShouldStopNow:
            logger.debug("%s interrupted : do not invoke callback",
                         self.name)
            return
        except Exception as e:
            import traceback
            logger.warning(traceback.format_exc())
            logger.debug("%s (%s)%s : completed with trouble",
                         self.name, type(e).__name__, e)
            self.__class__.running = None
            found = accepted = None
        self.__class__.running = None
        logger.debug("%s before invoking callback" % self.name)
        if self.gui:
            from gi.repository import GObject
            GObject.idle_add(self.callback, found, accepted)
        else:
            self.callback(found, accepted)


def citation(d):
    return ("%(scientificName)s "
            "(%(family)s)" % d).replace('   ', ' ')


def what_to_do_with_it(found, accepted):
    if found is None and accepted is None:
        logger.info("nothing matches")
        return
    logger.info("%s", citation(found))
    if accepted == []:
        logger.info("invalid reference in gbif.")
    if accepted:
        logger.info("%s - is its accepted form", citation(accepted))
