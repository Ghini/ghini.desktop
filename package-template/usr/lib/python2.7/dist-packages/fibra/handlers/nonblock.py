"""
The nonblock module provides a handler class (NonBlockHandler) which allows
a tasklet to momentarily run in a seperate thread.

If a tasklet yields NonBlock(), it's next iteration will be performed in a
thread.

The handler uses a threadpool with a default of 2 worker threads.
"""

from Queue import Queue, Empty, Full
from threading import Thread

import time


class Unblock(object):
    """yield Unblock(task) to process next iteration in a seperate thread.
    """
    def __init__(self): 
        pass


class NonBlockHandler(object):
    """Allows a tasklet to yield Unblock(), which will cause the next
    iteration to run in a seperate thread.
    """
    active = False
    handled_types = [Unblock]
    def __init__(self, worker_count=2):
        self.inbox = Queue()
        self.outbox = Queue()
        self.running = True
        self.running_tasks = 0
        self.workers = None
        self.worker_count = worker_count

    def status(self):
        return self.running_tasks

    def start_workers(self):
        self.workers = set([Thread(target=self.worker_thread) for i in xrange(self.worker_count)])
        for worker in self.workers:
            worker.setDaemon(True)
            worker.start()

    def worker_thread(self):
        while self.running:
            task = self.inbox.get()
            try:
                r = task.next()
            except Exception, e:
                r = e
            self.outbox.put((r,task))

    def handle(self, unblock, task):
        self.active = True
        if self.workers is None: self.start_workers()
        self.running_tasks += 1
        self.inbox.put(task)

    def pre_schedule(self):
        while self.running_tasks > 0:
            try:
                r,task = self.outbox.get_nowait()
            except Empty:
                self.active = True
                return
            self.running_tasks -= 1
            self.schedule.install(task, initial_value=r)
        self.active = False

                

