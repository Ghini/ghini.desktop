#!/usr/bin/env python

"""
print a list if duplicate ids in an XML file
"""
import os
import random
import sys

import lxml.etree as etree

# TODO: this might mess up some quoted elements so the new file should
# be checked before saving it over the old one

filename_arg = 1
overwrite = False

if sys.argv[1] == '-w':
    overwrite = True
    filename_arg = 2


if len(sys.argv) < filename_arg+1:
    print('** you have to supply a filename')
    sys.exit(1)


random.seed()
ids = set()

filename = sys.argv[filename_arg]
print(("duplicates in %s: " % filename))
tree = etree.parse(filename)
for el in tree.getiterator():
    elid = el.get('id')
    if elid not in ids:
        ids.add(elid)
    elif elid:
        newid = None
        if overwrite:
            while newid in ids:
                newid = '%s%s' % (elid, str(random.randint(0, 99)))
            ids.add(newid)
            el.set('id', newid)
            print(('%s = %s' % (elid, newid)))
        else:
            print(elid)
if overwrite:
    tree.write('%s.dupid' % filename, encoding='utf8')




