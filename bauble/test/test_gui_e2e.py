import os
from configparser import RawConfigParser
import signal
import sqlite3
import subprocess
import time

import pytest


APP_COMMAND = ["python", "/app/scripts/ghini"]


@pytest.fixture
def isolated_app(tmp_path, monkeypatch):
    user = f"ghini_e2e_{tmp_path.name}".replace("-", "_")
    home = tmp_path / "home"
    home.mkdir()
    env = os.environ.copy()
    env.update(
        {
            "HOME": str(home),
            "NO_AT_BRIDGE": "0",
            "PYTHONPATH": "/app",
            "USER": user,
        }
    )

    for key, value in env.items():
        if key in {"HOME", "NO_AT_BRIDGE", "PYTHONPATH", "USER"}:
            monkeypatch.setenv(key, value)

    appdata = tmp_path / f"~{user}" / ".bauble" / "3.1"
    (appdata / "res" / "templates").mkdir(parents=True)

    return {
        "appdata": appdata,
        "cwd": tmp_path,
        "env": env,
    }


@pytest.fixture
def dogtail_modules(isolated_app):

    try:
        from dogtail import config as dogtail_config
        from dogtail import predicate as dogtail_predicate
        from dogtail import rawinput as dogtail_rawinput
        from dogtail import tree as dogtail_tree
    except SystemExit:
        pytest.skip("dogtail requires AT-SPI toolkit accessibility")

    dogtail_config.config.logDebugToFile = False
    dogtail_config.config.logDebugToStdOut = False
    dogtail_config.config.searchCutoffCount = 1
    dogtail_config.config.defaultDelay = 0.05
    return dogtail_tree, dogtail_predicate, dogtail_rawinput


@pytest.fixture
def ghini_process(isolated_app):
    process = subprocess.Popen(
        APP_COMMAND,
        cwd=isolated_app["cwd"],
        env=isolated_app["env"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        yield process
    finally:
        terminate_process(process)


@pytest.fixture
def ghini_process_factory(isolated_app):
    processes = []

    def start_process():
        process = subprocess.Popen(
            APP_COMMAND,
            cwd=isolated_app["cwd"],
            env=isolated_app["env"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        processes.append(process)
        return process

    try:
        yield start_process
    finally:
        for process in processes:
            terminate_process(process)


def terminate_process(process):
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.send_signal(signal.SIGKILL)
        process.wait(timeout=5)


@pytest.fixture
def sqlite_connection(isolated_app):
    connection_name = "E2E Garden"
    database_file = isolated_app["cwd"] / "e2e-garden.db"
    pictures_root = isolated_app["cwd"] / "pictures"
    pictures_root.mkdir()

    create_database = subprocess.run(
        [
            "python",
            "-c",
            (
                "import sys; "
                "import bauble.db as db; "
                "db.open('sqlite:///' + sys.argv[1], verify=False); "
                "db.create(import_defaults=True)"
            ),
            str(database_file),
        ],
        cwd=isolated_app["cwd"],
        env=isolated_app["env"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=60,
        check=False,
    )
    assert create_database.returncode == 0, (
        "Failed to create E2E SQLite database\n\n"
        f"stdout:\n{create_database.stdout}\n\nstderr:\n{create_database.stderr}"
    )

    write_preferences(
        isolated_app["appdata"],
        {
            connection_name: {
                "type": "SQLite",
                "file": str(database_file),
                "default": False,
                "pictures": str(pictures_root),
            }
        },
        connection_name,
    )
    return {
        "database_file": database_file,
        "name": connection_name,
    }


def write_preferences(appdata_dir, connections, default_connection):
    appdata_dir.mkdir(parents=True, exist_ok=True)
    config = RawConfigParser()
    config.add_section("bauble.config")
    config.set("bauble.config", "version", "(4, 0)")
    config.add_section("conn")
    config.set("conn", "list", str(connections))
    config.set("conn", "default", str(default_connection))
    with (appdata_dir / "config").open("w") as config_file:
        config.write(config_file)


def wait_for_node(dogtail_tree, predicate, timeout=20):
    deadline = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < deadline:
        try:
            return dogtail_tree.root.findChild(predicate, recursive=True)
        except Exception as exc:
            last_error = exc
            time.sleep(0.25)
    raise AssertionError(
        "Timed out waiting for accessible node: "
        f"{predicate}\n\nAccessible tree:\n{dump_accessible_tree(dogtail_tree.root)}"
    ) from last_error


def wait_for_absence(dogtail_tree, predicate, timeout=20):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        node = dogtail_tree.root.findChild(
            predicate,
            recursive=True,
            retry=False,
            requireResult=False,
        )
        if node is None:
            return
        time.sleep(0.25)
    raise AssertionError(
        "Accessible node remained present.\n\n"
        f"Accessible tree:\n{dump_accessible_tree(dogtail_tree.root)}"
    )


def dump_accessible_tree(node, depth=0, max_depth=6):
    if depth > max_depth:
        return ""
    role_name = getattr(node, "roleName", "")
    name = getattr(node, "name", "")
    lines = [f"{'  ' * depth}{role_name}: {name}"]
    try:
        children = list(node.children)
    except Exception:
        children = []
    for child in children[:20]:
        child_dump = dump_accessible_tree(child, depth + 1, max_depth)
        if child_dump:
            lines.append(child_dump)
    return "\n".join(lines)


def test_connection_manager_opens_and_can_be_cancelled(dogtail_modules, ghini_process):
    dogtail_tree, _dogtail_predicate, _dogtail_rawinput = dogtail_modules
    window = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name.startswith("Ghini"),
    )

    assert find_named_child(window, "Connection Details") is not None
    assert find_named_child(window, "Add", role_name="push button") is not None
    assert find_named_child(window, "Remove", role_name="push button") is not None
    assert find_named_child(window, "Connect", role_name="push button") is not None

    find_named_child(window, "Cancel", role_name="push button").click()

    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if ghini_process.poll() is not None:
            break
        time.sleep(0.25)

    assert ghini_process.poll() is not None


def test_sqlite_connection_opens_main_window(
    dogtail_modules, sqlite_connection, ghini_process
):
    dogtail_tree, _dogtail_predicate, _dogtail_rawinput = dogtail_modules
    main_window = connect_to_sqlite_database(dogtail_tree, sqlite_connection["name"])

    assert find_child_by_role(main_window, "menu bar") is not None
    assert find_child_by_role(main_window, "combo box") is not None


def test_can_search_existing_species(dogtail_modules, sqlite_connection, ghini_process):
    dogtail_tree, _dogtail_predicate, dogtail_rawinput = dogtail_modules
    family_name = "EESEARCHACEAE"
    genus_name = "Eesearchgenus"
    species_name = "eosearch"

    seed_taxonomy_location_fixture(
        sqlite_connection["database_file"],
        family_name=family_name,
        genus_name=genus_name,
        species_name=species_name,
        location_code="E2ES",
        location_name="E2E Search Bed",
    )

    main_window = connect_to_sqlite_database(dogtail_tree, sqlite_connection["name"])
    search_entry = find_child_by_role(main_window, "text")
    assert search_entry is not None, dump_accessible_tree(main_window)

    enter_text(
        search_entry,
        f"species where genus.epithet={genus_name}",
        dogtail_rawinput,
    )
    dogtail_rawinput.pressKey("Enter")

    results_view = find_child_by_role(main_window, "table")
    assert results_view is not None, dump_accessible_tree(main_window)
    wait_for_node(
        dogtail_tree,
        lambda node: node.roleName in {"table cell", "label"}
        and genus_name in node.name
        and species_name in node.name,
        timeout=20,
    )


def test_can_search_existing_accession(
    dogtail_modules, sqlite_connection, ghini_process
):
    dogtail_tree, _dogtail_predicate, dogtail_rawinput = dogtail_modules
    family_name = "EEACCSEARCHACEAE"
    genus_name = "Eeaccsearchgenus"
    species_name = "eoaccsearch"
    accession_code = "ACC-SEARCH-001"

    seed_plant_fixture(
        sqlite_connection["database_file"],
        family_name=family_name,
        genus_name=genus_name,
        species_name=species_name,
        accession_code=accession_code,
        plant_code="1",
        location_code="AS01",
        location_name="E2E Accession Search Bed",
    )

    main_window = connect_to_sqlite_database(dogtail_tree, sqlite_connection["name"])
    search_entry = find_child_by_role(main_window, "text")
    assert search_entry is not None, dump_accessible_tree(main_window)

    enter_text(search_entry, f"accession where code={accession_code}", dogtail_rawinput)
    dogtail_rawinput.pressKey("Enter")

    results_view = find_child_by_role(main_window, "table")
    assert results_view is not None, dump_accessible_tree(main_window)
    wait_for_node(
        dogtail_tree,
        lambda node: node.roleName in {"table cell", "label"}
        and accession_code in node.name,
        timeout=20,
    )

    accession_count = query_sqlite_database(
        sqlite_connection["database_file"],
        (
            "select count(*) from accession "
            "join species on accession.species_id = species.id "
            "join genus on species.genus_id = genus.id "
            "join family on genus.family_id = family.id "
            "where accession.code = ? "
            "and species.epithet = ? "
            "and genus.epithet = ? "
            "and family.epithet = ?"
        ),
        accession_code,
        species_name,
        genus_name,
        family_name,
    )
    assert accession_count == 1


def test_main_search_shows_database_completion_before_search(
    dogtail_modules, sqlite_connection, ghini_process
):
    dogtail_tree, _dogtail_predicate, dogtail_rawinput = dogtail_modules
    location_code = "GLC1"
    location_name = "E2E Completion Bed"

    seed_plant_fixture(
        sqlite_connection["database_file"],
        family_name="EECOMPLETEACEAE",
        genus_name="Eecompletegenus",
        species_name="eocomplete",
        accession_code="COMPLETE-E2E-001",
        plant_code="1",
        location_code=location_code,
        location_name=location_name,
    )

    main_window = connect_to_sqlite_database(dogtail_tree, sqlite_connection["name"])
    search_entry = find_child_by_role(main_window, "text")
    assert search_entry is not None, dump_accessible_tree(main_window)

    click_node_center(search_entry, dogtail_rawinput)
    dogtail_rawinput.keyCombo("<Control>a")
    dogtail_rawinput.pressKey("BackSpace")
    dogtail_rawinput.typeText(location_code[:2])

    wait_for_node(
        dogtail_tree,
        lambda node: getattr(node, "showing", True)
        and location_code in getattr(node, "name", ""),
        timeout=10,
    )


def test_daily_searches_do_not_log_infobox_tracebacks(
    dogtail_modules, sqlite_connection, ghini_process
):
    dogtail_tree, _dogtail_predicate, dogtail_rawinput = dogtail_modules
    family_name = "EEINFOBOXACEAE"
    genus_name = "Eeinfoboxgenus"
    species_name = "eoinfobox"
    location_code = "IB01"
    location_name = "E2E Infobox Bed"

    seed_plant_fixture(
        sqlite_connection["database_file"],
        family_name=family_name,
        genus_name=genus_name,
        species_name=species_name,
        accession_code="INFOBOX-SEARCH-001",
        plant_code="1",
        location_code=location_code,
        location_name=location_name,
    )

    main_window = connect_to_sqlite_database(dogtail_tree, sqlite_connection["name"])
    search_entry = find_child_by_role(main_window, "text")
    assert search_entry is not None, dump_accessible_tree(main_window)

    searches = [
        (f"family where epithet={family_name}", family_name),
        (f"genus where epithet={genus_name}", genus_name),
        (f"species where genus.epithet={genus_name}", species_name),
        (f"location where code={location_code}", location_code),
    ]
    for query, expected_text in searches:
        enter_text(search_entry, query, dogtail_rawinput)
        dogtail_rawinput.pressKey("Enter")
        wait_for_node(
            dogtail_tree,
            lambda node, text=expected_text: node.roleName in {"table cell", "label"}
            and text in node.name,
            timeout=20,
        )
        time.sleep(0.2)

    terminate_process(ghini_process)
    stderr = ghini_process.stderr.read() if ghini_process.stderr is not None else ""

    assert "SearchView.update_infobox failed" not in stderr


def test_main_search_no_match_recovers_with_search_button(
    dogtail_modules, sqlite_connection, ghini_process
):
    dogtail_tree, _dogtail_predicate, dogtail_rawinput = dogtail_modules
    family_name = "EERECOVERACEAE"
    genus_name = "Eerecovergenus"
    species_name = "eorecover"
    location_code = "RC01"
    location_name = "E2E Recovery Bed"

    seed_plant_fixture(
        sqlite_connection["database_file"],
        family_name=family_name,
        genus_name=genus_name,
        species_name=species_name,
        accession_code="RECOVER-E2E-001",
        plant_code="1",
        location_code=location_code,
        location_name=location_name,
    )

    main_window = connect_to_sqlite_database(dogtail_tree, sqlite_connection["name"])
    search_entry = find_child_by_role(main_window, "text")
    assert search_entry is not None, dump_accessible_tree(main_window)

    enter_text(search_entry, "location where code=DOESNOTEXIST", dogtail_rawinput)
    dogtail_rawinput.pressKey("Enter")
    time.sleep(0.5)
    fail_on_visible_error_alert(dogtail_tree, dogtail_rawinput, ghini_process)

    enter_text(search_entry, f"location where code={location_code}", dogtail_rawinput)
    search_button = find_main_search_button(main_window, search_entry)
    assert search_button is not None, dump_accessible_tree(main_window)
    click_node_center(search_button, dogtail_rawinput)

    wait_for_node(
        dogtail_tree,
        lambda node: node.roleName in {"table cell", "label"}
        and location_code in node.name
        and location_name in node.name,
        timeout=20,
    )
    fail_on_visible_error_alert(dogtail_tree, dogtail_rawinput, ghini_process)


def test_search_entry_accepts_input_after_species_editor_save(
    dogtail_modules, sqlite_connection, ghini_process
):
    dogtail_tree, _dogtail_predicate, dogtail_rawinput = dogtail_modules
    family_name = "EEAFTERSPECIESACEAE"
    genus_name = "Eeafterspeciesgenus"
    species_name = "eoafterspecies"

    main_window = connect_to_sqlite_database(dogtail_tree, sqlite_connection["name"])

    activate_menu_item(main_window, "Insert", role_name="menu")
    activate_menu_item(dogtail_tree.root, "Family", role_name="menu item")

    family_editor = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Family Editor",
    )
    family_entry = find_child_by_role(family_editor, "text")
    assert family_entry is not None, dump_accessible_tree(family_editor)
    enter_text(family_entry, family_name, dogtail_rawinput)

    find_named_child(family_editor, "Add Genera", role_name="push button").click()

    genus_editor = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Genus Editor",
    )
    genus_entries = find_children_by_role(genus_editor, "text")
    assert len(genus_entries) >= 2, dump_accessible_tree(genus_editor)
    enter_text(genus_entries[1], genus_name, dogtail_rawinput)

    find_named_child(genus_editor, "Add Species", role_name="push button").click()

    species_editor = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Species Editor",
    )
    species_entries = find_children_by_role(species_editor, "text")
    assert species_entries, dump_accessible_tree(species_editor)
    enter_text(species_entries[0], species_name, dogtail_rawinput)

    find_named_child(species_editor, "OK", role_name="push button").click()
    wait_for_absence(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Species Editor",
        timeout=20,
    )

    search_entry = find_child_by_role(main_window, "text")
    assert search_entry is not None, dump_accessible_tree(main_window)
    enter_text(search_entry, f"family where epithet={family_name}", dogtail_rawinput)
    dogtail_rawinput.pressKey("Enter")

    wait_for_node(
        dogtail_tree,
        lambda node: node.roleName in {"table cell", "label"}
        and family_name in node.name,
        timeout=20,
    )


def test_can_edit_existing_family_from_result_context_menu(
    dogtail_modules, sqlite_connection, ghini_process
):
    dogtail_tree, _dogtail_predicate, dogtail_rawinput = dogtail_modules
    family_name = "EEEDITACEAE"
    edited_family_name = "EEEDITEDACEAE"

    seed_taxonomy_location_fixture(
        sqlite_connection["database_file"],
        family_name=family_name,
        genus_name="Eeeditgenus",
        species_name="eoedit",
        location_code="E2EE",
        location_name="E2E Edit Bed",
    )

    main_window = connect_to_sqlite_database(dogtail_tree, sqlite_connection["name"])
    search_entry = find_child_by_role(main_window, "text")
    assert search_entry is not None, dump_accessible_tree(main_window)

    enter_text(search_entry, f"family where epithet={family_name}", dogtail_rawinput)
    dogtail_rawinput.pressKey("Enter")

    result = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName in {"table cell", "label"}
        and family_name in node.name,
        timeout=20,
    )
    right_click_node_center(result, dogtail_rawinput)
    activate_menu_item(dogtail_tree.root, "Edit", role_name="menu item")

    editor_window = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Family Editor",
    )
    family_entry = find_child_by_role(editor_window, "text")
    assert family_entry is not None, dump_accessible_tree(editor_window)
    assert accessible_text(family_entry) == family_name

    enter_text(family_entry, edited_family_name, dogtail_rawinput)
    find_named_child(editor_window, "OK", role_name="push button").click()
    wait_for_absence(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Family Editor",
        timeout=20,
    )
    terminate_process(ghini_process)

    family_count = query_sqlite_database(
        sqlite_connection["database_file"],
        "select count(*) from family where epithet = ?",
        edited_family_name,
    )
    old_family_count = query_sqlite_database(
        sqlite_connection["database_file"],
        "select count(*) from family where epithet = ?",
        family_name,
    )
    assert family_count == 1
    assert old_family_count == 0


def test_family_delete_confirmation_cancel_and_confirm(
    dogtail_modules, sqlite_connection, ghini_process
):
    dogtail_tree, _dogtail_predicate, dogtail_rawinput = dogtail_modules
    family_name = "EEDELETEACEAE"
    timestamp = "2026-05-13 00:00:00"

    execute_sqlite_database(
        sqlite_connection["database_file"],
        (
            "insert into family (epithet, author, qualifier, _created, _last_updated) "
            "values (?, '', '', ?, ?)"
        ),
        family_name,
        timestamp,
        timestamp,
    )

    main_window = connect_to_sqlite_database(dogtail_tree, sqlite_connection["name"])
    search_entry = find_child_by_role(main_window, "text")
    assert search_entry is not None, dump_accessible_tree(main_window)

    def search_family():
        enter_text(
            search_entry, f"family where epithet={family_name}", dogtail_rawinput
        )
        dogtail_rawinput.pressKey("Enter")
        return wait_for_node(
            dogtail_tree,
            lambda node: node.roleName in {"table cell", "label"}
            and family_name in node.name,
            timeout=20,
        )

    def request_delete():
        result = search_family()
        right_click_node_center(result, dogtail_rawinput)
        activate_menu_item(dogtail_tree.root, "Delete", role_name="menu item")
        return wait_for_node(
            dogtail_tree,
            lambda node: node.roleName in {"alert", "dialog"}
            and node_contains_text(node, "remove the family"),
            timeout=20,
        )

    confirmation = request_delete()
    assert node_contains_text(confirmation, family_name)
    find_named_child(confirmation, "No", role_name="push button").click()
    wait_for_absence(
        dogtail_tree,
        lambda node: node.roleName in {"alert", "dialog"}
        and node_contains_text(node, "remove the family"),
        timeout=20,
    )

    family_count = query_sqlite_database(
        sqlite_connection["database_file"],
        "select count(*) from family where epithet = ?",
        family_name,
    )
    assert family_count == 1

    confirmation = request_delete()
    assert node_contains_text(confirmation, family_name)
    find_named_child(confirmation, "Yes", role_name="push button").click()
    wait_for_absence(
        dogtail_tree,
        lambda node: node.roleName in {"alert", "dialog"}
        and node_contains_text(node, "remove the family"),
        timeout=20,
    )
    terminate_process(ghini_process)

    family_count = query_sqlite_database(
        sqlite_connection["database_file"],
        "select count(*) from family where epithet = ?",
        family_name,
    )
    assert family_count == 0


def test_can_search_existing_plant_and_show_details(
    dogtail_modules, sqlite_connection, ghini_process
):
    dogtail_tree, _dogtail_predicate, dogtail_rawinput = dogtail_modules
    accession_code = "SEARCH-E2E-001"
    plant_code = "1"
    location_code = "E2ESP"
    location_name = "E2E Search Plant Bed"

    seed_plant_fixture(
        sqlite_connection["database_file"],
        family_name="EEPLSEARCHACEAE",
        genus_name="Eeplantsearchgenus",
        species_name="eoplantsearch",
        accession_code=accession_code,
        plant_code=plant_code,
        location_code=location_code,
        location_name=location_name,
    )

    main_window = connect_to_sqlite_database(dogtail_tree, sqlite_connection["name"])
    search_entry = find_child_by_role(main_window, "text")
    assert search_entry is not None, dump_accessible_tree(main_window)

    enter_text(search_entry, f'"{accession_code}.{plant_code}"', dogtail_rawinput)
    dogtail_rawinput.pressKey("Enter")

    result = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName in {"table cell", "label"}
        and accession_code in node.name
        and plant_code in node.name,
        timeout=20,
    )
    click_node_center(result, dogtail_rawinput)

    wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "label" and location_name in node.name,
        timeout=20,
    )
    wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "label" and node.name == "Alive",
        timeout=20,
    )


def test_can_create_family_from_insert_menu(
    dogtail_modules, sqlite_connection, ghini_process
):
    dogtail_tree, _dogtail_predicate, dogtail_rawinput = dogtail_modules
    main_window = connect_to_sqlite_database(dogtail_tree, sqlite_connection["name"])
    family_name = "E2EACEAE"

    activate_menu_item(main_window, "Insert", role_name="menu")
    activate_menu_item(dogtail_tree.root, "Family", role_name="menu item")

    editor_window = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Family Editor",
    )
    family_entry = find_child_by_role(editor_window, "text")
    assert family_entry is not None, dump_accessible_tree(editor_window)
    family_entry.click()
    dogtail_rawinput.typeText(family_name)

    find_named_child(editor_window, "OK", role_name="push button").click()

    wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "frame" and node.name.startswith("Ghini"),
        timeout=20,
    )
    terminate_process(ghini_process)

    family_count = query_sqlite_database(
        sqlite_connection["database_file"],
        "select count(*) from family where epithet = ?",
        family_name,
    )
    assert family_count == 1


def test_can_create_genus_from_family_editor_chain(
    dogtail_modules, sqlite_connection, ghini_process
):
    dogtail_tree, _dogtail_predicate, dogtail_rawinput = dogtail_modules
    main_window = connect_to_sqlite_database(dogtail_tree, sqlite_connection["name"])
    family_name = "E2EGENACEAE"
    genus_name = "E2egenus"

    activate_menu_item(main_window, "Insert", role_name="menu")
    activate_menu_item(dogtail_tree.root, "Family", role_name="menu item")

    family_editor = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Family Editor",
    )
    family_entry = find_child_by_role(family_editor, "text")
    assert family_entry is not None, dump_accessible_tree(family_editor)
    family_entry.click()
    dogtail_rawinput.typeText(family_name)

    find_named_child(family_editor, "Add Genera", role_name="push button").click()

    genus_editor = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Genus Editor",
    )
    text_entries = find_children_by_role(genus_editor, "text")
    assert len(text_entries) >= 2, dump_accessible_tree(genus_editor)
    genus_entry = text_entries[1]
    genus_entry.click()
    dogtail_rawinput.typeText(genus_name)

    find_named_child(genus_editor, "OK", role_name="push button").click()

    wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "frame" and node.name.startswith("Ghini"),
        timeout=20,
    )
    terminate_process(ghini_process)

    genus_count = query_sqlite_database(
        sqlite_connection["database_file"],
        (
            "select count(*) from genus "
            "join family on genus.family_id = family.id "
            "where genus.epithet = ? and family.epithet = ?"
        ),
        genus_name,
        family_name,
    )
    assert genus_count == 1


def test_genus_editor_partial_family_keeps_accept_disabled_until_exact_match(
    dogtail_modules, sqlite_connection, ghini_process
):
    dogtail_tree, _dogtail_predicate, dogtail_rawinput = dogtail_modules
    family_name = "EEPARTIALACEAE"
    genus_name = "Eepartialgenus"
    timestamp = "2026-05-13 00:00:00"

    execute_sqlite_database(
        sqlite_connection["database_file"],
        (
            "insert into family (epithet, author, qualifier, _created, _last_updated) "
            "values (?, '', '', ?, ?)"
        ),
        family_name,
        timestamp,
        timestamp,
    )

    main_window = connect_to_sqlite_database(dogtail_tree, sqlite_connection["name"])
    activate_menu_item(main_window, "Insert", role_name="menu")
    activate_menu_item(dogtail_tree.root, "Genus", role_name="menu item")

    genus_editor = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Genus Editor",
    )
    entries = find_visible_text_entries_by_position(genus_editor)
    assert len(entries) >= 2, describe_text_entries(genus_editor)
    family_entry, genus_entry = entries[0], entries[1]
    ok_button = find_named_child(genus_editor, "OK", role_name="push button")
    assert ok_button is not None, dump_accessible_tree(genus_editor)
    assert not getattr(ok_button, "sensitive", True)

    enter_text(family_entry, family_name[:5], dogtail_rawinput)
    enter_text(genus_entry, genus_name, dogtail_rawinput)
    assert not getattr(ok_button, "sensitive", True), describe_text_entries(
        genus_editor
    )

    enter_text(family_entry, family_name, dogtail_rawinput)
    wait_for_sensitive(ok_button)
    ok_button.click()
    fail_on_visible_error_alert(dogtail_tree, dogtail_rawinput, ghini_process)
    wait_for_absence(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Genus Editor",
        timeout=20,
    )
    terminate_process(ghini_process)

    genus_count = query_sqlite_database(
        sqlite_connection["database_file"],
        (
            "select count(*) from genus "
            "join family on genus.family_id = family.id "
            "where genus.epithet = ? and family.epithet = ?"
        ),
        genus_name,
        family_name,
    )
    assert genus_count == 1


def test_can_create_species_from_genus_editor_chain(
    dogtail_modules, sqlite_connection, ghini_process
):
    dogtail_tree, _dogtail_predicate, dogtail_rawinput = dogtail_modules
    main_window = connect_to_sqlite_database(dogtail_tree, sqlite_connection["name"])
    family_name = "EESPECACEAE"
    genus_name = "Eespecgenus"
    species_name = "eospecies"

    activate_menu_item(main_window, "Insert", role_name="menu")
    activate_menu_item(dogtail_tree.root, "Family", role_name="menu item")

    family_editor = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Family Editor",
    )
    family_entry = find_child_by_role(family_editor, "text")
    assert family_entry is not None, dump_accessible_tree(family_editor)
    family_entry.click()
    dogtail_rawinput.typeText(family_name)

    find_named_child(family_editor, "Add Genera", role_name="push button").click()

    genus_editor = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Genus Editor",
    )
    genus_entries = find_children_by_role(genus_editor, "text")
    assert len(genus_entries) >= 2, dump_accessible_tree(genus_editor)
    genus_entries[1].click()
    dogtail_rawinput.typeText(genus_name)

    find_named_child(genus_editor, "Add Species", role_name="push button").click()

    species_editor = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Species Editor",
    )
    species_entries = find_children_by_role(species_editor, "text")
    assert species_entries, dump_accessible_tree(species_editor)
    species_entries[0].click()
    dogtail_rawinput.typeText(species_name)

    find_named_child(species_editor, "OK", role_name="push button").click()

    wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "frame" and node.name.startswith("Ghini"),
        timeout=20,
    )
    terminate_process(ghini_process)

    species_count = query_sqlite_database(
        sqlite_connection["database_file"],
        (
            "select count(*) from species "
            "join genus on species.genus_id = genus.id "
            "join family on genus.family_id = family.id "
            "where species.epithet = ? "
            "and genus.epithet = ? "
            "and family.epithet = ?"
        ),
        species_name,
        genus_name,
        family_name,
    )
    assert species_count == 1


def test_species_editor_partial_genus_keeps_accept_disabled_until_exact_match(
    dogtail_modules, sqlite_connection, ghini_process
):
    dogtail_tree, _dogtail_predicate, dogtail_rawinput = dogtail_modules
    family_name = "EESPECGENACEAE"
    genus_name = "Eespecautogenus"
    species_name = "eoautogenus"
    timestamp = "2026-05-13 00:00:00"

    execute_sqlite_database(
        sqlite_connection["database_file"],
        (
            "insert into family (epithet, author, qualifier, _created, _last_updated) "
            "values (?, '', '', ?, ?)"
        ),
        family_name,
        timestamp,
        timestamp,
    )
    execute_sqlite_database(
        sqlite_connection["database_file"],
        (
            "insert into genus "
            "(epithet, author, qualifier, family_id, _created, _last_updated) "
            "values (?, '', '', (select id from family where epithet = ?), ?, ?)"
        ),
        genus_name,
        family_name,
        timestamp,
        timestamp,
    )

    main_window = connect_to_sqlite_database(dogtail_tree, sqlite_connection["name"])
    activate_menu_item(main_window, "Insert", role_name="menu")
    activate_menu_item(dogtail_tree.root, "Species", role_name="menu item")

    species_editor = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Species Editor",
    )
    species_entries = find_visible_text_entries_by_position(species_editor)
    assert len(species_entries) >= 3, describe_text_entries(species_editor)
    genus_entry, species_entry = species_name_entries(species_entries)
    ok_button = find_named_child(species_editor, "OK", role_name="push button")
    add_accessions_button = find_named_child(
        species_editor, "Add Accessions", role_name="push button"
    )
    assert ok_button is not None, dump_accessible_tree(species_editor)
    assert add_accessions_button is not None, dump_accessible_tree(species_editor)
    assert not getattr(ok_button, "sensitive", True)
    assert not getattr(add_accessions_button, "sensitive", True)

    enter_text(genus_entry, genus_name[:6], dogtail_rawinput)
    dogtail_rawinput.pressKey("Tab")
    enter_text(species_entry, species_name, dogtail_rawinput)
    assert not getattr(ok_button, "sensitive", True), describe_text_entries(
        species_editor
    )
    assert not getattr(add_accessions_button, "sensitive", True), describe_text_entries(
        species_editor
    )

    enter_text(genus_entry, genus_name, dogtail_rawinput)
    dogtail_rawinput.pressKey("Tab")
    wait_for_sensitive(ok_button)
    wait_for_sensitive(add_accessions_button)
    ok_button.click()
    fail_on_visible_error_alert(dogtail_tree, dogtail_rawinput, ghini_process)
    wait_for_absence(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Species Editor",
        timeout=20,
    )
    terminate_process(ghini_process)

    species_count = query_sqlite_database(
        sqlite_connection["database_file"],
        (
            "select count(*) from species "
            "join genus on species.genus_id = genus.id "
            "join family on genus.family_id = family.id "
            "where species.epithet = ? "
            "and genus.epithet = ? "
            "and family.epithet = ?"
        ),
        species_name,
        genus_name,
        family_name,
    )
    assert species_count == 1


def test_species_editor_notes_tab_adds_note_and_persists(
    dogtail_modules, sqlite_connection, ghini_process
):
    dogtail_tree, _dogtail_predicate, dogtail_rawinput = dogtail_modules
    family_name = "EENOTEACEAE"
    genus_name = "Eenotegenus"
    species_name = "eonote"
    note_user = "e2e-user"
    note_category = "label"
    note_text = "Use this note on generated labels."

    seed_taxonomy_location_fixture(
        sqlite_connection["database_file"],
        family_name=family_name,
        genus_name=genus_name,
        species_name="seed",
        location_code="NT01",
        location_name="E2E Note Bed",
    )

    main_window = connect_to_sqlite_database(dogtail_tree, sqlite_connection["name"])
    activate_menu_item(main_window, "Insert", role_name="menu")
    activate_menu_item(dogtail_tree.root, "Species", role_name="menu item")

    species_editor = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Species Editor",
    )
    species_entries = find_visible_text_entries_by_position(species_editor)
    assert len(species_entries) >= 3, describe_text_entries(species_editor)
    genus_entry, species_entry = species_name_entries(species_entries)

    enter_text(genus_entry, genus_name, dogtail_rawinput)
    dogtail_rawinput.pressKey("Tab")
    enter_text(species_entry, species_name, dogtail_rawinput)

    add_species_note(
        species_editor,
        note_user,
        note_category,
        note_text,
        dogtail_rawinput,
    )

    ok_button = find_named_child(species_editor, "OK", role_name="push button")
    assert ok_button is not None, dump_accessible_tree(species_editor)
    wait_for_sensitive(ok_button)
    ok_button.click()
    fail_on_visible_error_alert(dogtail_tree, dogtail_rawinput, ghini_process)
    wait_for_absence(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Species Editor",
        timeout=20,
    )
    terminate_process(ghini_process)

    note_rows = fetch_sqlite_database(
        sqlite_connection["database_file"],
        (
            "select species_note.user, species_note.category, species_note.note "
            "from species_note "
            "join species on species_note.species_id = species.id "
            "join genus on species.genus_id = genus.id "
            "join family on genus.family_id = family.id "
            "where species.epithet = ? "
            "and genus.epithet = ? "
            "and family.epithet = ?"
        ),
        species_name,
        genus_name,
        family_name,
    )
    assert note_rows == [(note_user, note_category, note_text)]


def test_can_create_accession_from_species_editor_chain(
    dogtail_modules, sqlite_connection, ghini_process
):
    dogtail_tree, _dogtail_predicate, dogtail_rawinput = dogtail_modules
    main_window = connect_to_sqlite_database(dogtail_tree, sqlite_connection["name"])
    family_name = "EEACCACEAE"
    genus_name = "Eeaccgenus"
    species_name = "eoaccession"
    accession_code = "ACC-E2E-001"

    activate_menu_item(main_window, "Insert", role_name="menu")
    activate_menu_item(dogtail_tree.root, "Family", role_name="menu item")

    family_editor = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Family Editor",
    )
    family_entry = find_child_by_role(family_editor, "text")
    assert family_entry is not None, dump_accessible_tree(family_editor)
    family_entry.click()
    dogtail_rawinput.typeText(family_name)

    find_named_child(family_editor, "Add Genera", role_name="push button").click()

    genus_editor = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Genus Editor",
    )
    genus_entries = find_children_by_role(genus_editor, "text")
    assert len(genus_entries) >= 2, dump_accessible_tree(genus_editor)
    genus_entries[1].click()
    dogtail_rawinput.typeText(genus_name)

    find_named_child(genus_editor, "Add Species", role_name="push button").click()

    species_editor = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Species Editor",
    )
    species_entries = find_children_by_role(species_editor, "text")
    assert species_entries, dump_accessible_tree(species_editor)
    species_entries[0].click()
    dogtail_rawinput.typeText(species_name)

    find_named_child(species_editor, "OK", role_name="push button").click()
    wait_for_absence(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Species Editor",
        timeout=20,
    )

    activate_menu_item(main_window, "Insert", role_name="menu")
    activate_menu_item(dogtail_tree.root, "Accession", role_name="menu item")

    accession_editor = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Accession Editor",
    )
    dogtail_rawinput.typeText(f"{genus_name} {species_name}")
    dogtail_rawinput.pressKey("Tab")

    accession_entries = find_children_by_role(accession_editor, "text")
    assert len(accession_entries) >= 2, dump_accessible_tree(accession_editor)
    accession_entries[1].click()
    dogtail_rawinput.keyCombo("<Control>a")
    dogtail_rawinput.typeText(accession_code)

    find_named_child(accession_editor, "OK", role_name="push button").click()

    wait_for_absence(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Accession Editor",
        timeout=20,
    )

    terminate_process(ghini_process)

    accession_count = query_sqlite_database(
        sqlite_connection["database_file"],
        (
            "select count(*) from accession "
            "join species on accession.species_id = species.id "
            "join genus on species.genus_id = genus.id "
            "join family on genus.family_id = family.id "
            "where accession.code = ? "
            "and species.epithet = ? "
            "and genus.epithet = ? "
            "and family.epithet = ?"
        ),
        accession_code,
        species_name,
        genus_name,
        family_name,
    )
    accession_total = query_sqlite_database(
        sqlite_connection["database_file"],
        "select count(*) from accession",
    )
    species_total = query_sqlite_database(
        sqlite_connection["database_file"],
        (
            "select count(*) from species "
            "join genus on species.genus_id = genus.id "
            "join family on genus.family_id = family.id "
            "where species.epithet = ? "
            "and genus.epithet = ? "
            "and family.epithet = ?"
        ),
        species_name,
        genus_name,
        family_name,
    )
    assert (
        accession_count == 1
    ), f"accession_total={accession_total}, species_total={species_total}"


def test_add_accessions_from_unsaved_species_editor_commits_accession(
    dogtail_modules, sqlite_connection, ghini_process
):
    dogtail_tree, _dogtail_predicate, dogtail_rawinput = dogtail_modules
    family_name = "EEUNSAVEDACCACEAE"
    genus_name = "Eeunsavedaccgenus"
    species_name = "eounsavedacc"
    accession_code = "UNSAVED-ACC-E2E"
    timestamp = "2026-05-13 00:00:00"

    execute_sqlite_database(
        sqlite_connection["database_file"],
        (
            "insert into family (epithet, author, qualifier, _created, _last_updated) "
            "values (?, '', '', ?, ?)"
        ),
        family_name,
        timestamp,
        timestamp,
    )
    execute_sqlite_database(
        sqlite_connection["database_file"],
        (
            "insert into genus "
            "(epithet, author, qualifier, family_id, _created, _last_updated) "
            "values (?, '', '', (select id from family where epithet = ?), ?, ?)"
        ),
        genus_name,
        family_name,
        timestamp,
        timestamp,
    )

    main_window = connect_to_sqlite_database(dogtail_tree, sqlite_connection["name"])
    activate_menu_item(main_window, "Insert", role_name="menu")
    activate_menu_item(dogtail_tree.root, "Species", role_name="menu item")

    species_editor = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Species Editor",
    )
    species_entries = find_visible_text_entries_by_position(species_editor)
    assert len(species_entries) >= 3, describe_text_entries(species_editor)
    genus_entry, species_entry = species_name_entries(species_entries)
    enter_text(genus_entry, genus_name, dogtail_rawinput)
    dogtail_rawinput.pressKey("Tab")
    enter_text(species_entry, species_name, dogtail_rawinput)

    add_accessions_button = find_named_child(
        species_editor, "Add Accessions", role_name="push button"
    )
    assert add_accessions_button is not None, dump_accessible_tree(species_editor)
    wait_for_sensitive(add_accessions_button)
    add_accessions_button.click()

    accession_editor = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Accession Editor",
    )
    assert (
        find_text_entry_containing(accession_editor, f"{genus_name} {species_name}")
        is not None
    ), describe_text_entries(accession_editor)

    accession_entries = find_visible_text_entries_by_position(accession_editor)
    assert len(accession_entries) >= 2, describe_text_entries(accession_editor)
    enter_text(accession_entries[1], accession_code, dogtail_rawinput)

    ok_button = find_named_child(accession_editor, "OK", role_name="push button")
    assert ok_button is not None, dump_accessible_tree(accession_editor)
    wait_for_sensitive(ok_button)
    ok_button.click()
    fail_on_visible_error_alert(dogtail_tree, dogtail_rawinput, ghini_process)
    wait_for_absence(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Accession Editor",
        timeout=20,
    )
    wait_for_absence(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Species Editor",
        timeout=20,
    )
    terminate_process(ghini_process)

    accession_rows = fetch_sqlite_database(
        sqlite_connection["database_file"],
        (
            "select accession.code, species.epithet, genus.epithet, family.epithet "
            "from accession "
            "join species on accession.species_id = species.id "
            "join genus on species.genus_id = genus.id "
            "join family on genus.family_id = family.id "
            "where accession.code = ?"
        ),
        accession_code,
    )
    assert accession_rows == [(accession_code, species_name, genus_name, family_name)]


def test_daily_species_editor_add_accession_creates_plant_with_source(
    dogtail_modules, sqlite_connection, ghini_process_factory
):
    dogtail_tree, _dogtail_predicate, dogtail_rawinput = dogtail_modules
    family_name = "EEDAILYACEAE"
    genus_name = "Eedailygenus"
    species_name = "eodaily"
    accession_code = "DAILY-E2E-001"
    plant_code = "1"
    location_code = "EDLY"
    location_name = "E2E Daily Workflow Bed"
    source_name = "E2E Daily Workflow Nursery"
    source_code = "DW-2026-001"
    plant_quantity = "7"
    vernacular_name = "Daily workflow label"
    vernacular_language = "English"
    note_user = "e2e-daily"
    note_category = "label"
    note_text = "Daily workflow note for label review."

    seed_family_genus_location_source_fixture(
        sqlite_connection["database_file"],
        family_name=family_name,
        genus_name=genus_name,
        location_code=location_code,
        location_name=location_name,
        source_name=source_name,
    )

    ghini_process = ghini_process_factory()
    main_window = connect_to_sqlite_database(dogtail_tree, sqlite_connection["name"])

    activate_menu_item(main_window, "Insert", role_name="menu")
    activate_menu_item(dogtail_tree.root, "Species", role_name="menu item")

    species_editor = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Species Editor",
    )
    species_entries = find_visible_text_entries_by_position(species_editor)
    assert len(species_entries) >= 3, describe_text_entries(species_editor)
    genus_entry, species_entry = species_name_entries(species_entries)

    enter_text(genus_entry, genus_name, dogtail_rawinput)
    dogtail_rawinput.pressKey("Tab")
    enter_text(species_entry, species_name, dogtail_rawinput)
    add_species_vernacular_name(
        species_editor,
        vernacular_name,
        vernacular_language,
        dogtail_tree,
        dogtail_rawinput,
    )
    add_species_note(
        species_editor,
        note_user,
        note_category,
        note_text,
        dogtail_rawinput,
    )

    add_accessions_button = find_named_child(
        species_editor, "Add Accessions", role_name="push button"
    )
    assert add_accessions_button is not None, dump_accessible_tree(species_editor)
    assert getattr(add_accessions_button, "sensitive", True), dump_accessible_tree(
        species_editor
    )
    add_accessions_button.click()

    accession_editor = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Accession Editor",
    )
    assert (
        find_text_entry_containing(accession_editor, f"{genus_name} {species_name}")
        is not None
    ), describe_text_entries(accession_editor)

    accession_entries = find_visible_text_entries_by_position(accession_editor)
    assert len(accession_entries) >= 6, describe_text_entries(accession_editor)
    enter_text(accession_entries[1], accession_code, dogtail_rawinput)

    left_column_entries = text_entries_in_column(
        accession_entries, accession_entries[1]
    )
    assert len(left_column_entries) >= 4, describe_text_entries(accession_editor)
    enter_text(left_column_entries[2], "Seed", dogtail_rawinput)
    enter_text(left_column_entries[3], plant_quantity, dogtail_rawinput)

    right_column_entries = text_entries_to_right_of(
        accession_entries,
        accession_entries[1],
        minimum_x_offset=220,
    )
    assert len(right_column_entries) >= 3, describe_text_entries(accession_editor)
    enter_text(right_column_entries[1], "13-05-2026", dogtail_rawinput)
    enter_text(right_column_entries[2], "14-05-2026", dogtail_rawinput)

    accession_combos = find_visible_combo_boxes_by_position(accession_editor)
    assert len(accession_combos) >= 2, describe_combo_boxes(accession_editor)
    select_combo_item_by_text(
        accession_combos[-2],
        "Accession of wild source",
        dogtail_tree,
        dogtail_rawinput,
    )
    wait_for_sensitive(accession_combos[-1])
    select_combo_item_by_text(
        accession_combos[-1],
        "Wild native",
        dogtail_tree,
        dogtail_rawinput,
    )

    source_tab = find_named_child(accession_editor, "Source", showing_only=True)
    assert source_tab is not None, dump_accessible_tree(accession_editor)
    click_node_center(source_tab, dogtail_rawinput)

    source_entries = wait_for_visible_text_entries(accession_editor, minimum=1)
    enter_text(source_entries[0], source_name, dogtail_rawinput)
    dogtail_rawinput.pressKey("Tab")
    source_entries = wait_for_visible_text_entries(accession_editor, minimum=2)
    enter_text_by_keyboard(source_entries[1], source_code, dogtail_rawinput)
    source_field_values = [accessible_text(entry) for entry in source_entries]

    add_plants_button = find_named_child(
        accession_editor, "Add plants", role_name="push button"
    )
    assert add_plants_button is not None, dump_accessible_tree(accession_editor)
    assert getattr(add_plants_button, "sensitive", True), dump_accessible_tree(
        accession_editor
    )
    add_plants_button.click()

    plant_editor = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name.startswith("Plant Editor"),
    )
    plant_entries = find_children_by_role(plant_editor, "text")
    assert len(plant_entries) >= 4, dump_accessible_tree(plant_editor)
    assert accessible_text(plant_entries[1]) == plant_code, describe_text_entries(
        plant_editor
    )
    plant_material_combo = find_combo_box_named(plant_editor, "Planting")
    assert plant_material_combo is not None, describe_combo_boxes(plant_editor)
    select_combo_item_by_text(
        plant_material_combo,
        "Seed/Spore",
        dogtail_tree,
        dogtail_rawinput,
    )
    enter_text(plant_entries[3], plant_quantity, dogtail_rawinput)
    click_node_center(plant_entries[2], dogtail_rawinput)
    dogtail_rawinput.keyCombo("<Control>a")
    dogtail_rawinput.pressKey("BackSpace")
    dogtail_rawinput.typeText(location_code[:2])
    wait_for_node(
        dogtail_tree,
        lambda node: getattr(node, "showing", True)
        and location_code in getattr(node, "name", "")
        and location_name in getattr(node, "name", ""),
        timeout=10,
    )
    enter_text(plant_entries[2], location_code, dogtail_rawinput)
    dogtail_rawinput.pressKey("Tab")

    plant_ok = find_named_child(plant_editor, "OK", role_name="push button")
    assert plant_ok is not None, dump_accessible_tree(plant_editor)
    wait_for_sensitive(plant_ok)
    plant_ok.click()
    wait_for_absence(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name.startswith("Plant Editor"),
        timeout=20,
    )
    fail_on_visible_error_alert(dogtail_tree, dogtail_rawinput, ghini_process)

    terminate_process(ghini_process)
    stderr = ghini_process.stderr.read() if ghini_process.stderr is not None else ""

    daily_rows = fetch_sqlite_database(
        sqlite_connection["database_file"],
        (
            "select family.epithet, genus.epithet, species.epithet, "
            "accession.code, accession.recvd_type, accession.quantity_recvd, "
            "accession.date_accd, accession.date_recvd, accession.prov_type, "
            "accession.wild_prov_status, source.sources_code, contact.name, "
            "plant.code, plant.acc_type, plant.quantity, "
            "location.code, location.name "
            "from species "
            "join genus on species.genus_id = genus.id "
            "join family on genus.family_id = family.id "
            "join accession on accession.species_id = species.id "
            "join source on source.accession_id = accession.id "
            "join contact on source.source_detail_id = contact.id "
            "join plant on plant.accession_id = accession.id "
            "join location on plant.location_id = location.id "
            "where accession.code = ?"
        ),
        accession_code,
    )
    diagnostic_rows = {
        "accession": fetch_sqlite_database(
            sqlite_connection["database_file"],
            "select code, species_id from accession where code = ?",
            accession_code,
        ),
        "species": fetch_sqlite_database(
            sqlite_connection["database_file"],
            "select id, epithet, genus_id from species where epithet = ?",
            species_name,
        ),
        "genus": fetch_sqlite_database(
            sqlite_connection["database_file"],
            "select id, epithet, family_id from genus where epithet = ?",
            genus_name,
        ),
        "family": fetch_sqlite_database(
            sqlite_connection["database_file"],
            "select id, epithet from family where epithet = ?",
            family_name,
        ),
        "full_left_join": fetch_sqlite_database(
            sqlite_connection["database_file"],
            (
                "select accession.id, accession.code, species.id, species.epithet, "
                "genus.id, genus.epithet, family.id, family.epithet, "
                "source.id, source.sources_code, source.source_detail_id, "
                "contact.id, contact.name, plant.id, plant.code, "
                "location.id, location.code, location.name "
                "from accession "
                "left join species on accession.species_id = species.id "
                "left join genus on species.genus_id = genus.id "
                "left join family on genus.family_id = family.id "
                "left join source on source.accession_id = accession.id "
                "left join contact on source.source_detail_id = contact.id "
                "left join plant on plant.accession_id = accession.id "
                "left join location on plant.location_id = location.id "
                "where accession.code = ?"
            ),
            accession_code,
        ),
        "source": fetch_sqlite_database(
            sqlite_connection["database_file"],
            (
                "select source.sources_code, source.source_detail_id, "
                "source.accession_id from source"
            ),
        ),
        "source_contact": fetch_sqlite_database(
            sqlite_connection["database_file"],
            (
                "select source.sources_code, source.source_detail_id, "
                "source.accession_id, contact.id, contact.name "
                "from source "
                "left join contact on source.source_detail_id = contact.id"
            ),
        ),
        "contact": fetch_sqlite_database(
            sqlite_connection["database_file"],
            "select id, name from contact where name = ?",
            source_name,
        ),
        "plant": fetch_sqlite_database(
            sqlite_connection["database_file"],
            (
                "select plant.code, plant.acc_type, plant.quantity, "
                "accession.code, location.code "
                "from plant "
                "join accession on plant.accession_id = accession.id "
                "join location on plant.location_id = location.id"
            ),
        ),
        "vernacular": fetch_sqlite_database(
            sqlite_connection["database_file"],
            (
                "select vernacular_name.name, vernacular_name.language, "
                "default_vernacular_name.vernacular_name_id is not null "
                "from vernacular_name "
                "join species on vernacular_name.species_id = species.id "
                "left join default_vernacular_name "
                "on default_vernacular_name.species_id = species.id "
                "and default_vernacular_name.vernacular_name_id = vernacular_name.id "
                "where species.epithet = ?"
            ),
            species_name,
        ),
        "notes": fetch_sqlite_database(
            sqlite_connection["database_file"],
            (
                "select species_note.user, species_note.category, species_note.note "
                "from species_note "
                "join species on species_note.species_id = species.id "
                "where species.epithet = ?"
            ),
            species_name,
        ),
    }
    assert daily_rows == [
        (
            family_name,
            genus_name,
            species_name,
            accession_code,
            "SEED",
            7,
            "2026-05-13",
            "2026-05-14",
            "Wild",
            "WildNative",
            source_code,
            source_name,
            plant_code,
            "Seed",
            int(plant_quantity),
            location_code,
            location_name,
        )
    ], (
        f"diagnostics={diagnostic_rows!r}\n"
        f"source_field_values={source_field_values!r}\n"
        f"stderr_tail={stderr[-1000:]!r}"
    )
    assert diagnostic_rows["vernacular"] == [(vernacular_name, vernacular_language, 1)]
    assert diagnostic_rows["notes"] == [(note_user, note_category, note_text)]


def test_can_edit_existing_accession_from_result_context_menu(
    dogtail_modules, sqlite_connection, ghini_process
):
    dogtail_tree, _dogtail_predicate, dogtail_rawinput = dogtail_modules
    family_name = "EEEDITACCACEAE"
    genus_name = "Eeeditaccgenus"
    species_name = "eoeditacc"
    accession_code = "ACC-EDIT-001"
    edited_accession_code = "ACC-EDIT-002"

    seed_plant_fixture(
        sqlite_connection["database_file"],
        family_name=family_name,
        genus_name=genus_name,
        species_name=species_name,
        accession_code=accession_code,
        plant_code="1",
        location_code="EA01",
        location_name="E2E Accession Bed",
    )

    main_window = connect_to_sqlite_database(dogtail_tree, sqlite_connection["name"])
    search_entry = find_child_by_role(main_window, "text")
    assert search_entry is not None, dump_accessible_tree(main_window)

    enter_text(search_entry, f"accession where code={accession_code}", dogtail_rawinput)
    dogtail_rawinput.pressKey("Enter")

    result = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName in {"table cell", "label"}
        and accession_code in node.name,
        timeout=20,
    )
    right_click_node_center(result, dogtail_rawinput)
    activate_menu_item(dogtail_tree.root, "Edit", role_name="menu item")

    accession_editor = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Accession Editor",
    )
    accession_code_entry = find_text_entry_with_value(accession_editor, accession_code)
    assert accession_code_entry is not None, dump_accessible_tree(accession_editor)

    enter_text(accession_code_entry, edited_accession_code, dogtail_rawinput)

    ok_button = find_named_child(accession_editor, "OK", role_name="push button")
    assert ok_button is not None, dump_accessible_tree(accession_editor)
    assert getattr(ok_button, "sensitive", True), dump_accessible_tree(accession_editor)
    ok_button.click()
    wait_for_absence(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Accession Editor",
        timeout=20,
    )
    terminate_process(ghini_process)

    edited_count = query_sqlite_database(
        sqlite_connection["database_file"],
        "select count(*) from accession where code = ?",
        edited_accession_code,
    )
    old_code_count = query_sqlite_database(
        sqlite_connection["database_file"],
        "select count(*) from accession where code = ?",
        accession_code,
    )
    assert edited_count == 1
    assert old_code_count == 0


def test_can_select_existing_source_when_editing_accession(
    dogtail_modules, sqlite_connection, ghini_process
):
    dogtail_tree, _dogtail_predicate, dogtail_rawinput = dogtail_modules
    family_name = "EESOURCEACEAE"
    genus_name = "Eesourcegenus"
    species_name = "eosource"
    accession_code = "SOURCE-E2E-001"
    plant_code = "1"
    source_name = "Daily Workflow Nursery"
    source_code = "DW-2026-001"
    timestamp = "2026-05-13 00:00:00"
    source_contact_names = [
        source_name,
        "daily workflow nursery",
        "Aardvark Daily Workflow Source",
        "Workflow Specialty Nursery",
        "Zeta Daily Workflow Supplier",
    ]

    seed_plant_fixture(
        sqlite_connection["database_file"],
        family_name=family_name,
        genus_name=genus_name,
        species_name=species_name,
        accession_code=accession_code,
        plant_code=plant_code,
        location_code="E2SO",
        location_name="E2E Source Bed",
    )
    for contact_name in source_contact_names:
        execute_sqlite_database(
            sqlite_connection["database_file"],
            (
                "insert into contact (name, description, _created, _last_updated) "
                "values (?, '', ?, ?)"
            ),
            contact_name,
            timestamp,
            timestamp,
        )
    target_contact_id = query_sqlite_database(
        sqlite_connection["database_file"],
        "select id from contact where name = ?",
        source_name,
    )

    main_window = connect_to_sqlite_database(dogtail_tree, sqlite_connection["name"])
    search_entry = find_child_by_role(main_window, "text")
    assert search_entry is not None, dump_accessible_tree(main_window)
    enter_text(search_entry, f"accession where code={accession_code}", dogtail_rawinput)
    dogtail_rawinput.pressKey("Enter")

    result = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName in {"table cell", "label"}
        and accession_code in node.name,
        timeout=20,
    )
    right_click_node_center(result, dogtail_rawinput)
    activate_menu_item(dogtail_tree.root, "Edit", role_name="menu item")

    accession_editor = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Accession Editor",
    )
    assert find_text_entry_with_value(accession_editor, accession_code) is not None

    source_tab = find_named_child(accession_editor, "Source", showing_only=True)
    assert source_tab is not None, dump_accessible_tree(accession_editor)
    click_node_center(source_tab, dogtail_rawinput)

    source_entries = find_visible_text_entries_by_position(accession_editor)
    assert source_entries, dump_accessible_tree(accession_editor)
    enter_text(source_entries[0], source_name, dogtail_rawinput)
    dogtail_rawinput.pressKey("Tab")
    source_entries = [
        entry
        for entry in find_visible_text_entries_by_position(accession_editor)
        if entry.size[0] > 10 and entry.size[1] > 10
    ]
    assert len(source_entries) >= 2, "\n".join(
        [
            dump_accessible_tree(accession_editor, max_depth=10),
            *[
                f"{index}: {accessible_text(entry)!r} "
                f"pos={entry.position} size={entry.size}"
                for index, entry in enumerate(source_entries)
            ],
        ]
    )
    enter_text_by_keyboard(source_entries[1], source_code, dogtail_rawinput)

    ok_button = find_named_child(accession_editor, "OK", role_name="push button")
    source_entries = [
        entry
        for entry in find_visible_text_entries_by_position(accession_editor)
        if entry.size[0] > 10 and entry.size[1] > 10
    ]
    field_values = [accessible_text(entry) for entry in source_entries]
    assert ok_button is not None, field_values
    assert getattr(ok_button, "sensitive", True), field_values
    ok_button.click()
    fail_on_visible_error_alert(dogtail_tree, dogtail_rawinput, ghini_process)
    wait_for_absence(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Accession Editor",
        timeout=20,
    )
    terminate_process(ghini_process)
    stderr = ghini_process.stderr.read() if ghini_process.stderr is not None else ""

    source_rows = fetch_sqlite_database(
        sqlite_connection["database_file"],
        (
            "select source.sources_code, contact.name, contact.id "
            "from source "
            "join accession on source.accession_id = accession.id "
            "join contact on source.source_detail_id = contact.id "
            "where accession.code = ?"
        ),
        accession_code,
    )
    accession_rows = fetch_sqlite_database(
        sqlite_connection["database_file"],
        (
            "select accession.code, accession.species_id, source.sources_code, "
            "source.source_detail_id "
            "from accession "
            "left join source on source.accession_id = accession.id "
            "where accession.code = ?"
        ),
        accession_code,
    )
    assert source_rows == [(source_code, source_name, target_contact_id)], {
        "accession_rows": accession_rows,
        "field_values": field_values,
        "stderr": stderr,
    }


def test_can_create_source_from_accession_editor(
    dogtail_modules, sqlite_connection, ghini_process
):
    dogtail_tree, _dogtail_predicate, dogtail_rawinput = dogtail_modules
    family_name = "EENEWSOURCEACEAE"
    genus_name = "Eenewsourcegenus"
    species_name = "eonewsource"
    accession_code = "NEW-SOURCE-E2E-001"
    source_name = "E2E New Source Nursery"

    seed_plant_fixture(
        sqlite_connection["database_file"],
        family_name=family_name,
        genus_name=genus_name,
        species_name=species_name,
        accession_code=accession_code,
        plant_code="1",
        location_code="E2NS",
        location_name="E2E New Source Bed",
    )

    main_window = connect_to_sqlite_database(dogtail_tree, sqlite_connection["name"])
    search_entry = find_child_by_role(main_window, "text")
    assert search_entry is not None, dump_accessible_tree(main_window)
    enter_text(search_entry, f"accession where code={accession_code}", dogtail_rawinput)
    dogtail_rawinput.pressKey("Enter")

    result = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName in {"table cell", "label"}
        and accession_code in node.name,
        timeout=20,
    )
    right_click_node_center(result, dogtail_rawinput)
    activate_menu_item(dogtail_tree.root, "Edit", role_name="menu item")

    accession_editor = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Accession Editor",
    )
    source_tab = find_named_child(accession_editor, "Source", showing_only=True)
    assert source_tab is not None, dump_accessible_tree(accession_editor)
    click_node_center(source_tab, dogtail_rawinput)

    new_button = find_named_child(accession_editor, "New", role_name="push button")
    assert new_button is not None, dump_accessible_tree(accession_editor)
    new_button.click()

    contact_editor = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog"
        and node.name == "Contact (Donor) Editor",
    )
    contact_entries = find_visible_text_entries_by_position(contact_editor)
    assert contact_entries, dump_accessible_tree(contact_editor)
    enter_text_by_keyboard(contact_entries[0], source_name, dogtail_rawinput)

    contact_ok = find_named_child(contact_editor, "OK", role_name="push button")
    assert contact_ok is not None, dump_accessible_tree(contact_editor)
    assert getattr(contact_ok, "sensitive", True), dump_accessible_tree(contact_editor)
    click_node_center(contact_ok, dogtail_rawinput)
    wait_for_absence(
        dogtail_tree,
        lambda node: node.roleName == "dialog"
        and node.name == "Contact (Donor) Editor",
        timeout=20,
    )
    source_entries = wait_for_visible_text_entries(accession_editor, minimum=1)
    assert accessible_text(source_entries[0]) == source_name

    ok_button = find_named_child(accession_editor, "OK", role_name="push button")
    assert ok_button is not None, dump_accessible_tree(accession_editor)
    assert getattr(ok_button, "sensitive", True), dump_accessible_tree(accession_editor)
    ok_button.click()
    fail_on_visible_error_alert(dogtail_tree, dogtail_rawinput, ghini_process)
    wait_for_absence(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Accession Editor",
        timeout=20,
    )
    terminate_process(ghini_process)
    stderr = ghini_process.stderr.read() if ghini_process.stderr is not None else ""

    source_rows = fetch_sqlite_database(
        sqlite_connection["database_file"],
        (
            "select source.sources_code, contact.name "
            "from source "
            "join accession on source.accession_id = accession.id "
            "join contact on source.source_detail_id = contact.id "
            "where accession.code = ?"
        ),
        accession_code,
    )
    assert source_rows == [(None, source_name)], {
        "stderr": stderr,
        "source_rows": source_rows,
    }


def test_can_create_location_from_insert_menu(
    dogtail_modules, sqlite_connection, ghini_process
):
    dogtail_tree, _dogtail_predicate, dogtail_rawinput = dogtail_modules
    location_code = "E2EL"
    location_name = "E2E Plant Bed"

    main_window = connect_to_sqlite_database(dogtail_tree, sqlite_connection["name"])

    activate_menu_item(main_window, "Insert", role_name="menu")
    activate_menu_item(dogtail_tree.root, "Location", role_name="menu item")

    location_editor = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog"
        and find_named_child(node, "OK", role_name="push button") is not None
        and find_named_child(node, "Add plants", role_name="push button") is not None,
    )
    location_entries = [
        entry
        for entry in find_children_by_role(location_editor, "text")
        if getattr(entry, "showing", True)
    ]
    assert len(location_entries) >= 3, dump_accessible_tree(location_editor)

    type_into_empty_text(location_entries[1], location_code, dogtail_rawinput)
    type_into_empty_text(location_entries[2], location_name, dogtail_rawinput)

    ok_button = find_named_child(location_editor, "OK", role_name="push button")
    field_values = [accessible_text(entry) for entry in location_entries[:3]]
    assert ok_button is not None, field_values
    assert getattr(ok_button, "sensitive", True), field_values
    ok_button.click()
    wait_for_absence(
        dogtail_tree,
        lambda node: node.roleName == "dialog"
        and find_named_child(node, "Add plants", role_name="push button") is not None,
        timeout=20,
    )

    search_entry = find_child_by_role(main_window, "text")
    assert search_entry is not None, dump_accessible_tree(main_window)
    enter_text(search_entry, f"location where code={location_code}", dogtail_rawinput)
    dogtail_rawinput.pressKey("Enter")
    wait_for_node(
        dogtail_tree,
        lambda node: node.roleName in {"table cell", "label"}
        and location_code in node.name
        and location_name in node.name,
        timeout=20,
    )

    terminate_process(ghini_process)

    location_count = query_sqlite_database(
        sqlite_connection["database_file"],
        "select count(*) from location where code = ? and name = ?",
        location_code,
        location_name,
    )
    assert location_count == 1


def test_location_editor_tab_moves_code_to_name_and_enables_accept(
    dogtail_modules, sqlite_connection, ghini_process
):
    dogtail_tree, _dogtail_predicate, dogtail_rawinput = dogtail_modules
    location_code = "TAB1"
    location_name = "E2E Keyboard Bed"

    main_window = connect_to_sqlite_database(dogtail_tree, sqlite_connection["name"])

    activate_menu_item(main_window, "Insert", role_name="menu")
    activate_menu_item(dogtail_tree.root, "Location", role_name="menu item")

    location_editor = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog"
        and find_named_child(node, "OK", role_name="push button") is not None
        and find_named_child(node, "Add plants", role_name="push button") is not None,
    )
    location_entries = find_visible_text_entries_by_position(location_editor)
    assert len(location_entries) >= 3, dump_accessible_tree(location_editor)
    code_entry = location_entries[0]
    name_entry = location_entries[1]

    enter_text_by_keyboard(code_entry, location_code, dogtail_rawinput)
    dogtail_rawinput.pressKey("Tab")
    dogtail_rawinput.typeText(location_name)
    time.sleep(0.1)
    assert accessible_text(code_entry) == location_code
    assert accessible_text(name_entry) == location_name

    ok_button = find_named_child(location_editor, "OK", role_name="push button")
    assert ok_button is not None, dump_accessible_tree(location_editor)
    wait_for_sensitive(ok_button)
    ok_button.click()
    fail_on_visible_error_alert(dogtail_tree, dogtail_rawinput, ghini_process)
    wait_for_absence(
        dogtail_tree,
        lambda node: node.roleName == "dialog"
        and find_named_child(node, "Add plants", role_name="push button") is not None,
        timeout=20,
    )
    terminate_process(ghini_process)

    location_count = query_sqlite_database(
        sqlite_connection["database_file"],
        "select count(*) from location where code = ? and name = ?",
        location_code,
        location_name,
    )
    assert location_count == 1


def test_can_edit_existing_location_from_result_context_menu(
    dogtail_modules, sqlite_connection, ghini_process
):
    dogtail_tree, _dogtail_predicate, dogtail_rawinput = dogtail_modules
    location_code = "E2ED"
    location_name = "E2E Display Bed"
    edited_location_name = "E2E Edited Bed"
    timestamp = "2026-05-13 00:00:00"

    execute_sqlite_database(
        sqlite_connection["database_file"],
        (
            "insert into location (code, name, description, _created, _last_updated) "
            "values (?, ?, '', ?, ?)"
        ),
        location_code,
        location_name,
        timestamp,
        timestamp,
    )

    main_window = connect_to_sqlite_database(dogtail_tree, sqlite_connection["name"])
    search_entry = find_child_by_role(main_window, "text")
    assert search_entry is not None, dump_accessible_tree(main_window)

    enter_text(search_entry, f"location where code={location_code}", dogtail_rawinput)
    dogtail_rawinput.pressKey("Enter")

    result = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName in {"table cell", "label"}
        and location_code in node.name
        and location_name in node.name,
        timeout=20,
    )
    right_click_node_center(result, dogtail_rawinput)
    activate_menu_item(dogtail_tree.root, "Edit", role_name="menu item")

    location_editor = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog"
        and find_named_child(node, "OK", role_name="push button") is not None
        and find_named_child(node, "Add plants", role_name="push button") is not None,
    )
    location_entries = [
        entry
        for entry in find_children_by_role(location_editor, "text")
        if getattr(entry, "showing", True)
    ]
    assert len(location_entries) >= 3, dump_accessible_tree(location_editor)
    assert accessible_text(location_entries[1]) == location_code
    assert accessible_text(location_entries[2]) == location_name

    enter_text(location_entries[2], edited_location_name, dogtail_rawinput)

    ok_button = find_named_child(location_editor, "OK", role_name="push button")
    field_values = [accessible_text(entry) for entry in location_entries[:3]]
    assert ok_button is not None, field_values
    assert getattr(ok_button, "sensitive", True), field_values
    ok_button.click()
    wait_for_absence(
        dogtail_tree,
        lambda node: node.roleName == "dialog"
        and find_named_child(node, "Add plants", role_name="push button") is not None,
        timeout=20,
    )
    terminate_process(ghini_process)

    edited_count = query_sqlite_database(
        sqlite_connection["database_file"],
        "select count(*) from location where code = ? and name = ?",
        location_code,
        edited_location_name,
    )
    old_name_count = query_sqlite_database(
        sqlite_connection["database_file"],
        "select count(*) from location where code = ? and name = ?",
        location_code,
        location_name,
    )
    assert edited_count == 1
    assert old_name_count == 0


def test_can_create_plant_from_insert_menu(
    dogtail_modules, sqlite_connection, ghini_process_factory
):
    dogtail_tree, _dogtail_predicate, dogtail_rawinput = dogtail_modules
    family_name = "EEPLANTACEAE"
    genus_name = "Eeplantgenus"
    species_name = "eoplant"
    accession_code = "PLANT-E2E-001"
    location_code = "E2EL"
    location_name = "E2E Plant Bed"
    plant_code = "1"

    execute_sqlite_database(
        sqlite_connection["database_file"],
        (
            "insert into location (code, name, _created, _last_updated) "
            "values (?, ?, current_timestamp, current_timestamp)"
        ),
        location_code,
        location_name,
    )

    ghini_process = ghini_process_factory()
    main_window = connect_to_sqlite_database(dogtail_tree, sqlite_connection["name"])

    activate_menu_item(main_window, "Insert", role_name="menu")
    activate_menu_item(dogtail_tree.root, "Family", role_name="menu item")

    family_editor = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Family Editor",
    )
    family_entry = find_child_by_role(family_editor, "text")
    assert family_entry is not None, dump_accessible_tree(family_editor)
    family_entry.click()
    dogtail_rawinput.typeText(family_name)

    find_named_child(family_editor, "Add Genera", role_name="push button").click()

    genus_editor = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Genus Editor",
    )
    genus_entries = find_children_by_role(genus_editor, "text")
    assert len(genus_entries) >= 2, dump_accessible_tree(genus_editor)
    genus_entries[1].click()
    dogtail_rawinput.typeText(genus_name)

    find_named_child(genus_editor, "Add Species", role_name="push button").click()

    species_editor = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Species Editor",
    )
    species_entries = find_children_by_role(species_editor, "text")
    assert species_entries, dump_accessible_tree(species_editor)
    species_entries[0].click()
    dogtail_rawinput.typeText(species_name)

    find_named_child(species_editor, "OK", role_name="push button").click()
    wait_for_absence(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Species Editor",
        timeout=20,
    )

    activate_menu_item(main_window, "Insert", role_name="menu")
    activate_menu_item(dogtail_tree.root, "Accession", role_name="menu item")

    accession_editor = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Accession Editor",
    )
    dogtail_rawinput.typeText(f"{genus_name} {species_name}")
    dogtail_rawinput.pressKey("Tab")

    accession_entries = find_children_by_role(accession_editor, "text")
    assert len(accession_entries) >= 2, dump_accessible_tree(accession_editor)
    accession_entries[1].click()
    dogtail_rawinput.keyCombo("<Control>a")
    dogtail_rawinput.typeText(accession_code)

    find_named_child(accession_editor, "Add plants", role_name="push button").click()

    plant_editor = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name.startswith("Plant Editor"),
    )
    plant_entries = find_children_by_role(plant_editor, "text")
    assert len(plant_entries) >= 4, dump_accessible_tree(plant_editor)
    # Dogtail reports text fields in GTK container order for this dialog.
    enter_text(plant_entries[1], plant_code, dogtail_rawinput)
    enter_text(plant_entries[3], "1", dogtail_rawinput)
    enter_text(plant_entries[2], location_code, dogtail_rawinput)
    dogtail_rawinput.pressKey("Tab")

    ok_button = find_named_child(plant_editor, "OK", role_name="push button")
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and not getattr(ok_button, "sensitive", True):
        time.sleep(0.25)
    assert getattr(ok_button, "sensitive", True), "\n".join(
        [
            dump_accessible_tree(plant_editor, max_depth=10),
            *[
                f"{index}: {accessible_text(entry)!r} pos={entry.position} size={entry.size}"
                for index, entry in enumerate(
                    find_children_by_role(plant_editor, "text")
                )
            ],
        ]
    )
    ok_button.click()
    wait_for_absence(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name.startswith("Plant Editor"),
        timeout=20,
    )
    terminate_process(ghini_process)

    plant_count = query_sqlite_database(
        sqlite_connection["database_file"],
        (
            "select count(*) from plant "
            "join accession on plant.accession_id = accession.id "
            "join species on accession.species_id = species.id "
            "join genus on species.genus_id = genus.id "
            "join family on genus.family_id = family.id "
            "join location on plant.location_id = location.id "
            "where plant.code = ? "
            "and species.epithet = ? "
            "and genus.epithet = ? "
            "and family.epithet = ? "
            "and location.code = ? "
            "and location.name = ?"
        ),
        plant_code,
        species_name,
        genus_name,
        family_name,
        location_code,
        location_name,
    )
    plant_rows = fetch_sqlite_database(
        sqlite_connection["database_file"],
        (
            "select plant.code, accession.code, species.epithet, genus.epithet, "
            "family.epithet, location.code, location.name "
            "from plant "
            "join accession on plant.accession_id = accession.id "
            "join species on accession.species_id = species.id "
            "join genus on species.genus_id = genus.id "
            "join family on genus.family_id = family.id "
            "join location on plant.location_id = location.id"
        ),
    )
    assert plant_count == 1, plant_rows


def test_can_edit_existing_plant_from_result_context_menu(
    dogtail_modules, sqlite_connection, ghini_process
):
    dogtail_tree, _dogtail_predicate, dogtail_rawinput = dogtail_modules
    family_name = "EEEDITPLANTACEAE"
    genus_name = "Eeeditplantgenus"
    species_name = "eoeditplant"
    accession_code = "PLANT-EDIT-001"
    plant_code = "P1"
    edited_plant_code = "P2"
    location_code = "EP01"
    location_name = "E2E Plant Edit Bed"

    seed_plant_fixture(
        sqlite_connection["database_file"],
        family_name=family_name,
        genus_name=genus_name,
        species_name=species_name,
        accession_code=accession_code,
        plant_code=plant_code,
        location_code=location_code,
        location_name=location_name,
    )

    main_window = connect_to_sqlite_database(dogtail_tree, sqlite_connection["name"])
    search_entry = find_child_by_role(main_window, "text")
    assert search_entry is not None, dump_accessible_tree(main_window)

    enter_text(search_entry, f"{accession_code}.{plant_code}", dogtail_rawinput)
    dogtail_rawinput.pressKey("Enter")

    result = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName in {"table cell", "label"}
        and f"{accession_code}.{plant_code}" in node.name,
        timeout=20,
    )
    right_click_node_center(result, dogtail_rawinput)
    activate_menu_item(dogtail_tree.root, "Edit", role_name="menu item")

    plant_editor = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name.startswith("Plant Editor"),
    )
    plant_code_entry = find_text_entry_with_value(plant_editor, plant_code)
    assert plant_code_entry is not None, dump_accessible_tree(plant_editor)

    enter_text(plant_code_entry, edited_plant_code, dogtail_rawinput)
    assert accessible_text(plant_code_entry) == edited_plant_code

    ok_button = find_named_child(plant_editor, "OK", role_name="push button")
    assert ok_button is not None, dump_accessible_tree(plant_editor)
    assert getattr(ok_button, "sensitive", True), dump_accessible_tree(plant_editor)
    ok_button.click()
    wait_for_absence(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name.startswith("Plant Editor"),
        timeout=20,
    )
    terminate_process(ghini_process)

    edited_count = query_sqlite_database(
        sqlite_connection["database_file"],
        (
            "select count(*) from plant "
            "join accession on plant.accession_id = accession.id "
            "where accession.code = ? and plant.code = ?"
        ),
        accession_code,
        edited_plant_code,
    )
    old_code_count = query_sqlite_database(
        sqlite_connection["database_file"],
        (
            "select count(*) from plant "
            "join accession on plant.accession_id = accession.id "
            "where accession.code = ? and plant.code = ?"
        ),
        accession_code,
        plant_code,
    )
    assert edited_count == 1
    assert old_code_count == 0


def test_can_create_seed_propagation_from_plant_editor(
    dogtail_modules, sqlite_connection, ghini_process_factory
):
    dogtail_tree, _dogtail_predicate, dogtail_rawinput = dogtail_modules
    accession_code = "PROP-E2E-001"
    location_code = "E2EP"
    location_name = "E2E Propagation Bed"
    plant_code = "1"
    propagation_date = "2026-05-13"
    propagation_date_input = "13-05-2026"
    genus_name = "Eepropgenus"
    species_name = "eopropagation"

    seed_plant_fixture(
        sqlite_connection["database_file"],
        family_name="EEPROPACEAE",
        genus_name=genus_name,
        species_name=species_name,
        accession_code=accession_code,
        plant_code=plant_code,
        location_code=location_code,
        location_name=location_name,
    )

    ghini_process = ghini_process_factory()
    main_window = connect_to_sqlite_database(dogtail_tree, sqlite_connection["name"])
    search_entry = find_child_by_role(main_window, "text")
    assert search_entry is not None, dump_accessible_tree(main_window)

    enter_text(search_entry, f"{accession_code}.{plant_code}", dogtail_rawinput)
    dogtail_rawinput.pressKey("Enter")
    result = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName in {"table cell", "label"}
        and f"{accession_code}.{plant_code}" in node.name,
        timeout=20,
    )
    right_click_node_center(result, dogtail_rawinput)
    activate_menu_item(dogtail_tree.root, "Edit", role_name="menu item")

    plant_editor = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name.startswith("Plant Editor"),
    )

    propagation_tab = find_named_child(plant_editor, "Propagations", showing_only=True)
    assert propagation_tab is not None, dump_accessible_tree(plant_editor)
    dogtail_rawinput.keyCombo("<Control>Page_Down")
    time.sleep(0.1)

    find_named_child(
        propagation_tab, "Add", role_name="push button", showing_only=True
    ).click()

    propagation_editor = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Propagation Editor",
    )
    propagation_entries = find_visible_text_entries_by_position(propagation_editor)
    assert len(propagation_entries) >= 4, dump_accessible_tree(propagation_editor)
    enter_text(propagation_entries[0], propagation_date_input, dogtail_rawinput)
    enter_text(propagation_entries[2], "12", dogtail_rawinput)
    enter_text(propagation_entries[3], propagation_date_input, dogtail_rawinput)

    propagation_ok = find_named_child(propagation_editor, "OK", role_name="push button")
    propagation_values = [accessible_text(entry) for entry in propagation_entries]
    assert propagation_ok is not None, propagation_values
    assert getattr(propagation_ok, "sensitive", True), "\n".join(
        f"{index}: {value!r} pos={entry.position} size={entry.size}"
        for index, (entry, value) in enumerate(
            zip(propagation_entries, propagation_values)
        )
    )
    propagation_ok.click()
    wait_for_absence(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name == "Propagation Editor",
        timeout=20,
    )

    plant_ok = find_named_child(plant_editor, "OK", role_name="push button")
    assert plant_ok is not None, dump_accessible_tree(plant_editor)
    assert getattr(plant_ok, "sensitive", True), "\n".join(
        f"{index}: {accessible_text(entry)!r} pos={entry.position} size={entry.size}"
        for index, entry in enumerate(
            find_visible_text_entries_by_position(plant_editor)
        )
    )
    plant_ok.click()
    wait_for_absence(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name.startswith("Plant Editor"),
        timeout=20,
    )
    fail_on_visible_error_alert(dogtail_tree, dogtail_rawinput, ghini_process)

    terminate_process(ghini_process)

    propagation_rows = fetch_sqlite_database(
        sqlite_connection["database_file"],
        (
            "select propagation.prop_type, propagation.date, prop_seed.nseeds, "
            "prop_seed.date_sown, plant.code, accession.code "
            "from propagation "
            "join plant_prop on propagation.id = plant_prop.propagation_id "
            "join plant on plant_prop.plant_id = plant.id "
            "join accession on plant.accession_id = accession.id "
            "join prop_seed on propagation.id = prop_seed.propagation_id "
            "where accession.code = ? and plant.code = ?"
        ),
        accession_code,
        plant_code,
    )
    assert propagation_rows == [
        (
            "Seed",
            propagation_date,
            12,
            propagation_date,
            plant_code,
            accession_code,
        )
    ]


def connect_to_sqlite_database(dogtail_tree, connection_name):
    window = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name.startswith("Ghini"),
    )

    assert find_named_child(window, connection_name) is not None
    find_named_child(window, "Connect", role_name="push button").click()

    return wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "frame" and node.name.startswith("Ghini"),
        timeout=30,
    )


def find_named_child(node, name, role_name=None, showing_only=None) -> Optional[Any]:
    return node.findChild(
        lambda child: child.name == name
        and (role_name is None or child.roleName == role_name),
        recursive=True,
        retry=False,
        requireResult=False,
        showingOnly=showing_only,
    )


def find_child_by_role(node, role_name) -> Optional[Any]:
    return node.findChild(
        lambda child: child.roleName == role_name,
        recursive=True,
        retry=False,
        requireResult=False,
    )


def find_text_entry_with_value(node, value) -> Optional[Any]:
    return node.findChild(
        lambda child: child.roleName == "text" and accessible_text(child) == value,
        recursive=True,
        retry=False,
        requireResult=False,
    )


def find_text_entry_containing(node, value) -> Optional[Any]:
    return node.findChild(
        lambda child: child.roleName == "text"
        and value in accessible_text(child).replace("\u200b", ""),
        recursive=True,
        retry=False,
        requireResult=False,
    )


def node_contains_text(node, text):
    if text in getattr(node, "name", ""):
        return True
    return (
        node.findChild(
            lambda child: text in getattr(child, "name", ""),
            recursive=True,
            retry=False,
            requireResult=False,
        )
        is not None
    )


def find_children_by_role(node, role_name):
    matches = []

    def collect(current):
        if getattr(current, "roleName", None) == role_name:
            matches.append(current)
        try:
            children = list(current.children)
        except Exception:
            return
        for child in children:
            collect(child)

    collect(node)
    return matches


def find_visible_text_entries_by_position(node):
    entries = [
        entry
        for entry in find_children_by_role(node, "text")
        if getattr(entry, "showing", True)
    ]
    return sorted(entries, key=lambda entry: (entry.position[1], entry.position[0]))


def text_entries_in_column(entries, reference_entry, tolerance=90):
    reference_x = reference_entry.position[0]
    return sorted(
        [
            entry
            for entry in entries
            if abs(entry.position[0] - reference_x) <= tolerance
            and entry.size[0] > 10
            and entry.size[1] > 10
        ],
        key=lambda entry: entry.position[1],
    )


def text_entries_to_right_of(entries, reference_entry, minimum_x_offset=150):
    reference_x = reference_entry.position[0]
    return sorted(
        [
            entry
            for entry in entries
            if entry.position[0] >= reference_x + minimum_x_offset
            and entry.size[0] > 10
            and entry.size[1] > 10
        ],
        key=lambda entry: (entry.position[1], entry.position[0]),
    )


def find_visible_combo_boxes_by_position(node):
    combos = [
        combo
        for combo in find_children_by_role(node, "combo box")
        if getattr(combo, "showing", True) and combo.size[0] > 10 and combo.size[1] > 10
    ]
    return sorted(combos, key=lambda combo: (combo.position[1], combo.position[0]))


def find_combo_box_named(node, name):
    for combo in find_visible_combo_boxes_by_position(node):
        if combo.name == name:
            return combo
    return None


def describe_combo_boxes(node):
    return "\n".join(
        [
            dump_accessible_tree(node, max_depth=10),
            *[
                f"{index}: {combo.name!r} "
                f"pos={combo.position} size={combo.size} "
                f"sensitive={getattr(combo, 'sensitive', True)}"
                for index, combo in enumerate(
                    find_visible_combo_boxes_by_position(node)
                )
            ],
        ]
    )


def wait_for_visible_text_entries(node, minimum=1, timeout=20):
    deadline = time.monotonic() + timeout
    entries = []
    while time.monotonic() < deadline:
        entries = [
            entry
            for entry in find_visible_text_entries_by_position(node)
            if entry.size[0] > 10 and entry.size[1] > 10
        ]
        if len(entries) >= minimum:
            return entries
        time.sleep(0.25)

    details = [
        dump_accessible_tree(node, max_depth=10),
        *[
            f"{index}: {accessible_text(entry)!r} "
            f"pos={entry.position} size={entry.size}"
            for index, entry in enumerate(entries)
        ],
    ]
    raise AssertionError("\n".join(details))


def describe_text_entries(node):
    return "\n".join(
        [
            dump_accessible_tree(node, max_depth=10),
            *[
                f"{index}: {accessible_text(entry)!r} "
                f"pos={entry.position} size={entry.size} showing={entry.showing}"
                for index, entry in enumerate(find_children_by_role(node, "text"))
            ],
        ]
    )


def species_name_entries(entries):
    top_left_entry = min(
        entries, key=lambda entry: (entry.position[1], entry.position[0])
    )
    left_column_x = top_left_entry.position[0]
    left_column_entries = sorted(
        [entry for entry in entries if abs(entry.position[0] - left_column_x) < 100],
        key=lambda entry: entry.position[1],
    )
    assert len(left_column_entries) >= 2, "\n".join(
        f"{index}: {accessible_text(entry)!r} pos={entry.position}"
        for index, entry in enumerate(entries)
    )
    return left_column_entries[0], left_column_entries[1]


def add_species_vernacular_name(
    species_editor,
    vernacular_name,
    vernacular_language,
    dogtail_tree,
    dogtail_rawinput,
):
    additional_info_tab = find_named_child(
        species_editor, "Additional info", showing_only=True
    )
    assert additional_info_tab is not None, dump_accessible_tree(species_editor)
    click_node_center(additional_info_tab, dogtail_rawinput)

    vernacular_label = wait_for_node(
        dogtail_tree,
        lambda node: node.name == "Vernacular names" and getattr(node, "showing", True),
        timeout=10,
    )
    add_button = visible_button_near(
        species_editor,
        None,
        x_min=vernacular_label.position[0],
        x_max=vernacular_label.position[0] + 360,
        y_min=vernacular_label.position[1] - 40,
    )
    assert add_button is not None, dump_accessible_tree(species_editor, max_depth=10)
    click_node_center(add_button, dogtail_rawinput)
    time.sleep(0.2)

    dogtail_rawinput.typeText(vernacular_name)
    dogtail_rawinput.pressKey("Tab")
    time.sleep(0.2)
    dogtail_rawinput.typeText(vernacular_language)
    dogtail_rawinput.pressKey("Tab")
    time.sleep(0.2)


def add_species_note(
    species_editor,
    note_user,
    note_category,
    note_text,
    dogtail_rawinput,
):
    notes_tab = find_named_child(species_editor, "Notes", showing_only=True)
    assert notes_tab is not None, dump_accessible_tree(species_editor)
    click_node_center(notes_tab, dogtail_rawinput)

    add_button = find_named_child(
        species_editor, "Add", role_name="push button", showing_only=True
    )
    assert add_button is not None, dump_accessible_tree(species_editor)
    click_node_center(add_button, dogtail_rawinput)

    note_entries = wait_for_visible_text_entries(species_editor, minimum=4)
    note_body = max(note_entries, key=lambda entry: entry.size[1])
    note_fields = [entry for entry in note_entries if entry is not note_body]
    empty_fields = [entry for entry in note_fields if accessible_text(entry) == ""]
    assert len(empty_fields) >= 2, describe_text_entries(species_editor)
    user_entry = min(
        empty_fields, key=lambda entry: (entry.position[1], entry.position[0])
    )
    category_entry = max(
        empty_fields, key=lambda entry: (entry.position[1], -entry.position[0])
    )

    enter_text_by_keyboard(user_entry, note_user, dogtail_rawinput)
    enter_text_by_keyboard(category_entry, note_category, dogtail_rawinput)
    enter_text_by_keyboard(note_body, note_text, dogtail_rawinput)


def visible_button_near(node, name, x_min=None, x_max=None, y_min=None, y_max=None):
    candidates = []
    for button in find_children_by_role(node, "push button"):
        if name is not None and button.name != name:
            continue
        if not getattr(button, "showing", True):
            continue
        x, y = button.position
        if x_min is not None and x < x_min:
            continue
        if x_max is not None and x > x_max:
            continue
        if y_min is not None and y < y_min:
            continue
        if y_max is not None and y > y_max:
            continue
        candidates.append(button)
    if not candidates:
        return None
    return min(candidates, key=lambda button: (button.position[1], button.position[0]))


def wait_for_sensitive(node, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if getattr(node, "sensitive", True):
            return
        time.sleep(0.25)
    raise AssertionError(f"Node did not become sensitive: {node.name!r}")


def select_combo_item_by_text(combo, text, dogtail_tree, dogtail_rawinput):
    click_node_center(combo, dogtail_rawinput)
    item = wait_for_node(
        dogtail_tree,
        lambda node: node.name == text
        and getattr(node, "showing", True)
        and node.roleName in {"menu item", "list item", "table cell", "label"},
        timeout=10,
    )
    click_node_center(item, dogtail_rawinput)
    time.sleep(0.2)


def find_main_search_button(main_window, search_entry):
    entry_x, entry_y = search_entry.position
    entry_width, entry_height = search_entry.size
    entry_center_y = entry_y + entry_height // 2
    buttons = [
        button
        for button in find_children_by_role(main_window, "push button")
        if getattr(button, "showing", True)
        and button.size[0] > 10
        and button.size[1] > 10
    ]
    candidates = [
        button
        for button in buttons
        if button.position[0] > entry_x + entry_width
        and abs((button.position[1] + button.size[1] // 2) - entry_center_y) < 40
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda button: button.position[0])


def enter_text(node, text, dogtail_rawinput):
    x, y = node.position
    width, height = node.size
    dogtail_rawinput.click(x + width // 2, y + height // 2)
    time.sleep(0.1)
    try:
        node.text = text
    except AttributeError:
        dogtail_rawinput.keyCombo("<Control>a")
        dogtail_rawinput.typeText(text)
    time.sleep(0.1)
    assert accessible_text(node) == text


def type_into_empty_text(node, text, dogtail_rawinput):
    x, y = node.position
    width, height = node.size
    dogtail_rawinput.click(x + width // 2, y + height // 2)
    time.sleep(0.1)
    try:
        node.text = text
    except AttributeError:
        dogtail_rawinput.typeText(text)
    time.sleep(0.1)
    assert accessible_text(node) == text


def enter_text_by_keyboard(node, text, dogtail_rawinput):
    x, y = node.position
    width, height = node.size
    dogtail_rawinput.click(x + width // 2, y + height // 2)
    time.sleep(0.1)
    dogtail_rawinput.keyCombo("<Control>a")
    dogtail_rawinput.pressKey("BackSpace")
    dogtail_rawinput.typeText(text)
    time.sleep(0.1)
    assert accessible_text(node) == text


def click_node_center(node, dogtail_rawinput):
    try:
        node.grabFocus()
    except Exception:
        pass
    x, y = node.position
    width, height = node.size
    dogtail_rawinput.click(x + width // 2, y + height // 2)
    time.sleep(0.1)


def activate_node(node, dogtail_rawinput):
    try:
        if "click" in node.actions:
            node.doActionNamed("click")
            time.sleep(0.1)
            return
        if "activate" in node.actions:
            node.doActionNamed("activate")
            time.sleep(0.1)
            return
    except Exception:
        pass
    click_node_center(node, dogtail_rawinput)


def fail_on_visible_error_alert(dogtail_tree, dogtail_rawinput, process=None):
    alert = dogtail_tree.root.findChild(
        lambda node: node.roleName == "alert" and getattr(node, "showing", True),
        recursive=True,
        retry=False,
        requireResult=False,
    )
    if alert is None:
        return

    details = find_named_child(alert, "Details", role_name="toggle button")
    if details is not None:
        activate_node(details, dogtail_rawinput)
        time.sleep(0.2)

    stderr = ""
    if process is not None:
        terminate_process(process)
        stderr = process.stderr.read() if process.stderr is not None else ""

    raise AssertionError(
        "Unexpected GUI error alert.\n\n"
        f"Accessible tree:\n{dump_accessible_tree(alert, max_depth=8)}\n\n"
        f"stderr:\n{stderr}"
    )


def right_click_node_center(node, dogtail_rawinput):
    try:
        node.grabFocus()
    except Exception:
        pass
    x, y = node.position
    width, height = node.size
    dogtail_rawinput.click(x + width // 2, y + height // 2, button=3)
    time.sleep(0.1)


def accessible_text(node):
    try:
        return node.queryText().getText(0, -1)
    except Exception:
        return getattr(node, "text", "")


def activate_menu_item(root, name, role_name=None):
    item = find_named_child(root, name, role_name=role_name, showing_only=True)
    assert item is not None, dump_accessible_tree(root)
    item.click()


def query_sqlite_database(database_file, query, *parameters):
    result = subprocess.run(
        [
            "python",
            "-c",
            (
                "import sqlite3, sys; "
                "db, query, *params = sys.argv[1:]; "
                "conn = sqlite3.connect(db); "
                "print(conn.execute(query, params).fetchone()[0]); "
                "conn.close()"
            ),
            str(database_file),
            query,
            *parameters,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return int(result.stdout.strip())


def fetch_sqlite_database(database_file, query, *parameters):
    with sqlite3.connect(database_file) as connection:
        return connection.execute(query, parameters).fetchall()


def execute_sqlite_database(database_file, statement, *parameters):
    with sqlite3.connect(database_file) as connection:
        connection.execute(statement, parameters)


def seed_taxonomy_location_fixture(
    database_file,
    *,
    family_name,
    genus_name,
    species_name,
    location_code,
    location_name,
):
    timestamp = "2026-05-13 00:00:00"
    with sqlite3.connect(database_file) as connection:
        cursor = connection.cursor()
        cursor.execute(
            (
                "insert into family (epithet, author, qualifier, _created, _last_updated) "
                "values (?, '', '', ?, ?)"
            ),
            (family_name, timestamp, timestamp),
        )
        family_id = cursor.lastrowid
        cursor.execute(
            (
                "insert into genus "
                "(epithet, author, qualifier, family_id, _created, _last_updated) "
                "values (?, '', '', ?, ?, ?)"
            ),
            (genus_name, family_id, timestamp, timestamp),
        )
        genus_id = cursor.lastrowid
        cursor.execute(
            (
                "insert into species (epithet, genus_id, _created, _last_updated) "
                "values (?, ?, ?, ?)"
            ),
            (species_name, genus_id, timestamp, timestamp),
        )
        cursor.execute(
            (
                "insert into location (code, name, _created, _last_updated) "
                "values (?, ?, ?, ?)"
            ),
            (location_code, location_name, timestamp, timestamp),
        )


def seed_family_genus_location_source_fixture(
    database_file,
    *,
    family_name,
    genus_name,
    location_code,
    location_name,
    source_name,
):
    timestamp = "2026-05-13 00:00:00"
    with sqlite3.connect(database_file) as connection:
        cursor = connection.cursor()
        cursor.execute(
            (
                "insert into family (epithet, author, qualifier, _created, _last_updated) "
                "values (?, '', '', ?, ?)"
            ),
            (family_name, timestamp, timestamp),
        )
        family_id = cursor.lastrowid
        cursor.execute(
            (
                "insert into genus "
                "(epithet, author, qualifier, family_id, _created, _last_updated) "
                "values (?, '', '', ?, ?, ?)"
            ),
            (genus_name, family_id, timestamp, timestamp),
        )
        cursor.execute(
            (
                "insert into location (code, name, _created, _last_updated) "
                "values (?, ?, ?, ?)"
            ),
            (location_code, location_name, timestamp, timestamp),
        )
        cursor.execute(
            (
                "insert into contact (name, description, _created, _last_updated) "
                "values (?, '', ?, ?)"
            ),
            (source_name, timestamp, timestamp),
        )


def seed_plant_fixture(
    database_file,
    *,
    family_name,
    genus_name,
    species_name,
    accession_code,
    plant_code,
    location_code,
    location_name,
):
    timestamp = "2026-05-13 00:00:00"
    with sqlite3.connect(database_file) as connection:
        cursor = connection.cursor()
        cursor.execute(
            (
                "insert into family (epithet, author, qualifier, _created, _last_updated) "
                "values (?, '', '', ?, ?)"
            ),
            (family_name, timestamp, timestamp),
        )
        family_id = cursor.lastrowid
        cursor.execute(
            (
                "insert into genus "
                "(epithet, author, qualifier, family_id, _created, _last_updated) "
                "values (?, '', '', ?, ?, ?)"
            ),
            (genus_name, family_id, timestamp, timestamp),
        )
        genus_id = cursor.lastrowid
        cursor.execute(
            (
                "insert into species (epithet, genus_id, _created, _last_updated) "
                "values (?, ?, ?, ?)"
            ),
            (species_name, genus_id, timestamp, timestamp),
        )
        species_id = cursor.lastrowid
        cursor.execute(
            (
                "insert into accession "
                "(code, id_qual, private, species_id, _created, _last_updated) "
                "values (?, '', 0, ?, ?, ?)"
            ),
            (accession_code, species_id, timestamp, timestamp),
        )
        accession_id = cursor.lastrowid
        cursor.execute(
            (
                "insert into location (code, name, _created, _last_updated) "
                "values (?, ?, ?, ?)"
            ),
            (location_code, location_name, timestamp, timestamp),
        )
        location_id = cursor.lastrowid
        cursor.execute(
            (
                "insert into plant "
                "(code, acc_type, memorial, quantity, accession_id, location_id, "
                "_created, _last_updated) "
                "values (?, 'Plant', 0, 1, ?, ?, ?, ?)"
            ),
            (plant_code, accession_id, location_id, timestamp, timestamp),
        )
