import sys
import os
import glob

if sys.platform not in ('linux2', 'win32'):
    print '**Error: Your platform is not supported: %s' % sys.platform
    sys.exit(1)


import paver

try:
    import setuptools
except ImportError:
    os.system('python %s' % os.path.join(os.curdir, 'ez_setup.py'))

from bauble import version_str as version

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


# generate the data_files list for the locale files
#if sys.platform == 'linux2':
#    locale_dir = 'share/local
#    pass
#elif sys.platform == 'win32'
#    pass

@task
@needs(['generate_setup', 'minilib', 'setuptools.command.sdist'])
def sdist():
    """
    Overrides sdist to make sure that our setup.py is generated.
    """
    pass


@task
@needs('distutils.command.build')
def build():
    """
    Override the build command.
    """
    # generate .mo translations
    builddir = 'build'
    if sys.platform == 'linux2':
        locale_tmpl = os.path.join(builddir, 'share', 'locale', '%s',
                                   'LC_MESSAGES')
    matches = glob.glob('po/*.po')
    for po in matches:
        # create an .mo in build/share/locale/$LANG/LC_MESSAGES
        loc, ext = os.path.splitext(os.path.basename(po))
        localedir = locale_tmpl % loc
        if not os.path.exists(localedir):
            os.makedirs(localedir)
        paver.runtime.sh('msgfmt %s -o %s/bauble.mo' % \
                         (po, localedir))


@task
@needs(['setuptools.command.install'])
def install():
    """
    Overrides install
    """
    # install the menu and icons entries on Linux system that complies
    # with the freedesktop.org specs
    if sys.platform == 'linux2':
        os.system('xdg-desktop-menu install --novendor bauble.desktop')
        icon_sizes = [16, 22, 32, 48, 64]#, 128]
        for size in icon_sizes:
            os.system('xdg-icon-resource install --novendor --size %s '\
                      'bauble/images/bauble-%s.png bauble' % (size, size))


# TODO: need to figure out how to install the translations from the
# build directory

options(
    setup=Bunch(
        name="bauble",
        version=version,
        scripts=["scripts/bauble"],
        options=opts,
        dist_dir='dist/bauble-%s' % version, # distribution directory
        packages = all_packages,
        package_dir = all_package_dirs,
        package_data = package_data,
        data_files = py2exe_data_files,
        install_requires=["SQLAlchemy>=0.4.4", "pysqlite>=2.3.2",
                          "simplejson>=1.7.1", "lxml>=2.0.1"],
        author="Brett",
        author_email="brett@belizebotanic.org",
        description="""\
        Bauble is a biodiversity collection manager software application""",
        license="GPL",
        keywords="database biodiversity botanic collection",
        url="http://bauble.belizebotanic.org",
#      download_url="http://bauble.belizebotanic.org/#download"
        )
)
