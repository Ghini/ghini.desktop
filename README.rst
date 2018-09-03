Ghini
======

.. image:: https://travis-ci.org/Ghini/ghini.desktop.svg
.. image:: https://img.shields.io/pypi/v/ghini.svg
.. image:: https://coveralls.io/repos/Ghini/ghini.desktop/badge.svg?branch=master&service=github
  :target: https://coveralls.io/github/Ghini/ghini.desktop?branch=master

* **ghini-1.0** is stable - use this; 
* **ghini-1.1** is testing - feedback is welcome;
* **master** is unstable - do not open issues on this one; 

What is Ghini (desktop)
------------------------

Ghini was born as Bauble at the Belize Botanic Gardens, At its heart it is a
framework for creating database applications. In its distributed form Ghini
is an application to manage plant records and specifically living
collections. Either as Ghini or Bauble, the software is used among others
by BBG, the Jardín Botánico de Quito and the Mackay Regional
Botanical Garden to manage their live collections. Included by default is
RBG Kew's Family and Genera list from Vascular Plant Families and Genera
compiled by R. K. Brummitt and published by the Royal Botanic Gardens, Kew
in 1992 used by permission from RBG Kew.

All code contained as part of the Bauble package is licenced under
the GNU GPLv3+.

Terms and Names
---------------

At the time of its inception around 2004, Bauble was a desktop application,
namely indicating the software and the organization behind it.
More recently the original author of Bauble is rewriting Bauble as a web
application, with the possibility of installing it as a desktop program.
In order to avoid confusion between the new ``bauble.web`` program, its
perspective ``bauble.desktop`` desktop version, the stable and still current
desktop application ``bauble.classic`` along with corresponding Node.js web
based prototype ``mfrasca/ghini``, development split into two separate
organizations: Ghini and Bauble.

The Bauble website describes this in further detail.

Within the Ghini organization

- ``ghini.desktop`` is the new name of the stable and well established
  software previously distributed as ``bauble.classic``. ``ghini.desktop``.
  As Ghini's flagship, it is a GTK+ desktop application, described
  here.
- ``ghini.web`` is the name of the geographic and web interface to a
  ``ghini.desktop`` PostgreSQL database.
- ``ghini.github.io`` contains the sources for the Ghini website.

The name _Ghini_ honours Luca Ghini, the founder of the botanical
garden of Pisa, the place where the current maintainer Mario
Frasca completed his computer science studies.

Requirements
------------
ghini.desktop requires the following packages to run.

* Python (travis-ci checks Bauble against Python 2.6 and 2.7)
* SQLAlchemy (>= 0.6.0, at least up to 1.0.3)
* pygtk (>= 2.12, at least up to 2.24)
* PyGObject (>= 2.11.1, at least up to 2.28.6)
* lxml (>= 2.0)

One of the following database connectors is needed:

* pysqlite >= 2.3.2
* psycopg2 >= 2.0.5 
* mysql-python >= 1.2.1 

To use the formatting plugin you will also need to install an
XSL->PDF renderer. For a libre renderer, check out Apache FOP
at https://xmlgraphics.apache.org/fop/

Further info
------------

The complete documentation for ghini.desktop is to be found at
http://ghini.readthedocs.org. It includes detailed and up-to-date
installation procedures for different platforms, troubleshooting,
and a very thorough user-manual.

For any kind of question, you can open an issue `here on GitHub
<https://github.com/Ghini/ghini.desktop/issues/new>`_, or if you feel more
comfortable with it, start a thread on `our Google group
<https://groups.google.com/forum/#!forum/bauble>`_.
