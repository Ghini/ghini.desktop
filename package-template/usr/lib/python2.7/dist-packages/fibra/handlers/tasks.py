"""
The tasks module provides a handler class (TaskHandler) which allows a
tasklet to create other tasklets.

If a tasklet yields a generator object, it is installed into the scheduler
and will run concurrently with the tasklet.

If a tasklet yields a Wait object with a generator object as its argument,
it will install the generator into the scheduler (making it a tasklet) and 
pause its execution and wait until the new tasklet is finished.

"""

import types



class Finished(Exception):
    """Raised when a sub task finishes.
    """
    pass


class Async(object):
    """yield Async(task) to start another task and run it concurrently.
    """
    def __init__(self, task, watch=None):
        self.task = task
        self.watch = watch


class Return(object):
    """yield Return(value) from a spawned generator to return that value
    to the waiting task.
    """
    def __init__(self, value):
        self.value = value


class Suspend(object):
    """yield Suspend() to remove a task from the schedule.
    The task will need to be resumed manually by the application.
    """
    def __init__(self):
        pass


class Self(object):
    """yield Self() to get a reference to the yielding task.
    """
    def __init__(self): 
        pass


class TasksHandler(object):
    """The task handler allows running tasks to start other tasks by 
    yielding generator, on_finish or spawn objects.
    """
    active = False
    handled_types = [Async, StopIteration, types.GeneratorType, Return, Suspend, Self]
    
    def __init__(self):
        self.waiting_tasks = {}
        self.handlers = dict((i, getattr(self, "handle_%s" % i.__name__)) for i in self.handled_types)

    def status(self):
        return len(self.waiting_tasks), self.waiting_tasks

    def handle(self, new_task, task):
        self.active = True
        self.handlers[type(new_task)](new_task, task)

    def handle_Return(self, event, task):
        try:
            waiting_task = self.waiting_tasks.pop(task)
        except KeyError, e:
            raise RuntimeError("Return yielded from a top level task. (%s)"%task)
        self.schedule.unwatch(task)
        self.schedule.install(waiting_task, event.value)

    def handle_StopIteration(self, exception, task):
        try:
            v = None
            if task in self.schedule.watchers:
                self.schedule.unwatch(task)
                #v = Finished() #TODO only do this if requested.
            self.schedule.install(self.waiting_tasks.pop(task), v)
                
        except KeyError:
            pass

    def handle_Async(self, event, task):
        self.schedule.install(event.task) 
        self.schedule.install(task) 
        if event.watch:
            self.schedule.watch(event.task, event.watch)

    def handle_Suspend(self, event, task):
        pass

    def handle_Self(self, event, task):
        self.schedule.install(task, task)

    def handle_generator(self, new_task, task):
        def watcher(e):
            parent = self.waiting_tasks.pop(new_task)
            self.schedule.install(parent, e)
        self.waiting_tasks[new_task] = task
        self.schedule.watch(new_task, watcher)
        self.schedule.install(new_task)

    def pre_schedule(self): 
        self.active = len(self.waiting_tasks) > 0
