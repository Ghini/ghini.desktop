# try:
#     from ez_setup import use_setuptool
#     use_setuptools()
#     from setuptools import setup
# except ImportError:
try:
    import setuptools
    from setuptools import setup
except ImportError, e:
    print e
    from distutils.core import setup
import os, sys, glob

import sys

USING_PY2EXE = False
if sys.argv[1] == 'py2exe':
    USING_PY2EXE = True

def get_version():
    """
    returns the bauble version combined with the subversion revision number
    """
    from bauble import version_str as version
    return version

version = get_version()
gtk_pkgs = ["pango", "atk", "gobject", "gtk", "cairo", "pango", "pangocairo"]
#plugins = ['garden', 'abcd', 'report', 'report.default', 'plants', 'tag',
#	   'imex']
#plugins_pkgs = ['bauble.plugins.%s' % p for p in plugins]
#subpackages = ['plugins', 'utils']
#all_packages=["bauble"] + ["bauble.%s" % p for p in subpackages] + plugins_pkgs
plugins = setuptools.find_packages(where='bauble/plugins',
				   exclude=['test', 'bauble.*.test'])
plugins_pkgs = ['bauble.plugins.%s' % p for p in plugins]
all_packages = setuptools.find_packages(exclude=['test', 'bauble.*.test'])

package_data = {'': ['README', 'CHANGES', 'LICENSE'],
                'bauble': ['*.ui','*.glade','images/*.png', 'pixmaps/*.png',
                           'images/*.svg', 'images/*.ico']}

data_patterns = ['default/*.txt', '*.ui', '*.glade', '*.xsl', '*.xsd']
for pkg in plugins_pkgs:
    package_data[pkg] = data_patterns

all_package_dirs = {'': '.'}
for p in all_packages:
    all_package_dirs[p] = p.replace('.', '/')

if USING_PY2EXE:
    import py2exe
    # TODO: see if we can use setuptools.find_packages() instead searching for
    # sqlalchemy packages manually
    def get_sqlalchemy_includes():
        includes = []
        from imp import find_module
        file, path, descr = find_module('sqlalchemy')
        for dir, subdir, files in os.walk(path):
            submod = dir[len(path)+1:]
            includes.append('sqlalchemy.%s' % submod)
            if submod in ('mods', 'ext', 'databases'):
                includes.extend(['sqlalchemy.%s.%s' % (submod, s) for s in [f[:-2] for f in files if not f.endswith('pyc') and not f.startswith('__init__.py')]])
        return includes

    # TODO: check again that this is necessary for pysqlite2, we might
    # be able to juse use the python 2.5 built in sqlite3 module
    py2exe_includes = ['pysqlite2.dbapi2', 'simplejson', 'lxml',
                       'MySQLdb', 'psycopg2', 'encodings'] + \
                       gtk_pkgs + plugins_pkgs + \
                       get_sqlalchemy_includes()

    opts = {
        "py2exe": {
            "compressed": 1,
            "optimize": 2,
            "includes": py2exe_includes,
            "dll_excludes": ["iconv.dll", "intl.dll",
                "libatk-1.0-0.dll", "libgdk_pixbuf-2.0-0.dll",
                "libgdk-win32-2.0-0.dll", "libglib-2.0-0.dll",
                "libgmodule-2.0-0.dll", "libgobject-2.0-0.dll",
                "libgthread-2.0-0.dll", "libgtk-win32-2.0-0.dll",
                "libpango-1.0-0.dll", "libpangowin32-1.0-0.dll",
                "libxml2", "libglade-2.0-0", "zlib1"]
        }
    }

    # py2exe doesn't seem to respect packages_data so build data_files from
    # package_data
    py2exe_data_files = []
    for package, patterns in package_data.iteritems():
        pkg_dir = all_package_dirs[package]
        for p in patterns:
            matches = glob.glob(pkg_dir + '/' + p)
            if matches != []:
                index = p.rfind('/')
                if index != -1:
                    install_dir = '%s/%s' % (pkg_dir, p[:index])
                else:
                    install_dir = pkg_dir
                py2exe_data_files.append((install_dir,
                                          [m.replace(os.sep, '/') \
                                               for m in matches]))
else:
    opts = None
    py2exe_data_files = None
    py2exe_includes = []

#print package_data

#print '------- packages --------\n' + str(all_packages)
#print '------- package directories --------\n' + str(all_package_dirs)
#print '------- packages data--------\n' + str(package_data)

# TODO: fix warnings about console, windows, install_requires, dist_dir and
# options arguments

# TODO: external dependencies not in the PyPI: PyGTK>=2.10
setup(name="bauble",
      version=version,
      console=["scripts/bauble"],
      windows = [
        {'script': 'scripts/bauble',
         'icon_resources': [(1, "bauble/images/icon.ico")]}],
      scripts=["scripts/bauble"], # for setuptools?
      options=opts,
      dist_dir='dist/bauble-%s' % version, # distribution directory
      packages = all_packages,
      package_dir = all_package_dirs,
      package_data = package_data,
      data_files = py2exe_data_files,
      install_requires=["SQLAlchemy>=0.4.3", "pysqlite>=2.3.2",
                        "simplejson>=1.7.1", "lxml>=2.0.1"],
#      extras_requires=["mysql-python and psycopg"

      # metadata
      #test_suite="test.test", #TODO:running "setup.py test" hasn't been tested
      author="Brett",
      author_email="brett@belizebotanic.org",
      description="""\
      Bauble is a biodiversity collection manager software application""",
      license="GPL",
      keywords="database biodiversity botanic collection",
      url="http://bauble.belizebotanic.org",
#      download_url="http://bauble.belizebotanic.org/#download"
     )

from distutils.util import execute
def install_linux():
    """
    install the menu and icons entries on Linux system that complies
    with the freedesktop.org specs
    """
    os.system('xdg-desktop-menu install --novendor bauble.desktop')
    os.system('xdg-desktop-icon install --novendor bauble/images/bauble.xpm')
    icon_sizes = [16, 22, 32, 48, 64]#, 128]
    for size in icon_sizes:
        os.system('xdg-icon-resource install --novendor --size %s bauble/images/bauble-%s.png bauble' % (size, size))

if sys.platform == 'linux2':
    execute(install_linux, [], msg='installing menu entry and icon')
