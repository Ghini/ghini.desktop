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

Application release gates completed on ``ghini-4-dev-clean`` at ``9919e220``:

* ``scripts/docker-dev test-smoke`` passed:

  * warning-gated base check: 16 passed;
  * GTK smoke suite: 142 passed;
  * core GUI E2E subset: 5 passed, 17 deselected.

* ``scripts/docker-dev test-regression`` passed:

  * warning-gated suite: 415 passed, 28 skipped;
  * GTK smoke suite: 142 passed;
  * full GUI E2E suite: 22 passed.

* ``scripts/docker-dev postgres-check`` passed:

  * PostgreSQL lane: 3 passed.

* ``scripts/docker-dev postgres-smoke`` was validated against a temporary
  PostgreSQL database seeded by the disposable PostgreSQL lane:

  * external read-only smoke lane: 4 passed.

Earlier release hardening also verified ``scripts/docker-dev build`` and a live
WFO provider smoke query from the Docker image. Those checks should be rerun if
the release candidate is rebuilt after additional dependency or certificate
changes.

Pending Release Gates
---------------------

The following must be completed before tagging ``v4.0.0rc1``:

* Guided visual release scenarios:

  * ``visual-smoke``
  * ``connect-main-window``
  * ``taxonomy-create``
  * ``location-create``
  * ``edit-record``
  * ``delete-confirmation``
  * ``daily-accession-workflow``
  * ``propagation-workflow``

  These guided scenarios were used to find and verify several release blockers,
  and the current automated GUI E2E suite covers those regressions. They have
  not been rerun on ``9919e220`` because the current release work is using
  no-intervention testing. Before tagging, either rerun them as a visual
  confirmation pass or record an explicit release decision to rely on the
  automated evidence above.

* A real PostgreSQL smoke pass against a disposable representative database
  copy, not a production database. Use ``scripts/docker-dev postgres-smoke``
  for the automated read-only portion of this gate.
* Final review of open GitLab issues to confirm only release-deferred work
  remains open.
* Tag ``v4.0.0rc1`` after the pending gates pass.
