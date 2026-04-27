# bauble/plugins/garden/models/__init__.py

from typing import TYPE_CHECKING, List, Optional

# relationships.py
from sqlalchemy.orm import relationship

if TYPE_CHECKING:
    from .accession import Accession
    from .association_tables import PlantPropagation
    from .location import Location
    from .plant import Plant
    from .plant_change import PlantChange
    from .propagation import Propagation
    from .source import Source
    from .verification import Verification
    from .voucher import Voucher


# Accession <--> Plant
def define_accession_plant_relationships(accession: "Accession", plant: "Plant"):

    # use Plant.code for the order_by to avoid ambiguous column names
    accession.plants: List["Plant"] = relationship(  # type: ignore[assignment]
        # "Plant",
        plant,
        cascade="all, delete-orphan",
        # order_by='plant.code',
        back_populates="accession",
        uselist=True,
        single_parent=True,
    )
    plant.accession: "Accession" = relationship(  # type: ignore[assignment]
        # "Accession",
        accession,
        back_populates="plants",
        uselist=False,
        cascade="save-update",
        active_history=True,
    )


def define_accession_related_relationships(
    accession: "Accession",
    source: "Source",
    verification: "Verification",
    voucher: "Voucher",
):

    # the source of the accession
    accession.source: Optional["Source"] = relationship(
        # "Source",
        source,
        uselist=False,
        cascade="all, delete-orphan",
        back_populates="accession",
        single_parent=True,
        active_history=True,
    )
    accession.verifications: List["Verification"] = relationship(
        # "Verification",  # order_by='date',
        verification,
        cascade="all, delete-orphan",
        back_populates="accession",
        single_parent=True,
        uselist=True,  # An Accession can have multiple Vouchers
    )

    accession.vouchers: List["Voucher"] = relationship(
        # "Voucher",
        voucher,
        cascade="all, delete-orphan",
        back_populates="accession",
        uselist=True,
        single_parent=True,
    )
    source.accession: "Accession" = relationship(  # type: ignore[assignment]
        # "Accession",
        accession,
        back_populates="source",
    )
    voucher.accession: "Accession" = relationship(  # type: ignore[assignment]
        # "Accession",
        accession,
        back_populates="vouchers",
        uselist=False,
        active_history=True,
    )
    verification.accession: "Accession" = relationship(  # type: ignore[assignment]
        # "Accession",
        accession,
        back_populates="verifications",
        uselist=False,
        active_history=True,
    )


# Location <--> Plant
def define_location_relationships(
    plant: "Plant", location: "Location", plant_change: "PlantChange"
):

    # Location <--> Plant
    location.plants: List["Plant"] = relationship(  # type: ignore[assignment]
        # "Plant",
        plant,
        back_populates="location",
        uselist=True,
        overlaps="location",
    )

    plant.location: "Location" = relationship(  # type: ignore[assignment]
        # "Location",
        location,
        back_populates="plants",
        uselist=False,  # A Plant belongs to one Location
        cascade="save-update",
        active_history=True,
    )

    # Location <--> PlantChange
    location.plants_from_location = relationship(
        # "PlantChange",
        plant_change,
        primaryjoin="Location.id == foreign(PlantChange.from_location_id)",
        back_populates="from_location",
        overlaps="plants_from_location",
    )

    location.plants_to_location = relationship(
        # "PlantChange",
        plant_change,
        primaryjoin="Location.id == foreign(PlantChange.to_location_id)",
        back_populates="to_location",
        overlaps="plants_to_location",
    )

    # Plant <--> PlantChange (with ambiguity)

    plant.changes: "PlantChange" = relationship(  # type: ignore[assignment]
        # "PlantChange",
        plant_change,
        back_populates="plant",
        cascade="all, delete-orphan",
        single_parent=True,
        overlaps="plant,changes",
        foreign_keys=lambda pc=plant_change: [pc.plant_id],
    )

    plant.branches: "PlantChange" = relationship(  # type: ignore[assignment]
        # "PlantChange",
        plant_change,
        back_populates="parent_plant",
        cascade="delete, delete-orphan",
        single_parent=True,
        overlaps="parent_plant,branches",
        foreign_keys=lambda pc=plant_change: [pc.parent_plant_id],
    )

    plant_change.plant: "Plant" = relationship(  # type: ignore[assignment]
        # "Plant",
        plant,
        foreign_keys=lambda pc=plant_change: [pc.plant_id],
        back_populates="changes",
        uselist=False,
        cascade="all, delete-orphan",
        single_parent=True,
        overlaps="changes",
    )

    plant_change.parent_plant: "Plant" = relationship(  # type: ignore[assignment]
        # "Plant",
        plant,
        foreign_keys=lambda pc=plant_change: [pc.parent_plant_id],
        back_populates="branches",
        uselist=False,
        cascade="delete, delete-orphan",
        single_parent=True,
        overlaps="branches",
        active_history=True,
    )

    plant_change.from_location: "Location" = relationship(  # type: ignore[assignment]
        # "Location",
        location,
        foreign_keys=lambda pc=plant_change: [pc.from_location_id],
        # primaryjoin="PlantChange.from_location_id == foreign(Location.id)",
        uselist=False,  # One-to-one relationship with Location
        active_history=True,
        overlaps="from_location",
        back_populates="plants_from_location",
    )

    plant_change.to_location: "Location" = relationship(  # type: ignore[assignment]
        # "Location",
        location,
        foreign_keys=lambda pc=plant_change: [pc.to_location_id],
        uselist=False,  # One-to-one relationship with Location
        active_history=True,
        overlaps="to_location",
        back_populates="plants_to_location",
    )


def define_propagation_relationships(
    plant: "Plant", propagation: "Propagation", plant_propagation: "PlantPropagation"
):

    plant.propagations: "Propagation" = relationship(  # type: ignore[assignment]
        # "Propagation",
        propagation,
        secondary=plant_propagation,
        back_populates="plants",
        cascade="all, delete-orphan",
        single_parent=True,
    )

    propagation.plants: List["Plant"] = relationship(  # type: ignore[assignment]
        # "Plant",
        plant,
        secondary=plant_propagation,
        back_populates="propagations",
        cascade="all, delete-orphan",
        single_parent=True,
    )


def setup_all_relationships():
    from .accession import Accession
    from .association_tables import PlantPropagation
    from .location import Location
    from .plant import Plant
    from .plant_change import PlantChange
    from .propagation import Propagation
    from .source import Source
    from .verification import Verification
    from .voucher import Voucher

    define_accession_plant_relationships(Accession, Plant)
    define_accession_related_relationships(Accession, Source, Verification, Voucher)
    define_location_relationships(Plant, Location, PlantChange)
    define_propagation_relationships(Plant, Propagation, PlantPropagation)
