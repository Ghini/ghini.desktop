#
# test.py
#
# Description: test for the Plant plugin
#

import os, sys, unittest
from sqlalchemy import *
import bauble
from bauble.plugins.plants.species_model import Species, species_table, \
    VernacularName, vernacular_name_table, species_synonym_table, \
    SpeciesSynonym
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
                      'sp_author': 'Bateman ex Lindl.'},
                     {'id': 2, 'sp': 'cochleata', 'genus_id': 2,
                      'sp_author': '(L.) Lem\xc3\xa9e'},
                     {'id': 3, 'sp': 'precatorius', 'genus_id': 3,
                      'sp_author': 'L.'},
                     {'id': 4, 'sp': 'alapense', 'genus_id': 4,
                      'sp_hybrid': 'x', 'sp_author': 'F\xc3\xa9e'},
                     {'id': 5, 'sp': 'cochleata', 'genus_id': 2,
                      'sp_author': '(L.) Lem\xc3\xa9e', 'infrasp_rank': 'var.',
                      'infrasp': 'cochleata'},
                     {'id': 6, 'sp': 'cochleata', 'genus_id': 2,
                      'sp_author': '(L.) Lem\xc3\xa9e', 'infrasp_rank': 'cv.',
                      'infrasp': 'Black Night'},
                     {'id': 7, 'sp': 'precatorius', 'genus_id': 3,
                      'sp_author': 'L.', 'cv_group':'SomethingRidiculous'},
                     {'id': 8, 'sp': 'precatorius', 'genus_id': 3,
                      'sp_author': 'L.', 'infrasp_rank': 'cv.',
                      'infrasp': 'Hot Rio Nights',
                      'cv_group':'SomethingRidiculous'},
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
    2: 'Encyclia cochleata (L.) Lem\xc3\xa9e',
    3: 'Abrus precatorius L.',
    4: 'Campyloneurum x alapense F\xc3\xa9e',
    5: 'Encyclia cochleata (L.) Lem\xc3\xa9e var. cochleata',
    6: 'Encyclia cochleata (L.) Lem\xc3\xa9e \'Black Night\''}

species_markup_authors_map = {\
    1: '<i>Maxillaria</i> <i>variabilis</i> Bateman ex Lindl.',
    2: '<i>Encyclia</i> <i>cochleata</i> (L.) Lem\xc3\xa9e',
    3: '<i>Abrus</i> <i>precatorius</i> L.',
    4: '<i>Campyloneurum</i> x <i>alapense</i> F\xc3\xa9e',
    5: '<i>Encyclia</i> <i>cochleata</i> (L.) Lem\xc3\xa9e var. <i>cochleata</i>',
    6: '<i>Encyclia</i> <i>cochleata</i> (L.) Lem\xc3\xa9e \'Black Night\''}

sp_synonym_test_data = ({'id': 1, 'synonym_id': 1, 'species_id': 2},
                        )

vn_test_data = ({'id': 1, 'name': 'SomeName', 'language': 'English',
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



class AttrDict(dict):

    def __init__(self, **kwargs):
        dict.__init__(self)
        for name, value in kwargs.iteritems():
            self[name] = value

    def __getattr__(self, attr):
        if attr in self:
            return dict.__getitem__(self, attr)
        else:
            return None

    def __setattr__(self, attr, value):
        return dict.__setitem__(self, attr, value)


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
        # TODO: do away with testString and use this instead
        for id, s in species_str_map.iteritems():
#            print s
#            print Species.str(self.session.load(Species, id))
            self.assert_(str(self.session.load(Species, id)) == s)

        for id, s in species_str_authors_map.iteritems():
#            print s
#            print Species.str(self.session.load(Species, id), authors=True)
            self.assert_(Species.str(self.session.load(Species, id),
                                     authors=True) == s)

        for id, s in species_markup_map.iteritems():
            self.assert_(Species.str(self.session.load(Species, id),
                                     markup=True) == s)

        for id, s in species_markup_authors_map.iteritems():
            self.assert_(Species.str(self.session.load(Species, id),
                                     markup=True, authors=True) == s)


    def setUp(self):
        super(SpeciesTests, self).setUp()


    def test_vernacular_name(self):
        '''
        test creating verncular names, attaching them to the species, setting
        the species.default_vernacular_name and then deleting them
        '''
        session = create_session()
        sp_query = session.query(Species)
        sp_name = 'testvernspecies'
        sp = sp_query.select()[0]
        vn = session.query(VernacularName).select()[0]
        session.save(vn)
        sp.vernacular_names.append(vn)
        session.flush()
        sp.default_vernacular_name = vn
        session.flush()
        del sp.default_vernacular_name
        session.flush()
        assert sp.default_vernacular_name not in session
        assert vn not in session
        #session.delete(vn) # give and InvalidRequestError
        session.flush()
        session.expire(sp) # this expire() has to be here or it will fail
        assert sp.default_vernacular_name is None, 'default vernacular name is not None'
        session.flush()


class SynonymsTests(PlantTestCase):

    def test_species_synonyms(self):
        load_sp = lambda id: self.session.load(Species, id)

        def create_syn(sp_id, syn_id):
            syn = SpeciesSynonym()
            syn.synonym = load_sp(syn_id)
            load_sp(sp_id).synonyms.append(syn)
            self.session.save(syn)
            return syn

        def syn_str(id1, id2, isit='not'):
            sp1 = load_sp(id1)
            sp2 = load_sp(id2)
            return '%s(%s).synonyms: %s' % \
                   (sp1, sp1.id,
                    str(map(lambda s: '%s(%s)' % \
                            (s, s.species_id), sp1.synonyms)))

        def synonym_of(id1, id2):
            sp1 = load_sp(id1)
            sp2 = load_sp(id2)
            return sp2.id in [syn.id for syn in sp1.synonyms]

        # make sure that appending a synonym works
        syn = create_syn(1, 2)
        self.session.flush()
        self.assert_(synonym_of(1, 2), syn_str(1,2))
        self.session.clear()

        # test the removing a synonyms works
        sp1 = load_sp(1)
#        print map(lambda s: '%s(%s)' % (str(s), s.id), sp1.synonyms)
        syn0 = sp1.synonyms[0]
#        print syn0
        self.assert_(syn0 is not None)
        sp2 = syn0.synonym
        sp1.synonyms.remove(syn0)
        self.session.flush()
        self.failIf(synonym_of(sp1.id, sp2.id), syn_str(sp1.id, sp2.id))


        def i_wish_it_worked_like_this():
            # this is would be nice where species.synonyms was a list of
            # species instead of a list of synonyms
            sp.synonyms.append(self.session.load(Species, 2))
            self.session.flush()
            assert self.session.load(Species, 2) in self.session.load(Species, 1).synonyms


    def test_genus_synonyms(self):
        pass


    def test_family_synonyms(self):
        pass


class PlantTestSuite(unittest.TestSuite):
   def __init__(self):
       super(PlantTestSuite, self).__init__()
       self.addTests(map(SpeciesTests,('test_vernacular_name', 'test_string')))
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
