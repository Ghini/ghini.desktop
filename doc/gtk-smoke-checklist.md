# GTK 3.24 Smoke Checklist

This checklist closes the remaining GTK-related rows in
`doc/search-migration-accounting.md`. The application stays on GTK 3.24; do not
migrate to GTK 4. GTK 4 compatibility work is acceptable only when it does not
move the runtime target away from GTK 3.24.

Record each row as one of:

- `pass`: behavior works on GTK 3.24.
- `bug`: behavior fails and needs a focused fix.
- `superseded`: the old behavior is intentionally not used by the current UI.

## Row Coverage

- Remaining GTK rows: 52
- Covered by this checklist: 52
- Source branch rows: 9, 39, 41, 43, 47, 49, 50, 60, 66, 67, 68, 69, 88, 89,
  113, 114, 115, 116, 117, 118, 119, 120, 121, 123, 126, 128, 130, 131, 132,
  133, 134, 135, 136, 138, 139, 141, 142, 143, 144, 146, 147, 148, 149, 150,
  151, 152, 153, 154, 155, 156, 157, 159

## Environment

Use the current Docker development image and an isolated test database unless
explicitly verifying an existing PostgreSQL database.

Recommended setup:

```sh
scripts/docker-dev build
scripts/docker-dev gtk-smoke
```

The automated smoke suite runs under Xvfb inside the Docker development image.
It loads every Glade file, verifies the core widget IDs used by the main
workflows, and instantiates the key root windows/dialogs through
`GenericEditorView`.

Manual checks are still useful when changing behavior that depends on live user
interaction, database state, or visual layout. Before starting manual checks:

- Confirm the window title shows the git-derived application version.
- Confirm no GTK import/version warnings appear in the terminal during startup.
- Keep terminal output visible and capture any traceback with the checklist row.

## 1. Startup, Main Window, And Search

Covers rows: 47, 49, 66, 67, 68, 69, 88, 113, 118, 119, 120, 121, 123, 126,
141, 142, 143, 144, 146

- [ ] App reaches the connection manager and then the primary window.
- [ ] Main window menus populate without missing Insert/Edit/View actions.
- [ ] Insert submenu opens and contains expected object actions.
- [ ] Context menus open from search results without popup argument errors.
- [ ] Menu accelerators do not raise GTK warnings or tracebacks.
- [ ] CSS applies without GTK method errors.
- [ ] Search entry accepts text, clears text, and preserves cursor behavior.
- [ ] Search results populate, group, expand, collapse, and update selection.
- [ ] Hover or selection color changes do not break readability.
- [ ] Background work uses GLib idle callbacks without thread-enter/thread-leave
  warnings.
- [ ] Closing and reopening the main view does not leave stale boxes, menus, or
  running-thread warnings.

## 2. Connection Manager And Common Dialogs

Covers rows: 41, 43, 50, 60, 116, 117, 131

- [ ] Connection manager opens with saved connection names in the combo box.
- [ ] Add and Remove connection buttons work without deprecated response errors.
- [ ] Combo boxes can add, select, remove, and clear entries.
- [ ] PostgreSQL fields accept database, host, port, user, password flag, and
  picture-root values.
- [ ] File chooser opens for SQLite database and picture-root selection.
- [ ] File chooser OK and Cancel responses are handled correctly.
- [ ] Generic entry dialogs accept OK and Cancel responses correctly.
- [ ] Text extraction from entries and buffers returns strings, not bytes.

## 3. Family And Genus Editors

Covers rows: 9, 39, 114, 115, 128, 130, 132, 133, 134, 135, 136, 138, 139,
147, 148, 149, 150, 153, 154, 155, 159

- [ ] Family editor opens from Add and from search-result Edit.
- [ ] Required-field validation enables and disables OK correctly.
- [ ] Family completion and family drop-down behavior works in genus/species
  workflows.
- [ ] Genus editor opens from Add and from family Add Genus.
- [ ] Genus completion filters and selects without duplicate changed events.
- [ ] Deprecated table/packing replacements render labels, entries, buttons, and
  tabs with stable spacing.
- [ ] Buttons with icons render without `icon-size`, stock, or missing-icon
  warnings.
- [ ] Button images and labels fit their buttons.
- [ ] Add, OK, Cancel, and delete confirmation response values match the code.
- [ ] Context actions use named icons only where current GTK 3.24 UI expects
  named icons.

## 4. Species Editor

Covers rows: 9, 39, 114, 115, 128, 130, 131, 132, 133, 134, 135, 136, 138,
139, 147, 148, 151, 152, 153, 154, 155, 156, 157, 159

- [ ] Species editor opens cleanly from Add Species and from search-result Edit.
- [ ] Genus completion filters, displays family context, and selects a genus.
- [ ] Family completion drop-down still works through the species workflow.
- [ ] Species epithet entry strips spaces and handles hybrid marker input.
- [ ] Synonym warning box appears when entering a synonym genus/species and Yes
  or No updates the editor correctly.
- [ ] Tabs render and switch correctly: Species name, Additional info, Notes,
  Pictures.
- [ ] Notes tab can add, edit, and remove a note.
- [ ] Pictures tab opens, displays controls, and handles picture-root paths.
- [ ] OK, Add Accessions, Next, and Cancel responses match the intended editor
  flow.
- [ ] Notes and pictures do not leave detached widgets or duplicated boxes after
  repeated open/close cycles.

## 5. Accession, Plant, Location, Source, And Propagation Editors

Covers rows: 9, 39, 41, 50, 60, 114, 115, 116, 117, 130, 131, 132, 133, 134,
135, 136, 138, 147, 148, 154, 155, 159

- [ ] Accession editor opens from Add Accession and from species Add
  Accessions.
- [ ] Species completion and verification taxon completion work.
- [ ] Verification boxes add, expand, collapse, and remove correctly.
- [ ] Source tab widgets render with correct labels and spacing.
- [ ] Plant editor opens from Add Plant and from accession Add Plants.
- [ ] Split mode opens and validates required accession, code, location, reason,
  and date fields.
- [ ] Location editor opens from Add Location and Edit Location buttons.
- [ ] Propagation editor opens from plant/source flows and handles date widgets.
- [ ] Date buttons open calendar controls and write dates back to entries.
- [ ] Delete confirmations display question icons/buttons and return the correct
  response.
- [ ] File chooser and picture-root controls work from garden editors.

## 6. Notes, Pictures, Infoboxes, And Bottom Notebook

Covers rows: 39, 89, 114, 130, 134, 135, 136, 138, 147, 148, 149, 150, 154,
155, 156, 157, 159

- [ ] Main search result infoboxes render properties with expected labels.
- [ ] Bottom notebook pages appear for notes and pictures when selecting rows.
- [ ] Notes glade content displays in both editor and main-window contexts.
- [ ] Pictures glade content displays in both editor and main-window contexts.
- [ ] Icon-name changes do not produce missing image placeholders.
- [ ] Repeated row selection does not duplicate infobox pages or crash.

## 7. Completion Criteria

After the smoke pass:

- Update `doc/search-migration-accounting.md` rows from `GTK 3.24 compatibility
  review` to one of the closed decisions or bug references.
- Keep any fixes small and atomic.
- Re-run:

```sh
scripts/docker-dev check
scripts/docker-dev warnings
```

The GTK accounting bucket is closed only when every row is either verified,
fixed, or intentionally superseded.
