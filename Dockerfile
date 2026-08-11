# syntax=docker/dockerfile:1.4
#
# Release image for ghini.desktop. Bakes in the application and its runtime
# dependencies at a pinned version; only configuration and the SQLite
# database file are expected to live on the host.
#
#  Build: docker buildx build --load \
#           --build-arg USER_ID=$(id -u) --build-arg GROUP_ID=$(id -g) \
#           --build-arg GHINI_VERSION=3.1.<patch> \
#           -t ghini-desktop:3.1.<patch> .
#
#  Run:   docker run --rm -it \
#           -e DISPLAY=$DISPLAY \
#           -v /tmp/.X11-unix:/tmp/.X11-unix \
#           -v $HOME/.bauble/3.1:/home/ghini/.bauble/3.1 \
#           ghini-desktop:3.1.<patch>
#
# GHINI_MODE controls the entrypoint: "app" (default) launches Ghini,
# "shell" drops into bash for troubleshooting.
#
# GHINI_VERSION is derived from the release tag (see setuptools_scm in
# pyproject.toml), not fixed by this Dockerfile — 3.1.<patch> reflects the
# current "ghini-3.1" release line and will need updating if that changes.

ARG GHINI_VERSION=0.0.0+unknown

########################################
# Stage 1: Build Stage
# — resolve deps, build the wheel, assemble the runtime venv
########################################
FROM ubuntu:24.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Some of Ghini's GTK 3 map dependencies live outside Ubuntu main.
RUN sed -i 's/Components: main$/Components: main universe/' /etc/apt/sources.list.d/ubuntu.sources || true

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    gettext \
    pkg-config \
    python3 \
    python3-dev \
    python3-pip \
    python3-venv \
    libjpeg-dev \
    libpq-dev \
    libxslt1-dev \
    zlib1g-dev \
    libcairo2-dev \
    libffi-dev \
    libgirepository1.0-dev \
    libkrb5-dev \
    && rm -rf /var/lib/apt/lists/*
    # Dropped from the old file's build stage: git (no longer clones a repo —
    # GHINI_VERSION is passed in explicitly, see below); libpython3-dev
    # (superseded by python3-dev); libcairo2 (pulled in automatically as a
    # dependency of libcairo2-dev); the four gir1.2-* map packages and
    # krb5-user (nothing in this stage imports gi or runs krb5 tools — they
    # only matter at runtime, see the runtime stage below).
    #
    # New here: ca-certificates (pip/apt need it to verify HTTPS during the
    # build); python3-pip (mirrors Dockerfile.dev — ensures pip is available
    # even where python3-venv's bundled ensurepip isn't); libffi-dev (needed
    # to build C extensions that link against libffi, pulled in transitively
    # by some of base.lock's dependencies).

# --- Throwaway venv used only to build the wheel (setuptools-scm, wheel, etc.
#     from bootstrap.lock). This venv is discarded; it never reaches runtime. ---
RUN python3 -m venv /opt/build-venv
ENV PATH="/opt/build-venv/bin:${PATH}"

COPY requirements/bootstrap.lock /tmp/ghini-build/bootstrap.lock
RUN python -m pip install --no-cache-dir -r /tmp/ghini-build/bootstrap.lock

WORKDIR /src
COPY . /src

# Version is pinned explicitly rather than derived from git history, so the
# build doesn't depend on tags being present in the CI checkout.
ARG GHINI_VERSION
ENV SETUPTOOLS_SCM_PRETEND_VERSION=${GHINI_VERSION}
RUN python -m pip wheel --no-cache-dir --no-deps --no-build-isolation -w /dist /src

# --- The venv that actually ships. Only base.lock (runtime deps) + the wheel
#     go in here — no build tooling, no debugpy, nothing from bootstrap.lock. ---
ENV VIRTUAL_ENV=/opt/venv/ghini
RUN python3 -m venv --system-site-packages "${VIRTUAL_ENV}"
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

COPY requirements/base.lock /tmp/ghini-build/base.lock
RUN python -m pip install --no-cache-dir -r /tmp/ghini-build/base.lock \
    && python -m pip install --no-cache-dir --no-deps /dist/*.whl

########################################
# Stage 2: Runtime Stage
# — only what's needed to run Ghini
########################################
FROM ubuntu:24.04 AS runtime

ARG USER_ID=1000
ARG GROUP_ID=1000
ARG GHINI_VERSION=0.0.0+unknown

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV VIRTUAL_ENV=/opt/venv/ghini
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"
ENV HOME=/home/ghini
ENV USER=ghini
ENV LOGNAME=ghini
ENV NO_AT_BRIDGE=1
ENV GHINI_MODE=app
ENV GHINI_VERSION=${GHINI_VERSION}
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN sed -i 's/Components: main$/Components: main universe/' /etc/apt/sources.list.d/ubuntu.sources || true

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    libpq5 \
    libcairo2 \
    gir1.2-gtk-3.0 \
    gir1.2-gtkclutter-1.0 \
    gir1.2-champlain-0.12 \
    gir1.2-gtkchamplain-0.12 \
    python3-gi \
    python3-cairo \
    krb5-user \
    adwaita-icon-theme \
    at-spi2-core \
    ca-certificates \
    dbus-x11 \
    gdk-pixbuf2.0-bin \
    gir1.2-gdkpixbuf-2.0 \
    gir1.2-pango-1.0 \
    hicolor-icon-theme \
    libcanberra-gtk3-module \
    librsvg2-common \
    shared-mime-info \
    xauth \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*
    # Dropped from the old file's runtime stage: libpython3.9, libjpeg62-turbo,
    # libxslt1.1, zlib1g, libgirepository-1.0-1, libkrb5-3 (all pulled in
    # automatically as transitive dependencies of the packages above — no
    # need to name them explicitly, and doing so pins them to a Ubuntu point
    # release unnecessarily); postgresql-client (its CLI tools — pg_dump,
    # psql — aren't used by the app itself, only by dev/test tooling; libpq5
    # alone is enough for psycopg2 to work).
    #
    # python3-gi / python3-cairo replace the old file's `pip install
    # PyGObject` — using apt's prebuilt system bindings instead, per
    # Dockerfile.dev's proven approach.
    #
    # Everything from adwaita-icon-theme down has no equivalent in the old
    # file: icon themes, dbus/accessibility integration, and X11 auth that a
    # real desktop session needs but a bare root shell never exercised.

# WFO omits this intermediate certificate from its TLS chain, and Ghini talks
# to WFO during normal operation — keep verification enabled by installing the
# public intermediate certificate in the runtime trust store.
COPY docker/certs/network-solutions-rsa-ov-ssl-ca-3.crt \
    /usr/local/share/ca-certificates/network-solutions-rsa-ov-ssl-ca-3.crt
RUN update-ca-certificates

RUN existing_group="$(getent group "${GROUP_ID}" | cut -d: -f1 || true)" \
    && if [[ -z "${existing_group}" ]]; then \
        groupadd --gid "${GROUP_ID}" ghini; \
    elif [[ "${existing_group}" != "ghini" ]] && ! getent group ghini >/dev/null; then \
        groupmod --new-name ghini "${existing_group}"; \
    fi \
    && existing_user="$(getent passwd "${USER_ID}" | cut -d: -f1 || true)" \
    && if [[ -z "${existing_user}" ]]; then \
        useradd --uid "${USER_ID}" --gid "${GROUP_ID}" --create-home --shell /bin/bash ghini; \
    elif [[ "${existing_user}" != "ghini" ]] && ! id ghini >/dev/null 2>&1; then \
        usermod --login ghini --home /home/ghini --move-home --shell /bin/bash "${existing_user}"; \
        usermod --gid "${GROUP_ID}" ghini; \
    fi \
    && mkdir -p "${HOME}" \
    && chown -R "${USER_ID}:${GROUP_ID}" "${HOME}"

# Runtime venv (app + base.lock deps only) built in the previous stage.
COPY --from=builder --chown=ghini:ghini "${VIRTUAL_ENV}" "${VIRTUAL_ENV}"

# The launcher isn't part of the installed package (see note above the
# Dockerfile) so it's baked in explicitly, alongside the app.
COPY --chown=ghini:ghini scripts/ghini /opt/ghini/scripts/ghini

RUN cat > /usr/local/bin/ghini-entrypoint <<'EOS' \
    && chmod +x /usr/local/bin/ghini-entrypoint
#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "__ghini_mode__" ]]; then
    shift
elif [[ "$#" -gt 0 ]]; then
    exec "$@"
fi

case "${GHINI_MODE:-app}" in
    app)
        exec python /opt/ghini/scripts/ghini "$@"
        ;;
    shell)
        exec bash "$@"
        ;;
    *)
        exec "$@"
        ;;
esac
EOS

USER ghini
WORKDIR /home/ghini

ENTRYPOINT ["/usr/local/bin/ghini-entrypoint"]
CMD ["__ghini_mode__"]