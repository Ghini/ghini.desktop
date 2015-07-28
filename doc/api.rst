API Documentation
------------------------

:mod:`bauble`
=============
.. automodule:: bauble
.. autodata:: bauble.version
.. autodata:: bauble.gui
.. autofunction:: bauble.command_handler
.. autofunction:: bauble.main
.. autofunction:: bauble.main_is_frozen
.. autofunction:: bauble.quit
.. autofunction:: bauble.save_state


:mod:`bauble.db`
================
.. automodule:: bauble.db
.. autodata:: bauble.db.Session
.. autodata:: bauble.db.engine
.. autodata:: bauble.db.Base
.. py:data:: bauble.db.Base

   All tables/mappers in Bauble which use the SQLAlchemy declarative
   plugin for declaring tables and mappers should derive from this
   class.

   An instance of :class:`sqlalchemy.ext.declarative.Base`

.. autoattribute:: bauble.db.metadata
.. py:data:: bauble.db.metadata

   The default metadata for all Bauble tables.

   An instance of :class:`sqlalchemy.schema.MetaData`

.. autoclass:: bauble.db.MapperBase
.. autoclass:: bauble.db.HistoryExtension
   :show-inheritance:
   :members:
.. autoclass:: bauble.db.History
   :show-inheritance:
.. autofunction:: bauble.db.open
.. autofunction:: bauble.db.create
.. autofunction:: bauble.db.verify_connection


:mod:`bauble.connmgr`
=======================
.. automodule:: bauble.connmgr
.. autoclass:: bauble.connmgr.ConnectionManager
   :show-inheritance:
   :members:


:mod:`bauble.editor`
=======================
.. automodule:: bauble.editor
.. autofunction:: bauble.editor.default_completion_cell_data_func
.. autofunction:: bauble.editor.default_completion_match_func
.. autoclass:: bauble.editor.ValidatorError
.. autoclass:: bauble.editor.Validator
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
.. autoclass:: bauble.editor.NotesPresenter
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
.. autofunction:: bauble.meta.get_default
.. autoclass:: bauble.meta.BaubleMeta
   :show-inheritance:


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
.. autoclass:: bauble.pluginmgr.Plugin
   :members:
.. autoclass:: bauble.pluginmgr.Tool
.. autoclass:: bauble.pluginmgr.View
.. autoclass:: bauble.pluginmgr.CommandHandler


:mod:`bauble.prefs`
=======================
.. automodule:: bauble.prefs
.. autodata:: bauble.prefs.default_prefs_file
.. autodata:: bauble.prefs.config_version_pref
.. autodata:: bauble.prefs.date_format_pref
.. autodata:: bauble.prefs.parse_dayfirst_pref
.. autodata:: bauble.prefs.parse_yearfirst_pref
.. autodata:: bauble.prefs.units_pref


:mod:`bauble.task`
=======================
.. automodule:: bauble.task
.. autofunction:: bauble.task.queue
.. autofunction:: bauble.task.set_message
.. autofunction:: bauble.task.clear_messages


:mod:`bauble.types`
=======================
.. automodule:: bauble.btypes

.. autoclass:: bauble.btypes.Enum
   :show-inheritance:
.. autoclass:: bauble.btypes.Date
   :show-inheritance:
.. autoclass:: bauble.btypes.DateTime
   :show-inheritance:



:mod:`bauble.utils`
=======================
.. automodule:: bauble.utils
.. autofunction:: bauble.utils.find_dependent_tables
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
.. autofunction:: bauble.utils.make_label_clickable
.. autofunction:: bauble.utils.enum_values_str
.. autofunction:: bauble.utils.which
.. autofunction:: bauble.utils.ilike
.. autofunction:: bauble.utils.range_builder
.. autofunction:: bauble.utils.topological_sort
.. autofunction:: bauble.utils.get_distinct_values
.. autofunction:: bauble.utils.get_invalid_columns
.. autofunction:: bauble.utils.get_urls

.. autoclass:: GenericMessageBox
   :show-inheritance:
   :members:

.. autoclass:: MessageBox
   :show-inheritance:
   :members:

.. autoclass:: YesNoMessageBox
   :show-inheritance:
   :members:
.. autofunction:: bauble.utils.add_message_box


:mod:`bauble.view`
==================
.. automodule:: bauble.view
.. autoclass:: bauble.view.Action
   :show-inheritance:
   :members:
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
.. autoclass:: bauble.view.LinksExpander
   :show-inheritance:
   :members: update
.. autoclass:: bauble.view.SearchView
   :show-inheritance:
.. class:: bauble.view.SearchView.ViewMeta
   

:mod:`bauble.search`
====================
.. autoclass:: bauble.search.SearchParser
   :members: parse_string
.. autoclass:: bauble.search.SearchStrategy
   :members:
.. autoclass:: bauble.search.MapperSearch
   :show-inheritance:
   :members: search
.. autoclass:: bauble.search.QueryBuilder
   :show-inheritance:


:mod:`bauble.plugins.plants`
============================
.. automodule:: bauble.plugins.plants

.. autoclass:: bauble.plugins.plants.Family
   :show-inheritance: 

.. autoclass:: bauble.plugins.plants.family.FamilySynonym
   :show-inheritance: 

.. autoclass:: bauble.plugins.plants.Genus
   :show-inheritance: 

.. autoclass:: bauble.plugins.plants.genus.GenusSynonym
   :show-inheritance: 

.. autoclass:: bauble.plugins.plants.Species
   :show-inheritance: 

.. autoclass:: bauble.plugins.plants.species.SpeciesSynonym
   :show-inheritance: 

.. autoclass:: bauble.plugins.plants.species.VernacularName
   :show-inheritance: 

.. autoclass:: bauble.plugins.plants.species.DefaultVernacularName
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
.. autoclass:: bauble.plugins.garden.accession.AccessionNote
   :show-inheritance: 
.. autoclass:: bauble.plugins.garden.Plant
   :show-inheritance: 
   :members: get_delimiter
.. autoclass:: bauble.plugins.garden.plant.PlantNote
   :show-inheritance: 
.. autoclass:: bauble.plugins.garden.plant.PlantChange
   :show-inheritance: 
.. autoclass:: bauble.plugins.garden.plant.PlantStatus
   :show-inheritance: 
.. autoclass:: bauble.plugins.garden.Location
   :show-inheritance: 
.. autoclass:: bauble.plugins.garden.propagation.Propagation
   :show-inheritance: 
.. autoclass:: bauble.plugins.garden.propagation.PropRooted
   :show-inheritance: 
.. autoclass:: bauble.plugins.garden.propagation.PropCutting
   :show-inheritance: 
.. autoclass:: bauble.plugins.garden.propagation.PropSeed
   :show-inheritance: 
.. autoclass:: bauble.plugins.garden.source.Source
   :show-inheritance: 
.. autoclass:: bauble.plugins.garden.source.SourceDetail
   :show-inheritance: 
.. autoclass:: bauble.plugins.garden.source.Collection
   :show-inheritance: 
.. autoclass:: bauble.plugins.garden.accession.Verification
   :show-inheritance: 
.. autoclass:: bauble.plugins.garden.accession.Voucher
   :show-inheritance: 


:mod:`bauble.plugins.abcd`
==========================
.. automodule:: bauble.plugins.abcd
.. autofunction:: bauble.plugins.abcd.validate_xml
.. autofunction:: bauble.plugins.abcd.create_abcd
.. autoclass:: bauble.plugins.abcd.ABCDAdapter
   :members:
.. autoclass:: bauble.plugins.abcd.ABCDExporter

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
.. autofunction:: bauble.plugins.tag.remove_callback
.. autofunction:: bauble.plugins.tag.get_tagged_objects
.. autofunction:: bauble.plugins.tag.untag_objects
.. autofunction:: bauble.plugins.tag.tag_objects
.. autofunction:: bauble.plugins.tag.get_tag_ids
.. autoclass:: bauble.plugins.tag.Tag
.. autoclass:: bauble.plugins.tag.TaggedObj
.. autoclass:: bauble.plugins.tag.TagItemGUI

