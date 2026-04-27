#
# Copyright 2008-2010 Brett Adams
# Copyright 2012-2016 Mario Frasca <mario@anche.no>.
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
import logging
from gettext import gettext as _
from itertools import chain
from typing import Any, ClassVar, Dict, List, Optional, Union

import bauble.btypes as types
import bauble.db as db
import bauble.error as error
import bauble.utils as utils
from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    Unicode,
    UnicodeText,
    UniqueConstraint,
    asc,
    func,
    select,
    text,
)
from sqlalchemy.ext.associationproxy import association_proxy

# from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import hybrid_property

# from sqlalchemy.orm import foreign
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.orm.session import object_session

__all__ = ["Species"]
logger: Any = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


def _remove_zws(s):
    "remove_zero_width_space"
    if s:
        return s.replace("\u200b", "")
    return s


class VNList(list):
    """
    A Collection class for Species.vernacular_names

    This makes it possible to automatically remove a
    default_vernacular_name if the vernacular_name is removed from the
    list.
    """

    def remove(self, vn) -> None:
        super().remove(vn)
        try:
            if vn.species.default_vernacular_name == vn:
                del vn.species.default_vernacular_name
        except Exception as e:
            logger.debug(e)


infrasp_rank_values: Any = {
    "subsp.": _("subsp."),
    "var.": _("var."),
    "subvar.": _("subvar"),
    "f.": _("f."),
    "subf.": _("subf."),
    "cv.": _("cv."),
    None: "",
}


# TODO: there is a trade_name column but there's no support yet for editing
# the trade_name or for using the trade_name when building the string
# for the species, for more information about trade_names see,
# http://www.hortax.org.uk/gardenplantsnames.html

# TODO: the specific epithet should not be non-nullable but instead
# make sure that at least one of the specific epithet, cultivar name
# or cultivar group is specificed


def rank_level(rank):
    "define rank order"

    ordering = [
        "familia",
        "subfamilia",
        "tribus",
        "subtribus",
        "genus",
        "subgenus",
        "species",
        None,
        "subsp.",
        "var.",
        "subvar.",
        "f.",
        "subf.",
        "cv.",
    ]
    return ordering.index(rank)


def compare_rank(rank1, rank2):
    "implement the binary comparison operation needed for sorting"

    return rank_level(rank1).__cmp__(rank_level(rank2))


# Defer import of Genus
def get_genus():
    from bauble.plugins.plants.genus import Genus

    return Genus


class Species(db.Base, db.Serializable, db.DefiningPictures, db.WithNotes):
    """
    :Table name: species

    :Columns:
        *epithet*:
        *sp2*:
        *author*:

        *hybrid*:
            Hybrid flag

        *infrasp1*:
        *infrasp1_rank*:
        *infrasp1_author*:

        *infrasp2*:
        *infrasp2_rank*:
        *infrasp2_author*:

        *infrasp3*:
        *infrasp3_rank*:
        *infrasp3_author*:

        *infrasp4*:
        *infrasp4_rank*:
        *infrasp4_author*:

        *cv_group*:
        *trade_name*:

        *sp_qual*:
            Species qualifier

            Possible values:
                *agg.*: An aggregate species

                *s. lat.*: aggregrate species (sensu lato)

                *s. str.*: segregate species (sensu stricto)

        *label_distribution*:
            UnicodeText
            This field is optional and can be used for the label in case
            str(self.distribution) is too long to fit on the label.

    :Properties:
        *accessions*:

        *vernacular_names*:

        *default_vernacular_name*:

        *synonyms*:

        *distribution*:

    :Constraints:
        The combination of epithet, author, hybrid, sp_qual,
        cv_group, trade_name, genus_id
    """
    label_distribution: Any
    synonyms: Any
    awards: Any
    __tablename__: str = "species"
    id: Mapped[int] = mapped_column(primary_key=True, nullable=False)
    epithet: Mapped[str] = mapped_column(Unicode(64), index=True)
    genus_id: Mapped[int] = mapped_column(ForeignKey("genus.id"), nullable=False)
    __table_args__: Any = (
        UniqueConstraint("genus_id", "epithet", name="_genus_epithet_uc"),
    )


    # Define relationship to Genus
    genus: Mapped["Genus"] = relationship(
        "Genus",
        back_populates="species",
        lazy="joined",
        uselist=False,
        active_history=True,
    )
    accessions: Mapped[List["Accession"]] = relationship("Accession", back_populates="species", uselist=True)

    rank: ClassVar[str] = "species"
    link_keys: Any = ["accepted"]

    @hybrid_property
    def ht_epithet(self):
        """Retrieve the genus epithet from the related Genus instance."""
        return self.genus.epithet if self.genus else None

    @ht_epithet.expression
    def ht_epithet(cls):
        """Enable SQL querying on ht_epithet by joining with Genus."""
        return get_genus().epithet

    @classmethod
    def retrieve(cls, session, keys):
        """
        Retrieve a single Species instance based on the provided keys.

        :param session: SQLAlchemy session.
        :param keys: Dictionary of filtering criteria (e.g., {"epithet": ..., "ht-epithet": ...}).
        :return: The Species instance if found, otherwise None.
        """
        from .genus import Genus

        try:
            # Start from Species explicitly, then join Genus explicitly
            stmt = (
                select(cls)
                .select_from(cls)
                .join(Genus, cls.genus_id == Genus.id)
            )

            # Normalize inputs (strip zero-width spaces, casefold for case-insensitive compare)
            ep = keys.get("epithet")
            ht = keys.get("ht-epithet")

            if ep:
                stmt = stmt.where(func.lower(cls.epithet) == func.lower(func.trim(ep)))
            if ht:
                stmt = stmt.where(func.lower(Genus.epithet) == func.lower(func.trim(ht)))

            # One row or None
            result = session.execute(stmt).scalars().one_or_none()

            if result:
                return result

            # Log warning if no result is found
            logger.warning(f"No Species found for criteria: {keys}")
            return None

        except MultipleResultsFound:
            logger.warning(f"Multiple Species found for criteria: {keys}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving Species with criteria {keys}: {e}")
            return None




    def search_view_markup_pair(self):
        """provide the two lines describing object for SearchView row."""
        try:
            sess = object_session(self)

            def _rel_loaded(name: str) -> bool:
                # relationship present in __dict__ => already loaded, no lazy load
                return name in self.__dict__

            # --- vernacular names (list) ---
            if sess is not None:
                vern_list = list(self.vernacular_names or [])
            else:
                vern_list = list(self.__dict__.get("vernacular_names") or [])

            # --- family (via genus) ---
            family_txt = ""
            if sess is not None:
                try:
                    family_txt = f"{self.genus.family}"
                except Exception:
                    family_txt = ""
            else:
                g = self.__dict__.get("genus")
                if g is not None:
                    try:
                        family_txt = f"{getattr(g, 'family', '') or ''}"
                    except Exception:
                        family_txt = ""

            # build the second line (substring)
            if vern_list:
                vtxt = ", ".join(str(v) for v in vern_list if v is not None)
                substring = f"{family_txt} -- {vtxt}" if family_txt else vtxt
            else:
                substring = family_txt

            # --- synonym trail (accepted) ---
            trail = ""
            accepted = self.accepted if (sess is not None) else self.__dict__.get("accepted")
            if accepted:
                trail += (
                    '<span foreground="#555555" size="small" weight="light"> - '
                    + _("synonym of %s") + "</span>"
                ) % accepted.markup(authors=True)

            # --- main citation ---
            citation = self.markup(authors=True)
            authorship_text = utils.xml_safe(self.author)
            if authorship_text:
                citation = citation.replace(
                    authorship_text,
                    f'<span weight="light">{authorship_text}</span>',
                )

            return citation + trail, substring or ""
        except Exception:
            import traceback
            logger.warning(traceback.format_exc())
            return "...", "..."


    @property
    def cites(self):
        """the cites status of this taxon, or None

        cites appendix number, one of I, II, or III.
        not enforced by the software in v1.0.x
        """

        cites_notes = [
            i.note for i in self.notes if i.category and i.category.upper() == "CITES"
        ]
        if not cites_notes:
            return self.genus.cites
        return cites_notes[0]

    @property
    def conservation(self):
        """the IUCN conservation status of this taxon, or DD

        one of: EX, RE, CR, EN, VU, NT, LC, DD
        not enforced by the software in v1.0.x
        """

        {
            "EX": _("Extinct (EX)"),
            "EW": _("Extinct Wild (EW)"),
            "RE": _("Regionally Extinct (RE)"),
            "CR": _("Critically Endangered (CR)"),
            "EN": _("Endangered (EN)"),
            "VU": _("Vulnerable (VU)"),
            "NT": _("Near Threatened (NT)"),
            "LV": _("Least Concern (LC)"),
            "DD": _("Data Deficient (DD)"),
            "NE": _("Not Evaluated (NE)"),
        }

        notes = [
            i.note for i in self.notes if i.category and i.category.upper() == "IUCN"
        ]
        return (notes + ["DD"])[0]

    @property
    def condition(self):
        """the condition of this taxon, or None

        this is referred to what the garden conservator considers the
        area of interest. it is really an interpretation, not a fact.
        """
        # one of, but not forcibly so:
        [_("endemic"), _("indigenous"), _("native"), _("introduced")]

        notes = [i.note for i in self.notes if i.category.lower() == "condition"]
        return (notes + [None])[0]

    def __lowest_infraspecific(self):
        infrasp = [
            (self.infrasp1_rank, self.infrasp1, self.infrasp1_author),
            (self.infrasp2_rank, self.infrasp2, self.infrasp2_author),
            (self.infrasp3_rank, self.infrasp3, self.infrasp3_author),
            (self.infrasp4_rank, self.infrasp4, self.infrasp4_author),
        ]
        infrasp = [i for i in infrasp if i[0] not in ["cv.", "", None]]
        if infrasp == []:
            return ("", "", "")
        return sorted(infrasp, key=lambda a: rank_level(a[0]))[-1]

    @property
    def infraspecific_rank(self):
        return self.__lowest_infraspecific()[0] or ""

    @property
    def infraspecific_epithet(self):
        return self.__lowest_infraspecific()[1] or ""

    @property
    def infraspecific_author(self):
        return self.__lowest_infraspecific()[2] or ""

    @property
    def cultivar_epithet(self):
        infrasp = (
            (self.infrasp1_rank, self.infrasp1, self.infrasp1_author),
            (self.infrasp2_rank, self.infrasp2, self.infrasp2_author),
            (self.infrasp3_rank, self.infrasp3, self.infrasp3_author),
            (self.infrasp4_rank, self.infrasp4, self.infrasp4_author),
        )
        for rank, epithet, _author in infrasp:
            if rank == "cv.":
                return epithet
        return ""

    # columns
    sp = synonym("epithet")
    sp2: Mapped[str] = mapped_column(Unicode(64), index=True)  # in case hybrid=True
    author: Mapped[Optional[str]] = mapped_column(Unicode(128))
    order_by: Any = [asc(epithet), asc(author)]
    hybrid: Mapped[bool] = mapped_column(Boolean, default=False)
    sp_qual: Mapped[str] = mapped_column(
        types.Enum(values=["agg.", "s. lat.", "s. str.", None], omit_aliases=False),
        default=None,
    )
    cv_group: Mapped[str] = mapped_column(Unicode(50))
    trade_name: Mapped[str] = mapped_column(Unicode(64))

    infrasp1: Mapped[str] = mapped_column(Unicode(64))
    infrasp1_rank: Mapped[str] = mapped_column(
        types.Enum(
            values=list(infrasp_rank_values.keys()),
            translations=infrasp_rank_values,
            omit_aliases=False,
        )
    )
    infrasp1_author: Mapped[str] = mapped_column(Unicode(64))

    infrasp2: Mapped[str] = mapped_column(Unicode(64))
    infrasp2_rank: Mapped[str] = mapped_column(
        types.Enum(
            values=list(infrasp_rank_values.keys()),
            translations=infrasp_rank_values,
            omit_aliases=False,
        )
    )
    infrasp2_author: Mapped[str] = mapped_column(Unicode(64))

    infrasp3: Mapped[str] = mapped_column(Unicode(64))
    infrasp3_rank: Mapped[str] = mapped_column(
        types.Enum(
            values=list(infrasp_rank_values.keys()),
            translations=infrasp_rank_values,
            omit_aliases=False,
        )
    )
    infrasp3_author: Mapped[str] = mapped_column(Unicode(64))

    infrasp4: Mapped[str] = mapped_column(Unicode(64))
    infrasp4_rank: Mapped[str] = mapped_column(
        types.Enum(
            values=list(infrasp_rank_values.keys()),
            translations=infrasp_rank_values,
            omit_aliases=False,
        )
    )
    infrasp4_author: Mapped[str] = mapped_column(Unicode(64))

    # the Species.genus property is defined as back_populates in Genus.species

    label_distribution : Mapped[str] = mapped_column(UnicodeText)
    bc_distribution: Mapped[str] = mapped_column(UnicodeText)

    # relations
    synonyms = association_proxy("_synonyms", "synonym")
    _synonyms: Mapped[List["SpeciesSynonym"]] = relationship(
        "SpeciesSynonym",
        primaryjoin="Species.id==SpeciesSynonym.species_id",
        cascade="all, delete-orphan",
        uselist=True,
        back_populates="species",
    )

    # this is a dummy relation, it is only here to make cascading work
    # correctly and to ensure that all synonyms related to this genus
    # get deleted if this genus gets deleted
    _synonyms_synonym: Mapped[List["SpeciesSynonym"]] = relationship(
        "SpeciesSynonym",
        primaryjoin="Species.id==SpeciesSynonym.synonym_id",
        cascade="all, delete-orphan",
        uselist=True,
    )

    # VernacularName.species gets defined here too.
    vernacular_names: Mapped[List["VernacularName"]] = relationship(
        "VernacularName",
        cascade="all, delete-orphan",
        collection_class=VNList,
        back_populates="species",
        uselist=True,
        single_parent=False,
    )

    _default_vernacular_name: Mapped[Optional["DefaultVernacularName"]] = relationship(
        "DefaultVernacularName",
        uselist=False,
        single_parent=False,
        cascade="all, delete-orphan",
        back_populates="species",
        active_history=True,
    )
    distribution: Mapped[Optional["SpeciesDistribution"]] = (
        relationship(
            "SpeciesDistribution",
            cascade="all, delete-orphan",
            back_populates="species",
            single_parent=False,
            uselist=False,
            active_history=True,
        )
        or []
    )

    habit_id: Mapped[int] = mapped_column(Integer, ForeignKey("habit.id"), default=None)
    habit: Mapped[Optional["Habit"]] = relationship(
        "Habit", uselist=False, back_populates="species", active_history=True
    )

    flower_color_id: Mapped[int] = mapped_column(Integer, ForeignKey("color.id"), default=None)
    flower_color: Mapped[Optional["Color"]] = relationship(
        "Color", uselist=False, back_populates="species", active_history=True
    )

    # Relationships
    verifications: Mapped[List["Verification"]] = relationship(
        "Verification",
        primaryjoin="Verification.species_id == Species.id",
        back_populates="species",
        cascade="save-update, merge",  # Less aggressive cascade
        uselist=True,
        overlaps="prev_species",
    )
    previous_verifications: Mapped[List["Verification"]] = relationship(
        "Verification",
        primaryjoin="Verification.prev_species_id == Species.id",
        back_populates="prev_species",
        cascade="save-update, merge",  # Less aggressive cascade
        uselist=True,
        overlaps="species",
    )
    # hardiness_zone : Mapped[str] = mapped_column(Unicode(4))

    awards : Mapped[str] = mapped_column(UnicodeText)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def __str__(self) -> str:
        "return the default string representation for self."
        return self.str()

    def _get_default_vernacular_name(self):
        if self._default_vernacular_name is None:
            return None
        return self._default_vernacular_name.vernacular_name

    def _set_default_vernacular_name(self, vn) -> None:
        if vn is None:
            del self.default_vernacular_name
            return
        if vn not in self.vernacular_names:
            self.vernacular_names.append(vn)
        d = DefaultVernacularName()
        d.vernacular_name = vn
        self._default_vernacular_name = d

    def _del_default_vernacular_name(self) -> None:
        utils.delete_or_expunge(self._default_vernacular_name)
        del self._default_vernacular_name

    default_vernacular_name: Any = property(
        _get_default_vernacular_name,
        _set_default_vernacular_name,
        _del_default_vernacular_name,
    )

    def distribution_str(self):
        if self.distribution is None:
            return ""
        else:
            dist = [f"{d}" for d in self.distribution]
            return ", ".join(sorted(dist))

    def markup(self, authors: bool = False, genus: bool = True):
        """returns this object as a string with markup

        :param authors: whether the authorship should be included
        :param genus: whether the genus name should be included

        """
        return self.str(authors, markup=True, genus=genus)

    # in PlantPlugins.init() we set this to 'x' for win32
    hybrid_char: str = "×"

    def str(
        self,
        authors: bool = False,
        markup: bool = False,
        remove_zws: bool = False,
        genus: bool = True,
        qualification: Optional[Any] = None
    ):
        """
        returns a string for species

        :param authors: flag to toggle whether authorship should be included
        :param markup: flag to toggle whether the returned text is marked up
        to show italics on the epithets
        :param remove_zws: flag to toggle zero width spaces, helping
        semantically correct lexicographic order.
        :param genus: flag to toggle leading genus name.
        :param qualification: pair or None. if specified, first is the
        qualified rank, second is the qualification.
        """
        # TODO: this method will raise an error if the session is none
        # since it won't be able to look up the genus....we could
        # probably try to query the genus directly with the genus_id
        if genus is True:
            genus = str(self.genus)
        else:
            genus = ""
        if self.epithet and not remove_zws:
            epithet = "\u200b" + self.epithet  # prepend with zero_width_space
        else:
            epithet = self.epithet
        sp2 = self.sp2
        if markup:
            escape = utils.xml_safe

            def italicize(s):
                return "<i>{}</i>".format(escape(  # all but the multiplication signs
                    s
                ).replace("×", "</i>×<i>"))

            genus = italicize(genus)
            if epithet is not None:
                epithet = italicize(epithet)
            if sp2 is not None:
                sp2 = italicize(sp2)
        else:
            italicize = escape = lambda x: x

        author = None
        if authors and self.author:
            author = escape(self.author)

        infrasp = (
            (self.infrasp1_rank, self.infrasp1, self.infrasp1_author),
            (self.infrasp2_rank, self.infrasp2, self.infrasp2_author),
            (self.infrasp3_rank, self.infrasp3, self.infrasp3_author),
            (self.infrasp4_rank, self.infrasp4, self.infrasp4_author),
        )

        infrasp_parts = []
        group_added = False
        for irank, iepithet, iauthor in infrasp:
            if irank == "cv." and iepithet:
                if self.cv_group and not group_added:
                    group_added = True
                    infrasp_parts.append(
                        _("(%(group)s Group)") % dict(group=self.cv_group)
                    )
                infrasp_parts.append(f"'{escape(iepithet)}'")
            else:
                if irank:
                    infrasp_parts.append(irank)
                if iepithet and irank:
                    infrasp_parts.append(italicize(iepithet))
                elif iepithet:
                    infrasp_parts.append(escape(iepithet))

            if authors and iauthor:
                infrasp_parts.append(escape(iauthor))
        if self.cv_group and not group_added:
            infrasp_parts.append(_("%(group)s Group") % dict(group=self.cv_group))

        # create the binomial part
        binomial = [genus, self.hybrid and self.hybrid_char, epithet, author]
        logger.debug("binomial parts: »{}« »{}« »{}« »{}«".format(*tuple(binomial)))

        # create the tail, ie: anything to add on to the end
        tail = []
        if self.sp_qual:
            tail = [self.sp_qual]

        if qualification is not None:
            rank, qual = qualification
            if qual in ["incorrect"]:
                rank = None
            if rank == "sp":
                binomial.insert(2, qual)
            elif not rank:
                binomial[2] += " (" + qual + ")"
            elif rank == "genus":
                binomial.insert(0, qual)
            elif rank == "infrasp":
                if infrasp_parts:
                    infrasp_parts.insert(0, qual)
            else:
                for r, e, _a in infrasp:
                    if r == "cv.":
                        e = f"'{e}'"
                    if rank == r:
                        pos = infrasp_parts.index(e)
                        infrasp_parts.insert(pos, qual)
                else:
                    logger.info(f"cannot find specified rank {e}")

        parts = chain(binomial, infrasp_parts, tail)
        s = " ".join(i for i in parts if i)
        if self.hybrid:
            s = s.replace(f"{self.hybrid_char} ", self.hybrid_char)
        return s

    @property
    def accepted(self) -> Any:
        """Return the accepted name for this species (if it is a synonym)."""
        if self._synonyms_synonym:
            return self._synonyms_synonym[0].species
        return None

    @accepted.setter
    def accepted(self, value):
        """Assign this species as a synonym of another species."""
        assert isinstance(value, Species)
        if self == value or self in value.synonyms:
            return  # Prevent cycles or redundant assignment

        session = db.object_session(self)
        if not session:
            logger.warning("species:accepted.setter - object not in session")
            return

        # Remove existing synonym relationship, if any
        existing = next(iter(self._synonyms_synonym), None)
        if existing:
            session.delete(existing)
            session.flush()

        # Create new synonym relationship
        if value != self:
            value.synonyms.append(self)

    def has_accessions(self):
        """true if species is linked to at least one accession"""

        return False

    infrasp_attr: Any = {
        1: {
            "rank": "infrasp1_rank",
            "epithet": "infrasp1",
            "author": "infrasp1_author",
        },
        2: {
            "rank": "infrasp2_rank",
            "epithet": "infrasp2",
            "author": "infrasp2_author",
        },
        3: {
            "rank": "infrasp3_rank",
            "epithet": "infrasp3",
            "author": "infrasp3_author",
        },
        4: {
            "rank": "infrasp4_rank",
            "epithet": "infrasp4",
            "author": "infrasp4_author",
        },
    }

    def get_infrasp(self, level):
        """
        level should be 1-4
        """
        return (
            getattr(self, self.infrasp_attr[level]["rank"]),
            getattr(self, self.infrasp_attr[level]["epithet"]),
            getattr(self, self.infrasp_attr[level]["author"]),
        )

    def set_infrasp(self, level, rank, epithet, author: Optional[Any] = None) -> None:
        """
        level should be 1-4
        """
        setattr(self, self.infrasp_attr[level]["rank"], rank)
        setattr(self, self.infrasp_attr[level]["epithet"], epithet)
        setattr(self, self.infrasp_attr[level]["author"], author)

    def as_dict(self, recurse: bool = True):
        result = {
            col: getattr(self, col)
            for col in list(self.__table__.columns.keys())
            if col not in ["id"]
            and col[0] != "_"
            and getattr(self, col) is not None
            and not col.endswith("_id")
        }
        result["object"] = "taxon"
        result["rank"] = "species"
        result["ht-rank"] = "genus"
        result["ht-epithet"] = self.genus.epithet
        if recurse and self.accepted is not None:
            result["accepted"] = self.accepted.as_dict(recurse=False)
        return result

    @classmethod
    def correct_field_names(cls, keys) -> None:
        pass

    @classmethod
    def compute_serializable_fields(cls, session, keys):
        from .genus import Genus

        result = {"genus": None}
        # retrieve genus object
        specifies_family = keys.get("familia")
        result["genus"] = Genus.retrieve_or_create(
            session,
            {"epithet": keys["ht-epithet"], "ht-epithet": specifies_family},
            create=(specifies_family is not None),
        )
        if result["genus"] is None:
            raise error.NoResultException()
        return result

    def top_level_count(self):
        plants = [p for a in self.accessions for p in a.plants]
        return {
            (1, "Species"): 1,
            (2, "Genera"): {self.genus.id},
            (3, "Families"): {self.genus.family.id},
            (4, "Accessions"): len(self.accessions),
            (5, "Plantings"): len(plants),
            (6, "Living plants"): sum(p.quantity for p in plants),
            (7, "Locations"): {p.location.id for p in plants},
            (8, "Sources"): {
                a.source.source_detail.id
                for a in self.accessions
                if a.source and a.source.source_detail
            },
        }


def as_dict(self):
    result = db.Serializable.as_dict(self)
    result["species"] = self.species.str(self.species, remove_zws=True)
    return result


def compute_serializable_fields(cls, session, keys):
    logger.debug(f"compute_serializable_fields(session, {keys})")
    result = {}
    genus_name, epithet = keys["species"].split(" ", 1)
    sp_dict = {"ht-epithet": genus_name, "epithet": epithet}
    result["species"] = Species.retrieve_or_create(session, sp_dict, create=False)
    return result


def retrieve(session, keys):
    from .genus import Genus

    genus, epithet = keys["species"].split(" ", 1)
    try:
        return (
            session.execute(
                select(Species)
                .where(Species.category == keys["category"])
                .join(Species.genus)
                .where(Species.epithet == epithet)
                .join(Genus)
                .where(Genus.epithet == genus)
            )
            .scalars()
            .one()
        )
    except Exception as e:
        logger.error(f"Error retrieving species with keys {keys}: {e}")
        return None


SpeciesNote: Any = db.make_note_class(
    "Species", Species, compute_serializable_fields, as_dict, retrieve
)
Species.notes = relationship(
    "SpeciesNote",
    back_populates="species",
    cascade="all, delete-orphan",
    uselist=True,
    single_parent=True,
)


class SpeciesSynonym(db.Base):
    """
    :Table name: species_synonym
    """
    id: Any
    __tablename__: str = "species_synonym"

    # columns
    id : Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    species_id: Mapped[int] = mapped_column(Integer, ForeignKey("species.id"), nullable=False)
    synonym_id: Mapped[int] = mapped_column(Integer, ForeignKey("species.id"), nullable=False, unique=True)

    # Relationship to the main Species entity
    species: Mapped["Species"] = relationship(
        "Species",
        uselist=False,  # One-to-one relationship
        back_populates="_synonyms",
        foreign_keys=[species_id],
        active_history=True,
    )

    # relations
    synonym: Mapped["Species"] = relationship(
        "Species",
        back_populates="_synonyms_synonym",
        uselist=False,  # One-to-one relationship
        foreign_keys=[synonym_id],
        active_history=True,
    )

    def __init__(self, synonym: Optional[Any] = None, **kwargs) -> None:
        # it is necessary that the first argument here be synonym for
        # the Species.synonyms association_proxy to work
        self.synonym = synonym
        super().__init__(**kwargs)

    def __str__(self) -> str:
        return str(self.synonym)


class VernacularName(db.Base, db.Serializable):
    """
    :Table name: vernacular_name

    :Columns:
        *name*:
            the vernacular name

        *language*:
            language is free text and could include something like UK
            or US to identify the origin of the name

        *species_id*:
            key to the species this vernacular name refers to

    :Properties:

    :Constraints:
    """

    __tablename__: str = "vernacular_name"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    name: Mapped[str] = mapped_column(Unicode(128), nullable=False)
    language: Mapped[str] = mapped_column(Unicode(128))
    species_id: Mapped[int] = mapped_column(Integer, ForeignKey("species.id"), nullable=False)
    __table_args__: Any = (
        UniqueConstraint("name", "language", "species_id", name="vn_index"),
        {},
    )
    species: Mapped["Species"] = relationship(
        "Species",
        back_populates="vernacular_names",
        uselist=False,
        single_parent=False,
        active_history=True,
    )

    def search_view_markup_pair(self):
        """provide the two lines describing object for SearchView row."""
        return str(self), self.species.markup(authors=False)

    def __str__(self) -> str:
        if self.name:
            return self.name
        else:
            return ""

    def replacement(self):
        "user wants the species, not just the name"
        return self.species

    def as_dict(self):
        result = db.Serializable.as_dict(self)
        result["species"] = self.species.str(remove_zws=True)
        return result

    @classmethod
    def compute_serializable_fields(cls, session, keys):
        logger.debug(f"compute_serializable_fields(session, {keys})")
        result = {"species": None}
        if "species" in keys:
            # now we must connect the name to the species it refers to
            genus_name, epithet = keys["species"].split(" ", 1)
            sp_dict = {"ht-epithet": genus_name, "epithet": epithet}
            result["species"] = Species.retrieve_or_create(
                session, sp_dict, create=False
            )
        return result

    @classmethod
    def retrieve(cls, session, keys):
        from .genus import Genus

        g_epithet, s_epithet = keys["species"].split(" ", 1)
        sp = (
            session.execute(
                select(Species)
                .where(Species.epithet == s_epithet)
                .join(Genus)
                .where(Genus.epithet == g_epithet)
            )
            .scalars()
            .first()
        )
        try:
            return (
                session.execute(
                    select(cls).where(
                        cls.species == sp, cls.language == keys["language"]
                    )
                )
                .scalars()
                .one()
            )
        except:
            return None

    @property
    def pictures(self):
        return self.species.pictures


class DefaultVernacularName(db.Base):
    """
    :Table name: default_vernacular_name

    DefaultVernacularName is not meant to be instantiated directly.
    Usually the default vernacular name is set on a species by setting
    the default_vernacular_name property on Species to a
    VernacularName instance

    :Columns:
        *id*:
            Integer, primary_key

        *species_id*:
            foreign key to species.id, nullable=False

        *vernacular_name_id*:

    :Properties:

    :Constraints:
    """

    __tablename__: str = "default_vernacular_name"
    __table_args__: Any = (
        UniqueConstraint("species_id", "vernacular_name_id", name="default_vn_index"),
        {},
    )

    # columns
    id: Mapped[int] = mapped_column(primary_key=True)
    species_id: Mapped[int] = mapped_column(Integer, ForeignKey("species.id"), nullable=False)
    vernacular_name_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("vernacular_name.id"), nullable=False
    )

    # relations
    vernacular_name: Mapped["VernacularName"] = relationship(VernacularName, uselist=False)
    species: Mapped["Species"] = relationship(
        "Species",
        uselist=False,
        back_populates="_default_vernacular_name",
        single_parent=False,
        active_history=True,
    )

    def __str__(self) -> str:
        return str(self.vernacular_name)


class SpeciesDistribution(db.Base):
    """
    :Table name: species_distribution

    :Columns:

    :Properties:

    :Constraints:
    """
    id: Any
    __tablename__: str = "species_distribution"

    # columns
    id : Mapped[int] = mapped_column(Integer, primary_key=True)
    geographic_area_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("geographic_area.id"), nullable=False
    )
    species_id: Mapped[int] = mapped_column(Integer, ForeignKey("species.id"), nullable=False)
    species: Mapped["Species"] = relationship(
        "Species",
        back_populates="distribution",
        single_parent=False,
        uselist=False,
        active_history=True,
    )

    def __str__(self) -> str:
        return str(self.geographic_area)


# late bindings
SpeciesDistribution.geographic_area = relationship(
    "GeographicArea",
    primaryjoin="SpeciesDistribution.geographic_area_id==GeographicArea.id",
    uselist=False,
)


class Habit(db.Base):
    __tablename__: str = "habit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Unicode(64))
    code: Mapped[str] = mapped_column(Unicode(8), unique=True)
    species: Mapped[List["Species"]] = relationship(
        "Species",
        back_populates="habit",
        uselist=True,
    )

    def __str__(self) -> str:
        if self.name:
            return f"{self.name} ({self.code})"
        else:
            return str(self.code)


class Color(db.Base):
    __tablename__: str = "color"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Unicode(32))
    code: Mapped[str] = mapped_column(Unicode(8), unique=True)
    species: Mapped[List["Species"]] = relationship(
        "Species",
        back_populates="flower_color",
        uselist=True,
    )

    def __str__(self) -> str:
        if self.name:
            return f"{self.name} ({self.code})"
        else:
            return str(self.code)


db.Species = Species
db.SpeciesNote = SpeciesNote
db.VernacularName = VernacularName
db.VernacularName = VernacularName
db.VernacularName = VernacularName
