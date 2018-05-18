#!/usr/bin/env python
#
# Copyright (c) 2005,2006,2007,2008,2009 Brett Adams <brett@belizebotanic.org>
# Copyright (c) 2015 Mario Frasca <mario@anche.no>
# Copyright (c) 2016,2017 Ross Demuth <rossdemuth123@gmail.com>
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

try:
    import setuptools
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    import setuptools
import os
import sys
import glob
spawn = setuptools.distutils.spawn
dep_util = setuptools.distutils.dep_util
dir_util = setuptools.distutils.dir_util
file_util = setuptools.distutils.file_util
from distutils.command.build import build as _build
#from setuptools.command.build_py import build_py as _build
from setuptools import Command
from setuptools.command.install import install as _install
from bauble import version

# TODO: external dependencies not in the PyPI: PyGTK>=2.14
# TODO: optional dependencies: MySQL-Python, psycopg2,
# Sphinx (for building docs, maybe include in buildr-requires)

# TODO: fix permissions on files when creating an sdist with:
# find . -regex '.*?\.\(glade\|xsl\|txt\|svg\|ui\)'  -exec chmod 644 {} \;

# TODO: run the clean before creating an sdist, or at least the
# manifest should not include those files that would be cleaned

# relative path for locale files
locale_path = os.path.join('share', 'locale')

gtk_pkgs = ["pango", "atk", "gobject", "gtk", "cairo", "pangocairo", "gio"]
plugins = setuptools.find_packages(
    where='bauble/plugins',
    exclude=['test', 'bauble.*.test', 'ghini.*.test'])
plugins_pkgs = ['bauble.plugins.%s' % p for p in plugins]
all_packages = setuptools.find_packages(exclude=['test', 'bauble.*.test',
                                                 'ghini.*.test'])

package_data = {'': ['README.rst', 'CHANGES', 'LICENSE'],
                'bauble': ['*.ui', '*.glade', 'images/*.png', 'pixmaps/*.png',
                           'images/*.svg', 'images/*.gif', 'images/*.ico',
                           'images/*.bmp']}

# ceate a list of the data patterns to look for in the packages
data_patterns = ['default/*.txt', '*.ui', '*.glade', '*.xsl', '*.xsd',
                 '*.html', '*.csv', '*.svg', '*.ps']
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
    sqlalchemy_includes = ['sqlalchemy.dialects.sqlite',
                           'sqlalchemy.dialects.postgresql']
    py2exe_includes = ['sqlite3', 'lxml', 'gdata', 'fibra', 'psycopg2',
                       'encodings', 'mako', 'mako.cache',
                       'pygments.styles.default', 'pyparsing']
    py2exe_includes += gtk_pkgs + plugins_pkgs + sqlalchemy_includes
    py2exe_setup_args = {
        'windows': [{'script': 'scripts/ghini',
                     'icon_resources': [(1, "bauble/images/icon.ico")]}]}
    py2exe_options = {
        "py2exe": {
            #no compression makes for better NSIS compression
            "compressed": False,
            "optimize": 2,
            "includes": py2exe_includes,
            "dll_excludes": [
                # GTK, included elsewhere
                "iconv.dll", "intl.dll", "libatk-1.0-0.dll",
                "libgdk_pixbuf-2.0-0.dll", "libgdk-win32-2.0-0.dll",
                "libglib-2.0-0.dll", "libgmodule-2.0-0.dll",
                "libgobject-2.0-0.dll", "libgthread-2.0-0.dll",
                "libgtk-win32-2.0-0.dll", "libpango-1.0-0.dll",
                "libpangowin32-1.0-0.dll", "libxml2-2.dll",
                # windows dlls
                "DNSAPI.DLL", "MSIMG32.DLL", "Secur32.dll", "SHFOLDER.dll",
                "CRYPT32.dll", "MPR.dll"
                ]
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
        description = 'build standalone Windows executable'
        def run(self):
            # TODO: make sure we have everything installed that we need to
            # bundle e.g. sqlite, psycopg2, others...
            _py2exe_cmd.run(self)
            # install locale files
            locales = os.path.dirname(locale_path)
            build_base = self.get_finalized_command('build').build_base

            src = os.path.join(build_base, locales)
            dir_util.copy_tree(src, os.path.join(self.dist_dir, locales))

            # copy GTK to the dist directory, assuming PyGTK
            # all-in-one installer
            gtk_root = 'c:\\python27\\lib\\site-packages\\gtk-2.0\\runtime'
            dist_gtk = os.path.join(self.dist_dir, 'gtk')
            import shutil
            if not os.path.exists(dist_gtk):
                ignore = shutil.ignore_patterns('src', 'gtk-doc', 'icons',
                                                'man', 'demo', 'aclocal',
                                                'doc', 'include', 'emacs',
                                                'gettext', 'glade3',
                                                'gtksourceview-2.0', 'info',
                                                'intltool')
                shutil.copytree(gtk_root, dist_gtk, ignore=ignore)

            # register the pixbuf loaders
            # populate loaders.cache also
            exe = '%s\\bin\\gdk-pixbuf-query-loaders.exe' % dist_gtk
            dest1 = '%s\\etc\\gtk-2.0\\gdk-pixbuf.loaders' % dist_gtk
            dest2 = '%s\\lib\\gdk-pixbuf-2.0\\2.10.0\\loaders.cache' % dist_gtk
            cmd1 = 'call "%s" > "%s"' % (exe, dest1)
            cmd2 = 'call "%s" > "%s"' % (exe, dest2)
            print cmd1
            print cmd2
            os.system(cmd1)
            os.system(cmd2)

            # copy the the MS-Windows gtkrc to make it the default theme
            rc = '%s\\share\\themes\\MS-Windows\\gtk-2.0\\gtkrc' % dist_gtk
            dest = '%s\\etc\\gtk-2.0' % dist_gtk
            file_util.copy_file(rc, dest)

            # copy the gnome index.theme - stops stderr messages
            gtheme = '%s\\share\\icons\\hicolor\\index.theme' % gtk_root
            dest = '%s\\share\\icons\\hicolor' % self.dist_dir
            dir_util.mkpath(dest)
            file_util.copy_file(gtheme, dest)

            # copy LICENSE to dist\share\LICENSE.ghini (for help>about)
            file_util.copy_file(
                "LICENSE",
                os.path.join(self.dist_dir, 'share', 'ghini', 'LICENSE'))

    class NsisCmd(Command):
        """Command to create a Windows NSIS installer"""

        description = 'build windows NSIS installer'

        user_options = [
            ('makensis=', 'm', 'path to makensis'),
            ('nsis-script=', 's', 'script to build installer from')
            ]

        def initialize_options(self):
            envars = ['programw6432', 'programfiles', 'localappdata']
            mns = 'nsis\\makensis'
            locs = [os.path.join(os.getenv(ev, 'c:\\'), mns) for ev in envars]
            self.makensis = (
                [loc for loc in locs if spawn.find_executable(loc)] +
                [spawn.find_executable('makensis')])[0]
            self.nsis_script = 'scripts\\build-multiuser.nsi'

        def finalize_options(self):
            if self.makensis:
                is_exe = spawn.find_executable(self.makensis) is not None
                exe_name = os.path.split(self.makensis)[-1]
                is_makensis = exe_name in ('makensis', 'makensis.exe')
                if not is_exe or not is_makensis:
                    raise Exception('makensis not found at: %s' % self.makensis)
            else:
                raise Exception('can not find makensis, NSIS needs to be '
                                'installed in the default location, on the '
                                'path or provided using --makensis=')

            if not os.path.exists(self.nsis_script):
                raise Exception('can not find nsis build script at: %s'
                                % self.nsis_script)

        def run(self):
            print 'using %s to build %s' % (self.makensis, self.nsis_script)
            os.system('"%s" %s' % (self.makensis, self.nsis_script))

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
        description = 'build Windows executable *ONLY AVAILABLE IN WINDOWS'
        pass

    class NsisCmd(_empty_cmd):
        description = 'build Windows NSIS installer *ONLY AVAILABLE IN WINDOWS'
        pass


# build command
class build(_build):
    def run(self):
        if sys.platform == 'win32':
            # try to guess the path of the gettext utilities
            os.environ['PATH'] = os.environ['PATH'] + \
                ';c:\\Program Files\\GnuWin32\\bin'
        if not spawn.find_executable('msgfmt'):
            msg = '** Error: Building Ghini requires the gettext utilities ' \
                  'be installed.  If they are installed please ensure that ' \
                  'the msgfmt command is in your PATH'
            print msg
            sys.exit(1)

        # create build/share directory
        dir_util.mkpath(os.path.join(self.build_base, 'share', 'ghini'))

        _build.run(self)

        dest_tmpl = os.path.join(self.build_base, locale_path, '%s',
                                 'LC_MESSAGES')
        matches = glob.glob('po/*.po')
        from bauble.i18n import TEXT_DOMAIN
        for po in matches:
            # create an .mo in build/share/locale/$LANG/LC_MESSAGES
            loc, ext = os.path.splitext(os.path.basename(po))
            localedir = dest_tmpl % loc

            mo = '%s/%s.mo' % (localedir, TEXT_DOMAIN)
            if not os.path.exists(localedir):
                dir_util.mkpath(localedir)
            if not os.path.exists(mo) or dep_util.newer(po, mo):
                spawn.spawn(['msgfmt', po, '-o', mo])

        # copy .desktop and icons
        if sys.platform in ('linux3', 'linux2'):
            app_dir = os.path.join(self.build_base, 'share', 'applications')
            dir_util.mkpath(app_dir)
            file_util.copy_file('data/ghini.desktop', app_dir)

            icon_sizes = [16, 22, 24, 32, 48, 64]
            icon_root = os.path.join(
                self.build_base, 'share', 'icons', 'hicolor')

            # copy scalable icon
            scalable_dir = os.path.join(icon_root, 'scalable', 'apps')
            dir_util.mkpath(scalable_dir)
            file_util.copy_file('data/ghini.svg', scalable_dir)

            pixmaps_dir = os.path.join(self.build_base, 'share', 'pixmaps')
            dir_util.mkpath(pixmaps_dir)
            file_util.copy_file('data/ghini.svg', pixmaps_dir)

            # copy .png icons
            dimension = lambda s: '%sx%s' % (s, s)
            for size in icon_sizes:
                img = 'data/ghini-%s.png' % size
                dest = os.path.join(icon_root, '%s/apps/ghini.png'
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
        if sys.platform not in ('linux3', 'linux2', 'win32', 'darwin'):
            msg = "**Error: Can't install on this platform: %s" % sys.platform
            print msg
            sys.exit(1)

        # create build/share directory
        dir_util.mkpath(os.path.join(self.build_base, 'share', 'ghini'))

        if not self.single_version_externally_managed:
            print 'before installing new egg, remove old ones!'
            old_egg_dirs = [a for (a, b, c) in os.walk(self.install_data)
                            if (os.path.basename(a).startswith('bauble')
                                or os.path.basename(a).startswith('ghini.desktop'))
                               and os.path.basename(a).endswith('egg')]
            for oed in old_egg_dirs:
                dir_util.remove_tree(oed)
            self.do_egg_install()
        else:
            _install.run(self)

        # install ghini.desktop and icons
        if sys.platform in ('linux3', 'linux2'):
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

        file_util.copy_file(
            "LICENSE",
            os.path.join(self.install_data, 'share', 'ghini', 'LICENSE'))


# docs command
DOC_BUILD_PATH = 'doc/.build/'


class docs(Command):
    user_options = [('all', 'a', 'rebuild all the docs')]

    def initialize_options(self):
        self.all = False

    def finalize_options(self):
        pass

    def run(self):
        try:
            import sphinx
            sphinx
        except ImportError:
            print 'Building the docs requires the '\
                  'Sphinx(http://sphinx.pocoo.org) package'
            return
        if not os.path.exists(DOC_BUILD_PATH):
            dir_util.mkpath(DOC_BUILD_PATH)
        cmd = ['sphinx-build', '-b', 'html', 'doc', DOC_BUILD_PATH]
        if self.all:
            # rebuild all the docs
            cmd.insert(1, '-E')
        spawn.spawn(cmd)


# clean command
class clean(Command):
    user_options = [('all', 'a', 'clean everything'),
    ]

    def initialize_options(self):
        self.all = False

    def finalize_options(self):
        pass

    def run(self):
        patterns = ['MANIFEST', '*~', '*flymake*', '*.pyc', '*.h']
        cwd = os.getcwd()
        import fnmatch
        for path, subdirs, files in os.walk(cwd):
            for pattern in patterns:
                matches = fnmatch.filter(files, pattern)
                if matches:
                    def delete(p):
                        print 'removing %s' % p
                        os.remove(p)
                    map(delete, [os.path.join(path, m) for m in matches])
        if os.path.exists('dist'):
            dir_util.remove_tree('dist')
        if os.path.exists('build'):
            dir_util.remove_tree('build')
        if os.path.exists(DOC_BUILD_PATH):
            dir_util.remove_tree(DOC_BUILD_PATH)
        # older eggs, possibly going under previous name
        egg_info_dirs = ['ghini.desktop.egg-info', 'bauble.egg-info']
        for eid in egg_info_dirs:
            if os.path.exists(eid):
                dir_util.remove_tree(eid)

        # deb_dist - used by stdeb
        deb_dist = 'deb_dist'
        if os.path.exists(deb_dist):
            dir_util.remove_tree(deb_dist)


class run(Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        cwd = os.getcwd()
        os.system(os.path.join(cwd, 'ghini.sh'))


# require pysqlite if not using python2.5 or greater
needs_sqlite = []
try:
    import sqlite3
    sqlite3
except ImportError:
    needs_sqlite = ["pysqlite>=2.3.2"]

scripts = ["scripts/ghini"]
if sys.platform == 'win32':
    scripts = ["scripts/ghini", "scripts/ghini.bat", "scripts/ghini.vbs",
               "scripts/ghini-update.bat"]

setuptools.setup(name="ghini.desktop",
                 cmdclass={'build': build, 'install': install,
                           'py2exe': py2exe_cmd, 'nsis': NsisCmd,
                           'docs': docs, 'clean': clean, 'run': run},
                 version=version,
                 scripts=scripts,
                 packages=all_packages,
                 package_dir=all_package_dirs,
                 package_data=package_data,
                 data_files=data_files,
                 install_requires=["SQLAlchemy==1.0.8",
                                   "raven==6.7.0",
                                   "Pillow==2.3.0",
                                   "lxml",
                                   "pyqrcode==1.2.1",
                                   "mako==0.9.1",
                                   "gdata==2.0.18",
                                   "requests",
                                   "fibra==0.0.17",
                                   "pyparsing==2.0.1",
                                   'python-dateutil<2.0'] + needs_sqlite,
                 test_suite="nose.collector",
                 author="Mario Frasca",
                 author_email="mario@anche.no",
                 description="Ghini is a biodiversity collection manager "
                 "software application",
                 license="GPLv2+",
                 keywords="database biodiversity botanic collection "
                 "botany herbarium arboretum",
                 url="http://github.com/Ghini/ghini.desktop/",
                 options=py2exe_options,
                 **py2exe_setup_args
                 )
