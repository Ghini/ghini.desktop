# Docker Development

Ghini Desktop can be run and developed from a Docker image based on
Ubuntu 24.04. This is the recommended Linux workflow when the host
distribution does not provide compatible GTK, GI, PostgreSQL, Kerberos, and
Python dependency versions.

## Requirements

- Docker with Buildx support.
- An X11 desktop session on the host for GUI runs.
- A PostgreSQL database connection if you are not using SQLite.
- Optional Kerberos files if your PostgreSQL environment requires Kerberos.

## Local Configuration

Copy the example environment file and edit it for your machine:

```sh
cp .env.example .env
```

The committed `.env.example` contains placeholders. The local `.env` file is
ignored by Git because it may contain database hostnames, database names,
Kerberos paths, and other machine-specific settings.

For password-based PostgreSQL authentication, set `DB_PASSWORD` in `.env`.
`scripts/docker-dev` passes it through to the container but it should remain
local and uncommitted.

`scripts/docker-dev` also passes a `TZ` value into the container so default
dates in the GUI follow the user-visible host date rather than UTC. It uses
`GHINI_TZ` when set, then `TZ`, then the host `/etc/timezone` or
`/etc/localtime`, and falls back to `UTC` only when no host timezone can be
detected. Set `GHINI_TZ=America/New_York` or another IANA timezone in `.env` to
override detection.

Date-only user fields, such as propagation dates and accession-code date
tokens, use the process local calendar date. Automatic audit timestamps, such as
`_created`, `_last_updated`, and history rows, use UTC internally so SQLite and
PostgreSQL runs do not depend on the desktop timezone.

## Build

```sh
scripts/docker-dev build
```

The build creates the `ghini-desktop-dev:latest` image by default. Override the
image name with `GHINI_IMAGE` in `.env` or in the shell.

The development image installs Python packages from committed lock files in
`requirements/`. This keeps rebuilds deterministic for a given Git commit.

`Dockerfile.dev` and `scripts/docker-dev` are the supported development
workflow. The root `Dockerfile` is older experimental packaging work and should
not be used as the source of truth for local development, testing, or merge
request validation.

## Branch Workflow

Use `ghini-4-dev-clean` as the current integration branch for the Python,
SQLAlchemy, GTK 3.24, Docker, and developer tooling work. Keep feature and fix
branches small, then merge or cherry-pick them back to `ghini-4-dev-clean` once
their focused tests and warning-gated suite pass.

The `search` branch is preserved as a fallback branch. Do not use it as the
integration base for new work.

The `search-clean-history` branch is a tracking branch for the old `search`
work. Its commit subjects use state markers:

- `[D]`: the intent is already ported to `ghini-4-dev-clean`.
- `[P]`: the intent is partially ported and should remain on the migration
  checklist.
- `[T]`: the intent is still todo.

When additional old work is ported, update `search-clean-history` so the
corresponding commit body records the `ghini-4-dev-clean` commit hash with
`(ported: ...)` or `(partial: ...)`.

## Updating Python Dependencies

Edit the dependency declarations in `pyproject.toml`, then regenerate the Docker
lock files:

```sh
scripts/docker-dev lock
```

Review and commit the `pyproject.toml` and `requirements/*.lock` changes
together. The lock set includes bootstrap packaging tools, runtime packages,
and development/test packages. Rebuild the image after changing the locks:

```sh
scripts/docker-dev build
```

## Legacy Dependency Notes

Some older runtime packages are still intentionally present:

- `fibra` drives Ghini's cooperative task runner in `bauble.task`.
- `PyQRCode` is used by the Mako report templates for QR label rendering.
- `raven` is used by the optional legacy Sentry logging integration.

`gdata-python3` is referenced by older installer metadata but is not imported
by the application runtime and is not installed in the Docker development
environment.

## Run The Application

```sh
scripts/docker-dev app
```

The runner mounts the source checkout at `/app`, uses `/home/ghini/.bauble/3.1`
inside the container for Ghini configuration, and passes through X11 display
settings. The application runs from the mounted source tree, so code edits on
the host are visible to the container immediately.

## Shell

```sh
scripts/docker-dev shell
```

Use this for ad hoc investigation inside the same dependency environment as the
application.

## Pytest

Run the default pytest command:

```sh
scripts/docker-dev pytest
```

Override pytest arguments for one run:

```sh
PYTEST_ARGS='bauble/test_querybuilderparser.py -q' scripts/docker-dev pytest
```

Shell environment values take precedence over `.env`, which makes one-off test
runs possible without editing local configuration.

## Warning-Gated Tests

Run the full test suite with migration-related warnings promoted to errors:

```sh
scripts/docker-dev warnings
```

This command currently treats Python deprecations, PyGObject/GTK deprecations,
and SQLAlchemy deprecations as failures. Use it before pushing migration work
or opening a merge request, especially when changing database, GTK, or shared
test infrastructure.

You can still pass extra pytest arguments through `PYTEST_ARGS` or positional
arguments. For example:

```sh
PYTEST_ARGS='bauble/test/test_search.py -q' scripts/docker-dev warnings
scripts/docker-dev warnings bauble/plugins/garden/test.py -q
```

## GTK Test Layers

Run the headless GTK smoke suite:

```sh
scripts/docker-dev gtk-smoke
```

This suite loads real Glade widgets and instantiates editor views and
presenters under Xvfb. It is fast enough for regular development and catches
many GTK, validation, and presenter wiring regressions, but it does not drive
the application as a black-box user.

Run the GUI end-to-end suite:

```sh
scripts/docker-dev gui-e2e
```

This suite launches the real application under Xvfb, enables AT-SPI, and uses
dogtail accessibility APIs to inspect and interact with windows, dialogs, and
controls. It is intentionally separate from `gtk-smoke` because it is slower,
depends on accessibility names and roles, and is more sensitive to windowing
behavior.

Run the opt-in PostgreSQL regression lane:

```sh
scripts/docker-dev postgres-check
```

This command starts a disposable PostgreSQL container, runs a focused backend
regression inside the Ghini development container, and removes the PostgreSQL
container afterward. It is intended as a release or migration gate, not as the
default fast development loop. The test database is disposable: `db.create()`
drops and recreates the Ghini schema before importing defaults.

Override the PostgreSQL lane image or credentials when needed:

```sh
GHINI_POSTGRES_IMAGE=postgres:16-alpine scripts/docker-dev postgres-check
GHINI_POSTGRES_PASSWORD=secret scripts/docker-dev postgres-check
```

You can also point the PostgreSQL lane at an already available disposable
database by running the test directly and setting `GHINI_TEST_POSTGRES_URI`:

```sh
GHINI_TEST_POSTGRES_URI=postgresql://ghini:ghini@postgres/ghini_test \
  scripts/docker-dev run -- python -m pytest bauble/test/test_postgresql_lane.py -q
```

Do not point `GHINI_TEST_POSTGRES_URI` at a real garden database. The lane owns
the target schema and recreates it.

Run the external PostgreSQL smoke lane against a disposable representative
database copy:

```sh
GHINI_EXTERNAL_POSTGRES_URI=postgresql://ghini:secret@postgres.example.net/ghini_copy \
  scripts/docker-dev postgres-smoke
```

This lane does not call `db.create()` and does not recreate the target schema.
It opens the database the same way the application does, tolerates the version
warning path used for older Ghini databases, and performs read-only checks for
required tables, basic counts, a daily accession/taxonomy join, and session
rollback recovery. Use this for release confidence against a representative
PostgreSQL copy. Do not use a production database for release testing.

For the release-candidate procedure that copies a representative database into
a disposable local PostgreSQL container first, see
[`doc/postgresql-release-smoke.md`](postgresql-release-smoke.md).
The one-command release path is:

```sh
GHINI_SOURCE_POSTGRES_URI=postgresql://readonly_user:secret@postgres.example.net/ghini \
  scripts/docker-dev postgres-copy-smoke
```

## Formatting And Checks

Format changed Python files with Black:

```sh
scripts/docker-dev format
```

Check changed Python files without rewriting them:

```sh
scripts/docker-dev check
```

Both commands default to Python files changed relative to `HEAD`, including
untracked files. Pass explicit paths to format or check a specific file set:

```sh
scripts/docker-dev format bauble/_version.py setup.py
scripts/docker-dev check bauble/_version.py tests/test_version.py setup.py
```

`check` also runs the lightweight version and database-version tests. It is
intentionally narrower than the full legacy test suite, so use
`scripts/docker-dev pytest` when you need broader application coverage.

These commands use `GHINI_TOOL_CONTAINER`, defaulting to a short-lived
`ghini-dev-check-<pid>` name, so they can run while the main
`GHINI_CONTAINER` application container is still open.

## Common Development Loop

For normal development, use this sequence:

```sh
scripts/docker-dev build
scripts/docker-dev app
scripts/docker-dev format
scripts/docker-dev check
scripts/docker-dev pytest
scripts/docker-dev warnings
```

`format` and `check` are quick changed-file checks. `pytest` gives full
behavioral coverage. `warnings` repeats the full suite with deprecation
warnings promoted to errors, which is the final gate for dependency migration
work.

## SQLAlchemy Migration Policy

The migration target is SQLAlchemy 2.x. Current development should use
SQLAlchemy 2 style APIs and keep legacy deprecations out of new code:

- Prefer `select(...)`, `session.execute(...)`, `scalars()`, `mappings()`, and
  `session.get(...)` over legacy `Query` APIs.
- Wrap textual SQL in `sqlalchemy.text(...)`.
- Preserve the legacy database schema unless a change is intentional and
  documented. In particular, typed ORM annotations must not accidentally turn
  legacy nullable columns into `NOT NULL` columns.
- Keep relationship ownership explicit. Use `delete-orphan` only where the
  parent truly owns the child row, and add focused tests for scalar/list and
  cascade behavior.
- Run `scripts/docker-dev warnings` before pushing SQLAlchemy migration work.

When auditing model changes, compare the intended schema against the upstream
3.1 development baseline and fix only accidental schema changes. Existing user
databases must remain connectable during the migration.

## GTK Policy

Ghini Desktop stays on GTK 3.24. Do not migrate the application to GTK 4.

Compatibility helpers may be written in a way that does not make a future GTK 4
migration harder, but GTK 4 should not drive current design decisions, Glade UI
changes, or dependency choices. Use Ubuntu 24.04's GTK 3, PyGObject, and GI
typelib packages from the Docker image as the reference runtime.

## Private Hostnames

Docker does not automatically inherit host-only `/etc/hosts` aliases. By
default, `scripts/docker-dev` resolves configured database hosts on the host and
passes matching `--add-host` entries to Docker. This covers `DB_HOST` and the
hosts in `GHINI_TEST_POSTGRES_URI`, `GHINI_EXTERNAL_POSTGRES_URI`, and
`GHINI_SOURCE_POSTGRES_URI` when they resolve to an IPv4 address on the host.

Disable this behavior when you want Docker DNS or a custom Docker network to
handle all names:

```sh
GHINI_DOCKER_AUTO_ADD_HOSTS=0
```

For extra aliases, add explicit local-only host mappings to `.env`:

```sh
GHINI_DOCKER_ADD_HOSTS=postgres.example.net:192.0.2.10,postgres:192.0.2.10
```

Each comma-separated value is passed to Docker as `--add-host`. Explicit
mappings remain useful when a saved Ghini connection uses a short alias, such as
`postgres`, while `.env` uses a fully qualified name.

## Debugging

Start Ghini under debugpy:

```sh
scripts/docker-dev debug
```

Start pytest under debugpy:

```sh
scripts/docker-dev pytest-debug
```

Both modes listen on `localhost:5678`. VS Code launch configurations are
provided in `.vscode/launch.json`.

## VS Code

Open this repository in VS Code and use the Docker tasks:

- `Docker: Build Dev Image`
- `Docker: Run Ghini`
- `Docker: Debug Ghini`
- `Docker: Run Pytest`
- `Docker: Run Warning-Gated Pytest`
- `Docker: Debug Pytest`
- `Docker: Format Changed Python`
- `Docker: Check Changed Python`
- `Docker: Shell`

The debug configurations attach to debugpy in the container and map the local
workspace to `/app`.

## VS Code Dev Containers

The repository also includes `.devcontainer/devcontainer.json`. With the VS Code
Dev Containers extension installed:

1. Open the repository in VS Code.
2. Run `Dev Containers: Reopen in Container`.
3. Let VS Code build the `Dockerfile.dev` image.

The Dev Container setup creates `.env` from `.env.example` when `.env` does not
exist. Edit `.env` on the host for your database, display, and Kerberos
settings before launching Ghini.

The container uses `/opt/venv/ghini/bin/python` as the Python interpreter and
keeps the repository mounted at `/app`.

## Notes

- The development image uses apt-provided PyGObject (`python3-gi`) and GI
  typelibs rather than building PyGObject from pip. This keeps the Python GTK
  bindings aligned with Ubuntu's introspection libraries.
- The image pins the OS baseline to Ubuntu 24.04.
- The Python dependency versions are declared in `pyproject.toml` and locked
  for Docker builds in `requirements/`.
- Black is installed in the development image and is available through
  `scripts/docker-dev format` and `scripts/docker-dev check`.
- `scripts/docker-dev` forwards the host timezone as `TZ` so date defaults in
  the GUI match the desktop local date. Override this with `GHINI_TZ` in
  `.env` when needed.
- `scripts/docker-dev` grants X11 access with
  `xhost +SI:localuser:$(id -un)` by default. Set `GHINI_XHOST=0` to disable
  that step if your host display access is configured another way.
