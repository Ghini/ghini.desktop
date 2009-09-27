#!/usr/bin/env python

"""
print a list if duplicate ids in an XML file
"""

import os
import sys

import lxml.etree as etree

if len(sys.argv) < 2:
    print '** you have to supply a filename'
    sys.exit(1)

ids = set()

filename = sys.argv[1]
print "duplicates in %s: " % filename
tree = etree.parse(filename)
for el in tree.getiterator():
    elid = el.get('id')
    if elid not in ids:
        ids.add(elid)
    elif elid:
        print '%s' % elid





