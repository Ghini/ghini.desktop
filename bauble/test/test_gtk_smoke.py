import os
from pathlib import Path

import pytest

import bauble.paths as paths
import bauble.prefs as prefs
from bauble.editor import GenericEditorView
from bauble.gtkinit import Gtk

prefs.testing = True


LIB_DIR = Path(paths.lib_dir())


CORE_WIDGETS = {
    "bauble.glade": (
        "main_window",
        "main_comboentry",
        "go_button",
        "view_box",
        "statusbar",
        "bottom_notebook",
        "prefs_window",
        "history_window",
    ),
    "connmgr.glade": (
        "main_dialog",
        "name_combo",
        "add_button",
        "remove_button",
        "type_combo",
        "database_entry",
        "host_entry",
        "port_entry",
        "user_entry",
        "passwd_chkbx",
        "pictureroot_entry",
        "connect_button",
    ),
    "notes.glade": ("notes_dialog", "notes_editor", "notes_add_button"),
    "pictures.glade": ("notes_dialog", "notes_editor", "picture_button"),
    "pictures_view.glade": ("pictures_view_dialog", "pictures_box"),
    "querybuilder.glade": ("main_dialog", "domain_combo", "add_clause_button"),
    os.path.join("plugins", "garden", "acc_editor.glade"): (
        "accession_dialog",
        "acc_code_entry",
        "acc_species_entry",
        "acc_ok_button",
    ),
    os.path.join("plugins", "garden", "contact.glade"): (
        "source_details_dialog",
        "source_name_entry",
        "source_type_combo",
    ),
    os.path.join("plugins", "garden", "institution.glade"): (
        "inst_dialog",
        "inst_name",
        "inst_code",
        "inst_ok",
    ),
    os.path.join("plugins", "garden", "loc_editor.glade"): (
        "location_dialog",
        "loc_name_entry",
        "loc_code_entry",
        "loc_ok_button",
    ),
    os.path.join("plugins", "garden", "picture_importer.glade"): (
        "picture_importer_dialog",
        "filepath_entry",
        "button_browse",
        "button_ok",
    ),
    os.path.join("plugins", "garden", "plant_editor.glade"): (
        "plant_editor_dialog",
        "plant_acc_entry",
        "plant_code_entry",
        "plant_loc_comboentry",
        "pad_ok_button",
    ),
    os.path.join("plugins", "garden", "pocket_server.glade"): (
        "pocket_server_dialog",
        "server_toggle_button",
        "code_entry",
        "close_button",
    ),
    os.path.join("plugins", "garden", "prop_editor.glade"): (
        "prop_dialog",
        "prop_type_combo",
        "prop_date_entry",
        "prop_ok_button",
    ),
    os.path.join("plugins", "imex", "select_export.glade"): (
        "select_export_dialog",
        "select_import_dialog",
        "filename",
        "input_filename",
    ),
    os.path.join("plugins", "plants", "family_editor.glade"): (
        "family_dialog",
        "fam_family_entry",
        "fam_syn_treeview",
        "fam_ok_button",
    ),
    os.path.join("plugins", "plants", "genus_editor.glade"): (
        "genus_dialog",
        "gen_family_entry",
        "gen_genus_entry",
        "gen_ok_button",
    ),
    os.path.join("plugins", "plants", "species_editor.glade"): (
        "species_dialog",
        "sp_genus_entry",
        "sp_species_entry",
        "sp_ok_button",
    ),
    os.path.join("plugins", "plants", "stored_queries.glade"): (
        "stqr_dialog",
        "stqr_label_entry",
        "stqr_query_textview",
    ),
    os.path.join("plugins", "plants", "taxonomy_check.glade"): (
        "dialog1",
        "file_path_entry",
        "treeview2",
        "ok_button",
    ),
    os.path.join("plugins", "report", "flat_export.glade"): (
        "main_dialog",
        "domain_combo",
        "treeview",
        "confirm_button",
    ),
    os.path.join("plugins", "report", "mako", "gui.glade"): (
        "window1",
        "template_chooser",
        "mako_options_box",
    ),
    os.path.join("plugins", "report", "report.glade"): (
        "report_dialog",
        "names_combo",
        "output_entry",
        "ok_button",
    ),
    os.path.join("plugins", "tag", "tag.glade"): (
        "tag_dialog",
        "tag_name_entry",
        "tag_desc_textview",
        "tag_item_dialog",
    ),
    os.path.join("plugins", "users", "ui.glade"): (
        "main_dialog",
        "users_tree",
        "read_button",
        "pwd_dialog",
    ),
}


ROOT_WIDGETS = {
    "bauble.glade": ("main_window", "prefs_window", "history_window"),
    "connmgr.glade": ("main_dialog",),
    "notes.glade": ("notes_dialog", "notes_editor"),
    "pictures.glade": ("notes_dialog", "notes_editor"),
    "pictures_view.glade": ("pictures_view_dialog",),
    "querybuilder.glade": ("main_dialog",),
    os.path.join("plugins", "garden", "acc_editor.glade"): (
        "accession_dialog",
        "acc_codes_dialog",
    ),
    os.path.join("plugins", "garden", "contact.glade"): ("source_details_dialog",),
    os.path.join("plugins", "garden", "institution.glade"): ("inst_dialog",),
    os.path.join("plugins", "garden", "loc_editor.glade"): ("location_dialog",),
    os.path.join("plugins", "garden", "picture_importer.glade"): (
        "picture_importer_dialog",
    ),
    os.path.join("plugins", "garden", "plant_editor.glade"): ("plant_editor_dialog",),
    os.path.join("plugins", "garden", "pocket_server.glade"): ("pocket_server_dialog",),
    os.path.join("plugins", "garden", "prop_editor.glade"): ("prop_dialog",),
    os.path.join("plugins", "imex", "select_export.glade"): (
        "select_export_dialog",
        "select_import_dialog",
    ),
    os.path.join("plugins", "plants", "family_editor.glade"): ("family_dialog",),
    os.path.join("plugins", "plants", "genus_editor.glade"): ("genus_dialog",),
    os.path.join("plugins", "plants", "species_editor.glade"): ("species_dialog",),
    os.path.join("plugins", "plants", "stored_queries.glade"): ("stqr_dialog",),
    os.path.join("plugins", "plants", "taxonomy_check.glade"): ("dialog1",),
    os.path.join("plugins", "report", "flat_export.glade"): ("main_dialog",),
    os.path.join("plugins", "report", "mako", "gui.glade"): ("window1",),
    os.path.join("plugins", "report", "report.glade"): (
        "choose_dialog",
        "report_dialog",
    ),
    os.path.join("plugins", "tag", "tag.glade"): ("tag_dialog", "tag_item_dialog"),
    os.path.join("plugins", "users", "ui.glade"): ("main_dialog", "pwd_dialog"),
}


def glade_files():
    return sorted(LIB_DIR.glob("**/*.glade"))


def destroy_builder_windows(builder):
    for obj in builder.get_objects():
        if isinstance(obj, Gtk.Window):
            obj.destroy()

    while Gtk.events_pending():
        Gtk.main_iteration_do(False)


@pytest.mark.parametrize(
    "filename", glade_files(), ids=lambda p: str(p.relative_to(LIB_DIR))
)
def test_glade_file_loads(filename):
    builder = Gtk.Builder()
    try:
        builder.add_from_file(str(filename))
    finally:
        destroy_builder_windows(builder)


@pytest.mark.parametrize("relative_name, widget_ids", sorted(CORE_WIDGETS.items()))
def test_core_glade_widgets_exist(relative_name, widget_ids):
    builder = Gtk.Builder()
    try:
        builder.add_from_file(str(LIB_DIR / relative_name))
        missing = [
            widget_id
            for widget_id in widget_ids
            if builder.get_object(widget_id) is None
        ]
        assert missing == []
    finally:
        destroy_builder_windows(builder)


@pytest.mark.parametrize(
    "relative_name, root_widget",
    [
        (relative_name, root_widget)
        for relative_name, root_widgets in sorted(ROOT_WIDGETS.items())
        for root_widget in root_widgets
    ],
)
def test_generic_editor_view_loads_root_widget(relative_name, root_widget):
    view = GenericEditorView(str(LIB_DIR / relative_name), root_widget_name=root_widget)
    window = view.get_window()

    try:
        assert isinstance(window, Gtk.Window)
    finally:
        window.destroy()
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)
