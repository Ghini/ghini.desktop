Structure of user interface
------------------------------------

The user interface is built according to the Model-View-Presenter
architectural pattern.  In theory, but also in the practice of all new parts
of the software:

* The **view** is described as part of a **glade** file. This includes the
  signal-callback associations. The base class is ``GenericEditorView``
  defined in ``bauble.editor``. Create an instance of the base class,
  passing it the **glade** file name and the root widget name, then handle
  the instance to the **presenter** constructor.

* The **model** simply follows the sqlalchemy practices. The **presenter**
  continuously updates it according to changes in the **view**. The
  **presenter** commits all **model** updates to the database if the
  **view** is closed successfully, or rolls them back if the **view** is
  canceled.

* The subclassed **presenter** defines and implements:

  * ``widget_to_field_map``, the association from widget name to name of
    model attribute,
  * ``view_accept_buttons``, the list of widget names which, if
    activated by the user, mean that the view should be closed,
  * all needed callbacks,
  * optionally, it plays the **model** role, too.

A well behaved **presenter** uses the **view** api to query the values
inserted by the user or to forcibly set widget statuses. Please do not learn
from the practice in our older presenters, most of which directly handle
widgets, something that prevents us from writing unit tests.

There is no way to unit test a subclassed view, so please don't subclass views.

The base class for the presenter, ``GenericEditorPresenter`` defined in
``bauble.editor``, implements many useful generic callbacks.

We use the same architectural pattern for non-database interaction, by
setting the presenter also as model. We do this, for example, for the JSON
export dialog box. The following command will give you a list of
``GenericEditorView`` instantiations::

  grep -nHr -e GenericEditorView\( bauble

An other good example of Presenter/View pattern (no model) is given by the
connection manager.

Extending Ghini with Plugins
-----------------------------

Nearly everything about Ghini is extensible through plugins. Plugins
can create tables, define custom searchs, add menu items, create
custom commands and more.

To create a new plugin you must extend the ``bauble.pluginmgr.Plugin``
class.

The ``Tag`` plugin is a good minimal example, even if the ``TagItemGUI``
falls outside the Model-View-Presenter architectural pattern.
