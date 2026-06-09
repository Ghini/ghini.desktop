Ghini 4.0.0rc1 Release Notes
============================

Status
------

These are draft release-candidate notes for the Ghini 4 baseline. Do not tag
``v4.0.0rc1`` until the pending release gates at the end of this document are
complete.

Supported Baseline
------------------

This release candidate targets the Docker development/runtime workflow on a
current Ubuntu host. The supported path is:

* GTK 3.24 through the Docker development image.
* Python dependencies from the repository lock files.
* SQLAlchemy 2 runtime behavior.
* SQLite databases for local testing and small deployments.
* PostgreSQL databases, including the disposable Docker PostgreSQL test lane.
* VS Code development against the Docker image.

Ghini remains a GTK 3 application. GTK 4 migration is intentionally out of
scope.

Daily Workflow Scope
--------------------

The release-candidate baseline focuses on the daily botanical collection
workflow:

* search for families, genera, species, accessions, plants, and locations;
* create and edit family, genus, and species records;
* use genus autocomplete while creating species;
* validate species names through the WFO-backed taxonomic lookup path;
* add vernacular names and notes;
* create accessions from species;
* select or create accession sources;
* create locations and plants;
* add and redisplay seed propagation records;
* edit records from the result tree context menu;
* handle delete confirmations without accidental removal.

Major Changes
-------------

Runtime and development
~~~~~~~~~~~~~~~~~~~~~~~

* Added the Docker/VS Code development workflow as the supported runtime and
  development path.
* Added pinned dependency locks and warning-gated test commands.
* Added Black to the Docker development image and check workflow.
* Added deterministic version reporting from git metadata.
* Added release smoke, regression, GUI E2E, guided visual, and PostgreSQL test
  commands through ``scripts/docker-dev``.

Database and SQLAlchemy 2
~~~~~~~~~~~~~~~~~~~~~~~~~

* Updated SQLAlchemy 2 behavior around transactions, raw SQL execution,
  relationship handling, and nullable schema fields discovered during import
  testing.
* Added a PostgreSQL disposable test lane.
* Fixed PostgreSQL closed-connection recovery for search/home navigation.
* Fixed sequence reset behavior and error reporting paths found during import
  testing.

GUI workflow
~~~~~~~~~~~~

* Restored autocomplete behavior in primary search and daily workflow
  selectors.
* Stabilized result-tree context-menu editing after search refreshes.
* Fixed result infobox tracebacks in daily searches for location, family,
  genus, and species results.
* Added automated GUI E2E coverage for search, edit, delete confirmation,
  creation, location, source, plant, and propagation workflows.
* Fixed propagation persistence and redisplay behavior found during guided
  testing.
* Fixed editor handling for vernacular-name persistence and database length
  validation.

Import and export
~~~~~~~~~~~~~~~~~

* Fixed quick CSV export handling for optional empty relationships.
* Added tests that accepted-name imports preserve both the original and
  accepted taxa.
* Kept useful exception details in import failure dialogs.

Taxonomic lookup
~~~~~~~~~~~~~~~~

* Added a normalized taxonomic lookup provider layer.
* Implemented WFO as the first provider for interactive species lookup.
* Kept the existing Species Editor callback behavior through a compatibility
  adapter.
* Verified live WFO lookup from the Docker image with HTTPS verification
  enabled.
* Updated the legacy manual batch TNRS workflow to point at the current TNRS
  site.

Fixed Release-Blocking Issues
-----------------------------

The following GitLab issues were fixed or reclassified for this release
candidate:

* #24 Replace legacy plant-name lookup with maintained TNRS/WFO-compatible
  service.
* #29 Stabilize accession source selector for daily accession workflow.
* #30 Restore autocomplete in primary search and daily workflow selectors.
* #32 Vernacular-name entry must persist without special Enter-key handling.
* #33 Quick CSV export must tolerate optional empty values.
* #34 Taxon import with accepted-name data must preserve both taxa.
* #35 Daily editor fields should validate or safely handle database length
  limits.
* #36 PlantsPlugin initialization fails when preferences are unavailable.
* #38 Main search field unusable after species editor save.
* #39 Species Notes editor can hang during routine species entry.
* #40 Daily searches log infobox tracebacks during result display.
* #41 Add Accession from new Species can fail with detached Species instance.
* #42 Add Accession can autoflush incomplete seed propagation during editor
  startup.

Deferred Issues
---------------

The following work is intentionally deferred from ``v4.0.0rc1``:

* #7 Triage the full upstream GitHub issue backlog.
* #37 Modernize batch taxonomy check with provider-backed lookup.

Known Scope Limits
------------------

* The root ``Dockerfile`` is older experimental packaging work. Use
  ``Dockerfile.dev`` and ``scripts/docker-dev`` for this release candidate.
* The batch taxonomy-check workflow remains a manual TNRS file-import workflow.
  It points at the current TNRS site, but provider-backed batch lookup is
  deferred to #37.
* Full report and label generation are not yet treated as release-blocking
  daily workflow gates unless a specific tested workflow is added before final
  release.
* GTK menu icon warnings are tracked as non-blocking unless they affect daily
  workflow behavior.

Test Evidence
-------------

Automated release evidence for current application code at ``5ff50632``:

* ``scripts/docker-dev test-smoke`` passed:

  * changed-file check: 16 passed;
  * GTK smoke suite: 156 passed;
  * core GUI E2E subset: 6 passed, 23 deselected.

* ``scripts/docker-dev gui-regression`` passed:

  * full automated Dogtail GUI E2E suite: 29 passed.

* ``scripts/docker-dev warnings`` passed:

  * warning-gated suite: 435 passed, 43 skipped.

* ``scripts/docker-dev postgres-check`` passed:

  * PostgreSQL lane against a disposable schema: 3 passed.

* ``scripts/docker-dev postgres-smoke`` passed against a disposable local
  PostgreSQL database initialized through the PostgreSQL lane:

  * external read-only smoke lane: 8 passed.

Earlier release evidence verified ``scripts/docker-dev build`` and
``postgres-copy-smoke`` against representative ``ghini_test3`` data. Rerun the
new ``postgres-release`` gate against a fresh representative copy before
tagging so the final PostgreSQL evidence matches the current commit.

* Open GitLab issue review completed at ``32b59e85``:

  * #31 remains open as the release tracker;
  * #7 and #37 remain open and are marked ``release-deferred``.

Earlier release hardening also verified a live WFO provider smoke query from
the Docker image. That check should be rerun if the release candidate is
rebuilt after additional dependency or certificate changes.

Pending Release Gates
---------------------

The following must be completed before tagging ``v4.0.0rc1``:

* Run ``GHINI_SOURCE_POSTGRES_URI=... scripts/docker-dev postgres-release``
  against a fresh representative PostgreSQL copy.
* Tag ``v4.0.0rc1`` after the PostgreSQL copy gate passes and final review is
  complete.

Guided visual scenarios are not a required ``v4.0.0rc1`` gate after the
automated GUI E2E suite passes. The guided scenarios were used to find release
blockers, and the current automated suite covers those regressions. They remain
available for optional visual confirmation before tagging.
