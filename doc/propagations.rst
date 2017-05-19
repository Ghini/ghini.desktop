.. _propagations:

Dealing with Propagations
==========================

Ghini offers the possibility to associate Propagations trials to Plants and
to document their treatments and results. Treatments are integral parts of
the description of a Propagation trial. If a Propagation trial is
successful, Ghini lets you associate it to a new Accession. You can only
associate one Accession to a Propagation Trial.

Here we describe how you use this part of the interface.

Creating a Propagation
------------------------

A Propagation (trial) is obtained from a Plant. Ghini reflects this in its
interface: you select a plant, open the Plant Editor on it, activate the
Propagation Tab, click on Add.

When you do the above, you get a Propagation Editor window. Ghini does not
consider Propagation trials as independent entities. As a result, Ghini
treats the Propagation Editor as a special editor window, which you can only
reach from the Plant Editor.

For a new Propagation, you select the type of propagation (this becomes an
immutable property of the propagation) then insert the data describing it.

You will be able to edit the propagation data via the same path: select a
plant, open the Plant Editor, identify the propagation you want to edit,
click on the corresponding Edit button. You will be able to edit all
properties of an existing Propagation trial, except its type.

In the case of a seed propagation trial, you have a pollen parent, and a
seed parent. You should always associate the Propagation trial to the seed
parent.

.. note:: In Ghini-1.0 you specify the pollen parent plant in the "Notes"
          field, while Ghini-1.1 has a (relation) field for it. According to
          ITF2, there might be cases in seed propagation trials where it is
          not known which Plant plays which role. Again, in Ghini-1.0 you
          should use a note to indicate whether this is the case, Ghini-1.1
          has a (boolean) field indicating whether this is the case.


Using a Propagation
--------------------------

A Propagation trial may be successful and result in a new Accession.

Ghini helps you reflect this in the database: create a new Accession,
immediately switch to the Source tab and select "Garden Propagation" in the
(admittedly somewhat misleading) Contact field.

Start typing the plant number and a list of matching plants with propagation
trials will appear for you to select from.

Select the plant, and the list of accessed and unaccessed propagation trials
will appear in the lower half of the window.

Select a still unaccessed propagation trial from the list and click on Ok to
complete the operation.

Using the data from the Propagation trial, Ghini completes some of the
fields in the General tab: Taxon name, Type of material, and possibly
Provenance. You will be able to edit these fields, but please note that the
software will not prevent introducing conceptual inconsistencies in your
database.

You can associate a Propagation trial to only one Accession.
