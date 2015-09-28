Extending Bauble with Plugins
-----------------------------

Nearly everything about Bauble is extensible through plugins. Plugins
can create tables, define custom searchs, add menu items, create
custom commands and more.

To create a new plugin you must extend the ``bauble.pluginmgr.Plugin``
class.


structure of user interface
------------------------------------

the user interface is built according to the Model-View-Presenter
architectural pattern.  The **view** is described in a **glade** file and is
totally dumb, you do not subclass it because it implements no behaviour and
because its appearance is, as said, described elsewhere (the **glade** file), including the
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

A good example of Presenter/View pattern (no model) is given by the
connection manager.

We use the same architectural pattern for non-database interaction, by
setting the presenter also as model. We do this, for example, for the JSON
export dialog box.
