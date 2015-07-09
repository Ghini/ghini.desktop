# -*- coding: utf-8 -*-
#
# Copyright (c) 2005,2006,2007,2008,2009 Brett Adams <brett@belizebotanic.org>
# Copyright (c) 2012-2015 Mario Frasca <mario@anche.no>
#
# This file is part of bauble.classic.
#
# bauble.classic is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# bauble.classic is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bauble.classic. If not, see <http://www.gnu.org/licenses/>.

import os

from sqlalchemy import *
from sqlalchemy.exc import *

import bauble.plugins.tag as tag_plugin
from bauble.plugins.plants import Family
from bauble.plugins.tag import Tag
from bauble.test import BaubleTestCase, check_dupids


def test_duplicate_ids():
    """
    Test for duplicate ids for all .glade files in the tag plugin.
    """
    import bauble.plugins.tag as mod
    import glob
    head, tail = os.path.split(mod.__file__)
    files = glob.glob(os.path.join(head, '*.glade'))
    for f in files:
        assert(not check_dupids(f))


class TagTests(BaubleTestCase):


    family_ids = [1, 2]

    def setUp(self):
        super(TagTests, self).setUp()
        self.family = Family(family=u'family')
        self.session.add(self.family)
        self.session.commit()
        #for f in self.family_ids:
        #    family_table.insert({'id': f, 'family': unicode(f)}).execute()
        #for col in family_table.c:
        #    utils.reset_sequence(col)


    def tearDown(self):
        super(TagTests, self).tearDown()
        #self.session.bind.execute(family_table.delete())


##     def test_get_tagged_objects(self):
##         pass

    def test_str(self):
        """
        Test Tag.__str__ method
        """
        name = u'test'
        tag = Tag(tag=name)
        self.assert_(str(tag) == name)


    def test_tag_objects(self):
        family2 = Family(family=u'family2')
        self.session.add(family2)
        self.session.commit()
        family1_id = self.family.id
        family2_id = family2.id
        tag_plugin.tag_objects('test', [self.family, family2])
        # get object by string
        tagged_objs = tag_plugin.get_tagged_objects('test')
        sorted_pairs= sorted([(type(o), o.id) for o in tagged_objs],
                             cmp=lambda x, y: cmp(x[0], y[0]))
        self.assert_(sorted_pairs == [(Family,family1_id), (Family,family2_id)],
                     sorted_pairs)

        # get object by tag
        tag = self.session.query(Tag).filter_by(tag=u'test').one()
        tagged_objs = tag_plugin.get_tagged_objects(tag)
        sorted_pairs= sorted([(type(o), o.id) for o in tagged_objs],
                             cmp=lambda x, y: cmp(x[0], y[0]))
        self.assert_(sorted_pairs == [(Family,family1_id), (Family,family2_id)],
                     sorted_pairs)

        tag_plugin.tag_objects('test', [self.family, family2])

        #
        # now untag everything
        #
        tag_plugin.untag_objects('test', [self.family, family2])
        # get object by string
        tagged_objs = tag_plugin.get_tagged_objects('test')
        pairs = [(type(o), o.id) for o in tagged_objs]
        self.assert_(pairs == [], pairs)

        # get object by tag
        tag = self.session.query(Tag).filter_by(tag=u'test').one()
        tagged_objs = tag_plugin.get_tagged_objects(tag)


    def test_get_tag_ids(self):
        family2 = Family(family=u'family2')
        self.session.add(family2)
        self.session.commit()
        tag_plugin.tag_objects('test', [self.family, family2])
        tag_plugin.tag_objects('test2', [self.family])

        # test we only return the ids the objects have in common
        #sel = select([tag_table.c.id], tag_table.c.tag==u'test')
        results = self.session.query(Tag.id).filter_by(tag=u'test')
        test_id = [r[0] for r in results]
        # should only return id for "test"
        ids = tag_plugin.get_tag_ids([self.family, family2])
        self.assert_(ids==test_id, '%s==%s' % (ids, test_id))

        # test that we return multiple tag ids if the objs share tags
        tag_plugin.tag_objects('test2', [family2])
        #sel = select([tag_table.c.id], or_(tag_table.c.tag==u'test',
        #                                   tag_table.c.tag==u'test2'))
        results = self.session.query(Tag.id).filter(or_(Tag.tag==u'test',
                                                        Tag.tag==u'test2'))
        test_id = sorted([r[0] for r in results])
        # should return ids for both test and test2
        ids = sorted(tag_plugin.get_tag_ids([self.family, family2]))
        self.assert_(ids==test_id, '%s == %s' % (ids, test_id))

