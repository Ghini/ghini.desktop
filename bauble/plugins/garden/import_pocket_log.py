#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2016-2018 Mario Frasca <mario@anche.no>.
# Copyright 2017 Jardín Botánico de Quito
# Copyright 2018 Tanager Botanical Garden <tanagertourism@gmail.com>
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
# Data from the ghini.pocket log is written to the session, inconditionally.
#

import logging
logger = logging.getLogger(__name__)

import os.path

from dateutil.parser import parse
from bauble import db
from bauble.plugins.garden import Location, Plant, PlantNote, Accession, Verification
from bauble.plugins.plants import Species, Genus, Family


def lookup(session, klass, **kwargs):
    obj = session.query(klass).filter_by(**kwargs).first()
    if obj is None:
        obj = klass(**kwargs)
        session.add(obj)
        session.flush()
    return obj


def heuristic_split(full_plant_code):
    try:
        accession_code, plant_code = full_plant_code.rsplit('.', 1)
        if plant_code[0] == '0':
            raise ValueError('plant code does not start with a 0')
        if len(accession_code) < 6:
            raise ValueError('seems there was no plant code after all')
    except:
        accession_code, plant_code = full_plant_code, '1'
    return accession_code, plant_code


def process_inventory_line(session, baseline, timestamp, parameters):
    location_code, full_plant_code, imei = parameters
    if not full_plant_code:
        # what should we do…
        return
    accession_code, plant_code = heuristic_split(full_plant_code)
    location = lookup(session, Location, code=(location_code or 'default'))

    # if plant is in place, edit it, otherwise, create it.
    plant = session.query(Plant).filter_by(code=plant_code).join(Accession).filter_by(code=accession_code).first()
    if plant is not None:
        # no location_code means just asserting existence, on existing plant, so no effect.
        if location_code:
            plant.location = location
    else:
        # if not even accession is in place, let's create a default one
        accession = session.query(Accession).filter_by(code=accession_code).first()
        if accession is None:
            fictive_family = lookup(session, Family, epithet='Zz-Plantae')
            fictive_genus = lookup(session, Genus, family=fictive_family, epithet='Zzd-Plantae')
            fictive_species = lookup(session, Species, genus=fictive_genus, infrasp1='sp')
            accession = lookup(session, Accession, code=accession_code, species=fictive_species)
        plant = lookup(session, Plant, code=plant_code, accession=accession, quantity=1, location=location)

    # even if location is none, still we have seen the plant today, so we make a note of it
    date_str = str(timestamp.date())
    lookup(session, PlantNote, plant=plant, category='inventory', date=timestamp, note=date_str)


def process_pending_edit_line(session, baseline, timestamp, parameters):
    full_plant_code, scientific_name, quantity, coordinates, pictures = parameters[:5], parameters[5:]
    if not full_plant_code:
        # what should we do…
        return

    quantity = int(quantity or '1')

    # does the accession code actually indicate a specific plant within the accession?
    accession_code, plant_code = heuristic_split(full_plant_code)

    fictive_family = lookup(session, Family, epithet='Zz-Plantae')
    fictive_genus = lookup(session, Genus, family=fictive_family, epithet='Zzd-Plantae')
    fictive_species = lookup(session, Species, genus=fictive_genus, infrasp1='sp')

    # how long is the species indication?
    epithets = [i for i in scientific_name.split(' ') if i]
    if len(epithets) == 0:
        # no identification whatsoever
        species = fictive_species
    elif len(epithets) == 1:
        # identified to rank genus, which must exist
        genus = lookup(session, Genus, epithet=epithets[0])
        species = lookup(session, Species, genus=genus, infrasp1='sp')
    elif len(epithets) >= 2:
        if len(epithets) > 2:
            logger.info("ignoring infraspecific epithets ›%s‹" % scientific_name)
        genus = lookup(session, Genus, epithet=epithets[0])
        species = lookup(session, Species, genus=genus, epithet=epithets[1])
    
    # does this plant already exist?  
    plant = session.query(Plant).filter_by(code=plant_code).join(Accession).filter_by(code=accession_code).first()
    accession = session.query(Accession).filter_by(code=accession_code).first()
    if plant is None:
        # if it does not, we have work to do …
        location = lookup(session, Location, code='default')
        if accession is None:
            accession = lookup(session, Accession, code=accession_code, species=species, quantity_recvd=quantity)
        plant = lookup(session, Plant, code=plant_code, accession=accession, location=location, quantity=quantity)
    else:
        plant.quantity=quantity

    if species != fictive_species:
        if species.epithet:
            lookup(session, Verification, date=timestamp, accession=accession, species=species,
                   verifier=db.current_user(), level=0, prev_species=accession.species)
        accession.species = species
        

    if coordinates != '(@;@)':
        # remove any previous such note
        session.query(PlantNote).filter_by(plant=plant, category='<coords>').delete()
        # add new one
        lat, lon = (float(i) for i in coordinates[1:-1].split(';'))
        value = "{lat:%0.6f,lon:%0.6f}" % (lat, lon)
        note = lookup(session, PlantNote, plant=plant, category='<coords>', note=value)

    for picture in pictures:
        basename = os.path.basename(picture)
        note = lookup(session, PlantNote, plant=plant, category='<picture>', note=basename)


def process_line(session, line, baseline):
    """process the changes in 'line'

    """
    import re
    try:
        timestamp, category, trailer = re.split(r' :(?:([A-Z_]*):) ', line)
        timestamp = parse(timestamp.replace("_", "T")+"Z")
    except:
        logger.error("some serious error in your pocket data line ›%s‹" % line)
        return None
    parameters = re.split(r' : ', trailer)
    if category == 'INVENTORY':
        process_inventory_line(session, baseline, timestamp, parameters)
    elif category == 'PENDING_EDIT':
        process_pending_edit_line(session, baseline, timestamp, parameters)
    else:
        logger.error("unhandled category in your pocket data line ›%s‹" % line)

