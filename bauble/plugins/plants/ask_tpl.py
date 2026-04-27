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
import inspect
import logging
import os
import threading
import time
from gettext import gettext as _
from typing import Any, Callable, Optional, Union

import bauble
import requests
from requests.adapters import HTTPAdapter

try:
    # urllib3>=1.26
    from urllib3.util.retry import Retry
except Exception:
    Retry = None  # fallback handled below
    
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
        def extract_family(wfo_path: str) -> Optional[str]:
            parts = wfo_path.split("$")
            parts = parts[0].split("/")
            if len(parts) > 3:
                return parts[-3]  # Third-to-last element
            return None

        def extract_species(wfo_path: str) -> Optional[str]:
            parts = wfo_path.split("$")
            parts = parts[0].split("/")
            if len(parts) > 3:
                return parts[-1]  # Third-to-last element
            return None
        
        _WFO_URL = os.environ.get(
            "WFO_GRAPHQL_URL",
            "https://list.worldfloraonline.org/gql.php",
        )
        
        def _accepted_id_from(node: dict) -> Optional[str]:
            cpu = node.get("currentPreferredUsage") if isinstance(node, dict) else None
            has_name = cpu.get("hasName") if isinstance(cpu, dict) else None
            return has_name.get("id") if isinstance(has_name, dict) else None

        # Build a shared session once (module scope) so we reuse DNS and TCP,
        # but with sane retry policy.
        def _build_session():
            s = requests.Session()
            # Compatible Retry config across urllib3 versions
            if Retry:
                retry_kwargs = dict(
                    total=3,
                    connect=3,
                    read=3,
                    backoff_factor=0.6,
                    status_forcelist=(429, 502, 503, 504),
                    raise_on_status=False,
                )
                if "allowed_methods" in inspect.signature(Retry.__init__).parameters:
                    retry_kwargs["allowed_methods"] = frozenset({"POST", "GET"})  # method_whitelist on older urllib3
                else:
                    retry_kwargs["method_whitelist"] = frozenset({"POST", "GET"})  # method_whitelist on older urllib3
                adapter = HTTPAdapter(
                    max_retries=Retry(**retry_kwargs),
                    pool_maxsize=4,
                    pool_connections=4,
                )
            else:
                adapter = HTTPAdapter(pool_maxsize=4, pool_connections=4)
            s.mount("https://", adapter)
            s.headers.update({
                "User-Agent": "ghini.desktop/ask_tpl (+https://github.com/ghini/ghini.desktop)",
                "Accept": "application/json",
                "Content-Type": "application/json",
            })
            return s

        _SESSION = _build_session()

        def query_wfo_api(input_string: str) -> Any:
            #url = "https://list.worldfloraonline.org/gql.php"
            query = """
            query ($inputString: String!) {
                taxonNameMatch(inputString: $inputString) {
                    inputString
                    searchString
                    match {
                        id
                        title
                        fullNameStringPlain
                        genusString
                        speciesString
                        authorsString
                        role
                        rank
                        wfoPath
                        currentPreferredUsage {
                            hasName {
                                id
                            }
                        }
                    }
                    candidates {
                        id
                        title
                        fullNameStringPlain
                        genusString
                        speciesString
                        authorsString
                        role
                        rank
                        wfoPath
                        currentPreferredUsage {
                            hasName {
                                id
                            }
                        }
                    }
                }
            }
            """
            variables = {"inputString": input_string}
            #response = requests.post(url, json={"query": query, "variables": variables})
            #return response.json()
            # Primary attempt
            try:
                resp = _SESSION.post(
                    _WFO_URL,
                    json={"query": query, "variables": variables},
                    timeout=(3.05, 10),  # (connect, read)
                )
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.SSLError as ssl_error:
                # Likely the EOF-in-protocol issue; fall back to a one-off connection.
                logger.warning("WFO SSLError on first attempt (%s). Retrying with Connection: close…", ssl_error)
                try:
                    # Close session’s pool to avoid reusing a bad socket
                    _SESSION.close()
                except Exception:
                    pass

                # Fresh one-shot session with 'Connection: close'
                with requests.Session() as s:
                    s.headers.update(_SESSION.headers)
                    s.headers["Connection"] = "close"
                    try:
                        resp = s.post(
                            _WFO_URL,
                            json={"query": query, "variables": variables},
                            timeout=(3.05, 10),
                        )
                        resp.raise_for_status()
                        return resp.json()
                    except requests.exceptions.SSLError as ssl_error2:
                        # Give one tiny backoff and try once more
                        logger.warning("WFO SSLError on second attempt (%s). Backing off and trying once more…", ssl_error2)
                        time.sleep(0.8)
                        resp = s.post(
                            _WFO_URL,
                            json={"query": query, "variables": variables},
                            timeout=(3.05, 10),
                        )
                        resp.raise_for_status()
                        return resp.json()
            except requests.exceptions.RequestException as request_exception:
                # Surface non-SSL request failures (timeouts, 5xx after retries, etc.)
                logger.warning("WFO query failed: %s", request_exception)
                raise         

        def ask_wfo(name: str) -> Optional[list[dict[str, Any]]]:
            try:
                result = query_wfo_api(name)
            except requests.exceptions.SSLError:
                # transient TLS trouble — tell the user and continue without blocking the UI
                bauble.gui.show_error_box(
                    _("World Flora Online is temporarily unavailable over HTTPS."),
                    _("The connection was closed during TLS handshake. Please try again later."),
                )
                return None
            except requests.exceptions.Timeout:
                bauble.gui.show_error_box(_("WFO request timed out."), _("Try again."))
                return None
            except Exception as unknown_exception:
                # Other network errors: log and surface a concise message
                logger.warning("ask_wfo: %s", unknown_exception, exc_info=True)
                bauble.gui.show_error_box(_("Could not contact WFO."), str(unknown_exception))
                return None
            
            data = result.get("data", {}).get("taxonNameMatch", {})

            #if "match" in data and data["match"]:
            if data.get("match"):
                match = data["match"]
                family = extract_family(match["wfoPath"] or "")
                species_seg = extract_species(match["wfoPath"] or "")
                acc_id = _accepted_id_from(match)
                is_accepted = (acc_id == match.get("id"))
                return [
                    {
                        "ID": match.get("id"),
                        "FullName": match.get("fullNameStringPlain"),
                        "Genus": match.get("genusString"),
                        "Species": (
                            species_seg
                            if match.get("speciesString") is None
                            else match.get("speciesString")
                        ),
                        "role": match.get("role"),  # accepted, synonym, unplaced, deprecated
                        "Accepted ID": acc_id,
                        "Taxonomic status": (
                            "Accepted"
                            if is_accepted
                            else (
                                "Synonym"
                                if acc_id
                                else "Unplaced"
                            )
                        ),
                        "Genus hybrid marker": (
                            "×"
                            if str(match.get("fullNameStringPlain") or "").startswith("×")
                            and match.get("genusString") is None
                            else ""
                        ),
                        "Species hybrid marker": (
                            "× "
                            if " × " in str(match.get("fullNameStringPlain") or "")
                            and match.get("speciesString") is None
                            else ""
                        ),
                        "Authorship": match.get("authorsString"),
                        "Family": family,
                        "Title": match.get("title"),
                    }
                ]
            elif data.get("candidates"):
                candidates = []
                for candidate in data["candidates"]:
                    family = extract_family(candidate.get("wfoPath") or "")
                    species = extract_species(candidate.get("wfoPath") or "")
                    acc_id = _accepted_id_from(candidate)
                    is_accepted = acc_id == candidate.get("id")
                    candidates.append(
                        {
                            "ID": candidate.get("id"),
                            "FullName": candidate.get("fullNameStringPlain"),
                            "Genus": candidate.get("genusString"),
                            "Species": (
                                species
                                if candidate.get("speciesString") is None
                                else candidate.get("speciesString")
                            ),
                            "role": candidate.get("role"),  # accepted, synonym, unplaced, deprecated
                            "Accepted ID": acc_id,
                            "Taxonomic status": (
                                "Accepted"
                                if is_accepted 
                                else (
                                    "Synonym"
                                    if acc_id
                                    else "Unplaced"
                                )
                            ),
                            "Genus hybrid marker": (
                                "×"
                                if str(candidate.get("fullNameStringPlain") or "").startswith("×")
                                and candidate.get("genusString")  is None
                                else ""
                            ),
                            "Species hybrid marker": (
                                "×"
                                if " × " in str(candidate.get("fullNameStringPlain") or "")
                                and candidate.get("speciesString")  is None
                                else ""
                            ),
                            "Authorship": candidate.get("authorsString"),
                            "Family": family,
                            "Title": candidate.get("title"),
                        }
                    )
                return candidates
            else:
                return None

        class ShouldStopNow(Exception):
            pass

        class NoResult(Exception):
            pass

        if self.binomial is None:
            return
        
        found: Optional[dict[str, Any]] = None
        accepted: Optional[Union[dict[str, Any], list[dict[str, Any]]]] = None

        try:
            accepted = None
            logger.debug("%s before first query", self.name)
            candidates = ask_wfo(self.binomial)
            if not candidates:  # ✅ FIX: Handle empty results properly
                logger.info("nothing matches")  # ✅ Log correct message
                return  # ✅ Exit instead of raising NoResult
            logger.debug("%s after first query", self.name)
            if self.stopped():
                raise ShouldStopNow("after first query")
            if len(candidates) > 1:
                for item in candidates:
                    g, s = item["Genus"], item["Species"]
                    seq = difflib.SequenceMatcher(a=self.binomial, b=f"{g} {s}")
                    item["_score_"] = seq.ratio()

                found = sorted(
                    candidates,
                    key=lambda a: (a["_score_"], a["Taxonomic status"]),
                )[-1]
                logger.debug("best match has score %s", found["_score_"])
                if found["_score_"] < self.threshold:
                    found["_score_"] = 0
            else:
                found = candidates.pop()

            logger.debug("found this: %s", str(found))

            # If it's a synonym, resolve its accepted concept via Accepted ID
            acc_id = found.get("Accepted ID")
            is_accepted = bool(acc_id and acc_id == found.get("ID"))
            if not is_accepted and acc_id:
                # accepted = found
                accepted_list = ask_wfo(acc_id)
                accepted = accepted_list[0] if accepted_list else None

                logger.debug("ask_tpl on the Accepted ID returns %s", accepted)
                if accepted is None:
                    logger.debug(
                        "taxon %s %s (%s) is marked as synonym. "
                        "accepted form (%s) is at infraspecific rank.",
                        found.get("Genus"),
                        found.get("Species"),
                        found.get("ID"),
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

        if self.gui:
            from bauble.gtkinit import GLib

            GLib.idle_add(self.callback, found, accepted)
        else:
            self.callback(found, accepted)


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
