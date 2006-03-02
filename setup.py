# try:
#     from ez_setup import use_setuptool
#     use_setuptools()
#     from setuptools import setup
# except ImportError:
from distutils.core import setup    
import os
import glob

import sys

# TODO: if on a unix system then create a shell script in the PATH
# to launch bauble, on windows?
# TODO: the only thing that's not working is bundling pysqlite2, the 
# problem seems that that the .pyd file in the sqlite directory
# doesn't get included so somehow i guess we need to get this
# inside library.zip or at least somewhere where pysqlite2 can find it

from bauble import version_str as version

# TODO: need someway to include specific modules in src/lib like fpconst.py

gtk_pkgs = [ "pango", "atk", "gobject", "gtk", "cairo", "pango", "pangocairo"]
sqlobject_pkgs = ['firebird', 'include', 'inheritance', 'mysql', 'postgres', 
                  'sqlite', 'sybase', 'maxdb', 'util', 'manager']

plugins = ['garden','gbif','geography','imex_abcd','imex_csv','imex_mysql',
            'formatter','plants','searchview', 'tag']
plugins_pkgs = ['bauble.plugins.%s' % p for p in plugins]
subpackages = ['plugins', 'utils']
all_packages=["bauble"] + ["bauble.%s" % p for p in subpackages] + plugins_pkgs

# packaged to be included in the py2exe library.zip
py2exe_includes = gtk_pkgs + plugins_pkgs + ["encodings"]

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
                #"packages": ["encodings"],# "pysqlite2"],
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
    py2exe_data_files += [('bauble', ('bauble/bauble.ui',
				      'bauble/conn_mgr.glade')),
                          ('bauble/images', 
			   glob.glob('bauble/images/*.png')+glob.glob('bauble/images/*.svg')),
                          ('bauble/pixmaps', glob.glob('bauble/pixmaps/*.png'))] 
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
      packages = all_packages,
      package_dir = all_package_dirs,
      package_data = package_data,
      data_files = py2exe_data_files,
#      install_requires=["FormEncode==0.2.2", "SQLObject==0.7",
#                        "pysqlite==2.0.4"],
#                        "PyGTK>=2.6"],# pygtk is not supported using distutils
#      extras_requires=["mysql-python and psycopg"
      
      # metadata
      author="Brett",
      author_email="brett@belizebotanic.org",
      description="""\
      Bauble is a biodiversity collection manager software application
      """,
      license="GPL",
      keywords="database biodiversity botanic collection",
      url="http://bauble.belizebotanic.org",
#      download_url="http://bauble.belizebotanic.org/files/bauble-0.1.tar.gz"
     )            
