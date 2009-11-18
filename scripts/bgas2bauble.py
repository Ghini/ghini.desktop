#!/usr/bin/env python

import collections
import copy
import csv
import logging
import itertools
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

from bauble.plugins.plants import Family, Genus, Species, SpeciesNote, Habit, \
    Color, VernacularName
from bauble.plugins.garden import Accession, Plant, Location

family_table = Family.__table__
genus_table = Genus.__table__
species_table = Species.__table__
species_note_table = SpeciesNote.__table__
acc_table = Accession.__table__
location_table = Location.__table__
plant_table = Plant.__table__

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
    Return a dictionary that maps to the columns on a species table.
    This function will only use the parts of the record that make up
    the species name and will not use other misc. field like HABIT,
    FLCOLOR, etc.

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

    authors = [None, None, None, None]
    if 'AUTHORS' in rec.dbf.fieldNames and rec['authors']:
        # the bars in the author string delineate the authors for the
        # different epithet ranks
        #
        # TODO: should we do some sort of smart capitalization here
        clean = lambda a: None if a in ('', ' ') else a
        authors = map(clean, utils.utf8(rec['authors']).split('|'))
    row['sp_author'] = authors[0]
    try:
        # not all species records have the same amount of author so we
        # set as many as we can
        row['infrasp1_author'] = authors[1]
        row['infrasp2_author'] = authors[2]
        row['infrasp3_author'] = authors[3]
    except IndexError:
        pass

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
    # SCINAME.DBF field
    #
    # Fields that have an almost direct translation from BGAS to Bauble
    # ----------------------------------------------------------------
    # ig: generic hybrid symbo
    # genus:
    # is: species hybrid symbol
    # species
    # rank: infraspecific rank
    # infrepi: infraspecific epithet
    # cultivar: cultivar name but can also include second rank and epithet
    # habit:
    # comname: vernacular name
    #
    # flcolor: is freetext in BGAS but could probably just put 2 fields
    #
    # Random field that could be put in notes
    # ---------------------------------------
    # scinote:
    # phenol: added as a SpeciesNote with category "Phenological"
    #
    # Fields that can be freetext string columns
    # ------------------------------------------
    # reference:
    # awards:
    # cultpare:
    # hardzone:
    # nativity: (like jesus?) -- maybe label distribution
    # natbc: text field of where it grows naturally in British Columbia
    #
    # fields to nix:
    # authcheck


    # TODO: would probably be faster to bulk insert all the species
    # and then retrieve all the species ids for the other
    # objects...could have some sort of map of
    # {species_namedtuple: [notes, vernames, etc]
    status('converting SCINAME.DBF ...')
    genus_insert = get_insert(genus_table, ['genus', 'family_id'])
    species_defaults = get_defaults(species_table)
    genus_defaults = get_defaults(genus_table)

    no_genus_ctr = 0 # num of records with not genus
    rec_ctr = 0 # num of records
    commit_ctr = 0 # num of rows commited

    session = sessionmaker(autocommit=True)()

    # create a map of habits ids to habit codes
    habits = {}
    for habit in session.query(Habit):
        habits[habit.code] = habit.id

    # create a map of color ids to color codes
    colors = {}
    for color in session.query(Color):
        colors[color.code] = color.id

    species_rows = collections.deque()
    dbf = open_dbf('SCINAME.DBF')
    for rec in dbf:
        rec_ctr += 1
        genus = str('%s %s' % (rec['ig'], rec['genus'])).strip()
        genus_id = None
        if not genus:
            # no genus for the species record so use the catch-all
            # unknown genus
            no_genus_ctr += 1
            genus_id = unknown_genus_id
        else:
            # search for the genus id by name
            genus_id = get_column_value(genus_table.c.id,
                                        genus_table.c.genus == genus)
            if not genus_id:
                #  couldn't find the full genus name so add it. first
                #  search for just the genus name without the hybrid
                #  string and if it's found then add the new genus to
                #  the same family as the one without the hybrid
                #  string
                warning('adding genus %s from sciname.dbf.' % genus)
                family_id = get_column_value(genus_table.c.family_id,
                                         genus_table.c.genus == rec['genus'])
                if not family_id:
                    warning('** %s has no family. adding to %s' \
                                % (genus, unknown_family_name))
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
        row = species_obj_from_rec(rec, defaults=defaults)
        species_rows.append(row)

        # set the genus on the new row
        row.genus = session.query(Genus).get(genus_id)

        # set the habit
        row.habit_id = None
        try:
            row.habit_id = habits[rec['HABIT']]
        except KeyError, e:
            # make sure we only get here because the habit is empty
            if rec['HABIT'] not in ('', ' '):
                raise

        # # TODO: flower color can have -,>& delimiters....what should
        # # we do, create two flower colors for a species????
        row.flower_color_id = None
        try:
            row.flower_color_id = colors[rec['FLCOLOR']]
        except KeyError, e:
            #print e
            pass

        if rec['comname']:
            names = rec['comname'].split(',')
            names = [VernacularName(name=utils.utf8(name.strip()),
                                    language=u'English') \
                         for name in rec['comname'].split(',')]
            # TODO: can you set the names list to the vernacular names
            # property directly
            row.vernacular_names.extend(names)
            row.default_vernacular_name = names[0]

        if rec['scinote']:
            note = SpeciesNote()
            note.note = utils.utf8(rec['scinote'])
            note.category = u'BGAS'
            note.date = '1/1/1900'
            note.species = row

        if rec['phenol']:
            note = SpeciesNote()
            note.note = utils.utf8(rec['scinote'])
            note.category = u'Phenological'
            note.date = '1/1/1900'
            note.species = row

        if (rec_ctr % 200) == 0:
            # collect periodically so we don't run out of memory
            session.begin()
            session.add_all(species_rows)
            session.commit()
            commit_ctr += len(species_rows)
            session.expunge_all()
            species_rows.clear()
            gc.collect()

    session.begin()
    session.add_all(species_rows)
    session.commit()
    commit_ctr += len(species_rows)
    species_rows.clear()
    session.close()
    gc.collect()

    info('inserted %s species in %s records' % (commit_ctr, len(dbf)))
    if commit_ctr != len(dbf):
        raise ValueError

    warning('** %s sciname entries with no genus.  Added to the genus %s' \
                % (no_genus_ctr, unknown_genus_name))
    dbf.close()
    del dbf


def get_species(rec, defaults=None):
    """
    Try to determine the species id of a record.

    WARNING: If a genus is found in the rec and does not exist then it
    is inserted.

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

    # TODO: i don't like that this function inserts genera
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
    species_defaults.update(dict(genus_id=None, sp=None, sp2=None,
                                 infrasp1=None, infrasp1_rank=None,
                                 infrasp2=None, infrasp2_rank=None))
    delayed_species = collections.deque()
    delayed_accessions = collections.deque()
    acc_rows = collections.deque()

    # TODO: what if the data differs but the accession code is the
    # same...does this ever happen in practice
    added_codes = set()
    plants = set()

    rec_ctr = 0
    for rec in dbf:
        rec_ctr += 1
        if (rec_ctr % 200) == 0:
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
            delayed_species.append(species) # to bulk insert() later
            delayed_accessions.append((species, row))

    if options.verbosity > 1:
        print ''

    gc.collect()

    # TODO: could inserting all the delayed species cause problems
    # if species with duplicate names are inserted then we won't know
    # which one to get for the species_id of the accession
    debug('  populating delayed species...')
    conn = db.engine.connect()
    trans = conn.begin()
    species_insert = get_insert(species_table, species_defaults.keys())
    conn.execute(species_insert, *delayed_species)
    info('inserted %s species from plants.dbf' % len(delayed_species))
    trans.commit()
    conn.close()

    gc.collect()

    # set species id on the rows that we couldn't get earlier
    rec_ctr = 0
    debug('  populating delayed accessions...')
    for species, acc in delayed_accessions:
        rec_ctr += 1
        if (rec_ctr % 200) == 0:
            # collect periodically so we don't run out of memory
            gc.collect()

        # get the species id now that all the species have been inserted
        conditions = []
        for col, val in species.iteritems():
            if col not in ('_last_updated', '_created', 'id'):
                conditions.append(species_table.c[col]==val)
        sql = select([species_table.c.id], and_(*conditions))
        result = db.engine.execute(sql).fetchone()
        acc['species_id'] = result[0]
        result.close()
        acc_rows.append(acc)
        del species
    del delayed_accessions

    gc.collect()

    # insert the accessions
    debug('  insert %s accessions...' % len(acc_rows))
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
    values = collections.deque()
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



def do_synonym():
    """
    """
    status('converting SYNONYM.DBF ...')
    dbf = open_dbf('SYNONYM.DBF')


def do_habit():
    """
    Convert the HABIT.DBF table to bauble.plugins.plants.species_model.Habit
    """
    status('converting HABIT.DBF ...')
    habit_table = Habit.__table__
    defaults = get_defaults(habit_table)
    dbf = open_dbf('HABIT.DBF')
    habit_rows = []
    for rec in dbf:
        row = defaults.copy()
        row.update({'name': utils.utf8(rec['habdescr']),
                    'code': utils.utf8(rec['habit'])})
        habit_rows.append(row)
        del rec
    dbf.close()

    conn = db.engine.connect()
    trans = conn.begin()
    insert = get_insert(habit_table, ['name', 'code'])
    conn.execute(insert, *habit_rows)
    trans.commit()
    conn.close()
    info('inserted %s habits.' % len(habit_rows))


def do_color():
    """
    Convert the COLOR.DBF table to bauble.plugins.plants.species_model.Color
    """
    status('converting COLOUR.DBF ...')
    color_table = Color.__table__
    defaults = get_defaults(color_table)
    dbf = open_dbf('COLOUR.DBF')
    color_rows = []
    for rec in dbf:
        row = defaults.copy()
        row.update({'name': utils.utf8(rec['coldescr']),
                    'code': utils.utf8(rec['colour'])})
        color_rows.append(row)
        del rec
    dbf.close()

    conn = db.engine.connect()
    trans = conn.begin()
    insert = get_insert(color_table, ['name', 'code'])
    conn.execute(insert, *color_rows)
    trans.commit()
    conn.close()
    info('inserted %s colors.' % len(color_rows))



stages = {'0': do_family,
          '1': do_habit,
          '2': do_color,
          '3': do_sciname,
          '4': do_bedtable,
          '5': do_plants,
          '6': do_synonym}

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

def chunk(iterable, n):
    '''
    return iterable in chunks of size n
    '''
    # TODO: this could probably be implemented way more efficiently,
    # maybe using itertools
    chunk = collections.deque()
    ctr = 0
    for it in iterable:
        chunk.append(it)
        ctr += 1
        if ctr >= n:
            yield chunk
            chunk = collections.deque()
            ctr = 0


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

