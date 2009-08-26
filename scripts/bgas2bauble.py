#!/usr/bin/env python
import copy
import csv
import os
import sys

from dbfpy import dbf
import sqlalchemy as sa
from sqlalchemy import *
from sqlalchemy.orm import *

import bauble
import bauble.db as db
import bauble.utils as utils
import bauble.meta as meta
import bauble.pluginmgr as pluginmgr

import logging
logging.basicConfig()

from optparse import OptionParser

default_uri = 'sqlite:///:memory:'

parser = OptionParser()
parser.add_option("-b", "--bgas", dest="bgas",
                  default=os.path.join(os.getcwd(), 'bgas'),
                  help="path to BGAS files", metavar="DIR")
parser.add_option("-s", "--stage", dest="stage", default='0',
                  help="stage of conversion to start at", metavar="STAGE")
parser.add_option("-t", "--test", dest="test", action="store_true",
                  default=False, help="run only tests")
parser.add_option("-d", "--database", dest="database",
                  default=default_uri, metavar="DBURI",
                  help="the database uri to store the converted databaset")
(options, args) = parser.parse_args()

db.open(options.database, False)
pluginmgr.load()
# the one thing this script doesn't do that bauble does is called
# pluginmgr.init()
#pluginmgr.init(force=True)
if options.stage == '0' or options.database == default_uri:
    db.create(import_defaults=False)

from bauble.plugins.plants import Family, Genus, Species
from bauble.plugins.garden import Accession, Plant, Location

family_table = Family.__table__
genus_table = Genus.__table__
species_table = Species.__table__
acc_table = Accession.__table__
location_table = Location.__table__

session = bauble.Session()

src = os.path.join(os.getcwd(), 'dump')
dst = os.path.join(os.getcwd(), 'bauble')

if not os.path.exists(dst):
    os.makedirs(dst)

# TODO: this script needs to be very thoroughly tested

# filenames: bedtable.csv colour.csv dummy.csv family.csv geocode.csv
# habit.csv hereitis.csv plants.csv rcvdas.csv remocode.csv
# removal.csv removals.csv sciname.csv source.csv subset.csv
# synonym.csv transfer.csv

# BGAS data problems:
#
# 1. Some scientific names which have an infraspecific rank but don't
# have an infraspecific epithet.
#
# 2. Some genera do not have families.  Inn FAMILY.DBF, SCINAME.DBF
# and PLANTS.DBF
#
# 3. ACCNO: 11710, no rank but has infrepi and cultivar but it appears
# that the infrepi should be in the cultivar group
#
# 4. what should we do about duplication accession numbers: e.g. ACCNO: 20442
#
# 5. How do you know which of the duplicate accessions the
# hereitis.dbf row is referring to.
#
# 6. Should propno in hereitis.dbf and plants.dbf become a bauble
# plant number or a seperate accession?
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
    return defaults


def get_insert(table, columns):
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
    result = select([column], where).execute().fetchone()
    if result:
        return result[0]
    return None


# create (unknown) family for those genera that don't have a family
unknown_family_name = u'(unknown)'
if options.stage == '0':
    family_table.insert().values(family=unknown_family_name).execute()
unknown_family_id = get_column_value(family_table.c.id,
                              family_table.c.family==unknown_family_name)

unknown_genus_name = u'(unknown)'
if options.stage == '0':
    genus_table.insert().values(family_id=unknown_family_id,
                                genus=unknown_genus_name).execute()
unknown_genus_id = get_column_value(genus_table.c.id,
                              genus_table.c.genus==unknown_genus_name)


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

    row['sp'] = utils.utf8(rec['species'])
    if rec['is']:
        row['hybrid'] = True
    else:
        row['hybrid'] = False

    if 'AUTHORS' in rec.dbf.fieldNames and rec['authors']:
        # TODO: what's with all the '|' bars in the author string
        row['sp_author'] = utils.utf8(rec['authors'].replace('|','').strip())

    # set default infrasp values
    row['infrasp_rank'] = u''
    row['infrasp'] = None
    row['infrasp2_rank'] = u''
    row['infrasp2'] = None

    # match all the combinations of rank, infrepi and cultivar
    if rec['rank'] and rec['infrepi'] and rec['cultivar']:
        row['infrasp_rank'] = utils.utf8(rec['rank']).replace('ssp.', 'subsp.')
        row['infrasp'] = utils.utf8(rec['infrepi'])
        row['infrasp2_rank'] = u'cv.'
        row['infrasp2'] = utils.utf8(rec['cultivar'])
    elif rec['rank'] and not rec['infrepi'] and rec['cultivar']:
        # has infrespecific rank but no epithet...and a cultivar...??
        # maybe in this case we should just drop the rank and add cv. cultivar
        row['infrasp_rank'] = utils.utf8(rec['rank']).replace('ssp.', 'subsp.')
        row['infrasp2_rank'] = u'cv.'
        row['infrasp2'] = utils.utf8(rec['cultivar'])
    elif rec['rank'] and rec['infrepi'] and not rec['cultivar']:
        row['infrasp_rank'] = utils.utf8(rec['rank']).replace('ssp.', 'subsp.')
        row['infrasp'] = utils.utf8(rec['infrepi'])
    elif rec['rank'] and not rec['infrepi'] and not rec['cultivar']:
        # has infrespecific rank but no epithet...???
        row['infrasp_rank'] = utils.utf8(rec['rank']).replace('ssp.', 'subsp.')
    elif not rec['rank'] and rec['infrepi'] and rec['cultivar']:
        #row['infrasp_rank']
        row['infrasp'] = utils.utf8(rec['infrepi'])
        row['infrasp2_rank'] = u'cv.'
        row['infrasp2'] = utils.utf8(rec['cultivar'])
    elif not rec['rank'] and rec['infrepi'] and not rec['cultivar']:
        # has infrespecific epithet but not rank or cultivar.???
        row['infrasp'] = utils.utf8(rec['infrepi'])
    elif not rec['rank'] and not rec['infrepi'] and rec['cultivar']:
        row['infrasp_rank'] = u'cv.'
        row['infrasp'] = utils.utf8(rec['cultivar'])
    elif not rec['rank'] and not rec['infrepi'] and not rec['cultivar']:
        # use all the default values
        pass
    else:
        raise ValueError("ERROR: don't know how to handle record:\n%s" % rec)

    if 'SCINOTE' in rec.dbf.fieldNames and rec['scinote']:
        row['notes'] = utils.utf8(rec['scinote'])

    return row



def do_family():
    """
    Create the family and genus tables from a FAMILY.DBF file
    """
    print 'converting FAMILY.DBF ...'
    dbf = open_dbf('FAMILY.DBF')
    defaults = get_defaults(family_table)
    insert = get_insert(family_table, ['family'])
    families = {}
    genera = {}

    # create the insert values for the family table and genera
    for rec in dbf:
        family = rec['family']
        if not family in families:
            row = defaults.copy()
            row['family'] = family
            families[family] = row

        genus = rec['genus']
        if not genus in genera:
            genera[genus] =  {'family': family, 'genus': genus}
        else:
            # luckily there are not duplicate genera/families but
            # we'll leave this here just in case for future data
            raise ValueError('duplicate genus: %s(%s) -- %s(%s)' \
                % (genus, family, genera['genus'], genera['family']))

    # insert the families
    db.engine.execute(insert, *list(families.values()))
    print 'inserted %s family.' % len(families)

    # get the family id's for the genera
    genus_rows = []
    defaults = get_defaults(genus_table)
    for genus in genera.values():
        family = genus.pop('family')
        if not family:
            print '** %s has no family. adding to %s' \
                % (genus['genus'], unknown_family_name)
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
    db.engine.execute(insert, *genus_rows)
    print 'inserted %s genus rows out of %s records.' \
        % (len(genus_rows), len(dbf))



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
    print 'converting SCINAME.DBF ...'
    dbf = open_dbf('SCINAME.DBF')
    species_insert = get_insert(species_table,
                                ['genus_id', 'sp', 'hybrid', 'infrasp',
                                 'infrasp_rank', 'sp_author', 'notes',
                                 'infrasp2', 'infrasp2_rank'])
    species_rows = []
    genus_insert = get_insert(genus_table, ['genus', 'family_id'])
    no_genus_ctr = 0
    species_defaults = get_defaults(species_table)
    genus_defaults = get_defaults(genus_table)
    for rec in dbf:
        genus = str('%s %s' % (rec['ig'], rec['genus'])).strip()
        genus_id = None
        if not genus:
            no_genus_ctr += 1
            genus_id = unknown_genus_id
        else:
            #genus_id = get_column_value(genus_table.c.id,
            #                     genus_table.c.genus == genus)
            stmt = 'select id from genus where genus=="%s";' % genus
            r = db.engine.execute(stmt).fetchone()
            if r:
                genus_id = r[0]
        if not genus_id:
            #family_id = get_column_value(genus_table.c.family_id,
            #                      genus_table.c.genus == rec['genus'])
            family_id = None
            stmt = 'select family_id from genus where genus=="%s";' % genus
            r = db.engine.execute(stmt).fetchone()
            if r:
                family_id = r[0]
            print 'adding genus %s from sciname.dbf.' % genus
            if not family_id:
                print '** %s has no family. adding to %s' \
                    % (genus, unknown_family_name)
                family_id = unknown_family_id
            genus_row = genus_defaults.copy()
            genus_row.update({'genus': genus, 'family_id': family_id})
            db.engine.execute(genus_insert, genus_row)
            genus_id = get_column_value(genus_table.c.id,
                                 genus_table.c.genus == genus)

        # TODO: check that the species name doesn't already exists,
        # can probably go ahead and import it but just give a message
        # that says something like "it appears the species already
        # exists"
        defaults = species_defaults.copy()
        defaults['genus_id'] = genus_id
        row = species_dict_from_rec(rec, defaults=defaults)
        species_rows.append(row)

    db.engine.execute(species_insert, *species_rows)
    print 'inserted %s species out of %s records' \
        % (len(species_rows), len(dbf))
    print '** %s sciname entries with no genus.  Added to the genus %s' \
        % (no_genus_ctr, unknown_genus_name)


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
    print 'converting PLANTS.DBF ...'
    dbf = open_dbf('PLANTS.DBF')
    rec_ctr = 0
    species_table = Species.__table__
    acc_table = Accession.__table__
    acc_insert = get_insert(acc_table,
                            ['code', 'species_id', ])
    acc_defaults = get_defaults(acc_table)
    species_defaults = get_defaults(species_table)
    delayed_species = []
    delayed_accessions = []

    def get_species_id(r):
        # TODO: this could probably become a generic function where we
        # can also pass a flag on whether to create the species if we
        # can't find them...do the same for get_family_id() and
        # get_genus_id()
        genus_id = None
        genus = str('%s %s' % (rec['ig'], rec['genus'])).strip()
        if 'genus_id' in r and r['genus_id']:
            genus_id = r['genus_id']
        else:
            #genus_id = get_column_value(genus_table.c.id,
            #                        genus_table.c.genus == genus)
            stmt = 'select id from genus where genus=="%s";' % genus
            r = db.engine.execute(stmt).fetchone()
            if r:
                genus_id = r[0]
        if not genus_id:
            # TODO: here we're assume the genera don't have an
            # associated family but it shouldn't really matter b/c
            # there seems to be only one genus (BL.0178) in plants.dbf
            # that isn't already in the database
            print 'adding genus %s from plants.dbf.' % genus
            genus_table.insert().values(family_id=unknown_family_id,
                                        genus=genus).execute()
            genus_id = get_column_value(genus_table.c.id,
                                 genus_table.c.genus == genus)

        defaults = species_defaults.copy()
        defaults['genus_id'] = genus_id
        row = species_dict_from_rec(rec, defaults=defaults)
        conditions = []
        for col, val in row.iteritems():
            if col not in ('_last_updated', '_created'):
                conditions.append(species_table.c[col]==val)
        species_id = get_column_value(species_table.c.id, and_(*conditions))
        if not species_id:
            delayed_species.append(row)
            return None

        return species_id

    acc_rows = []
    added_codes = set()
    duplicates = []
    for rec in dbf:
        rec_ctr += 1
        if (rec_ctr % 500) == 0:
            sys.stdout.write('.')
            sys.stdout.flush()
            # break

        if not rec['accno']:
            print '** accno is empty: %s' % rec['accno']
            raise ValueError('** accno is empty: %s' % rec['accno'])
        elif rec['accno'] in added_codes:
            #print '** duplicate code: %s....not importing' % rec['accno']
            duplicates.append(rec['accno'])
            continue
            #raise ValueError('** duplicate code: \n%s' % rec)

        species_id = get_species_id(rec)
        if species_id:
            row = acc_defaults.copy()
            row['code'] = utils.utf8(rec['accno'])
            row['species_id'] = species_id
            acc_rows.append(row)
        else:
            delayed_accessions.append(rec)

        added_codes.add(rec['accno'])

    print ''

    # TODO: could inserting all the delayed species cause problems
    # if species with duplicate names are inserted then we won't know
    # which one to get for the species_id of the accession
    if delayed_species:
        db.engine.execute(species_table.insert(), *delayed_species)
        print 'inserted %s species from plants.dbf' % len(delayed_species)

    for rec in delayed_accessions:
        row = acc_defaults.copy()
        row['code'] = utils.utf8(rec['ACCNO'])
        species_id = get_species_id(rec)
        if not species_id:
            print rec
            print delayed_species
            raise ValueError('cound\'t get species id')
        row['species_id'] = get_species_id(rec)
        acc_rows.append(row)

    # insert the accessions
    db.engine.execute(acc_insert, *acc_rows)
    print 'inserted %s accesions out of %s records' \
        % (len(acc_rows), len(dbf))
    if len(duplicates) > 0:
        # print 'the following are duplicate accession numbers where only '\
        #     'the first occurence of the accession code were added to '\
        #     'the database:\n%s' % sorted(duplicates)
        print '%s duplicate accessions not inserted.' % len(duplicates)


def do_bedtable():
    print 'converting BEDTABLE.DBF ...'
    dbf = open_dbf('BEDTABLE.DBF')
    location_rows = []
    defaults = get_defaults(location_table)
    for rec in dbf:
        row = defaults.copy()
        row.update({'site': utils.utf8(rec['bedno']),
                    'description': utils.utf8(rec['beddescr'])})
        location_rows.append(row)
    db.engine.execute(location_table.insert(), *location_rows)
    print 'inserted %s locations out of %s records' \
        % (len(location_rows), len(dbf))


def do_hereitis():
    """
    """
    # TODO: i can't really do anything with the hereitis table until i
    # can resolve the duplicates
    print 'converting HEREITIS.DBF ...'
    dbf = open_dbf('HEREITIS.DBF')
    codes = set()
    for rec in dbf:
        code = rec['accno']
        if rec['propno'] != 0:
            #print '%s.%s' % (rec['accno'], rec['propno'])
            pass
        if code in codes:
            #print 'dup: %s' % code
            pass
        else:
            codes.add(code)


def do_synonym():
    """
    """
    print 'converting SYNONYM.DBF ...'
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
    print 'testing...'
    # test all possible combinations of imported species names
    # test for duplicate species
    # test that all accession codes are unique
    # test that all plant codes are unique
    pass


if __name__ == '__main__':
    global current_stage
    if options.test:
        test()
    else:
        import timeit
        nstages = len(stages)
        total_seconds = 0
        for stage in range(int(options.stage), nstages):
            current_stage = stages[str(stage)]
            t = timeit.timeit('current_stage()',
                              "from __main__ import current_stage;", number=1)
            print '... in %s seconds.' % t
            total_seconds += t
        print 'total run time: %s seconds' % total_seconds


