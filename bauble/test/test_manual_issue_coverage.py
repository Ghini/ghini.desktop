import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

TEST_SOURCES = (
    "bauble/test/test_db.py",
    "bauble/test/test_editor.py",
    "bauble/test/test_gui_e2e.py",
    "bauble/test/test_gui_guided.py",
    "bauble/test/test_gtk_smoke.py",
    "bauble/test/test_postgresql_external_smoke.py",
    "bauble/test/test_postgresql_lane.py",
    "bauble/test/test_search.py",
    "bauble/test/test_source_selector.py",
    "bauble/plugins/garden/test.py",
    "bauble/plugins/imex/test.py",
    "bauble/plugins/plants/taxonomy_check_test.py",
    "bauble/plugins/plants/test.py",
    "bauble/plugins/plants/test_asktpl.py",
)


MANUAL_ISSUE_REGRESSION_COVERAGE = {
    2: (
        "GUI propagation workflow persists plant propagation records",
        (
            "test_can_create_seed_propagation_from_plant_editor",
            "test_propagation_editor_seed_fields_enable_accept",
            "test_seed_propagation_clean_tolerates_missing_cutting",
        ),
    ),
    3: (
        "GUI search workflows",
        (
            "test_can_search_existing_species",
            "test_can_search_existing_accession",
            "test_can_search_existing_plant_and_show_details",
        ),
    ),
    4: (
        "GUI edit workflows",
        (
            "test_can_edit_existing_family_from_result_context_menu",
            "test_can_edit_existing_accession_from_result_context_menu",
            "test_can_edit_existing_location_from_result_context_menu",
            "test_can_edit_existing_plant_from_result_context_menu",
        ),
    ),
    5: (
        "Delete and confirmation dialogs",
        (
            "test_family_delete_confirmation_cancel_and_confirm",
            "test_remove_callback_with_genera_cant_cascade",
            "test_remove_callback_with_accessions_cant_cascade",
        ),
    ),
    6: (
        "Guided visual result workflow",
        (
            "test_guided_issue_body_formats_multiline_markdown",
            "test_guided_issue_body_includes_all_checkpoints_when_no_failure",
        ),
    ),
    8: (
        "Plant search selection exposes plant detail infobox",
        (
            "test_can_search_existing_plant_and_show_details",
            "test_plant_infobox_constructs_with_expander_widgets",
        ),
    ),
    9: (
        "GUI autocomplete responds during guided search",
        (
            "test_main_search_history_completion_shows_popup",
            "test_main_search_changed_refreshes_database_completion",
            "test_dynamic_completion_refreshes_at_minimum_key_length",
        ),
    ),
    10: (
        "Taxonomy search result infobox renders",
        (
            "test_family_infobox_updates_builder_widgets",
            "test_location_infobox_counts_plants",
            "test_species_infobox_counts_garden_rows",
        ),
    ),
    11: (
        "GTK menu items avoid container warnings",
        (
            "test_create_menu_item_with_image_uses_single_gtk_menu_child",
            "test_create_menu_item_with_png_image_uses_image_menu_item",
        ),
    ),
    12: (
        "Plant Editor saves plant from Accession Editor workflow",
        (
            "test_daily_species_editor_add_accession_creates_plant_with_source",
            "test_accession_editor_from_species_id_populates_taxon_and_commits",
        ),
    ),
    13: (
        "Location Editor save is visible through location search",
        (
            "test_can_create_location_from_insert_menu",
            "test_can_edit_existing_location_from_result_context_menu",
            "test_location_editor_presenter_populates_and_edits_fields",
        ),
    ),
    14: (
        "Search results can be opened for editing from result tree",
        (
            "test_can_edit_existing_family_from_result_context_menu",
            "test_can_edit_existing_accession_from_result_context_menu",
            "test_can_edit_existing_location_from_result_context_menu",
            "test_can_edit_existing_plant_from_result_context_menu",
        ),
    ),
    15: (
        "Propagation default date uses expected local date",
        (
            "test_today_str_uses_local_today",
            "test_new_propagation_gets_visible_default_date",
        ),
    ),
    16: (
        "PostgreSQL-backed regression lane",
        (
            "test_postgresql_database_create_imports_defaults",
            "test_postgresql_can_persist_core_taxonomy_fixture",
            "test_external_postgresql_can_read_daily_join",
        ),
    ),
    17: (
        "Plant Editor persists planting code edits",
        (
            "test_plant_editor_presenter_populates_and_edits_code",
            "test_plant_editor_blocks_overlong_code",
            "test_can_edit_existing_plant_from_result_context_menu",
        ),
    ),
    18: (
        "PostgreSQL database creation imports default rows",
        ("test_postgresql_database_create_imports_defaults",),
    ),
    19: (
        "Create-plant GUI test enables OK after location entry",
        (
            "test_can_create_plant_from_insert_menu",
            "test_plant_editor_presenter_populates_and_edits_code",
        ),
    ),
    20: (
        "Accession source selector is deduplicated, sorted, and searchable",
        (
            "test_source_contacts_are_sorted_and_deduplicated_for_combo_display",
            "test_source_completion_matches_case_insensitive_substrings_and_ids",
            "test_can_select_existing_source_when_editing_accession",
        ),
    ),
    21: (
        "Plant material choices are explicit for the release baseline",
        ("test_plant_material_choices_match_release_baseline",),
    ),
    22: (
        "Quick CSV export tolerates empty optional relationships",
        ("test_export_none_is_empty",),
    ),
    23: (
        "Taxon import with accepted names creates both taxa",
        (
            "test_import_family_with_accepted_preserves_both_taxa",
            "test_import_species_with_accepted_preserves_both_taxa",
        ),
    ),
    24: (
        "Maintained taxonomy lookup service maps provider results",
        (
            "test_wfo_provider_maps_accepted_result",
            "test_wfo_provider_maps_synonym_result",
            "test_tnrs_web_url_points_to_current_service",
        ),
    ),
    25: (
        "PostgreSQL search and home navigation recover from closed connections",
        (
            "test_search_retries_once_after_invalidated_connection",
            "test_postgresql_session_recovers_after_backend_disconnect",
            "test_external_postgresql_session_recovers_after_read_rollback",
        ),
    ),
    26: (
        "Result tree expansion state refreshes when child rows appear",
        ("test_result_expand_keeps_retry_child_for_empty_rows",),
    ),
    27: (
        "Timestamp timezone and local-date behavior",
        (
            "test_today_str_uses_local_today",
            "test_new_propagation_gets_visible_default_date",
            "test_location_retrieve_or_create_with_timestamps",
        ),
    ),
    28: (
        "Autoflush and no-autoflush boundaries under SQLAlchemy 2",
        (
            "test_source_accessible_plants_suppresses_autoflush",
            "test_is_code_unique_suppresses_autoflush",
            "test_accession_editor_does_not_pending_disabled_source_placeholders",
        ),
    ),
    29: (
        "Accession source selector daily workflow",
        (
            "test_source_contacts_are_sorted_and_deduplicated_for_combo_display",
            "test_source_model_partial_match_keeps_typing_valid",
            "test_source_exact_match_accepts_display_text_or_id",
        ),
    ),
    30: (
        "Autocomplete in primary search and daily workflow selectors",
        (
            "test_main_search_database_completion_values_uses_seeded_records",
            "test_dynamic_completion_exact_match_ignores_zero_width_space",
            "test_genus_editor_family_completion_selects_family_object",
        ),
    ),
    32: (
        "Vernacular-name entry persists without special Enter handling",
        (
            "test_daily_species_editor_add_accession_creates_plant_with_source",
            "test_species_vernacular_name_syncs_while_cell_is_edited",
            "test_export_single_species_with_vernacular_name",
        ),
    ),
    33: (
        "Quick CSV export tolerates optional empty values",
        ("test_export_none_is_empty",),
    ),
    34: (
        "Taxon import with accepted-name data preserves both taxa",
        (
            "test_import_family_with_accepted_preserves_both_taxa",
            "test_import_species_with_accepted_preserves_both_taxa",
        ),
    ),
    35: (
        "Daily editor fields validate database length limits",
        (
            "test_family_editor_blocks_overlong_epithet",
            "test_genus_editor_blocks_overlong_epithet_and_author",
            "test_species_editor_blocks_overlong_names",
            "test_location_editor_blocks_overlong_code_and_name",
            "test_accession_editor_blocks_overlong_code",
            "test_accession_source_id_blocks_overlong_value",
        ),
    ),
    36: (
        "PlantsPlugin initializes when preferences are unavailable",
        ("test_synonym_search_defaults_enabled_without_initialized_prefs",),
    ),
    38: (
        "Main search field remains usable after species editor save",
        ("test_search_entry_accepts_input_after_species_editor_save",),
    ),
    39: (
        "Species Notes editor does not hang during routine species entry",
        (
            "test_species_editor_notes_add_button_adds_note_box",
            "test_note_box_date_entry_uses_editor_date_validator",
            "test_note_box_appends_new_note_once_when_date_is_missing",
        ),
    ),
    40: (
        "Daily searches do not log infobox tracebacks",
        ("test_daily_searches_do_not_log_infobox_tracebacks",),
    ),
    41: (
        "Add Accession from new Species avoids detached Species failures",
        (
            "test_accession_editor_reloads_detached_species_for_id_qual_rank",
            "test_accession_editor_from_species_id_populates_taxon_and_commits",
        ),
    ),
    42: (
        "Add Accession avoids autoflush of incomplete seed propagation state",
        (
            "test_source_accessible_plants_suppresses_autoflush",
            "test_seed_propagation_clean_removes_blank_seed_detail",
            "test_plant_editor_commit_discards_blank_seed_propagation_detail",
        ),
    ),
}


def _test_names_in(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    }


def _all_test_names() -> set[str]:
    names: set[str] = set()
    for relative_path in TEST_SOURCES:
        names.update(_test_names_in(REPO_ROOT / relative_path))
    return names


def test_manual_issue_regression_coverage_lists_all_tracked_manual_issues():
    expected_issue_numbers = {
        2,
        3,
        4,
        5,
        6,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        18,
        19,
        20,
        21,
        22,
        23,
        24,
        25,
        26,
        27,
        28,
        29,
        30,
        32,
        33,
        34,
        35,
        36,
        38,
        39,
        40,
        41,
        42,
    }

    assert set(MANUAL_ISSUE_REGRESSION_COVERAGE) == expected_issue_numbers


def test_manual_issue_regression_coverage_references_existing_tests():
    known_tests = _all_test_names()
    missing = {
        issue_number: sorted(
            test_name for test_name in tests if test_name not in known_tests
        )
        for issue_number, (_title, tests) in MANUAL_ISSUE_REGRESSION_COVERAGE.items()
    }
    missing = {issue_number: tests for issue_number, tests in missing.items() if tests}

    assert missing == {}


def test_manual_issue_regression_coverage_has_behavioral_tests_for_each_issue():
    empty = {
        issue_number: title
        for issue_number, (title, tests) in MANUAL_ISSUE_REGRESSION_COVERAGE.items()
        if not tests
    }

    assert empty == {}
