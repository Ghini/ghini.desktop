#
# Copyright 2008-2010 Brett Adams
# Copyright 2015-2017 Mario Frasca <mario@anche.no>.
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
# propagation module
#
import datetime
import logging
from gettext import gettext as _
from typing import TYPE_CHECKING, Any, ClassVar, List, Optional

import bauble.btypes as types
import bauble.prefs as prefs
import bauble.utils as utils
from bauble.db import Base, WithNotes, make_note_class
from bauble.plugins.garden.constants import (
    bottom_heat_unit_values as bottom_heat_unit_values,
)
from bauble.plugins.garden.constants import (
    cutting_type_values,
    flower_buds_values,
    leaves_values,
    length_unit_values,
    prop_type_values,
    tip_values,
    wound_values,
)

if TYPE_CHECKING:
    from bauble.plugins.garden.source import Source

from bauble.utils import sorted_relationship
from sqlalchemy import ForeignKey, Integer, UnicodeText, asc, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.orm.session import object_session

# from sqlalchemy import text

# right after the imports of constants, define a safe default
DEFAULT_PROP_TYPE = (
    "Unknown" if "Unknown" in prop_type_values else next(iter(prop_type_values.keys()))
)

logger: Any = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Propagation(Base, WithNotes):
    """
    Propagation
    """

    __tablename__: str = "propagation"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prop_type: Mapped[str] = mapped_column(
        types.Enum(
            values=list(prop_type_values.keys()),
            translations=prop_type_values,
            omit_aliases=False,
        ),
        nullable=False,
        default=DEFAULT_PROP_TYPE,  # <-- ORM default
        server_default=text(f"'{DEFAULT_PROP_TYPE}'"),  # <-- DB default
    )
    date: Mapped[Optional[datetime.date]] = mapped_column(types.Date)
    order_by: ClassVar[list[Any]] = [asc(date)]

    _cutting: Mapped[Optional["PropCutting"]] = relationship(
        "PropCutting",
        primaryjoin="Propagation.id == PropCutting.propagation_id",
        cascade="all, delete-orphan",
        uselist=False,
        single_parent=True,
        back_populates="propagation",
        active_history=True,
    )
    _seed: Mapped[Optional["PropSeed"]] = relationship(
        "PropSeed",
        primaryjoin="Propagation.id == PropSeed.propagation_id",
        cascade="all, delete-orphan",
        uselist=False,
        single_parent=True,
        back_populates="propagation",
        active_history=True,
    )

    # One-to-one relationship with Source for propagation
    source: Mapped[Optional["Source"]] = relationship(
        "Source",
        uselist=False,
        back_populates="propagation",
        cascade="all, delete-orphan",
        foreign_keys="Source.propagation_id",
        active_history=True,
    )

    # One-to-many relationship with Source for plant_propagation
    used_source: Mapped[List["Source"]] = relationship(
        "Source",
        back_populates="plant_propagation",
        foreign_keys="Source.plant_propagation_id",
    )

    @property
    def accessions(self):
        if not self.used_source:
            return []
        accessions = []
        session = object_session(self.used_source[0].accession)
        for us in self.used_source:
            if us.accession not in session.new:
                accessions.append(us.accession)
        return sorted_relationship(accessions, key=lambda x: x.code)

    @property
    def accessible_quantity(self):
        """the resulting product minus the already accessed material

        return 1 if the propagation is not completely specified.

        """
        quantity = None
        incomplete = True
        if self.prop_type == "UnrootedCutting":
            incomplete = self._cutting is None  # cutting without fields
            if not incomplete:
                quantity = sum([item.quantity for item in self._cutting.rooted])
        elif self.prop_type == "Seed":
            incomplete = self._seed is None  # seed without fields
            if not incomplete:
                quantity = self._seed.nseedlings
        if incomplete:
            return 1  # let user grab one at a time, in any case
        if quantity is None:
            quantity = 0
        removethis = sum((a.quantity_recvd or 0) for a in self.accessions)
        return max(quantity - removethis, 0)

    def get_summary(self, partial: bool = False):
        """compute a textual summary for this propagation

        a full description contains all fields, in `key:value;` format, plus
        a prefix telling us whether the resulting material of the
        propagation was added as accessed in the collection.

        partial==1 means we only want to get the list of resulting
        accessions.

        partial==2 means we do not want the list of resulting accessions.

        """
        date_format = prefs.prefs[prefs.date_format_pref]

        def get_date(date):
            if isinstance(date, datetime.date):
                return date.strftime(date_format)
            return date

        values = []
        accession_codes = []

        if self.used_source and partial != 2:
            values = [_("used in") + f": {acc.code}" for acc in self.accessions]
            accession_codes = [acc.code for acc in self.accessions]

        if partial == 1:
            return ";".join(accession_codes)

        if self.prop_type == "UnrootedCutting" and self._cutting is not None:
            c = self._cutting
            values.append(_("Cutting"))
            if c.cutting_type is not None:
                values.append(
                    _("Cutting type") + f": {cutting_type_values[c.cutting_type]}"
                )
            if c.length:
                values.append(
                    _("Length: %(length)s%(unit)s")
                    % dict(length=c.length, unit=length_unit_values[c.length_unit])
                )
            if c.tip:
                values.append(_("Tip") + f": {tip_values[c.tip]}")
            if c.leaves:
                s = _("Leaves") + f": {leaves_values[c.leaves]}"
                if c.leaves == "Removed" and c.leaves_reduced_pct:
                    s += f" ({c.leaves_reduced_pct}%)"
                values.append(s)
            if c.flower_buds:
                values.append(
                    _("Flower buds") + f": {flower_buds_values[c.flower_buds]}"
                )
            if c.wound is not None:
                values.append(_("Wounded") + f": {wound_values[c.wound]}")
            if c.fungicide:
                values.append(_("Fungal soak") + f": {c.fungicide}")
            if c.hormone:
                values.append(_("Hormone treatment") + f": {c.hormone}")
            if c.bottom_heat_temp:
                values.append(
                    _("Bottom heat: %(temp)s%(unit)s")
                    % dict(
                        temp=c.bottom_heat_temp,
                        unit=bottom_heat_unit_values[c.bottom_heat_unit],
                    )
                )
            if c.container:
                values.append(_("Container") + f": {c.container}")
            if c.media:
                values.append(_("Media") + f": {c.media}")
            if c.location:
                values.append(_("Location") + f": {c.location}")
            if c.cover:
                values.append(_("Cover") + f": {c.cover}")

            if c.rooted_pct:
                values.append(_("Rooted: %s%%") % c.rooted_pct)

            if c.rooted:
                values.append(_("Rooted: %s") % sum(i.quantity for i in c.rooted))
        elif self.prop_type == "Seed" and self._seed is not None:
            seed = self._seed
            values.append(_("Seed"))
            if seed.pretreatment:
                values.append(_("Pretreatment") + f": {seed.pretreatment}")
            if seed.nseeds:
                values.append(_("# of seeds") + f": {seed.nseeds}")
            date_sown = get_date(seed.date_sown)
            if date_sown:
                values.append(_("Date sown") + f": {date_sown}")
            if seed.container:
                values.append(_("Container") + f": {seed.container}")
            if seed.media:
                values.append(_("Media") + f": {seed.media}")
            if seed.covered:
                values.append(_("Covered") + f": {seed.covered}")
            if seed.location:
                values.append(_("Location") + f": {seed.location}")
            germ_date = get_date(seed.germ_date)
            if germ_date:
                values.append(_("Germination date") + f": {germ_date}")
            if seed.nseedlings:
                values.append(_("# of seedlings") + f": {seed.nseedlings}")
            if seed.germ_pct:
                values.append(_("Germination rate") + f": {seed.germ_pct}%")
            date_planted = get_date(seed.date_planted)
            if date_planted:
                values.append(_("Date planted") + f": {date_planted}")
        else:
            # Unknown / not yet specified: show something benign
            label = prop_type_values.get(self.prop_type, _("Propagation"))
            values.append(str(label))

        s = "; ".join(values)

        return s

    def clean(self) -> None:
        if self.prop_type == "UnrootedCutting":
            if self._seed is not None:
                utils.delete_or_expunge(self._seed)
            self._seed = None
            if not self._cutting.bottom_heat_temp:
                self._cutting.bottom_heat_unit = None
            if not self._cutting.length:
                self._cutting.length_unit = None
        elif self.prop_type == "Seed":
            if self._cutting is not None:
                utils.delete_or_expunge(self._cutting)
            self._cutting = None
            if self._seed is not None and self._seed.is_empty():
                utils.delete_or_expunge(self._seed)
                self._seed = None


PropagationNote: Any = make_note_class("Propagation", Propagation)
Propagation.notes = relationship(
    "PropagationNote",
    back_populates="propagation",
    cascade="all,delete-orphan",
    single_parent=True,
)


class PropCuttingRooted(Base):
    """
    Rooting dates for cutting
    """

    __tablename__: str = "prop_cutting_rooted"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[types.Date] = mapped_column(types.Date)
    quantity: Mapped[int] = mapped_column(
        Integer, autoincrement=False, default=0, nullable=False
    )
    cutting_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("prop_cutting.id"), nullable=False
    )
    order_by: ClassVar[list[Any]] = [asc(date)]

    # Add the missing relationship
    cutting: Mapped["PropCutting"] = relationship(
        "PropCutting", back_populates="rooted"
    )


class PropCutting(Base):
    """
    A cutting
    """

    wound: Any
    flower_buds: Any
    bottom_heat_temp: Any
    bottom_heat_unit: Any
    __tablename__: str = "prop_cutting"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cutting_type: Mapped[Optional[str]] = mapped_column(
        types.Enum(
            values=list(cutting_type_values.keys()),
            translations=cutting_type_values,
            omit_aliases=False,
        ),
        default="Other",
        nullable=True,
    )
    tip: Mapped[Optional[str]] = mapped_column(
        types.Enum(
            values=list(tip_values.keys()), translations=tip_values, omit_aliases=False
        ),
        nullable=True,
    )
    leaves: Mapped[Optional[str]] = mapped_column(
        types.Enum(
            values=list(leaves_values.keys()),
            translations=leaves_values,
            omit_aliases=False,
        ),
        nullable=True,
    )
    leaves_reduced_pct: Mapped[Optional[int]] = mapped_column(
        Integer, autoincrement=False, nullable=True
    )
    length: Mapped[Optional[int]] = mapped_column(
        Integer, autoincrement=False, nullable=True
    )
    length_unit: Mapped[Optional[str]] = mapped_column(
        types.Enum(
            values=list(length_unit_values.keys()),
            translations=length_unit_values,
            omit_aliases=False,
        ),
        nullable=True,
    )

    # single/double/slice
    wound: Mapped[Optional[str]] = mapped_column(
        types.Enum(
            values=list(wound_values.keys()),
            translations=wound_values,
            omit_aliases=False,
        ),
        nullable=True,
    )

    # removed/None
    flower_buds: Mapped[Optional[str]] = mapped_column(
        types.Enum(
            values=list(flower_buds_values.keys()),
            translations=flower_buds_values,
            omit_aliases=False,
        ),
        nullable=True,
    )

    fungicide: Mapped[Optional[str]] = mapped_column(
        UnicodeText, nullable=True
    )  # fungal soak
    hormone: Mapped[Optional[str]] = mapped_column(
        UnicodeText, nullable=True
    )  # powder/liquid/None....solution

    media: Mapped[Optional[str]] = mapped_column(UnicodeText, nullable=True)
    container: Mapped[Optional[str]] = mapped_column(UnicodeText, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(UnicodeText, nullable=True)
    cover: Mapped[Optional[str]] = mapped_column(
        UnicodeText, nullable=True
    )  # vispore, poly, plastic dome, poly bag

    # temperature of bottom heat
    bottom_heat_temp: Mapped[Optional[int]] = mapped_column(
        Integer, autoincrement=False, nullable=True
    )

    # TODO: make the bottom heat unit required if bottom_heat_temp is
    # not null

    # F/C
    bottom_heat_unit: Mapped[Optional[str]] = mapped_column(
        types.Enum(
            values=list(bottom_heat_unit_values.keys()),
            translations=bottom_heat_unit_values,
            omit_aliases=False,
        ),
        nullable=True,
    )
    rooted_pct: Mapped[Optional[int]] = mapped_column(
        Integer, autoincrement=False, nullable=True
    )

    propagation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("propagation.id"), nullable=False
    )

    rooted: Mapped[list["PropCuttingRooted"]] = relationship(
        "PropCuttingRooted",
        cascade="all, delete-orphan",
        primaryjoin="PropCutting.id == PropCuttingRooted.cutting_id",
        back_populates="cutting",
    )

    propagation: Mapped["Propagation"] = relationship(
        "Propagation", back_populates="_cutting", uselist=False, active_history=True
    )


class PropSeed(Base):
    """ """

    covered: Any
    location: Any
    moved_from: Any
    __tablename__: str = "prop_seed"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pretreatment: Mapped[Optional[str]] = mapped_column(UnicodeText, nullable=True)
    nseeds: Mapped[int] = mapped_column(Integer, nullable=False, autoincrement=False)
    date_sown: Mapped[types.Date] = mapped_column(types.Date, nullable=False)
    container: Mapped[Optional[str]] = mapped_column(
        UnicodeText, nullable=True
    )  # 4" pot plug tray, other
    media: Mapped[Optional[str]] = mapped_column(
        UnicodeText, nullable=True
    )  # seedling media, sphagnum, other

    # covered with #2 granite grit: no, yes, lightly heavily
    covered: Mapped[Optional[str]] = mapped_column(UnicodeText, nullable=True)

    # not same as location table, glasshouse(bottom heat, no bottom
    # heat), polyhouse, polyshade house, fridge in polybag
    location: Mapped[Optional[str]] = mapped_column(UnicodeText, nullable=True)

    # TODO: do we need multiple moved to->moved from and date fields
    moved_from: Mapped[Optional[str]] = mapped_column(UnicodeText, nullable=True)
    moved_to: Mapped[Optional[str]] = mapped_column(UnicodeText, nullable=True)
    moved_date: Mapped[Optional[types.Date]] = mapped_column(types.Date, nullable=True)

    germ_date: Mapped[Optional[types.Date]] = mapped_column(types.Date, nullable=True)

    nseedlings: Mapped[Optional[int]] = mapped_column(
        Integer, autoincrement=False, nullable=True
    )  # number of seedling
    germ_pct: Mapped[Optional[int]] = mapped_column(
        Integer, autoincrement=False, nullable=True
    )  # % of germination
    date_planted: Mapped[Optional[types.Date]] = mapped_column(
        types.Date, nullable=True
    )

    propagation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("propagation.id"), nullable=False
    )

    propagation: Mapped["Propagation"] = relationship(
        "Propagation", back_populates="_seed", uselist=False, active_history=True
    )

    def is_empty(self) -> bool:
        """Return True when no seed detail fields have been filled in."""
        return all(
            getattr(self, field) in (None, "")
            for field in (
                "pretreatment",
                "nseeds",
                "date_sown",
                "container",
                "media",
                "covered",
                "location",
                "moved_from",
                "moved_to",
                "moved_date",
                "germ_date",
                "nseedlings",
                "germ_pct",
                "date_planted",
            )
        )

    def __str__(self) -> str:
        # what would the string be...???
        # cuttings of self.accession.species_str() and accession number
        return repr(self)
