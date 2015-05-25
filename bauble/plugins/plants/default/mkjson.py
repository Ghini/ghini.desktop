#!/usr/bin/env python

import csv
synonym = {}

with open("genus_synonym.txt") as f:
    f.readline()
    spamreader = csv.reader(f, delimiter=',', quotechar='"')
    for syn, gen in spamreader:
        synonym[int(syn)] = int(gen)

family = {}
with open("family.txt") as f:
    f.readline()
    spamreader = csv.reader(f, delimiter=',', quotechar='"')
    for famid, famname in spamreader:
        family[int(famid)] = famname

genus = {}
with open("genus.txt") as f:
    f.readline()
    spamreader = csv.reader(f, delimiter=',', quotechar='"')
    for genid, name, author, famid in spamreader:
        genid = int(genid)
        genus[genid] = name

with open("genus.txt") as f:
    f.readline()
    spamreader = csv.reader(f, delimiter=',', quotechar='"')
    for genid, name, author, famid in spamreader:
        genid = int(genid)
        famid = int(famid)
        if genid in synonym:
            acc_part = ', "accepted": "%s"' % genus[synonym[genid]]
        else:
            acc_part = ''
        print ' {"object": "taxon", "rank": "genus", "epithet": "%s", '\
            '"author": "%s", "ht-rank": "familia", "ht-epithet": "%s"%s},' \
            % (name, author, family[famid], acc_part)
