#
# Copyright 2026 Chris Wyse
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
from __future__ import annotations

import inspect
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Optional, Protocol

import requests
from requests.adapters import HTTPAdapter

try:
    from urllib3.util.retry import Retry
except Exception:
    Retry = None  # fallback handled in WfoTaxonLookupProvider

logger = logging.getLogger(__name__)

HYBRID_MARKER = "\N{MULTIPLICATION SIGN}"
WFO_GRAPHQL_URL = "https://list.worldfloraonline.org/gql.php"


class TaxonLookupStatus:
    ACCEPTED = "accepted"
    SYNONYM = "synonym"
    UNPLACED = "unplaced"
    DEPRECATED = "deprecated"
    AMBIGUOUS = "ambiguous"
    NO_MATCH = "no_match"


@dataclass(frozen=True)
class TaxonLookupRequest:
    name: str
    family: Optional[str] = None
    rank: Optional[str] = None
    provider_id: Optional[str] = None


@dataclass(frozen=True)
class TaxonLookupResult:
    submitted_name: str
    provider: str
    provider_id: Optional[str]
    matched_name: Optional[str]
    genus: Optional[str]
    species: Optional[str]
    family: Optional[str]
    authorship: Optional[str]
    rank: Optional[str]
    status: str
    accepted_provider_id: Optional[str] = None
    title: Optional[str] = None
    genus_hybrid_marker: str = ""
    species_hybrid_marker: str = ""
    raw: Optional[dict[str, Any]] = None
    accepted: Optional["TaxonLookupResult"] = None  # resolved accepted name for synonyms

    @property
    def canonical_name(self) -> str:
        return " ".join(part for part in [self.genus, self.species] if part)

    def as_ask_tpl_dict(self) -> dict[str, Any]:
        """Return the historical dictionary shape consumed by SpeciesEditor."""
        return {
            "ID": self.provider_id,
            "FullName": self.matched_name,
            "Genus": self.genus,
            "Species": self.species,
            "role": self.status,
            "Accepted ID": self.accepted_provider_id,
            "Taxonomic status": self.status.title().replace("_", " "),
            "Genus hybrid marker": self.genus_hybrid_marker,
            "Species hybrid marker": self.species_hybrid_marker,
            "Authorship": self.authorship,
            "Family": self.family,
            "Title": self.title or self.matched_name,
        }


@dataclass(frozen=True)
class TaxonLookupResponse:
    request: TaxonLookupRequest
    provider: str
    results: list[TaxonLookupResult]
    raw: Optional[dict[str, Any]] = None


class TaxonLookupProvider(Protocol):
    name: str

    def lookup(self, request: TaxonLookupRequest) -> TaxonLookupResponse:
        pass


class WfoTaxonLookupProvider:
    name = "wfo"

    def __init__(
        self,
        endpoint: Optional[str] = None,
        timeout: tuple[float, int] = (3.05, 10),
    ) -> None:
        self.endpoint = endpoint or os.environ.get("WFO_GRAPHQL_URL", WFO_GRAPHQL_URL)
        self.timeout = timeout
        self._session: Optional[requests.Session] = None

    @property
    def session(self) -> requests.Session:
        session = self._session
        if session is None:
            session = self._session = self._build_session()
        return session

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        if Retry:
            retry_kwargs: dict[str, Any] = {
                "total": False,
                "connect": 0,
                "read": 0,
                "backoff_factor": 0.6,
                "status_forcelist": (429, 502, 503, 504),
                "raise_on_status": False,
            }
            if "allowed_methods" in inspect.signature(Retry.__init__).parameters:
                retry_kwargs["allowed_methods"] = frozenset({"POST", "GET"})
            else:
                retry_kwargs["method_whitelist"] = frozenset({"POST", "GET"})
            adapter = HTTPAdapter(
                max_retries=Retry(**retry_kwargs),
                pool_maxsize=4,
                pool_connections=4,
            )
        else:
            adapter = HTTPAdapter(pool_maxsize=4, pool_connections=4)
        session.mount("https://", adapter)
        session.headers.update(
            {
                "User-Agent": "ghini.desktop/taxon_lookup (+https://github.com/ghini/ghini.desktop)",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )
        return session


    def _query_by_id(self, name_id: str) -> Optional[dict[str, Any]]:
        query = """
        query ($nameId: String) {
            taxonNameById(nameId: $nameId) {
                id
                title
                fullNameStringPlain
                genusString
                speciesString
                authorsString
                role
                rank
                currentPreferredUsage {
                    hasName {
                        id
                    }
                }
            }
        }
        """
        try:
            response = self.session.post(
                self.endpoint,
                json={"query": query, "variables": {"nameId": name_id}},
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json().get("data", {}).get("taxonNameById")
        except requests.exceptions.RequestException as e:
            logger.warning("WFO _query_by_id failed: %s", e)
            return None

    def lookup(self, request: TaxonLookupRequest) -> TaxonLookupResponse:
        import dataclasses
        payload = self._query(request.name)
        data = payload.get("data", {}).get("taxonNameMatch", {})
        nodes = []
        if data.get("match"):
            nodes = [data["match"]]
        elif data.get("candidates"):
            nodes = data["candidates"]

        results = []
        for node in nodes:
            result = self._map_node(request, node)
            if result.status == TaxonLookupStatus.SYNONYM and result.accepted_provider_id:
                accepted_node = self._query_by_id(result.accepted_provider_id)
                if accepted_node:
                    accepted_request = TaxonLookupRequest(name=result.accepted_provider_id)
                    accepted_result = self._map_node(accepted_request, accepted_node)
                    if accepted_result.family is None and result.family is not None:
                        import dataclasses
                        accepted_result = dataclasses.replace(
                            accepted_result, family=result.family
                        )
                    result = dataclasses.replace(result, accepted=accepted_result)
            results.append(result)

        return TaxonLookupResponse(
            request=request,
            provider=self.name,
            results=results,
            raw=payload,
        )

    def _query(self, input_string: str) -> dict[str, Any]:
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
        try:
            response = self.session.post(
                self.endpoint,
                json={"query": query, "variables": variables},
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.SSLError as ssl_error:
            raise  # no point retrying, fall through caller.
        except requests.exceptions.RequestException as request_exception:
            logger.warning("WFO query failed: %s", request_exception)
            raise

    def _map_node(
        self, request: TaxonLookupRequest, node: dict[str, Any]
    ) -> TaxonLookupResult:
        accepted_id = self._accepted_id_from(node)
        provider_id = node.get("id")
        role = str(node.get("role") or "").lower()
        status = self._status_for(role, provider_id, accepted_id)
        wfo_path = node.get("wfoPath") or ""
        full_name = node.get("fullNameStringPlain") or ""
        genus = node.get("genusString")
        species = node.get("speciesString")

        # extract species epithet from full name when speciesString is absent
        if species is None and genus and full_name.startswith(genus):
            rest = full_name[len(genus):].strip()
            parts = rest.split()
            if parts:
                species = parts[0]

        # fallback to wfoPath if still None
        if species is None:
            species = self._extract_species(wfo_path, genus)

        return TaxonLookupResult(
            submitted_name=request.name,
            provider=self.name,
            provider_id=provider_id,
            matched_name=full_name.strip() or None,
            genus=genus,
            species=species,
            family=self._extract_family(wfo_path, genus),
            authorship=node.get("authorsString"),
            rank=node.get("rank"),
            status=status,
            accepted_provider_id=accepted_id,
            title=node.get("title"),
            genus_hybrid_marker=(
                HYBRID_MARKER
                if full_name.startswith(HYBRID_MARKER)
                and node.get("genusString") is None
                else ""
            ),
            species_hybrid_marker=(
                HYBRID_MARKER
                if f" {HYBRID_MARKER} " in full_name
                and node.get("speciesString") is None
                else ""
            ),
            raw=node,
        )

    @staticmethod
    def _accepted_id_from(node: dict[str, Any]) -> Optional[str]:
        current_usage = node.get("currentPreferredUsage")
        has_name = (
            current_usage.get("hasName") if isinstance(current_usage, dict) else None
        )
        return has_name.get("id") if isinstance(has_name, dict) else None

    @staticmethod
    def _extract_family(wfo_path: str, genus: Optional[str] = None) -> Optional[str]:
        parts = wfo_path.split("$")[0].split("/")
        if genus and genus in parts:
            idx = parts.index(genus)
            return parts[idx - 1] if idx > 0 else None
        if len(parts) > 3:
            return parts[-3]
        return None

    @staticmethod
    def _extract_species(wfo_path: str, genus: Optional[str] = None) -> Optional[str]:
        parts = wfo_path.split("$")[0].split("/")
        if genus and genus in parts:
            idx = parts.index(genus)
            return parts[idx + 1] if idx + 1 < len(parts) else None
        if len(parts) > 3:
            return parts[-1]
        return None

    @staticmethod
    def _status_for(
        role: str, provider_id: Optional[str], accepted_provider_id: Optional[str]
    ) -> str:
        if role == TaxonLookupStatus.DEPRECATED:
            return TaxonLookupStatus.DEPRECATED
        if provider_id and accepted_provider_id == provider_id:
            return TaxonLookupStatus.ACCEPTED
        if role == TaxonLookupStatus.SYNONYM or accepted_provider_id:
            return TaxonLookupStatus.SYNONYM
        if role == TaxonLookupStatus.ACCEPTED:
            return TaxonLookupStatus.ACCEPTED
        return TaxonLookupStatus.UNPLACED


TNRS_API_URL = "https://tnrsapi.xyz/tnrs_api.php"


class TnrsTaxonLookupProvider:
    name = "tnrs"

    def __init__(
        self,
        endpoint: Optional[str] = None,
        timeout: tuple[float, int] = (3.05, 15),
    ) -> None:
        self.endpoint = endpoint or os.environ.get("TNRS_API_URL", TNRS_API_URL)
        self.timeout = timeout

    def lookup(self, request: TaxonLookupRequest) -> TaxonLookupResponse:
        payload = {
            "opts": {
                "sources": "wcvp",
                "class": "wfo",
                "mode": "resolve",
                "matches": "best",
                "acc": "0",
            },
            "data": [[1, request.name]],
        }
        try:
            response = requests.post(
                self.endpoint,
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            logger.warning("TNRS query failed: %s", e)
            raise

        results = []
        for row in data if isinstance(data, list) else []:
            result = self._map_row(request, row)
            if result:
                results.append(result)

        return TaxonLookupResponse(
            request=request,
            provider=self.name,
            results=results,
            raw=data,
        )

    def _map_row(
        self, request: TaxonLookupRequest, row: dict[str, Any]
    ) -> Optional[TaxonLookupResult]:
        matched = row.get("Name_matched")
        if not matched:
            return None
        provider_id = row.get("Name_matched_id")
        accepted_id = row.get("Accepted_name_id")
        status_raw = str(row.get("Taxonomic_status") or "").lower()
        if status_raw == "accepted":
            status = TaxonLookupStatus.ACCEPTED
        elif status_raw == "synonym":
            status = TaxonLookupStatus.SYNONYM
        else:
            status = TaxonLookupStatus.UNPLACED

        accepted = None
        if status == TaxonLookupStatus.SYNONYM and row.get("Accepted_name"):
            accepted_name = row["Accepted_name"]
            accepted_parts = accepted_name.split()
            accepted = TaxonLookupResult(
                submitted_name=matched,
                provider=self.name,
                provider_id=str(accepted_id) if accepted_id else None,
                matched_name=accepted_name,
                genus=accepted_parts[0] if accepted_parts else None,
                species=accepted_parts[1] if len(accepted_parts) > 1 else None,
                family=row.get("Accepted_family"),
                authorship=row.get("Accepted_name_author"),
                rank=row.get("Accepted_name_rank"),
                status=TaxonLookupStatus.ACCEPTED,
                accepted_provider_id=None,
                raw=row,
            )

        return TaxonLookupResult(
            submitted_name=request.name,
            provider=self.name,
            provider_id=str(provider_id) if provider_id else None,
            matched_name=matched,
            genus=row.get("Genus_matched"),
            species=row.get("Specific_epithet_matched"),
            family=row.get("Accepted_family") or row.get("Name_matched_accepted_family"),
            authorship=row.get("Canonical_author"),
            rank=row.get("Name_matched_rank"),
            status=status,
            accepted_provider_id=str(accepted_id) if accepted_id else None,
            accepted=accepted,
            raw=row,
        )


PROVIDERS: list[TaxonLookupProvider] = [
    WfoTaxonLookupProvider(),
    TnrsTaxonLookupProvider(),
]


def lookup_taxon(name: str) -> Optional[list[TaxonLookupResult]]:
    """Try each provider in order, returning results from the first that succeeds."""
    for provider in PROVIDERS:
        try:
            results = provider.lookup(TaxonLookupRequest(name=name)).results
            if results:
                return results
        except Exception as e:
            logger.warning("%s failed for %r: %s", provider.name, name, e)
    return None
