# bauble/plugins/garden/models/verification.py

import logging
from gettext import gettext as _
from typing import TYPE_CHECKING, Any, ClassVar

from bauble.btypes import Date as DbDate
from bauble.db import Base
from sqlalchemy import ForeignKey, Integer, Unicode, UnicodeText, asc
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from bauble.plugins.plants.species_model import Species
    
logger = logging.getLogger(__name__)

ver_level_descriptions: dict[int, str] = {
    0: _("Not checked by any authority"),
    1: _("Determined by comparison with other named plants"),
    2: _("Determined by a taxonomist"),
    3: _("Systematic revision"),
    4: _("Type gathering or propagated from type material"),
}


class Verification(Base):
    """
    :Table name: verification

    :Columns:
      verifier: :class:`sqlalchemy.types.Unicode`
        The name of the person that made the verification.
      date: :class:`sqlalchemy.DbDate`
        The date of the verification
      reference: :class:`sqlalchemy.types.UnicodeText`
        The reference material used to make this verification
      level: :class:`sqlalchemy.types.Integer`
        Determines the level or authority of the verifier. If it is
        not known whether the name of the record has been verified by
        an authority, then this field should be None.

        Possible values:
            - 0: The name of the record has not been checked by any authority.
            - 1: The name of the record determined by comparison with
              other named plants.
            - 2: The name of the record determined by a taxonomist or by
              other competent persons using herbarium and/or library and/or
              documented living material.
            - 3: The name of the plant determined by taxonomist engaged in
              systematic revision of the group.
            - 4: The record is part of type gathering or propagated from
              type material by asexual methods

      notes: :class:`sqlalchemy.types.UnicodeText`
        Notes about this verification.
      accession_id: :class:`sqlalchemy.types.Integer`
        Foreign Key to the :class:`Accession` table.
      species_id: :class:`sqlalchemy.types.Integer`
        Foreign Key to the :class:`~bauble.plugins.plants.Species` table.
      prev_species_id: :class:`~sqlalchemy.types.Integer`
        Foreign key to the :class:`~bauble.plugins.plants.Species`
        table. What it was verified from.

    """

    __tablename__: str = "verification"

    # columns
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    verifier: Mapped[str] = mapped_column(Unicode(64), nullable=False)
    date: Mapped[DbDate] = mapped_column(DbDate, nullable=False)
    reference: Mapped[str] = mapped_column(UnicodeText)
    accession_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("accession.id"), nullable=False
    )

    order_by: ClassVar[list[Any]] = [asc(date)]

    # the level of assurance of this verification
    level: Mapped[int] = mapped_column(Integer, nullable=False, autoincrement=False)

    # what it was verified as
    species_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("species.id"), nullable=False
    )

    # what it was verified from
    prev_species_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("species.id"), nullable=False
    )

    # Relationships
    species: Mapped["Species"] = relationship(
        "Species",
        primaryjoin="Verification.species_id == Species.id",
        foreign_keys=[species_id],
        uselist=False,
        overlaps="previous_verifications",
        active_history=True,
    )
    prev_species: Mapped["Species"] = relationship(
        "Species",
        primaryjoin="Verification.prev_species_id == Species.id",
        foreign_keys=[prev_species_id],
        uselist=False,
        overlaps="verifications",
        active_history=True,
    )
    notes: Mapped[str] = mapped_column(UnicodeText)
