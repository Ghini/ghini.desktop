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
#print data
#sys.exit(1)

setup(name="bauble",
      version="0.1",      
      url="http://bauble.belizebotanic.org",
      author_email='brett@belizebotanic.org',
      options=opts,      
      console=["bauble.py"],
#      package_dir = {'sqlobject': 'src/lib/sqlobject',
#                     'pysqlite2': 'src/lib/pysqlite2',
#                     'lib': 'src/lib'},
      packages=["bauble"] + ["bauble.%s" % p for p in subpackages] + \
          plugins_pkgs,
      #package_data={'pysqlite2': glob.glob("src\\lib\\pysqlite2\\*.pyd")},            
      package_data={'': ["*.ui"],
                    'bauble.plugins.geography': ['default/*.txt']},
                                                  
      data_files=[('bauble', ('bauble/bauble.ui',)),
                  ('bauble/images', glob.glob('bauble/images/*.png'))] + 
                  data
     )            