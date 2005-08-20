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

#subpackages = ['editors', 'tables', 'tools', 'utils', 'views']
#
#editors = ['accessions', 'families', 'genera', 'locations',
#           'plantnames', 'plants']
#editors_pkgs  = ['editors.%s' % p for p in editors]           
#
#tables = ['accessions', 'families', 'genera', 'locations',
#          'plantnames', 'plants']
#tables_pkgs = ['tables.%s' % p for p in tables]
#       
#views = ['browse', 'gbif', 'search']                
#views_pkgs = ['views.%s' % p for p in views]
#  
#tools_pkgs = ['tools.%s' % p for p in ['import_export']]

plugins = ['garden','gbif','geography','imex_abcd','imex_csv','imex_mysql',
            'labels','plants','searchview']
plugin_pkgs = ['plugins.%s' % p for p in plugins]

lib     = ['sqlobject']#, 'pysqlite2']

sqlobject_pkgs = ['firebird', 'include', 'inheritance', 'mysql', 'postgres', 
                  'sqlite', 'sybase', 'maxdb', 'util', 'manager']

# packaged to be included in the py2exe library.zip
#py2exe_includes = gtk_pkgs + editors_pkgs + tables_pkgs + views_pkgs + \
#                  tools_pkgs + lib + ["encodings"]#, "lib"]
py2exe_includes = gtk_pkgs + plugin_pkgs + lib + ["encodings"]#, "lib"]

opts = {
    "py2exe": {
            "compressed": 1,
            "optimize": 2,
            "includes": py2exe_includes,
            "packages": ["encodings"],# "pysqlite2"],
        "dll_excludes": ["iconv.dll", "intl.dll",
            "libatk-1.0-0.dll", "libgdk_pixbuf-2.0-0.dll",
            "libgdk-win32-2.0-0.dll", "libglib-2.0-0.dll",
            "libgmodule-2.0-0.dll", "libgobject-2.0-0.dll",
            "libgthread-2.0-0.dll", "libgtk-win32-2.0-0.dll",
            "libpango-1.0-0.dll", "libpangowin32-1.0-0.dll",
            "libxml2", "libglade-2.0-0", "zlib1"]
    }
}

setup(name="bauble",
      version="0.1",
      url="http://bauble.belizebotanic.org",
      author_email='brett@belizebotanic.org',
      options=opts,      
      package_dir = {'': 'src',
                     'sqlobject': 'src/lib/sqlobject',
                     'pysqlite2': 'src/lib/pysqlite2',
                     'lib': 'src/lib'},
      #packages=[""] + subpackages + editors_pkgs + tables_pkgs + 
      #         views_pkgs + tools_pkgs + lib +
      package=[""] + plugins_pkgs + ["sqlobject.%s" % p for p in sqlobject_pkgs],
      package_data={'pysqlite2': glob.glob("src\\lib\\pysqlite2\\*.pyd")},
      console=["src\\bauble.py"],
      data_files=[('', ('src\\bauble.ui',)),
                  ('images',
                   glob.glob('src'+os.sep+'images'+os.sep+'*.png')),
                  ('lib',
                   glob.glob('src'+os.sep+'lib'+os.sep+'sqlite*.*')),
                  ('pysqlite2',
                   glob.glob('src'+os.sep+'lib'+os.sep+'pysqlite2'+os.sep+'*.*'))]
    )            