#
# test_bauble.py
#
import os
import sys
import unittest
import datetime

from sqlalchemy import *

import bauble
import bauble.db as db
from bauble.types import Enum
from bauble.utils.log import debug
from bauble.view import SearchParser
from bauble.utils.pyparsing import *
from bauble.test import BaubleTestCase
import bauble.meta as meta

"""
Tests for the main bauble module.
"""

class BaubleTests(BaubleTestCase):

    def test_enum_type(self):
        """
        Test bauble.types.Enum
        """
        class Test(db.Base):
            __tablename__ = 'test_enum_type'
            id = Column(Integer, primary_key=True)
            value = Column(Enum(values=['1', '2', '']), default=u'')
        table = Test.__table__
        table.create(bind=db.engine)
#         t = Test(id=1)
#         self.session.add(t)
#         self.session.commit()
        db.engine.execute(table.insert(), {"id": 1})
        #debug(t.value)


    def test_date_type(self):
        """
        Test bauble.types.Date
        """
        pass


    def test_datetime_type(self):
        """
        Test bauble.types.DateTime
        """
        dt = bauble.types.DateTime()

        # with negative timezone
        s = '2008-12-1 11:50:01.001-05:00'
        result = '2008-12-01 11:50:01.000001-05:00'
        v = dt.process_bind_param(s, None)
        self.assert_(v.isoformat(' ') == result)

        # test with positive timezone
        s = '2008-12-1 11:50:01.001+05:00'
        result = '2008-12-01 11:50:01.000001+05:00'
        v = dt.process_bind_param(s, None)
        self.assert_(v.isoformat(' ') == result)

        # test with no timezone
        s = '2008-12-1 11:50:01.001'
        result = '2008-12-01 11:50:01.000001'
        v = dt.process_bind_param(s, None)
        self.assert_(v.isoformat(' ') == result)

        # test with no milliseconds
        s = '2008-12-1 11:50:01'
        result = '2008-12-01 11:50:01'
        v = dt.process_bind_param(s, None)
        self.assert_(v.isoformat(' ') == result)



    def test_base_table(self):
        """
        Test db.Base is setup correctly
        """
        m = meta.BaubleMeta(name=u'name', value=u'value')
        table = m.__table__
        self.session.add(m)
        m = self.session.query(meta.BaubleMeta).first()

        # test that _created and _last_updated were created correctly
        self.assert_(hasattr(m, '_created') \
                     and isinstance(m._created, datetime.datetime))
        self.assert_(hasattr(m, '_last_updated') \
                     and isinstance(m._last_updated, datetime.datetime))
