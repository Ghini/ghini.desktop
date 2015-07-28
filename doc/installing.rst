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

#. Download the `devinstall.sh` script and run it::

     https://raw.githubusercontent.com/Bauble/bauble.classic/master/scripts/devinstall.sh

   Please not that the script will not help you install any extra database
   connector. This you will do in a later step.

   You can study the script to see what steps if runs for you. In short it
   will install dependencies which can't be satisfied in a virtual
   environment, then it will create a virtual environment named `bacl`,
   download the sources and connect your git checkout to the `bauble-1.0`
   branch (this you can consider a production line), it then builds bauble,
   downloading all remaining dependencies, and finally it creates a startup
   script in your `~/bin` folder.

   If the script ends without error, you can now start bauble::

     ~/bin/bauble

   or update bauble to the latest released production patch::

     ~/bin/bauble -u

   The same script you can use to switch to a different production line, but
   at the moment there's only `bauble-1.0`.

#. on Unity, open a terminal, start bauble, its icon will show up in the
   launcher, you can now `lock to launcher` it.

#. If you would like to use the default `SQLite <http://sqlite.org/>`_
   database or you don't know what this means then you can skip this step.
   If you would like to use a database backend other than the default SQLite
   backend then you will also need to install a database connector.

   If you would like to use a `PostgreSQL <http://www.postgresql.org>`_
   database then activate the virtual environment and install psycopg2 with
   the following commands::

     source ~/.virtualenvs/bacl/bin/activate
     pip install -U psycopg2

   You might need solve dependencies. How to do so, depends on which Linux
   flavour you are using. Check with your distribution documentation.

.. rubric:: Next...

:ref:`connecting`.

Installing on MacOSX
====================

Being MacOSX a unix environment, most things will work the same as on Linux
(sort of).

One difficulty is that there are many more versions of MacOSX out
there than one would want to support, and only the current and its
immediately preceding release are kept up-to-date by Apple-the-firm.

Last time we tested, some of the dependencies could not be installed on
MacOSX 10.5 and we assume similar problems would present themselves on older
OSX versions.  Bauble has been successfully tested with 10.7 and 10.9.

First of all, you need things which are an integral part of a unix
environment, but which are missing in a off-the-shelf mac:

#. developers tools: xcode. check the wikipedia page for the version
   supported on your mac.
#. package manager: homebrew (tigerbrew for older OSX versions).

with the above installed, run::

    brew doctor

make sure you understand the problems it reports, and correct them. pygtk
will need xquartz and brew will not solve the dependency
automatically. either install xquartz using brew or the way you prefer::

    brew install Caskroom/cask/xquartz

then install the remaining dependencies::

    brew install git
    brew install pygtk  # takes time and installs all dependencies

follow all instructions on how to activate what you have installed.

the rest is just as on a normal unix machine, and we have a `devinstall.sh`
script for it. Read the above Linux instructions, follow them, enjoy.

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

#. download and install ``git`` (comes with a unix-like ``sh`` and includes
   ``vi``).

   all default options are fine, except we need git to be executable from
   the command prompt:

   .. image:: git3.png

#. download and install Python 2.x (32bit) from:

   http://www.python.org

   Bauble has been developed and tested using Python 2.x.  It will
   definitely **not** run on Python 3.x.  If you are interested in helping
   port to Python 3.x, please contact the Bauble maintainers.

   when installing Python, do put Python in the PATH:

   .. image:: python3.png

#. download ``pygtk`` from the following source. (this requires 32bit
   python). be sure you download the "all in one" version::

    http://ftp.gnome.org/pub/GNOME/binaries/win32/pygtk/

   make a complete install, selecting everything:

   .. image:: pygtk1.png

#. (optional) download and install a database connector other than
   ``sqlite3``. 

   On Windows, it is NOT easy to install ``psycopg2`` from sources, using
   pip, so "avoid the gory details" and use a pre-compiled pagkage from:
   
   http://initd.org/psycopg/docs/install.html

#. **REBOOT**

   hey, this is Windows, you need to reboot for changes to take effect!

#. download and run the batch file::

    https://raw.githubusercontent.com/Bauble/bauble.classic/master/scripts/devinstall.bat

   this will pull the ``bauble.classic`` repository on github to your home
   directory, under ``Local\github\Bauble``, checkout the ``bauble-1.0``
   production line, create a virtual environment and install bauble into it.

   you can also run ``devinstall.bat`` passing it as argument the numerical
   part of the production line you want to follow.

#. the following, you will do regularly, to stay up-to-date with the
   development line you chose to follow::

    cd %HOMEDRIVE%%HOMEPATH%
    .virtualenv\bacl\Scripts\activate.bat
    cd Local\github\Bauble\bauble.classic
    git pull
    python setup.py install

#. you can now start bauble using the ``bauble.lnk`` shortcut that the
   installation procedure copies to the ``Scripts`` directory of the virtual
   environment::

    %HOMEDRIVE%%HOMEPATH%\.virtualenv\bacl\Scripts\bauble.lnk

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

    Unzip it and run ``python setup.py installw`` in the folder you unzip it to.

.. rubric:: Next...

:ref:`connecting`.



