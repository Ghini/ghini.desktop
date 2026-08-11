#
# Copyright 2008-2010 Brett Adams
# Copyright 2015-2016 Mario Frasca <mario@anche.no>.
# Copyright 2017 Jardín Botánico de Quito
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
# bauble/plugins/garden/models/source.py


from gettext import gettext as _
from typing import TYPE_CHECKING, Optional

import bauble.btypes as types
from bauble import utils as utils
from bauble.db import Base
from sqlalchemy import Float, ForeignKey, Integer, Unicode, UnicodeText
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    # these are only for type‐hints; the real classes live in their modules
    from bauble.plugins.plants.geography import GeographicArea

    from .contact import Contact
    from .propagation import Propagation


class Source(Base):
    """connected 1-1 to Accession.

    Source objects have the function to add fields to one Accession.  From
    an Accession, to access the fields added here you obviously still need
    to go through its `.source` member.

    Create an Accession a, then create a Source s, then assign a.source = s

    """

    __tablename__ = "source"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # ITF2 - E7 - Donor's Accession Identifier - donacc
    sources_code: Mapped[Optional[str]] = mapped_column(Unicode(32))

    # 1-to-1 back to Accession
    accession_id: Mapped[int] = mapped_column(ForeignKey("accession.id"), unique=True)

    # @classmethod
    # def init(cls) -> None:
    #    from .propagation import Propagation

    # who donated it
    source_detail_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("contact.id"), nullable=True
    )
    source_detail: Mapped[Optional["Contact"]] = relationship(
        "Contact",
        uselist=False,
        back_populates="sources",
        active_history=True,
    )

    # optional collection metadata
    collection: Mapped["Collection"] = relationship(
        "Collection",
        uselist=False,
        back_populates="source",
        single_parent=True,
        active_history=True,
    )

    # This propagation relationship links a Source to a specific
    # Propagation that is not tied to a Plant. It likely represents
    # a propagation trial or source-related propagation activity
    # independent of the plant hierarchy.
    # propagation metadata
    propagation_id: Mapped[Optional[int]] = mapped_column(ForeignKey("propagation.id"))
    propagation: Mapped["Propagation"] = relationship(
        "Propagation",
        uselist=False,
        back_populates="source",
        cascade="all, delete-orphan",
        single_parent=True,
        foreign_keys=[propagation_id],
        active_history=True,
    )

    # an Accession of known Source (what we are describing here) may be in
    # relation to a successful Plant Propagation trial. In this case, the
    # Propagation points back to all Accessions that resulted from it, via
    # `used_source[i].accession`. Arguably not practical.
    # link back to a single Plant-Propagation trial
    plant_propagation_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("propagation.id")
    )
    plant_propagation: Mapped["Propagation"] = relationship(
        "Propagation",
        primaryjoin="Source.plant_propagation_id==Propagation.id",
        back_populates="used_source",
        uselist=False,
        foreign_keys=[plant_propagation_id],
    )


class Collection(Base):
    """
    :Table name: collection

    :Columns:
            *collector*: :class:`sqlalchemy.types.Unicode`

            *collectors_code*: :class:`sqlalchemy.types.Unicode`

            *date*: :class:`sqlalchemy.types.Date`

            *locale*: :class:`sqlalchemy.types.UnicodeText`

            *latitude*: :class:`sqlalchemy.types.Float`

            *longitude*: :class:`sqlalchemy.types.Float`

            *gps_datum*: :class:`sqlalchemy.types.Unicode`

            *geo_accy*: :class:`sqlalchemy.types.Float`

            *elevation*: :class:`sqlalchemy.types.Float`

            *elevation_accy*: :class:`sqlalchemy.types.Float`

            *habitat*: :class:`sqlalchemy.types.UnicodeText`

            *geographic_area_id*: :class:`sqlalchemy.types.Integer`

            *notes*: :class:`sqlalchemy.types.UnicodeText`

            *accession_id*: :class:`sqlalchemy.types.Integer`


    :Properties:


    :Constraints:
    """

    __tablename__ = "collection"

    # columns
    id: Mapped[int] = mapped_column(primary_key=True)
    # ITF2 - F24 - Primary Collector's Name
    collector: Mapped[Optional[str]] = mapped_column(Unicode(64), nullable=True)
    # ITF2 - F.25 - Collector's Identifier
    collectors_code: Mapped[Optional[str]] = mapped_column(Unicode(50), nullable=True)
    # ITF2 - F.27 - Collection Date
    date: Mapped[Optional[types.Date]] = mapped_column(types.Date, nullable=True)
    locale: Mapped[str] = mapped_column(UnicodeText, nullable=False)
    # ITF2 - F1, F2, F3, F4 - Latitude, Degrees, Minutes, Seconds, Direction
    latitude: Mapped[Optional[str]] = mapped_column(Unicode(15), nullable=True)
    # ITF2 - F5, F6, F7, F8 - Longitude, Degrees, Minutes, Seconds, Direction
    longitude: Mapped[Optional[str]] = mapped_column(Unicode(15), nullable=True)
    gps_datum: Mapped[Optional[str]] = mapped_column(Unicode(32), nullable=True)
    # ITF2 - F9 - Accuracy of Geographical Referencing Data
    geo_accy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # ITF2 - F17 - Altitude
    elevation: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # ITF2 - F18 - Accuracy of Altitude
    elevation_accy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # ITF2 - F22 - Habitat
    habitat: Mapped[Optional[str]] = mapped_column(UnicodeText, nullable=True)
    # ITF2 - F18 - Collection Notes
    notes: Mapped[Optional[str]] = mapped_column(UnicodeText, nullable=True)

    geographic_area_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("geographic_area.id"), nullable=True
    )
    region: Mapped[Optional["GeographicArea"]] = relationship(
        "GeographicArea", uselist=False, active_history=True
    )

    source_id: Mapped[int] = mapped_column(ForeignKey("source.id"), unique=True)
    source: Mapped["Source"] = relationship("Source", back_populates="collection")

    def search_view_markup_pair(self):
        """provide the two lines describing object for SearchView row."""
        acc = self.source.accession
        safe = utils.xml_safe
        return (
            f"{safe(acc)} - <small>{safe(acc.species_str())}</small>",
            safe(self),
        )

    def __str__(self) -> str:
        return _("Collection at %s") % (self.locale or repr(self))
