#!/usr/bin/env python
#
#  Copyright (c) 2005,2006,2007,2008  Brett Adams <brett@belizebotanic.org>
#  This is free software, see GNU General Public License v2 for details.
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
import distutils.util as util
import distutils.spawn as spawn
import distutils.dep_util as dep_util
import distutils.dir_util as dir_util
import distutils.file_util as file_util
from setuptools import Command
from setuptools.command.install import install as _install
from setuptools.command.sdist import sdist as _sdist
from bauble import version

# TODO: external dependencies not in the PyPI: PyGTK>=2.14

# TODO: fix permissions on files when creating an sdist with:
# find . -regex '.*?\.\(glade\|xsl\|txt\|svg\|ui\)'  -exec chmod 644 {} \;

# TODO: run the clean before creating an sdist, or at least the
# manifest should not include those files that would be cleaned

# relative path for locale files
locale_path = os.path.join('share', 'locale')

gtk_pkgs = ["pango", "atk", "gobject", "gtk", "cairo", "pango", "pangocairo"]
plugins = setuptools.find_packages(where='bauble/plugins',
				   exclude=['test', 'bauble.*.test'])
plugins_pkgs = ['bauble.plugins.%s' % p for p in plugins]
all_packages = setuptools.find_packages(exclude=['test', 'bauble.*.test'])

package_data = {'': ['README', 'CHANGES', 'LICENSE'],
                'bauble': ['*.ui','*.glade','images/*.png', 'pixmaps/*.png',
                           'images/*.svg', 'images/*.gif', 'images/*.ico']}

# ceate a list of the data patterns to look for in the packages
data_patterns = ['default/*.txt', '*.ui', '*.glade', '*.xsl', '*.xsd']
for pkg in plugins_pkgs:
    package_data[pkg] = data_patterns

all_package_dirs = {'': '.'}
for p in all_packages:
    all_package_dirs[p] = p.replace('.', '/')

data_files = []

# setup py2exe and nsis installer
if sys.platform == 'win32' and sys.argv[1] in ('nsis', 'py2exe'):
    import py2exe
    from distutils.command.py2exe import py2exe as _py2exe_cmd
    # setuptools.find packages doesn't dig deep enough so we search
    # for a list of all packages in the sqlalchemy namespace

    # TODO: although this works its kind of crappy, find_packages
    # should really be enough and maybe the problem lies elsewhere

    sqlalchemy_includes = []
    from imp import find_module
    f, path, descr = find_module('sqlalchemy')
    for parent, subdir, files in os.walk(path):
        submod = parent[len(path)+1:]
        sqlalchemy_includes.append('sqlalchemy.%s' % submod)
        if submod in ('mods', 'ext', 'databases'):
            sqlalchemy_includes.extend(['sqlalchemy.%s.%s' % (submod, s) for s in [f[:-2] for f in files if not f.endswith('pyc') and not f.startswith('__init__.py')]])

    # TODO: check again that this is necessary for pysqlite2, we might
    # be able to juse use the python 2.5 built in sqlite3 module
    py2exe_includes = ['pysqlite2.dbapi2', 'lxml',
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
                data_files.append((install_dir,
                                   [m.replace(os.sep, '/') for m in matches]))

    class py2exe_cmd(_py2exe_cmd):
        def run(self):
            # TODO: make sure we have everything installed that we need to
            # bundle e.g. mysql-python, psycopg2, others...
            _py2exe_cmd.run(self)
            # install locale files
            locales = os.path.dirname(locale_path)
            build_base = self.get_finalized_command('build').build_base
            #print build_base
            src = os.path.join(build_base, locales)
            dir_util.copy_tree(src, os.path.join(self.dist_dir, locales))

            # copy GTK to the dist directory
            # TODO: create a flag to control whether or not to copy
            gtk_root = 'c:\\gtk'
            #if os.path.exists(gtk_root):
            dist_gtk = os.path.join(self.dist_dir, 'gtk')
            if not os.path.exists(dist_gtk):
                dir_util.copy_tree(gtk_root, dist_gtk)

            # register the pixbuf loaders
            exe = '%s\\bin\\gdk-pixbuf-query-loaders.exe' % dist_gtk
            dest = '%s\\etc\\gtk-2.0\\gdk-pixbuf.loaders' % dist_gtk
            cmd = 'call "%s" > "%s"' % (exe, dest)
            print cmd
            os.system(cmd)

    class nsis_cmd(Command):
        # 1. copy the gtk dist to the dist directory
        # 2. run the script to update the pixbuf paths
        # 3. tun the nsis command to create the installer
        # 4. try to do everything silent if possible instead of using
        # the NSIS compiler GUI
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
    py2exe_includes = []
    class _empty_cmd(Command):
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
        if sys.platform == 'win32':
            # try to guess the path of the gettext utilities
            os.environ['PATH'] = os.environ['PATH'] + \
                ';c:\\Program Files\\GnuWin32\\bin'
        if not spawn.find_executable('msgfmt'):
            msg = '** Error: Building Bauble requires the gettext utilities ' \
                  'be installed.  If they are installed please ensure that ' \
                  'the msgfmt command is in your PATH'
            print msg
            sys.exit(1)

        _build.run(self)

        # create build/share directory
        dir_util.mkpath(os.path.join(self.build_base, 'share'))

        dest_tmpl = os.path.join(self.build_base, locale_path, '%s',
                                 'LC_MESSAGES')
        matches = glob.glob('po/*.po')
        for po in matches:
            # create an .mo in build/share/locale/$LANG/LC_MESSAGES
            loc, ext = os.path.splitext(os.path.basename(po))
            localedir = dest_tmpl % loc
            mo = '%s/bauble.mo' % localedir
            if not os.path.exists(localedir):
                dir_util.mkpath(localedir)
            if not os.path.exists(mo) or dep_util.newer(po, mo):
                spawn.spawn(['msgfmt', po, '-o', mo])

        # copy .desktop and icons
        if sys.platform == 'linux2':
            app_dir = os.path.join(self.build_base, 'share/applications')
            dir_util.mkpath(app_dir)
            file_util.copy_file('data/bauble.desktop', app_dir)

            icon_sizes = [16, 22, 24, 32, 48, 64]#, 128]
            icon_root = os.path.join(self.build_base, 'share/icons/hicolor')

            # copy scalable icon
            scalable_dir = os.path.join(icon_root, 'scalable/apps')
            dir_util.mkpath(scalable_dir)
            file_util.copy_file('data/bauble.svg', scalable_dir)

            pixmaps_dir = os.path.join(self.build_base, 'share/pixmaps')
            dir_util.mkpath(pixmaps_dir)
            file_util.copy_file('data/bauble.svg', pixmaps_dir)

            # copy .png icons
            dimension = lambda s: '%sx%s' % (s, s)
            for size in icon_sizes:
                img = 'data/bauble-%s.png' % size
                dest = os.path.join(icon_root, '%s/apps/bauble.png'
                                    % dimension(size))
                dir_util.mkpath(os.path.split(dest)[0])
                file_util.copy_file(img, dest)



# install command
class install(_install):

    def has_i18n(self):
        return True

    def initialize_options(self):
        _install.initialize_options(self)
        self.skip_xdg = False

    def finalize_options(self):
        _install.finalize_options(self)

    def run(self):
        if sys.platform not in ('linux2', 'win32'):
            msg = "**Error: Can't install on this platform: %s" % sys.platform
            print msg
            sys.exit(1)

        if not self.single_version_externally_managed:
            self.do_egg_install()
        else:
            _install.run(self)


        # check if someone else is copying the files to the destination
        #if self.single_version_externally_managed:# and not self.root:
        #    return

        # install bauble.desktop and icons
        if sys.platform == 'linux2':
            # install everything in share
            dir_util.copy_tree(os.path.join(self.build_base, 'share'),
                                os.path.join(self.install_data, 'share'))
        elif sys.platform == 'win32':
            # install only i18n files
            locales = os.path.dirname(locale_path)
            install_cmd = self.get_finalized_command('install')
            build_base = install_cmd.build_base
            src = os.path.join(build_base, locales)
            dir_util.copy_tree(src, os.path.join(self.install_data, locales))



# docs command
DOC_BUILD_PATH = 'doc/.build/'
class docs(Command):
    user_options = [('all', None, 'rebuild all the docs')]
    def initialize_options(self):
        self.all = False
    def finalize_options(self):
        pass
    def run(self):
        try:
            import sphinx
        except ImportError:
            print 'Building the docs requires the '\
                  'Sphinx(http://sphinx.pocoo.org) package'
            return
        if not os.path.exists(DOC_BUILD_PATH):
            dir_utils.mkpath(DOC_BUILD_PATH)
        cmd = ['sphinx-build', '-E', '-b', 'html', 'doc', DOC_BUILD_PATH]
        if self.all:
            # rebuild all the docs
            cmd.insert(1, '-a')
        spawn.spawn(cmd)


# clean command
class clean(Command):
    user_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        patterns = ['MANIFEST', '*~', '*flymake*', '*.pyc']
        cwd = os.getcwd()
        import fnmatch
        for path, subdirs, files in os.walk(cwd):
            for pattern in patterns:
                matches = fnmatch.filter(files, pattern)
                if matches:
                    def delete(p):
                        print 'removing %s' % p
                        os.remove(p)
                    map(delete ,[os.path.join(path, m) for m in matches])
        if os.path.exists('dist'):
            dir_util.remove_tree('dist')
        if os.path.exists('build'):
            dir_util.remove_tree('build')
        if os.path.exists(DOC_BUILD_PATH):
            dir_util.remove_tree(DOC_BUILD_PATH)
        # .egg info
        egg_info_dir = 'bauble.egg-info'
        if os.path.exists(egg_info_dir):
            dir_util.remove_tree(egg_info_dir)

        # deb_dist - used by stdeb
        deb_dist = 'deb_dist'
        if os.path.exists(deb_dist):
            dir_util.remove_tree(deb_dist)

# TODO: sdist_deb should really create the tarball from a checkout
# directly from the repository instead of the current working
# directory so that we don't pick up any estranged files that don't
# belong in the tarball

# sdist_deb command
class sdist_deb(_sdist):
    user_options = []
#     def initialize_options(self):
#         pass
    def finalize_options(self):
        _sdist.finalize_options(self)
        self.formats = ['gztar']

    def run(self):
        _sdist.run(self)
        cfg = os.path.abspath('stdeb.cfg')
        cmd = ['py2dsc', '--extra-cfg-file', cfg, #'--no-pycentral',
               '--dist-dir', 'dist/deb_dist',
               '--ignore-install-requires', self.archive_files[0]]
        spawn.spawn(cmd)

# require pysqlite if not using python2.5 or greater
needs_sqlite = []
try:
    import sqlite3
except ImportError:
    needs_sqlite = "pysqlite>=2.3.2"

# TODO: images in bauble/images should really be in data and copied as
# package_data or data_files

setuptools.setup(name="bauble",
                 cmdclass={'build': build, 'install': install,
                           'py2exe': py2exe_cmd, 'nsis': nsis_cmd,
                           'docs': docs, 'clean': clean,
                           'sdist_deb': sdist_deb},
                 version=version,
                 scripts=["scripts/bauble", "scripts/bauble-admin"],
                 packages = all_packages,
                 package_dir = all_package_dirs,
                 package_data = package_data,
                 data_files = data_files,
                 install_requires=["SQLAlchemy>=0.5rc4",#<0.6",
                                   "lxml",#==2.1.1",
                                   "mako>=0.2.2",
                                   "gdata.py>=1.2.4"] + needs_sqlite,
                 test_suite="nose.collector",
                 author="Brett Adams",
                 author_email="brett@belizebotanic.org",
                 description="Bauble is a biodiversity collection manager " \
                 "software application",
                 license="GPL",
                 keywords="database biodiversity botanic collection",
                 url="http://bauble.belizebotanic.org",
                 options=py2exe_options,
                 **py2exe_setup_args
     )
