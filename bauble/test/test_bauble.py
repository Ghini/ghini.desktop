#
# test_bauble.py
#
import os, sys, unittest
import datetime
from sqlalchemy import *
from bauble.view import SearchParser
from bauble.utils.pyparsing import *
from bauble.test import BaubleTestCase
import bauble.meta as meta

"""
Tests for the main bauble module.
"""

class BaubleTests(BaubleTestCase):

    def test_base_table(self):
        """
        Test bauble.Base is setup correctly
        """
        m = meta.BaubleMeta(name=u'name', value=u'value')
        table = m.__table__
        self.session.save(m)
        m = self.session.query(meta.BaubleMeta).first()
        print >>sys.stderr, type(m._created)

        # test that _created and _last_updated were created correctly
        self.assert_(hasattr(m, '_created') \
                     and isinstance(m._created, datetime.datetime))
        self.assert_(hasattr(m, '_last_updated') \
                     and isinstance(m._last_updated, datetime.datetime))



