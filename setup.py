# try:
#     from ez_setup import use_setuptool
#     use_setuptools()
#     from setuptools import setup
# except ImportError:
from distutils.core import setup    
import os
import glob

import sys
if sys.platform == "win32":
    import py2exe

# TODO: if on a unix system then create a shell script in the PATH
# to launch bauble, on windows?
# TODO: the only thing that's not working is bundling pysqlite2, the 
# problem seems that that the .pyd file in the sqlite directory
# doesn't get included so somehow i guess we need to get this
# inside library.zip or at least somewhere where pysqlite2 can find it

# TODO: need someway to include specific modules in src/lib like fpconst.py

gtk_pkgs = [ "pango", "atk", "gobject", "gtk" ]

plugins = ['garden','gbif','geography','imex_abcd','imex_csv','imex_mysql',
            'labels','plants','searchview']
plugins_pkgs = ['bauble.plugins.%s' % p for p in plugins]

lib = ['sqlobject']#, 'pysqlite2']

sqlobject_pkgs = ['firebird', 'include', 'inheritance', 'mysql', 'postgres', 
                  'sqlite', 'sybase', 'maxdb', 'util', 'manager']
subpackages = ['plugins', 'utils']
# packaged to be included in the py2exe library.zip
py2exe_includes = gtk_pkgs + plugins_pkgs + lib + ["encodings"]#, "lib"]

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

# get the data files for the plugins, this should 
# only be used for py2exe
globs= []
for pattern in ('default%s*.txt'%os.sep, '*.ui', '*.glade'):
    # glob for pattern in each of the package directories
    i = pattern.rfind(os.sep)
    extra_path = ""
    if i != -1:
        extra_path = pattern[:pattern.find(os.sep)]
    globs += [(p.replace('.',os.sep) + os.sep + extra_path, 
              glob.glob('%s\\%s' % (p.replace('.',os.sep), pattern))) \
             for p in plugins_pkgs]
data = [p for p in globs if len(p[1]) != 0]

setup(name="Bauble",
      version="0.1",      
#      console=["bauble.py"],
      options=opts,
      packages=["bauble"] + ["bauble.%s" % p for p in subpackages] + \
      plugins_pkgs,
      scripts=["scripts/bauble"], # for setuptools?      
      package_data={'': ['*.ui','images/*.png'],
                    'bauble.plugins.geography': ['default/*.txt'],
                    'bauble.plugins.garden': ['*.glade']},
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
      keywords="database biodiversity botanic",
      url="http://bauble.belizebotanic.org",
      download_url="http://bauble.belizebotanic.org/bauble-0.1.tar.gz"      
     )            
