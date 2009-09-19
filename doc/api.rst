API Documentation
------------------------

:mod:`bauble`
=============
.. automodule:: bauble
.. autodata:: bauble.version
.. autodata:: bauble.Session
.. autodata:: bauble.gui
.. autofunction:: bauble.main_is_frozen
.. autofunction:: bauble.save_state
.. autofunction:: bauble.quit
.. autofunction:: bauble.set_busy
.. autofunction:: bauble.command_handler
.. autofunction:: bauble.main


:mod:`bauble.db`
================
.. automodule:: bauble.db
.. autodata:: bauble.db.engine
.. autodata:: bauble.db.Base
.. autodata:: bauble.db.metadata
.. autoclass:: bauble.db.MapperBase
   :show-inheritance:
   :members:

.. autofunction:: bauble.db.open
.. autofunction:: bauble.db.create


:mod:`bauble.connmgr`
=======================
.. automodule:: bauble.connmgr


:mod:`bauble.editor`
=======================
.. automodule:: bauble.editor
.. autofunction:: bauble.editor.default_completion_cell_data_func
.. autofunction:: bauble.editor.default_completion_match_func
.. autoclass:: bauble.editor.StringOrNoneValidator
.. autoclass:: bauble.editor.UnicodeOrNoneValidator
.. autoclass:: bauble.editor.IntOrNoneStringValidator
.. autoclass:: bauble.editor.FloatOrNoneStringValidator
.. autoclass:: bauble.editor.GenericEditorView
   :members:
.. autoclass:: bauble.editor.GenericEditorPresenter
   :members:
.. autoclass:: bauble.editor.GenericModelViewPresenterEditor
   :members:


:mod:`bauble.i18n`
=======================
.. automodule:: bauble.i18n


:mod:`bauble.ui`
=======================
.. automodule:: bauble.ui
.. autoclass:: bauble.ui.GUI
   :show-inheritance:
   :members:


:mod:`bauble.meta`
=======================
.. automodule:: bauble.meta


:mod:`bauble.paths`
=======================
.. automodule:: bauble.paths
.. autofunction:: bauble.paths.main_dir
.. autofunction:: bauble.paths.lib_dir
.. autofunction:: bauble.paths.locale_dir
.. autofunction:: bauble.paths.user_dir


:mod:`bauble.pluginmgr`
=======================
.. automodule:: bauble.pluginmgr
.. autofunction:: bauble.pluginmgr.register_command
.. autofunction:: bauble.pluginmgr.load
.. autofunction:: bauble.pluginmgr.init
.. autofunction:: bauble.pluginmgr.install
.. .. autoclass:: bauble.pluginmgr.RegistryEmptyError
.. .. autoclass:: bauble.pluginmgr.Registry
..   :members:
.. .. autoclass:: bauble.pluginmgr.RegistryEntry
..   :members:
.. autoclass:: bauble.pluginmgr.Plugin
   :members:
.. autoclass:: bauble.pluginmgr.Tool
.. autoclass:: bauble.pluginmgr.View
.. autoclass:: bauble.pluginmgr.CommandHandler
.. .. autofunction:: bauble.pluginmgr.topological_sort


:mod:`bauble.prefs`
=======================
.. automodule:: bauble.prefs


:mod:`bauble.task`
=======================
.. automodule:: bauble.task
.. autofunction:: bauble.task.queue
.. .. autofunction:: bauble.task.flush
.. autofunction:: bauble.task.set_message
.. autofunction:: bauble.task.clear_messages


:mod:`bauble.types`
=======================
.. automodule:: bauble.types

.. autoclass:: bauble.types.Enum
   :show-inheritance:
.. autoclass:: bauble.types.Date
   :show-inheritance:
.. autoclass:: bauble.types.DateTime
   :show-inheritance:



:mod:`bauble.utils`
=======================
.. automodule:: bauble.utils
.. autofunction:: bauble.utils.find_dependent_tables
.. .. autoclass:: bauble.utils.GladeWidgets
..   :members: remove_parent, signal_autoconnect
.. autofunction:: bauble.utils.tree_model_has
.. autofunction:: bauble.utils.search_tree_model
.. autofunction:: bauble.utils.clear_model
.. autofunction:: bauble.utils.combo_set_active_text
.. autofunction:: bauble.utils.set_combo_from_value
.. autofunction:: bauble.utils.combo_get_value_iter
.. autofunction:: bauble.utils.set_widget_value
.. autofunction:: bauble.utils.create_message_dialog
.. autofunction:: bauble.utils.message_dialog
.. autofunction:: bauble.utils.create_yes_no_dialog
.. autofunction:: bauble.utils.yes_no_dialog
.. autofunction:: bauble.utils.create_message_details_dialog
.. autofunction:: bauble.utils.message_details_dialog
.. autofunction:: bauble.utils.setup_text_combobox
.. autofunction:: bauble.utils.setup_date_button
.. autofunction:: bauble.utils.to_unicode
.. autofunction:: bauble.utils.utf8
.. autofunction:: bauble.utils.xml_safe
.. autofunction:: bauble.utils.xml_safe_utf8
.. autofunction:: bauble.utils.natsort_key
.. autofunction:: bauble.utils.delete_or_expunge
.. autofunction:: bauble.utils.reset_sequence
.. autofunction:: bauble.utils.date_to_str
.. autofunction:: bauble.utils.make_label_clickable
.. autofunction:: bauble.utils.enum_values_str



:mod:`bauble.view`
=======================
.. automodule:: bauble.view
.. autoclass:: bauble.view.InfoBox
   :show-inheritance:
   :members: on_switch_page, add_expander, update
.. autoclass:: bauble.view.InfoBoxPage
   :show-inheritance:
   :members: add_expander, get_expander, remove_expander, update
.. autoclass:: bauble.view.InfoExpander
   :show-inheritance:
   :members: set_widget_value, update
.. autoclass:: bauble.view.PropertiesExpander
   :show-inheritance:
   :members: update
.. autoclass:: bauble.view.SearchParser
   :members: parse_string
.. autoclass:: bauble.view.SearchStrategy
   :members:
.. autoclass:: bauble.view.MapperSearch
   :show-inheritance:
   :members: search
.. autoclass:: bauble.view.ResultSet
   :members: add, count, clear
.. autoclass:: bauble.view.SearchView
   :show-inheritance:
.. class:: bauble.view.SearchView.ViewMeta
   


:mod:`bauble.plugins.plants`
============================
.. automodule:: bauble.plugins.plants

.. autoclass:: bauble.plugins.plants.Family
   :show-inheritance: 

.. autoclass:: bauble.plugins.plants.FamilySynonym
   :show-inheritance: 

.. autoclass:: bauble.plugins.plants.Genus
   :show-inheritance: 

.. autoclass:: bauble.plugins.plants.GenusSynonym
   :show-inheritance: 

.. autoclass:: bauble.plugins.plants.Species
   :show-inheritance: 

.. autoclass:: bauble.plugins.plants.SpeciesSynonym
   :show-inheritance: 

.. autoclass:: bauble.plugins.plants.VernacularName
   :show-inheritance: 

.. autoclass:: bauble.plugins.plants.DefaultVernacularName
   :show-inheritance: 

.. autoclass:: bauble.plugins.plants.SpeciesDistribution
   :show-inheritance: 

.. autoclass:: bauble.plugins.plants.Geography
   :show-inheritance: 


:mod:`bauble.plugins.garden`
============================
.. automodule:: bauble.plugins.garden

.. autoclass:: bauble.plugins.garden.Accession
   :show-inheritance: 

.. autoclass:: bauble.plugins.garden.Plant
   :show-inheritance: 

   .. automethod:: bauble.plugins.garden.Plant.get_delimiter()

.. autoclass:: bauble.plugins.garden.Location
   :show-inheritance: 

.. autoclass:: bauble.plugins.garden.Collection
   :show-inheritance: 

.. autoclass:: bauble.plugins.garden.Donation
   :show-inheritance: 

.. autoclass:: bauble.plugins.garden.Donor
   :show-inheritance: 

:mod:`bauble.plugins.abcd`
==========================
.. automodule:: bauble.plugins.abcd

:mod:`bauble.plugins.imex`
==========================
.. automodule:: bauble.plugins.imex

:mod:`bauble.plugins.report`
============================
.. automodule:: bauble.plugins.report

:mod:`bauble.plugins.report.xsl`
====================================
.. automodule:: bauble.plugins.report.xsl

:mod:`bauble.plugins.report.mako`
=====================================
.. automodule:: bauble.plugins.report.mako

:mod:`bauble.plugins.tag`
=========================
.. automodule:: bauble.plugins.tag
