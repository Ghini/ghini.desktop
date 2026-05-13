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
    enter_text(plant_entries[0], accession_code, dogtail_rawinput)
    enter_text(plant_entries[1], plant_code, dogtail_rawinput)
    enter_text(plant_entries[3], "1", dogtail_rawinput)
    enter_text(plant_entries[2], location_code, dogtail_rawinput)
    enter_text(plant_entries[1], plant_code, dogtail_rawinput)

    ok_button = find_named_child(plant_editor, "OK", role_name="push button")
    field_values = [
        plant_editor.name,
        *[accessible_text(entry) for entry in plant_entries[:4]],
    ]
    assert ok_button is not None, field_values
    assert getattr(ok_button, "sensitive", True), field_values
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


def find_named_child(node, name, role_name=None, showing_only=None):
    return node.findChild(
        lambda child: child.name == name
        and (role_name is None or child.roleName == role_name),
        recursive=True,
        retry=False,
        requireResult=False,
        showingOnly=showing_only,
    )


def find_child_by_role(node, role_name):
    return node.findChild(
        lambda child: child.roleName == role_name,
        recursive=True,
        retry=False,
        requireResult=False,
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


def enter_text(node, text, dogtail_rawinput):
    x, y = node.position
    width, height = node.size
    dogtail_rawinput.click(x + width // 2, y + height // 2)
    time.sleep(0.1)
    dogtail_rawinput.keyCombo("<Control>a")
    dogtail_rawinput.typeText(text)


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
