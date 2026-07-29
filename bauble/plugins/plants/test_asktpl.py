#
# Copyright 2008-2010 Brett Adams
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
#
# Description: test for the Plant plugin
#
# Refactored for Pytest and SQLAlchemy 2.0.36 compatibility

from __future__ import annotations

import logging
from typing import Any, Iterator, Optional
from unittest.mock import patch

import pytest
from bauble.plugins.plants.ask_tpl import AskTPL, what_to_do_with_it
from bauble.plugins.plants.taxon_lookup import (
    TaxonLookupRequest,
    TaxonLookupStatus,
    WfoTaxonLookupProvider,
)


class MockResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict[str, Any]:
        return self.payload


@pytest.fixture
def mock_requests() -> Iterator[None]:
    """
    Mock the `requests.get` function to simulate API responses.
    """

    def wfo_payload(match: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        return {"data": {"taxonNameMatch": {"match": match, "candidates": []}}}

    def mock_post(
        url: str,
        json: Optional[dict[str, Any]] = None,
        timeout: Optional[tuple[float, int]] = None,
    ) -> MockResponse:
        import time

        time.sleep(0.1)
        answers = {
            "Rhopalocarpus alternifolium": wfo_payload(
                {
                    "id": "wfo-rhopalocarpus",
                    "title": "Rhopalocarpus alternifolius var. sambiranensis Capuron",
                    "fullNameStringPlain": "Rhopalocarpus alternifolius var. sambiranensis Capuron",
                    "genusString": "Rhopalocarpus",
                    "speciesString": "alternifolius",
                    "authorsString": "Capuron",
                    "role": "accepted",
                    "rank": "variety",
                    "wfoPath": "/Sphaerosepalaceae/Rhopalocarpus/alternifolius",
                    "currentPreferredUsage": {"hasName": {"id": "wfo-rhopalocarpus"}},
                }
            ),
            "Iris florentina": wfo_payload(
                {
                    "id": "kew-321828",
                    "title": "Iris x florentina L.",
                    "fullNameStringPlain": "Iris x florentina L.",
                    "genusString": "Iris",
                    "speciesString": "florentina",
                    "authorsString": "L.",
                    "role": "synonym",
                    "rank": "species",
                    "wfoPath": "/Iridaceae/Iris/florentina",
                    "currentPreferredUsage": {"hasName": {"id": "kew-321867"}},
                }
            ),
            "kew-321867": wfo_payload(
                {
                    "id": "kew-321867",
                    "title": "Iris x germanica L.",
                    "fullNameStringPlain": "Iris x germanica L.",
                    "genusString": "Iris",
                    "speciesString": "germanica",
                    "authorsString": "L.",
                    "role": "accepted",
                    "rank": "species",
                    "wfoPath": "/Iridaceae/Iris/germanica",
                    "currentPreferredUsage": {"hasName": {"id": "kew-321867"}},
                }
            ),
            "Manducaria italica": wfo_payload(),
        }

        input_string = (json or {}).get("variables", {}).get("inputString", "")
        variables = (json or {}).get("variables", {})
        if "nameId" in variables:
            name_id = variables["nameId"]
            by_id = {
                "kew-321867": {
                    "id": "kew-321867",
                    "title": "Iris x germanica L.",
                    "fullNameStringPlain": "Iris x germanica L.",
                    "genusString": "Iris",
                    "speciesString": "germanica",
                    "authorsString": "L.",
                    "role": "accepted",
                    "rank": "species",
                    "currentPreferredUsage": {"hasName": {"id": "kew-321867"}},
                },
            }
            return MockResponse({"data": {"taxonNameById": by_id.get(name_id)}})
        return MockResponse(answers.get(input_string, wfo_payload()))

    class MockSession:
        headers: dict[str, str]

        def __init__(self) -> None:
            self.headers = {}

        def mount(self, *args: Any, **kwargs: Any) -> None:
            pass

        def post(self, *args: Any, **kwargs: Any) -> MockResponse:
            return mock_post(*args, **kwargs)

        def close(self) -> None:
            pass

        def __enter__(self) -> MockSession:
            return self

        def __exit__(self, *args: Any) -> None:
            pass

    def mock_tnrs_post(*args: Any, **kwargs: Any) -> MockResponse:
        # TNRS non ha corrispondenze note nei test: nessun risultato.
        return MockResponse({"data": []})

    with patch("bauble.plugins.plants.taxon_lookup.requests.Session", MockSession), \
         patch("bauble.plugins.plants.taxon_lookup.requests.post", mock_tnrs_post):
        yield


@pytest.mark.usefixtures("mock_requests", "mock_logger")
class TestAskTPL:
    """
    Tests for the AskTPL class and its interactions.
    """

    logger_name: str = "bauble.plugins.plants.ask_tpl"
    logger = logging.getLogger(logger_name)

    def test_simple_answer(self, mock_logger: Any) -> None:
        self.logger.setLevel(logging.INFO)
        binomial = "Rhopalocarpus alternifolium"
        AskTPL(binomial, what_to_do_with_it, timeout=2).run()

        infolog = mock_logger.messages[self.logger_name]["info"]
        assert len(infolog) == 1
        assert (
            infolog[0]
            == "Rhopalocarpus alternifolius var. sambiranensis Capuron (Sphaerosepalaceae)"
        )

    def test_taxon_is_synonym(self, mock_logger: Any) -> None:
        self.logger.setLevel(logging.INFO)
        binomial = "Iris florentina"
        AskTPL(binomial, what_to_do_with_it, timeout=2).run()

        infolog = mock_logger.messages[self.logger_name]["info"]
        assert len(infolog) == 2
        assert infolog[0] == "Iris x florentina L. (Iridaceae)"
        assert infolog[1] == "Iris x germanica L. (Iridaceae) - is its accepted form"

    def test_empty_answer(self: TestAskTPL, mock_logger: Any) -> None:
        self.logger.setLevel(logging.INFO)
        binomial = "Manducaria italica"
        AskTPL(binomial, what_to_do_with_it, timeout=2).run()

        infolog = mock_logger.messages[self.logger_name]["info"]
        assert len(infolog) == 1
        assert infolog[0] == "nothing matches"

    def test_wfo_provider_maps_accepted_result(self) -> None:
        response = WfoTaxonLookupProvider().lookup(
            TaxonLookupRequest(name="Rhopalocarpus alternifolium")
        )

        assert len(response.results) == 1
        result = response.results[0]
        assert result.provider == "wfo"
        assert result.provider_id == "wfo-rhopalocarpus"
        assert result.family == "Sphaerosepalaceae"
        assert result.genus == "Rhopalocarpus"
        assert result.species == "alternifolius"
        assert result.authorship == "Capuron"
        assert result.status == TaxonLookupStatus.ACCEPTED
        assert result.accepted_provider_id == "wfo-rhopalocarpus"

    def test_wfo_provider_maps_synonym_result(self) -> None:
        response = WfoTaxonLookupProvider().lookup(
            TaxonLookupRequest(name="Iris florentina")
        )

        assert len(response.results) == 1
        result = response.results[0]
        assert result.provider_id == "kew-321828"
        assert result.status == TaxonLookupStatus.SYNONYM
        assert result.accepted_provider_id == "kew-321867"
        assert result.as_ask_tpl_dict()["Taxonomic status"] == "Synonym"

    def test_wfo_provider_returns_no_results_for_empty_answer(self) -> None:
        response = WfoTaxonLookupProvider().lookup(
            TaxonLookupRequest(name="Manducaria italica")
        )

        assert response.results == []

    def test_do_not_run_same_query_twice(self, mock_logger: Any) -> None:
        self.logger.setLevel(logging.DEBUG)
        binomial = "Iris florentina"
        obj = AskTPL(binomial, what_to_do_with_it, timeout=2)
        obj.start()
        AskTPL(binomial, what_to_do_with_it, timeout=2).run()
        obj.stop()

        debuglog = mock_logger.messages[self.logger_name]["debug"]
        assert (
            "already requesting Iris florentina, ignoring repeated request" in debuglog
        )

    def test_do_not_run_two_requests_at_same_time(self, mock_logger: Any) -> None:
        self.logger.setLevel(logging.DEBUG)
        obj = AskTPL("Iris florentina", what_to_do_with_it, timeout=2)
        obj.start()
        AskTPL("Iris germanica", what_to_do_with_it, timeout=2).run()
        obj.stop()

        debuglog = mock_logger.messages[self.logger_name]["debug"]
        assert (
            "running different request (Iris florentina), stopping it, starting Iris germanica"
            in debuglog
        )
