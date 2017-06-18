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

You don't specify the search domain, all are included, nor do you indicate
which fields you want to match, this is implicit in the search domain.

The following table helps you understand the results and guides you in
formulating your searches.

=============================  =====================  ============
search domain overview                                            
------------------------------------------------------------------
name and shorthands            field                  result type 
=============================  =====================  ============
family, fam                    epithet (family)       Family      
genus, gen                     epithet (genus)        Genus       
species, sp                    epithet (sp) **×**     Species     
vernacular, common, vern       name                   Species     
geography, geo                 name                   Geography   
accession, acc                 code                   Accession   
planting, plant                code **×**             Plant       
location, loc                  code, name             Location    
contact, person, org, source   name                   Contact     
collection, col, coll          locale                 Collection  
tag, tags                      name                   Tag         
=============================  =====================  ============
              
Examples of searching by value would be: Maxillaria, Acanth,
2008.1234, 2003.2.1, indica.

Unless explicitly quoted, spaces separate search strings. For example if you
search for ``Block 10`` then Ghini will search for the strings Block and 10
and return all the results that match either of these strings. If you want
to search for Block 10 as one whole string then you should quote the string
like ``"Block 10"``.

.. admonition:: × Composite Primary Keys
   :class: note

                A **species** epithet means little without the corresponding
                genus, likewise a **planting** code is unique only within
                the accession to which it belongs.  In database theory
                terminology, epithet and code are not sufficient to form a
                **primary key** for respectively species and planting.
                These domains need a **composite** primary key.

                Search by value lets you look for **plantings** by their
                complete planting code, which includes the accession code.
                Taken together, Accession code and Planting code do provide
                a **composite primary key** for plantings.  For **species**,
                we have introduced the binomial search, described below.


Search by Expression
++++++++++++++++++++++++++++++++++++++++

Searching with expression gives you a little more control over what you are
searching for. You narrow the search down to a specific domain, the software
defines which fields to search within the domain you specified.

An expression is built as ``<domain> <operator> <value>``. For example the
search: ``gen=Maxillaria`` would return all the genera that match the name
Maxillaria. In this case the domain is ``gen``, the operator is ``=`` and
the value is ``Maxillaria``.

The above search domain overview table tells you the names of the search
domains, and, per search domain, which fields are searched.

The search string ``loc like block%`` would return all the Locations for
which name or code start with "block".  In this case the domain is ``loc``
(a shorthand for ``location``), the operator is ``like`` (this comes from
SQL and allows for "fuzzy" searching), the value is ``block%``, the
implicitly matched fields are ``name`` and ``code``.  The percent sign is
used as a wild card so if you search for ``block%`` then it searches for all
values that start with max.  If you search for ``%10`` it searches for all
values that end in ``10``.  The string ``%ck%10`` would search for all value
that contain ``ck`` and end in ``10``.

.. admonition:: When a query takes ages to complete
   :class: note

   You give a query, it takes time to compute, the result contains
   unreasonably many entries.  This happens when you intend to use a
   strategy, but your strings do not form a valid expression.  In this case
   Ghini falls back to *search by value*. For example the search string
   ``gen lik maxillaria`` will search for the strings ``gen``, ``lik``, and
   ``maxillaria``, returning all that match at least one of the three
   criteria.

Binomial search
+++++++++++++++++++++++++++++++++++

You can also perform a search in the database if you know the species, just
by placing a few initial letters of genus and species epithets in the search
engine, correctly capitalized, i.e.: **Genus epithet** with one leading capital
letter, **Species epithet** all lowercase.

This way you can perform the search ``So ha``.

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

Queries allow the most control over searching. With queries you can search
across relations, specific columns, combine search criteria using boolean
operators like and(&&), or(||), not(!), enclose them in parentheses, and
more.

Please contact the authors if you want more information, or if you volunteer
to document this more thoroughly.  In the meanwhile you may start
familiarizing yourself with the core structure of Ghini's database.

.. figure:: images/schemas/ghini-10.png

   **core structure of Ghini's database**

A few examples:

* plantings of family Fabaceae in location Block 10::

    plant WHERE accession.species.genus.family=Fabaceae AND location.site="Block 10"

* locations that contain no plants::

    location WHERE plants = Empty

* accessions associated to a species of known binomial name::

    accession WHERE species.genus.genus=Mangifera AND species.sp=indica

* accessions we propagated in the year 2016::
        
    accession WHERE plants.propagations._created BETWEEN |datetime|2016,1,1| AND |datetime|2017,1,1|

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

Query Grammar
==================

For those who don't fear a bit of formal precision, this is top-part of the
grammar implemented by the Query Search Strategy, here given in BNF.  Some
grammatical categories are informally defined; a few are left to your
imagination; literals are included in single quotes; the grammar is mostly
case insensitive, unless otherwise stated::

    query ::= domain 'WHERE' complex_expression
    complex_expressions ::= single_expression
                        | single_expression 'AND' complex_expression
                        | single_expression 'OR' complex_expression
  
    single_expression ::= bool_expression
                        | 'NOT' bool_expressions
    bool_expression ::= identifier binop value
                      | identifier binop_set value_list
                      | aggregated binop value
                      | identifier 'BETWEEN' value 'AND' value
                      | '(' query_expression ')'

    identifier ::= [a-z][a-z0-9_]*
    aggregated ::= aggregating_func '(' identifier ')'
    aggregating_func ::= 'SUM'
                       | 'MIN'
                       | 'MAX'
                       | 'COUNT'

    value ::= typed_value 
            | numeric_value
            | none_token
            | empty_token
            | string_value

    typed_value ::= '|' type_name '|' value_list '|'
    numeric_value ::== #( just a number )
    none_token ::= 'None'    #( case sensitive )
    empty_token ::= 'Empty'  #( case sensitive )
    string_value = quoted_string | unquoted_string

    type_name ::= 'datetime'  #( only one for the time being )
    quoted_string ::= '"' unquoted_string '"'
    unquoted_string ::=  #( alphanumeric and more )

    value_list ::= value ',' value_list
                 | value

    domain ::= #( one of our search domains )

    binop ::= '=' 
            | '==' 
            | '!=' 
            | '<>' 
            | '<' 
            | '<=' 
            | '>' 
            | '>=' 
            | 'NOT' 
            | 'LIKE' 
            | 'CONTAINS' 
            | 'HAS' 
            | 'ILIKE' 
            | 'ICONTAINS' 
            | 'IHAS' 
            | 'IS'
    binop_set ::= 'IN'


