Downloading the source
======================

The Bauble source can be downloaded from our source
repository on `github <http://github.com/Bauble/bauble.classic>`_.

If you want a particular version of Bauble, we release and maintain versions
into branches. you should ``git checkout`` the branch corresponding to the
version of your choice. Branch names for Bauble versions are of the form
``bauble-x.y``, where x.y can be 1.0, for example. Our workflow is to commit
to the `master` development branch or to a `patch` branch and to include the
commits into a `release` branch when ready.

To check out the most recent code from the source repository you will need
to install the `Git <http://www.git.org>`_ version control system. Git is
incuded in all reasonable Linux distributions and can be installed on all
current operating systems.

Once you have installed Git you can checkout the latest Bauble code with
the following command::

        git clone https://github.com/Bauble/bauble.classic.git

For more information about other available code branches go to
`bauble.classic on github <http://www.github.com/Bauble/bauble.classic>`_.


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

work on the new branch. when ready, go to github, merge the branch with
master, solve conflicts where necessary, delete the temporary branch.

when ready for publication, merge master into the production line.

Plugins structure
=============================

Bauble is a framework for handling collections, and is distributed along
with a set of plugins making Bauble a botanical collection manager. But
Bauble stays a framework and you could in theory remove all plugins we
distribute and write your own, or write your own plugins that extend or
complete the current Bauble behaviour.

Once you have selected and opened a database connection, you land in the
Search window. The Search window is an interaction between two objects:
SearchPresenter (SP) and SearchView (SV).

SV is what you see, SP holds the program status and handles the requests you
express through SV. Handling these requests affect the content of SV and the
program status in SP.

The search results shown in the largest part of SV are rows, objects that
are instances of classes registered in a plugin.

Each of these classes must implement an amount of functions in order to
properly behave within the Bauble framework. The Bauble framework reserves
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

