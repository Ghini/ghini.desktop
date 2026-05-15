import datetime
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

import bauble
import bauble.connmgr as connmgr
import bauble.paths as paths
import bauble.prefs as prefs
import bauble.view as view
from bauble.connmgr import ConnMgrPresenter
from bauble.editor import GenericEditorView
from bauble.gtkinit import Gtk
from bauble.shared import InfoExpander
from bauble.plugins.garden.location_editor import (
    LocationEditorPresenter,
    LocationEditorView,
)
from bauble.plugins.garden.accession_editor import (
    AccessionEditorPresenter,
    AccessionEditorView,
)
from bauble.plugins.garden.models.accession import Accession
from bauble.plugins.garden.models.location import Location
from bauble.plugins.garden.models.plant import Plant
from bauble.plugins.garden.plant_editor import (
    PlantEditorPresenter,
    PlantEditorView,
    PlantInfoBox,
)
from bauble.plugins.garden.propagation_editor import (
    PropagationEditorPresenter,
    PropagationEditorView,
)
from bauble.plugins.garden.models.propagation import Propagation
from bauble.plugins.plants.family import (
    Family,
    FamilyEditorPresenter,
    FamilyEditorView,
    FamilyInfoBox,
)
from bauble.plugins.plants.genus import Genus, GenusEditorPresenter, GenusEditorView
from bauble.plugins.plants.species import Species
from bauble.plugins.plants.species_editor import (
    SpeciesEditorPresenter,
    SpeciesEditorView,
)

prefs.testing = True


LIB_DIR = Path(paths.lib_dir())


class DummyInfoExpander(InfoExpander):
    def __init__(self, label="Dummy") -> None:
        super().__init__(label)
        self.updated_with = None

    def update(self, value) -> None:
        self.updated_with = value


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


class SaveablePrefs(dict):
    def save(self):
        return None


@pytest.fixture
def gtk_prefs(tmp_path):
    store = SaveablePrefs()
    store[bauble.conn_list_pref] = {}
    store[bauble.conn_default_pref] = None
    store[prefs.picture_root_pref] = str(tmp_path / "pictures")
    return SimpleNamespace(
        prefs=store,
        testing=True,
        picture_root_pref=prefs.picture_root_pref,
    )


@pytest.fixture
def connmgr_view():
    view = GenericEditorView(
        str(LIB_DIR / "connmgr.glade"), root_widget_name="main_dialog"
    )
    try:
        yield view
    finally:
        view.get_window().destroy()
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)


@pytest.fixture
def family_editor_view():
    view = FamilyEditorView()
    try:
        yield view
    finally:
        view.get_window().destroy()
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)


@pytest.fixture
def genus_editor_view():
    view = GenusEditorView()
    try:
        yield view
    finally:
        view.get_window().destroy()
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)


@pytest.fixture
def species_editor_view():
    view = SpeciesEditorView()
    try:
        yield view
    finally:
        view.get_window().destroy()
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)


@pytest.fixture
def location_editor_view():
    view = LocationEditorView()
    try:
        yield view
    finally:
        view.get_window().destroy()
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)


@pytest.fixture
def plant_editor_view():
    view = PlantEditorView()
    try:
        yield view
    finally:
        view.get_window().destroy()
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)


@pytest.fixture
def accession_editor_view():
    view = AccessionEditorView()
    try:
        yield view
    finally:
        view.get_window().destroy()
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)


@pytest.fixture
def propagation_editor_view():
    view = PropagationEditorView()
    try:
        yield view
    finally:
        view.get_window().destroy()
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)


@pytest.fixture(autouse=True)
def disable_connection_manager_background_threads(monkeypatch):
    monkeypatch.setattr(ConnMgrPresenter, "start_thread", lambda self, thread: thread)


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


def test_infobox_page_packs_info_expander_widgets():
    page = view.InfoBoxPage()
    expander = DummyInfoExpander("General")
    row = object()

    page.add_expander(expander)

    assert expander.get_widget() in page.vbox.get_children()
    assert page.get_expander("General") is expander

    page.update(row)

    assert expander.updated_with is row
    assert page.remove_expander("General") is expander
    assert expander.get_widget() not in page.vbox.get_children()


def test_plant_infobox_constructs_with_expander_widgets():
    infobox = PlantInfoBox()
    widget = infobox.get_widget()

    try:
        assert isinstance(widget, Gtk.Notebook)
    finally:
        widget.destroy()
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)


def test_links_expander_packs_link_button_widgets():
    expander = view.LinksExpander(
        links=[
            {
                "name": "SearchButton",
                "_base_uri": "https://example.test/search?q=%s",
                "_space": "+",
                "title": "Search",
                "tooltip": "Search example",
            }
        ]
    )
    link_button = expander.buttons[0]
    widget = link_button.get_widget()

    assert widget in expander.vbox.get_children()
    assert widget.get_halign() == Gtk.Align.START

    expander.update("Guided family")

    assert widget.get_uri() == "https://example.test/search?q=Guided+family"


def test_family_infobox_updates_builder_widgets(session):
    family = Family(epithet="Guidedaceae", qualifier="")
    session.add(family)
    session.flush()

    infobox = FamilyInfoBox()
    widget = infobox.get_widget()

    try:
        infobox.update(family)
        assert infobox.general.widgets.fam_name_data.get_label()
    finally:
        widget.destroy()
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)


def test_connection_manager_empty_state(connmgr_view, gtk_prefs):
    presenter = ConnMgrPresenter(connmgr_view, prefs=gtk_prefs)

    assert presenter.connection_names == []
    assert connmgr_view.widget_get_visible("noconnectionlabel")
    assert not connmgr_view.widget_get_visible("expander")
    assert not connmgr_view.widgets.connect_button.get_sensitive()


def test_connection_manager_populates_postgresql_connection(connmgr_view, gtk_prefs):
    gtk_prefs.prefs[bauble.conn_list_pref] = {
        "Wyse Home Garden": {
            "type": "PostgreSQL",
            "db": "ghini_test3",
            "host": "postgres",
            "port": 5432,
            "user": "ghini",
            "passwd": True,
            "pictures": "/app/Wyse Home Garden",
        }
    }
    gtk_prefs.prefs[bauble.conn_default_pref] = "Wyse Home Garden"

    presenter = ConnMgrPresenter(connmgr_view, prefs=gtk_prefs)

    assert presenter.connection_name == "Wyse Home Garden"
    assert connmgr_view.combobox_get_active_text("name_combo") == "Wyse Home Garden"
    assert connmgr_view.combobox_get_active_text("type_combo") == "PostgreSQL"
    assert connmgr_view.widget_get_value("database_entry") == "ghini_test3"
    assert connmgr_view.widget_get_value("host_entry") == "postgres"
    assert connmgr_view.widget_get_value("port_entry") == "5432"
    assert connmgr_view.widget_get_value("user_entry") == "ghini"
    assert connmgr_view.widget_get_active("passwd_chkbx")
    assert (
        connmgr_view.widget_get_value("pictureroot2_entry") == "/app/Wyse Home Garden"
    )
    assert connmgr_view.widget_get_visible("dbms_parambox")
    assert not connmgr_view.widget_get_visible("sqlite_parambox")
    assert connmgr_view.widgets.connect_button.get_sensitive()


def test_connection_manager_entry_edits_update_presenter(connmgr_view, gtk_prefs):
    gtk_prefs.prefs[bauble.conn_list_pref] = {
        "dev": {
            "type": "PostgreSQL",
            "db": "old_db",
            "host": "old_host",
            "port": 5432,
            "user": "old_user",
            "passwd": False,
            "pictures": "/tmp/dev",
        }
    }
    gtk_prefs.prefs[bauble.conn_default_pref] = "dev"
    presenter = ConnMgrPresenter(connmgr_view, prefs=gtk_prefs)

    connmgr_view.widget_set_value("database_entry", "new_db")
    presenter.on_text_entry_changed("database_entry")
    connmgr_view.widget_set_value("host_entry", "new_host")
    presenter.on_text_entry_changed("host_entry")
    connmgr_view.widget_set_value("port_entry", "6543")
    presenter.on_text_entry_changed("port_entry")
    connmgr_view.widget_set_value("user_entry", "new_user")
    presenter.on_text_entry_changed("user_entry")
    connmgr_view.widget_set_active("passwd_chkbx", True)
    presenter.on_chkbx_toggled("passwd_chkbx")

    assert presenter.database == "new_db"
    assert presenter.host == "new_host"
    assert presenter.port == "6543"
    assert presenter.user == "new_user"
    assert presenter.passwd is True
    assert presenter.is_dirty()


def test_connection_manager_switches_between_db_sections(connmgr_view, gtk_prefs):
    gtk_prefs.prefs[bauble.conn_list_pref] = {
        "dev": {
            "type": "PostgreSQL",
            "db": "ghini",
            "host": "postgres",
            "port": 5432,
            "user": "ghini",
            "passwd": False,
            "pictures": "/tmp/dev",
        }
    }
    gtk_prefs.prefs[bauble.conn_default_pref] = "dev"
    presenter = ConnMgrPresenter(connmgr_view, prefs=gtk_prefs)

    connmgr_view.combobox_set_active("type_combo", connmgr.dbtypes.index("SQLite"))
    presenter.on_combo_changed("type_combo")

    assert presenter.dbtype == "SQLite"
    assert connmgr_view.widget_get_visible("sqlite_parambox")
    assert not connmgr_view.widget_get_visible("dbms_parambox")

    connmgr_view.combobox_set_active("type_combo", connmgr.dbtypes.index("PostgreSQL"))
    presenter.on_combo_changed("type_combo")

    assert presenter.dbtype == "PostgreSQL"
    assert connmgr_view.widget_get_visible("dbms_parambox")
    assert not connmgr_view.widget_get_visible("sqlite_parambox")


def test_connection_manager_add_and_remove_connection(
    monkeypatch, connmgr_view, gtk_prefs
):
    monkeypatch.setattr(connmgr, "prefs", gtk_prefs)
    connmgr_view.run_entry_dialog = lambda *args, **kwargs: "new connection"
    connmgr_view.run_yes_no_dialog = lambda *args, **kwargs: True
    presenter = ConnMgrPresenter(connmgr_view, prefs=gtk_prefs)

    presenter.on_add_button_clicked()

    assert presenter.connection_names == ["new connection"]
    assert "new connection" in presenter.connections
    assert connmgr_view.combobox_get_active_text("name_combo") == "new connection"
    assert connmgr_view.widget_get_visible("expander")
    assert not connmgr_view.widget_get_visible("noconnectionlabel")

    presenter.on_remove_button_clicked(connmgr_view.widgets.remove_button)

    assert presenter.connection_names == []
    assert presenter.connections == {}
    assert connmgr_view.widget_get_visible("noconnectionlabel")
    assert not connmgr_view.widget_get_visible("expander")


def test_family_editor_presenter_populates_and_edits_fields(
    session, family_editor_view
):
    family = Family(epithet="Arecaceae", qualifier="")
    session.add(family)
    session.flush()

    presenter = FamilyEditorPresenter(family, family_editor_view)

    assert family_editor_view.widget_get_value("fam_family_entry") == "Arecaceae"
    assert family_editor_view.widget_get_value("fam_qualifier_combo") == ""
    assert not family_editor_view.widgets.fam_ok_button.get_sensitive()

    family_editor_view.widget_set_value("fam_family_entry", "Palmae")
    presenter.on_text_entry_changed("fam_family_entry")

    assert family.epithet == "Palmae"
    assert presenter.is_dirty()
    assert family_editor_view.widgets.fam_ok_button.get_sensitive()
    assert family_editor_view.widgets.fam_ok_and_add_button.get_sensitive()
    assert family_editor_view.widgets.fam_next_button.get_sensitive()


def test_genus_editor_presenter_populates_and_edits_fields(session, genus_editor_view):
    family = Family(epithet="Arecaceae", qualifier="")
    genus = Genus(family=family, epithet="Cocos", author="L.")
    session.add_all([family, genus])
    session.flush()

    presenter = GenusEditorPresenter(genus, genus_editor_view)

    assert genus.family == family
    assert genus_editor_view.widget_get_value("gen_family_entry") == "Arecaceae"
    assert genus_editor_view.widget_get_value("gen_genus_entry") == "Cocos"
    assert genus_editor_view.widget_get_value("gen_author_entry") == "L."
    assert not genus_editor_view.widgets.gen_ok_button.get_sensitive()

    genus_editor_view.widget_set_value("gen_genus_entry", "Phoenix")
    presenter.on_text_entry_changed("gen_genus_entry")
    genus_editor_view.widget_set_value("gen_author_entry", "Mill.")
    presenter.on_text_entry_changed("gen_author_entry")

    assert genus.epithet == "Phoenix"
    assert genus.author == "Mill."
    assert presenter.is_dirty()
    assert genus_editor_view.widgets.gen_ok_button.get_sensitive()
    assert genus_editor_view.widgets.gen_ok_and_add_button.get_sensitive()
    assert genus_editor_view.widgets.gen_next_button.get_sensitive()


def test_species_editor_presenter_populates_and_edits_fields(
    session, species_editor_view
):
    family = Family(epithet="Arecaceae", qualifier="")
    genus = Genus(family=family, epithet="Cocos", author="L.")
    species = Species(genus=genus, epithet="nucifera", author="L.", hybrid=False)
    session.add_all([family, genus, species])
    session.flush()

    presenter = SpeciesEditorPresenter(species, species_editor_view)

    assert species.genus == genus
    assert species_editor_view.widget_get_value("sp_genus_entry") == "Cocos"
    assert species_editor_view.widget_get_value("sp_species_entry") == "nucifera"
    assert species_editor_view.widget_get_value("sp_author_entry") == "L."
    assert not species_editor_view.widget_get_active("sp_hybrid_check")

    species_editor_view.widget_set_value("sp_species_entry", "odorata")
    presenter.on_text_entry_changed("sp_species_entry")
    species_editor_view.widget_set_value("sp_author_entry", "Dammer")
    presenter.on_text_entry_changed("sp_author_entry")
    species_editor_view.widget_set_active("sp_hybrid_check", True)
    presenter.on_chkbx_toggled("sp_hybrid_check")

    assert species.epithet == "odorata"
    assert species.author == "Dammer"
    assert species.hybrid is True
    assert presenter.is_dirty()
    assert species_editor_view.widgets.sp_ok_button.get_sensitive()
    assert species_editor_view.widgets.sp_next_button.get_sensitive()


def test_location_editor_presenter_populates_and_edits_fields(
    session, location_editor_view
):
    location = Location(code="A1", name="Palm House", description="Warm house")
    session.add(location)
    session.flush()

    presenter = LocationEditorPresenter(location, location_editor_view)

    assert location_editor_view.widget_get_value("loc_code_entry") == "A1"
    assert location_editor_view.widget_get_value("loc_name_entry") == "Palm House"
    assert location_editor_view.widget_get_value("loc_desc_textview") == "Warm house"
    assert not location_editor_view.widgets.loc_ok_button.get_sensitive()

    location_editor_view.widget_set_value("loc_code_entry", "B2")
    presenter.on_text_entry_changed("loc_code_entry")
    location_editor_view.widget_set_value("loc_name_entry", "Fern Room")
    presenter.on_text_entry_changed("loc_name_entry")
    location_editor_view.widget_set_value("loc_desc_textview", "Cool house")
    presenter.on_textbuffer_changed(
        location_editor_view.widgets.loc_desc_textview.get_buffer(),
        attr="description",
    )

    assert location.code == "B2"
    assert location.name == "Fern Room"
    assert location.description == "Cool house"
    assert presenter.is_dirty()
    assert location_editor_view.widgets.loc_ok_button.get_sensitive()
    assert location_editor_view.widgets.loc_ok_and_add_button.get_sensitive()
    assert location_editor_view.widgets.loc_next_button.get_sensitive()


def test_location_editor_requires_code_before_accept(session, location_editor_view):
    location = Location(code=None, name=None, description=None)
    session.add(location)

    presenter = LocationEditorPresenter(location, location_editor_view)

    assert not location_editor_view.widgets.loc_ok_button.get_sensitive()

    location_editor_view.widget_set_value("loc_name_entry", "Unnamed bed")
    presenter.on_text_entry_changed("loc_name_entry")

    assert location.name == "Unnamed bed"
    assert presenter.is_dirty()
    assert not location_editor_view.widgets.loc_ok_button.get_sensitive()

    location_editor_view.widget_set_value("loc_code_entry", "U1")
    presenter.on_text_entry_changed("loc_code_entry")

    assert location.code == "U1"
    assert location_editor_view.widgets.loc_ok_button.get_sensitive()


def make_test_plant(session):
    family = Family(epithet="Arecaceae", qualifier="")
    genus = Genus(family=family, epithet="Cocos", author="L.")
    species = Species(genus=genus, epithet="nucifera", author="L.", hybrid=False)
    accession = Accession(code="2026.001", species=species)
    location = Location(code="P1", name="Palm House", description=None)
    plant = Plant(
        accession=accession,
        location=location,
        code="1",
        quantity=1,
        acc_type="Plant",
        memorial=False,
    )
    session.add_all([family, genus, species, accession, location, plant])
    session.flush()
    return plant


def make_test_accession(session):
    family = Family(epithet="Arecaceae", qualifier="")
    genus = Genus(family=family, epithet="Cocos", author="L.")
    species = Species(genus=genus, epithet="nucifera", author="L.", hybrid=False)
    accession = Accession(
        code="2026.001",
        species=species,
        quantity_recvd=1,
        recvd_type="PLNT",
        private=False,
    )
    session.add_all([family, genus, species, accession])
    session.flush()
    return accession


def test_plant_editor_presenter_populates_and_edits_code(
    monkeypatch, session, plant_editor_view
):
    monkeypatch.setattr(prefs, "testing", False)
    plant = make_test_plant(session)

    presenter = PlantEditorPresenter(plant, plant_editor_view)

    assert plant_editor_view.widget_get_value("plant_acc_entry") == "2026.001"
    assert plant_editor_view.widget_get_value("plant_code_entry") == "1"
    assert plant_editor_view.widget_get_value("plant_quantity_entry") == "1"
    assert (
        plant_editor_view.widget_get_value("plant_loc_comboentry") == "(P1) Palm House"
    )
    assert not plant_editor_view.widgets.pad_ok_button.get_sensitive()

    plant_editor_view.widget_set_value("plant_code_entry", "2")
    presenter.on_plant_code_entry_changed(plant_editor_view.widgets.plant_code_entry)

    assert plant.code == "2"
    assert presenter.is_dirty()
    assert plant_editor_view.widgets.pad_ok_button.get_sensitive()
    assert plant_editor_view.widgets.pad_next_button.get_sensitive()


def test_plant_editor_quantity_changes_update_model(
    monkeypatch, session, plant_editor_view
):
    monkeypatch.setattr(prefs, "testing", False)
    plant = make_test_plant(session)

    presenter = PlantEditorPresenter(plant, plant_editor_view)
    plant_editor_view.widget_set_value("plant_quantity_entry", "3")

    presenter.on_quantity_changed(plant_editor_view.widgets.plant_quantity_entry)

    assert plant.quantity == 3
    assert presenter.change.quantity == 2
    assert presenter.is_dirty()
    assert plant_editor_view.widgets.pad_ok_button.get_sensitive()


def test_plant_editor_invalid_quantity_blocks_accept(
    monkeypatch, session, plant_editor_view
):
    monkeypatch.setattr(prefs, "testing", False)
    plant = make_test_plant(session)

    presenter = PlantEditorPresenter(plant, plant_editor_view)
    plant_editor_view.widgets.plant_quantity_entry.set_text("not a number")

    assert plant.quantity == 1
    assert plant_editor_view.widgets.plant_quantity_entry.get_text() == "1"
    assert not presenter.has_problems()
    assert not presenter.is_dirty()
    assert not plant_editor_view.widgets.pad_ok_button.get_sensitive()
    assert not plant_editor_view.widgets.pad_next_button.get_sensitive()


def test_accession_editor_presenter_populates_and_edits_core_fields(
    session, accession_editor_view
):
    accession = make_test_accession(session)

    presenter = AccessionEditorPresenter(accession, accession_editor_view)

    assert accession_editor_view.widget_get_value("acc_code_entry") == "2026.001"
    assert accession_editor_view.widget_get_value("acc_quantity_recvd_entry") == "1"
    assert (
        accession_editor_view.widget_get_value("acc_recvd_type_comboentry")
        == "Planting"
    )
    assert not accession_editor_view.widget_get_active("acc_private_check")
    assert not accession_editor_view.widgets.acc_ok_button.get_sensitive()

    accession_editor_view.widgets.acc_code_entry.set_text("2026.002")
    presenter.on_acc_code_entry_changed(accession_editor_view.widgets.acc_code_entry)
    accession_editor_view.widget_set_value("acc_quantity_recvd_entry", "3")
    presenter.on_text_entry_changed("acc_quantity_recvd_entry")
    accession_editor_view.widget_set_active("acc_private_check", True)
    presenter.on_chkbx_toggled("acc_private_check")

    assert accession.code == "2026.002"
    assert accession.quantity_recvd == "3"
    assert accession.private is True
    assert presenter.is_dirty()
    assert accession_editor_view.widgets.acc_ok_button.get_sensitive()
    assert accession_editor_view.widgets.acc_ok_and_add_button.get_sensitive()
    assert accession_editor_view.widgets.acc_next_button.get_sensitive()


def test_accession_editor_duplicate_code_blocks_accept(session, accession_editor_view):
    existing = make_test_accession(session)
    duplicate = Accession(code="2026.002", species=existing.species)
    session.add(duplicate)
    session.flush()

    presenter = AccessionEditorPresenter(existing, accession_editor_view)

    accession_editor_view.widgets.acc_code_entry.set_text("2026.002")
    presenter.on_acc_code_entry_changed(accession_editor_view.widgets.acc_code_entry)

    assert existing.code is None
    assert presenter.has_problems()
    assert not accession_editor_view.widgets.acc_ok_button.get_sensitive()


def test_propagation_editor_seed_fields_enable_accept(session, propagation_editor_view):
    propagation = Propagation(
        prop_type="Seed",
        date=datetime.date(2026, 4, 22),
    )
    session.add(propagation)
    date_text = propagation.date.strftime(prefs.prefs[prefs.date_format_pref])

    presenter = PropagationEditorPresenter(propagation, propagation_editor_view)

    assert propagation_editor_view.widget_get_value("prop_type_combo") == "Seed"
    assert propagation_editor_view.widget_get_value("prop_date_entry") == date_text
    assert propagation_editor_view.widgets.seed_box.get_visible()
    assert not propagation_editor_view.widgets.cutting_box.get_visible()
    assert not propagation_editor_view.widgets.prop_ok_button.get_sensitive()

    propagation_editor_view.widget_set_value("seed_nseeds_entry", "12")
    propagation_editor_view.widget_set_value("seed_sown_entry", date_text)

    assert propagation._seed.nseeds == "12"
    assert propagation._seed.date_sown == propagation.date
    assert presenter.is_dirty()
    presenter.refresh_sensitivity()
    assert propagation_editor_view.widgets.prop_ok_button.get_sensitive()


def test_propagation_editor_cutting_fields_and_rooted_rows(
    session, propagation_editor_view
):
    propagation = Propagation(
        prop_type="UnrootedCutting",
        date=datetime.date(2026, 5, 1),
    )
    session.add(propagation)

    presenter = PropagationEditorPresenter(propagation, propagation_editor_view)

    assert (
        propagation_editor_view.widget_get_value("prop_type_combo") == "UnrootedCutting"
    )
    assert propagation_editor_view.widgets.cutting_box.get_visible()
    assert not propagation_editor_view.widgets.seed_box.get_visible()
    assert not propagation_editor_view.widgets.prop_ok_button.get_sensitive()

    propagation_editor_view.widget_set_value("cutting_length_entry", "10")
    propagation_editor_view.widget_set_value("cutting_rooted_pct_entry", "75")

    assert propagation._cutting.length == "10"
    assert propagation._cutting.rooted_pct == "75"

    rooted_model = propagation_editor_view.widgets.rooted_treeview.get_model()
    assert len(rooted_model) == 0

    presenter._cutting_presenter.on_rooted_add_clicked(None)
    assert len(rooted_model) == 1
    treeiter = rooted_model.get_iter_first()
    rooted = rooted_model[treeiter][0]
    assert rooted.cutting is propagation._cutting

    propagation_editor_view.widgets.rooted_treeview.get_selection().select_iter(
        treeiter
    )
    presenter._cutting_presenter.on_rooted_remove_clicked(None)

    assert len(rooted_model) == 0
    assert rooted.cutting is None
    assert presenter.is_dirty()
    presenter.refresh_sensitivity()
    assert propagation_editor_view.widgets.prop_ok_button.get_sensitive()
