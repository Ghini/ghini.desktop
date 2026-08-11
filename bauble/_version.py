"""Version helpers for Ghini Desktop.

Package builds and editable installs get their version from Git through
setuptools-scm. This module intentionally is not generated at build time, so
normal development commands do not rewrite tracked source files.
"""

from __future__ import annotations

import re
import subprocess
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
_BASE_VERSION = "3.1.9" #:bump
_FALLBACK_VERSION = f"{_BASE_VERSION}+unknown"
_SUPPORTED_MAJOR = 3
_VERSION_TAG_PATTERN = "v3.*"


def _is_supported_version(value: str) -> bool:
    match = re.match(r"^(\d+)\.", value)
    return bool(match and int(match.group(1)) >= _SUPPORTED_MAJOR)


def _version_from_metadata() -> str | None:
    try:
        metadata_version = package_version(_PACKAGE_NAME)
    except PackageNotFoundError:
        return None

    if _is_supported_version(metadata_version):
        return metadata_version
    return None


def _git_output(root: Path, *args: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(root), *args],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        return None


def _version_from_describe(describe: str) -> str | None:
    dirty = describe.endswith("-dirty")
    clean_describe = describe.removesuffix("-dirty")
    dirty_suffix = ".dirty" if dirty else ""

    tagged = re.match(
        r"^v(?P<tag>" + str(_SUPPORTED_MAJOR) + r"\.\d+\.\d+)-(?P<count>\d+)-g(?P<node>[0-9a-f]+)$",
        clean_describe,
    )
    if tagged:
        tag = tagged.group("tag")
        count = int(tagged.group("count"))
        node = tagged.group("node")
        if count == 0 and not dirty:
            return tag
        return f"{tag}.post{count}+g{node}{dirty_suffix}"

    if re.match(r"^[0-9a-f]+$", clean_describe):
        return f"{_BASE_VERSION}.dev0+g{clean_describe}{dirty_suffix}"

    return None


def _version_from_git() -> str | None:
    root = Path(__file__).resolve().parents[1]
    try:
        from setuptools_scm import get_version
    except ImportError:
        pass
    else:
        try:
            return str(get_version(
                root=str(root),
                version_scheme="post-release",
                local_scheme="node-and-date",
                tag_regex=r"^v(?P<version>" + str(_SUPPORTED_MAJOR) + r"(?:\.\d+){2})$",
                scm={
                    "git": {
                        "describe_command": (
                            "git describe --dirty --tags --long --match v" + str(_SUPPORTED_MAJOR) + ".*"
                        )
                    }
                },
                fallback_version=_BASE_VERSION,
            ))
        except Exception:
            pass

    describe = _git_output(
        root,
        "describe",
        "--tags",
        "--match",
        _VERSION_TAG_PATTERN,
        "--long",
        "--dirty",
        "--always",
    )
    if describe:
        parsed = _version_from_describe(describe)
        if parsed:
            return parsed

    return None


def _parse_version_tuple(value: str) -> tuple[int | str, ...]:
    return tuple(int(part) if part.isdigit() else part for part in value.split("."))


version = __version__ = (
    _version_from_metadata() or _version_from_git() or _FALLBACK_VERSION
)
version_tuple = __version_tuple__ = _parse_version_tuple(version)

_commit_match = re.search(r"\+g([0-9a-f]+)(?:\.|$)", version)
commit_id = __commit_id__ = (
    _commit_match.group(1)
    if _commit_match
    else _git_output(
        Path(__file__).resolve().parents[1],
        "rev-parse",
        "--short",
        "HEAD",
    )
)
