#!/usr/bin/env python
import copy
import csv
import logging
import os
import sys

from dbfpy import dbf
import sqlalchemy as sa
from sqlalchemy import *
from sqlalchemy.orm import *

import bauble
import bauble.prefs as prefs
import bauble.db as db
import bauble.utils as utils
import bauble.meta as meta
import bauble.pluginmgr as pluginmgr

import logging
logging.basicConfig()

from optparse import OptionParser

prefs.prefs.init()

default_uri = 'sqlite:///:memory:'

parser = OptionParser()
parser.add_option("-b", "--bgas", dest="bgas",
                  default=os.path.join(os.getcwd(), 'bgas'),
                  help="path to BGAS files", metavar="DIR")
parser.add_option("-s", "--stage", dest="stage", default='0',
                  help="stage of conversion to start at", metavar="STAGE")
parser.add_option("-t", "--test", dest="test", action="store_true",
                  default=False, help="run only tests")
parser.add_option("-p", "--problems", dest="problems", action="store_true",
                  default=False, help="print out problems with data")
parser.add_option("-d", "--database", dest="database",
                  default=default_uri, metavar="DBURI",
                  help="the database uri to store the converted databaset")
parser.add_option("-v", "--verbosity", dest="verbosity",
                  default=0, metavar="LEVEL", type="int",
                  help="the amount of information to display about the " \
                      "conversion process")
(options, args) = parser.parse_args()

def logger(msg, level):
    if level <= options.verbosity:
        print msg

status = lambda msg: logger(msg, 0)
error = lambda msg: logger('*** %s' % msg, 0)
warning = lambda msg: logger('* %s' % msg, 1)
info = lambda msg: logger(msg, 2)
debug = lambda msg: logger(msg, 3)

db.open(options.database, False)
pluginmgr.load()
# the one thing this script doesn't do that bauble does is called
# pluginmgr.init()
#pluginmgr.init(force=True)
if options.stage == '0' or options.database == default_uri:
    db.create(import_defaults=False)
    from bauble.plugins.imex.csv_ import CSVImporter

    # import default geography date
    importer = CSVImporter()
    import bauble.plugins.plants as plants
    filename = os.path.join(plants.__path__[0], 'default', 'geography.txt')
    importer.start([filename], force=True)

from bauble.plugins.plants import Family, Genus, Species, SpeciesNote
from bauble.plugins.garden import Accession, Plant, Location

family_table = Family.__table__
genus_table = Genus.__table__
species_table = Species.__table__
species_note_table = SpeciesNote.__table__
acc_table = Accession.__table__
location_table = Location.__table__
plant_table = Plant.__table__

session = bauble.Session()

src = os.path.join(os.getcwd(), 'dump')
dst = os.path.join(os.getcwd(), 'bauble')

if not os.path.exists(dst):
    os.makedirs(dst)

# TODO: this script needs to be very thoroughly tested

# BGAS tables: bedtable colour dummy family geocode habit hereitis
# plants rcvdas remocode removal removals sciname source subset
# synonym transfer

# BGAS data problems:
#
# 7. Do the removed codes need to be in their own table or can they
# just be an enum column..if you need to add new removed codes then it
# would probably be best to have their own table...is they need their
# own table then we can probably drop the codes and just use the
# descriptions
#
# 8 Do the colors need their own table...if you need to add new colors
# then yes, in that case we can probably just drop the codes and just
# use the descriptions
#
# 9. what should we do with the source.dbf table, are they donations
# or would source be something different and we need to add then to
# bauble, maybe the donations table should be changed to something
# more general, some are persons others are institutions
#
# 10. The beds in BGAS are laid out hierachially?  Does this work well
# for you or could you just use names like "Alpine Garden - Europe",
# "Alpine Garden - Bulb Frame".  Right now there are 296 "beds" in the
# bed table which would make a long list to choose from.  Although at
# the moment in Bauble if you typed in Alpine it would show all beds
# that matched the name Alpine and you would just have to choose a
# name from that shortened list. I could make it hiearchial but it is
# a little more invasive into the way Bauble does things now.

# TODO: we either need to patch dbfpy to not use so much memory or
# dump the date to CSV first before importing it to dbf, or maybe do
# each of the steps in different processes so that the previous
# processes' memory gets freed...a script like:
# python "from scripts import bgas2bauble ; bgas2bauble.do_family()"

open_dbf = lambda f: dbf.Dbf(os.path.join(options.bgas, f), readOnly=True)

def set_defaults(obj, defaults):
    """
    Set the default values for attributes on an object.

    Arguments:
    - `obj`:
    - `defaults`: a dictionary of default values
    """
    for column, val in defaults.iteritems():
        setattr(obj, column, val)
    # for column in table.c:
    #     if isinstance(column.default, ColumnDefault):
    #         defaults[column.name] = column.default.execute()


def get_defaults(table):
    """
    Return a dictionary of precomputed column defaults on a table.

    Arguments:
    - `table`:
    """
    defaults = {}
    for column in table.c:
        if isinstance(column.default, ColumnDefault):
            defaults[column.name] = column.default.execute()
    defaults['_created'] = _created
    defaults['_last_updated'] = _last_updated
    return defaults


def get_insert(table, columns):
    """
    Return an insert statement for table with column for the column keys.
    """
    defaults = get_defaults(table)
    # just to be safe make sure the table has all the columns
    for c in columns:
        assert c in table.c, '%s not a column on table %s' % (c, table.name)
    column_keys = list(set(columns).union(defaults.keys()))
    insert = table.insert().compile(column_keys=column_keys)
    return insert


def get_column_value(column, where):
    """
    Return the value of a column in the database.

    Arguments:
    - `colums`:
    - `where`:
    """
    result = select([column], where).execute()
    first = result.fetchone()
    result.close()
    del result
    if not first:
        return None
    val = first[0]
    first.close()
    del first
    return val


# create (unknown) family for those genera that don't have a family
unknown_family_name = u'(unknown)'
if options.stage == '0':
    family_table.insert().values(family=unknown_family_name).execute().close()
unknown_family_id = get_column_value(family_table.c.id,
                              family_table.c.family==unknown_family_name)

# create (unknown) genus for those species that don't have a genus
unknown_genus_name = u'(unknown)'
if options.stage == '0':
    genus_table.insert().values(family_id=unknown_family_id,
                                genus=unknown_genus_name).execute().close()
unknown_genus_id = get_column_value(genus_table.c.id,
                              genus_table.c.genus==unknown_genus_name)

# create (unknown) location
unknown_location_name = u'(unknown)'
unknown_location_code = u'UNK'
if options.stage == '0':
    location_table.insert().values(code=unknown_location_code,
                                  name=unknown_location_name).execute().close()
unknown_location_id = get_column_value(location_table.c.id,
                              location_table.c.code==unknown_location_code)

# precompute the _last_updated and _created columns so we don't have
# to execute the default for every insert
_last_updated = db.engine.execute(class_mapper(Family).c._last_updated.default)
_created = db.engine.execute(class_mapper(Family).c._created.default)

problem_labels = ['** have infraspecific rank but no epithet but do have a '\
                      'cultivar name',
                  '** have infraspecific rank but no epithet',
                  '** have an infraspecific epithet and cultivar but no '\
                      'infraspecific rank',
                  '** have infraspecific epithet but not rank or cultivar',

                  '']
problems = {0: [],
            1: [],
            2: [],
            3: []}


def species_dict_from_rec(rec, defaults=None):
    """
    rec: a dbf record to build the species from

    defaults: a dictionary that holds the default values for the
    species when those properties aren't available in rec.  if you do
    not want the defaults dict to be modified you should pass in a
    copy of your dict
    """
    if defaults:
        row = defaults
    else:
        row = get_defaults(species_table)

    #print 'default: %s' % species_table_defaults
    #row['genus_id'] = rec['genus_id']

    def clean_rec(rec):
        d = rec.asDict()
        dirt = ['FLCOLOR', 'PIN', 'REFERENCE', 'HABIT',
                'SCINOTE', 'HARDZONE', 'NATIVITY', 'AWARDS', 'PHENOL',
                'AUTHCHECK', 'NATBC', 'WILDNUM', 'L_UPDATE', 'DATEACCD',
                'PRONOTES', 'PHOTO', 'DELSTAT', 'LABELS', 'MEMORIAL',
                'OPERATOR', 'VERIFIED', 'INTENDLOC2', 'INTENDLOC1',
                'QTYRCVD', 'VOUCHER', 'VERIFIED', 'WILDCOLL', 'NOTES',
                'INITLOC', 'GEOCODE', 'SOURCE', 'PISBG', 'DATERCVD']
        for key in dirt:
            try:
                d.pop(key)
            except:
                pass
        return d

    row['sp'] = utils.utf8(rec['species'])
    if rec['is']:
        row['hybrid'] = True
    else:
        row['hybrid'] = False

    if 'AUTHORS' in rec.dbf.fieldNames and rec['authors']:
        # TODO: what's with all the '|' bars in the author string
        row['sp_author'] = utils.utf8(rec['authors'].replace('|','').strip())

    # match all the combinations of rank, infrepi and cultivar
    if rec['rank'] and rec['infrepi'] and rec['cultivar']:
        row['infrasp1_rank'] = utils.utf8(rec['rank']).replace('ssp.','subsp.')
        row['infrasp1'] = utils.utf8(rec['infrepi'])
        row['infrasp2_rank'] = u'cv.'
        row['infrasp2'] = utils.utf8(rec['cultivar'])
    elif rec['rank'] and not rec['infrepi'] and rec['cultivar']:
        # has infraspecific rank but no epithet...and a cultivar...??
        # maybe in this case we should just drop the rank and add cv. cultivar
        problems[0].append(clean_rec(rec))
        row['infrasp1_rank'] = utils.utf8(rec['rank']).replace('ssp.','subsp.')
        row['infrasp1'] = u''
        row['infrasp2_rank'] = u'cv.'
        row['infrasp2'] = u''
    elif rec['rank'] and rec['infrepi'] and not rec['cultivar']:
        row['infrasp1_rank'] = utils.utf8(rec['rank']).replace('ssp.','subsp.')
        row['infrasp1'] = utils.utf8(rec['infrepi'])
    elif rec['rank'] and not rec['infrepi'] and not rec['cultivar']:
        # has infrespecific rank but no epithet...???
        problems[1].append(clean_rec(rec))
        row['infrasp1_rank'] = utils.utf8(rec['rank']).replace('ssp.','subsp.')
        row['infrasp1'] = u''
    elif not rec['rank'] and rec['infrepi'] and rec['cultivar']:
        # have an infraspecific epithet and cultivar but no
        # infraspecific rank
        # TODO: could this mean that the infrepi part is the hybrid part
        problems[2].append(clean_rec(rec))
        row['infrasp1_rank'] = u'cv.'
        row['infrasp1'] = utils.utf8(rec['cultivar'])
        if row['hybrid']:
            row['sp2'] = utils.utf8(rec['infrepi'])
        else:
            row['infrasp2_rank'] = u'var.'
            row['infrasp2'] = utils.utf8(rec['infrepi'])
    elif not rec['rank'] and rec['infrepi'] and not rec['cultivar']:
        # has infraspecific epithet but not rank or cultivar.???
        problems[3].append(clean_rec(rec))
        if row['hybrid']:
            row['sp2'] = utils.utf8(rec['infrepi'])
        else:
            # WARNING: adding this as a variety is probably wrong but
            # what else can we do
            row['infrasp1_rank'] = u'var.'
            row['infrasp1'] = utils.utf8(rec['infrepi'])
    elif not rec['rank'] and not rec['infrepi'] and rec['cultivar']:
        row['infrasp1_rank'] = u'cv.'
        row['infrasp1'] = utils.utf8(rec['cultivar'])
    elif not rec['rank'] and not rec['infrepi'] and not rec['cultivar']:
        # use all the default values
        pass
    else:
        raise ValueError("ERROR: don't know how to handle record:\n%s" % rec)

    if 'SCINOTE' in rec.dbf.fieldNames and rec['scinote']:
        row['notes'] = utils.utf8(rec['scinote'])

    return row


def species_obj_from_rec(rec, defaults):
    d = species_dict_from_rec(rec, defaults)
    sp = Species()

    if 'notes' in d:
        notes = d.pop('notes')
        note = SpeciesNote()
        note.note = notes
        note.date = '1/1/1900'
        sp.notes.append(note)

    for key, value in d.iteritems():
        #print '%s=%s' % (key, value)
        setattr(sp, key, value)
    return sp


def do_family():
    """
    Create the family and genus tables from a FAMILY.DBF file
    """
    status('converting FAMILY.DBF ...')
    dbf = open_dbf('FAMILY.DBF')
    defaults = get_defaults(family_table)
    insert = get_insert(family_table, ['family'])
    families = {}
    genera = {}

    # create the insert values for the family table and genera
    rec_ctr = 0
    for rec in dbf:
        rec_ctr += 1
        if (rec_ctr % 200) == 0:
            # collect periodically so we don't run out of memory
            gc.collect()
        family = rec['family']
        if not family in families:
            row = defaults.copy()
            row['family'] = family
            families[family] = row

        genus = rec['genus']
        if not genus in genera:
            genera[genus] =  {'family': family, 'genus': genus,
                              '_created': _created,
                              '_last_updated': _last_updated}
        else:
            # luckily there are not duplicate genera/families but
            # we'll leave this here just in case for future data
            raise ValueError('duplicate genus: %s(%s) -- %s(%s)' \
                % (genus, family, genera['genus'], genera['family']))
        del rec

    # insert the families
    conn = db.engine.connect()
    trans = conn.begin()
    conn.execute(insert, *list(families.values()))
    trans.commit()
    conn.close()
    info('inserted %s family.' % len(families))

    # get the family id's for the genepra
    genus_rows = []
    defaults = get_defaults(genus_table)
    for genus in genera.values():
        family = genus.pop('family')
        if not family:
            warning('%s has no family. adding to %s' \
                % (genus['genus'], unknown_family_name))
            #print '** no family: %s' %  genus
            genus['family_id'] = unknown_family_id
        else:
            fid = get_column_value(family_table.c.id,
                            family_table.c.family == family)
            genus['family_id'] = fid
        genus.update(defaults)
        genus_rows.append(genus)

    # insert the genus rows
    insert = get_insert(genus_table, ['genus', 'family_id'])
    conn = db.engine.connect()
    trans = conn.begin()
    conn.execute(insert, *genus_rows)
    trans.commit()
    conn.close()
    info('inserted %s genus rows out of %s records.' \
             % (len(genus_rows), len(dbf)))
    dbf.close()
    del dbf



def do_sciname():
    """
    Convert the sciname table into species and add other missing genera.

    The do_family() function should be run before this function
    """
    # ig: generic hybrid symbo
    # genus:
    # is: species hybrid symbol
    # species
    # rank: infraspecific rank
    # infrepi: infraspecific epithet
    # cultivar: cultivar name but can also include second rank and epithet
    # habit:
    # comname: vernacular name
    # nativity: (like jesus?)
    # natbc: native to BC?
    # authcheck:
    # reference:
    # awards:
    # cultpare:
    # flcolor:
    # hardzeon:
    # scinote:
    # phenol:
    status('converting SCINAME.DBF ...')
    dbf = open_dbf('SCINAME.DBF')
    # species_insert = get_insert(species_table,
    #                             ['genus_id', 'sp', 'sp2', 'hybrid',
    #                              'sp_author', 'infrasp1', 'infrasp1_rank',
    #                              'infrasp2', 'infrasp2_rank'])
    species_rows = []
    child_rows = []
    genus_insert = get_insert(genus_table, ['genus', 'family_id'])
    no_genus_ctr = 0
    species_defaults = get_defaults(species_table)
    genus_defaults = get_defaults(genus_table)
    rec_ctr = 0
    for rec in dbf:
        rec_ctr += 1
        if (rec_ctr % 500) == 0:
            # collect periodically so we don't run out of memory
            gc.collect()
        genus = str('%s %s' % (rec['ig'], rec['genus'])).strip()
        genus_id = None
        if not genus:
            no_genus_ctr += 1
            genus_id = unknown_genus_id
            #print 'no genus: %s' % rec.asDict()
        else:
            #genus_id = get_column_value(genus_table.c.id,
            #                     genus_table.c.genus == genus)
            stmt = 'select id from genus where genus=="%s";' % genus
            r = db.engine.execute(stmt).fetchone()
            if r:
                genus_id = r[0]
                r.close()
        if not genus_id:
            #family_id = get_column_value(genus_table.c.family_id,
            #                      genus_table.c.genus == rec['genus'])
            family_id = None
            stmt = 'select family_id from genus where genus=="%s";' % genus
            r = db.engine.execute(stmt).fetchone()
            if r:
                family_id = r[0]
                r.close()
            warning('adding genus %s from sciname.dbf.' % genus)
            if not family_id:
                warning('** %s has no family. adding to %s' \
                    % (genus, unknown_family_name))
                # print '** %s has no family. adding to %s' \
                #     % (genus, unknown_family_name)
                family_id = unknown_family_id
            genus_row = genus_defaults.copy()
            genus_row.update({'genus': genus, 'family_id': family_id})
            db.engine.execute(genus_insert, genus_row).close()
            genus_id = get_column_value(genus_table.c.id,
                                 genus_table.c.genus == genus)

        # TODO: check that the species name doesn't already exists,
        # can probably go ahead and import it but just give a message
        # that says something like "it appears the species already
        # exists"
        defaults = species_defaults.copy()
        defaults['genus_id'] = genus_id
        #row = species_dict_from_rec(rec, defaults=defaults)
        row = species_obj_from_rec(rec, defaults=defaults)
        # infrasp = ()
        # note = {}
        # if 'infrasp' in row:
        #     infrasp = row.pop('infrasp')

        # if 'notes' in row:
        #     note['note'] = row.pop('notes')

        # child_rows.append((row, infrasp, note))
        # #infrasp_rows.append((row, infrasp))
        # species_rows.append(row)

        # del rec

    session = bauble.Session()
    def set_genus(s):
        s.genus=session.query(Genus).get(s.genus_id)
    map(set_genus, species_rows)
    session.add_all(species_rows)
    session.commit()
    # db.engine.execute(species_insert, *species_rows).close()

    # # now that the species have been inserted get the ids for
    # # infraspecific parts and the species notes
    # infrasp_defaults = get_defaults(infrasp_table)
    # new_infrasp = []
    # new_notes = []
    # for sp, infrasp, note in child_rows:
    #     # query the row
    #     conditions = []
    #     for col, val in sp.iteritems():
    #         if col not in ('_last_updated', '_created'):
    #             conditions.append(species_table.c[col]==val)
    #     species_id = get_column_value(species_table.c.id, and_(*conditions))
    #     for i in infrasp:
    #         iid = get_column_value(infrasp_table.c.id,
    #                                and_(infrasp_table.c.species_id==species_id,
    #                                     infrasp_table.c.level == i['level']))
    #         if iid:
    #             print sp
    #             print infrasp
    #             raise ValueError
    #         i['species_id'] = species_id
    #         #print i
    #         i['_created'] = _created
    #         i['_last_updated'] = _last_updated
    #         db.engine.execute(infrasp_insert, i).close()
    #         #new_infrasp.append(i)

    #     note['species_id'] = species_id
    #     note['date'] = '1/1/1900'
    #     note['_created'] = _created
    #     note['_last_updated'] = _last_updated
    #     new_notes.append(note)

    # #db.engine.execute(infrasp_insert, *new_infrasp).close()

    # # insert the notes
    # species_note_insert = get_insert(species_note_table,
    #                                  ['species_id', 'note', 'date'])
    # db.engine.execute(species_note_insert, *new_notes).close()

    info('inserted %s species out of %s records' \
        % (len(species_rows), len(dbf)))
    warning('** %s sciname entries with no genus.  Added to the genus %s' \
                % (no_genus_ctr, unknown_genus_name))
    dbf.close()
    del dbf


def get_species(rec, defaults=None):
    """
    Try to determine the species id of a record.

    :param rec: a dbf record
    :parem defaults: the default dict to use for the species values
    """
    # TODO: this could probably become a generic function where we
    # can also pass a flag on whether to create the species if we
    # can't find them...do the same for get_family_id() and
    # get_genus_id()

    genus_id = None
    genus = None

    if not defaults:
        defaults = get_defaults(species_table)

    if 'IG' in rec:
        genus = str('%s %s' % (rec['ig'], rec['genus'])).strip()
    else:
        genus = str('%s' % rec['genus'])

    #genus = str('%s %s' % (rec['ig'], rec['genus'])).strip()

    if 'genus_id' in rec and rec['genus_id']:
        genus_id = r['genus_id']
        genus = get_column_value(genus_table.c.genus,
                                 genus_table.c.genus_id == genus_id)
    else:
        genus = str('%s %s' % (rec['ig'], rec['genus'])).strip()
        genus_id = get_column_value(genus_table.c.id,
                                    genus_table.c.genus == genus)

    if not genus_id:
        # TODO: here we're assume the genera don't have an
        # associated family but it shouldn't really matter b/c
        # there seems to be only one genus (BL.0178) in plants.dbf
        # that isn't already in the database
        info('adding genus %s from plants.dbf.' % genus)
        genus_table.insert().values(family_id=unknown_family_id,
                                    genus=genus).execute().close()
        genus_id = get_column_value(genus_table.c.id,
                             genus_table.c.genus == genus)
        warning('genus has no family: %s' % genus)

    defaults = defaults.copy()
    defaults['genus_id'] = genus_id
    row = species_dict_from_rec(rec, defaults=defaults)

    # infrasp = []
    # if 'infrasp' in row:
    #     infrasp = row.pop('infrasp')

    # sql = select([species_table.c.id],
    #              from_obj=[species_table.select().alias().join(infrasp_table)])

    # infrasp_conditions = []
    # for i in infrasp:
    #     conditions = []
    #     for col, val in i.iteritems():
    #         if col not in ('_last_updated', '_created'):
    #             conditions.append(infrasp_table.c[col]==val)
    #             #infrasp_conditions.append(infrasp_table.c[col]==val)
    #     infrasp_conditions.append(and_(*conditions))

    # if infrasp_conditions:
    #     sql = sql.where(or_(*infrasp_conditions)).apply_labels()

    if 'notes' in row:
        row.pop('notes')

    conditions = []
    for col, val in row.iteritems():
        if col not in ('_last_updated', '_created'):
            conditions.append(species_table.c[col]==val)

    sql = select([species_table.c.id], and_(*conditions))
    result = db.engine.execute(sql).fetchone()
    if result:
        row['id'] = result[0]
        result.close()
    else:
        # TODO: should the species id be set to None or just not added
        row['id'] = None

    return row


def do_plants():
    """
    BGAS Plants are what we refer to as accessions
    """
    # accno, propno, source, dateaccd, datercvd, qtyrcvd, rcvdas, ig,
    # genus, is, species, rank, infrepi, cultivar, idqual, verified,
    # othernos, iswild, wildnum, wildcoll, wildnote, geocode, voucher,
    # photo, initloc, intendloc1, intendloc2, labels, pisbg, memorial,
    # pronotes, notes, operator, l_update, delstat

    # TODO: we will have to match the species names exactly since they
    # aren't referenced to a scientific name by id or anything
    status('converting PLANTS.DBF ...')
    dbf = open_dbf('PLANTS.DBF')

    acc_insert = get_insert(acc_table,
                            ['code', 'species_id', ])
    acc_defaults = get_defaults(acc_table)
    species_defaults = get_defaults(species_table)
    delayed_species = []
    delayed_accessions = []
    #delayed_accessions = set()

    # TODO: what if the data differs but the accession code is the same
    added_codes = set()
    acc_rows = []
    acc_rows_append = lambda x: acc_rows.append(x)
    plants = set()

    rec_ctr = 0
    for rec in dbf:
        rec_ctr += 1
        if (rec_ctr % 500) == 0:
            # collect periodically so we don't run out of memory
            gc.collect()
            if options.verbosity > 1:
                sys.stdout.write('.')
                sys.stdout.flush()

        # TODO: create tags for PISBG

        # TODO: should record the name of the person who creates new
        # accession and use the operator field for old
        # accessions...of course the audit trail will also record this
        p = (unicode(rec['accno']), unicode(rec['propno']))
        if p not in plants:
            plants.add(p)
        else:
            raise ValueError('duplicate accession: %s' % p)

        if not rec['accno']:
            error('** accno is empty: %s' % rec['accno'])
            raise ValueError('** accno is empty: %s' % rec['accno'])

        if rec['accno'] not in added_codes:
            added_codes.add(rec['accno'])
        else:
            # don't add duplicates
            continue

        species = get_species(rec, species_defaults)
        row = acc_defaults.copy()
        row['code'] = unicode(rec['accno'])
        if 'id' in species and species['id']:
            row['species_id'] = species['id']
            acc_rows.append(row)
        else:
            delayed_species.append(species)
            delayed_accessions.append((rec, row))

    if options.verbosity > 1:
        print ''

    # TODO: could inserting all the delayed species cause problems
    # if species with duplicate names are inserted then we won't know
    # which one to get for the species_id of the accession
    if delayed_species:
        conn = db.engine.connect()
        trans = conn.begin()
        for species in delayed_species:
            conn.execute(species_table.insert(), species)
        #conn.execute(species_table.insert(), *delayed_species)
        info('inserted %s species from plants.dbf' % len(delayed_species))
        trans.commit()
        conn.close()

    # set species id on the rows that we couldn't get earlier
    rec_ctr = 0
    for rec, row in delayed_accessions:
        # map would be faster here than a loop but if we don't do
        # manual garbage collection then we'll run out of memory
        rec_ctr += 1
        if (rec_ctr % 200) == 0:
            # collect periodically so we don't run out of memory
            gc.collect()
        species = get_species(rec, species_defaults)
        row['species_id'] = species['id']
        acc_rows.append(row)
        del rec
    del delayed_accessions

    gc.collect()

    # insert the accessions
    conn = db.engine.connect()
    trans = conn.begin()
    conn.execute(acc_insert, *acc_rows)
    info('inserted %s accesions out of %s records' \
             % (len(acc_rows), len(dbf)))
    trans.commit()
    conn.close()

    dbf.close()
    del dbf
    # now that we have all the accessions loop through all the records
    # again and create the plants
    values = []
    plant_defaults = get_defaults(plant_table)
    row_map = {}
    rec_ctr = 0
    for acc_code, plant_code in plants:
        rec_ctr += 1
        if (rec_ctr % 500) == 0:
            # collect periodically so we don't run out of memory
            gc.collect()
        acc_id = get_column_value(acc_table.c.id,
                                  acc_table.c.code == unicode(acc_code))
        row = plant_defaults.copy()
        row['accession_id'] = acc_id
        row['code'] = unicode(plant_code)
        row['location_id'] = unknown_location_id
        # TODO: should check row doesn't already exists
        row_map[(acc_code, plant_code)] = row
        values.append(row)

    gc.collect()
    # i couldn't get plant_table.update() to ever work properly so
    # instead we just loop through the hereitis table and set the
    # values on the plant before inserting the plant rows

    # loop through the hereitis table to set the location_id
    status('converting HEREITIS.DBF ...')
    dbf = open_dbf('HEREITIS.DBF')
    rec_ctr = 0
    for rec in dbf:
        rec_ctr += 1
        if (rec_ctr % 500) == 0:
            # collect periodically so we don't run out of memory
            gc.collect()
        acc_code = unicode(rec['accno'])
        plant_code = unicode(rec['propno'])
        bedno = unicode(rec['bedno'])
        location_id = unknown_location_id
        if bedno not in ('8A', '1B49'):
            location_id = get_column_value(location_table.c.id,
                                           location_table.c.code == bedno)
        else:
            error('location does not exist for %s.%s: %s' % \
                      (acc_code, plant_code, bedno))
        row_map[(acc_code, plant_code)]['location_id'] = location_id
        del rec

    conn = db.engine.connect()
    trans = conn.begin()
    conn.execute(plant_table.insert(), *values)
    trans.commit()
    conn.close()
    status('inserted %s plants' % len(values))


def do_bedtable():
    # TODO: for the bed table it might make sense to do a "section"
    # column so the section could be, say "Alpine Garden" and the
    # specific locations could be "Australasia"...but what do we
    # really gain from this...we would also need multiple sections
    # like: Main Garden->Alpine Garden->Australasia which would
    # probably be more suitable to just giving the location table a
    # parent_id to another location....but then it gets difficult
    # getting all the plants from sections with children
    status('converting BEDTABLE.DBF ...')
    dbf = open_dbf('BEDTABLE.DBF')
    location_rows = []
    defaults = get_defaults(location_table)
    for rec in dbf:
        row = defaults.copy()
        row.update({'code': utils.utf8(rec['bedno']),
                    'name': utils.utf8(rec['beddescr'])})
        # row.update({'name': utils.utf8(rec['bedno']),
        #             'description': utils.utf8(rec['beddescr'])})
        location_rows.append(row)
        del rec
    conn = db.engine.connect()
    trans = conn.begin()
    conn.execute(location_table.insert(), *location_rows)
    trans.commit()
    conn.close()
    info('inserted %s locations out of %s records' \
             % (len(location_rows), len(dbf)))
    dbf.close()
    del dbf


def do_hereitis():
    """
    This function set the correct values of the column of the plants
    table.  The accessions and plants are created in do_plants()
    """
    # The hereitis table is roughly equivalent to the plants table
    # accno:
    #
    # propno: plant code?
    # bedno: location.site
    # alive: acc_status?
    # labels: ??
    # l_update: last updated?
    #

    # all the work from the hereitis table is not done in do_plants
    return
    status('converting HEREITIS.DBF ...')
    dbf = open_dbf('HEREITIS.DBF')
    plant_update = plant_table.update().\
    where(plant_table.c.id == bindparam('plant_id')).\
    values(location_id=bindparam('location_id'))

    conn = db.engine.connect()
    trans = conn.begin()
    for rec in dbf:
        acc_code = unicode(rec['accno'])
        plant_code = unicode(rec['propno'])
        id_query = select([plant_table.c.id],
                          and_(plant_table.c.code==plant_code,
                               acc_table.c.code==acc_code),
                          from_obj=plant_table.join(acc_table))
        r = conn.execute(id_query).fetchone()
        plant_id = r[0]
        r.close()

        # get the location id from the bedno
        bedno = unicode(rec['bedno'])
        # location_id = get_column_value(location_table.c.id,
        #                                location_table.c.code == bedno)
        location_id = unknown_location_id
        if bedno not in ('8A', '1B49'):
            location_id = get_column_value(location_table.c.id,
                                           location_table.c.code == bedno)
        else:
            error('location does not exist for %s.%s: %s' % \
                      (acc_code, plant_code, bedno))
        #     continue
        # if not location_id:
        #     error('location does not exists for %s.%s: %s' % \
        #               (acc_code, plant_code, bedno))
        #     #continue
        #     location_id=1

        #conn.execute(update(plant_table, plant_table.c.id==plant_id,
        #                    values={plant_table.c.location_id: location_id}))
        #db.engine.echo = True
        #plant_id = 4
        #debug('%s: %s' % (plant_id, location_id))

        # i could never get the plant_table.update() stuff to work, it
        # would run fine but wouldn't update the table.  the only
        # thing that really seemed different from the generated code
        # from my statement is the generated code was also trying to
        # update _last_updated so maybe this is the problem
        stmt = 'update plant set location_id=%s where id=%s;' % \
            (location_id, plant_id)
        #debug(stmt)
        #conn.execute(stmt)
        db.engine.execute(stmt)
        #plant_table.update().where(plant_table.c.id==plant_id).values(location_id=location_id).execute(bind=conn)
        #conn.execute(plant_update, plant_id=plant_id, location_id=location_id)
        del rec

    trans.commit()
    conn.close()


def do_synonym():
    """
    """
    status('converting SYNONYM.DBF ...')
    dbf = open_dbf('SYNONYM.DBF')


stages = {'0': do_family,
          '1': do_sciname,
          '2': do_bedtable,
          '3': do_plants,
          '4': do_hereitis,
          '5': do_synonym}

def run():
    for stage in range(int(options.stage), nstages):
        stages[str(stage)]()


def test():
    info('testing...')
    # test all possible combinations of imported species names
    # test for duplicate species
    # test that all accession codes are unique
    # test that all plant codes are unique
    pass


if __name__ == '__main__':
    import gc
    global current_stage
    if options.test:
        test()
    else:
        import timeit
        nstages = len(stages)
        total_seconds = 0
        nruns = 1
        for stage in range(int(options.stage), nstages):
            current_stage = stages[str(stage)]
            t = timeit.timeit('current_stage()',
                              "from __main__ import current_stage;",
                              number=nruns)
            gc.collect()
            info('... in %s seconds.' % t)
            total_seconds += t
        info('total run time: %s seconds' % total_seconds)

    if nruns < 2 and options.problems:
        for key, probs in problems.iteritems():
            print problem_labels[key]
            print '------------------------'
            for row in probs:
                print row
            print ''

