#!/usr/bin/env python
#
# Copyright 2017 Mario Frasca <mario@anche.no>.
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

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

consoleHandler = logging.StreamHandler()
logging.getLogger().addHandler(consoleHandler)
consoleHandler.setLevel(logging.INFO)
logging.getLogger().setLevel(logging.INFO)

import os.path

path = os.path.dirname(os.path.realpath(__file__))

import json

with open(os.path.join(path, "settings.json")) as f:
    (user, pw, filename, imei2user, dburi, pic_path) = json.load(f)

import bauble.db
import bauble.utils
from bauble.plugins.garden.models import Accession, Location, Plant, PlantNote
from bauble.plugins.plants import Genus, Species
from sqlalchemy import select

bauble.db.open(dburi, True, True)
session = bauble.db.Session()

q = session.execute(
        select(Species)
        .where(Species.infrasp1 == "sp")
        .join(Genus)
        .where(Genus.epithet == "Zzz")
    ).scalars()
zzz = q.one()

loc = session.execute(
            select(Location)
            .where(Location.code == "desconocid")
            ).scalars().one()

import sys

with open("/tmp/plant-pictures.txt") as f:
    for text in f.readlines():
        text = str(text.strip())
        acc_no = text[:6]

        try:
            q = session.execute(
                    select(Plant)
                    .join(Accession)
                    .where(Accession.code == acc_no)
                    .where(Plant.code == "1")
                ).scalars()

            plant = q.one()
        except:
            try:
                accession = (
                    session.execute(
                        select(Accession)
                        .where(Accession.code == acc_no)
                    ).scalars()
                    .one()
                )
            except:
                accession = Accession(species=zzz, code=acc_no)
                session.add(accession)
                sys.stdout.write("a")
            plant = Plant(
                accession=accession, location=loc, quantity=1, code="1"
            )
            session.add(plant)
            sys.stdout.write("p")
            session.flush()

        # `plant` is the object to receive pictures, and it is in the session.

        q = session.execute(
                select(Plant)
               .join(Accession)
               .where(Accession.code == acc_no)
               .join(PlantNote)
               .where(PlantNote.category == "<picture>")
               .where(PlantNote.note == text)
            ).scalars()
        
        if q.count() == 0:
            # we need to add this note to the plant
            note = PlantNote(plant=plant, category="<picture>", note=text)
            session.add(note)
            sys.stdout.write("f")
        else:
            sys.stdout.write(".")
        sys.stdout.flush()
session.commit()
print()
