import select
import socket
import time

from errno import EBADF



class Read(object):
    def __init__(self, fd, timeout=0):
        self.fd = fd
        self.timeout = timeout


class Write(object):
    def __init__(self, fd, timeout=0):
        self.fd = fd
        self.timeout = timeout


class Close(object):
    def __init__(self, fd):
        self.fd = fd


class IOHandler(object):
    handled_types = [Read, Write, Close]
    active = False

    def __init__(self):
        self.readers = {}
        self.writers = {}
    
    def status(self):
        print self.readers
        print self.writers
        return len(self.readers), len(self.writers)
    

    def select(self):
        readers = self.readers.keys()
        writers = self.writers.keys()
        all = readers + writers
        try:
            return select.select(readers, writers, all, 0)
        except socket.error, e:
            if e.errno == EBADF:
                for fd in readers:
                    try: 
                        select.select([fd], [], [], 0)
                    except socket.error:
                        task, check, timeout = self.readers.pop(fd)
                        self.schedule.install(task, IOError("read has EBADF %s"%task))
                for fd in writers:
                    try: 
                        select.select([], [fd], [], 0)
                    except socket.error:
                        task, check, timeout = self.writers.pop(fd)
                        self.schedule.install(task, IOError("read has EBADF %s"%task))
                return self.select()
            else:
                raise

    def pre_schedule(self):
        if self.readers or self.writers:
            install = self.schedule.install
            r, w, e = self.select()
            error = set()
            for i in e:
                raise IOError("Something bad happened.")
            for i in r:
                install(self.readers.pop(i)[0])
            for i in w:
                install(self.writers.pop(i)[0])

        now = time.time()
        for fd, (task, check, timeout) in self.readers.items():
            if check == 0: continue
            if now > timeout:
                self.readers.pop(fd)
                install(task, IOError("read has timed out %s"%task))
        for fd, (task, check, timeout) in self.writers.items():
            if check == 0: continue
            if now > timeout:
                self.writers.pop(fd)
                install(task, IOError("write has timed out %s"%task))

        self.active = len(self.readers) + len(self.writers)
    
    def handle(self, event, task):
        self.active = True
        if event.__class__ is Write:
            if event.fd in self.writers: raise IOError("fd is being used")
            self.writers[event.fd] = task, event.timeout, time.time() + event.timeout
        if event.__class__ is Read:
            if event.fd in self.readers: raise IOError("fd is being used")
            self.readers[event.fd] = task, event.timeout, time.time() + event.timeout
        if event.__class__ is Close:
            if event.fd in self.readers: 
                t, timeout, ts = self.readers.pop(event.fd)
                self.schedule.install(t, IOError('IO was closed'))
            if event.fd in self.writers: 
                t, timeout, ts = self.writers.pop(event.fd)
                self.schedule.install(t, IOError('IO was closed'))
            self.schedule.install(task)
    
