#
# Copyright (c) 2018 Mario Frasca <mario@anche.no>
#
# This file is part of ghini.desktop.
#
# ghini.desktop is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ghini.desktop is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ghini.desktop. If not, see <http://www.gnu.org/licenses/>.
#
import glob
import logging
import os
import re
from typing import List, Pattern

import pytest
from babel.messages.pofile import read_po

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@pytest.fixture  # type: ignore[misc]
def po_files() -> List[str]:
    """
    Fixture to locate all .po files in the 'po' directory.
    """
    pattern = __file__.split(os.path.sep)[:-3]
    po_dir = os.path.sep.join(pattern)
    files = glob.glob(os.path.join(po_dir, "po", "*.po"))
    return files


@pytest.fixture  # type: ignore[misc]
def translation_pattern() -> Pattern[str]:
    """
    Fixture to compile the translation key pattern.
    """
    return re.compile(r"%\([a-z0-9_]*\)s")


def test_same_keys(po_files: List[str], translation_pattern: Pattern[str]) -> None:
    """
    Test that keys in the original message and translations match for all .po files.
    """
    for filename in po_files:
        with open(filename, encoding="utf-8") as po_file:
            catalog = read_po(po_file)
            for msg in catalog:
                if not msg.id or not msg.string:
                    # Skip non-translation or untranslated entries
                    continue
                incoming = set(translation_pattern.findall(msg.id))
                translated = set(translation_pattern.findall(msg.string))
                assert incoming == translated, (
                    f"Mismatch in {filename}: "
                    f"original keys {incoming} do not match translated keys {translated}"
                )
