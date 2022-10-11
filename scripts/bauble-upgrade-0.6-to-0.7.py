#!/usr/bin/env python

# this script needs both a connections to a database created with bauble 0.6.x
# and the csv files exported from the same database, it will create a directory
# called 0.7 in the same directory as the exported csv files with the new
# converted files...you will also need the default geography data to have
# functioning database



# What has changed from 0.6->0.7 ?
# ------------------
# - species.id_qual column is now accession.id_qual column, any species
# specific id_qual data should be moved to the accessions with that species
# - accession.country_id is now accession.geography_id, try to find a match
# for the country_id if there is one in the geography table
# - species_meta is no more, this means that all the previous distribution data
# won't match up, it would be good if we could find a string match and add this
# to the new species_distribution table
import csv
import os
import shutil
import sys
from optparse import OptionParser

from bauble.plugins.geography import *
from migrate.run import *
from sqlalchemy import *

import bauble
from bauble.plugins.plants import *


#import bauble.pluginmgr as pluginmgr

parser = OptionParser()
parser.add_option('-c', '--conn', dest='conn', help='the db connection uri',
                   metavar='CONN')
(options, args) = parser.parse_args()

if options.conn is None:
    parser.error('a database uri is required')

# a directory full of CSV text files exported from Bauble 0.6
src_path = None
print(args)
if len(args) == 0:
    src_path = os.getcwd()
else:
    src_path = args[0]
    if not os.path.exists(src_path):
        parser.error('%s does not exist' % src_path)

# where to put the new files
dst_path = os.path.join(src_path, '0.7')
if not os.path.exists(dst_path):
    os.mkdir(dst_path)

global_connect(options.conn)
engine = default_metadata.engine
session = create_session()


major, minor, rev = bauble.version
if minor != 6:
    print('** Error: This script will only upgrade from bauble 0.6')
    sys.exit(1)


def quote(s):
    if s is None:
        return ''
    elif isinstance(s, str):
        return '"%s"' % s
    return '%s' % s

QUOTE_STYLE = csv.QUOTE_MINIMAL
QUOTE_CHAR = '"'

def write_csv(filename, rows):
    f = file(filename, 'wb')
    writer = csv.writer(f, quotechar=QUOTE_CHAR, quoting=QUOTE_STYLE)
    writer.writerows(rows)
    f.close()


def migrate_idqual():
    print('migrating idqual')
    # select all species that have idqual set
    #species = species.select(id_qual != None)
    sp_results = select([species_table.c.id, species_table.c.id_qual],
                        species_table.c.id_qual != None).execute()
#    print sp_results
    acc_cols = list(accession_table.c.keys())
    new_cols = acc_cols[:]
    new_cols.append('id_qual')
    rows = []
    rows.append(new_cols)

    # copy the accessions whose species have id_qual
    for sp_id, sp_idqual in sp_results:
        for acc in accession_table.select(accession_table.c.species_id==sp_id).execute():
            v = [acc[c] for c in acc_cols]
            v.append('%s' % sp_idqual)
            rows.append(v)

    # copy the rest of the accessions that don't have id_qau
    sp_results = select([species_table.c.id],
                        species_table.c.id_qual == None)
    for acc in accession_table.select(accession_table.c.species_id.in_(sp_results)).execute():
        v = [acc[c] for c in acc_cols]
        v.append(None)
        rows.append(v)
    write_csv(os.path.join(dst_path, 'accession.txt'), rows)

    # copy the species and remove the id_qaul column
    rows = []
    sp_cols = list(species_table.c.keys())
    sp_cols.remove('id_qual')
    rows.append(sp_cols)
    for sp in species_table.select().execute():
        v = [sp[c] for c in sp_cols]
        rows.append(v)
    write_csv(os.path.join(dst_path, 'species.txt'), rows)

def migrate_distribution():
    # TODO: this would need to connect to a 0.7 database to search
    # for matching distribution data
    # *** we could just start over with the distribution data and forget about
    # trying to migrate it
    pass


def migrate_accession_geography():
    pass
#    r = session.query(Accession).select(accession_table.c.country_id!=None)
#    assert len(r) == 0




# TODO: update bauble meta
# TODO: create a registry
# TODO: it might make more sense to make some of the changes and then dump the
# data to and import it again to make sure things like the meta table and
# registry are created correctly
# TODO: the other options is to create a select statement that will create
# the columns we want to import

# TODO: how to use this script...export all tables from bauble first,

# This script will :
# 1. Create some CSV text files for importing into a Bauble 0.7
# database
# 2. Copy the rest of the CSV text files from a source directory into a
# destination that should also be imported into a new Bauble 0.7 database
#
# Basically this script will create a directory full of CSV files that
# can be imported into a Bauble 0.7 database.


# run this script and use the files it outputs in place of the ones from

migrate_accession_geography()
migrate_idqual()
migrate_distribution()


copy_list = ['donor.txt', 'family_synonym.txt', 'family.txt',
             'species_synonym.txt', 'genus_synonym.txt', 'genus.txt',
             'collection.txt', 'tagged_obj.txt', 'location.txt', 'tag.txt',
             'verification.txt', 'default_vernacular_name.txt',
             'plant_history.txt', 'vernacular_name.txt', 'donation.txt',
             'plant.txt']
for f in copy_list:
    print(('copying %s' % f))
    shutil.copy(os.path.join(src_path, f), dst_path)
