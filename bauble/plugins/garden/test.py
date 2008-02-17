import unittest
from sqlalchemy import *
from sqlalchemy.exceptions import *
from testbase import BaubleTestCase, log
import bauble.utils as utils
from bauble.plugins.garden.accession import Accession, accession_table, \
    dms_to_decimal, decimal_to_dms, longitude_to_dms, latitude_to_dms
from bauble.plugins.garden.donor import Donor, donor_table
from bauble.plugins.garden.source import Donation, donation_table, \
     Collection, collection_table
from bauble.plugins.garden.plant import plant_table
from bauble.plugins.garden.location import location_table
from bauble.plugins.plants.family import family_table
from bauble.plugins.plants.genus import genus_table
from bauble.plugins.plants.species_model import species_table
import bauble.plugins.plants.test as plants_test
from bauble.plugins.garden.institution import Institution

# TODO: create a test to make sure that if you delete an accession then the
# plants that are "children" of this accession are also deleted

accession_test_data = ({'id':1 , 'code': u'1.1', 'species_id': 1,
                        'source_type': u'Donation'},
                       {'id':2 , 'code': u'2.2', 'species_id': 2,
                        'source_type': u'Collection'},
                       )

plant_test_data = ({'id':1 , 'code': u'1', 'accession_id': 1,
                    'location_id': 1},
                   )

location_test_data = ({'id': 1, 'site': u'Somewhere Over The Rainbow'},
                      )

donor_test_data = ({'id': 1, 'name': u'SomeDonor'},
                   )

donation_test_data = ({'id': 1, 'accession_id': 1, 'donor_id': 1},
                      )

collection_test_data = ({'id': 1, 'accession_id': 2, 'locale': u'Somewhere'},
                        )

test_data_table_control = ((accession_table, accession_test_data),
                           (location_table, location_test_data),
                           (plant_table, plant_test_data),
                           (donor_table, donor_test_data),
                           (donation_table, donation_test_data),
                           (collection_table, collection_test_data))

def setUp_test_data():
    '''
    if this method is called again before tearDown_test_data is called you
    will get an error about the test data rows already existing in the database
    '''
    for table, data in test_data_table_control:
        for row in data:
            table.insert().execute(row)
        for col in table.c:
            utils.reset_sequence(col)
    i = Institution()
    i.name = u'TestInstitution'
    i.technical_contact = u'TestTechnicalContact Name'
    i.email = u'contact@test.com'
    i.contact = u'TestContact Name'
    i.code = u'TestCode'



def tearDown_test_data():
    for table, data in test_data_table_control:
        for row in data:
            #print 'delete %s %s' % (table, row['id'])
            table.delete(table.c.id==row['id']).execute()




# TODO: things to create tests for
#
# - test all cascading works as expected
# - need to test that the Donor doesn't get deleted if it is orphaned since
# we don't want to ever throw out donor information

# TODO: if we ever get a GUI tester then do the following
# test all possible combinations of entering data into the accession editor
# 1. new accession without source
# 2. new accession with source
# 3. existing accession without source
# 4. existing accession with new source
# 5. existing accession with existing source
# - create test for parsing latitude/longitude entered into the lat/lon entries


class GardenTestCase(BaubleTestCase):

    def __init__(self, *args):
        super(GardenTestCase, self).__init__(*args)

    def setUp(self):
        super(GardenTestCase, self).setUp()
        plants_test.setUp_test_data()
        setUp_test_data()

    def tearDown(self):
        super(GardenTestCase, self).tearDown()
        plants_test.tearDown_test_data()
        tearDown_test_data()


class DonorTests(GardenTestCase):

    def __init__(self, *args):
        super(DonorTests, self).__init__(*args)

    def test_delete_donor(self):
        acc = self.session.load(Accession, 1)
        donor = self.session.load(Donor, 1)
        donation = Donation()
        donation.donor = donor
        acc.source = donation
        self.session.commit()
        self.session.close()

        # do the rest in a new session
        import bauble
        session = bauble.Session()
        donor = session.load(Donor, 1)
        # shouldn't be allowed to delete donor if it has donations,
        # what is happening here is that when deleting the donor the
        # corresponding donations.donor_id's are being be set to null which
        # isn't allowed by the scheme....is this the best we can do? or can we
        # get some sort of error when creating a dangling reference
        session.delete(donor)
        self.assertRaises(SQLError, session.commit)


class AccessionTests(GardenTestCase):

    def __init__(self, *args):
        super(AccessionTests, self).__init__(*args)

    def test_set_source(self):
        acc = self.session.load(Accession, 1)
        donor = self.session.load(Donor, 1)

        # set source on accession as a Donation
        donation = Donation()
        donation.donor = donor
        acc.source = donation
        self.session.flush()
        self.session.expire(acc)
        acc = self.session.load(Accession, 1)
        self.assertEquals(acc.source.id, donation.id)

        # create a new Donation and set that as the source, this should
        # delete the old donation object since it's an orphan,
        old_donation_id = donation.id
        donation2 = Donation()
        donation2.donor = donor
        acc.source = donation2
        self.session.flush()
        self.session.expire(acc)
        self.assertEquals(acc.source.id, donation2.id)

        # make sure the old donation gets deleted since it's an orphan
        self.assertRaises(InvalidRequestError, self.session.load, Donation,
                          old_donation_id)

        # delete the source
        acc.source = None
        self.session.flush()
        self.session.expire(acc)
        old_donation_id = donation2.id
        self.assertEquals(acc.source, None)

        # make sure the orphaned donation get's deleted
        self.assertRaises(InvalidRequestError, self.session.load, Donation,
                          old_donation_id)

        # set accession.source to a Collection
        collection = Collection(locale=u'TestAccLocale')
        acc.source = collection
        self.session.flush()
        self.session.expire(acc)
        self.assertEquals(acc.source.id, collection.id)

        # changed source from collection to donation
        old_collection_id = collection.id
        donation3 = Donation()
        donation3.donor = donor
        acc.source = donation3
        self.session.flush()
        self.session.expire(acc)
        self.assertEquals(acc.source.id, donation3.id)

        # make sure the orphaned collection get's deleted
        self.assertRaises(InvalidRequestError, self.session.load, Collection,
                          old_collection_id)

        # change source from donation to collection
        old_donation_id = donation3.id
        collection2 = Collection(locale=u'TestAccLocale2')
        acc.source = collection2
        self.session.flush()
        self.session.expire(acc)
        self.assertEquals(acc.source.id, collection2.id)

        # change source without flushing
        donation4 = Donation()
        acc.source = donation4
        collection3 = Collection(locale=u'TestAccLocale3')
        acc.source = collection3
        self.session.flush()
#        utils.log.echo(False)

        # make sure the orphaned donation get's deleted
        self.assertRaises(InvalidRequestError, self.session.load, Donation,
                          old_donation_id)



# latitude: deg[0-90], min[0-59], sec[0-59]
# longitude: deg[0-180], min[0-59], sec[0-59]

ALLOWED_DECIMAL_ERROR = 5
THRESHOLD = .01
DMS = 0 # DMS
DEG_MIN_DEC = 1 # Deg with minutes decimal
DEG_DEC = 2 # Degrees decimal
UTM = 3 # Datum(wgs84/nad83 or nad27), UTM Zone, Easting, Northing

# decimal points to accuracy in decimal degrees
# 1 +/- 8000m
# 2 +/- 800m
# 3 +/- 80m
# 4 +/- 8m
# 5 +/- 0.8m
# 6 +/- 0.08m

conversion_test_data = (
                        ((('N', 17, 21, 59),('W', 89, 1, 41)),
                          ((17, 21.98333333), (-89, 1.68333333)),
                          (17.36638889, -89.02805556),
                          (('wgs84', 16, 284513, 1921226))),
                        ((('S', 50, 19, 32.59),('W', 74, 2, 11.6)),
                          ((-50, 19.543166), (-74, 2.193333)),
                          (-50.325719, -74.036555),
                          (('wgs84', 18, 568579, 568579)),
                          (('nad27', 18, 568581, 4424928)))
                        )

#parse_lat_lon_data = ('17, 21, 59', '17 21 59', '17:21:59',
#                      '17, 21.98333333', '17 21.98333333',
#                      '17.36638889',
#                      '50, 19, 32.59', '50 19 32.59', '50:19:32.59',
#                      '-50 19.543166', '-50, 19.543166',
#                      '-50.325719')
parse_lat_lon_data = ('17 21 59', '17 21.98333333', '17.36638889',
                      '50 19 32.59', '-50 19.543166', '-50.325719')


class DMSConversionTests(unittest.TestCase):

    # test coordinate conversions
    def test_dms_to_decimal(self):
        for data_set in conversion_test_data:
            dms_data = data_set[DMS]
            dec_data = data_set[DEG_DEC]
            lat_dec = dms_to_decimal(*dms_data[0])
            lon_dec = dms_to_decimal(*dms_data[1])
            self.assertAlmostEqual(lat_dec, dec_data[0], ALLOWED_DECIMAL_ERROR)
            self.assertAlmostEqual(lon_dec, dec_data[1], ALLOWED_DECIMAL_ERROR)


    def test_decimal_to_dms(self):
        # TODO: this is temporary disabled b/c the converted numbers aren't
        # exactly equal, the easiest thing would probably be to compare the
        # components of the returned tuples instead comparing the two
        # tuples together...we need to get this as accurate as possible
        for data_set in conversion_test_data:
            assert_ = lambda left, right: self.assert_(abs(left-right)<THRESHOLD, 'abs(%s - %s) is not less than %s' % (left, right, THRESHOLD))

            dms_data = data_set[DMS]
            dec_data = data_set[DEG_DEC]

            lat_dms = latitude_to_dms(dec_data[0])
            dms = dms_data[0]
            self.assertEqual(dms[0], lat_dms[0])
            assert_(dms[1], lat_dms[1])
            assert_(dms[2], lat_dms[2])
            assert_(dms[3], lat_dms[3])
##             print dms
##             print lat_dms
##             print abs(dms[3]-lat_dms[3])

            lon_dms = longitude_to_dms(dec_data[1])
            dms = dms_data[1]
            self.assertEqual(dms[0], lon_dms[0])
            assert_(dms[1], lon_dms[1])
            assert_(dms[2], lon_dms[2])
            assert_(dms[3], lon_dms[3])
##             print dms
##             print lon_dms
##             print abs(dms[3]-lon_dms[3])
##             print '--------'


    def test_parse_lat_lon(self):
        for data in parse_lat_lon_data:
            pass


class GardenTestSuite(unittest.TestSuite):

   def __init__(self):
       super(GardenTestSuite, self).__init__()
       self.addTests(map(DMSConversionTests, ('test_dms_to_decimal',
                                              'test_decimal_to_dms',
                                              'test_parse_lat_lon')))
       self.addTests(map(AccessionTests, ('test_set_source',)))
       self.addTests(map(DonorTests, ('test_delete_donor',)))


testsuite = GardenTestSuite
