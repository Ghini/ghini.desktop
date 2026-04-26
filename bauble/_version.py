"""Version helpers for Ghini Desktop.

Package builds and editable installs get their version from Git through
setuptools-scm. This module intentionally is not generated at build time, so
normal development commands do not rewrite tracked source files.
"""

from __future__ import annotations

import re
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from pathlib import Path

__all__ = [
    "__version__",
    "__version_tuple__",
    "version",
    "version_tuple",
    "__commit_id__",
    "commit_id",
]

_PACKAGE_NAME = "ghini-desktop"
_FALLBACK_VERSION = "4.0.0+unknown"


def _version_from_metadata() -> str | None:
    try:
        return package_version(_PACKAGE_NAME)
    except PackageNotFoundError:
        return None


def _version_from_git() -> str | None:
    try:
        from setuptools_scm import get_version
    except ImportError:
        return None

    try:
        return get_version(
            root=str(Path(__file__).resolve().parents[1]),
            version_scheme="post-release",
            local_scheme="node-and-date",
        )
    except Exception:
        return None


def _parse_version_tuple(value: str) -> tuple[int | str, ...]:
    return tuple(int(part) if part.isdigit() else part for part in value.split("."))


version = __version__ = (
    _version_from_metadata() or _version_from_git() or _FALLBACK_VERSION
)
version_tuple = __version_tuple__ = _parse_version_tuple(version)

_commit_match = re.search(r"\+g([0-9a-f]+)(?:\.|$)", version)
commit_id = __commit_id__ = _commit_match.group(1) if _commit_match else None
