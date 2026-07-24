from __future__ import annotations

import pytest

from bauble import _version


def test_version_metadata_rejects_legacy_major() -> None:
    assert not _version._is_supported_version("1.0.82.post645+g5d638fc31")
    assert _version._is_supported_version("4.0.0")


@pytest.mark.parametrize(
    ("describe", "expected"),
    [
        ("v4.0.0-0-g5d638fc3", "4.0.0"),
        ("v4.0.0-3-g5d638fc3", "4.0.0.post3+g5d638fc3"),
        ("5d638fc3", "4.0.0.dev0+g5d638fc3"),
        ("5d638fc3-dirty", "4.0.0.dev0+g5d638fc3.dirty"),
    ],
)
def test_version_from_git_describe(describe: str, expected: str) -> None:
    assert _version._version_from_describe(describe) == expected
