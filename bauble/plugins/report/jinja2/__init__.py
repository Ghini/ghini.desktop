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

# import math
import os
import re

# import shutil
# import tempfile
from gettext import gettext as _
from typing import Any

from bauble import paths, utils
from bauble.gtkinit import Gtk
from bauble.plugins.report import PS, SVG, TemplateFormatterPlugin

logger: Any = logging.getLogger(__name__)


class Jinja2FormatterPlugin(TemplateFormatterPlugin):

    title: str = "Jinja2"
    extension: str = ".jj2"
    domain_pattern: Any = re.compile(r"^\{#\s*DOMAIN\s+([a-z_]*)\s*#\}$")
    option_pattern: Any = re.compile(
        r"^{#\s*OPTION ([a-z_]*): \("
        r"type: ([a-z_]*), "
        r"default: '(.*)', "
        r"tooltip: '(.*)'\)\s*#}$"
    )

    @classmethod
    def get_template(name):
        """Load a Jinja2 template from available paths."""
        if not name:
            msg = _("Please select a template.")
            utils.idle_message(msg, Gtk.MessageType.WARNING)
            return None
        try:
            path, name = os.path.split(name)
            from jinja2 import (
                ChoiceLoader,
                Environment,
                FileSystemLoader,
                PackageLoader,
            )

            env = Environment(
                loader=ChoiceLoader(
                    [
                        FileSystemLoader(path),
                        FileSystemLoader(os.path.join(paths.user_dir(), "templates")),
                        PackageLoader("bauble.plugins.report", "templates"),
                    ]
                )
            )
            env.globals["PS"] = PS
            env.globals["SVG"] = SVG
            env.globals["enumerate"] = enumerate
            template = env.get_template(name)
        except RuntimeError as e:
            import traceback

            utils.idle_message(
                f"Reading template {name}\n{type(e).__name__}({e})\n{traceback.format_exc()}",
                type=Gtk.MessageType.ERROR,
            )
            logger.error(f"Failed to load Jinja2 template {name}: {e}")
            return None

        return template


formatter_plugin = Jinja2FormatterPlugin
