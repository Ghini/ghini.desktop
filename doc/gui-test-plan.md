# GUI Test Plan

This plan defines the supported GUI test layers for Ghini Desktop. The goal is
high-value confidence in critical workflows without turning GUI testing into an
unbounded manual burden.

Ghini remains a GTK 3.24 application. Do not migrate to GTK 4 as part of GUI
test work.

## Test Layers

### Fast Development Smoke

Command:

```sh
scripts/docker-dev test-smoke
```

This is the short no-intervention suite for day-to-day development. It should
finish quickly enough to run before committing focused changes. It combines:

- formatting and version/database checks
- GTK smoke checks
- a small stable subset of Dogtail GUI E2E tests for startup, search, and
  simple create workflows

Keep this suite conservative. Add a test to smoke only when it is deterministic,
fast, and covers a workflow whose failure should stop normal development.

### Full Release Regression

Command:

```sh
scripts/docker-dev test-regression
```

This is the no-intervention release gate. It is expected to take longer than
the smoke suite and should be run before release or merge-request review. It
combines:

- warning-gated pytest coverage
- GTK smoke checks
- the full automated Dogtail GUI E2E suite

Known failures must be marked `xfail` with a GitLab issue reference. When a
guided visual run finds a bug and the fix is stable, add or update an automated
regression in this layer whenever practical.

### Headless Automated

Command:

```sh
scripts/docker-dev gui-e2e
```

This layer runs the real application under Xvfb and drives it through Dogtail
and AT-SPI. It should assert objective state:

- dialogs and main windows open
- required buttons and fields exist
- small workflows complete
- database rows match the GUI action

Use this layer for deterministic regressions. Do not use it to inspect layout
quality or subjective usability.

### Guided Visual

Command:

```sh
scripts/docker-dev gui-guided --list
scripts/docker-dev gui-guided visual-smoke --sqlite-fixture
scripts/docker-dev gui-guided connect-main-window --sqlite-fixture
scripts/docker-dev gui-guided taxonomy-create --sqlite-fixture
scripts/docker-dev gui-guided location-create --sqlite-fixture
scripts/docker-dev gui-guided edit-record --sqlite-fixture
scripts/docker-dev gui-guided delete-confirmation --sqlite-fixture
scripts/docker-dev gui-guided daily-accession-workflow --sqlite-fixture
scripts/docker-dev gui-guided connection-manager
scripts/docker-dev gui-guided propagation-workflow
scripts/docker-dev gui-guided --summary
scripts/docker-dev gui-guided --issue-body
```

This layer runs the application visibly on the host display and prompts the
tester at workflow checkpoints. The tester confirms a set of expected outcomes
and may add free-text notes. Results are written to:

```text
test-results/gui-guided/
```

Guided testing should not prompt for every assertion. Prompts are reserved for
workflow-level confirmation, visual inspection, and unexpected observations.
The runner pauses after launch and before closing the application so the tester
can inspect the visible window at useful points.

Use `--summary` after a guided run to print the latest JSON result in a readable
form. Pass an artifact path to summarize a specific run.

Use `--issue-body` after a guided run to print a GitLab-ready markdown issue
body for the latest JSON result. Pass an artifact path to generate an issue body
for a specific run. The generated body includes failed checkpoint notes, branch
and commit, fixture details, and captured stdout/stderr.

Use `--sqlite-fixture` when the scenario should run against a disposable,
known-good SQLite database instead of saved local connection settings. The
fixture currently creates a `Guided SQLite` connection and seeds a searchable
`Guidedaceae` taxonomy chain, `Guided Test Institution` metadata, accession
`GUIDED-ACC-001`, plant `GUIDED-ACC-001.1`, and location `GLOC` for guided
scenarios. The Institution Editor should not appear during fixture startup;
record it as an unexpected observation if it does.

### Manual Checklist

Manual checklist coverage remains useful for broad exploratory review and for
areas not yet automated. The current GTK checklist is:

```text
doc/gtk-smoke-checklist.md
```

Manual-only checks should be converted to guided or automated tests only when
the workflow is important enough to justify maintenance.

## Promotion Policy

Guided visual tests are for discovery and human confirmation. Automated suites
are for repeatable confidence. For every guided finding:

- If the behavior is stable and objectively assertable, add a regression test.
- If it is a primary workflow and fast enough, include it in `test-smoke`.
- If it is important but slow or broad, include it in `test-regression`.
- If it cannot be automated cleanly, leave the GitLab issue with the guided
  artifact and the reason automation is deferred.

## Critical Paths

The following paths are the initial target set. This is intentionally narrow.
For release readiness, these paths are the baseline. A release candidate should
not be tagged until each row is either covered by the automated/guided gates or
explicitly deferred in GitLab and release notes. See
`doc/release-readiness.rst` for the release-blocker policy.

| Path | Headless | Guided | Notes |
| --- | --- | --- | --- |
| Connection manager opens | yes | yes | Validates startup and saved connection UI. |
| Connect to database and open main window | yes | yes | Use SQLite for automation; PostgreSQL for guided local checks. |
| Search existing records | yes | yes | Species, accession, and plant searches covered by Dogtail E2E. |
| Create family/genus/species | yes | yes | Guided scenario: `taxonomy-create`. |
| Create accession from species | yes | optional | Covered by Dogtail E2E. |
| Select existing accession source | yes | yes | Covered by Dogtail E2E; guided in `daily-accession-workflow`. |
| Create location | yes | yes | Guided scenario: `location-create`. |
| Create plant from accession | yes | yes | Covered by Dogtail E2E; guided test checks usability. |
| Create seed propagation from plant | yes | yes | Dogtail E2E verifies seed propagation and database state. |
| Edit existing family/genus/species/accession/plant/location | partial | yes | Family, accession, location, and plant edit pass; genus/species edit remain covered by creation-chain and guided workflows. |
| Delete/remove confirmation dialogs | yes | yes | Family delete cancel/confirm covered by Dogtail E2E. |

## Release Gate Mapping

Use this gate sequence before a release candidate:

1. `scripts/docker-dev test-smoke`
2. `scripts/docker-dev test-regression`
3. `scripts/docker-dev postgres-check`
4. `scripts/docker-dev postgres-copy-smoke` against a disposable
   representative PostgreSQL database copy
5. Optional guided visual scenarios for startup, connection, taxonomy creation,
   location creation, record editing, delete confirmation, daily accession
   workflow, and propagation workflow

Known failures are acceptable only when they are marked `xfail` or recorded in
GitLab with a release decision. A defect should block release when it affects
startup, database connection, data integrity, search/navigation, or the daily
taxonomy-to-accession-to-plant workflow.

For `v4.0.0rc1`, the guided visual scenarios are not a required gate after the
automated GUI E2E suite passes. Guided runs remain useful for discovery and
visual confirmation, but release confidence comes from the no-intervention
smoke/regression/PostgreSQL gates and from converting guided findings into
automated tests or tracked release decisions.

## Bug Recording Policy

Every unexpected GUI failure found during automated or guided testing must be
recorded in GitLab unless it is fixed immediately in the same focused change.

Use these templates:

- `GUI test finding`
- `Manual test note`
- `Python issue`

Recommended labels:

- `bug`
- `gui`
- `guided-test`
- `headless-test`
- `gtk3`
- `sqlalchemy-2`
- `needs-investigation`

When an automated test is marked `xfail`, include the GitLab issue ID in the
reason once the issue exists. Example:

```python
@pytest.mark.xfail(reason="gitlab#123: propagation save chain does not persist")
```

## Guided Test Result Handling

Guided runs create ignored JSON artifacts under `test-results/gui-guided/`.
Artifacts include checkpoint results, tester notes, the Git branch and commit,
the display value, application return code, and captured stdout/stderr. If any
checkpoint result is `fail`, create a GitLab issue and include:

- scenario name
- checkpoint name
- tester notes
- app stdout/stderr from the JSON artifact
- screenshots if available
- branch and commit tested

The helper command below generates a clean starter body with those fields:

```sh
scripts/docker-dev gui-guided --issue-body
scripts/docker-dev gui-guided --issue-body test-results/gui-guided/<artifact>.json
```

Do not commit routine guided result artifacts. Commit a guided result only when
it is intentionally used as evidence for a regression or merge request.

GitLab #6 recorded the initial guided visual workflow implementation. Keep this
plan current when adding or retiring guided scenarios.

## Development Rules

- Prefer headless tests for objective behavior.
- Prefer guided tests for visual confirmation and human workflow review.
- Keep GUI tests scenario-sized, not assertion-by-assertion user prompts.
- Seed prerequisite data directly when the test target is a downstream workflow.
- Verify GUI changes with direct database assertions when records should be
  created, updated, or deleted.
- Record current failures as GitLab issues or `xfail` tests instead of silently
  skipping them.
