Bauble
======

what is Bauble (classic)
------------------------

At its heart Bauble is a framework for creating database applications.  In
its distributed form Bauble is an application to manage plant records and
specifically living collections.  It is used among others by Belize Botanic
Gardens to manage their live collections.  Included by default is RBG Kew's
Family and Genera list from Vascular Plant Families and Genera compiled by
R. K. Brummitt and published by the Royal Botanic Gardens, Kew in 1992 used
by permission from RBG Kew.

All code contained as part of the Bauble package is licenced under the
GNU GPLv2+.

Terms and Names
---------------

This file describes 'bauble.classic', a standalone
application. 'bauble.classic' was formerly known just as as
'Bauble'. currently 'Bauble' is the name of an organization on github,
enclosing 'bauble.classic', 'bauble.webapp' and 'bauble.api'.

the two new projects 'bauble2' and 'bauble.api' are what you would
fork/download if you want to participate to the development of a web-based
version of 'Bauble'.

'bauble.classic' is what you would install if you want to start using
'Bauble' straight away.

The database structure of both 'bauble.classic' and the pair
'bauble2/bauble.api' is similar so any data you would insert using
'bauble.classic' will be available once you install a running version of
'bauble2/bauble.api'.

Requirements
------------
bauble.classic requires the following packages to run.  The installer for Windows comes 
with everything already built in except for GTK+ and the optional XSL->PDF 
renderer which is need to use the formatter plugin.


* a debug version of Python (>= 2.4, recently tested with 2.7.5)
* SQLAlchemy (>= 0.6.0, recently tested with 0.9.1)
* pygtk (>= 2.12)
* PyGObject (>= 2.11.1)
* lxml (>= 2.0)

each of the following database connectors is optional, but at least one is needed:

* pysqlite >= 2.3.2
* psycopg2 >= 2.0.5 
* mysql-python >= 1.2.1 

To use the formatter plugin you will also need to install an XSL->PDF renderer. For
a free renderer check out Apache FOP (>=.92beta) at 
http://xmlgraphics.apache.org/fop/


Installation
------------

### Linux

1. Download the bauble.classic sources from either:
   * git clone https://github.com/Bauble/bauble.classic.git
   * git clone https://github.com/mfrasca/bauble.classic.git
2. Change to the bauble directory containing the sources
3. (optional) make a virtual environment with --system-site-packages.
4. install system wide: pygtk (ubuntu, debian: python-gtk2)
5. Type "[sudo] python setup.py install" on the command line.
6. (optional) install a python DBMS wrapper (or use sqlite3).
7. Type bauble on the command line to run Bauble.

### MacOSX

being MacOSX a unix environment, most stuff should work just like in Linux,
but we've never tried.

### Windows

the 'batteries included' install allows the simple sequence:

1. Download the bauble-<version>-.exe file from 
   http://bauble.belizebotanic.org
2. Double click on the file when it finishes downloading.
3. Run Bauble from the Start menu.

unfortunately, nobody maintains the above installer, so you possibly better
do a source install and take care of installing the 'batteries', which are
not so many:

1. python (32bit) from:
   http://www.python.org
2. pygtk (requires 32bit python) from:
   http://ftp.gnome.org/pub/GNOME/binaries/win32/pygtk/
3. gettext from
   http://www.boost.org/doc/libs/1_56_0/libs/locale/doc/html/gettext_for_windows.html
4. psycopg2 from
   TODO: still don't know. on Windows, pip does not manage install it.
   without it, you can use bauble on sqlite3 databases.

now you sort of follow the same steps as in a normal operating system,
taking care of the usual obvious differences between Windows and the unix
world:

1. install pip (from http://bootstrap.pypa.io/get-pip.py),
   virtualenvwrapper-win (using pip),
   git (includes git-shell)
2. download the bauble.classic sources (using git)
3. create a new virtual environment
   (the parameter is the relative path to the directory that is to contain it)
4. activate it
5. python setup.py install
6. prepare a git-shell script that:
   activates the virtual environment
   sets the language
   invokes bauble
