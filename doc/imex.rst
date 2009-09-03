Importing and Exporting Data
============================

Although Bauble can be extended through plugins to support alternate
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
In general it is best to only import CSV files into Bauble that were
previously exported from Bauble. It is possible to import any CSV file
but that is more advanced that this doc will cover.

To import CSV files into Bauble select
:menuselection:`Tools-->Export-->Comma Seperated Values` from the
menu.

After clicking OK on the dialog that ask if you are sure you know what
you're doing a file chooser will open.  In the file chooser select the
files you want to import.  


Exporting to CSV
----------------

To export the Bauble data to CSV select
:menuselection:`Tools-->Export-->Comma Seperated Values` from the menu.

This tool will ask you to select a directory to export the CSV data.
All of the tables in Bauble will be exported to files in the format
tablename.txt where tablename is the name of the table where the data
was exported from.
