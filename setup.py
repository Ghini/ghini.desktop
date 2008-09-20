try:
    import setuptools
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
import setuptools

import os
import sys
import glob
import distutils.core
from distutils.command.build import build as _build
from distutils.command.install import install as _install
import distutils.util as util
import distutils.spawn as spawn
import distutils.dep_util as dep_util
import distutils.dir_util as dir_util

from bauble import version_str
version = version_str

# TODO: external dependencies not in the PyPI: PyGTK>=2.10

# relative path for locale files
locale_path = os.path.join('share', 'locale')

gtk_pkgs = ["pango", "atk", "gobject", "gtk", "cairo", "pango", "pangocairo"]
plugins = setuptools.find_packages(where='bauble/plugins',
				   exclude=['test', 'bauble.*.test'])
plugins_pkgs = ['bauble.plugins.%s' % p for p in plugins]
all_packages = setuptools.find_packages(exclude=['test', 'bauble.*.test'])

package_data = {'': ['README', 'CHANGES', 'LICENSE'],
                'bauble': ['*.ui','*.glade','images/*.png', 'pixmaps/*.png',
                           'images/*.svg', 'images/*.ico']}

# ceate a list of the data patterns to look for in the packages
data_patterns = ['default/*.txt', '*.ui', '*.glade', '*.xsl', '*.xsd']
for pkg in plugins_pkgs:
    package_data[pkg] = data_patterns

all_package_dirs = {'': '.'}
for p in all_packages:
    all_package_dirs[p] = p.replace('.', '/')

# setup py2exe and nsis installer
if sys.platform == 'win32' and sys.argv[1] in ('nsis', 'py2exe'):
    import py2exe
    from distutils.command.py2exe import py2exe as _py2exe_cmd
    # setuptools.find packages doesn't dig deep enough so we search
    # for a list of all packages in the sqlalchemy namespace
    sqlalchemy_includes = []
    from imp import find_module
    file, path, descr = find_module('sqlalchemy')
    for dir, subdir, files in os.walk(path):
        submod = dir[len(path)+1:]
        sqlalchemy_includes.append('sqlalchemy.%s' % submod)
        if submod in ('mods', 'ext', 'databases'):
            sqlalchemy_includes.extend(['sqlalchemy.%s.%s' % (submod, s) for s in [f[:-2] for f in files if not f.endswith('pyc') and not f.startswith('__init__.py')]])

    # TODO: check again that this is necessary for pysqlite2, we might
    # be able to juse use the python 2.5 built in sqlite3 module
    py2exe_includes = ['pysqlite2.dbapi2', 'simplejson', 'lxml',
                       'MySQLdb', 'psycopg2', 'encodings'] + \
                       gtk_pkgs + plugins_pkgs + sqlalchemy_includes
    py2exe_setup_args = {'console': ["scripts/bauble"],
                         'windows': [{'script': 'scripts/bauble',
                                      'icon_resources': [(1, "bauble/images/icon.ico")]}]}
    py2exe_options = {
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

    class py2exe_cmd(_py2exe_cmd):
        def run(self):
            # TODO: make sure we have everything installed that we need to
            # bundle e.g. mysql-python, psycopg2, others...
            #self.dist_dir = os.path.join('dist', 'py2exe')
            _py2exe_cmd.run(self)
            # install locale files
            locales = os.path.dirname(locale_path)
            build_base = self.get_finalized_command('build').build_base
            #print build_base
            src = os.path.join(build_base, locales)
            dir_util.copy_tree(src, os.path.join(self.dist_dir, locales))

    class nsis_cmd(distutils.core.Command):
        user_options = []
        def initialize_options(self):
            pass
        def finalize_options(self):
            pass
        def run(self):
            print "**Error: Can't run this command."
            print sys.exit(1)
            # run py2exe

else:
    py2exe_options = {}
    py2exe_setup_args = {}
    py2exe_data_files = None
    py2exe_includes = []
    class _empty_cmd(distutils.core.Command):
        user_options = []
        def initialize_options(self):
            pass
        def finalize_options(self):
            pass
        def run(self):
            print "**Error: Can't run this command."
            print sys.exit(1)
    class py2exe_cmd(_empty_cmd):
        pass
    class nsis_cmd(_empty_cmd):
        pass


# build command
class build(_build):
    def run(self):
        if not spawn.find_executable('msgfmt'):
            msg = '** Error: Building Bauble requires the gettext utilities ' \
                  'be installed.'
            print msg
            sys.exit(1)

        _build.run(self)
        dest_tmpl = os.path.join(self.build_base, locale_path, '%s',
                                 'LC_MESSAGES')
        matches = glob.glob('po/*.po')
        for po in matches:
            # create an .mo in build/share/locale/$LANG/LC_MESSAGES
            loc, ext = os.path.splitext(os.path.basename(po))
            localedir = dest_tmpl % loc
            mo = '%s/bauble.mo' % localedir
            if not os.path.exists(localedir):
                os.makedirs(localedir)
            if not os.path.exists(mo) or dep_util.newer(po, mo):
                spawn.spawn(['msgfmt', po, '-o', mo])


# install command
class install(_install):
    def run(self):
        if sys.platform not in ('linux2', 'win32'):
            msg = "**Error: Can't install on this platform: %s" % sys.platform
            print msg
            sys.exit(1)

        _install.run(self)
        if sys.platform == 'linux2':
            # install standard desktop files
            spawn.spawn(['xdg-desktop-menu', 'install', '--novendor',
                        'bauble.desktop'])
            icon_sizes = [16, 22, 32, 48, 64]#, 128]
            for size in icon_sizes:
                img = 'bauble/images/bauble-%s.png' % size
                spawn.spawn(['xdg-icon-resource', 'install', '--novendor',
                            '--size', str(size),  img,  'bauble'])
        elif sys.platform == 'win32':
            pass
        # install locale files
        locales = os.path.dirname(locale_path)
        src = os.path.join(self.build_base, locales)
        dir_util.copy_tree(src, os.path.join(self.prefix, locales))


# require pysqlite if not using python2.5
needs_sqlite = []
try:
    import sqlite3
except ImportError:
    needs_sqlite = "pysqlite>=2.3.2"


setuptools.setup(name="bauble",
                 cmdclass={'build': build, 'install': install,
                           'py2exe': py2exe_cmd, 'nsis': nsis_cmd},
                 version=version,
                 scripts=["scripts/bauble"], # for setuptools?
                 packages = all_packages,
                 package_dir = all_package_dirs,
                 package_data = package_data,
                 data_files = py2exe_data_files,
                 install_requires=["SQLAlchemy>=0.4.4,<0.5",
                                   "simplejson>=1.7.1",
                                   "lxml>=2.0"] + needs_sqlite,
                 #TODO:running "setup.py test" hasn't been tested
                 test_suite="test.test",
                 author="Brett",
                 author_email="brett@belizebotanic.org",
                 description="Bauble is a biodiversity collection manager " \
                 "software application",
                 license="GPL",
                 keywords="database biodiversity botanic collection",
                 url="http://bauble.belizebotanic.org",
                 options=py2exe_options,
                 **py2exe_setup_args
     )
