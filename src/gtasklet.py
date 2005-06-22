#!/usr/bin/env python

'''A pygtk based pseudo-thread module system'''

__revision__ = '0.1.0'

import gobject
import warnings


class WaitCondition(object):
    '''Base class for all wait-able condition objects.  These are used
    in a yield statement inside tasklets for specifying what event(s)
    it should wait for in order to receive control once more.'''
    
    def __init__(self):
        '''Abstract base class, do not call directly'''
        self.triggered = False

    def arm(self, callback):
        '''Prepare the wait condition to receive events.  The
        "callback" is to be called when the event is triggered.  The
        callback returns True or False; if it returns True, it means
        the WaitCondition object must "rearm" itself, otherwise it
        should disarm.  This normally should not be called by the
        programmer.'''
        raise NotImplementedError

    def disarm(self):
        '''Stop the wait condition from receiving events.  This
        normally should not be called by the programmer.'''
        raise NotImplementedError


class WaitForIO(WaitCondition):
    '''An object that waits for IO conditions on sockets or file descriptors'''
    def __init__(self, filedes, condition=gobject.IO_IN, priority=gobject.PRIORITY_DEFAULT):
        '''WaitForIO(filedes, condition=gobject.IO_IN, priority=gobject.PRIORITY_DEFAULT)

        Creates an object that waits for IO on the file descriptor
        (int) @filedes, a gobject.IOChannel, or an object with a
        fileno() method, such as socket or unix file.'''
        WaitCondition.__init__(self)
        self.filedes = filedes
        self.__condition = condition # listen condition
        self.condition = None # last occurred condition
        self.__callback = None
        self.__id = None
        self.__priority = priority

    def arm(self, callback):
        '''See WaitCondition.arm'''
        self.__callback = callback
        if self.__id is None:
            try:
                ## http://bugzilla.gnome.org/show_bug.cgi?id=139176
                iochan = isinstance(self.filedes, gobject.IOChannel)
            except AttributeError:
                iochan = False
            if iochan:
                self.__id = self.filedes.add_watch(self.__condition,
                                                   self.__io_cb,
                                                   priority=self.__priority)
            else:
                if isinstance(self.filedes, int):
                    filedes = self.filedes
                else:
                    filedes = self.filedes.fileno()
                self.__id = gobject.io_add_watch(filedes, self.__condition,
                                                 self.__io_cb,
                                                 priority=self.__priority)

    def disarm(self):
        '''See WaitCondition.disarm'''
        if self.__id is not None:
            gobject.source_remove(self.__id)
            self.__id = None
            self.__callback = None

    def __io_cb(self, filedes, condition):
        self.triggered = True
        self.condition = condition
        retval = self.__callback(self)
        self.triggered = False
        if not retval:
            self.__id = None
        return retval


class WaitForTimeout(WaitCondition):
    '''An object that waits for a specified ammount of time (a timeout)'''
    def __init__(self, timeout, priority=gobject.PRIORITY_DEFAULT):
        '''WaitForTimeout(timeout, priority=gobject.PRIORITY_DEFAULT)

        An object that waits for a specified ammount of time,
        indicated by the parameter @timeout in miliseconds'''
        
        WaitCondition.__init__(self)
        self.timeout = timeout
        self.__id = None
        self.__callback = None
        self.__priority = priority
        
    def arm(self, callback):
        '''See WaitCondition.arm'''
        if self.__id is None:
            self.__callback = callback
            self.__id = gobject.timeout_add(self.timeout, self.__timeout_cb,
                                            priority=self.__priority)

    def disarm(self):
        '''See WaitCondition.disarm'''
        if self.__id is not None:
            gobject.source_remove(self.__id)
            self.__id = None
            self.__callback = None

    def restart(self):
        '''Restart the timeout.'''
        callback = self.__callback
        self.disarm()
        self.arm(callback)

    def __timeout_cb(self):
        self.triggered = True
        retval = self.__callback(self)
        self.triggered = False
        if not retval:
            self.__id = None
        #print "%r: returning %r" % (self, retval)
        return retval

class WaitForIdle(WaitCondition):
    '''An object that waits for the main loop to become idle'''

    def __init__(self, priority=gobject.PRIORITY_DEFAULT_IDLE):
        '''WaitForIdle(priority=gobject.PRIORITY_DEFAULT_IDLE)

        An object that waits for the main loop to become idle, with a
        priority indicated by @priority'''
        WaitCondition.__init__(self)
        self.__callback = None
        self.__id = None
        self.__priority = priority

    def arm(self, callback):
        '''See WaitCondition.arm'''
        if self.__id is None:
            self.__callback = callback
            self.__id = gobject.idle_add(self.__idle_cb, self.__priority)

    def disarm(self):
        '''See WaitCondition.disarm'''
        if self.__id is not None:
            gobject.source_remove(self.__id)
            self.__id = None
            self.__callback = None

    def __idle_cb(self):
        self.triggered = True
        retval = self.__callback(self)
        self.triggered = False
        if not retval:
            self.__id = None
        return retval


class WaitForTasklet(WaitCondition):
    '''An object that waits for a tasklet to complete'''
    def __init__(self, tasklet):
        '''WaitForTasklet(timeout)

        An object that waits for a specified ammount of time,
        indicated by the parameter @timeout in miliseconds'''
        
        WaitCondition.__init__(self)
        self.__tasklet = tasklet
        self.__id = None
        self.__callback = None
        self.retval = None
        
    def arm(self, callback):
        '''See WaitCondition.arm'''
        self.__callback = callback
        if self.__id is None:
            self.__id = self.__tasklet.add_join_callback(self.__join_cb)

    def disarm(self):
        '''See WaitCondition.disarm'''
        if self.__id is not None:
            self.__tasklet.remove_join_callback(self.__id)
            self.__id = None
            self.__callback = None

    def __join_cb(self, retval):
        self.triggered = True
        self.retval = retval
        self.__callback(self)
        self.triggered = False
        self.__id = None
        self.__tasklet = None
        self.__callback = None

class WaitForSignal(WaitCondition):
    '''An object that waits for a signal emission'''

    def __init__(self, obj, signal):
        '''WaitForSignal(obj, signal)

        Waits for a signal to be emitted on a specific GObject instance'''
        WaitCondition.__init__(self)
        assert isinstance(obj, gobject.GObject)
        self.__obj = obj
        self.signal = signal
        self.__callback = None
        self.__id = None
        self.signal_args = None

    def arm(self, callback):
        '''See WaitCondition.arm'''
        if self.__id is None:
            self.__callback = callback
            self.__id = self.__obj.connect(self.signal, self.__signal_cb)

    def disarm(self):
        '''See WaitCondition.disarm'''
        if self.__id is not None:
            self.__obj.disconnect(self.__id)
            self.__id = None
            self.__callback = None

    def __signal_cb(self, obj, *args):
        self.triggered = True
        self.signal_args = args
        retval = self.__callback(self)
        self.triggered = False
        if not retval:
            self.__id = None
        return retval


class WaitForProcess(WaitCondition):
    '''An object that waits for a process to end'''
    def __init__(self, pid):
        '''WaitForProcess(pid)

        Creates an object that waits for the subprocess identified by
        @pid to end.'''
        WaitCondition.__init__(self)
        self.pid = pid
        self.__callback = None
        self.__id = None
        self.status = None

    def arm(self, callback):
        '''See WaitCondition.arm'''
        self.__callback = callback
        if self.__id is None:
            self.__id = gobject.child_watch_add(self.pid, self.__child_cb)

    def disarm(self):
        '''See WaitCondition.disarm'''
        if self.__id is not None:
            gobject.source_remove(self.__id)
            self.__id = None
            self.__callback = None

    def __child_cb(self, pid, status):
        self.triggered = True
        self.status = status
        self.__callback(self)
        self.triggered = False
        self.status = None
        self.__id = None

class Tasklet(object):
    '''An object that launches and manages a tasklet.'''
    def __init__(self, func=None, *args):
        '''Tasklet(func=None, *args)

        Launch a generator function @func (with arguments *args) as
        tasklet.  If @func is None, run() should be overridden in a
        subclass.'''
        self.__join_callbacks = {}
        self.wait_list = []
        ## bootstrap the tasklet
        self.__func = func
        self.gen = self.run(*args)
        self.__func = None
        self.__next_round()
        self.__event = None

    def run(self, *args):
        """Method that executes the task.  Can be overridden in a
        subclass, if no function is passed into the constructor."""
        return self.__func(self, *args)

    def __next_round(self):
        old_wait_list = self.wait_list
        ## Disarm old conditions before giving control to the tasklet,
        ## otherwise bad things may happen
        for cond in old_wait_list:
            cond.disarm()

        gen_value = None
        try:
            if hasattr(self.gen, "next"):
                gen_value = self.gen.next()
            else: self.return_value(None)
        except StopIteration:
            self.return_value(None)
            return
        
        
        if gen_value is None:
            self.wait_list = ()
        elif isinstance(gen_value, list):
            self.wait_list = gen_value
        elif isinstance(gen_value, tuple):
            self.wait_list = list(gen_value)
        else:
            self.wait_list = [gen_value]

        ## (re)arm the conditions
        for cond in self.wait_list:
            cond.arm(self.__wait_condition_cb)

    def __wait_condition_cb(self, triggered_cond):
        assert self.__event is None
        self.__event = triggered_cond
        self.__next_round()
        self.__event = None
        if self.wait_list is None:
            return False
        else:
            return (triggered_cond in self.wait_list)

    def add_join_callback(self, callback):
        '''add_join_callback(callback) -> int

        Add a callable to be invoked when the tasklet finishes.
        Return a connection handle that can be used in
        remove_join_callback()'''
        handle = hash(callback)
        while handle in self.__join_callbacks:
            handle += 1
        self.__join_callbacks[handle] = callback
        return handle

    def remove_join_callback(self, handle):
        '''remove_join_callback(handle)

        Remove a callable previously added with add_join_callback()'''
        del self.__join_callbacks[handle]

    def return_value(self, retval):
        '''Called from the tasklet function; return a value and stop
        execution.'''
        for cond in self.wait_list:
            cond.disarm()
        self.gen = None
        del self.wait_list[:]
        for callback in self.__join_callbacks.values():
            callback(retval)
        self.__join_callbacks.clear()

    def post_message(self, message):
        '''Post a message to be received by the tasklet as an event'''
        assert self.__event is None
        self.__event = message
        self.__next_round()
        if self.__event is not None:
            warnings.warn("Tasklet forgot to receive a message!")
        self.__event = None

    def get_event(self):
        '''Get next event.  Can be either a WaitCondition instance
        that was previously yielded, in case it was triggered, or some
        other python object that may have been sent with
        post_message().'''
        event = self.__event
        self.__event = None
        return event
        


## ----------------------------
## And here are the examples...
## ----------------------------
class _CountSomeNumbers2(Tasklet):
    '''Counts numbers with at random time spacings'''
    def run(self, count, timeout):
        '''Execute the task.'''
        for i in xrange(count):
            print ">> _count_some_numbers2", i
            yield WaitForTimeout(random.randint(70, timeout))
            event = self.get_event()
            if event == 'quit':
                ## this would be the place to do some cleanup.
                return
        self.return_value(count*2)

def _count_some_numbers1(tasklet, count):
    '''Counts numbers with at fixed time spacings'''
    timeout = WaitForTimeout(1000)
    for i in xrange(count):
        print "_count_some_numbers1", i
        task2 = _CountSomeNumbers2(None, 10, 130)
        taskwait = WaitForTasklet(task2)
        yield timeout, taskwait
        event = tasklet.get_event()
        if event is timeout:
            print ">>> Got tired of waiting for task!! Canceling!"
            ## have to cancel task wait notification first, otherwise
            ## we get reentrancy, which is not allowed.
            #taskwait.disarm()
            ## send a message asking the tasklet to stop
            task2.post_message('quit')
        else:
            print ">>> task returned %r, good task!" % taskwait.retval
            ## restart timeout from scratch, otherwise it keeps
            ## running and we end up giving the next task too little
            ## time.
            #timeout.restart()


def _test():
    '''a simple test/example'''
    Tasklet(_count_some_numbers1, 100)
    gobject.MainLoop().run()


if __name__ == '__main__':
    import random
    _test()
