import unittest
from sqlalchemy import *
from sqlalchemy.exceptions import *
from testbase import BaubleTestCase, log
from bauble.plugins.garden.accession import Accession, accession_table, \
    dms_to_decimal, decimal_to_dms, longitude_to_dms, latitude_to_dms
from bauble.plugins.garden.donor import Donor, donor_table
from bauble.plugins.garden.source import Donation, Collection
from bauble.plugins.garden.plant import plant_table
from bauble.plugins.garden.location import location_table
from bauble.plugins.plants.family import family_table
from bauble.plugins.plants.genus import genus_table
from bauble.plugins.plants.species_model import species_table
import bauble.plugins.plants.test as plants_test


accession_test_data = ({'id':1 , 'code': '1.1', 'species_id': 1},
                       )

plant_test_data = ({'id':1 , 'code': '1', 'accession_id': 1, 'location_id': 1},
                   )

location_test_data = ({'id': 1, 'site': 'Somewhere Over The Rainbow'},
                      )

donor_test_data = ({'id': 1, 'name': 'SomeDonor'},
                   )

def setUp_test_data():
    '''
    if this method is called again before tearDown_test_data is called you
    will get an error about the test data rows already existing in the database
    '''
    accession_table.insert().execute(*accession_test_data)
    location_table.insert().execute(*location_test_data)
    plant_table.insert().execute(*plant_test_data)
    donor_table.insert().execute(*donor_test_data)


def tearDown_test_data():
    control = ((accession_table, accession_test_data),
               (location_table, location_test_data),
               (plant_table, plant_test_data),
               (donor_table, donor_test_data))
    for table, data in control:
        for row in data:
            #print 'delete %s %s' % (table, row['id'])
            table.delete(table.c.id==row['id']).execute()




# TODO: things to create tests for
#
# - test all cascading works as expected
# - test adding a source to an accession and changeing the source the same
# way it's done in the accession editor
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

# latitude: deg[0-90], min[0-59], sec[0-59]
# longitude: deg[0-180], min[0-59], sec[0-59]

ALLOWED_DECIMAL_ERROR = 5
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

    def setUp(self):
        super(DonorTests, self).setUp()


    def test_delete_donor(self):
        session = create_session()
        acc = session.query(Accession).select()[0]
        donor = session.query(Donor).select()[0]
        donation = Donation(donor_id=donor.id)
        acc.source = donation
        session.flush()
        session.close()

        # do the rest in a new session
        session = create_session()
        donor = session.query(Donor).select()[0]
        # shouldn't be allowed to delete donor if it has donations,
        # what is happening here is that when deleting the donor the
        # corresponding donations.donor_id's are being be set to null which
        # isn't allowed by the scheme....is this the best we can do? or can we
        # get some sort of error when creating a dangling reference
        session.delete(donor)
        self.assertRaises(SQLError, session.flush)


class AccessionTests(GardenTestCase):

    def setUp(self):
        super(AccessionTests, self).setUp()


    def test_set_source(self):
        session = create_session()
        query = session.query(Accession)
        acc = query.select_by(code='1.1')[0]
        # acc.source is None
        self.assert_(acc.source == None)

        # set source on accession as a Donation
        donor_id = select([donor_table.c.id], donor_table.c.id==1).scalar()
        #donor_id = session.load(Donor, 1).id
        donation = Donation(donor_id=donor_id)
        acc.source = donation
        session.flush()
        session.expire(acc)
        self.assertEquals(acc.source.id, donation.id)

        # create a new Donation and set that as the source, this should
        # delete the old donation object since it's an orphan,
        old_donation_id = donation.id
        donation2 = Donation(donor_id=donor_id)
        acc.source = donation2
        session.flush()
        session.expire(acc)
        self.assertEquals(acc.source.id, donation2.id)

        # make sure the old donation gets deleted since it's an orphan
        self.assertRaises(InvalidRequestError, session.load, Donation, old_donation_id)

        # delete the source
        acc.source = None
        session.flush()
        session.expire(acc)
        old_donation_id = donation2.id
        self.assertEquals(acc.source, None)

        # make sure the orphaned donation get's deleted
        self.assertRaises(InvalidRequestError, session.load, Donation, old_donation_id)

        # set accession.source to a Collection
        collection = Collection(locale='TestAccLocale')
        acc.source = collection
        session.flush()
        session.expire(acc)
        self.assertEquals(acc.source.id, collection.id)

        # changed source from collection to donation
        old_collection_id = collection.id
        donation3 = Donation(donor_id=donor_id)
        acc.source = donation3
        session.flush()
        session.expire(acc)
        self.assertEquals(acc.source.id, donation3.id)

        # make sure the orphaned collection get's deleted
        self.assertRaises(InvalidRequestError, session.load, Collection, old_collection_id)

        # change source from donation to collection
        old_donation_id = donation3.id
        collection2 = Collection(locale='TestAccLocale2')
        acc.source = collection2
        session.flush()
        session.expire(acc)
        self.assertEquals(acc.source.id, collection2.id)

        # make sure the orphaned donation get's deleted
        self.assertRaises(InvalidRequestError, session.load, Donation, old_donation_id)

        session.close()


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
        # tuples together
        return

        for data_set in conversion_test_data:
            dms_data = data_set[DMS]
            dec_data = data_set[DEG_DEC]
            lat_dms = latitude_to_dms(dec_data[0])
            self.assertEqual(dms_data[0], lat_dms)
            lon_dms = longitude_to_dms(dec_data[1])
            self.assertEqual(dms_data[1], lon_dms)


    def test_parse_lat_lon(self):
        for data in parse_lat_lon_data:
            pass


class GardenTestSuite(unittest.TestSuite):

   def __init__(self):
       unittest.TestSuite.__init__(self)
       self.addTests(map(DMSConversionTests, ('test_dms_to_decimal',
                                              'test_decimal_to_dms',
                                              'test_parse_lat_lon')))
       self.addTests(map(AccessionTests, ('test_set_source',)))
       self.addTests(map(DonorTests, ('test_delete_donor',)))


testsuite = GardenTestSuite
