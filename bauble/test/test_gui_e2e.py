import os
import signal
import subprocess
import time

import pytest


APP_COMMAND = ["python", "/app/scripts/ghini"]


@pytest.fixture
def dogtail_modules(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("PYTHONPATH", "/app")
    monkeypatch.setenv("NO_AT_BRIDGE", "0")

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
def ghini_process():
    env = os.environ.copy()
    process = subprocess.Popen(
        APP_COMMAND,
        env=env,
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


def dump_accessible_tree(node, depth=0, max_depth=3):
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


def find_named_child(node, name, role_name=None):
    return node.findChild(
        lambda child: child.name == name
        and (role_name is None or child.roleName == role_name),
        recursive=True,
        retry=False,
        requireResult=False,
    )
