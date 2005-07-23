
from tables import *

# FIXME: there are lots of problems with these tables
# 1. in some tables there is a row with no real values, i think this means
# from a cultivated source with no know origin but it should be verified and
# more intuitive
# 2. some row values that have default=None shouldn't, they are only set that
# way so that the mystery row with no values will import correctly
# 3. other stuff...


# level 1
class Continents(BaubleTable):
    continent = StringCol(length=24)
    code = IntCol()
    
    regions = MultipleJoin('Regions', joinColumn='continent_id')
    
    def __str__(self): return self.continent
    
    
# level2
class Regions(BaubleTable):
    region = StringCol(length=64)
    code = IntCol()
    
    # i don't think this is used
    iso_code = StringCol(default=None)
    
    continent = ForeignKey('Continents')
    areas = MultipleJoin('Areas', joinColumn='region_id')
    
    def __str__(self): return self.region
    
    
# level3
class Areas(BaubleTable):
    code = StringCol(length=5)
    #area = StringCol(length=64)
    area = UnicodeCol(length=64)
    iso_code = StringCol(length=4, default=None)
    ed2_status = StringCol(length=64, default=None)
    notes = StringCol(default=None)
    
    region = ForeignKey('Region')
    states = MultipleJoin('States', joinColumn='area_id')
    
    def __str__(self): return self.area
    
    
# level4
class States(BaubleTable):
    state = UnicodeCol(length=64)
    code = StringCol(length=8)
    iso_code = StringCol(length=8)
    ed2_status = StringCol(length=64, default=None)
    notes = UnicodeCol(default=None)
    
    area = ForeignKey('Area')
    places = MultipleJoin('Places', joinColumn='state_id')
    
    def __str__(self): return self.state
    
    
# gazetteer
class Places(BaubleTable):
    
    # TODO: if this is None then i think it means cultivated, should really do
    # something about this
    name = UnicodeCol(length=64, default=None)
    synonym = UnicodeCol(length=64, default=None)
    notes = UnicodeCol(default=None)
    
    #continent = ForeignKey('Continent')
    region = ForeignKey('Region', default=None)
    area = ForeignKey('Area', default=None)
    state = ForeignKey('States', default=None)
    kew_region = ForeignKey('KewRegions', default=None)

    def __str__(self): return self.name


class KewRegions(BaubleTable):
    
    # TODO: one column in the data has none, i don't know why, i think it means
    # that its cultivated and its origin is unknown, neother code or region
    # should really be None
    code = IntCol(default=None)
    region = StringCol(length=64, default=None)
    subdiv = StringCol(length=1, default=None)
    
    
    
    places = MultipleJoin('Places', joinColumn='kew_region_id')
    
    def __str__(self): return self.region
    
tables = [Continents, Regions, Areas, States, Places, KewRegions]