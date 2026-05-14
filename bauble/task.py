# -*- coding: utf-8 -*-
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
The bauble.task module allows you to queue up long running tasks.
Tasks run in a worker thread; GUI updates are marshalled to the GTK main loop.
"""

import inspect
import threading

from gi.repository import Gtk, GLib

import bauble

import logging
logger = logging.getLogger(__name__)

__running = False
__kill = False
__thread = None
__message_ids = []
_context_id = None
_state_lock = threading.Lock()


def running():
    with _state_lock:
        return __running


def kill():
    global __kill
    with _state_lock:
        __kill = True


def _ui_set_busy(is_busy):
    if bauble.gui is None:
        return False
    try:
        bauble.gui.set_busy(is_busy)
        if is_busy:
            bauble.gui.progressbar.show()
            bauble.gui.progressbar.set_pulse_step(1.0)
            bauble.gui.progressbar.set_fraction(0)
        else:
            bauble.gui.progressbar.set_pulse_step(0)
            bauble.gui.progressbar.set_fraction(0)
            bauble.gui.progressbar.hide()
    except Exception:
        logger.exception('error while updating busy/progressbar state')
    return False


def _ui_clear_messages():
    if bauble.gui is None or bauble.gui.widgets is None or bauble.gui.widgets.statusbar is None:
        return False
    global _context_id, __message_ids
    try:
        if _context_id is None:
            _context_id = bauble.gui.widgets.statusbar.get_context_id('__task')
        for mid in __message_ids:
            bauble.gui.widgets.statusbar.remove(_context_id, mid)
        __message_ids = []
    except Exception:
        logger.exception('error while clearing status messages')
    return False


def _worker(task, args, kwargs):
    global __running, __kill
    try:
        if callable(task) and not inspect.isgenerator(task):
            task = task(*args, **kwargs)
        elif args or kwargs:
            raise TypeError('queue() received args/kwargs but task is not callable')

        if inspect.isgenerator(task):
            while True:
                with _state_lock:
                    if __kill:
                        __kill = False
                        break
                try:
                    next(task)
                except StopIteration:
                    break
        elif callable(task):
            task()
    finally:
        with _state_lock:
            __running = False
            __kill = False
        GLib.idle_add(_ui_set_busy, False)
        GLib.idle_add(_ui_clear_messages)


def queue(task, *args, **kwargs):
    global __running, __thread
    with _state_lock:
        if __running:
            raise RuntimeError('a task is already running')
        __running = True

    GLib.idle_add(_ui_set_busy, True)

    __thread = threading.Thread(target=_worker, args=(task, args, kwargs), daemon=True)
    __thread.start()


def set_message(msg):
    if bauble.gui is None or bauble.gui.widgets is None:
        return
    global _context_id
    if _context_id is None:
        _context_id = bauble.gui.widgets.statusbar.get_context_id('__task')
        logger.info('new context id: %s' % _context_id)

    def _push():
        msg_id = bauble.gui.widgets.statusbar.push(_context_id, msg)
        __message_ids.append(msg_id)
        return False

    GLib.idle_add(_push)


def clear_messages():
    GLib.idle_add(_ui_clear_messages)
