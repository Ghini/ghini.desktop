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

from bauble.plugins.plants.family import Family
from bauble.plugins.plants.genus import Genus
from bauble.plugins.plants.species import Species

session = bauble.Session()
