#!/usr/bin/python

import sys, os, glob, csv, zipfile

# NOTE: for some reason the files for the old family names downloaded from the
# kew website don't end in .TXT like the rest
# these have to be renamed manually
# to rename then use:
# for F in `ls | grep -v .TXT | grep AE` ; do mv $F $F.TXT ; done

# TODO: should create synonym for the family replacements

#src = os.path.join(os.environ['HOME'], 'tmp', 'kew')
src = os.path.join(os.environ['HOME'], 'devel', 'bauble', 'data', 'kew-families.zip')
dst = os.path.join(os.environ['HOME'], 'devel', 'bauble', 'data')
family_rename_map = {'COMPOSITAE': 'ASTERACEAE',
                     'CRUCIFERAE': 'BRASSICACEAE',
                     'GRAMINEAE': 'POACEAE',
                     'GUTTIFERAE': 'CLUSIACEA',
                     'LABIATAE': 'LAMIACEAE',
                     'LEGUMINOSAE-CAESALPINIOIDEAE': 'FABACEAE',
                     'LEGUMINOSAE-MIMOSOIDEAE': 'FABACEAE',
                     'LEGUMINOSAE-PAPILIONOIDEAE': 'FABACEAE',
                     'PALMAE': 'ARECACEAE',
                     'UMBELLIFERAE': 'APIACEAE',
                   }

gen_columns = '"id","hybrid","genus","author","synonymID","familyID"'
fam_columns = '"id","family"'

genera_file = file(os.path.join(dst, 'kew_genera.txt'), 'w+')
genera_file.write('%s\n' % gen_columns)
genera = csv.writer(genera_file, quoting=csv.QUOTE_NONNUMERIC)

families = file(os.path.join(dst, 'kew_families.txt'), 'w+')
families.write('%s\n' % fam_columns)

fam_id = 1 # the start id

# look up family id's from here, mostly to avoid
# redundancy for the legumes
family_map = {}

if os.path.isdir(src):
    files = sorted(glob.glob(os.path.join(src, '*.TXT')))
    file_read = lambda f: open(f).readlines()
else:
    z = zipfile.ZipFile(src, 'r')
    files = z.namelist()
    file_read = lambda f: z.read(f).strip().split('\n')

for f in sorted(files):
    fam = os.path.basename(f)[:-4]
    if fam in family_rename_map:
        fam = family_rename_map[fam]
    fam = fam.capitalize()

    if fam not in family_map:
        family_map[fam] = fam_id
        fam_id+=1
        families.write('%d,"%s"\n' % (family_map[fam], fam))

    for i in csv.reader(file_read(f)):
        # TODO: the ^M needs to be stripped from the lines
        genera.writerow(i + [family_map[fam]])

try:
    z.close()
except NameError as e:
    print('wasn\'t a zip')

genera_file.close()
families.close()



