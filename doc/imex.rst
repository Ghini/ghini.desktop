Importing and Exporting Data
============================

Although Ghini can be extended through plugins to support alternate
import and export formats, by default it can only import and export
comma seperated values files or CSV.

There is some support for exporting to the Access for Biological
Collections Data it is limited.

There is also limited support for exporting to an XML format that more
or less reflects exactly the tables and row of the database.

Exporting ABCD and XML will not be covered here.

.. warning:: Importing files will most likely destroy any data you
  have in the database so make sure you have backed up your data.

Importing from CSV
------------------
In general it is best to only import CSV files into Ghini that were
previously exported from Ghini. It is possible to import any CSV file
but that is more advanced that this doc will cover.

To import CSV files into Ghini select
:menuselection:`Tools-->Export-->Comma Seperated Values` from the
menu.

After clicking OK on the dialog that ask if you are sure you know what
you're doing a file chooser will open.  In the file chooser select the
files you want to import.  


Exporting to CSV
----------------

To export the Ghini data to CSV select
:menuselection:`Tools-->Export-->Comma Seperated Values` from the menu.

This tool will ask you to select a directory to export the CSV data.
All of the tables in Ghini will be exported to files in the format
tablename.txt where tablename is the name of the table where the data
was exported from.

Importing from JSON
-------------------

This is *the* way to import data into an existing database, without
destroying previous content. A typical example of this functionality would
be importing your digital collection into a fresh, just initialized Ghini
database. Converting a database into bauble json interchange format is
beyond the scope of this manual, please contact one of the authors if you
need any further help.

Using the Ghini json interchange format, you can import data which you have
exported from a different Ghini installation.

Exporting to JSON
-----------------

This feature is still under development.

.. image:: images/screenshots/export-to-json.png

when you activate this export tool, you are given the choice to specify what
to export. You can use the current selection to limit the span of the
export, or you can start at the complete content of a domain, to be chosen
among Species, Accession, Plant.  

Exporting *Species* will only export the complete taxonomic information in
your database. *Accession* will export all your accessions plus all the
taxonomic information it refers to: unreferred to taxa will not be
exported. *Plant* will export all living plants (some accession might not be
included), all referred to locations and taxa.

