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

schedule = fibra.schedule()

__running = False
__kill = False

def running():
    return _running


def kill():
    """
    Kill the current task.
    """
    global __kill
    __kill = True


def _idle():
    """
    Called when a task is idle.
    """
    while gtk.events_pending():
        gtk.main_iteration()

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
    # idle function might be enough
    schedule.install(task)
    bauble.set_busy(True)
    if bauble.gui is not None:
        bauble.gui.progressbar.show()
        bauble.gui.progressbar.set_pulse_step(1.0)
        bauble.gui.progressbar.set_fraction(0)
    global _running
    _running = True
    schedule.run()
    _running = False
    if bauble.gui is not None:
        bauble.gui.progressbar.set_pulse_step(0)
        bauble.gui.progressbar.set_fraction(0)
        bauble.gui.progressbar.hide()
    bauble.set_busy(False)



# def _update_gui():
#     while gtk.events_pending():
#         gtk.main_iteration()


# TODO: This exception is probably not relevant since we switched to
# the task system to using fibra...but i'm gonna leave it here for now
# for compatibility reasons
class TaskQuitting(Exception):
    pass

# def _run_task(func, *args, **kwargs):
#     global __gtk_quitting
#     task = func(*args, **kwargs)
#     try:
#         while True:
#             if not __gtk_quitting:
#                 task.next()
#                 _update_gui()
#                 # TODO: should we sleep here for maybe 1ms to make
#                 # things more responsive
#             else:
#                 raise TaskQuitting
#     except StopIteration:
#         pass


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


#_flushing = False

# def flush():
#     '''
#     Flush out the task queue.  This is normally called by
#     :func:`bauble.task.queue`
#     '''
#     global _flushing
#     if _flushing:
#         return

#     _flushing = True
#     bauble.set_busy(True)
#     while not _task_queue.empty():
#         if bauble.gui is not None:
#             bauble.gui.progressbar.show()
#             bauble.gui.progressbar.set_pulse_step(1.0)
#             bauble.gui.progressbar.set_fraction(0)
#         func, on_quit, on_error, args = _task_queue.get()
#         try:
#             _run_task(func, *args)
#             if on_quit:
#                 on_quit()
#         except (GeneratorExit, TaskQuitting), e:
#             raise
#         except Exception, e:
#             #  we can't raise an exception here since the other
#             #  pending tasks would be able to complete...on_error also
#             #  shouldn't raise an exception
#             #gobject.idle_add(on_error, e)
#             error(e)
#             if on_error:
#                 on_error(e)

#     bauble.set_busy(False)
#     clear_messages()
#     if bauble.gui is not None:
#         bauble.gui.progressbar.set_pulse_step(0)
#         bauble.gui.progressbar.set_fraction(0)
#         bauble.gui.progressbar.hide()
#     _flushing = False


# __quit_handler_id = None
# __gtk_quitting = False

# def _quit():
#     global __gtk_quitting
#     __gtk_quitting = True
#     return 0 # return 0 to remove from gtk quit handlers


# def queue(task, on_quit, on_error, *args):
#     """
#     Queue a new task

#     :param task: the task to queue
#     :param callback: the function to call when the task is finished
#     :param args: the arguments to pass to the task
#     """
#     global _task_queue
#     global __quit_handler_id
#     if __quit_handler_id is None:
#         level = gtk.main_level()
#         __quit_handler_id = gtk.quit_add(level, _quit)
#     _task_queue.put((task, on_quit, on_error, args))
#     flush()
