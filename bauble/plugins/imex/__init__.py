#
# imex plugin
#
# Description: plugin to provide importing and exporting
#

# TODO: would be best to provide some intermediate format so that we could
# transform from any format to another

import os, csv, traceback
from sqlalchemy import *
import bauble
import bauble.utils as utils
import bauble.pluginmgr as pluginmgr
import bauble.task
import Queue
from bauble.plugins.imex.csv_ import CSVImportTool, CSVExportTool, \
     CSVExportCommandHandler, CSVImportCommandHandler
from bauble.plugins.imex.iojson import JSONImportTool, JSONExportTool
from bauble.plugins.imex.xml import XMLExportTool, XMLExportCommandHandler

# TODO: it might be best to do something like the reporter plugin so
# that this plugin provides a generic interface for importing and exporting
# and let the different tools provide the settings which are then passed to
# their start() methods

# see http://www.postgresql.org/docs/current/static/sql-copy.html

# NOTE: always beware when writing an imex plugin not to use the
# table.insert().execute(*list) statement or it will fill in values for
# missing columns so that all columns will have some value

class ImexPlugin(pluginmgr.Plugin):
    tools = [CSVImportTool, CSVExportTool, 
             JSONImportTool, JSONExportTool, XMLExportTool]
    commands = [CSVExportCommandHandler, CSVImportCommandHandler,
                XMLExportCommandHandler]


plugin = ImexPlugin
