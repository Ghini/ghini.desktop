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
from gettext import gettext as _
from typing import Any

prop_type_values: Any = {
    "Seed": _("Seed"),
    "UnrootedCutting": _("Unrooted cutting"),
    "Unknown": _("Unknown"),  
}

prop_type_results: Any = {
    "Seed": "SEDL",
    "UnrootedCutting": "RCUT",
}

cutting_type_values: Any = {
    "Nodal": _("Nodal"),
    "InterNodal": _("Internodal"),
    "Other": _("Other"),
}

tip_values: Any = {
    "Intact": _("Intact"),
    "Removed": _("Removed"),
    "None": _("None"),
    None: "",
}

leaves_values: Any = {
    "Intact": _("Intact"),
    "Removed": _("Removed"),
    "None": _("None"),
    None: "",
}

flower_buds_values: Any = {"Removed": _("Removed"), "None": _("None"), None: ""}

wound_values: Any = {
    "No": _("No"),
    "Single": _("Singled"),
    "Double": _("Double"),
    "Slice": _("Slice"),
    None: "",
}

hormone_values: Any = {"Liquid": _("Liquid"), "Powder": _("Powder"), "No": _("No")}

bottom_heat_unit_values: Any = {"F": _("°F"), "C": _("°C"), None: ""}

length_unit_values: Any = {"mm": _("mm"), "cm": _("cm"), "in": _("in"), None: ""}


# TODO: some of these reasons are specific to UBC and could probably be culled.
change_reasons: Any = {
    "DEAD": _("Dead"),
    "DISC": _("Discarded"),
    "DISW": _("Discarded, weedy"),
    "LOST": _("Lost, whereabouts unknown"),
    "STOL": _("Stolen"),
    "WINK": _("Winter kill"),
    "ERRO": _("Error correction"),
    "DIST": _("Distributed elsewhere"),
    "DELE": _("Deleted, yr. dead. unknown"),
    "ASS#": _("Transferred to another acc.no."),
    "FOGS": _("Given to FOGs to sell"),
    "PLOP": _("Area transf. to Plant Ops."),
    "BA40": _("Given to Back 40 (FOGs)"),
    "TOTM": _("Transfered to Totem Field"),
    "SUMK": _("Summer Kill"),
    "DNGM": _("Did not germinate"),
    "DISN": _("Discarded seedling in nursery"),
    "GIVE": _("Given away (specify person)"),
    "OTHR": _("Other"),
    None: "",
}


# TODO: should sex be recorded at the species, accession or plant
# level or just as part of a check since sex can change in some species
sex_values: Any = {"Female": _("Female"), "Male": _("Male"), "Both": ""}

acc_type_values: Any = {
    "Plant": _("Planting"),
    "Seed": _("Seed/Spore"),
    "Vegetative": _("Vegetative Part"),
    "Tissue": _("Tissue Culture"),
    "Other": _("Other"),
    None: "",
}
