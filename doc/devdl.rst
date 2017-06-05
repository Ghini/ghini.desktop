Downloading the source
======================

The Ghini source can be downloaded from our source
repository on `github <http://github.com/Ghini/ghini.desktop>`_.

If you want a particular version of Ghini, we release and maintain versions
into branches. You should ``git checkout`` the branch corresponding to the
version of your choice. Branch names for Ghini versions are of the form
``bauble-x.y``, where x.y can be 1.0, for example. Our workflow is to commit
to the `master` development branch or to a `patch` branch and to include the
commits into a `release` branch when ready.

To check out the most recent code from the source repository you will need
to install the `Git <http://www.git.org>`_ version control system. Git is
incuded in all reasonable Linux distributions and can be installed on all
current operating systems.

Once you have installed Git you can checkout the latest Ghini code with
the following command::

        git clone https://github.com/Ghini/ghini.desktop.git

For more information about other available code branches go to
`ghini.desktop on github <http://www.github.com/Ghini/ghini.desktop>`_.


Development Workflow
=============================

production line
-----------------

A bauble production line is a branch. Currently there is only one production
line, that is bauble-1.0.  In perspective, we will have several one, each in
use by one or more gardens.

As long as we have only one production line, I keep working on the master
branch, unless I later realize the work is going to take longer than one or
two days.

batches of simple issues
------------------------------

For issues that can be managed in one or two commits, and as long as there's
no other activity on the repository, work on the master branch, accumulate
issue-solving commits, finally merge master into the production line
bauble-1.0.

larger issues
---------------

When facing a single larger issue, create a branch tag, and follow the
workflow described at

https://git-scm.com/book/en/v2/Git-Branching-Basic-Branching-and-Merging

in short::

    git up
    git checkout -b issue-xxxx
    git push origin issue-xxxx

work on the new branch. When ready, go to github, merge the branch with
master, solve conflicts where necessary, delete the temporary branch.

when ready for publication, merge master into the production line.

Updating the set of translatable strings
==============================================

From time to time, during the process of updating the software, you will be
adding or modifying strings in the python sources, in the documentation, in
the glade sources. Most of our strings are translatable, and are offered to
weblate for people to contribute, in the form of several ``.po``
files. These ``po`` files receive contributions from weblate, and offer
lines without translation from new lines of code.

We have organized the translation of ghini as two separate repositories in
github, each repository being associated to sections of the same project on
weblate. Translation of the software is in ghini.desktop, the software
project, while translation of the documentation —itself part of the
software— is in a separate project, ghini.desktop-docs.i18n.

To update the ``po`` files relative to the software, you run a script from
the project root dir::

  ./scripts/i18n.sh

This will update your ``po`` files, something you need commit and push to
github.

To update the ``po`` filese relative to the documentation, you need a
up-to-date checkout of both projects. The root directory of the 
ghini.desktop-docs.i18n project contains a script with an all telling name::

  runme



Adding missing unit tests
====================================

If you are interested contributing to development of Ghini, a good way to
do so would be by helping us finding and writing the missing unit tests.

A well tested function is one whose behaviour you cannot change without
breaking at least one unit test.

We all agree that in theory theory and practice match perfectly and that one
first writes the tests, then implements the function. In practice, however,
practice does not match theory and we have been writing tests after writing
and even publishing the functions.

This section describes the process of adding unit tests for
``bauble.plugins.plants.family.remove_callback``.

What to test
------------------------

First of all, open the coverage report index, and choose a file with low
coverage.

For this example, run in October 2015, we landed on
``bauble.plugins.plants.family``, at 33%.

https://coveralls.io/builds/3741152/source?filename=bauble%2Fplugins%2Fplants%2Ffamily.py

The first two functions which need tests, ``edit_callback`` and
``add_genera_callback``, include creation and activation of an object
relying on a custom dialog box. We should really first write unit tests for
that class, then come back here.

The next function, ``remove_callback``, also activates a couple of dialog
and message boxes, but in the form of invoking a function requesting user
input via yes-no-ok boxes. These functions we can easily replace with a
function mocking the behaviour.

how to test
--------------------------

So, having decided what to describe in unit test, we look at the code and we
see it needs discriminate a couple of cases:

**parameter correctness**
  * the list of families has no elements.
  * the list of families has more than one element.
  * the list of families has exactly one element.

**cascade**
  * the family has no genera
  * the family has one or more genera

**confirm**
  * the user confirms deletion
  * the user does not confirm deletion

**deleting**
  * all goes well when deleting the family
  * there is some error while deleting the family

I decide I will only focus on the **cascade** and the **confirm**
aspects. Two binary questions: 4 cases.

where to put the tests
-----------------------------------

Locate the test script and choose the class where to put the extra unit tests.

https://coveralls.io/builds/3741152/source?filename=bauble%2Fplugins%2Fplants%2Ftest.py#L273

.. note:: The ``FamilyTests`` class contains a skipped test, implementing it
          will be quite a bit of work because we need rewrite the
          FamilyEditorPresenter, separate it from the FamilyEditorView and
          reconsider what to do with the FamilyEditor class, which I think
          should be removed and replaced with a single function.

writing the tests
------------------------------

After the last test in the FamilyTests class, I add the four cases I want to
describe, and I make sure they fail, and since I'm lazy, I write the most
compact code I know for generating an error::

        def test_remove_callback_no_genera_no_confirm(self):
            1/0

        def test_remove_callback_no_genera_confirm(self):
            1/0

        def test_remove_callback_with_genera_no_confirm(self):
            1/0

        def test_remove_callback_with_genera_confirm(self):
            1/0

One test, step by step
---------------------------------

Let's start with the first test case.

When writing tests, I generally follow the pattern: 

* T₀ (initial condition), 
* action, 
* T₁ (testing the result of the action given the initial conditions)

.. note:: There's a reason why unit tests are called unit tests. Please
          never test two actions in one test.

So let's describe T₀ for the first test, a database holding a family without
genera::

        def test_remove_callback_no_genera_no_confirm(self):
            f5 = Family(family=u'Arecaceae')
            self.session.add(f5)
            self.session.flush()

We do not want the function being tested to invoke the interactive
``utils.yes_no_dialog`` function, we want ``remove_callback`` to invoke a
non-interactive replacement function. We achieve this simply by making
``utils.yes_no_dialog`` point to a ``lambda`` expression which, like the
original interactive function, accepts one parameter and returns a
boolean. In this case: ``False``::

        def test_remove_callback_no_genera_no_confirm(self):
            # T_0
            f5 = Family(family=u'Arecaceae')
            self.session.add(f5)
            self.session.flush()

            # action
            utils.yes_no_dialog = lambda x: False
            from bauble.plugins.plants.family import remove_callback
            remove_callback(f5)

Next we test the result.

Well, we don't just want to test whether or not the object Arecaceae was
deleted, we also should test the value returned by ``remove_callback``, and
whether ``yes_no_dialog`` and ``message_details_dialog`` were invoked or
not.

A ``lambda`` expression is not enough for this. We do something apparently
more complex, which will make life a lot easier.

Let's first define a rather generic function::

    def mockfunc(msg=None, name=None, caller=None, result=None):
        caller.invoked.append((name, msg))
        return result

and we grab ``partial`` from the ``functools`` standard module, to partially
apply the above ``mockfunc``, leaving only ``msg`` unspecified, and use this
partial application, which is a function accepting one parameter and
returning a value, to replace the two functions in ``utils``. The test
function now looks like this::

    def test_remove_callback_no_genera_no_confirm(self):
        # T_0
        f5 = Family(family=u'Arecaceae')
        self.session.add(f5)
        self.session.flush()
        self.invoked = []

        # action
        utils.yes_no_dialog = partial(
            mockfunc, name='yes_no_dialog', caller=self, result=False)
        utils.message_details_dialog = partial(
            mockfunc, name='message_details_dialog', caller=self)
        from bauble.plugins.plants.family import remove_callback
        result = remove_callback([f5])
        self.session.flush()

The test section checks that ``message_details_dialog`` was not invoked,
that ``yes_no_dialog`` was invoked, with the correct message parameter, that
Arecaceae is still there::

        # effect
        self.assertFalse('message_details_dialog' in
                         [f for (f, m) in self.invoked])
        self.assertTrue(('yes_no_dialog', u'Are you sure you want to '
                         'remove the family <i>Arecaceae</i>?')
                        in self.invoked)
        self.assertEquals(result, None)
        q = self.session.query(Family).filter_by(family=u"Arecaceae")
        matching = q.all()
        self.assertEquals(matching, [f5])

And so on
-------------------------

    `there are two kinds of people, those who complete what they start, and
    so on`

Next test is almost the same, with the difference that the
``utils.yes_no_dialog`` should return ``True`` (this we achieve by
specifying ``result=True`` in the partial application of the generic
``mockfunc``). 

With this action, the value returned by ``remove_callback`` should be
``True``, and there should be no Arecaceae Family in the database any more::

    def test_remove_callback_no_genera_confirm(self):
        # T_0
        f5 = Family(family=u'Arecaceae')
        self.session.add(f5)
        self.session.flush()
        self.invoked = []

        # action
        utils.yes_no_dialog = partial(
            mockfunc, name='yes_no_dialog', caller=self, result=True)
        utils.message_details_dialog = partial(
            mockfunc, name='message_details_dialog', caller=self)
        from bauble.plugins.plants.family import remove_callback
        result = remove_callback([f5])
        self.session.flush()

        # effect
        self.assertFalse('message_details_dialog' in
                         [f for (f, m) in self.invoked])
        self.assertTrue(('yes_no_dialog', u'Are you sure you want to '
                         'remove the family <i>Arecaceae</i>?')
                        in self.invoked)
        self.assertEquals(result, True)
        q = self.session.query(Family).filter_by(family=u"Arecaceae")
        matching = q.all()
        self.assertEquals(matching, [])

have a look at commit 734f5bb9feffc2f4bd22578fcee1802c8682ca83 for the other
two test functions.

Putting all together
--------------------------

From time to time you want to activate the test class you're working at::

    nosetests bauble/plugins/plants/test.py:FamilyTests

And at the end of the process you want to update the statistics::

    ./scripts/update-coverage.sh


Plugins structure
=============================

Ghini is a framework for handling collections, and is distributed along
with a set of plugins making Ghini a botanical collection manager. But
Ghini stays a framework and you could in theory remove all plugins we
distribute and write your own, or write your own plugins that extend or
complete the current Ghini behaviour.

Once you have selected and opened a database connection, you land in the
Search window. The Search window is an interaction between two objects:
SearchPresenter (SP) and SearchView (SV).

SV is what you see, SP holds the program status and handles the requests you
express through SV. Handling these requests affect the content of SV and the
program status in SP.

The search results shown in the largest part of SV are rows, objects that
are instances of classes registered in a plugin.

Each of these classes must implement an amount of functions in order to
properly behave within the Ghini framework. The Ghini framework reserves
space to pluggable classes.

SP knows of all registered (plugged in) classes, they are stored in a
dictionary, associating a class to its plugin implementation.  SV has a slot
(a gtk.Box) where you can add elements. At any time, at most only one
element in the slot is visible.

A plugin defines one or more plugin classes. A plugin class plays the role
of a partial presenter (pP - plugin presenter) as it implement the callbacks
needed by the associated partial view fitting in the slot (pV - plugin
view), and the MVP pattern is completed by the parent presenter (SP), again
acting as model. To summarize and complete:

* SP acts as model,
* the pV partial view is defined in a glade file.
* the callbacks implemented by pP are referenced by the glade file.
* a context menu for the SP row,
* a children property.

when you register a plugin class, the SP:

* adds the pV in the slot and makes it non-visible.
* adds an instance of pP in the registered plugin classes.
* tells the pP that the SP is the model.
* connects all callbacks from pV to pP.

when an element in pV triggers an action in pP, the pP can forward the
action to SP and can request SP that it updates the model and refreshes the
view.

When the user selects a row in SP, SP hides everything in the pluggable slot
and shows only the single pV relative to the type of the selected row, and
asks the pP to refresh the pV with whatever is relative to the selected row.

Apart from setting the visibility of the various pV, nothing needs be
disabled nor removed: an invisible pV cannot trigger events!

