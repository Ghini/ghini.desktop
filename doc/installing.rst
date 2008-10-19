Installation
------------

Bauble will run on both Windows and Linux.  

Installing on Linux
===================

To install Bauble on Linux first requires that you install some of its
dependencies.  These include Python, GTK+, PyGTK, SQLAlchemy and
others. Fortunately as long as you have these four packages installed
then Bauble should be able to install the rest of its dependencies by
itself.

.. warning:: The following instructions details installing Bauble and
   its dependent packages system-wide.  It is possible that this could
   update some files on your computer that might affect other
   applications.

#.  Install `Python <http://www.python.org>`_ 2.4 or greater, `GTK+
    <http://www.gtk.org>`_ and `PyGTK <http://www.pygtk.org>`_ using
    your package manager.
#.  Download and extract the Bauble source package from
    http://bauble.belizebotanic.org/#download
#.  In the directory where you extracted Bauble run the following command:

    ``python ez_setup.py``

#.  Install `SQLAlchemy <http://www.sqlalchemy.org>`_ with the
    following command:

    ``easy_install -U SQLAlchemy>0.5``

#.  In the installation direction execute the following command:

    ``python setup.py install``

#.  If you would like to use the default `SQLite
    <http://sqlite.org/>`_ database or you don't know what this means
    then you can skip this step.  If you would like to use a database
    backend other than the default SQLite backend then you will also
    need to install a database connector.

    If you would like to use a `PostgreSQL <http://www.postgresql.org>`_
    database then install psycopg2 with the following commands:

    ``easy_install -U psycopg2``

#.  Run Bauble from the command line with the ``bauble`` command or in
    the application menu under *Education*


Installing on Windows
=====================

The Windows installer is a "batteries-included" installer.  It
installs everything needed to run Bauble.  If you would
like to install Bauble manually then you can download and install the
dependencies and then install Bauble from the source package.

.. note:: Bauble has been tested with and is known to work on Windows
   XP. Although it should work fine on other versions Windows it has
   not been thoroughly tested.

1. Download the latest windows installer from http://bauble.belizebotanic.org/#download.
2. Double-click on the installation file you just downloaded.
3. Run Bauble from the Windows Start Menu under Bauble.


If you would like to generate and print PDF reports using Bauble's
default report generator then you will need to download and install
`Apache FOP <http://xmlgraphics.apache.org/fop/>`_. After extracting the FOP archive you will need to include
the directory you extracted to in your PATH.

.. rubric:: Next...

:ref:`connecting`.


