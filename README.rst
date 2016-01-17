Ghini
======

.. image:: https://travis-ci.org/Ghini/ghini.desktop.svg
.. image:: https://img.shields.io/pypi/v/ghini.svg
.. image:: https://coveralls.io/repos/Ghini/ghini.desktop/badge.svg?branch=master&service=github
  :target: https://coveralls.io/github/Ghini/ghini.desktop?branch=master

* **ghini-1.0** is stable - use this; 
* **ghini-1.1** is testing - feedback is welcome;
* **master** is unstable - do not open issues on this one; 

what is Ghini (desktop)
------------------------

Ghini was born as Bauble at the Belize Botanic Gardens, At its heart it is a
framework for creating database applications.  In their distributed form
Bauble and Ghini are applications to manage plant records and specifically
living collections.  Either as Ghini or Bauble, the software is used among
others by Belize Botanic Gardens, the Jardín Botánico de Quito, the Mackay
Regional Botanical Garden, to manage their live collections.  Included by
default is RBG Kew's Family and Genera list from Vascular Plant Families and
Genera compiled by R. K. Brummitt and published by the Royal Botanic
Gardens, Kew in 1992 used by permission from RBG Kew.

All code contained as part of the Bauble package is licenced under
the GNU GPLv2+.

Terms and Names
---------------

This file describes 'ghini.desktop', a standalone application. Until 2015
'ghini.desktop' was known as 'Bauble/bauble.classic'. Ghini and Bauble are
two github organizations. The current maintainer of Ghini forked development
from Bauble into Ghini mostly because of his difficulty in pronouncing
"bauble" and in explaining why the software was named that way.

Luca Ghini was the founder of the botanical garden of Pisa, and Pisa is the
place where the current maintainer Mario Frasca has completed his studies in
computer science.

Within the Ghini organization, you will find 'ghini.desktop', this program,
'ghini.github.io', the sources for the ghini website, 'ghini.geoweb', a very
very alpha quality thing which still did not formalize.

Just as Bauble's flagship was bauble.classic, Ghini's flagship is ghini.desktop.

Requirements
------------
ghini.desktop requires the following packages to run.

* Python (travis-ci checks Bauble against Python 2.6 and 2.7)
* SQLAlchemy (>= 0.6.0, at least up to 1.0.3)
* pygtk (>= 2.12, at least up to 2.24)
* PyGObject (>= 2.11.1, at least up to 2.28.6)
* lxml (>= 2.0)

each of the following database connectors is optional, but at least one is needed:

* pysqlite >= 2.3.2
* psycopg2 >= 2.0.5 
* mysql-python >= 1.2.1 

To use the formatter plugin you will also need to install an
XSL->PDF renderer. For a free renderer check out Apache FOP
(>=.92beta) at http://xmlgraphics.apache.org/fop/

Further info
------------

The complete documentation for ghini.desktop is to be found at
http://bauble.readthedocs.org. It includes detailed and up-to-date
installation procedures for different platforms, troubleshooting,
and a very thorough user manual.

For any kind of question, you can open an issue `here on github
<https://github.com/Ghini/ghini.desktop/issues/new>`_, or if you feel more
comfortable with it, you can start a thread on `our google group
<https://groups.google.com/forum/#!forum/bauble>`_.
