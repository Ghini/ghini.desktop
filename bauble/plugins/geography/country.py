
from bauble.plugins import BaubleTable
from sqlobject import *

class Country(BaubleTable):
    country = UnicodeCol(length=50)
    code = StringCol(length=2)
    
    def __str__(self):
        return self.country