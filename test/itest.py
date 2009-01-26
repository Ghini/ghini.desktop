#!/usr/bin/env python
#
# itest.py
#
# provides an interactive test environment
#
import sqlalchemy as sa
from sqlalchemy.orm import *

import bauble
import bauble.db as db
import bauble.meta as meta
import bauble.pluginmgr as pluginmgr

import logging
logging.basicConfig()

uri = 'sqlite:///:memory:'
db.open(uri, False)
pluginmgr.load()
db.create(import_defaults=False)

from bauble.plugins.plants import Family, Genus, Species
from bauble.plugins.garden import Accession, Plant, Location

session = bauble.Session()

f = Family(family=u'family')
g = Genus(family=f, genus=u'genus')
s = Species(genus=g, sp=u's')
a = Accession(species=s, code=u'1')
l = Location(site=u'site')
p = Plant(accession=a, location=l, code=u'1')

session.add_all([f, g, s, a, p])
session.commit()
