#
#
#

import os, sys
import bauble.utils as utils

def main_dir():
   if utils.main_is_frozen():
       dir = os.path.dirname(sys.executable)
   else: dir = os.path.dirname(sys.argv[0])
   if dir == "": 
       dir = os.curdir
   return dir


def lib_dir():
    return os.path.dirname(__file__)