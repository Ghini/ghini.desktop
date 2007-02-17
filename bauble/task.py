#
# task.py
#
# Description: manage long running tasks
#
import gobject
import bauble
import bauble.utils.gtasklet as gtasklet
from bauble.utils.log import debug
import Queue

_task_queue = Queue.Queue(0)

# TODO: after some specified time the status bar should be cleared but not
# too soon, maybe 30 seconds or so but only once the queue is empty, anytime
# something is added to the queue we should set a 30 second timeout to
# check again if the queue is empty and set the status bar message if it's
# empty

# TODO: how do we pass arguments to the callbac

# TODO: every task should have a way to change the status bar message, i don't
# know if this means passing a sub task to the main task to send messages too
# or if we can just call some function that sets the message on the queue
# task sig:
# task(status

# IDEAS/PLANNING
# - after each task finishes it must yeild the quit message, possibly with a 
# return value or error code or exception or something
# when the quit message is recieved we should check the queue and start the next
# task, this would be a good time to add the timer to clear the statusbar, 
# anytime a new task is added we should clear the timer
# - if there is an error or exception raised in the middle of execution then
# how should we handle it
# - eask task should be independent of the others
# - ability to pass custom message names and callback that should be called 
# when those message are sent
# - may have to pass the task itself to the quit message so we know which task
# has quit, if not the task then we need a way to identify the task

# TODO: in general we need to be conscious of what is run in a generator 
# context and what isn't

# TODO: instead of sending the quit message we could just have a task that waits 
# for the the current task to finish and call the callback when it finishes
# so then it doesn't matter how it exits or send the quit message 

# TODO: do we need a timeout function that regulary check the queue or just 
# accept that everytime something is queue the task manager keeps running all
# the tasks in the queue until it's empty, the next queueed task would then 
# start the process again

# callback -- 
# - it seems the only good way to do callbacks is if the callback itself is
# a tasklet, you just have to keep this in mind in case you want to open
# dialogs or anything else that might conflict with a tasklet
# - maybe we could indicate what type of callback we should call, a method or
# another tasklet

# TODO: if we passed some custom class to the tasklet instead of a method then
# the class could have some interface like a cancel() method that tells the
# task to cancel itself

# TODO: catch the quit or closes signals and see if there are any running tasks
# and send then the task cancel signal so they can ask the user if they
# really wan't to cancel the task

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
    
    def internal():
        global _flushing
        _flushing = True
        bauble.set_busy(True)        
        while not _task_queue.empty():
            if bauble.gui is not None:
                bauble.gui.progressbar.show()
                bauble.gui.progressbar.set_pulse_step(1.0)
                bauble.gui.progressbar.set_fraction(0)
            tasklet, callback, args = _task_queue.get()
            _current_task = gtasklet.run(tasklet(*args))      
            yield gtasklet.WaitForTasklet(_current_task)
            gtasklet.get_event()
            debug('type(callback) = %s' % type(callback))
            #yield gtasklet.run(callback())
            if callback is not None:
                callback()
        bauble.set_busy(False)
        clear_messages()
        if bauble.gui is not None:
            bauble.gui.progressbar.set_pulse_step(0)
            bauble.gui.progressbar.set_fraction(0)
            bauble.gui.progressbar.hide()                    
        _flushing = False
        
    gtasklet.run(internal())



def queue(task, callback, *args):
    """
    @param task: the task to queue
    @param callback: the function to call when the task is finished
    @param args: the arguments to pass to the task
    
    NOTE: callbacks haven't been implemented
    """
    # TODO: the problem with callbacks is that they are run in the context
    # of the generator so terrible things start to happen with things
    # like dialog boxes run in the callback
    _task_queue.put((task, callback, args))
    flush()
