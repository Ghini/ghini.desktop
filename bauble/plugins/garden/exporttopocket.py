# -*- coding: utf-8 -*-
#
# Copyright 2017 Mario Frasca <mario@anche.no>.
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

import logging
logger = logging.getLogger(__name__)

from bauble.plugins.garden.accession import Accession
from bauble.plugins.garden.location import Location
from bauble.plugins.garden.plant import PlantNote, Plant
from bauble.plugins.garden.source import (Source, Contact)

from bauble import db
from bauble import pluginmgr
from bauble.i18n import _

def export_to_pocket():
    from bauble.plugins.plants import Species, Genus, Family
    session = db.Session()
    
    session.close()
    return True


class ExportToPocketTool(pluginmgr.Tool):
    category = _('Export')
    label = _('to ghini.pocket')

    @classmethod
    def start(self):
        export_to_pocket()
