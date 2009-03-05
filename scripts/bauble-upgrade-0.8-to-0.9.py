#!/usr/bin/env python
#
# bauble-upgrade-0.8-to-0.9.py
#
# export CSV files from a Bauble 0.8 database to save them as CSV
# files that can be imported into a Bauble 0.9 databa
#

# What has changed from 0.8 -> 0.9
# 1. species.id_qual_rank field added
# 2. tag.description added
# 3. the datetime format changed

import csv
import os
import shutil
import sys
from optparse import OptionParser

parser = OptionParser()
#parser.add_option('-s', '--src', dest='src', help='the source path',
#                  metavar='SRC')
(options, args) = parser.parse_args()

if not args:
    print parser.error('a directory with a dumped CSV files is required')


# a directory full of CSV text files exported from Bauble 0.8
src_path = args[0]
if not os.path.exists(src_path):
    parser.error('%s does not exist' % src_path)

# where to put the new files
dst_path = os.path.join(src_path, '0.9')
if os.path.exists(dst_path):
    response = raw_input('%s exists.  Would you like to delete it? ' %dst_path)
    if response in ('y', 'Y'):
        shutil.rmtree(dst_path)
os.mkdir(dst_path)


def to_unicode(obj, encoding='utf-8'):
    """
    Return obj converted to unicode.  If obj is already a unicode
    object it will no try to decode it to converted it to <encoding>
    but will just return the original obj
    """
    if isinstance(obj, basestring):
        if not isinstance(obj, unicode):
            obj = unicode(obj, encoding)
    else:
        try:
            obj = unicode(obj, encoding)
        except:
            obj = unicode(str(obj), encoding)
    return obj



class UnicodeReader:

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        self.reader = csv.DictReader(f, dialect=dialect, **kwds)
        self.encoding = encoding


    def next(self):
        row = self.reader.next()
        t = {}
        for k, v in row.iteritems():
            t[k] = to_unicode(v, self.encoding)
        return t


    def __iter__(self):
        return self



class UnicodeWriter:

    def __init__(self, f, fieldnames, dialect=csv.excel, encoding="utf-8",
                 **kwds):
        f.write('%s\n' % ','.join(fieldnames))
        self.writer = csv.DictWriter(f, fieldnames, dialect=dialect, **kwds)
        self.encoding = encoding


    def writerow(self, row):
        t = []
        for s in row:
            t.append(to_unicode(s, self.encoding))
        self.writer.writerow(t)


    def writerows(self, rows):
        # ** NOTE: this isn't doing any unicode conversion
        self.writer.writerows(rows)
        #for row in rows:
        #    self.writerow(row)


def check_dates():
    """
    Check the dates are correct.
    """
    # Does it really matter if we change the dates, the only thing
    # that changes is the microseconds which we don't really care
    # about anyways....the only reason it might be worth it is if we
    # want to write some plugin that shows the order when things were
    # changed and although unlikely, two things could have been
    # changed at almost the same time in which case the microseconds would
    # help
    pass

def do_all():
    """
    Make sure the date formats are correct.
    """
    pass


def build_map(filename):
    f = os.path.join(src_path, filename)
    reader = UnicodeReader(open(f))
    id_map = {}
    for line in reader:
        #print line
        id_map[line['id']] = line
    return id_map


def do_accession():
    """
    Ask the user to choose an infrasp_rank.
    """
    # TODO: would probably be easier if the id_qual is not None then
    # set id_qual_rank to sp. and be done with it
    species_map = build_map('species.txt')
    genus_map = build_map('genus.txt')

    src = os.path.join(src_path, 'accession.txt')
    reader = UnicodeReader(open(src))

    name_parts = ['genus', 'sp', 'infrasp_rank', 'infrasp']
    out = []
    for line in reader:
        #if False:
        if line['id_qual']:
            line['id_qual_rank'] = 'sp'
#             sp = species_map[line['species_id']]
#             sp['genus'] = genus_map[sp['genus_id']]['genus']
#             print '-----'
#             print '%s (%s)' % (' '.join([sp[p] for p in name_parts]),
#                                line['code'])
#             print 'id_qual: %s' % line['id_qual']
#             response = raw_input('(g)enus, (s)p or (i)nfrasp?: ')
#             if response == 'd':
#                 line['id_qual'] = ''
#                 line['id_qual_rank'] = 'sp'
#             elif response in ('genus', 'sp', 'infrasp'):
#                 line['id_qual_rank'] = response
#             elif response == 'g':
#                 line['id_qual_rank'] = 'genus'
#             elif response == 's':
#                 line['id_qual_rank'] = 'sp'
#             elif response == 'i':
#                 line['id_qual_rank'] = 'infrasp'
#             elif response == '':
#                 pass # do nothing
#             else:
#                 raise ValueError('invalid value')
#             print line
        out.append(line)

    fieldnames = reader.reader.fieldnames
    fieldnames.append('id_qual_rank')
    dst = os.path.join(dst_path, 'accession.txt')
    writer = UnicodeWriter(open(dst, 'w'), fieldnames=fieldnames)
    writer.writerows(out)


def do_bauble():
    """
    Drop the registry and version.
    """
    src = os.path.join(src_path, 'bauble.txt')
    reader = UnicodeReader(open(src))
    out = []
    for line in reader:
        if line['name'] == 'version':
            line['value'] = '0.9.0'
        if line['name'] != 'registry':
            out.append(line)
    fieldnames = reader.reader.fieldnames
    dst = os.path.join(dst_path, 'bauble.txt')
    writer = UnicodeWriter(open(dst, 'w'), fieldnames=fieldnames)
    writer.writerows(out)

#update_funcs = ['species.txt': do_species,
#                'bauble.txt', do_bauble]
do_accession()
do_bauble()

copy_list = ['collection.txt', 'default_vernacular_name.txt',
             'donation.txt', 'donor.txt', 'family_synonym.txt', 'family.txt',
             'genus.txt', 'genus_synonym.txt', 'geography.txt', 'location.txt',
             'plant_history.txt', 'plant.txt', 'species.txt',
             'species_distribution.txt',
             'species_synonym.txt', 'tagged_obj.txt', 'tag.txt',
             'verification.txt', 'vernacular_name.txt']


for f in copy_list:
    shutil.copy(os.path.join(src_path, f), dst_path)
