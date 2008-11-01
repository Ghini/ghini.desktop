Bauble API Documentation
------------------------

:mod:`bauble`
=============
.. automodule:: bauble
.. autofunction:: bauble.main_is_frozen
.. autofunction:: bauble.save_state
.. autofunction:: bauble.quit
.. autofunction:: bauble.set_busy
.. autofunction:: bauble.command_handler
.. autofunction:: bauble.main

:mod:`bauble.db`
================
.. automodule:: bauble.db

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


:mod:`bauble.i18n`
=======================
.. automodule:: bauble.i18n


:mod:`bauble._gui`
=======================
.. automodule:: bauble._gui


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
.. autoclass:: bauble.pluginmgr.RegistryEmptyError
.. autoclass:: bauble.pluginmgr.Registry
   :members:
.. autoclass:: bauble.pluginmgr.RegistryEntry
   :members:
.. autoclass:: bauble.pluginmgr.Plugin
   :members:
.. autoclass:: bauble.pluginmgr.Tool
.. autoclass:: bauble.pluginmgr.View
.. autoclass:: bauble.pluginmgr.CommandHandler
.. autofunction:: bauble.pluginmgr.topological_sort


:mod:`bauble.prefs`
=======================
.. automodule:: bauble.prefs


:mod:`bauble.task`
=======================
.. automodule:: bauble.task
.. autofunction:: bauble.task.queue
.. autofunction:: bauble.task.flush
.. autofunction:: bauble.task.set_message
.. autofunction:: bauble.task.clear_messages


:mod:`bauble.types`
=======================
.. automodule:: bauble.types


:mod:`bauble.utils`
=======================
.. automodule:: bauble.utils


:mod:`bauble.view`
=======================
.. automodule:: bauble.view



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

:mod:`bauble.plugins.abcd`
==========================
.. automodule:: bauble.plugins.abcd

:mod:`bauble.plugins.imex`
==========================
.. automodule:: bauble.plugins.imex

:mod:`bauble.plugins.report`
============================
.. automodule:: bauble.plugins.report

:mod:`bauble.plugins.report.default`
====================================
.. automodule:: bauble.plugins.report.default

:mod:`bauble.plugins.report.template`
=====================================
.. automodule:: bauble.plugins.report.template

:mod:`bauble.plugins.tag`
=========================
.. automodule:: bauble.plugins.tag
