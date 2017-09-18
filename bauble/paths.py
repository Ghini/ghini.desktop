# -*- coding: utf-8 -*-
#
# Copyright (c) 2005,2006,2007,2008,2009 Brett Adams <brett@belizebotanic.org>
# Copyright (c) 2012-2016 Mario Frasca <mario@anche.no>
# Copyright (c) 2016 Ross Demuth <rossdemuth123@gmail.com>
#
# This file is part of ghini.desktop.
#
# ghini.desktop is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ghini.desktop is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ghini.desktop. If not, see <http://www.gnu.org/licenses/>.
#
# provide paths that bauble will need
#
"""
Access to standard paths used by Ghini.
"""
import os
import sys


def main_is_frozen():
    """
    Returns True/False if Ghini is being run from a py2exe
    executable.  This method duplicates bauble.main_is_frozen in order
    to make paths.py not depend on any other Bauble modules.
    """
    import imp
    return (hasattr(sys, "frozen") or  # new py2exe
            hasattr(sys, "importers") or  # old py2exe
            imp.is_frozen("__main__"))  # tools/freeze


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
    return os.path.abspath(d)


def lib_dir():
    """
    Returns the path of the bauble module.
    """
    if main_is_frozen():
        d = os.path.join(main_dir(), 'bauble')
    else:
        d = os.path.dirname(__file__)
    return os.path.abspath(d)


def locale_dir():
    """
    Returns the root path of the locale files
    """

    the_installation_directory = installation_dir()
    d = os.path.join(the_installation_directory, 'share', 'locale')
    return os.path.abspath(d)


def installation_dir():
    """
    Returns the root path of the installation target
    """

    if sys.platform in ('linux4', 'linux3', 'linux2', 'darwin'):
        # installation_dir, relative to this file, is 7 levels up.
        this_file_location = __file__.split(os.path.sep)
        try:
            index_of_lib = this_file_location.index('lib')
        except ValueError:
            index_of_lib = 0
        d = os.path.sep.join(this_file_location[:-index_of_lib - 1])
    elif sys.platform == 'win32':
        # main_dir is the location of the scripts, which is located in the
        # installation_dir:
        d = main_dir()
    else:
        raise NotImplementedError('This platform does not support '
                                  'translations: %s' % sys.platform)
    return os.path.abspath(d)


def user_dir():
    """Returns the path to where user data are saved.

    this is not the same as Application Data, for app_data is going to be
    replaced at each new installation or upgrade of the software. user_data
    is responsibility of the user and the software should use it, not
    overrule it. 

    not implemented yet. will be a configuration item.

    """
    return appdata_dir()

    
def appdata_dir():
    """Returns the path to where Ghini application data and settings are saved.

    """
    if sys.platform == "win32":
        if 'APPDATA' in os.environ:
            d = os.path.join(os.environ["APPDATA"], "Bauble")
        elif 'USERPROFILE' in os.environ:
            d = os.path.join(os.environ['USERPROFILE'], 'Application Data',
                             'Bauble')
        else:
            raise Exception('Could not get path for user settings: no '
                            'APPDATA or USERPROFILE variable')
    elif sys.platform in ('linux4', 'linux3', 'linux2', 'darwin'):
        # using os.expanduser is more reliable than os.environ['HOME']
        # because if the user runs bauble with sudo then it will
        # return the path of the user that used sudo instead of ~root
        try:
            d = os.path.join(os.path.expanduser('~%s' % os.environ['USER']),
                             '.bauble')
        except Exception:
            raise Exception('Could not get path for user settings: '
                            'could not expand $HOME for user %(username)s' %
                            dict(username=os.environ['USER']))
    else:
        raise Exception('Could not get path for user settings: '
                        'unsupported platform')
    return os.path.abspath(d)
