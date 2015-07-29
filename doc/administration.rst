Administration
--------------

If you are using a real DBMS to hold your botanic data, then you need do
something about database administration. While database adnimistration is
far beyond the scope of this document, we make our users aware of it.

SQLite
======

SQLite is not what one would consider a real DBMS: each SQLite database is
just in one file. Make safety copies and you will be fine. If you don't know
where to look for your database files, consider that, per default, bauble
puts its data in the ``~/.bauble/`` directory (in Windows it is somewhere in
your ``AppData`` directory).

MySQL
=====

Please refer to the official documentation.

PostgreSQL
==========

Please refer to the official documentation. A very thorough discussion of
your backup options starts at `chapter_24`_.

.. _chapter_24: http://www.postgresql.org/docs/9.1/static/backup.html
