#
# module to provide a list of common names for a plantname
#

#import os
#import gtk
from sqlobject import *
#import bauble.utils as utils
#import bauble.paths as paths
from bauble.plugins import BaubleTable#, tables, editors

class VernacularName(BaubleTable):
    
    name = UnicodeCol()
    language = UnicodeCol()
    
    species = ForeignKey('Species', notNull=True)
    
#class VernacularNameEditor(TableEditor):