#
# bauble module
#

import imp, os, sys

def main_is_frozen():
   return (hasattr(sys, "frozen") or # new py2exe
           hasattr(sys, "importers") # old py2exe
           or imp.is_frozen("__main__")) # tools/freeze

import pygtk
if not main_is_frozen():
    pygtk.require("2.0")
import gtk

import bauble.utils as utils
import bauble.paths as paths


sys.path.append(paths.lib_dir())
sys.path.append(paths.lib_dir() + os.sep + 'lib')

# TODO: the plugins dir should be on the path so we can import
# plugins without bauble.plugins in front of it and so the plugins don't 
# have to be in the lib dir



try:
    from sqlobject import *
except ImportError:
    msg = "SQLObject not installed. Please install SQLObject from "\
          "http://www.sqlobject.org"
    utils.message_dialog(msg, gtk.MESSAGE_ERROR)    
    raise

from bauble._app import BaubleApp
app = BaubleApp()


