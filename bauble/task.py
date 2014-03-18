#
# task.py
"""
The bauble.task module allows you to queue up long running tasks. The
running tasks still block but allows the GUI to update.
"""
import Queue

import fibra
import gobject
import gtk

import bauble
import bauble.utils as utils
from bauble.utils.log import debug, error

# TODO: after some specified time the status bar should be cleared but not
# too soon, maybe 30 seconds or so but only once the queue is empty, anytime
# something is added to the queue we should set a 30 second timeout to
# check again if the queue is empty and set the status bar message if it's
# empty

# TODO: provide a way to create background tasks that don't call set_busy()

# TODO: check the fibra version here....has to be >0.17 or maybe
# ==0.17 since fibra doesn't seem to ensure any sort of API
# compatability

schedule = fibra.schedule()

__running = False
__kill = False


def running():
    """
    Return True/False if a task is running.
    """
    return __running


def kill():
    """
    Kill the current task.

    This will kill the task when it goes idle and not while its
    running.  A task is idle after it yields.
    """
    global __kill
    __kill = True


def _idle():
    """
    Called when a task is idle.
    """
    while gtk.events_pending():
        gtk.main_iteration(block=False)

    global __kill
    if __kill:
        __kill = False
        raise StopIteration()


schedule.register_idle_func(_idle)


def queue(task):
    """
    Run a task.
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
        __running = False
    except:
        raise
    finally:
        __running = False
        if bauble.gui is not None:
            bauble.gui.progressbar.set_pulse_step(0)
            bauble.gui.progressbar.set_fraction(0)
            bauble.gui.progressbar.hide()
            bauble.gui.set_busy(False)
        clear_messages()


__message_ids = []


def set_message(msg):
    """
    A convenience function for setting a message on the
    statusbar. Returns the message id
    """
    if bauble.gui is None or bauble.gui.widgets is None:
        return
    global _context_id
    try:
        _context_id
    except NameError, e:  # context_id not defined
        _context_id = bauble.gui.widgets.statusbar.get_context_id('__task')
    msg_id = bauble.gui.widgets.statusbar.push(_context_id, msg)
    __message_ids.append(msg_id)
    return msg_id


def clear_messages():
    """
    Clear all the messages from the statusbar that were set with
    :func:`bauble.task.set_message`
    """
    if bauble.gui is None or bauble.gui.widgets is None \
            or bauble.gui.widgets.statusbar is None:
        return
    global _context_id, __message_ids
    for mid in __message_ids:
        bauble.gui.widgets.statusbar.remove(_context_id, mid)
