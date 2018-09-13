#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2016-2018 Mario Frasca <mario@anche.no>.
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
# Data from the ghini.pocket log is written to the session, inconditionally.
#

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

consoleHandler = logging.StreamHandler()
logging.getLogger().addHandler(consoleHandler)
consoleHandler.setLevel(logging.DEBUG)
logging.getLogger().setLevel(logging.DEBUG)

import bauble.db
import bauble.utils

from bauble.plugins.garden import Location
from bauble.plugins.garden import Plant, PlantNote
from bauble.plugins.garden import Accession
from bauble.plugins.plants import Species, Genus, Family


def get_genus(session, keys):
    try:
        keys['gn_epit'], keys['sp_epit'] = keys['species'].split(' ')
    except:
        keys['gn_epit'], keys['sp_epit'] = (u'Zzz', u'sp')

    genus = session.query(Genus).filter(Genus.epithet == keys['gn_epit']).one()
    return genus


def get_species(session, keys):
    if keys['sp_epit'] == u'sp':
        keys['infrasp1'], keys['sp_epit'] = u'sp', u''
    else:
        keys['infrasp1'] = u''

    if keys['sp_epit'] == u'':
        try:
            species = session.query(Species).filter(
                Species.genus == genus).filter(
                Species.infrasp1 == u'sp').first()
            if species != zzz:  # no hace falta mencionarlo
                sys.stdout.write('+')  # encontramos fictive species
        except:
            species = Species(genus=genus, sp=u'', infrasp1=u'sp')
            session.add(species)
            session.flush()
            sys.stdout.write('*')  # tuvimos que crear fictive species
    else:
        try:
            species = session.query(Species).filter(
                Species.genus == genus).filter(
                Species.infrasp1 == u'').filter(
                Species.epithet == keys['sp_epit']).one()
            sys.stdout.write('+')  # encontramos Species
        except:
            species = Species(genus=genus, sp=u'', epithet=keys['sp_epit'])
            session.add(species)
            session.flush()
            sys.stdout.write('*')  # tuvimos que crear Species
    return species


def lookup(session, klass, **kwargs):
    obj = session.query(klass).filter_by(**kwargs).first()
    if obj is None:
        obj = klass(**kwargs)
        session.add(obj)
        session.flush()
    return obj


def process_inventory_line(session, baseline, timestamp, parameters):
    location_code, accession_code, imei = parameters
    pass


def process_pending_edit_line(session, baseline, timestamp, parameters):
    full_plant_code, scientific_name, quantity, coordinates, *pictures = parameters

    if quantity:
        quantity = int(quantity)
    else:
        quantity = 1

    # does the accession code actually indicate a specific plant within the accession?
    accession_code, plant_code = full_plant_code.rsplit('.', 1)

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
        print(plant, accession, species)
    pass


def process_line(session, line, baseline):
    """process the changes in 'line'

    """
    import re
    try:
        timestamp, category, trailer = re.split(r' :(?:([A-Z_]*):) ', line)
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


if False:
    q = session.query(Species).filter(Species.infrasp1 == u'sp')
    q = q.join(Genus).filter(Genus.epithet == u'Zzz')
    zzz = q.one()

    import csv
    import sys

    header = ['timestamp', 'location', 'acc_code', 'imei', 'species']
    last_loc = None

    import fileinput
    for line in fileinput.input():
        sys.stdout.flush()
        obj = dict(zip(header, [i.strip() for i in unicode(line).split(':')]))
        if len(obj) < 3:
            continue  # ignore blank lines
        obj.setdefault('species', 'Zzz sp')

        if not obj['location']:
            obj['location'] = last_loc
        last_loc = obj['location']

        loc = lookup(session, Location, code=last_loc)
        genus = get_genus(session, obj)  # alters obj
        species = get_species(session, obj)

        try:
            q = session.query(Plant)
            q = q.join(Accession).filter(Accession.code == obj['acc_code'])
            q = q.filter(Plant.code == u'1')
            plant = q.one()
            if plant.location != loc:
                plant.location = loc
                sys.stdout.write(':')  # we altered a plant location
            else:
                sys.stdout.write('.')  # we confirmed a plant location
        except Exception as e:
            try:
                accession = session.query(Accession).filter(Accession.code == obj['acc_code']).one()
            except Exception as e:
                accession = Accession(species=species, code=obj['acc_code'])
                session.add(accession)
                sys.stdout.write('a')  # we added a new accession
            plant = Plant(accession=accession, location=loc, quantity=1, code=u'1')
            session.add(plant)
            session.flush()
            sys.stdout.write('p')  # we added a new plant
        # operación perro - mark the plant as seen today
        q = session.query(PlantNote)
        q = q.filter(PlantNote.plant == plant)
        q = q.filter(PlantNote.category == u'inventario')
        q = q.filter(PlantNote.note == obj['timestamp'][:8])
        if q.count() == 0:
            note = PlantNote(plant=plant, category=u'inventario', note=obj['timestamp'][:8])
            session.add(note)
            session.flush()

    print
    session.commit()
