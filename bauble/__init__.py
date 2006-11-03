#
# bauble module
#

import imp, os, sys

# major, minor, revision 
# should be updated for each release of bauble

# this is from the python docs, we should probably have something similar
# for bauble so we can do release candidate and beta releases
# version_info 
# A tuple containing the five components of the version number: 
# major, minor, micro, releaselevel, and serial. All values except 
# releaselevel are integers; the release level is 'alpha', 'beta', 
# 'candidate', or 'final'. The version_info value corresponding to the Python 
# version 2.0 is (2, 0, 0, 'final', 0). New in version 2.0. 
version = (0,6,0)
version_str = '%s.%s.%s' % (version)

def main_is_frozen():
   return (hasattr(sys, "frozen") or # new py2exe
           hasattr(sys, "importers") or # old py2exe
           imp.is_frozen("__main__")) # tools/freeze

import pygtk
if not main_is_frozen():
   pygtk.require("2.0")     
else: # main is frozen
   # put library.zip first in the path when using py2exe so libxml2 gets 
   # imported correctly, 
   zipfile = sys.path[-1]
   sys.path.insert(0,zipfile)

import gtk
import bauble.utils as utils
import bauble.paths as paths
sys.path.append(paths.lib_dir())

# create the user directory
if not os.path.exists(paths.user_dir()):
    os.makedirs(paths.user_dir())

try:
    from sqlalchemy import *
    # TODO: check sqlalchemy version
except ImportError:
    msg = "SQLAlchemy not installed. Please install SQAlchemy from "\
          "http://www.sqlalchemy.org"
    utils.message_dialog(msg, gtk.MESSAGE_ERROR)    
    raise


# set SQLAlchemy logging level
import logging
#logging.getLogger('sqlalchemy').setLevel(logging.DEBUG)
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)

# TODO: make this work, we get strange errors when using this, probably because
# of the way table is implemented, with a singleton metaclass
#
#class BaubleTable(Table):
#    
#    def __init__(self, *args, **kwargs):
#        # TODO: add _created
#        super(BaubleTable, self).__init__(*args, **kwargs)
#        super(BaubleTable, self).append_column(Column('_last_updated', DateTime, 
#                                                      onupdate=func.current_timestamp()))

class BaubleMapper(object):
    
    def __init__(self, **kwargs):
        for attr, value in kwargs.iteritems():
            setattr(self, attr, value)


from bauble._app import BaubleApp
app = BaubleApp()


