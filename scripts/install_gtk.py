
#
# Description: Download all the required files need for GTK+/pygtk development
# and create a working environment to use them
#
# Author: brett@belizebotanic.org
#
# License: GPL
#

# TODO:
# - let the user choose a mirror
# - *-dev versions of files?
# - check MD5
#

import sys, traceback

if sys.platform != 'win32':
    print "Error: This script is only for Win32"
    sys.exit(1)

import os
import urllib
import zipfile
import _winreg
import shutil

from optparse import OptionParser
parser = OptionParser()
parser.add_option('-r', '--redl', action='store_true', dest='redl',
                  default=False, help="redownload existing files")
parser.add_option('-g', '--gtk-only', action='store_true', dest='gtk_only',
                 default=False, help='only download the GTK+ files, not PyGTK')
parser.add_option('-i', '--install_path', dest="install_path", metavar="DIR",
                  help="directory to install GTK+, default is c:\GTK")
parser.add_option('-d', '--download_path', dest="download_path", metavar="DIR",
                  help="directory to download files, default is .\install_gtk")
parser.add_option('-v', '--verbose', dest='verbose', action='store_true',
                  default=False)
(options, args) = parser.parse_args()


supported_python_version = '2.5'

if options.install_path:
    GTK_INSTALL_PATH = options.install_path
else:
    GTK_INSTALL_PATH = 'c:\\GTK'

# TODO: as far as I know there's no other way to get the list of most
# current files without listing them explicitly here which may be
# better since we might include an incompatible release, maybe another
# script could at least fest me the version numbers so i can quickly
# check if any of the files need to be updated

# main gtk/pygtk files
SERVER_ROOT = 'http://ftp.gnome.org/pub/gnome/binaries/win32'
GTK_PATH = 'gtk+/2.14/gtk+_2.14.7-1_win32.zip'
GLIB_PATH = 'glib/2.18/glib_2.18.4-1_win32.zip'
PANGO_PATH = 'pango/1.22/pango_1.22.4-1_win32.zip'
ATK_PATH = 'atk/1.24/atk_1.24.0-1_win32.zip'

# PYCAIRO_PATH = 'pycairo/1.4/pycairo-1.4.12-2.win32-py2.6.exe'
# PYGOBJECT_PATH = 'pygobject/2.14/pygobject-2.14.2-2.win32-py2.6.exe'
# PYGTK_PATH = 'pygtk/2.12/pygtk-2.12.1-3.win32-py2.6.exe'
PYCAIRO_PATH = 'pycairo/1.4/pycairo-1.4.12-1.win32-py2.5.exe'
PYGOBJECT_PATH = 'pygobject/2.14/pygobject-2.14.1-1.win32-py2.5.exe'
PYGTK_PATH = 'pygtk/2.12/pygtk-2.12.1-2.win32-py2.5.exe'

CROCO_PATH = 'libcroco/0.6/libcroco-0.6.1.zip'
GSF_PATH = 'libgsf/1.14/libgsf-1.14.8.zip'
RSVG_PATH = 'librsvg/2.22/librsvg_2.22.3-1_win32.zip'
SVG_PIXBUF_PATH = 'librsvg/2.22/svg-gdk-pixbuf-loader_2.22.3-1_win32.zip'
SVG_GTK_ENGINE = 'librsvg/2.22/svg-gtk-engine_2.22.3-1_win32.zip'

#PYTHON_24_FILES = PYCAIRO_24_PATH, PYGOBJECT_24_PATH, PYGTK_24_PATH
#PYTHON_25_FILES = PYCAIRO_25_PATH, PYGOBJECT_25_PATH, PYGTK_25_PATH

# dependencies
CAIRO_PATH = 'dependencies/cairo_1.8.6-1_win32.zip'
EXPAT_PATH = 'dependencies/expat-2.0.0.zip'
FONTCONFIG_PATH = 'dependencies/fontconfig-2.4.2-tml-20071015.zip'
FREETYPE_PATH = 'dependencies/freetype_2.3.8-1_win32.zip'
GETTEXT_PATH = 'dependencies/gettext-runtime-0.17-1.zip'
BZIP_PATH = 'dependencies/libbzip2-1.0.2.zip'
ICONV_PATH = 'dependencies/libiconv-1.9.1.bin.woe32.zip' # should i be getting the woe32 or the other one?
JPEG_PATH = 'dependencies/libjpeg-6b-4.zip'
PNG_PATH = 'dependencies/libpng_1.2.34-1_win32.zip'
TIFF_PATH = 'dependencies/libtiff-3.8.2.zip'
XML_PATH = 'dependencies/libxml2-2.6.27.zip'
ZLIB_PATH = 'dependencies/zlib-1.2.3.zip'

ALL_FILES = [PYCAIRO_PATH, PYGOBJECT_PATH, PYGTK_PATH,
             GTK_PATH, GLIB_PATH, PANGO_PATH, ATK_PATH, ZLIB_PATH, BZIP_PATH,
             ICONV_PATH, GETTEXT_PATH, PNG_PATH, JPEG_PATH, TIFF_PATH,
             CAIRO_PATH, RSVG_PATH, SVG_PIXBUF_PATH, SVG_GTK_ENGINE,
             XML_PATH, CROCO_PATH, GSF_PATH, FONTCONFIG_PATH,
             EXPAT_PATH, FREETYPE_PATH]


def get_subkey_names(reg_key):
    """
    @param reg_key: a RegKey object
    Get the names of the subkeys under reg_key
    """
    index = 0
    L = []
    while True:
        try:
            name = _winreg.EnumKey(reg_key, index)
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
    for reg_hive in (_winreg.HKEY_LOCAL_MACHINE,
                      _winreg.HKEY_CURRENT_USER):
        try:
            python_key = _winreg.OpenKey(reg_hive, python_path)
        except EnvironmentError:
            continue
        for version_name in get_subkey_names(python_key):
            key = _winreg.OpenKey(python_key, version_name)
            modification_date = _winreg.QueryInfoKey(key)[2]
            try:
                install_path = _winreg.QueryValue(key, 'installpath')
                versions[version_name] = install_path
            except Exception:
                pass
    return versions

# detect python version and download pygtk installers
if not options.gtk_only:
    python_versions = get_python_versions()
    available_versions = {}
if len(python_versions.keys()) == 0:
    print "Error: Install Python first"
    sys.exit(1)

try:
    PYTHON_HOME = python_versions[supported_python_version]
    PYTHON_EXE = os.path.join(PYTHON_HOME, 'python.exe')
    if os.path.exists(PYTHON_EXE):
        print 'Using Python %s' % supported_python_version
        #print 'Python %s seems to be installed correctly' % version
    else:
        print 'Python %s NOT installed correctly' % version
        sys.exit(1)

except KeyError:
    print 'This script only supports Python %s' % supported_python_version
    sys.exit(1)

if options.download_path:
    DL_PATH = options.download_path
else:
    DL_PATH = os.path.join(os.getcwd(), 'install_gtk')

print 'using download path: %s' % DL_PATH
if not os.path.exists(DL_PATH):
    os.makedirs(DL_PATH)

# download all the files
for url in ['%s/%s' % (SERVER_ROOT, FILE) for FILE in ALL_FILES]:
    filename = url.split('/')[-1]
    dest_file = os.path.join(DL_PATH, filename)
    if os.path.exists(dest_file) and not options.redl:
        continue
    print 'downloading %s...' % filename
    #filename, headers = urllib.urlretrieve(url, os.path.join(DL_PATH, filename))
    tmp, headers = urllib.urlretrieve(url)
    if headers.type != 'text/html': # usually an error message
        shutil.move(tmp, os.path.join(DL_PATH, filename))
    else:
        print 'could not retrieve %s' % url
        sys.exit(1)


# 1. for all downloaded files except for the python files we need to unzip them
# into the GTK+ installation directory
# 2. install the pygtk files
# 3. add GTK+ to whatever paths and registry entries it expects
#

if os.path.exists(GTK_INSTALL_PATH):
    msg = '%s already exists. Are you sure you want to install GTK+ '\
          'here? (y/n) ' % GTK_INSTALL_PATH
    response = ''
    while response is '' or response not in 'yYnN':
        response = raw_input(msg).strip()
    if response in 'nN':
        sys.exit(1)
else:
    os.makedirs(GTK_INSTALL_PATH)


# for all the files that we downloaded (or would have downloaded) then
# either unzip or execute them
for filename in [f.split('/')[-1] for f in ALL_FILES]:
    #print filename
    if filename.endswith('.zip'):
        try:
            zip = zipfile.ZipFile(os.path.join(DL_PATH, filename), 'r')
        except Exception:
            print traceback.format_exc()
            print 'Error: bad zip file -- %s' % os.path.join(DL_PATH, filename)
            sys.exit(1)
        for zf in zip.namelist():
            if zf.endswith('/'):
                # for some reason sometimes there's a compressed
                # directory that doesn't refer to a file...???
                continue
            zf_path = '\\'.join(zf.split('/')[:-1])
            extract_path = os.path.join(GTK_INSTALL_PATH, zf_path)
            if not os.path.exists(extract_path):
                os.makedirs(extract_path)
            dest_filename = os.path.join(GTK_INSTALL_PATH,zf.replace('/','\\'))
            try:
                dest_file = open(dest_filename, 'wb')
            except Exception, e:
                print e
                raise
            if options.verbose:
                print 'unzipping %s to %s' % (filename, GTK_INSTALL_PATH)
            data = zip.read(zf)
            dest_file.write(data)
            dest_file.close()
        zip.close()
    elif filename.endswith('.exe'):
        fullname = '"%s"' % os.path.join(DL_PATH, filename)
        if options.verbose:
            print 'running installer %s' % fullname
        os.system(fullname)

# at some point the svg pixbuf loader started linking against libpng13.dll
# so we just copy our libpng12-0.dll to libpng13.dll
PNG_13_PATH = os.path.join(GTK_INSTALL_PATH, 'bin', 'libpng13.dll')
if not os.path.exists(PNG_13_PATH):
    shutil.copyfile(os.path.join(GTK_INSTALL_PATH, 'bin', 'libpng12-0.dll'), PNG_13_PATH)

# register the pixbuf loaders
load_pixbufs_cmd = '%s\\bin\\gdk-pixbuf-query-loaders.exe > %s\\etc\\gtk-2.0\\gdk-pixbuf.loaders' % (GTK_INSTALL_PATH, GTK_INSTALL_PATH)
if options.verbose:
    print load_pixbufs_cmd
print load_pixbufs_cmd
os.system(load_pixbufs_cmd)

print 'done.'
