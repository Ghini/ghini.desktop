#
# Copyright (c) 2005,2006,2007,2008,2009 Brett Adams <brett@belizebotanic.org>
# Copyright (c) 2012-2015 Mario Frasca <mario@anche.no>
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
# task.py
"""
The bauble.task module allows you to queue up long running tasks. The
running tasks still block but allows the GUI to update.
"""
import logging
from typing import Any, Optional

import bauble
import fibra
from bauble.gtkinit import Gtk

logger: Any = logging.getLogger(__name__)

# TODO: after some specified time the status bar should be cleared but not
# too soon, maybe 30 seconds or so but only once the queue is empty, anytime
# something is added to the queue we should set a 30 second timeout to
# check again if the queue is empty and set the status bar message if it's
# empty

# TODO: provide a way to create background tasks that don't call set_busy()

# TODO: check the fibra version here....has to be >0.17 or maybe
# ==0.17 since fibra doesn't seem to ensure any sort of API
# compatibility

schedule: Any = fibra.schedule()

__running: bool = False
__kill: bool = False

# Define once at module level
_context_id: Optional[int] = None
__message_ids: list[int] = []


def running():
    """
    Return True/False if a task is running.
    """
    return __running


def kill() -> None:
    """
    Kill the current task.

    This will kill the task when it goes idle and not while it's
    running.  A task is idle after it yields.
    """
    global __kill
    __kill = True


def _idle() -> None:
    """
    Called when a task is idle.
    """
    while Gtk.events_pending():
        Gtk.main_iteration()

    global __kill
    if __kill:
        __kill = False
        raise StopIteration()


schedule.register_idle_func(_idle)


def queue(task) -> None:
    """Run a task.

    task should be a generator with side effects. it does not matter what it
    yields, it is important that it does stop from time to time yielding
    whatever it wants to, and causing the side effect it has to cause.

    """

    # TODO: we might have to add a quit handler similar to what the
    # pre-fibra task manager had but raising StopIteration in the task
    # idle function might be enough...just needs more testing
    schedule.install(task)
    if bauble.gui is not None:
        bauble.gui.set_busy(True)
        bauble.gui.progressbar.show()
        bauble.gui.progressbar.set_pulse_step(1.0)
        bauble.gui.progressbar.set_fraction(0)
    global __running
    __running = True
    try:
        schedule.run()
    except Exception:
        raise
    finally:
        __running = False
        if bauble.gui is not None:
            bauble.gui.progressbar.set_pulse_step(0)
            bauble.gui.progressbar.set_fraction(0)
            bauble.gui.progressbar.hide()
            bauble.gui.set_busy(False)
        clear_messages()

def set_message(msg):
    """
    A convenience function for setting a message on the
    statusbar. Returns the message id
    """
    if not (bauble.gui and bauble.gui.widgets and bauble.gui.widgets.statusbar):
        return
    global _context_id
    if _context_id is None:
        _context_id = bauble.gui.widgets.statusbar.get_context_id("__task")
        logger.info(f"new context id: {_context_id}")
    msg_id = bauble.gui.widgets.statusbar.push(_context_id, msg)
    __message_ids.append(msg_id)
    return msg_id


def clear_messages() -> None:
    """
    Clear all the messages from the statusbar that were set with
    :func:`bauble.task.set_message`
    """
    if not (bauble.gui and bauble.gui.widgets and bauble.gui.widgets.statusbar):
        return

    for mid in __message_ids:
        bauble.gui.widgets.statusbar.remove(_context_id, mid)
    __message_ids.clear()