# PostgreSQL Release Smoke

Use this procedure before tagging a release candidate when the application must
be checked against representative PostgreSQL data. The source database should
be copied into a disposable local PostgreSQL container first. Do not run schema
reset tests or write tests against a production garden database.

## Preconditions

- `scripts/docker-dev build` has completed.
- The source PostgreSQL database is reachable from the Docker development
  container.
- The source URI uses a read-only database role when possible.
- `GHINI_SOURCE_POSTGRES_URI` points at the source database to copy.

Example:

```sh
export GHINI_SOURCE_POSTGRES_URI='postgresql://readonly_user:secret@postgres.example.net/ghini'
```

## Create The Dump

Create an ignored dump artifact under `test-results/`:

```sh
scripts/docker-dev run -- bash -lc '
  set -euo pipefail
  mkdir -p /app/test-results/postgres-smoke
  pg_dump \
    --format=custom \
    --no-owner \
    --no-acl \
    --file=/app/test-results/postgres-smoke/representative.dump \
    "$GHINI_SOURCE_POSTGRES_URI"
'
```

## Restore Into A Disposable Container

Start a local PostgreSQL container for the restored copy:

```sh
docker run --detach --rm \
  --name ghini-postgres-release-smoke \
  --env POSTGRES_USER=ghini \
  --env POSTGRES_PASSWORD=ghini \
  --env POSTGRES_DB=ghini_copy \
  postgres:16-alpine
```

Wait for it to accept connections:

```sh
until docker exec ghini-postgres-release-smoke \
  pg_isready -U ghini -d ghini_copy >/dev/null 2>&1
do
  sleep 1
done
```

Restore the dump into the disposable database:

```sh
GHINI_DOCKER_NETWORK=container:ghini-postgres-release-smoke \
  scripts/docker-dev run -- \
  pg_restore \
    --dbname=postgresql://ghini:ghini@127.0.0.1:5432/ghini_copy \
    --no-owner \
    --role=ghini \
    /app/test-results/postgres-smoke/representative.dump
```

## Run The Read-Only Smoke

Run the external PostgreSQL smoke lane against the restored copy:

```sh
GHINI_DOCKER_NETWORK=container:ghini-postgres-release-smoke \
GHINI_EXTERNAL_POSTGRES_URI=postgresql://ghini:ghini@127.0.0.1:5432/ghini_copy \
  scripts/docker-dev postgres-smoke
```

The smoke lane does not recreate the schema. It verifies required tables, basic
counts, the daily accession/taxonomy join, and session rollback recovery.

## Cleanup

Remove the disposable database container:

```sh
docker stop ghini-postgres-release-smoke
```

The dump file is ignored by git under `test-results/`. Remove it when it is no
longer needed:

```sh
rm -f test-results/postgres-smoke/representative.dump
```
