# bauble/plugins/garden/models/accession.py
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
# accessions module
#
import datetime
import logging
from decimal import ROUND_DOWN, Decimal
from functools import reduce
from gettext import gettext as _
from typing import TYPE_CHECKING, Any, ClassVar, Optional

import bauble.btypes as types
from bauble.btypes import Date as DbDate
from bauble.db import Base, Serializable, Session, WithNotes, make_note_class
from bauble.plugins.plants.genus import Genus
from bauble.plugins.plants.species_model import Species
from bauble.utils import check, safe_int, xml_safe
from sqlalchemy import Boolean, ForeignKey, Integer, Unicode, asc, event, select
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    object_session,
    reconstructor,
    relationship,
    validates,
)

if TYPE_CHECKING:
    from .location import Location  # adjust path if needed

# ─── lookup tables ───────────────────────────────────────

# ITF2 - E.1; Provenance Type Flag; Transfer code: prot
prov_type_values: ClassVar[list[tuple[Optional[str], str]]] = [
    ("Wild", _("Accession of wild source")),
    ("Cultivated", _("Propagule(s) from a wild source plant")),
    ("NotWild", _("Accession not of wild source")),
    ("Purchase", _("Purchase or gift")),
    ("InsufficientData", _("Insufficient Data")),
    ("Unknown", _("Unknown")),
    (None, ""),
]

# ITF2 - E.3; Wild Provenance Status Flag; Transfer code: wpst
#  - further specifies the W and Z prov type flag
#
# according to the ITF2, the keys should literally be one of: 'Wild native',
# 'Wild non-native', 'Cultivated native', 'Cultivated non-native'.  In
# practice the standard just requires we note whether a wild (a cultivated
# propagule Z or the one directly collected W) plant is native or not to the
# place where it was found. a boolean should suffice, exporting will expand
# to and importing will collapse from the standard value. Giving all four
# options after the user has already selected W or Z works only confusing to
# user not familiar with ITF2 standard.
wild_prov_status_values: ClassVar[list[tuple[str, str]]] = [
    # Endemic found within indigenous range
    ("WildNative", _("Wild native")),
    # found outside indigenous range
    ("WildNonNative", _("Wild non-native")),
    # Endemic, cultivated, reintroduced or translocated within its
    # indigenous range
    ("CultivatedNative", _("Cultivated native")),
    # MISSING cultivated, found outside its indigenous range
    # (u'CultivatedNonNative', _("Cultivated non-native"))
    # TO REMOVE:
    ("Impound", _("Impound")),
    ("Collection", _("Collection")),
    ("Rescue", _("Rescue")),
    ("InsufficientData", _("Insufficient Data")),
    ("Unknown", _("Unknown")),
    # Not transferred
    (None, ""),
]

# not ITF2
# - further specifies the Z prov type flag value
cultivated_prov_status_values: ClassVar[list[tuple[str, str]]] = [
    ("InVitro", _("In vitro")),
    ("Division", _("Division")),
    ("Seed", _("Seed")),
    ("Unknown", _("Unknown")),
    (None, ""),
]

# not ITF2
# - further specifies the G prov type flag value
purchase_prov_status_values: ClassVar[list[tuple[str, str]]] = [
    ("National", _("National")),
    ("Imported", _("Imported")),
    ("Unknown", _("Unknown")),
    (None, ""),
]

# not ITF2
recvd_type_values: ClassVar[dict[Optional[str], str]] = {
    "ALAY": _("Air layer"),
    "BBPL": _("Balled & burlapped plant"),
    "BRPL": _("Bare root plant"),
    "BUDC": _("Bud cutting"),
    "BUDD": _("Budded"),
    "BULB": _("Bulb"),
    "CLUM": _("Clump"),
    "CORM": _("Corm"),
    "DIVI": _("Division"),
    "GRAF": _("Graft"),
    "LAYE": _("Layer"),
    "PLNT": _("Planting"),
    "PSBU": _("Pseudobulb"),
    "RCUT": _("Rooted cutting"),
    "RHIZ": _("Rhizome"),
    "ROOC": _("Root cutting"),
    "ROOT": _("Root"),
    "SCIO": _("Scion"),
    "SEDL": _("Seedling"),
    "SEED": _("Seed"),
    "SPOR": _("Spore"),
    "SPRL": _("Sporeling"),
    "TUBE": _("Tuber"),
    "UNKN": _("Unknown"),
    "URCU": _("Unrooted cutting"),
    "BBIL": _("Bulbil"),
    "VEGS": _("Vegetative spreading"),
    "SCKR": _("Root sucker"),
    None: "",
}

accession_type_to_plant_material: ClassVar[dict[Optional[str], str]] = {
    # u'Plant': _('Planting'),
    "BBPL": "Plant",
    "BRPL": "Plant",
    "PLNT": "Plant",
    "SEDL": "Plant",
    # u'Seed': _('Seed/Spore'),
    "SEED": "Seed",
    "SPOR": "Seed",
    "SPRL": "Seed",
    # u'Vegetative': _('Vegetative Part'),
    "BUDC": "Vegetative",
    "BUDD": "Vegetative",
    "BULB": "Vegetative",
    "CLUM": "Vegetative",
    "CORM": "Vegetative",
    "DIVI": "Vegetative",
    "GRAF": "Vegetative",
    "LAYE": "Vegetative",
    "PSBU": "Vegetative",
    "RCUT": "Vegetative",
    "RHIZ": "Vegetative",
    "ROOC": "Vegetative",
    "ROOT": "Vegetative",
    "SCIO": "Vegetative",
    "TUBE": "Vegetative",
    "URCU": "Vegetative",
    "BBIL": "Vegetative",
    "VEGS": "Vegetative",
    "SCKR": "Vegetative",
    # u'Tissue': _('Tissue Culture'),
    "ALAY": "Tissue",
    # u'Other': _('Other'),
    "UNKN": "Other",
    None: None,
}

logger = logging.getLogger(__name__)


# ─── helper functions ────────────────────────────────────
def get_species_instance(
    session, epithet, genus_epithet: Optional[Any] = None, create: bool = False
):
    """
    Retrieves a Species instance based on epithet and optional genus epithet.
    Returns a Species instance or None.
    """
    # Strip zero-width spaces and whitespace
    ep = (epithet or "").replace("\u200b", "").strip()
    ge = (genus_epithet or "").replace("\u200b", "").strip() or None

    keys = {"epithet": ep}
    if ge:
        keys["ht-epithet"] = ge

    # SAFE lookup: no flush
    sp = Species.retrieve(session, keys)
    if sp is not None or not create:
        return sp
    
    return Species.retrieve_or_create(session=session, keys=keys, create=create)

def longitude_to_dms(decimal):
    return decimal_to_dms(Decimal(decimal), "long")


def latitude_to_dms(decimal):
    return decimal_to_dms(Decimal(decimal), "lat")


def decimal_to_dms(decimal, long_or_lat):
    """
    :param decimal: the value to convert
    :param long_or_lat: should be either "long" or "lat"

    @returns dir, degrees, minutes seconds, seconds rounded to two
    decimal places
    """
    if long_or_lat == "long":
        check(abs(decimal) <= 180)
    else:
        check(abs(decimal) <= 90)
    dir_map = {"long": ["E", "W"], "lat": ["N", "S"]}
    direction = dir_map[long_or_lat][0]
    if decimal < 0:
        direction = dir_map[long_or_lat][1]
    dec = Decimal(str(abs(decimal)))
    d = Decimal(str(dec)).to_integral(rounding=ROUND_DOWN)
    m = Decimal(abs((dec - d) * 60)).to_integral(rounding=ROUND_DOWN)
    m2 = Decimal(abs((dec - d) * 60))
    places = 2
    q = Decimal((0, (1,), -places))
    s = Decimal(abs((m2 - m) * 60)).quantize(q)
    return direction, d, m, s


def dms_to_decimal(dir, deg, min, sec, precision: int = 6):
    """
    convert degrees, minutes, seconds to decimal
    return a decimal.Decimal
    """
    nplaces = Decimal(10) ** -precision
    if dir in ("E", "W"):  # longitude
        check(abs(deg) <= 180)
    else:
        check(abs(deg) <= 90)
    check(abs(min) < 60)
    check(abs(sec) < 60)
    deg = Decimal(str(abs(deg)))
    min = Decimal(str(min))
    sec = Decimal(str(sec))
    dec = abs(sec / Decimal("3600")) + abs(min / Decimal("60.0")) + deg
    if dir in ("W", "S"):
        dec = -dec
    return dec.quantize(nplaces)


def compute_accession_note_serializable_fields(cls, session, keys):
    result = {"accession": None}

    acc_keys = {}
    acc_keys.update(keys)
    acc_keys["code"] = keys["accession"]
    accession = Accession.retrieve_or_create(
        session, acc_keys, create=("taxon" in acc_keys and "rank" in acc_keys)
    )

    result["accession"] = accession

    return result


# ─── ORM classes ─────────────────────────────────────────


class Accession(Base, Serializable, WithNotes):
    """
    :Table name: accession

    :Columns:
        *code*: :class:`sqlalchemy.types.Unicode`
            the accession code

        *prov_type*: :class:`bauble.types.Enum`
            the provenance type

            Possible values:
                * first column of prov_type_values

        *wild_prov_status*:  :class:`bauble.types.Enum`
            this column can be used to give more provenance
            information

            Possible values:
                * union of first columns of wild_prov_status_values,
                * purchase_prov_status_values,
                * cultivated_prov_status_values

        *date_accd*: :class:`bauble.DbDate`
            the date this accession was accessioned

        *id_qual*: :class:`bauble.types.Enum`
            The id qualifier is used to indicate uncertainty in the
            identification of this accession

            Possible values:
                * aff. - affinity with
                * cf. - compare with
                * forsan - perhaps
                * near - close to
                * ? - questionable
                * incorrect

        *id_qual_rank*: :class:`sqlalchemy.types.Unicode`
            The rank of the species that the id_qual refers to.

        *private*: :class:`sqlalchemy.types.Boolean`
            Flag to indicate where this information is sensitive and
            should be kept private

        *species_id*: :class:`sqlalchemy.types.Integer()`
            foreign key to the species table

    :Properties:
        *species*:
            the species this accession refers to

        *source*:
            source is a relation to a Source instance

        *plants*:
            a list of plants related to this accession

        *verifications*:
            a list of verifications on the identification of this accession

    :Constraints:

    """

    __tablename__: str = "accession"
    __cached_species_str: ClassVar[dict[tuple[bool, bool], str]] = {}
    __warned_about_id_qual: ClassVar[bool] = False

    # columns
    #: the accession code
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(Unicode(20), nullable=False, unique=True)
    code_format: str = "%Y%PD####"
    order_by: ClassVar = [asc(code)]

    @validates("code")
    def validate_stripping(self, key: str, value: Optional[str]) -> Optional[str]:
        return value.strip() if value else None

    prov_type: Mapped[Optional[str]] = mapped_column(
        types.Enum(
            values=[i[0] for i in prov_type_values],
            translations=dict(prov_type_values),
            omit_aliases=False,
        ),
        default=None,
    )

    wild_prov_status: Mapped[Optional[str]] = mapped_column(
        types.Enum(
            values=[i[0] for i in wild_prov_status_values],
            translations=dict(wild_prov_status_values),
            omit_aliases=False,
        ),
        default=None,
    )

    date_accd: Mapped[DbDate] = mapped_column(DbDate)
    date_recvd: Mapped[DbDate] = mapped_column(DbDate)
    quantity_recvd: Mapped[int] = mapped_column(Integer, autoincrement=False)
    recvd_type: Mapped[Optional[str]] = mapped_column(
        types.Enum(
            values=list(recvd_type_values.keys()),
            translations=recvd_type_values,
            omit_aliases=False,
        ),
        default=None,
    )

    # ITF2 - C24 - Rank Qualified Flag - Transfer code: rkql
    # B: Below Family; F: Family; G: Genus; S: Species; I: first
    # Infraspecific Epithet; J: second Infraspecific Epithet; C: Cultivar;
    id_qual_rank: Mapped[str] = mapped_column(Unicode(10))

    # ITF2 - C25 - Identification Qualifier - Transfer code: idql
    id_qual: Mapped[Optional[str]] = mapped_column(
        types.Enum(
            values=["aff.", "cf.", "incorrect", "forsan", "near", "?", ""],
            omit_aliases=False,
        ),
        nullable=False,
        default="",
    )

    # "private" new in 0.8b2
    private: Mapped[bool] = mapped_column(Boolean, default=False)
    species_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("species.id"), nullable=False
    )

    # intended location
    intended_location_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("location.id")
    )
    intended2_location_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("location.id")
    )

    # relations
    species: Mapped["Species"] = relationship(
        "Species",
        uselist=False,
        back_populates="accessions",
        cascade="all, delete-orphan",
        single_parent=True,
        active_history=True,
    )

    intended_location: Mapped[Optional["Location"]] = relationship(
        "Location", primaryjoin="Accession.intended_location_id==Location.id"
    )
    intended2_location: Mapped[Optional["Location"]] = relationship(
        "Location", primaryjoin="Accession.intended2_location_id==Location.id"
    )

    @classmethod
    def get_next_code(cls, code_format: Optional[Any] = None):
        """
        Return the next available accession code.

        the format is stored in the `bauble` table.
        the format may contain a %PD, replaced by the plant delimiter.
        date formatting is applied.

        If there is an error getting the next code the None is returned.
        """
        from .plant import Plant  # pylint: disable=import-outside-toplevel

        # auto generate/increment the accession code
        session = Session()
        try:
            if code_format is None:
                code_format = cls.code_format
            format = code_format.replace("%PD", Plant.get_delimiter())
            today = datetime.date.today()
            if format.find("%{Y-1}") >= 0:
                format = format.replace("%{Y-1}", str(today.year - 1))
            format = today.strftime(format)
            start = format.rstrip("#")
            if start == format:
                # fixed value
                return start
            digits = len(format) - len(start)
            num_fmt = start + "%%0%dd" % digits

            codes = session.execute(
                select(Accession.code).where(Accession.code.like(f"{start}%"))
            ).scalars().all()

            if codes:
                suffixes = [safe_int(c[len(start) :]) for c in codes]
                next_number = (max(suffixes) or 0) + 1
            else:
                next_number = 1

            return num_fmt % next_number
        
        except Exception as e:
            logger.debug(e)
            return None
        finally:
            session.close()

    def search_view_markup_pair(self):
        """provide the two lines describing object for SearchView row."""
        first, second = (
            xml_safe(str(self)),
            self.species_str(markup=True, authors=True),
        )
        suffix = _("%(1)s plant groups in %(2)s location(s)") % {
            "1": len(set(self.plants)),
            "2": len({p.location for p in self.plants}),
        }
        suffix = (
            '<span foreground="#555555" size="small" '
            f'weight="light"> - {suffix}</span>'
        )
        return first + suffix, second

    @property
    def parent_plant(self):
        try:
            return self.source.plant_propagation.plant
        except AttributeError:
            return None

    @property
    def propagations(self):
        import operator

        return reduce(operator.add, [p.propagations for p in self.plants], [])

    @property
    def pictures(self):
        import operator

        return reduce(operator.add, [p.pictures for p in self.plants], [])

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.__cached_species_str = {}

    @reconstructor
    def init_on_load(self) -> None:
        """
        Called instead of __init__() when an Accession is loaded from
        the database.
        """
        self.__cached_species_str = {}

    def invalidate_str_cache(self) -> None:
        self.__cached_species_str = {}

    def __str__(self) -> str:
        return self.code

    def species_str(self, authors: bool = False, markup: bool = False):
        """
        Return the string of the species with the id qualifier(id_qual)
        injected into the proper place.

        If the species isn't part of a session of if the species is dirty,
        i.e. in object_session(species).dirty, then a new string will be
        built even if the species hasn't been changed since the last call
        to this method.
        """

        # WARNING: don't use session.is_modified() here because it
        # will query lots of dependencies
        try:
            cached = self.__cached_species_str[(markup, authors)]
        except KeyError:
            self.__cached_species_str[(markup, authors)] = None
            cached = None
        session = object_session(self.species)
        if session:
            # if not part of a session or if the species is dirty then
            # build a new string
            if cached is not None and self.species not in session.dirty:
                return cached
        if not self.species:
            return None

        # show a warning if the id_qual is aff. or cf. but the
        # id_qual_rank is None, but only show it once
        try:
            self.__warned_about_id_qual
        except AttributeError:
            self.__warned_about_id_qual = False
        if (
            self.id_qual in ("aff.", "cf.")
            and not self.id_qual_rank
            and not self.__warned_about_id_qual
        ):
            msg = (
                _("If the id_qual is aff. or cf. " "then id_qual_rank is required. %s ")
                % self.code
            )
            logger.warning(msg)
            self.__warned_about_id_qual = True

        if self.id_qual:
            logger.debug(f"id_qual is {self.id_qual}")
            sp_str = self.species.str(
                authors,
                markup,
                remove_zws=True,
                qualification=(self.id_qual_rank, self.id_qual),
            )
        else:
            sp_str = self.species.str(authors, markup, remove_zws=True)

        self.__cached_species_str[(markup, authors)] = sp_str
        return sp_str

    def markup(self):
        return f"{self.code} ({self.accession.species_str(markup=True, authors=True)})"

    def as_dict(self):
        result = Serializable.as_dict(self)
        result["species"] = self.species.str(remove_zws=True, authors=False)
        if self.source and self.source.source_detail:
            result["contact"] = self.source.source_detail.name
        return result

    @classmethod
    def correct_field_names(cls, keys) -> None:
        for internal, exchange in [("species", "taxon")]:
            if exchange in keys:
                keys[internal] = keys[exchange]
                del keys[exchange]

    @classmethod
    def compute_serializable_fields(cls, session, keys):
        logger.debug(f"compute_serializable_fields(session, {keys})")
        result = {"species": None}
        keys = dict(keys)  # make copy
        if "species" in keys:
            keys["taxon"] = keys["species"]
            keys["rank"] = "species"
        if "rank" in keys and "taxon" in keys:
            # now we must connect the accession to the species it refers to
            if keys["rank"] == "species":
                genus_name, epithet = keys["taxon"].split(" ", 1)
                sp_dict = {"ht-epithet": genus_name, "epithet": epithet}
                result["species"] = Species.retrieve_or_create(
                    session, sp_dict, create=False
                )
            elif keys["rank"] == "genus":
                result["species"] = Species.retrieve_or_create(
                    session, {"ht-epithet": keys["taxon"], "epithet": "sp"}
                )
            elif keys["rank"] == "familia":
                unknown_genus = "Zzz-" + keys["taxon"][:-1]
                Genus.retrieve_or_create(
                    session,
                    {"ht-epithet": keys["taxon"], "epithet": unknown_genus},
                )
                result["species"] = Species.retrieve_or_create(
                    session, {"ht-epithet": unknown_genus, "epithet": "sp"}
                )
        return result

    @classmethod
    def retrieve(cls, session, keys):
        stmt = (
            cls.query_with_default_order()
            .where(cls.code == keys["code"])
            )

        return session.execute(stmt).scalars.one_or_none()

    def top_level_count(self):
        sd = self.source and self.source.source_detail
        return {
            (1, "Accessions"): 1,
            (2, "Species"): {self.species.id},
            (3, "Genera"): {self.species.genus.id},
            (4, "Families"): {self.species.genus.family.id},
            (5, "Plantings"): len(self.plants),
            (6, "Living plants"): sum(p.quantity for p in self.plants),
            (7, "Locations"): {p.location.id for p in self.plants},
            (8, "Sources"): set(sd and [sd.id] or []),
        }


# from .plant import Plant  # explicit import at runtime


# invalidate an accessions string cache after it has been updated
# Register the after_update event
@event.listens_for(Accession, "after_update")
def receive_after_update(mapper, connection, target) -> None:
    target.invalidate_str_cache()


AccessionNote: Any = make_note_class(
    "Accession", Accession, compute_accession_note_serializable_fields
)
Accession.notes: Mapped["AccessionNote"] = relationship(
    "AccessionNote",
    back_populates="accession",
    cascade="all, delete-orphan",
    single_parent=True,
    uselist=True,
)
