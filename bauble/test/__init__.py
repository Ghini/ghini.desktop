#
# Copyright (c) 2005,2006,2007,2008,2009 Brett Adams <brett@belizebotanic.org>
# Copyright (c) 2012-2015 Mario Frasca <mario@anche.no>
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
import logging
from logging import LogRecord

# Global configuration
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


def update_gui() -> None:
    """
    Flush any GTK Events.  Used for doing GUI testing.
    """

    from bauble.gtkinit import Gtk

    while Gtk.events_pending():
        Gtk.main_iteration()


def check_dupids(filename: str) -> List[str]:
    """
    Return a list of duplicate ids in a glade file
    """
    ids = set()
    duplicates = set()
    from lxml import etree

    tree = etree.parse(filename)
    for el in tree.iter():
        if el.tag == "col":
            continue
        elid = el.get("id")
        if elid not in ids:
            ids.add(elid)
        elif elid and elid not in duplicates:
            duplicates.add(elid)
    logger.warning(duplicates)
    return list(duplicates)


class MockLoggingHandler(logging.Handler):
    """Mock logging handler to check for expected logs."""

    messages: Dict[str, Dict[str, List[str]]]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.reset()
        super().__init__(*args, **kwargs)

    def emit(self, record: LogRecord) -> None:
        received = self.messages.setdefault(record.name, {}).setdefault(
            record.levelname.lower(), []
        )
        received.append(self.format(record))

    def reset(self) -> None:
        self.messages = {}


def mockfunc(
    msg: Optional[str] = None,
    name: Optional[str] = None,
    caller: Optional[Any] = None,
    result: bool = False,
    *args: Any,
    **kwargs: Any,
) -> bool:
    if caller is not None and hasattr(caller, "invoked"):
        caller.invoked.append((name, msg))
    return result
