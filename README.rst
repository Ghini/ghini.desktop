Ghini
======

* **ghini-1.0** is stable - use this; 
* **ghini-1.1** is testing - feedback is welcome;
* **master** is unstable - do not open issues on this one; 

.. |travis| image:: https://travis-ci.org/Ghini/ghini.desktop.svg?branch=ghini-1.0-dev
.. |pypi| image:: https://img.shields.io/pypi/v/bauble.svg
.. |coveralls| image:: https://coveralls.io/repos/Ghini/ghini.desktop/badge.svg?branch=ghini-1.0-dev&service=github

======== ======== ============
travis   pypi     coveralls
======== ======== ============
|travis| |pypi|   |coveralls|
======== ======== ============

=========== =========== =========== =========== =========== =========== =========== =========== 
Spanish     Portuguese  French      German      Dutch       Italian     Tchech      Sweedish
=========== =========== =========== =========== =========== =========== =========== ===========
|trans-es|  |trans-pt|  |trans-fr|  |trans-de|  |trans-nl|  |trans-it|  |trans-cs|  |trans-sv|  
=========== =========== =========== =========== =========== =========== =========== ===========

.. |trans-es| image:: https://hosted.weblate.org/widgets/ghini/es/svg-badge.svg
.. |trans-pt| image:: https://hosted.weblate.org/widgets/ghini/pt_BR/svg-badge.svg
.. |trans-fr| image:: https://hosted.weblate.org/widgets/ghini/fr/svg-badge.svg
.. |trans-de| image:: https://hosted.weblate.org/widgets/ghini/de/svg-badge.svg
.. |trans-nl| image:: https://hosted.weblate.org/widgets/ghini/nl/svg-badge.svg
.. |trans-it| image:: https://hosted.weblate.org/widgets/ghini/it/svg-badge.svg
.. |trans-cs| image:: https://hosted.weblate.org/widgets/ghini/cs/svg-badge.svg
.. |trans-sv| image:: https://hosted.weblate.org/widgets/ghini/sv/svg-badge.svg

what is Ghini (desktop)
------------------------

Ghini was born as Bauble at the Belize Botanic Gardens, At its heart it is a
framework for creating database applications.  In its distributed form Ghini
is an application to manage plant records and specifically living
collections.  Either as Ghini or Bauble, the software is used among others
by Belize Botanic Gardens, the Jardín Botánico de Quito, the Mackay Regional
Botanical Garden, to manage their live collections.  Included by default is
RBG Kew's Family and Genera list from Vascular Plant Families and Genera
compiled by R. K. Brummitt and published by the Royal Botanic Gardens, Kew
in 1992 used by permission from RBG Kew.

All code contained as part of the Bauble package is licenced under
the GNU GPLv2+.

Terms and Names
---------------

When it was born, around 2004, Bauble was a desktop application, and the
name Bauble used to indicate the software and the organization behind it.
More recently the original author of Bauble is rewriting Bauble as a web
application and with the possibility to install it as a desktop program.  In
order to avoid confusion between the new ``bauble.web`` program, its
perspective ``bauble.desktop`` desktop version, the stable and still current
desktop application ``bauble.classic`` and its corresponding node.js web
based prototype ``mfrasca/ghini``, we have split development in two separate
organizations: Ghini and Bauble.

please check the Bauble site for further details about it.


The name _Ghini_ is to honour Luca Ghini, the founder of the botanical
garden of Pisa, and Pisa is the place where the current maintainer Mario
Frasca has completed his studies in computer science.

Within the Ghini organization, you will find 'ghini.desktop', this program,
'ghini.pocket', a tiny android database viewer meant to help you take your
database in your pocket, 'ghini.github.io', the sources for the ghini
website, 'ghini.web', showcased at http://gardens.ghini.me, and ghini.tour,
a collection of settings for building audio guides to gardens.

|ghini-family|

Just as Bauble's flagship was bauble.classic, Ghini's flagship is ghini.desktop.

.. |ghini-family| image:: https://github.com/Ghini/ghini.desktop/raw/ghini-1.0-dev/doc/images/ghini-family.png

Windows, in a hurry
---------------------

Are you a Windows user and are in a hurry to run ghini.desktop? Download and install in the given order
`Git <https://github.com/git-for-windows/git/releases/download/v2.10.0.windows.1/Git-2.10.0-32-bit.exe>`_, `Python <https://www.python.org/ftp/python/2.7.12/python-2.7.12.msi>`_, `pylxml <https://pypi.python.org/packages/2.7/l/lxml/lxml-3.6.0.win32-py2.7.exe>`_, `psycopg <http://www.stickpeople.com/projects/python/win-psycopg/2.6.1/psycopg2-2.6.1.win32-py2.7-pg9.4.4-release.exe>`_, `pygtk <http://ftp.gnome.org/pub/GNOME/binaries/win32/pygtk/2.24/pygtk-all-in-one-2.24.2.win32-py2.7.msi>`_, 
then download and run `devinstall.bat <https://raw.githubusercontent.com/Ghini/ghini.desktop/ghini-1.0/scripts/devinstall.bat>`_ and keep `ghini-update.bat <https://raw.githubusercontent.com/Ghini/ghini.desktop/ghini-1.0/scripts/ghini-update.bat>`_ for later reference.

Or also read the rest.

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
