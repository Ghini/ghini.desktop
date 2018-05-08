Dear conservator, dear scientist,
=========================================

You are reading Ghini's presentation letter.  Ghini is a github free software project,
focusing on botany.  Ghini is brought to you by a small community of coders, botanists,
translators, and it is supported by a few institutions around the world, among which the
gardens that have adopted it for all their collection management needs.

The Ghini family is a software suite composed of standalone programs, data servers and
handheld clients, for data management, and publication:

.. image:: images/ghini-family-streams.png

* Ghini's core, ``ghini.desktop``, lets you enter and correct your data, navigate its links,
  produce reports, import and or export using several standard or ad-hoc formats, review your
  taxonomy using online sources, all according the best practices suggested by top gardens
  and formalized in standard formats like ABCD, ITF2, but also as elaborated by our
  developers, based on the feedback by Ghini users.  ``ghini.desktop`` is developed and
  continously tested on GNU/Linux, but it runs equally well on Windows, or OSX. [1]
* ``ghini.pocket`` is your full time garden companion.  ``ghini.pocket`` is an Android app
  you install from the Play Store, and it assists you in collecting, or correcting, data
  while in the field, it lets you associate pictures to your plants, and verify taxonomic
  information.  Back to office, you simply import your collected data in the desktop client,
  and reduce the time at the data terminal to a true bare minimum.
* ``ghini.web`` is a web server and a courtesy data hub service.  ``ghini.web`` offers you
  world wide visibility: you export a selection of your data from your desktop database, and
  handle it for publication to the Ghini project, and we will include it at
  http://gardens.ghini.me/, at no cost while we're able to do that, or for a guaranteed
  minimal amount of time if you are able to support our hosting costs.  ``ghini.web`` serves
  a world map to help locate participating gardens, and within each garden, its contributed
  georeferenced plants.  it also serves information panels, for the use of the most recent
  Ghini family member: ``ghini.tour``.
* ``ghini.tour`` is a geographic tour Android app aimed at visitors, it uses OpenStreetMap as
  base map and retrieves its data from the web data aggregator.

All software within the Ghini family is licensed according to the GNU Public License.  Are
you acquainted with this License, and the "Copyleft" concept?  In short, the GPL translates
the ethical scientific need to share knowledge, into legal terms. If you want to read more
about it, please refer to https://www.gnu.org/licenses/copyleft.html

Ghini's idea about knowledge and software ownership is that software is procedural knowledge
and as such it should be made a "commons": With software as a commons, "free software" and
more specifically "Copylefted software", you not only get the source code, you receive the
right to adapt it, and the invitation to study and learn from it, and to share it, both share
forward to colleagues, and share back to the source.  With proprietary software, you are
buying your own ignorance, and with that, your dependency.

This fancy term "copyleft" instead of just "free software", consider that it simply specifies
that the "copylefted" software you received is free software with this one extra clause that
guarantees that every rights that you were granted when you received the software are
permanently sticky to the software.

With copylefted software you are free —actually welcome— to employ local software developers
in your neighbourhood to alter the software according to your needs, and please do this on
github, fork the code, develop just as openly as the common practice within Ghini, and
whenever you want, open a pull request so your edits can be considered for inclusion in the
main line.  Ghini is mostly continuously unit tested, so before your code is added to the
main line, it should follow our quality guidelines for contributions.  With free software you
acquire freedom and contributing to free software earns you visibility: your additions stays
yours, you share them back to the community, and will see them completed and made better by
others.  Having your code added to the main line simplifies your upgrade steps.

You can also contribute to the software by helping translate into your native language. [5]

I publish some videos on youtube, highlighting some of the software capabilities. [6]

Not sharing back to the community may be formally legal, but is definitely not nice.  Several
developers have spent cumulatively many thousand hours developing this software, and we're
sharing with the community.  We hope by this to stimulate a community sentiment in whoever
starts using what we have produced.

Thanks for your consideration; please let me know if you have any questions,

Mario Frasca MSc


Many institutions still consider software an investment, an asset that is not to be shared
with others, as if it was some economic good that can't be duplicated, like gold, or money.
As of now, I am aware of the existence of very few copylefted programs for botanic data
management:

* ``ghini.desktop``, born as ``bauble.classic`` and made a Commons by the Belize Botanical
  Garden.  ``ghini.desktop`` has three more components, a pocket data collecting android app,
  a nodejs web server aggregating data from different gardens and presenting it
  geographically, again a geographic tour app aimed at visitors and using the web data
  aggregator as its data source.  You find every Ghini component on github:
  http://github.com/Ghini

* Specify 6 and 7, made a Commons by the Kansas University.  A bit complex to set up, and
  very difficult to configure, tricky to update.  The institutions I've met who tried it,
  only the bigger ones, with in-house software management capabilities manage to successfully
  use it.  They use it for very large collections.  Specify is extremely generic, it adapts
  to herbaria, seed collections, but also to collections of eggs, organic material, fossils,
  preserved dead animals, possibly even viruses, I'm not sure.  It is this extreme
  flexibility that makes its configuration such a complex task.  Specify is also on github:
  https://github.com/specify and is licensed as GPL, too.

* Botalista, a French/Swiss cooperation, is GPL as far as rumour goes. Its development
  hasn't yet gone public.

* ``bauble.web`` is an experimental web server by the author of ``bauble.classic``.
  ``bauble.classic`` has been included into Ghini, to become ``ghini.desktop``.  Bauble uses
  a very permissive license, which makes it free but not copylefted.  As much as 50% of
  bauble.web and possibly 30% of ghini.desktop is in common between the two projects.  Bauble
  seems to be stagnating, and has not yet reached production.

* ``Taxasoft-BG``, from Eric Gouda, a Dutch botanist, specialist in Bromeliaceae, collection
  manager at the Utrecht botanical garden.  It was Mario Frasca who convinced Eric to publish
  what he was doing, and to publish it under the GPL, but the repository was not updated
  after 2016, April 13th and Eric forgot to explicitly specify the license.  You find it on
  github: https://github.com/Ejgouda/Taxasoft-BG

Of the above, only ``ghini.desktop`` satisfies the conditions: copylefted, available,
documented, maintained, easy to install and configure.  Moreover: cross platform,
internationalized.




Ghini, in
honour to Luca Ghini, founder of the first botanical garden in Europe,
and I've broadened the family with a hand held inventory reviewing tool,
a data aggregator which I'm running as a service at
http://gardens.ghini.me/, and a hand held app for garden visitors.

In case you're interested to publish your tree collection on the net, I
would be happy to include your plants, species, coordinates to
http://gardens.ghini.me.  Georeferenced textual information panels, also
very welcome, all offered as courtesy: we're still defining the offer.
The idea behind this is allowing visitors explore aggregated gardens
collections, and it focuses as of now on trees.

a small example is : http://gardens.ghini.me/#garden=Jardín%20el%20Cuchubo

best regards,

Mario Frasca


[1] http://ghini.readthedocs.io/ - http://ghini.github.io/

[2] https://play.google.com/store/apps/details?id=me.ghini.pocket

[3] http://gardens.ghini.me/

[4] https://play.google.com/store/apps/details?id=me.ghini.tour

[5] https://hosted.weblate.org/projects/ghini/#languages

[6] https://www.youtube.com/playlist?list=PLtYRCnAxpinU_8WEDuRlgsYnNVe4J_4kv
