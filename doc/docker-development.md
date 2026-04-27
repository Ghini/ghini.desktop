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

## Build

```sh
scripts/docker-dev build
```

The build creates the `ghini-desktop-dev:latest` image by default. Override the
image name with `GHINI_IMAGE` in `.env` or in the shell.

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

## Private Hostnames

Docker does not automatically inherit host-only `/etc/hosts` aliases. If your
database hostname resolves on the host but not inside the container, add a
local-only host mapping to `.env`:

```sh
GHINI_DOCKER_ADD_HOSTS=postgres.example.net:192.0.2.10,postgres:192.0.2.10
```

Each comma-separated value is passed to Docker as `--add-host`.

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

- The development image uses apt-provided PyGObject and GI typelibs rather
  than building PyGObject from pip.
- The image pins the OS baseline to Ubuntu 24.04.
- The Python dependency versions are declared in `pyproject.toml`.
- Black is installed in the development image and is available through
  `scripts/docker-dev format` and `scripts/docker-dev check`.
- `scripts/docker-dev` grants X11 access with
  `xhost +SI:localuser:$(id -un)` by default. Set `GHINI_XHOST=0` to disable
  that step if your host display access is configured another way.
