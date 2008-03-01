#
# provide paths that bauble will need
#

import os, sys

# TODO: we could just have setup or whatever create a file in the lib
# directory that tells us where all the other directories are but how do we
# know where the lib directory is

# TODO: for Linux/*nix support we need to be able to find /usr/share/X
# for files like icons and bauble.desktop

def main_is_frozen():
    import imp
    return (hasattr(sys, "frozen") or # new py2exe
            hasattr(sys, "importers") or # old py2exe
            imp.is_frozen("__main__")) # tools/freeze

def main_dir():
    #if bauble.main_is_frozen():
    if main_is_frozen():
       dir = os.path.dirname(sys.executable)
    else:
       dir = os.path.dirname(sys.argv[0])
    if dir == "":
       dir = os.curdir
    return dir


def lib_dir():
    #if bauble.main_is_frozen():
    if main_is_frozen():
       dir = os.path.join(main_dir(), 'bauble')
    else:
        dir = os.path.dirname(__file__)
    return dir


def locale_dir():
    if sys.platform == 'win32':
        return os.path.join(lib_dir(), 'po')
    else:
        # TODO: need to get the share directory where the locale files were
        # installed
        return os.path.join(lib_dir(), 'po')


def user_dir():
    if sys.platform == "win32":
        if 'APPDATA' in os.environ:
            dir = os.path.join(os.environ["APPDATA"], "Bauble")
        elif 'USERPROFILE' in os.environ:
            dir = os.path.join(os.environ['USERPROFILE'], 'Application Data',
                               'Bauble')
        else:
            raise Exception('Could not get path for user settings: no ' \
                            'APPDATA variable')
    elif sys.platform == "linux2":
        if 'HOME' in os.environ:
            dir = os.path.join(os.environ["HOME"], ".bauble")
        else:
            raise Exception('Could not get path for user settings: '\
                            'no HOME variable')
    else:
        raise Exception('Could not get path to user settings: ' \
                         'unsupported platform')
    return dir
