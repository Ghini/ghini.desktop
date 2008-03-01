import unittest
from sqlalchemy import *
from sqlalchemy.exceptions import *
from testbase import BaubleTestCase, log
import bauble.utils as utils
import bauble.plugins.tag as tag_plugin
from bauble.plugins.tag import Tag, tag_table
from bauble.plugins.plants import Family, family_table, Genus, genus_table, \
     Species, species_table, VernacularName, vernacular_name_table
from bauble.plugins.garden import Accession, accession_table, Plant, \
     plant_table, Location, location_table


def setUp_test_data():
    pass

def tearDown_test_data():
    pass


class TagTestCase(BaubleTestCase):

    def __init__(self, *args):
        super(TagTestCase, self).__init__(*args)

    def setUp(self):
        super(TagTestCase, self).setUp()

    def tearDown(self):
        super(TagTestCase, self).tearDown()


class TagTests(TagTestCase):


    family_ids = [1, 2]

    def setUp(self):
        super(TagTests, self).setUp()
        for f in self.family_ids:
            family_table.insert({'id': f, 'family': unicode(f)}).execute()
        for col in family_table.c:
            utils.reset_sequence(col)


    def tearDown(self):
        super(TagTests, self).tearDown()
        self.session.bind.execute(family_table.delete())


##     def test_get_tagged_objects(self):
##         pass


    def test_tag_objects(self):
        tag_plugin.tag_objects('test', [self.session.load(Family, 1),
                                        self.session.load(Family, 2)])
        # get object by string
        tagged_objs = tag_plugin.get_tagged_objects('test')
        sorted_pairs= sorted([(type(o), o.id) for o in tagged_objs],
                             cmp=lambda x, y: cmp(x[0], y[0]))
        self.assert_(sorted_pairs == [(Family, 1), (Family, 2)], sorted_pairs)

        # get object by tag
        tag = self.session.query(tag_plugin.Tag).filter_by(tag=u'test').one()
        tagged_objs = tag_plugin.get_tagged_objects(tag)
        sorted_pairs= sorted([(type(o), o.id) for o in tagged_objs],
                             cmp=lambda x, y: cmp(x[0], y[0]))
        self.assert_(sorted_pairs == [(Family, 1), (Family, 2)], sorted_pairs)

        tag_plugin.tag_objects('test', [self.session.load(Family, 1),
                                        self.session.load(Family, 1)])

        #
        # now untag everything
        #
        tag_plugin.untag_objects('test', [self.session.load(Family, 1),
                                          self.session.load(Family, 2)])
        # get object by string
        tagged_objs = tag_plugin.get_tagged_objects('test')
        pairs = [(type(o), o.id) for o in tagged_objs]
        self.assert_(pairs == [], pairs)

        # get object by tag
        tag = self.session.query(tag_plugin.Tag).filter_by(tag=u'test').one()
        tagged_objs = tag_plugin.get_tagged_objects(tag)


    def test_get_tag_ids(self):
        fam1 = self.session.load(Family, 1)
        fam2 = self.session.load(Family, 2)
        tag_plugin.tag_objects('test', [fam1, fam2])
        tag_plugin.tag_objects('test2', [fam1])

        # test we only return the ids the objects have in common
        sel = select([tag_table.c.id], tag_table.c.tag==u'test')
        test_id = [r[0] for r in sel.execute()]
        ids = tag_plugin.get_tag_ids([fam1, fam2])
        self.assert_(ids==test_id, ids)

        # test that we return multiple tag ids if the objs share tags
        tag_plugin.tag_objects('test2', [fam1])
        sel = select([tag_table.c.id], or_(tag_table.c.tag==u'test',
                                           tag_table.c.tag==u'test2'))
        test_id = [r[0] for r in sel.execute()]
        ids = tag_plugin.get_tag_ids([fam1, fam2])
        self.assert_(ids==test_id, ids)


class TagTestSuite(unittest.TestSuite):

    def __init__(self):
        super(TagTestSuite, self).__init__()
        self.addTests(map(TagTests, ('test_tag_objects', 'test_get_tag_ids')))


testsuite = TagTestSuite
