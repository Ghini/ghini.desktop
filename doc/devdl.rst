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
