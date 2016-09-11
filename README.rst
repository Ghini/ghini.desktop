Ghini
======

.. image:: https://travis-ci.org/Ghini/ghini.desktop.svg
.. image:: https://img.shields.io/pypi/v/bauble.svg
.. image:: https://coveralls.io/repos/Ghini/ghini.desktop/badge.svg?branch=master&service=github

.. image:: https://hosted.weblate.org/widgets/bauble/es/svg-badge.svg
.. image:: https://hosted.weblate.org/widgets/bauble/pt_BR/svg-badge.svg
.. image:: https://hosted.weblate.org/widgets/bauble/fr/svg-badge.svg
.. image:: https://hosted.weblate.org/widgets/bauble/de/svg-badge.svg
.. image:: https://hosted.weblate.org/widgets/bauble/nl/svg-badge.svg
.. image:: https://hosted.weblate.org/widgets/bauble/it/svg-badge.svg
.. image:: https://hosted.weblate.org/widgets/bauble/cs/svg-badge.svg
.. image:: https://hosted.weblate.org/widgets/bauble/sv/svg-badge.svg

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

If you are in a hurry
---------------------

Download the following files and do the most logical thing with them. Or also read the rest.

* https://github.com/git-for-windows/git/releases/download/v2.10.0.windows.1/Git-2.10.0-32-bit.exe
* https://www.python.org/ftp/python/2.7.12/python-2.7.12.msi
* https://pypi.python.org/packages/2.7/l/lxml/lxml-3.6.0.win32-py2.7.exe
* http://www.stickpeople.com/projects/python/win-psycopg/2.6.1/psycopg2-2.6.1.win32-py2.7-pg9.4.4-release.exe
* http://ftp.gnome.org/pub/GNOME/binaries/win32/pygtk/2.24/pygtk-all-in-one-2.24.2.win32-py2.7.msi
* https://raw.githubusercontent.com/Ghini/ghini.desktop/ghini-1.0/scripts/devinstall.bat
* https://raw.githubusercontent.com/Ghini/ghini.desktop/ghini-1.0/scripts/ghini-update.bat


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
http://ghini.readthedocs.io. It includes detailed and up-to-date
installation procedures for different platforms, troubleshooting,
and a very thorough user manual.

For any kind of question, you can open an issue `here on github
<https://github.com/Ghini/ghini.desktop/issues/new>`_, or if you feel more
comfortable with it, you can start a thread on `our google group
<https://groups.google.com/forum/#!forum/bauble>`_.
