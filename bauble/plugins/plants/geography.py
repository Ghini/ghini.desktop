#
# Copyright 2008-2010 Brett Adams
# Copyright 2012-2015 Mario Frasca <mario@anche.no>.
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
# geography.py
#
from operator import itemgetter
from typing import Any, Optional

from bauble.db import Base, Session
from bauble.gtkinit import Gtk
from sqlalchemy import ForeignKey, Integer, String, Unicode, select
from sqlalchemy.orm import Mapped, mapped_column, object_session, relationship


def get_species_in_geographic_area(geo):
    """
    Return all the Species that have distribution in geo
    """
    session = object_session(geo)
    if not session:
        ValueError(
            "get_species_in_geographic_area(): geographic_area is not in a session"
        )

    # get all the geographic_area children under geo
    from bauble.plugins.plants.species_model import Species, SpeciesDistribution

    # get the children of geo
    geo_table = geo.__table__
    master_ids = {geo.id}
    # populate master_ids with all the geographic_area ids that represent
    # the children of particular geographic_area id

    def get_geographic_area_children(parent_id):
        """
        Recursively retrieve the children geographic areas of a given parent.

        Args:
            parent_id (int): The ID of the parent geographic area.

        Returns:
            list: A list of IDs representing the children geographic areas.
        """
        stmt = select(geo_table.c.id).where(geo_table.c.parent_id == parent_id)

        kids = [row[0] for row in session.execute(stmt).all()]
        for kid in kids:
            # Recursively fetch the children of the current child
            grand_kids = get_geographic_area_children(kid)
            master_ids.update(grand_kids)

        return kids

    geokids = get_geographic_area_children(geo.id)
    master_ids.update(geokids)
    from sqlalchemy import bindparam

    q = (
        session.execute(
            select(Species)
            .join(SpeciesDistribution)
            .where(
                SpeciesDistribution.geographic_area_id.in_(
                    bindparam("master_ids", expanding=True)
                )
            )
            .params(master_ids=master_ids)
        )
    ).scalars()
    return list(q)


class GeographicAreaMenu:
    menu: Any

    def __init__(self, callback) -> None:
        # Create an instance of Gtk.Menu instead of subclassing it
        self.menu = Gtk.Menu()
        geographic_area_table = GeographicArea.__table__

        # Query the database for the geographic area information
        geos = (
            Session.execute(
                select(
                    geographic_area_table.c.id,
                    geographic_area_table.c.name,
                    geographic_area_table.c.parent_id,
                )
            )
            .mappings()
            .all()
        )
        geos_hash = {}
        for row in geos:
            geo_id = row["id"]
            name = row["name"]
            parent_id = row["parent_id"]  # None for roots
            geos_hash.setdefault(parent_id, []).append((geo_id, name))

        # Sort each list of children by name
        for kids in geos_hash.values():
            kids.sort(key=itemgetter(1))  # sort by name

        def get_kids(pid):
            try:
                return geos_hash.get(pid, [])
            except KeyError:
                return []

        def has_kids(pid):
            try:
                return len(geos_hash.get(pid, [])) > 0
            except KeyError:
                return False

        def build_menu(geo_id, name):
            item = Gtk.MenuItem(name)
            if not has_kids(geo_id):
                item.connect("activate", callback, geo_id)
                return item

            submenu = Gtk.Menu()
            kids = get_kids(geo_id)

            for kid_id, kid_name in kids:
                submenu.append(build_menu(kid_id, kid_name))

            sel_item = Gtk.MenuItem(name)
            submenu.insert(sel_item, 0)
            submenu.insert(Gtk.SeparatorMenuItem(), 1)
            sel_item.connect("activate", callback, geo_id)
            item.set_submenu(submenu)

            return item

        def populate():
            """
            Add geographic_area values to the menu. Any top-level items that don't
            have any kids are appended to the bottom of the menu.
            """
            if not geos_hash:
                return

            no_kids = []
            # ✅ Guard against missing None key
            for geo_id, geo_name in geos_hash.get(None, []):
                if not has_kids(geo_id):
                    no_kids.append((geo_id, geo_name))
                else:
                    self.menu.append(build_menu(geo_id, geo_name))

            for geo_id, geo_name in sorted(no_kids, key=itemgetter(1)):
                self.menu.append(build_menu(geo_id, geo_name))

            self.menu.show_all()

        from bauble.gtkinit import GLib

        GLib.idle_add(populate)

    def get_menu(self):
        return self.menu


class GeographicArea(Base):
    """
    Represents a geographic_area unit.

    :Table name: geographic_area

    :Columns:
        *name*:

        *tdwg_code*:

        *iso_code*:

        *parent_id*:

    :Properties:
        *children*:

    :Constraints:
    """

    id: Any
    __tablename__: str = "geographic_area"

    # columns
    id : Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    tdwg_code: Mapped[str] = mapped_column(String(6))
    iso_code: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("geographic_area.id"),
        nullable=True,          # ← allow NULL for roots
    )
    def __str__(self) -> str:
        return self.name


# late bindings
GeographicArea.children = relationship(
    "GeographicArea",
    primaryjoin=GeographicArea.parent_id == GeographicArea.id,
    cascade="all",
    back_populates="parent",
    order_by=[GeographicArea.name],
)

GeographicArea.parent = relationship(
    "GeographicArea",
    back_populates="children",
    remote_side=[GeographicArea.__table__.c.id],
)
