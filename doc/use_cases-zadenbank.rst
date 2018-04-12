seed database? why do you need a separate database?
-------------------------------------------------------

We got involved in a group focusing on endagered plant seeds.  They want to
note down when seeds come in, but also when they go out to people that order
the seed.  They ask whether ghini could be used.

..  admonition:: Does ghini need being adapted for such a seed database?
    :class: toggle

       interesting, and yes you can use ghini, and no it doesn't need any
       adaptation, just you need to read some of its terms differently.

       the taxonomy part is just taxonomy, plant species information, no need to
       explain that, no way to interpret it otherwise.

       Accessions and Plants, you know what an accession is, but since
       you're consistently handling plants still only in seed form, the
       Wikipedia explanation of an accession sounds like this: it is a seed
       or group of seeds that are of the same taxon, are of the same
       propagule type (or treatment), were received from the same source,
       were received at the same time.

       I guess that your group holds seeds in jars, or in other sort of
       containers that is able to hold hundreds of seeds, and that you keep
       these seed containers in larger containers.  For ease of reasoning,
       let me call the smaller container a jar.  Each jar is one of ghini's
       »plant groups«, which we call plant, or planting.  The larger
       container-container would be one of ghini's Locations.

       You understand that a jar contains seeds of just one accession, as
       above described: same taxon, same treatment, same source, same time.

       that is, it's a plant within an accession, and has multiplicity
       (quantity) as much as the amount of seeds.

..  admonition:: How do I handle receiving a batch of seeds?
    :class: toggle

       .. note:: When we receive seeds, we either collect them ourselves, or
                 we receive it from an other seed collector.  We handle
                 receiving them possibly on the spot, or with a small delay.
                 Even when handled together with several other batches of
                 seeds we received, each batch keeps its individuality.
       
                 We want to be later able to find back, for example, how
                 many seeds we still have from a specific batch, or when we
                 last received seeds from a specific source.

       As long as you put this information in the database, as long as you
       follow the same convention when doing so, you will be able to write
       and execute such queries using ghini.

       One possibility, the one described here, is based on notes.  (Ghini
       does not, as yet, implement the concept "Acquisition". There is an
       issue related to the Acquisition and Donation objects, but we haven't
       quite formalized things yet.)

       You surely already use codes to identify a batch of seeds entering
       the seed bank.  Just copy this code in a note, category 'received',
       to each accession in the received batch.  This will let you select
       the accessions by the query::

         accession where notes[category='received'].note='<your code>'

       Use the 'Source' tab if you think so, it offers space for indicating
       an external source, or an expedition.  When receiving from an
       external source, you can specify the code internal to their
       organization.  This will be useful when requesting an extra batch.

..  admonition:: How do I handle sending seeds?
    :class: toggle

       you then grab an amount
       of seeds from the batch, and put it in a bag. this becomes a new
       planting within the accession. a standard operation.

..  admonition:: When I send seeds, it's not just one bag, how does ghini help me keeping things together?
    :class: toggle

       

I've just run a tiny test, and I think this is quite usable
-------------------------------------------------------------
what I did ... enter a few species (Urtica dioica, Zea mays), and asked the plant list to help me with spelling and authorship.
I enter an accession (and plant, from the accession), by following the steps:

1) make sure we have locations (drawers for seed jars)
2) add accession, seeds, 300, put in drawer 1,
3) add plant (but this goes automatically): when adding the accession, I specify that all plant material should go into planting &lt;acc_no&gt;.1, that's 300 seeds/spores. — I don't need open the plant editor.

I have several more jars with seeds in drawer 1.

now someone calls your people and wants 30 seeds of Urtica dioica, and 30 of Zea mays and 20 of Oryza sativa and 30 of Panicum maximum, and I first of all check that I have enough of each.

this step goes by creating a Tag, and make it the default tag.  While I check the quantities, that is I make sure that there's a jar with enough seeds of the desired species. Remember: a jar is a plant, not an accession, and I suggest tagging the accession to which the jar belongs, this will show more information at a later step.

know I have enough of all of them, what accession number it is, and I know in which drawer to find them.

I prepare the envelopes, writing on them the species name, the quantity, the accession number, and the drawer,
so I go to the drawers, per envelope I grab the corresponding jar with the right accession number, collect the desired amount of seeds, put them in the envelope, and when done for all envelopes, I go back to the database.

at the database, I select the Tag I just created, this brings all jars I used in the results list.
I need to expand the Tag, so the accessions show in the results list. I do this by clicking on the triangle next to it.  next I expand the accession, to show the jar and all past envelopes associated to it (jar is the one ending in '.1', all others are later envelopes)
now I right click on the first plant (the jar) in the list which came out of the expansion of the accession line.
a menu shows, and one of the options is 'split', which I choose.
a plant editor window comes in view, in 'split mode'.
this one lets me create a database image of the plant group I just physically created, that is, it lets me subtract 30 items from plant group number one, the one in the jar, and annotate it as a new plant group, in an envelope.
location I would say that the new envelop is in the 'out box', on its way to leave the garden.

final step, it represents the physical step of sending the envelope, possibly together with several other envelopes, in a sending, which should have a code.
ghini does not offer this as an object, but you can make it a note in the various new plantings you just created.
that is: when you split each of the jar collections, creating the various envelopes you're about to send, you should add a note, marking the code of the sending, or the person to whom you're sending, or whatever you do to identify a sending.
(in my tiny test, I added a note with category 'sold' and note text '2018-0061')
there's one step which is even less practical, but we can work at it…
when you finally do send the envelopes, you need to bring to 0 all quantities within your database. they're not any more available to you, after you send them!
you have to do this one by one, there's no shortcuts.
you can select the plants with something like... 
plant where notes[category='sold'].note = '2018-0061'
then set the quantity to zero, marking the fact that the envelopes were physically sent.

If you make a report you would be able to see when the seed entered, how much seed still in stock and all the people that have received seed with quantity. And what if they want to keep seed from every plant seperate? What kind of accession would you give...?

seeds from each species is separate, yes.
if you want to produce a report, please show how the report should look like, so I can write the template.
what do you mean with "to keep seed from every plant separate"?

Yes and if you have for example an orchid field and from this field you collect the seed from each individual plant because the plant is endangered. What type of accession number would you give? And what would happen if you collect seed every year. I think they want to keep each individual seperate as far as I have understood up till now.
Are seed accession numbers done in the same way as plants?
It is not yet so clear how they want to work.
Could I propose ghini en wat zijn jouw voorwaarden? Als die er zijn?

check the text I wrote for the wikipedia, what is an accession.

But are seeds and plants the same according to you.
I will read first....

I accept gifts, and material.
there aren't such further conditions. it depends if you're making money with it, then I would like to see some myself, and I need to get good review, and continuous feedback.
yes a seed and a plant are both plant material.  I don't see a difference.

No money I thought name...

if you collect 10 plants in a field, not only same species, but all from the same population, all at the same time, I would put them all in the same accession.
if you collect 500 seeds next to that, then it's a different form so it's a second accession, quantity: 500, material: seed.

That is not what they want, every individual they want the seed tobe kept seperate.

that's terrible overkill.
that's plants, not accessions.

Maybe not for endagered plants.

by separating them in different accession, you are missing the chance of building a common history for similar plants.
I think this idea comes from not having completely understood what is an accession
please do check the text I wrote for the wikipedia, and follow the link to my source. it's an old pdf from an Irish garden.

Not possible to give an extra number with the accession number?

that's already the way it works
the extra number behind the accession number is the plant code.
it's how the MoBot suggests, how BG-Recorder does, and how we do, too.

That could solve the problem.

problem, which I don't see. <span class="emoji  emoji-spritesheet-0" style="background-position: -396px -0px;" title="joy">:joy:</span>

If you start travelling you cannot always help, that could be an issue.
Maybe they are going to develop their own thing. What does ghini work on name software? Something that I can tell them to trigger interest?
Or is all this also written on your site?

I think I'm always connected, except while sitting in a bus, or air plane.  or while doing shopping.  but I've the feeling I'm always connected.
I don't think that developing their own thing will spare them time
complaining about things missing in ghini will help others with the same needs
developing their own thing will not do that

So what kind of programme is ghini working....something interesting to trigger interest?
wait, there should be a nice article from the Böll foundation, it's in German, but all Dutch read Duits, toch?
sorry, me not understand 'what programme is ghini working'
can't parse the grammar of the sentence

Is it java....with what is it made?
Trigger interest what can I say?

ah. that. it's written in Python, it is cross platform, it uses industry standard SQLAlchemy, it lets you choose what database server you prefer, it's GPL (free as in free speech),
it's actively supported

Yes that is what I want to hear...

it couples with a web server for garden visibility, and with a handheld Android app to ease data entry.
I think all written in the docs, if you look for it.
or in <a href="http://ghini.github.io" target="_blank" rel="noopener noreferrer">http://ghini.github.io</a>

I'm looking for a publication by the Böll foundation, about "why the public sector should care for free software".
This time it is collecting wild plants not botanical garden plants?
From different locations in the netherlands?
And if they are interested what would you ask for your work, besides myself helping to get the work.
Een uur tarief????
weet ik veel, een uurtarief? kijk, in Nederland kost ik niet minder dan zo'n 20€ per uur... dat wil in niet vragen, maar zou ik ook niet weigeren.
I am also living from air just like you...
I'm living of the house in Pisa, and of gifts I receive.
I am living from kleine erfenis van mijn vader...
I generally tune my request to the availability.  the ARM was paying me, how much was it... was it 50€ each worked Saturday, 5 hours in the kelder?
and it was marked as a gift and I was not paying taxes on that.  I would be quite happy with that.  it would definitely contribute to expenses.
I think that was the maximum they were allowed to give, free of taxes.  I would definitely accept that.
I have been reacting even for a testing pendel van eten...je wordt niet uigenodigd.
oeps
you should apply for fixing bikes, very enjoyable.  you dirty your fingers and it won't come off for days, but it's enjoyable work.
just the thought of it feels good.
Kleur, smaak en textuur...van eten leek mij wat. Vogels ringen, natuur medewerker, admin werker, receptioniste, secretaresse, postbode....ga maar zo door maar niets...
anyhow, if you want to mention, that a professional software developer is available at give-away price, because he decided he would move to a 'lageloonland' and reduce his needs, work next to a hammock, and always have fresh fruit juice on his table, and temperature of 35°C day after day all year round.
next month I will be house-sitting at Loes &amp; Kees. they will travel to NL.  means saving money on housing.
lunch time!
Maar als ik de database werkgroep mensen vraag hoe ver ze zijn. Wat zou ik kunnen vragen als interessante vragen?kan jij mij dit nog laten weten....interessante vragen. Dit is de eerste keer dat zij bij elkaar zijn. Ik zit zelf niet in deze groeo maar kan wel vragen hoe het gaat in hun werkgroep?
Dus heb je een idee voor goede vragen? Laat het mij weten?
<a href="http://www.botanicgardens.ie/educ/accnosho.pdf" target="_blank" rel="noopener noreferrer">http://www.botanicgardens.ie/educ/accnosho.pdf</a>
<a href="https://en.wikipedia.org/wiki/Accession_number_(library_science)" target="_blank" rel="noopener noreferrer">https://en.wikipedia.org/wiki/Accession_number_(library_science)</a>
I'm thinking, what I would ask to the database work-group within an organization
I guess, just one... do they know which are the processes that play in the organization, that they hope to ease by introducing a database management system.
otherwise, they risk introducing unnecessary complications, things that only add work and don't solve any problem.
I'm thinking of the definition of the concept "solution". How can you speak of "This solves X" if you don't know "X"?
So if you think that Ghini does not solve your botanical problem, you can contribute to Ghini by stating the problem, and have me solve it for you (and all that have the same problem).
