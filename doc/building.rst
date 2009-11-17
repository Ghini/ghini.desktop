Building the source
========================

In order to build Bauble from the source code you will first need to
download the code.  For more information about download the Bauble
source go to :doc:`devdl`.

Building on Windows
-------------------

1. Install Python.  Python has mostly been devloped and tested using
   Python 2.6.  It may work with other 2.x versions of Python but will
   definitely not work with Python 3.0 and greater.  You can download
   Python 2.6.2 from `python.org
   <http://www.python.org/download/releases/2.6.2/>`_.

2. Install GTK+. The easiest way to install GTK+ is to download the
   latest runtime packages from `gtk-win.sourceforge.net
   <http://gtk-win.sourceforge.net/home/index.php/Downloads>`_.

   .. note:: The gtk-win package currently doesn't support SVG which can
      cause a problem with Bauble.

   There is also a script in the Bauble source archive in
   scripts/install_gtk.py which will download the GTK+ Win32
   installer.  This will also download and install the SVG pixbuf
   loader for GTK+.

3. Install the Python GTK+ packages.  These installers have to be
   downloaded and run individually.

   - `PyCairo <http://ftp.gnome.org/pub/GNOME/binaries/win32/pycairo/>`_
   - `PyGObject <http://ftp.gnome.org/pub/GNOME/binaries/win32/pygobject/>`_
   - `PyGTK <http://ftp.gnome.org/pub/GNOME/binaries/win32/pygtk/>`_

4. Compile Bauble.  From the command line go to the directory where the
   bauble source code is and type the following::

		 python setup.py py2exe

5. Run Bauble.  To run the compiled executable run::

		.\dist\bauble.exe

6. To optionally build an NSIS installer package you must install NSIS
   from `nsis.sourceforge.net
   <http://nsis.sourceforge.net/Download>`_.  After installing NSIS
   right click on ``.\scripts\build.nsi`` in Explorer and select
   *Compile NSIS Script*.


Building on Linux
-----------------

Building on Linux will require you to be familiar with the package
manager for your distribution.  

1. Using your package manager install the following dependencies::

   	      python, pygtk, lxml, pyparsing, mako, gdata, sqlalchemy-0.5, 
	      fibra==0.0.17, python-dateutil

2. You can test if you have all the Bauble depedencies properly
   installed by running Bauble from the top directory of the source
   archive with the command::
   
		./bauble.sh

3. Install Bauble with the following command::

   	   	  sudo python setup.py install

   .. warning:: This will install Bauble directly into the system
      python package directory and will not use your systems package
      manager.  This usually means that you can not automatically
      uninstall Bauble.  If you do not need to install Bauble into the
      system python package directory then run Bauble the same as in Step 2.


