# -*- coding: utf-8 -*-
#
# Copyright (c) 2005,2006,2007,2008,2009 Brett Adams <brett@belizebotanic.org>
# Copyright (c) 2012-2015 Mario Frasca <mario@anche.no>
# Copyright 2017 Jardín Botánico de Quito
#
# This file is part of ghini.desktop.
#
# ghini.desktop is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ghini.desktop is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ghini.desktop. If not, see <http://www.gnu.org/licenses/>.

import sys
import unittest

import logging
logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)

import bauble
import bauble.db as db
from bauble.error import BaubleError
from bauble.prefs import prefs
import bauble.pluginmgr as pluginmgr

## for sake of testing, just use sqlite3.
uri = 'sqlite:///:memory:'


def init_bauble(uri, create=False):
    try:
        db.open(uri, verify=False)
    except Exception, e:
        print >>sys.stderr, e
        #debug e
    if not bauble.db.engine:
        raise BaubleError('not connected to a database')
    prefs.init()
    prefs.testing = True
    pluginmgr.load()
    db.create(create)
    pluginmgr.init(force=True)


def update_gui():
    """
    Flush any GTK Events.  Used for doing GUI testing.
    """
    import gtk
    while gtk.events_pending():
        gtk.main_iteration(block=False)


def check_dupids(filename):
    """
    Return a list of duplicate ids in a glade file
    """
    ids = set()
    duplicates = set()
    import lxml.etree as etree
    tree = etree.parse(filename)
    for el in tree.getiterator():
        if el.tag == 'col':
            continue
        elid = el.get('id')
        if elid not in ids:
            ids.add(elid)
        elif elid and elid not in duplicates:
            duplicates.add(elid)
    logger.warn(duplicates)
    return list(duplicates)


class MockLoggingHandler(logging.Handler):
    """Mock logging handler to check for expected logs."""

    def __init__(self, *args, **kwargs):
        self.reset()
        logging.Handler.__init__(self, *args, **kwargs)

    def emit(self, record):
        received = self.messages.setdefault(
            record.name, {}).setdefault(
                record.levelname.lower(), [])
        received.append(self.format(record))

    def reset(self):
        self.messages = {}

        
class BaubleTestCase(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(BaubleTestCase, self).__init__(*args, **kwargs)
        prefs.testing = True

    def setUp(self):
        assert uri is not None, "The database URI is not set"
        init_bauble(uri)
        self.session = db.Session()
        self.handler = MockLoggingHandler()
        logging.getLogger().addHandler(self.handler)

    def tearDown(self):
        logging.getLogger().removeHandler(self.handler)
        self.session.close()
        db.metadata.drop_all(bind=db.engine)
        bauble.pluginmgr.commands.clear()
        pluginmgr.plugins.clear()

    # assertIsNone is not available before 2.7
    import sys
    if sys.version_info[:2] < (2, 7):
        def assertIsNone(self, item):
            self.assertTrue(item is None)


def mockfunc(msg=None, name=None, caller=None, result=False, *args, **kwargs):
    caller.invoked.append((name, msg))
    return result
