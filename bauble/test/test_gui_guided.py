import importlib.util
import sys
from pathlib import Path


def load_gui_guided_module():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "gui_guided.py"
    spec = importlib.util.spec_from_file_location("gui_guided", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_guided_issue_body_formats_multiline_markdown():
    gui_guided = load_gui_guided_module()
    result = {
        "scenario": "visual-smoke",
        "started_at": "2026-05-20T12:00:00+00:00",
        "finished_at": "2026-05-20T12:02:00+00:00",
        "app_returncode": 0,
        "run_context": {
            "git_branch": "ghini-4-dev-clean",
            "git_commit": "abc123",
            "git_describe": "v4.0.0-1-gabc123",
            "display": ":0",
        },
        "fixture": {
            "connection_name": "Guided SQLite",
            "database_file": "/tmp/guided.sqlite",
            "seed_search": "family where epithet=Guidedaceae",
            "plant_search": '"GUIDED-ACC-001.1"',
        },
        "checkpoints": [
            {
                "name": "Main window usable",
                "result": "pass",
                "note": "Menus opened normally.",
                "recorded_at": "2026-05-20T12:01:00+00:00",
            },
            {
                "name": "Basic search visible",
                "result": "fail",
                "note": "Search results did not update.",
                "recorded_at": "2026-05-20T12:02:00+00:00",
            },
        ],
        "stdout": "stdout line",
        "stderr": "stderr line",
    }

    body = gui_guided.format_issue_body(Path("result.json"), result)

    assert "\\n" not in body
    assert "## Summary\n\nGuided visual test finding" in body
    assert "- [FAIL] Basic search visible" in body
    assert "- [PASS] Main window usable" not in body
    assert "Search results did not update." in body
    assert "```text\nstderr line\n```" in body
    assert "`bug`, `gui`, `guided-test`, `needs-investigation`" in body


def test_guided_issue_body_includes_all_checkpoints_when_no_failure():
    gui_guided = load_gui_guided_module()
    result = {
        "scenario": "connection-manager",
        "checkpoints": [
            {
                "name": "Connection manager opens",
                "result": "pass",
                "note": "",
                "recorded_at": "2026-05-20T12:00:00+00:00",
            }
        ],
        "stdout": "",
        "stderr": "",
    }

    body = gui_guided.format_issue_body(Path("pass.json"), result)

    assert "- [PASS] Connection manager opens" in body
    assert "Notes: (not recorded)" in body
