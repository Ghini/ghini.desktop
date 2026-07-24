"""Unit tests for the pure string-handling helpers in bauble._version.

These tests cover _is_supported_version() and _version_from_describe():
given a version string or a `git describe` output, do they parse and
format it correctly. They run against hand-written input strings, not
against a real git repository.

What this file does NOT cover:
- _version_from_git()'s actual call into setuptools_scm.get_version().
- The tag_regex / fallback_version configuration in pyproject.toml and
  setup.py, which is what setuptools_scm uses at real build time and
  where a mismatch between the two (or with bauble/_version.py) will
  not be caught here.
- Anything that requires a real tagged commit and an actual build
  (sdist/wheel/`pip install .`) to reproduce.

A test that exercised the real bug this project hit once - a stale
major-version tag_regex in pyproject.toml disagreeing with _version.py -
would need to create a scratch git repo with a real tag and call
setuptools_scm.get_version() against the real project config, not just
these helpers in isolation.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from bauble import _version
_BASE = _version._BASE_VERSION


def test_version_metadata_rejects_legacy_major() -> None:
    assert not _version._is_supported_version("1.0.82.post645+g5d638fc31")
    assert _version._is_supported_version(_BASE)


@pytest.mark.parametrize(
    ("describe", "expected"),
    [
        (f"v{_BASE}-0-g5d638fc3", _BASE),
        (f"v{_BASE}-3-g5d638fc3", f"{_BASE}.post3+g5d638fc3"),
        ("5d638fc3", f"{_BASE}.dev0+g5d638fc3"),
        ("5d638fc3-dirty", f"{_BASE}.dev0+g5d638fc3.dirty"),
    ],
)
def test_version_from_git_describe(describe: str, expected: str) -> None:
    assert _version._version_from_describe(describe) == expected
