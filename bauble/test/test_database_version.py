from __future__ import annotations

import pytest

from bauble import db


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("3.1.7", (3, 1)),
        ("1.1.5", (1, 1)),
        ("1.0.9", (1, 0)),
        ("4.0.0.post5296+gfa6130fcc", (4, 0)),
        ("4.0.0.post5296+gfa6130fcc.d20260427", (4, 0)),
    ],
)
def test_version_series_accepts_pep440_versions(
    value: str, expected: tuple[int, int]
) -> None:
    assert db.version_series(value) == expected


@pytest.mark.parametrize("value", ["", "unknown", "4"])
def test_version_series_rejects_invalid_versions(value: str) -> None:
    with pytest.raises(ValueError):
        db.version_series(value)


@pytest.mark.parametrize(
    ("database_version", "application_version"),
    [
        # same minor ("schema generation"), different major: compatible
        ("1.1.5", "3.1.9"),
        ("3.1.0", "1.1.20"),
        # identical series
        ("3.1.9", "3.1.9"),
        # hypothetical 3.0.x app line reading a legacy 1.0.x database
        ("1.0.9", "3.0.0"),
    ],
)
def test_database_version_accepts_matching_minor_series(
    database_version: str, application_version: str
) -> None:
    assert db.database_version_is_compatible(database_version, application_version)


@pytest.mark.parametrize(
    ("database_version", "application_version"),
    [
        # same major, different minor: not compatible
        ("1.0.9", "1.1.5"),
        ("1.1.5", "1.0.9"),
        # different major and different minor: not compatible
        ("3.1.7", "4.0.0.post5296+gfa6130fcc"),
    ],
)
def test_database_version_rejects_mismatched_minor_series(
    database_version: str, application_version: str
) -> None:
    assert not db.database_version_is_compatible(database_version, application_version)
