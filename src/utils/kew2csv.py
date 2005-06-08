#!/usr/bin/python

import glob

gen_columns = "id", "hybrid", "genus", "author", "synonym", "family_id"
fam_columns = "id", "family"

genera = file("kew_genera.txt", "w+")
genera.write(str(gen_columns)[1:-1] + "\n")

families = file("kew_families.txt", "w+")
families.write(str(fam_columns)[1:-1] + "\n")

fam_id = 1
for f in sorted(glob.glob("*.TXT")):
    fam = f[:-4].capitalize()
    families.write('"' + str(fam_id) + '","' + fam + '"\n')
    print fam
    for i in open(f).readlines():
        genera.write(i.strip() + ',"' + str(fam_id) + '"\n')
    fam_id = fam_id + 1
      
genera.close()
families.close()
    
    
    
