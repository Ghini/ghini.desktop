# bauble/plugins/garden/models/__init__.py


from .accession import (
    Accession,
    AccessionNote,
    accession_type_to_plant_material,
    cultivated_prov_status_values,
    decimal_to_dms,
    dms_to_decimal,
    get_species_instance,
    latitude_to_dms,
    longitude_to_dms,
    prov_type_values,
    purchase_prov_status_values,
    recvd_type_values,
    wild_prov_status_values,
)
from .contact import Contact, ContactNote
from .location import Location, LocationNote
from .plant import Plant, PlantNote, PlantSearch
from .plant_change import PlantChange
from .propagation import (
    Propagation,
    PropagationNote,
    PropCutting,
    PropCuttingRooted,
    PropSeed,
)
from .source import Collection, Source
from .verification import Verification
from .voucher import Voucher

__all__ = [
    "Accession",
    "AccessionNote",
    "accession_type_to_plant_material",
    "cultivated_prov_status_values",
    "decimal_to_dms",
    "dms_to_decimal",
    "get_species_instance",
    "latitude_to_dms",
    "longitude_to_dms",
    "prov_type_values",
    "purchase_prov_status_values",
    "recvd_type_values",
    "wild_prov_status_values",
    "Contact",
    "ContactNote",
    "Location",
    "LocationNote",
    "Plant",
    "PlantNote",
    "PlantChange",
    "PlantSearch",
    "Source",
    "Collection",
    "Verification",
    "Voucher",
]


# IMPORTANT: do NOT wire relationships here.
# Provide an explicit helper instead; call it from app startup.
def wire_relationships():
    from .relationships import setup_all_relationships

    setup_all_relationships()
