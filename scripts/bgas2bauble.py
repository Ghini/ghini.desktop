#!/usr/bin/env python

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

try:
    import psyco
    psyco.full()
except ImportError:
    pass
else:
    print 'running with psyco.'

prefs.prefs.init()

default_uri = 'sqlite:///:memory:'
granularity = 200 # per how many records we garbage collect and print a tick

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
from bauble.plugins.garden import Accession, AccessionNote, Plant, Location, \
    PlantRemoval, Contact, Source, SourceContact, Collection

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

def print_tick():
    sys.stdout.write('.')
    sys.stdout.flush()

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


def insert_rows(insert, rows):
    """
    Use the insert statment to insert rows in a transaction.
    """
    conn = db.engine.connect()
    trans = conn.begin()
    conn.execute(insert, *rows)
    trans.commit()
    conn.close()


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


def where_from_dict(table, dict_, ignore_columns):
    """
    Create a where condition for table where dict_ is column/value
    mapping and ignore_columns are the columns to ignore in dict_
    """
    cols = filter(lambda c: c not in ignore_columns, dict_.keys())
    return and_(*map(lambda col: table.c[col] == dict_[col], cols))


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

# create locations that some plants refer to but aren't in BEDTABLE.DBF
unknown_location_name = u'(unknown)'
unknown_location_code = u'UNK'
if options.stage == '0':
    location_table.insert().values(code=unknown_location_code,
                                  name=unknown_location_name).execute().close()
    location_table.insert().values(code=u'8A', name=u'8A').execute().close()
    location_table.insert().values(code=u'1B49', name=u'1B49').execute().close()
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

def has_value(rec, col):
        return col.upper() in rec.dbf.fieldNames and rec[col]


def get_value(rec, col, as_str=True):
    """
    Return a value from the rec if it exists.
    """
    if has_value(rec, col):
        if as_str:
            return utils.utf8(rec[col])
        else:
            return rec[col]
    return None


def get_max_id(table):
    """
    Use the insert statment to insert rows in a transaction.
    """
    if isinstance(table, str):
        tablename = table
    else:
        tablename = table.name
    conn = db.engine.connect()
    trans = conn.begin()
    r = conn.execute('select max(id) from %s' % tablename).fetchone()[0]
    if not r:
        r = 1
    trans.commit()
    conn.close()
    return r


def species_name_dict_from_rec(rec, defaults=None):
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
    row['genus'] = str('%s %s' % (rec['ig'], rec['genus'])).strip()

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

    row['sp'] = get_value(rec, 'species')
    row['sp2'] = None
    if rec['is']:
        row['hybrid'] = True
    else:
        row['hybrid'] = False

    row['infrasp1'] = None
    row['infrasp1_rank'] = None
    row['infrasp1_author'] = None
    row['infrasp2'] = None
    row['infrasp2_rank'] = None
    row['infrasp2_author'] = None
    row['infrasp3'] = None
    row['infrasp3_rank'] = None
    row['infrasp3_author'] = None

    authors = [None, None, None, None]
    if has_value(rec, 'authors'):
        # the bars in the author string delineate the authors for the
        # different epithet ranks
        #
        # TODO: should we do some sort of smart capitalization here
        clean = lambda a: None if a in ('', ' ') else a
        authors = map(clean, get_value(rec, 'authors').split('|'))
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
        row['infrasp1_rank'] = get_value(rec, 'rank').replace('ssp.','subsp.')
        row['infrasp1'] = get_value(rec, 'infrepi')
        row['infrasp2_rank'] = u'cv.'
        row['infrasp2'] = get_value(rec, 'cultivar')
    elif rec['rank'] and not rec['infrepi'] and rec['cultivar']:
        # has infraspecific rank but no epithet...and a cultivar...??
        # maybe in this case we should just drop the rank and add cv. cultivar
        problems[0].append(clean_rec(rec))
        row['infrasp1_rank'] = get_value(rec, 'rank').replace('ssp.','subsp.')
        row['infrasp1'] = u''
        row['infrasp2_rank'] = u'cv.'
        row['infrasp2'] = u''
    elif rec['rank'] and rec['infrepi'] and not rec['cultivar']:
        row['infrasp1_rank'] = get_value(rec, 'rank').replace('ssp.','subsp.')
        row['infrasp1'] = get_value(rec, 'infrepi')
    elif rec['rank'] and not rec['infrepi'] and not rec['cultivar']:
        # has infrespecific rank but no epithet...???
        problems[1].append(clean_rec(rec))
        row['infrasp1_rank'] = get_value(rec, 'rank').replace('ssp.','subsp.')
        row['infrasp1'] = u''
    elif not rec['rank'] and rec['infrepi'] and rec['cultivar']:
        # have an infraspecific epithet and cultivar but no
        # infraspecific rank
        # TODO: could this mean that the infrepi part is the hybrid part
        problems[2].append(clean_rec(rec))
        row['infrasp1_rank'] = u'cv.'
        row['infrasp1'] = get_value(rec, 'cultivar')
        if row['hybrid']:
            row['sp2'] = get_value(rec, 'infrepi')
        else:
            row['infrasp2_rank'] = u'var.'
            row['infrasp2'] = get_value(rec, 'infrepi')
    elif not rec['rank'] and rec['infrepi'] and not rec['cultivar']:
        # has infraspecific epithet but not rank or cultivar.???
        problems[3].append(clean_rec(rec))
        if row['hybrid']:
            row['sp2'] = get_value(rec, 'infrepi')
        else:
            # WARNING: adding this as a variety is probably wrong but
            # what else can we do
            row['infrasp1_rank'] = u'var.'
            row['infrasp1'] = get_value(rec, 'infrepi')
    elif not rec['rank'] and not rec['infrepi'] and rec['cultivar']:
        row['infrasp1_rank'] = u'cv.'
        row['infrasp1'] = get_value(rec, 'cultivar')
    elif not rec['rank'] and not rec['infrepi'] and not rec['cultivar']:
        # use all the default values
        pass
    else:
        raise ValueError("ERROR: don't know how to handle record:\n%s" % rec)

    return row



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
        if (rec_ctr % granularity) == 0:
            # collect periodically so we don't run out of memory
            print_tick()
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
    insert_rows(insert, list(families.values()))
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
    insert_rows(insert, genus_rows)
    info('inserted %s genus rows out of %s records.' \
             % (len(genus_rows), len(dbf)))
    dbf.close()
    del dbf
    print ''



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

    status('converting SCINAME.DBF ...')
    genus_insert = get_insert(genus_table, ['genus', 'family_id'])
    species_defaults = get_defaults(species_table)
    genus_defaults = get_defaults(genus_table)

    no_genus_ctr = 0 # num of records with not genus
    rec_ctr = 0 # num of records
    dup_ctr = 0 # the num of rows with duplicate species date

    session = db.Session()

    # create a map of habits ids to habit codes
    habits = {}
    for habit in session.query(Habit):
        habits[habit.code] = habit.id

    # create a map of color ids to color codes
    colors = {}
    for color in session.query(Color):
        colors[color.code] = color.id
    session.close()

    species_rows = []
    genus_ids = {}
    delayed_species = []
    delayed_genera = {}
    dbf = open_dbf('SCINAME.DBF')

    columns = ['id', 'genus_id', 'sp', 'sp2', 'sp_author', 'hybrid', 'infrasp1',
               'infrasp1_rank', 'infrasp1_author', 'infrasp2', 'infrasp2_rank',
               'infrasp2_author', 'infrasp3', 'infrasp3_rank',
               'infrasp3_author', '_created', '_last_updated', 'awards',
               'habit_id', 'flower_color_id']
    species_insert = get_insert(species_table, columns)

    species_map = {} # so we can lookup the inserted species later
    hashes = set()



    species_id_ctr = get_max_id('species')
    species_note_defaults = get_defaults(species_note_table)
    species_note_defaults['date'] = '1/1/1900'
    notes = []

    vernacular_name_defaults = get_defaults(VernacularName.__table__)
    vernacular_name_defaults['language'] = u'English'
    vernac_names = []
    names_set = set() # set to hold duplicate names

    for rec in dbf:
        if rec_ctr % granularity == 0:
            gc.collect()
            print_tick()
        rec_ctr += 1
        defaults = species_defaults.copy()
        row = species_name_dict_from_rec(rec, defaults)
        row['id'] = species_id_ctr
        genus = row.pop('genus')
        if not genus:
            # no genus for the species record so use the catch-all
            # unknown genus
            no_genus_ctr += 1
            genus_id = unknown_genus_id
        else:
            # get the genus id
            genus_id = genus_ids.get(genus, None)
            if not genus_id:
                genus_id = get_column_value(genus_table.c.id,
                            genus_table.c.genus == genus)
            if genus_id:
                genus_ids[genus] = genus_id
            elif genus not in delayed_genera:
                #  couldn't find the full genus name so add it to
                #  delayed_genera for adding later. first search for
                #  just the genus name without the hybrid string and
                #  if it's found then add the new genus to the same
                #  family as the one without the hybrid string
                # warning('adding genus %s from sciname.dbf.' % genus)
                genus_row = genus_defaults.copy()
                genus_row['genus'] = genus
                family_id = get_column_value(genus_table.c.family_id,
                             genus_table.c.genus == rec['genus'])
                if not family_id:
                    # warning('** %s has no family. adding to %s' \
                    #             % (genus, unknown_family_name))
                    family_id = unknown_family_id
                genus_row['family_id'] = family_id
                delayed_genera[genus] = genus_row

        # create the species tuple before we add things like notes,
        # awards, habit, flower_color, etc.,
        species_tuple = tuple(zip(row.keys(), row.values()))
        species_hash = hash(species_tuple)

        row['awards'] = get_value(rec, 'awards')
        row['habit'] = get_value(rec, 'habit')
        row['flower_color'] = get_value(rec, 'flower_color')

        # set the habit
        habit = row.pop('habit')
        if habit not in (None, '', ' '):
            row['habit_id'] = habits[habit]
        else:
            row['habit_id'] = None

        # TODO: flower color can have -,>& delimiters....what should
        # we do, create two flower colors for a species????
        flower_color = row.pop('flower_color')
        if flower_color not in (None, '', ' '):
            row['flower_color_id'] = colors[flower_color]
        else:
            row['flower_color_id'] = None


        if has_value(rec, 'SCINOTE'):
            #print get_value(rec, 'scinote')
            note = species_note_defaults.copy()
            note.update(dict(category=u'Scientific', note=get_value(rec, 'scinote'),
                             species_id=species_id_ctr))
            notes.append(note)
        if has_value(rec, 'PHENOL'):
            note = species_note_defaults.copy()
            note.update(dict(category=u'Phenology', note=get_value(rec, 'phenol'),
                             species_id=species_id_ctr))
            notes.append(note)
        if has_value(rec, 'NOTES'):
            note = species_note_defaults.copy()
            note.update(dict(category=None, note=get_value(rec, 'notes'),
                             species_id=species_id_ctr))
            notes.append(note)

        # if the species_hash is the same, e.g. the species name is
        # the same we still has all the notes even though in some
        # cases even the notes will be the same, e.g.
        # ;Gaura;;lindheimeri;;;Crimson Butterflies;ENGELM.& A.GRAY | | |;HER_P;;Garden Origin;;False;Pride of Place Plants (New Eden) online;;;PIN; 5;To 60cm/Foliage dark crimson.;

        # TODO: this vernacular name thing isn't working properly and
        # is creating a lot of vernacular names in the wrong
        # place....or maybe its just a problem with the view not
        # clearing them out when the editors are opened....UPDATE: is
        # this still the case???
        for name in [n.strip() for n in rec['comname'].split(',')]:
            if name not in (None, '', ' ') and not (species_id_ctr, name) in names_set:
                vernac = vernacular_name_defaults.copy()
                vernac['species_id'] = species_id_ctr
                vernac['name'] = utils.utf8(name)
                vernac_names.append(vernac)
                names_set.add((species_id_ctr, name))

        # hash the species data tuples so we know if we are creating
        # duplicates and to make the rows retrievable so we can look
        # up the species ids later
        if species_hash not in species_map:
            # only insert non duplicates
            species_map[species_hash] = row.copy()
            # if we don't have the genus yet then add to
            # delayed_species so we can look up the genera later
            if genus_id:
                row['genus_id'] = genus_id
                species_rows.append(row)
            else:
                row['genus'] = genus
                delayed_species.append(row)
        else:
            dup_ctr += 1
            # error(genus)
            # error('values already exist: %s' % row)
            # #error('%s' % str(species_tuple))
            # print
            # error(species_map[species_hash])
            # raise ValueError
        species_id_ctr += 1

    nrecords = len(dbf)
    dbf.close() # close it so we can garbage collect before insert
    gc.collect()

    insert_rows(genus_insert, delayed_genera.values())
    info('inserted %s genus' % len(delayed_genera))

    info('delayed_species: %s' % len(delayed_species))
    # set the genus_id on the delayed_species
    for species in delayed_species:
        genus = species.pop('genus')
        if genus in genus_ids:
            genus_id = genus_ids[genus]
        else:
            genus_id = get_column_value(genus_table.c.id,
                                        genus_table.c.genus == genus)
            genus_ids[genus] = genus_id
        species['genus_id'] = genus_id
        species_rows.append(species)

    insert_rows(species_insert, species_rows)
    info('inserted %s species in %s records (%s duplicates)' % \
             (len(species_rows), nrecords, dup_ctr))

    if len(species_rows)+dup_ctr != nrecords:
        print 'species_row: %s' % len(species_rows)
        print 'dup_ctr: %s' % dup_ctr
        print 'nrecords: %s' % nrecords
        raise ValueError('len(species_rows)+dup_ctr != nrecords')

    warning('** %s sciname entries with no genus.  Added to the genus %s' \
                % (no_genus_ctr, unknown_genus_name))


    note_insert = get_insert(SpeciesNote.__table__,
                             ['category', 'date', 'note', 'species_id'])
    insert_rows(note_insert, notes)
    info('%s species notes inserted' % len(notes))

    name_insert = get_insert(VernacularName.__table__,
                             ['name', 'language', 'species_id'])
    insert_rows(name_insert, vernac_names)
    info('%s vernacular names inserted' % len(vernac_names))



def get_species_id(species, defaults=None):
    """
    """
    if 'genus_id' not in species:
        genus_id = get_column_value(genus_table.c.id,
                                    genus_table.c.genus == species['genus'])
    ignore = ('_last_updated', '_created', 'genus')
    where = where_from_dict(species_table, species, ignore)
    return get_column_value(species_table.c.id, where)




def do_plants():
    """
    BGAS Plants are what we refer to as accessions
    """
    # accno, propno, source, dateaccd, datercvd, qtyrcvd, rcvdas, ig,
    # genus, is, species, rank, infrepi, cultivar,
    #
    # idqual: id qualifier or id quality: seems like this is an
    # A,B,C,D which designates the quality of the identification
    #
    # verified: True/False
    #
    # othernos:
    # iswild:
    # wildnum,
    # wildcoll: collection locale, often seems like a long/lat
    #
    # wildnote: collection notes?
    #
    # geocode:
    #
    # voucher: voucher made?, looks like it should be True/False but
    # there are some other string values here as well, maybe
    # collection notes; TODO: maybe we should just make this a note in
    # the collection notes or something since it's only True/False
    #
    # photo:
    #
    # initloc: initial location,location code?, this could probably be
    # pushed to plant 0 and and latter plants would have been
    # transferred from here
    #
    # intendloc1: intended location, location code?
    # intendloc2: intended location 2, location code?
    # labels: number of labels, is this a request?, Integer

    # pisbg: plant introduction schema for botanic gardens, True/False
    #
    # memorial: True/False
    #
    # pronotes: propagation notes?
    #
    # notes
    #
    # operator
    #
    # l_update: last updated, should be a DateTime but there are also
    # some other strings here, looks like mostly misplaced "operator"
    # field strings
    #
    # delstat: deletion status?

    # TODO: we will have to match the species names exactly since they
    # aren't referenced to a scientific name by id or anything
    status('converting PLANTS.DBF ...')
    dbf = open_dbf('PLANTS.DBF')
    acc_insert = get_insert(acc_table,
                            ['code', 'species_id', ])

    acc_defaults = get_defaults(acc_table)
    acc_notes_defaults = get_defaults(AccessionNote.__table__)
    acc_notes_defaults['date'] = '1/1/1900'
    acc_notes_defaults['category'] = None

    plant_defaults = get_defaults(plant_table)
    plant_defaults['location_id'] = unknown_location_id

    species_defaults = get_defaults(species_table)
    _last_updated = species_defaults.pop('_last_updated')
    _created = species_defaults.pop('_created')
    delayed_species = {} # species not in db and to be inserted in bulk later
    species_ids = {}
    delayed_accessions = [] # accessions without species to be inserted later
    acc_rows = []
    source_rows = {}

    # different note types
    acc_notes = {}
    acc_pronotes = {}
    acc_wildnote = {}

    # TODO: what if the data differs but the accession code is the
    # same...does this ever happen in practice
    added_codes = set()
    plants = {}

    # map the locations ids by their codes for quick lookup
    locations = {}
    session = db.Session()
    for loc in session.query(Location):
        locations[loc.code] = loc.id
    session.close()

    rec_ctr = 0
    # build up a list of all the accession and plants
    for rec in dbf:
        if (rec_ctr % granularity) == 0:
            # collect periodically so we don't run out of memory
            gc.collect()
            print_tick()
        rec_ctr += 1

        # TODO: should record the name of the person who creates new
        # accession and use the operator field for old
        # accessions...of course the audit trail will also record this

        # accno/propno combinations are unique in PLANTS.DBF but not
        # in HEREITIS.DBF
        p = (rec['accno'], rec['propno'])
        if p not in plants:
            plant_row = plant_defaults.copy()
            plant_row['code'] = unicode(rec['propno'])
            #plant_row['date_accd'] = rec['dateaccd']
            #plant_row['date_recvd'] = rec['datercvd']
            # TODO: should pronotes be for the plant
            plants[p] = plant_row
        else:
            raise ValueError('duplicate accession: %s' % p)

        # this is just an extra check and an exception should never be raised
        if not rec['accno']:
            error('** accno is empty: %s' % rec['accno'])
            raise ValueError('** accno is empty: %s' % rec['accno'])

        # TODO: here we are skipping adding duplicate accession codes
        # but we should still use the same information for the skipped
        # codes so we don't accidentally lose anything like notes and
        # collection locales, maybe we could just create one
        # collection locale but before setting it just make sure the
        # collection location and notes and everything are the same
        # and if they aren't then create a duplicate or give and
        # error...i think in BGAS some fields are locked after they
        # are first entered so that creating later propagules they
        # share the same information


        # TODO: the date accessioned should come from the accession
        # with the lowest propno...does this always come first in the file

        if rec['accno'] not in added_codes:
            added_codes.add(rec['accno'])
        else:
            # for now we're only creating accessions, not plants so
            # only enter those that are unique
            continue

        # *************************************************************************
        # EVERYTHING PAST HERE WILL BE SKIPPED IF THE ACCESSION CODE IS A DUPLICATE
        # *************************************************************************

        # look up the species_id for the accessions, if we can't find
        # the species_id then add the species row to delayed_species
        # and we'll bulk commit them later and look up the species_id
        # for the accessions after that
        row = acc_defaults.copy()
        row['code'] = unicode(rec['accno'])
        row['_last_updated'] = rec['l_update']
        row['pisbg'] = rec['pisbg']
        row['memorial'] = rec['memorial']
        row['date_accd'] = rec['dateaccd']
        row['date_recvd'] = rec['datercvd']
        row['recvd_type'] = rec['rcvdas']
        row['quantity_recvd'] = rec['qtyrcvd']

        if rec['intendloc1']:
            row['intended_location_id'] = locations[rec['intendloc1']]
        if rec['intendloc2']:
            row['intended2_location_id'] = locations[rec['intendloc2']]

        # get the different type of notes
        if rec['notes'].strip():
            acc_notes[p] = acc_notes_defaults.copy()
            acc_notes[p]['note'] = utils.utf8(rec['notes'])

        if rec['pronotes'].strip():
            acc_pronotes[p] = acc_notes_defaults.copy()
            acc_pronotes[p]['note'] = utils.utf8(rec['pronotes'])
            acc_pronotes[p]['category'] = u'pronotes?'

        # TODO: this wildnotes is temporary and should probably go in
        # the collection notes
        if rec['wildnote'].strip():
            acc_wildnote[p] = acc_notes_defaults.copy()
            acc_wildnote[p]['note'] = utils.utf8(rec['wildnote'])
            acc_wildnote[p]['category'] = u'wildnote?'

        species = species_name_dict_from_rec(rec, species_defaults)
        species_tuple = tuple(zip(species.keys(), species.values()))

        # check if we already have a cached species.id, if not then
        # search for one in the database
        species_id = species_ids.get(species_tuple, None)
        if not species_id:
            species_id = species_ids.setdefault(species_tuple,
                                                get_species_id(species))
        if species_id:
            row['species_id'] = species_id
            acc_rows.append(row)
        else:
            # couldn't get the species id so check if the genus is in
            # the database and if it isn't then insert it
            genus = species.pop('genus')
            genus_id = get_column_value(genus_table.c.id,
                                        genus_table.c.genus == genus)
            if not genus_id:
                # in the original test data that i got from UBC the
                # only genus that didn't didn't exist was (BL.0178) so
                # this might be uneccesary logic but its here just in case
                info('adding genus %s from plants.dbf.' % genus)
                family_id = unknown_family_id
                # couldn't find the genus so add it
                if genus.startswith('x '):
                    # try to get a family of the parent genus if its a hybrid
                    family_id = get_column_value(family_table.c.id,
                                                 genus_table.c.genus==genus[2:])
                    if not family_id:
                        family_id = unknown_family_id
                if family_id == unknown_family_id:
                    warning('genus has no family: %s' % genus)
                genus_table.insert().values(family_id=family_id,
                                            genus=genus).execute().close()
                genus_id = get_column_value(genus_table.c.id,
                                            genus_table.c.genus==genus)

            # add the timestamps back in since these are species we'll
            # be creating later
            species['genus_id'] = genus_id
            species['_last_updated'] = _last_updated
            species['_created'] = _created
            delayed_species[species_tuple] = species
            delayed_accessions.append((species_tuple, row))

            source = {}
            # add collection and source contact data if there is any
            coll_data = (rec['wildcoll'], rec['wildnum'], rec['wildnote'])
            if filter(lambda x: not x.strip(), coll_data):
                collection = {}
                collection['locale'] = utils.utf8(rec['wildcoll'])
                collection['collectors_code'] = utils.utf8(rec['wildnum'])
                collection['notes'] = utils.utf8(rec['wildnote'])
                source['collection'] = collection

            if filter(lambda x: not x.strip(), [str(rec['source']), str(rec['othernos'])]):
                source_contact = {}
                source_contact['contact_id'] = rec['source']
                source_contact['contact_code'] = utils.utf8(rec['othernos'])
                source['source_contact'] = source_contact

            if source:
                source_rows[row['code']] = source
                #source_rows.setdefault(row['code'], {}).append(source)

    print ''

    gc.collect()

    # TODO: could inserting all the delayed species cause problems
    # if species with duplicate names are inserted then we won't know
    # which one to get for the species_id of the accession
    debug('  insert %s delayed species...' % len(delayed_species.values()))
    species_insert = get_insert(species_table, species_defaults.keys())
    insert_rows(species_insert, delayed_species.values())
    info('inserted %s species from plants.dbf' % len(delayed_species.values()))

    gc.collect()

    # set species id on the accession rows that we couldn't get earlier
    rec_ctr = 0
    debug('  populating %s delayed accessions...' % (len(delayed_accessions)))
    for species_tuple, acc in delayed_accessions:
        rec_ctr += 1
        if (rec_ctr % granularity) == 0:
            # collect periodically so we don't run out of memory
            print_tick()
            gc.collect()

        # get the species id now that all the species have been inserted
        ignore_columns = ('_last_updated', '_created', 'id', 'habit', 'notes',
                          'flower_color', 'awards')
        species = delayed_species[species_tuple]
        if isinstance(species, int):
            species_id = species
        else:
            # find the species.id and cache it
            species_id = get_species_id(species)
            delayed_species[species_tuple] = species_id
        acc['species_id'] = species_id
        acc_rows.append(acc)
    del delayed_species
    del delayed_accessions

    gc.collect()

    # insert the accessions
    debug('  insert %s accessions...' % len(acc_rows))
    insert_rows(acc_insert, acc_rows)
    info('inserted %s accesions out of %s records' \
             % (len(acc_rows), len(dbf)))

    dbf.close()
    del dbf
    # now that we have all the accessions loop through all the records
    # again and create the plants
    rec_ctr = 0
    for plant_tuple, plant_row in plants.iteritems():
        acc_code, plant_code = plant_tuple
        rec_ctr += 1
        if (rec_ctr % granularity) == 0:
            # collect periodically so we don't run out of memory
            print_tick()
            gc.collect()
        acc_id = get_column_value(acc_table.c.id,
                                  acc_table.c.code == unicode(acc_code))
        if not acc_id:
            # this is just an extra check and we shouldn't ever get here
            print str((acc_code, plant_code))
            raise ValueError

        plant_row['accession_id'] = acc_id

        # set the accession id for the notes
        if plant_tuple in acc_notes:
            acc_notes[plant_tuple]['accession_id'] = acc_id
        if plant_tuple in acc_pronotes:
            acc_pronotes[plant_tuple]['accession_id'] = acc_id
        if plant_tuple in acc_wildnote:
            acc_wildnote[plant_tuple]['accession_id'] = acc_id

        # set the accession_id for the source records
        if unicode(acc_code) in source_rows:
            source_rows[unicode(acc_code)]['accession_id'] = acc_id

    gc.collect()
    print ''

    # we now have all the information for the accession notes so commit
    notes_insert = get_insert(AccessionNote.__table__,
                              ['note', 'date', 'category', 'accession_id'])
    insert_rows(notes_insert, acc_notes.values())
    info('inserted %s accession notes' % len(acc_notes.values()))
    insert_rows(notes_insert, acc_pronotes.values())
    info('inserted %s accession pronotes' % len(acc_pronotes.values()))
    insert_rows(notes_insert, acc_wildnote.values())
    info('inserted %s accession wildnote' % len(acc_wildnote.values()))

    # insert the source rows individually since there aren't very many
    # and we need to get the ids back...we could just generate our own
    # ids then we wouldn't have to look them up later
    collections = []
    source_insert = get_insert(Source.__table__, ['collection_id', 'source_contact_id',
                                                  'accession_id'])
    collection_insert = get_insert(Collection.__table__, ['locale', 'collectors_code',
                                                          'notes', ])
    source_contact_insert = get_insert(SourceContact.__table__, ['contact_id',
                                                                 'contact_code'])
    collection_table = Collection.__table__
    source_contact_table = SourceContact.__table__
    info('insert source rows...')
    for source in source_rows.values():
        coll_id = None
        collection = {}
        if 'collection' in source:
            collection = source.pop('collection')
            # TODO: check first the collection doesn't exist
            insert_rows(collection_insert, [collection])
            where = where_from_dict(collection_table, collection,
                                    ('_last_updated', '_created'))
            coll_id = get_column_value(collection_table.c.id, where)

        #debug('%s - %s' % (coll_id, type(coll_id)))
        source['collection_id'] = coll_id

        sc_id = None
        source_contact = {}
        if 'source_contact' in source:
            source_contact = source.pop('source_contact')
            # TODO: check first the source contact doesn't exists
            insert_rows(source_contact_insert, [source_contact])
            where = where_from_dict(source_contact_table, source_contact,
                                    ('_last_updated', '_created'))
            sc_id = get_column_value(source_contact_table.c.id, where)
        source['source_contact_id'] = sc_id
        # TODO: are the colletions unique, how do we get them back, we
        # should check it a search returns more than one collection.id

        if not source.get('accession_id', None):
            print collection
            print source_contact
            print source
            raise ValueError
        insert_rows(source_insert, [source])


    # i couldn't get plant_table.update() to ever work properly so
    # instead we just loop through the hereitis table and set the
    # values on the plant before inserting the plant rows

    # loop through the hereitis table to set the location_id, for any
    # plants that are in PLANTS.DBF but aren't in HEREITIS.DBF the
    # locations is set to unknown_location
    status('converting HEREITIS.DBF ...')
    # TODO: the HEREITIS table can have duplicate rows for the same
    # accession number and plant code
    dbf = open_dbf('HEREITIS.DBF')
    rec_ctr = 0
    added = set()
    hereitis_dupes = set()
    for rec in dbf:
        rec_ctr += 1
        if (rec_ctr % granularity) == 0:
            # collect periodically so we don't run out of memory
            print_tick()
            gc.collect()
        location_id = locations[unicode(rec['bedno'])]
        plant_tuple = (rec['accno'], rec['propno'])
        if plants[plant_tuple]['location_id'] == unknown_location_id:
            plants[plant_tuple]['location_id'] = location_id
            added.add(plant_tuple)
        else:
            # it looks like the dupes have different l_update columns
            # so maybe we should drop them if everything else is the
            # same and use whichever one has the latest date...it
            # seems like if anything they should be transfers or just
            # old date that wasn't updated
            hereitis_dupes.add(rec)
            # error(plants_map[plant_tuple])
            # raise ValueError('location_id already set')

    plant_insert = get_insert(plant_table, ['accession_id', 'code',
                                            'location_id'])
    insert_rows(plant_insert, plants.values())
    #print len(plants_map.values())
    # TODO: do we need plant rows or can we just use plants_map.values()
    #print len(plant_rows)
    print ''
    info('inserted %s plants' % len(plants.values()))
    #status('%s duplicates' % dup_ctr)
    info('%s duplicates' % len(hereitis_dupes))
    dbf.close()



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


def do_removals():
    """
    Convert the REMOVALS.DBF table to bauble.plugins.garnde.plant.PlantRemoval
    """
    # accno;propno;remodate;remoqty;remocode;remofrom;notes
    # TODO: we don't have an equivalent for quantity
    status('converting REMOVALS.DBF ...')
    removal_table = PlantRemoval.__table__
    defaults = get_defaults(removal_table)
    dbf = open_dbf('REMOVALS.DBF')
    removal_rows = []
    locations = {}
    session = db.Session()
    for loc in session.query(Location):
        locations[loc.code] = loc.id
    session.close()
    for rec in dbf:
        row = defaults.copy()
        # TODO: the date format is yyyy-mm-dd...does this work for us
        row['date'] = rec['remodate']
        row['from_location_id'] = locations[rec['remofrom']]
        row['reason'] = rec['remocode']
        plant_id = get_column_value(plant_table.c.id,
                                    and_(Plant.code==unicode(rec['propno']),
                                         Accession.code==unicode(rec['accno'])))
        if not plant_id:
            error(row)
            raise ValueError
        row['plant_id'] = plant_id
        removal_rows.append(row)
        # note = {}
        # note['note'] = rec['notes']
        # note['date'] = rec['remodate']
    insert = get_insert(PlantRemoval.__table__,
                        ['date', 'from_location_id', 'plant_id'])
    insert_rows(insert, removal_rows)


def do_source():
    """
    Convert the SOURCE.DBF table to bauble.plugins.plants.species_model.Source
    """
    status('converting SOURCE.DBF ...')
    contact_table = Contact.__table__
    defaults = get_defaults(contact_table)
    dbf = open_dbf('SOURCE.DBF')
    contact_rows = []
    names = set()
    name_ctr = {}
    for rec in dbf:
        row = defaults.copy()
        name = utils.utf8(rec['keyword'])
        if name in names and not name == 'Missing':
            name = '%s - %s' % (name, rec['soudescr'].split(',')[0].strip())

        # make sure the names are unique
        if name in names:
            orig_name = name
            ctr = name_ctr.setdefault(name, 1)
            name = '%s - %s' % (name, ctr)
            name_ctr[orig_name] = ctr+1

        row.update({'id': utils.utf8(rec['source']),
                    'name': name,
                    'address': utils.utf8(rec['soudescr'])})
        names.add(row['name'])
        contact_rows.append(row)
        del rec
    dbf.close()

    conn = db.engine.connect()
    trans = conn.begin()
    insert = get_insert(contact_table, ['id', 'name', 'address'])
    conn.execute(insert, *contact_rows)
    trans.commit()
    conn.close()
    info('inserted %s contacts.' % len(contact_rows))


stages = {
    '0': do_family,
    '1': do_habit,
    '2': do_color,
    '3': do_sciname,
    '4': do_bedtable,
    '5': do_source,
    '6': do_plants,
    '7': do_synonym,
    '8': do_removals}

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
    chunk = []
    ctr = 0
    for it in iterable:
        chunk.append(it)
        ctr += 1
        if ctr >= n:
            yield chunk
            chunk = []
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

