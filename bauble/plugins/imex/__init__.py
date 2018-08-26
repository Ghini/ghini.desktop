# -*- coding: utf-8 -*-
#
# Copyright 2015 Mario Frasca <mario@anche.no>.
#
# This file is part of ghini.desktop.
#
# ghini.desktop is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ghini.desktop is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ghini.desktop. If not, see <http://www.gnu.org/licenses/>.
#
# imex plugin
#
# Description: plugin to provide importing and exporting
#

# TODO: would be best to provide some intermediate format so that we could
# transform from any format to another

import bauble.pluginmgr as pluginmgr
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
