using ghini for a seed database
====================================================

We keep getting involved in groups focusing on endagered plant seeds.  They
want to note down when seeds come in, but also when they go out to people
that order the seed.

In ghini, we keep speaking of ›Plants‹, ›Locations‹, while such user groups
focus on ›Seeds‹ and ›Jars‹ and ›Drawers‹ and ›Boxes‹ and ›Envelopes‹.  So
people wonder whether ghini could be adapted to their use case, or for
directions on how to develop their own database.

.. admonition:: Does ghini need being adapted for such a seed database?
   :class: toggle

      no it doesn't need any adaptation, it's just that you need to read
      some of its terms differently.

      the taxonomy part is just taxonomy, plant species information, no need to
      explain that, no way to interpret it otherwise.

      ›Accessions‹ and ›Plants‹, you know what an ›Accession‹ is, but since
      you're consistently handling ›Plants‹ still only in seed form, the
      Wikipedia explanation of an accession sounds like this: it is a seed
      or group of seeds that are of the same taxon, are of the same
      propagule type (or treatment), were received from the same source,
      were received at the same time.

      If you hold seeds in jars, or in other sort of containers that is able
      to hold hundreds of seeds, please make sure that a jar contains seeds
      of just one accession, as above described: same taxon, same treatment,
      same source, same time.

      Each one of your ›Jars‹ of seeds is in ghini speak a ›Plant‹, and the
      amount of seeds in the ›Jar‹ is the ›Plant‹ ›quantity‹.  An ›Envelope‹
      is just the same as a ›Jar‹: a container of seeds from the same
      ›Accession‹, just presumably smaller.
       
      A ›Box‹ (where you keep several ›Envelopes‹) or a ›Drawer‹ (where you
      keep several ›Jars‹) are in ghini speak a ›Location‹.

      Since a ›Jar‹ or an ›Envelope‹ contains seeds from an ›Accession‹, you
      will clearly label it with its ›Accession‹ code (and trailing ›Plant‹
      number).  You might write the amount of seeds, too, but this would be
      repeating information from the database, and repeating information
      introduces an inconsistency risk factor.

.. admonition:: How do I handle receiving a batch of seeds?
   :class: toggle

      .. note:: When we receive seeds, we either collect them ourselves, or
                we receive it from an other seed collector.  We handle
                receiving them possibly on the spot, or with a small delay.
                Even when handled together with several other batches of
                seeds we received, each batch keeps its individuality.
       
                We want to be later able to find back, for example, how many
                seeds we still have from a specific batch, or when we last
                received seeds from a specific source.

      As long as you put this information in the database, as long as you
      follow the same convention when doing so, you will be able to write
      and execute such queries using ghini.

      One possibility, the one described here, is based on ›Notes‹.  (Ghini
      does not, as yet, implement the concept "Acquisition". There is an
      issue related to the Acquisition and Donation objects, but we haven't
      quite formalized things yet.)

      You surely already use codes to identify a batch of seeds entering the
      seed bank.  Just copy this code in a ›Note‹, category 'received', to
      each ›Accession‹ in the received batch.  This will let you select the
      ›Accessions‹ by the query::

        accession where notes[category='received'].note='<your code>'

      Use the 'Source' tab if you think so, it offers space for indicating
      an external source, or an expedition.  When receiving from an external
      source, you can specify the code internal to their organization.  This
      will be useful when requesting an extra batch.

.. admonition:: How do I handle sending seeds?
   :class: toggle

      what you physically do is to grab the desired amount of seeds of the
      indicated species from a jar, put it in an envelope and send it.  what
      you do from a point of view of the database is exactly the same, but
      precisely described in a protocol:

      * Use the database to identify the ›Jar‹ containing the desired amount
        of the right seeds.
      * remove that amount of seeds from the ›Jar‹ (decrement the quantity),
      * put the seeds in an ›Envelope‹ (yes, that's a database object).
      * send the envelope (but keep it in the database).
      
      this in short.

.. admonition:: When I send seeds, it's not just one bag, how does ghini
                help me keeping things together?
   :class: toggle

      There's two levels of keeping things together: one is while you're
      preparing the sending, and then for later reference.

      While preparing the sending, we advise you use a temporary ›Tag‹ on the
      objects being edited.

      For later reference, you will have common ›Note‹ texts, to identify
      received and sent batches.

.. admonition:: Can you give a complete example?
   :class: toggle

      Right.  Quite fair.  Let's see…

      Say you were requested to deliver 50 seeds of Parnassia palustris, 30
      of Gentiana pneumonanthe, 80 of Fritillaria meleagris, and 30 of
      Hypericum pulchrum.

      **step 1**

      The first step is to check the quantities you have in house, and if
      you do have enough, where you have them.  You do this per requested
      species::

        accession where species.genus.epithet=Parnassia and species.epithet=palustris and sum(plants.quantity)>0

      Expand in the results pane the ›Accession‹ from which you want to grab
      the seeds, so you see the corresponding ›Jars‹, highlight one, and tag
      it with a new ›Tag‹.  To do this the first time, go through the steps,
      just once, of creating a new ›Tag‹.  The new tag becomes the active
      tag, and subsequent tagging will be speedier.  I would call the tag
      ›sending‹, but that's only for ease of exposition and further
      completely irrelevant.

      Repeat the task for Gentiana pneumonanthe, Fritillaria meleagris,
      Hypericum pulchrum::

        accession where species.genus.epithet=Gentiana and species.epithet=pneumonanthe and sum(plants.quantity)>0
        accession where species.genus.epithet=Fritillaria and species.epithet=meleagris and sum(plants.quantity)>0
        accession where species.genus.epithet=Hypericum and species.epithet=pulchrum and sum(plants.quantity)>0

      Again highilight the accession from which you can grab seeds, and hit
      Ctrl-Y (this tags the highighted row with the active tag).  Don't
      worry if nothing seems to happen when you hit Ctrl-Y, this is a silent
      operation.

      **step 2**

      Now we prepare to go to the seeds bank, with the envelopes we want to
      fill.

      Select the ›sending‹ ›Tag‹ from the tags menu, this will bring back in
      the results pane all the tagged ›Plants‹ (›Jars‹ or ›Envelopes‹), and
      will tell you in which ›Location‹ (›Drawer‹ or ›Box‹) they are to be
      found.  Write this information on each of your physical envelopes.
      Write also the ›Species‹ name, and the quantity you can provide.

      Walk now to your seeds bank and, for each of the envelopes you just
      prepared, open the ›Location‹, grab the ›Plant‹, extract the correct
      amount of seeds, put them in your physical envelope.

      And back to the database!

      **step 3**

      If nobody used your workstation, you still have the Tag in the results
      pane, and it's expanded so you see all the individual plants you
      tagged.

      One by one, you have to ›split‹ the plant.  This is a standard
      operation that you activate by right-clicking on the plant.
      
      A plant editor window comes in view, in 'split mode'.
      
      Splitting a plant lets you create a database image of the plant group
      you just physically created, eg: it lets you subtract 30 items from
      the Gentiana pneumonanthe plant (group number one, that is the one in
      the jar), and create a new plant group for the same accession.  A good
      practice would be to specify as ›Location‹ for this new plant the 'out
      box', that is, the envelope is on its way to leave the garden.

      Don't forget to delete the temporary 'sending' ›Tag‹.

      **step 4**

      Final step, it represents the physical step of sending the envelope,
      possibly together with several other envelopes, in a single sending,
      which should have a code.
      
      Just as you did when you received a batch of plants, you work with
      notes, this time the category is 'sent', and the note text is
      whatever you normally do to identify a sending.  So suppose you're
      doing a second sending to Pino in 2018, you add the note to each of
      the newly created envelopes: category 'sent', text: '2018-pino-002'.

      When you finally do send the envelopes, these stop being part of your
      collection.  You still want to know that they have existed, but you
      do not want to count them among the seeds that are available to you.

      Bring back all the plants in the sending '2018-pino-002'::

        plant where notes[category='sent'].note = '2018-pino-002'

      You now need to edit them one by one, mark the ›quantity‹ to zero, and
      optionally specify the reason of the change, which would be ›given
      away‹, and the recipient is already specified in the 'sent' ›Note‹.

      This last operation could be automated, we're thinking of it, it would
      become a script, acting on a selection.  Stay tuned.
