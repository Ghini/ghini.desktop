import os
from configparser import RawConfigParser
import signal
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
        from dogtail import tree as dogtail_tree
    except SystemExit:
        pytest.skip("dogtail requires AT-SPI toolkit accessibility")

    dogtail_config.config.logDebugToFile = False
    dogtail_config.config.logDebugToStdOut = False
    dogtail_config.config.searchCutoffCount = 1
    dogtail_config.config.defaultDelay = 0.05
    return dogtail_tree, dogtail_predicate


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
    return connection_name


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
    dogtail_tree, _dogtail_predicate = dogtail_modules
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
    dogtail_tree, _dogtail_predicate = dogtail_modules
    window = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "dialog" and node.name.startswith("Ghini"),
    )

    assert find_named_child(window, sqlite_connection) is not None
    find_named_child(window, "Connect", role_name="push button").click()

    main_window = wait_for_node(
        dogtail_tree,
        lambda node: node.roleName == "frame" and node.name.startswith("Ghini"),
        timeout=30,
    )

    assert find_child_by_role(main_window, "menu bar") is not None
    assert find_child_by_role(main_window, "combo box") is not None


def find_named_child(node, name, role_name=None):
    return node.findChild(
        lambda child: child.name == name
        and (role_name is None or child.roleName == role_name),
        recursive=True,
        retry=False,
        requireResult=False,
    )


def find_child_by_role(node, role_name):
    return node.findChild(
        lambda child: child.roleName == role_name,
        recursive=True,
        retry=False,
        requireResult=False,
    )
