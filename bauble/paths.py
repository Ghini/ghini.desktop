#
# provide paths that bauble will need
#

import os, sys

# TODO: we could just have setup or whatever create a file in the lib
# directory that tells us where all the other directories are but how do we
# know where the lib directory is

def main_is_frozen():
    """
    Returns True/False if Bauble is being run from a py2exe
    executable.  This method duplicates bauble.main_is_frozen in order
    to make paths.py not depend on any other Bauble modules.
    """
    import imp
    return (hasattr(sys, "frozen") or # new py2exe
            hasattr(sys, "importers") or # old py2exe
            imp.is_frozen("__main__")) # tools/freeze


def main_dir():
    """
    Returns the path of the bauble executable.
    """
    if main_is_frozen():
        d = os.path.dirname(sys.executable)
    else:
        d = os.path.dirname(sys.argv[0])
    if d == "":
        d = os.curdir
    return d


def lib_dir():
    """
    Returns the path of the bauble module.
    """
    if main_is_frozen():
        d = os.path.join(main_dir(), 'bauble')
    else:
        d = os.path.dirname(__file__)
    return d


def locale_dir():
    """
    Returns the root path of the locale files
    """
    if sys.platform == 'linux2':
        return os.path.join('/usr', 'share', 'locale')
    elif sys.platform == 'win32':
        import bauble.paths as paths
        return os.path.join(paths.main_dir(), 'share', 'locale')
    else:
        raise NotImplementedError('This platform does not support '\
                                  'translations: %s' % sys.platform)


def user_dir():
    """
    Returns the path to where Bauble settings should be saved.
    """
    from bauble.i18n import _
    if sys.platform == "win32":
        if 'APPDATA' in os.environ:
            return os.path.join(os.environ["APPDATA"], "Bauble")
        elif 'USERPROFILE' in os.environ:
            return os.path.join(os.environ['USERPROFILE'], 'Application Data',
                               'Bauble')
        else:
            from bauble.i18n import _
            raise Exception(_('Could not get path for user settings: no ' \
                              'APPDATA or USERPROFILE variable'))
    elif sys.platform == "linux2":
        # using os.expanduser is more reliable than os.environ['HOME']
        # because if the user runs bauble with sudo then it will
        # return the path of the user that used sudo instead of ~root
        try:
            return os.path.join(os.path.expanduser('~%s' % os.environ['USER']),
				'.bauble')
        except:
            raise Exception(_('Could not get path for user settings: '\
                              'could not expand $HOME for user %(username)s' %\
                              dict(username=os.environ['USER'])))
    else:
        raise Exception(_('Could not get path for user settings: '\
                          'unsupported platform'))

