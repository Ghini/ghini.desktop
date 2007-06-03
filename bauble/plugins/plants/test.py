import os, sys, unittest
from sqlalchemy import *
import bauble
from bauble.plugins.plants.species_model import Species, species_table, \
    VernacularName, vernacular_name_table
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

family_test_data = ({'id': 1, 'family': 'Orchidaceae'},
                    {'id': 2, 'family': 'Leguminosae'})

genus_test_data = ({'id': 1, 'genus': 'Maxillaria', 'family_id': 1},
                   )

species_test_data = ({'id':1 , 'sp': 'variabilis', 'genus_id': 1},
                     )

vn_test_data = ({'id': 1, 'name': 'SomeName', 'language': 'English',
                 'species_id': 1},
                )

def setUp_test_data():
    '''
    if this method is called again before tearDown_test_data is called you
    will get an error about the test data rows already existing in the database
    '''
    family_table.insert().execute(*family_test_data)
    genus_table.insert().execute(*genus_test_data)
    species_table.insert().execute(*species_test_data)
    vernacular_name_table.insert().execute(*vn_test_data)


def tearDown_test_data():
    control = ((family_table, family_test_data),
               (genus_table, genus_test_data),
               (species_table, species_test_data),
               (vernacular_name_table, vn_test_data))
    for table, data in control:
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


# all possible combinations of species values
sp_example_dicts = [AttrDict(genus='Genus', sp='species'),
                     AttrDict(genus='Genus', sp='species', sp_author='SpAuthor'),
                     AttrDict(genus='Genus', sp='spname', sp_hybrid='x'),
                     AttrDict(genus='Genus', sp='spname', infrasp_rank='var.', infrasp='ispname'),
                     AttrDict(genus='Genus', sp='spname', infrasp_rank='cv.', infrasp='ispname'),
                     AttrDict(genus='Genus', sp='spname', cv_group='CvGroupName'), # TODO: should this be valid?
                     AttrDict(genus='Genus', sp='spname', cv_group='CvGroupName', infrasp_rank='cv.', infrasp='ispname'),
                     AttrDict(genus='Genus', sp='spname', cv_group='CvGroupName', infrasp_rank='cv.')
                     ]
sp_examples_no_authors_no_markup = (('Genus species', sp_example_dicts[0]),
                                     ('Genus species', sp_example_dicts[1]),
                                     ('Genus x spname', sp_example_dicts[2]),
                                     ('Genus spname var. ispname', sp_example_dicts[3]),
                                     ('Genus spname \'ispname\'', sp_example_dicts[4]),
                                     ('Genus spname CvGroupName Group', sp_example_dicts[5]),
                                     ('Genus spname (CvGroupName Group) \'ispname\'', sp_example_dicts[6]),
                                     ('Genus spname CvGroupName Group', sp_example_dicts[7])
                                     )

sp_examples_yes_authors_no_markup = (('Genus species', sp_example_dicts[0]),
                                      ('Genus species SpAuthor', sp_example_dicts[1]),
                                      ('Genus x spname', sp_example_dicts[2]),
                                      ('Genus spname var. ispname', sp_example_dicts[3]),
                                      ('Genus spname \'ispname\'', sp_example_dicts[4]))

sp_examples_no_authors_yes_markup = (('<i>Genus</i> <i>species</i>', sp_example_dicts[0]),
                                      ('<i>Genus</i> <i>species</i>', sp_example_dicts[1]),
                                      ('<i>Genus</i> x <i>spname</i>', sp_example_dicts[2]),
                                      ('<i>Genus</i> <i>spname</i> var. <i>ispname</i>', sp_example_dicts[3]),
                                      ('<i>Genus</i> <i>spname</i> \'ispname\'', sp_example_dicts[4]),
                                      ('<i>Genus</i> <i>spname</i> CvGroupName Group', sp_example_dicts[5]),
                                      ('<i>Genus</i> <i>spname</i> (CvGroupName Group) \'ispname\'', sp_example_dicts[6]))

sp_examples_yes_authors_yes_markup = (('<i>Genus</i> <i>species</i>', sp_example_dicts[0]),
                                       ('<i>Genus</i> <i>species</i> SpAuthor', sp_example_dicts[1]),
                                       ('<i>Genus</i> x <i>spname</i>', sp_example_dicts[2]),
                                       ('<i>Genus</i> <i>spname</i> var. <i>ispname</i>', sp_example_dicts[3]),
                                       ('<i>Genus</i> <i>spname</i> \'ispname\'', sp_example_dicts[4]),
                                       ('<i>Genus</i> <i>spname</i> CvGroupName Group', sp_example_dicts[5]),
                                       ('<i>Genus</i> <i>spname</i> (CvGroupName Group) \'ispname\'', sp_example_dicts[6]))

#
#def profile():
#    example_dicts = [AttrDict(genus='Genus', sp='species'),
#                     AttrDict(genus='Genus', sp='species', sp_author='SpAuthor'),
#                     AttrDict(genus='Genus', sp='spname', sp_hybrid='x'),
#                     AttrDict(genus='Genus', sp='spname', infrasp_rank='var.', infrasp='ispname'),
#                     AttrDict(genus='Genus', sp='spname', infrasp_rank='cv.', infrasp='ispname'),
#                     AttrDict(genus='Genus', sp='spname', cv_group='CvGroupName'), # TODO: should this be valid?
#                     AttrDict(genus='Genus', sp='spname', cv_group='CvGroupName', infrasp_rank='cv.', infrasp='ispname'),
#                     AttrDict(genus='Genus', sp='spname', cv_group='CvGroupName', infrasp_rank='cv.')
#                     ]
#    examples_yes_authors_yes_markup = (('<i>Genus</i> <i>species</i>', example_dicts[0]),
#                                       ('<i>Genus</i> <i>species</i> SpAuthor', example_dicts[1]),
#                                       ('<i>Genus</i> x <i>spname</i>', example_dicts[2]),
#                                       ('<i>Genus</i> <i>spname</i> var. <i>ispname</i>', example_dicts[3]),
#                                       ('<i>Genus</i> <i>spname</i> \'ispname\'', example_dicts[4]),
#                                       ('<i>Genus</i> <i>spname</i> CvGroupName Group', example_dicts[5]),
#                                       ('<i>Genus</i> <i>spname</i> (CvGroupName Group) \'ispname\'', example_dicts[6]))
#    for i in xrange(1, 1000):
#        for name, name_dict in examples_yes_authors_yes_markup:
#            s = Species.str(name_dict, authors=True, markup=True)
#            assert(name == s)
#
#
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

    def testString(self):
        '''
        test Species string conversion function
        '''
        log.info('\ntest Species.str(authors=False, markup=False)\n----------------')
        for name, name_dict in sp_examples_no_authors_no_markup:
            s = Species.str(name_dict, authors=False, markup=False)
            log.info('-- %s\n  %s == %s' % (name_dict, name, s))
            assert(name == s), 'authors=False, markup=False, %s == %s' % (name, name_dict)

        log.info('\ntest Species.str(authors=True, markup=False)\n----------------')
        for name, name_dict in sp_examples_yes_authors_no_markup:
            s = Species.str(name_dict, authors=True, markup=False)
            log.info('-- %s\n  %s == %s' % (name_dict, name, s))
            assert(name == s)

        log.info('\ntest Species.str(authors=False, markup=True)\n----------------')
        for name, name_dict in sp_examples_no_authors_yes_markup:
            s = Species.str(name_dict, authors=False, markup=True)
            log.info('-- %s\n  %s == %s' % (name_dict, name, s))
            assert(name == s)

        log.info('\ntest Species.str(authors=True, markup=True)\n----------------')
        for name, name_dict in sp_examples_yes_authors_yes_markup:
            s = Species.str(name_dict, authors=True, markup=True)
            log.info('-- %s\n  %s == %s' % (name_dict, name, s))
            assert(name == s)

    def setUp(self):
        super(SpeciesTests, self).setUp()


    def testVernacularName(self):
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


class PlantTestSuite(unittest.TestSuite):
   def __init__(self):
       unittest.TestSuite.__init__(self, map(SpeciesTests,
                                             ('testString','testVernacularName')))

testsuite = PlantTestSuite



