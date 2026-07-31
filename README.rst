Ghini
======

.. |travis| image:: https://github.com/Ghini/ghini.desktop/actions/workflows/python-app.yml/badge.svg
.. |pypi| image:: https://img.shields.io/pypi/v/ghini.desktop.svg
.. |coveralls| image:: https://coveralls.io/repos/Ghini/ghini.desktop/badge.svg?branch=ghini-3.1-dev&service=github

=========== ======== ============
test suite  pypi     coveralls
=========== ======== ============
|travis|    |pypi|   |coveralls|
=========== ======== ============

=========== =========== =========== =========== =========== =========== =========== =========== 
Spanish     Portuguese  French      Ukrainian   Hungarian   Italian     Tchech      Dutch
=========== =========== =========== =========== =========== =========== =========== ===========
|trans-es|  |trans-pt|  |trans-fr|  |trans-uk|  |trans-hu|  |trans-it|  |trans-cs|  |trans-nl|  
=========== =========== =========== =========== =========== =========== =========== ===========

.. |trans-es| image:: https://hosted.weblate.org/widgets/ghini/es/svg-badge.svg
.. |trans-pt| image:: https://hosted.weblate.org/widgets/ghini/pt/svg-badge.svg
.. |trans-fr| image:: https://hosted.weblate.org/widgets/ghini/fr/svg-badge.svg
.. |trans-uk| image:: https://hosted.weblate.org/widgets/ghini/uk/svg-badge.svg
.. |trans-hu| image:: https://hosted.weblate.org/widgets/ghini/hu/svg-badge.svg
.. |trans-it| image:: https://hosted.weblate.org/widgets/ghini/it/svg-badge.svg
.. |trans-cs| image:: https://hosted.weblate.org/widgets/ghini/cs/svg-badge.svg
.. |trans-nl| image:: https://hosted.weblate.org/widgets/ghini/nl/svg-badge.svg

what is Ghini (desktop)
-----------------------

Ghini (pronounced "Ghee-nee") is a database application for managing
botanical collections, in particular living collections.

Ghini was originally developed as Bauble at the Belize Botanic Gardens.
At its heart, however, it is a framework for creating database
applications. Bauble and Ghini have been used to manage plant records
and, specifically, living collections.

Ghini and its predecessor Bauble have been developed with the support
of botanical institutions in several countries. We are grateful to the
Belize Botanic Gardens, the University of British Columbia, and the
Mackay Regional Botanic Garden for their early support and interest;
to the Jardín Botánico de Quito and the Botanische Tuin van de
Universiteit Utrecht for their important taxonomic support; and to all
the individuals who have given their encouragement and support, too
many to mention without risking forgetting others.

Some of these institutions no longer use Ghini, while others contributed
to the project without deploying it in routine work. Their contribution
to the project nevertheless remains part of its history.

History and names
-----------------

Until 2015, 'ghini.desktop' was known as 'Bauble/bauble.classic'.
Development was subsequently moved from the Bauble organisation to the
Ghini organisation, and the application was renamed Ghini.

The name honours Luca Ghini (1490–1556), regarded as the inventor of the
herbarium. Although none of his books survived, his students became some
of the most influential botanists of the Renaissance. He founded the
botanical garden of Pisa, where the current maintainer, Mario Frasca,
later studied computer science.

The original name, Bauble, was retained for many years. It was eventually
replaced in part because the word is difficult to pronounce and spell
consistently for speakers of several languages, and because its meaning
has no particular connection with botanical collections.

The Ghini family
----------------

Within the Ghini organisation you will find:

* 'ghini.desktop', this program;
* 'ghini.pocket', a small Android database viewer intended to let you
  carry your database in your pocket;
* 'ghini.github.io', the sources for the Ghini website;
* 'ghini.web', showcased at http://gardens.ghini.me; and
* 'ghini.tour', a collection of settings for building audio guides to
  gardens.

The Ghini family has also adopted two ODK products,
`Collect <https://github.com/opendatakit/collect>`_ and
`Aggregate <https://github.com/opendatakit/aggregate>`_, which help
users add or correct information in the database. They are not part of
the Ghini organisation, but are integrated members of the Ghini family.

Data and licensing
------------------

Included by default is RBG Kew's Family and Genera list from *Vascular
Plant Families and Genera*, compiled by R. K. Brummitt and published by
the Royal Botanic Gardens, Kew, in 1992, used by permission from RBG Kew.

All code contained in the Ghini package is licensed under the GNU GPLv2+.

|ghini-family|

Just as Bauble's flagship was bauble.classic, Ghini's flagship is ghini.desktop.

.. |ghini-family| image:: https://github.com/Ghini/ghini.desktop/raw/ghini-1.0-dev/doc/images/ghini-family.png

Windows, in a hurry
---------------------

Are you a Windows user and are in a hurry to run ghini.desktop? Download and install in the given order
`Git <https://github.com/git-for-windows/git/releases/download/v2.10.0.windows.1/Git-2.10.0-32-bit.exe>`_, `Python <https://www.python.org/ftp/python/2.7.12/python-2.7.12.msi>`_, `pylxml <https://pypi.python.org/packages/2.7/l/lxml/lxml-3.6.0.win32-py2.7.exe>`_, `psycopg <http://www.stickpeople.com/projects/python/win-psycopg/2.6.1/psycopg2-2.6.1.win32-py2.7-pg9.4.4-release.exe>`_, `pygtk <http://ftp.gnome.org/pub/GNOME/binaries/win32/pygtk/2.24/pygtk-all-in-one-2.24.2.win32-py2.7.msi>`_, 
then download and run `devinstall.bat <https://raw.githubusercontent.com/Ghini/ghini.desktop/ghini-1.0/scripts/devinstall.bat>`_ and keep `ghini-update.bat <https://raw.githubusercontent.com/Ghini/ghini.desktop/ghini-1.0/scripts/ghini-update.bat>`_ for later reference.

Or also read the rest.

Linux Docker development
------------------------

For current Linux development, use the Ubuntu 24.04 Docker workflow documented
in ``doc/docker-development.md``. It provides deterministic Python dependency
locks, GTK 3.24/PyGObject runtime packages, X11 GUI launching, VS Code tasks,
debugpy support, formatting, pytest, and warning-gated migration checks.

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
