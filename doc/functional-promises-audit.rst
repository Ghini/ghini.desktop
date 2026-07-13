Ghini — functional-promises audit
================================================

A reminder of the functionality declared by the software, to be used as a minimal usability / functional-promises audit.
This is not an introductory manual: it's a list of features with a corresponding reproducible test.

Sources:

- current documentation, https://ghini.readthedocs.io (ghini-1.0-dev version)
- seven screencast transcripts produced over 10 years ago (versions 1.0.54/1.0.55), cited only where they show a behavior no longer described in the current docs

Conventions:

- **Promise**: declared behavior, in one line
- **Test**: steps to reproduce it and expected result
- 🎥 = item reconstructed from video, not present in the current docs: verify whether the behavior still exists before treating it as a valid promise
- ⚠️ = the docs themselves flag the feature as incomplete or a stub

1. Connection and first run
-----------------------------

**Promise**: on the very first activation, with no connections configured, Ghini warns the user and guides them through creating a connection.

Test:

1. Start Ghini with no saved connection.
2. Expected: a "no connection" alert appears, inviting the user to use **Add**.
3. Click Add, enter a meaningful name (e.g. "my garden").
4. Expected: return to the previous screen with the new connection selected and Connection Details expanded.

-----

**Promise**: with SQLite and "Use default locations" active, the connection name alone is enough to create a working database.

Test:

1. Create a connection, leave "Use default locations" active, click Connect.
2. Expected: Ghini creates a ``.db`` file with the same name as the connection and a same-named pictures folder (in ``~/.bauble`` on Linux/macOS, in ``AppData\Roaming\Bauble`` on Windows).

-----

**Promise**: if the connection points to a database Ghini has never seen before, explicit confirmation is requested before initializing it, because initialization empties any pre-existing content.

Test:

1. Connect to an empty or non-Ghini file/database.
2. Expected: empty-database alert, followed by a "do you want to create it?" prompt with Yes/No.
3. Answer Yes.
4. Expected: tables are created and the default taxonomic dataset is imported (this can take a minute or two).

-----

🎥 **Promise**: during first run, Ghini offers (or used to offer) a user registration form — name and email address — used to contact the user in case the program automatically detects a technical problem.

Test:

1. Complete first run on a new database.
2. Check whether a registration form with name/email still appears.
3. If absent: the promise "I can be contacted in case of error" is no longer kept in its original form.
4. Note this as a deviation, not a bug, and check whether an equivalent mechanism exists (e.g. error reporting, see section 8).

-----

**Promise**: on reopening, Ghini automatically suggests the last connection used.

Test:

1. Close and reopen Ghini after having used a connection.
2. Expected: the previous connection is preselected; Enter or clicking Connect leads directly to the Home screen.

2. Data entry — base entities
------------------------------

**Promise**: :menuselection:`Insert --> Location` creates a new location with a name and a unique code.

Test:

1. :menuselection:`Insert --> Location`.
2. Enter a name (e.g. "Greenhouse 1 Table 1") and a unique short code.
3. Expected: the location appears in the Home overview, the "Locations" counter increases, marked as not yet used.

-----

**Promise**: a location can be created specifying only the code, without a full name.

Test:

1. :menuselection:`Insert --> Location`, fill in only the code, save.
2. Expected: no blocking validation error.

-----

**Promise**: :menuselection:`Insert --> Species` offers autocompletion on the genus and allows spelling/taxonomic verification through an online reference service, also retrieving the authorship.

Test:

1. :menuselection:`Insert --> Species`, type a partial genus (e.g. "Cyc").
2. Expected: a completion list with genera existing in the reference dataset.
3. Type a specific epithet with a deliberate spelling mistake.
4. Start the online verification/query.
5. Expected: a response with the closest correct spelling and the associated authorship; the option to import the result into the record.
6. Multiple-result case: a query returning more than one result (e.g. a hybrid plus a synonym of the accepted name) must allow importing several entries in a single pass, without having to repeat the query.

-----

**Promise**: :menuselection:`Insert --> Accession` links an existing species to a group of plants of the same origin/propagule type, with autocompletion on the taxonomic name.

Test:

1. :menuselection:`Insert --> Accession`, type the taxon name: expected automatic completion.
2. Enter the Accession ID and the quantity received.
3. Save. Expected: the new accession is visible and linked to the chosen species.

-----

**Promise**: identification uncertainty can be declared via a qualifier (e.g. "cf.") at a specific rank.

Test:

1. In Accession, choose a taxon, set the identification qualifier to "cf." at rank "species".
2. Expected: the record saves and shows the uncertainty without blocking entry.

-----

**Promise**: every main editor (Family, Genus, Species, Accession) allows chained entry: an "Add Genera/Species/Accession" button saves the current record and immediately opens the editor for the child; a "Next" button saves and opens a new blank editor of the same type.

Test:

1. Open the Family editor, fill it in, click "Add Genera".
2. Expected: the Family is saved and a Genus editor opens already linked to that Family.
3. Repeat with "Next" on a Genus: expected blank Genus editor, with the previous Genus saved.

-----

**Promise**: Plant is linked both to an Accession and to a Location; multiple plants can be created in one go using a range syntax in the code field (creation only, not when editing).

Test:

1. :menuselection:`Insert --> Plant`, in the code field type a range, e.g. ``3-5``.
2. Expected: the field turns blue to signal multi-creation mode; on save, codes 3, 4, 5 are created.
3. Also try a combined syntax, e.g. ``1,4-7,25``: expected creation of codes 1, 4, 5, 6, 7, 25.
4. Expected: any value set in the other fields while in this mode is copied to all the plants created.
5. Verify that the same syntax is NOT available when editing an already-existing Plant.

-----

**Promise**: every record can have text Notes; a URL entered in a note generates a link visible in the Links panel when the record is selected.

Test:

1. Open the Notes of a record, enter a note containing a URL.
2. Expected: when selecting the record in the search results, the URL appears as a clickable link in the Links panel.

-----

**Promise**: the "danger zone" section of the Location editor allows merging the current location into another one, to correct typos or implement policy changes.

Test:

1. Open the editor of a Location with associated plants, expand the danger zone, perform a merge into another existing location.
2. Expected: the plants end up reassigned to the destination location; the origin location ends up empty or removed.

3. Pictures / images
----------------------

**Promise**: Plant and Species have a "Pictures" tab for associating images; the image is copied into the configured pictures folder and a 500×500 thumbnail is generated in a thumbnails subfolder.

Test:

1. In Plant or Species, Pictures tab, associate an image file.
2. Expected: the file is copied into the connection's pictures folder; a 500×500 thumbnail appears in the thumbnails subfolder.

-----

**Promise**: images are not stored in the database (as of version 1.0.62) — only the path, as a special note of category ``<picture>``; sharing across workstations requires a network folder or a file-sync service.

Test:

1. Associate an image with a plant, then inspect the Notes of that same record.
2. Expected: a note of category ``<picture>`` appears, with the path relative to the pictures root folder.
3. Verify that the database file has not grown significantly in size after adding heavy images (a sign that the image is not embedded in the DB).

-----

**Promise**: selecting a Plant or a Species in the results shows its images in the pictures panel on the left; selecting an Accession shows the images of all the plants in that accession.

Test:

1. Select in sequence a Plant with photos, a Species with photos, an Accession whose plants have photos.
2. Expected in all three cases: pictures panel populated consistently with the rule above.

-----

**Promise**: a Species can be associated with a "by reference" image (external URL) instead of a local file, via a note of category ``<picture>`` with the URL as text.

Test:

1. On a Species, Notes → new note, category ``<picture>``, text = URL of an illustration.
2. Expected: behavior analogous to a normal picture note, but pointing to a remote resource.

-----

**Promise**: there is a tool for bulk-importing a pictures collection already organized on the file system, deriving accession/plant/species from the file name according to a rule declared by the user.

Test (:menuselection:`Tools --> Import --> Pictures`):

1. Prepare a small folder of images with names that include an accession number and, in some cases, the species name (e.g. ``2018.0020.1 (4) Epidendrum.jpg``).
2. Start the import, specifying the folder, a "recursive" yes/no option, a default location for new plants, and the naming rule.
3. Expected, in the review step: one row per image, with the data extracted from the file name, sortable by column, with the option to choose row by row what to import and what not.
4. Proceed to the final step: expected a commit/rollback log; on confirmation, expected actual creation (or modification) of the locations and plants involved, with a corresponding note tracking the import.
5. Verify that, after the commit, the images are visible in the pictures panel of the created plants.
6. Verify the behavior of "Previous" (going back to correct things) and "Cancel" (aborting with no change at all to the database) before final confirmation.

4. Search
-----------

**Promise**: Ghini offers four distinct search strategies — by value, by expression, by binomial name, by query — all case-insensitive except binomial search.

Test: for each strategy, a minimal search:

- by value: type a single word (e.g. a genus) in the search bar without specifying a domain. Expected: results of several types (domains) containing that string in any field.
- by expression: type ``gen=GenusName``. Expected: only Genus entries that match exactly.
- by expression with wildcard: type ``loc like block%``. Expected: all Locations whose name or code starts with "block".
- by binomial name: type two words with correct capital+lowercase initials, e.g. ``So ha``. Expected: only Species compatible with those genus/epithet initials.
- by query: type a query with syntax ``domain WHERE expression``, e.g. ``location WHERE plants = Empty``. Expected: only Locations with no associated plants.

-----

**Promise**: a search with several unquoted words is interpreted as an OR between the words; in quotes, it's treated as a single string.

Test:

1. Search ``Block 10`` (unquoted) vs ``"Block 10"`` (quoted).
2. Expected: different results, the second more restrictive (exact string match).

-----

**Promise**: if a search string doesn't form a valid expression, Ghini automatically falls back to search by value, even if this produces an excessive number of results.

Test:

1. Type a malformed expression, e.g. ``gen lik maxillaria`` (wrong operator).
2. Expected: no blocking error; result equivalent to a search by value on the three words.

-----

**Promise**: the Query Builder visually generates a syntactically valid query, supports AND/OR between clauses, and correctly translates the special values ``None`` and ``Empty``.

Test:

1. Open the Query Builder (icon to the left of the search bar, or :menuselection:`Tools --> Query Builder`).
2. Choose a domain, add two clauses connected by AND.
3. Expected: the generated query appears in the search bar and is executable, and remains editable by hand.
4. Build a clause that compares a set-field with ``Empty`` (e.g. an accession's plants).
5. Expected: the generated query correctly uses ``Empty`` as a reserved term, not as a quoted string.

-----

🎥 **Promise**: the Home screen offers some slots/buttons for stored queries, recallable with a click, each with a configurable tooltip, and a dedicated editor for modifying them ("Edit stored queries").

Test:

1. Verify the existence, in the Home screen, of a "stored queries" section with slots/buttons.
2. Verify whether it is now possible to save a new query directly into a slot from the interface (in the video this step still had to be done "by hand", outside the interface: check whether this has been resolved).
3. Run an existing stored query with a click. Expected: the query runs and the result count appears in the overview.
4. Verify the presence and functioning of "Edit stored queries" for modifying existing queries.
5. Verify the handling of an overly long slot label (in the video it was truncated, showing only the beginning and end of the string).

5. Propagations
-----------------

**Promise**: a Propagation trial can be created only starting from an existing Plant (Propagation tab of the Plant editor → Add); the propagation type, once chosen, is immutable.

Test:

1. Open a Plant, Propagation tab, Add.
2. Choose a propagation type, enter the data, save.
3. Reopen the propagation in edit mode: expected all fields editable except the type.

-----

**Promise**: in seed propagations, the "seed parent" must always be associated; in Ghini 1.0 the "pollen parent" is recorded in a free-text Notes field (not in a dedicated relational field).

Test:

1. Create a seed propagation on a Plant.
2. Verify that the associated parent is the seed parent, and that there is a way (a note) to record the pollen parent.

-----

**Promise**: a successful propagation can generate a new Accession by selecting "Garden Propagation" as Contact in the Source tab of the Accession editor; typing the plant number shows only plants with propagation trials; selecting a plant shows only propagations not yet accessioned.

Test:

1. Create a new Accession, go straight to the Source tab.
2. Select Contact "Garden Propagation".
3. Type the number of a plant that has propagations: expected autocompletion limited to plants with propagations.
4. Select the plant: expected a list of propagations not yet accessioned for that plant.
5. Select one, confirm. Expected: the Taxon, Type of material (and Provenance, if known) fields in the General tab are automatically populated from the propagation data, while still remaining editable.
6. Verify that the same propagation, once accessioned, can no longer be proposed as "not yet accessioned" for a second Accession (one trial → one accession only).

-----

🎥 **Promise**: from the Accession view it is possible to expand to see the Plants, see at a glance the propagation status of each plant (e.g. seed not yet germinated, propagations already accessioned), and navigate with a click from the accession/child-plant code to the corresponding result, and conversely from the parent-plant code to highlight it again.

Test:

1. Build or find an accession with plants whose propagations are in different states (not germinated, accessioned).
2. Expand the accession in the results to see the plants.
3. Verify that propagation status is visible without opening an editor (at a glance, in the results).
4. Click on the code of an accession derived from a propagation: expected addition to the results view.
5. Click on the parent plant's code: expected highlighting/return to the parent plant.
6. If any of these bidirectional navigation behaviors no longer exists in the current interface, note it as a deviation from the original promise, not necessarily as a blocking defect.

6. Tagging
--------------

**Promise**: tagging applies to the active selection in the search results; select-all/select-none and single-item toggle have dedicated keyboard shortcuts.

Test:

1. Run a search with multiple results.
2. ``Ctrl-A``: expected selection of all rows.
3. ``Ctrl-Shift-A``: expected full deselection.
4. ``Ctrl-click`` on a single row: expected toggle of that row's selection only.

-----

**Promise**: ``Ctrl-T`` (or Tag → Tag Selection) opens a three-part dialog box — list of the selection, list of tags with status (applied to all / to some / to none), a link to create a new tag.

Test:

1. Select several objects of mixed status (some already tagged with a given tag, some not).
2. ``Ctrl-T``.
3. Expected: that tag shows up with an "undecided" status (neither checked nor blank) to indicate it applies only to part of the selection.
4. Create a new tag from the same window. Expected: the tag becomes the active one and shows checked in the Tag menu.

-----

**Promise**: with an active tag, ``Ctrl-Y`` applies the tag to the whole current selection without opening any window; ``Ctrl-Shift-Y`` removes it.

Test:

1. With an active tag and a selection made, press ``Ctrl-Y``. Expected: immediate application with no dialog.
2. Press ``Ctrl-Shift-Y`` on the same selection: expected immediate removal.

-----

**Promise**: a tag can be recalled from the Tags menu to automatically repopulate the results view with all the tagged objects, shareable with other users of the same database so they can rerun a report on the same selection without repeating the collection work.

Test:

1. Tag some objects, then select the same tag from the Tags menu in a different session (or by a different user on the same shared database).
2. Expected: the results view repopulates with exactly the tagged objects.

7. Reports
-------------

**Promise**: the Report Tool acts on the current selection; a report on the whole collection can be started quickly from shortcuts in the Home screen (the "Families: in use" cell for a taxonomic focus, "Locations: total" for a garden focus).

Test:

1. From Home, click the "Families: in use" cell. Expected: a selection/report on the whole taxonomic collection starts.
2. From Home, click "Locations: total". Expected: an analogous start, focused on locations.
3. On any selection, :menuselection:`Tools --> Report`: expected a list of available templates, a prompt for any parameters, the report produced in the application associated with that format (e.g. PDF, HTML, CSV).

-----

**Promise**: there are two report engines (Mako and XSL); templates are static once configured, except for a special "scratch" template that can be edited on the fly.

Test:

1. Verify the availability of at least one Mako template and one XSL template among those offered.
2. Verify whether the "scratch" template exists and works: edit it, run it, verify that the edit has an immediate effect on the generated report.

-----

**Promise**: the XSL formatter requires an external XSL→PDF renderer (Apache FOP) to produce PDFs.

Test:

1. Run a report that uses the XSL formatter set for PDF output, on a system with FOP installed. Expected: correct PDF output.
2. On a system without FOP: expected a comprehensible error message (not a silent crash).

8. Data import / export
-------------------------

⚠️ **Promise declared incomplete by the docs themselves**: "Exporting to JSON" is flagged as a feature still under development.

Test:

1. Check the current state of :menuselection:`Tools --> Export --> JSON`.
2. If still non-functional or partial, the docs are consistent with reality; if it works today, the docs need updating (the promise has been exceeded).

-----

**Promise**: CSV export produces one file per database table, named ``tablename.txt``, in a folder chosen by the user.

Test:

1. :menuselection:`Tools --> Export --> CSV`, choose an empty folder.
2. Expected: one or more ``tablename.txt`` files appear with the corresponding data.

-----

**Promise**: CSV import is intended only for files previously exported by Ghini itself; an arbitrary generic import is not guaranteed.

Test:

1. Export to CSV, then re-import that same export (:menuselection:`Tools --> Export --> Comma Separated Values`, confirming the "are you sure you know what you're doing" warning). Expected: import with no errors.
2. Try importing an arbitrary CSV not generated by Ghini: behavior not guaranteed, to be observed and flagged if it causes silent damage.

-----

⚠️ **Promise**: importing/exporting CSV or JSON files **can destroy existing data in the database** — the docs themselves recommend a prior backup.

Test:

1. Verify that the backup is actually necessary (i.e. that an import does not by itself protect existing data) before any test session on this section.
2. Run only on a test database, never on the production database.

-----

**Promise**: JSON import (Ghini's own interchange format) is the intended way to populate a new database without destroying pre-existing content, typically to bring an already-ready digital collection into a freshly initialized Ghini instance.

Test:

1. On a Ghini database already populated with some data, import a JSON interchange file produced by a different Ghini instance.
2. Expected: pre-existing data is not deleted; new data is added consistently (check duplicate/conflict handling, if it comes up).

-----

⚠️ **Promise not implemented**: importing from a generic external database (e.g. an Excel spreadsheet or another DBMS) has, according to the docs, no generic solution — it remains an open issue (issue #127 on the tracker).

Test: no test applicable; only check whether this is still the situation or whether a solution has been implemented in the meantime (check the status of the linked issue).

(For importing a pictures collection, see section 3, which has a dedicated and complete procedure.)

9. Users and permissions (PostgreSQL only)
--------------------------------------------

⚠️ **Stub, not just in the docs: probably in the requirement itself, too.**
The "Creating Users" and "Permissions" sections are empty or barely sketched ("Ghini allows read, write and execute permissions", with no further detail) in the current documentation.

Context note (uncertain memory, to be treated as such): this feature originated from contact with a botanical garden that managed sensitive material — field locations of rare, protected, or high-value-on-the-illegal-market plants — for which serious, differentiated permissions were needed, not just a generic read/write/execute.
It's unclear whether that contact ever produced precise requirements, or whether the Users plugin was ever developed beyond this stub to address that case.
In other words: what may be missing here is not just the documentation of an existing feature, but the feature itself, never completed because the requirement never made it to its destination.

This changes the nature of the test: before writing detailed test cases for "user creation" and "permissions", it's worth clarifying whether the feature is still needed by anyone with similar requirements (sensitive data, access differentiated by location), or whether it's a branch that should be considered closed.

Minimal tests that can still be run today:

1. Verify that the Users plugin is available only on PostgreSQL databases (not on SQLite/MySQL), as stated.
2. Log in with a user holding the ``CREATEROLE`` privilege.
3. Try creating a new user from the :menuselection:`Tools --> Users` plugin (menu name to be verified in the current interface).
4. Expected, if the feature really exists: user creation with the ability to assign read/write/execute permissions.
5. If the plugin doesn't exist or doesn't respond to these steps, the point is not "a bug to fix" but "decide whether the original use case (sensitive data, protected locations) is still relevant and deserves to be picked up again from scratch as a proper requirement".

10. Process notes for whoever uses this checklist
----------------------------------------------------

- 🎥 items should be verified at lower priority than the rest: they document an implicit promise made to an audience (the Korean botanical garden, in this case) rather than a written spec. If the behavior is gone, this is material for deciding whether to reintroduce it, document its removal, or knowingly let it drop.
- ⚠️ items are not bugs to be fixed urgently: they are limitations the project has always openly declared. They're useful for deciding whether to keep the declaration of incompleteness or whether it's time for an update (in either direction).
- Whenever a test fails unexpectedly (for a reason other than the ones above), it's a candidate for an issue on the project tracker, not just a note in this document.
