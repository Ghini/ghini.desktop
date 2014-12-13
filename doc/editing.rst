Editing and Inserting Data
==========================

The main way that we add or change information in Bauble is by using
the editors.  Each basic type of data has its own editor.  For example
there is a Family editor, a Genus editor, an Accession editor, etc.

To create a new record click on the :menuselection:`Insert` menu on
the menubar and then select the type of record your would like to
create.  This will open a new blank editor for the type.

To edit an existing record in the database right click on an item in
the search results and select :menuselection:`Edit` from the popup
menu.  This will open an editor that will allow you to change the
values on the record that you selected.

Most types also have children which you can add by right clicking on
the parent and selecting "Add ???..." on the context menu.  For
example you can add a Genus to a Family by right clicking on a Family
and selecting "Add genus".


Notes
-----
Almost all of the editors in Bauble have a *Notes* tab which should work
the same regardless of which editor you are using.  

If you enter a web address in a note then the link will show up in the
Links box when the item your are editing is selected in the search results.

You can browse the notes for an item in the database using the Notes
box at the bottom of the screen.  The Notes box will be desensitized
if the selected item does not have any notes.


Family
------
The Family editor allows you to add or change a botanical family.

The *Family* field on the editor will change the name of the family.
The Family field is required.

The *Qualifier* field will change the family qualifier.  The value can
either be *sensu lato*, *sensu stricto* or nothing.

*Synonyms* allow you to add other families that are synonyms with the
family you are currently editing.  To add a new synonyms type in a
family name in the entry.  You must select a family name from the list
of completions.  Once you have selcted a family name that you want to
add as a synonym click on the Add button next to the synonym list and
it will add the selected synonym to the list.  To remove a synonym
select the synonym from the list and click on the Remove button.

To cancel your changes without saving then click on the *Cancel* button.

To save the family you are working on then click *OK*.

To save the family you are working on and add a genus to it then click on
the *Add Genera* button.

To add another family when you are finished editing the current one
click on the *Next* button on the bottom.  This will save the current
family and open a new blank family editor.


Genus
-----
The Genus editor allows you to add or change a botanical genus.

The *Family* field on the genus editor allows you to choose the family
for the genus.  When you begin type a family name it will show a list
of families to choose from.  The family name must already exist in the
database before you can set it as the family for the genus.

The *Genus* field allows you to set the genus for this entry.

The *Author* field allows you to set the name or abbreviation of the
author(s) for the genus.

*Synonyms* allow you to add other genera that are synonyms with the
genus you are currently editing.  To add a new synonyms type in a
genus name in the entry.  You must select a genus name from the list
of completions.  Once you have selcted a genus name that you want to
add as a synonym click on the Add button next to the synonym list and
it will add the selected synonym to the list.  To remove a synonym
select the synonym from the list and click on the Remove button.

To cancel your changes without saving then click on the *Cancel* button.

To save the genus you are working on then click *OK*.

To save the genus you are working on and add a species to it then click on
the *Add Species* button.

To add another genus when you are finished editing the current one
click on the *Next* button on the bottom.  This will save the current
genus and open a new blank genus editor.


Species/Taxon
-------------
A species is a taxon in the database.  It represents a unique name in
the database.  The species editor will allow you to construct the name
as well as associate metadata with the taxon such as its distribution,
synonyms and other informaiton.

To cancel your changes without saving then click on the *Cancel* button.

To save the species you are working on then click *OK*.

To save the species you are working on and add an accession to it then click on
the *Add Accession* button.

To add another species when you are finished editing the current one
click on the *Next* button on the bottom.  This will save the current
species and open a new blank species editor.

Accessions
----------

The Accession editor allows us to add an accession to a species.  In
Bauble an accession represents a group of plants or clones.  The
accession would refer maybe a group of seed or cuttings from a
species.  A plant would be an individual from that accesssion, i.e. a
specific plant in a specific location.

Accession Source
^^^^^^^^^^^^^^^^
The source of the accessions lets you add more information about where
this accession came from.  At the moment the type of the source can be
either a Collection or a Donation.


Collection
""""""""""
A Collection.


Donation
""""""""
A Donation.


Plant
-----
The Plant editor.

Creating multiple plants
^^^^^^^^^^^^^^^^^^^^^^^^
You can create multiple Plants by using ranges in the code entry.
This is only allowed when creating new plants and it is not possible
when editing existing Plants in the database.

For example the range, 3-5 will create plant with code 3,4,5.  The
range 1,4-7,25 will create plants with codes 1,4,5,6,7,25.

When you enter the range in the plant code entry the entry will turn
blue to indicate that you are now creating multiple plants.  Any
fields that are set while in this mode will be copied to all the
plants that are created.


Locations
---------
The Location editor



