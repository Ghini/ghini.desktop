#!/usr/bin/env python
#
# csv convert 1.0 to 1.1
#
# use Ghini/Bauble 1.0 database to export your database as CSV files; then
# use this script to convert the exported CSV files in the newer format;
# finally use Ghini 1.1 to import the converted export in a new database.
#

#import csv
import glob
import argparse
import os
import shutil
import sys

import logging
logging.basicConfig()


import bauble
if bauble.version_tuple[0] != '1' and bauble.version_tuple[1] != '1':
    print "Ghini 1.1 must be installed"
    print bauble.version
    print bauble.version_tuple
    sys.exit(1)

#from bauble import utils
from bauble.plugins.imex.csv_ import UnicodeReader, UnicodeWriter


parser = argparse.ArgumentParser(
    description='csv convert 1.0 to 1.1')
parser.add_argument('source')
parser.add_argument('-o', '--output', dest='destination', default='')
parser.add_argument('-f', '--force', dest='force', action='store_true',
                    help='force overwriting destination')
args = parser.parse_args()

if not args:
    print parser.error('a directory with a dumped CSV files is required')


#dummy_date = "1902-01-01"
#dummy_timestamp = '1902-01-01 00:00:00.0-00:00'
dummy_date = None
dummy_timestamp = None


# a directory full of CSV text files exported from Bauble 1.0
src_path = args.source
if not os.path.exists(src_path):
    parser.error('%s does not exist' % src_path)

# where to put the new files
if args.destination == '':
    dst_path = os.path.join(src_path, '1.1')
else:
    dst_path = args.destination
if os.path.exists(dst_path) and args.force:
    shutil.rmtree(dst_path)
elif os.path.exists(dst_path):
    response = raw_input('%s exists.  Would you like to delete it? '
                         % dst_path)
    if response in ('y', 'Y'):
        shutil.rmtree(dst_path)
    else:
        sys.exit(1)
os.mkdir(dst_path)


def build_id_map(filename):
    f = os.path.join(src_path, filename)
    reader = UnicodeReader(open(f))
    id_map = {}
    for line in reader:
        #print line
        id_map[line['id']] = line
    return id_map


def create_writer(filename, columns):
    writer = UnicodeWriter(open(filename, "a+b"))
    writer.writerow(columns)
    return writer


def do_family(filename):
    """
    Convert the family.txt
    """
    reader = UnicodeReader(open(filename))

    family_filename = os.path.join(dst_path, 'family.txt')
    family_writer = UnicodeWriter(open(family_filename, "wb"))
    family_columns = ['id', 'epithet', 'hybrid_marker', 'author', 'aggregate',
                      '_created', '_last_updated']
    family_writer.writerow(family_columns)

    for line in reader:
        family_writer.writerow([line['id'], line['family'], '', '', '',
                               line['_created'], line['_last_updated']])
    print 'converted'


def do_genus(filename):
    """
    Convert genus.txt
    """

    reader = UnicodeReader(open(filename))

    genus_filename = os.path.join(dst_path, 'genus.txt')
    genus_writer = UnicodeWriter(open(genus_filename, "wb"))
    genus_columns = [
        'id', 'epithet', 'hybrid_marker', 'author', 'aggregate',
        'family_id', '_created', '_last_updated']
    genus_writer.writerow(genus_columns)

    for line in reader:
        genus_writer.writerow(
            [line['id'], line['genus'], line['hybrid'] and u'×' or '',
             line['author'], line['qualifier'],
             line['family_id'], line['_created'],
             line['_last_updated']])
    print 'converted'


def do_species(filename):
    """
    Convert species.txt
    """
    reader = UnicodeReader(open(filename))

    species_filename = os.path.join(dst_path, 'species.txt')
    species_writer = UnicodeWriter(open(species_filename, "wb"))
    species_columns = [
        'id', 'epithet', 'hybrid_marker', 'author', 'aggregate', 'cv_group',
        'trade_name', 'infrasp1', 'infrasp1_rank', 'infrasp1_author',
        'infrasp2', 'infrasp2_rank', 'infrasp2_author',
        'infrasp3', 'infrasp3_rank', 'infrasp3_author',
        'infrasp4', 'infrasp4_rank', 'infrasp4_author',
        'genus_id', 'label_distribution', 'bc_distribution', 'habit_id',
        'flower_color_id', 'awards', '_created', '_last_updated']
    species_writer.writerow(species_columns)

    for line in reader:
        hybrid_marker = ''
        species_writer.writerow([
            line['id'], line['sp'], hybrid_marker, line['sp_author'],
            line['sp_qual'], line['cv_group'],
            line['trade_name'],
            line['infrasp1'], line['infrasp1_rank'], line['infrasp1_author'],
            line['infrasp2'], line['infrasp2_rank'], line['infrasp2_author'],
            line['infrasp3'], line['infrasp3_rank'], line['infrasp3_author'],
            line['infrasp4'], line['infrasp4_rank'], line['infrasp4_author'],
            line['genus_id'],
            line['label_distribution'],
            line['habit_id'],
            line['flower_color_id'],
            line['awards'],
            line['_created'], line['_last_updated']])
    print 'converted'


prov_type_map = {"Wild": 'Wild',
                 "Propagule of cultivated wild plant": 'Cultivated',
                 "Not of wild source": 'NotWild',
                 "Insufficient Data": 'InsufficientData',
                 "Unknown": "Unknown",
                 None: None,
                 'None': None}

wild_prov_map = {"Wild native": 'WildNative',
                 "Wild non-native": 'WildNonNative',
                 "Cultivated native": 'CultivatedNative',
                 "Insufficient Data": 'InsufficientData',
                 "Unknown": 'Unknown',
                 None: None,
                 'None': None}


def do_accession(filename):
    reader = UnicodeReader(open(filename))

    accession_filename = os.path.join(dst_path, 'accession.txt')
    accession_columns = ['id', 'code', 'prov_type', 'wild_prov_status',
                         'date_accd', 'date_recvd', 'quantity_recvd',
                         'recvd_type', 'id_qual', 'id_qual_rank', 'private',
                         'species_id', 'intended_location_id',
                         'intended2_location_id', '_created', '_last_updated']
    accession_writer = create_writer(accession_filename, accession_columns)

    for line in reader:
        prov_type = prov_type_map[line['prov_type']]
        wild_prov_status = wild_prov_map[line['wild_prov_status']]
        accession_writer.writerow([line['id'], line['code'], prov_type,
                                   wild_prov_status, line['date'], None,
                                   None, None, line['id_qual'],
                                   line['id_qual_rank'], line['private'],
                                   line['species_id'], None, None,
                                   line['_created'], line['_last_updated']])
    print 'converted'

acc_type_map = {'Plant': 'Plant',
                'Seed/Spore': 'Seed',
                'Vegetative Part': 'Vegetative',
                'Tissue Culture': 'Tissue',
                'Other': 'Other',
                None: None}


def do_plant(filename):
    reader = UnicodeReader(open(filename))

    plant_filename = os.path.join(dst_path, 'plant.txt')
    plant_columns = ['id', 'code', 'acc_type', 'memorial',
                     'quantity', 'accession_id', 'location_id', '_created',
                     '_last_updated']
    plant_writer = create_writer(plant_filename, plant_columns)

    for line in reader:
        if line['acc_status'] == 'Dead':
            quantity = 0
        else:
            quantity = 1
        acc_type = acc_type_map[line['acc_type']]
        plant_writer.writerow([line['id'], line['code'], acc_type, False,
                               quantity, line['accession_id'],
                               line['location_id'], line['_created'],
                               line['_last_updated']])
    print 'converted'


def do_bauble(filename):
    # should only have to convert the version string
    reader = UnicodeReader(open(filename))
    columns = ['id', 'name', 'value', '_created', '_last_updated']
    bauble_filename = os.path.join(dst_path, 'bauble.txt')
    writer = create_writer(bauble_filename, columns)
    for line in reader:
        if line['name'] == 'version':
            value = '1.0.0'
        else:
            value = line['value']
        writer.writerow([line['id'], line['name'], value, line['_created'],
                         line['_last_updated']])
    print 'converted'


def do_location(filename):
    reader = UnicodeReader(open(filename))

    location_filename = os.path.join(dst_path, 'location.txt')
    location_columns = ['id', 'code', 'name', 'description', '_created',
                        '_last_updated']
    location_writer = create_writer(location_filename, location_columns)
    location_codes = set()
    for line in reader:
        code = ''
        # try to uniquify the name for the code
        parts = line['site'].split(' ')
        if len(parts) == 1:
            code = line['site'][0:3].upper()
        else:
            for part in parts:
                try:
                    int(part)
                    code += part
                except:
                    code += part[0:2].upper()
        if code in location_codes:
            raise Exception('code not unique: %s' % code)
        location_codes.add(code)
        location_writer.writerow([line['id'], code, line['site'],
                                  line['description'], line['_created'],
                                  line['_last_updated']])
    print 'converted'


def copy_file(filename):
    """
    Copy filename to the destination for new files
    """
    shutil.copy(filename, dst_path)
    print 'copied'


def skip_file(filename):
    """
    Do nothing with the file, not even copy it.
    """
    print 'skipped'


file_map = {
    'accession_note.txt': copy_file,
    'accession.txt': copy_file,
    'bauble.txt': copy_file,
    'collection.txt': copy_file,
    'color.txt': copy_file,
    'default_vernacular_name.txt': copy_file,
    'family_note.txt': copy_file,
    'family_synonym.txt': copy_file,
    'family.txt': copy_file,
    'genus_note.txt': copy_file,
    'genus_synonym.txt': copy_file,
    'genus.txt': copy_file,
    'geography.txt': copy_file,
    'habit.txt': copy_file,
    'history.txt': copy_file,
    'location.txt': copy_file,
    'plant_change.txt': copy_file,
    'plant_note.txt': copy_file,
    'plant_prop.txt': copy_file,
    'plant_status.txt': copy_file,
    'plant.txt': copy_file,
    'plugin.txt': copy_file,
    'propagation.txt': copy_file,
    'prop_cutting_rooted.txt': copy_file,
    'prop_cutting.txt': copy_file,
    'prop_seed.txt': copy_file,
    'source_detail.txt': copy_file,
    'source.txt': copy_file,
    'species_distribution.txt': copy_file,
    'species_note.txt': copy_file,
    'species_synonym.txt': copy_file,
    'species.txt': copy_file,
    'tagged_obj.txt': copy_file,
    'tag.txt': copy_file,
    'verification.txt': copy_file,
    'vernacular_name.txt': copy_file,
    'voucher.txt': copy_file,
    }

# for each text file in src_path call the appropriate entry in file_map
for f in glob.glob(os.path.join(src_path, "*.txt")):
    basename = os.path.basename(f)
    print basename,
    if basename not in file_map:
        print "** don't know what to do with: %s" % f
        sys.exit(1)
    if not file_map[basename]:
        shutil.copy(f, dst_path)
        print 'copied'
    else:
        file_map[basename](f)


# copy the habit
rootdir = os.path.split(bauble.__file__)[0]
habit_file = os.path.join(rootdir, 'plugins', 'plants', 'default', 'habit.txt')
shutil.copy(habit_file, dst_path)
