#
# Copyright 2015 Mario Frasca <mario@anche.no>.
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
import logging
import threading
from gettext import gettext as _
from typing import Any, Callable, Optional, Union

import bauble
import requests

from bauble.plugins.plants.taxon_lookup import (
    TaxonLookupRequest,
    TaxonLookupResult,
    WfoTaxonLookupProvider,
)

logger: Any = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class AskTPL(threading.Thread):
    _stop: bool
    binomial: Any
    threshold: Any
    callback: Any
    timeout: Any
    gui: Any
    running: Any = None

    def __init__(
        self,
        binomial: Optional[str],
        callback: Callable[
            [
                Optional[dict[str, Any]],
                Optional[Union[dict[str, Any], list[dict[str, Any]]]],
            ],
            None,
        ],
        threshold: float = 0.8,
        timeout: int = 4,
        gui: bool = False,
        group: Optional[Any] = None,
        verbose: Optional[bool] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(group=group, target=None, name=None)
        logger.debug(
            "new %s, already running %s.",
            self.name,
            self.running and self.running.name,
        )
        if self.running is not None:
            if self.running.binomial == binomial:
                logger.debug(
                    "already requesting %s, ignoring repeated request",
                    binomial,
                )
                binomial = None
            else:
                logger.debug(
                    "running different request (%s), stopping it, starting %s",
                    self.running.binomial,
                    binomial,
                )
                self.running.stop()
        if binomial:
            self.__class__.running = self
        self._stop = False
        self.binomial = binomial
        self.threshold = threshold
        self.callback = callback
        self.timeout = timeout
        self.gui = gui

    def stop(self) -> None:
        self._stop = True

    def stopped(self) -> bool:
        return self._stop

    def run(self) -> None:
        if self.gui:
            from bauble.gtkinit import GLib

        provider = WfoTaxonLookupProvider()

        def ask_wfo(name: str) -> Optional[list[TaxonLookupResult]]:
            try:
                return provider.lookup(TaxonLookupRequest(name=name)).results
            except requests.exceptions.SSLError:
                GLib.idle_add(
                    bauble.gui.show_error_box,
                    _("World Flora Online is temporarily unavailable over HTTPS."),
                    _("The connection was closed during TLS handshake. Please try again later."))
                return None
            except requests.exceptions.Timeout:
                GLib.idle_add(
                    bauble.gui.show_error_box,
                    _("WFO request timed out."), _("Try again."))
                return None
            except Exception as unknown_exception:
                # Other network errors: log and surface a concise message
                logger.warning("ask_wfo: %s", unknown_exception, exc_info=True)
                GLib.idle_add(
                    bauble.gui.show_error_box,
                    _("Could not contact WFO."), str(unknown_exception))
                return None

        class ShouldStopNow(Exception):
            pass

        if self.binomial is None:
            return

        found: Optional[TaxonLookupResult] = None
        accepted: Optional[TaxonLookupResult] = None

        try:
            accepted = None
            logger.debug("%s before first query", self.name)
            candidates = ask_wfo(self.binomial)
            logger.debug("%s after first query", self.name)
            if self.stopped():
                raise ShouldStopNow("after first query")
            if not candidates:
                logger.debug("%s returned no candidates", self.name)
            elif len(candidates) > 1:
                scored = [
                    (
                        difflib.SequenceMatcher(
                            a=self.binomial,
                            b=item.canonical_name,
                        ).ratio(),
                        item.status,
                        item,
                    )
                    for item in candidates
                ]
                score, _status, found = sorted(scored, key=lambda item: item[:2])[-1]
                logger.debug("best match has score %s", score)
                if score < self.threshold:
                    score = 0
            else:
                found = candidates.pop()

            logger.debug("found this: %s", str(found))

            acc_id = found.accepted_provider_id if found else None
            is_accepted = bool(found and acc_id and acc_id == found.provider_id)
            if found and not is_accepted and acc_id:
                accepted_list = ask_wfo(acc_id)
                accepted = accepted_list[0] if accepted_list else None

                logger.debug("ask_tpl on the Accepted ID returns %s", accepted)
                if accepted is None:
                    logger.debug(
                        "taxon %s %s (%s) is marked as synonym. "
                        "accepted form (%s) is at infraspecific rank.",
                        found.genus,
                        found.species,
                        found.provider_id,
                        acc_id,
                    )
                logger.debug("%s after second query", self.name)
            if self.stopped():
                raise ShouldStopNow("after second query")
        except ShouldStopNow:
            logger.debug("%s interrupted : do not invoke callback", self.name)
            return
        except Exception as err:
            import traceback

            logger.warning(traceback.format_exc())
            logger.debug(
                "%s (%s)%s : completed with trouble",
                self.name,
                type(err).__name__,
                err,
            )
            self.__class__.running = None
            found = None
            accepted = None

        self.__class__.running = None

        logger.debug("%s before invoking callback", self.name)
        found_dict = found.as_ask_tpl_dict() if found else None
        accepted_dict = accepted.as_ask_tpl_dict() if accepted else None

        if self.gui:
            GLib.idle_add(self.callback, found_dict, accepted_dict)
        else:
            self.callback(found_dict, accepted_dict)


def citation(d: dict[str, Any]) -> str:
    # return (
    #     "%(Genus hybrid marker)s%(Genus)s "
    #     "%(Species hybrid marker)s%(Species)s "
    #     # "%(Infraspecific rank)s %(Infraspecific epithet)s "
    #     "%(Authorship)s (%(Family)s)" % d
    # ).replace("   ", " ")
    return ("{Title} ({Family})".format(**d)).replace("   ", " ")


def what_to_do_with_it(
    found: Optional[dict[str, Any]],
    accepted: Optional[Union[dict[str, Any], list[dict[str, Any]]]],
) -> None:
    if found is None and accepted is None:
        logger.info("nothing matches")
        return
    if found is not None:
        logger.info("%s", citation(found))
    if accepted == []:
        logger.info("invalid reference in tpl.")
    if isinstance(accepted, dict):
        logger.info("%s - is its accepted form", citation(accepted))
