#!/usr/bin/env python
#
# bauble-upgrade-0.9-to-1.0.py
#
# export CSV files from a Bauble 0.9 database to save them as CSV
# files that can be imported into a Bauble 1.0 databa
#

import csv
import glob
from optparse import OptionParser
import os
import shutil
import sys


import bauble
if bauble.version_tuple[0] != '1' and bauble.version_tuple[1] != '0':
    print("Bauble 1.0 must be installed")
    print((bauble.version))
    print((bauble.version_tuple))
    sys.exit(1)

import bauble.utils as utils
from bauble.plugins.imex.csv_ import UnicodeReader, UnicodeWriter


parser = OptionParser()
#parser.add_option('-s', '--src', dest='src', help='the source path',
#                  metavar='SRC')
parser.add_option('-f', '--force', dest='force', action='store_true',
                  help='the source path')
(options, args) = parser.parse_args()

if not args:
    print((parser.error('a directory with a dumped CSV files is required')))



#dummy_date = "1902-01-01"
#dummy_timestamp = '1902-01-01 00:00:00.0-00:00'
dummy_date = None
dummy_timestamp = None


# a directory full of CSV text files exported from Bauble 0.8
src_path = args[0]
if not os.path.exists(src_path):
    parser.error('%s does not exist' % src_path)

# where to put the new files
dst_path = os.path.join(src_path, '1.0')
if os.path.exists(dst_path) and options.force:
    shutil.rmtree(dst_path)
elif os.path.exists(dst_path):
    response = eval(input('%s exists.  Would you like to delete it? ' \
                             % dst_path))
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


class NoteWriter(object):

    def __init__(self, filename, parent_id_column, id_start=1):
        self.id_ctr = id_start
        self.columns = ['id', 'note', 'date', 'user', 'category', '_created',
                        '_last_updated']
        self.columns.append(parent_id_column)
        self.writer = create_writer(filename, self.columns)

    def write(self, note, parent_id, date=dummy_date, category=None):
        new_note = [self.id_ctr, note, date, None, category, dummy_timestamp,
                    dummy_timestamp, parent_id]
        self.writer.writerow(new_note)
        self.id_ctr += 1


def do_family(filename):
    """
    Convert the family.txt
    """
    from bauble.plugins.plants import Family, FamilyNote, FamilySynonym
    reader = UnicodeReader(open(filename))

    family_filename = os.path.join(dst_path, 'family.txt')
    family_writer = UnicodeWriter(open(family_filename, "wb"))
    family_columns = ['id', 'family', 'qualifier', '_created', '_last_updated']
    family_writer.writerow(family_columns)

    note_filename = os.path.join(dst_path, 'family_note.txt')
    note_writer = NoteWriter(note_filename, 'family_id')

    for line in reader:
        note = line.pop('notes')
        family_writer.writerow([line['id'], line['family'], line['qualifier'],
                               line['_created'], line['_last_updated']])
        if note:
            note_writer.write(note, line['id'])


def do_genus(filename):
    """
    Convert genus.txt
    """
    from bauble.plugins.plants import Genus, GenusNote

    reader = UnicodeReader(open(filename))

    genus_filename = os.path.join(dst_path, 'genus.txt')
    genus_writer = UnicodeWriter(open(genus_filename, "wb"))
    genus_columns = ['id', 'genus', 'hybrid', 'author', 'qualifier',
                     'family_id', '_created', '_last_updated']
    genus_writer.writerow(genus_columns)

    note_filename = os.path.join(dst_path, 'genus_note.txt')
    note_writer = NoteWriter(note_filename, 'genus_id')

    for line in reader:
        note = line.pop('notes')
        genus_writer.writerow([line['id'], line['genus'], line['hybrid'],
                               line['author'], line['qualifier'],
                               line['family_id'], line['_created'],
                               line['_last_updated']])
        if note:
            note_writer.write(note, line['id'])


def do_species(filename):
    """
    Convert species.txt
    """
    from bauble.plugins.plants import Species, SpeciesNote
    reader = UnicodeReader(open(filename))

    species_filename = os.path.join(dst_path, 'species.txt')
    species_writer = UnicodeWriter(open(species_filename, "wb"))
    species_columns = ['id', 'sp', 'sp2', 'sp_author', 'hybrid', 'sp_qual',
                       'cv_group', 'trade_name', 'infrasp1', 'infrasp1_rank',
                       'infrasp1_author', 'infrasp2', 'infrasp2_rank',
                       'infrasp2_author', 'infrasp3', 'infrasp3_rank',
                       'infrasp3_author', 'infrasp4', 'infrasp4_rank',
                       'infrasp4_author', 'genus_id', 'label_distribution',
                       'habit_id', 'flower_color_id', 'awards', '_created',
                       '_last_updated']
    species_writer.writerow(species_columns)

    note_filename = os.path.join(dst_path, 'species_note.txt')
    note_writer = NoteWriter(note_filename, 'species_id')

    for line in reader:
        # in bauble 0.9 if sp_hybrid was not None then the infrasp held sp2
        hybrid = False
        if line['sp_hybrid']:
            hybrid = True
            if line['infrasp_rank'] or line['infrasp_author']:
                print(('**', line['sp'], line['infrasp'], line['infrasp_rank'], \
                    line['infrasp_author']))
            sp2 = line['infrasp']
            infrasp1 = None
        else:
            sp2 = None
            infrasp1 = line['infrasp']

        species_writer.writerow([line['id'], line['sp'], sp2,
                                 line['sp_author'], hybrid,
                                 line['sp_qual'], line['cv_group'],
                                 line['trade_name'], infrasp1,
                                 line['infrasp_rank'], line['infrasp_author'],
                                 None, None, None, # infrasp2
                                 None, None, None, # infrasp3
                                 None, None, None, # infrasp4
                                 line['genus_id'],
                                 None, # label_distribution
                                 None, # habit_id,
                                 None, # flower_color_id
                                 None, # awards
                                 line['_created'], line['_last_updated']])

        note = line.pop('notes')
        if note:
            note_writer.write(note, line['id'])


geography_id_map = {}

def do_geography(filename):
    # geography changed slightly with Bauble 1.0 so just copy the
    # default file and hope the ids are the same
    rootdir = os.path.split(bauble.__file__)[0]
    default_file = os.path.join(rootdir, 'plugins', 'plants', 'default',
                                'geography.txt')
    default_reader = UnicodeReader(open(default_file))
    geography_reader = UnicodeReader(open(filename))
    columns = ['id', 'name', 'tdwg_code', 'iso_code', 'parent_id', '_created',
               '_last_updated']

    writer = create_writer(os.path.join(dst_path, filename), columns)

    # build map of default tdwg codes to geography.id
    default_tdwg_map = {}
    for line in default_reader:
        default_tdwg_map[line['tdwg_code']] = line['id']

    # built a map of the default geography id's to 0.9 geography.id's
    for line in geography_reader:
        # TODO: this might miss some id's and might need to be
        # corrected but it works for us at the moment
        try:
            default_id = default_tdwg_map[line['tdwg_code']]
        except:
            pass
            # print line
            # print line['tdwg_code'].partition('-')
            # head, middle, tail = line['tdwg_code'].partition('-')
            # default_id = default_tdwg_map[head]
        geography_id_map[line['id']] = default_id

    # manually add 'Cultivated'
    geography_id_map[None] = default_tdwg_map[None]

    # now that the map is built just copy over the default geography
    shutil.copy(default_file, dst_path)


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


next_accession_note_id = -1

def do_accession(filename):
    from bauble.plugins.garden import Accession, AccessionNote
    reader = UnicodeReader(open(filename))

    accession_filename = os.path.join(dst_path, 'accession.txt')
    accession_columns = ['id', 'code', 'prov_type', 'wild_prov_status',
                         'date_accd', 'date_recvd', 'quantity_recvd',
                         'recvd_type', 'id_qual', 'id_qual_rank', 'private',
                         'species_id', 'intended_location_id',
                         'intended2_location_id', '_created', '_last_updated']
    accession_writer = create_writer(accession_filename, accession_columns)

    note_filename = os.path.join(dst_path, 'accession_note.txt')
    note_writer = NoteWriter(note_filename, 'accession_id')

    for line in reader:
        prov_type = prov_type_map[line['prov_type']]
        wild_prov_status = wild_prov_map[line['wild_prov_status']]
        accession_writer.writerow([line['id'], line['code'], prov_type,
                                   wild_prov_status, line['date'], None,
                                   None, None, line['id_qual'],
                                   line['id_qual_rank'], line['private'],
                                   line['species_id'], None, None,
                                   line['_created'], line['_last_updated']])
        note = line.pop('notes')
        if note:
            note_writer.write(note, line['id'])

    next_accession_note_id = note_writer.id_ctr

acc_type_map = {'Plant': 'Plant',
                'Seed/Spore': 'Seed',
                'Vegetative Part': 'Vegetative',
                'Tissue Culture': 'Tissue',
                'Other': 'Other',
                None: None}

def do_plant(filename):
    from bauble.plugins.garden import Plant, PlantNote
    reader = UnicodeReader(open(filename))

    plant_filename = os.path.join(dst_path, 'plant.txt')
    plant_columns = ['id', 'code', 'acc_type', 'memorial',
                     'quantity', 'accession_id', 'location_id', '_created',
                     '_last_updated']
    plant_writer = create_writer(plant_filename, plant_columns)

    note_filename = os.path.join(dst_path, 'plant_note.txt')
    note_writer = NoteWriter(note_filename, 'plant_id')

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
        note = line.pop('notes')
        if note:
            note_writer.write(note, line['id'])


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
    #del writer


def do_location(filename):
    from bauble.plugins.garden import Location
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

def do_vernacular(filename):
    from bauble.plugins.plants import VernacularName
    reader = UnicodeReader(open(filename))

    vernacular_filename = os.path.join(dst_path, 'vernacular_name.txt')
    vernacular_columns = ['id', 'name', 'language', 'species_id', '_created',
                        '_last_updated']
    vernacular_writer = create_writer(vernacular_filename, vernacular_columns)
    vernacular_codes = set()
    for line in reader:
        if not line['name']:
            continue
        vernacular_writer.writerow([line['id'], line['name'], line['language'],
                                  line['species_id'], line['_created'],
                                  line['_last_updated']])


def do_species_distribution(filename):
    from bauble.plugins.plants import SpeciesDistribution
    reader = UnicodeReader(open(filename))

    distribution_filename = os.path.join(dst_path, 'species_distribution.txt')
    distribution_columns = ['id', 'species_id', 'geography_id', '_created',
                            '_last_updated']
    writer = create_writer(distribution_filename, distribution_columns)
    for line in reader:
        geo_id = geography_id_map[line['geography_id']]
        writer.writerow([line['id'], line['species_id'], geo_id,
                         line['_created'], line['_last_updated']])



def copy_file(filename):
    """
    Copy filename to the destination for new files
    """
    shutil.copy(filename, dst_path)


def skip_file(filename):
    """
    Do nothing with the file, not even copy it.
    """
    print('- skipping')


file_map = {'accession.txt': do_accession,
            'bauble.txt': do_bauble,
            'collection.txt': skip_file,
            'default_vernacular_name.txt': copy_file,
            'donation.txt': skip_file,
            'donor.txt': skip_file,
            'family_synonym.txt': copy_file,
            'family.txt': do_family,
            'genus_synonym.txt': copy_file,
            'genus.txt': do_genus,
            #'geography.txt': do_geography,
            'geography.txt': skip_file,
            'location.txt': do_location,
            'plant_history.txt': skip_file,
            'plant.txt': do_plant,
            'plugin.txt': skip_file,
            'species_distribution.txt': do_species_distribution,
            'species_synonym.txt': copy_file,
            'species.txt': do_species,
            'tagged_obj.txt': copy_file,
            'tag.txt':  copy_file,
            'verification.txt': skip_file,
            'vernacular_name.txt': do_vernacular}

# geography needs to be done first
do_geography(os.path.join(src_path, "geography.txt"))

# for each text file in src_path call the appropriate entry in file_map
for f in glob.glob(os.path.join(src_path, "*.txt")):
    basename = os.path.basename(f)
    print(basename)
    if basename not in file_map:
        print(("** don't know what to do with: %s" % f))
        sys.exit(1)
    if not file_map[basename]:
        shutil.copy(f, dst_path)
    else:
        file_map[basename](f)


source_type_map = {'Expedition': 'Expedition',
                   "Gene bank": "GeneBank",
                   "Botanic Garden or Arboretum" : "BG",
                   "Research/Field Station": 'Research/FieldStation',
                   "Staff member": "Staff",
                   "University Department": 'UniversityDepartment',
                   "Horticultural Association/Garden Club": 'Club',
                   "Municipal department": 'MunicipalDepartment',
                   "Nursery/Commercial": 'Commercial',
                   "Individual": "Individual",
                   "Other": "Other",
                   "Unknown": "Unknown"}

# handle the source/donor/collection/donation conversion seperately
def do_source():
    source_writer = ''
    detail_columns = ['id', 'name', 'description', 'source_type', '_created',
                      '_last_updated']
    detail_writer = create_writer(os.path.join(dst_path, 'source_detail.txt'),
                                  detail_columns)
    detail_ids = set()
    donor_reader = UnicodeReader(open(os.path.join(src_path, 'donor.txt')))

    for line in donor_reader:
        description = ''
        if line['address']:
            description = '%s\n' % line['address']
        if line['email']:
            description += 'email: %s' % line['email']
        if line['tel']:
            description += '\ntel: %s' % line['tel']
        if line['fax']:
            description += '\nfax: %s' % line['fax']
        if line['notes']:
            description += '\n%s' % line['notes']

        source_type = ''
        if line['donor_type']:
            source_type = source_type_map[line['donor_type']]
        detail_writer.writerow([line['id'], line['name'], description,
                               source_type, line['_created'],
                               line['_last_updated']])
        detail_ids.add(int(line['id']))

    source_columns = ['id', 'sources_code', 'accession_id', 'source_detail_id',
                      'propagation_id', 'plant_propagation_id', '_created',
                      '_last_updated']
    source_writer = create_writer(os.path.join(dst_path, 'source.txt'),
                                  source_columns)
    source_ids = set()

    donation_reader = UnicodeReader(open(os.path.join(src_path,'donation.txt')))
    note_writer = NoteWriter("accession_note.txt", 'accession_id',
                             id_start=next_accession_note_id)
    for line in donation_reader:
        source_writer.writerow([line['id'], None, line['accession_id'],
                                line['donor_id'], # same as source_id
                                None, None, line['_created'],
                                line['_last_updated']])
        source_ids.add(int(line['id']))
        note_writer.write(line['notes'], line['accession_id'],
                         category='Donation')

    collection_reader = UnicodeReader(open(os.path.join(src_path,
                                                        'collection.txt')))
    collection_columns = ['id', 'collector', 'collectors_code', 'date',
                          'locale', 'latitude', 'longitude', 'gps_datum',
                          'geo_accy', 'elevation', 'elevation_accy', 'habitat',
                          'notes', 'geography_id', 'source_id',
                          '_created', '_last_updated']
    collection_writer = create_writer(os.path.join(dst_path, 'collection.txt'),
                                      collection_columns)
    # create one SourceDetail for all the old collection
    coll_detail_id = max(detail_ids) + 1
    coll_detail_name = 'Old Collection'
    coll_detail_desc = "These are the collections that were made before Bauble 1.0 that didn't fit the new Bauble database format"
    detail_writer.writerow([coll_detail_id, coll_detail_name, coll_detail_desc,
                           'Expedition', dummy_timestamp, dummy_timestamp])
    next_source_id = max(source_ids) + 1
    for line in collection_reader:
        source_writer.writerow([next_source_id, # sources_code
                                None,
                                line['accession_id'], # accession_id
                                coll_detail_id, # source_detail_id
                                None,  # propagation_id
                                None,  # plant_propagation_id
                                line['_created'],
                                line['_last_updated']])
        geo_id = geography_id_map[line['geography_id']]
        collection_writer.writerow([line['id'], line['collector'],
                                    line['collectors_code'], line['date'],
                                    line['locale'], line['latitude'],
                                    line['longitude'], line['gps_datum'],
                                    line['geo_accy'], line['elevation'],
                                    line['elevation_accy'], line['habitat'],
                                    line['notes'], geo_id,
                                    next_source_id,
                                    line['_created'], line['_last_updated']])
        next_source_id += 1


do_source()

# copy the habit
rootdir = os.path.split(bauble.__file__)[0]
habit_file = os.path.join(rootdir, 'plugins', 'plants', 'default', 'habit.txt')
shutil.copy(habit_file, dst_path)
