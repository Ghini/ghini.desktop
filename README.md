Bauble
======

terms and names
---------------

This file describes 'bauble.classic', a standalone
application. 'bauble.classic' was formerly known as 'Bauble'. currently
'Bauble' is the name of an organization on github, enclosing
'bauble.classic', 'bauble2' and 'bauble.api'.

'bauble.classic' is what you would install if you want to use 'Bauble'.

the two new projects 'bauble2' and 'bauble.api' are what you would
fork/download if you want to participate to the development of a web-based
version of 'Bauble'. the database structure of both 'bauble.classic' and the
pair 'bauble2/bauble.api' is similar so any data you would insert using
'bauble.classic' will be available once you install a running version of
'bauble2/bauble.api'.

what is Bauble
--------------

At its heart Bauble is a framework for creating database applications.  In
its distributed form Bauble is an application to manage plant records and 
specifically living collections.  It is used by Belize Botanic Gardens to 
manage their live collections.  Included by default is RBG Kew's Family and 
Genera list from Vascular Plant Families and Genera compiled by R. K. Brummitt
and published by the Royal Botanic Gardens, Kew in 1992 used by permission 
from RBG Kew.

All code contained as part of the Buable package is licenced under the
GNU GPLv2+.



Requirements:
-------------
Bauble requires the following packages to run.  The installer for Windows comes 
with everything already built in except for GTK+ and the optional XSL->PDF 
renderer which is need to use the formatter plugin.


Python 2.4 (not tested with other versions but they may work as well)

* SQLAlchemy>=0.6.0
* pygtk>=2.12
* lxml>=2.0

At least one of the following database connectors:

* pysqlite >= 2.3.2
* psycopg2 >= 2.0.5 
* mysql-python >= 1.2.1 

To use the formatter plugin you will also need to install an XSL->PDF renderer. For
a free renderer check out Apache FOP (>=.92beta) at 
http://xmlgraphics.apache.org/fop/


Installation:
-------------

Linux
~~~~~
1. Download the bauble.classic sources from either:
   * http://bauble.belizebotanic.org (and extract the archive to a directory)
   * git clone https://github.com/Bauble/bauble.classic.git
2. Change to the bauble directory containing the sources
3. (optional) make a virtual environment with --system-site-packages.
4. install system wide: pygtk
4. Type "python setup.py install" on the command line.
5. (optional) install a python DBMS wrapper (or use sqlite3).
6. To run Bauble type bauble on the command line.

Windows
~~~~~~~
1. Download the bauble-<version>-.exe file from 
   http://bauble.belizebotanic.org
2. Double click on the file when it finishes downloading.
3. Run Bauble from the Start menu.
