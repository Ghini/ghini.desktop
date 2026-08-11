# Upstream Release Triage

This document records the first release-focused pass over open upstream GitHub
issues in `Ghini/ghini.desktop`.

Reviewed source:

- Upstream repository: <https://github.com/Ghini/ghini.desktop>
- Open upstream issue list reviewed with `gh issue list` on 2026-05-23.
- Local release policy: [release-readiness.rst](release-readiness.rst)

The goal is not to bulk-import the upstream backlog. The first Ghini 4 baseline
release should include only issues that affect startup, data integrity,
database compatibility, search/navigation, or the daily
taxonomy-to-accession-to-plant workflow.

## Already Covered Or Superseded

| Upstream | Decision | Local coverage |
| --- | --- | --- |
| [#425](https://github.com/Ghini/ghini.desktop/issues/425) Error `(psycopg2.InterfaceError) connection already closed` | Covered | Closed locally by PostgreSQL dropped-connection recovery and `postgres-check` coverage. |
| [#308](https://github.com/Ghini/ghini.desktop/issues/308) Missing timezone in MapperBase timestamps | Covered | Closed locally by local date/UTC audit timestamp policy. |
| [#130](https://github.com/Ghini/ghini.desktop/issues/130) Cannot expand row if expanded while nothing depends on it | Covered | Closed locally by result expansion retry fix and GTK smoke coverage. |
| [#463](https://github.com/Ghini/ghini.desktop/issues/463) The Plant List to World Flora Online | Imported | Covered by GitLab #24. |
| [#472](https://github.com/Ghini/ghini.desktop/issues/472) TNRS moved | Imported | Covered by GitLab #24. |
| [#111](https://github.com/Ghini/ghini.desktop/issues/111) Autocomplete for manual query properties | Partially imported | Daily-workflow autocomplete is covered by GitLab #30; full query-builder-style completion remains deferred. |
| [#58](https://github.com/Ghini/ghini.desktop/issues/58) ID format and wild status in accession editor | Covered by release gate | The current Accession Editor exposes ID format and wild status fields. Keep this in the daily workflow guided test rather than importing separately unless testing fails. |
| [#72](https://github.com/Ghini/ghini.desktop/issues/72) Error creating connection manager presenter | Covered by release gate | Connection manager startup is covered by automated and guided tests. Import only if reproduced on GTK 3.24. |

## Include In Release Scope

These issues should either be fixed before `v4.0.0` or explicitly reclassified
after current-code reproduction.

| Upstream | Release reason | Local action |
| --- | --- | --- |
| [#95](https://github.com/Ghini/ghini.desktop/issues/95) Vernacular-name entry requires Enter to persist | Daily species workflow includes adding vernacular names for labels. Losing the value is data loss from the user's perspective. | Imported as GitLab #32. |
| [#461](https://github.com/Ghini/ghini.desktop/issues/461) Quick CSV export stops on `None` values | Export should tolerate optional fields. This is part of the import/export release gate. | Imported as GitLab #33. |
| [#441](https://github.com/Ghini/ghini.desktop/issues/441) Taxon import with `accepted` field does not import both taxa | Taxonomic import/data integrity issue. It overlaps the SQLAlchemy/import regression gate. | Imported as GitLab #34. |
| [#399](https://github.com/Ghini/ghini.desktop/issues/399) Text entries do not validate database field lengths | Can turn normal editor input into database errors, especially for long location/source names. | Imported as GitLab #35, scoped to daily editors first. |
| [#55](https://github.com/Ghini/ghini.desktop/issues/55) Intended-location buttons do not activate | Accession and plant workflow touches intended/current location controls. | Include in daily workflow verification; import if reproduced. |
| [#56](https://github.com/Ghini/ghini.desktop/issues/56) New accession reuses previous intended locations | Could silently attach wrong location state during accession entry. | Include in daily workflow verification; import if reproduced. |
| [#252](https://github.com/Ghini/ghini.desktop/issues/252) Empty location cannot be deleted after prior use | Relationship/cascade behavior can affect cleanup after plant moves. | Reproduce after relationship audit; likely release-deferred unless daily cleanup fails. |
| [#157](https://github.com/Ghini/ghini.desktop/issues/157) Deleted top-level objects remain in result view | Search-result state after deletion is part of navigation safety. | Include in delete-confirmation regression; import if current coverage does not prove it fixed. |

## Defer From First Baseline Release

These issues may matter later, but should not block the first stable Ghini 4
baseline unless a current test proves they break the supported workflow.

| Upstream | Decision |
| --- | --- |
| [#9](https://github.com/Ghini/ghini.desktop/issues/9) User-defined type-of-material values | Useful enhancement; current release only requires existing type choices to save correctly. |
| [#14](https://github.com/Ghini/ghini.desktop/issues/14) User-defined reason for current change | Enhancement; not needed for baseline workflow. |
| [#15](https://github.com/Ghini/ghini.desktop/issues/15) List for accession intended locations | Enhancement; verify current controls but do not expand behavior for baseline. |
| [#36](https://github.com/Ghini/ghini.desktop/issues/36) Provenance list | Enhancement/question; current list must work, but expanding it can wait. |
| [#63](https://github.com/Ghini/ghini.desktop/issues/63) Identification qualifier spacing | Display-quality bug; defer unless user workflow depends on qualified accession labels. |
| [#98](https://github.com/Ghini/ghini.desktop/issues/98) Accession ID qualifier semantics | Broader taxonomy/design question; defer. |
| [#180](https://github.com/Ghini/ghini.desktop/issues/180) Notes tab in propagations | Enhancement; propagation save/display is the release-critical path. |
| [#235](https://github.com/Ghini/ghini.desktop/issues/235) Accession source categories | Enhancement; source selector correctness is covered locally by GitLab #29. |
| [#454](https://github.com/Ghini/ghini.desktop/issues/454) Authors missing on some labels | Defer unless label output becomes part of the `v4.0.0` acceptance test. |
| [#466](https://github.com/Ghini/ghini.desktop/issues/466) Quantity units and fuzzy support | Enhancement/design work; current numeric quantity must save correctly. |
| [#465](https://github.com/Ghini/ghini.desktop/issues/465) Better plant culture information | Enhancement/design work. |
| [#458](https://github.com/Ghini/ghini.desktop/issues/458) GBIF as taxonomic source | Provider decision belongs to GitLab #24, not baseline runtime stability. |
| [#457](https://github.com/Ghini/ghini.desktop/issues/457) Implement autonyms | Taxonomy enhancement; defer. |
| [#444](https://github.com/Ghini/ghini.desktop/issues/444) Improved renaming and synonyms workflow | Important but larger than baseline stabilization. |
| [#403](https://github.com/Ghini/ghini.desktop/issues/403) Windows installer | Out of scope for Ubuntu/Docker baseline release. |
| [#432](https://github.com/Ghini/ghini.desktop/issues/432), [#325](https://github.com/Ghini/ghini.desktop/issues/325), [#245](https://github.com/Ghini/ghini.desktop/issues/245) macOS/OSX items | Out of scope for Ubuntu/Docker baseline release. |

## Follow-Up

1. Add current-code reproduction tests before fixing broad issues.
2. Decide whether upstream #55, #56, #157, and #252 reproduce on
   `ghini-4-dev-clean`.
3. Update this table when an upstream issue is fixed, imported, or explicitly
   deferred.
