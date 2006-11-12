# try:
#     from ez_setup import use_setuptool
#     use_setuptools()
#     from setuptools import setup
# except ImportError:
from distutils.core import setup    
import os, sys, glob

import sys

# TODO: to include pygtk and gtk in the dist 
# see http://py2exe.org/index.cgi/Py2exeAndPyGTK

# TODO: use an icon for the exe
# http://py2exe.org/index.cgi/CustomIcons

# TODO: alot of this work doesn't have to be done if we're not using py2exe,
# we could either create another module to import when create a exe or just
# use an ifdef
def get_version():
    '''
    returns the bauble version combined with the subversion revision number
    '''
    from bauble import version_str as version
    #from svn import repos, fs, core
    import xml.dom.minidom
    stdin, stdout = os.popen4('svn info "%s" --xml' % os.getcwd())
    svninfo = stdout.read()
    dom = xml.dom.minidom.parseString(svninfo)
    el = dom.getElementsByTagName("commit")
    revision = el[0].getAttribute('revision')
    return '%s.r%s' % (version, revision)
    
version = get_version()

# TODO: need someway to include specific modules in src/lib like fpconst.py

gtk_pkgs = [ "pango", "atk", "gobject", "gtk", "cairo", "pango", "pangocairo"]

plugins = ['garden','geography','abcd','imex_csv','formatter','plants','searchview', 'tag']
plugins_pkgs = ['bauble.plugins.%s' % p for p in plugins]
subpackages = ['plugins', 'utils']
all_packages=["bauble"] + ["bauble.%s" % p for p in subpackages] + plugins_pkgs

if sys.argv[1] == 'py2exe':
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
    
    py2exe_includes = ['pysqlite2.dbapi2', #'lxml', 'lxml._elementpath',
                       'encodings'] + gtk_pkgs + plugins_pkgs + get_sqlalchemy_includes()
else:
    py2exe_includes = []

# get all the package data
plugin_data = {}
data_patterns = ('default/*.txt', '*.ui', '*.glade')
for pattern in data_patterns:
    # glob for pattern in each of the package directories
    i = pattern.rfind(os.sep)
    extra_path = ""
    if i != -1:
        extra_path = pattern[:pattern.find(os.sep)]
    for p in plugins_pkgs:
        package_dir = p.replace('.',os.sep) + '/'
        files = glob.glob('%s%s' % (package_dir, pattern))        
        if len(files) != 0:
            if p not in plugin_data:
                plugin_data[p] = []
            plugin_data[p] += [f[len(package_dir):] for f in files]            

bauble_package_data = {'bauble': ['*.ui','*.glade','images/*.png', 'pixmaps/*.png', 'images/*.svg']}
#package_data = {'pysqlite2': ['*.pyd']}
package_data = {}
package_data.update(bauble_package_data)
package_data.update(plugin_data)

#
# generate the data files for py2exe, why can't it just use package_data?
#
if sys.platform == "win32":
    import py2exe    
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
    globs= []
    for pattern in ('default%s*.txt'%os.sep, '*.ui', '*.glade', '*.xsl'):
        # glob for pattern in each of the package directories
        i = pattern.rfind(os.sep)
        extra_path = ""
        if i != -1:
            extra_path = pattern[:pattern.find(os.sep)]
        globs += [(p.replace('.',os.sep) + os.sep + extra_path, 
                  glob.glob('%s\\%s' % (p.replace('.',os.sep), pattern))) \
                 for p in plugins_pkgs]    
    py2exe_data_files = [p for p in globs if len(p[1]) != 0]
    py2exe_data_files += [('', ('README', 'LICENSE', 'CHANGES')),
                          ('bauble', ('bauble/bauble.ui',
                                      'bauble/conn_mgr.glade')),
                          ('bauble/images', 
                           glob.glob('bauble/images/*.png')+\
                           glob.glob('bauble/images/*.svg')),
                          ('bauble/pixmaps',
                           glob.glob('bauble/pixmaps/*.png'))] 
else:
    opts=None
    py2exe_data_files = None
    
all_package_dirs = {}
for p in all_packages:    
    all_package_dirs[p] = p.replace('.', os.sep)
    
#print '------- packages --------\n' + str(all_packages)
#print '------- package directories --------\n' + str(all_package_dirs)
#print '------- packages data--------\n' + str(package_data)

setup(name="Bauble",
      version=version,
      console=["scripts/bauble"],
      windows=["scripts/bauble"],          
      scripts=["scripts/bauble"], # for setuptools?
      options=opts,
      dist_dir='dist/Bauble-%s' % version, # distribution directory
      packages = all_packages,
      package_dir = all_package_dirs,
      package_data = package_data,
      data_files = py2exe_data_files,
      install_requires=["FormEncode>=0.4", "SQLAlchemy>=0.3.0",
                        "pysqlite==2.3.2",
                        "PyGTK>=2.8.6"],# pygtk is not supported using distutils
#      extras_requires=["mysql-python and psycopg"
      
      # metadata
      author="Brett",
      author_email="brett@belizebotanic.org",
      description="""\
      Bauble is a biodiversity collection manager software application""",
      license="GPL",
      keywords="database biodiversity botanic collection",
      url="http://bauble.belizebotanic.org",
#      download_url="http://bauble.belizebotanic.org/files/bauble-0.1.tar.gz"
     )            
