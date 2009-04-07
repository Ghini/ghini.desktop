import unittest

from sqlalchemy import *
from sqlalchemy.exc import *

from bauble.error import CheckConditionError
from bauble.test import BaubleTestCase
import bauble.utils as utils
from bauble.plugins.garden.accession import Accession, AccessionEditor, \
    dms_to_decimal, decimal_to_dms, longitude_to_dms, latitude_to_dms
from bauble.plugins.garden.donor import Donor
from bauble.plugins.garden.source import Donation, Collection
from bauble.plugins.garden.plant import Plant, PlantEditor
from bauble.plugins.garden.location import Location
from bauble.plugins.plants.family import Family
from bauble.plugins.plants.genus import Genus
from bauble.plugins.plants.species_model import Species
import bauble.plugins.plants.test as plants_test
from bauble.plugins.garden.institution import Institution

# TODO: create a test to make sure that if you delete an accession then the
# plants that are "children" of this accession are also deleted
from datetime import datetime
accession_test_data = ({'id':1 , 'code': u'1.1', 'species_id': 1,
                        'date': datetime.today(),
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

test_data_table_control = ((Accession, accession_test_data),
                           (Location, location_test_data),
                           (Plant, plant_test_data),
                           (Donor, donor_test_data),
                           (Donation, donation_test_data),
                           (Collection, collection_test_data))

def setUp_data():
    """
    create_test_data()
    #if this method is called again before tearDown_test_data is called you
    #will get an error about the test data rows already existing in the database
    """
    for cls, data in test_data_table_control:
        table = cls.__table__
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
        plants_test.setUp_data()
        #setUp_test_data()
        self.family = Family(family=u'fam')
        self.genus = Genus(family=self.family, genus=u'gen')
        self.species = Species(genus=self.genus, sp=u'sp')
        self.session.add_all([self.family, self.genus, self.species])
        self.session.commit()


    def create(self, class_, **kwargs):
        obj = class_(**kwargs)
        self.session.add(obj)
        return obj


class DonorTests(GardenTestCase):


    def __init__(self, *args):
        super(DonorTests, self).__init__(*args)

    def test_delete(self):
        acc = self.create(Accession, species=self.species, code=u'1')
        donor = Donor(name=u'name')
        donation = Donation()
        donation.donor = donor
        acc.source = donation
        self.session.commit()
        self.session.close()

        # test that we can't delete a donor if it has corresponding donations
        import bauble
        session = bauble.Session()
        donor = session.query(Donor).filter_by(name=u'name').one()
        # shouldn't be allowed to delete donor if it has donations,
        # what is happening here is that when deleting the donor the
        # corresponding donations.donor_id's are being be set to null which
        # isn't allowed by the scheme....is this the best we can do? or can we
        # get some sort of error when creating a dangling reference
        session.delete(donor)
        self.assertRaises(SQLError, session.commit)


class PlantTests(GardenTestCase):

    def __init__(self, *args):
        super(PlantTests, self).__init__(*args)

    def setUp(self):
        super(PlantTests, self).setUp()

    def tearDown(self):
        super(PlantTests, self).tearDown()


    def test_constraints(self):
        acc = self.create(Accession, species=self.species, code=u'1')
        location = Location(site=u'site')
        plant = Plant(accession=acc, location=location, code=u'1')
        self.session.commit()

        # test that we can't have duplicate codes with the same accession
        plant2 = Plant(accession=acc, location=location, code=u'1')
        self.session.add(plant2)
        self.assertRaises(IntegrityError, self.session.commit)

    def test_delete(self):
        """
        Test that when a plant is deleted...
        """
        pass

    def itest_plant_editor(self):
        """
        Interactively test the PlantEditor
        """
        acc = self.create(Accession, species=self.species, code=u'1')
        location = Location(site=u'site')
        plant = Plant(accession=acc, location=location, code=u'1')
        self.session.commit()
        editor = PlantEditor(model=plant)
        editor.start()



class AccessionTests(GardenTestCase):

    def __init__(self, *args):
        super(AccessionTests, self).__init__(*args)

    def setUp(self):
        super(AccessionTests, self).setUp()


    def tearDown(self):
        super(AccessionTests, self).tearDown()


    def test_species_str(self):
        """
        Test Accesion.species_str()
        """
        acc = self.create(Accession, species=self.species, code=u'1')
        s = 'gen sp'
        sp_str = acc.species_str()
        self.assert_(s == sp_str, '%s == %s' % (s, sp_str))
        acc.id_qual = '?'
        s = 'gen sp(?)'
        sp_str = acc.species_str()
        self.assert_(s == sp_str, '%s == %s' % (s, sp_str))

        acc.id_qual = 'aff.'
        acc.id_qual_rank = 'sp'
        s = 'gen aff. sp'
        sp_str = acc.species_str()
        self.assert_(s == sp_str, '%s == %s' %(s, sp_str))

        # here species.infrasp is None but we still allow the string
        acc.id_qual = 'cf.'
        acc.id_qual_rank = 'infrasp'
        s = 'gen sp cf. None'
        sp_str = acc.species_str()
        self.assert_(s == sp_str, '%s == %s' %(s, sp_str))

        # species.infrasp is still none but these just get pasted on
        # the end so it doesn't matter
        acc.id_qual = 'incorrect'
        acc.id_qual_rank = 'infrasp'
        s = 'gen sp(incorrect)'
        sp_str = acc.species_str()
        self.assert_(s == sp_str, '%s == %s' %(s, sp_str))

        acc.id_qual = 'forsan'
        acc.id_qual_rank = 'sp'
        s = 'gen sp(forsan)'
        sp_str = acc.species_str()
        self.assert_(s == sp_str, '%s == %s' %(s, sp_str))

        acc.species.infrasp_rank = 'cv.'
        acc.species.infrasp = 'Cultivar'
        acc.id_qual = 'cf.'
        acc.id_qual_rank = 'infrasp'
        s = "gen sp cf. 'Cultivar'"
        sp_str = acc.species_str()
        self.assert_(s == sp_str, '%s == %s' %(s, sp_str))

        # this used to test that if the id_qual was set but the
        # id_qual_rank wasn't then we would get an error. now we just
        # show an warning and put the id_qual on the end of the string
#         acc.id_qual = 'aff.'
#         acc.id_qual_rank = None
#         self.assertRaises(CheckConditionError, acc.species_str)


    def test_delete(self):
        """
        Test that when an accession is deleted any orphaned rows are
        cleaned up.
        """
        acc = self.create(Accession, species=self.species, code=u'1')
        plant = self.create(Plant, accession=acc,
                            location=Location(site=u'site'), code=u'1')
        self.session.commit()

        # test that the plant is deleted after being orphaned
        plant_id = plant.id
        self.session.delete(acc)
        self.session.commit()
        self.assert_(not self.session.query(Plant).get(plant_id))

        # test that the donation and collection is deleted after being orphaned
        #is done in test_source
#         acc = acc = self.create(Accession, species=self.species, code=u'1')
#         coll = Collection(locale=u'locale')
#         acc.source = coll
#         self.session.add(coll)
#         self.session.commit()
#         coll_id = coll.id
#         self.session.delete(acc)
#         self.session.commit()
#         self.assert_(not self.session.query(Plant).get(coll_id))
        # test that the collection is orphaned after being deleted

    def test_constraints(self):
        """
        Test the constraints on the accession table.
        """
        acc = Accession(species=self.species, code=u'1')
        self.session.add(acc)
        self.session.commit()

        # test that accession.code is unique
        acc = Accession(species=self.species, code=u'1')
        self.session.add(acc)
        self.assertRaises(IntegrityError, self.session.commit)


    def test_set_source(self):
        #acc = self.session.query(Accession).get(1)
        #donor = self.session.query(Donor).get(1)
        acc = Accession(code=u'1', species=self.species)
        donor = Donor(name=u'me')
        self.session.add_all([acc, donor])
        self.session.commit()

        # set source on accession as a Donation
        donation = Donation()
        donation.donor = donor
        acc.source = donation
        self.session.flush()
        #self.session.expire(acc)
        self.session.refresh(acc)
        self.assertEquals(acc.source.id, donation.id)
        self.assertEquals(acc.source_type, u'Donation')

        # create a new Donation and set that as the source, this should
        # delete the old donation object since it's an orphan,
        old_donation_id = donation.id
        donation2 = Donation()
        donation2.donor = donor
        acc.source = donation2
        self.session.flush()
        self.session.expire(acc)
        self.assertEquals(acc.source.id, donation2.id)
        self.assertEquals(acc.source_type, u'Donation')

        # delete all the donations
        # TODO: the donor should never be deleted if a donation is
        # deleted and a donation should never get deleted if a donor
        # is deleted, an error should be reaised if you attempt to
        # delete a donor that has donations but should an error be
        # raised if you attempt to delete a donation that has a donor,
        # i don't think so

        # make sure the old donation gets deleted since it's an orphan
        print self.session.query(Donation).get(old_donation_id)
        self.assert_(self.session.query(Donation).get(old_donation_id) == None)

        # delete the source by setting acc.source=None
        donation = Donation()
        donation.donor = donor
        acc.source = donation
        acc.source = None
        self.session.flush()
        self.session.expire(acc)
        old_donation_id = donation2.id
        self.assertEquals(acc.source, None)
        self.assertEquals(acc.source_type, None)

        # delete the source 2
        donation = Donation()
        donation.donor = donor
        acc.source = donation
        del acc.source
        self.session.flush()
        self.session.expire(acc)
        old_donation_id = donation2.id
        self.assertEquals(acc.source, None)
        self.assertEquals(acc.source_type, None)

        # make sure the orphaned donation get's deleted
        self.assert_(not self.session.query(Donation).get(old_donation_id))

        # set accession.source to a Collection
        collection = Collection(locale=u'TestAccLocale')
        acc.source = collection
        self.session.flush()
        self.session.expire(acc)
        self.assertEquals(acc.source.id, collection.id)
        self.assertEquals(acc.source_type, u'Collection')

        # changed source from collection to donation
        old_collection_id = collection.id
        donation3 = Donation()
        donation3.donor = donor
        acc.source = donation3
        self.session.flush()
        self.session.expire(acc)
        self.assertEquals(acc.source.id, donation3.id)
        self.assertEquals(acc.source_type, u'Donation')

        # make sure the orphaned collection get's deleted
        self.assert_(not self.session.query(Collection).get(old_collection_id))

        # change source from donation to collection
        old_donation_id = donation3.id
        collection2 = Collection(locale=u'TestAccLocale2')
        acc.source = collection2
        self.session.flush()
        self.session.expire(acc)
        self.assertEquals(acc.source.id, collection2.id)
        self.assertEquals(acc.source_type, u'Collection')

        # change source without flushing
        donation4 = Donation()
        acc.source = donation4
        collection3 = Collection(locale=u'TestAccLocale3')
        acc.source = collection3
        self.session.flush()
#        utils.log.echo(False)

        # make sure the orphaned donation get's deleted
        self.assert_(not self.session.query(Donation).get(old_donation_id))


    def test_double_commit(self):
        """
        This tests a bug with SQLAlchemy that was tentatively fixed
        after SQ 0.4.4 was released in r4264.  There is a reference to
        this in the SA mailing list.

        The bug is here just to check if this ever gets fixed.
        """
        import bauble.utils.log as log
        sp = self.session.query(Species).get(1)
        acc = Accession()
        self.session.add(acc)
        acc.species = sp
        acc.code = u"3"
        # not donor_id, should raise an IntegrityError
        donation = Donation()
        acc.source = donation
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            # before SA 0.4.5 this would give and InvalidRequestError
            # about not being able to refresh Accession after a rollback
            try:
                self.session.commit()
            except InvalidRequestError, e:
                # we get here in SA pre-0.4.5, we can't use those
                # versions for bauble
                raise
            except IntegrityError:
                # it should raise an integrity error because there is
                # still no donor_id on donation
                pass


    def itest_accession_editor(self):
        """
        Interactively test the PlantEditor
        """
        donor = self.create(Donor, name=u'test')
        self.session.commit()
        acc = self.create(Accession, species=self.species, code=u'1')
        editor = AccessionEditor(model=acc)
        editor.start()
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

from decimal import Decimal
dec = Decimal
conversion_test_data = (
                        ((('N', 17, 21, dec(59)), # dms
                          ('W', 89, 1, 41)),
                         ((dec(17), dec('21.98333333')), # deg min_dec
                          (dec(-89), dec('1.68333333'))),
                         (dec('17.366389'), dec('-89.028056')), # dec deg
                         (('wgs84', 16, 284513, 1921226))), # utm
                        ((('S', 50, 19, dec('32.59')), # dms
                          ('W', 74, 2, dec('11.6'))),
                         ((dec(-50), dec('19.543166')), # deg min_dec
                          (dec(-74), dec('2.193333'))),
                         (dec('-50.325719'), dec('-74.036556')), # dec deg
                          (('wgs84', 18, 568579, 568579)),
                          (('nad27', 18, 568581, 4424928))),
                        ((('N', 9, 0, dec('4.593384')),
                          ('W', 78, 3, dec('28.527984'))),
                         ((9, dec('0.0765564')),
                          (-78, dec('3.4754664'))),
                         (dec('9.00127594'), dec('-78.05792444')))
                        )

#parse_lat_lon_data = ('17, 21, 59', '17 21 59', '17:21:59',
#                      '17, 21.98333333', '17 21.98333333',
#                      '17.36638889',
#                      '50, 19, 32.59', '50 19 32.59', '50:19:32.59',
#                      '-50 19.543166', '-50, 19.543166',
#                      '-50.325719')
parse_lat_lon_data = ('17 21 59', '17 21.98333333', '17.03656',
                      '50 19 32.59', '-50 19.543166', '-50.32572')


class DMSConversionTests(unittest.TestCase):

    # test coordinate conversions
    def test_dms_to_decimal(self):
        # test converting DMS to degrees decimal
        ALLOWED_ERROR = 6
        for data_set in conversion_test_data:
            dms_data = data_set[DMS]
            dec_data = data_set[DEG_DEC]
            lat_dec = dms_to_decimal(*dms_data[0])
            lon_dec = dms_to_decimal(*dms_data[1])
            self.assertAlmostEqual(lat_dec, dec_data[0], ALLOWED_ERROR)
            self.assertAlmostEqual(lon_dec, dec_data[1], ALLOWED_ERROR)



    def test_decimal_to_dms(self):
        # test converting degrees decimal to dms, allow a certain
        # amount of error in the seconds
        ALLOWABLE_ERROR = 2
        for data_set in conversion_test_data:
            dms_data = data_set[DMS]
            dec_data = data_set[DEG_DEC]

            # convert to DMS
            lat_dms = latitude_to_dms(dec_data[0])
            self.assertEqual(lat_dms[0:2], dms_data[0][0:2])
            # test seconds with allowable error
            self.assertAlmostEqual(lat_dms[3], dms_data[0][3], ALLOWABLE_ERROR)

            lon_dms = longitude_to_dms(dec_data[1])
            self.assertEqual(lon_dms[0:2], dms_data[1][0:2])
            # test seconds with allowable error
            self.assertAlmostEqual(lon_dms[3], dms_data[1][3], ALLOWABLE_ERROR)


    def test_parse_lat_lon(self):
        for data in parse_lat_lon_data:
            pass



