#
# provide paths that bauble will need
#

import os, sys

# we can't the i18n module because it depends on this module for locale_dir
#from bauble.i18n import _

# TODO: we could just have setup or whatever create a file in the lib
# directory that tells us where all the other directories are but how do we
# know where the lib directory is

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
                              'APPDATA or USERPROFILE variable')
#             raise Exception(_('Could not get path for user settings: no ' \
#                               'APPDATA or USERPROFILE variable'))
    elif sys.platform == "linux2":
        # using os.expanduser is more reliable than os.environ['HOME']
        # because if the user runs bauble with sudo then it will
        # return the path of the user that used sudo instead of ~root
        try:
            return os.path.join(os.path.expanduser('~%s' % os.environ['USER']),
				'.bauble')
        except:
            raise Exception('Could not get path for user settings: '\
                            'no HOME variable')
#             raise Exception(_('Could not get path for user settings: '\
#                               'no HOME variable'))
    else:
        raise Exception('Could not get path for user settings: '\
                          'no HOME variable')
#         raise Exception(_('Could not get path to user settings: ' \
#                           'unsupported platform'))
