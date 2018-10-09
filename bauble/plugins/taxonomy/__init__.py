# -*- coding: utf-8 -*-
#
# Copyright 2018 Mario Frasca <mario@anche.no>.
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
logger.setLevel(logging.DEBUG)

from .classes import Taxon, Rank
from bauble import pluginmgr
from bauble import paths
from bauble import db

import os.path


class TaxonomyPlugin(pluginmgr.Plugin):
    tools = []
    provides = {'Rank': Rank,
                'Taxon': Taxon, }

    @classmethod
    def init(cls):
        pluginmgr.provided.update(cls.provides)

    @classmethod
    def install(cls, import_defaults=True):
        """
        Do any setup and configuration required by this plugin like
        creating tables, etc...
        """
        if not import_defaults:
            return
        path = os.path.join(paths.lib_dir(), "plugins", "taxonomy", "default")
        filenames = [os.path.join(path, f) for f in (
            'rank.txt', 'taxon.txt', )]

        logger.debug('TaxonomyPlugin about to import %s' % (filenames, ))
        from bauble.plugins.imex.csv_ import CSVImporter
        csv = CSVImporter()
        csv.start(filenames, metadata=db.metadata, force=True)


plugin = TaxonomyPlugin
