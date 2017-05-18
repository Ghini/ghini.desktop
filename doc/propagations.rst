.. _propagations:

Dealing with Propagations
==========================

Ghini offers the possibility to associate propagations trials to plants and
to document their treatments and results. Treatments are integral parts of
the description of a propagation trial, the result of a propagation trial is
an Accession.

Here we describe how you use this part of the interface, and present Ghini's
view on the task of associating a new accession number to a successful
propagation trial.

Creating a Propagation
------------------------

A Propagation (trial) is obtained from a Plant. Ghini reflects this in its
interface: you select a plant, open the Plant Editor on it, activate the
Propagation Tab, click on Add.

When you do the above, you get a Propagation Editor window. Ghini does not
consider Propagation trials as independent entities, as a result, the
Propagation Editor is a special editor window, which you can only reach from
the Plant Editor.

For a new Propagation, you select the type of propagation (this becomes an
immutable property of the propagation) then insert the data describing it.

You will be able to edit the propagation data via the same path: select a
plant, open the Plant Editor, identify the propagation you want to edit,
click on the corresponding Edit button. You will be able to edit all
properties of an existing Propagation trial, except its type.

In the case of a seed propagation trial, you have a pollen parent, and a
seed parent. According to ITF2, there might be cases in which it is not
known which Plant plays which role in the propagation trial. If the role of
both parents are known, you should always associate the Propagation trial to
the seed parent. Ghini-1.0 does not let you specify the pollen parent plant
except in the "Notes" field.


Using a Propagation
--------------------------

A Propagation trial may be successful and result in a new Accession.

Ghini helps you reflect this in the database: create a new Accession,
immediately switch to the Source tab and select "Garden Propagation" in the
(admittedly somewhat misleading) Contact field. Start typing the plant
number and a list of matching plants with still unaccessed propagation
trials will appear for you to select from.

Select a propagation trial from the list and that's it. Using the data from
the Propagation trial, Ghini will complete some of the fields in the General
tab: Taxon name, Type of material, and possibly Provenance. You will be able
to edit these fields, but please note that the software will not prevent
introducing conceptual inconsistencies in your database.

You can associate a Propagation trial to only one Accession.
