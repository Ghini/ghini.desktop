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

    For Bauble 0.9:
    ``easy_install -U 'SQLAlchemy>0.5'``
    
    For Bauble 0.8
    ``easy_install -U 'SQLAlchemy<0.5b1'``

#.  In the installation direction execute the following command:

    ``python setup.py install``

    If this doesn't complete successfully see :ref:`troubleshoot_install`.

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

.. rubric:: Next...

:ref:`connecting`.

Installing on Windows
=====================

The Windows installer is a "batteries-included" installer.  It
installs everything needed to run Bauble.  If you would
like to install Bauble manually then you can download and install the
dependencies and then install Bauble from the source package.

.. note:: Bauble has been tested with and is known to work on Windows
   XP. Although it should work fine on other versions Windows it has
   not been thoroughly tested.

#.  Download the latest windows installer from http://bauble.belizebotanic.org/#download.
#.  Double-click on the installation file you just downloaded.
#.  Run Bauble from the Windows Start Menu under Bauble.


If you would like to generate and print PDF reports using Bauble's
default report generator then you will need to download and install
`Apache FOP <http://xmlgraphics.apache.org/fop/>`_. After extracting the FOP archive you will need to include
the directory you extracted to in your PATH.

.. rubric:: Next...

:ref:`connecting`.

.. _troubleshoot_install:

Troubleshooting the Install
===========================

#.  What are the packages that are installed by Bauble:

    The following packages are required by Bauble

    	*  SQLAlchemy
    	*  simplejson
    	*  lxml

    The following packages are optional:

    	* Mako - required by the template based report generator
    	* gdata - required by the Picassa photos InfoBox


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

    Unzip it and run `python setup.py install` in the folder you unzip it to.

.. rubric:: Next...

:ref:`connecting`.



