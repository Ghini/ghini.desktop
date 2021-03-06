#!/bin/bash

# this is a simple text conversion
#

rm -fr 3.1 2>/dev/null
mkdir 3.1
cp *.txt 3.1
cd 3.1

mv geography.txt geographic_area.txt
mv source_detail.txt contact.txt
rm plant_status.txt

sed -i '1 s/source_detail/contact/g' *.txt
sed -i '1 s/geography/geographic_area/g' *.txt

sed -i '1 s/family,/epithet,/' family.txt
sed -i '1 s/genus,/epithet,/' genus.txt
sed -i '1 s/sp,/epithet,/' species.txt
sed -i '1 s/sp_author,/author,/' species.txt

sed -i 's/,DATETIME/,'$(date --utc --iso=minutes)'/g' *.txt
sed -i 's/^version,1\.0\.[0-9]*,/version,3.1.0,/' bauble.txt

