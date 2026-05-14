# GUI Test Plan

This plan defines the supported GUI test layers for Ghini Desktop. The goal is
high-value confidence in critical workflows without turning GUI testing into an
unbounded manual burden.

Ghini remains a GTK 3.24 application. Do not migrate to GTK 4 as part of GUI
test work.

## Test Layers

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
scripts/docker-dev gui-guided visual-smoke
scripts/docker-dev gui-guided connection-manager
scripts/docker-dev gui-guided propagation-workflow
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

### Manual Checklist

Manual checklist coverage remains useful for broad exploratory review and for
areas not yet automated. The current GTK checklist is:

```text
doc/gtk-smoke-checklist.md
```

Manual-only checks should be converted to guided or automated tests only when
the workflow is important enough to justify maintenance.

## Critical Paths

The following paths are the initial target set. This is intentionally narrow.

| Path | Headless | Guided | Notes |
| --- | --- | --- | --- |
| Connection manager opens | yes | yes | Validates startup and saved connection UI. |
| Connect to database and open main window | yes | yes | Use SQLite for automation; PostgreSQL for guided local checks. |
| Search existing records | todo | yes | Tracked by GitLab #3. |
| Create family/genus/species | yes | optional | Taxonomy creation is already covered by Dogtail E2E. |
| Create accession from species | yes | optional | Covered by Dogtail E2E. |
| Create location | yes | optional | Covered by Dogtail E2E. |
| Create plant from accession | yes | yes | Covered by Dogtail E2E; guided test checks usability. |
| Create seed propagation from plant | xfail | yes | Current GUI test documents GitLab #2. |
| Edit existing family/genus/species/accession/plant/location | todo | yes | Tracked by GitLab #4. |
| Delete/remove confirmation dialogs | todo | yes | Tracked by GitLab #5. |

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

Do not commit routine guided result artifacts. Commit a guided result only when
it is intentionally used as evidence for a regression or merge request.

Tracked follow-up: GitLab #6 covers making the guided visual workflow repeatable
across the current critical-path scenarios.

## Development Rules

- Prefer headless tests for objective behavior.
- Prefer guided tests for visual confirmation and human workflow review.
- Keep GUI tests scenario-sized, not assertion-by-assertion user prompts.
- Seed prerequisite data directly when the test target is a downstream workflow.
- Verify GUI changes with direct database assertions when records should be
  created, updated, or deleted.
- Record current failures as GitLab issues or `xfail` tests instead of silently
  skipping them.
