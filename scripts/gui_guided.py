#!/usr/bin/env python3
"""Run visible, user-confirmed GUI test scenarios and record feedback."""

from __future__ import annotations

import argparse
from configparser import RawConfigParser
import json
import os
import signal
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory


APP_COMMAND = ["python", "/app/scripts/ghini"]
RESULT_DIR = Path("test-results/gui-guided")
GUIDED_CONNECTION_NAME = "Guided SQLite"
GUIDED_FIXTURE = {
    "institution_name": "Guided Test Institution",
    "family_name": "Guidedaceae",
    "genus_name": "Guidedgenus",
    "species_name": "guidedspecies",
    "accession_code": "GUIDED-ACC-001",
    "location_code": "GLOC",
    "location_name": "Guided Test Bed",
    "plant_code": "1",
    "plant_search": '"GUIDED-ACC-001.1"',
    "seed_search": "family where epithet=Guidedaceae",
}
GUIDED_FIXTURE_SEED_SCRIPT = """
import sqlite3
import sys

import bauble.db as db
from bauble.plugins.garden.institution import Institution

database = sys.argv[1]
timestamp = "2026-05-14 00:00:00"

db.open("sqlite:///" + database, verify=False)
institution = Institution()
institution.name = "Guided Test Institution"
institution.write()

with sqlite3.connect(database) as connection:
    cursor = connection.cursor()
    cursor.execute(
        "insert into family (epithet, author, qualifier, _created, _last_updated) "
        "values (?, '', '', ?, ?)",
        ("Guidedaceae", timestamp, timestamp),
    )
    family_id = cursor.lastrowid
    cursor.execute(
        "insert into genus "
        "(epithet, author, qualifier, family_id, _created, _last_updated) "
        "values (?, '', '', ?, ?, ?)",
        ("Guidedgenus", family_id, timestamp, timestamp),
    )
    genus_id = cursor.lastrowid
    cursor.execute(
        "insert into species (epithet, genus_id, _created, _last_updated) "
        "values (?, ?, ?, ?)",
        ("guidedspecies", genus_id, timestamp, timestamp),
    )
    species_id = cursor.lastrowid
    cursor.execute(
        "insert into accession "
        "(code, id_qual, private, species_id, _created, _last_updated) "
        "values (?, '', 0, ?, ?, ?)",
        ("GUIDED-ACC-001", species_id, timestamp, timestamp),
    )
    accession_id = cursor.lastrowid
    cursor.execute(
        "insert into location (code, name, _created, _last_updated) "
        "values (?, ?, ?, ?)",
        ("GLOC", "Guided Test Bed", timestamp, timestamp),
    )
    location_id = cursor.lastrowid
    cursor.execute(
        "insert into plant "
        "(code, acc_type, memorial, quantity, accession_id, location_id, "
        "_created, _last_updated) "
        "values (?, 'Plant', 0, 1, ?, ?, ?, ?)",
        ("1", accession_id, location_id, timestamp, timestamp),
    )
"""


@dataclass(frozen=True)
class Checkpoint:
    name: str
    expected: tuple[str, ...]
    instructions: tuple[str, ...] = ()


@dataclass(frozen=True)
class Scenario:
    name: str
    description: str
    checkpoints: tuple[Checkpoint, ...]
    launch_app: bool = True


SCENARIOS = {
    "connection-manager": Scenario(
        name="connection-manager",
        description="Open Ghini and visually inspect the connection manager.",
        checkpoints=(
            Checkpoint(
                name="Connection manager opens",
                instructions=(
                    "Wait for the initial Ghini connection dialog.",
                    "Do not connect yet.",
                ),
                expected=(
                    "The dialog title starts with Ghini and shows the current version.",
                    "Saved connections appear in the connection selector.",
                    "Connection Details can expand and collapse.",
                    "Add, Remove, Cancel, and Connect buttons are visible.",
                    "No error dialog or traceback appears.",
                ),
            ),
        ),
    ),
    "connect-main-window": Scenario(
        name="connect-main-window",
        description="Connect to a configured database and inspect the main window.",
        checkpoints=(
            Checkpoint(
                name="Connected main window",
                instructions=(
                    "Use the connection manager to connect to a test database.",
                    "Wait for the primary Ghini window.",
                ),
                expected=(
                    "The main window opens without error dialogs.",
                    "The menu bar is visible and Insert/Edit/View menus open.",
                    "The search control is visible and accepts input.",
                    "No terminal traceback appears during startup.",
                ),
            ),
        ),
    ),
    "visual-smoke": Scenario(
        name="visual-smoke",
        description=(
            "Run a short visible smoke test from startup through search. "
            "Use --sqlite-fixture for a disposable database."
        ),
        checkpoints=(
            Checkpoint(
                name="Connection manager visible",
                instructions=(
                    "Wait for the initial Ghini connection dialog.",
                    "Inspect the saved connection list and connection details.",
                ),
                expected=(
                    "The connection dialog opens on the host display.",
                    "The current Ghini version is visible in the title bar.",
                    "No error dialog or traceback appears before connecting.",
                ),
            ),
            Checkpoint(
                name="Main window usable",
                instructions=(
                    f"Connect to {GUIDED_CONNECTION_NAME}, or another test database.",
                    "If the Institution Editor opens unexpectedly, record that in the checkpoint notes.",
                    "Wait for the main Ghini window.",
                    "Open one menu and click back into the search field.",
                ),
                expected=(
                    "The main window opens without error dialogs.",
                    "Menus open and close normally.",
                    "The search field accepts focus and typed text.",
                ),
            ),
            Checkpoint(
                name="Basic search visible",
                instructions=(
                    "Run a simple search, for example: family where epithet=Guidedaceae.",
                    "Select a visible result if one is returned.",
                ),
                expected=(
                    "Search results render in the result pane or a clear no-results message appears.",
                    "Selecting a result does not produce an error dialog.",
                    "Any visible detail pane behavior is noted.",
                ),
            ),
        ),
    ),
    "taxonomy-create": Scenario(
        name="taxonomy-create",
        description="Exercise family-to-genus-to-species creation visually.",
        checkpoints=(
            Checkpoint(
                name="Family editor opens",
                instructions=(
                    f"Connect to {GUIDED_CONNECTION_NAME} with --sqlite-fixture.",
                    "Open Insert > Family.",
                    "Enter family name: Guidedvisualaceae.",
                ),
                expected=(
                    "The Family Editor opens without an error dialog.",
                    "The family name field accepts text.",
                    "Add Genera and OK controls are visible.",
                ),
            ),
            Checkpoint(
                name="Genus editor opens from family",
                instructions=(
                    "Click Add Genera from the Family Editor.",
                    "Enter genus name: Guidedvisualgenus.",
                ),
                expected=(
                    "The Genus Editor opens without closing unexpectedly.",
                    "The family context is retained.",
                    "Add Species and OK controls are visible.",
                ),
            ),
            Checkpoint(
                name="Species saved",
                instructions=(
                    "Click Add Species from the Genus Editor.",
                    "Enter species epithet: visualspecies.",
                    "Save the species editor.",
                    "Return to the main window.",
                    "Search for: species where genus.epithet=Guidedvisualgenus.",
                ),
                expected=(
                    "The Species Editor saves without an error dialog.",
                    "The editor chain closes or returns to the main window cleanly.",
                    "The search result shows Guidedvisualgenus visualspecies.",
                ),
            ),
        ),
    ),
    "location-create": Scenario(
        name="location-create",
        description="Exercise location creation visually.",
        checkpoints=(
            Checkpoint(
                name="Location editor opens",
                instructions=(
                    f"Connect to {GUIDED_CONNECTION_NAME} with --sqlite-fixture.",
                    "Open Insert > Location.",
                    "Enter location code: GVLOC.",
                    "Enter location name: Guided Visual Bed.",
                ),
                expected=(
                    "The Location Editor opens without an error dialog.",
                    "Code and name fields accept text.",
                    "OK becomes available after required fields are valid.",
                ),
            ),
            Checkpoint(
                name="Location saved",
                instructions=(
                    "Save the Location Editor.",
                    "Search for: location where code=GVLOC.",
                ),
                expected=(
                    "The Location Editor closes cleanly.",
                    "No integrity or traceback dialog appears.",
                    "The saved location can be found or is visible through normal location lookup.",
                ),
            ),
        ),
    ),
    "create-plant": Scenario(
        name="create-plant",
        description="Exercise the accession-to-plant creation workflow visually.",
        checkpoints=(
            Checkpoint(
                name="Plant editor opened from accession",
                instructions=(
                    f"Connect to {GUIDED_CONNECTION_NAME} with --sqlite-fixture.",
                    "Open Insert > Accession.",
                    "Choose species: Guidedgenus guidedspecies.",
                    "Use accession code: GUIDED-ACC-NEW.",
                    "Select Add plants.",
                ),
                expected=(
                    "The Plant Editor opens in normal mode.",
                    "Accession, Planting code, Quantity, and Location fields are visible.",
                    "General, Propagations, Notes, and Pictures tabs are visible.",
                    "Required-field validation enables OK only after valid input.",
                ),
            ),
            Checkpoint(
                name="Plant saved",
                instructions=(
                    "Enter plant code: 2.",
                    "Enter quantity: 1.",
                    "Use location code: GLOC.",
                    "Save the plant and return to the accession editor or main window.",
                ),
                expected=(
                    "No integrity error dialog appears.",
                    "The plant editor closes after OK.",
                    "The saved plant can be found through search or the accession view.",
                ),
            ),
        ),
    ),
    "propagation-workflow": Scenario(
        name="propagation-workflow",
        description="Exercise the plant propagation workflow visually.",
        checkpoints=(
            Checkpoint(
                name="Propagation editor opens",
                instructions=(
                    f"Connect to {GUIDED_CONNECTION_NAME} with --sqlite-fixture.",
                    'Search for: "GUIDED-ACC-001.1".',
                    "Open the Plant Editor for the result.",
                    "Open the Propagations tab and select Add.",
                ),
                expected=(
                    "The Propagation Editor opens.",
                    "Seed is the default propagation type.",
                    "Date and seed-detail fields are visible.",
                    "No traceback appears when Add is selected.",
                ),
            ),
            Checkpoint(
                name="Seed propagation saved",
                instructions=(
                    "Enter propagation date: 2026-05-14.",
                    "Enter number of seeds: 12.",
                    "Enter date sown: 2026-05-14.",
                    "Save the propagation, then save the plant or parent editor.",
                ),
                expected=(
                    "The Propagation Editor closes after OK.",
                    "The propagation appears in the Plant Editor Propagations tab.",
                    "The saved propagation remains visible after reopening the plant.",
                    "No integrity error dialog appears.",
                ),
            ),
        ),
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "scenario",
        nargs="?",
        help="Scenario name to run. Use --list to show available scenarios.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available scenarios and exit.",
    )
    parser.add_argument(
        "--no-launch",
        action="store_true",
        help="Do not launch Ghini; only prompt through the selected checkpoints.",
    )
    parser.add_argument(
        "--auto-close",
        action="store_true",
        help="Close Ghini immediately after the last checkpoint.",
    )
    parser.add_argument(
        "--result-dir",
        default=str(RESULT_DIR),
        help=f"Directory for JSON result artifacts. Default: {RESULT_DIR}",
    )
    parser.add_argument(
        "--sqlite-fixture",
        action="store_true",
        help="Create a disposable SQLite database and launch Ghini with that config.",
    )
    parser.add_argument(
        "--summary",
        nargs="?",
        const="latest",
        metavar="RESULT_JSON",
        help=(
            "Print a readable summary for RESULT_JSON, or the latest guided "
            "result when no path is supplied."
        ),
    )
    return parser.parse_args()


def list_scenarios() -> None:
    for name, scenario in sorted(SCENARIOS.items()):
        print(f"{name}: {scenario.description}")


def prompt_result() -> tuple[str, str]:
    while True:
        result = input("Result [pass/fail/skip]: ").strip().lower()
        if result in {"pass", "fail", "skip"}:
            break
        print("Enter pass, fail, or skip.")
    note = input("Notes or additional observations (optional): ").strip()
    return result, note


def prompt_continue(message: str) -> None:
    input(f"{message} Press Enter to continue.")


def launch_app(env_overrides: dict[str, str] | None = None) -> subprocess.Popen[str]:
    env = os.environ.copy()
    env.setdefault("NO_AT_BRIDGE", "0")
    env.setdefault("PYTHONPATH", "/app")
    if env_overrides:
        env.update(env_overrides)
    return subprocess.Popen(
        APP_COMMAND,
        cwd="/app",
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def create_sqlite_fixture(root: Path) -> dict[str, object]:
    home = root / "home"
    appdata = home / ".bauble" / "3.1"
    default_appdata = Path("/home/ghini/.bauble/3.1")
    database_file = root / "guided.sqlite"
    pictures_root = root / "pictures"
    appdata.mkdir(parents=True)
    pictures_root.mkdir()
    if os.environ.get("GHINI_GUIDED_WRITE_DEFAULT_CONFIG") == "1":
        (default_appdata / "res" / "templates").mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env.update(
        {
            "HOME": str(home),
            "PYTHONPATH": "/app",
            "USER": "ghini",
            "LOGNAME": "ghini",
        }
    )
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
        cwd="/app",
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=120,
        check=False,
    )
    if create_database.returncode != 0:
        raise RuntimeError(
            "Failed to create guided SQLite fixture\n\n"
            f"stdout:\n{create_database.stdout}\n\nstderr:\n{create_database.stderr}"
        )

    seed_database = subprocess.run(
        ["python", "-c", GUIDED_FIXTURE_SEED_SCRIPT, str(database_file)],
        cwd="/app",
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=False,
    )
    if seed_database.returncode != 0:
        raise RuntimeError(
            "Failed to seed guided SQLite fixture\n\n"
            f"stdout:\n{seed_database.stdout}\n\nstderr:\n{seed_database.stderr}"
        )

    write_preferences(
        appdata,
        connection_name=GUIDED_CONNECTION_NAME,
        database_file=database_file,
        pictures_root=pictures_root,
    )
    if os.environ.get("GHINI_GUIDED_WRITE_DEFAULT_CONFIG") == "1":
        write_preferences(
            default_appdata,
            connection_name=GUIDED_CONNECTION_NAME,
            database_file=database_file,
            pictures_root=pictures_root,
        )
    return {
        "connection_name": GUIDED_CONNECTION_NAME,
        "appdata": str(default_appdata),
        "home": str(home),
        "database_file": str(database_file),
        "pictures_root": str(pictures_root),
        **GUIDED_FIXTURE,
        "env": {"HOME": "/home/ghini", "USER": "ghini", "LOGNAME": "ghini"},
    }


def write_preferences(
    appdata_dir: Path, *, connection_name: str, database_file: Path, pictures_root: Path
) -> None:
    appdata_dir.mkdir(parents=True, exist_ok=True)
    config = RawConfigParser()
    config.add_section("bauble.config")
    config.set("bauble.config", "version", "(4, 0)")
    config.add_section("conn")
    config.set(
        "conn",
        "list",
        str(
            {
                connection_name: {
                    "type": "SQLite",
                    "file": str(database_file),
                    "default": False,
                    "pictures": str(pictures_root),
                }
            }
        ),
    )
    config.set("conn", "default", str(connection_name))
    with (appdata_dir / "config").open("w") as config_file:
        config.write(config_file)


def git_value(*args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd="/app",
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception:
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def collect_run_context() -> dict[str, object]:
    return {
        "git_branch": git_value("rev-parse", "--abbrev-ref", "HEAD"),
        "git_commit": git_value("rev-parse", "HEAD"),
        "git_describe": git_value("describe", "--tags", "--dirty", "--always"),
        "display": os.environ.get("DISPLAY", ""),
        "user": os.environ.get("USER", ""),
        "pythonpath": os.environ.get("PYTHONPATH", ""),
    }


def terminate_process(process: subprocess.Popen[str]) -> tuple[str, str]:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.send_signal(signal.SIGKILL)
            process.wait(timeout=5)
    stdout, stderr = process.communicate(timeout=5)
    return stdout, stderr


def run_scenario(
    scenario: Scenario,
    *,
    launch: bool,
    pause_before_close: bool,
    sqlite_fixture: bool,
) -> dict[str, object]:
    started_at = datetime.now(timezone.utc)
    run_context = collect_run_context()
    fixture_context: dict[str, object] = {}
    fixture_tempdir = None
    if sqlite_fixture:
        fixture_tempdir = TemporaryDirectory(prefix="ghini-guided-")
        fixture_context = create_sqlite_fixture(Path(fixture_tempdir.name))
    env_overrides = fixture_context.get("env")
    process = (
        launch_app(env_overrides if isinstance(env_overrides, dict) else None)
        if launch and scenario.launch_app
        else None
    )
    checkpoint_results = []
    print(f"\nScenario: {scenario.name}")
    print(scenario.description)
    print("\nThe application is visible on your display.")
    print("Use this runner for human-visible checkpoints, not every assertion.")
    print("Enter notes for anything surprising, even when the checkpoint passes.")
    print("Confirm only after each checkpoint-level workflow is complete.\n")
    if fixture_context:
        print("Disposable SQLite fixture:")
        print(f"- Connection: {fixture_context['connection_name']}")
        print(f"- Seed search: {fixture_context['seed_search']}")
        print(f"- Plant search: {fixture_context['plant_search']}")
        print(
            "- Seed records: "
            f"{fixture_context['genus_name']} {fixture_context['species_name']}, "
            f"accession {fixture_context['accession_code']}, "
            f"plant {fixture_context['plant_code']}, "
            f"location {fixture_context['location_code']}"
        )
        print()

    try:
        if process is not None:
            prompt_continue("Ghini has been launched.")
        for index, checkpoint in enumerate(scenario.checkpoints, start=1):
            print(f"Checkpoint {index}: {checkpoint.name}")
            if checkpoint.instructions:
                print("Actions:")
                for item in checkpoint.instructions:
                    print(f"- {item}")
            print("Expected:")
            for item in checkpoint.expected:
                print(f"- {item}")
            result, note = prompt_result()
            checkpoint_results.append(
                {
                    "name": checkpoint.name,
                    "result": result,
                    "note": note,
                    "recorded_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            print()
        if process is not None and pause_before_close:
            prompt_continue("Review the visible Ghini window before it closes.")
    finally:
        stdout = stderr = ""
        returncode = None
        if process is not None:
            stdout, stderr = terminate_process(process)
            returncode = process.returncode
        if fixture_tempdir is not None:
            fixture_tempdir.cleanup()

    finished_at = datetime.now(timezone.utc)
    return {
        "scenario": scenario.name,
        "description": scenario.description,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "run_context": run_context,
        "fixture": {k: v for k, v in fixture_context.items() if k != "env"},
        "app_returncode": returncode,
        "checkpoints": checkpoint_results,
        "stdout": stdout,
        "stderr": stderr,
    }


def write_result(result: dict[str, object], result_dir: Path) -> Path:
    result_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = result_dir / f"{timestamp}-{result['scenario']}.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return path


def latest_result_path(result_dir: Path) -> Path | None:
    results = sorted(result_dir.glob("*.json"), key=lambda path: path.stat().st_mtime)
    return results[-1] if results else None


def load_result(path_arg: str, result_dir: Path) -> tuple[Path, dict[str, object]]:
    if path_arg == "latest":
        path = latest_result_path(result_dir)
        if path is None:
            raise FileNotFoundError(f"No guided result artifacts found in {result_dir}")
    else:
        path = Path(path_arg)
    return path, json.loads(path.read_text())


def print_summary(path: Path, result: dict[str, object]) -> None:
    checkpoints = result.get("checkpoints", [])
    if not isinstance(checkpoints, list):
        checkpoints = []

    counts = {"pass": 0, "fail": 0, "skip": 0}
    for checkpoint in checkpoints:
        if not isinstance(checkpoint, dict):
            continue
        status = checkpoint.get("result")
        if status in counts:
            counts[status] += 1

    print(f"Guided result: {path}")
    print(f"Scenario: {result.get('scenario', '')}")
    print(f"Started: {result.get('started_at', '')}")
    print(f"Finished: {result.get('finished_at', '')}")
    print(
        "Checkpoints: "
        f"{counts['pass']} passed, {counts['fail']} failed, {counts['skip']} skipped"
    )

    run_context = result.get("run_context", {})
    if isinstance(run_context, dict):
        branch = run_context.get("git_branch", "")
        commit = run_context.get("git_commit", "")
        describe = run_context.get("git_describe", "")
        print(f"Git: {branch} {commit} {describe}".strip())

    fixture = result.get("fixture", {})
    if isinstance(fixture, dict) and fixture:
        print(f"Fixture: {fixture.get('connection_name', '')}")
        print(f"Seed search: {fixture.get('seed_search', '')}")
        if fixture.get("plant_search"):
            print(f"Plant search: {fixture.get('plant_search')}")

    print()
    for index, checkpoint in enumerate(checkpoints, start=1):
        if not isinstance(checkpoint, dict):
            continue
        result_text = str(checkpoint.get("result", "")).upper()
        name = checkpoint.get("name", "")
        note = checkpoint.get("note", "")
        print(f"{index}. [{result_text}] {name}")
        if note:
            print(f"   Note: {note}")

    if counts["fail"]:
        print()
        print("Create a GitLab issue for each unexpected failure.")
        print(
            "Include the scenario, failed checkpoint, notes, branch/commit, and stderr."
        )


def main() -> int:
    args = parse_args()
    if args.summary:
        path, result = load_result(args.summary, Path(args.result_dir))
        print_summary(path, result)
        checkpoints = result.get("checkpoints", [])
        if not isinstance(checkpoints, list):
            checkpoints = []
        failed = any(
            isinstance(checkpoint, dict) and checkpoint.get("result") == "fail"
            for checkpoint in checkpoints
        )
        return 1 if failed else 0
    if args.list:
        list_scenarios()
        return 0
    if not args.scenario:
        list_scenarios()
        return 2
    scenario = SCENARIOS.get(args.scenario)
    if scenario is None:
        print(f"Unknown scenario: {args.scenario}", file=sys.stderr)
        list_scenarios()
        return 2

    result = run_scenario(
        scenario,
        launch=not args.no_launch,
        pause_before_close=not args.auto_close,
        sqlite_fixture=args.sqlite_fixture,
    )
    path = write_result(result, Path(args.result_dir))
    print(f"Guided GUI result written to {path}")
    failed = any(checkpoint["result"] == "fail" for checkpoint in result["checkpoints"])
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
