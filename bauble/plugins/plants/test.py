#
# test.py
#
# Description: test for the Plant plugin
#

import os, sys, unittest
from sqlalchemy import *
from sqlalchemy.exceptions import *
import bauble
from bauble.plugins.plants.species_model import Species, species_table, \
    VernacularName, vernacular_name_table, species_synonym_table, \
    SpeciesSynonym, DefaultVernacularName
from bauble.plugins.plants.family import family_table
from bauble.plugins.plants.genus import genus_table
from testbase import BaubleTestCase, log

#
# TODO: things to create tests for
#
# - test schema cascading works for all tables in the plants module
# - test unicode is working properly in the relevant fields, especially
# in the Species.str function
# - test the setting the default vernacular name on a species is working
# and that delete vernacular names and default vernacular names does
# proper  cascading
# make sure that deleting either of the species referred to in a synonym
# deletes the synonym

# TODO: create more species name test cases
# TODO: create some scenarios that should fail

family_test_data = ({'id': 1, 'family': 'Orchidaceae'},
                    {'id': 2, 'family': 'Leguminosae'},
                    {'id': 3, 'family': 'Polypodiaceae'})

genus_test_data = ({'id': 1, 'genus': 'Maxillaria', 'family_id': 1},
                   {'id': 2, 'genus': 'Encyclia', 'family_id': 1},
                   {'id': 3, 'genus': 'Abrus', 'family_id': 2},
                   {'id': 4, 'genus': 'Campyloneurum', 'family_id': 3},
                   )

species_test_data = ({'id': 1, 'sp': 'variabilis', 'genus_id': 1,
                      'sp_author': u'Bateman ex Lindl.'},
                     {'id': 2, 'sp': 'cochleata', 'genus_id': 2,
                      'sp_author': u'(L.) Lem\xe9e'},
                     {'id': 3, 'sp': u'precatorius', 'genus_id': 3,
                      'sp_author': u'L.'},
                     {'id': 4, 'sp': 'alapense', 'genus_id': 4,
                      'sp_hybrid': u'x', 'sp_author': u'F\xe9e'},
                     {'id': 5, 'sp': 'cochleata', 'genus_id': 2,
                      'sp_author': u'(L.) Lem\xe9e', 'infrasp_rank': u'var.',
                      'infrasp': u'cochleata'},
                     {'id': 6, 'sp': 'cochleata', 'genus_id': 2,
                      'sp_author': u'(L.) Lem\xe9e', 'infrasp_rank': u'cv.',
                      'infrasp': u'Black Night'},
                     {'id': 7, 'sp': 'precatorius', 'genus_id': 3,
                      'sp_author': u'L.', 'cv_group': u'SomethingRidiculous'},
                     {'id': 8, 'sp': 'precatorius', 'genus_id': 3,
                      'sp_author': u'L.', 'infrasp_rank': u'cv.',
                      'infrasp': u'Hot Rio Nights',
                      'cv_group': u'SomethingRidiculous'},
#                     {'id': 9, 'sp': 'precatorius', 'genus_id': 3,
#                      'sp_author': 'L.', cv_group='SomethingRidiculous'},
                     )

species_str_map = {\
    1: 'Maxillaria variabilis',
    2: 'Encyclia cochleata',
    3: 'Abrus precatorius',
    4: 'Campyloneurum x alapense',
    5: 'Encyclia cochleata var. cochleata',
    6: 'Encyclia cochleata \'Black Night\'',
    7: 'Abrus precatorius SomethingRidiculous Group',
    8: 'Abrus precatorius (SomethingRidiculous Group) \'Hot Rio Nights\'',
    }

species_markup_map = {\
    1: '<i>Maxillaria</i> <i>variabilis</i>',
    2: '<i>Encyclia</i> <i>cochleata</i>',
    3: '<i>Abrus</i> <i>precatorius</i>',
    4: '<i>Campyloneurum</i> x <i>alapense</i>',
    5: '<i>Encyclia</i> <i>cochleata</i> var. <i>cochleata</i>',
    6: '<i>Encyclia</i> <i>cochleata</i> \'Black Night\''}

species_str_authors_map = {\
    1: 'Maxillaria variabilis Bateman ex Lindl.',
    2: u'Encyclia cochleata (L.) Lem\xe9e',
    3: 'Abrus precatorius L.',
    4: u'Campyloneurum x alapense F\xe9e',
    5: u'Encyclia cochleata (L.) Lem\xe9e var. cochleata',
    6: u'Encyclia cochleata (L.) Lem\xe9e \'Black Night\''}

species_markup_authors_map = {\
    1: '<i>Maxillaria</i> <i>variabilis</i> Bateman ex Lindl.',
    2: u'<i>Encyclia</i> <i>cochleata</i> (L.) Lem\xe9e',
    3: '<i>Abrus</i> <i>precatorius</i> L.',
    4: u'<i>Campyloneurum</i> x <i>alapense</i> F\xe9e',
    5: u'<i>Encyclia</i> <i>cochleata</i> (L.) Lem\xe9e var. <i>cochleata</i>',
    6: u'<i>Encyclia</i> <i>cochleata</i> (L.) Lem\xe9e \'Black Night\''}

sp_synonym_test_data = ({'id': 1, 'synonym_id': 1, 'species_id': 2},
                        )

vn_test_data = ({'id': 1, 'name': u'SomeName', 'language': u'English',
                 'species_id': 1},
                {'id': 2, 'name': u'SomeName 2', 'language': u'English',
                 'species_id': 1},
                )

test_data_table_control = ((family_table, family_test_data),
                           (genus_table, genus_test_data),
                           (species_table, species_test_data),
                           (vernacular_name_table, vn_test_data),
                           (species_synonym_table, sp_synonym_test_data))

def setUp_test_data():
    '''
    if this method is called again before tearDown_test_data is called you
    will get an error about the test data rows already existing in the database
    '''
    for table, data in test_data_table_control:
        for row in data:
            table.insert().execute(row)


def tearDown_test_data():
    for table, data in test_data_table_control:
        for row in data:
            #print 'delete %s %s' % (table, row['id'])
            table.delete(table.c.id==row['id']).execute()



class PlantTestCase(BaubleTestCase):

    def __init__(self, *args):
        super(PlantTestCase, self).__init__(*args)


    def setUp(self):
        super(PlantTestCase, self).setUp()
        setUp_test_data()


    def tearDown(self):
        super(PlantTestCase, self).tearDown()
        tearDown_test_data()


class SpeciesTests(PlantTestCase):

    def test_string(self):
        for id, s in species_str_map.iteritems():
            spstr = Species.str(self.session.load(Species, id))
            self.assert_(spstr == s,
                         '%s != %s ** %s' % (spstr, s, unicode(spstr)))

        for id, s in species_str_authors_map.iteritems():
            spstr = Species.str(self.session.load(Species, id), authors=True)
            self.assert_(spstr == s,
                         '%s != %s ** %s' % (spstr, s, unicode(spstr)))

        for id, s in species_markup_map.iteritems():
            spstr = Species.str(self.session.load(Species, id), markup=True)
            self.assert_(spstr == s,
                         '%s != %s ** %s' % (spstr, s, unicode(spstr)))

        for id, s in species_markup_authors_map.iteritems():
            spstr = Species.str(self.session.load(Species, id),
                                     markup=True, authors=True)
            self.assert_(spstr == s,
                         '%s != %s ** %s' % (spstr, s, unicode(spstr)))


    def setUp(self):
        super(SpeciesTests, self).setUp()


    def test_default_vernacular_changed_twice(self):
        # test for regression in bug Launchpad #123286
        sp = self.session.load(Species, 1)
        sp.default_vernacular_name = sp.vernacular_names[0]
        sp.default_vernacular_name = sp.vernacular_names[1]
        self.session.commit()


    def test_vernacular_name(self):
        '''
        test creating verncular names, attaching them to the species, setting
        the species.default_vernacular_name and then deleting them
        '''
        sp_query = self.session.query(Species)
        sp = sp_query[0]
        vn = self.session.query(VernacularName)[0]

        # append vernacular name to species and make it the default
        sp.vernacular_names.append(vn)
        sp.default_vernacular_name = vn
        self.session.flush()
        self.assert_(vn.species == sp)

        # test that when the vernacular name is orphaned it and any default
        # vernacular names get deleted with it
        #sp.default_vernacular_name = vn
        #session.flush()
        dvn_id = sp._default_vernacular_name.id
        vn_id = vn.id
        sp.vernacular_names.remove(vn)
        self.session.flush()
        self.assertRaises(InvalidRequestError,
                          self.session.load, VernacularName, vn_id)
        self.assertRaises(InvalidRequestError,
                          self.session.load, DefaultVernacularName, dvn_id)



class SynonymsTests(PlantTestCase):

    def test_species_synonyms(self):
        load_sp = lambda id: self.session.load(Species, id)

        def syn_str(id1, id2, isit='not'):
            sp1 = load_sp(id1)
            sp2 = load_sp(id2)
            return '%s(%s).synonyms: %s' % \
                   (sp1, sp1.id,
                    str(map(lambda s: '%s(%s)' % \
                            (s, s.id), sp1.synonyms)))

        def synonym_of(id1, id2):
            sp1 = load_sp(id1)
            sp2 = load_sp(id2)
            return sp2 in sp1.synonyms

        # test that appending a synonym works using species.synonyms
        sp1 = load_sp(1)
        sp2 = load_sp(2)
        sp1.synonyms.append(sp2)
        self.session.flush()
        self.assert_(synonym_of(1, 2), syn_str(1,2))

        # test that removing a synonyms works using species.synonyms
        sp1.synonyms.remove(sp2)
        self.session.flush()
        self.failIf(synonym_of(1, 2), syn_str(1,2))

        self.session.clear()

        # test that appending a synonym works using species._synonyms
        sp1 = load_sp(1)
        sp2 = load_sp(2)
        syn = SpeciesSynonym(sp2)
        sp1._synonyms.append(syn)
        self.session.flush()
        self.assert_(synonym_of(1, 2), syn_str(1,2))

        # test that removing a synonyms works using species._synonyms
        sp1._synonyms.remove(syn)
        self.session.flush()
        self.failIf(synonym_of(1, 2), syn_str(1,2))

        # TODO: need to test adding a species and then immediately remove it
        # TOOD: need to test removing a species and then immediately adding
        # the same species
        self.session.clear()
        sp1 = load_sp(1)
        sp2 = load_sp(2)
        sp1.synonyms.append(sp2)
        self.session.flush()

        sp1.synonyms.remove(sp2)
        for s in self.session.dirty:
            if isinstance(s, SpeciesSynonym) and s.synonym == sp2:
                self.session.flush([s])
        sp1.synonyms.append(sp2)
        self.session.flush()

        self.session.clear()


    def test_genus_synonyms(self):
        pass


    def test_family_synonyms(self):
        pass


class PlantTestSuite(unittest.TestSuite):
   def __init__(self):
       super(PlantTestSuite, self).__init__()
       self.addTests(map(SpeciesTests,('test_vernacular_name',
                                       'test_default_vernacular_changed_twice',
                                       'test_string')))
       self.addTests(map(SynonymsTests, ('test_species_synonyms',)))

testsuite = PlantTestSuite


#def main():
#    from optparse import OptionParser
#    parser = OptionParser()
#    parser.add_option('-v', '--verbose', dest='verbose', action='store_true',
#                      help='verbose output')
#    parser.add_option('-p', '--profile', dest='profile', action='store_true',
#                      help='print run times')
#    options, args = parser.parse_args()
#
#    import profile
#    import time
#    if options.profile:
#        t1 = time.time()
#        #profile.run('test_speciesStr()')
#        profile.run('profile()')
#        t2 = time.time()
#        print 'time: %s' % (t2-t1)
#    else:
#        print 'starting tests...'
#        test_speciesStr(options.verbose)
#        print 'done.'
#
#
#if __name__ == '__main__':
#    main()
