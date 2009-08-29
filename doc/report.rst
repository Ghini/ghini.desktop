Generating reports
==================

Using the Mako Report Formatter
-------------------------------

The Mako report formatter uses the Mako template language for
generating reports. More information about Mako and it's language can
be found at `makotemplates.org <http://www.makotemplates.org>`_.

The Mako templating system should already be installed on your
computerif Bauble is installed.

Creating reports with Mako is similar in the way that you would create
a web page from a template.  It is much simpler than the XSL
Formatter(see below) and should be relatively easy to create template
for anyone with a little but of programming experience.

The template generator will use the same file extension as the
template which should indicate the type of output the template with
create.  For example, to generate an HTML page from your template you
should name the template something like `report.html`.  If the template
will generate a comma seperated value file you should name the
template `report.csv`.

The template will receive a variable called `values` which will
contain the list of values in the current search.


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

1. Download the latest Apache FOP.  The current version when this was
   written is 0.95 and can be downloaded `here
   <http://www.apache.org/dist/xmlgraphics/fop/binaries/fop-0.95-bin.zip>`_.

2. Extract the FOP archive to the C drive, i.e. C:\

3. Add the directory where you extracted FOP to the PATH environment
   variable.  If you extract FOP to C:\ add c:\fop-0.95 to the path.
   For more information about setting environment variables and the
   PATH in Windows XP go `here
   <http://vlaurie.com/computers2/Articles/environment.htm>`_.
