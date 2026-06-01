Release Readiness
=================

This page defines the minimum release bar for the Ghini 4 baseline. It is
intended to keep release work focused on the workflows that must be reliable
before tagging a public release.

Ghini remains a GTK 3.24 application. Do not migrate to GTK 4 for this
release. Compatibility cleanup is acceptable only when it keeps GTK 3.24 as
the runtime target.

Release Goals
-------------

The first Ghini 4 release should establish a stable, reproducible development
and runtime baseline:

* Run on a current Ubuntu host through the Docker development image.
* Use pinned dependency locks so the same source revision resolves the same
  Python dependency set.
* Report a git-derived version that matches the tagged release and build
  commit.
* Support the normal SQLite workflow and the PostgreSQL workflow used by
  existing garden databases.
* Preserve the daily collection-entry workflow used for botanical records.
* Record known failures as tracked issues, not hidden manual knowledge.

Critical Release Components
---------------------------

The following areas are release-critical. A release candidate may be cut only
when each area either passes its gate or has an explicit release decision.

Runtime and packaging
~~~~~~~~~~~~~~~~~~~~~

* ``scripts/docker-dev build`` completes from a clean checkout.
* ``scripts/docker-dev app`` opens the GTK connection manager on the host
  display.
* The Docker image includes the runtime and development tools required by the
  supported workflow: GTK 3.24, PyGObject, SQLAlchemy 2, PostgreSQL client
  support, Kerberos support, pytest, Black, Dogtail, and the lock-file tooling.
* The root ``Dockerfile.dev``, lock files, ``.devcontainer``, ``.vscode``, and
  ``scripts/docker-dev`` are the supported development/runtime path. Older
  packaging paths can remain present, but must not be documented as the
  release path unless they are verified.
* The application title/version and package metadata come from the release tag
  and commit. A tagged release should display the tag version without an
  unknown fallback.

Database safety
~~~~~~~~~~~~~~~

* New SQLite database creation works.
* Existing PostgreSQL database connection works without losing saved
  connection settings.
* Schema creation, metadata initialization, and default data import pass on
  both SQLite and PostgreSQL.
* Date-only user fields use the configured local date. Audit timestamps use
  UTC.
* CSV/direct import paths do not introduce NOT NULL, sequence, transaction, or
  rollback regressions.
* Tests that create or reset a PostgreSQL schema run only against disposable
  databases.

Search and navigation
~~~~~~~~~~~~~~~~~~~~~

* Searches return correct results for:

  * all plants in a location
  * a specific species
  * a genus
  * an accession
  * a plant code

* Search entry history, clear/search buttons, and result counts remain stable.
* Autocomplete works where the daily workflow depends on it.
* Search result expansion, collapse, selection, double-click, and context-menu
  editing work without requiring a repeat search.
* Failed searches and empty result sets do not corrupt later searches.
* PostgreSQL dropped-connection recovery retries a search once and leaves the
  session usable.

Taxonomy workflow
~~~~~~~~~~~~~~~~~

* Family, genus, and species editors open from the menu and from workflow
  buttons.
* Genus autocomplete works when creating a species.
* Species creation supports author, rank, infraspecific epithet, vernacular
  name, and notes.
* The species editor can continue into accession creation.
* The interactive taxonomic lookup path is documented and points at a
  maintained service.
* The batch taxonomy-check workflow is either verified enough for release or
  documented as deferred with a GitLab issue.

Accession and source workflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Accession creation from a species works.
* Automatic accession IDs are generated and can be overridden.
* Type of material, quantity, date accessioned, date received, provenance, and
  wild status can be entered and saved.
* Source selection is usable for daily work:

  * existing sources are not duplicated in the selector
  * sources are sorted predictably
  * source autocomplete works
  * a new source can be created and selected without losing the accession
    workflow

* Source ID and notes persist.

Plant, location, and propagation workflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Plant creation from an accession works.
* Planting material, quantity, and location can be entered and saved.
* Location selection and new-location creation work from the plant workflow.
* Plant search and result editing work after save.
* Seed propagation can be added, edited, saved, and redisplayed with the correct
  date and type.
* Propagation regressions found during guided testing have automated coverage
  or tracked issues.

Import, export, and reporting
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* CSV/direct import and export pass the current regression suite.
* Import failure dialogs preserve the useful exception detail.
* Label/report paths used by the daily workflow open without tracebacks.
* Any unverified report or label feature is listed in the release notes as
  unverified, not silently treated as supported.

Documentation and issue accounting
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* ``doc/docker-development.md`` describes the supported Docker workflow.
* ``doc/gui-test-plan.md`` describes the current smoke, regression, guided, and
  manual test layers.
* ``doc/search-migration-accounting.md`` is up to date for migration decisions
  from the old search branch.
* ``doc/upstream-release-triage.md`` records which upstream GitHub issues are
  included, deferred, or already covered for this release.
* Open GitLab issues are classified before release:

  * ``release-blocker``: must be fixed before release.
  * ``release-deferred``: known issue accepted for this release.
  * ``needs-triage``: not yet reviewed for release impact.

Release Test Gates
------------------

Fast development gate
~~~~~~~~~~~~~~~~~~~~~

Run this before merging focused changes:

.. code-block:: sh

   scripts/docker-dev test-smoke

This gate should remain fast enough for daily development. It checks formatting,
version/database basics, GTK smoke coverage, and a small deterministic GUI E2E
subset.

Release regression gate
~~~~~~~~~~~~~~~~~~~~~~~

Run this before tagging a release candidate:

.. code-block:: sh

   scripts/docker-dev test-regression
   scripts/docker-dev postgres-check
   GHINI_EXTERNAL_POSTGRES_URI=postgresql://... scripts/docker-dev postgres-smoke

``test-regression`` is the no-intervention release gate. ``postgres-check`` is
separate because it owns a disposable PostgreSQL schema and should never point
at a real garden database. ``postgres-smoke`` is the read-only external
PostgreSQL smoke lane for a disposable representative database copy.

Guided visual release gate
~~~~~~~~~~~~~~~~~~~~~~~~~~

Guided visual scenarios are discovery and human-confirmation tools, not the
primary release gate. For ``v4.0.0rc1``, the release decision is to rely on the
automated no-intervention GUI E2E suite after guided findings have been fixed,
automated, or explicitly deferred. Rerun guided scenarios only when a visual
confirmation pass is wanted before tagging.

The guided scenarios that cover the supported daily workflow are:

.. code-block:: sh

   scripts/docker-dev gui-guided visual-smoke --sqlite-fixture
   scripts/docker-dev gui-guided connect-main-window --sqlite-fixture
   scripts/docker-dev gui-guided taxonomy-create --sqlite-fixture
   scripts/docker-dev gui-guided location-create --sqlite-fixture
   scripts/docker-dev gui-guided edit-record --sqlite-fixture
   scripts/docker-dev gui-guided delete-confirmation --sqlite-fixture
   scripts/docker-dev gui-guided daily-accession-workflow --sqlite-fixture
   scripts/docker-dev gui-guided propagation-workflow --sqlite-fixture

Guided tests are not a substitute for automated assertions. They are used for
workflow confirmation, visual behavior, and tester notes. Any failure found
during a guided pass must be fixed, automated, or recorded as a
release-deferred issue.

Real database gate
~~~~~~~~~~~~~~~~~~

Before final release, perform a read/write smoke pass against a disposable copy
of the user's PostgreSQL database or another representative PostgreSQL database.
Do not run destructive schema-reset tests against a production database.
Use ``scripts/docker-dev postgres-smoke`` for the automated read-only portion
of this gate; any manual read/write checks must still use a disposable copy.
Use ``scripts/docker-dev postgres-copy-smoke`` to copy representative data into
a disposable local PostgreSQL container and run the read-only smoke in one
step. See ``doc/postgresql-release-smoke.md`` for the manual procedure.

Release Decisions
-----------------

Use the following policy when deciding what blocks a release:

* Block the release when a defect can corrupt data, prevent startup, prevent
  connection to SQLite/PostgreSQL, break the daily taxonomy/accession/plant
  workflow, or invalidate the test infrastructure.
* Defer when a defect is outside the supported release workflow, has a safe
  workaround, and is recorded in GitLab with release notes.
* Do not block on migrating to GTK 4, resolving the full upstream GitHub issue
  backlog, or replacing every legacy feature if the supported workflow is
  documented and tested.

Release Candidate Process
-------------------------

1. Create or update the release milestone in GitLab.
2. Classify every open issue as blocker, deferred, duplicate, or not relevant
   to this release.
3. Freeze feature work except for release blockers and test-infrastructure
   fixes.
4. Run the fast development gate.
5. Run the release regression gate.
6. Review the guided visual decision. For ``v4.0.0rc1``, guided reruns are
   optional once the automated no-intervention GUI suite passes and prior
   guided findings are fixed, automated, or deferred.
7. Run the real PostgreSQL database gate against a disposable copy.
8. Update release notes with fixed issues, deferred issues, supported
   platforms, and test evidence.
9. Tag a release candidate, for example ``v4.0.0rc1``.
10. If the candidate passes, tag ``v4.0.0`` and create the GitLab release.

Reference Practices
-------------------

This release process follows a few established practices:

* GitLab releases package a tagged snapshot with release notes and evidence:
  https://docs.gitlab.com/user/project/releases/
* GNOME maintainers verify that the project builds and passes tests before
  tagging a release:
  https://handbook.gnome.org/maintainers/making-a-release.html
* GNOME uses freezes and release candidates near the end of a cycle:
  https://handbook.gnome.org/release-planning.html
* Python package versions should follow the packaging version rules:
  https://packaging.python.org/en/latest/discussions/versioning/
* Expected test failures should be explicit, reasoned, and tracked:
  https://docs.pytest.org/en/stable/how-to/skipping.html
