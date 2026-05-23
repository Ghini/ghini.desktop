Taxonomic Lookup
################

This note records the current external taxonomic lookup path used by the
species editor during Ghini 4 development.

Current Interactive Lookup
==========================

The species editor lookup button calls ``AskTPL`` in
``bauble/plugins/plants/ask_tpl.py``. The class name is historical, but the
implementation currently queries the World Flora Online Plant List GraphQL
endpoint::

  https://list.worldfloraonline.org/gql.php

The endpoint can be overridden with ``WFO_GRAPHQL_URL``, which is useful for
tests, local mirrors, or a future self-hosted WFO Plant List API.

The query uses ``taxonNameMatch(inputString: ...)`` and expects:

* a closest ``match`` or candidate list,
* WFO IDs,
* genus, species, author, rank, role, and family path data,
* ``currentPreferredUsage.hasName.id`` to resolve accepted names for synonyms.

The lookup is intentionally asynchronous. UI code should not block species
editing if WFO is unavailable, times out, or returns no match.

Current Coverage
================

``bauble/plugins/plants/test_asktpl.py`` covers:

* a simple accepted-name answer with author and family data,
* a synonym answer followed by accepted-name resolution,
* an empty WFO answer,
* duplicate in-flight request suppression.

These are unit tests with mocked HTTP responses. They do not verify current WFO
network availability.

Remaining Work
==============

The legacy ``AskTPL`` name and species-editor callback names can be renamed
later, but that should be a separate compatibility cleanup. More importantly,
``bauble/plugins/plants/taxonomy_check.py`` still documents a TNRS file-based
workflow for batch checks. Before release, decide whether that workflow should:

* keep importing user-supplied TNRS files,
* switch to WFO matching exports,
* call the WFO matching or GraphQL API directly,
* or support both TNRS and WFO through a small provider interface.

The current daily-entry priority is the interactive species lookup used to
confirm author names while entering new species.
