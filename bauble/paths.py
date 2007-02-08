#
# provide paths that bauble will need
#

import os, sys
import bauble

def main_dir():
   if bauble.main_is_frozen():
       dir = os.path.dirname(sys.executable)
   else: 
      dir = os.path.dirname(sys.argv[0])
   if dir == "": 
       dir = os.curdir
   return dir


def lib_dir():
    if bauble.main_is_frozen():
       dir = os.path.join(main_dir(), 'bauble')
    else:
        dir = os.path.dirname(__file__)
    return dir

    
def user_dir():
    if sys.platform == "win32":
        if 'APPDATA' in os.environ:
            dir = os.path.join(os.environ["APPDATA"], "Bauble")
        else:
            raise Exception(_('Could not get path for user settings: no ' \
                              'APPDATA variable'))
    elif sys.platform == "linux2":
        if 'HOME' in os.environ:
            dir = os.path.join(os.environ["HOME"], ".bauble")
        else:
            raise Exception(_('Could not get path for user settings: '\
                              'no HOME variable'))
    else:
        raise Exception(_('Could not get path to user settings: ' \
                          'unsupported platform'))    
    return dir
