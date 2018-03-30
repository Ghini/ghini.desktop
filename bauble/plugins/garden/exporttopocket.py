# -*- coding: utf-8 -*-
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
#

import logging
logger = logging.getLogger(__name__)

from bauble.plugins.garden.plant import Plant
from bauble.plugins.garden.accession import Accession

from bauble import db
from bauble import pluginmgr


import gtk, gobject
import os


def create_pocket(filename):
    create_sql = ['''\
CREATE TABLE "android_metadata" (
 "locale"       TEXT DEFAULT 'en_US'
);
''', '''\
INSERT INTO "android_metadata" VALUES('en_US');
''', '''\
CREATE TABLE "species" (
  "_id"          INTEGER,
  "family"       TEXT,
  "genus"        TEXT,
  "epithet"      TEXT,
  "sub-rank"     TEXT,
  "sub-epithet"  TEXT,
  "author"       TEXT,
  PRIMARY KEY(_id)
);
''', '''\
CREATE TABLE "accession" (
  "_id"          INTEGER,
  "code"         TEXT,
  "species_id"   INTEGER,
  "source"       TEXT,
  "start_date"   TEXT,
  PRIMARY KEY(_id)
);
''', '''\
CREATE TABLE "plant" (
  "_id"          INTEGER,
  "accession_id" INTEGER,
  "code"         TEXT,
  "location"     TEXT,
  "end_date"     TEXT,
  "n_of_pics"    INTEGER,
  "quantity"     INTEGER,
  "edit_pending" INTEGER DEFAULT 0,
  PRIMARY KEY(_id)
);
''']
    import sqlite3
    cn = sqlite3.connect(filename)
    cr = cn.cursor()
    for statement in create_sql:
        cr.execute(statement)
    cn.commit()


def export_to_pocket(filename, include_private=True):
    from bauble.plugins.plants import Species
    from bauble import pb_set_fraction, pb_grab, pb_release
    gobject.idle_add(pb_grab)
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
    count = 1
    for i in species:
        try:
            cr.execute('INSERT INTO "species" '
                   '(_id, family, genus, epithet, "sub-rank", "sub-epithet", author) '
                   'VALUES (?, ?, ?, ?, ?, ?, ?);',
                   (i.id, i.genus.family.epithet, i.genus.epithet, i.epithet,
                    i.infraspecific_rank, i.infraspecific_epithet,
                    i.infraspecific_author or i.sp_author or ''))
        except Exception, e:
            logger.info("error exporting species %s: %s %s" % (i.id, type(e), e))
        gobject.idle_add(pb_set_fraction, 0.05 * count / len(species))
        count += 1
    count = 1
    for i in accessions:
        try:
            try:
                source_name = i.source.source_detail.name or ''
            except AttributeError:
                source_name = ''
            cr.execute('INSERT INTO "accession" '
                       '(_id, code, species_id, source, start_date) '
                       'VALUES (?, ?, ?, ?, ?);',
                       (i.id, i.code, i.species_id, source_name, i.date_accd))
        except Exception, e:
            logger.info("error exporting accession %s: %s %s" % (i.id, type(e), e))
        gobject.idle_add(pb_set_fraction, 0.05 + 0.4 * count / len(accessions))
        count += 1
    count = 1
    for i in plants:
        try:
            cr.execute('INSERT INTO "plant" '
                       '(_id, accession_id, code, location, end_date, n_of_pics, quantity) '
                       'VALUES (?, ?, ?, ?, ?, ?, ?);',
                       (i.id, i.accession_id, "." + i.code, i.location.code, i.date_of_death, len(i.pictures), i.quantity))
        except Exception, e:
            logger.info("error exporting plant %s: %s %s" % (i.id, type(e), e))
        gobject.idle_add(pb_set_fraction, 0.45 + 0.55 * count / len(plants))
        count += 1
    cn.commit()
    session.close()
    gobject.idle_add(pb_release)
    return True


class ExportToPocketTool(pluginmgr.Tool):
    category = _('Export')
    label = _('to ghini.pocket')

    @classmethod
    def start(self):
        d = gtk.FileChooserDialog(_("Choose a file to export to…"), None,
                                  gtk.FILE_CHOOSER_ACTION_SAVE,
                                  (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
                                   gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
        if d.run() == gtk.RESPONSE_ACCEPT:
            pocket = d.get_filename()
            try:
                os.unlink(pocket)
            except:
                pass
        else:
            pocket = None
        d.destroy()
        if pocket:
            create_pocket(pocket)
            from threading import Thread
            thread = Thread(target=export_to_pocket,
                            args=[pocket])
            thread.start()
