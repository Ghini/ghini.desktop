.. _searching-in-bauble:

Searching in Ghini
-------------------

Searching allows you to view, browse and create reports from your
data. You can perform searches by either entering the queries in the
main search entry or by using the Query Builder to create the queries
for you. The results of Ghini searches are listed in the main window.


Search Strategies
=================

Ghini offers four distinct search strategies:

* by value — in all domains;
* by expression — in a few implicit fields in one explicit domain;
* by query — in one domain; 
* by binomial name — only searches the Species domain.

All search strategies —with the notable exception of the binomial name
search— are case insensitive.


Search by Value
+++++++++++++++++++++++++++++++++++

Search by value is the simplest way to search. You enter one or more strings
and see what matches. The result includes objects of any type (domain) where
one or more of its fields contain one or more of the search strings.

You don't specify the search domain, all are included.  Within each search
domain, the values are tested against one or more fields:

=============================  ============  =====================
search domain overview
------------------------------------------------------------------
name and shorthands            result type   field
=============================  ============  =====================
family, fam                    Family        epithet (family)
genus, gen                     Genus         epithet (genus)
species, sp                    Species       epithet (sp) **×**
vernacular, common, vern       Species       name
geography, geo                 Geography     name
accession, acc                 Accession     code
plant, plants                  Plant         code **×**
location, loc                  Location      code, name
contact, person, org, source   Contact       name
collection, col, coll          Collection    locale
tag, tags                      Tag           name
=============================  ============  =====================
              
Examples of searching by value would be: Maxillaria, Acanth,
2008.1234, 2003.2.1, indica.

Unless explicitly quoted, spaces separate search strings. For example if you
search for ``Block 10`` then Ghini will search for the strings Block and 10
and return all the results that match either of these strings. If you want
to search for Block 10 as one whole string then you should quote the string
like ``"Block 10"``.

.. admonition:: ×

                Primary Keys

                A species epithet means very little without the
                corresponding genus, likewise a plant code is unique only
                within the accession to which the plant belongs.

                In database theory terminology, epithet and code are not
                primary keys for respectively species and planting.

                Search by value works this around and you can find plantings
                by their complete planting code, which includes the
                accession code. For species, we have introduced the
                **binomial search**.


Search by Expression
++++++++++++++++++++++++++++++++++++++++

Searching with expression gives you a little more control over what you are
searching for. It narrows the search down to a specific domain. Expression
consist of a **domain**, an **operator** and a **value**. For example the
search: ``gen=Maxillaria`` would return all the genera that match the name
Maxillaria. In this case the **domain** is ``gen``, the **operator** is
``=`` and the **value** is ``Maxillaria``.

The above search domain overview table tells you which fields are implicitly
matched when you explicitly name the search domain.

The search string ``gen like max%`` would return all the genera whose
names start with "Max". In this case the domain again is ``gen``, the
operator is ``like``, which allows for "fuzzy" searching and the value is
``max%``. The percent sign is used as a wild card so if you search for
``max%`` then it search for all value that start with max. If you search
for ``%max`` it searches for all values that end in max. The string ``%max%a``
would search for all value that contain max and end in a.

.. note::

   I give a query, it takes a huge time to compute, and it returns with an
   unreasonably long result.
   If the given strings do not form a valid expression, Ghini will fall back
   to *search by value*. For example the search string ``gen=`` will execute
   a search by value for the string ``gen`` and the search string ``gen
   like`` will search for the string ``gen`` and the string ``like``.

Binomial search
+++++++++++++++++++++++++++++++++++

You can also perform a search in the database if you know the species, just
by placing a few initial letters of genus and species epithets in the search
engine, correctly capitalized, i.e.: **Genus epithet** with one leading capital
letter, **Species epithet** all lowercase.

This way you can perform the search::
  
  So ha

These would be the initials for Solanum hayesii, or Solanum havanense.

Binomial search comes to compensate the limited usefulness of the above
search by expression when trying to look for a species.

It is the correct capitalization **Xxxx xxxx** that informs the
software of your intention to perform a binomial search.  The software's
second guess will be a search by value, which will possibly result in far
more matches than you had expected.

The similar request ``so ha`` will return, in a fresh install, over 3000
objects, starting at Family "Acalyp(**ha**)ceae", ending at Geography
"Western (**So**)uth America".

   
Search by Query
+++++++++++++++++++++++++++++++++++

Queries allow the most control over searching. With queries you can
search across relations, specific columns and join search using
boolean operators like AND and OR.

A few examples:

* plantings of family Fabaceae in location Block 10::

    plant where accession.species.genus.family=Fabaceae and location.site="Block 10"

* Which locations contain no plants::

    location where plants = Empty

* Which accessions are associated to a species of known binomial name::

  accession where species.genus.genus=Mangifera and species.sp=indica

* what accessions did we propagate last year::
        
    accession where plants.propagations._created between |datetime|2016,1,1| and |datetime|2017,1,1|

Searching with queries requires some knowledge of a little syntax and an
idea of the extensive Ghini database table structure. Both you acquire with
practice, and with the help of the Query Builder.


The Query Builder
=================

The Query Builder helps you build complex search queries through a point and
click interface.  To open the Query Builder click the |querybuilder| icon to
the left of the search entry or select :menuselection:`Tools-->Query
Builder` from the menu.

.. |querybuilder| image:: querybuilder.png
   :align: middle
   :width: 18

The Query Builder composes a query that will be understood by the Query
Search Strategy described above. You can use the Query Builder to get a
feeling of correct queries before you start typing them by hand, something
that you might prefer if you are a fast typer.

After opening the Query Builder you must select a search domain.  The
search domain will determine the type of data that is returned and the
properties that you can search.  

.. image:: images/screenshots/qb-choose_domain.png

The search domain is similar to a table in the database and the properties
would be the columns on the table.  Often the table/domain and
properties/columns are the same but not always.

Once a search domain is selected you can then select a property of the
domain to compare values to.  The search operator can then be changed
for how you want to make the search comparison.  Finally you must
enter a value to compare to the search property.  

.. image:: images/screenshots/qb-choose_property.png

If the search property you have selected can only have specific values then
a list of possible values will be provided for you to choose from.

If multiple search properties are necessary then clicking on the plus
sign will add more search properties.  Select And/Or next to the
property name choose how the properties will be combined in the search
query.

When you are done building your query click OK to perform the search.
