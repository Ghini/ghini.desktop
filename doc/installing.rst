Installation
------------

bauble.classic is a cross-platform program and it will run on unix machines
like Linux and MacOSX, as well as on Windows.

To install Bauble first requires that you install its dependencies that
cannot be installed automatically.  These include virtualenvwrapper, PyGTK
and pip. Python and GTK+, you probably already have. As long as you have
these packages installed then Bauble should be able to install the rest of
its dependencies by itself.

.. note:: If you follow these installation steps, you will end with Bauble
          running within a Python virtual environment, all Python
          dependencies installed locally, non conflicting with any other
          Python program you may have on your system.

          if you later choose to remove Bauble, you simply remove the
          virtual environment, which is a directory, with all of its
          content.

Installing on Linux
===================

#. Make sure your `Python <http://www.python.org>`_ version is 2.4
   or greater, that you have the develompent environment for `GTK+
   <http://www.gtk.org>`_ and that you have installed `PyGTK
   <http://www.pygtk.org>`_ using your package manager (ubuntu,
   debian: python-gtk2).

#. Download and extract the Bauble source package from

   https://github.com/Bauble/bauble.classic.git

#. Make and activate a virtual environment with
   ``--system-site-packages``.

#. If you would like to use the default `SQLite
   <http://sqlite.org/>`_ database or you don't know what this means
   then you can skip this step.  If you would like to use a database
   backend other than the default SQLite backend then you will also
   need to install a database connector.

   If you would like to use a `PostgreSQL <http://www.postgresql.org>`_
   database then install psycopg2 with the following commands::

     pip install -U psycopg2

#. In the installation directory execute the following command::

     python setup.py install

   If this doesn't complete successfully see :ref:`troubleshoot_install`.

#. Any time you want to run Bauble, open a terminal window, activate
   the virtual environment and execute the ``bauble`` command.

.. rubric:: Next...

:ref:`connecting`.

Installing on MacOSX
====================

Being MacOSX a unix environment, most stuff should work just like in
Linux, but we've never tried. Feedback highly welcome.

.. rubric:: Next...

:ref:`connecting`.

Installing on Windows
=====================

The Windows installer used to be a "batteries-included" installer,
installing everything needed to run Bauble.  The current maintainer
of bauble.classic cannot run Windows applications. If you want to
run the latest version of bauble on Windows: download and install
the dependencies and then install Bauble from the source package.

Please report any trouble and help with packaging will be very
welcome.

.. note:: Bauble has been tested with and is known to work on W-XP, W-7 and
   W-8. Although it should work fine on other versions Windows it has not
   been thoroughly tested.

the installation steps on Windows:

#. Install GTK+. The easiest way to install GTK+ is to download the
   latest runtime packages from `gtk-win.sourceforge.net
   <http://gtk-win.sourceforge.net/home/index.php/Downloads>`_.

   .. note:: The gtk-win package currently doesn't support SVG which can
      cause a problem with Bauble.

   There is also a script in the Bauble source archive in
   scripts/install_gtk.py which will download the GTK+ Win32
   installer.  This will also download and install the SVG pixbuf
   loader for GTK+.

#. download and install Python 2.x (32bit) from:

   http://www.python.org

   Bauble has been developed and tested using Python 2.x.  It will
   definitely `not` run on Python 3.x.  If you are interested in helping
   port to Python 3.x, please contact the Bauble maintainers.

#. download ``pygtk`` from the following source. (this requires 32bit
   python). be sure you download the "all in one" version. make a complete
   install, selecting everything:

   http://ftp.gnome.org/pub/GNOME/binaries/win32/pygtk/

#. download and install ``pip`` from:

   http://bootstrap.pypa.io/get-pip.py

#. download and install ``git`` (comes with a unix-like ``sh`` and ``vi``).

#. (optional) download and install a database connector other than
   ``sqlite3``. 

   On Windows, it is NOT easy to install ``psycopg2`` from
   sources, using pip, so "avoid the gory details" and use a pre-compiled 
   pagkage from:
   
   http://initd.org/psycopg/docs/install.html

#. include ``C:\Python27`` and ``C:\Python27\Scripts`` in your path.

#. install ``virtualenv`` (using ``pip``)

#. cd to your HOME dir, create the virtual environment, call it ``bacl`` and activate it::

    virtualenv --system-site-packages .virtualenvs\bacl
    .virtualenvs\bacl\Scripts\activate.bat

#. cd to where you want to get bauble.classic.

#. download the bauble.classic sources (using git) from:

   http://www.github.com/Bauble/bauble.classic/

#. cd into the newly created ``bauble.classic`` directory.

#. choose the development line you plan to follow, for example ``1.0``, build, install::

    git checkout bauble-1.0
    python setup.py build
    python setup.py install

#. create a ``bauble.bat`` file in your HOME dir, with this content::

    call .virtualenvs\bacl\Scripts\activate.bat
    pythonw .virtualenvs\bacl\Scripts\bauble

#. create a vbs file in your HOME dir, with this content::

    CreateObject("Wscript.Shell").Run "bauble.bat", 0, True

#. create a shortcut to the vbs file in the same HOME dir.

#. modify the icon of the shortcut, rename it as of your tastes.

#. drag and drop the shortcut into the Start Menu.

#. the following two, you will do regularly, to stay up-to-date with the
   development line you chose to follow::

    git pull
    python setup.py install

If you would like to generate and print PDF reports using Bauble's
default report generator then you will need to download and install
`Apache FOP <http://xmlgraphics.apache.org/fop/>`_. After extracting
the FOP archive you will need to include the directory you extracted
to in your PATH.

.. rubric:: Next...

:ref:`connecting`.

.. _troubleshoot_install:

Troubleshooting the Install
===========================

#.  What are the packages that are installed by Bauble:

    The following packages are required by Bauble

    	*  SQLAlchemy
    	*  lxml

    The following packages are optional:

    	* Mako - required by the template based report generator
    	* gdata - required by the Picasa photos InfoBox


#.  Couldn't install lxml.

    The lxml packages have to be compile with a C compiler. If you
    don't have a Make sure the libxml and libxsl packages are
    installed.  Installing the Cython packages.  On Linux you will
    have to install the gcc package.  On Windows there should be a
    precompiled version available at
    http://pypi.python.org/pypi/lxml/2.1.1

#.  Couldn't install gdata.

    For some reason the Google's gdata package lists itself in the
    Python Package Index but doesn't work properly with the
    easy_install command.  You can download the latest gdata package
    from:

    http://code.google.com/p/gdata-python-client/downloads/list

    Unzip it and run ``python setup.py installw` in the folder you unzip it to.

.. rubric:: Next...

:ref:`connecting`.



