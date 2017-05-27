Ghini's goal
================

Should you use this software? This question is for you to answer. We trust
that if you manage a botanic collection, you will find Ghini overly useful
and we hope that this page will convince you about it.

This page shows how Ghini makes software meet the needs of a botanic garden.

Botanic Garden
--------------------------------------------------------

According to the Wikipedia, »A botanic(al) garden is a garden dedicated to
the collection, cultivation and display of a wide range of plants labelled
with their botanical names«, and still according to the Wikipedia, »a
garden is a planned space, usually outdoors, set aside for the display,
cultivation, and enjoyment of plants and other forms of nature.«

So we have in a botanic garden both the physical space, the garden, as its
dynamic, the activities to which the garden is dedicated, activities which
makes us call the garden a botanic garden.

.. figure:: images/garden_worries_1.png

   **the physical garden**

.. figure:: images/garden_worries_2.png

   **collection related activities in the garden**

Botanic Garden Software
-----------------------------------------------

At the other end of our reasoning we have the application program Ghini, and
again quoting the Wikipedia, »an application program is a computer program
designed to perform a group of coordinated functions, tasks, or activities
for the benefit of the user«, or, in short, »designed to help people perform
an activity«.

Data and algorithms within Ghini have been designed to represent the
physical space and the dynamic of a botanic garden.

.. figure:: images/schemas/ghini-10.png

   **core structure of Ghini's database**

The central element in Ghini's point of view is the ``Accession``. Following
its links to other database objects lets us better understand the structure:

  An ``Accession`` represents the action of receiving plant material in
  the garden. As such, ``Accession`` is an abstract concept, it links
  physical living ``Plantings`` —groups of plants placed each at a
  ``Location`` in the garden— to the corresponding ``Species``. An
  ``Accession`` has zero or more ``Plantings`` associated to it (0..n), and
  it is at all times connected to exactly 1 ``Species``. Each ``Planting``
  belongs to exactly one ``Accession``, each ``Species`` may have multiple
  ``Accessions`` relating to it.

  An ``Accession`` stays in the database even if all of its ``Plantings``
  have been removed, sold, or have died. Identifying the ``Species`` of an
  ``Accession`` consistently connects all its ``Plantings`` to the
  ``Species``.

  An ``Accession`` may be obtained from an external ``Contact``, or be the
  result of a garden ``Propagation``.  This information is optional.  A
  successful ``Propagation`` trial can only result in one accession (0..1),
  while a ``Contact`` may provide multiple ``Accessions`` (0..n).

  Specialists may formulate their opinion about the ``Species`` to which an
  ``Accession`` belongs, by providing a ``Verification``, signing it, and
  stating the applicable level of confidence.

  If an ``Accession`` was obtained in the garden nursery from a successful
  ``Propagation``, the ``Propagation`` links the ``Accession`` and all of
  its ``Plantings`` to a single parent ``Planting``, the seed or the
  vegetative parent.

Even after the above explanation, new users generally still ask why they
need pass through an ``Accession`` screen while all they want is to insert a
``Plant`` in the collection, and again: what is this "accession" thing
anyway?  Most discussions on the net don't make the concept any clearer.
One of our users gave an example which I'm glad to include in Ghini's
documentation.

:use case: #. At the beginning of 2007 we got five seedlings of *Heliconia
              longa* (a plant ``Species``) from our neighbour (the
              ``Contact`` source). Since it was the first acquisition of the
              year, we named them 2007.0001 (we gave them a single unique
              ``Accession`` code) and we planted them all together at one
              ``Location`` as a single ``Planting`` with quantity 5.

           #. At the time of writing, nine years later, ``Accession``
              2007.0001 has 6 distinct ``Plantings``, each at a different
              ``Locations`` in our garden, obtained vegetatively (asexually)
              from the original 5 plants. Our only intervention was
              splitting, moving, and of course writing this information in
              the database.

           #. New ``Plantings`` obtained by (assisted) sexual ``Propagation``
              come in our database under different ``Accession`` codes, where
              our garden is the ``Contact`` source and where we know which of
              our ``Plantings`` is the seed parent.

the above three cases translate into several short usage stories:

#. activate the menu Insert → Accession, verify the existence and
   correctness of the ``Species`` *Heliconia longa*, specify the initial
   quantity of the ``Accession``; add its ``Planting`` at the desired
   ``Location``.
#. edit ``Planting`` to correct the amount of living plants — repeat this as
   often as necessary.
#. edit ``Planting`` to split it at separate ``Locations`` — this produces a
   different ``Planting`` under the same ``Accession``.
#. edit ``Planting`` to add a (seed) ``Propagation``.
#. edit ``Planting`` to update the status of the ``Propagation``.
#. activate the menu Insert → Accession to associate an accession to a
   successful ``Propagation`` trial; add the ``Planting`` at the desired
   ``Location``.

In particular the ability to split a ``Planting`` at several different
``Locations`` and to keep all uniformly associated to one ``Species``, or
the possibility to keep information about ``Plantings`` that have been
removed from the collection, help justify the presence of the ``Accession``
abstraction level.

-----------------------------------------------

Our User Stories section contains details about the above, and more.

-----------------------------------------------
