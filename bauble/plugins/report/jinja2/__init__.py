# -*- coding: utf-8 -*-
#
# Copyright 2018 Mario Frasca <mario@anche.no>.
# Copyright 2018 Tanager Botanical Garden <tanagertourism@gmail.com>
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
# report/jinja2/
#

import logging
logger = logging.getLogger(__name__)

import os
import shutil
import tempfile
import math
import re

from gi.repository import Gtk

from bauble.plugins.report import TemplateFormatterPlugin, PS, SVG
from bauble import utils
from bauble import paths


class Jinja2FormatterPlugin(TemplateFormatterPlugin):

    title = 'Jinja2'
    extension = '.jj2'
    domain_pattern = re.compile(r"^\{#\s*DOMAIN\s+([a-z_]*)\s*#\}$")
    option_pattern = re.compile(r"^{#\s*OPTION ([a-z_]*): \("
                                r"type: ([a-z_]*), "
                                r"default: '(.*)', "
                                r"tooltip: '(.*)'\)\s*#}$")

    def get_template(name):
        if not name:
            msg = _('Please select a template.')
            utils.idle_message(msg, Gtk.MessageType.WARNING)
            return False
        try:
            path, name = os.path.split(name)
            from jinja2 import Environment, PackageLoader, ChoiceLoader, FileSystemLoader
            env = Environment(
                loader=ChoiceLoader([FileSystemLoader(path),
                                     FileSystemLoader(os.path.join(paths.user_dir(), 'templates')),
                                     PackageLoader('bauble.plugins.report', 'templates')])
            )
            env.globals['PS'] = PS
            env.globals['SVG'] = SVG
            env.globals['enumerate'] = enumerate
            template = env.get_template(name)
        except RuntimeError as e:
            import traceback
            utils.idle_message("Reading template %s\n%s(%s)\n%s" % (name, type(e).__name__, e, traceback.format_exc()), type=Gtk.MessageType.ERROR)
            return False

        return template


formatter_plugin = Jinja2FormatterPlugin
