Generating reports
==================

A database without exporting facilities is of little use.  Ghini lets you
export your data in table format (open them in your spreadsheet editor of
choice), as labels (to be printed or engraved), as html pages or pdf or
postscript documents.

The Report Tool
---------------------

You activate the Report Tool from the main menu: :menuselection:`Tools-->Report`.  The Report Tools acts on
a selection, so first select something, then start the Report Tool.

.. admonition::  Report on the whole collection.
   :class: toggle
           
      To produce a report on your whole plant collection, a shortcut would be from the home screen, to click
      on the ``Families: in use`` cell.

      If your focus is more on the garden location than on taxonomy and accessions, you would click on the
      ``Locations: total`` cell.

Reports are produced by a report engine, making use of a report template.  Ghini relies upon two different
report engines (Mako & XSL), and offers several report templates, meant as usable examples.

Choose the report you need, specify parameters if required, and produce the report.  Ghini will open the
report in the associated application.

Configuring report templates, that's a task for who installs and configures ghini at your institution.
Basically, you create a template name, indicating the report engine and specifying the template.  Configured
templates are static, once configured you are not expected to alter them.  Only the special ``**scratch**``
template can be modified on the fly.

The remainder of this page provides technical information and links regarding the formatter engines, and
gives hints on writing report templates.  Writing templates comes very close to writing a computer program,
and that's beyond the scope of this manual, but we have hints that will definitely be useful to the
interested reader.


Using the Mako Report Formatter
-------------------------------

The Mako report formatter uses the Mako template language for
generating reports. More information about Mako and its language can
be found at `makotemplates.org <http://www.makotemplates.org>`_.

The Mako templating system should already be installed on your
computer if Ghini is installed.

Creating reports with Mako is similar in the way that you would create
a web page from a template.  It is much simpler than the XSL
Formatter(see below) and should be relatively easy to create template
for anyone with a little but of programming experience.

The template generator will use the same file extension as the
template which should indicate the type of output the template with
create.  For example, to generate an HTML page from your template you
should name the template something like `report.html`.  If the template
will generate a comma separated value file you should name the
template `report.csv`.

The template will receive a variable called `values` which will
contain the list of values in the current search.

The type of each value in `values` will be the same as the search
domain used in the search query.  For more information on search
domains see :ref:`search-domains`.

If the query does not have a search domain then the values could all
be of a different type and the Mako template should prepared to handle
them.


Using the XSL Report Formatter
------------------------------

The XSL report formatter requires an XSL to PDF renderer to
convert the data to a PDF file. Apache FOP is is a free and
open-source XSL->PDF renderer and is recommended.

If using Linux, Apache FOP should be installable using your package
manager.  On Debian/Ubuntu it is installable as ``fop`` in Synaptic or
using the following command::

   apt-get install fop


Installing Apache FOP on Windows
................................

You have two options for installing FOP on Windows. The easiest way is
to download the prebuilt `ApacheFOP-0.95-1-setup.exe <http://code.google.com/p/apache-fop-installer/downloads/detail?name=ApacheFOP-0.95-1-setup.exe&can=2&q=#makechanges>`_ installer.

Alternatively you can download the `archive
<http://www.apache.org/dist/xmlgraphics/fop/binaries/>`_.  After
extracting the archive you must add the directory you extracted the
archive to to your PATH environment variable.


