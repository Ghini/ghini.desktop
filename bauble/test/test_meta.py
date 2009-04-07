#
# test for bauble.meta
#

import bauble.meta as meta
from bauble.test import BaubleTestCase


class MetaTests(BaubleTestCase):

    def __init__(self, *args):
        super(MetaTests, self).__init__(*args)


    def test_get_default(self):
        """
        Test bauble.meta.get_default()
        """
        # test the object isn't created if it doesn't exist and we
        # don't pass a default value
        name = u'name'
        obj = meta.get_default(name)
        self.assert_(obj is None)

        # test that the obj is created if it doesn't exists and that
        # the default value is set
        value = u'value'
        meta.get_default(name, default=value)
        obj = self.session.query(meta.BaubleMeta).filter_by(name=name).one()
        self.assert_(obj.value == value)

        # test that the value isn't changed if it already exists
        value2 = u'value2'
        obj = meta.get_default(name, default=value2)
        self.assert_(obj.value == value)

        # test that if we pass our own session when we are creating a
        # new value that the object is added to the session but not committed
        obj = meta.get_default(u'name2', default=value, session=self.session)
        self.assert_(obj in self.session.new)
