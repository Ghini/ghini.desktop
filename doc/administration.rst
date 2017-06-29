Database Administration
--------------------------

If you are using a real DBMS to hold your botanic data, then you need do
something about database administration. While database administration is
far beyond the scope of this document, we make our users aware of it.

SQLite
======

SQLite is not what one would consider a real DBMS: each SQLite database is
just in one file. Make safety copies and you will be fine. If you don't know
where to look for your database files, consider that, per default, bauble
puts its data in the ``~/.bauble/`` directory.

In Windows it is somewhere in your ``AppData`` directory, most likely in
``AppData\Roaming\Bauble``. Do keep in mind that Windows does its best to
hide the ``AppData`` directory structure to normal users. 

The fastest way to open it is with the file explorer: type ``%APPDATA%`` and
hit enter.

MySQL
=====

Please refer to the official documentation.

PostgreSQL
==========

Please refer to the official documentation. A very thorough discussion of
your backup options starts at `chapter_24`_.

.. _chapter_24: http://www.postgresql.org/docs/9.1/static/backup.html

Ghini Configuration
----------------------

Ghini uses a configuration file to store values across invocations. This
file is associated to a user account and every user will have their own
configuration file.

To review the content of the Ghini configuration file, type ``:prefs`` in
the text entry area where you normally type your searches, then hit enter.

You normally do not need tweaking the configuration file, but you can do so
with a normal text editor program. Ghini configuration file is at the
default location for SQLite databases.

Reporting Errors
----------------------

Should you notice anything unexpected in Ghini's behaviour, please consider
filing an issue on the Ghini development site.

Ghini development site can be accessed via the Help menu.
