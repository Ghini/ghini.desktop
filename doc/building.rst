Developer's Manual
========================

helping bauble development
--------------------------

Installing Ghini always includes downloading the sources, connected to the
github repository. This is so because in our eyes, every user is always
potentially also a developer.

If you want to contribute to Ghini, you can do so in quite a few different ways:

 * use the software, note the things you don't like, open issue for each of them. a developer will react.
 * if you have an idea of what you miss in the software but can't quite
   formalize it into separate issues, you could consider hiring a
   professional. this is the best way to make sure that something happens
   quickly on Ghini. do make sure the developer opens issues and publishes
   their contribution on github.
 * translate! any help with translations will be welcome, so please do! you
   can do this without installing anything on your computer, just using the
   on-line translation service offered by http://hosted.weblate.org/
 * fork the respository, choose an issue, solve it, open a pull request. see
   the `bug solving workflow`_ below.

bug solving workflow
--------------------

normal development workflow
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* while using the software, you notice a problem, or you get an idea of
  something that could be better, you think about it good enough in order to
  have a very clear idea of what it really is, that you noticed. you open an
  issue and describe the problem. someone might react with hints.
* you open the issues site and choose one you want to tackle.
* assign the issue to yourself, this way you are informing the world that
  you have the intention to work at it. someone might react with hints.
* optionally fork the repository in your account and preferably create a
  branch, clearly associated to the issue.
* write unit tests and commit them to your branch (do not commit failing
  unit tests to the ``master`` branch).
* write more unit tests (ideally, the tests form the complete description of
  the feature you are adding or correcting).
* make sure the feature you are adding or correcting is really completely
  described by the unit tests you wrote.
* make sure your unit tests are atomic, that is, that you test variations on
  changes along one single variable. do not give complex input to unit
  tests or tests that do not fit on one screen (25 lines of code).
* write the code that makes your tests succeed.
* update the i18n files (run ``./scripts/i18n.sh``).
* whenever possible, translate the new strings you put in code or glade
  files.
* commit your changes.
* push to github.
* open a pull request.

publishing to production
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* open the pull request page using as base the production line, compared to
  ``master``.
* make sure a ``bump`` commit is included in the differences.
* it should be possible to automatically merge the branches.
* create the new pull request, call it as “publish to the production line”.
* you possibly need wait for travis-ci to perform the checks.
* merge the changes.
* tell the world about it: on facebook, the google group, linkedin, ...

closing step
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* review this workflow. consider this as a guideline, to yourself and to
  your colleagues. please help make it better and matching the practice.
