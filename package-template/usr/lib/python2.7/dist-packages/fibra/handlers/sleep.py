"""
The sleep module provides a handler class (SleepHandler) that allows a 
tasklet to pause its execution for a period of time.

A tasklet can yield a float, long, int or sleep object which represents
the duration to sleep before. The tasklet is then swapped out of the 
scheduler and re-installed when the required amount of time has passed.

The sleep handler uses a priority queue (using the heapq module) to store
swapped out tasklets. This means many tasks can be paused and waiting without
effecting the performance of the scheduler.
"""

from time import time as time_func
from heapq import heappush, heappop


class Sleep(object): 
    def __init__(self, T):
        self.T = T

    def __float__(self):
        return float(self.T)


class SleepHandler(object):
    """The SleepHandler will pause execution of a task for X seconds when a
    int, float, long or sleep object is yielded by a task.
    The Handler can also defer scheduling of a task for X second using 
    the defer method call.

    The SleepHandler uses a priority queue for scheduling, which make 
    it possible to schedule or pause a very large number of tasks
    without effecting performance of the scheduler.
    """
    active = False
    handled_types = [Sleep, float, int]

    def __init__(self):
        self.tasks = []
        self.exported_functions = [self.defer]

    def status(self):
        return len(self.tasks)

    def defer(self, T, task):
        """Defer starting a task for T seconds.
        """
        self.handle(T, task)

    def pre_schedule(self):
        now = time_func()
        while self.tasks:
            D,task,T = heappop(self.tasks)
            if now - T >= D:
                self.schedule.install(task)
            else:
                heappush(self.tasks, (D,task,T))
                break 
        self.active = len(self.tasks) > 0

    def handle(self, T, task):
        heappush(self.tasks, (float(T),task,time_func()))
        self.active = True

