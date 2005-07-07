
from tables import *

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
    iso_code = StringCol()
    
    continent = ForeignKey('Continents')
    areas = MultipleJoin('Areas', joinColumn='area_id')
    
    def __str__(self): return self.region
    
    
# level3
class Areas(BaubleTable):
    code = StringCol(length=5)
    #area = StringCol(length=64)
    area = UnicodeCol(length=64)
    iso_code = StringCol(length=4)
    ed2_status = StringCol(length=64)
    notes = StringCol()
    
    region = ForeignKey('Region')
    areas = MultipleJoin('Countries', joinColumn='country_id')
    
    def __str__(self): return self.area
    
    
# level4
class Countries(BaubleTable):
    country = UnicodeCol(length=64)
    code = StringCol(length=8)
    iso_code = StringCol(length=8)
    ed2_status = StringCol(length=64)
    notes = UnicodeCol()
    area = ForeignKey('Area')
    
    def __str__(self): return self.country
    
    
# gazetteer
class Places(BaubleTable):
    name = UnicodeCol(length=64)
    synonym = UnicodeCol(length=64)
    notes = UnicodeCol()
    
    #continent = ForeignKey('Continent')
    region = ForeignKey('Region')
    area = ForeignKey('Area')
    country = ForeignKey('Countries')
    region = ForeignKey('Region')
    kew_region = ForeignKey('KewRegions')

    def __str__(self): return self.name


class KewRegions(BaubleTable):
    
    # one column in the data has none, i don't know why
    code = IntCol(default=None)
    subdiv = StringCol(length=1, default=None)
    region = StringCol(length=64)
    
    places = MultipleJoin('Places', joinColumn='kew_region_id')
    
    def __str__(self): return self.region
    
tables = [Continents, Regions, Areas, Countries, Places, KewRegions]