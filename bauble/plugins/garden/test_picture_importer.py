#
# Copyright 2018 Mario Frasca <mario@anche.no>.
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
import pytest

from bauble import prefs
from bauble.plugins.garden.picture_importer import decode_parts

# Set testing mode
prefs.testing = True


@pytest.mark.usefixtures("db_session")
class TestDecodeParts:
    """
    Test cases for the decode_parts function in picture_importer.
    """

    def test_decode_parts_complete(self) -> None:
        assert decode_parts("2018.0020.1 (4) Epidendrum.jpg") == {
            "accession": "2018.0020",
            "plant": "1",
            "seq": "4",
            "species": "Epidendrum",
        }
        assert decode_parts("Masdevallia-2018.0020-2.jpg") == {
            "accession": "2018.0020",
            "plant": "1",
            "seq": "2",
            "species": "Masdevallia",
        }
        assert decode_parts("2007.0001 Annona muricata.jpg") == {
            "accession": "2007.0001",
            "plant": "1",
            "seq": "1",
            "species": "Annona muricata",
        }

    def test_decode_parts_none(self) -> None:
        assert decode_parts("20x18.0020.1 (4).jpg") is None

    def test_decode_parts_optional(self) -> None:
        assert decode_parts("2018.0020 (4) Dracula.jpg") == {
            "accession": "2018.0020",
            "plant": "1",
            "seq": "4",
            "species": "Dracula",
        }
        assert decode_parts("2018.0020.2 (4).jpg") == {
            "accession": "2018.0020",
            "plant": "2",
            "seq": "4",
            "species": "Zzz",
        }
        assert decode_parts("2018.0020 (4).jpg") == {
            "accession": "2018.0020",
            "plant": "1",
            "seq": "4",
            "species": "Zzz",
        }

    def test_decode_parts_seq_from_original(self) -> None:
        assert decode_parts("DSCN0123-2018.0020.JPG") == {
            "accession": "2018.0020",
            "plant": "1",
            "seq": "123",
            "species": "Zzz",
        }
        assert decode_parts("P1220810-2018.0020.JPG") == {
            "accession": "2018.0020",
            "plant": "1",
            "seq": "1220810",
            "species": "Zzz",
        }
        assert decode_parts("2018.0020 Vanda-P1220810.JPG") == {
            "accession": "2018.0020",
            "plant": "1",
            "seq": "1220810",
            "species": "Vanda",
        }

    def test_decode_parts_custom_accession_format(self) -> None:
        assert decode_parts("2007.01.321 Annona muricata.jpg", "####.##.###") == {
            "accession": "2007.01.321",
            "plant": "1",
            "seq": "1",
            "species": "Annona muricata",
        }
        assert decode_parts("2007.01.321.2 Annona sp.jpg", "####.##.###") == {
            "accession": "2007.01.321",
            "plant": "2",
            "seq": "1",
            "species": "Annona sp",
        }
        assert decode_parts("2009.01.21.2 Opuntia ficus-indica.jpg", "####.##.##") == {
            "accession": "2009.01.21",
            "plant": "2",
            "seq": "1",
            "species": "Opuntia ficus-indica",
        }

    def test_decode_parts_only_scan_name(self) -> None:
        assert decode_parts("Location/2018.0020.1 (4) Epidendrum.jpg") == {
            "accession": "2018.0020",
            "plant": "1",
            "seq": "4",
            "species": "Epidendrum",
        }
        assert decode_parts("Pictures/Masdevallia-2018.0020-2.jpg") == {
            "accession": "2018.0020",
            "plant": "1",
            "seq": "2",
            "species": "Masdevallia",
        }
