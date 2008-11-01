#
# task.py
#
# Description: manage long running tasks
#
import gobject, gtk
import bauble
import bauble.utils as utils
from bauble.i18n import *
from bauble.utils.log import debug
import Queue

_task_queue = Queue.Queue(0)

# TODO: after some specified time the status bar should be cleared but not
# too soon, maybe 30 seconds or so but only once the queue is empty, anytime
# something is added to the queue we should set a 30 second timeout to
# check again if the queue is empty and set the status bar message if it's
# empty

# TODO: catch the quit or closes signals and see if there are any running tasks
# and send then the task cancel signal so they can ask the user if they
# really wan't to cancel the task

# TODO: test callback

# WARNING: tasks don't work if called inside a gobject.idle_add
# callback...UPDATE: it seems like they do but they're touchy, we run
# bauble.create_database() inside of bauble._post_loop which
# eventually calls cvs import which is a task

def _update_gui():
    while gtk.events_pending():
        gtk.main_iteration()


class TaskQuitting(Exception):
    pass

def _run_task(func, *args, **kwargs):
    global __gtk_quitting
    task = func(*args, **kwargs)
    try:
        while True:
            if not __gtk_quitting:
                task.next()
                _update_gui()
            else:
                raise TaskQuitting
    except StopIteration:
        pass


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
    except NameError, e: # context_id not defined
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
    for id in __message_ids:
        bauble.gui.widgets.statusbar.remove(_context_id, id)


_flushing = False

def flush():
    '''
    Flush out the task queue.  This is normally called by
    :func:`bauble.task.queue`
    '''
    global _flushing
    if _flushing:
        return

    _flushing = True
    bauble.set_busy(True)
    while not _task_queue.empty():
        if bauble.gui is not None:
            bauble.gui.progressbar.show()
            bauble.gui.progressbar.set_pulse_step(1.0)
            bauble.gui.progressbar.set_fraction(0)
        func, on_quit, on_error, args = _task_queue.get()
        try:
            _run_task(func, *args)
            if on_quit is not None:
                on_quit()
        except (GeneratorExit, TaskQuitting), e:
            raise
        except Exception, e:
            #  we can't raise an exception here since the other
            #  pending tasks would be able to complete...on_error also
            #  shouldn't raise an exception
            #gobject.idle_add(on_error, e)
            on_error(e)

    bauble.set_busy(False)
    clear_messages()
    if bauble.gui is not None:
        bauble.gui.progressbar.set_pulse_step(0)
        bauble.gui.progressbar.set_fraction(0)
        bauble.gui.progressbar.hide()
    _flushing = False


__quit_handler_id = None
__gtk_quitting = False

def _quit():
    global __gtk_quitting
    __gtk_quitting = True
    return 0 # return 0 to remove from gtk quit handlers


def queue(task, on_quit, on_error, *args):
    """
    Queue a new task

    :param task: the task to queue
    :param callback: the function to call when the task is finished
    :param args: the arguments to pass to the task
    """
    global _task_queue
    global __quit_handler_id
    if __quit_handler_id is None:
        level = gtk.main_level()
        __quit_handler_id = gtk.quit_add(level, _quit)
    _task_queue.put((task, on_quit, on_error, args))
    flush()
