# try:
#     from ez_setup import use_setuptool
#     use_setuptools()
#     from setuptools import setup
# except ImportError:
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


gtk_pkgs = [ "pango", "atk", "gobject", "gtk", "cairo", "pango", "pangocairo"]

plugins = ['garden', 'abcd', 'report', 'report.default', 'plants', 'tag',
	   'imex']
plugins_pkgs = ['bauble.plugins.%s' % p for p in plugins]
subpackages = ['plugins', 'utils']
all_packages=["bauble"] + ["bauble.%s" % p for p in subpackages] + plugins_pkgs

package_data = {'': ['README', 'CHANGES', 'LICENSE'],
                'bauble': ['*.ui','*.glade','images/*.png', 'pixmaps/*.png',
                           'images/*.svg', 'images/*.ico']}

data_patterns = ['default/*.txt', '*.ui', '*.glade', '*.xsl']
for pkg in plugins_pkgs:
    package_data[pkg] = data_patterns

all_package_dirs = {'': '.'}
for p in all_packages:
    all_package_dirs[p] = p.replace('.', '/')


if USING_PY2EXE:
    import py2exe
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
        dir = all_package_dirs[package]
        for p in patterns:
            matches = glob.glob(dir + '/' + p)
            if matches != []:
                index = p.rfind('/')
                if index != -1:
                    install_dir = '%s/%s' % (dir, p[:index])
                else:
                    install_dir = dir
                py2exe_data_files.append((install_dir,
                                          [m.replace(os.sep, '/') \
                                               for m in matches]))
else:
    opts=None
    py2exe_data_files = None
    py2exe_includes = []

print package_data

#print '------- packages --------\n' + str(all_packages)
#print '------- package directories --------\n' + str(all_package_dirs)
#print '------- packages data--------\n' + str(package_data)

# TODO: fix warnings about console, windows, install_requires, dist_dir and
# options arguments

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
      install_requires=["SQLAlchemy>=0.4.2p3", "pysqlite==2.3.2",
                        "PyGTK>=2.10", "simplejson==1.7.1", "lxml"],# pygtk is not supported using distutils
#      extras_requires=["mysql-python and psycopg"

      # metadata
      test_suite="test.test", #TODO: running "setup.py test" hasn't been tested
      author="Brett",
      author_email="brett@belizebotanic.org",
      description="""\
      Bauble is a biodiversity collection manager software application""",
      license="GPL",
      keywords="database biodiversity botanic collection",
      url="http://bauble.belizebotanic.org",
#      download_url="http://bauble.belizebotanic.org/#download"
     )
