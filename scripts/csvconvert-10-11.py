#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# csv convert 1.0 to 1.1
#
# first: use Ghini/Bauble 1.0 to export your database as CSV files; then run
# this script to convert the exported CSV files into the newer format;
# finally use Ghini 1.1 to import the converted export in a new database.
#

import glob
import argparse
import os
import shutil
import sys
from functools import partial

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
from bauble.plugins.plants import itf2
itf2._ = lambda x: x


parser = argparse.ArgumentParser(
    description='csv convert 1.0 to 1.1')
parser.add_argument('source')
parser.add_argument('-o', '--output', dest='destination', default='')
parser.add_argument('-f', '--force', dest='force', action='store_true',
                    help='force overwriting destination')
args = parser.parse_args()

if not args:
    print parser.error('a directory with a dumped CSV files is required')


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
    print 'done'


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
            [line['id'], line['genus'], '',
             line['author'], line['qualifier'],
             line['family_id'], line['_created'],
             line['_last_updated']])
    print 'done'


def do_species(filename):
    """
    Convert species.txt
    """
    reader = UnicodeReader(open(filename))

    species_filename = os.path.join(dst_path, 'species.txt')
    writer = UnicodeWriter(open(species_filename, "wb"))
    columns = [
        'id', 'epithet', 'hybrid_marker', 'author', 'aggregate', 'cv_group',
        'trade_name', 'infrasp1', 'infrasp1_rank', 'infrasp1_author',
        'infrasp2', 'infrasp2_rank', 'infrasp2_author',
        'infrasp3', 'infrasp3_rank', 'infrasp3_author',
        'infrasp4', 'infrasp4_rank', 'infrasp4_author',
        'genus_id', 'label_distribution', 'bc_distribution', 'habit_id',
        'flower_color_id', 'awards', '_created', '_last_updated']
    writer.writerow(columns)

    post_process_hyop = []
    for line in reader:
        line = dict(line)
        if line['sp'] and (line['sp'].find(u'×') > 0):
            line['hybrid_marker'] = 'H'
            line['epithet'] = ''
            post_process_hyop.append(dict(line))
        else:
            line['hybrid_marker'] = (line['hybrid'] == 'True') and u'×' or ''
            line['epithet'] = line['sp']
        line['author'] = line['sp_author']
        line['aggregate'] = line['sp_qual']
        writer.writerow([line[k] for k in columns])

    hybrid_operand = os.path.join(dst_path, 'hybrid_operands.txt')
    hyop_columns = ['child_id', 'parent_id', 'role']
    hyop_writer = create_writer(hybrid_operand, hyop_columns)
    if post_process_hyop:
        print post_process_hyop

    print 'done'


prov_type_map = {'Wild': 'W',
                 'Cultivated': 'Z',
                 'NotWild': 'G',
                 'InsufficientData': 'U',
                 "Unknown": 'U',
                 None: None,
                 'None': None}

wild_prov_map = {'WildNative': 'Wild native',
                 'WildNonNative': 'Wild non-native',
                 'CultivatedNative': 'Cultivated native',
                 'InsufficientData': None,
                 'Unknown': None,
                 None: None,
                 'None': None}


def do_accession(filename):
    reader = UnicodeReader(open(filename))

    basename = os.path.basename(filename)
    accession_filename = os.path.join(dst_path, basename)
    columns = ['id', 'code', 'prov_type', 'wild_prov_status',
               'date_accd', 'date_recvd', 'quantity_recvd',
               'recvd_type', 'id_qual', 'id_qual_rank', 'private',
               'species_id', '_created', '_last_updated']
    writer = create_writer(accession_filename, columns)
    intended_location = os.path.join(dst_path, 'intended_location.txt')
    il_columns = ['accession_id', 'location_id', 'quantity', 'planned_date']
    il_writer = create_writer(intended_location, il_columns)

    for line in reader:
        line = dict(line)
        line['prov_type'] = prov_type_map[line['prov_type']]
        line['wild_prov_status'] = wild_prov_map[line['wild_prov_status']]
        writer.writerow([line[k] for k in columns])
        if line['intended_location_id']:
            il_writer.writerow(
                [line['id'], line['intended_location_id'], 0, None])
        if line['intended2_location_id']:
            il_writer.writerow(
                [line['id'], line['intended2_location_id'], 0, None])
    print 'done'

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
    print 'done'


def do_copy(filename, non_nullable=[], new_name=None, change=[]):
    """copy the file but consider variations on theme

    skip rows with unacceptable null values.
    write to new_name.
    change: [(key_field, key_value, value_field, replacement), ...]
    """
    reader = UnicodeReader(open(filename))
    columns = reader.reader.fieldnames
    if new_name:
        basename = new_name
        print 'as', new_name, '...',
    else:
        basename = os.path.basename(filename)
    bauble_filename = os.path.join(dst_path, basename)
    writer = create_writer(bauble_filename, columns)
    skipped = 0
    for line in reader:
        if any(line[k] is None for k in non_nullable):
            skipped += 1
            continue
        line = dict(line)
        for key_field, key_value, value_field, new_value in change:
            if line[key_field] == key_value:
                line[value_field] = new_value
        writer.writerow([line[k] for k in columns])
    if non_nullable:
        print 'skipped', skipped, '...',
    print 'done'


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
    print 'done'


def copy_file(filename):
    """
    Copy filename to the destination for new files
    """
    shutil.copy(filename, dst_path)
    print 'done'


def skip_file(filename):
    """
    Do nothing with the file, not even copy it.
    """
    print 'skipped'


file_map = {
    'bauble.txt': partial(do_copy,
                          change=[('name', 'version', 'value', '1.1.0')]),
    'collection.txt': copy_file,
    'color.txt': copy_file,
    'family.txt': do_family,
    'family_note.txt': copy_file,
    'family_synonym.txt': copy_file,
    'genus.txt': do_genus,
    'genus_note.txt': copy_file,
    'genus_synonym.txt': copy_file,
    'species.txt': do_species,
    'species_distribution.txt': copy_file,
    'species_note.txt': copy_file,
    'species_synonym.txt': copy_file,
    'geography.txt': partial(do_copy,
                             new_name='gheography.txt'),
    'habit.txt': copy_file,
    'history.txt': copy_file,
    'location.txt': copy_file,
    'accession.txt': do_accession,
    'accession_note.txt': copy_file,
    'plant.txt': copy_file,
    'plant_change.txt': copy_file,
    'plant_note.txt': copy_file,
    'plant_prop.txt': copy_file,
    'plant_status.txt': copy_file,
    'plugin.txt': copy_file,
    'propagation.txt': copy_file,
    'prop_cutting_rooted.txt': copy_file,
    'prop_cutting.txt': copy_file,
    'prop_seed.txt': copy_file,
    'source_detail.txt': copy_file,
    'source.txt': copy_file,
    'tagged_obj.txt': copy_file,
    'tag.txt': copy_file,
    'verification.txt': copy_file,
    'vernacular_name.txt': partial(do_copy,
                                   non_nullable=['name', 'species_id']),
    'default_vernacular_name.txt': copy_file,
    'voucher.txt': copy_file,
    }

# for each text file in src_path call the appropriate entry in file_map
for f in glob.glob(os.path.join(src_path, "*.txt")):
    basename = os.path.basename(f)
    print basename, '...',
    if basename not in file_map:
        print "** don't know what to do with: %s" % f
        sys.exit(1)
    if not file_map[basename]:
        shutil.copy(f, dst_path)
        print 'done'
    else:
        file_map[basename](f)


# copy the habit
rootdir = os.path.split(bauble.__file__)[0]
habit_file = os.path.join(rootdir, 'plugins', 'plants', 'default', 'habit.txt')
shutil.copy(habit_file, dst_path)
