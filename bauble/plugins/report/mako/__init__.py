#
# Copyright 2008-2010 Brett Adams
# Copyright 2012-2016 Mario Frasca <mario@anche.no>.
# Copyright 2017 Jardín Botánico de Quito
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
# report/mako/
#
import logging
import os
import re
from gettext import gettext as _
from typing import Any

from bauble import paths as bpaths
from bauble import utils as butils
from bauble.gtkinit import Gtk
from bauble.plugins.report import TemplateFormatterPlugin

logger: Any = logging.getLogger(__name__)


class MakoFormatterPlugin(TemplateFormatterPlugin):
    """
    The MakoFormatterPlugin passes the values in the search
    results directly to a Mako template.  It is up to the template
    author to validate the type of the values and act accordingly if not.
    """

    title: str = "Mako"
    extension: str = ".mako"
    domain_pattern: Any = re.compile(r"^##\s*DOMAIN\s+([a-z_]*)\s*$")
    option_pattern: Any = re.compile(
        r"^## OPTION ([a-z_]*): \("
        "type: ([a-z_]*), "
        "default: '(.*)', "
        r"tooltip: '(.*)'\)$"
    )
    paths: Any = []

    @classmethod
    def get_template(cls, name):
        """Load a Mako template from available paths."""
        if not name:
            msg = _("Please select a template.")
            butils.idle_message(msg, Gtk.MessageType.WARNING)
            return False
        cls.paths = [
            os.path.join(bpaths.user_dir(), "templates"),
            os.path.join(bpaths.lib_dir(), "plugins", "report", "templates"),
        ]
        path, name = os.path.split(name)
        if path:
            cls.paths.insert(0, path)
        from mako.lookup import TemplateLookup

        try:
            lookup = TemplateLookup(
                directories=cls.paths, input_encoding="utf-8", output_encoding="utf-8"
            )
            template = lookup.get_template(name)
            return template
        except Exception as e:
            import traceback

            butils.idle_message(
                f"Reading template {name}\n{type(e).__name__}({e})\n{traceback.format_exc()}",
                type=Gtk.MessageType.ERROR,
            )
            logger.error(f"Failed to load template {name}: {e}")
            return False


formatter_plugin = MakoFormatterPlugin
