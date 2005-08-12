#
# garden plugin 
#

import os, sys
from accession import *

print 'from plugins import BaublePlugin'
from bauble.plugins import BaublePlugin
print '---- from plugins import BaublePlugin'

#from cultivation import *

class GardenPlugin(BaublePlugin):
    editors = []
    tables = []
    views = []
    depends = ("plants",)

plugin = GardenPlugin