Developer's Manual
========================

helping bauble development
--------------------------

Installing Bauble always includes downloading the sources, connected to the
github repository. This is so because in our eyes, every user is always
potentially also a developer.

If you want to contribute to Bauble, you can do so in quite a few different ways::

 * use the software, note the things you don't like, open issue for each of them. a developer will react.
 * if you have an idea of what you miss in the software but can't quite
   formalize it into separate issues, you could consider hiring a
   professional. this is the best way to make sure that something happens
   quickly on Bauble. do make sure the developer opens issues and publishes
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

structure of user interface
------------------------------------

the user interface is built according to the Model-View-Presenter
architectural pattern.  The **view** is described in a glade file and is
totally dumb, you do not subclass it because it implements no behaviour and
because its appearance is, as said, described elsewhere, including the
association signal-callbacks. The **model** simply follows the sqlalchemy
practices. 

You will subclass the **presenter** in order to:

* define ``widget_to_field_map``, the association from name of view object
  to name of model attribute,
* override ``view_accept_buttons``, the list of widget names which, if
  activated by the user, mean that the view should be closed,
* define all needed callbacks,

The presenter should not know of the internal structure of the view,
instead, it should use the view api to set and query the values inserted by
the user. The base class for the presenter, ``GenericEditorPresenter``
defined in ``bauble.editor``, implements many generic callbacks.

Model and Presenter can be unit tested, not the View.

The ``Tag`` plugin is a good minimal example, even if the ``TagItemGUI``
falls outside this description. Other plugins do not respect the
description.

We use the same architectural pattern for non-database interaction, by
setting the presenter also as model. We do this, for example, for the JSON
export dialog box.

building (on Windows)
---------------------

Building a python program is a bit of a contraddiction.  You don't normally
*build* nor *compile* a python program, you run it in its (virtual) environment, and
python will process the modules loaded and produce faster-loading *compiled*
python files.  You can, however, produce a *Windows executable* from a python
script, executable containing the whole python environment and dependencies.

1. Follow all steps needed to set up a working Bauble environment from
   :doc:`installing`, but skip the final ``install`` step.

2. instead of *installing* Bauble, you produce a Windows executable.  This
   is achieved with the ``py2exe`` target, which is only available on
   Windows systems::

		 python setup.py py2exe

3. At this point you can run Bauble.  To run the compiled executable run::

		.\dist\bauble.exe

   or copy the executable to wherever you think appropriate.

4. To optionally build an NSIS installer package you must install NSIS
   from `nsis.sourceforge.net
   <http://nsis.sourceforge.net/Download>`_.  After installing NSIS
   right click on ``.\scripts\build.nsi`` in Explorer and select
   *Compile NSIS Script*.
