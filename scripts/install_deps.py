#
# Description: Download all other Bauble dependencies that aren't GTK/pygtk
# related
#
# Author: brett@belizebotanic.org
#
# License: GPL
#

# TODO:
# - let the user choose a mirror
# - *-dev versions of files?
# - check MD5
# - do an import MYSQL-python and check the version to see if we need to
# install the .exe files

import sys

if sys.platform != 'win32':
    print("Error: This script is only for Win32")
    sys.exit(1)

import os
import urllib.request, urllib.parse, urllib.error
import zipfile
import winreg
from optparse import OptionParser
parser = OptionParser()
parser.add_option('-r', '--redl', action='store_true', dest='redl',
                  default=False, help="redownload existing files")
#parser.add_option('-g', '--gtk-only', action='store_true', dest='gtk_only',
#                 default=False, help='only download the GTK+ files, not PyGTK')
#parser.add_option('-i', '--install_path', dest="install_path", metavar="DIR",
#                  help="directory to install GTK+, default is c:\GTK")
parser.add_option('-e', '--noeggs', action='store_true', dest='noeggs',
                  default=False, help="don't use easy_install")
parser.add_option('-d', '--download_path', dest="download_path", metavar="DIR",
                  help="directory to download files, default is .\install_deps")
(options, args) = parser.parse_args()


supported_python_version = '2.5'

# ALL_FILES = [
#     'http://oss.itsystementwicklung.de/download/pysqlite/2.5/2.5.1/pysqlite-2.5.1.win32-py2.6.exe',
#     'http://www.stickpeople.com/projects/python/win-psycopg/psycopg2-2.0.8.win32-py2.6-pg8.3.4-release.exe']
ALL_FILES = [
    'http://oss.itsystementwicklung.de/download/pysqlite/2.5/2.5.1/pysqlite-2.5.1.win32-py2.5.exe',
    'http://www.stickpeople.com/projects/python/win-psycopg/psycopg2-2.0.8.win32-py2.5-pg8.3.4-release.exe',
    'http://ufpr.dl.sourceforge.net/sourceforge/gnuwin32/gettext-0.14.4.exe']

EZ_SETUP_PATH = 'http://peak.telecommunity.com/dist/ez_setup.py'


# TODO: what about fop? its too big, maybe we should ask the user
#
# TODO: check for easy_install, if not installed then download and install
# ez_setup.py

eggs_install = {'lxml': '==2.1.5',
                'SQLAlchemy': '>=0.6',
                'py2exe': '==0.6.9',
                'gdata': '',
                'mako': ''
                'fibra: ==0.0.17',
                'pyparsing': '>=1.5'}



def get_subkey_names(reg_key):
    index = 0
    L = []
    while True:
        try:
            name = winreg.EnumKey(reg_key, index)
        except EnvironmentError:
            break
        index += 1
        L.append(name)
    return L


def get_python_versions():
    """
    Return a list with info about installed versions of Python.

    Each version in the list is represented as a tuple with 3 items:

    0   A long integer giving when the key for this version was last
          modified as 100's of nanoseconds since Jan 1, 1600.
    1   A string with major and minor version number e.g '2.4'.
    2   A string of the absolute path to the installation directory.
    """
    python_path = r'software\python\pythoncore'
    versions = {}
    for reg_hive in (winreg.HKEY_LOCAL_MACHINE,
                      winreg.HKEY_CURRENT_USER):
        try:
            python_key = winreg.OpenKey(reg_hive, python_path)
        except EnvironmentError:
            continue
        for version_name in get_subkey_names(python_key):
            key = winreg.OpenKey(python_key, version_name)
            modification_date = winreg.QueryInfoKey(key)[2]
            try:
                install_path = winreg.QueryValue(key, 'installpath')
                versions[version_name] = install_path
            except:
                pass
    return versions

PYTHON_HOME = None
PYTHON_EXE = None

# detect python version and download pygtk installers

python_versions = get_python_versions()
available_versions = {}
#print python_versions
if len(list(python_versions.keys())) == 0:
    print("Error: Install Python first")
    sys.exit(1)

try:
    PYTHON_HOME = python_versions[supported_python_version]
    PYTHON_EXE = os.path.join(PYTHON_HOME, 'python.exe')
    if os.path.exists(PYTHON_EXE):
        print(('Using Python %s' % supported_python_version))
        #print 'Python %s seems to be installed correctly' % version
    else:
        print(('Python %s NOT installed correctly' % version))
        sys.exit(1)

except KeyError:
    print(('This script only supports Python %s' % supported_python_version))
    sys.exit(1)


if options.download_path:
    DL_PATH = options.download_path
else:
    DL_PATH = os.path.join(os.getcwd(), 'install_deps')

print(('using download path: %s' % DL_PATH))
if not os.path.exists(DL_PATH):
    os.makedirs(DL_PATH)

# download all the files
#for url in ['%s/%s' % (SERVER_ROOT, FILE) for FILE in ALL_FILES]:
for url in ALL_FILES:
    filename = url.split('/')[-1]
    dest_file = os.path.join(DL_PATH, filename)
    if os.path.exists(dest_file) and not options.redl:
        continue
    print(('downloading %s...' % filename))
    try:
        urllib.request.urlretrieve(url, os.path.join(DL_PATH, filename))
    except Exception as e:
        print(e)
        print(('ERROR: Could not download %s' % url))
        sys.exit(1)


# for all the files that we downloaded (or would have downloaded) then
# either unzip or execute them
for filename in [f.split('/')[-1] for f in ALL_FILES]:
    fullname = '"%s"' % os.path.join(DL_PATH, filename)
    os.system(fullname)


# TODO: should we be calling easy_install -Z since py2exe seems to
# have problems with zipped up eggs

if not options.noeggs:
    # make sure that setuptools is installed
    EASY_INSTALL_EXE = os.path.join(PYTHON_HOME, 'scripts','easy_install.exe')
    if not os.path.exists(EASY_INSTALL_EXE):
        EZ_SETUP_DL_PATH = os.path.join(DL_PATH, 'ez_setup.py')
        if not os.path.exists(EZ_SETUP_DL_PATH):
            urllib.request.urlretrieve(EZ_SETUP_PATH, EZ_SETUP_DL_PATH)
        cmd = '%s "%s"' % (PYTHON_EXE, EZ_SETUP_DL_PATH)
        #print cmd
        os.system(cmd)

    # install the eggs
    for egg, version in list(eggs_install.items()):
        #cmd = '%s -Z "%s%s"' % (EASY_INSTALL_EXE, egg, version)
        cmd = '%s -Z -U "%s%s"' % (EASY_INSTALL_EXE, egg, version)
        os.system(cmd)

print('done.')
