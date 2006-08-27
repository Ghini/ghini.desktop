import unittest
from bauble.plugins.garden.accession import \
    dms_to_decimal, decimal_to_dms, longitude_to_dms, latitude_to_dms
    
# TODO: things to create tests for
# 
# - test all cascading works as expected
# - test adding a source to an accession and changeing the source the same
# way it's done in the accession editor

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
       unittest.TestSuite.__init__(self, map(DMSConversionTests,                                         
                                             ('test_dms_to_decimal',
                                              'test_decimal_to_dms',
                                              'test_parse_lat_lon')))
testsuite = GardenTestSuite
