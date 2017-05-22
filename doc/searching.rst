.. _searching-in-bauble:

Searching in Ghini
-------------------

Searching allows you to view, browse and create reports from your
data. You can perform searches by either entering the queries in the
main search entry or by using the Query Builder to create the queries
for you. The results of Ghini searches are listed in the main window.


Search Strategies
=================

Three are three types of search strategies available in Ghini. Considering
the search stragety types available in Ghini, sorted in increasing
complexity: you can search by value, expression or query.

Searching by query, the most complex and powerful, is assisted by the Query
Builder, described below.

All searches are case insensitive so searching for Maxillaria and
maxillaria will return the same results.


Search by Value
+++++++++++++++

Search by value is the simplest way to search. You just type in a
string and see what matches. Which fields/columns are search for your
string depends on how the different plugins are configured. For
example, by default the PlantPlugin search the family name, the genus
name, the species and infraspecific species names, vernacular names
and geography. So if you want to search in the notes field of any of
these types then searching by value is not the search you're looking
for.

Examples of searching by value would be: Maxillaria, Acanth,
2008.1234, 2003.2.1

Search string are separated by spaces. For example if you enter the
search string ``Block 10`` then Ghini will search for the strings Block
and 10 and return all the results that match either of these
strings. If you want to search for Block 10 as a while string then you
should quote the string like ``"Block 10"``.  


Search by Expression
++++++++++++++++++++

Searching with expression gives you a little more control over what
you are searching for. It can narrow the search down to a specific
domain. Expression consist of a domain, an operator and a value. For
example the search: ``gen=Maxillaria`` would return all the genera that
match the name Maxillaria. In this case the domain is gen, the
operator is = and the value is Maxillaria.

The search string ``gen like max%`` would return all the genera whose
names start with "Max". In this case the domain again is gen, the
operator is like, which allows for "fuzzy" searching and the value is
max%. The percent sign is used as a wild card so if you search for
max% then it search for all value that start with max. If you search
for %max it searches for all values that end in max. The string %max%a
would search for all value that contain max and end in a.

For more information about the different search domain and their short-hand
aliases, see search-domains_ .

If expression are invalid they are usually used as search by value
searchs. For example the search string ``gen=`` will execute a search by
value for the string gen and the search string ``gen like`` will search
for the string gen and the string like.  


Search by Query
+++++++++++++++

Queries allow the most control over searching. With queries you can
search across relations, specific columns and join search using
boolean operators like AND and OR.

An example of a query would be::

    plant where accession.species.genus.family=Fabaceae and location.site="Block 10"

This query would return all the plants whose family are Fabaceae and
are located in Block 10.

Searching with queries usually requires some knowledge of the Ghini
internals and database table layouts.  

A couple of useful examples:

* Which locations are in use::

    location where plants.id!=0

* Which genera are associated to at least one accession::

    genus where species.accession.id!=0

.. _search-domains:

Domains 
+++++++ 

The following are the common search domain and the columns they search
by default. The default columns are used when searching by value and
expression. The queries do not use the default columns.


:Domains:
    family, fam: Search :class:`bauble.plugins.plants.Family`

    genus, gen: Search :class:`bauble.plugins.plants.Genus`

    species, sp: Search :class:`bauble.plugins.plants.Species`
    
    geography: Search :class:`bauble.plugins.plants.Geography`

    acc: Search :class:`bauble.plugins.garden.Accession`

    plant: Search :class:`bauble.plugins.garden.Plant`

    location, loc: Search :class:`bauble.plugins.garden.Location`

The Query Builder
=================

The Query Builder helps you build complex search queries through a
point and click interface.  To open the Query Builder click the to the
left of the search entry or select :menuselection:`Tools-->Query
Builder` from the menu.

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
