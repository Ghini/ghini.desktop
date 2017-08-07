# -*- coding: utf-8 -*-
#
# Copyright 2017 Mario Frasca <mario@anche.no>.
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

import logging
logger = logging.getLogger(__name__)

from bauble.plugins.garden.plant import Plant
from bauble.plugins.garden.accession import Accession

from bauble import db
from bauble import pluginmgr
from bauble.i18n import _


def create_pocket(filename):
    create_sql = ['''\
CREATE TABLE "android_metadata" (
	"locale"	TEXT DEFAULT 'en_US'
);''', '''\
INSERT INTO "android_metadata" VALUES('en_US');''', '''\
CREATE TABLE "species" (
	"_id"	INTEGER,
	"family"	TEXT,
	"genus"	TEXT,
	"epithet"	TEXT,
	"sub-rank"	TEXT,
	"sub-epithet"	TEXT,
	"author"	TEXT,
	PRIMARY KEY(_id)
);''', '''\
CREATE TABLE "accession" (
	"_id"	INTEGER,
	"code"	TEXT,
	"species_id"	INTEGER,
	"source"	TEXT,
	PRIMARY KEY(_id)
);''', '''\
CREATE TABLE "plant" (
	"_id"	INTEGER,
	"accession_id"	INTEGER,
	"code"	TEXT
);''','''\
''']
    import sqlite3
    cn = sqlite3.connect(filename)
    cr = cn.cursor()
    for statement in create_sql:
        cr.execute(statement)
    cn.commit()

def export_to_pocket(filename, include_private=True):
    from bauble.plugins.plants import Species
    session = db.Session()
    plant_query = (session.query(Plant)
                   .order_by(Plant.code)
                   .join(Accession)
                   .order_by(Plant.id))
    if include_private is False:
        plant_query = (plant_query
                       .filter(Accession.private == False))  # `is` does not work
    plants = plant_query.all()
    accessions = (session.query(Accession)
                  .filter(Accession.id.in_([j.accession_id for j in plants]))
                  .order_by(Accession.id).all())
    species = (session.query(Species).
               filter(Species.id.in_([j.species_id for j in accessions]))
               .order_by(Species.id).all())
    import sqlite3
    cn = sqlite3.connect(filename)
    cr = cn.cursor()
    for s in species:
        try:
            cr.execute('INSERT INTO "species" '
                   '(_id, family, genus, epithet, "sub-rank", "sub-epithet", author) '
                   'VALUES (?, ?, ?, ?, ?, ?, ?);',
                   (s.id, s.genus.family.epithet, s.genus.epithet, s.epithet,
                    s.infraspecific_rank, s.infraspecific_epithet,
                    s.infraspecific_author or s.sp_author or ''))
        except Exception, e:
            print type(e), e, s.id
    for a in accessions:
        try:
            cr.execute('INSERT INTO "accession" '
                   '(_id, code, species_id, source) '
                   'VALUES (?, ?, ?, ?);',
                   (a.id, a.code, a.species_id, ''))
        except Exception, e:
            print type(e), e, a.id
    for p in plants:
        try:
            cr.execute('INSERT INTO "plant" '
                   '(_id, accession_id, code) '
                   'VALUES (?, ?, ?);',
                   (p.id, p.accession_id, "." + p.code))
        except Exception, e:
            print type(e), e, p.id
    cn.commit()
    session.close()
    return True


class ExportToPocketTool(pluginmgr.Tool):
    category = _('Export')
    label = _('to ghini.pocket')

    @classmethod
    def start(self):
        pocket = '/tmp/pocket.db'
        create_pocket(pocket)
        export_to_pocket(pocket)
