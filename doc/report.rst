.. |ghini.pocket| replace:: :py:mod:`ghini.pocket`
.. |ghini.desktop| replace:: :py:mod:`ghini.desktop`

Generating reports
==================

A database without exporting facilities is of little use.  Ghini lets you
export your data in table format (open them in your spreadsheet editor of
choice), as labels (to be printed or engraved), as html pages or pdf or
postscript documents.

The Report Tools
---------------------

Ghini has two Report Tools, one based on templates, and a quick solution for flat file production.  The
``Template`` based tool is as flexible as a programming language can be; the ``Quick CSV`` tool shares much
of its user interface with the query builder.

You activate the Report Tools from the main menu: :menuselection:`Tools-->Report`, then choose either ``From
Template``, or ``Quick CSV``.  Both Report Tools act on the current result in the results view, so you first
select something, then start the Report Tool.

.. image:: images/report-menu.png

.. admonition::  Selecting the whole collection.
   :class: toggle

      If you want to produce a report regarding your whole collection, you can do it from at least two
      points of view: you may want all the ``Species``, or you may want all the ``Locations``.

      A handy shortcut to get all your species in the selection, go to the home screen, then click on the
      ``Families: in use`` cell.

      If your focus is more on the garden location than on taxonomy and accessions, you would click on the
      ``Locations: total`` cell.

      The `Quick CSV` report tool can act on the whole collection, regardless the content of
      the results view.

Template Based Reports
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Activate the :menuselection:`Tools-->Report-->From Template` and you get the following dialog
box (fields may be filled in differently):

.. image:: images/report-from-template-dialog.png

You have already selected your objects in the main window, you now here select the report template you need,
and press on ``Execute`` to produce your report.  Ghini will open the report in the corresponding
application, if installed and enabled..

Ghini comes with a few sample package-templates, and it lets you install your own user-templates.

.. admonition::  package-templates vs. user-templates
   :class: toggle

      Package-templates are integral part of the installation and are overwritten every time you update your
      installation.  User-templates are in your custom data, together with your ghini configuration, which
      is the default location for your sqlite databases and your plant pictures.  User-templates are
      persistent as long as you stay in the same production line (say, ghini-3.1).

      To install a new template as a user-template, click on ``Add``, choose the file that contains your
      template, and type the name by which you want to install it.  |ghini.desktop| will copy it to your
      ghini user directory.  Installed templates are static, once configured you are not expected to alter
      them.  You can delete installed user templates (select it, then click on ``Remove``), or you can
      overrule a package-template by installing your own template using an already taken package-template
      name.

Choosing a template implies the choice of a template language.  |ghini.desktop| supports three template
languages: Jinja2, Mako and XSL.  There is only one formatting engine handling the Jinja2 template language,
and the same goes for Mako.  During installation you indicated which of the several XSL formatting engines
you wanted to have, if any.

Expand the ``Details`` section to see some information about the selected formatter template.

.. image:: images/report-from-template-dialog-details.png

The formatter engine combines selection and formatter template to produce a report.  Each formatter template
indicates the iteration domain, that is what kind of collection objects you focus on, in your report.  In
the above example, we are using Jinja2 to report about individual plants, producing —per plant— a postscript
label with a QR code.

Expand the ``Options`` section to see what extra parameters your selected template may require or expect.

.. image:: images/report-from-template-dialog-options.png

In the above example, the plant-labelling formatter lets you override the selection, and produce a set of
labels in your preferred format, and in a given range.

In general: choose the report you need, specify parameters if required, and produce the report.  Ghini will
open the report in the associated application.

This is as far as generic information can go.  Formatter templates can be very specific, and vary broadly
from each other, most of them are small pieces of software themselves.

Template-less Reports (Quick CSV)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Activate the :menuselection:`Tools-->Report-->Quick CSV` and you get the following dialog box:

.. image:: images/report-quick-csv-dialog.png

Start from the top and work your way to the bottom: decide whether you work on the selection or the whole
collection, choose the iteration domain, select the properties to include in the report, drag and drop them
in the list to get them in the correct order, choose the destination file, execute.  Ghini will open the
report in your preferred spreadsheet program.

Do you really need any further documentation?  If anything isn't clear then please ask.

Technical information
----------------------------------

The remainder of this page provides technical information and links regarding the formatter engines, and
gives hints on writing report templates.  Writing templates comes very close to writing a computer program,
and that's beyond the scope of this manual, but we have hints that will definitely be useful to the
interested reader.


Working with Templates Languages
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Common information
................................................

Creating reports with Mako and Jinja2 is similar in the way that you would create a web page from a
template.  Both Mako and Jinja2 are mostly used for dynamic creation of static web pages.  This is much
simpler than the XSL Formatter(see below) and should be relatively easy to create template for anyone with a
little but of programming experience.

Ghini instructs the template generator to use the same file extension as the template, stripping the
optional but advised ``.mako`` / ``.jj2`` trailing part.  The template name should indicate the type of
output produced by the template, the trailing ``.mako`` / ``.jj2`` prevents you from mistaking a template
for an output file.  For example, to generate an HTML page from your template you would name the template
something like ``report.html.mako`` if using Mako, or ``report.html.jj2`` if using Jinja2.  Similarly, you
would name a template ``report.csv.mako`` if it generates a comma separated value file.

You can also choose not to use the optional ``.mako`` / ``.jj2`` trailing part, but then it's your task to
remember that it is a template and which language it uses.

A template must declare its iteration domain, that is, on which type of objects it reports.  The iteration
domain is declared in a comment line, something like this (for Mako)::

     ## DOMAIN <name>

or this (for Jinja2)::

     {# DOMAIN <name> #}

Here ``<name>`` is one of ``Species``, ``Accession``, ``Plant``, ``Location``, or ``raw``.

The role of the DOMAIN declaration is to instruct ghini about the data to handle to the template, when
rendering it: when rendering a template, ghini starts by building a raw list, containing all top-level
objects in current result.  If the declared iteration domain is ``raw``, ghini will pass the raw list to the
template.  If the declared iteration domain is a ghini class, ghini will then build a list of all objects in
the iteration domain, associated to the raw list.

In either case, these objects are available to the template as elements of the list ``values``.

A template working with the ``raw`` list needs more programming logic to do what the user expects, but a
well-thought set of such templates can reduce the amount of template names that your users need to handle.

A template may require extra options, that can the user will define at run time.  These are described in
comment lines, like in this Mako example::

  ## OPTION accession_first: (type: integer, default: '', tooltip: 'start of range.')
  
The Jinja2 equivalent of the above is::

  {# OPTION accession_first: (type: integer, default: '', tooltip: 'start of range.') #}

As you can see from the example, an option has a name and the three compulsory fields ``type``, ``default``,
``tooltip``.  ``type`` must be the python name of a type, valid at runtime, and initializable from the
default value, and from the text inserted by the user at runtime.  Built-in examples would be ``str``,
``int``, ``float``, ``bool``.  If the user provided value is invalid for the type, or if the user provides
no value, the ``default`` value will be used.  ``tooltip`` is shown when the user places the mouse cursor
over the text, without clicking.


Working with Jinja2
..........................

Jinja2 is a mainstream, powerful and well documented template language.  Please refer to `Jinja2 online
documentation <http://jinja.pocoo.org/>`_ for information regarding how to write templates.

A good and comprehensive example for Jinja2 within |ghini.desktop| is the ``tortuosa.ps.jj2`` template.  It
shows how to write a template that inherits from a base template, how to define a template domain, how to
import pictures, and how to use the ``PS`` and ``SVG`` namespaces and the ``enumerate`` function, which are
all included by default to the environment accessible from your Jinja2 templates.



Working with Mako
......................................

The Mako report formatter uses the Mako template language for generating reports.  The Mako templating
system is included in all |ghini.desktop| installation.

Mako is less mainstream than Jinja2, and arguably less good documented, but also quite more flexible than
Jinja2.  They are very similar to each other so most concepts apply to both.  If you're doing something
rather simple, start with Jinja2.  If you stumble against Jinja2 limitations, try Mako.  If you don't
understand how Mako works, spend a couple of hours on Jinja2 documentation, then go back to Mako.

More information about Mako and its language can be found at `makotemplates.org
<http://www.makotemplates.org>`_.

A very comprehensive example for Mako within |ghini.desktop| is the ``accession-label-qr.ps.mako`` example.
It shows how to write a template that inherits from a base templates, how to define a template domain.  The
``accession-label-qr.ps.mako`` example also shows how to import pictures, how to import functions from the
available Python environment, and how to use the ``PS`` and ``SVG`` namespaces, included by default to the
environment accessible from your Mako templates.


Working with XSL Stylesheets
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The XSL report formatter requires an XSL to PDF renderer to
convert the data to a PDF file. Apache FOP is a free and
open-source XSL->PDF renderer and is recommended.

Installing Apache FOP on GNULinux
...................................

If using Linux, Apache FOP should be installable using your package
manager.  On Debian/Ubuntu it is installable as ``fop`` in Synaptic or
using the following command::

   apt-get install fop


Installing Apache FOP on Windows
................................

You have two options for installing FOP on Windows. The easiest way is to download the prebuilt
`ApacheFOP-0.95-1-setup.exe
<http://code.google.com/p/apache-fop-installer/downloads/detail?name=ApacheFOP-0.95-1-setup.exe&can=2&q=#makechanges>`_
installer.

Alternatively you can download the `archive <http://www.apache.org/dist/xmlgraphics/fop/binaries/>`_.  After
extracting the archive you must add the directory you extracted the archive to to your PATH environment
variable.
