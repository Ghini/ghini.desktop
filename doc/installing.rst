Installation
============

ghini.desktop is a cross-platform program and it will run on unix machines
like GNU/Linux and MacOSX, as well as on Windows.

To install Ghini first requires that you install its dependencies that
cannot be installed automatically.  These include virtualenv, PyGTK
and pip. Python and GTK+, you probably already have. As long as you have
these packages installed then Ghini should be able to install the rest of
its dependencies by itself.

.. note:: If you follow these installation steps, you will end with Ghini
          running within a Python virtual environment, all Python
          dependencies installed locally, non conflicting with any other
          Python program you may have on your system.

          if you later choose to remove Ghini, you simply remove the
          virtual environment, which is a directory, with all of its
          content.

Installing on GNU/Linux
--------------------------

Open a shell terminal window, and follow these instructions.

.. topic:: technical note

           You can study the script to see what steps if runs for you. In
           short it will install dependencies which can't be satisfied in a
           virtual environment, then it will create a virtual environment
           named ``ghide``, use git to download the sources to a directory
           named ``~/Local/github/Ghini/ghini.desktop``, and connect this
           git checkout to the ``ghini-1.0`` branch (this you can consider a
           production line), it then builds ghini, downloading all remaining
           dependencies in the virtual environment, and finally it creates a
           startup script. If you have ``sudo`` permissions, it will be
           placed in ``/usr/local/bin``, otherwise in your ``~/bin``
           folder. Again if you

.. topic:: beginner's note
           
           To run a script, first make sure you note down the name of the
           directory to which you have downloaded the script, then you open
           a terminal window and in that window you type `bash` followed by
           a space and the complete name of the script including directory
           name, and hit on the enter key.

#. Download the `devinstall.sh` script and run it::

     https://raw.githubusercontent.com/Ghini/ghini.desktop/master/scripts/devinstall.sh

   Please note that the script will not help you install any extra database
   connector. This is not strictly necessary and you can do it at any later step.

   If the script ends without error, you can now start ghini::

     ~/bin/ghini

   or update ghini to the latest released production patch::

     ~/bin/ghini -u

   The same script you can use to switch to a different production line.
   At the moment it's just `ghini-1.0` and `ghini-1.1`.

#. on Unity, open a terminal, start ghini, its icon will show up in the
   launcher, you can now `lock to launcher` it.

#. If you would like to use the default `SQLite <http://sqlite.org/>`_
   database or you don't know what this means then you can skip this step.
   If you would like to use a database backend other than the default SQLite
   backend then you will also need to install a database connector.

   If you would like to use a `PostgreSQL <http://www.postgresql.org>`_
   database then activate the virtual environment and install psycopg2 with
   the following commands::

     source ~/.virtualenvs/ghide/bin/activate
     pip install -U psycopg2

   You might need solve dependencies. How to do so, depends on which GNU/Linux
   flavour you are using. Check with your distribution documentation.

.. rubric:: Next...

:ref:`connecting`.

Installing on MacOSX
--------------------

Being MacOSX a unix environment, most things will work the same as on GNU/Linux
(sort of).

Last time we tested, some of the dependencies could not be installed on
MacOSX 10.5 and we assume similar problems would also show on older
OSX versions.  Ghini has been successfully tested with 10.7, 10.9 and 10.12.

First of all, you need things which are an integral part of a unix
environment, but which are missing in a off-the-shelf mac:

#. developers tools: xcode. check the wikipedia page for the version
   supported on your mac.
#. package manager: homebrew (tigerbrew for older OSX versions).

with the above installed, open a terminal window and run::

    brew doctor

make sure you understand the problems it reports, and correct them. pygtk
will need xquartz and brew will not solve the dependency
automatically. either install xquartz using brew or the way you prefer::

    brew install Caskroom/cask/xquartz

then install the remaining dependencies::

    brew install git
    brew install pygtk  # takes time and installs all dependencies

follow all instructions on how to activate what you have installed.

.. topic:: Mac running OSX 10.12 —Sierra—

           On OSX 10.12, ``brew`` reports that ``gettext`` is already
           installed, but then it won't let us find it. A solution is to run
           the following line::

             brew link gettext --force

           Before we can run ``devinstall.sh`` as on GNU/Linux, we still
           need installing a couple of python packages, globally. Do this::
   
             sudo pip install virtualenv lxml

The rest is just as on a normal unix machine. Read the above GNU/Linux instructions, follow them, enjoy.

.. rubric:: Next...

:ref:`connecting`.

Installing on Windows
---------------------

The current maintainer of ghini.desktop has no interest in learning how to
produce Windows installers, so the Windows installation is here reduced to
the same installation procedure as on Unix (GNU/Linux and MacOSX).

Please report any trouble. Help with packaging will be very welcome, in
particular by other Windows users.

The steps described here instruct you on how to install Git, Gtk, Python,
and the python database connectors. With this environment correctly set up,
the Ghini installation procedure runs as on GNU/Linux. The concluding steps are
again Windows specific.

.. note:: Ghini has been tested with and is known to work on W-XP, W-7 and
   W-8. Although it should work fine on other versions Windows it has not
   been thoroughly tested.

.. note:: Direct download links are given for all needed components. They
          have been tested in September 2015, but things change with
          time. If any of the direct download links stops working, please
          ring the bell, so we can update the information here.

.. _Direct link to download git: https://github.com/git-for-windows/git/releases/download/v2.10.0.windows.1/Git-2.10.0-32-bit.exe
.. _Direct link to download Python: https://www.python.org/ftp/python/2.7.12/python-2.7.12.msi
.. _Direct link to download lxml: https://pypi.python.org/packages/2.7/l/lxml/lxml-3.6.0.win32-py2.7.exe
.. _Direct link to download PyGTK: http://ftp.gnome.org/pub/GNOME/binaries/win32/pygtk/2.24/pygtk-all-in-one-2.24.2.win32-py2.7.msi
.. _Direct link to download psycopg2: http://www.stickpeople.com/projects/python/win-psycopg/2.6.1/psycopg2-2.6.1.win32-py2.7-pg9.4.4-release.exe

The installation steps on Windows:

#. download and install ``git`` (comes with a unix-like ``sh`` and includes
   ``vi``) from::

   https://git-scm.com/download/win
   
   `Direct link to download git`_

   all default options are fine, except we need git to be executable from
   the command prompt:

   .. image:: images/screenshots/git3.png

#. download and install Python 2.x (32bit) from::

   http://www.python.org

   `Direct link to download Python`_

   Ghini has been developed and tested using Python 2.x.  It will
   definitely **not** run on Python 3.x.  If you are interested in helping
   port to Python 3.x, please contact the Ghini maintainers.

   when installing Python, do put Python in the PATH:

   .. image:: images/screenshots/python3.png

#. download ``pygtk`` from the following source. (this requires 32bit
   python). be sure you download the "all in one" version::

   http://ftp.gnome.org/pub/GNOME/binaries/win32/pygtk/

   `Direct link to download PyGTK`_

   make a complete install, selecting everything:

   .. image:: images/screenshots/pygtk1.png

#. (Windows 8.x) please consider this additional step. It is possibly
   necessary to avoid the following error on Windows 8.1 installations::

    Building without Cython.
    ERROR: 'xslt-config' is not recognized as an internal or external command,
    operable program or batch file.

   If you skip this step and can confirm you get the error, please inform us.

   You can download lxml from::

    https://pypi.python.org/pypi/lxml/3.4.4

   Remember you need the 32 bit version, for Python 2.7.

   `Direct link to download lxml`_

#. (optional) download and install a database connector other than
   ``sqlite3``. 

   On Windows, it is NOT easy to install ``psycopg2`` from sources, using
   pip, so "avoid the gory details" and use a pre-compiled pagkage from:
   
   http://initd.org/psycopg/docs/install.html

   `Direct link to download psycopg2`_

#. **REBOOT**

   hey, this is Windows, you need to reboot for changes to take effect!

#. download and run (from ``\system32\cmd.exe``) the batch file:

    https://raw.githubusercontent.com/Ghini/ghini.desktop/master/scripts/devinstall.bat

   right before you hit the enter key to run the script, your screen might
   look like something like this:

   .. image:: images/screenshots/sys32cmd-1.png

   this will pull the ``ghini.desktop`` repository on github to your home
   directory, under ``Local\github\Ghini``, checkout the ``ghini-1.0``
   production line, create a virtual environment and install ghini into it.

   you can also run ``devinstall.bat`` passing it as argument the numerical
   part of the production line you want to follow.

   this is the last installation step that depends, heavily, on a working
   internet connection.

   the operation can take several minutes to complete, depending on the
   speed of your internet connection.

#. the last installation step creates the Ghini group and shortcuts in the
   Windows Start Menu, for all users. To do so, you need run a script with
   administrative rights. The script is called ``devinstall-finalize.bat``,
   it is right in your HOME folder, and has been created at the previous
   step.

   right-click on it, select run as administrator, confirm you want it to
   make changes to your computer. These changes are in the Start Menu only:
   create the Ghini group, place the Ghini shortcut.

#. download the batch file you will use to stay up-to-date with the
   production line you chose to follow:

    https://raw.githubusercontent.com/Ghini/ghini.desktop/master/scripts/ghini-update.bat

   if you are on a recent Ghini installation, each time you start the
   program, Ghini will check on the development site and alert you of any
   newer ghini release within your chosen production line.

   any time you want to update your installation, just start the command
   prompt and run ``ghini-update.bat``

If you would like to generate and print PDF reports using Ghini's
default report generator then you will need to download and install
`Apache FOP <http://xmlgraphics.apache.org/fop/>`_. After extracting
the FOP archive you will need to include the directory you extracted
to in your PATH.

.. rubric:: Next...

:ref:`connecting`.

.. _troubleshoot_install:

Troubleshooting
---------------------------

#.  any error related to lxml.

    In order to be able to compile lxml, you have to install a C compiler
    (on GNU/Linux this would be the ``gcc`` package) and Cython (a Python
    specialization, that gets compiled into C code. Note: Cython is not
    CPython).

    However, It should not be necessary to compile anything, and ``pip``
    should be able to locate the binary modules in the online libraries. 

    For some reason, this is not the case on Windows 8.1.

    https://pypi.python.org/pypi/lxml/3.4.4

    Please report any other trouble related to the installation of lxml.

#.  Couldn't install gdata.

    For some reason the Google's gdata package lists itself in the
    Python Package Index but doesn't work properly with the
    easy_install command.  You can download the latest gdata package
    from:

    http://code.google.com/p/gdata-python-client/downloads/list

    Unzip it and run ``python setup.py installw`` in the folder you unzip it to.

.. rubric:: Next...

:ref:`connecting`.
