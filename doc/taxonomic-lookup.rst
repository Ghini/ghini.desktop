Taxonomic Lookup
################

This note records the current external taxonomic lookup path used by the
species editor during Ghini 4 development.

Current Interactive Lookup
==========================

The species editor lookup button calls ``AskTPL`` in
``bauble/plugins/plants/ask_tpl.py``. The class name is historical. The
external service integration now lives behind the normalized lookup contract in
``bauble/plugins/plants/taxon_lookup.py``.

The first provider is ``WfoTaxonLookupProvider``. It queries the World Flora
Online Plant List GraphQL endpoint::

  https://list.worldfloraonline.org/gql.php

The endpoint can be overridden with ``WFO_GRAPHQL_URL``, which is useful for
tests, local mirrors, or a future self-hosted WFO Plant List API.

The provider maps Ghini's internal ``TaxonLookupRequest`` to WFO's
``taxonNameMatch(inputString: ...)`` query and maps WFO responses back to
``TaxonLookupResult`` objects. The normalized result records:

* submitted and matched names,
* provider and provider ID,
* genus, species, family, rank, and authorship,
* accepted, synonym, unplaced, or deprecated status,
* accepted-name provider ID for synonyms,
* raw provider data for diagnostics.

The WFO provider currently consumes:

* a closest ``match`` or candidate list,
* WFO IDs,
* genus, species, author, rank, role, and family path data,
* ``currentPreferredUsage.hasName.id`` to resolve accepted names for synonyms.

The lookup is intentionally asynchronous. UI code should not block species
editing if WFO is unavailable, times out, or returns no match.

Release Scope
=============

The Ghini 4.0.0 baseline release includes botanical name validation as part of
the daily interactive species-entry workflow. For the baseline, the required
behavior is:

* Ghini code talks to a normalized taxonomic lookup interface, not directly to
  a provider-specific response shape,
* the species editor can query a maintained service for author and accepted-name
  information,
* unavailable or empty lookup responses do not block species editing,
* accepted-name responses can be interpreted without reintroducing The Plant
  List dependencies,
* the behavior is covered by mocked tests so the release suite is deterministic.

The current implementation provides that normalized layer and the first WFO
provider. The WFO Plant List API documents both GraphQL and REST matching
interfaces, open access without API keys, stable WFO identifiers, and data
snapshots every six months. The TNRS service also has a maintained API suitable
for batch workflows; it should plug into the same contract if it remains part
of the release scope.

Current Coverage
================

``bauble/plugins/plants/test_asktpl.py`` covers:

* WFO provider mapping for accepted, synonym, and empty responses,
* a simple accepted-name answer with author and family data,
* a synonym answer followed by accepted-name resolution,
* an empty WFO answer,
* duplicate in-flight request suppression.

These are unit tests with mocked HTTP responses. They do not verify current WFO
network availability.

Remaining Work
==============

The legacy ``AskTPL`` name and species-editor callback names can be renamed
later, but that should be a separate compatibility cleanup.

``bauble/plugins/plants/taxonomy_check.py`` still documents a TNRS file-based
workflow for batch checks. Before closing the release-blocking taxonomy lookup
issue, decide whether that workflow should:

* keep importing user-supplied TNRS files,
* switch to WFO matching exports,
* call the WFO matching or GraphQL API directly,
* or support both TNRS and WFO through the normalized provider interface.

The current daily-entry priority is the interactive species lookup used to
confirm author names while entering new species.

References
==========

* WFO Plant List API: https://list.worldfloraonline.org/index.php
* WFO Plant List background: https://about.worldfloraonline.org/plant-list/
* TNRS API: https://tnrs.biendata.org/tnrsapi/
* BIEN TNRS API notes: https://bien.nceas.ucsb.edu/bien/tools/tnrs/tnrs-api/
