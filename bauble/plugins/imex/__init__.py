#
# imex plugin
#
# Description: plugin to provide importing and exporting
#

# TODO: would be best to provide some intermediate format so that we could
# transform from any format to another

import os, csv, traceback
import gtk.gdk, gobject
from sqlalchemy import *
import bauble
from bauble.i18n import *
import bauble.utils as utils
import bauble.pluginmgr as plugin
import bauble.task
from bauble.utils.log import log, debug
import bauble.utils.gtasklet as gtasklet
import Queue
from bauble.plugins.imex.csv_ import CSVImportTool, CSVExportTool, \
     CSVExportCommandHandler, CSVImportCommandHandler
from bauble.plugins.imex.xml import XMLExportTool, XMLExportCommandHandler

# TODO: it might be best to do something like the reporter plugin so
# that this plugin provides a generic interface for importing and exporting
# and let the different tools provide the settings which are then passed to
# their start() methods

# see http://www.postgresql.org/docs/current/static/sql-copy.html

class ImexPlugin(plugin.Plugin):
    tools = [CSVImportTool, CSVExportTool, XMLExportTool]
    commands = [CSVExportCommandHandler, CSVImportCommandHandler,
                XMLExportCommandHandler]


plugin = ImexPlugin
