not-so-brief list of highlights, meant to wetten your appetite.
---------------------------------------------------------------

Whey you first start Bauble, and connect to a database, Bauble will
initialize the database not only with all tables it needs to run, but it
will also populate the taxon tables for ranks family and genus, using the
data from the “RBG Kew's Family and Genera list from Vascular Plant Families
and Genera compiled by R. K. Brummitt and published by the Royal Botanic
Gardens, Kew in 1992”.  In 2015 we have reviewed the data regarding the
Orchidaceae, using “Tropicos, botanical information system at the Missouri
Botanical Garden - www.tropicos.org” as a source.

Bauble will let you import any data you put in an intermediate json
format. What you import will complete what you already have in the
database. If you need help, you can ask some Bauble professional to help you
transform your data into Bauble's intermediate json format.

Bauble will allow you define synonyms for species, genera, families. Also
this information can be represented in its intermediate json format and be
imported in an existing Bauble database.

Bauble implements the concept of 'accession', intermediate between physical
plants and abstract taxon. Each accession can associate a plant to different
taxa, if two taxonomists do not agree on the identification: each taxonomist
can have their say and do not need overwrite each other's work. All
verifications can be found back in the database, with timestamp and
signature.

Bauble allows you associate pictures to physical plants, this can help
recognize the plant in case a sticker is lost, or help taxonomic
identification if a taxonomist is not available at all times.

Bauble will let you export a report in whatever textual format you need. It
uses a powerful templating engine named 'mako', which will allow you export
the data in a selection to whatever format you need. Once installed, a
couple of examples are available in the mako subdirectory.

You can associate notes to plants, accessions, species, .... Notes can be
categorized and used in searches or reports.

Management of plant locations.

All changes in the database is stored in the database, as history log. All
changes are 'signed' and time-stamped.  Bauble makes it easy to retrieve the
list of all changes in the last working day.

Bauble allows you search the database using keywords, like the name of the
location or a genus name, or you can write more complex queries, which do
not reach the complexity of SQL but allow you a decent level of detail
localizing your data.

Bauble is not a database management system, so it does not reinvent the
wheel. It works storing its data in a SQL database, and it will connect to
any database management systen which accepts a SQLAlchemy connector. This
means any reasonably modern database system and includes MySQL, PostgreSQL,
Oracle. It can also work with sqlite, which, for single user purposes is
quite sufficient and efficient. If you connect Bauble to a real database
system, you might think of making the database part of a LAMP system
(Linux-Apache-MySQL-Php) and include your live data on your institution web
site.

The program was born in English and all its technical and user documentation
is still only in that language, but the program itself has been translated
and can be used in various other languages, including Spanish (86%),
Portuguese (100%), French (42%), to name some Southern American languages,
but also Swedish (100%) and Tchech (100%).

It is an easy and linear process installing Bauble on Windows, it will not
take longer than 10 minutes. Bauble was born on Linux and installing it on
ubuntu, fedora or debian is also rather simple. It has been recently
successfully tested on MacOSX 10.9. 

The installation process will produce an updatable installation, where
updating it will take less than one minute. Depending on the amount of
feedback we receive, we will produce updates every few days or once in a
while. 

Bauble is continuously and extensively unit tested, something that makes
regression of functionality close to impossible. Every update is
automatically quality checked, on the Travis Continuous Integration
service. Integration of TravisCI with the github platform will make it
difficult for us to release anything which has a single failing unit test.

Most changes and additions we make will come with some extra unit test,
which defines the behaviour and will make any undesired change easily
visible.

Bauble is extensible through plugins and can be customized to suit the needs
of the institution.
