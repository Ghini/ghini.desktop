#
# task.py
#
# Description: manage long running tasks
#
import gobject, gtk
import bauble
from bauble.utils.log import debug
import Queue

_task_queue = Queue.Queue(0)

# TODO: after some specified time the status bar should be cleared but not
# too soon, maybe 30 seconds or so but only once the queue is empty, anytime
# something is added to the queue we should set a 30 second timeout to
# check again if the queue is empty and set the status bar message if it's
# empty

# TODO: do we need a timeout function that regulary check the queue or just
# accept that everytime something is queued the task manager keeps running all
# the tasks in the queue until it's empty, the next queueed task would then
# start the process again

# TODO: if we passed some custom class to the tasklet instead of a method then
# the class could have some interface like a cancel() method that tells the
# task to cancel itself

# TODO: catch the quit or closes signals and see if there are any running tasks
# and send then the task cancel signal so they can ask the user if they
# really wan't to cancel the task

# TODO: test callback

def _update_gui():
    while gtk.events_pending():
        gtk.main_iteration()

def _run_task(func, *args, **kwargs):
    task = func(*args, **kwargs)
    try:
        while True:
            task.next()
            _update_gui()
    except StopIteration:
        pass


__message_ids = []

def set_message(msg):
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
    if bauble.gui is None or bauble.gui.widgets is None:
        return
    global _context_id, __message_ids
    for id in __message_ids:
        bauble.gui.widgets.statusbar.remove(_context_id, id)


_flushing = False

def flush():
    '''
    flush out the task queue
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
        except Exception, e:
            if on_error is not None:
                on_error(e)
            else:
                raise
    bauble.set_busy(False)
    clear_messages()
    if bauble.gui is not None:
        bauble.gui.progressbar.set_pulse_step(0)
        bauble.gui.progressbar.set_fraction(0)
        bauble.gui.progressbar.hide()
    _flushing = False



def queue(task, on_quit, on_error, *args):
    """
    @param task: the task to queue
    @param callback: the function to call when the task is finished
    @param args: the arguments to pass to the task
    """
    global _task_queue
    _task_queue.put((task, on_quit, on_error, args))
    flush()
