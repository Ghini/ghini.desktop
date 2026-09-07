#!/usr/bin/env python
"""Freeze ghini.desktop into a standalone Windows executable.

Produces a self-contained ``dist/`` folder (``ghini.exe`` plus all the
Python and C-extension files it needs) that can run on a Windows machine
with no Python installation of its own. This is the input the NSIS
installer script packages into ``setup.exe``.

Requirements to run this script:
  - Windows, Python 3.13, py2exe >= 0.14
  - GTK3 + PyGObject already importable (e.g. built with gvsbuild)
  - ghini.desktop itself already installed (``pip install -e .``)

This is a first draft: package/include lists below are a starting guess,
not a verified-complete list. Expect to add entries here once we see what
modulefinder misses (missing-module warnings show up in the CI log; DLL
lookup failures only show up when someone actually runs ghini.exe).
"""
import sys

if sys.platform != "win32":
    sys.exit("freeze_win.py must be run on Windows")

# py2exe's modulefinder scans the filesystem statically; it can't follow the
# import hooks that a modern (PEP 660) `pip install -e .` sets up, so it fails
# to find "bauble" even though it imports fine in a normal interpreter.
# Sidestep that entirely by putting the repo root - where the bauble/ package
# lives as a plain directory - on sys.path ourselves.
sys.path.insert(0, ".")

from py2exe import freeze

freeze(
    version_info={
        # Overwrite with the real value from setuptools-scm during CI,
        # once this script is wired into the workflow for real.
        "version": "3.1.0",
        "description": "Ghini: a biodiversity collection manager",
        "product_name": "ghini.desktop",
        "company_name": "",
    },
    windows=[
        {
            "script": "scripts/ghini",
            "dest_base": "ghini",
            "icon_resources": [(0, "bauble/images/icon.ico")],
        }
    ],
    options={
        # bundle_files < 3 (single-file / zipped-extensions modes) is not
        # supported from Python 3.12 onward - this also happens to match
        # what the NSIS installer already expects: a plain folder under
        # dist/, not a single exe.
        "bundle_files": 3,
        "compressed": True,
        "packages": ["bauble", "gi"],
        "includes": [
            "cairo",
            "psycopg2",
            "sqlalchemy",
            # imported internally, at the compiled-C level:
            "lxml._elementpath",
        ],
        # GI typelibs and GTK's own data files (icons, schemas, pixbuf
        # loaders) are not picked up by modulefinder at all - they need to
        # be copied into dist/ separately, the way the old win_gtk.bat did
        # for GTK2. That copy step still needs to be written; leaving it
        # out for this first draft on purpose so we can see cleanly whether
        # freeze() itself succeeds before layering more complexity on top.
    },
)
