
from bauble.plugins import BaubleTable
from sqlobject import *

class Country(BaubleTable):
    name = StringCol(length=50)
    code = StringCol(length=2)