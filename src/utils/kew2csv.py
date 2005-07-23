#!/usr/bin/python

import os, glob, csv

# NOTE: for some reason the files for the old family names downloaded from the 
# kew website don't end in .TXT like the rest
# these have to be renamed manually
# to rename then use:
# for F in `ls | grep -v .TXT | grep AE` ; do mv $F $F.TXT ; done

path = '/home/brett/tmp/kew/'
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

genera_file = file("kew_genera.txt", "w+")
genera_file.write(gen_columns + "\n")
genera = csv.writer(genera_file, quoting=csv.QUOTE_NONNUMERIC)

families = file("kew_families.txt", "w+")
families.write(fam_columns + "\n")

fam_id = 1 # the start id

# look up family id's from here, mostly to avoid
# redundancy for the legumes
family_map = {} 

for f in sorted(glob.glob(path + "*.TXT")):
    fam = os.path.basename(f)[:-4]
    if fam in family_rename_map:
        fam = family_rename_map[fam]
    fam = fam.capitalize()
    
    if fam not in family_map:
        family_map[fam] = fam_id
        fam_id+=1
        families.write('%d,"%s"\n' % (family_map[fam], fam))
        
    for i in csv.reader(open(f).readlines()):
        genera.writerow(i + [family_map[fam]])

      
genera_file.close()
families.close()
    
    
    
